"""DB 접근 로직 (이벤트 저장, 격자 단위 집계)"""
import math
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import CELL_SIZE
from app.models import Event
from app.schemas import EventCreate


def create_event(db: Session, event: EventCreate) -> Event:
    """Jetson이 올린 위험 이벤트 1건을 저장"""
    db_event = Event(
        lat=event.lat,
        lng=event.lng,
        risk=event.risk,
        ttc=event.ttc,
        # timestamp를 안 보내면 서버가 받은 시각으로 채움
        timestamp=event.timestamp or datetime.utcnow(),
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def _cell_origin(lat: float, lng: float) -> tuple[float, float]:
    """좌표를 CELL_SIZE 격자에 매핑해서 셀의 좌하단(남서쪽) 좌표를 반환"""
    cell_lat = math.floor(lat / CELL_SIZE) * CELL_SIZE
    cell_lng = math.floor(lng / CELL_SIZE) * CELL_SIZE
    # 부동소수점 오차 누적 방지용 반올림
    return round(cell_lat, 6), round(cell_lng, 6)


def get_risk_cells(db: Session) -> list[dict]:
    """전체 이벤트를 격자 셀 단위로 묶어서 누적 집계 반환

    이벤트 수가 많지 않은 데모 단계라 조회 시점에 Python에서 집계한다.
    데이터가 커지면 SQL GROUP BY로 옮기거나 별도 집계 테이블을 두면 됨.
    """
    events = db.query(Event).all()

    buckets: dict[tuple[float, float], list[Event]] = defaultdict(list)
    for e in events:
        key = _cell_origin(e.lat, e.lng)
        buckets[key].append(e)

    cells = []
    for (cell_lat, cell_lng), bucket_events in buckets.items():
        risks = [e.risk for e in bucket_events]
        ttcs = [e.ttc for e in bucket_events if e.ttc is not None]

        avg_risk = sum(risks) / len(risks)
        avg_ttc = sum(ttcs) / len(ttcs) if ttcs else None
        # 평균 위험도를 반올림하고 0~3 범위로 고정해 등급(grade)으로 사용
        grade = max(0, min(3, round(avg_risk)))

        cells.append(
            {
                "lat": cell_lat,
                "lng": cell_lng,
                "grade": grade,
                "events": len(bucket_events),
                "avg": round(avg_risk, 2),
                "ttc": round(avg_ttc, 2) if avg_ttc is not None else None,
            }
        )

    return cells
