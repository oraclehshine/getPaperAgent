from __future__ import annotations

import os
from typing import Any, Dict, List


def _repair_mojibake(s: Any) -> Any:
    if not isinstance(s, str) or not s:
        return s
    # Common mojibake markers when UTF-8 text is decoded as GBK.
    markers = ("锛", "銆", "鈥", "楂", "涓", "澶", "鏁", "瀵")
    if not any(m in s for m in markers):
        return s
    for enc in ("gbk", "gb18030"):
        try:
            fixed = s.encode(enc, errors="strict").decode("utf-8", errors="strict")
            if fixed:
                return fixed
        except Exception:
            continue
    return s


def _looks_mojibake_text(s: Any) -> bool:
    if not isinstance(s, str) or not s:
        return False
    markers = ("锛", "銆", "鈥", "楂", "涓", "澶", "鏁", "瀵", "妯", "鍗")
    return any(m in s for m in markers)


def _connect():
    try:
        import psycopg

        return psycopg.connect(
            host=os.getenv("PGHOST", "127.0.0.1"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "kch-learn"),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", ""),
        )
    except ImportError:
        import psycopg2  # type: ignore

        return psycopg2.connect(
            host=os.getenv("PGHOST", "127.0.0.1"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "kch-learn"),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", ""),
        )


def fetch_questions_realtime(weak_points: List[str], limit: int = 5000) -> List[Dict[str, Any]]:
    like_clauses = []
    params: List[Any] = []
    for w in weak_points:
        like_clauses.append("(coalesce(kaodian_name,'') ILIKE %s OR stem_md ILIKE %s OR coalesce(analysis_md,'') ILIKE %s)")
        kw = f"%{w}%"
        params.extend([kw, kw, kw])

    score_expr = "0"
    if like_clauses:
        score_expr = " + ".join([f"CASE WHEN {c} THEN 1 ELSE 0 END" for c in like_clauses])

    sql = f"""
    SELECT
      topic,
      question_no,
      kaodian_no,
      kaodian_name,
      stem_md,
      analysis_md,
      coalesce(image_urls, ARRAY[]::text[]) AS image_urls
    FROM rag_questions
    ORDER BY ({score_expr}) DESC, id ASC
    LIMIT %s
    """
    params.append(limit)

    rows: List[Dict[str, Any]] = []
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            for rec in cur.fetchall():
                obj = dict(zip(cols, rec))
                if obj.get("image_urls") is None:
                    obj["image_urls"] = []
                for k in ("topic", "question_no", "kaodian_no", "kaodian_name", "stem_md", "analysis_md"):
                    obj[k] = _repair_mojibake(obj.get(k))
                rows.append(obj)
    return rows


def has_mojibake_rows(rows: List[Dict[str, Any]]) -> bool:
    sample = rows[:30]
    bad = 0
    total = 0
    for r in sample:
        for k in ("topic", "kaodian_name", "stem_md"):
            total += 1
            if _looks_mojibake_text(r.get(k)):
                bad += 1
    return total > 0 and (bad / total) > 0.15
