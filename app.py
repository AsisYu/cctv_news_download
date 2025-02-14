from flask import Flask, render_template, request, jsonify, send_file
import os
import uuid
import subprocess
from threading import Lock, Thread
import requests
from urllib.parse import urljoin
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import json
from datetime import datetime
from ts_merger import TSMerger
import time
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MERGED_FOLDER'] = 'merged'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB限制
MAX_WORKERS = 8  # 最大线程数
TASKS_FILE = 'tasks.json'
SEGMENT_TIMEOUT = 30  # 单个片段下载超时时间（秒）
RETRY_LIMIT = 3      # 重试次数限制

# 确保上传和合并目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MERGED_FOLDER'], exist_ok=True)

# 进度存储
progress_data = {}
progress_lock = Lock()

# 创建TSMerger实例
ts_merger = TSMerger(
    output_dir=app.config['MERGED_FOLDER']  # 只需要指定输出目录
)

# 配置日志
logging.basicConfig(
    level=logging.ERROR,  # 修改为ERROR级别
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 关闭Werkzeug的默认日志
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

# 修改Flask的日志级别
app.logger.setLevel(logging.ERROR)

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.load_tasks()

    def load_tasks(self):
        """从文件加载任务"""
        try:
            if os.path.exists(TASKS_FILE):
                with open(TASKS_FILE, 'r') as f:
                    saved_tasks = json.load(f)
                    for task_id, task in saved_tasks.items():
                        if task['status'] != '下载完成！' and not task.get('error'):
                            task['status'] = '任务已恢复'
                            task['progress'] = 0
                    self.tasks = saved_tasks
        except Exception as e:
            print(f"加载任务失败: {e}")
            self.tasks = {}

    def save_tasks(self):
        """保存任务到文件"""
        try:
            with open(TASKS_FILE, 'w') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务失败: {e}")

    def add_task(self, task_id, task_info):
        """添加新任务"""
        task_info['created_at'] = datetime.now().isoformat()
        task_info['start_time'] = time.time()  # 添加任务开始时间
        self.tasks[task_id] = task_info
        self.save_tasks()

    def update_task(self, task_id, updates):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].update(updates)
            self.save_tasks()

    def get_task(self, task_id):
        """获取任务信息"""
        return self.tasks.get(task_id)

    def get_all_tasks(self):
        """获取所有任务"""
        return self.tasks

    def clean_old_tasks(self, days=7):
        """清理旧任务"""
        now = datetime.now()
        old_tasks = []
        for task_id, task in self.tasks.items():
            created_at = datetime.fromisoformat(task['created_at'])
            if (now - created_at).days > days:
                old_tasks.append(task_id)
                
        for task_id in old_tasks:
            del self.tasks[task_id]
        
        if old_tasks:
            self.save_tasks()

    def delete_task(self, task_id):
        """删除任务及其相关文件"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            
            # 删除任务目录
            task_dir = task.get('task_dir')
            if task_dir and os.path.exists(task_dir):
                try:
                    import shutil
                    shutil.rmtree(task_dir)
                except Exception as e:
                    print(f"删除任务目录失败: {e}")

            # 删除输出文件
            output_file = task.get('output_file')
            if output_file and os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as e:
                    print(f"删除输出文件失败: {e}")

            # 从任务列表中移除
            del self.tasks[task_id]
            self.save_tasks()
            return True
        return False

# 创建任务管理器实例
task_manager = TaskManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
            
        files = request.files.getlist('files[]')
        if not files or not files[0].filename:
            return jsonify({'error': '没有选择文件'}), 400

        # 创建任务ID
        task_id = str(uuid.uuid4())
        task_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
        os.makedirs(task_dir, exist_ok=True)

        # 保存文件
        file_paths = []
        for file in files:
            if file and file.filename.endswith('.ts'):
                filename = secure_filename(file.filename)
                file_path = os.path.join(task_dir, filename)
                file.save(file_path)
                file_paths.append(file_path)

        if not file_paths:
            return jsonify({'error': '没有有效的TS文件'}), 400

        # 创建合并任务
        task = {
            'id': task_id,
            'status': '准备合并',
            'progress': 0,
            'file_paths': file_paths,
            'created_at': datetime.now().isoformat(),
            'output_file': os.path.join(app.config['MERGED_FOLDER'], f'{task_id}.mp4')
        }
        
        # 保存任务信息
        task_manager.add_task(task_id, task)

        # 启动合并进程
        Thread(target=merge_ts_files, args=(task_id, file_paths, task['output_file'])).start()

        return jsonify({
            'task_id': task_id,
            'message': '文件上传成功，开始合并'
        })

    except Exception as e:
        logger.error(f"上传文件失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress/<task_id>')
def check_progress(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
        
    return jsonify({
        'status': task.get('status', '未知状态'),
        'progress': task.get('progress', 0),
        'error': task.get('error', False)
    })

def merge_ts_files(task_id, file_paths, output_file):
    try:
        task_manager.update_task(task_id, {'status': '开始合并', 'progress': 0})
        
        # 修改这里的调用方式
        output_file = ts_merger.merge_files(
            file_paths,  # 直接传递文件路径列表
            task_id     # 直接传递task_id
        )
        
        if output_file:  # 如果返回了输出文件路径
            task_manager.update_task(task_id, {
                'status': '合并完成！',
                'progress': 100,
                'output_file': output_file
            })
        else:
            raise Exception("合并失败")
                
    except Exception as e:
        logger.error(f"合并失败: {str(e)}")
        task_manager.update_task(task_id, {
            'status': f'合并失败: {str(e)}',
            'error': True,
            'progress': 0
        })

@app.route('/download/<task_id>')
def download_file(task_id):
    task = task_manager.get_task(task_id)  # 使用task_manager获取任务信息
    if not task or 'output_file' not in task:
        return '文件不存在', 404
    
    output_file = task['output_file']
    if not os.path.exists(output_file):
        return '视频文件不存在', 404
    
    # 获取文件名
    filename = os.path.basename(output_file)
    
    return send_file(
        output_file,
        as_attachment=True,
        download_name=f'{task.get("title", "video")}.mp4'  # 使用任务标题作为文件名
    )

@app.route('/video/download', methods=['POST'])
def video_download():
    try:
        data = request.get_json()
        pid = data.get('pid')
        if not pid:
            return jsonify({'error': 'PID不能为空'}), 400

        # 创建任务ID和目录
        task_id = str(uuid.uuid4())
        task_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
        os.makedirs(task_dir)

        # 初始化任务信息
        task_info = {
            'pid': pid,
            'progress': 0,
            'status': '正在解析视频地址...',
            'total_segments': 0,
            'task_dir': task_dir
        }

        # 添加到任务管理器
        task_manager.add_task(task_id, task_info)

        # 启动下载线程
        Thread(target=process_video_download, args=(task_id, pid, task_dir)).start()

        return jsonify({
            'task_id': task_id,
            'message': '开始下载视频'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_video_info(pid):
    url = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do"
    params = {
        "pid": pid,
        "client": "flash",
        "im": "0",
        "tsp": "1739418409",
        "vn": "2049",
        "vc": "3DA016CE1AD6E2F91CCE0AC6EEA1C361",
        "uid": "811C1B443CCB5A45DD38E7281599F1F1",
        "wlan": ""
    }
    
    headers = {
        "authority": "vdn.apps.cntv.cn",
        "accept": "*/*",
        "origin": "https://tv.cctv.com",
        "referer": "https://tv.cctv.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取视频信息时出错: {e}")
        return None

def download_segment(args):
    """下载单个视频片段的函数"""
    segment_url, segment_path, headers = args
    retry_count = 0
    start_time = time.time()
    
    while retry_count < RETRY_LIMIT:
        try:
            response = requests.get(
                segment_url, 
                headers=headers, 
                timeout=SEGMENT_TIMEOUT
            )
            response.raise_for_status()
            
            with open(segment_path, 'wb') as f:
                f.write(response.content)
            
            duration = int((time.time() - start_time) * 1000)  # 转换为毫秒
            return {
                'success': True,
                'duration': duration
            }
            
        except requests.Timeout:
            retry_count += 1
            if retry_count >= RETRY_LIMIT:
                return {
                    'success': False, 
                    'error': 'timeout',
                    'message': f'下载超时 ({SEGMENT_TIMEOUT}秒)'
                }
            continue
            
        except Exception as e:
            return {
                'success': False,
                'error': 'error',
                'message': str(e)
            }

def process_video_download(task_id, pid, task_dir):
    try:
        logger.info(f"开始下载任务 {task_id}")
        # 获取视频信息
        video_info = get_video_info(pid)
        if not video_info:
            raise Exception("获取视频信息失败")

        # 更新任务信息
        task_manager.update_task(task_id, {
            'title': video_info.get('title', '未知标题'),
            'status': f'获取到视频: {video_info.get("title", "未知标题")}',
            'progress': 5
        })

        # 从返回的JSON中获取m3u8地址
        m3u8_url = video_info.get('hls_url')
        if not m3u8_url:
            raise Exception("未找到视频地址")

        task_manager.update_task(task_id, {
            'm3u8_url': m3u8_url  # 保存m3u8地址
        })

        # 下载主M3U8文件
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://tv.cctv.com/",
            "Origin": "https://tv.cctv.com"
        }

        response = requests.get(m3u8_url, headers=headers)
        response.raise_for_status()
        
        m3u8_path = os.path.join(task_dir, "video.m3u8")
        with open(m3u8_path, "wb") as f:
            f.write(response.content)

        # 更新状态
        task_manager.update_task(task_id, {
            'status': '解析M3U8文件...',
            'progress': 10
        })

        # 解析M3U8获取片段
        content = response.content.decode('utf-8')
        base_url = os.path.dirname(m3u8_url)
        segments = parse_m3u8_segments(base_url, content)

        if not segments:
            raise Exception("未找到视频片段")

        # 下载二级M3U8
        second_m3u8_url = segments[0]
        response = requests.get(second_m3u8_url, headers=headers)
        response.raise_for_status()

        # 保存二级M3U8
        second_m3u8_path = os.path.join(task_dir, "video_2.m3u8")
        with open(second_m3u8_path, "wb") as f:
            f.write(response.content)

        # 解析二级M3U8获取视频片段
        second_content = response.content.decode('utf-8')
        video_segments = []
        base_path = os.path.dirname(second_m3u8_url)

        for line in second_content.split('\n'):
            if not line.startswith('#') and line.strip():
                if not line.startswith('http'):
                    segment_url = f"{base_path}/{line.strip()}"
                else:
                    segment_url = line.strip()
                video_segments.append(segment_url)

        total_segments = len(video_segments)
        task_manager.update_task(task_id, {
            'total_segments': total_segments,
            'status': f'找到 {total_segments} 个视频片段',
            'progress': 15
        })

        # 创建片段目录
        segments_dir = os.path.join(task_dir, 'segments')
        os.makedirs(segments_dir, exist_ok=True)

        # 准备下载任务
        download_tasks = []
        segments_info = {}  # 初始化片段信息
        
        # 提前创建所有片段的信息
        for i, segment_url in enumerate(video_segments, 1):
            segment_path = os.path.join(segments_dir, f'segment_{i:03d}.ts')
            download_tasks.append((segment_url, segment_path, headers))
            segments_info[str(i)] = {
                'status': 'waiting',
                'size': 0,
                'duration': None,
                'start_time': None
            }
        
        # 保存初始片段信息
        task_manager.update_task(task_id, {
            'segments_info': segments_info
        })

        # 使用计数器跟踪进度
        completed_count = 0
        download_lock = threading.Lock()

        # 更新任务进度的函数
        def update_progress(segment_number, status='downloading', duration=None, size=None):
            nonlocal completed_count
            with download_lock:
                if status == 'completed':
                    completed_count += 1
                
                # 计算实际进度
                progress = int((completed_count / total_segments) * 100)
                
                segments_info[str(segment_number)].update({
                    'status': status,
                    'duration': duration,
                    'size': size,
                    'completed_at': time.time() if status == 'completed' else None
                })
                
                task_manager.update_task(task_id, {
                    'progress': progress,
                    'status': f'下载片段 {completed_count}/{total_segments}',
                    'segments_info': segments_info,
                    'total_segments': total_segments,
                    'completed_segments': completed_count
                })
        
        # 下载片段
        failed_segments = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_url = {}
            for i, task in enumerate(download_tasks, 1):
                segments_info[str(i)]['start_time'] = time.time()
                future = executor.submit(download_segment, task)
                future_to_url[future] = (i, task[0])

            for future in as_completed(future_to_url):
                segment_number, url = future_to_url[future]
                try:
                    result = future.result()
                    if result['success']:
                        update_progress(
                            segment_number,
                            status='completed',
                            duration=result.get('duration'),
                            size=os.path.getsize(download_tasks[segment_number-1][1])
                        )
                    else:
                        update_progress(segment_number, status='failed')
                        failed_segments.append({
                            'url': url,
                            'error': result.get('error'),
                            'message': result.get('message')
                        })
                except Exception as e:
                    update_progress(segment_number, status='failed')
                    failed_segments.append({
                        'url': url,
                        'error': 'error',
                        'message': str(e)
                    })

        # 保存片段信息
        task_manager.update_task(task_id, {
            'segments_info': segments_info
        })
        
        # 如果有失败的片段，更新任务状态并提供重试选项
        if failed_segments:
            task_manager.update_task(task_id, {
                'status': f'下载失败: {len(failed_segments)} 个片段下载失败',
                'error': True,
                'failed_segments': failed_segments,
                'can_retry': True
            })
            raise Exception(f"{len(failed_segments)} 个片段下载失败，请重试")

        # 检查是否所有片段都下载成功
        expected_files = {os.path.join(segments_dir, f'segment_{i:03d}.ts') 
                         for i in range(1, total_segments + 1)}
        actual_files = set(glob.glob(os.path.join(segments_dir, 'segment_*.ts')))
        missing_files = expected_files - actual_files

        if missing_files:
            raise Exception(f"有 {len(missing_files)} 个片段下载失败")

        # 下载完成后更新总耗时和状态
        task = task_manager.get_task(task_id)  # 获取当前任务对象
        if not task:
            raise Exception("任务不存在")
            
        end_time = time.time()
        total_duration = int((end_time - task.get('start_time', end_time)) * 1000)
        task_manager.update_task(task_id, {
            'total_duration': total_duration,
            'end_time': end_time,
            'status': '下载完成，准备合并...',
            'progress': 95
        })

        # 使用TSMerger合并视频片段
        try:
            # 获取所有片段文件
            segments_dir = os.path.join(task_dir, 'segments')
            segment_files = sorted(glob.glob(os.path.join(segments_dir, 'segment_*.ts')))
            
            if not segment_files:
                raise Exception("没有找到可合并的片段")

            # 更新状态
            task_manager.update_task(task_id, {
                'status': '正在合并视频片段...'
            })

            # 定义进度回调函数
            def update_merge_progress(output):
                if 'frame=' in output:
                    current_progress = task.get('merge_info', {}).get('progress', 10)
                    task_manager.update_task(task_id, {
                        'merge_info': {
                            'progress': min(95, current_progress + 1),
                            'status': '合并中...'
                        }
                    })

            # 使用TSMerger进行合并
            result = ts_merger.merge_files(
                segment_files,  # 直接传递文件路径列表
                task_id        # 直接传递task_id
            )

            if not result:  # 如果返回None或False
                raise Exception("合并失败")

            # 合并成功，更新任务状态
            task_manager.update_task(task_id, {
                'merge_info': {
                    'progress': 100,
                    'status': '合并完成'
                },
                'output_file': result,
                'status': '合并完成！'
            })

        except Exception as merge_error:
            raise Exception(f"合并失败: {str(merge_error)}")

        logger.info(f"下载完成，开始合并视频 {task_id}")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"任务 {task_id} 处理失败: {error_msg}")
        task_manager.update_task(task_id, {
            'status': f'错误: {error_msg}',
            'error': True,
            'can_retry': True
        })

def parse_m3u8_segments(base_url, m3u8_content):
    """解析M3U8文件内容，返回视频片段URL列表"""
    lines = m3u8_content.strip().split('\n')
    segments = []
    
    for line in lines:
        if not line.startswith('#') and line.strip():  # 不是注释且不是空行
            # 如果是相对路径，转换为完整URL
            if not line.startswith('http'):
                segment_url = urljoin(base_url + '/', line.strip())
            else:
                segment_url = line.strip()
            segments.append(segment_url)
    
    return segments

@app.route('/tasks')
def get_tasks():
    return jsonify(task_manager.get_all_tasks())

@app.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        task_manager.delete_task(task_id)
        logger.info(f"删除任务 {task_id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"删除任务 {task_id} 失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<task_id>/retry', methods=['POST'])
def retry_download(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    if not task.get('can_retry'):
        return jsonify({'error': '该任务无法重试'}), 400
    
    # 重置任务状态
    task_manager.update_task(task_id, {
        'progress': task.get('last_progress', 0),
        'status': '准备重新下载失败的片段...',
        'error': False,
        'can_retry': False
    })
    
    # 启动重试线程
    Thread(target=retry_failed_segments, args=(task_id, task)).start()
    
    return jsonify({'message': '开始重试下载'})

def retry_failed_segments(task_id, task):
    try:
        task_dir = task.get('task_dir')
        if not task_dir:
            raise Exception("任务目录不存在")
        
        segments_dir = os.path.join(task_dir, 'segments')
        if not os.path.exists(segments_dir):
            raise Exception("片段目录不存在")
        
        # 获取当前已下载的片段
        existing_segments = sorted(glob.glob(os.path.join(segments_dir, 'segment_*.ts')))
        if not existing_segments:
            raise Exception("没有找到已下载的片段")
        
        # 获取最后一个成功下载的片段序号
        last_segment = existing_segments[-1]
        last_number = int(last_segment.split('_')[-1].split('.')[0])
        
        # 从最后成功片段往后两个开始下载
        start_number = max(1, last_number - 2)
        
        # 准备重试任务
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://tv.cctv.com/",
            "Origin": "https://tv.cctv.com"
        }
        
        # 获取原始片段URL列表
        with open(os.path.join(task_dir, "video_2.m3u8"), 'r') as f:
            m3u8_content = f.read()
        
        video_segments = []
        base_path = os.path.dirname(task.get('m3u8_url', ''))
        for line in m3u8_content.split('\n'):
            if not line.startswith('#') and line.strip():
                if not line.startswith('http'):
                    segment_url = f"{base_path}/{line.strip()}"
                else:
                    segment_url = line.strip()
                video_segments.append(segment_url)
        
        # 准备下载任务（从start_number开始）
        download_tasks = []
        for i, segment_url in enumerate(video_segments[start_number-1:], start_number):
            segment_path = os.path.join(segments_dir, f'segment_{i:03d}.ts')
            download_tasks.append((segment_url, segment_path, headers))
        
        # 更新进度
        total_segments = len(download_tasks)
        completed_count = 0
        
        def update_retry_progress():
            nonlocal completed_count
            completed_count += 1
            progress = int((completed_count / total_segments) * 100)
            task_manager.update_task(task_id, {
                'progress': progress,
                'status': f'重试下载片段 {completed_count}/{total_segments} (从{start_number}号片段开始)'
            })
        
        # 执行重试下载
        new_failed_segments = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_url = {
                executor.submit(download_segment, task): task[0]
                for task in download_tasks
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result['success']:
                        update_retry_progress()
                    else:
                        new_failed_segments.append({
                            'url': url,
                            'error': result.get('error'),
                            'message': result.get('message')
                        })
                except Exception as e:
                    new_failed_segments.append({
                        'url': url,
                        'error': 'error',
                        'message': str(e)
                    })
        
        # 检查重试结果
        if new_failed_segments:
            task_manager.update_task(task_id, {
                'status': f'重试失败: 仍有 {len(new_failed_segments)} 个片段下载失败',
                'error': True,
                'failed_segments': new_failed_segments,
                'can_retry': True,
                'last_retry_number': start_number
            })
        else:
            # 重试成功，继续后续处理
            task_manager.update_task(task_id, {
                'status': '重试成功，准备合并视频...',
                'progress': 95
            })
            
            # 继续合并过程
            process_video_download(task_id, task.get('pid'), task_dir)
            
    except Exception as e:
        task_manager.update_task(task_id, {
            'status': f'重试出错: {str(e)}',
            'error': True
        })

@app.route('/tasks/<task_id>/detail')
def get_task_detail(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
        
    try:
        # 获取片段信息
        segments_dir = os.path.join(task.get('task_dir', ''), 'segments')
        segments = []
        total_size = 0
        
        if os.path.exists(segments_dir):
            for file in sorted(os.listdir(segments_dir)):
                if file.endswith('.ts'):
                    file_path = os.path.join(segments_dir, file)
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    total_size += file_size
                    
                    # 从任务记录中获取下载耗时
                    segment_number = int(file.split('_')[1].split('.')[0])
                    segment_info = task.get('segments_info', {}).get(str(segment_number), {})
                    
                    segments.append({
                        'status': 'completed' if file_size > 0 else 'failed',
                        'size': file_size,
                        'duration': segment_info.get('duration')  # 单个片段的下载耗时
                    })
        
        # 计算总耗时（从开始到现在，或到结束时间）
        start_time = task.get('start_time')
        end_time = task.get('end_time')
        
        if start_time:
            if end_time:
                total_duration = int(end_time - start_time)
            else:
                total_duration = int(time.time() - start_time)
        else:
            total_duration = 0
        
        # 如果有输出文件，使用输出文件的大小
        output_file = task.get('output_file')
        if output_file and os.path.exists(output_file):
            total_size = os.path.getsize(output_file)
        
        # 扩展任务信息
        task_detail = {
            **task,
            'segments': segments,
            'total_size': total_size,
            'total_duration': total_duration
        }
        
        return jsonify(task_detail)
        
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<task_id>/segments/<int:segment_number>/retry', methods=['POST'])
def retry_segment(task_id, segment_number):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    try:
        # 获取片段信息
        segments_info = task.get('segments_info', {})
        segment_info = segments_info.get(str(segment_number))
        if not segment_info:
            raise Exception("片段信息不存在")
        
        # 准备重试
        task_dir = task.get('task_dir')
        segments_dir = os.path.join(task_dir, 'segments')
        
        # 从m3u8文件获取片段URL
        with open(os.path.join(task_dir, "video_2.m3u8"), 'r') as f:
            m3u8_content = f.read()
        
        video_segments = []
        base_path = os.path.dirname(task.get('m3u8_url', ''))
        for line in m3u8_content.split('\n'):
            if not line.startswith('#') and line.strip():
                if not line.startswith('http'):
                    segment_url = f"{base_path}/{line.strip()}"
                else:
                    segment_url = line.strip()
                video_segments.append(segment_url)
        
        if segment_number > len(video_segments):
            raise Exception("片段序号超出范围")
        
        # 准备下载任务
        segment_url = video_segments[segment_number - 1]
        segment_path = os.path.join(segments_dir, f'segment_{segment_number:03d}.ts')
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://tv.cctv.com/",
            "Origin": "https://tv.cctv.com"
        }
        
        # 更新状态
        segments_info[str(segment_number)].update({
            'status': 'downloading',
            'start_time': time.time()
        })
        task_manager.update_task(task_id, {
            'segments_info': segments_info,
            'status': f'重试下载第 {segment_number} 个片段'
        })
        
        # 执行下载
        result = download_segment((segment_url, segment_path, headers))
        
        # 更新结果
        if result['success']:
            segments_info[str(segment_number)].update({
                'status': 'completed',
                'duration': result.get('duration'),
                'size': os.path.getsize(segment_path)
            })
            message = '重试成功'
        else:
            segments_info[str(segment_number)].update({
                'status': 'failed'
            })
            message = f"重试失败: {result.get('message')}"
        
        task_manager.update_task(task_id, {
            'segments_info': segments_info,
            'status': message
        })
        
        return jsonify({
            'success': result['success'],
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/tasks/<task_id>/merge', methods=['POST'])
def start_merge(task_id):
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({'error': '任务不存在'}), 404
        
        # 检查是否有失败的片段
        segments_info = task.get('segments_info', {})
        failed_segments = [num for num, info in segments_info.items() 
                         if info.get('status') == 'failed']
        
        if failed_segments:
            return jsonify({
                'error': f'有 {len(failed_segments)} 个片段下载失败，请先重试'
            }), 400
            
        # 获取所有文件路径
        task_dir = task.get('task_dir')
        segments_dir = os.path.join(task_dir, 'segments')
        
        if not os.path.exists(segments_dir):
            return jsonify({'error': '片段目录不存在'}), 400
        
        # 获取并排序片段文件，使用绝对路径
        segment_files = sorted(glob.glob(os.path.join(segments_dir, 'segment_*.ts')))
        if not segment_files:
            return jsonify({'error': '没有找到可合并的片段'}), 400
        
        # 验证所有文件是否存在
        for file_path in segment_files:
            if not os.path.exists(file_path):
                return jsonify({'error': f'片段文件不存在: {os.path.basename(file_path)}'}), 400
            
        # 开始合并
        output_file = ts_merger.merge_files(
            segment_files,  # 传递完整的文件路径列表
            task_id
        )
        
        if not output_file:
            return jsonify({'error': '合并失败'}), 500
        
        # 更新任务状态
        task['status'] = 'completed'
        task['output_file'] = output_file
        task_manager.save_task(task)
        
        return jsonify({'message': '开始合并'})
        
    except Exception as e:
        logger.error(f"合并失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<task_id>/merge/progress')
def get_merge_progress(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({
            'progress': 0,
            'status': '任务不存在',
            'error': True
        })
    
    merge_info = task.get('merge_info', {})
    return jsonify({
        'progress': merge_info.get('progress', 0),
        'status': merge_info.get('status', '准备中...'),
        'error': merge_info.get('error', False)
    })

def merge_video_segments(task_id, task):
    """合并视频片段的函数"""
    try:
        task_dir = task.get('task_dir')
        segments_dir = os.path.join(task_dir, 'segments')
        
        # 更新合并状态
        task_manager.update_task(task_id, {
            'merge_info': {
                'progress': 0,
                'status': '准备合并文件...',
                'start_time': time.time()
            }
        })
        
        # 获取所有片段文件
        segment_files = sorted(glob.glob(os.path.join(segments_dir, 'segment_*.ts')))
        if not segment_files:
            raise Exception("没有找到可合并的片段")

        # 定义进度回调函数
        def update_merge_progress(output):
            if 'frame=' in output:
                current_progress = task_manager.get_task(task_id).get('merge_info', {}).get('progress', 0)
                task_manager.update_task(task_id, {
                    'merge_info': {
                        'progress': min(95, current_progress + 1),
                        'status': '正在合并...'
                    }
                })

        # 使用TSMerger进行合并
        result = ts_merger.merge_files(
            segment_files,  # 直接传递文件路径列表
            task_id        # 直接传递task_id
        )

        if not result:  # 如果返回None或False
            raise Exception("合并失败")

        # 更新任务状态
        end_time = time.time()
        merge_duration = int(end_time - task.get('merge_info', {}).get('start_time', end_time))
        
        task_manager.update_task(task_id, {
            'merge_info': {
                'progress': 100,
                'status': '合并完成',
                'duration': merge_duration
            },
            'output_file': result,
            'status': '合并完成！'
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"合并失败: {error_msg}")
        
        # 更新错误状态
        task_manager.update_task(task_id, {
            'merge_info': {
                'progress': 0,
                'status': f'合并失败: {error_msg}',
                'error': True
            },
            'status': f'合并失败: {error_msg}'
        })

# 添加视频预览路由
@app.route('/preview/<task_id>')
def preview_video(task_id):
    task = task_manager.get_task(task_id)
    if not task or 'output_file' not in task:
        return '视频不存在', 404
        
    # 返回视频文件，支持范围请求以实现流媒体播放
    output_file = task['output_file']
    if not os.path.exists(output_file):
        return '视频文件不存在', 404
        
    return send_file(
        output_file,
        mimetype='video/mp4',
        as_attachment=False,
        conditional=True  # 启用范围请求支持
    )

if __name__ == '__main__':
    app.run(debug=True) 