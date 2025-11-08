# Anthropic OpenAI Bridge

一个基于 FastAPI 和 Svelte 5 的 AI 模型代理服务，支持多供应商配置和管理。

## 项目简介

Anthropic OpenAI Bridge 是一个高性能的 API 代理服务，它实现了 Anthropic 兼容的 API 端点，并将请求转发到支持 OpenAI 兼容接口的后端供应商（如通义千问、ModelScope、AI Ping 等）。通过统一的 API 接口，您可以轻松切换不同的 AI 模型供应商，而无需修改客户端代码。

本项目提供：
- **Web 管理界面** - 基于 Svelte 5 的现代化管理界面
- **多供应商支持** - 支持多个 AI 供应商，支持优先级回退机制
- **实时监控** - 供应商健康状态实时监控（支持健康、部分健康、不健康、未检查四种状态）
- **可视化配置** - 通过 Web 界面轻松配置供应商和模型
- **流式响应** - 支持 Server-Sent Events (SSE) 流式输出，实时显示 Token 消耗
- **工具调用** - 完整的工具调用（Function Calling）支持
- **多模态输入** - 支持文本和图片输入
- **Token 计数** - 提供 token 计数端点
- **自动模型映射** - 智能模型映射（haiku→small, sonnet→middle, opus→big）
- **全局 Token 限制** - 可配置的全局 max_tokens 限制
- **健康检查** - 内置健康检查端点，支持手动检查模式
- **错误处理** - 完善的错误处理和日志记录
- **自动重试** - 支持超时和连接错误的自动重试机制
- **Toast 消息提示** - 友好的操作反馈提示

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 18+
- npm 或 yarn

### 启动服务

#### 方式一：一键启动（推荐）

```bash
# 在项目根目录运行
# 注意：需要分别启动后端和前端服务

# 终端 1：启动后端
cd backend
bash start.sh

# 终端 2：启动前端
cd frontend
bash start.sh
```

#### 方式二：分别启动

**1. 启动后端服务**
```bash
cd backend
bash start.sh
# 或者直接运行
python start_proxy.py
```

后端将在 http://localhost:8000 启动
- API 文档：http://localhost:8000/docs
- API 规范：http://localhost:8000/redoc

**2. 启动前端服务（新终端）**
```bash
cd frontend
bash start.sh
# 或者指定端口
bash start.sh -- --port 5175
# 或者直接运行
npm install  # 首次运行需要安装依赖
npm run dev
```

前端将在 http://localhost:5173 启动（默认端口，可通过 --port 参数修改）

### 安装依赖（仅后端）

```bash
cd backend
pip install -r requirements.txt
```

### 配置供应商

#### 通过 Web 界面配置（推荐）

1. 启动前端服务后，访问 http://localhost:5173
2. 点击"添加供应商"按钮
3. 填写供应商信息（名称、Base URL、API Key等）
4. 配置模型列表（大、中、小三个类别）
5. 保存配置

#### 通过配置文件

1. 编辑 `backend/provider.json` 文件，配置您的 AI 供应商信息
2. 设置环境变量来存储 API 密钥（推荐方式）

```bash
export QWEN_API_KEY="your-qwen-api-key"
export MODELSCOPE_API_KEY="your-modelscope-api-key"
export AIPING_API_KEY="your-aiping-api-key"
```

在 `backend/provider.json` 中使用环境变量：

```json
{
  "api_key": "${QWEN_API_KEY}"
}
```

### 配置 Claude Code

在 Claude Code 中使用本服务，需要配置以下环境变量：

#### 方式一：在 Claude Code 中配置环境变量

1. 打开 Claude Code 设置
2. 找到环境变量配置（Environment Variables）
3. 添加以下环境变量：

```bash
ANTHROPIC_BASE_URL=http://localhost:5175
ANTHROPIC_API_KEY="any-value"
```

**注意**：`ANTHROPIC_BASE_URL` 需要替换为实际的前端服务地址（如果前端运行在其他端口，请相应修改）。

#### 方式二：通过系统环境变量配置

在启动 Claude Code 之前，设置环境变量：

```bash
export ANTHROPIC_BASE_URL=http://localhost:5175
export ANTHROPIC_API_KEY="any-value"
```

然后启动 Claude Code 进行 Vibe Coding。

**提示**：前端管理界面会显示当前实际的服务地址，方便您配置正确的 `ANTHROPIC_BASE_URL`。

### 环境变量配置

- **MAX_TOKENS_LIMIT**: 全局最大 `max_tokens` 限制（默认: `4096`）
- **MIN_TOKENS_LIMIT**: 全局最小 `max_tokens` 限制（默认: `100`）
- **PROVIDER_CONFIG_PATH**: 供应商配置文件路径（默认: `./provider.json`）
- **HOST**: 服务器绑定地址（默认: `0.0.0.0`）
- **PORT**: 服务器端口（默认: `8000`）
- **LOG_LEVEL**: 日志级别（默认: `info`）

这些限制会应用到所有供应商，所有请求的 `max_tokens` 都会被限制在 `[MIN_TOKENS_LIMIT, MAX_TOKENS_LIMIT]` 范围内。

### 模型映射

项目支持自动模型映射：

- `haiku` → 映射到供应商配置中的 `small` 类别
- `sonnet` → 映射到供应商配置中的 `middle` 类别
- `opus` → 映射到供应商配置中的 `big` 类别

详细的配置说明请参考 [CONFIGURATION.md](./CONFIGURATION.md)。

## 运行服务

### 使用启动脚本（推荐）

```bash
# 默认配置启动（监听 0.0.0.0:8000，启用自动重载）
python start_proxy.py

# 自定义主机和端口
python start_proxy.py --host 127.0.0.1 --port 3000

# 通过环境变量配置
HOST=127.0.0.1 PORT=3000 python start_proxy.py

# 生产环境：禁用自动重载
python start_proxy.py --no-reload

# 自定义日志级别
python start_proxy.py --log-level debug
```

### 启动脚本选项

`start_proxy.py` 脚本支持以下选项：

- `--host HOST`: 绑定主机地址（默认: `0.0.0.0`，或使用 HOST 环境变量）
- `--port PORT`: 绑定端口（默认: `8000`，或使用 PORT 环境变量）
- `--reload`: 启用代码变更自动重载（默认: `True`）
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
│   │   ├── api/               # API 路由
│   │   │   ├── config.py      # 配置管理 API
│   │   │   ├── health.py      # 健康检查 API
│   │   │   └── providers.py   # 供应商管理 API
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── converter.py       # Anthropic ↔ OpenAI 格式转换
│   │   ├── client.py          # OpenAI 客户端封装
│   │   ├── model_manager.py   # 模型选择和供应商管理
│   │   ├── config.py          # 配置管理
│   │   ├── models.py          # 数据模型定义
│   │   ├── retry.py           # 重试机制
│   │   └── utils.py           # 工具函数
│   ├── requirements.txt       # Python 依赖
│   ├── provider.json          # 供应商配置文件（需自行创建）
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
│   │   │   │   └── ProviderForm.svelte
│   │   │   ├── services/      # API 服务层
│   │   │   │   ├── api.ts
│   │   │   │   ├── providers.ts
│   │   │   │   ├── health.ts
│   │   │   │   └── config.ts
│   │   │   ├── stores/        # Svelte 状态管理
│   │   │   │   ├── providers.ts
│   │   │   │   ├── health.ts
│   │   │   │   ├── config.ts
│   │   │   │   └── toast.ts
│   │   │   ├── types/         # TypeScript 类型定义
│   │   │   │   ├── provider.ts
│   │   │   │   ├── health.ts
│   │   │   │   └── config.ts
│   │   │   └── styles/        # 全局样式
│   │   └── routes/            # SvelteKit 路由
│   │       ├── +layout.svelte
│   │       ├── +page.svelte   # 首页（仪表板）
│   │       ├── providers/     # 供应商管理页面
│   │       │   └── +page.svelte
│   │       ├── health/         # 健康监控页面
│   │       │   └── +page.svelte
│   │       └── config/        # 配置页面
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
└── README.md                   # 项目说明文档
```

## 功能特性

### 后端功能

#### 供应商管理 API
- `GET /api/providers` - 获取所有供应商列表
- `GET /api/providers/{name}` - 获取指定供应商详情
- `POST /api/providers` - 创建新供应商
- `PUT /api/providers/{name}` - 更新供应商配置
- `DELETE /api/providers/{name}` - 删除供应商

#### 健康检查 API
- `GET /api/health` - 获取所有供应商健康状态（返回总体状态：健康、部分健康、不健康、未检查）
- `GET /api/health/{name}` - 获取指定供应商健康状态

#### 配置管理 API
- `GET /api/config` - 获取全局配置
- `PUT /api/config` - 更新全局配置

### 前端功能

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
  "providers": {
    "anthropic": {
      "name": "anthropic",
      "type": "anthropic",
      "base_url": "https://api.anthropic.com",
      "api_key": "your-api-key",
      "enabled": true,
      "priority": 1,
      "timeout": 30,
      "models": {
        "big": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
        "middle": ["claude-3-haiku-20240307"],
        "small": []
      }
    },
    "openai": {
      "name": "openai",
      "type": "openai",
      "base_url": "https://api.openai.com",
      "api_key": "your-api-key",
      "enabled": true,
      "priority": 2,
      "timeout": 30,
      "models": {
        "big": ["gpt-4", "gpt-4-turbo"],
        "middle": ["gpt-3.5-turbo"],
        "small": []
      }
    }
  }
}
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `name` | 供应商名称（唯一标识符） |
| `type` | 供应商类型（如 anthropic, openai） |
| `base_url` | API 基础 URL |
| `api_key` | API 密钥 |
| `enabled` | 是否启用该供应商 |
| `priority` | 优先级（数字越小优先级越高） |
| `timeout` | 请求超时时间（秒） |
| `models` | 模型配置，分为大、中、小三个类别 |

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

### 请求流程

1. 客户端向代理服务器发送请求
2. 代理服务器根据配置选择供应商
3. 转发请求到目标供应商 API
4. 接收响应并返回给客户端
5. 前端管理界面实时监控健康状态

## 错误处理

项目提供了完善的错误处理机制：

- **429 Rate Limit Error** - 请求频率超限
- **502 Bad Gateway** - 供应商 API 错误
- **503 Service Unavailable** - 连接错误
- **500 Internal Server Error** - 内部服务器错误

所有错误响应都包含详细的错误信息和供应商名称，便于调试和问题定位。

## 常见问题

### Q: 如何添加新的 AI 供应商？

A: 访问前端管理界面（http://localhost:5173），点击"添加供应商"按钮，填写供应商信息即可。或者手动编辑 `backend/provider.json` 文件。

### Q: 如何实现故障转移？

A: 系统根据 `priority` 字段选择供应商，优先级越高（数字越小）越优先。当高优先级供应商不可用时，自动切换到下一个可用供应商。

### Q: 如何监控供应商健康状态？

A: 访问前端管理界面的"健康监控"页面，点击"刷新状态"按钮进行手动检查。系统会显示总体状态（健康、部分健康、不健康、未检查）和每个供应商的详细信息。健康检查仅在手动点击时进行，不会自动请求，最大化节省 API 调用和 Token 消耗。

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
QWEN_API_KEY=your-qwen-api-key
MODELSCOPE_API_KEY=your-modelscope-api-key
AIPING_API_KEY=your-aiping-api-key
MAX_TOKENS_LIMIT=4096
MIN_TOKENS_LIMIT=100
```

然后在 `docker-compose.yml` 中添加：

```yaml
services:
  backend:
    environment:
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
# 将 dist 目录部署到 Web 服务器
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

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
