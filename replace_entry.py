# -*- coding:utf-8 -*-

import re

def rep_method(got):
    return '<a class="mw-headline" id=' + got.group(1) + '</a>'

content = ''

with open('Achievement.txt','r') as c:
    content = c.read()

content = content.replace('href="#','href="entry://#')
content = re.sub(r'<span class="mw-headline" id=(.*)</span>',rep_method,content)

with open('Achievement_1.txt','w') as w:
    w.write(content)