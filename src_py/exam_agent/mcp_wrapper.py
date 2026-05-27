from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("getPaperAgent MCP Wrapper", json_response=True)


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


@mcp.tool()
def search_question_refs(
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    grade: Optional[str] = None,
    subject: str = "math",
    weak_points: Optional[List[str]] = None,
    preferred_question_types: Optional[List[str]] = None,
    limit: int = 80,
    base_url: str = "http://127.0.0.1:8000",
) -> Dict[str, Any]:
    """
    Search question references from getPaperAgent over HTTP and return question_refs.
    """
    weak_points = weak_points or []
    preferred_question_types = preferred_question_types or []
    limit = max(1, min(int(limit), 300))

    payload = {
        "trace_id": trace_id,
        "user": {
            "user_id": user_id,
            "grade": grade,
        },
        "learning_context": {
            "subject": subject,
            "weak_points": weak_points,
        },
        "paper_request": {
            "preferred_question_types": preferred_question_types,
            "limit": limit,
        },
        "extra_context": {},
    }

    try:
        data = _post_json(f"{base_url.rstrip('/')}/v1/subagent/question-refs", payload)
        return data
    except urllib.error.HTTPError as e:
        return {
            "status": "error",
            "error_code": "HTTP_ERROR",
            "message": f"{e.code} {e.reason}",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "error_code": "WRAPPER_ERROR",
            "message": str(e),
        }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

