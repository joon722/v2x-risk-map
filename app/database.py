"""SQLAlchemy 엔진/세션 설정.

지금은 SQLite를 쓰지만, DATABASE_URL만 바꾸면 다른 DB로 쉽게 교체 가능하도록
엔진 생성과 세션 관리를 이 파일 하나에 모아둠.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

# SQLite는 멀티 스레드 환경(FastAPI)에서 기본적으로 커넥션 공유를 막기 때문에
# check_same_thread=False 옵션이 필요함. 다른 DB로 바꾸면 이 옵션은 제거해도 됨.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI Depends용 DB 세션 제너레이터"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
