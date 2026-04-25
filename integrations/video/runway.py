import base64
import os
import uuid
from pathlib import Path

_MOCK_JOBS: dict[str, dict] = {}


def _encode_image(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/png;base64,{b64}"


def _mock_job(image_path: str, prompt: str, status: str = "queued") -> dict:
    job_id = uuid.uuid4().hex
    _MOCK_JOBS[job_id] = {"status": "mock"}
    return {
        "job_id": job_id,
        "status": status,
        "provider": "runway",
        "image_path": image_path,
        "prompt": prompt,
    }


def create_video_job(image_path: str, prompt: str) -> dict:
    api_key = os.environ.get("RUNWAY_API_KEY")
    if not api_key:
        print("RUNWAY API ERROR: missing RUNWAY_API_KEY")
        return _mock_job(image_path, prompt)

    try:
        import runwayml

        client = runwayml.RunwayML(api_key=api_key)
        image_data = _encode_image(image_path)
        task = client.image_to_video.create(
            model="gen3a_turbo",
            prompt_image=image_data,
            prompt_text=prompt,
            ratio="720:1280",
            duration=5,
        )
        return {
            "job_id": task.id,
            "status": "queued",
            "provider": "runway",
            "image_path": image_path,
            "prompt": prompt,
        }
    except Exception as e:
        print("RUNWAY API ERROR:", e)
        return _mock_job(image_path, prompt, status="failed")


def check_video_status(job_id: str) -> dict:
    if job_id in _MOCK_JOBS:
        return {
            "job_id": job_id,
            "status": "completed",
            "url": f"mock_videos/{job_id}.mp4",
            "provider": "runway",
        }

    api_key = os.environ.get("RUNWAY_API_KEY")
    if not api_key:
        print("RUNWAY API ERROR: missing RUNWAY_API_KEY")
        return {"job_id": job_id, "status": "failed", "url": None, "provider": "runway"}

    try:
        import runwayml

        client = runwayml.RunwayML(api_key=api_key)
        task = client.tasks.retrieve(job_id)

        status_map = {
            "PENDING": "queued",
            "RUNNING": "processing",
            "SUCCEEDED": "completed",
            "FAILED": "failed",
            "CANCELLED": "failed",
            "THROTTLED": "queued",
        }
        status = status_map.get(task.status, "processing")
        url = task.output[0] if getattr(task, "output", None) and status == "completed" else None

        return {"job_id": job_id, "status": status, "url": url, "provider": "runway"}
    except Exception as e:
        print("RUNWAY API ERROR:", e)
        return {"job_id": job_id, "status": "failed", "url": None, "provider": "runway"}
