@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🚀 启动应用
echo ========================================
echo.
echo 正在启动，请稍候...
echo.

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM 启动应用（会自动处理 Docker 和 Piston）
python app.py

pause
