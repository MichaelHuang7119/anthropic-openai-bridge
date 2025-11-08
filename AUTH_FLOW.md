# 登录验证系统原理详解

## 概述

本项目采用 **JWT (JSON Web Token)** 进行用户认证，这是一种无状态的认证方式。整个系统分为前端和后端两部分，通过 HTTP Header 传递认证信息。

## 核心概念

### 1. JWT Token 简介

JWT 是一种开放标准（RFC 7519），用于在各方之间安全地传输信息。它由三部分组成：

```
Header.Payload.Signature
```

- **Header（头部）**：包含 token 类型和签名算法
- **Payload（载荷）**：包含用户信息（如 user_id, is_admin）和过期时间
- **Signature（签名）**：使用密钥对前两部分进行签名，确保 token 未被篡改

### 2. 密码安全

密码**永远不会**以明文形式存储或传输：
- 存储：使用 `bcrypt` 算法进行哈希
- 传输：通过 HTTPS 加密传输

## 完整登录流程

### 第一步：用户提交登录表单

**前端代码** (`frontend/src/routes/login/+page.svelte`):
```typescript
async function handleSubmit() {
  // 1. 用户输入邮箱和密码
  await authService.login(email, password);
}
```

**前端认证服务** (`frontend/src/lib/services/auth.ts`):
```typescript
async login(email: string, password: string) {
  // 2. 发送 POST 请求到后端
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  // 3. 接收响应（包含 token）
  const data = await response.json();
  
  // 4. 存储 token 到 localStorage
  this.setToken(data.access_token);
  this.setUser(data.user);
}
```

### 第二步：后端验证用户信息

**后端登录端点** (`backend/app/api/auth.py`):
```python
@router.post("/login")
async def login(request: LoginRequest):
    # 1. 从数据库查询用户
    user = await db.get_user_by_email(request.email.lower())
    
    # 2. 验证用户是否存在
    if not user:
        raise HTTPException(401, "Invalid email or password")
    
    # 3. 验证密码（使用 bcrypt 比对哈希值）
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    
    # 4. 检查用户是否激活
    if not user.get("is_active", True):
        raise HTTPException(403, "User account is disabled")
    
    # 5. 创建 JWT Token
    access_token = create_access_token({
        "sub": user["id"],        # 用户 ID（subject）
        "is_admin": user.get("is_admin", False)
    })
    
    # 6. 返回 token 和用户信息
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {...}
    }
```

### 第三步：密码验证原理

**密码哈希** (`backend/app/auth.py`):
```python
def hash_password(password: str) -> str:
    """使用 bcrypt 生成密码哈希"""
    salt = bcrypt.gensalt()  # 生成随机盐值
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

**为什么使用 bcrypt？**
- **加盐（Salt）**：每个密码都有唯一的盐值，防止彩虹表攻击
- **慢速哈希**：故意设计得慢，增加暴力破解成本
- **自适应**：可以调整计算成本，应对硬件进步

### 第四步：JWT Token 创建

**创建 Token** (`backend/app/auth.py`):
```python
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    
    # 1. 将 user_id 转换为字符串（JWT 标准要求）
    to_encode["sub"] = str(to_encode["sub"])
    
    # 2. 设置过期时间（24小时）
    expire = datetime.utcnow() + timedelta(minutes=60*24)
    to_encode["exp"] = expire
    
    # 3. 使用密钥签名（HS256 算法）
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    
    return encoded_jwt
```

**Token 内容示例**：
```json
{
  "sub": "1",           // 用户 ID（字符串格式）
  "is_admin": true,     // 是否为管理员
  "exp": 1762693114     // 过期时间戳（Unix 时间）
}
```

### 第五步：后续请求携带 Token

**前端 API 客户端** (`frontend/src/lib/services/api.ts`):
```typescript
private async request(url: string, options: RequestInit) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  // 从 localStorage 获取 token
  const authHeaders = authService.getAuthHeaders();
  // 结果: { 'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIs...' }
  
  Object.assign(headers, authHeaders);
  
  // 发送请求，自动携带 Authorization header
  const response = await fetch(url, { headers, ...options });
}
```

**HTTP 请求示例**：
```http
GET /api/providers HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### 第六步：后端验证 Token

**依赖注入系统** (`backend/app/auth.py`):
```python
def require_admin():
    """返回一个依赖函数，用于验证管理员权限"""
    async def dependency(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ):
        return await get_current_admin_user(credentials, request)
    return dependency

async def get_current_admin_user(credentials, request):
    # 1. 从 HTTPBearer 提取 token
    if credentials:
        token = credentials.credentials
        
        # 2. 验证 token 签名和过期时间
        user = verify_jwt_token(token)
        
        if user:
            # 3. 从数据库查询用户详细信息
            db = get_database()
            user_data = await db.get_user_by_id(user["user_id"])
            
            # 4. 验证用户是管理员且已激活
            if user_data and user_data.get("is_active") and user_data.get("is_admin"):
                return user_data
    
    # 5. 如果验证失败，抛出 401 错误
    raise HTTPException(401, "Not authenticated")
```

**Token 验证** (`backend/app/auth.py`):
```python
def verify_jwt_token(token: str):
    try:
        # 1. 解码并验证签名（使用相同的 SECRET_KEY）
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        # 2. 提取用户信息
        user_id_str = payload.get("sub")
        is_admin = payload.get("is_admin", False)
        
        # 3. 转换回整数
        user_id = int(user_id_str)
        
        return {
            "user_id": user_id,
            "is_admin": is_admin,
            "type": "jwt"
        }
    except JWTError:
        # Token 无效（签名错误、已过期等）
        return None
```

**FastAPI 依赖注入使用** (`backend/app/api/providers.py`):
```python
@router.get("")
async def get_providers(
    user: dict = Depends(require_admin())  # 自动验证 token
):
    # 如果 token 无效，这里不会执行，直接返回 401
    # 如果 token 有效，user 包含用户信息
    return providerService.getAll()
```

## 安全机制

### 1. Token 存储安全

**前端**：
- Token 存储在 `localStorage` 中
- **注意**：localStorage 可以被 XSS 攻击访问，但本项目是管理后台，风险可控
- 生产环境建议考虑使用 `httpOnly` cookie

### 2. Token 传输安全

- 所有请求通过 HTTPS 传输（生产环境）
- Token 放在 HTTP Header 中，不在 URL 中暴露

### 3. Token 过期机制

- Token 有效期：24 小时
- 过期后需要重新登录
- 前端检测到 401 错误时自动跳转登录页

### 4. 密码安全

- 密码使用 bcrypt 哈希，不可逆
- 每个密码有唯一盐值
- 即使数据库泄露，也无法还原原始密码

## 流程图

```
用户输入邮箱密码
    ↓
前端发送 POST /api/auth/login
    ↓
后端查询数据库
    ↓
验证密码（bcrypt.checkpw）
    ↓
创建 JWT Token（包含 user_id, is_admin, exp）
    ↓
返回 token 给前端
    ↓
前端存储到 localStorage
    ↓
后续请求自动携带 Authorization: Bearer <token>
    ↓
后端验证 token（jwt.decode + 数据库查询）
    ↓
返回请求结果
```

## 关键代码位置

### 前端
- **登录页面**：`frontend/src/routes/login/+page.svelte`
- **认证服务**：`frontend/src/lib/services/auth.ts`
- **API 客户端**：`frontend/src/lib/services/api.ts`

### 后端
- **登录端点**：`backend/app/api/auth.py` (login 函数)
- **认证逻辑**：`backend/app/auth.py`
  - `hash_password()` - 密码哈希
  - `verify_password()` - 密码验证
  - `create_access_token()` - 创建 JWT
  - `verify_jwt_token()` - 验证 JWT
  - `require_admin()` - 管理员权限依赖

## 常见问题

### Q: 为什么 token 中的 sub 必须是字符串？
A: 这是 JWT 标准（RFC 7519）的要求。`sub`（subject）字段必须是字符串类型。

### Q: Token 过期后怎么办？
A: 前端检测到 401 错误时，会自动清除 token 并跳转到登录页。

### Q: 如何防止 token 被窃取？
A: 
1. 使用 HTTPS 传输
2. 设置合理的过期时间
3. 实现 token 刷新机制（可选）
4. 监控异常登录行为

### Q: 为什么密码不能明文存储？
A: 即使数据库被泄露，攻击者也无法直接获取用户密码。bcrypt 哈希是不可逆的。

### Q: 依赖注入是如何工作的？
A: FastAPI 的 `Depends()` 会在请求处理前自动执行依赖函数。如果依赖函数抛出异常，请求会被拒绝。

## 总结

本系统的认证流程：
1. **登录**：验证邮箱密码 → 生成 JWT Token
2. **存储**：前端将 token 存储在 localStorage
3. **携带**：每次请求自动在 Header 中携带 token
4. **验证**：后端验证 token 签名和过期时间 → 查询用户信息 → 检查权限
5. **授权**：根据用户角色返回相应数据

这种设计实现了**无状态认证**，服务器不需要存储 session，适合分布式系统。

