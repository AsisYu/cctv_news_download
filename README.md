
# # 已失效

# # 功能介绍
通过py获取getHttpVideoInfo.do?pid=3...文件内的视频链接地址进行下载原视频，~~但是未实现视频合并功能~~（已实现），自动化下载合并视频已完成（仅限Edge浏览器）

------------

------------


#  如何使用？
安装python
安装一下必须的第三方插件


```shell
pip install requests

```
用于发送 HTTP 请求，并下载文件内容


```shell
pip install moviepy

```
用于视频处理和编辑


然后打开[cctv新闻联播官网](https://tv.cctv.com/lm/xwlb/?spm=C94212.P4YnMod9m2uD.EfOoEZcMXuiv.1 "cctv新闻联播官网")
![image](https://github.com/mcmtYu/cctv_news_download/assets/68932312/6428796a-3dc7-46b9-a222-01eb89bda9f3)


f12打开控制台，找到：
网络-Fetch/XHR，重新刷新一遍加载内容
找到以getHttpVideoInfo.do?pid=3...文件开头的文件
![image](https://github.com/mcmtYu/cctv_news_download/assets/68932312/06721f53-2005-4637-bea5-86fe3df17c72)


把该文件的链接复制下来，下载mian、search、merge三个py文件后放在同一目录，调出cmd，运行main.py粘贴链接地址等着就行了（linux同理）

![I((`H0EGEQ OZL9KWHB)Z}U](https://github.com/AsisYu/cctv_news_download/assets/68932312/51e376a2-16ef-498e-9ec9-30cb3e604498)


合并后的视频保存在根目录，merged.mp4

结束

------------

提一嘴，下载视频速度取决于设备网速，合并视频速度取决cpu
![image](https://github.com/mcmtYu/cctv_news_download/assets/68932312/f7f10ccd-50ee-4854-ba0f-e246e2a3a9d5)


#  automate文件夹里的自动化py仅限Edge浏览器，没有就安装或者别往下看了

安装python
安装一下必须的第三方插件(缺啥装啥，自行掂量)

hashlib：
```shell
pip install hashlib

```

selenium：
```shell
pip install selenium

```

bs4 (beautifulsoup4)：
```shell
pip install beautifulsoup4

```

re (正则表达式模块)：
```shell
pip install regex

```

requests (HTTP请求库)：
```shell
pip install requests

```

glob (路径模式匹配库)：
```shell
pip install glob

```

shutil (文件操作库)：
```shell
pip install shutil

```

moviepy (视频编辑库)：
```shell
pip install moviepy

```
安装完成直接运行main.py然后输入你想下载的年份月份，自动下载整个月份的新闻联播（重播）
![1](https://github.com/AsisYu/cctv_news_download/assets/68932312/0a5964db-47ec-4377-b699-934bbccc59e2)

合并完成的文件会对应在该日的文件夹目录下
![2](https://github.com/AsisYu/cctv_news_download/assets/68932312/88a1273e-1e7d-4d92-8d30-e0a34ab72a48)
在下载的时候代码会自动分辨是不是新闻联播，不是的会停顿让你选择是否继续
![1](https://github.com/AsisYu/cctv_news_download/assets/68932312/624a542f-2029-4848-9254-f13390b011d1)

然后在根目录创建文件保存不是新闻联播的对应日期，请自行分辨手动下载
![2](https://github.com/AsisYu/cctv_news_download/assets/68932312/b3b80c7f-a3d1-4ee4-af08-d8067f8b315b)

