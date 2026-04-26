import json
import re
from pathlib import Path

from core.tools.artifact_store import read_json, write_json
from core.tools.prompt_loader import load_prompt

use_llm = True

_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPT_PATH = str(_ROOT / "prompts" / "media" / "image-prompt-builder.md")


def _call_llm(prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def build_image_prompts(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "media-plan")
    if not ok:
        return False, f"Failed to read media-plan artifact: {result}"
    media_plan = result

    output = {"prompts": []}

    if use_llm:
        ok, prompt = load_prompt(
            _PROMPT_PATH,
            variables={"media_plan": json.dumps(media_plan, ensure_ascii=False)},
        )
        if not ok:
            return False, f"Failed to load image prompt template: {prompt}"

        try:
            llm_result = _call_llm(prompt)
        except Exception as e:
            print("PROMPT BUILDER ERROR:", e)
            return False, f"Image prompt builder LLM call failed: {e}"

        prompts = llm_result.get("prompts", [])
        if not isinstance(prompts, list) or len(prompts) == 0:
            return False, "Image prompt builder returned empty prompts"

        output = {"prompts": prompts}

    ok, msg = write_json(run_id, "image-prompts", output)
    if not ok:
        return False, f"Failed to write image-prompts artifact: {msg}"

    return True, output
