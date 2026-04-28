"""
文件解析工具：docx/pdf/xlsx/csv/OCR解析
"""
import os
import io
import csv
import docx
import openpyxl
import pdfplumber
import requests
from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph

from config import TEXTIN_APP_ID, TEXTIN_SECRET_CODE, DATA_DIR, logger


def iter_block_items(parent):
    """
    深度解析 Word 底层 XML 树，严格按照从上到下的物理顺序生成段落和表格。
    """
    if isinstance(parent, DocxDocument):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("不支持的节点类型")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def parse_docx_in_order(file_stream) -> str:
    """顺序解析 Docx 为 Markdown"""
    doc = docx.Document(file_stream)
    content = []
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.replace('\n', ' ').strip()
            if text:
                content.append(text)
        elif isinstance(block, Table):
            content.append("\n")
            for i, row in enumerate(block.rows):
                row_data = [cell.text.replace('\n', ' ').replace('\r', '').strip() for cell in row.cells]
                content.append("| " + " | ".join(row_data) + " |")
                if i == 0:
                    content.append("|" + "|".join(["---"] * len(row.cells)) + "|")
            content.append("\n")
    return "\n".join(content)


def parse_pdf_in_order(pdf_stream) -> tuple:
    """顺序解析 PDF，并返回(文本内容, 是否包含大量图片需转交OCR)"""
    content = []
    requires_ocr = False

    with pdfplumber.open(pdf_stream) as pdf:
        for page in pdf.pages:
            # 1. 检查图片占比，决定是否触发 TextIn 云端兜底
            page_area = float(page.width * page.height)
            for img in page.images:
                img_area = float(img.get('width', 0) * img.get('height', 0))
                if page_area > 0 and (img_area / page_area) > 0.05:
                    requires_ocr = True
                    break

            # 2. 提取页面上所有的表格，并记录它们的包围盒(bbox)
            tables = page.find_tables()
            table_bboxes = [t.bbox for t in tables]

            # 3. 提取所有的文字单词，附带它们的坐标
            words = page.extract_words(keep_blank_chars=True)

            # 4. 过滤掉那些"在表格内部"的文字
            non_table_words = []
            for w in words:
                in_table = False
                for bbox in table_bboxes:
                    if bbox[0] <= w['x0'] and bbox[1] <= w['top'] and bbox[2] >= w['x1'] and bbox[3] >= w['bottom']:
                        in_table = True
                        break
                if not in_table:
                    non_table_words.append(w)

            # 5. 将纯文本和 Markdown 表格封装成具有 `top` (Y坐标) 的对象
            page_elements = []

            # 合并同一行的文字
            current_line_text = ""
            current_line_top = -1
            line_tolerance = 5

            for w in non_table_words:
                if current_line_top == -1 or abs(w['top'] - current_line_top) < line_tolerance:
                    current_line_text += w['text']
                    if current_line_top == -1: current_line_top = w['top']
                else:
                    page_elements.append({'type': 'text', 'top': current_line_top, 'content': current_line_text.strip()})
                    current_line_text = w['text']
                    current_line_top = w['top']
            if current_line_text:
                page_elements.append({'type': 'text', 'top': current_line_top, 'content': current_line_text.strip()})

            # 将表格转化为 Markdown 并加入列表
            for t_obj in tables:
                table_content = ["\n"]
                table_data = t_obj.extract()
                for i, row in enumerate(table_data):
                    clean_row = [str(c).replace('\n', ' ').replace('\r', '').strip() if c else "" for c in row]
                    table_content.append("| " + " | ".join(clean_row) + " |")
                    if i == 0:
                        table_content.append("|" + "|".join(["---"] * len(clean_row)) + "|")
                table_content.append("\n")

                page_elements.append({
                    'type': 'table',
                    'top': t_obj.bbox[1],
                    'content': "\n".join(table_content)
                })

            # 6. 按照 Y 坐标 (top) 从上到下对文字和表格进行排序
            page_elements.sort(key=lambda x: x['top'])

            # 7. 拼装成本页的最终内容
            for el in page_elements:
                if el['content']:
                    content.append(el['content'])

    return "\n".join(content).strip(), requires_ocr


def read_local_file_content(file_path: str) -> str:
    """通用本地文件读取函数（升级版：自上而下顺序解析）"""
    if not os.path.exists(file_path):
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".docx":
            with open(file_path, "rb") as f:
                return parse_docx_in_order(f)
        elif ext == ".pdf":
            with open(file_path, "rb") as f:
                text, _ = parse_pdf_in_order(f)
                return text
    except Exception as e:
        print(f"解析标准文件 {file_path} 失败: {e}")
    return ""


def get_standard_document_content(major_element: str, matched_rule: str) -> str:
    """根据匹配到的规则名去读取标准原文"""
    if matched_rule:
        for ext in [".docx", ".pdf", ".doc"]:
            path = os.path.join(DATA_DIR, f"{matched_rule}{ext}")
            content = read_local_file_content(path)
            if content:
                return f"【审核标准原文：{matched_rule}】\n{content}"

    return "未在 data 文件夹下找到对应的标准原文文件，请仅根据通用ISO常识审核。"


def extract_text_via_textin(file_bytes: bytes) -> str:
    """调用 TextIn xParse 文档解析接口，直接输出原生 Markdown"""
    url = "https://api.textin.com/ai/service/v1/pdf_to_markdown"

    headers = {
        "x-ti-app-id": TEXTIN_APP_ID,
        "x-ti-secret-code": TEXTIN_SECRET_CODE,
        "Content-Type": "application/octet-stream"
    }

    params = {
        "parse_mode": "auto",
        "table_flavor": "md",
        "apply_document_tree": 1
    }

    try:
        response = requests.post(url, headers=headers, params=params, data=file_bytes)
        result = response.json()

        if result.get("code") == 200:
            return result.get("result", {}).get("markdown", "")
        else:
            print(f"TextIn 接口报错: {result.get('message')}")
    except Exception as e:
        print(f"云端解析异常: {e}")

    return "解析失败"


def extract_upload_file_text(file_bytes: bytes, filename: str) -> str:
    """解析用户上传的待审证据文件：自上而下顺序解析 + 云端兜底"""
    try:
        if filename.endswith(".docx"):
            return parse_docx_in_order(io.BytesIO(file_bytes))

        elif filename.endswith(".doc"):
            print(f"[{filename}] .doc 格式暂不支持，请转换为 .docx 格式")
            return ""

        elif filename.endswith(".xlsx"):
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            content = []
            for sheet in wb.worksheets:
                content.append(f"\n### {sheet.title}\n")
                for i, r in enumerate(sheet.iter_rows(values_only=True)):
                    row_data = [str(c).replace('\n', ' ').replace('\r', '').strip() if c is not None else "" for c in r]
                    if not any(row_data): continue
                    content.append("| " + " | ".join(row_data) + " |")
                    if i == 0:
                        content.append("|" + "|".join(["---"] * len(row_data)) + "|")
            return "\n".join(content)

        elif filename.endswith(".csv"):
            text = file_bytes.decode('utf-8-sig', errors='ignore')
            reader = csv.reader(io.StringIO(text))
            content = []
            for i, row in enumerate(reader):
                row_data = [c.replace('\n', ' ').replace('\r', '').strip() for c in row]
                if not any(row_data): continue
                content.append("| " + " | ".join(row_data) + " |")
                if i == 0:
                    content.append("|" + "|".join(["---"] * len(row_data)) + "|")
            return "\n".join(content)

        elif filename.endswith(".pdf"):
            result_text, requires_ocr = parse_pdf_in_order(io.BytesIO(file_bytes))

            if len(result_text) < 50 or "|" not in result_text or requires_ocr:
                print(f"[{filename}] 识别为混合型/扫描型 PDF，智能切换至 TextIn 云端解析...")
                return extract_text_via_textin(file_bytes)

            return result_text

    except Exception as e:
        print(f"数据解析遭遇异常: {e}")
    return ""