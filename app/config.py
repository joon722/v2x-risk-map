# 프로젝트 전역 설정값
# 나중에 기준 좌표를 바꿀 때 이 파일만 수정하면 됨

# SQLite 데이터베이스 파일 경로 (나중에 Postgres 등으로 교체 시 이 값만 바꾸면 됨)
DATABASE_URL = "sqlite:///./risk.db"

# 지도 기본 중심 좌표 (숭실대학교) - seed.py의 핫스팟 기준점, app/roads.py의
# 위경도->미터 변환 기준점으로도 사용
DEFAULT_CENTER_LAT = 37.4956
DEFAULT_CENTER_LNG = 126.9573
