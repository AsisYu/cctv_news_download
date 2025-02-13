import os
import requests
from urllib.parse import urljoin

def get_video_info():
    # API URL
    url = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do"
    
    # Query parameters
    params = {
        "pid": "15d96a5fbbe74bc0b460c9bacd17e16d",
        "client": "flash",
        "im": "0",
        "tsp": "1739418409",
        "vn": "2049",
        "vc": "3DA016CE1AD6E2F91CCE0AC6EEA1C361",
        "uid": "811C1B443CCB5A45DD38E7281599F1F1",
        "wlan": ""
    }
    
    # Headers
    headers = {
        "authority": "vdn.apps.cntv.cn",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "origin": "https://tv.cctv.com",
        "referer": "https://tv.cctv.com/",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
    }
    
    try:
        # Send GET request
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        # Return JSON response
        data = response.json()
        print("API响应状态码:", response.status_code)
        print("\n视频信息详情:")
        print(f"标题: {data.get('title', '未知')}")
        print(f"描述: {data.get('description', '无')}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"获取视频信息时出错: {e}")
        return None

def download_m3u8(m3u8_url):
    try:
        print(f"\n开始下载M3U8文件...")
        print(f"下载地址: {m3u8_url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Referer": "https://tv.cctv.com/",
            "Origin": "https://tv.cctv.com"
        }
        
        response = requests.get(m3u8_url, headers=headers)
        response.raise_for_status()
        
        content_length = len(response.content)
        print(f"文件大小: {content_length/1024:.2f} KB")
        print(f"响应状态码: {response.status_code}")
        
        # Save the m3u8 file
        with open("video.m3u8", "wb") as f:
            f.write(response.content)
        print("M3U8文件下载成功，已保存为 video.m3u8")
        
        # 显示文件内容预览
        print("\nM3U8文件内容预览:")
        content = response.content.decode('utf-8')
        preview_lines = content.split('\n')[:5]
        for line in preview_lines:
            print(line)
        if len(content.split('\n')) > 5:
            print("...")
            
        return content
            
    except requests.exceptions.RequestException as e:
        print(f"下载m3u8文件时出错: {e}")
        if hasattr(e.response, 'status_code'):
            print(f"错误状态码: {e.response.status_code}")
        if hasattr(e.response, 'text'):
            print(f"错误响应: {e.response.text[:200]}")
        return None

def parse_m3u8_segments(base_url, m3u8_content):
    """解析M3U8文件内容，返回视频片段URL列表"""
    lines = m3u8_content.strip().split('\n')
    segments = []
    
    for line in lines:
        if not line.startswith('#') and line.strip():  # 不是注释且不是空行
            # 如果是相对路径，转换为完整URL
            if not line.startswith('http'):
                segment_url = urljoin(base_url, line.strip())
            else:
                segment_url = line.strip()
            segments.append(segment_url)
    
    return segments

def download_m3u8_segments(m3u8_url):
    try:
        print("\n开始解析M3U8文件...")
        
        # 读取主m3u8文件
        with open('video.m3u8', 'r') as f:
            content = f.read()
        
        # 获取基础URL和二级m3u8地址
        base_url = "https://hls.cntv.cdn20.com"
        segments = parse_m3u8_segments(base_url, content)
        
        if not segments:
            print("未找到二级M3U8地址")
            return
        
        # 下载二级m3u8文件
        second_m3u8_url = segments[0]
        print(f"\n下载二级M3U8文件: {second_m3u8_url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Referer": "https://tv.cctv.com/",
            "Origin": "https://tv.cctv.com"
        }
        
        response = requests.get(second_m3u8_url, headers=headers)
        response.raise_for_status()
        
        # 保存二级m3u8文件
        with open("video_2.m3u8", "wb") as f:
            f.write(response.content)
        
        # 解析二级m3u8获取真正的视频片段
        second_content = response.content.decode('utf-8')
        video_segments = []
        
        for line in second_content.split('\n'):
            if not line.startswith('#') and line.strip():
                if not line.startswith('http'):
                    # 从二级m3u8的URL中获取基础路径
                    base_path = '/'.join(second_m3u8_url.split('/')[:-1])
                    segment_url = f"{base_path}/{line.strip()}"
                else:
                    segment_url = line.strip()
                video_segments.append(segment_url)
        
        if not video_segments:
            print("未找到视频片段")
            return
        
        print(f"找到 {len(video_segments)} 个视频片段")
        
        # 创建保存目录
        if not os.path.exists('video_segments'):
            os.makedirs('video_segments')
        
        # 下载每个视频片段
        for i, segment_url in enumerate(video_segments, 1):
            try:
                print(f"\n下载片段 {i}/{len(video_segments)}")
                print(f"URL: {segment_url}")
                
                response = requests.get(segment_url, headers=headers)
                response.raise_for_status()
                
                # 保存片段
                segment_path = os.path.join('video_segments', f'segment_{i:03d}.ts')
                with open(segment_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"片段 {i} 下载完成: {len(response.content)/1024:.2f} KB")
                
            except requests.exceptions.RequestException as e:
                print(f"下载片段 {i} 时出错: {e}")
                continue
        
        print("\n所有片段下载完成！")
        
    except Exception as e:
        print(f"处理M3U8文件时出错: {e}")

if __name__ == "__main__":
    video_info = get_video_info()
    if video_info:
        print("\n正在解析视频地址...")
        try:
            # 尝试不同的可能的键名
            if 'hls_url' in video_info:
                m3u8_url = video_info['hls_url']
            elif 'video' in video_info and 'chapters' in video_info['video']:
                m3u8_url = video_info['video']['chapters'][0]['url']
            else:
                print("视频信息结构:")
                print(video_info)
                raise KeyError("未找到m3u8地址")
                
            download_m3u8(m3u8_url)
            # 下载视频片段
            download_m3u8_segments(m3u8_url)
            
        except KeyError as e:
            print(f"在视频信息中未找到m3u8地址: {e}")