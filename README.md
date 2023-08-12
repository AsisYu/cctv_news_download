
通过py获取getHttpVideoInfo.do?pid=3...文件内的视频链接地址进行下载原视频，但是未实现视频合并功能
![(M$)YZNQIGPXF$E6X~@U0)4](https://github.com/mcmtYu/cctv_news_download2/assets/68932312/b107a058-8c40-40fb-bd80-45b01877a074)
# 如何使用？
首先打开cctv新闻联播官网
![image](https://github.com/mcmtYu/cctv_news_download2/assets/68932312/ad157c6a-101c-4f6d-9758-7cd08e188548)

f12打开控制台，找到：
网络-Fetch/XHR，重新刷新一遍加载内容
找到以getHttpVideoInfo.do?pid=3...文件开头的文件
![image](https://github.com/mcmtYu/cctv_news_download2/assets/68932312/7d38702e-aaea-494e-a8da-c9662b979d54)

把该文件的链接复制下来，再到PyCharm运行cctv.py文件粘贴链接开始下载
![image](https://github.com/mcmtYu/cctv_news_download2/assets/68932312/d0ad69d3-1147-48d2-822f-038621d86bc3)

下载的视频保存在cctv.py目录的日期文件夹里。
结束

ps：新手上路，多多包涵

![(M$)YZNQIGPXF$E6X~@U0)4](https://github.com/mcmtYu/cctv_news_download2/assets/68932312/b107a058-8c40-40fb-bd80-45b01877a074)
