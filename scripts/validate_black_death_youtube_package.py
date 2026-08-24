#!/usr/bin/env python3
"""Validate the locked Black Death YouTube upload package."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "black-death-quarantine"
PACKAGE = EPISODE / "packaging" / "youtube-package-v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


data = json.loads(PACKAGE.read_text(encoding="utf-8"))
release = EPISODE / data["release_candidate"]["path"]
thumbnail = EPISODE / data["thumbnail"]["path"]
rights = EPISODE / data["rights_review_path"]
sync = EPISODE / data["final_sync_path"]

if data["status"] != "READY_FOR_PRIVATE_UPLOAD":
    fail("package status is not READY_FOR_PRIVATE_UPLOAD")
if data["channel"]["channel_id"] != "UCYqdIlpFlB6uh_cpIYgo85g":
    fail("wrong YouTube channel")
if not release.is_file() or sha256(release) != data["release_candidate"]["sha256"]:
    fail("release candidate hash mismatch")
if data["release_candidate"]["format"] != "longform" or data["release_candidate"]["aspect_ratio"] != "16:9":
    fail("223-second episode must remain 16:9 longform")
if not thumbnail.is_file() or sha256(thumbnail) != data["thumbnail"]["sha256"]:
    fail("thumbnail hash mismatch")
if len(data["title_candidates"]) != 5:
    fail("exactly five title candidates are required")
if data["selected_title"] not in {item["title"] for item in data["title_candidates"]}:
    fail("selected title is not one of the scored candidates")
if not data["description"].startswith("일부 장면은 역사·의학 자료를 바탕으로 AI로 재현했습니다."):
    fail("AI disclosure must be the first description line")
if data["ai_use"]["selection"] != "Yes":
    fail("AI use must be Yes")
if data["audience"] != "not_made_for_kids":
    fail("audience must be not made for kids")
if not data["rights_review_completed"] or not data["source_ids"]:
    fail("rights review or source IDs missing")
if not rights.is_file() or json.loads(rights.read_text(encoding="utf-8"))["status"] != "PASS":
    fail("rights lock missing or failed")
if not sync.is_file() or json.loads(sync.read_text(encoding="utf-8"))["status"] != "PASS":
    fail("final sync lock missing or failed")
if not data["idempotency_key"]:
    fail("idempotency key missing")
if data["release_window"]["lane"] != "b" or data["release_window"]["status"] != "WAITING_FOR_APPROVED_WINDOW":
    fail("release must wait for the approved lane B window")
if data["commerce_route"]["status"] == "eligible" and not data["commerce_route"]["exact_package_approved"]:
    fail("affiliate package is not approved")

print("PASS")
print(f"title: {data['selected_title']}")
print(f"release_sha256: {data['release_candidate']['sha256']}")
print(f"target_public_at: {data['release_window']['target_public_at']}")
print(f"idempotency_key: {data['idempotency_key']}")
