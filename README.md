# Anthropic OpenAI Bridge

[![CI/CD Status](https://github.com/michaelhuang7119/anthropic-openai-bridge/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/michaelhuang7119/anthropic-openai-bridge/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Svelte 5](https://img.shields.io/badge/Svelte-5-orange.svg)](https://svelte.dev/)

> 🌐 **中文文档** | [中文快速指南](./README-zh.md) • [中文技术文档](./docs/README-COMPLETE-zh.md)

A high-performance AI model proxy service based on FastAPI and Svelte 5, supporting multi-provider configuration and management.

## ✨ Project Introduction

Anthropic OpenAI Bridge is an enterprise-grade API proxy service that implements Anthropic-compatible API endpoints and forwards requests to backend providers supporting OpenAI-compatible interfaces (such as Qwen, ModelScope, AI Ping, Anthropic, etc.). Through a unified API interface, you can easily switch between different AI model providers without modifying client code.

## 🚀 Key Features

- **🔥 High-Performance Architecture** - Async database + connection pool, HTTP connection pool optimization, supports 10k QPS
- **🛡️ Enterprise-Grade Security** - JWT key management, encrypted data storage, strong password policies
- **🌍 Internationalization Support** - 16 languages supported (Chinese, English, Japanese, Korean, etc.)
- **🌐 Modern Management Interface** - Svelte 5 + TypeScript, PWA support, dark/light themes
- **🔧 Smart Management** - OpenTelemetry integration, health monitoring, automatic failover, circuit breaker pattern
- **📊 Operations Monitoring** - Performance statistics, token usage tracking, real-time logs
- **💬 Conversation Management** - Chat history, multi-conversation support, token usage statistics
- **🏢 Multi-Provider Support** - Unified API interface, intelligent model mapping, provider token limits

## 🏃‍♂️ Quick Start

### Environment Requirements

- **Python 3.9+** (recommended 3.11+)
- **Node.js 18+** (recommended 20+)
- **npm/pnpm/yarn** (recommended pnpm)
- **Docker & Docker Compose** (optional, for containerized deployment)

### 🚀 One-Click Deployment (Recommended)

#### Docker Compose

```bash
# Clone the repository
git clone <your-repo-url>
cd anthropic-openai-bridge

# Start all services (backend + frontend)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f frontend
docker-compose logs -f backend
```

After starting the services:

- **Frontend Management Interface**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

#### Local Development

**1. Start Backend Service**

```bash
cd backend
bash start.sh
```

**2. Start Frontend Service (New Terminal)**

```bash
cd frontend
pnpm install  # Install dependencies first time
pnpm dev
# Or specify port
pnpm dev -- --port 5175
```

### 🔑 First Login

1. Visit the frontend management interface: http://localhost:5173
2. System will automatically redirect to login page
3. Use default admin credentials:
   - **Email**: `admin@example.com`
   - **Password**: `admin123`

> **Important**: Please change the password immediately after first login! Production environments require strong passwords.

### ⚙️ Required Environment Variables

**Production environment must set the following environment variables**:

```bash
# Required - JWT secret key
export JWT_SECRET_KEY="your-strong-secret-key-here"

# Recommended - Encryption key (for sensitive data encryption)
export ENCRYPTION_KEY="your-fernet-encryption-key-here"

# Recommended - Admin password (at least 12 characters)
export ADMIN_PASSWORD="your-secure-password"

# Performance optimization - database connection pool
export DB_POOL_SIZE=20
export DB_POOL_TIMEOUT=30.0

# Optional - monitoring configuration
export ENABLE_TELEMETRY=true
export OTLP_ENDPOINT=http://jaeger:4318
```

### 🏢 Configure AI Providers

**Must configure provider information before startup!**

Edit the `backend/provider.json` file:

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

### 🔑 Configure Claude Code

1. **Create an API Key**:
   - Login to the management interface
   - Go to "API Key Management" page
   - Click "Create API Key"
   - Fill in name and email (optional)
   - Copy the generated API Key (**Note: Cannot view the full key after creation**)

2. **Configure Claude Code Environment Variables**:

```bash
ANTHROPIC_BASE_URL=http://localhost:5175
ANTHROPIC_API_KEY="sk-xxxxxxxxxxxxx"  # Use the created API Key
```

## 📚 API Usage Examples

### Basic Message Request

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### Streaming Request

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "max_tokens": 200,
    "stream": true
  }'
```

### Tool Calling (Function Calling)

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "opus",
    "messages": [{"role": "user", "content": "What'"'"'s the weather in Beijing today?"}],
    "max_tokens": 200,
    "tools": [{
      "name": "get_weather",
      "description": "Get weather information for a specified city",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "City name"
          }
        },
        "required": ["location"]
      }
    }]
  }'
```

## 📊 Monitoring and Statistics

### Check Health Status

```bash
curl http://localhost:8000/health
```

### Get Token Usage Statistics

```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/token-usage
```

### View Request Logs

```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/requests
```

## 🌍 Documentation

### 📚 Development Resources
- 🔧 **[Development Guide](docs/DEVELOPMENT.md)** - Detailed development guide, architecture documentation, API reference
- 📖 **[Complete Technical Documentation](docs/README-COMPLETE.md)** - Comprehensive technical documentation

### 🌐 API & Demo
- 🔗 **[Interactive API Documentation](http://localhost:8000/docs)** - Complete interactive API documentation
- 🎮 **Online Demo** - (Coming Soon)

### 🐛 Support & Issues
- 📝 **[Issue Tracker](https://github.com/michaelhuang7119/anthropic-openai-bridge/issues)** - Report bugs and request features

### 🇨🇳 Chinese Resources
- 📄 **[中文快速指南](README-zh.md)** - 中文版说明文档
- 📘 **[中文技术文档](docs/README-COMPLETE-zh.md)** - 完整技术文档

## 📝 Changelog

### v1.6.0 (2025-11-29) - Comprehensive internationalization and user experience improvements

- **16 Language Support Added**: Chinese, English, 日本語, 한국어, Français, Español, Deutsch, Русский, Português, Italiano, Nederlands, العربية, हिन्दी, ไทย, Tiếng Việt, Bahasa Indonesia
- **Smart Language Switching**: One-click language switching in top navigation bar, automatically remembers user preferences
- **Full Localization**: All pages, forms, buttons, messages, Toast notifications completely translated
- **Fixed Chat Timestamps**: Resolved "Invalid Date" issue, supports multiple time formats
- **Svelte 5 Upgrade**: Fully upgraded to Svelte 5 syntax, using `$state()` and `$derived()` features

## 🤝 Contributing

We welcome all forms of contribution! Please read the **"Contributing Guidelines"** section in [📘 Development Guide](docs/DEVELOPMENT.md) for detailed information.

## 💖 Support the Project

If this project is helpful to you, please consider supporting our development efforts!

Your support helps us:
- 🚀 Continuously develop and optimize features
- 🐛 Quickly fix issues
- 📚 Improve documentation and examples
- 🌍 Add more language support
- ☕ Keep developers motivated

<div align="center">

### Sponsor Us

<table>
  <tr>
    <td align="center">
      <strong>Alipay</strong><br>
      <img src="./images/AliPay.png" width="200" alt="Alipay QR Code"><br>
      <sub>Scan to sponsor</sub>
    </td>
    <td align="center">
      <strong>WeChat Pay</strong><br>
      <img src="./images/WeChatPay.png" width="200" alt="WeChat Pay QR Code"><br>
      <sub>Scan to sponsor</sub>
    </td>
  </tr>
</table>

**Thanks for every bit of support!** 🙏

</div>

## 📄 License

This project is licensed under the [MIT License](./LICENSE).

## ⭐ Acknowledgments

Thanks to all developers who have contributed to this project!

---

<div align="center">

**[Documentation](docs/README-COMPLETE.md)** |
**[Development Guide](docs/DEVELOPMENT.md)** |
**[Issue Tracker](https://github.com/michaelhuang7119/anthropic-openai-bridge/issues)** |
**[Changelog](CHANGELOG.md)**

Made with ❤️ by the AOB Team

</div>