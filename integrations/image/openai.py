import base64
import time
import uuid
from pathlib import Path

_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "runs" / "artifacts" / "tmp_images"


def _call_model(client, model: str, prompt: str) -> dict:
    response = client.images.generate(model=model, prompt=prompt, n=1)
    item = response.data[0]
    if getattr(item, "url", None):
        return {"url": item.url}
    if getattr(item, "b64_json", None):
        _IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = _IMAGES_DIR / f"image_{uuid.uuid4().hex[:8]}.png"
        file_path.write_bytes(base64.b64decode(item.b64_json))
        return {"url": str(file_path)}
    return {"url": None}


def generate_image(prompt: str) -> dict:
    from openai import OpenAI

    client = OpenAI()

    for attempt in range(1, 4):
        try:
            result = _call_model(client, "gpt-image-2", prompt)
            return {"provider": "openai", "model": "gpt-image-2", "prompt": prompt, **result}
        except Exception as e:
            if getattr(e, "status_code", None) != 403:
                print("IMAGE API ERROR (gpt-image-2):", e)
                break
            print("RETRY gpt-image-2:", attempt)
            if attempt < 3:
                time.sleep(5)

    print("FALLBACK to dall-e-3")
    try:
        result = _call_model(client, "dall-e-3", prompt)
        return {"provider": "openai", "model": "dall-e-3", "prompt": prompt, **result}
    except Exception as e:
        print("IMAGE API ERROR (dall-e-3):", e)

    return {"provider": "openai", "model": None, "prompt": prompt, "url": None}
