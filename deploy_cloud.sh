#!/bin/bash
echo "===================== 云服务器一键部署脚本（Ubuntu/CentOS） ====================="
# 检查root权限
if [ "$(id -u)" -ne 0 ]; then
    echo "错误：需用root用户执行！请执行：sudo -i 切换root"
    exit 1
fi

# 安装依赖（Ubuntu/CentOS适配）
if command -v apt &> /dev/null; then
    echo "1. 检测到Ubuntu系统，安装依赖..."
    apt update -y > /dev/null
    apt install -y python3 python3-venv python3-pip git > /dev/null
elif command -v yum &> /dev/null; then
    echo "1. 检测到CentOS系统，安装依赖..."
    yum install -y python3 python3-venv python3-pip git > /dev/null
else
    echo "错误：不支持当前系统（仅支持Ubuntu/CentOS）"
    exit 1
fi

# 克隆仓库（用户需替换自己的GitHub仓库地址）
echo "2. 克隆项目仓库..."
git clone https://github.com/your-username/ModelScope-Image-Generator.git > /dev/null 2>&1
cd ModelScope-Image-Generator || exit 1

# 创建虚拟环境+装依赖
echo "3. 配置Python环境..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install requests pillow flask gunicorn > /dev/null 2>&1  # 云服务器用gunicorn启动，更稳定

# 提示修改配置
echo "4. 请修改配置文件（API Key+保存路径）..."
read -p "按Enter打开config.py编辑（编辑完保存退出即可）"
vi app/config.py

# 启动服务（后台运行，断开SSH不停止）
echo "5. 启动服务（后台运行，端口：5000）..."
nohup gunicorn -b 0.0.0.0:5000 --chdir app app:app > run.log 2>&1 &

# 开放端口（云服务器需开放5000端口，否则前端无法访问）
echo "6. 开放5000端口（防火墙配置）..."
if command -v ufw &> /dev/null; then
    ufw allow 5000 > /dev/null
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=5000/tcp > /dev/null
    firewall-cmd --reload > /dev/null
fi

echo "===================== 部署成功！ ====================="
echo "1. 日志查看：cd ModelScope-Image-Generator && tail -f run.log"
echo "2. 前端访问：浏览器输入 云服务器IP:5000（如：http://1.2.3.4:5000）"
echo "3. 停止服务：ps -ef | grep gunicorn | grep -v grep | awk '{print $2}' | xargs kill"
