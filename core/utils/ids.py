from datetime import datetime, timezone
import uuid


def generate_run_id() -> str:
    now = datetime.now(timezone.utc)
    timestamp = f"{now.strftime('%Y%m%d_%H%M%S')}_{now.strftime('%f')[:3]}"
    short_uuid = str(uuid.uuid4()).replace("-", "")[:8]
    return f"run_{timestamp}_{short_uuid}"


if __name__ == "__main__":
    for _ in range(5):
        print(generate_run_id())
