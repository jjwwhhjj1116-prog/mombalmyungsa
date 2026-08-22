#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


STAGE_IDS = [
    "00_topic_discovery",
    "01_evidence_map",
    "02_story_contract",
    "03_script_draft",
    "04_script_review",
    "05_script_approval",
    "06_storyboard",
    "07_generation_plan",
    "08_pilot_generation",
    "09_batch_generation",
    "10_clip_harvest",
    "11_voice_alignment",
    "12_tts_owned_edit",
    "13_semantic_motion_sound",
    "14_final_qa",
    "15_packaging_release",
]

STATUS_VALUES = {"pending", "in_progress", "completed", "blocked"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def nonempty_string_list(value):
    return isinstance(value, list) and bool(value) and all(nonempty_string(item) for item in value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--require-complete-through",
        choices=STAGE_IDS,
        help="Require every stage through this stage to be completed and hash-locked.",
    )
    args = parser.parse_args()

    errors = []
    warnings = []
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"valid": False, "errors": [f"JSON read error: {exc}"]}, ensure_ascii=False, indent=2))
        return 1

    if data.get("schema_version") != "timemedic.omni-stage-pipeline.v1":
        errors.append("schema_version must be timemedic.omni-stage-pipeline.v1")
    if data.get("brand") != "몸의 발명사":
        errors.append("brand must be 몸의 발명사")
    if data.get("production_mode") != "stage_gated_tts_owned_omni_hybrid_opening_i2v_then_t2v":
        errors.append("production_mode must be stage_gated_tts_owned_omni_hybrid_opening_i2v_then_t2v")

    topic = data.get("topic_selection", {})
    if topic.get("minimum_candidates", 0) < 10:
        errors.append("topic_selection.minimum_candidates must be at least 10")
    expected_dimensions = {
        "present_familiarity",
        "hidden_contradiction",
        "visual_mechanism",
        "human_stakes",
        "reversal_strength",
        "evidence_strength",
        "current_relevance",
        "originality",
    }
    if set(topic.get("dimensions", [])) != expected_dimensions:
        errors.append("topic_selection.dimensions must contain the eight required dimensions")
    hard_reject = topic.get("hard_reject", {})
    if hard_reject.get("evidence_strength_below") != 4:
        errors.append("topic hard reject must block evidence strength below 4")
    if hard_reject.get("visual_mechanism_below") != 3:
        errors.append("topic hard reject must block visual mechanism below 3")
    if hard_reject.get("medical_safety_language_missing") is not True:
        errors.append("topic hard reject must block missing medical safety language")

    invariants = data.get("invariants", {})
    required_invariants = {
        "one_sentence_one_timing_owner": True,
        "final_timing_master": "final_tts_word_alignment",
        "next_sentence_meaning_before_boundary": False,
        "generated_text_policy": "blank_plates_only",
        "paid_generation_before_script_approval": False,
        "batch_generation_before_pilot_qa_pass": False,
        "final_width": 1080,
        "final_height": 1920,
        "duration_tolerance_frames": 1,
        "caption_timing_source": "final_tts_word_alignment",
        "caption_even_split_forbidden": True,
        "flow_reference_grammar_lock_required": True,
        "thumbnail_is_video_frame_zero": True,
        "thumbnail_contract_stage": "06_storyboard",
        "thumbnail_final_pixels_before_generation": True,
        "thumbnail_mobile_qa_before_generation": True,
        "textless_opening_image_before_generation": True,
        "first_two_seconds_discontinuity_count_max": 0,
    }
    for key, expected in required_invariants.items():
        if invariants.get(key) != expected:
            errors.append(f"invariants.{key} must be {expected!r}")

    script = data.get("script_contract", {})
    if script.get("beats") != 16:
        errors.append("script_contract.beats must be 16")
    if script.get("default_profile") != "short_50_58":
        errors.append("script_contract.default_profile must be short_50_58")
    profiles = script.get("profiles", {})
    short_profile = profiles.get("short_50_58", {})
    if short_profile.get("target_seconds") != [50, 58]:
        errors.append("short_50_58 target_seconds must be [50, 58]")
    if short_profile.get("sentence_count") != [22, 30]:
        errors.append("short_50_58 sentence_count must be [22, 30]")
    if short_profile.get("audience_timeline_seconds") != [[0, 5], [5, 15], [15, 27], [27, 40], [40, 50], [50, 58]]:
        errors.append("short_50_58 must use the approved six-stage audience timeline")
    extended_profile = profiles.get("extended_60_80", {})
    if extended_profile.get("target_seconds") != [60, 80] or extended_profile.get("sentence_count") != [24, 36]:
        errors.append("extended_60_80 profile must keep 60-80 seconds and 24-36 sentences")
    if script.get("user_revision_required") is not True:
        errors.append("script_contract.user_revision_required must be true")
    if script.get("final_human_approval_required") is not True:
        errors.append("script_contract.final_human_approval_required must be true")
    if len(script.get("order", [])) != 16:
        errors.append("script_contract.order must contain 16 story beats")

    visual = data.get("visual_generation", {})
    expected_visual = {
        "engine": "Google Flow",
        "model": "Omni Flash",
        "forbidden_model": "Veo 3.1 Quality",
        "mode": "text_to_video",
        "aspect_ratio": "9:16",
        "seconds_per_unit": 8,
        "default_candidate_count": 1,
        "high_risk_candidate_count": 2,
        "candidate_selection": "best_segment_harvest",
        "optical_flow_policy": "exceptional_duration_repair_only",
    }
    for key, expected in expected_visual.items():
        if visual.get(key) != expected:
            errors.append(f"visual_generation.{key} must be {expected!r}")
    if visual.get("opening_mode_override") != "image_to_video_from_approved_textless_thumbnail":
        errors.append("visual_generation.opening_mode_override must use the approved textless thumbnail")
    if visual.get("remaining_units_mode") != "text_to_video":
        errors.append("visual_generation.remaining_units_mode must remain text_to_video")
    if visual.get("pilot_units") != ["hook", "mechanism_or_reversal"]:
        errors.append("visual_generation.pilot_units must be hook plus mechanism_or_reversal")
    if set(visual.get("prompt_views", [])) != {"ko_review", "en_generation"}:
        errors.append("visual_generation.prompt_views must contain ko_review and en_generation")

    typography = data.get("typography", {})
    expected_typography = {
        "font_family": "Gmarket Sans Bold",
        "font_size_px": 100,
        "stroke_width_px": 30,
        "stroke_color": "#000000",
        "shadow_required": True,
        "manual_line_breaks": True,
        "anchor_x_px": 540,
        "anchor_y_px": 1200,
        "anchor_y_ratio": 0.625,
        "anchor_reference": "10_of_16_from_top",
        "block_anchor": "center",
    }
    for key, expected in expected_typography.items():
        if typography.get(key) != expected:
            errors.append(f"typography.{key} must be {expected!r}")

    stages = data.get("stages", [])
    stage_ids = [stage.get("id") for stage in stages if isinstance(stage, dict)]
    if stage_ids != STAGE_IDS:
        errors.append("stages must match the exact 16-stage order")

    seen_in_progress = 0
    first_not_completed = None
    for index, stage_id in enumerate(STAGE_IDS):
        if index >= len(stages) or not isinstance(stages[index], dict):
            continue
        stage = stages[index]
        label = f"stage {stage_id}"
        expected_dependency = [] if index == 0 else [STAGE_IDS[index - 1]]
        if stage.get("depends_on") != expected_dependency:
            errors.append(f"{label}: depends_on must be {expected_dependency}")
        if not nonempty_string(stage.get("objective")):
            errors.append(f"{label}: objective is required")
        if not nonempty_string_list(stage.get("inputs")):
            errors.append(f"{label}: inputs must be a non-empty string array")
        if not nonempty_string_list(stage.get("outputs")):
            errors.append(f"{label}: outputs must be a non-empty string array")

        gate = stage.get("gate", {})
        if not isinstance(gate.get("human_approval_required"), bool):
            errors.append(f"{label}: gate.human_approval_required must be boolean")
        if not nonempty_string_list(gate.get("pass_criteria")):
            errors.append(f"{label}: gate.pass_criteria must be a non-empty string array")
        if not nonempty_string_list(gate.get("blocked_actions")):
            errors.append(f"{label}: gate.blocked_actions must be a non-empty string array")

        status = stage.get("status")
        if status not in STATUS_VALUES:
            errors.append(f"{label}: unsupported status {status!r}")
            continue
        if status == "in_progress":
            seen_in_progress += 1
        if status == "completed":
            if not nonempty_string(stage.get("lock_path")):
                errors.append(f"{label}: completed stage requires lock_path")
            if not SHA256_RE.fullmatch(str(stage.get("lock_sha256", ""))):
                errors.append(f"{label}: completed stage requires a lowercase 64-hex lock_sha256")
        elif stage.get("lock_path") is not None or stage.get("lock_sha256") is not None:
            warnings.append(f"{label}: non-completed stage normally should not retain a lock")

        if first_not_completed is None and status != "completed":
            first_not_completed = index
        if first_not_completed is not None and index > first_not_completed and status in {"completed", "in_progress"}:
            errors.append(f"{label}: cannot advance while an earlier stage is not completed")

    if seen_in_progress > 1:
        errors.append("at most one stage may be in_progress")

    for approval_stage in ("05_script_approval", "15_packaging_release"):
        if approval_stage in stage_ids:
            stage = stages[stage_ids.index(approval_stage)]
            if stage.get("gate", {}).get("human_approval_required") is not True:
                errors.append(f"stage {approval_stage} must require human approval")

    required_through = args.require_complete_through
    if required_through:
        final_index = STAGE_IDS.index(required_through)
        for stage in stages[: final_index + 1]:
            if stage.get("status") != "completed":
                errors.append(f"required stage {stage.get('id')} is not completed")
            if not SHA256_RE.fullmatch(str(stage.get("lock_sha256", ""))):
                errors.append(f"required stage {stage.get('id')} lacks a valid lock_sha256")

    metrics = {
        "stages": len(stages),
        "completed": sum(stage.get("status") == "completed" for stage in stages if isinstance(stage, dict)),
        "in_progress": sum(stage.get("status") == "in_progress" for stage in stages if isinstance(stage, dict)),
        "blocked": sum(stage.get("status") == "blocked" for stage in stages if isinstance(stage, dict)),
        "next_stage": next(
            (stage.get("id") for stage in stages if isinstance(stage, dict) and stage.get("status") != "completed"),
            None,
        ),
    }
    print(json.dumps({"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
