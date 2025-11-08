#!/bin/bash

# Anthropic OpenAI Bridge - 后端启动脚本

echo "🚀 Anthropic OpenAI Bridge - 启动后端服务..."

# 确保在 backend 目录
cd "$(dirname "$0")"

# 检查是否在正确的目录
if [ ! -f "start_proxy.py" ]; then
    echo "❌ 错误: 未找到 start_proxy.py，请确保在 backend 目录运行此脚本"
    exit 1
fi

# 检查Python版本
python3 --version

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -q -r requirements.txt

# 启动后端服务
echo "🌐 后端服务将在 http://localhost:8000 启动"
echo "📖 API文档: http://localhost:8000/docs"
echo "💡 按 Ctrl+C 停止服务"
echo ""

python start_proxy.py "$@"

