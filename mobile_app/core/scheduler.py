import yaml
import requests
from openai import OpenAI
from datetime import datetime, timedelta
import json

def is_date_in_active_ranges(target_date, active_dates_str):
    if not active_dates_str: return True
    ranges = active_dates_str.split('，')
    for r in ranges:
        try:
            start_str, end_str = r.split(' 至 ')
            start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
            if start_date <= target_date <= end_date: return True
        except Exception:
            pass
    return False

def filter_active_classes(fixed_classes, start_date, end_date):
    active_classes = []
    for cls in fixed_classes:
        active_dates_str = cls.get('active_dates', '')
        if not active_dates_str:
            active_classes.append(cls)
            continue
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
    now = datetime.now()
    today = now.date()
    weekday = today.weekday()
    if weekday == 6:
        start_date = today + timedelta(days=1)
        end_date = today + timedelta(days=7)
    else:
        start_date = today
        end_date = today + timedelta(days=(6 - weekday))
    return start_date, end_date

def generate_schedule(config: dict, api_key: str):
    start_date, end_date = get_schedule_range()
    
    raw_fixed_classes = config.get('fixed_classes', [])
    filtered_classes = filter_active_classes(raw_fixed_classes, start_date, end_date)
    clean_classes = [{k:v for k,v in c.items() if k != 'active_dates'} for c in filtered_classes]
    
    system_prompt = f"""你是一个顶级的考研时间管理和数据序列化专家。
今天是 {datetime.now().strftime('%Y年%m月%d日')}。
请你为用户生成从 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 期间的详细学习时间计划表。

【用户基础画像】
身份：{config.get('user_info', {}).get('role', '')}
目标：{config.get('user_info', {}).get('goal', '')}
备考科目：{config.get('user_info', {}).get('target_majors', '')}
活跃时间：{config.get('user_info', {}).get('daily_active_hours', '')}
固定休息：{config.get('user_info', {}).get('meal_and_rest', '')}

【过滤后的有效本期课表】
{yaml.dump(clean_classes, allow_unicode=True)}

【本期突发待办与预估通勤】
{yaml.dump(config.get('temp_tasks', []), allow_unicode=True)}

【排班偏好与绝对约束】
{yaml.dump(config.get('preferences', []), allow_unicode=True)}

【强制输出结构协议】
1. 绝对禁止输出任何 Markdown 格式或解释性说明。
2. 你必须且只能输出一份纯净的 JSON 字符串。
3. JSON 是字典，键是具体的日期（YYYY-MM-DD格式）。
4. type 字段只能是 ["class", "study", "commute", "fitness", "rest"] 中的一个。
模板示例：
{{
  "{start_date.strftime('%Y-%m-%d')}": [
    {{"time": "08:00-09:45", "task": "[复习] 考研数学精讲精练", "type": "study"}},
    {{"time": "09:55-11:30", "task": "新型航空遥感数据处理技术", "type": "class"}}
  ]
}}
请立刻输出涵盖 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} 要求的纯 JSON。
"""
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请输出纯 JSON，直接以 { 开头。"}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        content = content.strip()
        schedule_data = json.loads(content)
        
        markdown_str = ""
        for date_str, tasks in schedule_data.items():
            markdown_str += f"### 📅 {date_str}\n"
            for t in tasks:
                icon = "📖"
                if t.get("type") == "class": icon = "🎓"
                elif t.get("type") == "fitness": icon = "🏃"
                elif t.get("type") == "commute": icon = "🚌"
                elif t.get("type") == "rest": icon = "☕"
                markdown_str += f"- **{t.get('time', '')}** | {icon} {t.get('task', '')}\n"
            markdown_str += "\n"
        return True, schedule_data, markdown_str
    except Exception as e:
        return False, {}, str(e)

def send_to_pushplus(token: str, content: str):
    if not token or not content: return False, "Missing token or content"
    url = "http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": "📅 考研备战 | 你的专属动态时间表",
        "content": content,
        "template": "markdown"
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200 and response.json().get('code') == 200:
            return True, "推送成功"
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)
