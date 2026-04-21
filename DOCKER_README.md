# ISO 体系智能审核系统 - Docker 部署指南

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+

## 快速开始

### 1. 构建并启动容器

```bash
# 使用 docker-compose（推荐）
docker-compose up -d

# 或使用 docker build
docker build -t audit-system .
docker run -d -p 8000:8000 --name audit-system -v $(pwd)/data:/app/data -v $(pwd)/uploads:/app/uploads audit-system
```

### 2. 访问应用

打开浏览器访问：`http://localhost:8000`

### 3. 查看日志

```bash
docker-compose logs -f
```

### 4. 停止服务

```bash
docker-compose down
```

### 5. 停止并删除数据卷

```bash
docker-compose down -v
```

## 数据持久化

容器中的以下目录已挂载到主机：
- `./data` - 标准文件数据
- `./uploads` - 上传的待审核文件

这样即使容器重启或重建，数据也不会丢失。

## 环境变量

如需修改配置（如 API 密钥），可以：
1. 直接修改 `app.py` 中的配置
2. 或修改 `docker-compose.yml` 添加环境变量

```yaml
environment:
  - DEEPSEEK_API_KEY=your_api_key_here
```

## 备份与迁移

### 备份数据

```bash
# 备份 data 和 uploads 目录
tar -czf audit-system-backup.tar.gz data uploads audit_batches.db
```

### 迁移到新服务器

```bash
# 在新服务器上
# 1. 复制项目文件和备份数据
scp audit-system-backup.tar.gz user@new-server:/path/to/audit-system/
ssh user@new-server
cd /path/to/audit-system
tar -xzf audit-system-backup.tar.gz

# 2. 启动容器
docker-compose up -d
```

## 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs audit-system

# 检查端口占用
docker-compose ps
```

### 权限问题

```bash
# 确保目录有正确权限
chmod -R 755 data uploads
```
