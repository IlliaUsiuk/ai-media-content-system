import io
import json
import sys
import zipfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_ARTIFACTS = Path(__file__).resolve().parent.parent.parent / "runs" / "artifacts"
_LOGS = Path(__file__).resolve().parent.parent.parent / "runs" / "logs"
_EXAMPLE = "Coffee trends for Gen Z"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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
        st.caption(f"{caption} — no image")
        return
    p = Path(url)
    if p.exists():
        st.image(str(p), caption=caption, use_container_width=True)
    elif url.startswith("http"):
        st.image(url, caption=caption, use_container_width=True)
    else:
        st.caption(f"{caption} — not found")


def _regenerate_image(run_id: str, scene_idx: int, prompt: str):
    from integrations.image.openai import generate_image
    images_path = _ARTIFACTS / run_id / "images.json"
    data = _load_json(images_path) or {"images": []}
    result = generate_image(prompt)
    if scene_idx < len(data["images"]):
        data["images"][scene_idx]["url"] = result.get("url")
        data["images"][scene_idx]["model"] = result.get("model")
        data["images"][scene_idx]["provider"] = result.get("provider")
    _save_json(images_path, data)


def _generate_videos(run_id: str) -> bool:
    from workflows.media.video_prompt_builder import build_video_prompts
    from workflows.media.video_generator import generate_videos
    from workflows.media.video_runner import run_video_jobs
    from workflows.media.video_collector import collect_videos

    steps = [
        (build_video_prompts, "video-prompts.json",  "Building video prompts"),
        (generate_videos,     "video-assets.json",   "Linking images to prompts"),
        (run_video_jobs,      "video-jobs.json",     "Creating video jobs"),
        (collect_videos,      "videos.json",         "Collecting results"),
    ]

    with st.status("Generating videos...", expanded=True) as status:
        for fn, artifact, label in steps:
            st.write(f"{label}...")
            ok, result = fn(run_id)
            if not ok:
                status.update(label=f"Failed at {artifact}", state="error", expanded=True)
                st.error(str(result))
                return False
            # After video prompts: check result is non-empty
            if artifact == "video-prompts.json":
                prompts = result.get("prompts", []) if isinstance(result, dict) else []
                if not prompts:
                    status.update(label="Failed — video prompts empty", state="error", expanded=True)
                    st.error(
                        "Video prompts were not generated. "
                        "Check that ANTHROPIC_API_KEY is set and the video prompt builder is working."
                    )
                    return False
            if artifact == "video-assets.json":
                assets = result.get("videos", []) if isinstance(result, dict) else []
                if not assets:
                    status.update(label="Failed — video assets empty", state="error", expanded=True)
                    st.error(
                        "No video assets were created. "
                        "Check that images.json and video-prompts.json contain data."
                    )
                    return False
            st.write(f"✓ {artifact}")
        status.update(label="Videos ready", state="complete", expanded=False)
    return True


def _regenerate_images(run_id: str):
    from workflows.media.handler import handle_media
    handle_media(run_id)


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Media Content System", layout="wide")

st.title("AI Media Content System")
st.markdown("Generate scripts, images and video assets from a single idea.")

st.divider()

# ── Session state ─────────────────────────────────────────────────────────────

if "idea_input" not in st.session_state:
    st.session_state.idea_input = ""
if "run_id" not in st.session_state:
    st.session_state.run_id = None
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "script_edited" not in st.session_state:
    st.session_state.script_edited = False

# ── Input ─────────────────────────────────────────────────────────────────────

if st.button("Use example: Coffee trends for Gen Z"):
    st.session_state.idea_input = _EXAMPLE
    st.rerun()

idea = st.text_area(
    "Your content idea",
    value=st.session_state.idea_input,
    placeholder="e.g. Coffee trends for Gen Z",
    height=100,
)

col_a, col_b, col_c = st.columns(3)
with col_a:
    full_btn = st.button("Generate full pipeline", type="primary", use_container_width=True)
with col_b:
    images_btn = st.button("Regenerate images", use_container_width=True,
                           disabled=st.session_state.run_id is None)
with col_c:
    video_btn = st.button("Generate videos", use_container_width=True,
                          disabled=st.session_state.run_id is None)

# ── Actions ───────────────────────────────────────────────────────────────────

if full_btn:
    if not idea.strip():
        st.warning("Enter a content idea first.")
        st.stop()
    with st.spinner("Generating content..."):
        try:
            from core.orchestrator.runner import run_pipeline
            ok, run_id = run_pipeline(idea.strip())
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()
    if ok:
        st.session_state.run_id = run_id
        st.rerun()
    else:
        st.error(f"Pipeline failed — {run_id}")
        st.stop()

if images_btn and st.session_state.run_id:
    with st.spinner("Regenerating images..."):
        try:
            _regenerate_images(st.session_state.run_id)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()
    st.rerun()

if video_btn and st.session_state.run_id:
    try:
        ok = _generate_videos(st.session_state.run_id)
        if ok:
            st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# ── Nothing to show yet ───────────────────────────────────────────────────────

run_id = st.session_state.run_id
if not run_id:
    st.stop()

run_dir = _ARTIFACTS / run_id

# ── Status badges ─────────────────────────────────────────────────────────────

st.divider()

script_ready = (run_dir / "script.json").exists()
images_ready = (run_dir / "images.json").exists()
_vdata = _load_json(run_dir / "videos.json")
videos_ready = bool(_vdata and _vdata.get("videos"))

s1, s2, s3, _ = st.columns([1, 1, 1, 3])
with s1:
    if script_ready:
        st.success("Script ready")
    else:
        st.caption("○ Script")
with s2:
    if images_ready:
        st.success("Images ready")
    else:
        st.caption("○ Images")
with s3:
    if videos_ready:
        st.success("Videos ready")
    else:
        st.caption("○ Videos")

st.divider()

# ── Script ────────────────────────────────────────────────────────────────────

script_path = run_dir / "script.json"
script = _load_json(script_path)

_sh_col, _btn_col = st.columns([5, 1])
with _sh_col:
    st.subheader("Script")
with _btn_col:
    if script:
        if st.session_state.edit_mode:
            if st.button("Cancel", use_container_width=True):
                st.session_state.edit_mode = False
                st.rerun()
        else:
            if st.button("Edit scenes", use_container_width=True):
                st.session_state.edit_mode = True
                st.rerun()

if script:
    scenes = script.get("scenes", [])

    # ── Pending-edit callout ──────────────────────────────────────────────────
    if st.session_state.script_edited and not st.session_state.edit_mode:
        st.info("Script was edited. Regenerate images to apply your changes.")
        _regen_col, _ = st.columns([2, 3])
        with _regen_col:
            if st.button("Regenerate images from edited script", type="primary",
                         use_container_width=True):
                with st.spinner("Regenerating images..."):
                    try:
                        _regenerate_images(run_id)
                        st.session_state.script_edited = False
                        st.success("Images regenerated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Edit mode ─────────────────────────────────────────────────────────────
    if st.session_state.edit_mode:
        for scene in scenes:
            order = scene.get("order", "?")
            duration = scene.get("duration_sec", "?")
            with st.container(border=True):
                st.markdown(f"**Scene {order}** · {duration}s")
                col_l, col_r = st.columns(2)
                with col_l:
                    st.text_area(
                        "Voiceover",
                        value=scene.get("voiceover", ""),
                        key=f"edit_vo_{run_id}_{order}",
                        height=100,
                    )
                with col_r:
                    st.text_area(
                        "Visual description",
                        value=scene.get("visual_description", ""),
                        key=f"edit_vis_{run_id}_{order}",
                        height=100,
                    )
                st.text_input(
                    "On-screen text",
                    value=scene.get("on_screen_text", ""),
                    key=f"edit_os_{run_id}_{order}",
                )

        st.write("")
        _apply_col, _ = st.columns([2, 3])
        with _apply_col:
            if st.button("Apply changes", type="primary", use_container_width=True):
                new_scenes = []
                for scene in scenes:
                    order = scene.get("order", "?")
                    new_scenes.append({
                        **scene,
                        "voiceover": st.session_state.get(f"edit_vo_{run_id}_{order}",
                                                          scene.get("voiceover", "")),
                        "visual_description": st.session_state.get(f"edit_vis_{run_id}_{order}",
                                                                    scene.get("visual_description", "")),
                        "on_screen_text": st.session_state.get(f"edit_os_{run_id}_{order}",
                                                               scene.get("on_screen_text", "")),
                    })
                _save_json(script_path, {**script, "scenes": new_scenes})
                st.session_state.edit_mode = False
                st.session_state.script_edited = True
                st.rerun()

    # ── View mode ─────────────────────────────────────────────────────────────
    else:
        for scene in scenes:
            order = scene.get("order", "?")
            duration = scene.get("duration_sec", "?")
            st.markdown(f"**Scene {order}** · {duration}s")
            col_v, col_vis = st.columns(2)
            with col_v:
                st.markdown("**Voiceover**")
                st.info(scene.get("voiceover", "—"))
            with col_vis:
                st.markdown("**Visual description**")
                st.info(scene.get("visual_description", "—"))
            on_screen = scene.get("on_screen_text", "")
            if on_screen:
                st.markdown(f"**On-screen text:** {on_screen}")
            st.write("")
else:
    st.warning("script.json not found")

st.divider()

# ── Images ────────────────────────────────────────────────────────────────────

st.subheader("Generated images")

images_path = run_dir / "images.json"
images_data = _load_json(images_path)
_images_list = images_data.get("images", []) if images_data else []
if _images_list:
    images = _images_list
    cols_per_row = 3
    for row_start in range(0, len(images), cols_per_row):
        row_imgs = images[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for j, img in enumerate(row_imgs):
            scene_idx = row_start + j
            scene_label = f"Scene {scene_idx + 1}"
            url = img.get("url", "")
            with cols[j]:
                _show_image(url, caption=scene_label)
                st.caption(f"model: {img.get('model', '?')}  ·  {img.get('scene_id', '')}")
                with st.expander("Prompt"):
                    st.write(img.get("prompt", "—"))

                # Download PNG
                p = Path(url) if url else None
                if p and p.exists() and p.suffix.lower() == ".png":
                    st.download_button(
                        label="Download PNG",
                        data=p.read_bytes(),
                        file_name=f"scene_{scene_idx + 1}.png",
                        mime="image/png",
                        key=f"dl_{scene_idx}",
                    )
                elif url and url.startswith("http"):
                    st.markdown(f"[Open image ↗]({url})")
                else:
                    st.warning("Image file not found")

                if st.button("Regenerate image", key=f"regen_{scene_idx}"):
                    with st.spinner("Regenerating..."):
                        _regenerate_image(run_id, scene_idx, img.get("prompt", ""))
                    st.rerun()

    # Download all as ZIP
    st.write("")
    local_pngs = [
        (f"scene_{i + 1}.png", Path(img["url"]))
        for i, img in enumerate(images)
        if img.get("url") and Path(img["url"]).exists() and Path(img["url"]).suffix.lower() == ".png"
    ]
    if local_pngs:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, path in local_pngs:
                zf.writestr(name, path.read_bytes())
        zip_buf.seek(0)
        st.download_button(
            label="Download all images (ZIP)",
            data=zip_buf,
            file_name="generated_images.zip",
            mime="application/zip",
        )

else:
    if images_data is not None:
        st.warning("Image generation produced no images. Check that the image prompt builder ran correctly.")
    else:
        st.warning("images.json not found")

st.divider()

# ── Video assets ──────────────────────────────────────────────────────────────

st.subheader("Video assets")

va_path = run_dir / "video-assets.json"
va_data = _load_json(va_path)
va_videos = va_data.get("videos", []) if va_data else []
if va_videos:
    for i, v in enumerate(va_videos, start=1):
        st.markdown(f"**Scene {i}** · status: `{v.get('status', '?')}`")
        col_img, col_text = st.columns([1, 2])
        with col_img:
            _show_image(v.get("image", ""), caption="reference image")
        with col_text:
            st.markdown("**Video prompt**")
            st.info(v.get("prompt", "—"))
        st.write("")
else:
    st.info("Video assets are not ready yet. Generate videos after images are ready.")

st.divider()

# ── Videos ────────────────────────────────────────────────────────────────────

st.subheader("Videos")

videos_path = run_dir / "videos.json"
videos_data = _load_json(videos_path)
_videos_list = videos_data.get("videos", []) if videos_data else []
if _videos_list:
    for v in _videos_list:
        scene_id = v.get("scene_id", "scene")
        status = v.get("status", "")
        url = v.get("url", "") or ""
        st.markdown(f"**{scene_id}** · `{status}`")
        if url:
            p = Path(url)
            if p.exists() and url.endswith(".mp4"):
                st.video(str(p))
            elif url.startswith("http"):
                st.markdown(f"[Watch video →]({url})")
            else:
                st.caption("Mock video — no real file yet")
        else:
            st.caption("No video URL")
        st.write("")
else:
    st.info("Video not generated yet.")
    if st.button("Generate videos from images", type="primary"):
        try:
            ok = _generate_videos(run_id)
            if ok:
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()

# ── Run log ───────────────────────────────────────────────────────────────────

with st.expander("Run log"):
    log_path = _LOGS / f"{run_id}.json"
    log = _load_json(log_path)
    if log:
        st.json(log)
        _download_btn(log_path, "Download run-log.json")
    else:
        st.warning("run log not found")

st.divider()

# ── Export package ────────────────────────────────────────────────────────────

st.subheader("Export package")

log_p = _LOGS / f"{run_id}.json"

# Collect local PNGs
png_files = []
for i, img in enumerate(_images_list):
    url = img.get("url", "")
    p = Path(url) if url else None
    if p and p.exists() and p.suffix.lower() == ".png":
        png_files.append((f"scene_{i + 1}.png", p))

# Collect local MP4s
mp4_files = []
for i, v in enumerate(_videos_list):
    url = v.get("url", "") or ""
    p = Path(url) if url else None
    if p and p.exists() and p.suffix.lower() == ".mp4":
        mp4_files.append((f"scene_{i + 1}.mp4", p))

# script.txt
export_cols = st.columns(4)
col_i = 0

script_txt = ""
if script:
    lines = [script.get("title", "Script"), ""]
    for scene in script.get("scenes", []):
        lines.append(f"Scene {scene.get('order', '?')} ({scene.get('duration_sec', '?')}s)")
        if scene.get("voiceover"):
            lines.append(f"Voiceover: {scene['voiceover']}")
        if scene.get("on_screen_text"):
            lines.append(f"On-screen: {scene['on_screen_text']}")
        if scene.get("visual_description"):
            lines.append(f"Visual: {scene['visual_description']}")
        lines.append("")
    if script.get("cta"):
        lines.append(f"CTA: {script['cta']}")
    script_txt = "\n".join(lines)

if script_txt:
    with export_cols[col_i % 4]:
        st.download_button(
            label="Download script.txt",
            data=script_txt.encode("utf-8"),
            file_name="script.txt",
            mime="text/plain",
            key="export_script_txt",
        )
    col_i += 1

# images ZIP
if png_files:
    img_zip = io.BytesIO()
    with zipfile.ZipFile(img_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, p in png_files:
            zf.writestr(name, p.read_bytes())
    img_zip.seek(0)
    with export_cols[col_i % 4]:
        st.download_button(
            label="Download images.zip",
            data=img_zip,
            file_name="images.zip",
            mime="application/zip",
            key="export_images_zip",
        )
    col_i += 1

# videos ZIP
if mp4_files:
    vid_zip = io.BytesIO()
    with zipfile.ZipFile(vid_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, p in mp4_files:
            zf.writestr(name, p.read_bytes())
    vid_zip.seek(0)
    with export_cols[col_i % 4]:
        st.download_button(
            label="Download videos.zip",
            data=vid_zip,
            file_name="videos.zip",
            mime="application/zip",
            key="export_videos_zip",
        )
    col_i += 1

# Full package ZIP
_JSON_ARTIFACTS = [
    "script.json", "media-plan.json", "image-prompts.json", "images.json",
    "video-prompts.json", "video-assets.json", "video-jobs.json", "videos.json",
]
full_zip = io.BytesIO()
with zipfile.ZipFile(full_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    for filename in _JSON_ARTIFACTS:
        p = run_dir / filename
        if p.exists():
            zf.write(p, f"artifacts/{filename}")
    if log_p.exists():
        zf.write(log_p, f"artifacts/run-log.json")
    if script_txt:
        zf.writestr("script.txt", script_txt.encode("utf-8"))
    for name, p in png_files:
        zf.writestr(f"images/{name}", p.read_bytes())
    for name, p in mp4_files:
        zf.writestr(f"videos/{name}", p.read_bytes())
full_zip.seek(0)

st.write("")
st.download_button(
    label="Download full package (ZIP)",
    data=full_zip,
    file_name=f"{run_id}.zip",
    mime="application/zip",
    type="primary",
    use_container_width=True,
)

# ── Developer / Debug ─────────────────────────────────────────────────────────

with st.expander("Developer / Debug"):
    st.markdown("**JSON artifacts**")
    dev_cols = st.columns(4)
    dev_i = 0
    all_json = _JSON_ARTIFACTS + []
    for filename in all_json:
        p = run_dir / filename
        if p.exists():
            with dev_cols[dev_i % 4]:
                st.download_button(
                    label=filename,
                    data=p.read_bytes(),
                    file_name=filename,
                    mime="application/json",
                    key=f"dev_{filename}",
                )
            dev_i += 1
    if log_p.exists():
        with dev_cols[dev_i % 4]:
            st.download_button(
                label="run-log.json",
                data=log_p.read_bytes(),
                file_name="run-log.json",
                mime="application/json",
                key="dev_runlog",
            )
        dev_i += 1
    st.markdown(f"**run_id:** `{run_id}`")
