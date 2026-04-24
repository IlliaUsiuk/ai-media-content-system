import json
from datetime import datetime, timezone
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent / "runs" / "logs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_path(run_id: str) -> Path:
    return _BASE / f"{run_id}.json"


def _read(run_id: str) -> tuple[bool, dict | str]:
    path = _log_path(run_id)
    if not path.exists():
        return False, f"Log not found for run_id={run_id!r}: {path}"
    try:
        with open(path, encoding="utf-8") as f:
            return True, json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Log file contains invalid JSON: {e}"
    except OSError as e:
        return False, f"Cannot read log: {e}"


def _write(run_id: str, data: dict) -> tuple[bool, str]:
    path = _log_path(run_id)
    try:
        _BASE.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True, str(path)
    except (TypeError, ValueError) as e:
        return False, f"Cannot serialize log to JSON: {e}"
    except OSError as e:
        return False, f"Cannot write log: {e}"


def init_log(run_id: str, brief_id: str | None = None) -> tuple[bool, str]:
    log = {
        "run_id": run_id,
        "brief_id": brief_id,
        "status": "queued",
        "stages": [],
        "started_at": _now(),
        "finished_at": None,
        "total_cost": None,
        "errors": [],
        "summary": None,
    }
    return _write(run_id, log)


def update_stage(
    run_id: str,
    stage_name: str,
    status: str,
    input_ref: str | None = None,
    output_ref: str | None = None,
    cost_tokens: int | None = None,
) -> tuple[bool, str]:
    ok, result = _read(run_id)
    if not ok:
        return False, result

    log = result
    now = _now()

    stage = next((s for s in log["stages"] if s["stage_name"] == stage_name), None)
    if stage is None:
        log["stages"] = [s for s in log["stages"] if s["stage_name"] != stage_name]
        stage = {
            "stage_name": stage_name,
            "status": status,
            "started_at": now if status == "running" else None,
            "finished_at": None,
            "input_ref": input_ref,
            "output_ref": output_ref,
            "cost_tokens": cost_tokens,
        }
        log["stages"].append(stage)
    else:
        stage["status"] = status
        if status == "running" and stage["started_at"] is None:
            stage["started_at"] = now
        if input_ref is not None:
            stage["input_ref"] = input_ref
        if output_ref is not None:
            stage["output_ref"] = output_ref
        if cost_tokens is not None:
            stage["cost_tokens"] = cost_tokens

    if status in ("completed", "failed"):
        stage["finished_at"] = now

    if status == "running" and log["status"] == "queued":
        log["status"] = "running"

    return _write(run_id, log)


def add_error(run_id: str, stage_name: str, message: str) -> tuple[bool, str]:
    ok, result = _read(run_id)
    if not ok:
        return False, result

    log = result
    log["errors"].append({
        "stage_name": stage_name,
        "message": message,
        "timestamp": _now(),
    })

    return _write(run_id, log)


def finish_log(
    run_id: str,
    status: str,
    summary: str | None = None,
    total_cost: float | None = None,
) -> tuple[bool, str]:
    ok, result = _read(run_id)
    if not ok:
        return False, result

    log = result
    log["status"] = status
    log["finished_at"] = _now()
    if summary is not None:
        log["summary"] = summary
    if total_cost is not None:
        log["total_cost"] = total_cost

    return _write(run_id, log)
