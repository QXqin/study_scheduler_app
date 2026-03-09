import yaml
import requests
from openai import OpenAI
import sys
import os
from datetime import datetime, timedelta

def load_config(config_path="config.yaml"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, config_path)
    with open(full_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def is_date_in_active_ranges(target_date, active_dates_str):
    """
    判断目标日期（datetime 对象）是否在形如 "2025-10-27 至 2025-11-09，2026-01-19 至 2026-03-01" 的区间内
    如果没有 active_dates 字段，默认返回 True
    """
    if not active_dates_str:
        return True
    
    ranges = active_dates_str.split('，')
    for r in ranges:
        try:
            start_str, end_str = r.split(' 至 ')
            start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
            if start_date <= target_date <= end_date:
                return True
        except Exception:
            # 解析失败则回退为放行
            pass
    return False

def filter_active_classes(fixed_classes, start_date, end_date):
    """
    只返回在 [start_date, end_date] 区间内至少有一天是活跃的固定课程
    """
    active_classes = []
    for cls in fixed_classes:
        active_dates_str = cls.get('active_dates', '')
        if not active_dates_str:
            active_classes.append(cls)
            continue
            
        # 只要该排期范围 [start_date, end_date] 内的任何一天，该课是活跃的，就加进去
        delta = end_date - start_date
        is_active = False
        for i in range(delta.days + 1):
            check_date = start_date + timedelta(days=i)
            if is_date_in_active_ranges(check_date, active_dates_str):
                is_active = True
                break
                
        if is_active:
            active_classes.append(cls)
            
    return active_classes

def get_schedule_range():
    """
    判断当前时间，计算本次生成的排班范围。
    如果是周一到周六调用：生成范围为【今日】至【本周日】（用于处理突发事件的重排）
    如果是周日调用：生成范围为【下周一】至【下周日】（用于自动化周报推流）
    """
    now = datetime.now()
    today = now.date()
    weekday = today.weekday() # 0 = 周一, 6 = 周日
    
    if weekday == 6:
        # 周日，排下周
        start_date = today + timedelta(days=1)
        end_date = today + timedelta(days=7)
    else:
        # 周一至周六，排今日至本周日
        start_date = today
        end_date = today + timedelta(days=(6 - weekday))
        
    return start_date, end_date

def generate_schedule(config):
    api_key = config['api']['deepseek_api_key']
    
    start_date, end_date = get_schedule_range()
    
    # 过滤这周不上课的那些历史记录
    raw_fixed_classes = config.get('fixed_classes', [])
    filtered_classes = filter_active_classes(raw_fixed_classes, start_date, end_date)
    
    # 因为传给大模型为了节省 Token 不必再附带 active_dates 了
    clean_classes = []
    for c in filtered_classes:
        clean_classes.append({k:v for k,v in c.items() if k != 'active_dates'})
    
    # 构建严谨的 System Prompt，规避大模型幻觉与乱排版
    system_prompt = f"""你是一个顶级的考研时间管理和数据序列化专家。

【核心时间上下文】
今天是 {datetime.now().strftime('%Y年%m月%d日')}。
请你为用户生成从 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 期间的详细学习时间计划表。

【用户基础画像】
身份：{config.get('user_info', {}).get('role', '')}
目标：{config.get('user_info', {}).get('goal', '')}
备考科目：{config.get('user_info', {}).get('target_majors', '')}
活跃时间：{config.get('user_info', {}).get('daily_active_hours', '')}
固定休息：{config.get('user_info', {}).get('meal_and_rest', '')}

【过滤后的有效本期课表】
以下是经过系统过滤，在这几天**确实发生**的固定课程。你在排表时必须将其原封不动地插入对应星期的时间块。
{yaml.dump(clean_classes, allow_unicode=True)}

【本期突发待办与预估通勤】
（若无则忽略）
{yaml.dump(config.get('temp_tasks', []), allow_unicode=True)}

【排班偏好与绝对约束】
{yaml.dump(config.get('preferences', []), allow_unicode=True)}

【强制输出结构协议（极核要求，违背将导致系统崩溃）】
1. 绝对禁止输出任何 Markdown 格式或解释性说明。
2. 你必须且只能输出一份**纯净的 JSON 字符串**。
3. JSON 格式必须是字典，键是具体的日期（"YYYY-MM-DD"格式，必须涵盖要求的时间区间），值是那一天的时间块数组。
4. 每天的时间块数组，由早上自习一直覆盖到晚上休息。必须涵盖刚才的“固定课程”与“待办”。
5. type 字段只能是 ["class", "study", "commute", "fitness", "rest"] 中的一个。
模板示例：
{{
  "2026-03-09": [
    {{"time": "08:00-09:45", "task": "[复习] 考研数学精讲精练", "type": "study"}},
    {{"time": "09:55-11:30", "task": "新型航空遥感数据处理技术", "type": "class"}},
    {{"time": "14:00-16:00", "task": "[去健身房路上]", "type": "commute"}},
    {{"time": "16:00-18:00", "task": "胸背肌肉针对性器械训练", "type": "fitness"}}
  ]
}}
请立刻输出涵盖 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} 所有要求的纯 JSON。
"""

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    print(f"🚀 正在调用 DeepSeek API 为区间 [{start_date} -> {end_date}] 生成 JSON 结构化排期...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请输出纯 JSON，不要 Markdown 代码块（即不要出现 ```json）。直接以 {{ 开头。"}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        content = response.choices[0].message.content.strip()
        
        # 清理多余的标记
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
            
        import json
        schedule_data = json.loads(content)
        
        # 1. 保存给前端 App 用
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "current_schedule.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(schedule_data, f, ensure_ascii=False, indent=2)
            
        # 2. 转换成 Markdown 给微信 Pushplus
        markdown_str = ""
        for date_str, tasks in schedule_data.items():
            markdown_str += f"### 📅 {date_str}\n"
            for t in tasks:
                icon = "📖"
                if t.get("type") == "class":
                    icon = "🎓"
                elif t.get("type") == "fitness":
                    icon = "🏃"
                elif t.get("type") == "commute":
                    icon = "🚌"
                elif t.get("type") == "rest":
                    icon = "☕"
                markdown_str += f"- **{t.get('time', '')}** | {icon} {t.get('task', '')}\n"
            markdown_str += "\n"
            
        return markdown_str
    except Exception as e:
        print(f"❌ API 调用或解析失败: {e}")
        return ""

def send_to_pushplus(token, content):
    if not content:
        return
    url = "http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": "📅 考研备战 | 你的专属动态时间表",
        "content": content,
        "template": "markdown"
    }
    print("📡 正在通过 Pushplus 发送数据到微信...")
    response = requests.post(url, json=data)
    if response.status_code == 200 and response.json().get('code') == 200:
        print("✅ 推送成功！请立刻在微信端查收。")
    else:
        print(f"❌ 推送失败：{response.text}")

if __name__ == "__main__":
    try:
        config = load_config()
    except Exception:
        print("❌ 错误：配置文件读取失败。")
        sys.exit(1)
        
    api_key = config.get('api', {}).get('deepseek_api_key', '')
    push_token = config.get('api', {}).get('pushplus_token', '')
    
    if "YOUR_" in api_key or "YOUR_" in push_token:
        print("❌ 错误：请先打开 config.yaml，填入真实的 DeepSeek API Key 和 Pushplus Token。")
        sys.exit(1)
        
    schedule_markdown = generate_schedule(config)
    send_to_pushplus(push_token, schedule_markdown)
