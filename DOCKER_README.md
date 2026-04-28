# ISO 体系智能审核系统 - Docker 部署指南

## 项目结构

```
审核系统/
├── backend/                # 后端模块化代码
│   ├── app.py             # 主入口
│   ├── config.py          # 配置模块
│   ├── database.py        # 数据库模块
│   ├── models.py          # 数据模型
│   ├── routers/           # API路由
│   ├── services/          # AI服务
│   └── utils/             # 工具函数
├── frontend/               # 前端Vue项目
│   ├── src/               # 源代码
│   ├── Dockerfile         # 前端镜像
│   └── nginx.conf         # Nginx配置
├── data/                   # ISO标准文件
├── Dockerfile              # 后端镜像
├── docker-compose.yml      # 容器编排
├── .env                    # 环境变量（敏感）
├── .env.example            # 环境变量示例
└── requirements.txt        # Python依赖
```

## 部署架构

- **Backend**: Python FastAPI 服务（内部端口 8000）
- **Frontend**: Nginx 静态服务（对外端口 8081）

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
docker-compose up -d --build
```

此命令会：
1. 构建后端 Python 镜像
2. 构建前端（Node 构建 → Nginx 镜像）
3. 启动两个容器并建立内部网络通信
4. 运行时注入 `.env` 密钥到后端容器

### 3. 访问应用

打开浏览器访问：`http://localhost:8081`

### 4. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 只查看后端日志
docker-compose logs -f backend

# 只查看前端日志
docker-compose logs -f frontend
```

### 5. 常用操作

```bash
# 停止服务
docker-compose down

# 停止并删除数据卷（清除所有数据）
docker-compose down -v

# 强制重新构建镜像
docker-compose build --no-cache

# 重新启动
docker-compose up -d --force-recreate
```

## 数据持久化

使用 Docker Volume 持久化数据：
- `uploads_data` - 上传的待审核文件
- `db_data` - SQLite 数据库文件

查看卷位置：

```bash
docker volume ls
docker volume inspect audit-project_uploads_data
```

## 端口说明

| 服务 | 内部端口 | 外部端口 |
|------|---------|---------|
| Frontend (Nginx) | 80 | 8081 |
| Backend (FastAPI) | 8000 | 不暴露 |

外部用户只通过 Nginx（端口 8081）访问，API 请求由 Nginx 内部转发。

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

## 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend

# 检查容器状态
docker-compose ps

# 检查后端健康状态
docker exec audit-backend curl -f http://localhost:8000
```

### 前端无法访问后端 API

```bash
# 检查网络连通性
docker exec audit-frontend ping backend

# 测试API
curl http://localhost:8081/api/accidents/types
```

### 数据库问题

```bash
# 查看数据库文件
docker exec audit-backend ls -la /app/database/

# 进入容器调试
docker exec -it audit-backend bash
```

## 本地开发

本地开发时，前后端分开运行：

```bash
# 后端
cd backend && python app.py

# 前端
cd frontend && npm run dev
```

前端开发服务器会自动代理API请求到后端（见 vite.config.js）。