import re
import os
import subprocess
import requests
import datetime
import logging

# 创建 log 文件夹
log_folder = "log"
os.makedirs(log_folder, exist_ok=True)

# 配置日志记录器
log_path = os.path.join(log_folder, "log.txt")
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从控制台接收用户输入的链接地址
url = input("请输入链接地址：")

# 发起 GET 请求获取链接内容
response = requests.get(url)

# 确定保存文件的路径和文件名
file_name = "a.txt"
file_path = os.path.join(os.getcwd(), file_name)

# 将链接内容保存到文件中
with open(file_path, "w", encoding="utf-8") as file:
    file.write(response.text)

print(f"链接内容已保存到 {file_path}")

# 读取a.txt文件的内容
with open("a.txt", "r", encoding="utf-8") as file:
    content = file.read()

# 使用正则表达式筛选出包含视频链接的内容
pattern = r"https://[^\"\'\s]+"
video_links = re.findall(pattern, content)

# 将筛选出的视频链接写入到b.txt文件中
with open("b.txt", "w", encoding="utf-8") as file:
    for link in video_links:
        file.write(link + "\n")

print("视频链接已保存到 b.txt")

# 获取当前时间
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

logging.info(f"{now} - 链接内容已保存到 {file_path}")
logging.info(f"{now} - 视频链接已保存到 b.txt")

print(f"日志已保存到 {log_path}，即将运行search.py进行下载视频...")
print(f"下载视频中...中途请勿退出。")
subprocess.run(["python", "search.py"])
