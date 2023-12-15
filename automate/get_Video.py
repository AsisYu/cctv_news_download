import re
import os
import sys
import requests
import datetime
import logging
import subprocess
import calendar


tmp_dir = 'tmp'
file_path = 'tmp/get_link'
file_name = "tmp/video_content"
file_text = "需手动获取的日期.txt"
file_or_dir_names = ['date', 'get_link']

#日期
def get_all_days(year_value, moon_value):
    year_value = int(year_value)
    moon_value = int(moon_value)
    # 获取指定月份的天数
    num_days = calendar.monthrange(year_value, moon_value)[1]
    # 存储每一天的日期
    dates = []
    # 遍历每一天，将其存储在列表中
    for day in range(1, num_days + 1):
        dates.append((year_value, moon_value, day))
    return dates

#获取date文件并创建
def create_folders(parent_dir, nested_dir ,out_file_path):
    # 调用函数获取全部天数的日期
    global day_str
    all_dates = get_all_days(year_value, moon_value)
    for date in all_dates:
        day_str  = str(date[2]).zfill(2)

        # 拼接完整的父文件夹路径
        parent_dir_path = os.path.join(parent_dir)

        # 检查父文件夹是否存在
        if not os.path.exists(parent_dir_path):
            # 创建父文件夹
            os.mkdir(parent_dir_path)

        # 拼接完整的子文件夹路径
        nested_dir_path = os.path.join(parent_dir_path, nested_dir)

        # 检查子文件夹是否存在
        if not os.path.exists(nested_dir_path):
            # 创建子文件夹
            os.mkdir(nested_dir_path)

        # 拼接完整的子子文件夹路径
        nested_dir_path2 = os.path.join(parent_dir_path, nested_dir, day_str)

        # 检查子文件夹的子文件夹是否存在
        if not os.path.exists(nested_dir_path2):
            # 创建子文件夹的子文件夹
            os.mkdir(nested_dir_path2)

        #构建路径
        video_file_path = out_file_path+"/dvideo"
        # 检查暂存视频文件夹是否存在
        if not os.path.exists(video_file_path):
            # 创建子文件夹的子文件夹
            os.mkdir(video_file_path)


#过滤地址
def get_video_link(out_file_path):
    global link
    url = right_part

    # 发起 GET 请求获取链接内容
    response = requests.get(url)

    file_path = os.path.join(os.getcwd(), file_name)

    # 将链接内容保存到文件中
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(response.text)

    print(f"链接内容已保存到 {file_path}")

    # 读取文件的内容
    with open("tmp/video_content", "r", encoding="utf-8") as file:
        content = file.read()

    # 使用正则表达式筛选出包含视频链接的内容
    pattern = r"https://[^\"\'\s]+"
    video_links = re.findall(pattern, content)

    out_file_path = out_file_path+"/video-link"

    for link in video_links:
        with open(out_file_path, "a", encoding="utf-8") as file:
            file.write(link+"\n")


#下载
# 封装下载链接的函数
def download_link(link, folder_path):
    filename = os.path.basename(link)
    response = requests.get(link)
    file_path = os.path.join(folder_path, filename)
    with open(file_path, "wb") as file:
        file.write(response.content)

def download_video(out_file_path):
    read_file_path = out_file_path+"/video-link"
    outvideo_file_path = out_file_path+"/dvideo"
    try:
        filtered_links = []

        # 从文件中读取链接，并筛选特定链接
        with open(read_file_path, "r", encoding="utf-8") as file:
            for line in file:
                if "aac16" in line and "h2642000000nero" in line:
                    filtered_links.append(line.strip())

        # 下载链接文件中的文件并保存到今天日期的文件夹中
        for link in filtered_links:
            download_link(link, outvideo_file_path)

        print("文件已下载至对应日期的文件夹中，即将进行视频合并，中途请勿退出...")
        return
    except Exception as e:
        print("代码执行出现错误")



#写入需要的日期
def errodate_write():
    with open(file_text, 'a') as file:
        file.write(get_date+"需手动下载"+'\n')

#检查
def check_files_exist(tmp_dir, file_or_dir_names):
    # 遍历列表中的每个文件名或目录名进行检查
    for name in file_or_dir_names:
        # 拼接完整的路径
        full_path = os.path.join(tmp_dir, name)

        # 判断路径是否存在
        if not os.path.exists(full_path):
            print(f"错误: '{full_path}' 不存在，请先执行main.py.")
            sys.exit(1)  # 终止程序执行

    # 如果文件或目录都存在，打印确认信息，并执行后续代码
    print("所需的文件或目录都存在，继续执行...")


if __name__ == "__main__":
    check_files_exist(tmp_dir, file_or_dir_names)
    # 使用 with 语句安全地打开文件
    with open(file_path, 'r') as file:
        # 遍历文件的每一行
        for line in file:
            # 消除每行末尾的换行符和额外空白
            line = line.strip()
            # 寻找第一个冒号，并分割字符串
            parts = line.split(':', 1)
            if len(parts) == 2:
                # 左半部分
                left_part = parts[0]
                # 右半部分
                right_part = parts[1]

                get_date = left_part

                print(get_date)

                # 拆分日期字符串
                year, month, day = get_date.split("-")

                # 构建文件路径
                out_file_path = os.path.join(year, month, day)

                text = f"{get_date}获取失败，内容为空,请手动获取"
                text2 = f"{get_date}判断为非新闻联播，请手动获取"

                # 指定链接地址
                url = right_part

                try:
                    # 发送GET请求
                    response = requests.get(url)

                    # 检查响应状态
                    if response.status_code == 200:
                        # 获取页面内容
                        body = response.text

                        # 搜索特定标记 "tag":" 并判断其后是否为 "新闻"
                        marker = 'tag":"'
                        start_index = body.find(marker)
                        if start_index != -1:
                            # 提取标记之后的两个字符
                            tag_value = body[start_index + len(marker): start_index + len(marker) + 2]
                            if tag_value == '新闻':
                                print('无问题开始获取地址...')

                                with open("tmp/date", 'r') as file:
                                    content2 = file.read()  # 读取文件内容
                                    # 判断分隔符 "-" 是否存在，并找到其索引位置
                                    if '-' in content2:
                                        separator_index = content2.index('-')
                                        year_value = content2[:separator_index].strip()
                                        moon_value = content2[separator_index + 1:].strip()
                                    else:
                                        print("date文件内容不符合预期的格式")
                                parent_dir =  year_value # 父文件夹名称
                                nested_dir = moon_value  # 子文件夹名称
                                #创建文件夹方便保存视频
                                create_folders(parent_dir, nested_dir, out_file_path)
                                #过滤
                                get_video_link(out_file_path)
                                print("正在进行视频下载...")
                                #下载
                                download_video(out_file_path)
                            else:
                                print(text2)
                                errodate_write()
                                # 询问用户是否继续
                                user_input = input("是否要继续？(y/n): ").strip().lower()
                                if user_input == 'n':
                                    print("用户选择退出循环。")
                                    break  # 用户选择退出循环
                                elif user_input == 'y':
                                    continue  # 用户选择继续循环，可以省略不写
                                else:
                                    print("无效输入，已自动选择继续。")
                        else:
                            print(text)
                            errodate_write()
                            # 询问用户是否继续
                            user_input = input("是否要继续？(y/n): ").strip().lower()
                            if user_input == 'n':
                                print("用户选择退出循环。")
                                break  # 用户选择退出循环
                            elif user_input == 'y':
                                continue  # 用户选择继续循环，可以省略不写
                            else:
                                print("无效输入，已自动选择继续。")
                    else:
                        print('请求失败，状态码:', response.status_code)
                except requests.RequestException as e:
                    print('请求发生错误:', e)
