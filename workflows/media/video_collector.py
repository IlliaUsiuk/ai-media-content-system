from core.tools.artifact_store import read_json, write_json
from integrations.video.runway import check_video_status


def collect_videos(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "video-jobs")
    if not ok:
        return False, f"Failed to read video-jobs artifact: {result}"

    videos = []
    for job in result.get("jobs", []):
        status = check_video_status(job.get("job_id", ""))
        videos.append({
            "scene_id": job.get("scene_id", ""),
            "status": status.get("status"),
            "url": status.get("url"),
        })

    output = {"videos": videos}
    ok, msg = write_json(run_id, "videos", output)
    if not ok:
        return False, f"Failed to write videos artifact: {msg}"

    return True, output
