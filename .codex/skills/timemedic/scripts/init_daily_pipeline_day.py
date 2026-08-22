#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("schedule", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("--day", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    schedule = json.loads(args.schedule.read_text(encoding="utf-8"))
    template = json.loads(args.template.read_text(encoding="utf-8"))
    if not 1 <= args.day <= schedule.get("total_days", 0):
        raise SystemExit(f"day must be 1..{schedule.get('total_days')}")
    if schedule.get("topic_catalog_sha256") != sha256(args.catalog):
        raise SystemExit("schedule topic_catalog_sha256 mismatch")

    topic_by_id = {topic["topic_id"]: topic for topic in catalog["topics"]}
    day = schedule["days"][args.day - 1]
    created = []
    for lane in day["lanes"]:
        topic = topic_by_id[lane["topic_id"]]
        manifest = copy.deepcopy(template)
        manifest["id"] = topic["topic_id"]
        manifest["title"] = topic["title"]
        manifest["topic_queue"] = {
            "day_index": day["day_index"],
            "lane": lane["lane"],
            "queue_index": topic["queue_index"],
            "category_id": topic["category_id"],
            "category_name": topic["category_name"],
            "raw_claim": topic["raw_claim"],
            "verification_status": topic["verification_status"],
            "claim_risk_flags": topic["claim_risk_flags"],
            "idempotency_key": lane["idempotency_key"],
        }
        manifest["daily_operation"] = {
            "research_and_script_day": lane["research_and_script_day"],
            "video_production_day": lane["video_production_day"],
            "private_upload_at": lane["private_upload_at"],
            "scheduled_public_at": lane["scheduled_public_at"],
            "schedule_approved": lane["schedule_approved"],
        }
        manifest["catalog_sha256"] = sha256(args.catalog)
        manifest["schedule_sha256"] = sha256(args.schedule)
        episode_dir = args.out / topic["topic_id"]
        episode_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = episode_dir / "omni-stage-pipeline.json"
        if manifest_path.exists():
            raise SystemExit(f"refusing to overwrite existing pipeline: {manifest_path}")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append(str(manifest_path))

    print(json.dumps({"valid": True, "day": args.day, "created": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
