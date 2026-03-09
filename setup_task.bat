@echo off
chcp 65001 >nul
echo ==============================================
echo 考研看板 - 开机自启服务安装
echo ==============================================
echo 正在为你创建开机隐蔽自启任务...
set VBS_PATH=%~dp0run_hidden.vbs
schtasks /create /tn "StudySchedulerStartup" /tr "wscript.exe \"%VBS_PATH%\"" /sc onlogon /f
if %errorlevel% equ 0 (
    echo.
    echo ✅ 成功！以后每次开机，系统都会静默检查今天是否有课表。
    echo 缺失时会自动调用 DeepSeek 补全并推送到你微信！
) else (
    echo.
    echo ❌ 失败！请关闭当前窗口，然后【右键点击此文件 - 选择'以管理员身份运行'】！
)
pause
