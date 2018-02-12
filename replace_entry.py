# -*- coding:utf-8 -*-

import re
import urllib.parse

def rep_method(got):
    return '<a class="mw-headline" id=' + got.group(1) + '</a>'

content = ''
upload = 'https://static.mengniang.org'

with open('Achievement.txt','r',errors='ignore') as c:
    content = c.read()

print ('trans to entry...')
content = content.replace('href="#','href="entry://#')
print('trans upload src...')
content = content.replace('src="%s/'% upload,'src="/')
print('trans in page link...')
content = re.sub(r'<span class="mw-headline" id=(.*)</span>',rep_method,content)
# 替换图片格式为jpg
print('trans image ext')
content = content.replace('.png','.jpg').replace('.gif','.jpg').replace('.jpeg','.jpg')
# unquote一下内容，使图片文件名缩短
print('unquote')
content = urllib.parse.unquote(content)

with open('Achievement_1.txt','w',errors='ignore') as w:
    w.write(content)