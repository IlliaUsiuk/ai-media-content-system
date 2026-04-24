import json
import re
from datetime import datetime, timezone
from pathlib import Path

from core.tools.artifact_store import read_json, write_json
from core.tools.prompt_loader import load_prompt
from core.tools.schema_validator import validate

use_llm = True

_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPT_PATH = str(_ROOT / "prompts" / "workflows" / "script-generation.md")
_SCRIPT_SCHEMA_PATH = str(_ROOT / "schemas" / "entities" / "script.json")

_FORMAT_MAP = {
    "text": "text_post",
    "video": "short_video",
    "image": "image_post",
    "mixed": "mixed",
}


def _stub_script(run_id: str, brief: dict, angle: dict) -> dict:
    return {
        "script_id": f"{run_id}_script",
        "brief_id": brief["brief_id"],
        "research_pack_id": run_id,
        "angle_id": angle["angle_id"],
        "title": angle["title"],
        "format": _FORMAT_MAP.get(brief.get("format", ""), "text_post"),
        "language": brief["language"],
        "scenes": [
            {
                "scene_id": f"{run_id}_scene_1",
                "order": 1,
                "duration_sec": None,
                "visual_description": "Basic visual direction for the content.",
                "voiceover": None,
                "on_screen_text": None,
                "notes": "Stub script generated without LLM.",
            }
        ],
        "cta": None,
        "total_duration_sec": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
    }


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


def _normalize(run_id: str, brief: dict, angle: dict, llm_result: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    raw_scenes = llm_result.get("scenes", [])
    scenes = []
    for i, scene in enumerate(raw_scenes, start=1):
        scenes.append({
            "scene_id": f"{run_id}_scene_{i}",
            "order": i,
            "duration_sec": scene.get("duration_sec"),
            "visual_description": scene.get("visual_description", ""),
            "voiceover": scene.get("voiceover"),
            "on_screen_text": scene.get("on_screen_text"),
            "notes": scene.get("notes"),
        })
    return {
        "script_id": f"{run_id}_script",
        "brief_id": brief["brief_id"],
        "research_pack_id": run_id,
        "angle_id": angle["angle_id"],
        "title": llm_result.get("title", angle["title"]),
        "format": _FORMAT_MAP.get(brief.get("format", ""), "text_post"),
        "language": brief["language"],
        "scenes": scenes,
        "cta": llm_result.get("cta"),
        "total_duration_sec": llm_result.get("total_duration_sec"),
        "created_at": now,
        "status": "complete",
    }


def handle_script(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "brief")
    if not ok:
        return False, f"Failed to read brief artifact: {result}"
    brief = result

    ok, result = read_json(run_id, "research")
    if not ok:
        return False, f"Failed to read research artifact: {result}"
    research = result

    ok, result = read_json(run_id, "angles")
    if not ok:
        return False, f"Failed to read angles artifact: {result}"
    angle = result["angles"][0]

    script = None

    if use_llm:
        ok, prompt = load_prompt(
            _PROMPT_PATH,
            variables={
                "brief": json.dumps(brief, ensure_ascii=False),
                "research_pack": json.dumps(research, ensure_ascii=False),
                "selected_angle": json.dumps(angle, ensure_ascii=False),
            },
        )
        if ok:
            try:
                llm_result = _call_llm(prompt)
                assembled = _normalize(run_id, brief, angle, llm_result)
                valid, errors = validate(assembled, _SCRIPT_SCHEMA_PATH)
                if valid:
                    script = assembled
                else:
                    print("SCRIPT LLM ERROR:", errors)
            except (ImportError, Exception) as e:
                print("SCRIPT LLM ERROR:", e)
                script = None

    if script is None:
        script = _stub_script(run_id, brief, angle)

    ok, msg = write_json(run_id, "script", script)
    if not ok:
        return False, f"Failed to write script artifact: {msg}"

    return True, script
