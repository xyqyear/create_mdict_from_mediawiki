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

# 0是普通，1是debug
debug_mode = 1


def logger(content, debug):
    with open('latest_log.txt','a',encoding='utf-8') as log_file:
        if debug_mode == 0 and content == '':
            return
        elif debug_mode == 1:
            log_info = '\n[debug]: '.join([content, debug])
        else:
            log_info = content

        log_info = '[{}]:\n'.format(time.asctime()) + log_info + '\n'
        print(log_info)
        log_file.write(log_info)


# mode不为0就处理斜杠否则处理斜杠。
def handle_file_name(string, mode=0):
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


# 用于新建数据库文件
def new_db_file(site_url):
    handled_site_name = handle_file_name(site_url, 1)
    sqlite_file_name = handle_file_name(handled_site_name) + '.db'
    sqlite_file_path = os.path.join(os.path.abspath('.'), sqlite_file_name)
    if os.path.exists(sqlite_file_path):
        for t in range(2, 1001):
            sqlite_file_name = handle_file_name(
                handled_site_name) + '{}.db'.format(t)
            sqlite_file_path = os.path.join(
                os.path.abspath('.'), sqlite_file_name)
            if not os.path.exists(sqlite_file_path):
                break
    logger('正在创建数据库', 'sqlite_file_path:' + sqlite_file_path)
    sqlite_con = sqlite3.connect(sqlite_file_path)
    sqlite_con.execute(
        'CREATE TABLE content(id INTEGER, title TEXT, content TEXT)'
    )
    sqlite_con.execute(
        'CREATE TABLE images(id INTEGER, url TEXT)'
    )
    return sqlite_con


# 用于在表中插入内容
def insert_content(content_list):
    b = time.time()
    # 获取上一个数据的id并插入数据
    last_id = get_the_last_id_from_table('content')

    sqlite_connection.execute(
        'INSERT INTO content(id, title, content) values(?,?,?)',
        [last_id + 1, content_list[0], content_list[1]]
    )

    sqlite_connection.commit()
    logger('','[insert_content]: sqlite_time:{}'\
           .format(time.time()-b))


# 用于在表中插入图片链接
def insert_img(image_url):
    b = time.time()
    # 判断链接是否存在于images表中
    select_list = [
        url for url in sqlite_connection.execute(
            'SELECT * FROM images WHERE url in (?)',
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

    sqlite_connection.commit()
    logger('', '[insert_img]: sqlite_time:{}'\
           .format(time.time() - b))


# 从数据库中获取内容
# 返回(title, content)形式的元组
def get_content_from_db(content_id):
    b = time.time()
    content_tuple = [
        c for c in sqlite_connection.execute(
            'SELECT title,content FROM content WHERE id == (?)',
            [content_id]
        )][0]

    logger('', '[get_content_from_db]: content_id:{}\nsqlite_time:{}'\
           .format(content_id, time.time() - b))
    return content_tuple


# 从数据库中获取图片链接
# 返回图片url
def get_image_url_from_db(image_id):
    b = time.time()
    image_tuple = [
        c for c in sqlite_connection.execute(
            'SELECT url FROM images WHERE id == (?)',
            [image_id]
        )][0]
    logger('', '[get_image_url_from_db]: image_id:{}\nsqlite_time:{}'\
           .format(image_id, time.time() - b))
    return image_tuple[0]


# 获取表中最后一个id，如果没有就是0
# 输入的值是表名
def get_the_last_id_from_table(table):
    last_id_list = [
        id_ for id_ in sqlite_connection.execute(
            'SELECT id FROM {} ORDER BY id DESC LIMIT 1'
            .format(table)
        )]
    if len(last_id_list) == 0:
        last_id = 0
    else:
        last_id = last_id_list[0][0]
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

        # Test
        # if self.pages > 0:
        #   return

        # 这里使用一个迭代要方便些
        self.get_pages_from_list(next_page_url)


# 差不多已经完工
class PageHandler:
    def __init__(self, all_pages_list):
        self.all_pages = all_pages_list
        # [标题:处理好的内容源码,...]

    @staticmethod
    def rep_method(got):
        return '<a class="mw-headline" id=' + got.group(1) + '</a>'

    def get_content(self, page_url):

        # 获得网页源码
        content_source = str()
        retry_count = 4
        while retry_count>0:
            try:
                content_source = requests.get(page_url, timeout=20).text
                break
            except BaseException as e:
                retry_count -= 1
                logger(page_url + '  获取失败，重试剩余{}次'.format(retry_count), str(e))
                time.sleep(3)
        if retry_count == 0:
            return

        soup = BeautifulSoup(content_source, 'lxml')

        # 获得主内容源码，标题, 如果有重定向就获取
        main_content_source_soup = soup.find(id='mw-content-text')
        main_content_source = str(main_content_source_soup)
        redirected_from = soup.find(class_='mw-redirectedfrom')
        title_soup = soup.find(id='firstHeading')
        # 如果没有标题（可能是没有此页面导致的），就跳过。
        if title_soup:
            # 如果标题是数字，get_text就会返回一个int，这样子下面处理就会出问题
            title = str(title_soup.get_text())
        else:
            logger('此页面没有内容，跳过', 'no debug info')
            return

        # 如果此页面是重定向来的，内容就是'@@@LINK=' + title
        if redirected_from:
            logger('{}\n此页面是重定向过来的，正在添加重定向标志'.format(title), 'no debug info')
            insert_content([
                redirected_from.find(title=True)['title'],
                '@@@LINK=' + title])
            return

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
            img_replace = img_replace\
                .replace('.png', '.jpg')\
                .replace('.gif', '.jpg')\
                .replace('.jpeg', '.jpg') \
                .replace('https://', '/')\
                .replace('http://', '/') \
                .replace('//', '/')

            main_content_source = main_content_source\
                .replace(img['src'], img_replace)
            insert_img(img['src'])

        # 添加内容到self.contents当中
        insert_content([title, main_content_source])

    def work(self):
        # 从直接for url改成for int，为断点续传做准备
        for i in range(len(self.all_pages)):
            url = self.all_pages[i]
            self.get_content(url)
            logger(
                '正在获取\n{}\n剩余页面:{}'.format(
                    url,len(self.all_pages) - i),
                    'no debug info')
            i += 1
            # Test
            # if i == 200:
            #   break


# 下载图片
def download_image(main_site, quality):
    image_the_last_id = get_the_last_id_from_table('images')
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
            continue

        logger(
            '正在保存{}\n剩余{}张'.format(
                img_name,
                images_last),
            img_original_url +
            img_file_path)
        # 如果目录不存在就创建
        if not os.path.exists(img_forth_path):
            os.makedirs(img_forth_path)

        # 尝试获取图片。
        img_requests = None
        retry_count = 4
        while retry_count>0:
            try:
                img_requests = requests.get(img_url, timeout=30)
                if not img_requests.ok:
                    retry_count = 0
                    break
                break
            except Exception as e:
                retry_count -= 1
                logger(img_name + '获取失败，重试第{}次'.format(retry_count), str(e))
                time.sleep(3)
        if retry_count == 0:
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
            continue


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
    # Test
    # moegirl:
    #site = 'https://zh.moegirl.org'

    # thwiki:
    site = 'https://thwiki.cc'

    all_pages_page = site + '/Special:Allpages'
    # 下载图片质量，因为wiki图片很多，所以要压缩一下。
    image_quality = 50

    # 新建sqlite文件并获得sqlite的connection
    sqlite_connection = new_db_file(site)

    # 获取所有页面
    pages_getter = AllPagesGetter(site, all_pages_page)
    all_pages = pages_getter.all_pages

    # 处理页面并获取图片链接，存入数据库中
    page_handler = PageHandler(all_pages)
    page_handler.work()

    # 保存mdict源文件内容
    save_content()

    # 下载图片
    download_image(site, image_quality)

    logger('Done', 'Done')
