"""
统计计算函数
"""


def calculate_inspection_stats(evidence_text: str):
    """计算日常检查统计信息"""
    total_count = 0
    completed_count = 0
    cats = {}

    lines = evidence_text.strip().split("\n")
    for line in lines:
        line = line.strip()

        clean_line = line.strip("|").strip()

        if not clean_line:
            continue

        delimiter = " | " if " | " in clean_line else ","
        cols = clean_line.split(delimiter)

        if not cols or not cols[0].strip().replace('"', '').isdigit():
            continue

        total_count += 1

        if "已完成" in clean_line:
            completed_count += 1

        if len(cols) > 3:
            cat = cols[3].strip().replace('"', '')
            if cat and cat not in ["", "-", "无", "N/A"]:
                cats[cat] = cats.get(cat, 0) + 1

    top3 = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:3]
    rate = round((completed_count / total_count * 100), 2) if total_count > 0 else 0

    return total_count, completed_count, rate, top3