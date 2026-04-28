"""
管理后台API路由
"""
import json
import sqlite3
from datetime import datetime
from fastapi import APIRouter

from config import routing_dict, logger, PROMPT_LLM_MODEL, CHINA_TZ, ROUTING_DICT_PATH
from database import DB_FILE
from models import PromptUpdate, AIImproveRequest
from services.ai_service import improve_prompt_via_ai

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/prompts")
async def get_all_prompts():
    """获取所有提示词"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM system_prompts')
    rows = cursor.fetchall()
    conn.close()
    return {"status": "success", "data": [dict(r) for r in rows]}


@router.put("/prompts/{prompt_key}")
async def update_prompt(prompt_key: str, payload: PromptUpdate):
    """更新提示词"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE system_prompts SET content = ?, updated_at = ? WHERE prompt_key = ?",
                   (payload.content, datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S"), prompt_key))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/prompts/improve")
async def improve_prompt(payload: AIImproveRequest):
    """AI优化提示词"""
    return improve_prompt_via_ai(payload.current_prompt, payload.issues_feedback)


@router.get("/dictionary")
async def get_dictionary():
    """获取匹配字典"""
    with open(ROUTING_DICT_PATH, "r", encoding="utf-8") as f:
        return {"status": "success", "data": json.load(f)}


@router.post("/dictionary")
async def save_dictionary(payload: dict):
    """保存匹配字典"""
    # 动态更新全局变量和文件
    routing_dict.clear()
    routing_dict.update(payload)
    with open(ROUTING_DICT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)
    return {"status": "success"}