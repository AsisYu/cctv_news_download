import os
import requests
import re
from urllib.parse import quote
import logging
from datetime import datetime

def download_file(url, save_dir):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # 检查请求是否成功

    # 根据URL获取文件名
    filename = url.split('/')[-1]
    filename = quote(filename, safe='')

    # 构造保存路径
    save_path = os.path.join(save_dir, filename)

    # 下载文件
    with open(save_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file.write(chunk)

    logging.info(f"文件 '{filename}' 下载完成！保存路径：{save_path}")

    return save_path

def extract_https_links_from_content(content):
    links = re.findall(r'https://[^"\'\s]+', content)
    extracted_links = [link.strip() for link in links]

    return extracted_links

def save_links_to_file(links, save_path):
    with open(save_path, 'w', encoding='utf-8') as file:
        for link in links:
            file.write(link + '\n')

    logging.info(f"链接已保存到文件 '{save_path}'!")

def download_files(urls, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for url in urls:
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # 检查请求是否成功

            # 根据URL获取文件名
            filename = url.split('/')[-1]
            filename = quote(filename, safe='')

            # 获取文件扩展名
            extension = os.path.splitext(filename)[1].lower()

            # 仅下载视频文件（.mp4）
            if extension == '.mp4':
                # 构造保存路径
                save_path = os.path.join(save_dir, filename)

                # 下载文件
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)

                logging.info(f"文件 '{filename}' 下载完成！保存路径：{save_path}")
        except requests.exceptions.RequestException as e:
            logging.error(f"下载文件 '{url}' 失败：{e}")

def extract_links_from_file(file_path):
    links = []
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        links = re.findall(r'https?://[^\s<>"]+', content)
    return links

# 配置日志输出路径和文件名
log_path = "log.txt"
logging.basicConfig(filename=log_path, level=logging.INFO)

# 从控制台接收用户输入的 gethttp 链接
url = input("请输入要下载的文件的 URL：")

# gethttp文件保存目录
save_dir = "./"

# 保存提取的链接的文件路径
links_file_path = ".d"

# 下载文件
downloaded_file_path = download_file(url, save_dir)

# 读取文件内容
with open(downloaded_file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# 提取链接
extracted_links = extract_https_links_from_content(content)

# 保存链接到文件
save_links_to_file(extracted_links, links_file_path)

# 链接文件路径
links_file_path2 = links_file_path

# 获取当前日期
date_str = datetime.now().strftime("%Y-%m-%d")

# 创建文件夹路径
folder_path = os.path.join(os.getcwd(), date_str)

# 视频保存目录
save_dir = folder_path

# 从链接文件中提取视频链接列表
links = extract_links_from_file(links_file_path2)

# 下载视频文件
download_files(links, save_dir)

# 删除文件
if os.path.exists(links_file_path2):
    os.remove(links_file_path2)
    logging.info(f"文件 '{links_file_path2}' 删除成功！")
else:
    logging.error(f"文件 '{links_file_path2}' 不存在！")

if os.path.exists(downloaded_file_path):
    os.remove(downloaded_file_path)
    logging.info(f"文件 '{downloaded_file_path}' 删除成功！")
else:
    logging.error(f"文件 '{downloaded_file_path}' 不存在！")
