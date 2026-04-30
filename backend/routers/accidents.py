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
from models import (
    AccidentCreate, AccidentUpdate,
    RectificationCreate, RectificationUpdate, RectificationAssign, RectificationComplete,
    AlertCreate, AlertUpdate,
    TrainingCreate, TrainingUpdate
)
from services.ai_service import extract_accident_attachments, call_deepseek_accident_analysis, generate_accident_alert
from utils.ledger_generator import generate_accident_ledger_word, generate_batch_ledger_excel

router = APIRouter(prefix="/api/accidents", tags=["事故台账"])


# ==================== 文件上传 ====================

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


# ==================== 事故记录 CRUD ====================

@router.post("")
async def create_accident(accident: AccidentCreate):
    """创建事故记录"""
    logger.info(f"创建事故记录: {accident.accident_type} @ {accident.location}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO accident_records
        (accident_time, location, accident_type, casualties, description, attachments_json,
         department, engineer_name, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (accident.accident_time, accident.location, accident.accident_type,
          accident.casualties, accident.description, json.dumps(accident.attachments, ensure_ascii=False),
          accident.department, accident.engineer_name, accident.status, now, now))
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
    cursor.execute('''
        SELECT id, accident_time, location, accident_type, casualties, status,
               department, engineer_name, created_at
        FROM accident_records ORDER BY created_at DESC
    ''')
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
            "department": r["department"],
            "engineer_name": r["engineer_name"],
            "created_at": r["created_at"]
        })

    logger.info(f"查询事故台账完成: 共 {len(accidents)} 条记录")
    return {"status": "success", "data": accidents}


# ==================== 事故类型管理 ====================

@router.get("/types")
async def get_accident_types():
    """获取事故类型列表"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM accident_types ORDER BY id')
    types = cursor.fetchall()
    conn.close()
    return {"status": "success", "data": [{"id": t["id"], "type_name": t["type_name"]} for t in types]}


@router.post("/types")
async def create_accident_type(type_name: str):
    """新增事故类型"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO accident_types (type_name) VALUES (?)', (type_name,))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"status": "success", "data": {"id": new_id, "type_name": type_name}}
    except sqlite3.IntegrityError:
        conn.close()
        return {"status": "error", "message": "该事故类型已存在"}


@router.put("/types/{type_id}")
async def update_accident_type(type_id: int, type_name: str):
    """更新事故类型"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE accident_types SET type_name = ? WHERE id = ?', (type_name, type_id))
        if cursor.rowcount == 0:
            conn.close()
            return {"status": "error", "message": "事故类型不存在"}
        conn.commit()
        conn.close()
        return {"status": "success", "data": {"id": type_id, "type_name": type_name}}
    except sqlite3.IntegrityError:
        conn.close()
        return {"status": "error", "message": "该事故类型名称已存在"}


@router.delete("/types/{type_id}")
async def delete_accident_type(type_id: int):
    """删除事故类型"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM accident_types WHERE id = ?', (type_id,))
    if cursor.rowcount == 0:
        conn.close()
        return {"status": "error", "message": "事故类型不存在"}
    conn.commit()
    conn.close()
    return {"status": "success"}


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

    # 查询整改措施
    cursor.execute('SELECT * FROM rectification_measures WHERE accident_id = ? ORDER BY measure_order', (accident_id,))
    measures = cursor.fetchall()

    # 查询事故警示
    cursor.execute('SELECT * FROM accident_alerts WHERE accident_id = ?', (accident_id,))
    alert = cursor.fetchone()

    # 查询培训记录
    cursor.execute('SELECT * FROM training_records WHERE accident_id = ?', (accident_id,))
    trainings = cursor.fetchall()

    conn.close()

    result = {
        "id": accident["id"],
        "accident_time": accident["accident_time"],
        "location": accident["location"],
        "accident_type": accident["accident_type"],
        "casualties": accident["casualties"],
        "description": accident["description"],
        "attachments": json.loads(accident["attachments_json"] or "[]"),
        "department": accident["department"],
        "engineer_name": accident["engineer_name"],
        "status": accident["status"],
        "ledger_generated": accident["ledger_generated"],
        "ledger_path": accident["ledger_path"],
        "created_at": accident["created_at"],
        "submitted_at": accident["submitted_at"],
        "analysis": None,
        "measures": [],
        "alert": None,
        "trainings": []
    }

    if analysis:
        result["analysis"] = {
            "direct_cause": analysis["direct_cause"],
            "indirect_cause": analysis["indirect_cause"],
            "lessons_learned": analysis["lessons_learned"],
            "rectification_measures": analysis["rectification_measures"],
            "analysis_time": analysis["analysis_time"]
        }

    for m in measures:
        result["measures"].append({
            "id": m["id"],
            "measure_content": m["measure_content"],
            "measure_order": m["measure_order"],
            "responsible_person": m["responsible_person"],
            "deadline": m["deadline"],
            "status": m["status"],
            "completion_proof": json.loads(m["completion_proof_json"] or "[]"),
            "completed_at": m["completed_at"],
            "created_at": m["created_at"]
        })

    if alert:
        result["alert"] = {
            "id": alert["id"],
            "alert_title": alert["alert_title"],
            "alert_content": alert["alert_content"],
            "alert_image": alert["alert_image"],
            "notification_manager": alert["notification_manager"],
            "target_departments": json.loads(alert["target_departments_json"] or "[]"),
            "status": alert["status"],
            "created_at": alert["created_at"]
        }

    for t in trainings:
        result["trainings"].append({
            "id": t["id"],
            "training_date": t["training_date"],
            "training_location": t["training_location"],
            "training_content": t["training_content"],
            "trainer_name": t["trainer_name"],
            "attendees_count": t["attendees_count"],
            "sign_sheet_attachment": t["sign_sheet_attachment"],
            "photo_attachments": json.loads(t["photo_attachments_json"] or "[]"),
            "created_at": t["created_at"]
        })

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
    if accident.department is not None:
        update_fields.append("department = ?")
        update_values.append(accident.department)
    if accident.engineer_name is not None:
        update_fields.append("engineer_name = ?")
        update_values.append(accident.engineer_name)

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
    """删除事故记录及其所有相关附件文件"""
    logger.info(f"删除事故记录: id={accident_id}")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 先获取事故附件列表
    cursor.execute('SELECT attachments_json FROM accident_records WHERE id = ?', (accident_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        logger.warning(f"删除事故失败: id={accident_id} 不存在")
        return {"status": "error", "message": "事故记录不存在"}

    # 删除事故附件文件
    attachments_json = row["attachments_json"]
    if attachments_json:
        try:
            attachments = json.loads(attachments_json)
            for attachment_path in attachments:
                if attachment_path.startswith('/uploads/'):
                    filename = attachment_path.replace('/uploads/', '')
                    filepath = os.path.join(UPLOAD_DIR, urllib.parse.unquote(filename))
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        logger.info(f"已删除事故附件: {filepath}")
        except Exception as e:
            logger.warning(f"删除事故附件时出错: {e}")

    # 获取并删除整改措施的完成证明附件
    cursor.execute('SELECT completion_proof_json FROM rectification_measures WHERE accident_id = ?', (accident_id,))
    measure_rows = cursor.fetchall()
    for measure_row in measure_rows:
        completion_proof_json = measure_row["completion_proof_json"]
        if completion_proof_json:
            try:
                completion_proofs = json.loads(completion_proof_json)
                for proof_path in completion_proofs:
                    if proof_path.startswith('/uploads/'):
                        filename = proof_path.replace('/uploads/', '')
                        filepath = os.path.join(UPLOAD_DIR, urllib.parse.unquote(filename))
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            logger.info(f"已删除整改证明附件: {filepath}")
            except Exception as e:
                logger.warning(f"删除整改证明附件时出错: {e}")

    # 获取并删除培训记录的附件
    cursor.execute('SELECT sign_sheet_attachment, photo_attachments_json FROM training_records WHERE accident_id = ?', (accident_id,))
    training_rows = cursor.fetchall()
    for training_row in training_rows:
        # 删除签到表附件
        sign_sheet = training_row["sign_sheet_attachment"]
        if sign_sheet and sign_sheet.startswith('/uploads/'):
            filename = sign_sheet.replace('/uploads/', '')
            filepath = os.path.join(UPLOAD_DIR, urllib.parse.unquote(filename))
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"已删除培训签到表: {filepath}")

        # 删除照片附件
        photo_attachments_json = training_row["photo_attachments_json"]
        if photo_attachments_json:
            try:
                photo_attachments = json.loads(photo_attachments_json)
                for photo_path in photo_attachments:
                    if photo_path.startswith('/uploads/'):
                        filename = photo_path.replace('/uploads/', '')
                        filepath = os.path.join(UPLOAD_DIR, urllib.parse.unquote(filename))
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            logger.info(f"已删除培训照片: {filepath}")
            except Exception as e:
                logger.warning(f"删除培训照片时出错: {e}")

    # 删除数据库记录
    cursor.execute('DELETE FROM rectification_measures WHERE accident_id = ?', (accident_id,))
    cursor.execute('DELETE FROM training_records WHERE accident_id = ?', (accident_id,))
    cursor.execute('DELETE FROM accident_alerts WHERE accident_id = ?', (accident_id,))
    cursor.execute('DELETE FROM accident_analyses WHERE accident_id = ?', (accident_id,))
    cursor.execute('DELETE FROM accident_records WHERE id = ?', (accident_id,))

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

    # 允许重新分析，不再阻止已提交的事故

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
    # 先删除旧的分析结果和整改措施
    cursor.execute('DELETE FROM accident_analyses WHERE accident_id = ?', (accident_id,))
    cursor.execute('DELETE FROM rectification_measures WHERE accident_id = ?', (accident_id,))
    cursor.execute('''
        INSERT INTO accident_analyses
        (accident_id, direct_cause, indirect_cause, lessons_learned, rectification_measures, analysis_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (accident_id, analysis_result["direct_cause"], analysis_result["indirect_cause"],
          analysis_result["lessons_learned"], analysis_result["rectification_measures"], now))

    # 将AI生成的整改措施逐条入库
    measures_list = analysis_result.get("rectification_measures_list", [])
    for idx, measure in enumerate(measures_list, 1):
        if measure and isinstance(measure, str):
            cursor.execute('''
                INSERT INTO rectification_measures (accident_id, measure_content, measure_order, status)
                VALUES (?, ?, ?, 'pending')
            ''', (accident_id, measure.strip(), idx))

    conn.commit()
    conn.close()

    logger.info(f"事故分析完成: id={accident_id}, 生成了 {len(measures_list)} 条整改措施")
    return {"status": "success", "data": analysis_result}


# ==================== 整改措施管理 ====================

@router.get("/{accident_id}/measures")
async def get_measures(accident_id: int):
    """获取事故的整改措施列表"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM rectification_measures WHERE accident_id = ? ORDER BY measure_order', (accident_id,))
    rows = cursor.fetchall()
    conn.close()

    measures = []
    for r in rows:
        measures.append({
            "id": r["id"],
            "measure_content": r["measure_content"],
            "measure_order": r["measure_order"],
            "responsible_person": r["responsible_person"],
            "deadline": r["deadline"],
            "status": r["status"],
            "completion_proof": json.loads(r["completion_proof_json"] or "[]"),
            "completed_at": r["completed_at"],
            "created_at": r["created_at"]
        })

    return {"status": "success", "data": measures}


@router.post("/{accident_id}/measures")
async def add_measure(accident_id: int, measure: RectificationCreate):
    """手动添加整改措施"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO rectification_measures
        (accident_id, measure_content, measure_order, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
    ''', (accident_id, measure.measure_content, measure.measure_order, now))
    measure_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "data": {"id": measure_id}}


@router.put("/{accident_id}/measures/{measure_id}")
async def update_measure(accident_id: int, measure_id: int, measure: RectificationUpdate):
    """编辑整改措施内容"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM rectification_measures WHERE id = ? AND accident_id = ?', (measure_id, accident_id))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "整改措施不存在"}

    update_fields = []
    update_values = []

    if measure.measure_content is not None:
        update_fields.append("measure_content = ?")
        update_values.append(measure.measure_content)
    if measure.measure_order is not None:
        update_fields.append("measure_order = ?")
        update_values.append(measure.measure_order)

    if not update_fields:
        conn.close()
        return {"status": "success"}

    sql = f"UPDATE rectification_measures SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(measure_id)
    cursor.execute(sql, update_values)
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.put("/{accident_id}/measures/{measure_id}/assign")
async def assign_measure(accident_id: int, measure_id: int, assign: RectificationAssign):
    """指派整改责任人和期限"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM rectification_measures WHERE id = ? AND accident_id = ?', (measure_id, accident_id))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "整改措施不存在"}

    cursor.execute('''
        UPDATE rectification_measures
        SET responsible_person = ?, deadline = ?, status = 'in_progress'
        WHERE id = ?
    ''', (assign.responsible_person, assign.deadline, measure_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/{accident_id}/measures/{measure_id}/complete")
async def complete_measure(accident_id: int, measure_id: int, complete: RectificationComplete):
    """完成整改（上传附件）"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM rectification_measures WHERE id = ? AND accident_id = ?', (measure_id, accident_id))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "整改措施不存在"}

    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        UPDATE rectification_measures
        SET status = 'completed', completion_proof_json = ?, completed_at = ?
        WHERE id = ?
    ''', (json.dumps(complete.completion_proof, ensure_ascii=False), now, measure_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/measures/overdue")
async def get_overdue_measures():
    """获取逾期整改措施列表"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        SELECT m.*, a.accident_time, a.location, a.accident_type
        FROM rectification_measures m
        JOIN accident_records a ON m.accident_id = a.id
        WHERE m.status NOT IN ('completed')
        AND m.deadline IS NOT NULL
        AND m.deadline < ?
        ORDER BY m.deadline
    ''', (now,))
    rows = cursor.fetchall()
    conn.close()

    overdue = []
    for r in rows:
        overdue.append({
            "id": r["id"],
            "accident_id": r["accident_id"],
            "measure_content": r["measure_content"],
            "responsible_person": r["responsible_person"],
            "deadline": r["deadline"],
            "status": r["status"],
            "accident_time": r["accident_time"],
            "location": r["location"],
            "accident_type": r["accident_type"]
        })

    return {"status": "success", "data": overdue}


# ==================== 事故警示管理 ====================

@router.get("/{accident_id}/alert")
async def get_alert(accident_id: int):
    """获取事故警示"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM accident_alerts WHERE accident_id = ?', (accident_id,))
    alert = cursor.fetchone()
    conn.close()

    if not alert:
        return {"status": "success", "data": None}

    return {"status": "success", "data": {
        "id": alert["id"],
        "alert_title": alert["alert_title"],
        "alert_content": alert["alert_content"],
        "alert_image": alert["alert_image"],
        "notification_manager": alert["notification_manager"],
        "target_departments": json.loads(alert["target_departments_json"] or "[]"),
        "status": alert["status"],
        "created_at": alert["created_at"]
    }}


@router.post("/{accident_id}/alert/generate")
async def generate_alert(accident_id: int):
    """AI生成事故警示"""
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
    if not analysis:
        conn.close()
        return {"status": "error", "message": "该事故尚未进行AI分析"}

    accident_data = {
        "accident_time": accident["accident_time"],
        "location": accident["location"],
        "accident_type": accident["accident_type"],
        "casualties": accident["casualties"],
        "description": accident["description"]
    }
    analysis_result = {
        "direct_cause": analysis["direct_cause"],
        "indirect_cause": analysis["indirect_cause"],
        "lessons_learned": analysis["lessons_learned"],
        "rectification_measures": analysis["rectification_measures"]
    }

    alert_result = generate_accident_alert(accident_data, analysis_result)

    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO accident_alerts
        (accident_id, alert_title, alert_content, status, created_at)
        VALUES (?, ?, ?, 'draft', ?)
    ''', (accident_id, alert_result["alert_title"], alert_result["alert_content"], now))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"status": "success", "data": {
        "id": alert_id,
        "alert_title": alert_result["alert_title"],
        "alert_content": alert_result["alert_content"],
        "key_points": alert_result.get("key_points", []),
        "safety_tips": alert_result.get("safety_tips", [])
    }}


@router.put("/{accident_id}/alert")
async def update_alert(accident_id: int, alert: AlertUpdate):
    """编辑事故警示"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM accident_alerts WHERE accident_id = ?', (accident_id,))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "事故警示不存在"}

    update_fields = []
    update_values = []

    if alert.alert_title is not None:
        update_fields.append("alert_title = ?")
        update_values.append(alert.alert_title)
    if alert.alert_content is not None:
        update_fields.append("alert_content = ?")
        update_values.append(alert.alert_content)
    if alert.alert_image is not None:
        update_fields.append("alert_image = ?")
        update_values.append(alert.alert_image)
    if alert.notification_manager is not None:
        update_fields.append("notification_manager = ?")
        update_values.append(alert.notification_manager)
    if alert.target_departments is not None:
        update_fields.append("target_departments_json = ?")
        update_values.append(json.dumps(alert.target_departments, ensure_ascii=False))

    if not update_fields:
        conn.close()
        return {"status": "success"}

    sql = f"UPDATE accident_alerts SET {', '.join(update_fields)} WHERE accident_id = ?"
    update_values.append(accident_id)
    cursor.execute(sql, update_values)
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/{accident_id}/alert/send")
async def send_alert(accident_id: int):
    """标记警示已发送"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE accident_alerts SET status = ? WHERE accident_id = ?', ('sent', accident_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


# ==================== 培训记录管理 ====================

@router.get("/{accident_id}/trainings")
async def get_trainings(accident_id: int):
    """获取培训记录列表"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM training_records WHERE accident_id = ? ORDER BY training_date DESC', (accident_id,))
    rows = cursor.fetchall()
    conn.close()

    trainings = []
    for r in rows:
        trainings.append({
            "id": r["id"],
            "training_date": r["training_date"],
            "training_location": r["training_location"],
            "training_content": r["training_content"],
            "trainer_name": r["trainer_name"],
            "attendees_count": r["attendees_count"],
            "sign_sheet_attachment": r["sign_sheet_attachment"],
            "photo_attachments": json.loads(r["photo_attachments_json"] or "[]"),
            "created_at": r["created_at"]
        })

    return {"status": "success", "data": trainings}


@router.post("/{accident_id}/trainings")
async def add_training(accident_id: int, training: TrainingCreate):
    """创建培训记录"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 获取alert_id
    cursor.execute('SELECT id FROM accident_alerts WHERE accident_id = ?', (accident_id,))
    alert = cursor.fetchone()
    alert_id = alert[0] if alert else 0

    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO training_records
        (accident_id, alert_id, training_date, training_location, training_content,
         trainer_name, attendees_count, sign_sheet_attachment, photo_attachments_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (accident_id, alert_id, training.training_date, training.training_location,
          training.training_content, training.trainer_name, training.attendees_count,
          training.sign_sheet_attachment, json.dumps(training.photo_attachments, ensure_ascii=False), now))
    training_id = cursor.lastrowid

    # 更新警示状态为training_completed
    if alert_id:
        cursor.execute('UPDATE accident_alerts SET status = ? WHERE id = ?', ('training_completed', alert_id))

    conn.commit()
    conn.close()
    return {"status": "success", "data": {"id": training_id}}


@router.put("/{accident_id}/trainings/{training_id}")
async def update_training(accident_id: int, training_id: int, training: TrainingUpdate):
    """编辑培训记录"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM training_records WHERE id = ? AND accident_id = ?', (training_id, accident_id))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "培训记录不存在"}

    update_fields = []
    update_values = []

    if training.training_date is not None:
        update_fields.append("training_date = ?")
        update_values.append(training.training_date)
    if training.training_location is not None:
        update_fields.append("training_location = ?")
        update_values.append(training.training_location)
    if training.training_content is not None:
        update_fields.append("training_content = ?")
        update_values.append(training.training_content)
    if training.trainer_name is not None:
        update_fields.append("trainer_name = ?")
        update_values.append(training.trainer_name)
    if training.attendees_count is not None:
        update_fields.append("attendees_count = ?")
        update_values.append(training.attendees_count)
    if training.sign_sheet_attachment is not None:
        update_fields.append("sign_sheet_attachment = ?")
        update_values.append(training.sign_sheet_attachment)
    if training.photo_attachments is not None:
        update_fields.append("photo_attachments_json = ?")
        update_values.append(json.dumps(training.photo_attachments, ensure_ascii=False))

    if not update_fields:
        conn.close()
        return {"status": "success"}

    sql = f"UPDATE training_records SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(training_id)
    cursor.execute(sql, update_values)
    conn.commit()
    conn.close()
    return {"status": "success"}


# ==================== 台账导出 ====================

@router.post("/{accident_id}/ledger/generate")
async def generate_ledger(accident_id: int):
    """自动生成台账Word"""
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
    if not analysis:
        conn.close()
        return {"status": "error", "message": "该事故尚未进行AI分析"}

    cursor.execute('SELECT * FROM rectification_measures WHERE accident_id = ? ORDER BY measure_order', (accident_id,))
    measures = cursor.fetchall()
    conn.close()

    accident_data = {
        "id": accident["id"],
        "accident_time": accident["accident_time"],
        "location": accident["location"],
        "accident_type": accident["accident_type"],
        "casualties": accident["casualties"],
        "description": accident["description"],
        "department": accident["department"],
        "engineer_name": accident["engineer_name"]
    }
    analysis_result = {
        "direct_cause": analysis["direct_cause"],
        "indirect_cause": analysis["indirect_cause"],
        "lessons_learned": analysis["lessons_learned"],
        "rectification_measures": analysis["rectification_measures"]
    }
    measures_data = [{
        "measure_content": m["measure_content"],
        "responsible_person": m["responsible_person"],
        "deadline": m["deadline"],
        "status": m["status"]
    } for m in measures]

    ledger_path = generate_accident_ledger_word(accident_data, analysis_result, measures_data)

    # 更新事故记录
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE accident_records
        SET ledger_generated = 1, ledger_path = ?, updated_at = ?
        WHERE id = ?
    ''', (ledger_path, datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S"), accident_id))
    conn.commit()
    conn.close()

    return {"status": "success", "data": {"ledger_path": ledger_path}}


@router.get("/{accident_id}/ledger/download")
async def download_ledger(accident_id: int):
    """获取台账下载路径"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT ledger_path FROM accident_records WHERE id = ?', (accident_id,))
    accident = cursor.fetchone()
    conn.close()

    if not accident or not accident["ledger_path"]:
        return {"status": "error", "message": "台账尚未生成"}

    return {"status": "success", "data": {"ledger_path": accident["ledger_path"]}}


@router.post("/ledger/export-batch")
async def export_batch_ledger(accident_ids: list[int]):
    """批量导出Excel台账"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    accidents = []
    for id in accident_ids:
        cursor.execute('''
            SELECT a.*, an.direct_cause, an.indirect_cause, an.rectification_measures
            FROM accident_records a
            LEFT JOIN accident_analyses an ON a.id = an.accident_id
            WHERE a.id = ?
        ''', (id,))
        row = cursor.fetchone()
        if row:
            accidents.append({
                "id": row["id"],
                "accident_time": row["accident_time"],
                "location": row["location"],
                "accident_type": row["accident_type"],
                "casualties": row["casualties"],
                "department": row["department"],
                "engineer_name": row["engineer_name"],
                "direct_cause": row["direct_cause"],
                "indirect_cause": row["indirect_cause"],
                "rectification_measures": row["rectification_measures"],
                "status": row["status"]
            })

    conn.close()

    if not accidents:
        return {"status": "error", "message": "没有可导出的事故记录"}

    excel_path = generate_batch_ledger_excel(accidents)
    return {"status": "success", "data": {"excel_path": excel_path}}


# ==================== 整改措施状态管理 ====================

@router.put("/{accident_id}/measures/{measure_id}/status")
async def update_measure_status(accident_id: int, measure_id: int, status_data: dict):
    """更新整改措施状态"""
    new_status = status_data.get("status")
    if new_status not in ["pending", "in_progress", "completed", "overdue"]:
        return {"status": "error", "message": "无效的状态值"}

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM rectification_measures WHERE id = ? AND accident_id = ?', (measure_id, accident_id))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "整改措施不存在"}

    cursor.execute('UPDATE rectification_measures SET status = ? WHERE id = ?', (new_status, measure_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/measures/check-overdue")
async def check_and_mark_overdue():
    """检查并标记逾期整改措施"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # 查询所有已指派但未完成且已逾期的措施
    cursor.execute('''
        SELECT m.id, m.accident_id, m.responsible_person, m.deadline,
               a.accident_type, a.location, a.engineer_name
        FROM rectification_measures m
        JOIN accident_records a ON m.accident_id = a.id
        WHERE m.status IN ('pending', 'in_progress')
        AND m.deadline IS NOT NULL
        AND m.deadline < ?
    ''', (now,))
    overdue_measures = cursor.fetchall()

    marked_count = 0
    for m in overdue_measures:
        cursor.execute('UPDATE rectification_measures SET status = ? WHERE id = ?', ('overdue', m[0]))
        marked_count += 1

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "data": {
            "marked_count": marked_count,
            "overdue_measures": [{
                "id": m[0],
                "accident_id": m[1],
                "responsible_person": m[2],
                "deadline": m[3],
                "accident_type": m[4],
                "location": m[5],
                "engineer_name": m[6]
            } for m in overdue_measures]
        }
    }


@router.delete("/{accident_id}/trainings/{training_id}")
async def delete_training(accident_id: int, training_id: int):
    """删除培训记录及其附件文件"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 先获取培训记录的附件
    cursor.execute('SELECT sign_sheet_attachment, photo_attachments_json FROM training_records WHERE id = ? AND accident_id = ?', (training_id, accident_id))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return {"status": "error", "message": "培训记录不存在"}

    # 删除签到表附件
    sign_sheet = row["sign_sheet_attachment"]
    if sign_sheet and sign_sheet.startswith('/uploads/'):
        filename = sign_sheet.replace('/uploads/', '')
        filepath = os.path.join(UPLOAD_DIR, urllib.parse.unquote(filename))
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"已删除签到表附件: {filepath}")

    # 删除照片附件
    photo_attachments_json = row["photo_attachments_json"]
    if photo_attachments_json:
        try:
            photo_attachments = json.loads(photo_attachments_json)
            for photo_path in photo_attachments:
                if photo_path.startswith('/uploads/'):
                    filename = photo_path.replace('/uploads/', '')
                    filepath = os.path.join(UPLOAD_DIR, urllib.parse.unquote(filename))
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        logger.info(f"已删除照片附件: {filepath}")
        except Exception as e:
            logger.warning(f"删除照片附件时出错: {e}")

    cursor.execute('DELETE FROM training_records WHERE id = ? AND accident_id = ?', (training_id, accident_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


# ==================== 台账在线编辑 ====================

@router.get("/{accident_id}/ledger/content")
async def get_ledger_content(accident_id: int):
    """获取台账内容用于编辑"""
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

    cursor.execute('SELECT * FROM rectification_measures WHERE accident_id = ? ORDER BY measure_order', (accident_id,))
    measures = cursor.fetchall()
    conn.close()

    ledger_content = {
        "basic_info": {
            "accident_time": accident["accident_time"],
            "location": accident["location"],
            "accident_type": accident["accident_type"],
            "casualties": accident["casualties"],
            "department": accident["department"],
            "engineer_name": accident["engineer_name"],
            "description": accident["description"]
        },
        "analysis": None,
        "measures": []
    }

    if analysis:
        ledger_content["analysis"] = {
            "direct_cause": analysis["direct_cause"],
            "indirect_cause": analysis["indirect_cause"],
            "lessons_learned": analysis["lessons_learned"],
            "rectification_measures": analysis["rectification_measures"]
        }

    for m in measures:
        ledger_content["measures"].append({
            "id": m["id"],
            "content": m["measure_content"],
            "responsible_person": m["responsible_person"],
            "deadline": m["deadline"],
            "status": m["status"]
        })

    return {"status": "success", "data": ledger_content}


@router.put("/{accident_id}/ledger/content")
async def update_ledger_content(accident_id: int, content: dict):
    """保存编辑后的台账内容"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 更新基本信息
    basic_info = content.get("basic_info", {})
    if basic_info:
        update_fields = []
        update_values = []
        if "department" in basic_info:
            update_fields.append("department = ?")
            update_values.append(basic_info["department"])
        if "engineer_name" in basic_info:
            update_fields.append("engineer_name = ?")
            update_values.append(basic_info["engineer_name"])
        if "description" in basic_info:
            update_fields.append("description = ?")
            update_values.append(basic_info["description"])
        if update_fields:
            update_fields.append("updated_at = ?")
            update_values.append(datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S"))
            update_values.append(accident_id)
            sql = f"UPDATE accident_records SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, update_values)

    # 更新分析结果
    analysis_info = content.get("analysis", {})
    if analysis_info:
        cursor.execute('''
            UPDATE accident_analyses SET
            direct_cause = ?, indirect_cause = ?, lessons_learned = ?, rectification_measures = ?
            WHERE accident_id = ?
        ''', (
            analysis_info.get("direct_cause"),
            analysis_info.get("indirect_cause"),
            analysis_info.get("lessons_learned"),
            analysis_info.get("rectification_measures"),
            accident_id
        ))

    # 更新整改措施
    measures_list = content.get("measures", [])
    for m in measures_list:
        if m.get("id"):
            cursor.execute('''
                UPDATE rectification_measures SET
                measure_content = ?, responsible_person = ?, deadline = ?
                WHERE id = ? AND accident_id = ?
            ''', (m.get("content"), m.get("responsible_person"), m.get("deadline"), m["id"], accident_id))

    conn.commit()
    conn.close()
    return {"status": "success"}