import io
import json
import sys
import zipfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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


def _list_runs(limit: int = 10) -> list[str]:
    if not _ARTIFACTS.exists():
        return []
    dirs = [d for d in _ARTIFACTS.iterdir() if d.is_dir() and d.name.startswith("run_")]
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return [d.name for d in dirs[:limit]]


def _save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


def _regenerate_images(run_id: str):
    from workflows.media.handler import handle_media
    handle_media(run_id)


def _generate_videos(run_id: str) -> bool:
    from workflows.media.video_frame_prompt_builder import build_video_frame_prompts
    from workflows.media.video_frame_generator import generate_video_frames
    from workflows.media.video_prompt_builder import build_video_prompts
    from workflows.media.video_generator import generate_videos
    from workflows.media.video_runner import run_video_jobs
    from workflows.media.video_collector import collect_videos

    steps = [
        (build_video_frame_prompts, "video-frame-prompts.json", "Building video frame prompts"),
        (generate_video_frames,     "video-frames.json",        "Generating source frames"),
        (build_video_prompts,       "video-prompts.json",       "Building video prompts"),
        (generate_videos,           "video-assets.json",        "Pairing frames with prompts"),
        (run_video_jobs,            "video-jobs.json",          "Creating video jobs"),
        (collect_videos,            "videos.json",              "Collecting results"),
    ]

    _empty_checks = {
        "video-frame-prompts.json": ("prompts", "Video frame prompts came back empty."),
        "video-frames.json":        ("frames",  "Source frames not generated. Check OPENAI_API_KEY."),
        "video-assets.json":        ("videos",  "No video assets — check video-frames.json and video-prompts.json."),
    }

    with st.status("Generating videos...", expanded=True) as status:
        for fn, artifact, label in steps:
            st.write(f"{label}...")
            ok, result = fn(run_id)
            if not ok:
                status.update(label=f"Failed at {artifact}", state="error", expanded=True)
                st.error(str(result))
                return False
            if artifact in _empty_checks:
                key, msg = _empty_checks[artifact]
                if not (isinstance(result, dict) and result.get(key)):
                    status.update(label=f"Failed — {artifact} empty", state="error", expanded=True)
                    st.error(msg)
                    return False
            st.write(f"✓ {artifact}")
        status.update(label="Videos ready", state="complete", expanded=False)
    return True


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Media Content System", layout="wide")

st.title("AI Media Content System")
st.caption("Transform a content idea into a script, standalone images, and AI video.")

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
if "active_tab" not in st.session_state:
    st.session_state.active_tab = None

# ── Sidebar: Run history ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Run history")
    _runs = _list_runs()
    if _runs:
        _run_options = ["— select —"] + _runs
        _selected = st.selectbox("Open existing run", _run_options, key="run_history_select")
        if st.button("Load run", use_container_width=True):
            if _selected != "— select —":
                st.session_state.run_id = _selected
                st.session_state.edit_mode = False
                st.session_state.script_edited = False
                st.rerun()
    else:
        st.caption("No runs yet")
    st.button("Refresh runs", use_container_width=True)

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
    images_btn = st.button("Generate images", type="primary", use_container_width=True)
with col_b:
    video_btn = st.button("Generate video", type="primary", use_container_width=True)
with col_c:
    full_btn = st.button("Generate full package", use_container_width=True)

# ── Actions ───────────────────────────────────────────────────────────────────

if images_btn:
    if not idea.strip():
        st.warning("Enter a content idea first.")
        st.stop()
    with st.spinner("Running pipeline (script + images)..."):
        try:
            from core.orchestrator.runner import run_pipeline
            ok, _new_run_id = run_pipeline(idea.strip())
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()
    if not ok:
        st.error(f"Pipeline failed — {_new_run_id}")
        st.stop()
    st.session_state.run_id = _new_run_id
    st.session_state.active_tab = "images"
    st.rerun()

if video_btn:
    if not idea.strip():
        st.warning("Enter a content idea first.")
        st.stop()
    with st.spinner("Running pipeline..."):
        try:
            from core.orchestrator.runner import run_pipeline
            ok, _new_run_id = run_pipeline(idea.strip())
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()
    if not ok:
        st.error(f"Pipeline failed — {_new_run_id}")
        st.stop()
    st.session_state.run_id = _new_run_id
    st.session_state.active_tab = "video"
    ok_vid = _generate_videos(_new_run_id)
    if ok_vid:
        st.rerun()

if full_btn:
    if not idea.strip():
        st.warning("Enter a content idea first.")
        st.stop()
    with st.spinner("Generating content..."):
        try:
            from core.orchestrator.runner import run_pipeline
            ok, _new_run_id = run_pipeline(idea.strip())
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()
    if ok:
        st.session_state.run_id = _new_run_id
        st.rerun()
    else:
        st.error(f"Pipeline failed — {_new_run_id}")
        st.stop()

# ── Nothing to show yet ───────────────────────────────────────────────────────

run_id = st.session_state.run_id
if not run_id:
    st.stop()

run_dir = _ARTIFACTS / run_id
st.caption(f"Current run: `{run_id}`")

# ── Status badges ─────────────────────────────────────────────────────────────

st.divider()

script_ready  = (run_dir / "script.json").exists()
images_ready  = (run_dir / "images.json").exists()
frames_ready  = (run_dir / "video-frames.json").exists()
_vdata        = _load_json(run_dir / "videos.json")
videos_ready  = bool(_vdata and _vdata.get("videos"))

b1, b2, b3, b4, _ = st.columns([1, 1, 1, 1, 2])
with b1:
    st.success("Script") if script_ready else st.caption("○ Script")
with b2:
    st.success("Images") if images_ready else st.caption("○ Images")
with b3:
    st.success("Video frames") if frames_ready else st.caption("○ Video frames")
with b4:
    st.success("Videos") if videos_ready else st.caption("○ Videos")

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
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

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

# ── Pre-load all tab data ─────────────────────────────────────────────────────

images_data    = _load_json(run_dir / "images.json")
_images_list   = images_data.get("images", []) if images_data else []

_frames_data   = _load_json(run_dir / "video-frames.json")
_frames_list   = _frames_data.get("frames", []) if _frames_data else []

_vprompts_data = _load_json(run_dir / "video-prompts.json")
_vprompts_list = _vprompts_data.get("prompts", []) if _vprompts_data else []

videos_data    = _load_json(run_dir / "videos.json")
_videos_list   = videos_data.get("videos", []) if videos_data else []

# Collect exportable files
_png_files = [
    (f"scene_{i + 1}.png", Path(img["url"]))
    for i, img in enumerate(_images_list)
    if img.get("url") and Path(img["url"]).exists() and Path(img["url"]).suffix.lower() == ".png"
]
_frame_files = [
    (f"frame_{i + 1}.png", Path(fr["url"]))
    for i, fr in enumerate(_frames_list)
    if fr.get("url") and Path(fr["url"]).exists() and Path(fr["url"]).suffix.lower() == ".png"
]
_mp4_files = [
    (f"scene_{i + 1}.mp4", Path(v["url"]))
    for i, v in enumerate(_videos_list)
    if (v.get("url") or "") and Path(v["url"]).exists() and Path(v["url"]).suffix.lower() == ".mp4"
]

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_images, tab_video, tab_export, tab_debug = st.tabs(["Images", "Video", "Export", "Debug"])

# Auto-switch to the tab requested by the last action
_TAB_MAP = {"images": 0, "video": 1, "export": 2, "debug": 3}
_switch_to = st.session_state.active_tab
if _switch_to in _TAB_MAP:
    _idx = _TAB_MAP[_switch_to]
    st.session_state.active_tab = None
    components.html(
        f"""<script>
(function go() {{
    var t = window.parent.document.querySelectorAll('[role="tab"]');
    if (t[{_idx}]) {{ t[{_idx}].click(); }}
    else {{ setTimeout(go, 50); }}
}})();
</script>""",
        height=0,
    )

# ══════════════════════════════════════════════════════════════════════════════
# Images tab — standalone creatives
# ══════════════════════════════════════════════════════════════════════════════

with tab_images:
    st.subheader("Standalone Images")
    st.caption("Creative images for posts, ads, thumbnails or visual concepts.")

    if _images_list:
        cols_per_row = 3
        for row_start in range(0, len(_images_list), cols_per_row):
            row_imgs = _images_list[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for j, img in enumerate(row_imgs):
                scene_idx = row_start + j
                url = img.get("url", "")
                with cols[j]:
                    _show_image(url, caption=f"Scene {scene_idx + 1}")
                    st.caption(f"model: {img.get('model', '?')}  ·  {img.get('scene_id', '')}")
                    with st.expander("Prompt"):
                        st.write(img.get("prompt", "—"))
                    p = Path(url) if url else None
                    if p and p.exists() and p.suffix.lower() == ".png":
                        st.download_button(
                            label="Download PNG",
                            data=p.read_bytes(),
                            file_name=f"scene_{scene_idx + 1}.png",
                            mime="image/png",
                            key=f"dl_img_{scene_idx}",
                        )
                    elif url and url.startswith("http"):
                        st.markdown(f"[Open image ↗]({url})")
                    else:
                        st.warning("Image file not found")
                    if st.button("Regenerate", key=f"regen_img_{scene_idx}"):
                        with st.spinner("Regenerating..."):
                            _regenerate_image(run_id, scene_idx, img.get("prompt", ""))
                        st.rerun()

        st.write("")
        if _png_files:
            _zip_buf = io.BytesIO()
            with zipfile.ZipFile(_zip_buf, "w", zipfile.ZIP_DEFLATED) as _zf:
                for _name, _p in _png_files:
                    _zf.writestr(_name, _p.read_bytes())
            _zip_buf.seek(0)
            st.download_button(
                label="Download all images (ZIP)",
                data=_zip_buf,
                file_name="standalone_images.zip",
                mime="application/zip",
            )

        st.write("")
        if st.button("Regenerate standalone images", use_container_width=True):
            with st.spinner("Regenerating..."):
                try:
                    _regenerate_images(run_id)
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()
            st.rerun()

    else:
        if images_data is not None:
            st.warning("Image generation produced no images. Check that the image prompt builder ran correctly.")
        else:
            st.info("No standalone images yet. Run the full pipeline to generate them.")

# ══════════════════════════════════════════════════════════════════════════════
# Video tab — Runway pipeline
# ══════════════════════════════════════════════════════════════════════════════

with tab_video:
    st.subheader("AI Video")
    st.caption("Video uses dedicated source frames optimized for Runway, not the standalone images.")

    # A. Video source frames
    st.markdown("#### Video source frames")
    if _frames_list:
        cols_per_row = 3
        for row_start in range(0, len(_frames_list), cols_per_row):
            row_frames = _frames_list[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for j, frame in enumerate(row_frames):
                with cols[j]:
                    _show_image(frame.get("url", ""), caption=f"Runway source frame {row_start + j + 1}")
                    st.caption(
                        f"model: {frame.get('model', '?')}  ·  "
                        f"{frame.get('scene_id', '')[-7:]}"
                    )
    else:
        st.info("Video frames are not generated yet. Click **Generate videos** below to create Runway-ready frames.")

    # B. Video prompts
    if _vprompts_list:
        st.write("")
        st.markdown("#### Video prompts")
        for item in _vprompts_list:
            with st.expander(item.get("scene_id", "scene")):
                st.write(item.get("prompt", "—"))

    # C. Generated videos
    st.write("")
    st.markdown("#### Generated videos")
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
                st.caption("No video URL yet")
            st.write("")
    else:
        st.info("No videos yet.")

    st.write("")
    if st.button("Generate videos", type="primary", use_container_width=True, key="gen_video_tab"):
        try:
            ok = _generate_videos(run_id)
            if ok:
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# Export tab
# ══════════════════════════════════════════════════════════════════════════════

with tab_export:
    st.subheader("Export package")

    log_p = _LOGS / f"{run_id}.json"

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

    exp_cols = st.columns(4)
    _ci = 0

    if script_txt:
        with exp_cols[_ci % 4]:
            st.download_button(
                label="script.txt",
                data=script_txt.encode("utf-8"),
                file_name="script.txt",
                mime="text/plain",
                key="export_script_txt",
            )
        _ci += 1

    if _png_files:
        _iz = io.BytesIO()
        with zipfile.ZipFile(_iz, "w", zipfile.ZIP_DEFLATED) as _zf:
            for _n, _p in _png_files:
                _zf.writestr(_n, _p.read_bytes())
        _iz.seek(0)
        with exp_cols[_ci % 4]:
            st.download_button(
                label="Images ZIP",
                data=_iz,
                file_name="standalone_images.zip",
                mime="application/zip",
                key="export_images_zip",
            )
        _ci += 1

    if _frame_files:
        _fz = io.BytesIO()
        with zipfile.ZipFile(_fz, "w", zipfile.ZIP_DEFLATED) as _zf:
            for _n, _p in _frame_files:
                _zf.writestr(_n, _p.read_bytes())
        _fz.seek(0)
        with exp_cols[_ci % 4]:
            st.download_button(
                label="Video frames ZIP",
                data=_fz,
                file_name="video_frames.zip",
                mime="application/zip",
                key="export_frames_zip",
            )
        _ci += 1

    if _mp4_files:
        _vz = io.BytesIO()
        with zipfile.ZipFile(_vz, "w", zipfile.ZIP_DEFLATED) as _zf:
            for _n, _p in _mp4_files:
                _zf.writestr(_n, _p.read_bytes())
        _vz.seek(0)
        with exp_cols[_ci % 4]:
            st.download_button(
                label="Videos ZIP",
                data=_vz,
                file_name="videos.zip",
                mime="application/zip",
                key="export_videos_zip",
            )
        _ci += 1

    st.write("")
    _JSON_ARTIFACTS = [
        "script.json", "media-plan.json", "image-prompts.json", "images.json",
        "video-frame-prompts.json", "video-frames.json",
        "video-prompts.json", "video-assets.json", "video-jobs.json", "videos.json",
    ]
    _full_zip = io.BytesIO()
    with zipfile.ZipFile(_full_zip, "w", zipfile.ZIP_DEFLATED) as _zf:
        for _fn in _JSON_ARTIFACTS:
            _fp = run_dir / _fn
            if _fp.exists():
                _zf.write(_fp, f"artifacts/{_fn}")
        if log_p.exists():
            _zf.write(log_p, "artifacts/run-log.json")
        if script_txt:
            _zf.writestr("script.txt", script_txt.encode("utf-8"))
        for _n, _p in _png_files:
            _zf.writestr(f"images/{_n}", _p.read_bytes())
        for _n, _p in _frame_files:
            _zf.writestr(f"video_frames/{_n}", _p.read_bytes())
        for _n, _p in _mp4_files:
            _zf.writestr(f"videos/{_n}", _p.read_bytes())
    _full_zip.seek(0)

    st.download_button(
        label="Download full package (ZIP)",
        data=_full_zip,
        file_name=f"{run_id}.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# Debug tab
# ══════════════════════════════════════════════════════════════════════════════

with tab_debug:
    st.subheader("Debug")

    with st.expander("Run log", expanded=False):
        _log = _load_json(_LOGS / f"{run_id}.json")
        if _log:
            st.json(_log)
        else:
            st.warning("Run log not found")

    st.markdown("**Raw artifacts**")
    _ALL_JSON = [
        "brief.json", "research.json", "angles.json", "script.json",
        "media-plan.json", "image-prompts.json", "images.json",
        "video-frame-prompts.json", "video-frames.json",
        "video-prompts.json", "video-assets.json", "video-jobs.json", "videos.json",
        "review.json", "output.json",
    ]
    _dcols = st.columns(4)
    _di = 0
    for _fn in _ALL_JSON:
        _fp = run_dir / _fn
        if _fp.exists():
            with _dcols[_di % 4]:
                st.download_button(
                    label=_fn,
                    data=_fp.read_bytes(),
                    file_name=_fn,
                    mime="application/json",
                    key=f"dev_{_fn}",
                )
            _di += 1
    _lp = _LOGS / f"{run_id}.json"
    if _lp.exists():
        with _dcols[_di % 4]:
            st.download_button(
                label="run-log.json",
                data=_lp.read_bytes(),
                file_name="run-log.json",
                mime="application/json",
                key="dev_runlog",
            )
        _di += 1

    st.write("")
    st.caption(f"run_id: `{run_id}`")
