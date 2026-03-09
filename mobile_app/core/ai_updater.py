import yaml
import json
from openai import OpenAI

def update_config_with_nl(api_key: str, current_yaml_str: str, user_prompt: str):
    """
    Sends the current config as string and user prompt to DeepSeek, returning the updated YAML string.
    """
    system_prompt = f"""你是一个智能配置文件助理。
下面是用户当前的考研时间安排配置文件（YAML格式）。
用户会对这个配置提出自然语言修改要求（比如增加一个临时待办、修改偏好、删除某个任务）。
你需要理解用户的意图，直接修改 YAML 中对应的项（通常是 `temp_tasks` 或 `preferences`，如果没有请按需新建对象），然后输出**完整且纯净的最新的 YAML 文本**。

【硬性要求】
1. 你的回答**只能包含 YAML 文本**本身，不要包裹在 ```yaml ... ``` 中，不要有任何前言后语。
2. 绝对不能破坏原有的数据结构基础节点。
3. YAML 必须合法，缩进正确。

【当前配置】
{current_yaml_str}
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
        if new_yaml_str.startswith("```yaml"): new_yaml_str = new_yaml_str[7:]
        if new_yaml_str.startswith("```"): new_yaml_str = new_yaml_str[3:]
        if new_yaml_str.endswith("```"): new_yaml_str = new_yaml_str[:-3]
        new_yaml_str = new_yaml_str.strip()
            
        # 校验是否合法
        new_config = yaml.safe_load(new_yaml_str)
        if not isinstance(new_config, dict):
            raise ValueError("AI 返回了非字典的 YAML 结构")
            
        return True, new_yaml_str
    except Exception as e:
        return False, f"处理失败：{e}"
