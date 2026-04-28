# ===========================================
# 后端 Dockerfile - ISO 体系智能审核系统
# ===========================================

# 使用官方 Python 3.12 运行时作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app/backend

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY backend/ .

# 复制数据文件和配置文件到上级目录
COPY data/ /app/data/
COPY element_routing_dictionary_final.json /app/

# 创建上传和数据库目录
RUN mkdir -p /app/uploads /app/database

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8000 || exit 1

# 生产环境启动命令：Gunicorn + Uvicorn workers
CMD ["gunicorn", "app:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
