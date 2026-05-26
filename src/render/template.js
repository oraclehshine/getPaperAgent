function esc(s = '') {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function mdLikeToHtml(s = '') {
  return esc(s)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
}

function paperToHtml(paper) {
  const body = [];
  body.push(`<h1>${esc(paper.title)}</h1>`);
  body.push(`<div class="meta">模式：${esc(paper.exam_mode)}；时长：${esc(paper.request.expectation.paper_length_min)} 分钟；难度：${esc(paper.request.expectation.difficulty)}</div>`);

  for (const sec of paper.sections) {
    body.push(`<h2>${esc(sec.name)}</h2>`);
    sec.questions.forEach((q, i) => {
      body.push(`<div class="q"><b>${i + 1}.</b> ${mdLikeToHtml(q.stem_md || '')}</div>`);
      for (const u of q.image_urls || []) {
        body.push(`<div class="img"><img src="${u}" style="max-width:100%"/></div>`);
      }
    });
  }

  body.push('<div style="page-break-before:always"></div><h1>答案与解析</h1>');
  for (const sec of paper.sections) {
    body.push(`<h2>${esc(sec.name)}</h2>`);
    sec.questions.forEach((q, i) => {
      body.push(`<div class="q"><b>${i + 1}.</b> ${mdLikeToHtml(q.analysis_md || '（暂无解析）')}</div>`);
      for (const u of q.image_urls || []) {
        body.push(`<div class="img"><img src="${u}" style="max-width:100%"/></div>`);
      }
    });
  }

  return `<!doctype html><html><head><meta charset="utf-8"/><style>
body{font-family:"Microsoft YaHei",sans-serif;padding:24px;line-height:1.6}
.meta{color:#666;font-size:13px}
h2{border-bottom:1px solid #ddd;padding-bottom:6px;margin-top:24px}
.q{margin:10px 0}.img{margin:8px 0}
</style></head><body>${body.join('\n')}</body></html>`;
}

function paperToMarkdown(paper) {
  const out = [];
  out.push(`# ${paper.title}`);
  out.push(`- 模式: ${paper.exam_mode}`);
  out.push(`- 时长: ${paper.request.expectation.paper_length_min} 分钟`);
  out.push('');

  for (const sec of paper.sections) {
    out.push(`## ${sec.name}`);
    sec.questions.forEach((q, i) => {
      out.push(`${i + 1}. ${q.stem_md || ''}`);
      (q.image_urls || []).forEach((u) => out.push(`![](${u})`));
      out.push('');
    });
  }

  out.push('---');
  out.push('# 答案与解析');
  for (const sec of paper.sections) {
    out.push(`## ${sec.name}`);
    sec.questions.forEach((q, i) => {
      out.push(`${i + 1}. ${q.analysis_md || '（暂无解析）'}`);
      (q.image_urls || []).forEach((u) => out.push(`![](${u})`));
      out.push('');
    });
  }
  return out.join('\n');
}

module.exports = { paperToHtml, paperToMarkdown };
