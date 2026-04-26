import re

from core.tools.artifact_store import read_json, write_json


def _first_sentence(text: str) -> str:
    """Return the first sentence of text, or the full text if no sentence break found."""
    if not text:
        return ""
    m = re.search(r"[.!?](?:\s|$)", text)
    if m:
        return text[: m.end()].strip()
    return text.strip()


def _cap_words(text: str, limit: int = 120) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "..."


def build_video_prompts(run_id: str) -> tuple[bool, dict | str]:
    ok, script = read_json(run_id, "script")
    if not ok:
        return False, f"Failed to read script artifact: {script}"

    ok, media_plan = read_json(run_id, "media-plan")
    if not ok:
        return False, f"Failed to read media-plan artifact: {media_plan}"

    plan_by_scene = {
        item["scene_id"]: item
        for item in media_plan.get("items", [])
        if "scene_id" in item
    }

    prompts = []
    for scene in script.get("scenes", []):
        scene_id = scene.get("scene_id", "")
        visual = _first_sentence(scene.get("visual_description", ""))
        voiceover = _first_sentence(scene.get("voiceover", ""))

        plan = plan_by_scene.get(scene_id, {})
        camera = _first_sentence(plan.get("camera", ""))
        lighting = _first_sentence(plan.get("lighting", ""))
        mood = _first_sentence(plan.get("mood", ""))

        parts = []
        if visual:
            parts.append(visual)
        if camera:
            parts.append(f"Camera: {camera}")
        if lighting:
            parts.append(f"Lighting: {lighting}")
        if mood:
            parts.append(f"Mood: {mood}")
        parts.append("Motion: subtle cinematic movement.")
        if voiceover:
            parts.append(f'Match voiceover: "{voiceover}"')

        prompts.append({
            "scene_id": scene_id,
            "prompt": _cap_words(" ".join(parts)),
        })

    if not prompts:
        return False, "No video prompts generated — script.json has no scenes"

    output = {"prompts": prompts}
    ok, msg = write_json(run_id, "video-prompts", output)
    if not ok:
        return False, f"Failed to write video-prompts artifact: {msg}"

    return True, output
