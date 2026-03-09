# 考研智能追踪看板 (Study Scheduler)

> 一款专为考研党打造的本地化 AI 智能日程管理系统。完美结合大模型动态排表、微信推流与自定式响应看板。

[English](./README.md) | [中文](./README_zh-CN.md)

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![DeepSeek API](https://img.shields.io/badge/AI-DeepSeek-black)

## 核心特性 (Features)

- **AI 智能排期**：底座接入 DeepSeek API。系统能完美结合你的“必上校园课表”、“个人目标偏好”与“通勤时长”，通过 AI 统筹能力输出精准的极客级周计划。
- **防止幻觉的课表挂载**：支持极速导入常见大学课表软件 (如 WakeUp) 导出的 `.ics` 文件。底层附带防呆校验，精准识别当前有效学期，严格过滤已结课的课程，100% 避免大模型幻觉瞎排。
- **微信自动推流**：生成的计划不仅可供前端使用，还会渲染出极致排版的 Markdown 推送，通过 Pushplus 直接发送至你的微信。
- **响应式打卡看版**：基于 Streamlit 构建的高颜值本地交互终端。今日日程以复选框的形式完美展现，进度实时持久化到本地。支持局域网环境下使用手机端沉浸式访问打卡（PWA 体验）。
- **自然语言操控 (NLP Updater)**：嫌改 yaml 配置文件太麻烦？在网页里像跟人聊天一样发一句：“这周五不用开会了，改成背政治”，系统自动在后台完成 YAML 代码增删改查。
- **全自动静默启停**：附带免黑框开机自启脚本。每天开机静默查岗，周日自动生成下周总表，缺表自动补表，绝不打扰。

## 快速开始 (Quick Start)

### 依赖准备

- Python 3.8+
- 安装依赖库：`pip install pyyaml requests openai ics streamlit pydantic`
- 获取你的 [DeepSeek API Key](https://platform.deepseek.com/)
- 获取你的 [Pushplus Token](https://www.pushplus.plus/)

### 参数配置

1. 打开 `config.yaml`，在 `api` 节点下填入你的 DeepSeek Key 和 Pushplus Token。
2. 配置你的 `user_info`（目标院校、科目）和你的大白话 `preferences` (比如：必须健身、上午背单词等)。

### 课表导入 (可选)

如果你有大学课表的 `.ics` 文件：

```bash
python import_ics.py "/你的/绝对/路径/课表.ics"
```

### 运行使用

**一键启动交互看板：**

在文件夹中直接双击 `run_app.bat`，或者在终端中运行：

```bash
streamlit run app.py
```

*💡 手机端使用提示：确保手机与电脑连接同一 WiFi（如宿舍网络），在手机浏览器输入黑框里显示的 `Network URL` 即可直接打卡操作！*

**安装开机自启服务 (仅限 Windows)：**

右键以管理员身份运行 `setup_task.bat`。它会向系统注册一个隐藏的定时任务，随后每次开机会在后台静默完成课表查漏补缺和微信发送。

## 工程结构 (Project Structure)

```text
study_scheduler/
├── app.py               # Streamlit Web 看板核心界面
├── scheduler.py         # 核心排期引擎：组装 Prompt、调用 DeepSeek 并分发 JSON/Markdown
├── import_ics.py        # 课表解析器，精准提取周次起止时间
├── ai_updater.py        # NLP 大语言模型配置文件重写器
├── startup_check.py     # 负责开机时校验时间表存在性的逻辑
├── config.yaml          # 全局数据库，存储 API Key 及其它配置偏好
├── current_schedule.json# 打卡渲染必须的结构化数据集
├── progress.json        # 每日任务复选框打卡状态记录
├── run_app.bat          # 看板双击启动器
├── setup_task.bat       # Windows 定时任务安装器
└── run_hidden.vbs       # 消除 CMD 黑框的后台隐蔽脚本
```

## 开源协议 (License)

[MIT](./LICENSE)
