"""
事故台账API路由
"""
import os
import json
import uuid
import sqlite3
import urllib.parse
from datetime import datetime
from fastapi import APIRouter, UploadFile, File

from config import DB_FILE, UPLOAD_DIR, logger, CHINA_TZ, ACCIDENT_TYPES
from models import AccidentCreate, AccidentUpdate
from services.ai_service import extract_accident_attachments, call_deepseek_accident_analysis

router = APIRouter(prefix="/api/accidents", tags=["事故台账"])


@router.post("/upload")
async def upload_accident_attachment(files: list[UploadFile] = File(...)):
    """上传事故附件"""
    uploaded_paths = []
    for file in files:
        file_bytes = await file.read()
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{file.filename}"
        save_path = os.path.join(UPLOAD_DIR, safe_filename)
        with open(save_path, "wb") as buffer:
            buffer.write(file_bytes)
        uploaded_paths.append(f"/uploads/{urllib.parse.quote(safe_filename)}")
    return {"status": "success", "data": uploaded_paths}


@router.post("")
async def create_accident(accident: AccidentCreate):
    """创建事故记录"""
    logger.info(f"创建事故记录: {accident.accident_type} @ {accident.location}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO accident_records
        (accident_time, location, accident_type, casualties, description, attachments_json, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (accident.accident_time, accident.location, accident.accident_type,
          accident.casualties, accident.description, json.dumps(accident.attachments, ensure_ascii=False),
          accident.status, now, now))
    accident_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"事故记录创建成功: id={accident_id}")
    return {"status": "success", "data": {"id": accident_id}}


@router.get("")
async def get_accidents():
    """获取事故台账列表"""
    logger.info("查询事故台账列表")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, accident_time, location, accident_type, casualties, status, created_at FROM accident_records ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()

    accidents = []
    for r in rows:
        accidents.append({
            "id": r["id"],
            "accident_time": r["accident_time"],
            "location": r["location"],
            "accident_type": r["accident_type"],
            "casualties": r["casualties"],
            "status": r["status"],
            "created_at": r["created_at"]
        })

    logger.info(f"查询事故台账完成: 共 {len(accidents)} 条记录")
    return {"status": "success", "data": accidents}


@router.get("/types")
async def get_accident_types():
    """获取事故类型列表"""
    return {"status": "success", "data": ACCIDENT_TYPES}


@router.get("/{accident_id}")
async def get_accident_detail(accident_id: int):
    """获取事故详情（含AI分析结果）"""
    logger.info(f"查询事故详情: id={accident_id}")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM accident_records WHERE id = ?', (accident_id,))
    accident = cursor.fetchone()

    if not accident:
        conn.close()
        return {"status": "error", "message": "事故记录不存在"}

    cursor.execute('SELECT * FROM accident_analyses WHERE accident_id = ?', (accident_id,))
    analysis = cursor.fetchone()
    conn.close()

    result = {
        "id": accident["id"],
        "accident_time": accident["accident_time"],
        "location": accident["location"],
        "accident_type": accident["accident_type"],
        "casualties": accident["casualties"],
        "description": accident["description"],
        "attachments": json.loads(accident["attachments_json"] or "[]"),
        "status": accident["status"],
        "created_at": accident["created_at"],
        "submitted_at": accident["submitted_at"],
        "analysis": None
    }

    if analysis:
        result["analysis"] = {
            "direct_cause": analysis["direct_cause"],
            "indirect_cause": analysis["indirect_cause"],
            "lessons_learned": analysis["lessons_learned"],
            "rectification_measures": analysis["rectification_measures"],
            "analysis_time": analysis["analysis_time"]
        }

    logger.info(f"事故详情查询完成: id={accident_id}")
    return {"status": "success", "data": result}


@router.put("/{accident_id}")
async def update_accident(accident_id: int, accident: AccidentUpdate):
    """更新事故记录"""
    logger.info(f"更新事故记录: id={accident_id}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM accident_records WHERE id = ?', (accident_id,))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "事故记录不存在"}

    update_fields = []
    update_values = []

    if accident.accident_time is not None:
        update_fields.append("accident_time = ?")
        update_values.append(accident.accident_time)
    if accident.location is not None:
        update_fields.append("location = ?")
        update_values.append(accident.location)
    if accident.accident_type is not None:
        update_fields.append("accident_type = ?")
        update_values.append(accident.accident_type)
    if accident.casualties is not None:
        update_fields.append("casualties = ?")
        update_values.append(accident.casualties)
    if accident.description is not None:
        update_fields.append("description = ?")
        update_values.append(accident.description)
    if accident.attachments is not None:
        update_fields.append("attachments_json = ?")
        update_values.append(json.dumps(accident.attachments, ensure_ascii=False))

    update_fields.append("updated_at = ?")
    update_values.append(datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S"))
    update_values.append(accident_id)

    sql = f"UPDATE accident_records SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(sql, update_values)
    conn.commit()
    conn.close()

    logger.info(f"事故记录更新成功: id={accident_id}")
    return {"status": "success"}


@router.delete("/{accident_id}")
async def delete_accident(accident_id: int):
    """删除事故记录"""
    logger.info(f"删除事故记录: id={accident_id}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM accident_analyses WHERE accident_id = ?', (accident_id,))
    cursor.execute('DELETE FROM accident_records WHERE id = ?', (accident_id,))

    if cursor.rowcount == 0:
        conn.close()
        logger.warning(f"删除事故失败: id={accident_id} 不存在")
        return {"status": "error", "message": "事故记录不存在"}

    conn.commit()
    conn.close()
    logger.info(f"事故记录删除成功: id={accident_id}")
    return {"status": "success"}


@router.post("/{accident_id}/submit")
async def submit_accident_for_analysis(accident_id: int):
    """提交事故并触发AI分析"""
    logger.info(f"提交事故进行分析: id={accident_id}")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM accident_records WHERE id = ?', (accident_id,))
    accident = cursor.fetchone()

    if not accident:
        conn.close()
        return {"status": "error", "message": "事故记录不存在"}

    if accident["status"] == "submitted":
        conn.close()
        return {"status": "error", "message": "该事故已提交分析"}

    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('UPDATE accident_records SET status = ?, submitted_at = ?, updated_at = ? WHERE id = ?',
                   ('submitted', now, now, accident_id))
    conn.commit()
    conn.close()

    accident_data = {
        "accident_time": accident["accident_time"],
        "location": accident["location"],
        "accident_type": accident["accident_type"],
        "casualties": accident["casualties"],
        "description": accident["description"]
    }

    attachment_content = extract_accident_attachments(accident["attachments_json"])
    analysis_result = call_deepseek_accident_analysis(accident_data, attachment_content)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO accident_analyses
        (accident_id, direct_cause, indirect_cause, lessons_learned, rectification_measures, analysis_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (accident_id, analysis_result["direct_cause"], analysis_result["indirect_cause"],
          analysis_result["lessons_learned"], analysis_result["rectification_measures"], now))
    conn.commit()
    conn.close()

    logger.info(f"事故分析完成: id={accident_id}")
    return {"status": "success", "data": analysis_result}