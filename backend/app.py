"""
ISO 体系智能审核系统 API - 主入口
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import UPLOAD_DIR, BACKEND_HOST, BACKEND_PORT
from routers import audit, admin, reports, accidents

# 创建 FastAPI 应用
app = FastAPI(title="ISO 体系智能审核系统 API")

# 静态文件服务
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(audit.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(accidents.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)