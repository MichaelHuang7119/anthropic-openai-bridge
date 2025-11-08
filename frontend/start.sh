#!/bin/bash

# Anthropic OpenAI Bridge - 前端启动脚本

# 确保在 frontend 目录
cd "$(dirname "$0")"

if [ ! -f "package.json" ]; then
    echo "❌ 错误: 未找到 package.json，请确保在 frontend 目录运行此脚本"
    exit 1
fi

echo "🚀 Anthropic OpenAI Bridge - 启动前端开发服务器..."
echo ""

# 检查Node.js版本
if ! command -v node &> /dev/null; then
    echo "❌ 未安装 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "📦 Node.js 版本: $(node --version)"
echo "📦 npm 版本: $(npm --version)"
echo ""

# 检查是否需要安装依赖
NEED_INSTALL=false
if [ ! -d "node_modules" ]; then
    NEED_INSTALL=true
elif [ ! -f "node_modules/.bin/vite" ]; then
    echo "⚠️  检测到依赖不完整，重新安装..."
    NEED_INSTALL=true
fi

# 安装依赖
if [ "$NEED_INSTALL" = true ]; then
    echo "🛠️  安装依赖..."
    
    # 如果 package.json 中有 patch-package，先单独安装它
    # 这样可以确保 postinstall 脚本运行时 patch-package 已经可用
    if grep -q "patch-package" package.json; then
        echo "📦 先安装 patch-package（某些包的 postinstall 脚本需要）..."
        npm install --no-save patch-package || true
    fi
    
    # 先尝试正常安装
    if ! npm install; then
        echo "⚠️  首次安装失败，尝试使用 --legacy-peer-deps..."
        # 如果失败，尝试使用 --legacy-peer-deps（处理 peer dependency 冲突）
        if ! npm install --legacy-peer-deps; then
            echo "❌ 依赖安装失败，请检查错误信息"
            echo "💡 建议: 删除 node_modules 和 package-lock.json 后重试"
            echo "   rm -rf node_modules package-lock.json"
            echo "   npm install"
            exit 1
        fi
    fi
    echo ""
fi

# 验证关键依赖是否安装成功
if [ ! -f "node_modules/.bin/vite" ]; then
    echo "❌ 错误: vite 未正确安装，请尝试删除 node_modules 后重新运行"
    exit 1
fi

# 运行 svelte-kit sync 生成必要的配置文件（解决 tsconfig.json 警告）
if [ ! -d ".svelte-kit" ] || [ ! -f ".svelte-kit/tsconfig.json" ]; then
    echo "📝 生成 SvelteKit 配置文件..."
    if [ -f "node_modules/.bin/svelte-kit" ]; then
        npx svelte-kit sync > /dev/null 2>&1 || true
    fi
fi

# 启动开发服务器
# 注意：vite 的参数格式是 --port 5175，不需要额外的 --
echo "🌐 前端开发服务器启动中..."
if [ $# -gt 0 ]; then
    echo "📌 使用参数: $*"
fi
echo "📖 API代理到: http://localhost:8000"
echo "💡 按 Ctrl+C 停止服务"
echo ""

# 检查是否存在vite.config.ts
if [ ! -f "vite.config.ts" ]; then
    echo "⚠️  警告: 未找到 vite.config.ts，可能需要先配置"
fi

# 直接调用 vite，传递所有参数
# 使用 npx 确保使用本地安装的 vite
npx vite dev "$@"

