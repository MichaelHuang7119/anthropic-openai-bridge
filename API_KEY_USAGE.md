# API Key 使用说明

## API Key 格式

API Key 采用以下格式：
- **前缀**：`sk-`
- **长度**：32 字节随机数据（64 个十六进制字符）
- **示例**：`sk-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3`

## API Key 生成

后端使用 `generate_api_key()` 函数生成 API Key：

```python
def generate_api_key() -> str:
    """Generate a new API key."""
    # Generate a secure random key: sk-{32 random bytes in hex}
    random_bytes = secrets.token_bytes(32)
    return f"sk-{random_bytes.hex()}"
```

- 使用 `secrets.token_bytes(32)` 生成 32 字节的加密安全随机数
- 转换为十六进制字符串（64 个字符）
- 添加 `sk-` 前缀

## API Key 存储

- **完整 Key**：只在创建时返回一次，之后无法再次查看
- **哈希存储**：数据库中存储的是 SHA256 哈希值，不是原始 Key
- **前缀显示**：列表中只显示 `sk-{前8个字符}...` 格式的前缀

## API Key 使用方式

调用服务 API（如 `/v1/messages`）时，可以通过以下三种方式传递 API Key：

### 方式 1：X-API-Key Header（推荐）

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 方式 2：Query Parameter

```bash
curl -X POST "http://localhost:8000/v1/messages?api_key=sk-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 方式 3：Authorization Bearer Header（向后兼容）

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## 认证流程

### 1. 创建 API Key

**管理面板** → **API Key 管理** → **创建 API Key**

- 输入名称（必填）
- 输入邮箱（可选）
- 点击创建
- **重要**：立即复制完整 Key，创建后无法再次查看

### 2. 使用 API Key

在调用服务 API 时，将 API Key 放在请求头或查询参数中：

```python
import requests

api_key = "sk-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3"

response = requests.post(
    "http://localhost:8000/v1/messages",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": api_key
    },
    json={
        "model": "claude-3-5-sonnet-20241022",
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }
)
```

### 3. 后端验证流程

```python
async def get_current_api_user(request: Request):
    # 1. 尝试从 X-API-Key header 获取
    api_key = request.headers.get("X-API-Key")
    if api_key:
        api_key_data = await verify_api_key(api_key)
        if api_key_data:
            return api_key_data
    
    # 2. 尝试从 query parameter 获取
    api_key = request.query_params.get("api_key")
    if api_key:
        api_key_data = await verify_api_key(api_key)
        if api_key_data:
            return api_key_data
    
    # 3. 尝试从 Authorization Bearer header 获取
    # （如果 token 以 sk- 开头）
    
    # 验证失败，返回 401
    raise HTTPException(401, "API key required")
```

### 4. API Key 验证

```python
async def verify_api_key(api_key: str):
    # 1. 计算 API Key 的 SHA256 哈希
    key_hash = hash_api_key(api_key)  # SHA256(api_key)
    
    # 2. 从数据库查询匹配的哈希值
    api_key_data = await db.get_api_key_by_hash(key_hash)
    
    # 3. 检查 Key 是否存在且已激活
    if api_key_data and api_key_data.get("is_active"):
        # 4. 更新最后使用时间
        await db.update_api_key_last_used(api_key_data["id"])
        return api_key_data
    
    return None
```

## 安全特性

1. **哈希存储**：数据库中只存储 SHA256 哈希值，即使数据库泄露也无法还原原始 Key
2. **一次性显示**：完整 Key 只在创建时返回一次
3. **激活控制**：可以禁用 API Key，无需删除
4. **使用追踪**：记录最后使用时间
5. **前缀显示**：列表中只显示前缀，保护完整 Key

## 管理功能

### 查看列表
- 显示所有 API Key 的前缀、名称、邮箱、状态、创建时间、最后使用时间

### 编辑
- 修改名称
- 修改邮箱
- 启用/禁用状态

### 删除
- 永久删除 API Key
- 删除后立即失效，无法恢复

## 注意事项

1. **妥善保管**：API Key 创建后请立即复制并妥善保管
2. **不要泄露**：不要在代码仓库、日志、公开文档中暴露 API Key
3. **定期轮换**：建议定期创建新的 API Key 并删除旧的
4. **最小权限**：为不同用途创建不同的 API Key
5. **监控使用**：定期检查 API Key 的使用情况

## 示例代码

### Python

```python
import requests

API_KEY = "sk-your-api-key-here"
BASE_URL = "http://localhost:8000"

def call_messages_api(messages):
    response = requests.post(
        f"{BASE_URL}/v1/messages",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        json={
            "model": "claude-3-5-sonnet-20241022",
            "messages": messages
        }
    )
    return response.json()
```

### JavaScript/TypeScript

```typescript
const API_KEY = "sk-your-api-key-here";
const BASE_URL = "http://localhost:8000";

async function callMessagesAPI(messages: any[]) {
  const response = await fetch(`${BASE_URL}/v1/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY
    },
    body: JSON.stringify({
      model: "claude-3-5-sonnet-20241022",
      messages: messages
    })
  });
  return await response.json();
}
```

### cURL

```bash
export API_KEY="sk-your-api-key-here"
export BASE_URL="http://localhost:8000"

curl -X POST "${BASE_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

