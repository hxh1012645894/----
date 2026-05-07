"""
AI调用服务：DeepSeek/GLM调用函数
"""
import json
import time
import os
import urllib.parse
import re
from datetime import datetime

from config import deepseek_client, prompt_llm_client, DEEPSEEK_MODEL, PROMPT_LLM_MODEL, UPLOAD_DIR, logger, CHINA_TZ
from database import get_prompt_from_db, DB_FILE
from utils.stats import calculate_inspection_stats
from utils.file_parser import extract_upload_file_text


def clean_and_parse_json(result_text: str) -> dict:
    """清理并解析 JSON，增强容错能力"""
    # 1. 去除代码块标记
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()

    # 2. 处理双花括号
    result_text = result_text.replace("{{", "{").replace("}}", "}")

    # 3. 尝试直接解析
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        pass

    # 4. 修复常见问题：在 } 和 { 之间补充逗号，在键值对之间补充逗号
    # 修复 "...}" 后面紧跟 "{" 的情况
    result_text = re.sub(r'\}\s*\{', '},{', result_text)
    # 修复 "...]" 后面紧跟 "{" 的情况
    result_text = re.sub(r'\]\s*\{', '],{', result_text)
    # 修复字符串结尾缺少引号的情况（简单处理）
    result_text = re.sub(r'"\s*\n', '",\n', result_text)

    # 5. 再次尝试解析
    try:
        return json.loads(result_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        logger.error(f"原始内容前500字符: {result_text[:500]}")
        # 尝试截取第一个完整的 JSON 对象
        match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        raise


def call_deepseek_daily_inspection(evidence_text: str, standard_text: str) -> dict:
    """调用DeepSeek进行日常检查分析"""
    logger.info("=" * 60)
    logger.info("开始调用 DeepSeek 日常检查分析模型...")

    total, completed, rate, top3 = calculate_inspection_stats(evidence_text)

    top3_details = []
    for cat, count in top3:
        percentage = round((count / total * 100), 1) if total > 0 else 0
        top3_details.append(f"{cat}（{count}项，占{percentage}%）")
    top3_str = "、".join(top3_details) if top3_details else "无明显类别"

    logger.info(f"统计信息: 总数={total}, 已完成={completed}, 整改率={rate}%")
    logger.info(f"前三类别: {top3_str}")

    base_prompt = get_prompt_from_db('daily_inspection')
    prompt = base_prompt.replace("{standard_text}", standard_text)\
                        .replace("{evidence_text}", evidence_text)\
                        .replace("{total}", str(total))\
                        .replace("{completed}", str(completed))\
                        .replace("{rate}", str(rate))\
                        .replace("{top3_str}", top3_str)

    try:
        logger.info(f"正在调用 {DEEPSEEK_MODEL} 模型...")
        start_time = time.time()
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        elapsed = time.time() - start_time
        result_text = response.choices[0].message.content.strip()
        logger.info(f"DeepSeek 模型调用成功! 耗时: {elapsed:.2f} 秒")
        logger.info("=" * 60)
        return clean_and_parse_json(result_text)
    except Exception as e:
        logger.error(f"DeepSeek 模型调用失败: {str(e)}")
        logger.info("=" * 60)
        return {"结论": "分析出错", "逻辑缺陷描述": "大模型解析失败", "引用依据": "无", "修改意见": str(e)}


def call_deepseek_audit(standard_text: str, evidence_text: str) -> dict:
    """调用DeepSeek进行审核分析"""
    logger.info("=" * 60)
    logger.info("开始调用 DeepSeek 审核模型...")

    base_prompt = get_prompt_from_db('standard_audit')
    prompt = base_prompt.replace("{standard_text}", standard_text).replace("{evidence_text}", evidence_text)

    try:
        logger.info(f"正在调用 {DEEPSEEK_MODEL} 模型...")
        start_time = time.time()
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        elapsed = time.time() - start_time
        result_text = response.choices[0].message.content.strip()
        logger.info(f"DeepSeek 原始返回内容: {result_text[:500]}")
        logger.info(f"DeepSeek 模型调用成功! 耗时: {elapsed:.2f} 秒")
        logger.info("=" * 60)
        return clean_and_parse_json(result_text)
    except Exception as e:
        logger.error(f"DeepSeek 模型调用失败: {str(e)}")
        logger.info("=" * 60)
        return {"结论": "审核出错", "逻辑缺陷描述": "大模型返回格式解析失败", "引用依据": "无", "修改意见": str(e)}


def improve_prompt_via_ai(current_prompt: str, issues_feedback: str) -> dict:
    """调用智谱AI优化提示词"""
    logger.info("=" * 60)
    logger.info("开始调用智谱 AI 提示词优化...")
    logger.info(f"模型: {PROMPT_LLM_MODEL}")
    logger.info(f"用户反馈: {issues_feedback[:100]}...")

    meta_prompt = f"""
    你是一个顶级的 Prompt Engineering（提示词工程）专家。
    目前系统正在使用以下提示词进行 ISO 体系文档的 AI 审核：

    【当前提示词】：
    {current_prompt}

    业务人员在使用过程中，发现了以下问题或提出了如下改进需求：
    【用户反馈与痛点】：
    {issues_feedback}

    请你帮我重新编写并优化这个提示词，解决用户反馈的问题。
    注意：
    1. 必须保留原有的占位符变量（如 {{standard_text}}, {{evidence_text}} 等），不要修改它们的名字。
    2. 强化系统角色设定和逻辑严密性。
    3. 只需要返回优化后的纯提示词文本，不要包含任何 "```" 代码块标记，也不要解释你的修改过程。
    """

    try:
        logger.info(f"正在调用提示词优化 LLM {PROMPT_LLM_MODEL} 模型...")
        start_time = time.time()
        response = prompt_llm_client.chat.completions.create(
            model=PROMPT_LLM_MODEL,
            messages=[{"role": "user", "content": meta_prompt}],
            temperature=0.3
        )
        elapsed = time.time() - start_time
        optimized_prompt = response.choices[0].message.content.strip()
        logger.info(f"提示词优化 LLM 模型调用成功! 耗时: {elapsed:.2f} 秒")
        logger.info(f"优化后提示词长度: {len(optimized_prompt)} 字符")
        logger.info("=" * 60)
        return {"status": "success", "data": {"optimized_prompt": optimized_prompt}}
    except Exception as e:
        logger.error(f"提示词优化 LLM 模型调用失败: {str(e)}")
        logger.info("=" * 60)
        return {"status": "error", "message": str(e)}


def extract_accident_attachments(attachments_json: str) -> str:
    """提取事故附件内容供AI分析"""
    if not attachments_json:
        return "无附件"

    try:
        paths = json.loads(attachments_json)
        content_parts = []
        for path in paths:
            filename = path.replace("/uploads/", "")
            full_path = os.path.join(UPLOAD_DIR, urllib.parse.unquote(filename))
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    text = extract_upload_file_text(f.read(), filename)
                    if text:
                        content_parts.append(f"【附件：{filename}】\n{text}")
        return "\n\n".join(content_parts) if content_parts else "附件内容提取失败"
    except Exception as e:
        logger.error(f"附件提取失败: {e}")
        return "附件提取失败"


def call_deepseek_accident_analysis(accident_data: dict, attachment_content: str = "") -> dict:
    """调用DeepSeek进行事故根源分析"""
    logger.info("=" * 60)
    logger.info("开始调用 DeepSeek 事故根源分析模型...")

    base_prompt = get_prompt_from_db('accident_analysis')
    prompt = base_prompt.replace("{accident_time}", accident_data.get('accident_time', ''))\
                        .replace("{location}", accident_data.get('location', ''))\
                        .replace("{accident_type}", accident_data.get('accident_type', ''))\
                        .replace("{casualties}", str(accident_data.get('casualties', 0)))\
                        .replace("{description}", accident_data.get('description', ''))\
                        .replace("{attachment_content}", attachment_content)

    try:
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        result_text = response.choices[0].message.content.strip()
        result = clean_and_parse_json(result_text)
        logger.info(f"AI返回原始数据: {result}")
        logger.info("事故根源分析完成!")
        logger.info("=" * 60)

        # 处理整改措施：可能是数组或字符串
        rectification_measures = result.get("整改措施建议", [])
        if isinstance(rectification_measures, list):
            rectification_text = "\n".join([f"{i+1}. {m}" for i, m in enumerate(rectification_measures)])
        else:
            rectification_text = str(rectification_measures or "")
            rectification_measures = []

        return {
            "direct_cause": str(result.get("直接原因分析", "分析完成") or "分析完成"),
            "indirect_cause": str(result.get("间接原因分析", "") or ""),
            "lessons_learned": str(result.get("事故教训总结", "") or ""),
            "rectification_measures": rectification_text,
            "rectification_measures_list": rectification_measures  # 返回数组供后续入库
        }
    except Exception as e:
        logger.error(f"事故分析调用失败: {str(e)}")
        logger.info("=" * 60)
        return {
            "direct_cause": "分析失败",
            "indirect_cause": str(e),
            "lessons_learned": "无",
            "rectification_measures": "请重新提交分析"
        }


def generate_accident_alert(accident_data: dict, analysis_result: dict) -> dict:
    """调用AI生成图文形式的事故警示"""
    logger.info("=" * 60)
    logger.info("开始调用 AI 生成事故警示...")

    base_prompt = get_prompt_from_db('accident_alert')

    # 构建事故基本信息字符串
    accident_info = f"""- 事故类型：{accident_data.get('accident_type', '未知')}
- 发生时间：{accident_data.get('accident_time', '未知')}
- 发生地点：{accident_data.get('location', '未知')}
- 伤亡情况：{accident_data.get('casualties', 0)}人
- 详细描述：{accident_data.get('description', '无')}"""

    # 构建AI分析结果字符串
    analysis_info = f"""- 直接原因：{analysis_result.get('direct_cause', '未分析')}
- 间接原因：{analysis_result.get('indirect_cause', '未分析')}
- 事故教训：{analysis_result.get('lessons_learned', '无')}
- 整改措施：{analysis_result.get('rectification_measures', '无')}"""

    prompt = base_prompt.replace("{accident_data}", accident_info).replace("{analysis_result}", analysis_info)

    try:
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        result_text = response.choices[0].message.content.strip()
        result = clean_and_parse_json(result_text)
        logger.info("事故警示生成完成!")
        logger.info("=" * 60)

        return {
            "alert_title": result.get("alert_title", "事故警示"),
            "alert_content": result.get("alert_content", ""),
            "key_points": result.get("key_points", []),
            "safety_tips": result.get("safety_tips", []),
            "training_requirements": result.get("training_requirements", [])
        }
    except Exception as e:
        logger.error(f"事故警示生成失败: {str(e)}")
        logger.info("=" * 60)
        return {
            "alert_title": f"关于{accident_data.get('accident_type', '')}事故的警示",
            "alert_content": f"在{accident_data.get('location', '')}发生了一起{accident_data.get('accident_type', '')}事故，请各部门引以为戒，加强安全管理。",
            "key_points": ["注意安全操作", "遵守规章制度"],
            "safety_tips": ["定期检查设备", "加强培训教育"],
            "training_requirements": []
        }