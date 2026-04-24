import re
from pathlib import Path


def load_prompt(prompt_path: str, variables: dict | None = None) -> tuple[bool, str]:
    if variables is None:
        variables = {}

    try:
        content = Path(prompt_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, f"Prompt file not found: {prompt_path}"
    except OSError as e:
        return False, f"Cannot read prompt file: {e}"

    placeholders = re.findall(r"\{\{(\w+)\}\}", content)

    missing = sorted(set(p for p in placeholders if p not in variables))
    if missing:
        return False, f"Missing template variables: {', '.join(missing)}"

    rendered = re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables[m.group(1)]), content)
    return True, rendered
