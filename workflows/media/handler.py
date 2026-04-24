import json
import re
from pathlib import Path

from core.tools.artifact_store import read_json, write_json
from core.tools.prompt_loader import load_prompt

use_llm = True

_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPT_PATH = str(_ROOT / "prompts" / "workflows" / "media-planning.md")


def _call_llm(prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def handle_media(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "script")
    if not ok:
        return False, f"Failed to read script artifact: {result}"
    script = result

    output = {"items": []}

    if use_llm:
        ok, prompt = load_prompt(
            _PROMPT_PATH,
            variables={"script": json.dumps(script, ensure_ascii=False)},
        )
        if ok:
            try:
                llm_result = _call_llm(prompt)
                items = llm_result.get("items", [])
                if isinstance(items, list):
                    output = {"items": items}
            except (ImportError, Exception) as e:
                print("MEDIA LLM ERROR:", e)

    ok, msg = write_json(run_id, "media-plan", output)
    if not ok:
        return False, f"Failed to write media-plan artifact: {msg}"

    return True, output
