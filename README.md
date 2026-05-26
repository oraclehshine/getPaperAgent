# getPaperAgent

高考数学智能组卷 Agent（Python + LangChain + FastAPI）。

## 项目能力

- 新高考/老高考双模式组卷
- 严格采集必填信息：`subject`、`study_profile`、`expectation`、`exam_mode`
- 新高考 19 题结构（8 单选 + 3 多选 + 3 填空 + 5 解答）
- 题位-知识点-难度蓝图可配置
- PostgreSQL 实时检索题库（不可用时自动回退 JSONL）
- 图片本地化拷贝，避免外链失效
- 数学公式 MathJax 渲染，支持 HTML/PDF 导出
- PDF 版式：标题、页眉、页码、作答线、解答题答题区

## 目录结构

- `src_py/exam_agent/`：Python 主实现
- `src_py/exam_agent/config/intake_schema.json`：输入采集约束
- `src_py/exam_agent/config/blueprint_new_gaokao.json`：新高考题位蓝图
- `output_py_api/`：API 输出目录（paper json/md/html/pdf + assets）
- `../doc/math/exports/math_rag_questions.jsonl`：本地题库回退文件
- `../doc/math/exports/math_rag_questions.csv`：初始化/重灌 PG 数据源

## 环境准备

建议 Python 3.11+。

```powershell
cd E:\Agent-do\code
python -m pip install -e .
python -m pip install fastapi uvicorn psycopg[binary] psycopg2-binary playwright
python -m playwright install chromium
```

## PostgreSQL 配置

```powershell
$env:PGHOST="127.0.0.1"
$env:PGPORT="5432"
$env:PGDATABASE="kch-learn"
$env:PGUSER="postgres"
$env:PGPASSWORD="<your-password>"
```

说明：服务默认尝试 PostgreSQL 实时检索；如果数据库不可用或检测到乱码数据，会自动回退到 JSONL 题库。

## 启动服务

```powershell
$env:PYTHONPATH="E:\Agent-do\code\src_py"
python -m exam_agent.serve --host 127.0.0.1 --port 8000
```

打开：`http://127.0.0.1:8000/`

## 核心接口

- `GET /health`
- `GET /`
- `GET /file?path=...`
- `POST /intake`
- `POST /generate`
- `POST /chat`
- `GET /session/{session_id}`
- `DELETE /session/{session_id}`

## 生成示例

```json
{
  "request": {
    "subject": "math",
    "exam_mode": "new_gaokao",
    "study_profile": {
      "grade": "高三",
      "current_level": "中等",
      "weak_points": ["导数", "圆锥曲线"],
      "recent_score": "95/150"
    },
    "expectation": {
      "target": "110+",
      "difficulty": "中高",
      "paper_length_min": 120
    }
  },
  "use_postgres": true,
  "render_pdf": true
}
```

## 相关文档

- `../doc/math_exam_agent_init_plan.md`
- `../doc/math_exam_agent_技术实现说明.md`
- `../doc/新高考题位蓝图_联网依据与配置说明.md`

## 常见问题

1. `No module named uvicorn/playwright`
- 重新安装依赖并执行 `python -m playwright install chromium`

2. 题目中文乱码
- 优先检查 PostgreSQL 导入编码（UTF-8）
- 可运行 `../doc/math/init/_repair_reimport.sql` 进行重灌

3. 图片不显示
- 检查生成目录下 `paper_<id>_assets` 是否存在
- HTML/Markdown 应引用 `./paper_<id>_assets/...`
