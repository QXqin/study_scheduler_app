# Study Scheduler (考研智能看板)

> An AI-powered, locally-hosted study schedule manager designed for graduate entrance exam preparation, featuring dynamic schedule generation, WeChat notifications, and a responsive web dashboard.

[English](./README.md) | [中文](./README_zh-CN.md)

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![DeepSeek API](https://img.shields.io/badge/AI-DeepSeek-black)

## Features

- **Automated AI Scheduling**: Uses DeepSeek API to automatically generate a highly optimized weekly study plan based on your university class timetable, personal tasks, commute times, and study preferences.
- **Smart Date Parsing**: Accurately imports your existing university `.ics` schedules with strict active date validations—preventing expired classes from showing up in your future plans.
- **WeChat Notifications**: Seamlessly pushes your formatted daily routines directly to your phone via Pushplus.
- **Interactive Web App**: A responsive, mobile-friendly Streamlit interface that allows you to check off your daily tasks (progress saved locally). Accessible via local network on your mobile device.
- **NLP Configuration**: Modify your schedule naturally. Just type "Add a 2-hour workout this Friday evening" into the app, and the AI will rewrite your `config.yaml` and regenerate your schedule instantly.
- **Silent Auto-Boot**: Runs silently on Windows startup. It checks your schedule status and triggers an AI generation pipeline only when your current schedule is empty or out-of-date.

## Quick Start

### Prerequisites

- Python 3.8+
- Requirements: `pip install -r requirements.txt` (or install manually: `pyyaml`, `requests`, `openai`, `ics`, `streamlit`, `pydantic`)
- A valid [DeepSeek API Key](https://platform.deepseek.com/)
- A valid [Pushplus Token](https://www.pushplus.plus/)

### Configuration

1. Open `config.yaml` and input your `deepseek_api_key` and `pushplus_token`.
2. Edit your `user_info` and `preferences`.

### First Run & Import

If you have a university schedule mapped in an `.ics` file (e.g., exported from WakeUp Schedule):

```bash
python import_ics.py "/path/to/your/schedule.ics"
```

### Usage

**Launch the Interactive Local App:**

Double-click `run_app.bat` or run the following in your terminal:

```bash
streamlit run app.py
```

*Tip: For mobile access, connect your phone to the same Wi-Fi network and open the `Network URL` displayed in the terminal!*

**Install Silent Auto-Boot (Windows Only):**

Run `setup_task.bat` as Administrator. This creates a hidden scheduled task that checks if a new schedule needs to be generated upon system login.

## Project Structure

```text
study_scheduler/
├── app.py               # Streamlit web application
├── scheduler.py         # Core engine: contacts DeepSeek and converts JSON to Markdown
├── import_ics.py        # ICS parser with comprehensive date range mapping
├── ai_updater.py        # Natural Language config editor
├── startup_check.py     # Logic for the auto-boot verifications
├── config.yaml          # All states, keys, and tasks configuration
├── current_schedule.json# Extracted tasks powering the Streamlit UI
├── progress.json        # Checkbox tracking for the daily view
├── run_app.bat          # Easy-click launcher for the web app
├── setup_task.bat       # Windows Scheduled Task installer
└── run_hidden.vbs       # VBScript wrapper for silent startup execution
```

## License

[MIT](./LICENSE)
