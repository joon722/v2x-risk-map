"""ORM 모델 정의.

지금은 Event 테이블 하나만 두고, 격자 집계는 조회 시점에 계산한다
(app/crud.py의 get_risk_cells 참고). 이벤트 수가 아주 많아지면
집계 결과를 캐싱하는 테이블을 따로 두는 식으로 확장 가능.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, Float, DateTime

from app.database import Base


class Event(Base):
    """Jetson Nano가 업로드하는 위험 이벤트 1건"""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False, index=True)
    lng = Column(Float, nullable=False, index=True)
    risk = Column(Integer, nullable=False)  # 위험 등급 0~3
    ttc = Column(Float, nullable=True)  # Time To Collision (초)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
