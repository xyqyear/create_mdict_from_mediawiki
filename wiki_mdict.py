# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup

# 用于压缩图片
from PIL import Image

import re
import os
import time
import requests

# 用于unquote
import urllib.parse

# 用于暂存图片于内存
import io

# 用于储存数据
import sqlite3

# 网站地址
site = 'https://thwiki.cc'
# API地址
api_address = 'https://thwiki.cc/api.php'
# 是否使用API
is_using_api = False
# 是否使用代理
use_proxy = True
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


def new_db_file(site_url):
    """
    用于获取数据库对象
    :param site_url:网站链接 
    :return: 数据库链接对象
    """
    handled_site_name = handle_file_name(site_url, 1)
    sqlite_file_name = handle_file_name(handled_site_name) + '.db'
    sqlite_file_path = os.path.join(os.path.abspath('.'), sqlite_file_name)
    is_exists = os.path.exists(sqlite_file_path)
    logger('使用数据库文件：{}'.format(sqlite_file_name),
           'sqlite_file_path:' + sqlite_file_path)
    sqlite_con = sqlite3.connect(sqlite_file_path)
    if not is_exists:
        sqlite_con.execute(
            'CREATE TABLE content(id INTEGER, title TEXT, content TEXT, date TEXT)'
        )
        sqlite_con.execute(
            'CREATE TABLE images(id INTEGER, url TEXT)'
        )
        sqlite_con.execute(
            'CREATE TABLE process(id INTEGER, all_pages TEXT)'
        )
        sqlite_con.execute(
            'INSERT INTO process(id, all_pages) values(0, "")'
        )
        sqlite_con.commit()
    return sqlite_con


def insert_content(content_list):
    """
    用于在表中插入内容
    :param content_list: 0标题 1内容 2日期
    :return: 
    """
    b = time.time()

    # 检测title是否存在，如果存在就更新，不存在就插入
    select_content = [
        i[0] for i in sqlite_connection.execute(
            'SELECT title FROM content WHERE title == (?)',
            [content_list[0]]
        )
    ]
    if select_content:
        # 更新数据
        sqlite_connection.execute(
            'UPDATE content SET content=(?),date=(?) WHERE title==(?)',
            [content_list[1], content_list[2], content_list[0]]
        )
    else:
        # 获取上一个数据的id并插入数据
        last_id = get_the_last_id_from_table('content')
        sqlite_connection.execute(
            'INSERT INTO content(id, title, content, date) values(?,?,?,?)',
            [last_id + 1, content_list[0], content_list[1], content_list[2]]
        )

    logger('', '[insert_content]: sqlite_time:{}'
           .format(time.time() - b))


def insert_img(image_url):
    """
    用于在表中插入图片链接
    :param image_url: 图片链接
    :return: 
    """
    b = time.time()
    # 判断链接是否存在于images表中
    select_list = [
        url for url in sqlite_connection.execute(
            'SELECT id FROM images WHERE url in (?)',
            [image_url]
        )]
    if len(select_list) > 0:
        return

    # 获取上一个数据的id并插入数据
    last_id = get_the_last_id_from_table('images')

    sqlite_connection.execute(
        'INSERT INTO images(id, url) values(?,?)',
        [last_id + 1, image_url]
    )

    logger('', '[insert_img]: sqlite_time:{}'
           .format(time.time() - b))


def is_content_up2date(title, date_text):
    """
    用于判断页面是否是最新
    :param title: 页面标题
    :param date_text: 日期信息
    :return: 返回的布尔值表示是否为最新的
    """
    b = time.time()

    # 判断title是否存在
    select_list = [
        date[0] for date in sqlite_connection.execute(
            'SELECT date FROM content WHERE title == (?)',
            [title]
        )
    ]

    logger('', '[is_content_up2date]: sqlite_tile:{}'
           .format(time.time() - b))
    if select_list:
        if date_text == select_list[0]:
            return True
    return False


def update_process_id(pro_id):
    """
    更新目前工作进程id
    :param pro_id: 工作进程id
    :return: 
    """
    b = time.time()
    sqlite_connection.execute('UPDATE process set id=(?)', [pro_id])
    logger('', '[update_process_id]:sqlite_time:{}'
           .format(time.time() - b)
           )


def get_content_from_db(content_id):
    """
    从数据库中获取内容
    :param content_id: 页面id
    :return: (title, content)形式的元组
    """
    b = time.time()
    content_tuple = [
        c for c in sqlite_connection.execute(
            'SELECT title,content FROM content WHERE id == (?)',
            [content_id]
        )][0]

    logger('', '[get_content_from_db]: content_id:{}\nsqlite_time:{}'
           .format(content_id, time.time() - b))
    return content_tuple


def get_image_url_from_db(image_id):
    """
    从数据库中获取图片链接
    :param image_id: 图片id
    :return: 图片url
    """
    b = time.time()
    image_tuple = [
        c for c in sqlite_connection.execute(
            'SELECT url FROM images WHERE id == (?)',
            [image_id]
        )][0]
    logger('', '[get_image_url_from_db]: image_id:{}\nsqlite_time:{}'
           .format(image_id, time.time() - b))
    return image_tuple[0]


def get_the_last_id_from_table(table):
    """
    获取表中最后一个id，如果没有就是0
    :param table: 表名
    :return: 最后一个id
    """
    b = time.time()
    last_id_list = [
        id_ for id_ in sqlite_connection.execute(
            'SELECT id FROM {} ORDER BY id DESC LIMIT 1'
            .format(table)
        )]
    if len(last_id_list) == 0:
        last_id = 0
    else:
        last_id = last_id_list[0][0]
    logger('', '[get_the_last_id_from_table]:sqlite_time:{}'
           .format(time.time() - b))
    return last_id


# 用于获得所有页面
# 已经完工，估计没有什么bug
class AllPagesGetter:
    def __init__(self, main_site, all_pages_page_):
        self.site = main_site
        self.all_pages_page = all_pages_page_
        self.all_pages = list()
        self.pages = 0

        # 初始化时就开始执行函数
        self.get_pages_from_list(self.all_pages_page)

    def get_pages_from_list(self, list_page):

        # 获得索引页的源代码
        # all_pages_soup 是此页所有的wiki页面的源码
        # nav_tags_soup 是上一页下一页的导航
        if use_proxy:
            while True:
                proxy = get_proxy()
                try:
                    page_source = requests.get(
                        list_page,
                        timeout=20,
                        proxies={'http': 'http://{}'.format(proxy),
                                 'https': 'http://{}'.format(proxy)}
                    ).text
                    break
                except Exception as e:
                    logger('获取{}错误,重试。'.format(list_page), str(e))
                    if 'Cannot connect to proxy' in str(e) or \
                            'Connection aborted' in str(e):
                        delete_proxy(proxy)
        else:
            while True:
                try:
                    page_source = requests.get(list_page, timeout=20).text
                    break
                except Exception as e:
                    logger('获取{}错误,五秒后重试。'.format(list_page), str(e))
                    time.sleep(3)

        soup = BeautifulSoup(page_source, 'lxml')
        all_pages_soup = soup.find(class_='mw-allpages-chunk')
        nav_tags_soup = soup.find(class_='mw-allpages-nav')

        # 获得索引页的全部链接并转化为绝对路径
        relative_urls = all_pages_soup.find_all(href=True)
        urls = list()
        for single_href in relative_urls:
            urls.append(self.site + urllib.parse.unquote(
                single_href['href'],
                encoding='utf-8'))

        # 判断当前是否为最后一页，如果不是就获取下一页的链接
        nav_tags = nav_tags_soup.find_all(href=True)
        nav_urls = list()
        for single_nav_tag in nav_tags:
            nav_urls.append(self.site + single_nav_tag['href'])

        self.all_pages += urls
        self.pages += 1
        logger(' | '.join(['获取所有页面...',
                           '第{}页'.format(self.pages),
                           '已经抓取{}个词条'.format(len(self.all_pages))]),
               ' | '.join([nav_urls[0]]))

        # 如果导航栏的链接只有一个(也就是只有上一页或者下一页)而且当前页面不是初始页面
        # 这样就能保证是最后一页
        if len(nav_urls) == 1 and list_page is not self.all_pages_page:
            return
        else:
            # 下一页的链接就取最后一个
            next_page_url = nav_urls[-1]

        if test_mode:
            if self.pages > 0:
                return

        # 这里使用一个迭代要方便些
        self.get_pages_from_list(next_page_url)

    # TODO
    def get_pages_from_list_with_api(self):
        pass

# 差不多已经完工
class PageHandler:
    def __init__(self, all_pages_list):
        self.all_pages = all_pages_list
        # 用于设置目前的页面处理进程
        self.process = 0
        # [标题:处理好的内容源码,...]
        self.processed_this_time = 0
        self.start_time = time.time()

    @staticmethod
    def rep_method(got):
        return '<a class="mw-headline" id=' + got.group(1) + '</a>'

    def handle_content(self, content_source):
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
            insert_img(img['src'])

        return main_content_source

    @staticmethod
    def get_response(url):
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

    def get_content(self, page_url):
        # 获得网页源码
        content_response = self.get_response(page_url)

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
            logger('此页面没有内容，跳过', 'no debug info')
            return

        # 获得重定向，如果有就添加重定向
        redirected_from_list = re.findall(
            r'<a href=.* class="mw-redirect" title="(.*)">.*</a>',
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
                   .format(title), 'no debug info')
            insert_content([
                redirected_from,
                '@@@LINK=' + title,
                date_text
            ])
            return

        # 如果不是重定向，页面又是最新的，就跳过
        is_up2date = is_content_up2date(title, date_text)
        if is_up2date:
            logger('此页面是最新的，跳过。', 'no debug info')
            return

        # 处理源码以及添加图片
        main_content_source = self.handle_content(content_source)

        # 添加内容到self.contents当中
        insert_content([title, main_content_source, date_text])

    # TODO
    def get_content_with_api(self, page_url):
        pass

    def work(self):
        for i in range(self.process, len(self.all_pages)):

            url = self.all_pages[i]
            logger(
                '正在获取\n{}\n剩余页面:{}'.format(
                    url, len(self.all_pages) - i),
                'no debug info')
            self.get_content(url)
            update_process_id(i)

            # 每20个页面commit一次试试
            if i % 20 == 0:
                b = time.time()
                sqlite_connection.commit()
                logger('', '[PageHandler.work]:[sqlite_commit_time]:{}'
                       .format(time.time() - b))

            # 计算本次消耗的时间并计算平均时间
            self.processed_this_time += 1
            average_time = ((time.time() - self.start_time)
                           /self.processed_this_time)
            logger('[average_time]:{}'.format(average_time))

            # 计算预计剩余时间
            logger('[left_time]:{} hours'
                   .format((len(self.all_pages)-i)*average_time/3600))

            time.sleep(2)

            if test_mode:
                if i == 20:
                    break

    # TODO
    def work_with_api(self):
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
            logger('{}已经存在，跳过。'.format(img_name), 'no debug info')
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
               .format(image_the_last_id - i * average_time / 3600))

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
    all_pages_page = site + '/Special:Allpages'
    # 下载图片质量，因为wiki图片很多，所以要压缩一下。
    image_quality = 50

    # 新建sqlite文件并获得sqlite的connection
    sqlite_connection = new_db_file(site)

    process_id = [
        kk[0] for kk in sqlite_connection.execute(
            'SELECT id FROM process'
        )
    ][0]
    # 如果未获取所有页面就获取所有页面
    if process_id == 0:
        pages_getter = AllPagesGetter(site, all_pages_page)
        all_pages = pages_getter.all_pages
        sqlite_connection.execute(
            'UPDATE process set all_pages=(?)', [
                str(all_pages)])
        sqlite_connection.commit()
    else:
        all_pages_str = [
            pages_str[0] for pages_str in sqlite_connection.execute(
                'SELECT all_pages FROM process'
            )
        ][0]
        # 转化文本形式的all_pages为列表
        all_pages = eval(all_pages_str)

    # 处理页面并获取图片链接，存入数据库中
    if process_id >= 0:
        page_handler = PageHandler(all_pages)
        page_handler.process = process_id
        page_handler.work()
        sqlite_connection.commit()
        # 保存mdict源文件内容
        save_content()
        update_process_id(-1)

    # 下载图片
    download_image(site, image_quality)
    update_process_id(0)

    logger('Done', 'Done')
