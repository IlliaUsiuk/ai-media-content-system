from core.tools.artifact_store import read_json, write_json

_VERDICT_TO_STATUS = {
    "approved": "ready",
    "needs_revision": "needs_revision",
    "rejected": "rejected",
}


def handle_output(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "brief")
    if not ok:
        return False, f"Failed to read brief artifact: {result}"

    ok, result = read_json(run_id, "script")
    if not ok:
        return False, f"Failed to read script artifact: {result}"

    ok, result = read_json(run_id, "review")
    if not ok:
        return False, f"Failed to read review artifact: {result}"
    review = result

    status = _VERDICT_TO_STATUS.get(review["verdict"], "needs_revision")

    output = {
        "run_id": run_id,
        "status": status,
        "summary": review["summary"],
        "artifacts": [
            {"name": "brief", "path": "brief.json", "type": "json"},
            {"name": "script", "path": "script.json", "type": "json"},
            {"name": "review", "path": "review.json", "type": "json"},
        ],
        "next_actions": [],
    }

    ok, msg = write_json(run_id, "output", output)
    if not ok:
        return False, f"Failed to write output artifact: {msg}"

    return True, output
