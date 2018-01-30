# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup
from PIL import Image
import requests
import re
import time
import urllib.parse
import sys
import os
import io

# 据说可以玄学加成来避免requests卡死
import socket
socket.setdefaulttimeout(20)

# 用于替换span为a，不然mdict不能正确指向section
def rep_method(got):
    return '<a class="mw-headline" id=' + got.group(1) + '</a>'

site = 'https://thwiki.cc'
upload = '//upload.thwiki.cc'
image_quality = 50

all_urls = [site]
urls_known = []
open('Achievement.txt','w').close()
achieve_file = open('Achievement.txt','a',errors='ignore')
keys = []
redirects = {}                        #文件
url_except = ['http','www','/index.','/%E6%96%87%E4%BB%B6:','/File:',
              #用户                  #模板
              '/%E7%94%A8%E6%88%B7:','/%E6%A8%A1%E6%9D%BF:','/Template:']
imgs = []
start_time = time.time()

num = 0
while not len(all_urls) == 0:

    # 一堆调试信息
    print('num: ', num)
    print('not unquoted  :',all_urls[0])
    print('unquoted      :',urllib.parse.unquote(all_urls[0]))
    print('urls_len      :',len(all_urls))
    print('urls_known_len:',len(urls_known))
    print('redirects_len :',len(redirects))
    print('imgs_len      :',len(imgs))
    if num > 1:
        average_time = (time.time()-start_time)/(len(urls_known)-len(all_urls))
        print('average_time  :',average_time)
        seconds_left = len(all_urls) * average_time
        hours_left = int(seconds_left // 3600)
        minutes_left = int(seconds_left % 3600 // 60)
        print('time_left     :','%s:%s'% (hours_left, minutes_left))

    # 获取内容
    try:
        html_source = requests.get(all_urls[0],timeout=20).text
    except TimeoutError:
        print('get source timeout, retrying')
        continue
    except:
        print('Unexpected error:',sys.exc_info()[0])
        continue

    # 成功就删除此页面

    del all_urls[0]

    # 如果页面没有内容就跳过
    if '本页面目前没有内容' in html_source:
        print('No content, skipping')
        continue
    soup = BeautifulSoup(html_source, 'lxml')

    # 获得key，没有找到key就跳过
    try:
        key_source = soup.find(id='firstHeading')
        key = key_source.get_text()
    except AttributeError:
        print('no key, skipping')
        continue

    #处理重定向
    redirect = soup.find('span', 'mw-redirectedfrom')
    if redirect is not None :
        redirect_str = redirect.find('a')['title']
        redirects[redirect_str] = key

    #如果此词条已经处理过就仅仅提取重定向
    if key in keys:
        print('already exist, skipping')
        continue

    # 把key加入keys列表里，以后再次遇到此key就跳过
    keys.append(key)
    print(key)
    print('####################')

    # 获取内容
    mw_content = soup.find(id='mw-content-text')
    content = str(mw_content)

    # 寻找图片
    img_sources = soup.find_all('img')
    for img in img_sources:
        try:
            if not img['src'] in imgs:
                imgs.append(img['src'])
        except KeyError:
            pass

    # 以下替换链接为key,替换图片源为本地,替换跳转
    links = mw_content.find_all(href=True, title=True)
    for link in links:
        # 替换链接为本地key
        content = content.replace('href="' + link['href'], 'href="' + 'entry://%s' % link['title'])
    # 替换图片upload为本地路径
    content = content.replace('src="%s/'% upload,'src="/')
    # 替换词条内跳转为mdict格式
    content = content.replace('href="#','href="entry://#')
    content = re.sub(r'<span class="mw-headline" id=(.*)</span>', rep_method, content)
    # 替换图片格式为jpg
    content = content.replace('.png','.jpg').replace('.gif','.jpg').replace('.jpeg','.jpg')
    # unquote一下内容，使图片文件名缩短
    content = urllib.parse.unquote(content)

    # 如果链接不在列表里面就加入列表中
    all_links_source = soup.find_all(href=True, title=True)
    for link in all_links_source:
        # 筛选 url 去掉以url_except开头的。
        if_del = False
        for s in url_except:
            if link['href'].startswith(s):
                if_del = True
                break
        if if_del:
            continue

        if '页面不存在' in link['title']:
            continue

        full_link = site + re.sub('#.*$','',link['href'])
        if full_link not in urls_known:
            all_urls.append(full_link)
            urls_known.append(full_link)

    # 把key和内容写入Achievement.txt中
    achieve_file.write(key + '\n' + content + '\n</>\n')
    num += 1

    # Test
    #if num == 40:
    #    break

with open('imgs.py', 'w') as i:
    i.write('imgs=' + str(imgs))

# 处理重定向
nums = 1
redirects_keys = redirects.keys()
redirects_keys_len = len(redirects_keys)
for key in redirects_keys:
    content = key + '\n@@@LINK=' + redirects[key]
    print('处理重定向:\n%s : %s'%(nums, content))
    if not nums == redirects_keys_len:
        content += '\n</>\n'
    achieve_file.write(content)
    nums += 1

#关闭文件流
achieve_file.close()

###### 开始图片下载/处理 ######

num = 0
start_time = time.time()

for img in imgs:

    # 一堆调试信息
    print('now_unquoted :', urllib.parse.unquote(img))
    print('num          :', num)
    if num>1:
        average_time = (time.time() - start_time) / num
        print('average_time :', average_time)
        print('images_left  :', len(imgs)-num)
        seconds_left = (len(imgs)-num) * average_time
        hours_left = int(seconds_left // 3600)
        minutes_left = int(seconds_left % 3600 // 60)
        print('time_left    :','%s:%s'% (hours_left, minutes_left))
    print('####################')

    #链接的全路径
    if img.startswith('http'):
        full_img_network_path = img
    elif img.startswith('//'):
        full_img_network_path = 'https:' + img
    else:
        full_img_network_path = 'https://' + img

    # 超时或者404,403等就放弃
    try:
        img_requests = requests.get(full_img_network_path, timeout=60)
        if not img_requests.ok:
            continue
    except TimeoutError:
        continue
    except :
        print('Unexpected error:',sys.exc_info()[0])
        continue

    # 打开图片，并且处理图片为RGB模式，省空间
    # 不清楚为什么这里也会出错，不过姑且先加一个try吧
    try:
        img_object = Image.open(io.BytesIO(img_requests.content))
        img_RGB = img_object.convert('RGB')
    except:
        print(sys.exc_info()[0])
        continue

    # 处理文件路径
    img_rear_path = img.replace(upload,'upload').replace('.png','.jpg').replace('.gif','.jpg').replace('.jpeg','.jpg')
    # 处理图片路径，确保不会太长
    img_rear_path = urllib.parse.unquote(img_rear_path)
    img_path = os.path.join(os.path.abspath('.'),img_rear_path)
    img_dir , img_name = os.path.split(img_path)
    if not os.path.exists(img_dir):
        try:
            os.makedirs(img_dir)
        except OSError:
            print('文件名太长，跳过')
            continue

    # 以一定的质量保存图片，默认50以节省空间
    # 似乎总是喜欢出点错,干脆一个try解决 (/////)
    try:
        img_RGB.save(img_path, quality=image_quality)
    except:
        print(sys.exc_info()[0])
        continue
    num += 1