# ISO 体系智能审核系统 - Docker 部署指南

## 部署架构

本项目采用前后端分离的企业级部署架构：

- **Backend**: Python FastAPI 服务（内部端口 8000）
- **Frontend**: Nginx 静态服务（对外端口 80）

前端 Nginx 作为反向代理，将 `/api/*` 和 `/uploads/*` 请求转发到后端服务。

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 并填入真实密钥：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

**重要**: `.env` 文件包含敏感密钥，已在 `.gitignore` 中排除，**切勿提交到 Git**。

### 2. 一键启动前后端

```bash
docker-compose up -d
```

此命令会：
1. 构建后端 Python 镜像
2. 构建前端（Node 构建 → Nginx 镜像）
3. 启动两个容器并建立内部网络通信
4. 运行时注入 `.env` 密钥到后端容器

### 3. 访问应用

打开浏览器访问：`http://localhost`

### 4. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 只查看后端日志
docker-compose logs -f backend

# 只查看前端日志
docker-compose logs -f frontend
```

### 5. 停止服务

```bash
docker-compose down
```

### 6. 停止并删除数据卷（清除所有数据）

```bash
docker-compose down -v
```

## 数据持久化

使用 Docker Volume 持久化数据：
- `uploads_data` - 上传的待审核文件
- `db_data` - SQLite 数据库文件

查看卷位置：

```bash
docker volume ls
docker volume inspect audit-system_uploads_data
```

## 安全说明

### API 密钥管理

**绝对禁止**将密钥写入 Dockerfile：

```dockerfile
# ❌ 错误做法！镜像推送后密钥会泄露
ENV DEEPSEEK_API_KEY=sk-xxx
```

**正确做法**是通过 `docker-compose.yml` 的 `env_file` 在运行时注入：

```yaml
services:
  backend:
    env_file:
      - .env  # 镜像中不含密钥，容器启动时注入
```

这样镜像可以安全推送到任何 registry，密钥只在你的服务器上存在。

## 备份与迁移

### 备份数据

```bash
# 导出 Docker volumes 数据
docker run --rm -v audit-system_uploads_data:/data -v $(pwd):/backup alpine tar -czf /backup/uploads_backup.tar.gz /data
docker run --rm -v audit-system_db_data:/data -v $(pwd):/backup alpine tar -czf /backup/db_backup.tar.gz /data
```

### 迁移到新服务器

```bash
# 在新服务器上
# 1. 复制项目代码
scp -r . user@new-server:/path/to/audit-system/

# 2. 复制备份数据
scp uploads_backup.tar.gz db_backup.tar.gz user@new-server:/path/to/audit-system/

# 3. 启动容器
cd /path/to/audit-system
docker-compose up -d

# 4. 恢复数据（如需要）
docker run --rm -v audit-system_uploads_data:/data -v $(pwd):/backup alpine tar -xzf /backup/uploads_backup.tar.gz -C /
```

## 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器状态
docker-compose ps
```

### 前端无法访问后端 API

```bash
# 检查网络连通性
docker exec audit-frontend ping backend

# 检查后端健康状态
docker exec audit-backend curl -f http://localhost:8000
```

### 重新构建

```bash
# 强制重新构建镜像
docker-compose build --no-cache

# 重新启动
docker-compose up -d --force-recreate
```

## 端口说明

| 服务 | 内部端口 | 外部端口 |
|------|---------|---------|
| Frontend (Nginx) | 80 | 80 |
| Backend (FastAPI) | 8000 | 不暴露 |

外部用户只通过 Nginx（端口 80）访问，API 请求由 Nginx 内部转发。