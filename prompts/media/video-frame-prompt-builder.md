# Video Frame Prompt Builder — Runway-Safe Constraints

This document defines the rules used by `video_frame_prompt_builder.py`
to build image generation prompts for Runway source frames.
It is NOT a template loaded at LLM runtime. It is the specification
embedded in the builder's code.

---

## Purpose

These prompts are sent to an image generation API (OpenAI) to produce
reference frames that Runway will animate into video clips.

Requirements differ from standalone image prompts:

| Standalone images | Runway source frames |
|-------------------|----------------------|
| Creative, varied composition | Stable, consistent composition |
| Scene-specific environment | Same room every scene |
| Any character interpretation | Same character every scene |
| Can show screens, text, UI | No text, no UI, no numbers |
| Complex camera angles OK | Medium shot, eye-level preferred |
| Motion implied in framing | Static pose, clear and simple |

---

## Locked character definition (all scenes)

- Young adult, mid-20s to early 30s, gender-neutral
- Plain dark t-shirt or minimal clothing, no logos
- Short or pulled-back hair
- Same person across all scenes — do not vary appearance

## Locked environment definition (all scenes)

- Small home office or minimal desk setup
- Wooden desk, one warm desk lamp, plain background
- No second monitor, no multiple screens
- No text, posters, whiteboards, or readable objects in background
- Same room and desk position in every frame

---

## Per-scene action arc (6 beats)

| Scene | Emotional beat | Physical action | Hand position |
|-------|---------------|-----------------|---------------|
| 1 | Confused, tense | Holding a phone face-down, looking down at desk | One hand on desk, one loosely holding phone at waist |
| 2 | Concerned, leaning in | Leaning forward, reaching toward a pen | Both hands near desk surface |
| 3 | Focused, analytical | Hand resting on papers, looking down | One hand flat on paper, other on table edge |
| 4 | Determined, active | Writing in open notebook with pen, upright posture | One hand writing, other beside notebook |
| 5 | Calm, resolving | Sitting back in chair, looking slightly upward | Both hands relaxed in lap |
| 6 | Grounded, clear | Sitting upright, looking forward | Both hands flat on desk surface |

---

## Hard constraints for every prompt

Always include:
- `medium shot, eye level`
- `shallow depth of field`
- `warm desk lamp lighting, soft side shadows`
- `cinematic color grade, warm dark tones`
- `no text, no screens, no numbers, no readable content`

Never include:
- Any screen content (phone screen, laptop screen, dashboard)
- Numbers, charts, graphs, invoices, spreadsheets
- Readable text of any kind
- Hands near face or hair
- Complex hand gestures or finger pointing
- Split-screen or composite compositions
- Abstract or metaphorical visuals

---

## Output format (video-frame-prompts.json)

```json
{
  "prompts": [
    {
      "scene_id": "...",
      "prompt": "..."
    }
  ]
}
```
