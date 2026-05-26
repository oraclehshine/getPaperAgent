from __future__ import annotations

import re
from typing import Any, Dict, List


def _find_exam_mode(text: str) -> str | None:
    if "新高考" in text:
        return "new_gaokao"
    if "老高考" in text:
        return "old_gaokao"
    return None


def _find_grade(text: str) -> str | None:
    for g in ["高一", "高二", "高三"]:
        if g in text:
            return g
    return None


def _find_difficulty(text: str) -> str | None:
    for d in ["基础", "中等", "中高", "冲刺"]:
        if d in text:
            return d
    return None


def _find_minutes(text: str) -> int | None:
    m = re.search(r"(\d{2,3})\s*分钟", text)
    return int(m.group(1)) if m else None


def _find_target(text: str) -> str | None:
    m = re.search(r"(\d{2,3})\s*\+?分", text)
    if m:
        return f"目标{m.group(1)}分"
    if "提升" in text:
        return "提升成绩"
    return None


def _find_recent_score(text: str) -> str | None:
    m = re.search(r"最近\s*(\d{2,3})\s*分", text)
    if m:
        return f"{m.group(1)}/150"
    return None


def _find_current_level(text: str) -> str | None:
    if "基础薄弱" in text or "薄弱" in text:
        return "基础薄弱"
    if "中等" in text:
        return "中等"
    if "拔高" in text or "冲刺" in text:
        return "拔高"
    return None


def _find_weak_points(text: str) -> List[str]:
    pool = ["函数", "导数", "数列", "三角函数", "立体几何", "解析几何", "圆锥曲线", "概率", "统计", "向量"]
    return [k for k in pool if k in text]


def parse_user_text_to_request(user_text: str) -> Dict[str, Any]:
    t = user_text.strip()
    return {
        "subject": "math" if ("数学" in t or "math" in t.lower()) else None,
        "exam_mode": _find_exam_mode(t),
        "study_profile": {
            "grade": _find_grade(t),
            "current_level": _find_current_level(t),
            "weak_points": _find_weak_points(t),
            "recent_score": _find_recent_score(t),
        },
        "expectation": {
            "target": _find_target(t),
            "difficulty": _find_difficulty(t),
            "paper_length_min": _find_minutes(t),
        },
    }
