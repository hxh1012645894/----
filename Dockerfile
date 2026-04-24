# 使用官方 Python 3.12 运行时作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（curl 用于 healthcheck）
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY app.py .

# 复制数据文件（data 基本不变，打包进镜像）
COPY data/ ./data/

# 复制配置文件
COPY element_routing_dictionary_final.json .

# 创建必要目录
RUN mkdir -p uploads database

# 暴露端口
EXPOSE 8000

# 生产环境启动命令：Gunicorn 管理 Uvicorn workers（进程守护 + 自动重启）
CMD ["gunicorn", "app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "300", "--graceful-timeout", "30"]
