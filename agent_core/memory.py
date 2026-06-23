from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_core.state import AgentState


def save_run_memory(state: AgentState, manifest: dict[str, Any]) -> Path:
    run_dir = state.output_dir / "runs" / state.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run_manifest.json"

    payload = {
        "state": state.as_dict(),
        "manifest": manifest,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
