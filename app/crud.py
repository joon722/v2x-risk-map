"""DB 접근 로직 (이벤트 저장, 도로 구간 단위 집계)"""
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app import roads
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


def get_risk_segments(db: Session) -> list[dict]:
    """전체 이벤트를 가장 가까운 도로 구간(엣지)에 스냅해서 누적 집계 반환

    격자 대신 실제 도로 위에만 위험도가 표시되도록, 이벤트 좌표를
    app/roads.py가 들고 있는 OSM 도로망의 가장 가까운 엣지에 매칭한다.
    이벤트 수가 많지 않은 데모 단계라 조회 시점에 Python에서 집계한다.
    """
    events = db.query(Event).all()

    buckets: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        edge_id = roads.nearest_edge_id(e.lat, e.lng)
        buckets[edge_id].append(e)

    segments = []
    for edge_id, bucket_events in buckets.items():
        risks = [e.risk for e in bucket_events]
        ttcs = [e.ttc for e in bucket_events if e.ttc is not None]

        avg_risk = sum(risks) / len(risks)
        avg_ttc = sum(ttcs) / len(ttcs) if ttcs else None
        # 평균 위험도를 반올림하고 0~3 범위로 고정해 등급(grade)으로 사용
        grade = max(0, min(3, round(avg_risk)))

        p1, p2 = roads.get_edge_points(edge_id)

        segments.append(
            {
                "points": [list(p1), list(p2)],
                "grade": grade,
                "events": len(bucket_events),
                "avg": round(avg_risk, 2),
                "ttc": round(avg_ttc, 2) if avg_ttc is not None else None,
            }
        )

    return segments
