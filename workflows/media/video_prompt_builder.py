import re

from core.tools.artifact_store import read_json, write_json

# Emotional arc indexed by scene position (0-based).
# Scenes beyond the last entry use the final entry.
_ARC = [
    {
        "state": "confused and tense",
        "action": "stares downward at their desk, slowly sets a phone down with a heavy exhale",
        "camera": "slow push-in, shallow depth of field",
    },
    {
        "state": "unsettled and concerned",
        "action": "leans forward over the desk, reaches for a pen, then pauses mid-motion with a furrowed brow",
        "camera": "handheld slight motion, rack focus to hands",
    },
    {
        "state": "focused and analytical",
        "action": "traces a finger slowly across papers on the desk, eyes scanning methodically",
        "camera": "rack focus from background to face, slow push-in",
    },
    {
        "state": "determined and decisive",
        "action": "writes deliberately in a notebook with a set jaw, posture upright and forward",
        "camera": "medium shot, slow push-in, subtle handheld shake",
    },
    {
        "state": "calm and clear-headed",
        "action": "sits back in the chair, exhales slowly, looks up from the desk with quiet resolve",
        "camera": "static hold, gentle pull-back, shallow depth of field",
    },
    {
        "state": "grounded and authoritative",
        "action": "holds steady eye contact forward, hands resting calmly on the desk",
        "camera": "static hold, face centered, shallow depth of field",
    },
]

# Visual descriptions containing these keywords describe UI, data, or text.
# They are replaced with character-behavior framing that Runway handles well.
_UI_KEYWORDS = {
    "screen", "dashboard", "numbers", "chart", "graph", "text appearing",
    "interface", "app", "browser", "spreadsheet", "invoice", "split screen",
    "animated text", "numbered points", "points appearing", "phone screen",
    "display", "revenue", "balance", "bills", "data", "stats", "metrics",
}


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"[.!?](?:\s|$)", text)
    if m:
        return text[: m.end()].strip()
    return text.strip()


def _contains_ui(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _UI_KEYWORDS)


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

    scenes = script.get("scenes", [])
    prompts = []

    for idx, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", "")
        visual = scene.get("visual_description", "")

        arc = _ARC[min(idx, len(_ARC) - 1)]
        state = arc["state"]
        action = arc["action"]
        camera_motion = arc["camera"]

        plan = plan_by_scene.get(scene_id, {})
        lighting = _first_sentence(plan.get("lighting", "Warm practical desk lamp, soft directional shadows."))
        mood = _first_sentence(plan.get("mood", "Focused and tense."))

        # Only use visual_description if it describes character/environment, not UI.
        # UI-heavy descriptions are dropped — the arc action carries the scene instead.
        visual_line = ""
        if visual and not _contains_ui(visual):
            visual_line = _first_sentence(visual) + "\n"

        continuity = "This continues from the previous scene.\n" if idx > 0 else ""

        prompt = _cap_words(
            f"{visual_line}"
            f"The character is now {state}.\n"
            f"They {action}.\n"
            f"{continuity}"
            f"Camera: {camera_motion}.\n"
            f"Lighting: {lighting}\n"
            f"Mood: {mood}\n"
            f"Important: do not show readable text, UI, or numbers. "
            f"Focus on human behavior and motion."
        )

        prompts.append({"scene_id": scene_id, "prompt": prompt})

    if not prompts:
        return False, "No video prompts generated — script.json has no scenes"

    output = {"prompts": prompts}
    ok, msg = write_json(run_id, "video-prompts", output)
    if not ok:
        return False, f"Failed to write video-prompts artifact: {msg}"

    return True, output
