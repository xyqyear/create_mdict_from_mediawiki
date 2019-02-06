# 从mediawiki创建mdict

### 代码再次重写，尝试保存数据到leveldb.

## 依赖库:
	
	bs4
	PIL(pip install pillow)
	requests
	leveldb

如果windows不能使用pip安装leveldb的可以尝试使用[这个](https://github.com/happynear/py-leveldb-windows/)\
!!!!注意，用上面的预编译文件在windows上运行过后


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

修改以下两行来匹配为其他mediawiki\
upload是这个wiki的图片域名

	site = 'https://***.***'
    upload = 'upload.***.***'

site就是此wiki的域名，前面要加上http或者https\
修改以下一行更改api地址
    
    api_address = 'https://***.***/api.php'

如果已经完成一次爬取，下一次可以使用更新模式

    is_update_mode = False # or True

修改以下两行来决定是否使用代理以及添加代理框架的API\
代理框架是使用的[这个](https://github.com/jhao104/proxy_pool)\
可能需要小小配置一下。

    is_use_proxy = True
    proxy_pool = '192.168.10.125:23333'


本人不对使用此脚本的人用爬取下来的数据用作其他用途负任何责任

### TODO

- [x] 重写AllPagesGetter
- [x] 使用leveldb替换sqlite
- [x] 添加使用API爬取的支持
- [x] 支持仅更新，这样就不用每次都重新爬
- [ ] 使用XPath而不是Beautiful soup