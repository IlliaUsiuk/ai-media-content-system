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


st.set_page_config(page_title="AI Media Content System", layout="wide")
st.title("AI Media Content System")
st.caption("Turn a text idea into a content package: script, images, and video assets.")

st.divider()

idea = st.text_input("Content idea", placeholder="e.g. Coffee trends for Gen Z")
run_btn = st.button("Generate content package", type="primary")

if run_btn:
    if not idea.strip():
        st.warning("Enter a content idea first.")
    else:
        with st.spinner("Running pipeline..."):
            try:
                from core.orchestrator.runner import run_pipeline
                ok, run_id = run_pipeline(idea.strip())
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        if ok:
            st.success(f"Done — **{run_id}**")
        else:
            st.error(f"Pipeline failed — {run_id}")

        st.divider()

        col1, col2 = st.columns(2)

        # --- run log ---
        with col1:
            st.subheader("Run log")
            log = _load_json(_LOGS / f"{run_id}.json")
            if log:
                st.json(log)
            else:
                st.warning("run log not found")

        # --- script ---
        with col2:
            st.subheader("Script")
            script = _load_json(_ARTIFACTS / run_id / "script.json")
            if script:
                for scene in script.get("scenes", []):
                    with st.expander(f"Scene {scene.get('order', '?')}"):
                        st.write("**Voiceover:**", scene.get("voiceover", ""))
                        st.write("**Action:**", scene.get("action_description", ""))
                        st.write("**Duration:**", scene.get("duration_sec", ""), "sec")
            else:
                st.warning("script.json not found")

        st.divider()

        # --- images ---
        st.subheader("Images")
        images_data = _load_json(_ARTIFACTS / run_id / "images.json")
        if images_data:
            cols = st.columns(min(len(images_data["images"]), 4))
            for i, img in enumerate(images_data["images"]):
                with cols[i % len(cols)]:
                    url = img.get("url")
                    if url:
                        p = Path(url)
                        if p.exists():
                            st.image(str(p), caption=img.get("scene_id", ""), use_container_width=True)
                        else:
                            st.image(url, caption=img.get("scene_id", ""), use_container_width=True)
                    else:
                        st.warning(f"{img.get('scene_id')} — no image")
                    st.caption(f"model: {img.get('model', 'unknown')}")
        else:
            st.warning("images.json not found")

        st.divider()

        # --- video assets ---
        st.subheader("Video assets")
        video_assets = _load_json(_ARTIFACTS / run_id / "video-assets.json")
        if video_assets:
            for v in video_assets.get("videos", []):
                with st.expander(v.get("scene_id", "scene")):
                    st.write("**Status:**", v.get("status", ""))
                    st.write("**Prompt:**", v.get("prompt", ""))
                    st.write("**Image:**", v.get("image", ""))
        else:
            st.warning("video-assets.json not found")
