import re

from core.tools.artifact_store import read_json, write_json

# Character and environment locked across all scenes.
_CHARACTER = (
    "Young adult in their mid-20s, gender-neutral, wearing a plain dark t-shirt, "
    "sitting at a minimal wooden desk in a small home office"
)

# Per-scene arc: physical action + hand position + emotional beat.
# Indexed by scene position (0-based). Last entry repeats for longer scripts.
_FRAME_ARC = [
    {
        "beat": "tense and uncertain",
        "action": "holding a phone face-down, looking down at the desk",
        "hands": "one hand resting on the desk, the other loosely holding the phone at waist level",
    },
    {
        "beat": "concerned, leaning in",
        "action": "leaning slightly forward, reaching toward a pen on the desk",
        "hands": "both hands near the desk surface, fingers extended toward the pen",
    },
    {
        "beat": "focused and analytical",
        "action": "resting one hand flat on a sheet of paper, looking down at it",
        "hands": "one hand flat on paper, other hand resting on the table edge",
    },
    {
        "beat": "determined and active",
        "action": "writing in an open notebook with a pen, posture upright",
        "hands": "one hand holding pen over notebook, other resting beside the notebook",
    },
    {
        "beat": "calm and resolving",
        "action": "sitting back in the chair, looking slightly upward",
        "hands": "both hands relaxed in lap, clearly visible",
    },
    {
        "beat": "grounded and clear",
        "action": "sitting upright, looking forward with a settled expression",
        "hands": "both hands resting flat on the desk surface",
    },
]

# Lighting keywords from media-plan that describe screen-only light sources.
# These are replaced with a safe practical-light fallback.
_SCREEN_LIGHTING_PHRASES = {
    "pure screen", "no physical lighting", "screen only",
    "screen-lit", "screen glow only", "no lighting",
}

_SAFE_LIGHTING = "warm desk lamp from the side, soft directional shadows, no screen glow"

# Safety constraints split into two parts:
# - _SAFETY_HARD goes right after hands (never truncated)
# - _SAFETY_STYLE goes at the end (style notes, OK if partially cut)
_SAFETY_HARD = (
    "No text, no screens, no numbers, no readable content, no UI, no charts in frame. "
    "No hands near face or hair."
)
_SAFETY_STYLE = (
    "Medium shot, eye level, shallow depth of field. "
    "Cinematic color grade, warm dark tones."
)


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"[.!?](?:\s|$)", text)
    if m:
        return text[: m.end()].strip()
    return text.strip()


def _safe_lighting(raw: str) -> str:
    lower = raw.lower()
    if any(phrase in lower for phrase in _SCREEN_LIGHTING_PHRASES):
        return _SAFE_LIGHTING
    return raw


def _cap_words(text: str, limit: int = 80) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "..."


def build_video_frame_prompts(run_id: str) -> tuple[bool, dict | str]:
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
        arc = _FRAME_ARC[min(idx, len(_FRAME_ARC) - 1)]

        plan = plan_by_scene.get(scene_id, {})
        lighting = _safe_lighting(
            _first_sentence(plan.get("lighting", _SAFE_LIGHTING))
        )
        mood = _first_sentence(plan.get("mood", arc["beat"]))

        prompt = _cap_words(
            f"{_CHARACTER}. "
            f"Expression: {arc['beat']}. "
            f"Action: {arc['action']}. "
            f"Hands: {arc['hands']}. "
            f"{_SAFETY_HARD} "
            f"Lighting: {lighting} "
            f"Mood: {mood} "
            f"{_SAFETY_STYLE}",
            limit=100,
        )

        prompts.append({"scene_id": scene_id, "prompt": prompt})

    if not prompts:
        return False, "No video frame prompts generated — script.json has no scenes"

    output = {"prompts": prompts}
    ok, msg = write_json(run_id, "video-frame-prompts", output)
    if not ok:
        return False, f"Failed to write video-frame-prompts artifact: {msg}"

    return True, output
