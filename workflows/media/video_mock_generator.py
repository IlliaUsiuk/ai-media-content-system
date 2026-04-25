from core.tools.artifact_store import read_json, write_json


def generate_mock_videos(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "video-prompts")
    if not ok:
        return False, f"Failed to read video-prompts artifact: {result}"

    videos = []
    try:
        for n, item in enumerate(result.get("prompts", []), start=1):
            videos.append({
                "scene_id": item.get("scene_id", f"scene_{n}"),
                "path": f"mock_videos/scene_{n}.mp4",
                "prompt": item.get("prompt", ""),
            })
    except Exception as e:
        print("VIDEO MOCK ERROR:", e)
        videos = []

    output = {"videos": videos}
    ok, msg = write_json(run_id, "videos", output)
    if not ok:
        return False, f"Failed to write videos artifact: {msg}"

    return True, output
