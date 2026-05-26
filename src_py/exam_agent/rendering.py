from __future__ import annotations

import asyncio
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from playwright.async_api import async_playwright


def md_like_to_html(text: str) -> str:
    return escape(text or "").replace("\n", "<br/>")


def safe_url(u: str) -> str:
    if not u:
        return u
    sp = urlsplit(u)
    # 对 path 中中文/空格做编码，避免 PDF 渲染时图片丢失
    path = quote(sp.path, safe="/%")
    return urlunsplit((sp.scheme, sp.netloc, path, sp.query, sp.fragment))


def render_html(paper: dict) -> str:
    body = []
    body.append(f"<h1>{escape(paper['title'])}</h1>")
    body.append(
        f"<div class='meta'>模式：{escape(paper['exam_mode'])}；时长：{paper['request']['expectation']['paper_length_min']} 分钟；难度：{escape(paper['request']['expectation']['difficulty'])}</div>"
    )
    body.append("<div class='student'>姓名：__________ 班级：__________ 准考证号：________________</div>")

    for sec in paper["sections"]:
        body.append(f"<h2>{escape(sec['name'])}</h2>")
        for i, q in enumerate(sec["questions"], start=1):
            body.append(f"<div class='q'><b>{i}.</b> {md_like_to_html(q.get('stem_md', ''))}</div>")
            for u in q.get("image_urls", []):
                body.append(f"<div class='img'><img src='{safe_url(u)}' style='max-width:100%'/></div>")
            if sec["name"] in ("解答题",):
                body.append("<div class='answer-box'>解答区：</div>")
            else:
                body.append("<div class='answer-line'>作答：________________________________________</div>")

    body.append("<div style='page-break-before:always'></div><h1>答案与解析</h1>")
    for sec in paper["sections"]:
        body.append(f"<h2>{escape(sec['name'])}</h2>")
        for i, q in enumerate(sec["questions"], start=1):
            body.append(f"<div class='q'><b>{i}.</b> {md_like_to_html(q.get('analysis_md') or '（暂无解析）')}</div>")
            for u in q.get("image_urls", []):
                body.append(f"<div class='img'><img src='{safe_url(u)}' style='max-width:100%'/></div>")

    return """<!doctype html><html><head><meta charset='utf-8'/>
<script>
window.MathJax = {
  tex: { inlineMath: [['$','$'], ['\\\\(','\\\\)']], displayMath: [['$$','$$'], ['\\\\[','\\\\]']] },
  svg: { fontCache: 'global' }
};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
body{font-family:'Microsoft YaHei','PingFang SC','Noto Sans CJK SC',sans-serif;padding:8px 24px 24px 24px;line-height:1.6}
.q, .q *{font-family:'Cambria Math','STIX Two Math','Times New Roman','Microsoft YaHei',serif}
.meta{color:#666;font-size:13px}
.student{margin:8px 0 14px 0;font-size:13px}
h2{border-bottom:1px solid #ddd;padding-bottom:6px;margin-top:24px}
.q{margin:10px 0}.img{margin:8px 0}
.answer-line{margin:8px 0 16px 0;color:#333}
.answer-box{border:1px solid #cfcfcf; min-height:160px; margin:8px 0 20px 0; padding:8px; color:#666}
</style></head><body>""" + "\n".join(body) + "</body></html>"


def render_markdown(paper: dict) -> str:
    out = [f"# {paper['title']}", f"- 模式: {paper['exam_mode']}", ""]
    for sec in paper["sections"]:
        out.append(f"## {sec['name']}")
        for i, q in enumerate(sec["questions"], start=1):
            out.append(f"{i}. {q.get('stem_md','')}")
            for u in q.get("image_urls", []):
                out.append(f"![]({u})")
            out.append("")
    out.append("---\n# 答案与解析")
    for sec in paper["sections"]:
        out.append(f"## {sec['name']}")
        for i, q in enumerate(sec["questions"], start=1):
            out.append(f"{i}. {q.get('analysis_md') or '（暂无解析）'}")
            for u in q.get("image_urls", []):
                out.append(f"![]({u})")
            out.append("")
    return "\n".join(out)


async def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("file://" + str(html_path.resolve()).replace("\\", "/"), wait_until="networkidle")
        # 等待 MathJax 加载并完成公式排版，避免 PDF 中公式乱码/未渲染
        try:
            await page.wait_for_function("window.MathJax && MathJax.typesetPromise", timeout=15000)
            await page.evaluate("MathJax.typesetPromise()")
        except Exception:
            # 若网络受限导致 MathJax 未加载，继续导出（至少保证文本可见）
            pass
        await page.pdf(
            path=str(pdf_path.resolve()),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="""
                <div style='width:100%; font-size:9px; padding:0 12mm; color:#555; text-align:center;'>
                  高中数学试卷 | <span class='title'></span>
                </div>
            """,
            footer_template="""
                <div style='width:100%; font-size:9px; padding:0 12mm; color:#555; text-align:center;'>
                  第 <span class='pageNumber'></span> / <span class='totalPages'></span> 页
                </div>
            """,
            margin={"top": "20mm", "right": "12mm", "bottom": "18mm", "left": "12mm"},
        )
        await browser.close()


def html_to_pdf_sync(html_path: Path, pdf_path: Path) -> None:
    asyncio.run(html_to_pdf(html_path, pdf_path))
