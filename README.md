# Anthropic OpenAI Bridge

一个基于 FastAPI 和 Svelte 5 的高性能 AI 模型代理服务，支持多供应商配置和管理。

## 项目简介

Anthropic OpenAI Bridge 是一个企业级 API 代理服务，它实现了 Anthropic 兼容的 API 端点，并将请求转发到支持 OpenAI 兼容接口的后端供应商（如通义千问、ModelScope、AI Ping、Anthropic 等）。通过统一的 API 接口，您可以轻松切换不同的 AI 模型供应商，而无需修改客户端代码。

本项目提供：
- **🚀 Web 管理界面** - 基于 Svelte 5 的现代化管理界面，支持深色/浅色主题切换
- **🔐 双层认证系统** - 管理面板认证（邮箱密码）+ 服务 API 认证（API Key）
- **🔑 API Key 生命周期管理** - 支持创建、禁用、删除 API Key，支持用户关联和最后使用时间追踪
- **🏢 多供应商支持** - 支持多个 AI 供应商，支持优先级/随机回退机制
- **💓 智能健康监控** - 四种状态（健康、部分健康、不健康、未检查），手动检查模式节省 API 调用
- **🎨 可视化配置** - 通过 Web 界面轻松配置供应商和模型，支持大/中/小模型分类
- **⚡ 高性能流式响应** - 支持 Server-Sent Events (SSE) 流式输出，优化响应速度
- **🔧 完整工具调用** - 全面的工具调用（Function Calling）支持，包括参数验证和错误处理
- **🖼️ 多模态输入** - 支持文本和图片输入，兼容 Anthropic 和 OpenAI 格式
- **📊 Token 计数服务** - 独立的 token 计数端点，帮助控制成本
- **🗺️ 智能模型映射** - 自动模型映射（haiku→small, sonnet→middle, opus→big）
- **🚦 全局 Token 限制** - 可配置的全局 max_tokens/min_tokens 限制
- **🔍 健康检查系统** - 内置健康检查端点，支持单个/批量检查
- **📝 完善的日志** - 彩色输出日志，支持慢请求检测和错误追踪
- **🔄 自动重试机制** - 支持超时和连接错误的指数退避重试
- **🔄 熔断器模式** - 支持熔断器模式，快速失败防止级联故障
- **💬 友好的提示** - Toast 消息提示，操作反馈清晰
- **🔗 Anthropic 直连** - 支持直接连接 Anthropic API 格式提供商（无需转换）
- **📈 性能监控** - 详细的请求日志、性能统计和 Token 使用追踪
- **🔧 增强的缓存** - 支持内存和 Redis 缓存，可配置 TTL 和排除参数
- **🛡️ 安全加固** - 配置文件安全验证、环境变量支持、加密存储
- **🚀 Nginx 代理** - 内置 Nginx 配置，支持 gzip 压缩和健康检查
- **📱 URL Scheme 支持** - 支持快速配置链接，方便 Claude Desktop/Claude Code 使用

## 快速开始

### 环境要求

- **Python 3.9+** (推荐 3.10+)
- **Node.js 18+** (推荐 20+)
- **npm/pnpm/yarn** (推荐 pnpm)
- **Docker & Docker Compose** (可选，用于容器化部署)

### 快速启动（3种方式）

#### 🐳 方式一：Docker Compose 一键部署（推荐）

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

服务将在以下端口启动：
- **前端管理界面**: http://localhost:5173
- **后端 API**: http://localhost:8000 (内部网络，仅 Docker 可访问)
- **API 文档**: http://localhost:8000/docs

**自定义前端端口**：
```bash
EXPOSE_PORT=5175 docker-compose up -d
```

#### 💻 方式二：本地开发启动

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

#### 📦 方式三：后端开发模式

```bash
cd backend
# 开发模式（自动重载）
python start_proxy.py --reload

# 自定义主机和端口
python start_proxy.py --host 127.0.0.1 --port 3000

# 调试模式
python start_proxy.py --log-level debug
```

### 首次登录

1. 访问前端管理界面：http://localhost:5173
2. 系统会自动跳转到登录页面
3. 使用默认管理员账号登录：
   - **邮箱**：`admin@example.com`
   - **密码**：`admin123`
4. 登录后建议立即修改密码（通过管理员账号创建新用户或修改现有用户）

**注意**：默认管理员账号可通过环境变量配置：
```bash
export ADMIN_EMAIL="your-admin@example.com"
export ADMIN_PASSWORD="your-secure-password"
```

### 安装依赖（仅后端）

```bash
cd backend
pip install -r requirements.txt
```


### 配置供应商（重要）

**启动前必须先配置供应商信息！**

#### 方式一：通过配置文件（推荐）

编辑 `backend/provider.json` 文件，配置您的 AI 供应商信息：

```bash
# 设置环境变量（推荐方式）
export QWEN_API_KEY="your-qwen-api-key"
export MODELSCOPE_API_KEY="your-modelscope-api-key"
export AIPING_API_KEY="your-aiping-api-key"
export MOONSHOT_API_KEY="your-moonshot-api-key"

# 在 provider.json 中使用环境变量格式
# "api_key": "${QWEN_API_KEY}"
```

**当前支持的供应商类型：**

1. **通义千问 (Qwen)** - 阿里云 DashScope
   - Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
   - 支持 OpenAI 格式

2. **ModelScope** - 魔搭社区模型服务
   - Base URL: `https://api-inference.modelscope.cn/v1/`
   - 支持 OpenAI 格式

3. **AI Ping** - AI Ping 平台
   - Base URL: `https://aiping.cn/api/v1`
   - 支持 OpenAI 格式

4. **Moonshot AI** - Moonshot AI (Kimi)
   - Base URL: `https://api.moonshot.cn/v1`
   - 支持 OpenAI 格式

5. **Anthropic 直连** - 支持 Anthropic API 格式
   - Base URL: `https://api.anthropic.com` 或供应商提供的 Anthropic 格式端点
   - 设置 `"api_format": "anthropic"`

#### 方式二：通过 Web 界面配置

1. 启动服务后登录管理界面
2. 访问"供应商"页面
3. 点击"添加供应商"按钮
4. 填写供应商信息（名称、Base URL、API Key等）
5. 配置模型列表（大、中、小三个类别）
6. 保存配置

**注意**：Web 界面配置需要服务先启动，因此首次启动前建议先通过配置文件设置至少一个供应商。

### 配置 Claude Code

在 Claude Code 中使用本服务，需要：

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

**注意**：`ANTHROPIC_BASE_URL` 需要替换为实际的前端服务地址（如果前端运行在其他端口，请相应修改）。

### 环境变量配置

#### 后端环境变量

- **ADMIN_EMAIL**: 默认管理员邮箱（默认: `admin@example.com`）
- **ADMIN_PASSWORD**: 默认管理员密码（默认: `admin123`）
- **JWT_SECRET_KEY**: JWT Token 密钥（默认: `your-secret-key-change-this-in-production`）
- **MAX_TOKENS_LIMIT**: 全局最大 `max_tokens` 限制（默认: `1000000`）
- **MIN_TOKENS_LIMIT**: 全局最小 `max_tokens` 限制（默认: `100`）
- **PROVIDER_CONFIG_PATH**: 供应商配置文件路径（默认: `./provider.json`）
- **HOST**: 服务器绑定地址（默认: `0.0.0.0`）
- **PORT**: 服务器端口（默认: `8000`）
- **LOG_LEVEL**: 日志级别（默认: `info`）
- **DATABASE_PATH**: 数据库文件路径（默认: `./data/app.db`）

这些限制会应用到所有供应商，所有请求的 `max_tokens` 都会被限制在 `[MIN_TOKENS_LIMIT, MAX_TOKENS_LIMIT]` 范围内。

### 模型映射

项目支持自动模型映射：

- `haiku` → 映射到供应商配置中的 `small` 类别
- `sonnet` → 映射到供应商配置中的 `middle` 类别
- `opus` → 映射到供应商配置中的 `big` 类别

详细的配置说明请参考 [CONFIGURATION.md](./CONFIGURATION.md)。

## 认证和授权

### 认证机制

项目采用双重认证机制：

1. **管理面板认证**（邮箱密码登录）
   - 用于访问 Web 管理界面
   - 使用 JWT Token 进行身份验证
   - 支持管理员和普通用户两种角色
   - 只有管理员可以创建新用户和管理 API Key

2. **服务 API 认证**（API Key）
   - 用于访问 `/v1/messages` 等服务端点
   - 使用 API Key 进行身份验证
   - API Key 通过管理界面创建和管理
   - 每个 API Key 可以关联用户信息（名称、邮箱）

### 默认管理员账号

首次启动时，系统会自动创建默认管理员用户：
- **邮箱**：`admin@example.com`（可通过 `ADMIN_EMAIL` 环境变量配置）
- **密码**：`admin123`（可通过 `ADMIN_PASSWORD` 环境变量配置）

**安全提示**：首次登录后请立即修改默认密码！

### API Key 管理

1. **创建 API Key**：
   - 登录管理界面
   - 访问"API Key 管理"页面
   - 点击"创建 API Key"
   - 填写名称和邮箱（可选）
   - 保存生成的 API Key（创建后无法再次查看）

2. **使用 API Key**：
   - 在请求头中添加：`X-API-Key: sk-xxxxxxxxxxxxx`
   - 或在查询参数中添加：`?api_key=sk-xxxxxxxxxxxxx`

3. **管理 API Key**：
   - 查看所有 API Key 列表
   - 启用/禁用 API Key
   - 删除 API Key
   - 查看最后使用时间

详细说明请参考 [AUTH_SETUP.md](./AUTH_SETUP.md)。

## 运行服务

### 使用启动脚本（推荐）

```bash
# 默认配置启动（监听 0.0.0.0:8000，禁用自动重载）
python start_proxy.py

# 自定义主机和端口
python start_proxy.py --host 127.0.0.1 --port 3000

# 通过环境变量配置
HOST=127.0.0.1 PORT=3000 python start_proxy.py

# 开发环境：启用自动重载
python start_proxy.py --reload

# 自定义日志级别
python start_proxy.py --log-level debug
```

### 启动脚本选项

`start_proxy.py` 脚本支持以下选项：

- `--host HOST`: 绑定主机地址（默认: `0.0.0.0`，或使用 HOST 环境变量）
- `--port PORT`: 绑定端口（默认: `8000`，或使用 PORT 环境变量）
- `--reload`: 启用代码变更自动重载（默认: `False`）
- `--no-reload`: 禁用自动重载
- `--log-level LEVEL`: 设置日志级别（默认: `info`，可选: `critical`, `error`, `warning`, `info`, `debug`, `trace`）

启动脚本会自动检查端口是否可用，如果端口已被占用，会提供有用的错误信息和解决方案。

### 使用 uvicorn 直接启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API 使用示例

### 非流式请求

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

响应示例：
```json
{
  "id": "msg_xxx",
  "type": "message",
  "role": "assistant",
  "content": [{"type": "text", "text": "你好！很高兴为你服务。"}],
  "model": "haiku",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 5,
    "output_tokens": 10
  }
}
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

流式响应使用 Server-Sent Events (SSE) 格式，每个数据块以 `data: ` 开头。

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

响应示例：
```json
{
  "model": "haiku",
  "input_tokens": 5
}
```

### 健康检查

```bash
curl http://localhost:8000/health
```

响应：
```json
{
  "status": "healthy"
}
```

## 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_messages.py

# 运行测试并显示详细输出
pytest tests/ -v

# 运行测试并显示覆盖率
pytest tests/ --cov=app
```

## 项目结构

```
anthropic-openai-bridge/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由层
│   │   │   ├── auth.py        # 用户认证 API
│   │   │   ├── api_keys.py    # API Key 管理 API
│   │   │   ├── config.py      # 配置管理 API
│   │   │   ├── health.py      # 健康检查 API
│   │   │   ├── providers.py   # 供应商管理 API
│   │   │   └── stats.py       # 性能统计 API
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── message_service.py      # 消息处理服务（请求分发、供应商选择等）
│   │   │   ├── auth_service.py         # 认证授权服务
│   │   │   ├── api_key_service.py      # API Key 管理服务
│   │   │   └── stats_service.py        # 统计服务
│   │   ├── converters/        # 格式转换层
│   │   │   ├── anthropic_to_openai.py  # Anthropic 转 OpenAI 格式
│   │   │   └── openai_to_anthropic.py  # OpenAI 转 Anthropic 格式
│   │   ├── config/            # 配置管理
│   │   │   └── main.py        # 统一配置管理（熔断器、缓存、可观测性等）
│   │   ├── database/          # 数据库层
│   │   │   ├── base.py        # 数据库基类
│   │   │   ├── api_keys.py    # API Key 数据表
│   │   │   ├── request_logs.py # 请求日志表
│   │   │   └── stats.py       # 统计数据表
│   │   ├── cache/             # 缓存实现
│   │   │   ├── __init__.py    # 缓存抽象接口
│   │   │   ├── memory_cache.py # 内存缓存
│   │   │   ├── redis_cache.py  # Redis 缓存
│   │   │   └── smart_cache.py  # 智能缓存管理器
│   │   ├── tracing/           # 链路追踪和可观测性
│   │   │   └── tracing_system.py # TracingSystem 实现
│   │   ├── models/            # 数据模型
│   │   │   ├── __init__.py    # 通用模型
│   │   │   ├── auth.py        # 认证相关模型
│   │   │   ├── api_keys.py    # API Key 模型
│   │   │   └── stats.py       # 统计模型
│   │   ├── security.py        # 安全工具函数
│   │   ├── circuit_breaker.py # 熔断器实现（主动健康检查）
│   │   ├── client.py          # OpenAI 客户端封装
│   │   ├── retry.py           # 重试机制
│   │   └── main.py            # FastAPI 应用入口
│   ├── data/                  # 数据目录（数据库文件）
│   ├── requirements.txt       # Python 依赖
│   ├── provider.json          # 供应商配置文件（需自行创建）
│   ├── provider.json.example  # 配置文件示例
│   ├── start_proxy.py         # 代理服务启动脚本
│   └── start.sh               # 后端启动脚本
│
├── frontend/                   # 前端管理界面
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/    # 组件
│   │   │   │   ├── ui/        # 基础 UI 组件
│   │   │   │   │   ├── Button.svelte
│   │   │   │   │   ├── Card.svelte
│   │   │   │   │   ├── Badge.svelte
│   │   │   │   │   ├── Input.svelte
│   │   │   │   │   └── Toast.svelte
│   │   │   │   └── layout/   # 布局组件
│   │   │   │       └── Header.svelte
│   │   │   ├── services/      # API 服务层
│   │   │   │   ├── api.ts     # API 客户端
│   │   │   │   ├── auth.ts    # 认证服务
│   │   │   │   ├── apiKeys.ts # API Key 服务
│   │   │   │   ├── providers.ts
│   │   │   │   ├── health.ts
│   │   │   │   ├── config.ts
│   │   │   │   └── stats.ts
│   │   │   ├── stores/        # Svelte 状态管理
│   │   │   │   ├── toast.ts
│   │   │   │   └── theme.ts
│   │   │   ├── types/         # TypeScript 类型定义
│   │   │   └── styles/        # 全局样式
│   │   └── routes/            # SvelteKit 路由
│   │       ├── +layout.svelte
│   │       ├── +page.svelte   # 首页（仪表板）
│   │       ├── login/         # 登录页面
│   │       │   └── +page.svelte
│   │       ├── api-keys/      # API Key 管理页面
│   │       │   └── +page.svelte
│   │       ├── providers/     # 供应商管理页面
│   │       │   └── +page.svelte
│   │       ├── health/        # 健康监控页面
│   │       │   └── +page.svelte
│   │       ├── config/        # 配置页面
│   │       │   └── +page.svelte
│   │       └── stats/         # 性能监控页面
│   │           └── +page.svelte
│   ├── package.json           # Node.js 依赖
│   ├── svelte.config.js       # SvelteKit 配置
│   ├── vite.config.ts         # Vite 配置
│   ├── tsconfig.json          # TypeScript 配置
│   ├── nginx.conf             # Nginx 配置（用于 Docker）
│   ├── Dockerfile             # 前端 Dockerfile
│   └── start.sh               # 前端启动脚本
│
├── docker-compose.yml         # Docker Compose 配置
├── LICENSE                    # MIT 许可证
├── pytest.ini                 # pytest 配置
├── tests/                      # 测试文件
├── AUTH_SETUP.md              # 认证系统说明文档
└── README.md                   # 项目说明文档
```

## 功能特性

### 后端功能

#### 用户认证 API
- `POST /api/auth/login` - 用户登录（邮箱密码）
- `POST /api/auth/register` - 注册新用户（需要管理员权限）
- `GET /api/auth/me` - 获取当前用户信息

#### API Key 管理 API
- `GET /api/api-keys` - 获取所有 API Key 列表
- `GET /api/api-keys/{id}` - 获取指定 API Key 详情
- `POST /api/api-keys` - 创建新 API Key
- `PUT /api/api-keys/{id}` - 更新 API Key
- `DELETE /api/api-keys/{id}` - 删除 API Key

#### 供应商管理 API
- `GET /api/providers` - 获取所有供应商列表（需要管理员权限）
- `POST /api/providers` - 创建新供应商（需要管理员权限）
- `PUT /api/providers/{name}` - 更新供应商配置（需要管理员权限）
- `DELETE /api/providers/{name}` - 删除供应商（需要管理员权限）
- `POST /api/providers/{name}/test` - 测试供应商连接（需要管理员权限）

#### 健康检查 API
- `GET /api/health` - 获取所有供应商健康状态（需要管理员权限）
- `GET /api/health/{name}` - 获取指定供应商健康状态（需要管理员权限）

#### 配置管理 API
- `GET /api/config` - 获取全局配置（需要管理员权限）
- `PUT /api/config` - 更新全局配置（需要管理员权限）

#### 性能统计 API
- `GET /api/stats/requests` - 获取请求日志统计（需要管理员权限）
- `GET /api/stats/token-usage` - 获取 Token 使用统计（需要管理员权限）
- `GET /api/stats/summary` - 获取性能摘要统计（需要管理员权限）

#### 服务 API（需要 API Key）
- `POST /v1/messages` - 发送消息请求
- `POST /v1/messages/count_tokens` - 计算 Token 数量

### 前端功能

#### 登录页面
- 邮箱密码登录
- 自动跳转到首页
- 显示默认管理员账号提示

#### API Key 管理页面
- 创建 API Key（支持名称和邮箱关联）
- 查看所有 API Key 列表
- 启用/禁用 API Key
- 删除 API Key
- 查看最后使用时间
- 复制 API Key（仅在创建时显示）

#### 供应商管理页面
- 查看所有供应商列表
- 查看供应商健康状态（健康、部分健康、不健康、未检查）
- 添加新供应商
- 编辑现有供应商
- 删除供应商
- 测试供应商连接（显示响应时间）

#### 健康监控页面
- 手动刷新健康状态（零自动请求，节省 API 调用和 Token）
- 查看总体健康状态
- 查看每个供应商的详细健康信息
- 显示最后检查时间和响应时间

#### 配置页面
- 配置全局回退策略（优先级/随机）
- 配置熔断器参数（失败阈值、恢复超时）

#### 性能监控页面
- 查看请求日志统计
- 查看 Token 使用统计
- 查看性能摘要
- 按供应商筛选和统计
- 优化的分页加载（默认显示最近100条记录，支持"增加1000条"按钮扩展）

#### 首页仪表板
- 供应商统计概览
- 健康状态总览
- 系统信息
- Claude Code 配置说明（自动显示当前服务地址）

## 技术栈

### 后端
- **FastAPI** - 现代、快速的 Web 框架
- **Pydantic** - 数据验证和设置管理
- **OpenAI SDK** - 与 OpenAI 兼容的 API 交互
- **Uvicorn** - ASGI 服务器
- **SQLite** - 数据库（开发环境）
- **bcrypt** - 密码哈希
- **python-jose** - JWT Token 处理
- **pytest** - 测试框架

### 前端
- **Svelte 5** - 新一代前端框架
- **SvelteKit** - Svelte 应用框架
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 快速的前端构建工具

## 供应商配置说明

### 供应商配置示例

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
    }
  ],
  "fallback_strategy": "priority",
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 60
  }
}
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `name` | 供应商名称（唯一标识符） |
| `enabled` | 是否启用该供应商 |
| `priority` | 优先级（数字越小优先级越高） |
| `api_key` | API 密钥（支持环境变量 `${VAR_NAME}`） |
| `base_url` | API 基础 URL |
| `timeout` | 请求超时时间（秒） |
| `max_retries` | 最大重试次数 |
| `models` | 模型配置，分为大、中、小三个类别 |
| `api_format` | API 格式（'openai' 或 'anthropic'，默认为 'openai'） |

### 供应商支持

项目支持多个 AI 供应商，当前支持的供应商包括：

- **Anthropic Claude** - Anthropic 官方 API
- **OpenAI** - OpenAI GPT 系列
- **通义千问 (Qwen)** - 阿里云 DashScope
- **ModelScope** - 魔搭社区模型服务
- **AI Ping** - AI Ping 平台

每个供应商都支持：
- 优先级配置（数字越小优先级越高）
- 自动故障转移
- 独立的超时和重试配置
- 自定义 HTTP 请求头
- API 格式选择（OpenAI 或 Anthropic 格式）

### Anthropic 直连功能

项目新增了 Anthropic 直连功能，支持直接连接到 Anthropic API 格式的提供商，无需进行格式转换。通过在供应商配置中设置 `"api_format": "anthropic"`，可以启用此功能。

示例配置：
```json
{
  "name": "anthropic-direct",
  "enabled": true,
  "priority": 1,
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
```

## 架构设计

### 代理模式架构

```
客户端请求 → 代理服务器 → 供应商API
     ↑                          ↓
  前端管理界面 ← 统一接口 ← 响应处理
```

#### 优势
- 统一 API 接口
- 多供应商管理
- 故障转移
- 负载均衡
- 集中化配置
- 安全认证和授权

### 请求流程

1. 客户端向代理服务器发送请求（携带 API Key）
2. 代理服务器验证 API Key
3. 代理服务器根据配置选择供应商
4. 转发请求到目标供应商 API
5. 接收响应并返回给客户端
6. 前端管理界面实时监控健康状态

## 错误处理

项目提供了完善的错误处理机制：

- **401 Unauthorized** - 未认证或 API Key 无效
- **403 Forbidden** - 权限不足
- **429 Rate Limit Error** - 请求频率超限
- **502 Bad Gateway** - 供应商 API 错误
- **503 Service Unavailable** - 连接错误
- **500 Internal Server Error** - 内部服务器错误

所有错误响应都包含详细的错误信息和供应商名称，便于调试和问题定位。

## 常见问题

### Q: 如何添加新的 AI 供应商？

A: 登录管理界面，访问"供应商"页面，点击"添加供应商"按钮，填写供应商信息即可。或者手动编辑 `backend/provider.json` 文件。

### Q: 如何实现故障转移？

A: 系统根据 `priority` 字段选择供应商，优先级越高（数字越小）越优先。当高优先级供应商不可用时，自动切换到下一个可用供应商。

### Q: 如何监控供应商健康状态？

A: 登录管理界面，访问"健康监控"页面，点击"刷新状态"按钮进行手动检查。系统会显示总体状态（健康、部分健康、不健康、未检查）和每个供应商的详细信息。健康检查仅在手动点击时进行，不会自动请求，最大化节省 API 调用和 Token 消耗。

### Q: 如何创建 API Key？

A: 登录管理界面，访问"API Key 管理"页面，点击"创建 API Key"按钮，填写名称和邮箱（可选），保存后复制生成的 API Key。**注意：创建后无法再次查看完整 Key，请妥善保管。**

### Q: 忘记管理员密码怎么办？

A: 如果忘记了管理员密码，可以：
1. 删除数据库文件 `backend/data/app.db`
2. 重启后端服务，系统会重新创建默认管理员账号
3. 使用默认账号登录后立即修改密码

### Q: API Key 泄露了怎么办？

A: 登录管理界面，访问"API Key 管理"页面，找到对应的 API Key，点击"禁用"或"删除"按钮。建议定期轮换 API Key 以提高安全性。

## 部署

### Docker 部署（推荐）

#### 1. 构建并启动所有服务

```bash
# 在项目根目录运行
docker-compose up -d
```

这将自动构建并启动：
- 后端服务：http://localhost:8000（仅内部网络，不暴露到宿主机）
- 前端管理界面：http://localhost:5173（默认端口，可通过 EXPOSE_PORT 环境变量修改）

#### 自定义前端端口

```bash
# 设置环境变量
export EXPOSE_PORT=5175

# 启动服务
docker-compose up -d
```

前端将在 http://localhost:5175 启动。

#### 2. 查看服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

#### 3. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

#### 4. 重新构建镜像

```bash
# 重新构建并启动
docker-compose up -d --build
```

#### 5. 环境变量配置

创建 `.env` 文件来配置环境变量：

```bash
# .env 文件示例
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-password
JWT_SECRET_KEY=your-jwt-secret-key
QWEN_API_KEY=your-qwen-api-key
MODELSCOPE_API_KEY=your-modelscope-api-key
AIPING_API_KEY=your-aiping-api-key
MAX_TOKENS_LIMIT=1000000
MIN_TOKENS_LIMIT=100
```

然后在 `docker-compose.yml` 中添加：

```yaml
services:
  backend:
    environment:
      - ADMIN_EMAIL=${ADMIN_EMAIL}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - QWEN_API_KEY=${QWEN_API_KEY}
      - MODELSCOPE_API_KEY=${MODELSCOPE_API_KEY}
      - AIPING_API_KEY=${AIPING_API_KEY}
      - MAX_TOKENS_LIMIT=${MAX_TOKENS_LIMIT}
      - MIN_TOKENS_LIMIT=${MIN_TOKENS_LIMIT}
```

### 手动部署

#### 1. 部署后端

```bash
cd backend
python start_proxy.py
```

#### 2. 部署前端

```bash
cd frontend
npm run build
# 将 build 目录部署到 Web 服务器
```

## 注意事项

1. **API 密钥安全**：建议使用环境变量存储 API 密钥，不要将密钥直接写入配置文件。`provider.json` 文件已添加到 `.gitignore`，避免意外提交敏感信息
2. **Token 限制**：所有请求的 `max_tokens` 都会被限制在全局配置的范围内
3. **供应商兼容性**：某些供应商可能不支持所有 OpenAI 参数（如 `tool_choice`），系统会自动过滤不支持的参数
4. **流式响应**：流式响应使用 SSE 格式，客户端需要正确处理 `data: ` 前缀。系统支持实时 Token 消耗显示
5. **生产环境**：生产环境部署时建议禁用自动重载（`--no-reload`）并配置适当的日志级别
6. **健康检查**：健康检查采用手动模式，不会自动请求，避免不必要的 API 调用和 Token 消耗
7. **Docker 部署**：后端服务默认不暴露端口到宿主机，仅通过前端 Nginx 代理访问，提高安全性
8. **Claude Code 配置**：前端管理界面会自动显示当前服务地址，方便配置 `ANTHROPIC_BASE_URL`
9. **认证安全**：首次登录后请立即修改默认管理员密码，生产环境请设置强密码的 `JWT_SECRET_KEY`
10. **API Key 管理**：API Key 创建后无法再次查看完整 Key，请妥善保管。建议定期轮换 API Key

## 📜 许可证

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

### 第三方依赖

- **后端依赖**：[requirements.txt](backend/requirements.txt)
- **前端依赖**：[package.json](frontend/package.json)

## 🔗 相关链接

- **项目主页**：<https://github.com/your-username/anthropic-openai-bridge>
- **问题反馈**：<https://github.com/your-username/anthropic-openai-bridge/issues>
- **功能建议**：<https://github.com/your-username/anthropic-openai-bridge/discussions>
- **API 文档**：<http://localhost:8000/docs>

## 🎯 路线图

### v1.3.0 (规划中)
- [ ] **多语言支持** - 支持中文界面
- [ ] **插件系统** - 支持自定义插件扩展功能
- [ ] **指标仪表板** - 详细的性能和使用指标
- [ ] **告警系统** - 支持邮件/Webhook 告警

### v1.4.0 (规划中)
- [ ] **集群部署** - 支持多节点部署
- [ ] **Kubernetes** - 原生 K8s 支持
- [ ] **灰度发布** - 支持 A/B 测试
- [ ] **负载均衡** - 内置负载均衡算法

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

特别感谢所有贡献者和用户！

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！**

Made with ❤️ by Anthropic OpenAI Bridge Team

</div>
