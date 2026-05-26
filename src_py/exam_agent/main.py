from __future__ import annotations

import argparse
from pathlib import Path

from .chain import run_chain
from .io_utils import save_json, save_text
from .rendering import html_to_pdf_sync, render_html, render_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Math Exam Agent (Python + LangChain)")
    parser.add_argument("--request", default="request.sample.json")
    parser.add_argument("--out", default="output_py")
    parser.add_argument("--bank", default="../doc/math/exports/math_rag_questions.jsonl")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    req_file = (root / args.request).resolve()
    out_dir = (root / args.out).resolve()
    bank_file = (root / args.bank).resolve()
    schema_file = (Path(__file__).resolve().parent / "config" / "intake_schema.json").resolve()

    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_chain(req_file, schema_file, bank_file)

    if not result["intake"]["ok"]:
        save_json(out_dir / "missing_fields.json", result["intake"])
        print("信息不完整，已输出 missing_fields.json")
        return

    paper = result["paper"]
    save_json(out_dir / "paper.json", paper)

    md = render_markdown(paper)
    html = render_html(paper)
    save_text(out_dir / "paper.md", md)
    save_text(out_dir / "paper.html", html)

    html_to_pdf_sync(out_dir / "paper.html", out_dir / "paper.pdf")
    print("生成完成:")
    print(out_dir / "paper.json")
    print(out_dir / "paper.md")
    print(out_dir / "paper.html")
    print(out_dir / "paper.pdf")


if __name__ == "__main__":
    main()
