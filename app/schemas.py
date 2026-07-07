"""API 요청/응답에 쓰이는 Pydantic 스키마"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    """POST /api/events 요청 바디 (Jetson -> 서버)"""

    lat: float
    lng: float
    risk: int = Field(ge=0, le=3, description="위험 등급 0~3")
    ttc: Optional[float] = Field(default=None, description="Time To Collision (초)")
    timestamp: Optional[datetime] = Field(default=None, description="미전달 시 서버 수신 시각으로 대체")


class EventOut(BaseModel):
    """POST /api/events 응답 (저장된 이벤트 확인용)"""

    id: int
    lat: float
    lng: float
    risk: int
    ttc: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True


class RiskSegment(BaseModel):
    """GET /api/risk-segments 응답 항목 (도로 구간 하나의 누적 집계)"""

    points: list[list[float]]  # 도로 구간 양 끝점 [[lat, lng], [lat, lng]]
    grade: int  # 구간의 누적 위험 등급 0~3 (평균 risk를 반올림)
    events: int  # 구간에 누적된 이벤트 건수
    avg: float  # 평균 위험도 (반올림 전 원본 값)
    ttc: Optional[float]  # 평균 TTC (초)
