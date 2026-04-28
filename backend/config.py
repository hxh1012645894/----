"""
配置模块：环境变量、客户端初始化、常量定义
"""
import os
import json
import logging
from dotenv import load_dotenv
from datetime import timezone, timedelta
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 设置中国时区（UTC+8）
CHINA_TZ = timezone(timedelta(hours=8))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- 目录配置（支持Docker环境变量覆盖）---
# 在Docker中，这些路径由环境变量指定；本地开发时使用相对路径
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
DATA_DIR = os.getenv("DATA_DIR", "data")
DB_FILE = os.getenv("DB_FILE", "audit_batches.db")

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- API配置（从环境变量读取） ---
TEXTIN_APP_ID = os.getenv("TEXTIN_APP_ID")
TEXTIN_SECRET_CODE = os.getenv("TEXTIN_SECRET_CODE")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
PROMPT_LLM_API_KEY = os.getenv("PROMPT_LLM_API_KEY")
PROMPT_LLM_BASE_URL = os.getenv("PROMPT_LLM_BASE_URL")
PROMPT_LLM_MODEL = os.getenv("PROMPT_LLM_MODEL", "glm-4.7")

if not all([TEXTIN_APP_ID, TEXTIN_SECRET_CODE, DEEPSEEK_API_KEY]):
    print("警告: 请在 .env 文件中配置所有 API 密钥")

# DeepSeek 客户端（用于审核）
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# 提示词优化 LLM 客户端（通用 OpenAI 协议）
prompt_llm_client = OpenAI(api_key=PROMPT_LLM_API_KEY, base_url=PROMPT_LLM_BASE_URL)

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))

# --- 加载匹配字典 ---
# 在Docker中，ROUTING_DICT_PATH由环境变量指定；本地开发时自动计算
ROUTING_DICT_PATH = os.getenv("ROUTING_DICT_PATH")
if not ROUTING_DICT_PATH:
    # 本地开发：计算项目根目录下的文件路径
    ROUTING_DICT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "element_routing_dictionary_final.json")

with open(ROUTING_DICT_PATH, "r", encoding="utf-8") as f:
    routing_dict = json.load(f)

# 事故类型列表
ACCIDENT_TYPES = [
    "火灾事故",
    "爆炸事故",
    "中毒事故",
    "泄漏事故",
    "机械伤害",
    "高处坠落",
    "物体打击",
    "触电事故",
    "灼烫事故",
    "车辆伤害",
    "其他事故"
]