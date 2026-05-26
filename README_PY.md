# Python + LangChain Math Exam Agent

## 1) 启动 API
```powershell
cd E:\Agent-do\code
E:\Agent-do\.venv\Scripts\python.exe -m exam_agent.serve --host 127.0.0.1 --port 8000
```

## 2) 打开前端页面
- http://127.0.0.1:8000/

## 3) 接口
- `GET /health`
- `GET /`（前端页面）
- `GET /file?path=...`（下载产物）
- `POST /intake`
- `POST /generate`
- `POST /chat`（多轮，支持 `session_id`）
- `GET /session/{session_id}`
- `DELETE /session/{session_id}`

## 5) 新增能力（已接入）
- 题位蓝图配置：`src_py/exam_agent/config/blueprint_new_gaokao.json`
- PostgreSQL 实时检索：默认开启（表 `rag_questions`）
- PDF 版式：页眉 + 页码 + 客观题作答线 + 解答题答题区

## 6) PostgreSQL 环境变量
```powershell
$env:PGHOST="127.0.0.1"
$env:PGPORT="5432"
$env:PGDATABASE="kch-learn"
$env:PGUSER="postgres"
$env:PGPASSWORD="你的密码"
```

说明：
- `/chat` 与 `/generate` 默认 `use_postgres=true`。
- 若数据库不可用，服务自动回退 `bank_file`（JSONL）题库。

## 4) 多轮 /chat 示例
第1轮：
```json
{
  "user_text": "我要高三数学，新高考，导数和圆锥曲线薄弱",
  "render_pdf": false
}
```
第2轮：
```json
{
  "session_id": "上轮返回的session_id",
  "user_text": "目标110分，120分钟，中高难度",
  "render_pdf": true
}
```


前端面板新增：可直接选择 新高考(19题)/老高考(22题)、难度、时长，这些设置会通过 request_patch 覆盖会话草稿。

