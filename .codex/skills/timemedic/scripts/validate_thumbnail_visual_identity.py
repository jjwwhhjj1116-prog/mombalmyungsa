#!/usr/bin/env python3
"""Fail-closed validator for 몸의 발명사 thumbnail visual identity locks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


REQUIRED_TRUE = (
    "matte_handcrafted_resin",
    "adult_miniature_ratio_1_4_5_to_1_6",
    "sculpted_solid_hair",
    "simplified_painted_face",
)

ALLOWED_SCALE_CLUES = {
    "display_plinth",
    "dollhouse_wall_cutaway",
    "brass_rail",
    "oversized_screw",
    "museum_glass_reflection",
}

FORBIDDEN = {
    "skin_pores",
    "individual_eyelashes",
    "individual_hair_strands",
    "real_fabric_folds",
    "live_actor_lighting",
    "photoreal_human",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_asset(lock_path: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate
    return lock_path.parent / candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("lock")
    args = parser.parse_args()

    lock_path = Path(args.lock).resolve()
    data = json.loads(lock_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if data.get("verdict") != "PASS":
        errors.append("verdict must be PASS")
    if data.get("manual_visual_review_completed") is not True:
        errors.append("manual_visual_review_completed must be true")

    checks = data.get("checks") or {}
    for key in REQUIRED_TRUE:
        if checks.get(key) is not True:
            errors.append(f"checks.{key} must be true")

    clues = set(data.get("visible_scale_clues") or [])
    invalid_clues = clues - ALLOWED_SCALE_CLUES
    if invalid_clues:
        errors.append(f"invalid scale clues: {sorted(invalid_clues)}")
    if len(clues) < 2:
        errors.append("at least two visible scale clues are required")

    forbidden_detected = set(data.get("forbidden_detected") or [])
    unknown_forbidden = forbidden_detected - FORBIDDEN
    if unknown_forbidden:
        errors.append(f"unknown forbidden traits: {sorted(unknown_forbidden)}")
    if forbidden_detected:
        errors.append(f"forbidden traits detected: {sorted(forbidden_detected)}")

    asset_raw = data.get("asset_path")
    expected_hash = str(data.get("asset_sha256") or "").lower()
    if not asset_raw:
        errors.append("asset_path is required")
    elif not expected_hash:
        errors.append("asset_sha256 is required")
    else:
        asset_path = resolve_asset(lock_path, asset_raw)
        if not asset_path.exists():
            errors.append(f"asset not found: {asset_path}")
        elif sha256(asset_path) != expected_hash:
            errors.append("asset_sha256 mismatch")

    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            {
                "valid": True,
                "verdict": "PASS",
                "visible_scale_clues": sorted(clues),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
