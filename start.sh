#!/bin/bash

# Anthropic OpenAI Bridge - 统一启动脚本
# 使用 --dev 启用热重载，不使用则使用生产模式

set -e

# 函数：加载.env文件（支持.env和.env.example，优先级：.env > .env.example）
load_env() {
    local env_dir="$(dirname "$0")"
    local env_example="$env_dir/.env.example"
    local env_file="$env_dir/.env"

    # 先加载.env.example（作为默认值）
    if [ -f "$env_example" ]; then
        echo "📄 加载默认环境变量: $env_example"
        # 读取.env.example文件，导出环境变量
        set -a  # 自动导出变量
        source "$env_example"
        set +a
    fi

    # 再加载.env（覆盖.env.example中的值）
    if [ -f "$env_file" ]; then
        echo "📄 加载自定义环境变量: $env_file"
        # 读取.env文件，导出环境变量
        set -a  # 自动导出变量
        source "$env_file"
        set +a
    fi
}

# 加载环境变量
load_env

# 检查是否包含 --dev 参数
DEV_MODE=false
for arg in "$@"; do
    if [[ "$arg" == "--dev" ]]; then
        DEV_MODE=true
        break
    fi
done

echo "🚀 Anthropic OpenAI Bridge - 统一启动脚本"
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
        if nc -z localhost $port 2>/dev/null; then
            return 1  # 端口被占用
        else
            return 0  # 端口可用
        fi
    fi
}

# 函数：查找可用端口（只输出端口号到stdout）
find_available_port() {
    local start_port=$1
    local max_attempts=${2:-10}
    local port=$start_port

    for ((i=0; i<max_attempts; i++)); do
        if check_port $port; then
            if [ $i -gt 0 ]; then
                echo "✅ 端口 $port 可用（已尝试 $i 个端口）" >&2
            fi
            # 只输出端口号到stdout
            echo "$port"
            return 0
        fi

        if [ $i -eq 0 ]; then
            echo "⚠️  端口 $port 被占用，正在查找可用端口..." >&2
        fi
        ((port++))
    done

    echo "❌ 无法找到可用端口（已尝试 $max_attempts 个端口）" >&2
    return 1
}

# 检查并设置端口
echo "🔍 检查端口占用情况..."
BACKEND_PORT=$(find_available_port 8000 10)
if [ -z "$BACKEND_PORT" ] || ! [[ "$BACKEND_PORT" =~ ^[0-9]+$ ]]; then
    echo "❌ 无法找到可用的后端端口"
    exit 1
fi

# 使用环境变量中的EXPOSE_PORT（默认值5173）
FRONTEND_PORT=$(find_available_port 5173 10)
if [ -z "$FRONTEND_PORT" ] || ! [[ "$FRONTEND_PORT" =~ ^[0-9]+$ ]]; then
    echo "❌ 无法找到可用的前端端口"
    exit 1
fi

# 导出端口环境变量，供子脚本使用
export BACKEND_PORT
export EXPOSE_PORT=$FRONTEND_PORT

echo ""
echo "📌 最终端口配置:"
echo "   后端: $BACKEND_PORT"
echo "   前端: $FRONTEND_PORT"

echo ""
if [ "$DEV_MODE" = true ]; then
    echo "🔧 开发模式 - 启用热重载 + DEBUG 日志"
    echo "   日志级别: DEBUG (详细日志)"
    export VITE_USE_POLLING=true
    export RELOAD=true
    export WATCHFILES_FORCE_POLLING=1
else
    echo "🔧 生产模式 - 禁用热重载 + INFO 日志"
    echo "   日志级别: INFO (仅重要信息)"
    export RELOAD=false
fi

# 启动后端
echo "🌐 启动后端服务 (端口 $BACKEND_PORT)..."
cd "$(dirname "$0")/backend"
if [ ! -f "start.sh" ]; then
    echo "❌ 错误: 未找到后端启动脚本"
    exit 1
fi

# 在后台启动后端（根据DEV_MODE决定是否传递--reload）
if [ "$DEV_MODE" = true ]; then
    ./start.sh --dev &
else
    ./start.sh &
fi
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
echo "📱 启动前端服务器 (端口 5173)..."
cd "../frontend"
if [ ! -f "start.sh" ]; then
    echo "❌ 错误: 未找到前端启动脚本"
    exit 1
fi

echo "💡 提示: 按 Ctrl+C 退出整个应用"
echo ""

# 启动前端（前台运行，根据DEV_MODE决定是否启用热重载）
if [ "$DEV_MODE" = true ]; then
    ./start.sh --dev
else
    ./start.sh
fi

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