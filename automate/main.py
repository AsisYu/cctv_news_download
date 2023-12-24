from hashlib import md5
import os
import re
import sys
import time
import shutil
import subprocess
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.common.exceptions import TimeoutException
import calendar

text = "开始自动获取到getHttpVideoInfo.do?此过程不会进行下载合并!"
text2 = "获取结束!"

def delete_tmp():
    # 获取当前工作目录
    current_dir = os.getcwd()
    # 拼接要删除的目录路径
    tmp_dir = os.path.join(current_dir, 'tmp')
    # 判断目录是否存在
    if os.path.exists(tmp_dir):
        # 删除目录
        shutil.rmtree(tmp_dir)

def get_all_days(year, month):
    # 获取指定月份的天数
    num_days = calendar.monthrange(year, month)[1]
    # 存储每一天的日期
    dates = []
    # 遍历每一天，将其存储在列表中
    for day in range(1, num_days + 1):
        dates.append((year, month, day))
    return dates

def get_uid_and_vdnAdStaticCheck(url):
    """
    获取指定网页的cookie信息
    """
    # 使用Edge浏览器驱动，需下载对应版本的edgedriver并指定路径
    driver = webdriver.Edge()
    # 打开网页
    driver.get(url)
    # 设置最大重试次数
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            # 如果成功找到元素，则继续执行后续代码
            break
        except TimeoutException:
            # 如果超时，刷新页面
            driver.refresh()
            retry_count += 1
    # 获取当前页面的cookie信息
    document_cookie = driver.execute_script("return document.cookie")
    vdnAdStaticCheck = driver.execute_script("return vodh5player.VDN_AD_STATIC_CHECK")
    # 关闭浏览器
    driver.quit()
    # 使用正则表达式提取 Fingerprint 的值
    pattern = r'Fingerprint=(\w+);'
    match = re.search(pattern, document_cookie)
    if match:
        fingerprint_value = match.group(1)
        return {"uid":fingerprint_value,"vdnAdStaticCheck":vdnAdStaticCheck}
    else:
        raise ("未能从第一个视频网页的document.cookie里找到uid(fingerprint_value)")

def get_cctv_pids_and_links(url):
    """
    输出一个字典,分别为pid_list和link_list
    """
    # 创建EdgeDriver实例
    browser = webdriver.Edge()
    # 发送请求，获取页面内容
    browser.get(url)
    # 等待 class 为 "jvedio" 的 div 元素出现
    wait = WebDriverWait(browser, 20)
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'jvedio')))
            break  # 如果成功找到元素，则跳出循环
        except TimeoutException:
            attempts += 1
            browser.refresh()  # 刷新网页
            time.sleep(10)  # 等待10秒再进行下一次尝试
    html = browser.page_source
    # 解析页面内容，获取jvedio元素
    soup = BeautifulSoup(html, 'html.parser')
    jvedios = soup.find_all('div', class_='jvedio')
    # 关闭浏览器窗口
    browser.quit()
    pid_list = []
    link_list = []
    # 遍历jvedio元素
    for jvedio in jvedios:
        src = jvedio.find('img')['src']
        pid = os.path.splitext(src.split('/')[-1].split('-')[0])[0]
        if len(pid) == 32:
            pid_list.append(pid)
            link = jvedio.find('a')['lanmu1']
            link_list.append(link)
    return {"pid_list": pid_list, "link_list": link_list}

if __name__ == "__main__":
    delete_tmp()
    print(text)
    # 用户输入年份和月份
    year = int(input("请输入你想下载的年份："))
    month = int(input("请输入你想下载的月份："))
    # 使用 zfill() 方法补齐前导0，确保月份为两位数形式
    formatted_month = str(month).zfill(2)

    # 创建 tmp 文件夹
    os.makedirs('tmp', exist_ok=True)

    # 确定 get_link 的路径
    link_file = 'tmp/get_link'
    date_file = 'tmp/date'

    # 存储输入日期
    year_str = str(year)
    month_str = str(formatted_month)
    with open(date_file, 'a') as f:
        f.write(year_str+"-"+month_str+ '\n')

    # 调用函数获取全部天数的日期
    all_dates = get_all_days(year, month)
    # 遍历每一天的日期
    year_str = ""
    month_str = ""
    day_str = ""
    for date in all_dates:
        year_str = str(date[0])
        month_str = str(date[1]).zfill(2)
        day_str = str(date[2]).zfill(2)

        print(f"开始{year_str}-{month_str}-{day_str}的获取")

        url = f'https://search.cctv.com/search.php?qtext=%E6%96%B0%E9%97%BB%E8%81%94%E6%92%AD{year_str}{month_str}{day_str}&type=video'
        # 获得pids_and_links
        pids_and_links = get_cctv_pids_and_links(url)
        print(pids_and_links)
        # 获得uid_and_vdnAdStaticCheck
        if pids_and_links["link_list"] and len(pids_and_links["link_list"]) > 0:
            uid_and_vdnAdStaticCheck = get_uid_and_vdnAdStaticCheck(pids_and_links["link_list"][0])
            print(uid_and_vdnAdStaticCheck)
            for pid in pids_and_links["pid_list"]:
                timestamp = str(int(datetime.now().timestamp()))[:10]
                md5_p = md5(
                    (timestamp + "2049" + uid_and_vdnAdStaticCheck["vdnAdStaticCheck"] + uid_and_vdnAdStaticCheck[
                        "uid"]).encode('utf-8'))
                md5_p = md5_p.hexdigest().upper()
                video_link = "https://" + "vdn.apps.cntv.cn/api/getHttpVideoInfo.do?" + "pid=" + pid + \
                             "&client=flash&im=0&tsp=" + timestamp + \
                             "&vn=2049&vc=" + md5_p + "&uid=" + uid_and_vdnAdStaticCheck["uid"] + "&wlan="
                print(video_link)

                # 写入 video_link 到 get_link 文件
                with open(link_file, 'a') as f:
                    f.write(year_str + "-" + month_str + "-" + day_str + ":" + video_link + '\n')
                    break  # 只写入第一行内容
        else:
            print(text2)
            subprocess.run(["python", "get_Video.py"])
            sys.exit()
print(text2)
subprocess.run(["python", "get_Video.py"])
