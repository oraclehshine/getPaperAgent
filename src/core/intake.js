const fs = require('fs');

function readJson(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  return JSON.parse(raw);
}

function validateIntake(request, schema) {
  const missing = [];

  for (const f of schema.required_fields || []) {
    if (request[f] === undefined || request[f] === null || request[f] === '') {
      missing.push(f);
    }
  }

  if (request.subject && request.subject !== 'math') {
    throw new Error('当前仅支持数学学科（subject=math）');
  }

  if (request.exam_mode && !['new_gaokao', 'old_gaokao'].includes(request.exam_mode)) {
    missing.push('exam_mode');
  }

  if (request.study_profile) {
    const s = request.study_profile;
    if (!s.grade || !s.current_level || !Array.isArray(s.weak_points) || s.weak_points.length < 1) {
      missing.push('study_profile');
    }
  }

  if (request.expectation) {
    const e = request.expectation;
    if (!e.target || !e.difficulty || !e.paper_length_min) {
      missing.push('expectation');
    }
  }

  const uniq = [...new Set(missing)];
  return {
    ok: uniq.length === 0,
    missing: uniq,
    questions: uniq.map((k) => schema.clarification_questions[k] || `请补充：${k}`)
  };
}

module.exports = { readJson, validateIntake };
