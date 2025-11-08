# 开发模式说明

## 概述

开发模式允许在本地开发时无需提供有效的 API Key 即可访问服务 API。在开发模式下，**不进行任何 API Key 验证**，可以完全不提供 API Key，或者提供任意字符串作为 API Key。

## 启用方式

### 方式 1：使用命令行参数（推荐）

```bash
cd backend
./start.sh --dev
```

或者直接使用 Python：

```bash
cd backend
python start_proxy.py --dev
```

### 方式 2：使用环境变量

```bash
export DEV_MODE=true
cd backend
./start.sh
```

或者在启动时设置：

```bash
DEV_MODE=true ./start.sh
```

## 开发模式行为

### 完全跳过验证

在开发模式下：
- **不进行任何 API Key 验证**
- **不检查 API Key 是否存在**
- **不检查 API Key 是否有效**
- **不检查 API Key 是否激活**

### 允许的情况

以下所有情况都会被允许：

1. **不提供 API Key**：完全省略 `X-API-Key` header
2. **空字符串**：`X-API-Key: `（空值）
3. **任意字符串**：`X-API-Key: anything`、`X-API-Key: dev`、`X-API-Key: test123` 等
4. **无效的 API Key**：即使提供了无效的 API Key，也会直接允许访问

### 重要区别

**开发模式**：完全不验证，直接允许访问  
**生产模式**：必须提供有效的 API Key，否则返回 401 错误

## 前端配置（客户端调用）

如果您的客户端（如 Claude Code、其他应用）需要通过环境变量配置 API 端点，在开发模式下可以这样设置：

### 环境变量配置

```bash
# 设置 API 基础 URL（前端开发服务器地址）
export ANTHROPIC_BASE_URL=http://localhost:5176

# 设置 API Key（开发模式下可以是任意值）
export ANTHROPIC_API_KEY="any-value"
```

### 说明

- **ANTHROPIC_BASE_URL**：指向前端开发服务器地址（`http://localhost:5176`）
  - 前端服务器会将 `/v1/*` 请求代理到后端（`http://localhost:8000`）
  - 这样客户端可以直接访问前端地址，无需知道后端地址

- **ANTHROPIC_API_KEY**：在开发模式下可以是任意值
  - `"any-value"`、`"dev"`、`"test"` 等任意字符串都可以
  - 或者设置为空字符串 `""`
  - 后端在开发模式下不会验证这个值

### 完整开发环境设置示例

```bash
# 终端 1：启动后端（开发模式）
cd backend
./start.sh --dev

# 终端 2：启动前端
cd frontend
./start.sh

# 终端 3：设置客户端环境变量并运行客户端
export ANTHROPIC_BASE_URL=http://localhost:5176
export ANTHROPIC_API_KEY="any-value"
# 然后运行您的客户端应用
```

### 验证配置

您可以使用 curl 测试：

```bash
# 设置环境变量
export ANTHROPIC_BASE_URL=http://localhost:5176
export ANTHROPIC_API_KEY="any-value"

# 测试 API 调用
curl -X POST $ANTHROPIC_BASE_URL/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ANTHROPIC_API_KEY" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 注意事项

1. **前端代理**：前端服务器（`localhost:5176`）会将 `/v1/*` 和 `/api/*` 请求代理到后端（`localhost:8000`）
2. **开发模式**：确保后端已启用开发模式（`--dev` 或 `DEV_MODE=true`）
3. **生产环境**：在生产环境中，`ANTHROPIC_API_KEY` 必须是有效的 API Key

## 使用示例

### 不使用 API Key

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 使用任意字符串作为 API Key

```bash
# 使用 "dev"
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  -d '{"model": "claude-3-5-sonnet-20241022", "messages": [{"role": "user", "content": "Hello"}]}'

# 使用 "test"
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test" \
  -d '{"model": "claude-3-5-sonnet-20241022", "messages": [{"role": "user", "content": "Hello"}]}'

# 使用空字符串
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: " \
  -d '{"model": "claude-3-5-sonnet-20241022", "messages": [{"role": "user", "content": "Hello"}]}'
```

## 安全警告

⚠️ **重要**：开发模式会完全禁用 API Key 验证，**绝对不要在生产环境使用**！

启动时会显示警告信息：
```
⚠️  WARNING: Development mode is enabled. API Key authentication is disabled!
```

## 生产环境

在生产环境中：
- **不要**使用 `--dev` 参数
- **不要**设置 `DEV_MODE=true` 环境变量
- **必须**提供有效的 API Key

生产模式下，如果 API Key 无效或缺失，会立即返回 `401 Unauthorized` 错误。

## 检查当前模式

启动服务器时，会显示当前模式：

```
🚀 Starting Anthropic OpenAI Bridge Server
   Host: 0.0.0.0
   Port: 8000
   Provider Config: ./provider.json
   Auto-reload: Enabled
   Log level: info
   Development Mode: ✅ Enabled (API Key not required)
   ⚠️  WARNING: Development mode is enabled. API Key authentication is disabled!
```

或者：

```
   Development Mode: ❌ Disabled (API Key required)
```

## 日志

在开发模式下，会记录以下日志：

- **允许访问**：`Development mode: Allowing access without API key validation`

## 常见问题

### Q: 开发模式会影响管理面板的认证吗？

A: 不会。开发模式只影响服务 API（`/v1/messages` 等），不影响管理面板的 JWT Token 认证。

### Q: 开发模式下可以使用真实的 API Key 吗？

A: 可以，但不会验证。开发模式下，无论提供什么 API Key（包括真实的），都不会进行验证，直接允许访问。

### Q: 如何确保生产环境不会意外启用开发模式？

A: 
1. 检查启动脚本，确保没有 `--dev` 参数
2. 检查环境变量，确保 `DEV_MODE` 未设置或为 `false`
3. 启动时会显示当前模式，检查日志确认

### Q: 开发模式下的用户信息是什么？

A: 开发模式下返回的用户信息：
```python
{
    "api_key_id": None,
    "name": "dev-user",
    "email": None,
    "user_id": None,
    "type": "dev"
}
```

## 技术实现

开发模式通过以下方式实现：

1. **环境变量检查**：`DEV_MODE` 环境变量或 `--dev` 命令行参数
2. **早期返回**：在 `get_current_api_user()` 函数中，如果 `DEV_MODE` 为 `True`，直接返回开发用户信息，**不进行任何验证**
3. **日志记录**：记录开发模式下的访问，便于调试和审计

## 性能优势

开发模式下跳过验证带来的优势：
- **更快的响应**：不需要查询数据库验证 API Key
- **更简单的测试**：不需要创建和管理测试用的 API Key
- **更灵活的调试**：可以快速测试不同的场景


