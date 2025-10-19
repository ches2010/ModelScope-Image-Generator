#!/bin/bash
echo "===================== 本地一键运行脚本（Mac/Linux） ====================="
# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误：未安装Python 3！请先执行：sudo apt install python3 python3-venv（Ubuntu）或 brew install python3（Mac）"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "虚拟环境创建成功！"
else
    echo "虚拟环境已存在，跳过创建..."
fi

# 激活环境+装依赖
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install requests pillow flask > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "依赖安装失败！请检查网络"
    exit 1
fi

# 提示修改配置
echo "注意：请先打开 app/config.py，修改 MODEL_SCOPE_API_KEY 为你的Key！"
read -p "确认已修改配置？（按Enter继续，Ctrl+C退出）"

# 启动服务
echo "启动成功后，浏览器访问：http://127.0.0.1:5000"
python3 app/app.py
