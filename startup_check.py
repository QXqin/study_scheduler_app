import json
import datetime
import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_PATH = os.path.join(BASE_DIR, "current_schedule.json")
LAST_RUN_PATH = os.path.join(BASE_DIR, "last_sunday_run.txt")

now = datetime.datetime.now()
today_str = now.strftime("%Y-%m-%d")
is_sunday = now.weekday() == 6

needs_run = False

if is_sunday:
    # 检查是否这个周日已经运行过，防止每次重启电脑重复推送
    last_run = ""
    if os.path.exists(LAST_RUN_PATH):
        with open(LAST_RUN_PATH, 'r', encoding='utf-8') as f:
            last_run = f.read().strip()
    if last_run != today_str:
        needs_run = True
else:
    # 如果不是周日，检查今天是否已经在排期表 json 中（也就是判断是否已经有近期的表）
    if os.path.exists(SCHEDULE_PATH):
        try:
            with open(SCHEDULE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if today_str not in data:
                # 今天的计划没有找到，说明旧表过期了，需要跑一次新的
                needs_run = True
        except:
            needs_run = True
    else:
        needs_run = True

if needs_run:
    # 追加一行日志，证明脚本在后台执行过
    with open(os.path.join(BASE_DIR, "startup_log.txt"), 'a', encoding='utf-8') as f:
        f.write(f"[{now}] 检测到今日 ({today_str}) 无现存排期或是周日例行重排，正在后台触发 scheduler.py...\n")
        
    subprocess.run([sys.executable, "scheduler.py"], cwd=BASE_DIR)
    
    if is_sunday:
        with open(LAST_RUN_PATH, 'w', encoding='utf-8') as f:
            f.write(today_str)
else:
    with open(os.path.join(BASE_DIR, "startup_log.txt"), 'a', encoding='utf-8') as f:
        f.write(f"[{now}] 检测到今日 ({today_str}) 计划已存在，跳过调度，仅记录。\n")
