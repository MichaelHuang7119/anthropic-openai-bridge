# 使用 Node.js 22 镜像作为构建阶段
FROM node:22 AS builder

# 设置工作目录
WORKDIR /app

# 配置 npm 镜像源（使用国内镜像加速）
RUN npm config set registry https://registry.npmmirror.com/ && \
    npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 5

# 安装 pnpm (锁定版本以支持 lockfileVersion 9.0)
RUN npm install -g pnpm@10.18.3

# 配置 pnpm 镜像源和超时设置
RUN pnpm config set fetch-timeout 300000 && \
    pnpm config set fetch-retries 5 && \
    pnpm config set store-dir /tmp/.pnpm-store

# 复制 package 文件
COPY package.json pnpm-lock.yaml* ./

# 安装依赖（如果主镜像失败，尝试备用镜像）
RUN pnpm --version && \
    echo "Attempting to install with npmmirror.com registry..." && \
    (pnpm config set registry https://registry.npmmirror.com/ && \
     pnpm install --frozen-lockfile --fetch-timeout=300000) || \
    (echo "npmmirror.com failed, trying npmjs.org registry..." && \
     pnpm config set registry https://registry.npmjs.org/ && \
     pnpm install --frozen-lockfile --fetch-timeout=300000)

# 复制应用代码
COPY . .

# 构建应用
# 前端使用相对路径，通过 nginx 代理访问后端
RUN pnpm run build

# 生产阶段：使用 nginx 提供静态文件
FROM nginx:latest

# 设置时区（Debian/Ubuntu 方式）
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai

# 复制构建产物到 nginx
COPY --from=builder /app/build /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
