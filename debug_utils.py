from __future__ import annotations

import json
import time
from pathlib import Path

_DEBUG_LOG_PATH = Path("/home/afeng/afeng/AI_project_talking_about/.cursor/debug-a22373.log")


def debug_log(location: str, message: str, data: dict, hypothesis_id: str, run_id: str = "initial") -> None:
    payload = {
        "sessionId": "a22373",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
