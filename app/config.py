# 프로젝트 전역 설정값
# 나중에 격자 크기나 기준 좌표를 바꿀 때 이 파일만 수정하면 됨

# SQLite 데이터베이스 파일 경로 (나중에 Postgres 등으로 교체 시 이 값만 바꾸면 됨)
DATABASE_URL = "sqlite:///./risk.db"

# 격자(셀) 한 변의 크기 (위경도 단위, 도)
# 0.0003도 ≈ 위도 기준 약 33m (캠퍼스 내부 도로 단위에 맞춘 해상도)
# 주의: static/risk_map.html 안의 CELL_SIZE 상수와 반드시 같은 값이어야 함
CELL_SIZE = 0.0003

# 지도 기본 중심 좌표 (숭실대학교) - seed.py의 핫스팟 기준점으로도 사용
DEFAULT_CENTER_LAT = 37.4956
DEFAULT_CENTER_LNG = 126.9573
