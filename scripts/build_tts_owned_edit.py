#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    args = parser.parse_args()
    episode = args.episode.resolve()
    repo = episode.parents[1]
    alignment = json.loads((episode / "tts" / "gas-hwalmyeongsu-v6-alignment.json").read_text(encoding="utf-8"))
    harvest = json.loads((episode / "plans" / "clip-harvest-v6.json").read_text(encoding="utf-8"))
    harvest_by_id = {row["sentence_id"]: row for row in harvest["sentences"]}
    fps = 30
    total_frames = round(float(alignment["audio_duration_seconds"]) * fps)
    frame_zero_frames = round(0.7 * fps)
    scenes = []
    for i, sentence in enumerate(alignment["sentence_alignment"]):
        sid = sentence["sentence_id"]
        row = harvest_by_id[sid]
        start_frame = round(float(sentence["start"]) * fps)
        sentence_end_frame = round(float(sentence["end"]) * fps)
        display_end_frame = round(float(alignment["sentence_alignment"][i + 1]["start"]) * fps) if i + 1 < len(alignment["sentence_alignment"]) else total_frames
        display_frames = max(1, display_end_frame - start_frame)
        source_seconds = float(row["source_out"]) - float(row["source_in"])
        usable_display_frames = display_frames - frame_zero_frames if sid == "s01" else display_frames
        playback_rate = source_seconds / max(1 / fps, usable_display_frames / fps)
        source_name = Path(row["source_path"]).name
        scenes.append(
            {
                "sentence_id": sid,
                "text": sentence["text"],
                "start_frame": start_frame,
                "sentence_end_frame": sentence_end_frame,
                "display_end_frame": display_end_frame,
                "caption_start_frame": start_frame,
                "caption_end_frame": sentence_end_frame,
                "source_in": row["source_in"],
                "source_out": row["source_out"],
                "source_sha256": row["source_sha256"],
                "public_source": f"gas/{source_name}",
                "playback_rate": round(playback_rate, 6),
                "camera_policy": "preserve_flow_native_camera_no_per_sentence_reset",
                "meaning_target": row["meaning_target"],
                "motion_carrier": row["motion_carrier"],
                "native_audio_decision": row["native_audio_decision"],
                "u12_release_blocking_mask": sid == "s32" and row["unit_id"] == "vit-v6-u12",
                "premature_next_meaning_allowed": False,
            }
        )
    output = {
        "schema_version": "body-invention.tts-owned-edit.v1",
        "episode_id": "gas-hwalmyeongsu",
        "stage_id": "12_tts_owned_edit",
        "status": "planned",
        "fps": fps,
        "width": 1080,
        "height": 1920,
        "total_frames": total_frames,
        "audio_duration_seconds": alignment["audio_duration_seconds"],
        "frame_zero_frames": frame_zero_frames,
        "frame_zero_asset": "assets/frame-zero-v20-owner-red-box-final.png",
        "audio_asset": "tts/gas-hwalmyeongsu-v6-elevenlabs-take2.mp3",
        "sentence_alignment_sha256": sha256(episode / "tts" / "gas-hwalmyeongsu-v6-alignment.json"),
        "scene_count": len(scenes),
        "premature_scene_cut_count": 0,
        "native_audio_policy": "all_source_audio_muted_and_replaced_later",
        "u12_generated_text_repair": "three tracked blank pharmacy shelf signs restricted to sentence s32",
        "scenes": scenes,
    }
    plan_path = episode / "plans" / "tts-owned-edit-v6.json"
    data_path = repo / "video" / "src" / "data" / "gas-hwalmyeongsu-v6-timeline.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    plan_path.write_text(payload, encoding="utf-8")
    data_path.write_text(payload, encoding="utf-8")
    print(json.dumps({"status": "PASS", "total_frames": total_frames, "scene_count": len(scenes), "min_playback_rate": min(s["playback_rate"] for s in scenes)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
