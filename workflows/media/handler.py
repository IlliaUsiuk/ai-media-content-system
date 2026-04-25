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

    media_plan = {"items": []}

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
                    media_plan = {"items": items}
            except (ImportError, Exception) as e:
                print("MEDIA LLM ERROR:", e)

    ok, msg = write_json(run_id, "media-plan", media_plan)
    if not ok:
        return False, f"Failed to write media-plan artifact: {msg}"

    # build image prompts and generate images
    from workflows.media.prompt_builder import build_image_prompts
    from integrations.image.openai import generate_image

    ok, prompts_result = build_image_prompts(run_id)
    if not ok:
        return False, f"Failed to build image prompts: {prompts_result}"

    images = []
    for item in prompts_result.get("prompts", []):
        scene_id = item.get("scene_id", "")
        prompt_text = item.get("prompt", "")
        result = generate_image(prompt_text)
        images.append({
            "scene_id": scene_id,
            "url": result.get("url"),
            "prompt": prompt_text,
            "provider": result.get("provider"),
            "model": result.get("model"),
        })

    ok, msg = write_json(run_id, "images", {"images": images})
    if not ok:
        return False, f"Failed to write images artifact: {msg}"

    return True, media_plan
