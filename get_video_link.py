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
        if len(pid) == 32:
            pid_list.append(pid)
            link = jvedio.find('a')['lanmu1']
            link_list.append(link)
    return {"pid_list":pid_list,"link_list":link_list}

if __name__ == "__main__":
    url = 'https://search.cctv.com/search.php?qtext=%E6%B1%BD%E8%BD%A6&type=video'
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
