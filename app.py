import streamlit as st
import yaml
import json
import os
import datetime
from ai_updater import update_config_with_nl
import subprocess

st.set_page_config(page_title="考研智能看板", page_icon="📅", layout="centered")

# ----- 配置路径 -----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
SCHEDULE_JSON_PATH = os.path.join(BASE_DIR, "current_schedule.json")
PROGRESS_PATH = os.path.join(BASE_DIR, "progress.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_schedule_json():
    if not os.path.exists(SCHEDULE_JSON_PATH):
        return {}
    try:
        with open(SCHEDULE_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def load_progress():
    if not os.path.exists(PROGRESS_PATH):
        return {}
    try:
        with open(PROGRESS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_progress(prog):
    with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
        json.dump(prog, f, ensure_ascii=False)

# ----- UI 主体 -----
st.title("📚 考研智能追踪看板")
st.markdown("---")

tab1, tab2 = st.tabs(["📝 今日打卡", "⚙️ AI日程对讲机"])

with tab1:
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    st.header(f"今日计划 ({today_str})")
    
    schedule_data = load_schedule_json()
    progress_data = load_progress()
    
    # 今天的数组
    today_tasks = schedule_data.get(today_str, [])
    
    if not today_tasks:
        st.info("今天没有从排期表中解析到任务，或者你还没有生成最新的结构化表。请到第二个标签页触发一键重新生成。")
    else:
        for i, task_info in enumerate(today_tasks):
            time_slot = task_info.get("time", "")
            task_desc = task_info.get("task", "")
            task_type = task_info.get("type", "study")
            
            # 渲染一个 checkbox
            uid = f"{today_str}_{i}_{time_slot}"
            is_checked = progress_data.get(uid, False)
            
            label = f"**{time_slot}** | {task_desc}"
            
            # 根据类型加点 emoji
            if task_type == "class":
                label = f"🎓 {label}"
            elif task_type == "fitness":
                label = f"🏃 {label}"
            elif task_type == "commute":
                label = f"🚌 {label}"
            else:
                label = f"📖 {label}"
            
            new_val = st.checkbox(label, value=is_checked, key=uid)
            
            if new_val != is_checked:
                progress_data[uid] = new_val
                save_progress(progress_data)
                
with tab2:
    st.header("🤖 AI日程调控中心")
    st.markdown("不需要再手动去改那个难懂的 `config.yaml` 了。你需要做什么改变，直接在这里告诉 AI！")
    
    user_prompt = st.text_area("例如：'这周四晚上临时有个讲座，帮我加进日程里。'", height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ 让 AI 修改配置并重新排表", use_container_width=True):
            if not user_prompt:
                st.warning("请输入你的要求！")
            else:
                with st.spinner("AI 正在理解你的意图并修改底层配置文件..."):
                    config = load_config()
                    api_key = config.get('api', {}).get('deepseek_api_key', '')
                    success, msg = update_config_with_nl(api_key, CONFIG_PATH, user_prompt)
                    
                    if success:
                        st.success(msg)
                        st.info("正在唤醒 scheduler.py 进行重新排表（需要几十秒，请勿刷新页面）...")
                        
                        # 触发生成脚本
                        result = subprocess.run(["python", "scheduler.py"], cwd=BASE_DIR, capture_output=True, text=True)
                        if result.returncode == 0:
                            st.success("✅ 全新排表生成完毕，并已推送到微信！点击第一个标签页即可查看新的今日计划。")
                            st.balloons()
                        else:
                            st.error(f"❌ 调度失败: {result.stderr}")
                    else:
                        st.error(msg)
    with col2:
        if st.button("🔄 不修改配置，直接重排本周", use_container_width=True):
            with st.spinner("正在唤醒 scheduler.py 重新生成并推送到微信（需要几十秒）..."):
                result = subprocess.run(["python", "scheduler.py"], cwd=BASE_DIR, capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("✅ 全新排表生成完毕，并已推送到微信！")
                    st.balloons()
                else:
                    st.error(f"❌ 调度失败: {result.stderr}")

