#!/usr/bin/env python3
"""Build the locked sentence-owned clip harvest for the Black Death episode."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "black-death-quarantine"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


PILOTS = {
    "bdq-v1-u01a": {
        "path": "flow/pilots/bdq-v1-u01a-omni-flash-t2v-v1.mp4",
        "sha256": "50a07dd994a70b1b06e2daeb5711883d09fc7c967a3c55bfe497c943032c92c9",
        "start": 0.0,
        "end": 6.0,
    },
    "bdq-v1-u01b": {
        "path": "flow/pilots/bdq-v1-u01b-omni-flash-v1.mp4",
        "sha256": "4bae6b8989da16ab68781577c1639a22bd799c6a26ebb7975d7336f99dd71355",
        "start": 0.0,
        "end": 8.0,
    },
    "bdq-v1-u16": {
        "path": "flow/pilots/bdq-v1-u16-omni-flash-v1.mp4",
        "sha256": "6e0aea215281a34d114baf459b00950ce8763e5154e09543f535eeed41c5fffa",
        "start": 0.0,
        "end": 8.0,
    },
}


RECEIPT_OVERRIDES = {
    "bdq-v1-u10": "receipts/bdq-v1-u10-attempt-2.flow-receipt.json",
    "bdq-v1-u13": "receipts/bdq-v1-u13-attempt-2.flow-receipt.json",
}


WINDOW_OVERRIDES = {
    "bdq-v1-u02": (1.25, 8.0),
    "bdq-v1-u27": (0.0, 3.7),
}


REPAIRS = {
    "bdq-v1-u03": {
        "required": True,
        "stage": "13_semantic_motion_sound",
        "method": "track small rod-shaped bacteria particles along the dark moving stream only during the matching narration",
        "acceptance": "the stream reads as plague bacteria without text and the sail transition remains visible",
    },
    "bdq-v1-u27": {
        "required": True,
        "stage": "10_clip_harvest",
        "method": "use only the clean 0.0-3.7 second interval; if any generated phrase remains, cover it with an opaque semantic panel",
        "acceptance": "zero readable generated writing in every selected frame",
    },
}


def receipt_for(unit_id: str) -> dict:
    rel = RECEIPT_OVERRIDES.get(
        unit_id, f"receipts/{unit_id}.flow-receipt.json"
    )
    return json.loads((EPISODE / rel).read_text(encoding="utf-8"))


def main() -> None:
    units = json.loads(
        (EPISODE / "plans" / "generation-units-v6.json").read_text(
            encoding="utf-8"
        )
    )["units"]
    lines = [
        line.strip()
        for line in (EPISODE / "final-script-v1.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(lines) != 50:
        raise ValueError(f"expected 50 script sentences, got {len(lines)}")

    sentences = []
    unique_sources = set()
    for unit in units:
        unit_id = unit["unit_id"]
        if unit_id in PILOTS:
            source = PILOTS[unit_id]
        else:
            receipt = receipt_for(unit_id)
            if "pass" not in receipt["status"].lower():
                raise ValueError(f"non-pass receipt selected for {unit_id}")
            source = {
                "path": receipt["local_media"]["path"],
                "sha256": receipt["local_media"]["sha256"],
                "start": 0.0,
                "end": float(receipt["local_media"]["duration_seconds"]),
            }
        if unit_id in WINDOW_OVERRIDES:
            source["start"], source["end"] = WINDOW_OVERRIDES[unit_id]
        unique_sources.add(source["path"])

        sentence_ids = unit["sentence_ids"]
        span = source["end"] - source["start"]
        step = span / len(sentence_ids)
        for offset, sentence_id in enumerate(sentence_ids):
            sentence_index = int(sentence_id[1:]) - 1
            source_in = source["start"] + step * offset
            source_out = source["start"] + step * (offset + 1)
            sentences.append(
                {
                    "sentence_id": sentence_id,
                    "narration": lines[sentence_index],
                    "unit_id": unit_id,
                    "source_path": source["path"],
                    "source_sha256": source["sha256"],
                    "source_in": round(source_in, 3),
                    "source_out": round(source_out, 3),
                    "source_duration": round(source_out - source_in, 3),
                    "speed_ratio": 1.0,
                    "optical_flow": False,
                    "motion_carrier": unit.get("motion_carrier"),
                    "continuity_anchors": unit.get("continuity_anchors", []),
                    "native_audio_decision": "replace",
                    "native_audio_reason": "two-frame event sync and absence of speech or music were not proven for the selected window",
                    "visual_repair": REPAIRS.get(
                        unit_id, {"required": False}
                    ),
                }
            )

    if [item["sentence_id"] for item in sentences] != [
        f"s{i:02d}" for i in range(1, 51)
    ]:
        raise ValueError("sentence ownership is incomplete or out of order")

    output = {
        "schema_version": "body-invention.clip-harvest.v1",
        "episode_id": "black-death-quarantine",
        "revision": 12,
        "stage_id": "10_clip_harvest",
        "status": "selected",
        "input_hashes": {
            "script": sha256(EPISODE / "final-script-v1.txt"),
            "storyboard": sha256(EPISODE / "plans" / "storyboard-v6.json"),
            "batch_lock": sha256(
                EPISODE / "locks" / "09-batch-generation.lock.json"
            ),
        },
        "rules": {
            "one_sentence_one_scene": True,
            "normal_speed_default": True,
            "optical_flow_default": False,
            "generated_text_allowed": False,
            "native_audio_keep_requires_two_frame_sync": True,
            "unverified_native_audio_policy": "replace_with_edit_sfx",
            "final_tts_is_only_timeline": True,
        },
        "sentence_count": len(sentences),
        "unique_source_count": len(unique_sources),
        "failed_units": [],
        "conditional_pass_units": ["bdq-v1-u02", "bdq-v1-u03", "bdq-v1-u06", "bdq-v1-u27"],
        "mandatory_repairs": [
            {"unit_id": key, **value} for key, value in REPAIRS.items()
        ],
        "sentences": sentences,
        "approved_by": "internal_visual_harvest_review",
        "completed_at": datetime.now().astimezone().isoformat(),
    }
    output_path = EPISODE / "plans" / "clip-harvest-v1.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output_path)


if __name__ == "__main__":
    main()
