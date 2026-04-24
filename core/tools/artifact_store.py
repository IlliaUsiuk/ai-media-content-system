import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent / "runs" / "artifacts"


def _check_component(value: str, field: str) -> str | None:
    if not value:
        return f"{field} must not be empty"
    if "/" in value or "\\" in value or ".." in value:
        return f"{field} contains invalid characters: {value!r}"
    return None


def write_json(run_id: str, name: str, data: dict) -> tuple[bool, str]:
    err = _check_component(run_id, "run_id") or _check_component(name, "name")
    if err:
        return False, err

    artifact_dir = _BASE / run_id
    artifact_path = artifact_dir / f"{name}.json"

    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True, str(artifact_path)
    except (TypeError, ValueError) as e:
        return False, f"Cannot serialize {name!r} to JSON: {e}"
    except OSError as e:
        return False, f"Cannot write artifact {name!r}: {e}"


def read_json(run_id: str, name: str) -> tuple[bool, dict | str]:
    err = _check_component(run_id, "run_id") or _check_component(name, "name")
    if err:
        return False, err

    artifact_path = _BASE / run_id / f"{name}.json"

    try:
        with open(artifact_path, encoding="utf-8") as f:
            return True, json.load(f)
    except FileNotFoundError:
        return False, f"Artifact not found: {artifact_path}"
    except json.JSONDecodeError as e:
        return False, f"Artifact {name!r} contains invalid JSON: {e}"
    except OSError as e:
        return False, f"Cannot read artifact {name!r}: {e}"
