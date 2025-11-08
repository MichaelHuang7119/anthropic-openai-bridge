# 认证和授权系统说明

## 概述

Anthropic OpenAI Bridge 采用双重认证机制，分别用于管理面板和服务 API：

1. **管理面板认证**：邮箱密码登录（JWT Token）
2. **服务 API 认证**：API Key 验证

### 技术实现

- **密码哈希**：使用 `bcrypt` 库直接进行密码哈希和验证（不再使用 passlib）
- **JWT Token**：使用 `python-jose` 库生成和验证 JWT Token
- **API Key 存储**：使用 SQLite 数据库存储，API Key 使用 SHA256 哈希存储
- **认证方式**：使用 FastAPI 的依赖注入系统（`Depends`）进行认证检查

## 管理面板认证

### 登录机制

- **登录方式**：邮箱 + 密码
- **认证方式**：JWT Token（24小时有效期）
- **权限级别**：管理员（is_admin=true）和普通用户（is_admin=false）

### 默认管理员账号

首次启动时，系统会自动创建默认管理员用户：

- **邮箱**：`admin@example.com`（可通过 `ADMIN_EMAIL` 环境变量配置）
- **密码**：`admin123`（可通过 `ADMIN_PASSWORD` 环境变量配置）

**重要提示**：首次登录后请立即修改默认密码！

### 用户管理

#### 创建新用户

只有管理员可以创建新用户：

1. 登录管理界面
2. 访问用户管理页面（或通过 API）
3. 调用 `/api/auth/register` 端点创建新用户

新创建的用户默认不是管理员（`is_admin=false`）。

#### 用户权限

- **管理员用户**：
  - 可以访问所有管理功能
  - 可以创建、编辑、删除供应商
  - 可以创建、管理 API Key
  - 可以查看性能统计
  - 可以创建新用户

- **普通用户**：
  - 可以登录管理界面
  - 可以查看基本信息
  - 无法进行配置修改

### 登录流程

1. 访问前端管理界面（http://localhost:5173）
2. 系统自动跳转到登录页面（如果未登录）
3. 输入邮箱和密码
4. 系统验证后返回 JWT Token
5. Token 存储在 `localStorage` 中
6. 后续请求自动携带 Token

### API 端点

- `POST /api/auth/login` - 用户登录
  ```json
  {
    "email": "admin@example.com",
    "password": "admin123"
  }
  ```

- `POST /api/auth/register` - 注册新用户（需要管理员权限）
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "name": "User Name"
  }
  ```

- `GET /api/auth/me` - 获取当前用户信息（需要管理员权限）

## 服务 API 认证

### API Key 机制

- **认证方式**：API Key（格式：`sk-xxxxxxxxxxxxx`）
- **存储方式**：数据库存储（哈希存储，SHA256）
- **关联信息**：每个 API Key 可以关联用户信息（名称、邮箱）

### 创建 API Key

1. 登录管理界面
2. 访问"API Key 管理"页面
3. 点击"创建 API Key"
4. 填写：
   - **名称**：API Key 的名称（必填）
   - **邮箱**：关联的邮箱（可选）
5. 保存后复制生成的 API Key

**重要提示**：API Key 创建后无法再次查看完整 Key，请妥善保管！

### 使用 API Key

#### 方式 1：HTTP Header（推荐）

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 100
  }'
```

#### 方式 2：查询参数

```bash
curl -X POST "http://localhost:8000/v1/messages?api_key=sk-xxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 100
  }'
```

#### 方式 3：Bearer Token

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 100
  }'
```

### API Key 管理

#### 查看 API Key 列表

登录管理界面，访问"API Key 管理"页面，可以查看：
- API Key 名称
- Key 前缀（用于识别，不显示完整 Key）
- 关联邮箱
- 状态（启用/禁用）
- 最后使用时间
- 创建时间

#### 启用/禁用 API Key

- 点击"启用"或"禁用"按钮
- 禁用的 API Key 无法用于服务 API 认证

#### 删除 API Key

- 点击"删除"按钮
- 删除后该 API Key 立即失效
- 删除操作不可恢复

### API 端点

- `GET /api/api-keys` - 获取所有 API Key 列表（需要管理员权限）
- `GET /api/api-keys/{id}` - 获取指定 API Key 详情（需要管理员权限）
- `POST /api/api-keys` - 创建新 API Key（需要管理员权限）
  ```json
  {
    "name": "生产环境 API Key",
    "email": "user@example.com"
  }
  ```
- `PUT /api/api-keys/{id}` - 更新 API Key（需要管理员权限）
  ```json
  {
    "name": "更新后的名称",
    "email": "new-email@example.com",
    "is_active": true
  }
  ```
- `DELETE /api/api-keys/{id}` - 删除 API Key（需要管理员权限）

## 受保护的端点

### 管理面板端点（需要管理员权限）

以下端点需要管理员权限（JWT Token）：

- `/api/providers/*` - 供应商管理
- `/api/config/*` - 全局配置
- `/api/stats/*` - 性能统计
- `/api/api-keys/*` - API Key 管理
- `/api/auth/register` - 用户注册
- `/api/auth/me` - 获取当前用户信息

### 服务 API 端点（需要 API Key）

以下端点需要 API Key 认证：

- `/v1/messages` - 发送消息请求
- `/v1/messages/count_tokens` - 计算 Token 数量

### 公开端点（无需认证）

以下端点无需认证：

- `/health` - 健康检查
- `/docs` - API 文档
- `/redoc` - API 文档（ReDoc）
- `/openapi.json` - OpenAPI 规范
- `/` - 根端点
- `/api/auth/login` - 登录端点

## 安全最佳实践

### 1. 密码安全

- 使用强密码（至少 12 位，包含大小写字母、数字和特殊字符）
- 定期更换密码
- 不要使用默认密码
- 不要在多个服务中使用相同密码

### 2. API Key 安全

- 妥善保管 API Key，不要泄露
- 定期轮换 API Key
- 为不同环境创建不同的 API Key
- 及时删除不再使用的 API Key
- 不要在代码中硬编码 API Key

### 3. JWT Secret Key

生产环境请务必修改 `JWT_SECRET_KEY` 环境变量：

```bash
export JWT_SECRET_KEY="your-very-secure-random-secret-key-at-least-32-characters"
```

### 4. 数据库安全

- 数据库文件（`backend/data/app.db`）包含敏感信息，请妥善保管
- 定期备份数据库
- 不要将数据库文件提交到版本控制系统

### 5. 环境变量

敏感信息应通过环境变量配置，不要硬编码在代码中：

```bash
# 管理员账号
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="your-secure-password"

# JWT Secret
export JWT_SECRET_KEY="your-jwt-secret-key"

# 供应商 API Key
export QWEN_API_KEY="your-qwen-api-key"
```

## 故障排查

### 问题：401 Unauthorized（登录失败）

**原因**：
- 邮箱或密码错误
- 用户不存在
- 用户账户被禁用

**解决**：
1. 检查邮箱和密码是否正确
2. 确认用户是否存在且处于激活状态
3. 使用默认管理员账号登录（如果忘记密码）

### 问题：401 Unauthorized（API Key 无效）

**原因**：
- API Key 不存在
- API Key 已被禁用
- API Key 格式错误

**解决**：
1. 检查 API Key 是否正确
2. 确认 API Key 是否处于启用状态
3. 检查 API Key 格式（应以 `sk-` 开头）

### 问题：403 Forbidden

**原因**：
- 用户不是管理员
- 尝试访问需要管理员权限的端点

**解决**：
- 使用管理员账号登录
- 或联系管理员授予权限

### 问题：忘记管理员密码

**解决**：
1. 停止后端服务
2. 删除数据库文件：`rm backend/data/app.db`
3. 重启后端服务
4. 使用默认管理员账号登录
5. 立即修改密码

### 问题：API Key 泄露

**解决**：
1. 立即登录管理界面
2. 访问"API Key 管理"页面
3. 找到泄露的 API Key
4. 点击"禁用"或"删除"
5. 创建新的 API Key 替换

## 环境变量配置

### 后端环境变量

```bash
# 默认管理员账号
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123

# JWT Secret Key（生产环境必须修改）
JWT_SECRET_KEY=your-secret-key-change-this-in-production

# 数据库路径
DATABASE_PATH=./data/app.db
```

### Docker 环境变量

在 `docker-compose.yml` 中配置：

```yaml
services:
  backend:
    environment:
      - ADMIN_EMAIL=${ADMIN_EMAIL}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

## 数据库结构

### users 表

存储管理员用户信息：

- `id` - 用户 ID（主键）
- `email` - 邮箱（唯一）
- `password_hash` - 密码哈希（bcrypt）
- `name` - 用户名称
- `is_admin` - 是否为管理员
- `is_active` - 是否激活
- `created_at` - 创建时间
- `updated_at` - 更新时间
- `last_login_at` - 最后登录时间

### api_keys 表

存储 API Key 信息：

- `id` - API Key ID（主键）
- `key_hash` - API Key 哈希（SHA256，唯一）
- `key_prefix` - Key 前缀（用于显示）
- `name` - API Key 名称
- `email` - 关联邮箱
- `user_id` - 关联用户 ID（外键）
- `is_active` - 是否启用
- `last_used_at` - 最后使用时间
- `created_at` - 创建时间
- `updated_at` - 更新时间

## 安全建议

1. **生产环境部署**：
   - 修改默认管理员密码
   - 设置强密码的 `JWT_SECRET_KEY`
   - 使用 HTTPS
   - 限制管理界面访问（防火墙/IP 白名单）

2. **API Key 管理**：
   - 为不同环境创建不同的 API Key
   - 定期轮换 API Key
   - 监控 API Key 使用情况
   - 及时删除不再使用的 API Key

3. **用户管理**：
   - 定期审查用户列表
   - 及时禁用不再使用的账户
   - 使用强密码策略

4. **日志和监控**：
   - 监控登录失败次数
   - 监控 API Key 使用情况
   - 记录重要操作日志
