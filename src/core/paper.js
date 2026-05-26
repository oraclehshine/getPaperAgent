const fs = require('fs');

function readJsonl(filePath) {
  return fs
    .readFileSync(filePath, 'utf8')
    .replace(/^\uFEFF/, '')
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function pickTemplate(examMode) {
  if (examMode === 'new_gaokao') {
    return {
      title: '高中数学试卷（新高考）',
      sections: [
        { name: '单选题', count: 8 },
        { name: '多选题', count: 3 },
        { name: '填空题', count: 3 },
        { name: '解答题', count: 5 }
      ]
    };
  }

  return {
    title: '高中数学试卷（老高考）',
    sections: [
      { name: '选择题', count: 12 },
      { name: '填空题', count: 3 },
      { name: '解答题', count: 5 }
    ]
  };
}

function diffScore(q) {
  const t = `${q.stem_md || ''} ${q.analysis_md || ''}`;
  let s = 0;
  if (/压轴|综合|圆锥曲线|导数证明|最值/.test(t)) s += 2;
  if (/基础|概念|直接计算/.test(t)) s -= 1;
  return s;
}

function uniqueByStem(rows) {
  const seen = new Set();
  const out = [];
  for (const r of rows) {
    const key = (r.stem_md || '').slice(0, 120);
    if (!seen.has(key)) {
      seen.add(key);
      out.push(r);
    }
  }
  return out;
}

function splitDifficulty(rows) {
  const arr = [...rows].sort((a, b) => diffScore(a) - diffScore(b));
  const n = arr.length;
  return {
    basic: arr.slice(0, Math.floor(n * 0.5)),
    mid: arr.slice(Math.floor(n * 0.5), Math.floor(n * 0.85)),
    hard: arr.slice(Math.floor(n * 0.85))
  };
}

function buildPaper(request, questionBank) {
  const template = pickTemplate(request.exam_mode);
  const weakPoints = request.study_profile.weak_points || [];

  const weakHit = questionBank.filter((q) =>
    weakPoints.some((w) => `${q.kaodian_name || ''}${q.stem_md || ''}${q.analysis_md || ''}`.includes(w))
  );

  let candidates = uniqueByStem([...weakHit, ...questionBank]);

  const totalNeed = template.sections.reduce((sum, s) => sum + s.count, 0);
  if (candidates.length < totalNeed) {
    throw new Error(`题库数量不足，需 ${totalNeed} 题，实际 ${candidates.length} 题`);
  }

  const pool = splitDifficulty(candidates);
  const basicNeed = Math.floor(totalNeed * 0.5);
  const midNeed = Math.floor(totalNeed * 0.35);
  const hardNeed = totalNeed - basicNeed - midNeed;

  const picked = [
    ...pool.basic.slice(0, basicNeed),
    ...pool.mid.slice(0, midNeed),
    ...pool.hard.slice(0, hardNeed)
  ];

  let idx = 0;
  const sections = template.sections.map((sec) => {
    const qs = picked.slice(idx, idx + sec.count);
    idx += sec.count;
    return { ...sec, questions: qs };
  });

  return {
    title: template.title,
    exam_mode: request.exam_mode,
    request,
    sections,
    stats: {
      total_questions: totalNeed,
      weak_points: weakPoints,
      weak_hit_count: picked.filter((q) =>
        weakPoints.some((w) => `${q.kaodian_name || ''}${q.stem_md || ''}`.includes(w))
      ).length
    }
  };
}

module.exports = { readJsonl, buildPaper };

