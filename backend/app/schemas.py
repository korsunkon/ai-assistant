from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CallBase(BaseModel):
    filename: str
    original_path: str
    duration_sec: Optional[int] = None
    size_bytes: Optional[int] = None
    status: str


class CallRead(CallBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisCreate(BaseModel):
    name: str
    query_text: str
    call_ids: List[int]


class AnalysisRead(BaseModel):
    id: int
    name: str
    query_text: str
    created_at: datetime
    status: str
    progress: int

    class Config:
        from_attributes = True


class AnalysisStatus(BaseModel):
    id: int
    status: str
    progress: int
    total_calls: int
    processed_calls: int
    error_count: int


class AnalysisResultRead(BaseModel):
    id: int
    call_id: int
    analysis_id: int
    summary: Optional[str] = None
    json_result: Optional[str] = None
    filename: Optional[str] = None
    created_at: Optional[datetime] = None


# Шаблоны анализа
class AnalysisTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    query_text: str
    category: str = "general"


class AnalysisTemplateRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    query_text: str
    category: str
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Статистика для Dashboard
class IncidentStats(BaseModel):
    total_files: int
    files_with_incidents: int
    total_incidents: int
    incidents_by_type: dict
    severity_distribution: dict


class DashboardStats(BaseModel):
    analysis_id: int
    analysis_name: str
    stats: IncidentStats
    incidents: List[dict]  # Список инцидентов с тайм-кодами


