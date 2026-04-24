from datetime import datetime, timezone

from core.tools.artifact_store import write_json


def handle_intake(run_id: str, raw_idea: str) -> tuple[bool, dict | str]:
    brief = {
        "brief_id": run_id,
        "goal": raw_idea,
        "format": "text",
        "language": "en",
        "constraints": [],
        "required_unknowns": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "normalized",
    }

    ok, msg = write_json(run_id, "brief", brief)
    if not ok:
        return False, f"Failed to write brief artifact: {msg}"

    return True, brief
