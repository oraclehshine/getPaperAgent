from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def pick_template(exam_mode: str) -> Dict:
    if exam_mode == "new_gaokao":
        return {
            "title": "高中数学试卷（新高考）",
            "sections": [
                {"name": "单选题", "count": 8},
                {"name": "多选题", "count": 3},
                {"name": "填空题", "count": 3},
                {"name": "解答题", "count": 5},
            ],
        }
    return {
        "title": "高中数学试卷（老高考）",
        "sections": [
            {"name": "选择题", "count": 12},
            {"name": "填空题", "count": 4},
            {"name": "解答题", "count": 6},
        ],
    }


def new_gaokao_position_blueprint() -> Dict[str, List[List[str]]]:
    cfg = Path(__file__).resolve().parent / "config" / "blueprint_new_gaokao.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    out: Dict[str, List[List[str]]] = {}
    for sec, slots in data.get("sections", {}).items():
        out[sec] = [s.get("knowledge_points", []) for s in slots]
    return out


def new_gaokao_slot_blueprint() -> Dict[str, List[Dict]]:
    cfg = Path(__file__).resolve().parent / "config" / "blueprint_new_gaokao.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    return data.get("sections", {})


def diff_score(q: Dict) -> int:
    t = f"{q.get('stem_md', '')} {q.get('analysis_md', '')}"
    score = 0
    if any(k in t for k in ["压轴", "综合", "圆锥曲线", "导数证明", "最值"]):
        score += 2
    if any(k in t for k in ["基础", "概念", "直接计算"]):
        score -= 1
    return score


def unique_by_stem(rows: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for r in rows:
        k = (r.get("stem_md") or "")[:120]
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def split_diff(rows: List[Dict]) -> Dict[str, List[Dict]]:
    arr = sorted(rows, key=diff_score)
    n = len(arr)
    return {
        "basic": arr[: int(n * 0.5)],
        "mid": arr[int(n * 0.5) : int(n * 0.85)],
        "hard": arr[int(n * 0.85) :],
    }
