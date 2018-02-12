# -*- coding:utf-8 -*-

from PIL import Image
import io
import requests
import os
import time
import urllib.parse
import sys

from imgs import imgs_list

upload = '//upload.thwiki.cc'
quality = 50
start_time = time.time()
starts_from = int(input('starts from?: '))
num = starts_from

for img in imgs_list[starts_from:]:
    print('now_unquoted :', urllib.parse.unquote(img))
    print('num          :', num)
    if num>1:
        average_time = (time.time() - start_time) / num
        print('average_time :', average_time)
        print('images_left  :', len(imgs_list)-num)
        seconds_left = (len(imgs_list)-num) * average_time
        hours_left = int(seconds_left // 3600)
        minutes_left = int(seconds_left % 3600 // 60)
        print('time_left    :','%s:%s'% (hours_left, minutes_left))
    print('####################')

    # 如果图片不是upload就跳过
    if not img.startswith(upload):
        print('跳过，以为不是此wiki upload图片')
        continue
    # 处理文件路径
    img_rear_path = img.replace('.png', '.jpg').replace('.gif', '.jpg').replace('.jpeg', '.jpg')
    if upload is not '':
        img_rear_path = img_rear_path.replace(upload, 'upload')
    img_rear_path = urllib.parse.unquote(img_rear_path)
    img_path = os.path.join(os.path.abspath('.'),img_rear_path)
    if os.path.exists(img_path):
        print('文件已存在，跳过')
        continue
    img_dir , img_name = os.path.split(img_path)
    # 创建文件夹
    if not os.path.exists(img_dir):
        try:
            os.makedirs(img_dir)
        except OSError:
            print('创建文件夹有点问题，跳过')
            continue

    # 链接的全路径
    if img.startswith('http'):
        full_img_network_path = img
    elif img.startswith('//'):
        full_img_network_path = 'https:' + img
    else:
        full_img_network_path = 'https://' + img

    # 超时或者404,403等就放弃
    try:
        img_requests = requests.get(full_img_network_path,timeout=60)
        if not img_requests.ok:
            continue
    except TimeoutError:
        continue
    except :
        print('Unexpected error:',sys.exc_info()[0])
        continue

    # 不清楚为什么这里也会出错，不过姑且先加一个try吧
    try:
        img_object = Image.open(io.BytesIO(img_requests.content))
        img_RGB = img_object.convert('RGB')
    except:
        print(sys.exc_info()[0])
        continue

    # 似乎总是喜欢出点错,干脆一个try解决 (/////)
    try:
        img_RGB.save(img_path,quality = quality)
    except:
        print(sys.exc_info()[0])
        continue

    num += 1




