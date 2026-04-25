from core.tools.artifact_store import read_json, write_json


def generate_videos(run_id: str) -> tuple[bool, dict | str]:
    ok, images_result = read_json(run_id, "images")
    if not ok:
        return False, f"Failed to read images artifact: {images_result}"

    ok, prompts_result = read_json(run_id, "video-prompts")
    if not ok:
        return False, f"Failed to read video-prompts artifact: {prompts_result}"

    images_by_scene = {img["scene_id"]: img for img in images_result.get("images", [])}

    videos = []
    try:
        for item in prompts_result.get("prompts", []):
            scene_id = item.get("scene_id", "")
            image = images_by_scene.get(scene_id, {}).get("url")
            videos.append({
                "scene_id": scene_id,
                "image": image,
                "prompt": item.get("prompt", ""),
                "status": "ready_for_animation",
            })
    except Exception as e:
        print("VIDEO GENERATOR ERROR:", e)
        videos = []

    output = {"videos": videos}
    ok, msg = write_json(run_id, "video-assets", output)
    if not ok:
        return False, f"Failed to write video-assets artifact: {msg}"

    return True, output
