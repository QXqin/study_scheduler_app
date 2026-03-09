import flet as ft
from datetime import datetime
import json
import yaml

from core.ai_updater import update_config_with_nl
from core.scheduler import generate_schedule, send_to_pushplus
from core.import_ics import parse_ics_text

def main(page: ft.Page):
    page.title = "考研智能看板"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 800
    
    # Defaults load from local persistent android storage via page.client_storage
    api_key = page.client_storage.get("api_key") or ""
    push_token = page.client_storage.get("push_token") or ""
    config_yaml_str = page.client_storage.get("config_yaml") or "api:\nuser_info:\nfixed_classes: []\npreferences: []\ntemp_tasks: []\n"
    schedule_data = page.client_storage.get("schedule_json") or {}
    progress_data = page.client_storage.get("progress_json") or {}
    
    # Save helpers
    def save_settings(e):
        page.client_storage.set("api_key", api_field.value)
        page.client_storage.set("push_token", push_field.value)
        page.snack_bar = ft.SnackBar(ft.Text("设置已保存！"), open=True)
        page.update()
        
    def save_progress():
        page.client_storage.set("progress_json", progress_data)
        
    def save_config(yaml_str):
        nonlocal config_yaml_str
        config_yaml_str = yaml_str
        page.client_storage.set("config_yaml", yaml_str)
        
    def save_schedule(sd):
        nonlocal schedule_data
        schedule_data = sd
        page.client_storage.set("schedule_json", sd)

    # --- UI COMPONENTS ---
    
    # 1. 📝 今日计划 View
    today_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, visible=True)
    
    def render_today():
        today_view.controls.clear()
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_view.controls.append(ft.Text(f"今日计划 ({today_str})", size=24, weight=ft.FontWeight.BOLD))
        today_view.controls.append(ft.Divider())
        
        today_tasks = schedule_data.get(today_str, [])
        if not today_tasks:
            today_view.controls.append(ft.Text("今天没有排期任务，请到调控中心生成。", color=ft.colors.GREY_600))
        else:
            for i, task_info in enumerate(today_tasks):
                time_slot = task_info.get("time", "")
                task_desc = task_info.get("task", "")
                task_type = task_info.get("type", "study")
                
                uid = f"{today_str}_{i}_{time_slot}"
                is_checked = progress_data.get(uid, False)
                
                icon = "📖"
                if task_type == "class": icon = "🎓"
                elif task_type == "fitness": icon = "🏃"
                elif task_type == "commute": icon = "🚌"
                elif task_type == "rest": icon = "☕"
                
                def on_change(e, uid=uid):
                    progress_data[uid] = e.control.value
                    save_progress()
                    
                cb = ft.Checkbox(label=f"{time_slot} | {icon} {task_desc}", value=is_checked, on_change=on_change)
                today_view.controls.append(cb)
        page.update()

    # 2. 🤖 AI调控中心 View
    ai_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, visible=False)
    
    ai_prompt_field = ft.TextField(label="告诉 AI 你的安排修改，例如：明天晚上临时有个讲座", multiline=True, min_lines=3, max_lines=5)
    ai_status = ft.Text("", color=ft.colors.RED_500)
    ai_progress = ft.ProgressRing(visible=False)
    
    def on_ai_submit(e):
        if not ai_prompt_field.value:
            ai_status.value = "请输入内容"
            page.update()
            return
            
        ak = page.client_storage.get("api_key")
        pt = page.client_storage.get("push_token")
        if not ak:
            ai_status.value = "请先在设置页填写 DeepSeek API Key"
            page.update()
            return
            
        ai_status.value = "AI 正在理解你的意图..."
        ai_status.color = ft.colors.BLUE_500
        ai_progress.visible = True
        ai_submit_btn.disabled = True
        page.update()
        
        # 1. NL to Config
        success, new_yaml_str = update_config_with_nl(ak, config_yaml_str, ai_prompt_field.value)
        if not success:
            ai_status.value = new_yaml_str
            ai_status.color = ft.colors.RED_500
            ai_progress.visible = False
            ai_submit_btn.disabled = False
            page.update()
            return
            
        save_config(new_yaml_str)
        ai_status.value = "配置已更新，正在唤醒调度引擎生成排单..."
        page.update()
        
        # 2. Generate Schedule
        cfg = yaml.safe_load(new_yaml_str)
        success2, sd, md_str = generate_schedule(cfg, ak)
        
        if success2:
            save_schedule(sd)
            ai_status.value = "排期生成成功！正在推送微信..."
            page.update()
            
            # 3. Push
            if pt:
                ok, msg = send_to_pushplus(pt, md_str)
                if ok: 
                    ai_status.value = "✅ 全新排表生成完毕，已推送到微信！"
                    ai_status.color = ft.colors.GREEN_500
                else: 
                    ai_status.value = f"排表生成完毕，但推送失败：{msg}"
                    ai_status.color = ft.colors.ORANGE_500
            else:
                ai_status.value = "✅ 全新排表生成完毕！未配置推送。"
                ai_status.color = ft.colors.GREEN_500
        else:
            ai_status.value = f"生成失败: {md_str}"
            ai_status.color = ft.colors.RED_500
            
        ai_progress.visible = False
        ai_submit_btn.disabled = False
        render_today() # update the first tab in background
        page.update()

    ai_submit_btn = ft.ElevatedButton("✨ 让 AI 修改配置并重新排表", on_click=on_ai_submit)
    
    ai_view.controls.extend([
        ft.Text("🤖 AI日程调控中心", size=24, weight=ft.FontWeight.BOLD),
        ft.Text("不需要手动修改配置了，你需要做什么改变，直接在这里告诉 AI！", color=ft.colors.GREY_600),
        ft.Divider(),
        ai_prompt_field,
        ft.Row([ai_submit_btn]),
        ft.Row([ai_progress, ai_status], wrap=True)
    ])

    # 3. ⚙️ 应用设置 View
    settings_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, visible=False)
    
    api_field = ft.TextField(label="DeepSeek API Key", value=api_key, password=True, can_reveal_password=True)
    push_field = ft.TextField(label="Pushplus Token", value=push_token, password=True, can_reveal_password=True)
    
    def import_ics_result(e: ft.FilePickerResultEvent):
        # file_picker uses cross-platform selection APIs
        if e.files and len(e.files):
            file_path = e.files[0].path
            if file_path:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        ics_text = f.read()
                    
                    classes = parse_ics_text(ics_text)
                    cfg = yaml.safe_load(config_yaml_str)
                    if not cfg: cfg = {}
                    cfg['fixed_classes'] = classes
                    new_yaml = yaml.dump(cfg, allow_unicode=True, sort_keys=False)
                    save_config(new_yaml)
                    
                    page.snack_bar = ft.SnackBar(ft.Text(f"成功导入 {len(classes)} 节课程并写入配置！"), open=True)
                    page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"导入失败: {ex}"), open=True)
                    page.update()

    file_picker = ft.FilePicker(on_result=import_ics_result)
    page.overlay.append(file_picker)

    settings_view.controls.extend([
        ft.Text("⚙️ 应用全局设置", size=24, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        api_field,
        push_field,
        ft.ElevatedButton("保存 设置", on_click=save_settings, icon=ft.icons.SAVE),
        ft.Divider(),
        ft.Text("课表导入 (导入后会合并/覆盖当前的固定课内容)", color=ft.colors.GREY_600),
        ft.ElevatedButton("导入 .ics 课表文件", on_click=lambda _: file_picker.pick_files(allowed_extensions=["ics"]), icon=ft.icons.UPLOAD_FILE)
    ])

    # Switch logic
    def on_nav_change(e):
        today_view.visible = e.control.selected_index == 0
        ai_view.visible = e.control.selected_index == 1
        settings_view.visible = e.control.selected_index == 2
        
        if e.control.selected_index == 0:
            render_today()
            
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationDestination(icon=ft.icons.CHECK_CIRCLE_OUTLINE, label="今日计划"),
            ft.NavigationDestination(icon=ft.icons.SMART_TOY, label="AI 调控"),
            ft.NavigationDestination(icon=ft.icons.SETTINGS, label="设置"),
        ],
        on_change=on_nav_change
    )
    
    page.add(
        ft.SafeArea(
            ft.Container(
                content=ft.Stack([
                    today_view,
                    ai_view,
                    settings_view
                ]),
                padding=10,
                expand=True
            )
        )
    )
    
    render_today()

ft.app(target=main)
