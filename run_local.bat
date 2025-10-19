@echo off
chcp 65001 >nul
echo ===================== 本地一键运行脚本（Windows） =====================
echo 1. 检查Python是否安装...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未安装Python！请先安装Python 3.7+（https://www.python.org/downloads/）
    pause
    exit /b 1
)

echo 2. 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo 虚拟环境创建成功！
) else (
    echo 虚拟环境已存在，跳过创建...
)

echo 3. 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul
pip install requests pillow flask >nul 2>&1
if errorlevel 1 (
    echo 依赖安装失败！请检查网络后重试
    pause
    exit /b 1
)

echo 4. 提示修改API Key和保存路径...
echo 注意：请先打开 app/config.py，修改 MODEL_SCOPE_API_KEY 为你的Key！
echo （可选）如需修改图片保存路径，也在 config.py 中修改 IMAGE_SAVE_PATH
pause

echo 5. 启动服务...
echo 启动成功后，浏览器访问：http://127.0.0.1:5000
python app/app.py

pause
