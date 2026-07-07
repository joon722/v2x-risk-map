"""FastAPI 앱 엔트리포인트

- POST /api/events        : Jetson Nano가 위험 이벤트를 업로드
- GET  /api/risk-segments : 도로 구간별 누적 집계 반환 (프론트 지도가 이걸 fetch)
- GET  /                 : 데모용 프론트엔드(risk_map.html) 서빙
"""
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import crud
from app.database import Base, engine, get_db
from app.schemas import EventCreate, EventOut, RiskSegment

# 앱 시작 시 테이블이 없으면 생성 (데모 단계라 별도 마이그레이션 도구 없이 단순하게)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="V2X Risk Map API")

# 개발 편의를 위해 모든 origin 허용. 운영 배포 시에는 프론트 도메인만 넣도록 좁힐 것.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_map():
    """브라우저로 바로 접속했을 때 데모 지도 페이지를 보여줌"""
    return FileResponse(STATIC_DIR / "risk_map.html")


@app.post("/api/events", response_model=EventOut)
def upload_event(event: EventCreate, db: Session = Depends(get_db)):
    """Jetson Nano가 계산한 위험 이벤트(거리/TTC 기반 RISK 0~3)를 업로드"""
    db_event = crud.create_event(db, event)
    return db_event


@app.get("/api/risk-segments", response_model=list[RiskSegment])
def read_risk_segments(db: Session = Depends(get_db)):
    """도로 구간 단위로 누적 집계된 위험도를 반환 (웹 지도가 색칠할 때 사용)"""
    return crud.get_risk_segments(db)
