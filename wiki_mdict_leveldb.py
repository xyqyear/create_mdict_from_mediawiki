# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup

# 用于压缩图片
from PIL import Image

import re
import os
import gc
import time
import json
import platform
import requests

# 用于unquote
import urllib.parse

# 用于暂存图片于内存
import io

from config import (site, upload, api_address,
                    namespaces, is_download_image,
                    is_update_mode, is_use_proxy,
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
    with open('latest_log.txt', 'a', encoding='utf-8') as log_file:
        if debug_mode == 0 and content == '':
            return
        elif debug_mode == 1:
            log_info = '\n[debug]: '.join([content, debug])
        else:
            log_info = content

        log_info = '[{}]:\n'.format(time.asctime()) + log_info + '\n'
        print(log_info)
        log_file_info = '\n[debug]: '.join([content, debug])
        log_file_info = '[{}]:\n'.format(time.asctime()) + log_file_info + '\n'
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
        logger('','获取代理地址出错{}'.format(str(e)))
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
    :param mode: 不为0就处理斜杠否则处理斜杠。
    :return:
    """
    if mode == 0:
        return string\
            .replace('"', '_').replace('<', '_') \
            .replace('>', '_').replace('|', '_') \
            .replace(':', '_').replace('?', '_').replace('*', '_')

    else:
        return string\
            .replace('\\', '_').replace('/', '_') \
            .replace('"', '_').replace('<', '_') \
            .replace('>', '_').replace('|', '_') \
            .replace(':', '_').replace('?', '_').replace('*', '_')


def new_db_file():
    """
    用于获取数据库对象
    :return: 数据库链接对象的列表
    """
    logger('正在创建/取得数据库')
    titles_database = leveldb.LevelDB('titles')
    contents_database = leveldb.LevelDB('contents')
    redirects_database = leveldb.LevelDB('redirects')
    images_database = leveldb.LevelDB('images')
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
                if proxy:
                    pass
                else:
                    raise BaseException
                content_response = requests.get(
                    url,
                    timeout=20,
                    proxies={'http': 'http://{}'.format(proxy),
                             'https': 'http://{}'.format(proxy)}
                )
                break
            except BaseException as e:
                retry_count -= 1
                logger(url + '获取失败，重试剩余{}次'
                       .format(retry_count), str(e))
                if 'Cannot connect to proxy' in str(e) or \
                        'Connection aborted' in str(e):
                    delete_proxy(proxy)
                    retry_count += 1
    # 如果不使用
    else:
        while not retry_count == 0:
            try:
                content_response = requests.get(url, timeout=20)
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
    for namespace in namespaces:
        next_title = ''
        while True:
            request_url = api_address + '?action=query&' \
                                        'format=json&' \
                                        'list=allpages&' \
                                        'apfrom={continue_}&' \
                                        'apnamespace={namespace}&' \
                                        'apfilterredir=nonredirects&' \
                                        'aplimit=500'\
                                        .format(continue_=next_title,
                                                namespace=namespace)

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
        for title,status in titles_db.RangeIter():
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
        main_content_source_soup = BeautifulSoup(content_source, 'lxml')

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
        content_source = re.sub(r'(\r\n){2,}','\r\n',content_source)

        # 寻找图片
        img_tags = main_content_source_soup.find_all('img', src=True)
        for img in img_tags:
            # 这里也处理一下图片src
            # 1.unquote
            # 2.替换windows文件名敏感字符
            # 3.替换后缀名
            # 4.替换路径为本地路径
            img_replace = urllib.parse.unquote(img['src'])
            # 如果图片不是upload的图片，就舍弃
            if upload not in img_replace:
                continue
            img_replace = img_replace \
                .replace('.png', '.jpg') \
                .replace('.gif', '.jpg') \
                .replace('.jpeg', '.jpg')\
                .replace('https://', '/')\
                .replace('http://', '/')\
                .replace('//', '/')

            img_replace = handle_file_name(img_replace)

            content_source = content_source \
                .replace(img['src'], img_replace)
            # leveldb只允许一个同名键存在，所以就不用检查是否存在于数据库中了
            db_put(images_db, img['src'], [])

        return content_source

    def get_content(self, title):
        api_url = api_address + '?action=query&' \
                                'format=json&' \
                                'prop=revisions%7Credirects&' \
                                'titles={title}&' \
                                'rvprop=content%7Ctimestamp&' \
                                'rvparse=1&' \
                                'rdprop=title&' \
                                'rdlimit=500'\
                                .format(title=title)
        # 获得api返回
        content_response = get_response(api_url)

        if content_response:
            logger('获取页面成功')
        else:
            logger('获取页面失败')
            return

        # 获得api返回json
        response_json = content_response.json()

        # 获得页面信息
        page_json = response_json['query']['pages']
        page_info = [value for key, value in page_json.items()][0]
        if 'revisions' not in page_info:
            print('no revisions')
            return
        source = page_info['revisions'][0]['*']
        date = page_info['revisions'][0]['timestamp']

        if 'redirects' in page_info:
            for value in page_info['redirects']:
                redirected_from = value['title']
                content_json = json.dumps({'content': '@@@LINK=' + title})
                db_put(redirects_db, redirected_from, content_json)

        # 处理源码以及添加图片
        main_content_source = self.handle_content(source)

        # 添加内容到self.contents当中
        content_json = json.dumps(
            {'content': main_content_source, 'source': source, 'date': date})
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

            self.get_content(title)

            # 计算本次消耗的时间并计算平均时间
            self.processed_this_time += 1
            average_time = ((time.time() - self.start_time)
                            / self.processed_this_time)
            logger('[average_time]:{} s'.format(average_time))
            # 计算预计剩余时间
            logger('[remaining_time]:{} hours'
                   .format((self.page_num - i) * average_time / 3600))

            i += 1
            if not is_use_proxy:
                time.sleep(2)

            if test_mode:
                if i == 20:
                    break


class UpdateChecker:
    def __init__(self):
        self.process_num = \
            len([title for title, stats in titles_db.RangeIter()]) / 50
        self.processed = 0
        self.start_time = time.time()

    def check_update(self):

        for titles in self.get_next_50_titles():
            logger('正在检查更新...', str(titles))

            titles_str = '|'.join(titles)

            request_url = api_address + '?action=query&' \
                'format=json&' \
                'prop=revisions&' \
                'titles={titles_str}&' \
                'rvprop=timestamp'\
                .format(titles_str=titles_str)

            response = get_response(request_url, -1)
            if response:
                response_json = response.json()
            else:
                continue

            # 获得所有标题的最新date
            pages = [date for page_id, date in response_json['query']['pages'].items()]
            dates = dict()
            for page in pages:
                if 'title' in page and 'revisions' in page:
                    title = page['title']
                    date = page['revisions'][0]['timestamp']
                    dates[title] = date

            # 开始核对日期
            out_of_date_titles = ''
            for title, new_date in dates.items():
                if not db_exist(contents_db, title):
                    continue
                old_content = db_get(contents_db, title)
                old_content_json = json.loads(old_content)
                old_date = old_content_json['date']
                if not old_date == new_date:
                    out_of_date_titles += title + '  |  '
                    db_put(titles_db, title, [])

            logger('需要更新的页面：' + (out_of_date_titles if out_of_date_titles else '0'))

            # 计算剩余时间
            self.processed += 1
            average_time = \
                (time.time() - self.start_time) / self.processed
            remaining_time = \
                (self.process_num - self.processed) * average_time

            logger('average_time:{} s\nremaining_time:{}'
                   .format(average_time, remaining_time))

    @staticmethod
    def get_next_50_titles():
        """
        用于迭代接下来50个标题
        :return:
        """
        titles = list()
        for title, content in titles_db.RangeIter():
            titles.append(title.decode('utf-8'))
            if len(titles) == 50:
                yield titles
                titles = list()
        if titles:
            yield titles


# 下载图片
def download_image(main_site, quality):
    id_ = 0
    images_num = len([i for i in images_db.RangeIter()])
    start_time = time.time()
    for image, stats in images_db.RangeIter():
        # 如果下载过了就不下了
        if json.loads(stats.decode('utf-8')):
            continue
        img_original_url = image.decode()
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

        # 这个是文件的相对路径
        img_file_rear_path = img_url\
            .replace('https://', '')\
            .replace('http://', '')

        # unquote一下防止文件名过长
        img_file_rear_path = urllib.parse.unquote(img_file_rear_path)

        # 处理一下文件路径
        img_file_rear_path = handle_file_name(img_file_rear_path)
        img_file_rear_path = img_file_rear_path \
            .replace('.png', '.jpg') \
            .replace('.gif', '.jpg') \
            .replace('.jpeg', '.jpg')

        img_file_path = os.path.join(
            os.path.abspath('.'), 'upload', img_file_rear_path)

        img_forth_path, img_name = os.path.split(img_file_path)

        # 如果这张图片已经存在就跳过
        if os.path.exists(img_file_path):
            logger('{}已经存在，跳过。'.format(img_name))
            id_ += 1
            continue

        logger(
            '正在保存{}\n剩余{}张'.format(
                img_name,
                images_num - id_),
            img_original_url + '\nfile:' + img_file_path)
        # 如果目录不存在就创建
        if not os.path.exists(img_forth_path):
            os.makedirs(img_forth_path)

        # 尝试获取图片。
        img_requests = get_response(img_url)

        # 打开图片，并且处理图片为RGB模式，省空间
        # 不清楚为什么这里也会出错，不过姑且先加一个try吧
        try:
            img_object = Image.open(io.BytesIO(img_requests.content))
            img_rgb = img_object.convert('RGB')
            # 以一定的质量保存图片，质量在main里面指定
            img_rgb.save(img_file_path, quality=quality)
        except Exception as e:
            logger('保存图片{}失败,放弃。'.format(img_name), str(e))
            id_ += 1
            continue

        db_put(images_db, image, [1])
        # 计算平均时间
        id_ += 1
        average_time = ((time.time() - start_time)
                        / id_)
        logger('[average_time]:{} s'.format(average_time))

        # 计算预计剩余时间
        logger('[remaining_time]:{} hours'
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

    if is_update_mode:
        update_checker = UpdateChecker()
        update_checker.check_update()
        del update_checker
        gc.collect()

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