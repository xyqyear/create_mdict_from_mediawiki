# 从mediawiki创建mdict

## 依赖库:
	
	bs4
	PIL(pillow)
	requests

## 简介

本意是想从thwiki抓取数据放到kindle里看的
但是弄着弄着发现好像所有mediawiki的数据结构都差不多
于是就弄出这么个东西了

### create_mdict_from_mediawiki.py

主文件

修改以下两行来匹配为其他mediawiki

	site = 'https://thwiki.cc'
	upload = '//upload.thwiki.cc'
	
site就是此wiki的域名，前面要加上http
upload是此wiki的upload域名。加不加http取决于此wiki里图片标签的src后的内容是什么


本人不对使用此脚本的人用爬取下来的数据用作其他用途负任何责任