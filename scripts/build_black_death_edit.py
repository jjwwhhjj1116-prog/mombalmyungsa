#!/usr/bin/env python3
"""Build the TTS-owned Remotion timeline for the Black Death episode."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "black-death-quarantine"
PUBLIC = ROOT / "video" / "public"
FPS = 30
WIDTH = 1920
HEIGHT = 1080


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_locked(source: Path, target: Path, expected_hash: str) -> None:
    if sha256(source) != expected_hash:
        raise ValueError(f"source hash mismatch: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or sha256(target) != expected_hash:
        shutil.copy2(source, target)
    if sha256(target) != expected_hash:
        raise ValueError(f"copied hash mismatch: {target}")


def to_frame(seconds: float) -> int:
    return max(0, round(float(seconds) * FPS))


def display_tokens(words: list[dict]) -> list[dict]:
    single = {
        "오천만": "5천만",
        "천삼백사십칠년": "1347년",
        "천삼백칠십칠년": "1377년",
        "천팔백구십사년": "1894년",
    }
    merged: list[dict] = []
    index = 0
    while index < len(words):
        word = words[index]
        normalized = word["normalized"]
        if index + 1 < len(words):
            nxt = words[index + 1]
            if normalized in {"삼십", "사십"} and nxt["normalized"] == "일":
                merged.append(
                    {
                        "text": "30일" if normalized == "삼십" else "40일",
                        "start": word["start"],
                        "end": nxt["end"],
                    }
                )
                index += 2
                continue
            if normalized == "사" and nxt["normalized"] == "년":
                merged.append({"text": "4년", "start": word["start"], "end": nxt["end"]})
                index += 2
                continue
        plain = re.sub(r"^[^0-9A-Za-z가-힣]+|[^0-9A-Za-z가-힣?!]+$", "", word["text"])
        merged.append(
            {
                "text": single.get(normalized, plain or word["text"]),
                "start": word["start"],
                "end": word["end"],
            }
        )
        index += 1
    return merged


def break_lines(tokens: list[dict], max_line_chars: int = 12) -> list[str]:
    lines: list[list[str]] = [[]]
    count = 0
    for token in tokens:
        extra = len(token["text"]) + (1 if lines[-1] else 0)
        if lines[-1] and count + extra > max_line_chars and len(lines) == 1:
            lines.append([])
            count = 0
            extra = len(token["text"])
        lines[-1].append(token["text"])
        count += extra
    return [" ".join(line) for line in lines if line]


def caption_pages(alignment: dict) -> list[dict]:
    pages: list[dict] = []
    page_number = 0
    for sentence in alignment["sentence_alignment"]:
        sid = sentence["sentence_id"]
        words = [word for word in alignment["words"] if word["sentence_id"] == sid]
        tokens = display_tokens(words)
        groups: list[list[dict]] = []
        current: list[dict] = []
        visible = 0
        for token in tokens:
            extra = len(token["text"]) + (1 if current else 0)
            if current and visible + extra > 22:
                groups.append(current)
                current = []
                visible = 0
                extra = len(token["text"])
            current.append(token)
            visible += extra
        if current:
            groups.append(current)
        for group_index, group in enumerate(groups):
            page_number += 1
            start = to_frame(group[0]["start"])
            if group_index + 1 < len(groups):
                end = to_frame(groups[group_index + 1][0]["start"])
            else:
                end = to_frame(sentence["end"])
            pages.append(
                {
                    "page_id": f"cap-{page_number:03d}",
                    "sentence_id": sid,
                    "start_frame": start,
                    "end_frame": max(start + 1, end),
                    "lines": break_lines(group),
                    "tokens": [
                        {
                            "text": token["text"],
                            "start_frame": to_frame(token["start"]),
                            "end_frame": max(to_frame(token["start"]) + 1, to_frame(token["end"])),
                        }
                        for token in group
                    ],
                }
            )
    return pages


SEMANTIC = {
    "s02": ("death_toll", "5천만 명 이상", "soft-impact.wav"),
    "s05": ("cause_reveal", "벼룩 + 페스트균", "glass-click.wav"),
    "s14": ("network", "여러 갈래의 감염 경로", "timeline-whoosh.wav"),
    "s19": ("dilemma", "생계  ↔  감염", "soft-impact.wav"),
    "s26": ("question_flip", "질문을 뒤집다", "timeline-whoosh.wav"),
    "s28": ("ragusa", "1377년 · 라구사 · 30일", "counter-tick.wav"),
    "s30": ("quarantine", "30일 → 40일 · 검역", "counter-tick.wav"),
    "s31": ("chain_break", "감염의 길을 끊다", "glass-click.wav"),
    "s38": ("bacterium", "페스트균 발견", "glass-click.wav"),
    "s40": ("flea_link", "전파의 연결고리 · 벼룩", "glass-click.wav"),
    "s43": ("control_order", "1 벼룩 · 2 설치류", "counter-tick.wav"),
    "s44": ("treatment", "조기 발견 + 항생제", "soft-impact.wav"),
    "s47": ("five_layers", "격리 → 원인 → 벼룩 → 설치류 → 치료", "counter-tick.wav"),
    "s48": ("network_answer", "문제는 감염의 길 전체", "timeline-whoosh.wav"),
    "s49": ("disconnect", "그 길을 하나씩 끊었다", "glass-click.wav"),
    "s50": ("closing", "격리와 방역 체계", "soft-impact.wav"),
}


def main() -> None:
    alignment = json.loads((EPISODE / "tts" / "black-death-v1-alignment.json").read_text(encoding="utf-8"))
    harvest = json.loads((EPISODE / "plans" / "clip-harvest-v1.json").read_text(encoding="utf-8"))
    storyboard = json.loads((EPISODE / "plans" / "storyboard-v6.json").read_text(encoding="utf-8"))
    storyboard_by_id = {item["sentence_id"]: item for item in storyboard["scenes"]}
    align_by_id = {item["sentence_id"]: item for item in alignment["sentence_alignment"]}

    audio_source = EPISODE / alignment["audio_path"]
    copy_locked(audio_source, PUBLIC / "black-death" / audio_source.name, alignment["audio_sha256"])
    thumb_source = EPISODE / "assets" / "thumbnail-v1-landscape.png"
    copy_locked(thumb_source, PUBLIC / "black-death" / thumb_source.name, sha256(thumb_source))
    font_source = EPISODE / "assets" / "GmarketSansTTFBold.ttf"
    copy_locked(font_source, PUBLIC / "fonts" / font_source.name, sha256(font_source))

    source_public: dict[str, str] = {}
    for item in harvest["sentences"]:
        if item["unit_id"] in source_public:
            continue
        source = EPISODE / item["source_path"]
        public_rel = f"black-death/media/{item['unit_id']}.mp4"
        copy_locked(source, PUBLIC / public_rel, item["source_sha256"])
        source_public[item["unit_id"]] = public_rel

    total_frames = math.ceil(float(alignment["audio_duration_seconds"]) * FPS)
    scenes = []
    harvested = {item["sentence_id"]: item for item in harvest["sentences"]}
    sentence_order = [f"s{i:02d}" for i in range(1, 51)]
    for position, sid in enumerate(sentence_order):
        aligned = align_by_id[sid]
        selected = harvested[sid]
        board = storyboard_by_id[sid]
        start_frame = 0 if position == 0 else to_frame(aligned["start"])
        if position + 1 < len(sentence_order):
            display_end = to_frame(align_by_id[sentence_order[position + 1]]["start"])
        else:
            display_end = total_frames
        sentence_end = to_frame(aligned["end"])
        display_end = max(display_end, sentence_end, start_frame + 1)
        display_seconds = (display_end - start_frame) / FPS
        source_duration = float(selected["source_out"]) - float(selected["source_in"])
        playback_rate = source_duration / max(display_seconds, 0.05)
        scenes.append(
            {
                "sentence_id": sid,
                "text": aligned["text"],
                "start_frame": start_frame,
                "sentence_end_frame": sentence_end,
                "display_end_frame": display_end,
                "caption_start_frame": to_frame(aligned["start"]),
                "caption_end_frame": sentence_end,
                "unit_id": selected["unit_id"],
                "source_in": selected["source_in"],
                "source_out": selected["source_out"],
                "source_sha256": selected["source_sha256"],
                "public_source": source_public[selected["unit_id"]],
                "playback_rate": round(playback_rate, 6),
                "meaning_target": board["meaning_target"],
                "motion_carrier": board["motion_carrier"],
                "camera_purpose": board["camera_purpose"],
                "transition_mechanism": board["transition_mechanism"],
                "native_audio_decision": "replace",
                "bacteria_overlay": selected["unit_id"] == "bdq-v1-u03",
                "generated_text_mask": selected["unit_id"] == "bdq-v1-u27",
                "premature_next_meaning_allowed": False,
            }
        )

    premature = [scene["sentence_id"] for scene in scenes if scene["display_end_frame"] < scene["sentence_end_frame"]]
    if premature:
        raise ValueError(f"premature scene cuts: {premature}")

    timeline = {
        "schema_version": "body-invention.tts-owned-edit.v1",
        "episode_id": "black-death-quarantine",
        "stage_id": "12_tts_owned_edit",
        "status": "planned",
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "total_frames": total_frames,
        "audio_duration_seconds": alignment["audio_duration_seconds"],
        "frame_zero_frames": round(0.7 * FPS),
        "frame_zero_asset": "black-death/thumbnail-v1-landscape.png",
        "audio_asset": "black-death/black-death-v1-elevenlabs-full.mp3",
        "sentence_alignment_sha256": sha256(EPISODE / "tts" / "black-death-v1-alignment.json"),
        "clip_harvest_sha256": sha256(EPISODE / "plans" / "clip-harvest-v1.json"),
        "scene_count": len(scenes),
        "premature_scene_cut_count": 0,
        "native_audio_policy": "all_flow_audio_muted_and_replaced_with_frame_aligned_edit_sfx",
        "scenes": scenes,
    }

    events = []
    for sid, (kind, label, sound_asset) in SEMANTIC.items():
        aligned = align_by_id[sid]
        events.append(
            {
                "event_id": f"evt-{sid}-{kind}",
                "sentence_id": sid,
                "kind": kind,
                "label": label,
                "start_frame": to_frame(aligned["start"]),
                "end_frame": max(to_frame(aligned["start"]) + 1, to_frame(aligned["end"])),
                "sound_asset": sound_asset,
                "sound_lead_frames": 0,
            }
        )
    semantic = {
        "schema_version": "body-invention.semantic-motion-sound.v1",
        "episode_id": "black-death-quarantine",
        "stage_id": "13_semantic_motion_sound",
        "status": "planned",
        "font": "Gmarket Sans Bold",
        "caption_size_px": 100,
        "caption_vertical_slot_of_16": 10,
        "caption_pages": caption_pages(alignment),
        "semantic_events": events,
        "mandatory_repairs": {
            "bdq-v1-u03": "tracked rod-shaped bacteria overlay",
            "bdq-v1-u27": "opaque top-right semantic mask throughout selected clean interval",
        },
    }

    data = ROOT / "video" / "src" / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "black-death-v1-timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (data / "black-death-v1-semantic.json").write_text(json.dumps(semantic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EPISODE / "plans" / "tts-owned-edit-v1.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EPISODE / "plans" / "semantic-motion-sound-v1.json").write_text(json.dumps(semantic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scenes": len(scenes), "caption_pages": len(semantic["caption_pages"]), "events": len(events), "total_frames": total_frames, "duration": alignment["audio_duration_seconds"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
