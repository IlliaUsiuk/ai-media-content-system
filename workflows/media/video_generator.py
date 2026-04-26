from core.tools.artifact_store import read_json, write_json


def generate_videos(run_id: str) -> tuple[bool, dict | str]:
    ok, frames_result = read_json(run_id, "video-frames")
    if not ok:
        return False, f"Failed to read video-frames artifact: {frames_result}"

    ok, prompts_result = read_json(run_id, "video-prompts")
    if not ok:
        return False, f"Failed to read video-prompts artifact: {prompts_result}"

    frames_by_scene = {f["scene_id"]: f for f in frames_result.get("frames", [])}

    videos = []
    for item in prompts_result.get("prompts", []):
        try:
            scene_id = item.get("scene_id", "")
            frame = frames_by_scene.get(scene_id, {})
            url = frame.get("url")
            if not url:
                print(f"VIDEO GENERATOR: skipping scene {scene_id} — frame url is null")
                continue
            videos.append({
                "scene_id": scene_id,
                "image": url,
                "prompt": item.get("prompt", ""),
                "status": "ready_for_animation",
            })
        except Exception as e:
            print(f"VIDEO GENERATOR ERROR (scene {item.get('scene_id', '?')}): {e}")

    if not videos:
        return False, "Video generator produced no video assets — check that video-frames.json and video-prompts.json are non-empty"

    output = {"videos": videos}
    ok, msg = write_json(run_id, "video-assets", output)
    if not ok:
        return False, f"Failed to write video-assets artifact: {msg}"

    return True, output
