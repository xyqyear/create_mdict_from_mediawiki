`Deprecated`\
`已废弃`

# 从mediawiki创建mdict

## 依赖库:
	
	bs4
	PIL(pip install pillow)
	requests
	leveldb

如果windows不能使用pip安装leveldb的可以尝试使用[这个](https://github.com/happynear/py-leveldb-windows/)\
!!!!注意，用上面的预编译文件在windows上运行过后生成的数据库文件不能在linux上使用,反之亦然\
貌似是那个leveldb的预编译文件使用的leveldb版本的问题

对新版本api适配完成,但是由于新版api弃用了些东西,导致更新检查无法正常运作\
所以就把更新检查相关代码去掉了\
以后忙完了会考虑尝试使用新的方法来进行更新检查

## 简介

本意是想从[thwiki](http://thwiki.cc)抓取数据放到kindle里看的\
但是弄着弄着发现好像所有mediawiki的数据结构都差不多\
于是就弄出这么个东西了

需要mediawiki支持api

### config.py

配置文件

请先关闭测试模式!(在最后一行)\
如下更改

    test_mode = False

修改以下一行来匹配为其他mediawiki\
site就是此wiki的域名，前面要加上http或者https(链接最后不需要再加 "\\" 符号)\
例:

	site = 'https://***.***'   # 正确
	site = 'https://***.***/'   # 错误

修改以下一行更改api地址
    
    api_address = 'https://***.***/api.php'

修改以下两行来决定是否使用代理以及添加代理框架的API\
代理框架是使用的[这个](https://github.com/jhao104/proxy_pool)\
可能需要小小配置一下。

    is_use_proxy = True
    proxy_pool = '192.168.10.125:23333'
    
最后生成的文件是Achievemen.txt,需要用MdxBuilder来转换成mdx字典文件\
那个转换程序的Source填Achievement.txt\
Target是mdx的保存位置\
Data是程序生成的Data目录,也就是保存图片的地方


本人不对使用此脚本的人用爬取下来的数据用作其他用途负任何责任

### TODO

- [x] 重写AllPagesGetter
- [x] 使用leveldb替换sqlite
- [x] 添加使用API爬取的支持
- [x] 支持仅更新，这样就不用每次都重新爬
- [x] 重写图片本地保存路径相关代码,mdxbuilder终于不报错啦