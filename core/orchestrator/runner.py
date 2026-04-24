from core.utils.ids import generate_run_id
from core.tools.log_writer import init_log, update_stage, finish_log
from workflows.intake.handler import handle_intake
from workflows.research.handler import handle_research
from workflows.angles.handler import handle_angles
from workflows.script.handler import handle_script
from workflows.media.handler import handle_media
from workflows.review.handler import handle_review
from workflows.output.handler import handle_output

STAGES = [
    "intake",
    "research",
    "angles",
    "script",
    "media",
    "review",
    "output",
]


def run_pipeline(raw_idea: str) -> tuple[bool, str]:
    run_id = generate_run_id()

    ok, msg = init_log(run_id)
    if not ok:
        return False, f"Failed to init log: {msg}"

    print(f"[{run_id}] Pipeline started: {raw_idea!r}")

    for stage_name in STAGES:
        ok, msg = update_stage(run_id, stage_name, status="running")
        if not ok:
            return False, f"Failed to start stage {stage_name!r}: {msg}"

        print(f"[{run_id}] Running stage: {stage_name}")

        if stage_name == "intake":
            ok, result = handle_intake(run_id, raw_idea)
            if not ok:
                update_stage(run_id, stage_name, status="failed")
                finish_log(run_id, status="failed", summary=str(result))
                return False, f"Stage 'intake' failed: {result}"
            ok, msg = update_stage(run_id, stage_name, status="completed", output_ref="brief.json")
        elif stage_name == "research":
            ok, result = handle_research(run_id)
            if not ok:
                update_stage(run_id, stage_name, status="failed")
                finish_log(run_id, status="failed", summary=str(result))
                return False, f"Stage 'research' failed: {result}"
            ok, msg = update_stage(run_id, stage_name, status="completed", output_ref="research.json")
        elif stage_name == "angles":
            ok, result = handle_angles(run_id)
            if not ok:
                update_stage(run_id, stage_name, status="failed")
                finish_log(run_id, status="failed", summary=str(result))
                return False, f"Stage 'angles' failed: {result}"
            ok, msg = update_stage(run_id, stage_name, status="completed", output_ref="angles.json")
        elif stage_name == "script":
            ok, result = handle_script(run_id)
            if not ok:
                update_stage(run_id, stage_name, status="failed")
                finish_log(run_id, status="failed", summary=str(result))
                return False, f"Stage 'script' failed: {result}"
            ok, msg = update_stage(run_id, stage_name, status="completed", output_ref="script.json")
        elif stage_name == "media":
            ok, result = handle_media(run_id)
            if not ok:
                update_stage(run_id, stage_name, status="failed")
                finish_log(run_id, status="failed", summary=str(result))
                return False, f"Stage 'media' failed: {result}"
            ok, msg = update_stage(run_id, stage_name, status="completed", output_ref="media-plan.json")
        elif stage_name == "review":
            ok, result = handle_review(run_id)
            if not ok:
                update_stage(run_id, stage_name, status="failed")
                finish_log(run_id, status="failed", summary=str(result))
                return False, f"Stage 'review' failed: {result}"
            ok, msg = update_stage(run_id, stage_name, status="completed", output_ref="review.json")
        elif stage_name == "output":
            ok, result = handle_output(run_id)
            if not ok:
                update_stage(run_id, stage_name, status="failed")
                finish_log(run_id, status="failed", summary=str(result))
                return False, f"Stage 'output' failed: {result}"
            ok, msg = update_stage(run_id, stage_name, status="completed", output_ref="output.json")
        else:
            # TODO: dispatch to workflows/{stage_name}/handler.py
            ok, msg = update_stage(run_id, stage_name, status="completed")

        if not ok:
            return False, f"Failed to complete stage {stage_name!r}: {msg}"

    ok, msg = finish_log(run_id, status="completed", summary="Pipeline completed successfully")
    if not ok:
        return False, f"Failed to finish log: {msg}"

    print(f"[{run_id}] Pipeline finished.")
    return True, run_id
