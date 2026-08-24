#!/usr/bin/env python3
"""Validate and create visual QA artifacts for the rendered Black Death film."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "black-death-quarantine"
VIDEO = EPISODE / "renders" / "black-death-v1-final.mp4"
TIMELINE = ROOT / "video" / "src" / "data" / "black-death-v1-timeline.json"
SEMANTIC = ROOT / "video" / "src" / "data" / "black-death-v1-semantic.json"
QA = EPISODE / "qa" / "stage14"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main() -> int:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    semantic = json.loads(SEMANTIC.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not VIDEO.exists():
        raise FileNotFoundError(VIDEO)
    probe = json.loads(
        run(
            [
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", str(VIDEO),
            ]
        ).stdout
    )
    video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
    audio_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)
    duration = float(probe["format"]["duration"])
    expected_duration = timeline["total_frames"] / timeline["fps"]
    if abs(duration - expected_duration) > 0.08:
        errors.append(f"duration mismatch: {duration:.6f} vs {expected_duration:.6f}")
    if not video_stream or video_stream["codec_name"] != "h264":
        errors.append("missing H.264 video stream")
    elif int(video_stream["width"]) != 1920 or int(video_stream["height"]) != 1080:
        errors.append("video resolution is not 1920x1080")
    if not audio_stream or audio_stream["codec_name"] != "aac":
        errors.append("missing AAC audio stream")
    if timeline["scene_count"] != 50 or timeline["premature_scene_cut_count"] != 0:
        errors.append("scene ownership contract failed")
    if len(semantic["caption_pages"]) < 50:
        errors.append("caption page coverage is incomplete")
    if {page["sentence_id"] for page in semantic["caption_pages"]} != {f"s{i:02d}" for i in range(1, 51)}:
        errors.append("caption sentence coverage is incomplete")
    for scene in timeline["scenes"]:
        if scene["display_end_frame"] < scene["sentence_end_frame"]:
            errors.append(f"premature cut: {scene['sentence_id']}")

    QA.mkdir(parents=True, exist_ok=True)
    frame_zero = QA / "frame-zero-rendered.png"
    contact = QA / "sentence-midpoints-contact-5x10.jpg"
    run(["ffmpeg", "-y", "-ss", "0", "-i", str(VIDEO), "-frames:v", "1", str(frame_zero)])

    midpoint_frames = [max(scene["start_frame"], min(scene["display_end_frame"] - 1, (scene["start_frame"] + scene["display_end_frame"]) // 2)) for scene in timeline["scenes"]]
    select = "+".join(f"eq(n\\,{frame})" for frame in midpoint_frames)
    run(
        [
            "ffmpeg", "-y", "-i", str(VIDEO), "-vf",
            f"select='{select}',scale=384:216,tile=5x10",
            "-vsync", "0", "-frames:v", "1", str(contact),
        ]
    )

    psnr = run(
        [
            "ffmpeg", "-i", str(frame_zero), "-i", str(EPISODE / "assets" / "thumbnail-v1-landscape.png"),
            "-lavfi", "psnr", "-f", "null", "-",
        ]
    ).stderr
    match = re.search(r"average:([0-9.]+)", psnr)
    frame_zero_psnr = float(match.group(1)) if match else 0.0
    if frame_zero_psnr < 28.0:
        errors.append(f"frame zero does not match locked thumbnail closely enough: PSNR {frame_zero_psnr:.2f}")

    output = {
        "schema_version": "body-invention.final-qa.v1",
        "episode_id": "black-death-quarantine",
        "stage_id": "14_final_qa",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "render_path": "renders/black-death-v1-final.mp4",
        "render_sha256": sha256(VIDEO),
        "render_bytes": VIDEO.stat().st_size,
        "duration_seconds": duration,
        "expected_duration_seconds": expected_duration,
        "video_codec": video_stream["codec_name"] if video_stream else None,
        "audio_codec": audio_stream["codec_name"] if audio_stream else None,
        "width": int(video_stream["width"]) if video_stream else None,
        "height": int(video_stream["height"]) if video_stream else None,
        "fps": timeline["fps"],
        "scene_count": timeline["scene_count"],
        "premature_scene_cut_count": timeline["premature_scene_cut_count"],
        "caption_page_count": len(semantic["caption_pages"]),
        "semantic_event_count": len(semantic["semantic_events"]),
        "frame_zero_psnr": round(frame_zero_psnr, 3),
        "frame_zero_path": "qa/stage14/frame-zero-rendered.png",
        "frame_zero_sha256": sha256(frame_zero),
        "contact_sheet_path": "qa/stage14/sentence-midpoints-contact-5x10.jpg",
        "contact_sheet_sha256": sha256(contact),
        "completed_at": datetime.now().astimezone().isoformat(),
    }
    (QA / "final-qa-v1.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
