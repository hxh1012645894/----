"""
Pydantic数据模型定义
"""
from pydantic import BaseModel
from typing import List


class PromptUpdate(BaseModel):
    content: str


class AIImproveRequest(BaseModel):
    current_prompt: str
    issues_feedback: str


class AccidentCreate(BaseModel):
    accident_time: str
    location: str
    accident_type: str
    casualties: int = 0
    description: str = ""
    attachments: List[str] = []
    status: str = "draft"


class AccidentUpdate(BaseModel):
    accident_time: str = None
    location: str = None
    accident_type: str = None
    casualties: int = None
    description: str = None
    attachments: List[str] = None


class BatchReportSave(BaseModel):
    batch_name: str
    total_count: int
    pass_count: int
    pass_rate: float
    details: list