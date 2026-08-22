#!/usr/bin/env python3
import argparse
import copy
import json
import math
import re
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(data):
    errors = []
    fps = data.get("fps")
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or fps <= 0:
        errors.append("fps must be a positive number")
        fps = 30
    tolerance_ms = math.ceil(1000 / fps)

    canvas = data.get("canvas", {})
    if canvas.get("width") != 1080 or canvas.get("height") != 1920:
        errors.append("canvas must be exactly 1080x1920")

    tts_ms = data.get("tts_duration_ms")
    video_frames = data.get("video_duration_frames")
    if not isinstance(tts_ms, int) or isinstance(tts_ms, bool) or tts_ms <= 0:
        errors.append("tts_duration_ms must be a positive integer")
    if not isinstance(video_frames, int) or isinstance(video_frames, bool) or video_frames <= 0:
        errors.append("video_duration_frames must be a positive integer")
    if isinstance(tts_ms, int) and isinstance(video_frames, int):
        expected_frames = round((tts_ms / 1000) * fps)
        if abs(video_frames - expected_frames) > 1:
            errors.append(
                f"video/TTS duration mismatch: video={video_frames} frames, expected={expected_frames}, tolerance=1"
            )

    style = data.get("caption_style", {})
    expected_style = {
        "font_family": "Gmarket Sans Bold",
        "font_size_px": 100,
        "stroke_width_px": 30,
        "stroke_color": "#000000",
        "shadow_required": True,
        "anchor_x_px": 540,
        "anchor_y_px": 1200,
        "anchor_y_ratio": 0.625,
        "block_anchor": "center",
        "horizontal_align": "center",
    }
    for key, expected in expected_style.items():
        if style.get(key) != expected:
            errors.append(f"caption_style.{key} must be {expected!r}")

    timing_source = data.get("caption_timing_source")
    if timing_source not in {"elevenlabs_word_alignment", "forced_word_alignment"}:
        errors.append("caption_timing_source must be real ElevenLabs or forced word alignment")
    if data.get("caption_even_split") is not False:
        errors.append("caption_even_split must be false")

    tokens = data.get("word_tokens")
    if not isinstance(tokens, list) or not tokens:
        errors.append("word_tokens must be a non-empty array")
        tokens = []
    previous_start = -1
    for index, token in enumerate(tokens):
        label = f"word_tokens[{index}]"
        if not isinstance(token.get("sentence_id"), str) or not token.get("sentence_id", "").strip():
            errors.append(f"{label}.sentence_id is required")
        if not isinstance(token.get("text"), str) or not token.get("text", "").strip():
            errors.append(f"{label}.text is required")
        start = token.get("start_ms")
        end = token.get("end_ms")
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            errors.append(f"{label} must have integer start_ms < end_ms")
            continue
        if start < previous_start:
            errors.append(f"{label} is out of chronological order")
        if isinstance(tts_ms, int) and end > tts_ms + tolerance_ms:
            errors.append(f"{label}.end_ms exceeds TTS by more than one frame")
        previous_start = start

    sentences = data.get("sentence_alignment")
    if not isinstance(sentences, list) or not sentences:
        errors.append("sentence_alignment must be a non-empty array")
        sentences = []
    sentence_map = {}
    previous_end = 0
    for index, sentence in enumerate(sentences):
        label = f"sentence_alignment[{index}]"
        sentence_id = sentence.get("sentence_id")
        start = sentence.get("start_ms")
        end = sentence.get("end_ms")
        if not isinstance(sentence_id, str) or not sentence_id.strip():
            errors.append(f"{label}.sentence_id is required")
        elif sentence_id in sentence_map:
            errors.append(f"{label}.sentence_id must be unique")
        else:
            sentence_map[sentence_id] = sentence
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            errors.append(f"{label} must have integer start_ms < end_ms")
            continue
        if index == 0 and start != 0:
            errors.append("first sentence_alignment window must start at 0ms")
        if index > 0 and start != previous_end:
            errors.append(f"{label} must start exactly when the previous sentence window ends")
        previous_end = end
    if sentences and isinstance(tts_ms, int) and abs(sentences[-1].get("end_ms", -999999) - tts_ms) > tolerance_ms:
        errors.append("last sentence_alignment window must end within one frame of final TTS")

    for index, token in enumerate(tokens):
        sentence = sentence_map.get(token.get("sentence_id"))
        if sentence is None:
            errors.append(f"word_tokens[{index}].sentence_id has no sentence_alignment window")
            continue
        start = token.get("start_ms")
        end = token.get("end_ms")
        if isinstance(start, int) and start < sentence.get("start_ms", 0) - tolerance_ms:
            errors.append(f"word_tokens[{index}] starts before its sentence window")
        if isinstance(end, int) and end > sentence.get("end_ms", 0) + tolerance_ms:
            errors.append(f"word_tokens[{index}] ends after its sentence window")

    scenes = data.get("scene_windows")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scene_windows must be a non-empty array")
        scenes = []
    previous_end = 0
    seen_scene_ids = set()
    for index, scene in enumerate(scenes):
        label = f"scene_windows[{index}]"
        start = scene.get("start_ms")
        end = scene.get("end_ms")
        sentence_id = scene.get("sentence_id")
        if not sentence_id:
            errors.append(f"{label}.sentence_id is required")
        elif sentence_id in seen_scene_ids:
            errors.append(f"{label}.sentence_id must be unique")
        else:
            seen_scene_ids.add(sentence_id)
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            errors.append(f"{label} must have integer start_ms < end_ms")
            continue
        if index == 0 and start != 0:
            errors.append("first scene must start at 0ms")
        if index > 0 and start != previous_end:
            errors.append(f"{label} must start exactly when the previous sentence ends")
        sentence = sentence_map.get(sentence_id)
        if sentence is None:
            errors.append(f"{label}.sentence_id has no sentence_alignment window")
        elif isinstance(start, int) and isinstance(end, int):
            if abs(start - sentence.get("start_ms", start)) > tolerance_ms:
                errors.append(f"{label}.start_ms differs from sentence_alignment by more than one frame")
            if abs(end - sentence.get("end_ms", end)) > tolerance_ms:
                errors.append(f"{label}.end_ms differs from sentence_alignment by more than one frame")
            if index < len(sentences) and sentence_id != sentences[index].get("sentence_id"):
                errors.append(f"{label} must preserve sentence_alignment order")
        previous_end = end
    if sentences and len(scenes) != len(sentences):
        errors.append("scene_windows must contain exactly one window per sentence_alignment entry")
    if scenes and isinstance(tts_ms, int) and abs(scenes[-1].get("end_ms", -999999) - tts_ms) > tolerance_ms:
        errors.append("last scene must end within one frame of final TTS")

    caption_pages = data.get("caption_pages")
    if not isinstance(caption_pages, list) or not caption_pages:
        errors.append("caption_pages must be a non-empty array")
        caption_pages = []
    expected_token_index = 0
    previous_caption_end = -1
    for index, page in enumerate(caption_pages):
        label = f"caption_pages[{index}]"
        sentence_id = page.get("sentence_id")
        start = page.get("start_ms")
        end = page.get("end_ms")
        token_start = page.get("token_start_index")
        token_end = page.get("token_end_index")
        if not isinstance(page.get("text"), str) or not page.get("text", "").strip():
            errors.append(f"{label}.text is required")
        if sentence_id not in sentence_map:
            errors.append(f"{label}.sentence_id has no sentence_alignment window")
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            errors.append(f"{label} must have integer start_ms < end_ms")
            continue
        if start < previous_caption_end:
            errors.append(f"{label} overlaps the previous caption page")
        previous_caption_end = end
        if not isinstance(token_start, int) or not isinstance(token_end, int) or token_end < token_start:
            errors.append(f"{label} must have integer token_start_index <= token_end_index")
            continue
        if token_start != expected_token_index:
            errors.append(f"{label}.token_start_index must be {expected_token_index} to avoid missing or duplicate words")
        if token_end >= len(tokens):
            errors.append(f"{label}.token_end_index exceeds word_tokens")
            continue
        selected_tokens = tokens[token_start : token_end + 1]
        if any(token.get("sentence_id") != sentence_id for token in selected_tokens):
            errors.append(f"{label} may only own tokens from the same sentence_id")
        if selected_tokens:
            if abs(start - selected_tokens[0].get("start_ms", start)) > tolerance_ms:
                errors.append(f"{label}.start_ms differs from its first word by more than one frame")
            if abs(end - selected_tokens[-1].get("end_ms", end)) > tolerance_ms:
                errors.append(f"{label}.end_ms differs from its last word by more than one frame")
        sentence = sentence_map.get(sentence_id)
        if sentence and (start < sentence.get("start_ms", start) - tolerance_ms or end > sentence.get("end_ms", end) + tolerance_ms):
            errors.append(f"{label} exceeds its sentence window")
        expected_token_index = token_end + 1
    if tokens and expected_token_index != len(tokens):
        errors.append("caption_pages must cover every word token exactly once")

    sync_review = data.get("sync_review", {})
    if sync_review.get("status") != "PASS":
        errors.append("sync_review.status must be PASS")
    correction_rounds = sync_review.get("correction_rounds")
    if not isinstance(correction_rounds, int) or isinstance(correction_rounds, bool) or correction_rounds < 0:
        errors.append("sync_review.correction_rounds must be a non-negative integer")
    if correction_rounds and sync_review.get("corrected_render_verified") is not True:
        errors.append("sync_review.corrected_render_verified must be true after any correction")
    for field in ("final_render_verified", "caption_text_identity_pass", "visual_spot_check_pass", "audio_spot_check_pass"):
        if sync_review.get(field) is not True:
            errors.append(f"sync_review.{field} must be true")
    for field in ("premature_scene_cut_count", "missing_caption_token_count", "overlapping_caption_page_count"):
        if sync_review.get(field) != 0:
            errors.append(f"sync_review.{field} must be 0")
    for field in ("max_scene_boundary_error_frames", "max_caption_boundary_error_frames"):
        value = sync_review.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or value > 1:
            errors.append(f"sync_review.{field} must be between 0 and 1")
    artifact_hashes = sync_review.get("artifact_sha256", {})
    for field in ("final_video", "final_tts", "alignment", "caption_manifest", "thumbnail", "frame_zero_capture"):
        if not SHA256_RE.fullmatch(str(artifact_hashes.get(field, ""))):
            errors.append(f"sync_review.artifact_sha256.{field} must be 64-hex")

    thumbnail = data.get("thumbnail_contract", {})
    if thumbnail.get("status") != "PASS":
        errors.append("thumbnail_contract.status must be PASS")
    if thumbnail.get("frame_zero_visual_match") is not True:
        errors.append("thumbnail_contract.frame_zero_visual_match must be true")
    if thumbnail.get("display_start_frame") != 0:
        errors.append("thumbnail_contract.display_start_frame must be 0")
    if not isinstance(thumbnail.get("recognition_hold_end_ms"), int) or thumbnail.get("recognition_hold_end_ms", 0) < 700:
        errors.append("thumbnail_contract.recognition_hold_end_ms must be at least 700")
    if thumbnail.get("first_two_seconds_discontinuity_count") != 0:
        errors.append("thumbnail_contract.first_two_seconds_discontinuity_count must be 0")
    if thumbnail.get("added_silent_intro") is not False:
        errors.append("thumbnail_contract.added_silent_intro must be false")
    for field in ("thumbnail_sha256", "frame_zero_capture_sha256"):
        if not SHA256_RE.fullmatch(str(thumbnail.get(field, ""))):
            errors.append(f"thumbnail_contract.{field} must be 64-hex")

    lock = data.get("reference_grammar_lock", {})
    if lock.get("status") != "PASS":
        errors.append("reference_grammar_lock.status must be PASS")
    if not lock.get("source_analysis_paths"):
        errors.append("reference_grammar_lock.source_analysis_paths must be non-empty")
    if not lock.get("adopted_high_level_rules"):
        errors.append("reference_grammar_lock.adopted_high_level_rules must be non-empty")
    if lock.get("copied_specific_scene") is not False:
        errors.append("reference_grammar_lock.copied_specific_scene must be false")
    if not lock.get("generation_unit_ids"):
        errors.append("reference_grammar_lock.generation_unit_ids must be non-empty")
    for field in ("script_sha256", "storyboard_sha256"):
        if not SHA256_RE.fullmatch(str(lock.get(field, ""))):
            errors.append(f"reference_grammar_lock.{field} must be 64-hex")

    return errors


def self_test():
    sample = {
        "fps": 30,
        "canvas": {"width": 1080, "height": 1920},
        "tts_duration_ms": 1000,
        "video_duration_frames": 30,
        "caption_style": {
            "font_family": "Gmarket Sans Bold",
            "font_size_px": 100,
            "stroke_width_px": 30,
            "stroke_color": "#000000",
            "shadow_required": True,
            "anchor_x_px": 540,
            "anchor_y_px": 1200,
            "anchor_y_ratio": 0.625,
            "block_anchor": "center",
            "horizontal_align": "center",
        },
        "caption_timing_source": "forced_word_alignment",
        "caption_even_split": False,
        "word_tokens": [
            {"sentence_id": "S01", "text": "테스", "start_ms": 0, "end_ms": 450},
            {"sentence_id": "S01", "text": "트", "start_ms": 500, "end_ms": 1000},
        ],
        "sentence_alignment": [{"sentence_id": "S01", "start_ms": 0, "end_ms": 1000}],
        "scene_windows": [{"sentence_id": "S01", "start_ms": 0, "end_ms": 1000}],
        "caption_pages": [
            {
                "sentence_id": "S01",
                "text": "테스트",
                "start_ms": 0,
                "end_ms": 1000,
                "token_start_index": 0,
                "token_end_index": 1,
            }
        ],
        "sync_review": {
            "status": "PASS",
            "correction_rounds": 0,
            "corrected_render_verified": False,
            "final_render_verified": True,
            "caption_text_identity_pass": True,
            "visual_spot_check_pass": True,
            "audio_spot_check_pass": True,
            "premature_scene_cut_count": 0,
            "missing_caption_token_count": 0,
            "overlapping_caption_page_count": 0,
            "max_scene_boundary_error_frames": 0,
            "max_caption_boundary_error_frames": 0,
            "artifact_sha256": {
                "final_video": "c" * 64,
                "final_tts": "d" * 64,
                "alignment": "e" * 64,
                "caption_manifest": "f" * 64,
                "thumbnail": "1" * 64,
                "frame_zero_capture": "2" * 64,
            },
        },
        "thumbnail_contract": {
            "status": "PASS",
            "frame_zero_visual_match": True,
            "display_start_frame": 0,
            "recognition_hold_end_ms": 700,
            "first_two_seconds_discontinuity_count": 0,
            "added_silent_intro": False,
            "thumbnail_sha256": "1" * 64,
            "frame_zero_capture_sha256": "2" * 64,
        },
        "reference_grammar_lock": {
            "status": "PASS",
            "source_analysis_paths": ["reference.md"],
            "adopted_high_level_rules": ["multishot"],
            "copied_specific_scene": False,
            "generation_unit_ids": ["V01"],
            "script_sha256": "a" * 64,
            "storyboard_sha256": "b" * 64,
        },
    }
    errors = validate(sample)
    if errors:
        raise RuntimeError("self-test valid sample failed: " + "; ".join(errors))

    invalid_cases = []
    wrong_font = copy.deepcopy(sample)
    wrong_font["caption_style"]["font_size_px"] = 175
    invalid_cases.append(("wrong caption font size", wrong_font))

    wrong_scene = copy.deepcopy(sample)
    wrong_scene["scene_windows"][0]["end_ms"] = 850
    invalid_cases.append(("scene not owned by final TTS sentence", wrong_scene))

    wrong_caption = copy.deepcopy(sample)
    wrong_caption["caption_pages"][0]["start_ms"] = 120
    invalid_cases.append(("caption not aligned to first owned word", wrong_caption))

    wrong_thumbnail = copy.deepcopy(sample)
    wrong_thumbnail["thumbnail_contract"]["frame_zero_visual_match"] = False
    invalid_cases.append(("thumbnail not visible at frame zero", wrong_thumbnail))

    for label, invalid_sample in invalid_cases:
        if not validate(invalid_sample):
            raise RuntimeError(f"self-test invalid case was not rejected: {label}")
    print(json.dumps({"valid": True, "self_test": "PASS"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.contract is None:
        parser.error("contract is required unless --self-test is used")
    try:
        data = load_json(args.contract)
    except Exception as exc:
        print(json.dumps({"valid": False, "errors": [f"JSON read error: {exc}"]}, ensure_ascii=False, indent=2))
        return 1
    errors = validate(data)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
