"""
审核API路由
"""
import os
import uuid
import urllib.parse
from fastapi import APIRouter, UploadFile, File, Form
from typing import List

from config import UPLOAD_DIR, routing_dict, logger
from database import DB_FILE, get_prompt_from_db
from utils.file_parser import extract_text_via_textin, extract_upload_file_text, get_standard_document_content
from utils.matching import loose_match_sub_element
from services.ai_service import call_deepseek_audit, call_deepseek_daily_inspection

router = APIRouter(prefix="/api", tags=["审核"])


@router.post("/audit")
async def audit_files(
    major_element: str = Form(""),
    audit_mode: str = Form("standard"),
    files: List[UploadFile] = File(...)
):
    """审核文件"""
    logger.info("=" * 60)
    logger.info(f"收到文件审核请求: mode={audit_mode}, element={major_element}, files={len(files)} 个")
    results = []

    for file in files:
        file_bytes = await file.read()
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{file.filename}"
        save_path = os.path.join(UPLOAD_DIR, safe_filename)
        with open(save_path, "wb") as buffer:
            buffer.write(file_bytes)
        file_preview_path = f"/uploads/{urllib.parse.quote(safe_filename)}"

        if file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            evidence_text = extract_text_via_textin(file_bytes)
        else:
            evidence_text = extract_upload_file_text(file_bytes, file.filename)

        if "解析失败" in evidence_text or len(evidence_text.strip()) < 5:
            results.append({
                "文件名": file.filename,
                "匹配标准": "解析失败",
                "提取字数": len(evidence_text),
                "审核结果": {
                    "结论": "不符合",
                    "逻辑缺陷描述": "文件解析失败或提取内容过短，无法判断",
                    "引用依据": "无",
                    "修改意见": "请检查文件是否损坏，或图像是否清晰。"
                },
                "原文": evidence_text,
                "原文件在线地址": file_preview_path
            })
            continue

        if audit_mode == "daily_inspection":
            target_element = "8.1要素"
            major_file_name = routing_dict.get(target_element, {}).get("主要素文件", "EHSMS-8.1运行控制")
            standard_text = get_standard_document_content(target_element, major_file_name)
            llm_result = call_deepseek_daily_inspection(evidence_text, standard_text)

            results.append({
                "文件名": file.filename,
                "要素": target_element,
                "审核文件": "日常检查台账分析",
                "提取字数": len(evidence_text),
                "是否符合": True,
                "审核结果": llm_result,
                "原文": evidence_text,
                "原文件在线地址": file_preview_path
            })
        else:
            matched_rule = loose_match_sub_element(major_element, file.filename)
            standard_text = get_standard_document_content(major_element, matched_rule)
            llm_result = call_deepseek_audit(standard_text, evidence_text)

            is_pass = (llm_result.get("结论") == "符合")
            results.append({
                "文件名": file.filename, "要素": major_element, "审核文件": matched_rule, "提取字数": len(evidence_text),
                "是否符合": is_pass,
                "审核结果": llm_result,
                "原文": evidence_text,
                "原文件在线地址": file_preview_path
            })

    logger.info(f"审核完成! 共处理 {len(results)} 个文件")
    logger.info("=" * 60)
    return {"status": "success", "data": results}