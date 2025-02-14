import os
import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Optional
import shutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class TSMerger:
    def __init__(self, output_dir='merged'):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def merge_files(self, file_paths: List[str], task_id: str):
        """
        合并TS文件
        
        Args:
            file_paths: TS文件路径列表
            task_id: 任务ID
        """
        # 为每个任务创建独立的工作目录
        work_dir = os.path.join(self.output_dir, task_id)
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
            
        # 使用任务特定的文件列表
        filelist_path = os.path.join(work_dir, 'filelist.txt')
        
        try:
            # 创建文件列表，使用绝对路径
            with open(filelist_path, 'w', encoding='utf-8') as f:
                for file_path in file_paths:
                    # 转换为绝对路径
                    abs_path = os.path.abspath(file_path)
                    # 使用正斜杠替换反斜杠
                    safe_path = abs_path.replace('\\', '/')
                    f.write(f"file '{safe_path}'\n")
            
            # 设置输出文件路径
            output_file = os.path.join(self.output_dir, f'{task_id}.mp4')
            
            # 执行ffmpeg命令
            cmd = [
                'ffmpeg', '-f', 'concat',
                '-safe', '0',
                '-i', filelist_path,
                '-c', 'copy',
                '-y',  # 覆盖已存在的文件
                output_file
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg 错误: {stderr.decode()}")
                
            return output_file
            
        except Exception as e:
            raise Exception(f"合并失败: {str(e)}")
            
        finally:
            # 清理临时文件
            if os.path.exists(filelist_path):
                try:
                    os.remove(filelist_path)
                except:
                    pass
            # 清理工作目录
            try:
                os.rmdir(work_dir)
            except:
                pass

    def validate_ts_file(self, file_path):
        """
        验证TS文件是否有效
        :param file_path: TS文件路径
        :return: bool
        """
        try:
            if not os.path.exists(file_path):
                return False

            # 使用FFmpeg检查文件
            command = [
                'ffmpeg',
                '-v', 'error',
                '-i', file_path,
                '-f', 'null',
                '-'
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"验证文件失败 {file_path}: {str(e)}")
            return False

    def clean_task(self, task_id: str):
        """
        清理任务相关文件
        
        Args:
            task_id: 任务ID
        """
        # 清理工作目录
        work_dir = os.path.join(self.output_dir, task_id)
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        
        # 清理输出文件
        output_file = os.path.join(self.output_dir, f'{task_id}.mp4')
        if os.path.exists(output_file):
            os.remove(output_file)

def main():
    """命令行使用示例"""
    import argparse
    parser = argparse.ArgumentParser(description='合并TS文件')
    parser.add_argument('files', nargs='+', help='要合并的TS文件')
    parser.add_argument('-o', '--output', help='输出文件名')
    args = parser.parse_args()

    merger = TSMerger()
    result = merger.merge_files(args.files, args.output)
    
    if result['success']:
        print(f"合并成功: {result['output_file']}")
    else:
        print(f"合并失败: {result['message']}")

if __name__ == '__main__':
    main() 