#!/bin/bash

# Anthropic OpenAI Bridge - 前端启动脚本

# 确保在 frontend 目录
cd "$(dirname "$0")" || { echo "❌ 无法进入脚本目录"; exit 1; }

if [ ! -f "package.json" ]; then
    echo "❌ 错误: 未找到 package.json，请确保在 frontend 目录运行此脚本"
    exit 1
fi

echo "🚀 Anthropic OpenAI Bridge - 启动前端开发服务器..."
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未安装 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "📦 Node.js 版本: $(node --version)"
echo "📦 npm 版本: $(npm --version)"
echo ""

# 检查依赖
NEED_INSTALL=false
if [ ! -d "node_modules" ]; then
    NEED_INSTALL=true
elif [ ! -f "node_modules/.bin/vite" ]; then
    echo "⚠️  依赖不完整，将重新安装..."
    NEED_INSTALL=true
fi

if [ "$NEED_INSTALL" = true ]; then
    echo "🛠️  安装依赖..."
    if grep -q "patch-package" package.json; then
        echo "📦 预安装 patch-package..."
        npm install --no-save patch-package &>/dev/null || true
    fi

    if ! npm install; then
        echo "⚠️  尝试使用 --legacy-peer-deps..."
        if ! npm install --legacy-peer-deps; then
            echo "❌ 依赖安装失败"
            echo "💡 建议: rm -rf node_modules package-lock.json && npm install"
            exit 1
        fi
    fi
    echo ""
fi

if [ ! -f "node_modules/.bin/vite" ]; then
    echo "❌ vite 未安装成功"
    exit 1
fi

# 生成 SvelteKit 配置
if [ ! -d ".svelte-kit" ] || [ ! -f ".svelte-kit/tsconfig.json" ]; then
    echo "📝 生成 SvelteKit 配置..."
    npx svelte-kit sync &>/dev/null || true
fi

# 解析参数（支持 --polling）
VITE_ARGS=()
USE_POLLING=false

for arg in "$@"; do
    if [[ "$arg" == "--polling" ]]; then
        USE_POLLING=true
    else
        VITE_ARGS+=("$arg")
    fi
done

# 确定是否启用轮询：环境变量 > CLI 参数 > 自动检测
if [ -n "${VITE_USE_POLLING}" ]; then
    USE_POLLING="${VITE_USE_POLLING}"
elif [ "$USE_POLLING" = false ] && [ "$(uname)" = "Linux" ]; then
    # 自动为 Linux 启用轮询（兼容 WSL/Docker）
    USE_POLLING=true
    echo "ℹ️  自动启用轮询模式（Linux 环境）"
fi

# 设置环境变量给 Vite
if [ "$USE_POLLING" = true ]; then
    export VITE_USE_POLLING=true
    export CHOKIDAR_USEPOLLING=true  # 兼容旧工具
fi

# 启动信息
echo "🌐 启动前端开发服务器..."
echo "📖 代理后端: http://localhost:8000"
echo "🔄 HMR (热重载): 已启用"
if [ "$USE_POLLING" = true ]; then
    echo "📡 文件监听: 轮询模式 (Polling) — 兼容 WSL/Docker"
else
    echo "📡 文件监听: 原生模式 (Native)"
fi
echo "💡 按 Ctrl+C 停止服务"
echo ""

echo "🔧 接收到的原始参数: $*"
echo "🔧 传递给 Vite 的参数: ${VITE_ARGS[*]}"

# 启动 Vite
npx vite dev "${VITE_ARGS[@]}"