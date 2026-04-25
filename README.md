# AI Media Content System

A multi-stage AI pipeline that turns a text idea into a content package: script, generated images, and video-ready assets.

---

## Demo

**Input:**
```
"Coffee trends for Gen Z"
```

**Output:**

`script.json` — scene-by-scene script with voiceover and action per scene

`images.json` — generated images per scene via gpt-image-2:
```json
{
  "scene_id": "run_..._scene_1",
  "url": "runs/artifacts/tmp_images/image_9354f568.png",
  "prompt": "Extreme close-up of latte foam art...",
  "provider": "openai",
  "model": "gpt-image-2"
}
```

`video-assets.json` — image + video prompt paired per scene, ready for animation:
```json
{
  "scene_id": "run_..._scene_1",
  "image": "runs/artifacts/tmp_images/image_9354f568.png",
  "prompt": "Extreme close-up of latte foam art, camera snaps into a sharp push-in...",
  "status": "ready_for_animation"
}
```

---

## Problem

Creating short-form video content involves research, scripting, visual planning, and media generation. One big prompt produces inconsistent output. Manual work doesn't scale.

## Solution

A pipeline where each stage reads a validated JSON input, does one job, and writes a validated JSON output. LLM handles reasoning. External APIs handle media. Each run is isolated and reproducible.

---

## Pipeline

```
idea
 → brief
 → research
 → angles
 → script
 → media plan
 → image prompts → images (gpt-image-2)
 → video prompts → video assets (ready_for_animation)
```

Each step writes an artifact to `runs/artifacts/{run_id}/`. No step proceeds if the previous one failed.

---

## Key Features

- Multi-stage pipeline with strict JSON Schema contracts between stages
- Schema validation at every handoff — no silent failures
- LLM used only for reasoning (script, angles, prompts) — not for side effects
- Image generation via gpt-image-2 with retry (3 attempts) and fallback to dall-e-3
- Video-ready asset preparation layer — image + prompt + status per scene
- Immutable runs — each run has a unique `run_id`, artifacts are never overwritten
- Human approval gate before any publish action

---

## Tech Stack

- **Python** — pipeline, orchestrator, workflow handlers
- **Anthropic Claude** (claude-sonnet-4-6) — script, angles, media plan, prompts
- **OpenAI** (gpt-image-2 / dall-e-3) — image generation
- **JSON Schema** — contract validation between stages
- **Custom orchestrator** — stage sequencing, state machine, run logging

---

## Output structure

```
runs/artifacts/{run_id}/
  brief.json              ← normalized content brief
  research.json           ← grounded findings
  angles.json             ← content angle options
  script.json             ← scene-by-scene script
  media-plan.json         ← visual direction per scene
  image-prompts.json      ← image generation prompts
  images.json             ← generated images (URL + model)
  video-prompts.json      ← video generation prompts
  video-assets.json       ← image + prompt + status per scene
  review-report.json      ← QA verdict
  publish-job.json        ← requires human approval
```

---

## Current status

| Stage | Status |
|---|---|
| Text pipeline (brief → script → review) | Working |
| Image generation (gpt-image-2) | Working |
| Video prompt generation | Working |
| Video asset preparation | Working (`ready_for_animation`) |
| Live video generation | Not yet integrated |
| Assembly + final package | Not yet integrated |

---

## Next steps

- Integrate a video generation API (Runway, Kling, or Sora) in `integrations/video/`
- Add assembly stage (ffmpeg) to combine clips and audio
- Build a minimal web UI for run submission and artifact review
- Add per-stage cost tracking to the RunLog
