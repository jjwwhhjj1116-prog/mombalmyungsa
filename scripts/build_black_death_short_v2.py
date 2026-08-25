#!/usr/bin/env python3
"""Build the 2-minute Black Death Short from exact approved master TTS windows.

The v1 derivative was rejected because it compressed the episode to under one
minute and broke the explanatory chain.  V2 keeps a continuous causal arc:
hook -> vector -> impossible port choice -> incubation -> quarantine ->
bacterial/flea proof -> modern control -> closing meaning.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "video" / "src" / "data" / "black-death-v1-timeline.json"
SEMANTIC = ROOT / "video" / "src" / "data" / "black-death-v1-semantic.json"
OUTPUT = ROOT / "video" / "src" / "data" / "black-death-v2-short.json"
PLAN = ROOT / "episodes" / "black-death-quarantine" / "plans" / "derivative-short-v2.json"

# Only whole approved sentences are used.  Their audio is excerpted from the
# same continuous master narration, so there is no voice-identity jump.
SELECTED = [
    "s01", "s02", "s03", "s04", "s05", "s06", "s07",
    "s09", "s10", "s11",
    "s15", "s16", "s17", "s18", "s19", "s20", "s21",
    "s25", "s26", "s27", "s28", "s29", "s30", "s31", "s32",
    "s34", "s35", "s36", "s37", "s38", "s39", "s40", "s41", "s42", "s43", "s44",
    "s47", "s48", "s49", "s50",
]

# Manual crop anchors for the 16:9 source shots when placed in a 9:16 frame.
# The subject must remain inside the center 46% crop.  Fine adjustments are
# verified again from rendered contact sheets.
OBJECT_POSITIONS = {
    "s01": "54% center", "s02": "52% center", "s03": "50% center",
    "s04": "50% center", "s05": "50% center", "s06": "55% center",
    "s07": "50% center", "s09": "50% center", "s10": "50% center",
    "s11": "52% center", "s15": "50% center", "s16": "48% center",
    "s17": "52% center", "s18": "50% center", "s19": "50% center",
    "s20": "50% center", "s21": "50% center", "s25": "50% center",
    "s26": "50% center", "s27": "50% center", "s28": "55% center",
    "s29": "50% center", "s30": "50% center", "s31": "50% center",
    "s32": "50% center", "s34": "50% center", "s35": "50% center",
    "s36": "50% center", "s37": "50% center", "s38": "50% center",
    "s39": "50% center", "s40": "50% center", "s41": "50% center",
    "s42": "50% center", "s43": "50% center", "s44": "50% center",
    "s47": "50% center", "s48": "50% center", "s49": "50% center",
    "s50": "50% center",
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
    scenes: list[dict] = []
    pages: list[dict] = []
    events: list[dict] = []
    cursor = 0

    for sentence_id in SELECTED:
        source = by_id[sentence_id]
        source_start = int(source["start_frame"])
        source_end = int(source["sentence_end_frame"])
        duration = source_end - source_start
        if duration <= 0:
            raise ValueError(f"invalid sentence duration: {sentence_id}")

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
                "page_id": f"short-v2-{sentence_id}-{page['page_id']}",
                "sentence_id": sentence_id,
                "start_frame": min(token["start_frame"] for token in shifted_tokens),
                "end_frame": max(token["end_frame"] for token in shifted_tokens),
                "tokens": shifted_tokens,
            })

        for event in semantic.get("semantic_events", []):
            if event.get("sentence_id") != sentence_id:
                continue
            shifted = dict(event)
            shifted["event_id"] = f"short-v2-{event['event_id']}"
            shifted["start_frame"] = cursor + max(0, event["start_frame"] - source_start)
            shifted["end_frame"] = cursor + min(duration, event["end_frame"] - source_start)
            events.append(shifted)

        cursor += duration

    duration_seconds = round(cursor / int(timeline["fps"]), 3)
    if not 120 <= duration_seconds < 180:
        raise ValueError(f"V2 must stay in the 2-minute Shorts lane, got {duration_seconds}s")

    payload = {
        "schema_version": "body-invention.derivative-short.v2",
        "episode_id": "black-death-quarantine",
        "variant_id": "black-death-quarantine-short-v2",
        "source_script_sha256": "bda7311e1462317c713c609a38c4d2810d63c2a38374bf9b8a70211c81541816",
        "source_tts_sha256": "58f217efc7339e71241cf3bd9c7a5e2be2ef59a8a3bf1dd4b89226874db06fec",
        "selection_policy": "whole_approved_sentences_and_existing_continuous_master_tts_windows_only",
        "narrative_continuity": "hook_vector_port_dilemma_incubation_quarantine_proof_modern_control_closing",
        "new_claim_count": 0,
        "new_tts_generation_required": False,
        "fps": int(timeline["fps"]),
        "width": 1080,
        "height": 1920,
        "total_frames": cursor,
        "duration_seconds": duration_seconds,
        "frame_zero_frames": 21,
        "frame_zero_asset": "black-death/thumbnail-v2-short.png",
        "audio_asset": timeline["audio_asset"],
        "selected_sentence_ids": SELECTED,
        "scenes": scenes,
        "caption_pages": pages,
        "semantic_events": events,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    plan = {
        "schema_version": "body-invention.derivative-short-plan.v2",
        "episode_id": "black-death-quarantine",
        "variant_id": payload["variant_id"],
        "status": "ready_for_render",
        "replaces_rejected_variant": "black-death-quarantine-short-v1",
        "source_master": "renders/black-death-v1-final.mp4",
        "source_master_sha256": "85abdbdb012bd98a63bbf2c3b3215224c163bffe26114bf5c25a3d45dd06b8cf",
        "source_script_sha256": payload["source_script_sha256"],
        "source_tts_sha256": payload["source_tts_sha256"],
        "selected_sentence_ids": SELECTED,
        "exact_tts_excerpt_seconds": duration_seconds,
        "aspect_ratio": "9:16",
        "render_size": [1080, 1920],
        "thumbnail": "assets/thumbnail-v2-short.png",
        "frame_zero_seconds": 0.7,
        "independent_story_arc": [
            "hook", "vector", "port_double_bind", "incubation", "question_flip",
            "quarantine", "pathogen_and_flea_proof", "modern_control", "meaning",
        ],
        "new_claim_count": 0,
        "new_tts_generation_required": False,
        "human_reapproval_required": False,
        "qa_required": True,
        "idempotency_key": "youtube:UCYqdIlpFlB6uh_cpIYgo85g:black-death-quarantine:short-v2:pending-render-hash",
        "manifest_sha256": sha256(OUTPUT),
    }
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({duration_seconds}s)")
    print(f"wrote {PLAN.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
