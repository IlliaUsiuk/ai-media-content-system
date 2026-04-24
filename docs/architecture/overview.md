# Architecture Overview

## Core principle

The system is a **versioned workflow platform**, not a chat application.
The chat/UI is the control surface (input + status display). The real system
consists of typed workflow stages, schema-validated contracts, external tool
integrations, and immutable run artifacts.

Source: file1.pdf — "не строить 'один большой чат', а строить версионируемую workflow-платформу"

---

## System layers

```
┌──────────────────────────────────────────────────────┐
│  LAYER 1 — INTERFACE              app/ui/            │
│  Operator input + run status display                 │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP
┌────────────────────▼─────────────────────────────────┐
│  LAYER 2 — API GATEWAY            app/api/           │
│  POST /runs  GET /runs/:id  POST /runs/:id/approve   │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  LAYER 3 — ORCHESTRATOR    core/orchestrator/        │
│  Runner + State machine + Job routing                │
└────────┬───────────┬────────────────┬────────────────┘
         │           │                │
┌────────▼───┐  ┌────▼──────┐  ┌─────▼──────────────────┐
│ LAYER 4    │  │ LAYER 5   │  │ LAYER 6                 │
│ WORKFLOWS  │  │ TOOLS     │  │ INTEGRATIONS            │
│ workflows/ │  │ core/     │  │ integrations/           │
│            │  │ tools/    │  │   image/   video/       │
└────────┬───┘  └────┬──────┘  └─────┬──────────────────┘
         │           │               │
┌────────▼───────────▼───────────────▼──────────────────┐
│  LAYER 7 — STATE & ARTIFACTS                          │
│  runs/logs/  +  runs/artifacts/                       │
└───────────────────────────────────────────────────────┘
```

---

## Folder responsibilities

| Folder | Layer | Responsibility |
|--------|-------|----------------|
| `app/ui/` | Interface | Operator input, run status, artifact display |
| `app/api/` | API Gateway | HTTP endpoints, request routing |
| `core/orchestrator/` | Orchestrator | Pipeline runner, state machine, stage sequencing |
| `core/tools/` | Tools | Schema validation, prompt loading, artifact storage, logging |
| `core/utils/` | Tools | ID generation, checksums, shared helpers |
| `workflows/{stage}/` | Workflows | One handler per pipeline stage |
| `integrations/image/` | Integrations | Image generation API adapters |
| `integrations/video/` | Integrations | Video generation API adapters |
| `schemas/entities/` | Contracts | JSON Schema definitions for all data entities |
| `schemas/workflows/` | Contracts | JSON Schema for stage input/output contracts |
| `prompts/system/` | Prompts | System-level role prompts per agent type |
| `prompts/workflows/` | Prompts | Stage-specific prompt templates with variables |
| `prompts/media/` | Prompts | Image and video prompt builder templates |
| `runs/logs/` | State | RunLog per run (immutable, append-only) |
| `runs/artifacts/` | State | All artifacts per run, organized by run_id |
| `evals/tests/` | Quality | Sample inputs and expected outputs per stage |
| `evals/benchmarks/` | Quality | Gold sets for regression testing |
| `docs/` | Documentation | Product, architecture, workflows, policies |
| `scripts/` | Tooling | Local run scripts, Claude Code hooks |
| `.claude/` | Config | Claude Code settings, rules, permissions |

---

## Key architectural decisions

### 1. Schema-first contracts
Every stage communicates through schema-validated JSON. No stage passes plain text
to the next stage. This prevents "prose drift" where downstream stages fail to
parse upstream output.

Location: `schemas/entities/` and `schemas/workflows/`

### 2. Prompts as versioned files
All prompt templates live in `prompts/` as Markdown files with `{{variables}}`.
No prompt text appears inline in handler code. Changing a prompt = changing a file
+ committing to git.

Location: `prompts/system/`, `prompts/workflows/`, `prompts/media/`

### 3. External media generation
The language model never generates images or video directly. It generates
`MediaPrompt` objects (structured descriptions). External API adapters in
`integrations/` receive these prompts and return `MediaAsset` objects.

This means: changing the image provider = adding a new file in `integrations/image/`.
No workflow handler changes needed.

### 4. Immutable artifacts
Each run produces a unique `run_id`. Artifacts are written once and never
overwritten. This enables full auditability and reproducibility.

### 5. Human approval gate
The `output` stage sets `approval_required: true` and `approval_present: false`
by default. Nothing is published or finalized without explicit human approval via
`POST /runs/:id/approve`.

### 6. Three runtime environments (future)
As the system scales, three isolated environments will be used:
- `research-env` — document processing, citation extraction
- `creative-env` — script generation, media planning, ffmpeg assembly
- `publisher-env` — approval gates, output delivery

For MVP, all stages run in the same local environment.

---

## Data flow between stages

```
Operator idea (string)
    ↓ [intake]
ContentBrief (brief.json)
    ↓ [research]
ResearchPack (research.json)
    ↓ [angles]
ContentAngle[] (angles.json)
    ↓ [script]
Script (script.json)
    ↓ [media-planning]       ← Milestone 2+
MediaPlan (media-plan.json)
    ↓ [media-generation]     ← Milestone 3+
AssetManifest (asset-manifest.json)
    ↓ [assembly]             ← Milestone 4+
ContentPackage (content-package.json)
    ↓ [review]
ReviewReport (review-report.json)
    ↓ [output]
PublishJob (publish-job.json)
    ↓ [human approval]
done
```

Each arrow is a schema-validated handoff. The orchestrator (`core/orchestrator/runner.py`)
controls the sequencing and writes the RunLog at each step.

---

## MVP scope

For Milestone 1, only these components are active:

- `workflows/intake/`, `workflows/research/`, `workflows/angles/`
- `workflows/script/`, `workflows/review/`, `workflows/output/`
- `core/orchestrator/runner.py`, `core/orchestrator/state.py`
- `core/tools/` — all four utilities
- `schemas/entities/` — 6 entity schemas
- `schemas/workflows/` — 6 workflow contracts
- `prompts/system/` — 4 system prompts
- `prompts/workflows/` — 5 stage templates
- `runs/logs/`, `runs/artifacts/`
- `app/api/main.py` — 2 endpoints (or CLI only)

Everything else (`integrations/`, `workflows/media/`, `workflows/assembly/`,
`prompts/media/`) is scaffolded but empty until later milestones.
