@echo off
REM 此脚本用于测试或挂载到 Windows 任务计划程序
REM 切换到脚本所在目录
cd /d "%~dp0"
echo 正在安装依赖（若已安装则跳过）...
pip install -r requirements.txt -q
echo ----------------------------------------
python scheduler.py
echo ----------------------------------------
pause
