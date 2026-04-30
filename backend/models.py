"""
Pydantic数据模型定义
"""
from pydantic import BaseModel
from typing import List, Optional


class PromptUpdate(BaseModel):
    content: str


class AIImproveRequest(BaseModel):
    current_prompt: str
    issues_feedback: str


class AccidentCreate(BaseModel):
    accident_time: str
    location: str
    accident_type: str
    casualties: str = ""
    description: str = ""
    attachments: List[str] = []
    department: Optional[str] = None
    engineer_name: Optional[str] = None
    status: str = "draft"


class AccidentUpdate(BaseModel):
    accident_time: Optional[str] = None
    location: Optional[str] = None
    accident_type: Optional[str] = None
    casualties: Optional[str] = None
    description: Optional[str] = None
    attachments: Optional[List[str]] = None
    department: Optional[str] = None
    engineer_name: Optional[str] = None


# 整改措施相关模型
class RectificationCreate(BaseModel):
    measure_content: str
    measure_order: int = 1


class RectificationUpdate(BaseModel):
    measure_content: Optional[str] = None
    measure_order: Optional[int] = None


class RectificationAssign(BaseModel):
    responsible_person: str
    deadline: str


class RectificationComplete(BaseModel):
    completion_proof: List[str] = []


# 事故警示相关模型
class AlertCreate(BaseModel):
    alert_title: str
    alert_content: str
    alert_image: Optional[str] = None
    notification_manager: Optional[str] = None
    target_departments: List[str] = []


class AlertUpdate(BaseModel):
    alert_title: Optional[str] = None
    alert_content: Optional[str] = None
    alert_image: Optional[str] = None
    notification_manager: Optional[str] = None
    target_departments: Optional[List[str]] = None


# 培训记录相关模型
class TrainingCreate(BaseModel):
    training_date: str
    training_location: str
    training_content: str
    trainer_name: str
    attendees_count: int
    sign_sheet_attachment: Optional[str] = None
    photo_attachments: List[str] = []


class TrainingUpdate(BaseModel):
    training_date: Optional[str] = None
    training_location: Optional[str] = None
    training_content: Optional[str] = None
    trainer_name: Optional[str] = None
    attendees_count: Optional[int] = None
    sign_sheet_attachment: Optional[str] = None
    photo_attachments: Optional[List[str]] = None


class BatchReportSave(BaseModel):
    batch_name: str
    total_count: int
    pass_count: int
    pass_rate: float
    details: list