# Anthropic OpenAI Bridge

一个基于 FastAPI 和 Svelte 5 的高性能 AI 模型代理服务，支持多供应商配置和管理。

## ✨ 项目简介

Anthropic OpenAI Bridge 是一个企业级 API 代理服务，它实现了 Anthropic 兼容的 API 端点，并将请求转发到支持 OpenAI 兼容接口的后端供应商（如通义千问、ModelScope、AI Ping、Anthropic 等）。通过统一的 API 接口，您可以轻松切换不同的 AI 模型供应商，而无需修改客户端代码。

## 🚀 核心功能

### 🔥 高性能架构
- **异步数据库** - aiosqlite + 连接池，消除阻塞，提升并发能力 10-100 倍
- **HTTP 连接池优化** - 支持 10k QPS，Keepalive 连接优化
- **多级缓存架构** - L1（内存）+ L2（Redis）缓存，显著提升响应速度

### 🛡️ 企业级安全
- **JWT 密钥强制管理** - 生产环境必须配置，否则生成临时密钥并警告
- **加密密钥管理** - ENCRYPTION_KEY 支持，敏感数据加密存储
- **强密码策略** - 至少 12 字符，管理员密码检查

### 🌐 现代管理界面
- **Svelte 5 + TypeScript** - 现代化前端框架，类型安全
- **PWA 支持** - 离线访问、安装到主屏幕、后台同步
- **深色/浅色主题** - 用户体验优化
- **代码分割** - 优化首屏加载速度

### 🔧 智能管理
- **OpenTelemetry 集成** - 分布式追踪和监控
- **健康监控** - 手动检查模式，节省 API 调用
- **自动故障转移** - 优先级/随机回退机制
- **熔断器模式** - 快速失败防止级联故障

### 📊 运营监控
- **性能统计** - 请求日志、Token 使用追踪
- **压力测试** - 内置 10k QPS 压力测试脚本
- **实时日志** - 彩色输出，错误追踪

### 🏢 多供应商支持
- **统一 API 接口** - 支持 Anthropic 兼容格式
- **直连模式** - 支持 Anthropic API 格式提供商（无需转换）
- **智能模型映射** - haiku→small, sonnet→middle, opus→big

## 🏃‍♂️ 快速开始

### 环境要求

- **Python 3.9+** (推荐 3.10+)
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

#### 自定义前端端口

```bash
EXPOSE_PORT=5175 docker-compose up -d
```

#### 本地开发方式

**1. 启动后端服务**

```bash
cd backend
bash start.sh
# 或直接运行
python start_proxy.py
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

# 性能优化 - HTTP 连接池
export HTTP_MAX_KEEPALIVE_CONNECTIONS=100
export HTTP_MAX_CONNECTIONS=500
export HTTP_KEEPALIVE_EXPIRY=60

# 性能优化 - 缓存配置
export CACHE_TYPE=multi
export CACHE_MULTI_LEVEL=true
export REDIS_URL=redis://localhost:6379/0
export CACHE_MAX_SIZE=1000
export CACHE_DEFAULT_TTL=3600

# 可选 - 监控配置
export ENABLE_TELEMETRY=true
export OTLP_ENDPOINT=http://jaeger:4318
export SERVICE_VERSION=1.0.0
```

### 🏢 配置 AI 供应商

**启动前必须先配置供应商信息！**

#### 方式一：通过环境变量（推荐）

```bash
# 设置环境变量
export QWEN_API_KEY="your-qwen-api-key"
export MODELSCOPE_API_KEY="your-modelscope-api-key"
export AIPING_API_KEY="your-aiping-api-key"
export MOONSHOT_API_KEY="your-moonshot-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

#### 方式二：配置文件

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

#### 方式三：Web 界面配置

1. 启动服务后登录管理界面
2. 访问"供应商"页面
3. 点击"添加供应商"按钮
4. 填写供应商信息（名称、Base URL、API Key等）
5. 配置模型列表（大、中、小三个类别）
6. 保存配置

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

### 多模态输入（图片）

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "这张图片里有什么？"},
        {
          "type": "image",
          "source": {
            "type": "url",
            "url": "https://example.com/image.jpg"
          }
        }
      ]
    }],
    "max_tokens": 200
  }'
```

### Token 计数

```bash
curl -X POST http://localhost:8000/v1/messages/count_tokens \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "测试消息"}]
  }'
```

## 🏗️ 部署指南

### 🐳 Docker Compose（开发/测试环境）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### ☸️ Kubernetes（生产环境）

参考 [k8s/README.md](./k8s/README.md) 获取详细的 Kubernetes 部署指南。

```bash
# 应用所有配置
kubectl apply -f k8s/

# 查看部署状态
kubectl get pods -n anthropic-bridge
```

### 🧪 性能测试

```bash
# 安装依赖
pip install aiohttp

# 运行压力测试（目标 10k QPS）
python scripts/load_test.py --url http://localhost:5175 --qps 10000 --duration 60
```

### 🔄 CI/CD 流水线

项目配置了 GitHub Actions CI/CD 流水线，支持自动化测试、构建和部署：

```bash
# GitHub Actions 流水线包含以下阶段：
# 1. 测试阶段：运行后端和前端测试
# 2. 构建阶段：自动构建 Docker 镜像
# 3. 部署阶段：自动部署到 Kubernetes（仅 main 分支）
```

CI/CD 配置文件位于：`.github/workflows/ci-cd.yml`

### 📊 监控

#### OpenTelemetry

如果启用了 OpenTelemetry，可以通过以下方式查看追踪和指标：

1. **Jaeger**：查看分布式追踪
2. **Prometheus**：查看指标（需要配置 Prometheus exporter）

#### 健康检查

- 后端：`http://localhost:8000/health`
- 前端：`http://localhost:5175/`

## 🏛️ 项目架构

### 整体架构

```
客户端请求 → 代理服务器 → 供应商API
     ↑                          ↓
  前端管理界面 ← 统一接口 ← 响应处理
```

### 请求流程

1. 客户端向代理服务器发送请求（携带 API Key）
2. 代理服务器验证 API Key
3. 代理服务器根据配置选择供应商
4. 转发请求到目标供应商 API
5. 接收响应并返回给客户端
6. 前端管理界面实时监控健康状态

### 项目结构

```
anthropic-openai-bridge/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由层
│   │   ├── services/          # 业务逻辑层
│   │   ├── database/          # 数据库层（异步 + 连接池）
│   │   ├── cache/             # 多级缓存实现
│   │   ├── infrastructure/    # 基础设施层
│   │   └── config/            # 配置管理
│   ├── requirements.txt       # Python 依赖
│   ├── provider.json          # 供应商配置文件
│   └── start_proxy.py         # 启动脚本
│
├── frontend/                   # 前端管理界面
│   ├── src/
│   │   ├── lib/               # 组件和工具
│   │   └── routes/            # SvelteKit 路由
│   ├── package.json           # Node.js 依赖
│   └── static/                # PWA 静态资源
│
├── k8s/                       # Kubernetes 配置
├── scripts/                   # 工具脚本（负载测试等）
├── docker-compose.yml         # Docker Compose 配置
└── README.md                  # 项目文档
```

## 🛠️ 技术栈

### 后端
- **FastAPI** - 现代、快速的 Web 框架
- **aiosqlite** - 异步数据库操作 + 连接池
- **httpx** - HTTP 客户端，支持连接池优化
- **Pydantic** - 数据验证和设置管理
- **OpenTelemetry** - 分布式追踪和监控
- **pytest** - 测试框架

### 前端
- **Svelte 5** - 新一代前端框架
- **SvelteKit** - Svelte 应用框架
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 快速的前端构建工具 + 代码分割
- **PWA** - 离线支持和应用安装

### 基础设施
- **Docker** - 容器化平台
- **Kubernetes** - 生产环境部署
- **Redis** - 缓存服务
- **Nginx** - 反向代理和负载均衡

## 🔧 环境变量配置

### 必需变量

| 变量名 | 说明 | 默认值 | 备注 |
|--------|------|--------|------|
| `JWT_SECRET_KEY` | JWT Token 密钥 | - | 生产环境**必须**设置 |
| `ENCRYPTION_KEY` | 数据加密密钥 | - | 推荐设置 |
| `ADMIN_PASSWORD` | 管理员密码 | `admin123` | 建议设置强密码 |
| `ADMIN_EMAIL` | 管理员邮箱 | `admin@example.com` | - |

### 性能优化变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DB_POOL_SIZE` | 数据库连接池大小 | `10` |
| `DB_POOL_TIMEOUT` | 连接池超时时间 | `30.0` |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | Keepalive 连接数 | `50` |
| `HTTP_MAX_CONNECTIONS` | 最大连接数 | `200` |
| `HTTP_KEEPALIVE_EXPIRY` | Keepalive 过期时间 | `60` |
| `CACHE_TYPE` | 缓存类型 | `memory` |
| `CACHE_MULTI_LEVEL` | 启用多级缓存 | `false` |
| `CACHE_MAX_SIZE` | 内存缓存最大条目数 | `1000` |
| `CACHE_DEFAULT_TTL` | 默认 TTL | `3600` |
| `REDIS_URL` | Redis 连接 URL | `redis://localhost:6379/0` |

### 监控配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ENABLE_TELEMETRY` | 启用 OpenTelemetry | `false` |
| `OTLP_ENDPOINT` | OTLP 导出端点 | - |
| `SERVICE_VERSION` | 服务版本号 | `1.0.0` |

## 🧪 测试

### 单元测试和集成测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_messages.py
pytest tests/test_converter.py
pytest tests/test_assistant_tool_use.py
pytest tests/test_count_tokens.py
pytest tests/test_performance.py
pytest tests/test_tool_use_format.py

# 运行测试并显示详细输出
pytest tests/ -v

# 运行测试并显示覆盖率
pytest tests/ --cov=app

# 性能压力测试
python scripts/load_test.py --url http://localhost:5175 --qps 10000 --duration 60
```

### 测试文件说明

- **test_messages.py** - 消息处理和 API 端点测试
- **test_converter.py** - 格式转换器测试
- **test_assistant_tool_use.py** - 工具调用功能测试
- **test_count_tokens.py** - Token 计数功能测试
- **test_performance.py** - 性能和并发测试
- **test_tool_use_format.py** - 工具调用格式测试

测试配置文件：`pytest.ini`

## ❓ 常见问题

### Q: 如何添加新的 AI 供应商？

A: 登录管理界面，访问"供应商"页面，点击"添加供应商"按钮，填写供应商信息即可。或者手动编辑 `backend/provider.json` 文件。

### Q: 如何实现故障转移？

A: 系统根据 `priority` 字段选择供应商，优先级越高（数字越小）越优先。当高优先级供应商不可用时，自动切换到下一个可用供应商。

### Q: 如何监控供应商健康状态？

A: 登录管理界面，访问"健康监控"页面，点击"刷新状态"按钮进行手动检查。系统会显示总体状态（健康、部分健康、不健康、未检查）和每个供应商的详细信息。健康检查仅在手动点击时进行，最大化节省 API 调用和 Token 消耗。

### Q: 如何创建 API Key？

A: 登录管理界面，访问"API Key 管理"页面，点击"创建 API Key"按钮，填写名称和邮箱（可选），保存后复制生成的 API Key。**注意：创建后无法再次查看完整 Key，请妥善保管。**

### Q: 忘记管理员密码怎么办？

A: 如果忘记了管理员密码，可以：
1. 删除数据库文件 `backend/data/app.db`
2. 重启后端服务，系统会重新创建默认管理员账号
3. 使用默认账号登录后立即修改密码

### Q: API Key 泄露了怎么办？

A: 登录管理界面，访问"API Key 管理"页面，找到对应的 API Key，点击"禁用"或"删除"按钮。建议定期轮换 API Key 以提高安全性。

### Q: 生产环境如何优化性能？

A: 请参考 [DEPLOYMENT.md](./DEPLOYMENT.md) 中的生产环境配置建议，包括：
- 设置必需的 `JWT_SECRET_KEY` 和 `ENCRYPTION_KEY`
- 配置数据库和 HTTP 连接池
- 启用多级缓存
- 配置 OpenTelemetry 监控

## 🔒 安全注意事项

1. **生产环境必须设置**：
   - `JWT_SECRET_KEY` - 强随机密钥
   - `ENCRYPTION_KEY` - 加密密钥（用于敏感数据）
   - `ADMIN_PASSWORD` - 至少 12 字符的强密码

2. **API 密钥安全**：建议使用环境变量存储 API 密钥，不要将密钥直接写入配置文件

3. **HTTPS 配置**：生产环境请配置 TLS/SSL 证书

4. **访问控制**：使用防火墙或 Ingress 规则限制访问

5. **密钥管理**：使用专业的密钥管理服务（如 Kubernetes Secrets、HashiCorp Vault）

## 📁 配置文件说明

### 环境变量配置

**主要配置文件**：

- **`.env.example`** - Docker Compose 环境变量示例
  ```bash
  # 前端暴露端口（映射到宿主机端口）
  EXPOSE_PORT=5173
  ```

- **`backend/.env`** - 后端环境变量配置（需手动创建）

### 供应商配置示例

**`backend/provider.json.example`** - 供应商配置模板：

```json
{
  "providers": [
    {
      "name": "example-provider",
      "enabled": false,
      "priority": 1,
      "api_key": "your-api-key-here",
      "base_url": "https://api.example.com/v1",
      "timeout": 180,
      "max_retries": 2,
      "custom_headers": {},
      "models": {
        "big": ["claude-opus"],
        "middle": ["claude-sonnet"],
        "small": ["claude-haiku"]
      },
      "api_format": "openai",
      "max_tokens_limit": 32768
    }
  ],
  "fallback_strategy": "priority"
}
```

### 配置文件说明

| 配置文件 | 说明 | 用途 |
|---------|------|------|
| `.env.example` | Docker 环境变量示例 | Docker Compose 部署配置 |
| `backend/provider.json` | 供应商配置文件 | 主配置文件（需配置） |
| `backend/provider.json.example` | 供应商配置模板 | 配置参考 |
| `pytest.ini` | 测试配置 | pytest 测试框架配置 |
| `docker-compose.yml` | Docker Compose 配置 | 容器编排配置 |
| `.github/workflows/ci-cd.yml` | CI/CD 配置 | 自动化构建部署 |

## 🛠️ 工具脚本和依赖管理

### 性能测试脚本

**`scripts/load_test.py`** - 高性能负载测试工具：

```bash
# 基本用法
python scripts/load_test.py --url http://localhost:5175 --qps 10000 --duration 60

# 高级参数
python scripts/load_test.py \
  --url http://localhost:5175 \
  --qps 10000 \
  --duration 60 \
  --concurrency 100 \
  --api-key sk-test-key \
  --model haiku
```

**脚本特性**：
- 异步并发请求
- 可配置 QPS 和持续时间
- 详细的性能统计（响应时间、成功率、QPS 等）
- 支持自定义 API Key 和模型

### 测试验证脚本

**`scripts/test_all.py`** - 全面的测试验证工具：

```bash
# 验证所有测试文件语法和功能
python scripts/test_all.py
```

**验证内容**：
- 检查所有测试文件的Python语法
- 验证流式格式测试功能
- 测试文件完整性检查
- 提供详细的测试报告

**测试文件列表**：
- `test_assistant_tool_use.py` - 工具调用功能测试
- `test_converter.py` - 格式转换器测试
- `test_count_tokens.py` - Token计数功能测试
- `test_messages.py` - 消息处理和API端点测试
- `test_performance.py` - 性能和并发测试
- `test_streaming_format.py` - 流式输出格式验证测试 ✅
- `test_tool_use_format.py` - 工具调用格式测试

### 启动脚本

**三种启动方式**：

1. **项目根目录启动脚本**：
```bash
# 一键启动（启动后端和前端）
bash start.sh
```

2. **后端启动脚本**：
```bash
# 使用默认配置启动后端
bash backend/start.sh

# 或直接运行 Python 脚本
python backend/start_proxy.py
```

3. **前端启动脚本**：
```bash
# 启动前端开发服务器
bash frontend/start.sh

# 或直接运行
pnpm --prefix frontend dev
```

### 测试验证和CI/CD

项目包含完整的测试验证脚本和优化的CI/CD配置：

```bash
# 验证测试配置
python scripts/test_validation.py

# 本地运行测试验证
cd backend && cp ../pytest.ini ./ && cp -r ../tests ./ && PYTHONPATH=. pytest tests/ --cov=app
```

**CI/CD 优化**：
- 修复了pytest路径问题
- 优化了覆盖率报告生成
- 解决了"collected 0 items"错误
- 配置了正确的Python模块路径

### 依赖管理

**`backend/requirements.txt`** - Python 依赖包：
```bash
cd backend
pip install -r requirements.txt
```

## 📄 许可证

MIT License - 详情请查看 [LICENSE](LICENSE) 文件

```
MIT License

Copyright (c) 2025 Anthropic OpenAI Bridge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🔗 相关链接

- **项目主页**：<https://github.com/your-username/anthropic-openai-bridge>
- **问题反馈**：<https://github.com/your-username/anthropic-openai-bridge/issues>
- **功能建议**：<https://github.com/your-username/anthropic-openai-bridge/discussions>
- **API 文档**：<http://localhost:8000/docs>
- **部署指南**：请查看 [DEPLOYMENT.md](./DEPLOYMENT.md)
- **优化总结**：请查看 [OPTIMIZATION_SUMMARY.md](./OPTIMIZATION_SUMMARY.md)
- **Kubernetes 部署**：请查看 [k8s/README.md](./k8s/README.md)

## 🗺️ 路线图

### v1.4.0 (规划中)
- [ ] **多语言支持** - 支持中文界面
- [ ] **插件系统** - 支持自定义插件扩展功能
- [ ] **指标仪表板** - 详细的性能和使用指标
- [ ] **告警系统** - 支持邮件/Webhook 告警

### v1.5.0 (规划中)
- [ ] **集群部署** - 支持多节点部署
- [ ] **负载均衡** - 内置负载均衡算法
- [ ] **灰度发布** - 支持 A/B 测试
- [ ] **自动扩缩容** - 基于负载的动态扩缩容

### v2.0.0 (长期规划)
- [ ] **微服务架构** - 完全微服务化
- [ ] **实时协作** - 多用户实时编辑配置
- [ ] **AI 模型市场** - 内置模型市场
- [ ] **GraphQL 支持** - 支持 GraphQL 查询

## 🏆 致谢

感谢以下开源项目：
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [Svelte](https://svelte.dev/) - 新一代前端框架
- [Docker](https://www.docker.com/) - 容器化平台
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证库
- [Nginx](https://www.nginx.com/) - 高性能 Web 服务器
- [OpenTelemetry](https://opentelemetry.io/) - 可观测性标准
- [Kubernetes](https://kubernetes.io/) - 容器编排平台

特别感谢所有贡献者和用户！

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！**

Made with ❤️ by Anthropic OpenAI Bridge Team

</div>
