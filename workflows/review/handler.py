from datetime import datetime, timezone

from core.tools.artifact_store import read_json, write_json


def handle_review(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "script")
    if not ok:
        return False, f"Failed to read script artifact: {result}"
    script = result

    review = {
        "report_id": f"{run_id}_review",
        "run_id": run_id,
        "script_id": script["script_id"],
        "technical_pass": True,
        "quality_pass": True,
        "factual_pass": True,
        "violations": [],
        "uncertainties": [],
        "required_actions": [],
        "verdict": "approved",
        "summary": "Stub review passed.",
        "reasoning": "All checks passed in stub mode without LLM.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    ok, msg = write_json(run_id, "review", review)
    if not ok:
        return False, f"Failed to write review artifact: {msg}"

    return True, review
