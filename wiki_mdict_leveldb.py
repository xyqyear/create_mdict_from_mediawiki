# -*- coding:utf-8 -*-

import bs4

# 用于压缩图片
from PIL import Image

import re
import os
import gc
import time
import json
import hashlib
import platform
import requests

# 用于unquote
from urllib.parse import unquote, quote

# 用于暂存图片于内存
import io

from config import (site, api_address,
                    is_download_image, is_use_proxy,
                    proxy_pool, image_quality,
                    debug_mode, test_mode)

# 用于储存数据
import leveldb


def logger(content, debug='no debug info'):
    """
    日志输出器
    :param content: 日志内容
    :param debug: debug内容
    :return:
    """
    time_pre = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open('latest_log.txt', 'a', encoding='utf-8') as log_file:
        if debug_mode == 0 and content == '':
            return
        elif debug_mode == 1:
            log_info = '\n[debug]: '.join([content, debug])
        else:
            log_info = content

        log_info = '[{}]:\n'.format(time_pre) + log_info + '\n'
        print(log_info)
        log_file_info = '\n[debug]: '.join([content, debug])
        log_file_info = '[{}]:\n'.format(time_pre) + log_file_info + '\n'
        log_file.write(log_file_info)


def get_proxy():
    """
    # 获得一个代理地址
    :return: 代理地址
    """
    # 餱甚至这个也会出错，所以也加一个try
    try:
        proxy_address = requests.get('http://{}/get'.format(proxy_pool)).text
        return proxy_address
    except Exception as e:
        logger('', '获取代理地址出错{}'.format(str(e)))
        return False


def delete_proxy(proxy_):
    """
    # 删除一个代理地址
    :param proxy_:
    :return:
    """
    try:
        requests.get("http://{}/delete/?proxy={}".format(proxy_pool, proxy_))
    except Exception as e:
        logger('', '删除代理地址出错{}'.format(str(e)))


def handle_file_name(string, mode=0):
    """
    用于处理文件名敏感的字符串
    :param string: 需要处理的字符串
    :param mode: 为0就不处理斜杠否则处理斜杠。
    :return:
    """
    string = string\
        .replace('"', '_').replace('<', '_') \
        .replace('>', '_').replace('|', '_') \
        .replace(':', '_').replace('?', '_').replace('*', '_')

    if mode == 0:
        return string
    else:
        return string.replace('\\', '_').replace('/', '_')


def new_db_file():
    """
    用于获取数据库对象
    :return: 数据库链接对象的列表
    """
    logger('正在创建/加载数据库')
    if not os.path.exists('database'):
        os.mkdir('database')
    titles_database = leveldb.LevelDB('database/titles')
    contents_database = leveldb.LevelDB('database/contents')
    redirects_database = leveldb.LevelDB('database/redirects')
    images_database = leveldb.LevelDB('database/images')
    return [
        titles_database,
        contents_database,
        redirects_database,
        images_database]


def db_put(db, key, value):
    """
    向数据库添加数据
    所有数据都会被转化为str并用utf-8编码为bytes，存入数据库
    :param db: 数据库对象
    :param key:
    :param value:
    :return:
    """
    db.Put(str(key).encode('utf-8'), str(value).encode('utf-8'))


def db_exist(db, key):
    """
    判断指定key是否存在
    :param db:
    :param key:
    :return:
    """
    try:
        db.Get(str(key).encode('utf-8'))
        return True
    except KeyError:
        return False


def db_get(db, key):
    """
    从数据库获得数据
    :param db:
    :param key:
    :return:
    """
    try:
        return db.Get(str(key).encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger('从数据库获得键出错:{}'.format(str(e)))
        return False


def get_image_filename(image_url):
    """
    使用unquote之前的图片链接生辰一个图片名
    :param image_url:
    :return:
    """
    encoded_image_url = image_url.encode()
    md5 = hashlib.md5(encoded_image_url)
    sha1 = hashlib.sha1(encoded_image_url)

    return md5.hexdigest() + '_' + sha1.hexdigest() + '.jpg'


def get_response(url, retry_count=6):
    """
    get一个url
    集成了重试和使用代理的功能
    :param url: 需要获取的url
    :param retry_count: 重试次数，如果是-1就无限重试
    :return: 如果失败了就返回False，成功了就返回requests Response对象
    """
    content_response = False
    # 如果使用代理
    if is_use_proxy:
        while not retry_count == 0:
            proxy = get_proxy()
            try:
                if not proxy:
                    raise BaseException
                content_response = requests.get(
                    url,
                    timeout=20,
                    proxies={'http': 'http://{}'.format(proxy),
                             'https': 'http://{}'.format(proxy)}
                )
                if not content_response.content:
                    retry_count -= 1
                    break
                else:
                    time.sleep(2)
            except BaseException as e:
                retry_count -= 1
                logger(url + '获取失败，重试剩余{}次'
                       .format(retry_count), str(e))
                if 'Cannot connect to proxy' in str(e) or \
                        'Connection aborted' in str(e):
                    delete_proxy(proxy)
                    retry_count += 1
                time.sleep(2)
    # 如果不使用
    else:
        while not retry_count == 0:
            try:
                content_response = requests.get(url, timeout=20)
                if not content_response.content:
                    retry_count -= 1
                    break
            except BaseException as e:
                retry_count -= 1
                logger(url + '  获取失败，重试剩余{}次'
                       .format(retry_count), str(e))

                time.sleep(3)
    return content_response


def get_all_titles():
    """
    获取所有页面
    """
    pages = 0
    next_title = ''
    while True:
        request_url = api_address + '?action=query&' \
                                    'format=json&' \
                                    'list=allpages&' \
                                    'apfrom={continue_}&' \
                                    'aplimit=500'\
                                    .format(continue_=next_title)

        response = get_response(request_url, -1)
        if response:
            response_json = response.json()
        else:
            continue

        # 向数据库插入title
        for single_page_json in response_json['query']['allpages']:
            title = single_page_json['title']
            # 插入数据库中
            if db_exist(titles_db, title):
                continue
            db_put(titles_db, title, [])
            pages += 1
        logger(' | '.join(['获取所有词条...',
                           '已经获取{}个词条'.format(pages)]))

        # 检查API的返回是否有continue
        # 有就让continue_为apcontinue，否则就
        if 'continue' in response_json:
            next_title = response_json['continue']['apcontinue']
        else:
            break

        if test_mode:
            if pages > 0:
                break


# 差不多已经完工
class PageHandler:
    def __init__(self):
        self.processed_this_time = 0
        self.start_time = time.time()
        self.need_to_handle_titles = list()

        # 需要处理的页面数
        for title, status in titles_db.RangeIter():
            if json.loads(status.decode('utf-8')):
                continue
            self.need_to_handle_titles.append(title)
        self.page_num = len(self.need_to_handle_titles)

    @staticmethod
    def rep_method(got):
        return '<a class="mw-headline" id=' + got.group(1) + '</a>'

    def handle_content(self, content_source):
        """
        处理维基网页源码并且向数据库插入图片
        :param content_source: 维基内容源代码
        :return: 处理好的源码
        """
        main_content_source_soup = bs4.BeautifulSoup(content_source, 'lxml')

        # 去除html注释和代码
        for element in main_content_source_soup(text=lambda text: isinstance(text, bs4.Comment)):
            element.extract()
        [s.extract() for s in main_content_source_soup('script')]

        content_source = main_content_source_soup.prettify()

        # 替换链接为key
        links = main_content_source_soup.find_all(href=True, title=True)
        for link in links:
            content_source = content_source.replace(
                'href="' + link['href'], 'href="' + 'entry://{}'.format(link['title']))

        # 替换section为mdict格式
        content_source = content_source.replace(
            'href="#', 'href="entry://#')
        content_source = re.sub(
            r'<span class="mw-headline" id=(.*)</span>',
            self.rep_method,
            content_source)

        # 删除多余空行
        content_source = re.sub(r'(\r\n){2,}', '\r\n', content_source)

        # 寻找图片
        img_tags = main_content_source_soup.find_all('img', src=True)
        for img in img_tags:

            image_url = img['src']

            image_file_name = get_image_filename(image_url)

            content_source = content_source.replace(img['src'], image_file_name)
            # leveldb只允许一个同名键存在，所以就不用检查是否存在于数据库中了
            db_put(images_db, image_url, [])

        return content_source

    def put_content(self, title):
        api_url = api_address + '?action=parse' \
                                '&format=json' \
                                '&page={title}' \
                                '&prop=text' \
                                .format(title=quote(title))

        content_response = get_response(api_url)
        if not content_response:
            logger('获取页面失败', 'empty response')
            return

        response_json = content_response.json()

        # 获得页面信息
        if 'parse' not in response_json:
            logger('获取页面失败', 'no parse')
            return

        if 'text' not in response_json['parse']:
            logger('获取页面失败', 'no text')
            return

        logger('获取页面成功')

        source = response_json['parse']['text']['*']

        # 处理重定向
        if '<div class=\"redirectMsg\">' in source:
            redirected_to = re.findall(r'<a href=.*? title="(.*?)">', source)[0]
            content_json = json.dumps({'content': '@@@LINK=' + redirected_to})
            db_put(redirects_db, title, content_json)
            logger('页面重定向...')

        else:
            # 处理源码以及添加图片
            main_content_source = self.handle_content(source)

            content_json = json.dumps({'content': main_content_source, 'source': source})
            db_put(contents_db, title, content_json)

        # 标记此页面已经完工
        db_put(titles_db, title, [1])

    def work(self):
        i = 0
        for title, status in titles_db.RangeIter():
            title = title.decode('utf-8')

            # 如果此页被处理过，就跳过
            if json.loads(status.decode('utf-8')):
                continue

            logger('正在获取\n{}\n剩余页面:{}'
                   .format(title, self.page_num - i))

            self.put_content(title)

            # 计算本次消耗的时间并计算平均时间
            self.processed_this_time += 1
            average_time = ((time.time() - self.start_time)
                            / self.processed_this_time)

            logger('[average_time]:{:.2f} s\n[remaining_time]:{:.2f} hours'
                   .format(average_time, (self.page_num - i) * average_time / 3600))

            i += 1
            if not is_use_proxy:
                time.sleep(2)

            if test_mode:
                if i == 20:
                    break


# 下载图片
def download_image(main_site, quality):
    if not os.path.exists('Data'):
        os.mkdir('Data')
    id_ = 0
    images_num = len([i for i in images_db.RangeIter()])
    start_time = time.time()
    for image, stats in images_db.RangeIter():
        # 如果下载过了就不下了
        if json.loads(stats.decode('utf-8')):
            continue
        img_original_url = image.decode('utf-8')

        image_file_name = get_image_filename(img_original_url)
        image_path = os.path.join('Data', image_file_name)

        # 处理图片链接
        if img_original_url.startswith('https://') \
                or img_original_url.startswith('http://'):
            img_url = img_original_url
        elif img_original_url.startswith('//'):
            img_url = 'http:' + img_original_url
        elif img_original_url.startswith('/'):
            img_url = main_site + img_original_url
        # 如果这三种情况都不是的话就跳过这张图片
        else:
            id_ += 1
            continue

        image_name = os.path.split(unquote(img_original_url))[1]

        # 如果这张图片已经存在就跳过
        if os.path.exists(image_path):
            logger('{}已经存在，跳过。'.format(image_name))
            id_ += 1
            continue

        logger(
            '正在保存{}\n剩余{}张'.format(
                image_name,
                images_num - id_),
            img_original_url + '\nfile:' + image_path)

        # 尝试获取图片。
        img_requests = get_response(img_url)

        # 打开图片，并且处理图片为RGB模式，省空间
        # 不清楚为什么这里也会出错，不过姑且先加一个try吧
        try:
            img_object = Image.open(io.BytesIO(img_requests.content))
            img_rgb = img_object.convert('RGB')
            # 以一定的质量保存图片，质量在main里面指定
            img_rgb.save(image_path, quality=quality)
        except Exception as e:
            logger('保存图片{}失败,放弃。'.format(image_name), str(e))
            id_ += 1
            continue

        db_put(images_db, image, [1])
        # 计算平均时间
        id_ += 1
        average_time = ((time.time() - start_time)
                        / id_)
        logger('[average_time]:{:.2f} s'.format(average_time))

        # 计算预计剩余时间
        logger('[remaining_time]:{:.2f} hours'
               .format((images_num - id_) * average_time / 3600))

        time.sleep(2)


# 保存mdict源文件内容
def save_content():
    with open('Achievement.txt', 'w', encoding='utf-8') as f:
        is_first_run = True
        if platform.system() == 'Windows':
            next_line = '\n'
        else:
            next_line = '\r\n'
        for title, content in contents_db.RangeIter():
            title = title.decode('utf-8')
            content = json.loads(content.decode())['content']
            if is_first_run:
                f.write(title + next_line + content + next_line + '</>')
                is_first_run = False
            else:
                f.write(next_line + title + next_line + content + next_line + '</>')
        for title, content in redirects_db.RangeIter():
            title = title.decode('utf-8')
            content = json.loads(content.decode())['content']
            f.write(next_line + title + next_line + content + next_line + '</>')


if __name__ == '__main__':
    # 新建leveldb文件
    titles_db, contents_db, redirects_db, images_db = new_db_file()

    # 获得所有页面
    get_all_titles()

    # 处理页面并获取图片链接，存入数据库中
    page_handler = PageHandler()
    page_handler.work()
    del page_handler
    gc.collect()

    # 保存mdict源文件内容
    save_content()
    del contents_db
    del redirects_db
    gc.collect()

    # 下载图片
    if is_download_image:
        download_image(site, image_quality)

    logger('Done', 'Done')
