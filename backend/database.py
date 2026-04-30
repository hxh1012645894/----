"""
数据库模块：初始化数据库表、数据库操作函数
"""
import sqlite3

from config import DB_FILE, logger, DATA_DIR, UPLOAD_DIR


def migrate_casualties_field():
    """迁移 casualties 字段从 INTEGER 到 TEXT"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 检查 casualties 字段类型
    cursor.execute("PRAGMA table_info(accident_records)")
    columns = cursor.fetchall()
    for col in columns:
        if col[1] == 'casualties':
            current_type = col[2]
            if current_type == 'INTEGER':
                logger.info("正在迁移 casualties 字段从 INTEGER 到 TEXT...")
                # SQLite 不支持直接 ALTER COLUMN，需要重建表
                cursor.execute('''
                    CREATE TABLE accident_records_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        accident_time DATETIME NOT NULL,
                        location TEXT NOT NULL,
                        accident_type TEXT NOT NULL,
                        casualties TEXT DEFAULT '',
                        description TEXT,
                        attachments_json TEXT,
                        status TEXT DEFAULT 'draft',
                        department TEXT,
                        engineer_name TEXT,
                        extracted_info_json TEXT,
                        ledger_generated INTEGER DEFAULT 0,
                        ledger_path TEXT,
                        created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
                        submitted_at DATETIME,
                        updated_at DATETIME
                    )
                ''')
                # 复制数据，将 INTEGER 转为 TEXT
                cursor.execute('''
                    INSERT INTO accident_records_new
                    SELECT id, accident_time, location, accident_type,
                           CAST(casualties AS TEXT), description, attachments_json,
                           status, department, engineer_name, extracted_info_json,
                           ledger_generated, ledger_path, created_at, submitted_at, updated_at
                    FROM accident_records
                ''')
                # 删除旧表
                cursor.execute('DROP TABLE accident_records')
                # 重命名新表
                cursor.execute('ALTER TABLE accident_records_new RENAME TO accident_records')
                conn.commit()
                logger.info("casualties 字段迁移完成")
            break

    conn.close()


def init_db():
    """初始化所有数据库表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 历史报告表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batch_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_name TEXT,
            total_count INTEGER,
            pass_count INTEGER,
            pass_rate REAL,
            details_json TEXT,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours'))
        )
    ''')

    # 系统提示词表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_prompts (
            prompt_key TEXT PRIMARY KEY,
            prompt_name TEXT,
            content TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 事故记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accident_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_time DATETIME NOT NULL,
            location TEXT NOT NULL,
            accident_type TEXT NOT NULL,
            casualties TEXT DEFAULT '',
            description TEXT,
            attachments_json TEXT,
            status TEXT DEFAULT 'draft',
            department TEXT,
            engineer_name TEXT,
            extracted_info_json TEXT,
            ledger_generated INTEGER DEFAULT 0,
            ledger_path TEXT,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            submitted_at DATETIME,
            updated_at DATETIME
        )
    ''')

    # 事故AI分析结果表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accident_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_id INTEGER NOT NULL,
            direct_cause TEXT,
            indirect_cause TEXT,
            lessons_learned TEXT,
            rectification_measures TEXT,
            analysis_time DATETIME DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (accident_id) REFERENCES accident_records(id)
        )
    ''')

    # 整改措施表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rectification_measures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_id INTEGER NOT NULL,
            measure_content TEXT NOT NULL,
            measure_order INTEGER DEFAULT 1,
            responsible_person TEXT,
            deadline DATETIME,
            status TEXT DEFAULT 'pending',
            completion_proof_json TEXT,
            completed_at DATETIME,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (accident_id) REFERENCES accident_records(id)
        )
    ''')

    # 事故警示表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accident_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_id INTEGER NOT NULL,
            alert_title TEXT NOT NULL,
            alert_content TEXT NOT NULL,
            alert_image TEXT,
            notification_manager TEXT,
            target_departments_json TEXT,
            status TEXT DEFAULT 'draft',
            created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (accident_id) REFERENCES accident_records(id)
        )
    ''')

    # 培训记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_id INTEGER NOT NULL,
            alert_id INTEGER NOT NULL,
            training_date DATETIME NOT NULL,
            training_location TEXT,
            training_content TEXT,
            trainer_name TEXT,
            attendees_count INTEGER,
            sign_sheet_attachment TEXT,
            photo_attachments_json TEXT,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (accident_id) REFERENCES accident_records(id),
            FOREIGN KEY (alert_id) REFERENCES accident_alerts(id)
        )
    ''')

    # 事故类型表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accident_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours'))
        )
    ''')

    # 初始化默认事故类型（如果表为空）
    cursor.execute('SELECT count(*) FROM accident_types')
    if cursor.fetchone()[0] == 0:
        default_types = [
            '火灾事故', '爆炸事故', '中毒窒息', '坍塌事故',
            '机械伤害', '高处坠落', '物体打击', '触电事故',
            '灼烫事故', '车辆伤害', '其他事故'
        ]
        for t in default_types:
            cursor.execute('INSERT INTO accident_types (type_name) VALUES (?)', (t,))

    # 初始化默认提示词（如果表为空）
    cursor.execute('SELECT count(*) FROM system_prompts')
    if cursor.fetchone()[0] == 0:
        default_standard = """你是一个拥有20年经验的ISO体系高级内审员，你的审核风格是：逻辑极其严密、注重实质合规、且具备极强的"单文件深度分析"能力。
【审核标准文件原文】（判罚依据）：\n{standard_text}
【待审核证据文件内容】：\n{evidence_text}
请根据【审核标准文件原文】，对【待审核证据文件内容】进行深度的内容逻辑与合规性审核。
（请保持严格的JSON输出：包含"结论"、"逻辑缺陷描述"、"引用依据"、"修改意见"）"""

        default_daily = """你是一个资深的EHS安全专家和卓越的数据分析师。
【8.1要素管理标准原文】：\n{standard_text}
【待分析的日常检查汇总表内容】：\n{evidence_text}
系统已统计：总数{total}，已完成{completed}，整改率{rate}%，前三类别{top3_str}。
请结合上述数据和标准原文，固定输出"符合"结论，并给出专业的分析和整改意见。"""

        default_accident = """你是一位拥有20年经验的EHS（环境、健康与安全）高级专家，擅长事故调查与根源分析。你的分析风格是：逻辑严密、追根溯源、注重系统性改进。

【事故基本信息】：
- 发生时间：{accident_time}
- 发生地点：{location}
- 事故类型：{accident_type}
- 伤亡情况：{casualties}
- 详细描述：{description}
- 附件内容提取：{attachment_content}

请对该事故进行专业的根源分析，输出以下四项分析结果（JSON格式）：

{
    "直接原因分析": "分析导致事故发生的直接技术原因或操作失误（如设备故障、违章操作、防护缺失等）",
    "间接原因分析": "分析造成直接原因的深层管理原因（如培训不足、制度缺陷、监督不力、资源配置不合理等）",
    "事故教训总结": "总结本次事故对企业和行业的重要警示和经验教训",
    "整改措施建议": [
        "第一条整改措施（具体、可执行）",
        "第二条整改措施（具体、可执行）",
        "第三条整改措施（具体、可执行）"
    ]
}

注意：整改措施请拆分为独立的数组条目，每条措施要具体、可执行，便于后续派发给责任人跟踪落实。"""

        default_alert = """你是一个安全警示文案专家，擅长根据事故信息生成企业内部警示文案。你的文案风格是：醒目、简洁、有冲击力、易于传播。

【事故基本信息】：
{accident_data}

【AI分析结果】：
{analysis_result}

请生成一份适合在企业内部发布的事故警示（JSON格式）：

{
    "alert_title": "警示标题（简洁醒目，不超过20字）",
    "alert_summary": "事故摘要（一句话概述，不超过50字）",
    "key_points": ["关键要点1", "关键要点2", "关键要点3"],
    "safety_tips": ["安全提示1", "安全提示2", "安全提示3"],
    "training_requirements": ["培训要求1", "培训要求2"]
}

注意：
1. 标题要有警示作用，能引起员工注意
2. 关键要点要突出事故的核心问题
3. 安全提示要具体、可操作
4. 培训要求要与事故类型相关"""

        cursor.execute("INSERT INTO system_prompts (prompt_key, prompt_name, content) VALUES (?, ?, ?)",
                       ('standard_audit', '标准体系交叉审核提示词', default_standard))
        cursor.execute("INSERT INTO system_prompts (prompt_key, prompt_name, content) VALUES (?, ?, ?)",
                       ('daily_inspection', '日常检查台账分析提示词', default_daily))
        cursor.execute("INSERT INTO system_prompts (prompt_key, prompt_name, content) VALUES (?, ?, ?)",
                       ('accident_analysis', '事故根源分析提示词', default_accident))
        cursor.execute("INSERT INTO system_prompts (prompt_key, prompt_name, content) VALUES (?, ?, ?)",
                       ('accident_alert', '事故警示生成提示词', default_alert))

    conn.commit()
    conn.close()


def get_prompt_from_db(prompt_key: str) -> str:
    """从数据库获取提示词"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM system_prompts WHERE prompt_key = ?", (prompt_key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""


# 初始化数据库
init_db()

# 执行字段迁移（如果有）
migrate_casualties_field()

# 记录日志
logger.info(f"数据目录: {DATA_DIR}")
logger.info(f"数据库文件: {DB_FILE}")
logger.info(f"上传目录: {UPLOAD_DIR}")