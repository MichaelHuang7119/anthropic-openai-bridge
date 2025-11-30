#!/bin/bash

# Anthropic OpenAI Bridge - 统一开发启动脚本
# 支持前后端同时启动并启用热重载

set -e

echo "🚀 Anthropic OpenAI Bridge - 统一开发启动脚本"
echo ""

# 函数：检查端口是否可用
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
            return 1  # 端口被占用
        else
            return 0  # 端口可用
        fi
    else
        # fallback for systems without lsof
        if nc -z localhost $port; then
            return 1  # 端口被占用
        else
            return 0  # 端口可用
        fi
    fi
}

# 检查并设置端口
if ! check_port 8000; then
    echo "⚠️  警告: 端口 8000 已被占用，可能后端已在运行"
else
    echo "✅ 端口 8000 可用 (后端)"
fi

if ! check_port 5173; then
    echo "⚠️  警告: 端口 5173 已被占用，可能前端已在运行"
else
    echo "✅ 端口 5173 可用 (前端)"
fi

echo ""
echo "🔧 启用热重载配置..."
export VITE_USE_POLLING=true
export RELOAD=true
export WATCHFILES_FORCE_POLLING=1

# 启动后端
echo "🌐 启动后端服务 (端口 8000)..."
cd "$(dirname "$0")/backend"
if [ ! -f "start.sh" ]; then
    echo "❌ 错误: 未找到后端启动脚本"
    exit 1
fi

# 在后台启动后端
./start.sh --reload &
BACKEND_PID=$!

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 3

# 检查后端是否启动成功
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "✅ 后端服务启动成功 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务启动失败"
    exit 1
fi

# 启动前端
echo ""
echo "📱 启动前端开发服务器 (端口 5173)..."
cd "../frontend"
if [ ! -f "start.sh" ]; then
    echo "❌ 错误: 未找到前端启动脚本"
    exit 1
fi

echo "💡 提示: 按 Ctrl+C 退出整个应用"
echo ""

# 启动前端（前台运行，以便查看日志）
./start.sh

# 捕获 Ctrl+C 信号，优雅关闭后端
cleanup() {
    echo ""
    echo "🛑 正在关闭服务..."
    kill $BACKEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    echo "👋 服务已关闭"
    exit 0
}

trap cleanup INT

# 等待后台进程
wait $BACKEND_PID