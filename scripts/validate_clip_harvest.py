#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    args = parser.parse_args()
    episode = args.episode.resolve()
    manifest_path = episode / "plans" / "clip-harvest-v6.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    rows = manifest.get("sentences", [])
    expected = [f"s{i:02d}" for i in range(1, 38)]
    actual = [row.get("sentence_id") for row in rows]
    if actual != expected:
        errors.append("sentence ids must be exactly s01..s37 in order")
    if manifest.get("sentence_count") != 37 or len(rows) != 37:
        errors.append("sentence_count must be 37")
    units = set()
    for row in rows:
        sid = row.get("sentence_id", "unknown")
        source = episode / row.get("source_path", "")
        if not source.exists():
            errors.append(f"{sid}: missing source {source}")
            continue
        if sha256(source) != row.get("source_sha256"):
            errors.append(f"{sid}: source hash mismatch")
        start = float(row.get("source_in", -1))
        end = float(row.get("source_out", -1))
        duration = end - start
        if start < 0 or end > 8.000001 or not (1.0 <= duration <= 3.000001):
            errors.append(f"{sid}: invalid 1-3 second source window {start}-{end}")
        if float(row.get("speed_ratio", 0)) != 1.0:
            errors.append(f"{sid}: stage 10 must retain normal speed")
        if row.get("optical_flow") is not False:
            errors.append(f"{sid}: optical flow must be false at harvest")
        if row.get("native_audio_decision") not in {"keep", "mute", "replace"}:
            errors.append(f"{sid}: invalid native audio decision")
        if row.get("native_audio_decision") == "keep" and not row.get("audio_harvest_window"):
            errors.append(f"{sid}: kept native audio requires a harvest window")
        if row.get("reject_reason") is not None:
            errors.append(f"{sid}: selected row cannot have reject_reason")
        units.add(row.get("unit_id"))
    if len(units) != 13 or manifest.get("unique_source_count") != 13:
        errors.append("all 13 unique Flow units must be represented")
    if manifest.get("failed_units") or manifest.get("conditional_pass_units"):
        errors.append("failed or conditional units cannot pass harvest")
    u12 = [r for r in rows if r.get("unit_id") == "vit-v6-u12"]
    if len(u12) != 3:
        errors.append("u12 must own exactly s31-s33")
    for row in u12:
        repair = row.get("visual_repair", {})
        if repair.get("severity") != "release_blocking" or not repair.get("required"):
            errors.append(f"{row.get('sentence_id')}: u12 repair must be release blocking")
        if len(repair.get("source_masks", [])) < 2:
            errors.append(f"{row.get('sentence_id')}: u12 requires both shelf-label masks")
    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
