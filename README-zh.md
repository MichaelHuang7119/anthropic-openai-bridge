# Anthropic OpenAI Bridge

[![CI/CD Status](https://github.com/michaelhuang7119/anthropic-openai-bridge/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/michaelhuang7119/anthropic-openai-bridge/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Svelte 5](https://img.shields.io/badge/Svelte-5-orange.svg)](https://svelte.dev/)

> 🌐 **English Documentation** | [English Quick Guide](./README.md) • [English Technical Docs](./docs/README-COMPLETE.md)

一个基于 FastAPI 和 Svelte 5 的高性能 AI 模型代理服务，支持多供应商配置和管理。

## ✨ 项目简介

Anthropic OpenAI Bridge 是一个企业级 API 代理服务，它实现了 Anthropic 兼容的 API 端点，并将请求转发到支持 OpenAI 兼容接口的后端供应商（如通义千问、ModelScope、AI Ping、Anthropic 等）。通过统一的 API 接口，您可以轻松切换不同的 AI 模型供应商，而无需修改客户端代码。

## 🚀 核心功能

- **🔥 高性能架构** - 异步数据库 + 连接池，HTTP 连接池优化，支持 10k QPS
- **🛡️ 企业级安全** - JWT 密钥管理、数据加密存储、强密码策略
- **🌍 国际化支持** - 16种语言支持（中文、英文、日文、韩文等）
- **🌐 现代管理界面** - Svelte 5 + TypeScript，PWA 支持，深色/浅色主题
- **🔧 智能管理** - OpenTelemetry 集成，健康监控，自动故障转移，熔断器模式
- **📊 运营监控** - 性能统计，Token 使用追踪，实时日志
- **💬 对话管理** - 历史对话记录，多对话支持，Token 用量统计
- **🏢 多供应商支持** - 统一 API 接口，智能模型映射，供应商 Token 限制

## 🏃‍♂️ 快速开始

### 环境要求

- **Python 3.9+** (推荐 3.11+)
- **Node.js 18+** (推荐 20+)
- **npm/pnpm/yarn** (推荐 pnpm)
- **Docker & Docker Compose** (可选，用于容器化部署)

### 🚀 一键部署（推荐）

#### Docker Compose 方式

```bash
# 克隆项目
git clone <your-repo-url>
cd anthropic-openai-bridge

# 启动所有服务（后端 + 前端）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f frontend
docker-compose logs -f backend
```

服务启动后：

- **前端管理界面**: http://localhost:5173
- **API 文档**: http://localhost:8000/docs

#### 本地开发方式

**1. 启动后端服务**

```bash
cd backend
bash start.sh
```

**2. 启动前端服务（新终端）**

```bash
cd frontend
pnpm install  # 首次运行需要安装依赖
pnpm dev
# 或指定端口
pnpm dev -- --port 5175
```

### 🔑 首次登录

1. 访问前端管理界面：http://localhost:5173
2. 系统会自动跳转到登录页面
3. 使用默认管理员账号登录：
   - **邮箱**：`admin@example.com`
   - **密码**：`admin123`

> **重要**：首次登录后请立即修改密码！生产环境需要设置强密码。

### ⚙️ 配置必需环境变量

**生产环境必须设置以下环境变量**：

```bash
# 必需 - JWT 密钥
export JWT_SECRET_KEY="your-strong-secret-key-here"

# 推荐 - 加密密钥（用于敏感数据加密）
export ENCRYPTION_KEY="your-fernet-encryption-key-here"

# 推荐 - 管理员密码（至少 12 字符）
export ADMIN_PASSWORD="your-secure-password"

# 性能优化 - 数据库连接池
export DB_POOL_SIZE=20
export DB_POOL_TIMEOUT=30.0

# 可选 - 监控配置
export ENABLE_TELEMETRY=true
export OTLP_ENDPOINT=http://jaeger:4318
```

### 🏢 配置 AI 供应商

**启动前必须先配置供应商信息！**

编辑 `backend/provider.json` 文件：

```json
{
  "providers": [
    {
      "name": "qwen",
      "enabled": true,
      "priority": 1,
      "api_key": "${QWEN_API_KEY}",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "timeout": 60,
      "max_retries": 1,
      "models": {
        "big": ["qwen-plus", "qwen-max"],
        "middle": ["qwen-turbo"],
        "small": ["qwen-plus"]
      }
    },
    {
      "name": "anthropic-direct",
      "enabled": true,
      "priority": 2,
      "api_key": "${ANTHROPIC_API_KEY}",
      "base_url": "https://api.anthropic.com",
      "api_format": "anthropic",
      "timeout": 60,
      "max_retries": 1,
      "models": {
        "big": ["claude-3-opus-20240229"],
        "middle": ["claude-3-sonnet-20240229"],
        "small": ["claude-3-haiku-20240307"]
      }
    }
  ],
  "fallback_strategy": "priority",
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 60
  }
}
```

### 🔑 配置 Claude Code

1. **创建 API Key**：
   - 登录管理界面
   - 访问"API Key 管理"页面
   - 点击"创建 API Key"
   - 填写名称和邮箱（可选）
   - 复制生成的 API Key（**注意：创建后无法再次查看完整 Key**）

2. **配置 Claude Code 环境变量**：

```bash
ANTHROPIC_BASE_URL=http://localhost:5175
ANTHROPIC_API_KEY="sk-xxxxxxxxxxxxx"  # 使用创建的 API Key
```

## 📚 API 使用示例

### 基础消息请求

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "你好！"}],
    "max_tokens": 100
  }'
```

### 流式请求

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{"role": "user", "content": "给我讲个故事"}],
    "max_tokens": 200,
    "stream": true
  }'
```

### 工具调用（Function Calling）

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "opus",
    "messages": [{"role": "user", "content": "北京今天天气怎么样？"}],
    "max_tokens": 200,
    "tools": [{
      "name": "get_weather",
      "description": "获取指定城市的天气信息",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "城市名称"
          }
        },
        "required": ["location"]
      }
    }]
  }'
```

## 📊 监控和统计

### 查看健康状态

```bash
curl http://localhost:8000/health
```

### 获取 Token 使用统计

```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/token-usage
```

### 查看请求日志

```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/requests
```

## 🌐 更多信息

### 📚 开发资源
- 🔧 **[开发指南](docs/DEVELOPMENT-zh.md)** - 详细的开发指南、架构说明、API 文档
- 📖 **[完整技术文档](docs/README-COMPLETE-zh.md)** - 完整技术文档

### 🌐 API 与演示
- 🔗 **[交互式 API 文档](http://localhost:8000/docs)** - 完整的交互式 API 文档
- 🎮 **在线演示** - (待添加)

### 🐛 支持与问题反馈
- 📝 **[问题反馈](https://github.com/michaelhuang7119/anthropic-openai-bridge/issues)** - 报告问题和功能请求

### 🇺🇸 英文资源
- 📄 **[English Quick Guide](README.md)** - 英文版说明文档
- 📘 **[English Technical Docs](docs/README-COMPLETE.md)** - 完整英文技术文档

## 📝 更新日志

### v1.6.0 (2025-11-29) - 国际化与用户体验全面提升

- **新增 16 种语言支持**：中文、English、日本語、한국어、Français、Español、Deutsch、Русский、Português、Italiano、Nederlands、العربية、हिन्दी、ไทย、Tiếng Việt、Bahasa Indonesia
- **智能语言切换**：支持顶部导航栏一键切换语言，自动记忆用户偏好
- **全面本地化**：所有页面、表单、按钮、提示信息、Toast 消息完整翻译
- **修复聊天时间戳**：解决 "Invalid Date" 问题，支持多种时间格式
- **Svelte 5 升级**：全面升级到 Svelte 5 语法，使用 `$state()` 和 `$derived()` 等新特性

## 🤝 贡献

我们欢迎所有形式的贡献！请阅读 **[📘 开发指南](docs/DEVELOPMENT-zh.md)** 中的"**贡献指南**"章节了解详细信息。

## 💖 支持项目

如果这个项目对你有帮助，欢迎通过以下方式支持我们的开发工作！

您的支持将帮助我们：
- 🚀 持续开发和优化功能
- 🐛 快速修复问题
- 📚 完善文档和示例
- 🌍 添加更多语言支持
- ☕ 让开发者保持动力

<div align="center">

### 赞助我们

<table>
  <tr>
    <td align="center">
      <strong>支付宝</strong><br>
      <img src="./images/AliPay.png" width="200" alt="支付宝收款码"><br>
      <sub>扫描二维码赞助</sub>
    </td>
    <td align="center">
      <strong>微信支付</strong><br>
      <img src="./images/WeChatPay.png" width="200" alt="微信收款码"><br>
      <sub>扫描二维码赞助</sub>
    </td>
  </tr>
</table>

**感谢每一份支持！** 🙏

</div>

## 📄 许可证

本项目采用 [MIT 许可证](./LICENSE)。

## ⭐ 致谢

感谢所有为这个项目做出贡献的开发者！

---

<div align="center">

**[文档](docs/README-COMPLETE-zh.md)** |
**[开发指南](docs/DEVELOPMENT-zh.md)** |
**[问题反馈](https://github.com/michaelhuang7119/anthropic-openai-bridge/issues)** |
**[更新日志](CHANGELOG.md)**

Made with ❤️ by the AOB Team

</div>
