const fs = require('fs');
const path = require('path');
const { readJson, validateIntake } = require('./core/intake');
const { readJsonl, buildPaper } = require('./core/paper');
const { paperToHtml, paperToMarkdown } = require('./render/template');
const { renderPdf } = require('./render/pdf');

async function main() {
  const requestFile = process.argv[2] || path.resolve(__dirname, '../request.sample.json');
  const outDir = process.argv[3] || path.resolve(__dirname, '../output');

  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const schema = readJson(path.resolve(__dirname, './config/intake_schema.json'));
  const request = readJson(requestFile);

  const check = validateIntake(request, schema);
  if (!check.ok) {
    const miss = { missing: check.missing, questions: check.questions };
    fs.writeFileSync(path.join(outDir, 'missing_fields.json'), JSON.stringify(miss, null, 2));
    console.log('信息不完整，请先补充：', check.missing.join(','));
    process.exit(2);
  }

  const bank = readJsonl(path.resolve(__dirname, '../../doc/math/exports/math_rag_questions.jsonl'));
  const paper = buildPaper(request, bank);

  fs.writeFileSync(path.join(outDir, 'paper.json'), JSON.stringify(paper, null, 2));
  fs.writeFileSync(path.join(outDir, 'paper.md'), paperToMarkdown(paper), 'utf8');

  const html = paperToHtml(paper);
  const htmlFile = path.join(outDir, 'paper.html');
  const pdfFile = path.join(outDir, 'paper.pdf');
  fs.writeFileSync(htmlFile, html, 'utf8');

  await renderPdf(htmlFile, pdfFile);

  console.log('生成完成:');
  console.log('- ' + path.join(outDir, 'paper.json'));
  console.log('- ' + path.join(outDir, 'paper.md'));
  console.log('- ' + path.join(outDir, 'paper.html'));
  console.log('- ' + path.join(outDir, 'paper.pdf'));
}

main().catch((e) => {
  console.error('执行失败:', e.message || e);
  process.exit(1);
});
