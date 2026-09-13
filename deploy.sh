#!/usr/bin/env bash
# 智学错题助手 一键部署脚本（适用于 Ubuntu / Debian 云服务器）
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "⚠️  缺少 .env 文件，请先创建（写入你的智谱 API key）："
  echo "      echo 'ZHIPU_API_KEY=你的key' > .env"
  exit 1
fi

echo "==> [1/3] 安装系统依赖"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip

echo "==> [2/3] 创建虚拟环境并安装 Python 依赖"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "==> [3/3] 后台启动 Streamlit"
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > streamlit.log 2>&1 &

sleep 3
IP=$(curl -s ifconfig.me 2>/dev/null || echo "服务器公网IP")
echo ""
echo "✅ 部署完成！访问：http://$IP:8501"
echo "   查看日志：tail -f streamlit.log"
