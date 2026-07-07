# V2X 사고 위험 예측 지도

Jetson Nano가 도로변 인프라 역할을 하며 차량/지팡이의 GPS·IMU 데이터로
거리·TTC를 계산해 위험 등급(RISK 0~3)을 산출하고, 이 이벤트를 클라우드
서버에 업로드하면 서버가 실제 도로 구간 단위로 누적 집계해서 웹 지도 위
도로를 따라 색으로 표시하는 데모 프로젝트입니다. 격자가 아니라 OSM에서
받아온 실제 도로망에 이벤트를 스냅해서 건물 위에 칠해지는 일이 없도록
했습니다. 실시간 지도가 아니라 **누적 통계 지도**입니다.

## 폴더 구조

```
map/
├── app/
│   ├── main.py       # FastAPI 앱, 라우터, CORS, 정적 파일 서빙
│   ├── database.py   # SQLAlchemy 엔진/세션 (SQLite)
│   ├── models.py      # Event ORM 모델
│   ├── schemas.py     # Pydantic 요청/응답 스키마
│   ├── crud.py        # 이벤트 저장 + 도로 구간 집계 로직
│   ├── roads.py        # OSM 도로망 로드 + 좌표를 가장 가까운 도로 구간에 스냅
│   ├── config.py       # 기본 중심좌표 등 상수
│   └── data/roads.json  # Overpass API로 미리 받아둔 숭실대 주변 도로망
├── static/
│   └── risk_map.html  # 프론트엔드 (Leaflet + fetch)
├── seed.py                  # Jetson 업로드를 흉내내는 시더 스크립트 (가짜 데이터)
├── import_sumo_results.py   # SUMO 시뮬레이션 결과 CSV를 서버에 업로드하는 스크립트
├── sumo_risk_sample.csv     # import_sumo_results.py가 기대하는 CSV 포맷 예시
├── requirements.txt
└── risk.db            # 실행 시 자동 생성되는 SQLite 파일
```

## 실행 방법

```bash
# 1. (선택) 가상환경 생성
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 서버 실행 (프로젝트 루트에서)
uvicorn app.main:app --reload

# 4. 다른 터미널에서 시더 실행 (서버가 켜져 있어야 함)
python seed.py

# 5. 브라우저에서 확인
http://localhost:8000
```

시더를 실행하면 숭실대학교 부근 핫스팟 3곳에 위험 이벤트가 채워지고,
브라우저에서 실제 도로가 위험 등급별로 색칠된 것을 볼 수 있습니다.

## API 명세

### `POST /api/events`

Jetson Nano가 계산한 위험 이벤트 1건을 업로드합니다.

**요청 바디**
```json
{
  "lat": 37.4956,
  "lng": 126.9573,
  "risk": 3,
  "ttc": 0.8,
  "timestamp": "2026-07-04T10:00:00"
}
```
- `risk`: 0~3 (필수, Jetson이 거리·TTC로 산출한 위험 등급)
- `ttc`: Time To Collision, 초 단위 (선택)
- `timestamp`: 선택. 생략하면 서버 수신 시각으로 채워짐

**응답 (200)**
```json
{
  "id": 1,
  "lat": 37.4956,
  "lng": 126.9573,
  "risk": 3,
  "ttc": 0.8,
  "timestamp": "2026-07-04T10:00:00"
}
```

### `GET /api/risk-segments`

전체 이벤트를 가장 가까운 도로 구간(엣지)에 스냅해서 누적 집계한
결과를 반환합니다.

**응답 (200)**
```json
[
  {
    "points": [[37.4956, 126.9573], [37.4958, 126.9575]],
    "grade": 3,
    "events": 12,
    "avg": 2.83,
    "ttc": 0.75
  }
]
```
- `points`: 도로 구간 양 끝점 좌표. 프론트는 이 점들을 이어 폴리라인을 그림
- `grade`: 구간 내 이벤트들의 평균 위험도를 반올림해 0~3으로 고정한 값 (지도 색상 기준)
- `events`: 구간에 누적된 이벤트 건수
- `avg`: 반올림 전 평균 위험도
- `ttc`: 평균 TTC (초)

## 도로 스냅/등급 로직

- `app/data/roads.json`은 Overpass API(OpenStreetMap)로 숭실대 주변
  `highway=*` 도로망을 미리 받아둔 파일. 각 도로(way)를 인접한 두 점씩
  잘라 "엣지" 단위로 취급함
- `app/roads.py`의 `nearest_edge_id()`가 이벤트 좌표에서 가장 가까운
  엣지를 점-선분 최단거리로 찾아줌 (위경도를 로컬 평면 좌표로 근사
  변환해서 계산)
- 데모 단계라 `GET /api/risk-segments` 호출 시점에 Python에서 집계함
  (이벤트가 아주 많아지면 공간 인덱스(R-tree)나 SQL 쪽으로 옮기는 걸 권장)
- 다른 지역으로 옮기려면 `app/config.py`의 `DEFAULT_CENTER_LAT/LNG`를
  바꾸고, Overpass API로 그 지역 도로망을 다시 받아 `app/data/roads.json`을
  교체하면 됨 (`curl -X POST https://overpass-api.de/api/interpreter
  --data-urlencode 'data=[out:json];way["highway"](남,서,북,동);out geom;'`)

## DB 교체

지금은 SQLite(`risk.db`)를 쓰지만 `app/config.py`의 `DATABASE_URL`만
Postgres 등 다른 DB 커넥션 문자열로 바꾸면 됩니다. SQLite 전용 옵션
(`check_same_thread`)은 `app/database.py`에서 URL에 따라 자동으로
빠지도록 되어 있습니다.

## SUMO 시뮬레이션 결과 업로드

`seed.py`는 발표/데모용 가짜 데이터고, 실제 SUMO 학습 결과는
`import_sumo_results.py`로 업로드한다.

1. SUMO 쪽에서 구간(edge/lane)별 위험도를 계산한 뒤 아래 컬럼을 가진
   CSV로 export한다 (`sumo_risk_sample.csv` 참고):

   ```csv
   lat,lng,risk,ttc,timestamp
   37.4956,126.9573,3,0.8,2026-07-04T10:00:00
   ```
   - `lat`, `lng`, `risk`는 필수. `ttc`, `timestamp`는 선택(비워도 됨)
   - SUMO 내부 좌표(x,y)만 있다면, `net.xml`의 좌표계 정보로
     `sumolib.net.convertXY2LonLat()` 등을 이용해 먼저 위경도로 변환해서
     CSV를 만들어야 함

2. 서버가 켜져 있는 상태에서 업로드:
   ```bash
   python import_sumo_results.py sumo_risk.csv
   # 팀 공용 서버(터널 주소 등)로 올리려면
   python import_sumo_results.py sumo_risk.csv --url https://your-server-url
   ```

3. 브라우저를 새로고침하면 새로 업로드된 이벤트가 도로 구간 집계에 반영된다.

## 팀원 접근 방법

**코드 수정에 참여하려면**
```bash
git clone <이 저장소 URL>
cd map
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```
각자 로컬에서 서버를 띄워 작업하고, 브랜치 나눠서 커밋/푸시하면 된다.

**SUMO 결과만 올리려면 (코드 수정 없이)**
1. 팀에서 공유한 서버 주소를 받는다 (지금은 발표용 임시 터널 주소,
   나중에 정식 배포하면 고정 URL로 바뀔 예정)
2. 이 저장소에서 `import_sumo_results.py`와 `requirements.txt`만 받아서
   `pip install requests`
3. `python import_sumo_results.py 본인_결과.csv --url <공유받은 서버 주소>` 실행

**지도만 보려면**
- 공유받은 서버 주소를 브라우저 주소창에 그대로 입력하면 됨 (별도 설치 불필요)

> 주의: 지금 쓰는 cloudflared 임시 터널 주소는 서버를 껐다 켜면 매번 바뀐다.
> 팀원과 작업할 때는 그때그때 최신 주소를 공유해야 함. 고정 주소가 필요하면
> 클라우드에 정식 배포하는 걸 고려할 것.

## 동작 확인 체크리스트

1. `uvicorn app.main:app --reload` 실행 후 콘솔에 에러 없이 뜨는지 확인
2. `python seed.py` 실행 후 "완료: N건 업로드 성공, 0건 실패" 출력 확인
3. 브라우저에서 `http://localhost:8000` 접속 → 숭실대학교 주변 도로가
   위험 등급별로 색칠된 게 보이는지 확인 (건물 위가 아니라 도로 위에만 칠해져야 함)
4. 도로 구간을 클릭했을 때 좌하단에 상세 카드(등급/건수/평균 위험도/평균 TTC)가 뜨는지 확인
