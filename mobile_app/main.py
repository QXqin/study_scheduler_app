import traceback as _tb
import flet as ft
import threading

_import_error = None
try:
    from datetime import datetime
    import json
    import os
    import yaml
    from core.ai_updater import update_config_with_nl
    from core.scheduler import generate_schedule, send_to_pushplus
    from core.import_ics import parse_ics_text
except Exception as _e:
    _import_error = f"{_e}\n\n{_tb.format_exc()}"


class AppStorage:
    def __init__(self):
        storage_dir = os.getenv("FLET_APP_STORAGE_DATA", ".")
        self._path = os.path.join(storage_dir, "app_data.json")
        self._data = {}
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
        except Exception:
            self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def main(page: ft.Page):
    if _import_error:
        page.add(
            ft.SafeArea(
                ft.Column(
                    [
                        ft.Text("IMPORT ERROR", color="red", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(_import_error, size=12, selectable=True),
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                )
            )
        )
        page.update()
        return

    try:
        page.title = "考研智能看板"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 400
        page.window_height = 800

        storage = AppStorage()

        is_onboarded = storage.get("is_onboarded") or False

        api_key = storage.get("api_key") or ""
        push_token = storage.get("push_token") or ""
        custom_prompt = storage.get("custom_prompt") or ""
        config_yaml_str = storage.get("config_yaml") or "api:\nuser_info:\nfixed_classes: []\npreferences: []\ntemp_tasks: []\n"
        schedule_data = storage.get("schedule_json") or {}
        progress_data = storage.get("progress_json") or {}

        def save_progress():
            storage.set("progress_json", progress_data)

        def save_config(yaml_str):
            nonlocal config_yaml_str
            config_yaml_str = yaml_str
            storage.set("config_yaml", yaml_str)

        def save_schedule(sd):
            nonlocal schedule_data
            schedule_data = sd
            storage.set("schedule_json", sd)

        # -----------------------------------------------------
        # MAIN APP VIEWS
        # -----------------------------------------------------

        today_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, visible=True)

        def render_today():
            today_view.controls.clear()
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_view.controls.append(ft.Text(f"今日计划 ({today_str})", size=24, weight=ft.FontWeight.BOLD))
            today_view.controls.append(ft.Divider())

            today_tasks = schedule_data.get(today_str, [])
            if not today_tasks:
                today_view.controls.append(ft.Text("今天没有排期任务，请到调控中心生成。", color=ft.Colors.GREY_600))
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

        ai_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, visible=False)
        ai_prompt_field = ft.TextField(label="告诉 AI 你的安排修改...", multiline=True, min_lines=3, max_lines=5)
        ai_status = ft.Text("", color=ft.Colors.RED_500)
        ai_progress = ft.ProgressRing(visible=False)
        ai_submit_btn = ft.ElevatedButton("✨ 提交给 AI", disabled=False)

        def run_ai_task(user_input, is_first_time=False):
            try:
                ak = storage.get("api_key")
                pt = storage.get("push_token")
                cp = storage.get("custom_prompt") or ""
                
                if not is_first_time:
                    success, new_yaml_str = update_config_with_nl(ak, config_yaml_str, user_input)
                    if not success:
                        ai_status.value = new_yaml_str
                        ai_status.color = ft.Colors.RED_500
                        return
                    save_config(new_yaml_str)
                    if not is_first_time:
                        ai_status.value = "配置已更新，正在生成排期..."
                        page.update()

                cfg = yaml.safe_load(config_yaml_str)
                success2, sd, md_str = generate_schedule(cfg, ak, custom_prompt=cp)

                if success2:
                    save_schedule(sd)
                    if not is_first_time:
                        ai_status.value = "生成成功！正在推送..."
                        page.update()

                    if pt:
                        ok, msg = send_to_pushplus(pt, md_str)
                        if not is_first_time:
                            if ok:
                                ai_status.value = "✅ 排表已生成并推送微信！"
                                ai_status.color = ft.Colors.GREEN_500
                            else:
                                ai_status.value = f"✅ 生成完毕 (推送失败: {msg})"
                                ai_status.color = ft.Colors.ORANGE_500
                    else:
                        if not is_first_time:
                            ai_status.value = "✅ 全新排表生成完毕！"
                            ai_status.color = ft.Colors.GREEN_500
                else:
                    if not is_first_time:
                        ai_status.value = f"生成失败: {md_str}"
                        ai_status.color = ft.Colors.RED_500
            except Exception as e:
                if not is_first_time:
                    ai_status.value = f"发生系统错误: {e}"
                    ai_status.color = ft.Colors.RED_500
            finally:
                if is_first_time:
                    page.controls.clear()
                    page.navigation_bar = main_nav_bar
                    page.add(main_app_container)
                    render_today()
                else:
                    ai_progress.visible = False
                    ai_submit_btn.disabled = False
                    render_today()
                page.update()

        def on_ai_submit(e):
            if not ai_prompt_field.value:
                ai_status.value = "请输入内容"
                page.update()
                return

            if not storage.get("api_key"):
                ai_status.value = "未配置 API Key"
                page.update()
                return

            ai_status.value = "AI 正在思考中，请勿关闭应用..."
            ai_status.color = ft.Colors.BLUE_500
            ai_progress.visible = True
            ai_submit_btn.disabled = True
            page.update()

            t = threading.Thread(target=run_ai_task, args=(ai_prompt_field.value, False))
            t.start()

        ai_submit_btn.on_click = on_ai_submit

        ai_view.controls.extend([
            ft.Text("🤖 AI 日程调控", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ai_prompt_field,
            ft.Row([ai_submit_btn]),
            ft.Row([ai_progress, ai_status], wrap=True)
        ])

        # 3. 应用设置 View
        settings_view = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, visible=False)
        set_api_field = ft.TextField(label="DeepSeek API Key", value=api_key, password=True, can_reveal_password=True)
        set_push_field = ft.TextField(label="Pushplus Token", value=push_token, password=True, can_reveal_password=True)
        set_custom_prompt = ft.TextField(label="AI 排单专属提示词（例如：我绝不在早上背英语）", value=custom_prompt, multiline=True, min_lines=2, max_lines=4)

        def save_settings(e):
            storage.set("api_key", set_api_field.value)
            storage.set("push_token", set_push_field.value)
            storage.set("custom_prompt", set_custom_prompt.value)
            page.snack_bar = ft.SnackBar(ft.Text("设置已保存！"), open=True)
            page.update()

        def import_ics_result_settings(e: ft.FilePickerResultEvent):
            if e.files and len(e.files):
                file_path = e.files[0].path
                if file_path:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            ics_text = f.read()
                        classes = parse_ics_text(ics_text)
                        
                        cfg = yaml.safe_load(config_yaml_str) or {}
                        cfg['fixed_classes'] = classes
                        save_config(yaml.dump(cfg, allow_unicode=True, sort_keys=False))
                        
                        page.snack_bar = ft.SnackBar(ft.Text(f"成功导入 {len(classes)} 节课程！"), open=True)
                        page.update()
                    except Exception as ex:
                        page.snack_bar = ft.SnackBar(ft.Text(f"导入失败: {ex}"), open=True)
                        page.update()

        sett_file_picker = ft.FilePicker(on_result=import_ics_result_settings)
        page.overlay.append(sett_file_picker)

        settings_view.controls.extend([
            ft.Text("⚙️ 应用设置", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            set_api_field,
            set_push_field,
            set_custom_prompt,
            ft.ElevatedButton("保存设置", on_click=save_settings, icon=ft.Icons.SAVE),
            ft.Divider(),
            ft.Text("导入 .ics 课表会覆盖当前的固定课", color=ft.Colors.GREY_600),
            ft.ElevatedButton("重新导入课表", on_click=lambda _: sett_file_picker.pick_files(allowed_extensions=["ics"]), icon=ft.Icons.UPLOAD_FILE)
        ])

        # --- NAVIGATION ---
        def on_nav_change(e):
            today_view.visible = e.control.selected_index == 0
            ai_view.visible = e.control.selected_index == 1
            settings_view.visible = e.control.selected_index == 2
            if e.control.selected_index == 0:
                render_today()
            page.update()

        main_nav_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.CHECK_CIRCLE_OUTLINE, label="今日"),
                ft.NavigationBarDestination(icon=ft.Icons.SMART_TOY, label="调控"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="设置"),
            ],
            on_change=on_nav_change
        )

        main_app_container = ft.SafeArea(
            ft.Container(
                content=ft.Stack([today_view, ai_view, settings_view]),
                padding=10,
                expand=True
            )
        )

        # -----------------------------------------------------
        # ONBOARDING WIZARD & LOADING VIEWS
        # -----------------------------------------------------

        wizard_container = ft.Column(expand=True, alignment=ft.MainAxisAlignment.CENTER)
        
        wiz_api = ft.TextField(label="DeepSeek API Key (必填)", password=True, can_reveal_password=True)
        wiz_push = ft.TextField(label="Pushplus Token (选填)", password=True, can_reveal_password=True)
        wiz_status = ft.Text("", color=ft.Colors.RED_500)
        wiz_ics_status = ft.Text("尚未导入", color=ft.Colors.GREY_500)
        
        # Loading Page
        loading_view = ft.SafeArea(
            ft.Column(
                [
                    ft.ProgressRing(),
                    ft.Text("AI 正在为您首次初始化智能课表...", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("由于需要深度分析您的偏好和课表，这可能需要几十秒时间，请勿关闭应用。", color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True
            )
        )
        
        def finish_onboarding(e):
            if not wiz_api.value:
                wiz_status.value = "必须填写 API Key 才能使用 AI 排期功能"
                page.update()
                return
                
            storage.set("api_key", wiz_api.value)
            storage.set("push_token", wiz_push.value)
            storage.set("custom_prompt", "")
            storage.set("is_onboarded", True)
            
            page.controls.clear()
            page.add(loading_view)
            page.update()
            
            t = threading.Thread(target=run_ai_task, args=("首次生成排期", True))
            t.start()
            

        def import_ics_result_wiz(e: ft.FilePickerResultEvent):
            if e.files and len(e.files):
                file_path = e.files[0].path
                if file_path:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            ics_text = f.read()
                        classes = parse_ics_text(ics_text)
                        
                        cfg = yaml.safe_load(config_yaml_str) or {}
                        cfg['fixed_classes'] = classes
                        save_config(yaml.dump(cfg, allow_unicode=True, sort_keys=False))
                        
                        wiz_ics_status.value = f"✅ 已成功导入 {len(classes)} 节课程"
                        wiz_ics_status.color=ft.Colors.GREEN_500
                        page.update()
                    except Exception as ex:
                        wiz_ics_status.value = f"❌ 导入失败: {ex}"
                        wiz_ics_status.color = ft.Colors.RED_500
                        page.update()

        wiz_file_picker = ft.FilePicker(on_result=import_ics_result_wiz)
        page.overlay.append(wiz_file_picker)

        step1 = ft.Column([
            ft.Text("欢迎使用考研智能看板", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("为了让 AI 为您自动安排日程，我们需要初始化一些基础配置。", color=ft.Colors.GREY_700),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            wiz_api,
            wiz_push,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("固定的大学课表 (选填)：", weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.ElevatedButton("导入 .ics 文件", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: wiz_file_picker.pick_files(allowed_extensions=["ics"])),
                wiz_ics_status
            ]),
            ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
            wiz_status,
            ft.ElevatedButton("完成初始化 ->", on_click=finish_onboarding, width=400, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE))
        ], alignment=ft.MainAxisAlignment.CENTER)

        wizard_container.controls.append(step1)


        # -----------------------------------------------------
        # APP ENTRY LOGIC
        # -----------------------------------------------------

        if is_onboarded:
            page.navigation_bar = main_nav_bar
            page.add(main_app_container)
            render_today()
        else:
            page.add(ft.SafeArea(wizard_container))
            
    except Exception as e:
        page.add(
            ft.SafeArea(
                ft.Column([
                    ft.Text("FATAL ERROR ON STARTUP", color="red", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e), color="red"),
                    ft.Text(_tb.format_exc(), size=12, selectable=True)
                ], scroll=ft.ScrollMode.AUTO, expand=True)
            )
        )
        page.update()

ft.app(target=main)
