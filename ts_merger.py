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
        os.makedirs(output_dir, exist_ok=True)

    def merge_files(self, input_files, output_filename=None, progress_callback=None):
        """
        合并TS文件
        :param input_files: TS文件路径列表
        :param output_filename: 输出文件名(可选)
        :param progress_callback: 进度回调函数(可选)
        :return: dict, 包含合并结果信息
        """
        try:
            if not input_files:
                return {
                    'success': False,
                    'message': '没有输入文件'
                }

            # 如果没有指定输出文件名，使用时间戳生成
            if not output_filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f'merged_{timestamp}.mp4'

            # 确保输出文件路径
            output_file = os.path.join(self.output_dir, output_filename)
            
            # 创建临时文件列表
            list_file = os.path.join(self.output_dir, 'filelist.txt')
            with open(list_file, 'w', encoding='utf-8') as f:
                for file_path in input_files:
                    # 使用绝对路径
                    abs_path = os.path.abspath(file_path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")

            # FFmpeg命令
            command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                output_file
            ]

            # 执行合并
            logger.info(f"开始合并 {len(input_files)} 个文件到 {output_file}")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 等待完成并处理进度回调
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output and progress_callback:
                    progress_callback(output.strip())
            
            stdout, stderr = process.communicate()

            # 清理临时文件
            if os.path.exists(list_file):
                os.remove(list_file)

            # 检查结果
            if process.returncode == 0 and os.path.exists(output_file):
                logger.info(f"合并完成: {output_file}")
                return {
                    'success': True,
                    'output_file': output_file,
                    'message': '合并成功'
                }
            else:
                error_msg = stderr
                logger.error(f"合并失败: {error_msg}")
                return {
                    'success': False,
                    'message': f'合并失败: {error_msg}'
                }

        except Exception as e:
            logger.error(f"合并出错: {str(e)}")
            return {
                'success': False,
                'message': f'合并出错: {str(e)}'
            }

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