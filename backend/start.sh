#!/bin/bash

# Anthropic OpenAI Bridge - 后端启动脚本

echo "🚀 Anthropic OpenAI Bridge - 启动后端服务..."

# 确保在 backend 目录
cd "$(dirname "$0")" || { echo "❌ 无法进入脚本所在目录"; exit 1; }

# 检查是否在正确的目录
if [ ! -f "start_proxy.py" ]; then
    echo "❌ 错误: 未找到 start_proxy.py，请确保在 backend 目录运行此脚本"
    echo "   当前目录: $(pwd)"
    exit 1
fi

# 检查 Python 3 是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv || { echo "❌ 虚拟环境创建失败"; exit 1; }
fi

# 激活虚拟环境
source venv/bin/activate || { echo "❌ 无法激活虚拟环境"; exit 1; }

# 升级 pip（可选但推荐）
python -m pip install --upgrade pip -q

# 安装依赖
if [ -f "requirements.txt" ]; then
    echo "📥 安装或更新依赖..."
    pip install -q -r requirements.txt || { echo "❌ 依赖安装失败"; exit 1; }
else
    echo "⚠️  警告: 未找到 requirements.txt，跳过依赖安装"
fi

echo ""
echo "💡 默认启用自动重载（代码变更时自动重启）"
echo "   使用 --no-reload 禁用重载，或设置环境变量 RELOAD=false"
echo "   服务地址: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo "   按 Ctrl+C 停止服务"
echo ""

# 直接将所有参数传递给 Python 启动脚本
exec python start_proxy.py "$@"