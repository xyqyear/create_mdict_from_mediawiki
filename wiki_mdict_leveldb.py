# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup

# 用于压缩图片
from PIL import Image

import re
import os
import time
import json
import requests

# 用于unquote
import urllib.parse

# 用于暂存图片于内存
import io

# 用于储存数据
import leveldb

# 网站地址
site = 'https://thwiki.cc'
# 是否是更新模式
is_update_mode = False
# 需要下载的namespaces
#default:
#namespaces = ['0']
# thwiki
namespaces = ['0', # 主
              '4', # THBWiki
              '200', # 用户wiki
              '202', # 用户资料
              '506', # 附带文档
              '508', # 游戏对话
              '512',] # 歌词对话
# API地址
api_address = 'https://thwiki.cc/api.php'
# 是否使用API
is_using_api = False
# 是否使用代理
use_proxy = False
# 代理池服务器地址
proxy_pool = '192.168.10.125:23333'
# 日志输出模式:0是普通，1是debug
debug_mode = 1
# Test_mode
test_mode = True

# Test
# moegirl:
#site = 'https://zh.moegirl.org'


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
    proxy_address = requests.get('http://{}/get'.format(proxy_pool)).text
    return proxy_address


def delete_proxy(proxy_):
    """
    # 删除一个代理地址
    :param proxy_: 
    :return: 
    """
    requests.get("http://{}/delete/?proxy={}".format(proxy_pool, proxy_))


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
    images_database = leveldb.LevelDB('images')
    return [titles_database, contents_database, images_database]


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


def get_all_titles():
    """
    获取所有页面
    """
    pages = 0
    for namespace in namespaces:
        next_title = ''
        while True:
            if use_proxy:
                while True:
                    proxy = get_proxy()
                    try:
                        response_json = requests.get(
                            api_address +
                            '?action=query'
                            '&format=json'
                            '&list=allpages'
                            '&apfrom={continue_}'
                            '&apnamespace={namespace}'
                            '&apfilterredir=nonredirects'
                            '&aplimit=500'.format(continue_ = next_title,
                                                  namespace = namespace),
                            timeout=20,
                            proxies={'http': 'http://{}'.format(proxy),
                                     'https': 'http://{}'.format(proxy)}
                        ).json()
                        break
                    except Exception as e:
                        logger('获取{}错误,重试。'.format(next_title), str(e))
                        if 'Cannot connect to proxy' in str(e) or \
                                'Connection aborted' in str(e):
                            delete_proxy(proxy)
            else:
                while True:
                    try:
                        response_json = requests.get(
                            api_address +
                            '?action=query'
                            '&format=json'
                            '&list=allpages'
                            '&apfrom={continue_}'
                            '&apnamespace={namespace}'
                            '&apfilterredir=nonredirects'
                            '&aplimit=500'.format(continue_=next_title,
                                                  namespace=namespace),
                            timeout=20
                        ).json()
                        break
                    except Exception as e:
                        logger('获取{}错误,五秒后重试。'.format(next_title), str(e))
                        time.sleep(3)

            # 向数据库插入title
            for single_page_json in response_json['query']['allpages']:
                title = single_page_json['title']
                # 插入数据库中
                db_put(titles_db, title, [])

            pages += 1
            logger(' | '.join(['获取所有页面...',
                               '第{}页'.format(pages),
                               '已经抓取{}个词条'.format(pages)]))

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
        self.page_num = len([i for i in titles_db.RangeIter()])

    @staticmethod
    def rep_method(got):
        return '<a class="mw-headline" id=' + got.group(1) + '</a>'

    def handle_content(self, content_source):
        """
        处理维基网页源码并且向数据库插入图片
        :param content_source: 维基内容源代码
        :return: 处理好的源码
        """
        soup = BeautifulSoup(content_source, 'lxml')
        if is_using_api:
            main_content_source_soup = soup
            main_content_source = content_source
        else:
            main_content_source_soup = soup.find(id='mw-content-text')
            main_content_source = str(main_content_source_soup)

        # 替换链接为key
        links = main_content_source_soup.find_all(href=True, title=True)
        for link in links:
            main_content_source = main_content_source.replace(
                'href="' + link['href'], 'href="' + 'entry://{}'.format(link['title']))

        # 替换section为mdict格式
        main_content_source = main_content_source.replace(
            'href="#', 'href="entry://#')
        main_content_source = re.sub(
            r'<span class="mw-headline" id=(.*)</span>',
            self.rep_method,
            main_content_source)

        # 寻找图片
        img_tags = main_content_source_soup.find_all('img', src=True)
        for img in img_tags:
            # 这里也处理一下图片src
            # 1.unquote
            # 2.替换windows文件名敏感字符
            # 3.替换后缀名
            # 4.替换路径为本地路径
            img_replace = urllib.parse.unquote(img['src'])
            img_replace = handle_file_name(img_replace)
            img_replace = img_replace \
                .replace('.png', '.jpg') \
                .replace('.gif', '.jpg') \
                .replace('.jpeg', '.jpg') \
                .replace('https://', '/') \
                .replace('http://', '/') \
                .replace('//', '/')

            main_content_source = main_content_source \
                .replace(img['src'], img_replace)
            db_put(images_db, img['src'], [])

        return main_content_source

    @staticmethod
    def get_response(url):
        """
        get一个url
        集成了重试和使用代理的功能
        :param url: 
        :return: 如果失败了就返回False，成功了就返回requests Response对象
        """
        content_response = False
        # 如果使用代理
        if use_proxy:
            retry_count = 6
            while retry_count > 0:
                proxy = get_proxy()
                try:
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
            retry_count = 4
            while retry_count > 0:
                try:
                    content_response = requests.get(url, timeout=20)
                    break
                except BaseException as e:
                    retry_count -= 1
                    logger(url + '  获取失败，重试剩余{}次'
                           .format(retry_count), str(e))
                    time.sleep(3)
        return content_response

    def get_content(self, title):
        # 获得网页源码
        content_response = self.get_response(title)

        if content_response:
            content_source = content_response.text
            logger('获取页面成功')
        else:
            logger('获取页面失败')
            return

        # 获得标题，如果没有标题就跳过
        title_list = re.findall(
            r'<h1 id="firstHeading" class="firstHeading" lang=".*">(.*)</h1>',
            content_source
        )
        if title_list:
            title = title_list[0]
        else:
            logger('此页面没有内容，跳过')
            return

        # 获得重定向，如果有就添加重定向
        redirected_from_list = re.findall(
            r'<span class="mw-redirectedfrom">.*<a href=".*" class="mw-redirect" title="(.*)">.*</a>.*</span>',
            content_source
        )

        # 页面修改日期,用于判断页面是否更新
        mod_date = re.findall(
            r'<li id="footer-info-lastmod">(.*)</li>',
            content_source
        )
        if mod_date:
            date_text = mod_date[0]
        else:
            date_text = 'None'

        if redirected_from_list:
            redirected_from = redirected_from_list[0]
            logger('{}\n此页面是重定向过来的，正在添加重定向标志'
                   .format(title))
            insert_content([
                redirected_from,
                '@@@LINK=' + title,
                date_text
            ])
            return

        # 如果不是重定向，页面又是最新的，就跳过
        is_up2date = is_content_up2date(title, date_text)
        if is_up2date:
            logger('此页面是最新的，跳过。')
            return

        # 处理源码以及添加图片
        main_content_source = self.handle_content(content_source)

        # 添加内容到self.contents当中
        insert_content([title, main_content_source, date_text])

    def work(self):

        i = 0
        for title,stats in titles_db.RangeIter():
            title = title.decode('utf-8')

            # 如果此页被处理过，就跳过
            if json.loads(stats.decode('utf-8')):
                continue

            logger('正在获取\n{}\n剩余页面:{}'
                   .format(title, self.page_num - i))

            self.get_content(title)

            # 计算本次消耗的时间并计算平均时间
            self.processed_this_time += 1
            average_time = ((time.time() - self.start_time)
                           /self.processed_this_time)
            logger('[average_time]:{}'.format(average_time))
            # 计算预计剩余时间
            logger('[left_time]:{} hours'
                   .format((self.page_num-i)*average_time/3600))

            i += 1
            if not use_proxy:
                time.sleep(2)

            if test_mode:
                if i == 20:
                    break


# TODO
class UpdateChecker:
    def __init__(self):
        pass


# 下载图片
def download_image(main_site, quality):
    image_the_last_id = get_the_last_id_from_table('images')
    processed_this_time = 0
    start_time = time.time()
    for i in range(1, image_the_last_id + 1):

        images_last = image_the_last_id - i
        img_original_url = get_image_url_from_db(i)
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
            processed_this_time += 1
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
            processed_this_time += 1
            continue

        logger(
            '正在保存{}\n剩余{}张'.format(
                img_name,
                images_last),
            img_original_url + '\nfile:' + img_file_path)
        # 如果目录不存在就创建
        if not os.path.exists(img_forth_path):
            os.makedirs(img_forth_path)

        # 尝试获取图片。
        img_requests = None
        # 如果使用代理
        if use_proxy:
            retry_count = 6
            while retry_count > 0:
                proxy = get_proxy()
                try:
                    img_requests = requests.get(
                        img_url,
                        timeout=30,
                        proxies={'http': 'http://{}'.format(proxy),
                                 'https': 'http://{}'.format(proxy)}
                    )
                    if not img_requests.ok:
                        retry_count = 0
                        break
                    break
                except Exception as e:
                    retry_count -= 1
                    logger(img_name + '获取失败，重试第{}次'
                           .format(retry_count), str(e))
                    if 'Cannot connect to proxy' in str(e) or \
                            'Connection aborted' in str(e):
                        delete_proxy(proxy)
                        retry_count += 1

        # 如果不使用代理
        else:
            retry_count = 4
            while retry_count > 0:
                try:
                    img_requests = requests.get(img_url, timeout=30)
                    if not img_requests.ok:
                        retry_count = 0
                        break
                    break
                except Exception as e:
                    retry_count -= 1
                    logger(img_name + '获取失败，重试第{}次'
                           .format(retry_count), str(e))
                    time.sleep(3)

        if retry_count == 0:
            processed_this_time += 1
            continue

        # 打开图片，并且处理图片为RGB模式，省空间
        # 不清楚为什么这里也会出错，不过姑且先加一个try吧
        try:
            img_object = Image.open(io.BytesIO(img_requests.content))
            img_rgb = img_object.convert('RGB')
            # 以一定的质量保存图片，质量在main里面指定
            img_rgb.save(img_file_path, quality=quality)
        except Exception as e:
            logger('保存图片{}失败,放弃。'.format(img_name), str(e))
            processed_this_time += 1
            continue

        # 计算平均时间
        processed_this_time += 1
        average_time = ((time.time() - start_time)
                        / processed_this_time)
        logger('[average_time]:{}'.format(average_time))

        # 计算预计剩余时间
        logger('[left_time]:{} hours'
               .format((image_the_last_id - i) * average_time / 3600))

        time.sleep(2)

# 保存mdict源文件内容
def save_content():
    achievement = open('Achievement.txt', 'w', encoding='utf-8')
    content_the_last_id = get_the_last_id_from_table('content')
    for i in range(1, content_the_last_id + 1):
        title, now_content = get_content_from_db(i)
        achievement.write(title + '\n' + now_content)
        # 如果不是最后一个元素就换行
        if i is not content_the_last_id:
            achievement.write('\n</>\n')

    achievement.close()


if __name__ == '__main__':
    # 下载图片质量，因为wiki图片很多，所以要压缩一下。
    image_quality = 50

    # 新建leveldb文件
    titles_db, contents_db, images_db = new_db_file()

    # 获得所有页面
    get_all_titles()

    # 处理页面并获取图片链接，存入数据库中
    page_handler = PageHandler()
    page_handler.work()

    # 保存mdict源文件内容
    save_content()

    # 下载图片
    download_image(site, image_quality)

    logger('Done', 'Done')
