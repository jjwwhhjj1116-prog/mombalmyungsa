#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    validator = Path(__file__).with_name("validate_episode.py")
    validation = subprocess.run(
        [sys.executable, str(validator), str(args.episode)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if validation.stdout:
        print(validation.stdout, end="")
    if validation.returncode != 0:
        return validation.returncode

    data = json.loads(args.episode.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)

    flattened_shots = [
        (beat, shot)
        for beat in data["beats"]
        for shot in beat["direction_track"]
    ]
    script_ref = data.get("approved_script_path")
    script_candidates = []
    if script_ref:
        script_candidates.extend([
            Path.cwd() / script_ref,
            args.episode.parent / script_ref,
        ])
    script_path = next((candidate for candidate in script_candidates if candidate.exists()), None)
    if script_path is None:
        print(json.dumps({"built": False, "error": "approved_script_path could not be resolved"}, ensure_ascii=False, indent=2))
        return 1
    sentence_lines = [
        line.strip()
        for line in script_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(sentence_lines) != len(flattened_shots):
        print(json.dumps({
            "built": False,
            "error": "one-sentence-one-scene mismatch",
            "sentences": len(sentence_lines),
            "shots": len(flattened_shots),
        }, ensure_ascii=False, indent=2))
        return 1

    director_lines = [f"# {data.get('title', '몸의 발명사')} — 영상 연출본", ""]
    clean_lines = []
    eleven_lines = []
    events = []
    sound_events = []
    sound_by_beat = {}
    for sound in data.get("sound_events", []):
        sound_by_beat.setdefault(sound["beat_id"], []).append(sound)
    sound_sheet_lines = [f"# {data.get('title', '몸의 발명사')} — 사운드 큐시트", ""]

    sentence_index = 0
    for beat in data["beats"]:
        beat_narration = beat["narration"].strip()
        for shot in beat["direction_track"]:
            narration = sentence_lines[sentence_index]
            sentence_index += 1
            tag = str(shot.get("tts_tag", beat.get("tts_tag", ""))).strip()
            emotion = str(shot.get("emotion", beat["emotion"])).strip()
            subject_motion = str(shot.get("video_prompt", {}).get("subject_motion", "")).strip()
            scene = str(shot.get("scene", "")).strip() or (
                f"{shot['subject_focus']}: {subject_motion}" if subject_motion else shot["subject_focus"]
            )
            clean_lines.append(narration)
            eleven_lines.append(f"[{tag}] {narration}" if tag else narration)
            director_lines.extend([
                f"## {sentence_index:02d}. {shot['shot_id']} — {beat['role']}",
                "",
                f"- 대사: {narration}",
                f"- 장면: {scene}",
                f"- 감정: {emotion}",
                "",
            ])
            director_lines.append(
                "[연출: "
                f"트리거={shot['trigger_phrase']} | 대상={shot['subject_focus']} | 앵커={shot['anchor_id']} | "
                f"카메라={shot['camera_move']} | 이징={shot['camera_easing']} | 오버레이={shot['overlay']} | "
                f"전환={shot['transition']} | 목적={shot['causal_purpose']}]"
            )
            event = {
                "beat_id": beat["id"],
                "role": beat["role"],
                "dialogue": narration,
                "scene": scene,
                "line_text": narration,
                "emotion": emotion,
                "timing_status": "pending_tts_word_alignment",
                "source_start_ms": None,
                "at_seconds": None,
                **shot,
            }
            events.append(event)
        for sound in sound_by_beat.get(beat["id"], []):
            director_lines.append(
                "[사운드: "
                f"트리거={sound['trigger_phrase']} | 종류={sound['kind']} | 에셋={sound['asset_key']} | "
                f"정책={sound['source_policy']} | 싱크={sound['sync']} | 선행={sound['lead_frames']}프레임 | "
                f"목적={sound['causal_purpose']}]"
            )
            sound_event = {
                "role": beat["role"],
                "line_text": next(
                    (line for line in sentence_lines if sound["trigger_phrase"] in line),
                    beat_narration,
                ),
                "timing_status": "pending_tts_word_alignment",
                "source_start_ms": None,
                "at_seconds": None,
                **sound,
            }
            sound_events.append(sound_event)
            sound_sheet_lines.extend([
                f"## {sound['sound_id']} — beat {int(beat['id']):02d}",
                "",
                f"- 발화 트리거: `{sound['trigger_phrase']}`",
                f"- 종류·에셋: `{sound['kind']}` · `{sound['asset_key']}`",
                f"- 소스 정책: `{sound['source_policy']}`",
                f"- 싱크: `{sound['sync']}`, {sound['lead_frames']}프레임 선행",
                f"- 게인·덕킹: {sound['gain_db']}dB · 음악 {sound['duck_music_db']}dB",
                f"- 목적: {sound['causal_purpose']}",
                "",
            ])
        director_lines.append("")

    paths = {
        "director": args.out / "video-direction-script.md",
        "clean_tts": args.out / "narration-clean.txt",
        "eleven_v3": args.out / "eleven-v3.txt",
        "motion": args.out / "motion-timeline.json",
        "sound": args.out / "sound-timeline.json",
        "sound_sheet": args.out / "sound-cue-sheet.md",
    }
    paths["director"].write_text("\n".join(director_lines).rstrip() + "\n", encoding="utf-8")
    paths["clean_tts"].write_text("\n".join(clean_lines).rstrip() + "\n", encoding="utf-8")
    paths["eleven_v3"].write_text("\n".join(eleven_lines).rstrip() + "\n", encoding="utf-8")
    paths["motion"].write_text(
        json.dumps(
            {
                "episode_id": data["id"],
                "brand": data.get("brand", "몸의 발명사"),
                "requires_tts_word_alignment": True,
                "events": events,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    paths["sound"].write_text(
        json.dumps(
            {
                "episode_id": data["id"],
                "brand": data.get("brand", "몸의 발명사"),
                "requires_tts_word_alignment": True,
                "sound_design": data.get("sound_design", {}),
                "events": sound_events,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    paths["sound_sheet"].write_text("\n".join(sound_sheet_lines).rstrip() + "\n", encoding="utf-8")

    manifest = {
        "source": {"path": str(args.episode.resolve()), "sha256": sha256(args.episode)},
        "outputs": {
            name: {"path": str(path.resolve()), "sha256": sha256(path)}
            for name, path in paths.items()
        },
        "semantic_shots": len(events),
        "sound_events": len(sound_events),
        "timing_status": "pending_tts_word_alignment",
    }
    manifest_path = args.out / "production-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"built": True, "out": str(args.out), "semantic_shots": len(events), "sound_events": len(sound_events)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
