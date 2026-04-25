from core.tools.artifact_store import read_json, write_json
from integrations.video.runway import create_video_job


def run_video_jobs(run_id: str) -> tuple[bool, dict | str]:
    ok, result = read_json(run_id, "video-assets")
    if not ok:
        return False, f"Failed to read video-assets artifact: {result}"

    jobs = []
    for asset in result.get("videos", []):
        scene_id = asset.get("scene_id", "")
        job = create_video_job(
            image_path=asset.get("image", ""),
            prompt=asset.get("prompt", ""),
        )
        jobs.append({
            "scene_id": scene_id,
            "job_id": job.get("job_id"),
            "status": job.get("status"),
        })

    output = {"jobs": jobs}
    ok, msg = write_json(run_id, "video-jobs", output)
    if not ok:
        return False, f"Failed to write video-jobs artifact: {msg}"

    return True, output
