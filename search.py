import os
import datetime
import subprocess
import logging
import requests

# 创建 log 文件夹
log_folder = "log"
os.makedirs(log_folder, exist_ok=True)

# 配置日志记录器
logging.basicConfig(filename=os.path.join(log_folder, "linklog.txt"),
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


# 封装下载链接的函数
def download_link(link, folder_path):
    filename = os.path.basename(link)
    response = requests.get(link)
    file_path = os.path.join(folder_path, filename)
    with open(file_path, "wb") as file:
        file.write(response.content)


try:
    filtered_links = []

    # 从文件中读取链接，并筛选特定链接
    with open("b.txt", "r", encoding="utf-8") as file:
        for line in file:
            if "aac16" in line and "h2642000000nero" in line:
                filtered_links.append(line.strip())

    # 将筛选后的链接写入日志文件
    for link in filtered_links:
        logging.info(link)

    # 创建今天日期的文件夹
    today = datetime.date.today().strftime("%Y-%m-%d")
    folder_path = os.path.join(os.getcwd(), today)
    os.makedirs(folder_path, exist_ok=True)

    # 下载链接文件中的文件并保存到今天日期的文件夹中
    for link in filtered_links:
        download_link(link, folder_path)

    print("链接已写入 linklog.txt 文件，文件已下载至今天日期的文件夹中，即将进行视频合并，中途请勿退出...")

    # 删除 a.txt 和 b.txt 文件
    os.remove("a.txt")
    os.remove("b.txt")

except Exception as e:
    logging.error("代码执行出现错误：{}".format(e))
    print("代码执行出现错误，请检查错误日志或手动重新启动代码")

    # 重新执行代码
    print("重新执行代码...")
    os.execv(__file__, os.sys.argv)
subprocess.run(["python", "merge.py"])