from datetime import datetime, timezone

from core.tools.artifact_store import read_json, write_json


def handle_research(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "brief")
    if not ok:
        return False, f"Failed to read brief artifact: {result}"

    brief = result
    research = {
        "research_pack_id": run_id,
        "brief_id": brief["brief_id"],
        "research_goal": brief["goal"],
        "findings": [],
        "unknowns": ["no data yet"],
        "recommended_next_queries": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "insufficient",
    }

    ok, msg = write_json(run_id, "research", research)
    if not ok:
        return False, f"Failed to write research artifact: {msg}"

    return True, research
