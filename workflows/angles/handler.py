import json
import re
from datetime import datetime, timezone
from pathlib import Path

from core.tools.artifact_store import read_json, write_json
from core.tools.prompt_loader import load_prompt
from core.tools.schema_validator import validate

use_llm = True

_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPT_PATH = str(_ROOT / "prompts" / "workflows" / "angle-generation.md")
_ANGLE_SCHEMA_PATH = str(_ROOT / "schemas" / "entities" / "content-angle.json")


def _stub_angles(run_id: str, brief: dict, research: dict) -> dict:
    return {
        "angles": [
            {
                "angle_id": f"{run_id}_angle_1",
                "brief_id": brief["brief_id"],
                "research_pack_id": research["research_pack_id"],
                "title": "Basic angle",
                "approach": "educational",
                "core_message": brief["goal"],
                "target_emotion": "curiosity",
                "content_format": "text_post",
                "factual_dependencies": [],
                "risks": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "selected",
            }
        ]
    }


def _call_llm(prompt: str) -> dict:
    import anthropic  # ImportError → caught by caller

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text

    # strip optional markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)  # JSONDecodeError → caught by caller


_FORMAT_MAP = {
    "text": "text_post",
    "video": "short_video",
    "image": "image_post",
    "mixed": "mixed",
}


def _normalize(run_id: str, brief: dict, research: dict, raw_angles: list) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    content_format = _FORMAT_MAP.get(brief.get("format", ""), "text_post")
    angles = []
    for i, angle in enumerate(raw_angles, start=1):
        angles.append({
            "angle_id": f"{run_id}_angle_{i}",
            "brief_id": brief["brief_id"],
            "research_pack_id": research["research_pack_id"],
            "title": angle.get("title", ""),
            "approach": angle.get("approach", "educational"),
            "core_message": angle.get("core_message", brief["goal"]),
            "target_emotion": angle.get("target_emotion", "curiosity"),
            "content_format": content_format,
            "factual_dependencies": angle.get("factual_dependencies", []),
            "risks": angle.get("risks", []),
            "created_at": now,
            "status": "draft",
        })
    return {"angles": angles}


def handle_angles(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "brief")
    if not ok:
        return False, f"Failed to read brief artifact: {result}"
    brief = result

    ok, result = read_json(run_id, "research")
    if not ok:
        return False, f"Failed to read research artifact: {result}"
    research = result

    output = None

    if use_llm:
        ok, prompt = load_prompt(
            _PROMPT_PATH,
            variables={
                "brief": json.dumps(brief, ensure_ascii=False),
                "research_pack": json.dumps(research, ensure_ascii=False),
            },
        )
        if ok:
            try:
                llm_result = _call_llm(prompt)
                raw_angles = llm_result.get("angles", [])
                if isinstance(raw_angles, list) and raw_angles:
                    assembled = _normalize(run_id, brief, research, raw_angles)
                    all_valid = True
                    for angle in assembled["angles"]:
                        valid, errors = validate(angle, _ANGLE_SCHEMA_PATH)
                        if not valid:
                            print("VALIDATION ERROR:", errors)
                            all_valid = False
                            break
                    if all_valid:
                        output = assembled
            except (ImportError, Exception) as e:
                print("LLM ERROR:", e)
                output = None  # fall through to stub

    if output is None:
        output = _stub_angles(run_id, brief, research)

    ok, msg = write_json(run_id, "angles", output)
    if not ok:
        return False, f"Failed to write angles artifact: {msg}"

    return True, output
