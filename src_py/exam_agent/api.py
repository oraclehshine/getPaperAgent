from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .chain import run_chain
from .db_store import fetch_questions_realtime, has_mojibake_rows
from .io_utils import save_json, save_text
from .rendering import html_to_pdf_sync, render_html, render_markdown
from .nlp_parse import parse_user_text_to_request
from .session_utils import deep_merge


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = (Path(__file__).resolve().parent / "config" / "intake_schema.json").resolve()
DEFAULT_BANK = (ROOT / "../doc/math/exports/math_rag_questions.jsonl").resolve()
DEFAULT_OUT = (ROOT / "output_py_api").resolve()
DONE_FULL_DIR = (ROOT / "../doc/math/done_full").resolve()
DEFAULT_USE_POSTGRES = True
_GLOBAL_IMG_INDEX: Dict[str, Path] | None = None

# in-memory session store: session_id -> request draft
SESSION_STORE: Dict[str, Dict[str, Any]] = {}


class GeneratePayload(BaseModel):
    request: Dict[str, Any]
    out_dir: str = Field(default=str(DEFAULT_OUT))
    bank_file: str = Field(default=str(DEFAULT_BANK))
    use_postgres: bool = Field(default=DEFAULT_USE_POSTGRES)
    render_pdf: bool = True


class IntakePayload(BaseModel):
    request: Dict[str, Any]


class ChatPayload(BaseModel):
    user_text: str
    session_id: Optional[str] = None
    request_patch: Optional[Dict[str, Any]] = None
    out_dir: str = Field(default=str(DEFAULT_OUT))
    bank_file: str = Field(default=str(DEFAULT_BANK))
    use_postgres: bool = Field(default=DEFAULT_USE_POSTGRES)
    render_pdf: bool = True


app = FastAPI(title="Math Exam Agent API", version="0.3.0")
WEB_INDEX = (Path(__file__).resolve().parent / "web" / "index.html").resolve()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def web_index() -> FileResponse:
    return FileResponse(str(WEB_INDEX), media_type="text/html")


@app.get("/file")
def get_file(path: str = Query(..., description="Absolute path to output artifact")) -> FileResponse:
    p = Path(path).resolve()
    allowed_roots = [
        (ROOT / "output_py_api").resolve(),
        (ROOT / "output").resolve(),
    ]
    if not any(str(p).startswith(str(r)) for r in allowed_roots):
        raise HTTPException(status_code=403, detail="path not allowed")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(str(p))


@app.get("/session/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    draft = SESSION_STORE.get(session_id)
    if not draft:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "draft": draft}


@app.delete("/session/{session_id}")
def clear_session(session_id: str) -> Dict[str, Any]:
    SESSION_STORE.pop(session_id, None)
    return {"ok": True, "session_id": session_id}


def _run_with_request(
    request: Dict[str, Any],
    out_dir: Path,
    bank_file: Path,
    render_pdf: bool,
    use_postgres: bool = DEFAULT_USE_POSTGRES,
) -> Dict[str, Any]:
    import tempfile

    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(request, f, ensure_ascii=False)
        req_file = Path(f.name)

    question_bank = None
    if use_postgres:
        try:
            weak = ((request.get("study_profile") or {}).get("weak_points") or [])
            question_bank = fetch_questions_realtime(weak_points=weak, limit=10000)
            if has_mojibake_rows(question_bank):
                question_bank = None
        except Exception:
            # 数据库异常时回退本地 JSONL，保证服务可用
            question_bank = None
    result = run_chain(req_file, SCHEMA_FILE, bank_file, question_bank=question_bank)

    if not result["intake"]["ok"]:
        save_json(out_dir / "missing_fields.json", result["intake"])
        return {"ok": False, "intake": result["intake"], "next_questions": result["intake"]["questions"]}

    paper = result["paper"]
    q_keys = []
    for sec in paper.get("sections", []):
        for q in sec.get("questions", []):
            q_keys.append(f"{q.get('topic','')}|{q.get('question_no','')}|{q.get('kaodian_no','')}")
    stable_src = json.dumps(request, ensure_ascii=False, sort_keys=True) + "||" + "||".join(sorted(q_keys))
    paper_id = hashlib.sha1(stable_src.encode("utf-8")).hexdigest()[:12]

    paper_json = out_dir / f"paper_{paper_id}.json"
    paper_md = out_dir / f"paper_{paper_id}.md"
    paper_html = out_dir / f"paper_{paper_id}.html"
    paper_pdf = out_dir / f"paper_{paper_id}.pdf"
    paper_assets_dir = out_dir / f"paper_{paper_id}_assets"

    _localize_paper_images(paper, paper_assets_dir)

    save_json(paper_json, paper)
    save_text(paper_md, render_markdown(paper))
    save_text(paper_html, render_html(paper))

    if render_pdf:
        html_to_pdf_sync(paper_html, paper_pdf)

    return {
        "ok": True,
        "intake": result["intake"],
        "outputs": {
            "paper_json": str(paper_json),
            "paper_md": str(paper_md),
            "paper_html": str(paper_html),
            "paper_pdf": str(paper_pdf) if render_pdf else None,
        },
        "stats": paper.get("stats", {}),
    }


def _extract_image_name(u: str) -> str:
    if not u:
        return ""
    p = urlparse(u).path
    return Path(p).name


def _localize_paper_images(paper: Dict[str, Any], assets_dir: Path) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)
    global _GLOBAL_IMG_INDEX

    def find_src_image(topic: str, kp_no: str, kp_name: str, img_name: str) -> Optional[Path]:
        topic_dir = DONE_FULL_DIR / topic
        if topic_dir.exists():
            kp_no = (kp_no or "").zfill(2)
            candidates = [
                topic_dir / f"考点{kp_no}+{kp_name}" / "images" / img_name,
                topic_dir / "images" / img_name,
            ]
            for c in candidates:
                if c.exists():
                    return c
        # 回退：按图片文件名全局检索（解决 topic/考点名乱码导致定位失败）
        if _GLOBAL_IMG_INDEX is None:
            idx: Dict[str, Path] = {}
            for p in DONE_FULL_DIR.rglob("*"):
                if p.is_file() and p.parent.name == "images":
                    idx.setdefault(p.name, p)
            _GLOBAL_IMG_INDEX = idx
        return _GLOBAL_IMG_INDEX.get(img_name)

    for sec in paper.get("sections", []):
        for q in sec.get("questions", []):
            topic = q.get("topic", "")
            kp_no = q.get("kaodian_no", "")
            kp_name = q.get("kaodian_name", "")
            urls = q.get("image_urls", []) or []
            local_urls = []
            for u in urls:
                img_name = _extract_image_name(u)
                if not img_name:
                    continue
                src = find_src_image(topic, kp_no, kp_name, img_name)
                if not src:
                    continue
                dst = assets_dir / img_name
                if not dst.exists():
                    shutil.copy2(src, dst)
                local_urls.append(f"./{assets_dir.name}/{img_name}")
            q["image_urls"] = local_urls


@app.post("/intake")
def intake(payload: IntakePayload) -> Dict[str, Any]:
    res = _run_with_request(payload.request, DEFAULT_OUT, DEFAULT_BANK, render_pdf=False, use_postgres=DEFAULT_USE_POSTGRES)
    return res["intake"]


@app.post("/generate")
def generate(payload: GeneratePayload) -> Dict[str, Any]:
    out_dir = Path(payload.out_dir).resolve()
    bank_file = Path(payload.bank_file).resolve()
    try:
        res = _run_with_request(payload.request, out_dir, bank_file, payload.render_pdf, payload.use_postgres)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not res["ok"]:
        raise HTTPException(status_code=400, detail=res)
    return res


@app.post("/chat")
def chat(payload: ChatPayload) -> Dict[str, Any]:
    out_dir = Path(payload.out_dir).resolve()
    bank_file = Path(payload.bank_file).resolve()

    try:
        extracted = parse_user_text_to_request(payload.user_text)

        session_id = payload.session_id or str(uuid4())
        existing = SESSION_STORE.get(session_id, {
            "subject": None,
            "exam_mode": None,
            "study_profile": {"grade": None, "current_level": None, "weak_points": [], "recent_score": None},
            "expectation": {"target": None, "difficulty": None, "paper_length_min": None},
        })

        merged = deep_merge(existing, extracted)
        if payload.request_patch:
            merged = deep_merge(merged, payload.request_patch)
        SESSION_STORE[session_id] = merged

        res = _run_with_request(merged, out_dir, bank_file, payload.render_pdf, payload.use_postgres)
        res["session_id"] = session_id
        res["parsed_request"] = extracted
        res["merged_request"] = merged

        if res["ok"]:
            # cleanup completed session
            SESSION_STORE.pop(session_id, None)

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
