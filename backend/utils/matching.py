"""
文件匹配逻辑
"""
import os
import re
import difflib

from config import routing_dict


def loose_match_sub_element(major_element: str, file_name: str) -> str:
    """
    仅依靠上传文件名称与 JSON 进行匹配。

    匹配策略：
    1. 优先：文件名完全匹配（去除扩展名后与配置文件名完全一致）
    2. 兜底：融合包含、核心词根、最长公共子串、相似度的四重模糊匹配
    """
    element_data = routing_dict.get(major_element, {})
    sub_elements = element_data.get("子要素", {})

    def clean_text(text: str) -> str:
        """初级清洗：剔除前缀和无用符号"""
        t = text.replace("废弃物", "废物")
        return re.sub(r'[A-Za-z0-9\-\.\:（）\(\)《》_]|From|海正药业|杭州|公司内部|有限公司', '', t).strip()

    def get_core_noun(text: str) -> str:
        """深度清洗：暴露出业务专有名词核心"""
        stopwords = ["管理", "规定", "制度", "程序", "记录", "台账", "清单", "检查", "维护", "评估", "报告", "装置", "洗眼", "处理", "调查", "表", "单", "流程", "分析", "情况", "计划"]
        t = text
        for w in stopwords:
            t = t.replace(w, "")
        return t.strip()

    base_filename = os.path.splitext(file_name)[0]
    norm_filename = clean_text(base_filename)
    core_filename = get_core_noun(norm_filename)

    # ========== 第一步：完全匹配（优先）==========
    for rule_name, file_list in sub_elements.items():
        for expected_file in file_list:
            # 去除扩展名后进行完全匹配
            expected_base = os.path.splitext(expected_file)[0]
            if base_filename == expected_base:
                return rule_name
            # 清洗后完全匹配
            expected_clean = clean_text(expected_base)
            if norm_filename == expected_clean:
                return rule_name

    # ========== 第二步：模糊匹配（兜底）==========
    for rule_name, file_list in sub_elements.items():
        for expected_file in file_list:
            norm_expected = clean_text(expected_file)
            core_expected = get_core_noun(norm_expected)

            if not norm_expected:
                continue

            # 包含匹配
            if norm_expected in norm_filename:
                return rule_name

            # 最长公共子串匹配
            match = difflib.SequenceMatcher(None, norm_expected, norm_filename).find_longest_match(0, len(norm_expected), 0, len(norm_filename))
            if match.size >= 4:
                return rule_name

            # 相似度匹配
            similarity = difflib.SequenceMatcher(None, norm_expected, norm_filename).ratio()
            if similarity > 0.6:
                return rule_name

    major_file_name = element_data.get("主要素文件", "该要素缺失主要素文件配置")
    return major_file_name