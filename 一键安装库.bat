@echo off
setlocal enabledelayedexpansion

REM 设置控制台编码为UTF-8
chcp 65001

REM 定义需要安装的Python包
set "PACKAGES=hashlib selenium beautifulsoup4 regex requests glob shutil moviepy"

REM 循环遍历所有包并尝试安装，使用阿里云的镜像源
for %%p in (%PACKAGES%) do (
    echo 正在检查并尝试安装 %%p...
    pip install %%p -i https://mirrors.aliyun.com/pypi/simple/
)

echo.
echo 所有必要的Python包安装检查完成。
pause
