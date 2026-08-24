#!/usr/bin/env python3
"""Validate and resume the repository's stage-gated body-invention pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE_CONTRACT = REPO_ROOT / "config" / "stages.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_hash_map(episode: Path, mapping: dict, label: str, errors: list[str]) -> None:
    for relative, expected in mapping.items():
        target = episode / relative
        if not target.is_file():
            errors.append(f"{label}: missing {relative}")
            continue
        actual = sha256(target)
        if actual.lower() != str(expected).lower():
            errors.append(f"{label}: hash mismatch {relative}: {actual} != {expected}")


def validate_episode(episode: Path) -> tuple[list[str], dict]:
    errors: list[str] = []
    pipeline_path = episode / "pipeline.json"
    if not pipeline_path.is_file():
        return [f"missing pipeline.json: {episode}"], {}

    pipeline = load_json(pipeline_path)
    contract = load_json(STAGE_CONTRACT)
    expected_ids = contract["stage_ids"]
    stages = pipeline.get("stages", [])
    actual_ids = [stage.get("id") for stage in stages]
    if actual_ids != expected_ids:
        errors.append("stage order or IDs differ from config/stages.json")

    source = pipeline.get("source_of_truth", {})
    source_path = episode / source.get("path", "")
    if not source_path.is_file():
        errors.append("source_of_truth file is missing")
    else:
        actual_script_hash = sha256(source_path)
        if actual_script_hash != source.get("sha256"):
            errors.append("source_of_truth SHA-256 mismatch")
        expected_sentences = source.get("sentence_count")
        actual_sentences = len([line for line in source_path.read_text(encoding="utf-8").splitlines() if line.strip()])
        if expected_sentences != actual_sentences:
            errors.append(f"sentence count mismatch: {actual_sentences} != {expected_sentences}")

    production = pipeline.get("production_contract", {})
    expected_production = {
        "visual_identity": "continuous_living_miniature_diorama",
        "video_model": "Omni Flash",
        "video_mode": "text_to_video",
        "seconds_per_generation_unit": 8,
        "candidates_per_unit": 1,
        "voice_provider": "ElevenLabs",
        "voice_take": "Take 2",
        "tts_synthesis_strategy": "full_script_single_request",
        "tts_max_chunks_if_provider_limit": 3,
        "sentence_level_tts_stitching_forbidden": True,
        "one_sentence_one_scene": True,
        "final_tts_is_only_timeline": True,
        "caption_font": "Gmarket Sans Bold",
        "caption_size_px": 100,
        "caption_vertical_slot_of_16": 10,
        "thumbnail_is_frame_zero": True,
        "thumbnail_font": "Gmarket Sans Bold",
        "thumbnail_layout": "deep_hook_two_tier",
        "thumbnail_copy_max_visible_characters": 10,
        "thumbnail_outer_stroke_px": 30,
        "thumbnail_outer_stroke_color": "#FFFFFF",
        "thumbnail_inner_stroke_px": 14,
        "thumbnail_inner_stroke_color": "#111111",
        "thumbnail_setup_fill_color": "#FFFFFF",
        "thumbnail_keyword_fill_color": "#FFD21F",
        "thumbnail_subject_is_primary": True,
        "thumbnail_gold_cloud_forbidden": True,
        "thumbnail_product_packshot_present": False,
        "video_generation_requires_approved_thumbnail_lock": True,
        "video_generation_requires_mobile_thumbnail_qa": True,
        "video_generation_requires_textless_opening_image_lock": True,
    }
    for field, expected in expected_production.items():
        if production.get(field) != expected:
            errors.append(f"production_contract.{field} must be {expected!r}")

    voice_model = production.get("voice_model")
    if episode.name == "gas-hwalmyeongsu":
        if voice_model not in {"eleven_v3", "eleven_multilingual_v2"}:
            errors.append("historical gas-hwalmyeongsu voice_model must remain eleven_v3 or be explicitly regenerated with eleven_multilingual_v2")
    elif voice_model != "eleven_multilingual_v2":
        errors.append("production_contract.voice_model must be 'eleven_multilingual_v2' for current 몸의 발명사 episodes")

    duration_route = pipeline.get("duration_routing_contract", {})
    if duration_route.get("threshold_seconds") != 180.0:
        errors.append("duration_routing_contract.threshold_seconds must be 180.0")
    route_status = duration_route.get("status")
    if route_status not in {"pending_measurement", "locked"}:
        errors.append("duration_routing_contract.status must be pending_measurement or locked")
    if duration_route.get("measurement_source") != "final_approved_full_script_tts":
        errors.append("duration route must use final approved full-script TTS")
    routed_aspect = production.get("aspect_ratio")
    if route_status == "locked":
        measured = duration_route.get("duration_seconds")
        if not isinstance(measured, (int, float)) or measured <= 0:
            errors.append("locked duration route requires a positive duration_seconds")
        else:
            expected_aspect = "16:9" if measured > 180.0 else "9:16"
            expected_format = "longform" if measured > 180.0 else "shorts"
            if duration_route.get("content_format") != expected_format:
                errors.append(f"duration route content_format must be {expected_format}")
            if routed_aspect != expected_aspect:
                errors.append(f"production aspect_ratio must be {expected_aspect} for measured TTS")
    elif routed_aspect not in {"9:16", "16:9"}:
        errors.append("provisional production aspect_ratio must be 9:16 or 16:9")

    release = pipeline.get("release_contract", {})
    if release.get("channel_id") != "UCYqdIlpFlB6uh_cpIYgo85g":
        errors.append("release_contract.channel_id must target 몸의 발명사")
    if release.get("upload_visibility") != "private":
        errors.append("release_contract.upload_visibility must be private")
    if release.get("ai_disclosure_required") is not True:
        errors.append("release_contract.ai_disclosure_required must be true")
    if release.get("final_sync_pass_required") is not True:
        errors.append("release_contract.final_sync_pass_required must be true")

    seen_gap = False
    next_stage = None
    for index, stage in enumerate(stages):
        stage_id = stage.get("id", f"index-{index}")
        status = stage.get("status")
        if status not in contract["allowed_statuses"]:
            errors.append(f"{stage_id}: invalid status {status}")
            continue

        if status != "completed" and next_stage is None:
            next_stage = stage_id
            seen_gap = True
        elif status == "completed" and seen_gap:
            errors.append(f"{stage_id}: completed after a pending/blocked stage")

        if status == "completed":
            lock_rel = stage.get("lock_path")
            expected_lock_hash = stage.get("lock_sha256")
            if not lock_rel or not expected_lock_hash:
                errors.append(f"{stage_id}: completed without lock_path/lock_sha256")
                continue
            lock_path = episode / lock_rel
            if not lock_path.is_file():
                errors.append(f"{stage_id}: missing lock {lock_rel}")
                continue
            actual_lock_hash = sha256(lock_path)
            if actual_lock_hash != expected_lock_hash:
                errors.append(f"{stage_id}: lock SHA-256 mismatch")
            lock = load_json(lock_path)
            if lock.get("stage_id") != stage_id or lock.get("status") != "completed":
                errors.append(f"{stage_id}: lock identity/status mismatch")
            validate_hash_map(episode, lock.get("input_hashes", {}), f"{stage_id} input", errors)
            validate_hash_map(episode, lock.get("output_hashes", {}), f"{stage_id} output", errors)
            for sidecar in stage.get("sidecar_locks", []):
                sidecar_path = episode / sidecar.get("path", "")
                if not sidecar_path.is_file():
                    errors.append(f"{stage_id}: missing sidecar lock {sidecar.get('path')}")
                elif sha256(sidecar_path) != sidecar.get("sha256"):
                    errors.append(f"{stage_id}: sidecar lock SHA-256 mismatch {sidecar.get('path')}")
        elif status == "blocked":
            blocker_rel = stage.get("blocker_path")
            blocker_path = episode / blocker_rel if blocker_rel else None
            if not blocker_path or not blocker_path.is_file():
                errors.append(f"{stage_id}: blocked without a real blocker file")
            else:
                blocker = load_json(blocker_path)
                if blocker.get("stage_id") != stage_id or blocker.get("status") != "blocked":
                    errors.append(f"{stage_id}: blocker identity/status mismatch")

    storyboard_path = episode / "plans" / "storyboard-v6.json"
    generation_path = episode / "plans" / "generation-units-v6.json"
    if storyboard_path.is_file():
        storyboard = load_json(storyboard_path)
        if storyboard.get("script_sha256") != source.get("sha256"):
            errors.append("storyboard script_sha256 does not match source_of_truth")
        if storyboard.get("sentence_count") != source.get("sentence_count"):
            errors.append("storyboard sentence_count does not match source_of_truth")
        if len(storyboard.get("scenes", [])) != source.get("sentence_count"):
            errors.append("storyboard scenes do not have one scene per sentence")
    if generation_path.is_file():
        generation = load_json(generation_path)
        if generation.get("script_sha256") != source.get("sha256"):
            errors.append("generation plan script_sha256 does not match source_of_truth")
        if generation.get("model") != "Omni Flash" or generation.get("mode") != "text_to_video":
            errors.append("generation plan must keep Omni Flash text_to_video as the default mode")
        strategy = generation.get("generation_strategy")
        opening_override = generation.get("opening_mode_override")
        standard_opening = (
            strategy == "first_hook_image_to_video_then_text_to_video"
            and opening_override == "image_to_video_from_approved_textless_thumbnail"
        )
        split_opening_repair = (
            strategy == "split_opening_image_to_video_repair_then_text_to_video"
            and opening_override == "two_eight_second_i2v_sources_with_four_second_harvest_targets"
        )
        if not (standard_opening or split_opening_repair):
            errors.append("generation plan must use the approved first-hook path or a locked two-source opening repair")
        if generation.get("aspect_ratio") != routed_aspect or generation.get("seconds_per_unit") != 8:
            errors.append("generation plan must match routed aspect ratio and use eight-second units")
        units = generation.get("units", [])
        repair = generation.get("opening_repair_contract", {})
        if split_opening_repair:
            required_repair = {
                "status": "approved_after_two_failed_combined_opening_pilots",
                "first_unit_uses_locked_thumbnail": True,
                "second_unit_is_clean_info_i2v": True,
                "batch_generation_remains_blocked_until_both_pass": True,
            }
            for key, value in required_repair.items():
                if repair.get(key) != value:
                    errors.append(f"opening repair contract mismatch: {key}")
            repair_asset = repair.get("second_input_image", "")
            repair_asset_path = episode / repair_asset
            repair_asset_hash = repair.get("second_input_image_sha256")
            if not repair_asset_path.is_file() or sha256(repair_asset_path) != repair_asset_hash:
                errors.append("opening repair clean-info asset missing or SHA-256 mismatch")
            if repair.get("replacement_unit_ids") != ["bdq-v1-u01a", "bdq-v1-u01b"]:
                errors.append("opening repair replacement unit IDs are not locked")

        for index, unit in enumerate(units):
            if unit.get("candidate_count") != 1:
                errors.append(f"{unit.get('unit_id', 'unknown unit')}: candidate_count must be 1")
            if split_opening_repair and index == 1:
                expected_mode = "image_to_video_clean_info_repair"
                if unit.get("input_image") != repair.get("second_input_image"):
                    errors.append(f"{unit.get('unit_id', 'unknown unit')}: clean-info input image mismatch")
                if unit.get("input_image_sha256") != repair.get("second_input_image_sha256"):
                    errors.append(f"{unit.get('unit_id', 'unknown unit')}: clean-info input SHA-256 mismatch")
            else:
                expected_mode = "image_to_video" if index == 0 else "text_to_video"
            if unit.get("mode") != expected_mode:
                errors.append(f"{unit.get('unit_id', 'unknown unit')}: mode must be {expected_mode}")

    thumbnail_lock_path = episode / "locks" / "06-thumbnail.lock.json"
    if thumbnail_lock_path.is_file():
        thumbnail = load_json(thumbnail_lock_path)
        if thumbnail.get("font") != "Gmarket Sans Bold":
            errors.append("thumbnail font must be Gmarket Sans Bold")
        copy_blocks = thumbnail.get("copy_blocks", [])
        visible_count = len(re.sub(r"[\s\W_]", "", "".join(copy_blocks), flags=re.UNICODE))
        if thumbnail.get("layout") != "deep_hook_two_tier" or len(copy_blocks) != 2:
            errors.append("thumbnail must use two-tier deep-hook blocks")
        if visible_count > 10:
            errors.append("thumbnail copy must contain at most 10 visible characters")
        if thumbnail.get("fill_colors") != ["#FFFFFF", "#FFD21F"]:
            errors.append("thumbnail fills must use white setup and yellow keyword")
        if thumbnail.get("outer_stroke_color") != "#FFFFFF" or thumbnail.get("outer_stroke_width_px") != 30:
            errors.append("thumbnail must use the locked 30px white outer stroke")
        if thumbnail.get("inner_stroke_color") != "#111111" or thumbnail.get("inner_stroke_width_px") != 14:
            errors.append("thumbnail must use the locked charcoal inner stroke")
        if thumbnail.get("gold_outline_cloud_forbidden") is not True:
            errors.append("thumbnail must explicitly forbid the rejected gold outline cloud")
        if thumbnail.get("subject_is_primary") is not True:
            errors.append("thumbnail subject must remain the primary visual anchor")
        if thumbnail.get("product_packshot_present") is not False:
            errors.append("thumbnail product packshot must be absent")
        if thumbnail.get("duplicate_unlabeled_bottle_detected") is not False:
            errors.append("duplicate unlabeled bottle must not remain behind the official packshot")
        if thumbnail.get("frame_zero_hold_seconds") != 0.7:
            errors.append("thumbnail frame-zero hold must be 0.7 seconds")
        if thumbnail.get("mobile_visual_qa") != "PASS":
            errors.append("thumbnail mobile visual QA must pass before video generation")

        expected_thumbnail_assets = {
            production.get("opening_textless_asset", ""): production.get("opening_textless_asset_sha256"),
            production.get("thumbnail_final_asset", ""): production.get("thumbnail_final_asset_sha256"),
            production.get("thumbnail_mobile_qa_asset", ""): production.get("thumbnail_mobile_qa_asset_sha256"),
        }
        valid_thumbnail_assets = {}
        for relative, expected_hash in expected_thumbnail_assets.items():
            if not relative or not expected_hash:
                errors.append(f"missing locked thumbnail asset hash for {relative}")
                continue
            valid_thumbnail_assets[relative] = expected_hash
            if thumbnail.get("output_hashes", {}).get(relative) != expected_hash:
                errors.append(f"thumbnail lock does not own the current asset hash: {relative}")
        validate_hash_map(episode, valid_thumbnail_assets, "thumbnail hard gate", errors)

        visual_identity_path = episode / "locks" / "06-thumbnail-visual-identity.lock.json"
        if not visual_identity_path.is_file():
            errors.append("missing thumbnail visual identity lock")
        else:
            visual_identity = load_json(visual_identity_path)
            if visual_identity.get("verdict") != "PASS" or visual_identity.get("manual_visual_review_completed") is not True:
                errors.append("thumbnail visual identity lock must be manually reviewed PASS")

        if generation_path.is_file():
            generation_units = load_json(generation_path).get("units", [])
            opening = generation_units[0] if generation_units else {}
            expected_opening_path = production.get("opening_textless_asset")
            expected_opening_hash = production.get("opening_textless_asset_sha256")
            if opening.get("input_image") != expected_opening_path or opening.get("input_image_sha256") != expected_opening_hash:
                errors.append("first Flow unit must use the locked textless thumbnail image and SHA-256")
    elif any(stage.get("id") in {"07_generation_plan", "08_pilot_generation"} and stage.get("status") == "completed" for stage in stages):
        errors.append("thumbnail hard gate must be completed before generation planning or Flow")

    return errors, {"episode": str(episode), "next_stage": next_stage, "stage_count": len(stages)}


def validate_skill(errors: list[str]) -> None:
    skill_root = REPO_ROOT / ".codex" / "skills" / "timemedic"
    skill_path = skill_root / "SKILL.md"
    if not skill_path.is_file():
        errors.append("missing .codex/skills/timemedic/SKILL.md")
        return
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "name: timemedic" not in text[:500]:
        errors.append("timemedic SKILL.md frontmatter is invalid")
    for reference in re.findall(r"\(references/([^)]+\.md)\)", text):
        if not (skill_root / "references" / reference).is_file():
            errors.append(f"missing referenced skill file: {reference}")


def validate_topic_queue(errors: list[str]) -> None:
    config_root = REPO_ROOT / "config"
    source_path = config_root / "topic-source-100.txt"
    catalog_path = config_root / "topic-catalog-100.json"
    schedule_path = config_root / "50-day-two-video-schedule.json"
    for path in (source_path, catalog_path, schedule_path):
        if not path.is_file():
            errors.append(f"missing topic queue source: {path.relative_to(REPO_ROOT)}")
    if errors:
        return

    catalog = load_json(catalog_path)
    schedule = load_json(schedule_path)
    topics = catalog.get("topics", [])
    expected_ids = [f"topic-{index:03d}" for index in range(1, 101)]
    actual_ids = [topic.get("topic_id") for topic in topics]
    if len(topics) != 100 or actual_ids != expected_ids:
        errors.append("topic catalog must preserve exactly topic-001 through topic-100 in order")
    if catalog.get("source", {}).get("sha256", "").lower() != sha256(source_path):
        errors.append("topic source SHA-256 differs from catalog source lock")
    if schedule.get("topic_catalog_sha256", "").lower() != sha256(catalog_path):
        errors.append("schedule topic_catalog_sha256 differs from current catalog")
    days = schedule.get("days", [])
    if schedule.get("total_topics") != 100 or schedule.get("total_days") != 50 or len(days) != 50:
        errors.append("daily schedule must contain 100 topics across 50 days")
    scheduled_ids = [lane.get("topic_id") for day in days for lane in day.get("lanes", [])]
    if scheduled_ids != expected_ids:
        errors.append("daily schedule must assign the 100 topics in original numeric order")


def validate_repository() -> tuple[list[str], list[dict]]:
    errors: list[str] = []
    summaries: list[dict] = []
    validate_skill(errors)
    validate_topic_queue(errors)
    for pipeline_path in sorted((REPO_ROOT / "episodes").glob("*/pipeline.json")):
        episode_errors, summary = validate_episode(pipeline_path.parent)
        errors.extend(episode_errors)
        summaries.append(summary)
    if not summaries:
        errors.append("no episode pipeline.json files found")

    secret_pattern = re.compile(r"(?:sk_[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{25,})")
    excluded_scan_parts = {".git", ".local-tools", "node_modules", "__pycache__"}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded_scan_parts for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        if secret_pattern.search(content):
            errors.append(f"possible secret committed: {path.relative_to(REPO_ROOT)}")
    return errors, summaries


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_group = validate_parser.add_mutually_exclusive_group(required=True)
    validate_group.add_argument("--episode", type=Path)
    validate_group.add_argument("--all", action="store_true")
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--episode", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "status":
        errors, summary = validate_episode(args.episode.resolve())
        print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors, **summary}, ensure_ascii=False, indent=2))
        return 0 if not errors else 1

    if args.all:
        errors, summaries = validate_repository()
    else:
        errors, summary = validate_episode(args.episode.resolve())
        summaries = [summary]
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors, "episodes": summaries}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
