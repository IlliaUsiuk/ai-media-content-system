import json
from pathlib import Path


def validate(data: dict, schema_path: str) -> tuple[bool, list[str]]:
    try:
        from jsonschema import Draft7Validator, RefResolver
    except ImportError:
        return False, ["jsonschema is not installed. Run: pip install jsonschema"]

    try:
        resolved = Path(schema_path).resolve()
        with open(resolved, encoding="utf-8") as f:
            schema = json.load(f)
    except FileNotFoundError:
        return False, [f"Schema file not found: {schema_path}"]
    except json.JSONDecodeError as e:
        return False, [f"Schema file contains invalid JSON: {e}"]
    except OSError as e:
        return False, [f"Cannot read schema file: {e}"]

    try:
        resolver = RefResolver(base_uri=resolved.as_uri(), referrer=schema)
        validator = Draft7Validator(schema, resolver=resolver)
        errors = list(validator.iter_errors(data))
    except Exception as e:
        return False, [f"Validator setup failed: {e}"]

    if not errors:
        return True, []

    messages = []
    for error in errors:
        path = " -> ".join(str(p) for p in error.absolute_path) or "root"
        messages.append(f"{path}: {error.message}")

    return False, messages
