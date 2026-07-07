"""OSM 도로망을 불러와서 위험 이벤트를 가장 가까운 도로 구간에 스냅하는 로직

app/data/roads.json은 Overpass API로 미리 받아둔 숭실대 주변 도로(way) 목록
(각 way는 [lat, lng] 점들의 리스트). 여기서는 각 way를 인접한 두 점씩 잘라
"엣지" 단위로 쪼갠 뒤, 이벤트 좌표에서 가장 가까운 엣지를 찾아 그 엣지에
누적시킨다. 격자 대신 실제 도로 위에만 위험도가 표시되도록 하기 위함.
"""
import json
import math
from pathlib import Path

from app.config import DEFAULT_CENTER_LAT

ROADS_PATH = Path(__file__).resolve().parent / "data" / "roads.json"

# 위경도를 로컬 평면 좌표(미터)로 근사 변환하기 위한 기준점
# 캠퍼스 규모의 작은 영역이라 등장방형(equirectangular) 근사로 충분함
_LAT_TO_M = 110_540.0
_LNG_TO_M = 111_320.0 * math.cos(math.radians(DEFAULT_CENTER_LAT))


def _to_xy(lat: float, lng: float) -> tuple[float, float]:
    return lng * _LNG_TO_M, lat * _LAT_TO_M


class _Edge:
    __slots__ = ("id", "p1", "p2", "x1", "y1", "x2", "y2")

    def __init__(self, edge_id: str, p1: tuple[float, float], p2: tuple[float, float]):
        self.id = edge_id
        self.p1 = p1
        self.p2 = p2
        self.x1, self.y1 = _to_xy(*p1)
        self.x2, self.y2 = _to_xy(*p2)


def _load_edges() -> list[_Edge]:
    with open(ROADS_PATH, encoding="utf-8") as f:
        roads = json.load(f)

    edges = []
    for road in roads:
        points = road["points"]
        for i in range(len(points) - 1):
            edge_id = f"{road['id']}_{i}"
            p1 = (points[i][0], points[i][1])
            p2 = (points[i + 1][0], points[i + 1][1])
            edges.append(_Edge(edge_id, p1, p2))
    return edges


_EDGES = _load_edges()
_EDGES_BY_ID = {e.id: e for e in _EDGES}


def _point_to_segment_dist_sq(px, py, ax, ay, bx, by) -> float:
    """점(px,py)에서 선분(a-b)까지의 최단 거리의 제곱 (미터^2)"""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return (px - ax) ** 2 + (py - ay) ** 2

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2


def nearest_edge_id(lat: float, lng: float) -> str:
    """주어진 좌표에서 가장 가까운 도로 엣지의 id를 반환"""
    px, py = _to_xy(lat, lng)

    best_id = None
    best_dist_sq = math.inf
    for edge in _EDGES:
        d = _point_to_segment_dist_sq(px, py, edge.x1, edge.y1, edge.x2, edge.y2)
        if d < best_dist_sq:
            best_dist_sq = d
            best_id = edge.id

    return best_id


def get_edge_points(edge_id: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """엣지 id로 양 끝점 좌표 반환 (프론트에서 폴리라인 그릴 때 사용)"""
    edge = _EDGES_BY_ID[edge_id]
    return edge.p1, edge.p2
