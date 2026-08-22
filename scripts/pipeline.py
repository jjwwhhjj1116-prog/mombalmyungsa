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
        "aspect_ratio": "9:16",
        "seconds_per_generation_unit": 8,
        "candidates_per_unit": 1,
        "voice_provider": "ElevenLabs",
        "voice_take": "Take 2",
        "voice_model": "eleven_v3",
        "one_sentence_one_scene": True,
        "final_tts_is_only_timeline": True,
        "caption_font": "Gmarket Sans Bold",
        "caption_size_px": 100,
        "caption_vertical_slot_of_16": 10,
        "thumbnail_is_frame_zero": True,
        "thumbnail_font": "Gmarket Sans Bold",
        "thumbnail_font_size_px": 175,
        "thumbnail_stroke_px": 30,
    }
    for field, expected in expected_production.items():
        if production.get(field) != expected:
            errors.append(f"production_contract.{field} must be {expected!r}")

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
            errors.append("generation plan must use Omni Flash text_to_video")
        if generation.get("aspect_ratio") != "9:16" or generation.get("seconds_per_unit") != 8:
            errors.append("generation plan must use 9:16 eight-second units")
        for unit in generation.get("units", []):
            if unit.get("candidate_count") != 1:
                errors.append(f"{unit.get('unit_id', 'unknown unit')}: candidate_count must be 1")

    thumbnail_lock_path = episode / "locks" / "06-thumbnail.lock.json"
    if thumbnail_lock_path.is_file():
        thumbnail = load_json(thumbnail_lock_path)
        if thumbnail.get("font") != "Gmarket Sans Bold":
            errors.append("thumbnail font must be Gmarket Sans Bold")
        if thumbnail.get("font_size_px") != 175 or thumbnail.get("stroke_width_px") != 30:
            errors.append("thumbnail typography must be 175px with 30px stroke")
        if thumbnail.get("frame_zero_hold_seconds") != 0.7:
            errors.append("thumbnail frame-zero hold must be 0.7 seconds")

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


def validate_repository() -> tuple[list[str], list[dict]]:
    errors: list[str] = []
    summaries: list[dict] = []
    validate_skill(errors)
    for pipeline_path in sorted((REPO_ROOT / "episodes").glob("*/pipeline.json")):
        episode_errors, summary = validate_episode(pipeline_path.parent)
        errors.extend(episode_errors)
        summaries.append(summary)
    if not summaries:
        errors.append("no episode pipeline.json files found")

    secret_pattern = re.compile(r"(?:sk_[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{25,})")
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
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
