from hashlib import md5
import os
import re
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import random
import string
import calendar


def get_all_days(year, month):
    # 获取指定月份的天数
    num_days = calendar.monthrange(year, month)[1]

    # 存储每一天的日期
    dates = []

    # 遍历每一天，将其存储在列表中
    for day in range(1, num_days + 1):
        dates.append((year, month, day))

    return dates

def get_uid(url):
    """
    获取指定网页的cookie信息
    """
    # 使用Edge浏览器驱动，需下载对应版本的edgedriver并指定路径
    driver = webdriver.Edge()
    # 打开网页
    driver.get(url)
    # 等待网页加载完成
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    # 获取当前页面的cookie信息
    document_cookie = driver.execute_script("return document.cookie")
    # 关闭浏览器
    driver.quit()
    # 使用正则表达式提取 Fingerprint 的值
    pattern = r'Fingerprint=(\w+);'
    match = re.search(pattern, document_cookie)
    if match:
        fingerprint_value = match.group(1)
        return fingerprint_value
    else:
        raise("未能从第一个视频网页的document.cookie里找到uid(fingerprint_value)")

def get_cctv_pid_link(url):
    """
    输出一个字典,分别为pid_list和link_list
    """
    # 创建EdgeDriver实例
    browser = webdriver.Edge()
    # 发送请求，获取页面内容
    browser.get(url)
    # 等待 class 为 "jvedio" 的 div 元素出现
    wait = WebDriverWait(browser, 20)
    element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'jvedio')))
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
        if len(pid) > 31:
            pid_list.append(pid)
            link = jvedio.find('a')['lanmu1']
            link_list.append(link)
    return {"pid_list":pid_list,"link_list":link_list}

if __name__ == "__main__":
    # 用户输入年份和月份
    year = int(input("请输入你想下载的年份："))
    month = int(input("请输入你想下载的月份："))

    # 创建 tmp 文件夹
    os.makedirs('tmp', exist_ok=True)

    # 确定 get_link.txt 的路径
    link_file = 'tmp/get_link.txt'

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
        print("url="+url)
        pid_and_link = get_cctv_pid_link(url)
        print(pid_and_link)
        uid = get_uid(pid_and_link["link_list"][0])
        print("uid:"+uid)

        chars = string.ascii_uppercase + string.digits
        uid=''.join(random.choice(chars) for _ in range(32))
        for pid in pid_and_link["pid_list"]:
            timestamp = str(int(datetime.now().timestamp()))[:10]
            # 此处的47899B86370B879139C08E7A3B5E8826在网页源代码中为固定值,不知后续会不会变化
            md5_p = md5((timestamp + "2049" + "47899B86370B879139C08E7A3B5E8826" + uid).encode('utf-8')) #47899B86370B879139C08EA3B5E88267
            md5_p=md5_p.hexdigest().upper()
            video_link = "https://"+"vdn.apps.cntv.cn/api/getHttpVideoInfo.do?"+"pid=" +pid +"&client=flash&im=0&tsp="+timestamp+"&vn=2049&vc=" +md5_p+ "&uid=" + uid + "&wlan="
            print(video_link)
            # 写入 video_link 到 get_link.txt 文件
            with open(link_file, 'a') as f:
                f.write(year_str+"-"+month_str+"-"+day_str+":"+video_link + '\n')
                break   # 只写入第一行内容
