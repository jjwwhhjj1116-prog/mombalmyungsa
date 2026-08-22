#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


CATEGORY_RE = re.compile(r"^### \[카테고리 (\d+)\] (.+?) \((\d+)~(\d+)\)\s*$")
TOPIC_RE = re.compile(r"^(\d+)\.\s+\*\*(.+?)\*\*:\s*(.+?)\s*$")
SLOT_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def risk_flags(index, title, claim):
    text = f"{title} {claim}"
    flags = []
    if re.search(r"\d", text):
        flags.append("numeric_claim_requires_direct_source")
    if '"' in text or "'" in text or "“" in text or "”" in text:
        flags.append("quote_or_name_origin_requires_direct_source")
    if re.search(r"최초|처음|유래|탄생|원래|시초|어원", text):
        flags.append("origin_or_first_claim")
    if re.search(r"치료|효과|살리|구원|박멸|기적|회복|재생|수명", text):
        flags.append("medical_effect_claim")
    if re.search(r"죽|사망|피|고름|절단|기형|마약|독가스|수은|비소|방사능|고문", text):
        flags.append("graphic_or_sensitive_claim")
    if index <= 15:
        flags.append("commercial_product_claim")
    return flags or ["historical_causal_claim"]


def parse_topics(source):
    category = None
    categories = {}
    topics = []
    for line in source.read_text(encoding="utf-8").splitlines():
        category_match = CATEGORY_RE.match(line.strip())
        if category_match:
            category_id = int(category_match.group(1))
            category = {
                "category_id": category_id,
                "name": category_match.group(2).strip(),
                "declared_range": [int(category_match.group(3)), int(category_match.group(4))],
            }
            categories[category_id] = category
            continue

        topic_match = TOPIC_RE.match(line.strip())
        if not topic_match:
            continue
        if category is None:
            raise ValueError(f"topic appears before category: {line}")
        index = int(topic_match.group(1))
        title = topic_match.group(2).strip()
        claim = topic_match.group(3).strip()
        topics.append(
            {
                "queue_index": index,
                "topic_id": f"topic-{index:03d}",
                "category_id": category["category_id"],
                "category_name": category["name"],
                "title": title,
                "raw_claim": claim,
                "verification_status": "pending",
                "source_ids": [],
                "claim_risk_flags": risk_flags(index, title, claim),
                "workflow_status": "queued",
                "human_approved": False,
                "publishable": False,
            }
        )

    indexes = [item["queue_index"] for item in topics]
    if indexes != list(range(1, 101)):
        raise ValueError(f"expected topics 1..100 in exact order; found {indexes}")
    for category_id, entry in categories.items():
        actual = [item["queue_index"] for item in topics if item["category_id"] == category_id]
        expected = list(range(entry["declared_range"][0], entry["declared_range"][1] + 1))
        if actual != expected:
            raise ValueError(f"category {category_id} range mismatch: expected {expected}, found {actual}")
    return list(categories.values()), topics


def iso_at(day, hhmm, offset):
    hour, minute = map(int, hhmm.split(":"))
    return datetime.combine(day, time(hour, minute), tzinfo=offset).isoformat()


def build_schedule(topics, start_date, slots, upload_lead_minutes, schedule_approved):
    if len(slots) != 2 or any(not SLOT_RE.match(slot) for slot in slots):
        raise ValueError("exactly two valid HH:MM slots are required")
    kst = timezone(timedelta(hours=9))
    days = []
    for day_index in range(1, 51):
        public_day = start_date + timedelta(days=day_index - 1) if start_date else None
        lanes = []
        for lane_index, lane in enumerate(("a", "b")):
            topic = topics[(day_index - 1) * 2 + lane_index]
            scheduled_public = None
            private_upload = None
            if public_day:
                public_dt = datetime.fromisoformat(iso_at(public_day, slots[lane_index], kst))
                scheduled_public = public_dt.isoformat()
                private_upload = (public_dt - timedelta(minutes=upload_lead_minutes)).isoformat()
            lanes.append(
                {
                    "lane": lane,
                    "topic_id": topic["topic_id"],
                    "queue_index": topic["queue_index"],
                    "title": topic["title"],
                    "research_and_script_day": (public_day - timedelta(days=2)).isoformat() if public_day else f"DAY {day_index} D-2",
                    "video_production_day": (public_day - timedelta(days=1)).isoformat() if public_day else f"DAY {day_index} D-1",
                    "private_upload_at": private_upload,
                    "scheduled_public_at": scheduled_public,
                    "pipeline_instance_path": f"episodes/{topic['topic_id']}/omni-stage-pipeline.json",
                    "idempotency_key": f"timemedic:day-{day_index:02d}:lane-{lane}:{topic['topic_id']}",
                    "status": "queued",
                    "schedule_approved": schedule_approved,
                    "human_approved": False,
                    "publishable": False,
                }
            )
        days.append(
            {
                "day_index": day_index,
                "public_date": public_day.isoformat() if public_day else None,
                "lanes": lanes,
            }
        )
    return days


def build_markdown(days):
    lines = [
        "# 몸의 발명사 50일·하루 2편 주제표",
        "",
        "> 원문 주장은 모두 검증 전 아이디어다. 1차·학술 근거와 사용자 대본 승인을 통과하기 전에는 제작·게시하지 않는다.",
        "",
        "| DAY | A편 | B편 | 상태 |",
        "|---:|---|---|---|",
    ]
    for entry in days:
        lane_a, lane_b = entry["lanes"]
        lines.append(
            f"| {entry['day_index']:02d} | {lane_a['queue_index']:03d}. {lane_a['title']} | "
            f"{lane_b['queue_index']:03d}. {lane_b['title']} | 검증 대기 |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--slots", nargs=2, default=["11:00", "19:00"])
    parser.add_argument("--upload-lead-minutes", type=int, default=60)
    parser.add_argument("--approve-schedule", action="store_true")
    args = parser.parse_args()

    if args.upload_lead_minutes < 60:
        raise SystemExit("upload lead must be at least 60 minutes")
    categories, topics = parse_topics(args.source)
    days = build_schedule(topics, args.start_date, args.slots, args.upload_lead_minutes, args.approve_schedule)

    catalog = {
        "schema_version": "timemedic.topic-catalog.v1",
        "brand": "몸의 발명사",
        "source": {"path": str(args.source.resolve()), "sha256": sha256(args.source)},
        "views_goal": 1000000,
        "views_guaranteed": False,
        "queue_order": "strict_ascending_no_silent_skip",
        "existing_pilot_episode": "cpr-discovery",
        "existing_pilot_counts_toward_100": False,
        "categories": categories,
        "topics": topics,
    }
    schedule = {
        "schema_version": "timemedic.daily-two-video.v1",
        "brand": "몸의 발명사",
        "topic_catalog_sha256": None,
        "timezone": "Asia/Seoul",
        "daily_video_count": 2,
        "total_topics": len(topics),
        "total_days": len(days),
        "public_slots_local": args.slots,
        "private_upload_lead_minutes": args.upload_lead_minutes,
        "start_date": args.start_date.isoformat() if args.start_date else None,
        "schedule_approved": args.approve_schedule,
        "pipeline": ["D-2 research_script", "D-1 video_production", "D0 final_qa_private_upload_release"],
        "days": days,
    }

    args.catalog.parent.mkdir(parents=True, exist_ok=True)
    args.schedule.parent.mkdir(parents=True, exist_ok=True)
    args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    schedule["topic_catalog_sha256"] = sha256(args.catalog)
    args.schedule.write_text(json.dumps(schedule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(build_markdown(days), encoding="utf-8")
    print(
        json.dumps(
            {
                "valid": True,
                "topics": len(topics),
                "days": len(days),
                "first_day": [lane["topic_id"] for lane in days[0]["lanes"]],
                "last_day": [lane["topic_id"] for lane in days[-1]["lanes"]],
                "catalog": str(args.catalog),
                "schedule": str(args.schedule),
                "markdown": str(args.markdown) if args.markdown else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
