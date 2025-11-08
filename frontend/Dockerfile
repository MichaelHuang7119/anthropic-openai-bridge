# 使用 Node.js 18 alpine 镜像作为构建阶段
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 配置 npm 镜像源（使用国内镜像加速）
RUN npm config set registry https://registry.npmmirror.com/ && \
    npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 5

# 安装 pnpm
RUN npm install -g pnpm

# 配置 pnpm 镜像源
RUN pnpm config set registry https://registry.npmmirror.com/

# 复制 package 文件
COPY package.json pnpm-lock.yaml* ./

# 安装依赖（如果主镜像失败，尝试备用镜像）
RUN pnpm install --frozen-lockfile || \
    (pnpm config set registry https://registry.npm.taobao.org/ && \
     pnpm install --frozen-lockfile)

# 复制应用代码
COPY . .

# 构建应用
# 前端使用相对路径，通过 nginx 代理访问后端
RUN pnpm run build

# 生产阶段：使用 nginx 提供静态文件
FROM nginx:alpine

# 复制构建产物到 nginx
COPY --from=builder /app/build /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
