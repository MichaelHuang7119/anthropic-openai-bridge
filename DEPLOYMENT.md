# 部署文档

本文档说明如何部署 Anthropic OpenAI Bridge。

## 快速开始

### Docker Compose（开发/测试）

```bash
docker-compose up -d
```

### Kubernetes（生产环境）

参考 [k8s/README.md](./k8s/README.md)

## 环境变量配置

### 必需变量

```bash
# JWT 密钥（必需）
export JWT_SECRET_KEY="your-strong-secret-key-here"

# 加密密钥（推荐）
export ENCRYPTION_KEY="your-fernet-encryption-key-here"

# 管理员密码（推荐，至少 12 字符）
export ADMIN_PASSWORD="your-strong-admin-password-here"
```

### 性能优化变量

```bash
# 数据库连接池
export DB_POOL_SIZE=20
export DB_POOL_TIMEOUT=30.0

# HTTP 连接池
export HTTP_MAX_KEEPALIVE_CONNECTIONS=100
export HTTP_MAX_CONNECTIONS=500
export HTTP_KEEPALIVE_EXPIRY=60

# 缓存配置
export CACHE_TYPE=multi
export CACHE_MULTI_LEVEL=true
export REDIS_URL=redis://localhost:6379/0
export CACHE_MAX_SIZE=1000
export CACHE_DEFAULT_TTL=3600
```

### 监控配置（可选）

```bash
export ENABLE_TELEMETRY=true
export OTLP_ENDPOINT=http://jaeger:4318
export SERVICE_VERSION=1.0.0
```

## 前端 PWA 配置

前端已配置为 PWA，支持：

- 离线访问
- 安装到主屏幕
- 后台同步

首次访问时会自动注册 Service Worker。

## CI/CD

项目配置了 GitHub Actions CI/CD 流水线：

1. **测试阶段**：自动运行后端和前端测试
2. **构建阶段**：自动构建 Docker 镜像
3. **部署阶段**：自动部署到 Kubernetes（仅 main 分支）

### 配置 CI/CD

1. 在 GitHub 仓库设置中添加以下 Secrets：
   - `KUBECONFIG`：Kubernetes 配置文件（base64 编码）

2. 修改 `.github/workflows/ci-cd.yml` 中的镜像仓库地址

3. 修改 `k8s/*.yaml` 中的镜像地址

## 性能测试

运行压力测试：

```bash
# 安装依赖
pip install aiohttp

# 运行测试（目标 10k QPS）
python scripts/load_test.py --url http://localhost:5175 --qps 10000 --duration 60
```

## 监控

### OpenTelemetry

如果启用了 OpenTelemetry，可以通过以下方式查看追踪和指标：

1. **Jaeger**：查看分布式追踪
2. **Prometheus**：查看指标（需要配置 Prometheus exporter）

### 健康检查

- 后端：`http://localhost:8000/health`
- 前端：`http://localhost:5175/`

## 故障排查

### 数据库问题

检查数据库文件权限和路径：

```bash
ls -la backend/data/
```

### Redis 连接问题

检查 Redis 是否运行：

```bash
redis-cli ping
```

### 性能问题

1. 检查连接池配置
2. 查看 OpenTelemetry 追踪
3. 运行压力测试

## 安全建议

1. **生产环境必须设置**：
   - `JWT_SECRET_KEY`
   - `ENCRYPTION_KEY`
   - `ADMIN_PASSWORD`

2. **使用 HTTPS**：配置 TLS/SSL 证书

3. **限制访问**：使用防火墙或 Ingress 规则

4. **定期更新**：保持依赖和系统更新

5. **密钥管理**：使用密钥管理服务（如 Kubernetes Secrets、HashiCorp Vault）

