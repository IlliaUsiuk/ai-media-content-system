# Content Production Pipeline

## Overview

The pipeline transforms a text idea into a content package through sequential,
independent stages. Each stage reads a schema-valid JSON input, performs its work,
and writes a schema-valid JSON output to `runs/artifacts/{run_id}/`.

No stage skips schema validation. No stage proceeds if the previous stage failed.

## Pipeline stages

```
[intake] → [research] → [angles] → [script]
                                        ↓
                               [media-planning]
                                        ↓
                              [media-generation]
                                        ↓
                               [assembly] → [review] → [output]
```

Stages `media-planning`, `media-generation`, and `assembly` are added in
Milestones 2–4. The MVP pipeline (Milestone 1) runs:

```
[intake] → [research] → [angles] → [script] → [review] → [output]
```

---

## Stage definitions

### intake
**Purpose:** Normalize the raw operator idea into a structured ContentBrief.

**Input:** Raw text string from operator  
**Output:** `brief.json` — ContentBrief  
**Model use:** LLM normalizes and structures the input  
**Key rules:**
- Infer as little as possible
- Mark unknown required fields explicitly (e.g. `"geo": null`)
- Identify content format: text / image / video
- Identify channel if mentioned

---

### research
**Purpose:** Collect grounded findings from provided documents.

**Input:** `brief.json` — ContentBrief  
**Output:** `research.json` — ResearchPack  
**Model use:** LLM extracts quotes and synthesizes findings  
**Key rules:**
- Use only provided documents — no general knowledge without a source
- Quote-first: extract direct quotes before synthesizing
- Every finding must reference a source ID
- If evidence is insufficient, record as `unknowns[]` — do not fabricate
- Citations must be enabled

---

### angles
**Purpose:** Generate distinct conceptual approaches to the content.

**Input:** `research.json` — ResearchPack  
**Output:** `angles.json` — ContentAngle[]  
**Model use:** LLM generates angle options  
**Key rules:**
- Each angle must be materially different in idea, not just wording
- Angles are grounded in the research pack findings
- Minimum 3 angles, maximum 5

---

### script
**Purpose:** Write a structured script based on the chosen angle.

**Input:** `angles.json` (selected angle) + `research.json`  
**Output:** `script.json` — Script  
**Model use:** LLM writes the script  
**Key rules:**
- Use only facts from the research pack
- Structure: array of scenes, each with voiceover + action description + duration
- Include CTA if relevant to the brief
- Total duration must match the brief's `duration_sec` constraint

---

### media-planning *(Milestone 2+)*
**Purpose:** Translate each scene into a visual description and media prompt.

**Input:** `script.json` — Script  
**Output:** `media-plan.json` — MediaPlan with MediaPrompt[] per scene  
**Model use:** LLM generates visual descriptions  
**Key rules:**
- One MediaPrompt per scene (or per key visual)
- Each prompt includes: description, style, aspect ratio, type (image/video), duration
- Prompts must be self-contained — usable without context from other prompts

---

### media-generation *(Milestone 3–4+)*
**Purpose:** Call external APIs to generate images or video clips per scene.

**Input:** `media-plan.json` — MediaPlan  
**Output:** `asset-manifest.json` + assets in `runs/artifacts/{run_id}/assets/`  
**Model use:** None — calls integrations/image/ or integrations/video/  
**Key rules:**
- One API call per MediaPrompt
- Store MediaAsset with checksum and URL
- On API failure: mark asset as `status: failed`, continue with remaining scenes
- Never call real APIs in tests — use mocks

---

### assembly *(Milestone 4+)*
**Purpose:** Combine video clips and audio into a final content package.

**Input:** `asset-manifest.json` + `script.json`  
**Output:** `content-package.json` + assembled file in `runs/artifacts/{run_id}/package/`  
**Model use:** None — uses ffmpeg or equivalent  
**Key rules:**
- Scene order follows script.json scenes order
- Output multiple formats if specified in brief (e.g. 16:9 and 9:16)
- Store checksum of final assembled file

---

### review
**Purpose:** Quality assurance — check output against the brief and technical standards.

**Input:** `script.json` (M1) or `content-package.json` (M4)  
**Output:** `review-report.json` — ReviewReport  
**Model use:** LLM evaluates quality  
**Key rules:**
- Two independent review levels: technical QA + content QA
- Technical: format, length, completeness
- Content: alignment with brief, factual accuracy, tone
- Verdict options: `approved` / `needs_revision` / `rejected`
- On `needs_revision`: return to script stage, maximum 2 revision cycles
- On `rejected`: stop pipeline, record reason

---

### output
**Purpose:** Prepare final artifacts for operator review and approval.

**Input:** `review-report.json` with `verdict: approved`  
**Output:** `publish-job.json` — PublishJob  
**Model use:** None  
**Key rules:**
- Only proceeds if review verdict is `approved`
- Sets `approval_required: true`, `approval_present: false` by default
- Human must explicitly approve before any external action
- Writes final summary to RunLog

---

## Run state machine

```
queued → running → review_pending → approved → done
                                 → rejected  → done (failed)
           ↓
         error → done (failed)
```

State is tracked in `runs/logs/run_{id}.json` under `status`.

---

## Artifact structure per run

```
runs/
  logs/
    run_{id}.json            ← RunLog (all stages, costs, errors)
  artifacts/
    {run_id}/
      brief.json             ← ContentBrief
      research.json          ← ResearchPack
      angles.json            ← ContentAngle[]
      script.json            ← Script
      media-plan.json        ← MediaPlan (M2+)
      asset-manifest.json    ← AssetManifest (M3+)
      assets/                ← MediaAsset files (M3+)
      package/               ← ContentPackage (M4+)
      review-report.json     ← ReviewReport
      publish-job.json       ← PublishJob
```

All artifacts are immutable after being written. A new run always produces a new `run_id`.
