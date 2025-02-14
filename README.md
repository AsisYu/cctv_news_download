# 视频处理工具

一个基于 Flask 的视频处理工具，支持 TS 文件合并和 CCTV 视频下载功能。提供友好的 Web 界面，支持实时进度显示和任务管理。

## 功能特点

### TS 文件合并
- 支持多文件拖拽上传
- 自动排序合并
- 实时进度显示
- 支持大文件处理
- 合并状态实时反馈
- 支持失败重试

### CCTV 视频下载
- 支持通过 PID 下载视频
- 多线程并发下载
- 断点续传支持
- 失败重试机制
- 任务持久化存储
- 详细的下载进度显示
- 片段信息统计

### 任务管理系统
- 任务状态实时更新
- 详细的任务信息展示
- 支持任务删除和重试
- 片段级别的状态管理
- 下载速度和进度统计
- 文件大小和耗时统计

## 项目结构

    project/
    ├── app.py                 # Flask应用主程序
    ├── requirements.txt       # 项目依赖
    ├── tasks.json            # 任务持久化存储
    ├── static/               # 静态资源目录
    │   ├── css/
    │   │   └── style.css    # 自定义样式
    │   └── js/
    │       └── main.js      # 前端交互脚本
    ├── templates/            # 模板目录
    │   └── index.html       # 主页面模板
    ├── uploads/             # 上传文件存储目录
    └── merged/              # 合并后文件存储目录

## 技术栈

### 后端
- Python 3.8+
- Flask 2.0.1
- FFmpeg

### 前端
- Bootstrap 5
- jQuery 3.6.0
- Bootstrap Icons
- Animate.css

## 安装说明

1. 创建并激活虚拟环境：

Windows:
    python -m venv venv
    venv\Scripts\activate

Linux/Mac:
    python3 -m venv venv
    source venv/bin/activate

2. 安装Python依赖：

    pip install -r requirements.txt

如果requirements.txt不存在，可以手动安装必要的包：

    pip install flask
    pip install requests

3. 安装FFmpeg：

Linux:
    sudo apt update
    sudo apt install ffmpeg

macOS:
    brew install ffmpeg

4. 创建必要的目录：

    mkdir uploads merged

5. 运行应用：

    python app.py

## 使用说明

### TS文件合并
1. 点击"选择文件"或拖拽文件到上传区域
2. 选择需要合并的TS文件
3. 点击"开始合并"
4. 等待合并完成后下载

### CCTV视频下载
1. 访问CCTV视频页面
2. 在页面源代码中搜索"guid"找到视频PID
   - 按F12打开开发者工具
   - 按Ctrl+F搜索"guid"
   - 复制找到的32位字符串
3. 将PID复制到输入框
4. 点击"开始下载"
5. 等待下载完成

## 配置说明

主要配置项在app.py中：

    MAX_CONTENT_LENGTH = 2GB  # 最大上传限制
    MAX_WORKERS = 8           # 下载线程数
    SEGMENT_TIMEOUT = 30      # 片段下载超时时间(秒)
    RETRY_LIMIT = 3          # 重试次数限制

## 常见问题

### ModuleNotFoundError: No module named 'flask'
这个错误表示没有安装Flask包，解决方法：
1. 确保已激活虚拟环境（命令提示符前应该有(venv)）
2. 运行 `pip install flask`

### 其他依赖相关错误
如果遇到其他模块缺失错误，可以使用pip安装：

    pip install 模块名

### FFmpeg相关错误
1. 确保FFmpeg已正确安装
2. 确保FFmpeg在系统PATH中
3. 可以在命令行运行 `ffmpeg -version` 测试是否安装成功

### 下载失败问题
1. PID格式错误
   - 确保PID是32位的十六进制字符串
   - 检查是否包含非法字符
2. 网络连接问题
   - 检查网络连接是否正常
   - 可以尝试使用重试功能
3. 存储空间不足
   - 检查磁盘剩余空间
   - 清理临时文件

## 任务管理

- 已完成或出错的任务可以删除
- 下载失败的任务可以重试
- 任务进度实时显示
- 支持断点续传
- 自动清理过期任务

## 安全提示

1. 仅供个人学习使用
2. 请勿用于商业用途
3. 遵守相关法律法规
4. 注意保护版权

## 更新日志

### v1.0.0 (2024-02-14)
- 初始版本发布
- 支持TS文件合并
- 支持CCTV视频下载
- 任务管理系统
- 多线程下载
- 失败重试机制

## 许可证

本项目采用 MIT 许可证 