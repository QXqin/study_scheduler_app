import yaml
import os
from openai import OpenAI
import json

def update_config_with_nl(api_key, current_config_path, user_prompt):
    """
    Reads the current config, sends it to DeepSeek along with user instructions,
    and overwrites the config with the AI's updated version.
    """
    with open(current_config_path, 'r', encoding='utf-8') as f:
        current_yaml = f.read()

    system_prompt = f"""你是一个智能配置文件助理。
下面是用户当前的考研时间安排配置文件（YAML格式）。
用户会对这个配置提出自然语言修改要求（比如增加一个临时待办、修改偏好、删除某个任务）。
你需要理解用户的意图，直接修改 YAML 中对应的项（通常是 `temp_tasks` 或 `preferences`，如果没有请按需新建对象），然后输出**完整且纯净的最新的 YAML 文本**。

【硬性要求】
1. 你的回答**只能包含 YAML 文本**本身，不要包裹在 ```yaml ... ``` 中，不要有任何前言后语。
2. 绝对不能破坏原有的 `api`、`user_info`、`fixed_classes` 的数据结构，除非用户明确要求删除固定课。
3. YAML 必须合法，缩进正确。

【当前配置】
{current_yaml}
"""

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"我的修改要求是：{user_prompt}"}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        new_yaml_str = response.choices[0].message.content.strip()
        
        # 净化可能带有的 markdown code block tags
        if new_yaml_str.startswith("```yaml"):
            new_yaml_str = new_yaml_str[7:]
        if new_yaml_str.startswith("```"):
            new_yaml_str = new_yaml_str[3:]
        if new_yaml_str.endswith("```"):
            new_yaml_str = new_yaml_str[:-3]
            
        new_yaml_str = new_yaml_str.strip()
            
        # 校验是否合法
        new_config = yaml.safe_load(new_yaml_str)
        if not isinstance(new_config, dict) or 'api' not in new_config:
            raise ValueError("AI 返回了破损的 YAML 结构")
            
        # 写回
        with open(current_config_path, 'w', encoding='utf-8') as f:
            f.write(new_yaml_str)
            
        return True, "配置已成功更新并保存。"
        
    except Exception as e:
        return False, f"处理失败：{e}"
