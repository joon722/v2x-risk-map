"""SUMO 시뮬레이션에서 뽑은 구간별 위험도 CSV를 서버에 업로드하는 스크립트

SUMO 쪽에서 구간(edge/lane)별로 위험도를 계산한 뒤, 아래 컬럼을 가진
CSV로 export해서 이 스크립트로 서버에 밀어넣는다. seed.py와 달리
가짜 데이터가 아니라 실제 시뮬레이션 결과를 업로드할 때 사용.

CSV 형식 (sumo_risk_sample.csv 참고):
    lat,lng,risk,ttc,timestamp
    37.4956,126.9573,3,0.8,2026-07-04T10:00:00
    - lat, lng, risk : 필수
    - ttc, timestamp : 선택 (비워두면 timestamp는 서버 수신 시각으로 대체)

SUMO 내부 좌표(x,y)만 있고 위경도가 없다면, net.xml의 좌표계 정보로
sumolib.net.convertXY2LonLat() 등을 이용해 먼저 위경도로 변환한 뒤
이 스크립트에 넣을 CSV를 만들어야 함.

사용법:
    python import_sumo_results.py sumo_risk.csv
    python import_sumo_results.py sumo_risk.csv --url https://your-tunnel-url.trycloudflare.com
"""
import argparse
import csv

import requests

REQUIRED_COLUMNS = {"lat", "lng", "risk"}


def parse_args():
    parser = argparse.ArgumentParser(description="SUMO 위험도 CSV를 서버로 업로드")
    parser.add_argument("csv_path", help="SUMO 결과 CSV 파일 경로")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="업로드 대상 서버 주소 (기본: http://localhost:8000). "
        "팀 공용 서버나 cloudflared 터널 주소를 쓰려면 여기에 지정",
    )
    return parser.parse_args()


def load_rows(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV에 필수 컬럼이 없습니다: {missing} (필요: lat, lng, risk)")
        return list(reader)


def to_event_payload(row: dict) -> dict:
    payload = {
        "lat": float(row["lat"]),
        "lng": float(row["lng"]),
        "risk": int(float(row["risk"])),
    }
    if row.get("ttc"):
        payload["ttc"] = float(row["ttc"])
    if row.get("timestamp"):
        payload["timestamp"] = row["timestamp"]
    return payload


def main():
    args = parse_args()
    events_url = f"{args.url.rstrip('/')}/api/events"

    rows = load_rows(args.csv_path)
    total, failed = 0, 0

    for row in rows:
        try:
            payload = to_event_payload(row)
        except (KeyError, ValueError) as e:
            failed += 1
            print(f"행 파싱 실패: {row} -> {e}")
            continue

        try:
            res = requests.post(events_url, json=payload, timeout=5)
            res.raise_for_status()
            total += 1
        except requests.RequestException as e:
            failed += 1
            print(f"업로드 실패: {payload} -> {e}")

    print(f"완료: {total}건 업로드 성공, {failed}건 실패 (대상: {events_url})")


if __name__ == "__main__":
    main()
