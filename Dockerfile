# ===========================================
# 后端 Dockerfile - ISO 体系智能审核系统
# ===========================================

# 使用官方 Python 3.12 运行时作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app/backend

# 配置国内 Debian 镜像源（解决网络问题）
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用国内镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple && \
    pip config set global.trusted-host mirrors.aliyun.com

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码（包含 json 字典文件和 data 目录）
COPY backend/ .

# 创建上传目录（.dockerignore 排除了 uploads，需手动创建）
RUN mkdir -p uploads

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
