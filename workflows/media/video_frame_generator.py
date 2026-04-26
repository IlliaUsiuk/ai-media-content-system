from core.tools.artifact_store import read_json, write_json


def generate_video_frames(run_id: str) -> tuple[bool, dict | str]:
    ok, prompts_result = read_json(run_id, "video-frame-prompts")
    if not ok:
        return False, f"Failed to read video-frame-prompts artifact: {prompts_result}"

    from integrations.image.openai import generate_image

    frames = []
    for item in prompts_result.get("prompts", []):
        scene_id = item.get("scene_id", "")
        prompt_text = item.get("prompt", "")
        try:
            result = generate_image(prompt_text)
            frames.append({
                "scene_id": scene_id,
                "url": result.get("url"),
                "prompt": prompt_text,
                "provider": result.get("provider"),
                "model": result.get("model"),
            })
        except Exception as e:
            print(f"VIDEO FRAME GENERATOR ERROR (scene {scene_id}): {e}")
            frames.append({
                "scene_id": scene_id,
                "url": None,
                "prompt": prompt_text,
                "provider": None,
                "model": None,
                "error": str(e),
            })

    successful = [f for f in frames if f.get("url")]
    if not successful:
        return False, (
            f"Video frame generator produced no usable frames — "
            f"{len(frames)} attempted, all failed"
        )

    output = {"frames": frames}
    ok, msg = write_json(run_id, "video-frames", output)
    if not ok:
        return False, f"Failed to write video-frames artifact: {msg}"

    return True, output
