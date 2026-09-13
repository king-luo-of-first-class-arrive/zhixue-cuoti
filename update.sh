#!/usr/bin/env bash
# 智学错题助手 一键更新脚本：拉取最新代码 + 更新依赖 + 重启服务
set -e
cd "$(dirname "$0")"

echo "==> [1/3] 拉取最新代码"
git pull

echo "==> [2/3] 更新依赖"
source .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

echo "==> [3/3] 重启服务"
pkill -f "streamlit run app.py" 2>/dev/null && echo "已停止旧进程" || echo "无旧进程在运行"
sleep 1
export PYTHONUTF8=1   # 服务器 locale 常为 C/ASCII，不强制 UTF-8 会导致中文报 'ascii' codec 编码错误
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > streamlit.log 2>&1 &

sleep 3
echo "✅ 更新完成，访问 http://47.236.12.145:8501"
echo "--- 最近日志 ---"
tail -6 streamlit.log
