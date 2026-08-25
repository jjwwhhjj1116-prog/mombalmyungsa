#!/usr/bin/env python3
"""Build the exact-TTS-excerpt vertical Short manifest from the approved Black Death master."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "video" / "src" / "data" / "black-death-v1-timeline.json"
SEMANTIC = ROOT / "video" / "src" / "data" / "black-death-v1-semantic.json"
OUTPUT = ROOT / "video" / "src" / "data" / "black-death-v1-short.json"
PLAN = ROOT / "episodes" / "black-death-quarantine" / "plans" / "derivative-short-v1.json"

SELECTED = ["s01", "s03", "s04", "s05", "s06", "s16", "s17", "s19", "s26", "s27", "s28", "s30", "s31", "s50"]
OBJECT_POSITIONS = {
    "s01": "54% center", "s03": "50% center", "s04": "50% center", "s05": "50% center",
    "s06": "55% center", "s16": "48% center", "s17": "52% center", "s19": "50% center",
    "s26": "50% center", "s27": "50% center", "s28": "55% center", "s30": "50% center",
    "s31": "50% center", "s50": "50% center",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    semantic = json.loads(SEMANTIC.read_text(encoding="utf-8"))
    by_id = {scene["sentence_id"]: scene for scene in timeline["scenes"]}
    scenes = []
    pages = []
    events = []
    cursor = 0

    for sentence_id in SELECTED:
        source = by_id[sentence_id]
        source_start = int(source["start_frame"])
        source_end = int(source["sentence_end_frame"])
        duration = source_end - source_start
        scene = dict(source)
        scene.update({
            "source_master_start_frame": source_start,
            "source_master_end_frame": source_end,
            "start_frame": cursor,
            "sentence_end_frame": cursor + duration,
            "display_end_frame": cursor + duration,
            "object_position": OBJECT_POSITIONS[sentence_id],
        })
        scenes.append(scene)

        for page in semantic.get("caption_pages", []):
            tokens = [
                token for token in page.get("tokens", [])
                if token["end_frame"] > source_start and token["start_frame"] < source_end
            ]
            if not tokens:
                continue
            shifted_tokens = []
            for token in tokens:
                shifted = dict(token)
                shifted["start_frame"] = cursor + max(0, token["start_frame"] - source_start)
                shifted["end_frame"] = cursor + min(duration, token["end_frame"] - source_start)
                shifted_tokens.append(shifted)
            pages.append({
                "page_id": f"short-{sentence_id}-{page['page_id']}",
                "sentence_id": sentence_id,
                "start_frame": min(token["start_frame"] for token in shifted_tokens),
                "end_frame": max(token["end_frame"] for token in shifted_tokens),
                "tokens": shifted_tokens,
            })

        for event in semantic.get("semantic_events", []):
            if event.get("sentence_id") != sentence_id:
                continue
            shifted = dict(event)
            shifted["event_id"] = f"short-{event['event_id']}"
            shifted["start_frame"] = cursor + max(0, event["start_frame"] - source_start)
            shifted["end_frame"] = cursor + min(duration, event["end_frame"] - source_start)
            events.append(shifted)

        cursor += duration

    payload = {
        "schema_version": "body-invention.derivative-short.v1",
        "episode_id": "black-death-quarantine",
        "variant_id": "black-death-quarantine-short-v1",
        "source_script_sha256": "bda7311e1462317c713c609a38c4d2810d63c2a38374bf9b8a70211c81541816",
        "source_tts_sha256": "58f217efc7339e71241cf3bd9c7a5e2be2ef59a8a3bf1dd4b89226874db06fec",
        "selection_policy": "exact_approved_sentences_and_existing_tts_windows_only",
        "new_claim_count": 0,
        "new_tts_generation_required": False,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "total_frames": cursor,
        "duration_seconds": round(cursor / 30, 3),
        "frame_zero_frames": 21,
        "frame_zero_asset": "black-death/thumbnail-v1-short.png",
        "audio_asset": timeline["audio_asset"],
        "selected_sentence_ids": SELECTED,
        "scenes": scenes,
        "caption_pages": pages,
        "semantic_events": events,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    plan = {
        "schema_version": "body-invention.derivative-short-plan.v1",
        "episode_id": "black-death-quarantine",
        "variant_id": payload["variant_id"],
        "status": "ready_for_render",
        "source_master": "renders/black-death-v1-final.mp4",
        "source_master_sha256": "85abdbdb012bd98a63bbf2c3b3215224c163bffe26114bf5c25a3d45dd06b8cf",
        "source_script_sha256": payload["source_script_sha256"],
        "source_tts_sha256": payload["source_tts_sha256"],
        "selected_sentence_ids": SELECTED,
        "exact_tts_excerpt_seconds": payload["duration_seconds"],
        "aspect_ratio": "9:16",
        "render_size": [1080, 1920],
        "thumbnail": "assets/thumbnail-v1-short.png",
        "frame_zero_seconds": 0.7,
        "independent_story_arc": ["hook", "misconception", "mechanism", "double_bind", "question_flip", "quarantine", "meaning"],
        "new_claim_count": 0,
        "new_tts_generation_required": False,
        "human_reapproval_required": False,
        "qa_required": True,
        "idempotency_key": "youtube:UCYqdIlpFlB6uh_cpIYgo85g:black-death-quarantine:short-v1:pending-render-hash",
        "manifest_sha256": sha256(OUTPUT),
    }
    if PLAN.is_file():
        existing_plan = json.loads(PLAN.read_text(encoding="utf-8"))
        if existing_plan.get("status") == "completed_and_qa_locked":
            plan = existing_plan
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({payload['duration_seconds']}s)")
    print(f"wrote {PLAN.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
