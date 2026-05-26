from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.runnables import RunnableLambda, RunnableSequence

from .io_utils import load_json, load_jsonl
from .paper_logic import new_gaokao_slot_blueprint, pick_template, split_diff, unique_by_stem, diff_score

IMG_MD_RE = re.compile(r"!\[[^\]]*\]\((images/[^)]+)\)")
IMG_HTML_RE = re.compile(r'<img[^>]*src="(images/[^"]+)"')


def _extract_image_names(text: str) -> List[str]:
    names: List[str] = []
    if not text:
        return names
    for m in IMG_MD_RE.findall(text):
        names.append(m.split("/")[-1])
    for m in IMG_HTML_RE.findall(text):
        names.append(m.split("/")[-1])
    return names


def _normalize_image_urls(q: Dict[str, Any]) -> Dict[str, Any]:
    urls = list(q.get("image_urls") or [])
    if urls:
        q["image_urls"] = urls
        return q

    topic = q.get("topic", "")
    kp_name = q.get("kaodian_name", "")
    kp_no = (q.get("kaodian_no") or "").strip()
    if not topic or not kp_name or not kp_no:
        q["image_urls"] = []
        return q

    names = _extract_image_names(q.get("stem_md", "")) + _extract_image_names(q.get("analysis_md", ""))
    uniq_urls: List[str] = []
    seen = set()
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        uniq_urls.append(
            f"https://kch-learn.oss-cn-beijing.aliyuncs.com/math/{topic}/考点{kp_no.zfill(2)}+{kp_name}/assets/{n}"
        )
    q["image_urls"] = uniq_urls
    return q


def _check_intake(payload: Dict[str, Any]) -> Dict[str, Any]:
    req = payload["request"]
    schema = payload["schema"]
    missing = []
    for f in schema.get("required_fields", []):
        if f not in req or req[f] in (None, ""):
            missing.append(f)

    if req.get("subject") and req.get("subject") != "math":
        raise ValueError("当前仅支持数学（subject=math）")

    if req.get("exam_mode") not in ("new_gaokao", "old_gaokao"):
        missing.append("exam_mode")

    sp = req.get("study_profile") or {}
    if not sp.get("grade") or not sp.get("current_level") or not isinstance(sp.get("weak_points"), list) or len(sp.get("weak_points", [])) < 1:
        missing.append("study_profile")

    ex = req.get("expectation") or {}
    if not ex.get("target") or not ex.get("difficulty") or not ex.get("paper_length_min"):
        missing.append("expectation")

    missing = sorted(set(missing))
    payload["intake"] = {
        "ok": len(missing) == 0,
        "missing": missing,
        "questions": [schema.get("clarification_questions", {}).get(m, f"请补充：{m}") for m in missing],
    }
    return payload


def _assemble_paper(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not payload["intake"]["ok"]:
        return payload

    req = payload["request"]
    bank = payload["question_bank"]
    weak = req["study_profile"]["weak_points"]

    weak_rows = [
        q
        for q in bank
        if any(w in f"{q.get('kaodian_name','')}{q.get('stem_md','')}{q.get('analysis_md','')}" for w in weak)
    ]

    candidates = unique_by_stem(weak_rows + bank)
    template = pick_template(req["exam_mode"])
    total_need = sum(s["count"] for s in template["sections"])
    if len(candidates) < total_need:
        raise ValueError(f"题库不足：need={total_need}, got={len(candidates)}")

    sections: List[Dict[str, Any]] = []
    selected: List[Dict[str, Any]] = []

    # 新高考：按题号位置蓝图选题；不足时回退到全候选池
    if req["exam_mode"] == "new_gaokao":
        blueprint = new_gaokao_slot_blueprint()
        remaining = [dict(x) for x in candidates]
        for sec in template["sections"]:
            sec_name = sec["name"]
            sec_count = sec["count"]
            slots = blueprint.get(sec_name, [])
            sec_rows: List[Dict[str, Any]] = []

            for i in range(sec_count):
                slot = slots[i] if i < len(slots) else {}
                kws = slot.get("knowledge_points", [])
                diff_name = slot.get("difficulty", "medium")
                if diff_name == "easy":
                    diff_ok = lambda s: s <= 0
                elif diff_name == "medium":
                    diff_ok = lambda s: 0 <= s <= 1
                elif diff_name == "medium_hard":
                    diff_ok = lambda s: s >= 1
                else:
                    diff_ok = lambda s: s >= 2
                picked_idx = None
                for idx, q in enumerate(remaining):
                    text = f"{q.get('topic','')} {q.get('kaodian_name','')} {q.get('stem_md','')}"
                    if kws and any(k in text for k in kws) and diff_ok(diff_score(q)):
                        picked_idx = idx
                        break
                if picked_idx is None and remaining:
                    picked_idx = 0
                if picked_idx is not None:
                    sec_rows.append(remaining.pop(picked_idx))

            sec_rows = [_normalize_image_urls(dict(x)) for x in sec_rows]
            selected.extend(sec_rows)
            sections.append({"name": sec_name, "count": len(sec_rows), "questions": sec_rows})
    else:
        pools = split_diff(candidates)
        basic_need = int(total_need * 0.5)
        mid_need = int(total_need * 0.35)
        hard_need = total_need - basic_need - mid_need
        selected = pools["basic"][:basic_need] + pools["mid"][:mid_need] + pools["hard"][:hard_need]

        idx = 0
        for sec in template["sections"]:
            c = sec["count"]
            rows = [_normalize_image_urls(dict(x)) for x in selected[idx : idx + c]]
            sections.append({"name": sec["name"], "count": c, "questions": rows})
            idx += c

    payload["paper"] = {
        "title": template["title"],
        "exam_mode": req["exam_mode"],
        "request": req,
        "sections": sections,
        "stats": {
            "total_questions": total_need,
            "weak_points": weak,
            "weak_hit_count": sum(
                1
                for q in selected
                if any(w in f"{q.get('kaodian_name','')}{q.get('stem_md','')}" for w in weak)
            ),
        },
    }
    return payload


def build_agent_chain() -> RunnableSequence:
    return RunnableLambda(_check_intake) | RunnableLambda(_assemble_paper)


def run_chain(
    request_file: Path,
    schema_file: Path,
    bank_file: Path | None = None,
    question_bank: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    bank = question_bank if question_bank is not None else load_jsonl(bank_file)  # type: ignore[arg-type]
    payload = {
        "request": load_json(request_file),
        "schema": load_json(schema_file),
        "question_bank": bank,
    }
    return build_agent_chain().invoke(payload)
