#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


def probe(path: Path) -> dict:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=codec_type,width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    args = parser.parse_args()
    episode = args.episode.resolve()
    repo = episode.parents[1]
    plan_path = episode / "plans" / "tts-owned-edit-v6.json"
    timeline_path = repo / "video" / "src" / "data" / "gas-hwalmyeongsu-v6-timeline.json"
    video_path = episode / "renders" / "gas-hwalmyeongsu-v6-rough.mp4"
    errors = []

    if not plan_path.exists() or not timeline_path.exists() or not video_path.exists():
        missing = [str(path) for path in (plan_path, timeline_path, video_path) if not path.exists()]
        print(json.dumps({"status": "FAIL", "errors": [f"missing outputs: {missing}"]}, ensure_ascii=False, indent=2))
        return 1

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    if plan != timeline:
        errors.append("render timeline must be byte-semantically identical to the stage12 plan")
    scenes = plan.get("scenes", [])
    if len(scenes) != 37 or plan.get("scene_count") != 37:
        errors.append("stage12 must contain exactly 37 sentence-owned scenes")
    if plan.get("total_frames") != 4566 or plan.get("fps") != 30:
        errors.append("timeline must be 4566 frames at 30 fps")
    if plan.get("frame_zero_frames") != 21:
        errors.append("frame zero must hold for exactly 21 frames")
    if plan.get("premature_scene_cut_count") != 0:
        errors.append("premature_scene_cut_count must remain zero")
    for index, scene in enumerate(scenes):
        sid = f"s{index + 1:02d}"
        if scene.get("sentence_id") != sid:
            errors.append(f"scene order mismatch at {sid}")
            continue
        if scene.get("caption_end_frame") != scene.get("sentence_end_frame"):
            errors.append(f"{sid}: caption must end on its sentence boundary")
        if scene.get("sentence_end_frame", 0) > scene.get("display_end_frame", -1):
            errors.append(f"{sid}: scene cannot end before its spoken sentence")
        if index + 1 < len(scenes) and scene.get("display_end_frame") != scenes[index + 1].get("start_frame"):
            errors.append(f"{sid}: display must bridge only to the next sentence start")
        if scene.get("premature_next_meaning_allowed") is not False:
            errors.append(f"{sid}: next-sentence meaning may not appear early")
        if scene.get("native_audio_decision") != "replace":
            errors.append(f"{sid}: unverified Flow native audio must remain replaced")
    mask_ids = [scene.get("sentence_id") for scene in scenes if scene.get("u12_release_blocking_mask")]
    if mask_ids != ["s32"]:
        errors.append("the tracked blank-sign repair must be restricted to s32")
    s33 = next((scene for scene in scenes if scene.get("sentence_id") == "s33"), {})
    if s33.get("public_source") != "gas/vit-v6-u13.mp4" or s33.get("source_in") != 5.2 or s33.get("source_out") != 7.4:
        errors.append("s33 must use the visually approved u13 bubble-reflection window")

    media = probe(video_path)
    video_stream = next((stream for stream in media.get("streams", []) if stream.get("codec_type") == "video"), {})
    if (video_stream.get("width"), video_stream.get("height"), video_stream.get("r_frame_rate")) != (1080, 1920, "30/1"):
        errors.append("rough cut must render at 1080x1920 and 30 fps")
    duration = float(media.get("format", {}).get("duration", 0))
    expected_duration = plan.get("total_frames", 0) / plan.get("fps", 1)
    if abs(duration - expected_duration) > 0.1:
        errors.append(f"render duration drift is too large: {duration:.6f}s vs {expected_duration:.6f}s")

    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "duration_seconds": duration, "video": str(video_path)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
