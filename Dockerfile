# 使用官方 Python 3.12 运行时作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY app.py .

# 复制数据文件（data 基本不变，打包进镜像）
COPY data/ ./data/

# 复制配置文件
COPY element_routing_dictionary_final.json .

# 创建必要目录
RUN mkdir -p uploads data

# 暴露端口
EXPOSE 8000

# 运行应用
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
