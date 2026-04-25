import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_ARTIFACTS = Path(__file__).resolve().parent.parent.parent / "runs" / "artifacts"
_LOGS = Path(__file__).resolve().parent.parent.parent / "runs" / "logs"


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _download_btn(path: Path, label: str):
    if path.exists():
        st.download_button(
            label=label,
            data=path.read_bytes(),
            file_name=path.name,
            mime="application/json",
        )


def _show_image(url: str, caption: str = ""):
    if not url:
        st.warning(f"{caption} — no image")
        return
    p = Path(url)
    if p.exists():
        st.image(str(p), caption=caption, use_container_width=True)
    elif url.startswith("http"):
        st.image(url, caption=caption, use_container_width=True)
    else:
        st.warning(f"{caption} — image not found: {url}")


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Media Content System", layout="wide")
st.title("AI Media Content System")
st.caption("Turn a text idea into a content package: script, images, and video assets.")

st.divider()

# ── Input ─────────────────────────────────────────────────────────────────────

idea = st.text_area(
    "Content idea",
    placeholder="e.g. Coffee trends for Gen Z",
    height=80,
)
run_btn = st.button("Generate content package", type="primary")

if not run_btn:
    st.stop()

if not idea.strip():
    st.warning("Enter a content idea first.")
    st.stop()

# ── Run pipeline ──────────────────────────────────────────────────────────────

with st.spinner("Running pipeline..."):
    try:
        from core.orchestrator.runner import run_pipeline
        ok, run_id = run_pipeline(idea.strip())
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        st.stop()

if ok:
    st.success(f"Pipeline complete — `{run_id}`")
else:
    st.error(f"Pipeline failed — {run_id}")
    st.stop()

run_dir = _ARTIFACTS / run_id

st.divider()

# ── Script ────────────────────────────────────────────────────────────────────

st.subheader("Script")
script_path = run_dir / "script.json"
script = _load_json(script_path)
if script:
    scenes = script.get("scenes", [])
    for scene in scenes:
        with st.expander(f"Scene {scene.get('order', '?')} — {scene.get('duration_sec', '?')}s"):
            st.markdown(f"**Voiceover:** {scene.get('voiceover', '')}")
            st.markdown(f"**Action:** {scene.get('action_description', '')}")
    _download_btn(script_path, "Download script.json")
else:
    st.warning("script.json not found")

st.divider()

# ── Images ────────────────────────────────────────────────────────────────────

st.subheader("Generated images")
images_path = run_dir / "images.json"
images_data = _load_json(images_path)
if images_data:
    images = images_data.get("images", [])
    n = min(len(images), 4)
    cols = st.columns(n) if n > 0 else []
    for i, img in enumerate(images):
        with cols[i % n]:
            _show_image(img.get("url", ""), caption=f"scene {i + 1}")
            st.caption(f"model: {img.get('model', 'unknown')} · provider: {img.get('provider', '?')}")
            with st.expander("Prompt"):
                st.write(img.get("prompt", ""))
    _download_btn(images_path, "Download images.json")
else:
    st.warning("images.json not found")

st.divider()

# ── Video prompts ─────────────────────────────────────────────────────────────

st.subheader("Video prompts")
vp_path = run_dir / "video-prompts.json"
vp_data = _load_json(vp_path)
if vp_data:
    for item in vp_data.get("prompts", []):
        with st.expander(item.get("scene_id", "scene")):
            st.write(item.get("prompt", ""))
else:
    st.warning("video-prompts.json not found")

st.divider()

# ── Video assets ──────────────────────────────────────────────────────────────

st.subheader("Video assets")
va_path = run_dir / "video-assets.json"
va_data = _load_json(va_path)
if va_data:
    for v in va_data.get("videos", []):
        with st.expander(v.get("scene_id", "scene")):
            st.markdown(f"**Status:** `{v.get('status', '')}`")
            st.markdown(f"**Prompt:** {v.get('prompt', '')}")
            image_url = v.get("image", "")
            if image_url:
                _show_image(image_url, caption="reference image")
    _download_btn(va_path, "Download video-assets.json")
else:
    st.warning("video-assets.json not found")

st.divider()

# ── Videos ────────────────────────────────────────────────────────────────────

st.subheader("Videos")
videos_path = run_dir / "videos.json"
videos_data = _load_json(videos_path)
if videos_data:
    for v in videos_data.get("videos", []):
        scene_id = v.get("scene_id", "scene")
        status = v.get("status", "")
        url = v.get("url", "")
        with st.expander(f"{scene_id} — {status}"):
            if url:
                p = Path(url)
                if p.exists() and url.endswith(".mp4"):
                    st.video(str(p))
                elif url.startswith("http"):
                    st.markdown(f"[Watch video]({url})")
                else:
                    st.write("url:", url)
            else:
                st.warning("No video URL")
else:
    st.warning("videos.json not found")

st.divider()

# ── Run log ───────────────────────────────────────────────────────────────────

log_path = _LOGS / f"{run_id}.json"
log = _load_json(log_path)
with st.expander("Run log"):
    if log:
        st.json(log)
        _download_btn(log_path, "Download run-log.json")
    else:
        st.warning("run log not found")
