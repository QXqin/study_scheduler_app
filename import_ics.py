import yaml
import sys
import os
from datetime import datetime
try:
    from ics import Calendar
except ImportError:
    print("❌ 错误：缺少 `ics` 库，可以通过 `pip install ics` 安装")
    sys.exit(1)

def parse_ics_to_config(ics_file_path, config_path="config.yaml"):
    if not os.path.exists(ics_file_path):
        print(f"❌ 错误：找不到文件 {ics_file_path}")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_config_path = os.path.join(base_dir, config_path)
    
    with open(ics_file_path, 'r', encoding='utf-8') as f:
        ics_text = f.read()
    
    # 解析 ICS 日历
    cal = Calendar(ics_text)
    
    fixed_classes = []
    
    # 使用字典来按“星期_时间_课程名”归类并合并日期
    classes_dict = {}
    
    # 星期映射字典
    weekdays_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    for event in cal.events:
        # 获取本地的首次上课时间
        local_begin = event.begin.to('Asia/Shanghai')
        local_end = event.end.to('Asia/Shanghai')
        
        day_str = weekdays_zh[local_begin.weekday()]
        time_str = f"{local_begin.format('HH:mm')}-{local_end.format('HH:mm')}"
        
        # 组装课程信息 (名称 + 地点)
        course_info = event.name
        if event.location:
             course_info += f" ({event.location})"
             
        # 提取起止日期
        start_date_str = local_begin.format('YYYY-MM-DD')
        
        # 检查有没有 RRULE (直到什么时候结束)
        # ics 库中可以通过 event._extra 里的原始文本提取，或者简单地利用 event 的持续性
        # 由于 ics 的 event.get_rrule() 有时解析不够完善，我们可以暴力读取该事件的原始行
        end_date_str = start_date_str # 默认只有一天
        if hasattr(event, 'extra') or hasattr(event, '_unused'):
            raw_lines = str(event).split('\n')
            for line in raw_lines:
                if line.startswith('RRULE:'):
                    # RRULE:FREQ=WEEKLY;UNTIL=20251109T160000Z;INTERVAL=1
                    if 'UNTIL=' in line:
                        until_part = line.split('UNTIL=')[1].split(';')[0]
                        # 转换 UNTIL 为日期格式 (yyyy-mm-dd)
                        end_date_str = f"{until_part[:4]}-{until_part[4:6]}-{until_part[6:8]}"
                    break

        unique_key = f"{day_str}_{time_str}_{course_info}"
        
        if unique_key not in classes_dict:
            classes_dict[unique_key] = {
                "day": day_str,
                "time": time_str,
                "course": course_info,
                "active_dates": []
            }
        
        # 将该日期段加入
        date_range = f"{start_date_str} 至 {end_date_str}"
        if date_range not in classes_dict[unique_key]["active_dates"]:
            classes_dict[unique_key]["active_dates"].append(date_range)
            
    # 将字典转为列表并格式化 date_range
    for key, val in classes_dict.items():
        val["active_dates"] = "，".join(val["active_dates"])
        fixed_classes.append(val)
            
    # 按星期排序，方便阅读
    day_order = {day: i for i, day in enumerate(weekdays_zh)}
    fixed_classes.sort(key=lambda x: (day_order[x['day']], x['time']))
    
    # 写回 yaml
    if os.path.exists(full_config_path):
        with open(full_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {}
        
    config['fixed_classes'] = fixed_classes
    
    with open(full_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        
    print(f"✅ 成功从 {ics_file_path} 导入 {len(fixed_classes)} 节课程到 {config_path}！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("💡 用法: python import_ics.py <你的课表文件.ics>")
    else:
        parse_ics_to_config(sys.argv[1])
