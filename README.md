# 从mediawiki创建mdict

### 代码重写，尝试保存数据到sqlite文件.

## 依赖库:
	
	bs4
	PIL(pillow)
	requests

## 简介

本意是想从[thwiki](http://thwiki.cc)抓取数据放到kindle里看的\
但是弄着弄着发现好像所有mediawiki的数据结构都差不多\
于是就弄出这么个东西了

获取所有页面是通过 site/Special:Allpages 这个页面来获得的，但是不保证所有mediawiki站点都支持此页面

### wiki_mdict.py

主文件

修改以下一行来匹配为其他mediawiki

	site = 'https://thwiki.cc'

修改以下两行来决定是否使用代理以及添加代理框架的API

    use_proxy = True
    proxy_pool = '192.168.10.125:23333'
	
site就是此wiki的域名，前面要加上http或者https



本人不对使用此脚本的人用爬取下来的数据用作其他用途负任何责任