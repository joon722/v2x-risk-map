"""Jetson Nano의 위험 이벤트 업로드를 흉내내는 시더 스크립트

실제로는 Jetson이 차량/지팡이의 GPS·IMU로 거리·TTC를 계산해서
POST /api/events로 실시간 전송하지만, 데모용으로 핫스팟 주변에
가짜 이벤트를 여러 개 뿌려서 지도가 바로 채워지도록 함.

사용법: 서버(uvicorn)를 먼저 켜둔 상태에서
    python seed.py
    python seed.py --url https://your-tunnel-url.trycloudflare.com  # 팀 공용 서버로 쏘고 싶을 때
"""
import argparse
import random
from datetime import datetime, timedelta

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="샘플 위험 이벤트를 서버에 뿌리는 시더")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="업로드 대상 서버 주소 (기본: http://localhost:8000)",
    )
    return parser.parse_args()

# app/config.py의 DEFAULT_CENTER_LAT/LNG와 동일 (숭실대학교)
CENTER_LAT, CENTER_LNG = 37.4956, 126.9573

# 핫스팟별로 위험도 편향(risk_bias)과 이벤트 개수를 다르게 줘서
# 지도에 등급이 섞인 격자들이 보이도록 구성 (캠퍼스 규모라 오프셋을 도시 블록보다 좁게 잡음)
HOTSPOTS = [
    {"lat": CENTER_LAT, "lng": CENTER_LNG, "count": 40, "risk_bias": 3},  # 정문 교차로 - 매우 위험
    {"lat": CENTER_LAT + 0.0012, "lng": CENTER_LNG + 0.0008, "count": 25, "risk_bias": 2},  # 캠퍼스 내부 도로 - 위험
    {"lat": CENTER_LAT - 0.0008, "lng": CENTER_LNG - 0.0012, "count": 15, "risk_bias": 1},  # 후문 방향 - 주의 구간
]


def random_offset(spread: float = 0.0003) -> float:
    """핫스팟 중심 주변으로 좌표를 흩뿌리기 위한 랜덤 오프셋"""
    return random.uniform(-spread, spread)


def risk_to_ttc(risk: int) -> float:
    """위험도가 높을수록 TTC(충돌까지 남은 시간)가 짧아지도록 매핑"""
    base = {0: 5.0, 1: 3.0, 2: 1.5, 3: 0.6}[risk]
    return round(base + random.uniform(-0.3, 0.3), 2)


def gen_event(hotspot: dict) -> dict:
    """핫스팟 하나를 기준으로 이벤트 1건 생성"""
    bias = hotspot["risk_bias"]
    # 편향값 주변으로 약간의 편차를 줘서 등급이 딱 한 값으로 고정되지 않게 함
    risk = max(0, min(3, bias + random.choice([-1, 0, 0, 0, 1])))

    lat = hotspot["lat"] + random_offset()
    lng = hotspot["lng"] + random_offset()
    ttc = risk_to_ttc(risk)

    # 최근 3일 이내로 타임스탬프를 흩어서 누적 데이터처럼 보이게 함
    timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 60 * 24 * 3))

    return {
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "risk": risk,
        "ttc": ttc,
        "timestamp": timestamp.isoformat(),
    }


def main():
    args = parse_args()
    events_url = f"{args.url.rstrip('/')}/api/events"

    total, failed = 0, 0

    for hotspot in HOTSPOTS:
        for _ in range(hotspot["count"]):
            event = gen_event(hotspot)
            try:
                res = requests.post(events_url, json=event, timeout=5)
                res.raise_for_status()
                total += 1
            except requests.RequestException as e:
                failed += 1
                print(f"업로드 실패: {event} -> {e}")

    print(f"완료: {total}건 업로드 성공, {failed}건 실패 (대상: {events_url})")


if __name__ == "__main__":
    main()
