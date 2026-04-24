# Claude Code Rules — AI Media Content System

## Before starting any task
- Read docs/product.md to understand what the system is.
- Read docs/workflows/pipeline.md to understand the pipeline stages.
- Read schemas/entities/ to understand the data contracts before touching any workflow.
- If the task involves a specific stage, read workflows/{stage}/handler.py and its schema first.

## How to work in this repo
- Plan before executing: identify which files change and what the output should be.
- Work one stage at a time — do not modify multiple pipeline stages in one session.
- After any change to a prompt in prompts/, check that the corresponding eval in evals/tests/ still passes.
- After any schema change in schemas/, check all workflow handlers that use that schema.
- After any handler change in workflows/, verify that the artifact written to runs/artifacts/ is schema-valid.

## File ownership rules
- prompts/ — prompt templates only, no logic.
- schemas/ — JSON Schema definitions only, no logic.
- workflows/ — stage handlers only, no prompt text inline.
- core/orchestrator/ — pipeline control only, no business logic.
- core/tools/ — utility functions only, each does one thing.
- integrations/ — external API adapters only, one file per provider.
- runs/ — never edit manually, written by the system only.

## What not to do
- Do not write prompts inline in handler code.
- Do not skip schema validation between stages.
- Do not add logic to core/tools/ that belongs in a workflow handler.
- Do not call integrations/image/ or integrations/video/ in tests without a mock.
- Do not create new top-level directories without updating docs/architecture/overview.md.
- Do not modify runs/ artifacts directly.

## Default mode
- Always start in plan mode — describe the change before making it.
- If a task is ambiguous, ask for the minimum missing information before proceeding.
- If blocked, stop with a clear description of what is needed to unblock.
