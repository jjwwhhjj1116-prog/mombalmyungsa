#!/usr/bin/env python3
"""Single-channel YouTube Data API v3 uploader for 몸의 발명사.

The command never discovers or falls back to other token files. It verifies the
OAuth-owned channel ID before opening the video and again after private upload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LIBS = ROOT / ".local-tools" / "youtube-api"
if LOCAL_LIBS.is_dir():
    sys.path.insert(0, str(LOCAL_LIBS))
PRIVATE_ROOT = ROOT / ".private" / "youtube"
CLIENT_FILE = PRIVATE_ROOT / "body-invention-oauth-client.json"
TOKEN_FILE = PRIVATE_ROOT / "body-invention-token.json"
LEDGER_FILE = PRIVATE_ROOT / "body-invention-upload-ledger.jsonl"

EXPECTED_CHANNEL_ID = "UCYqdIlpFlB6uh_cpIYgo85g"
EXPECTED_CHANNEL_NAME = "몸의 발명사"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"[BLOCKED] {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_libraries() -> None:
    try:
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        fail(
            "Install google-api-python-client, google-auth-oauthlib, and "
            "google-auth-httplib2 in the uploader runtime."
        )


def youtube_service(force_consent: bool = False):
    require_libraries()
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    credentials = None
    if TOKEN_FILE.is_file() and not force_consent:
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    if not credentials or not credentials.valid:
        if not CLIENT_FILE.is_file():
            fail(f"OAuth desktop client file is missing: {CLIENT_FILE}")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
        credentials = flow.run_local_server(
            host="localhost",
            port=0,
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true",
            open_browser=True,
        )
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def require_body_invention_channel(youtube) -> dict:
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items") or []
    if len(items) != 1:
        fail(f"OAuth token returned {len(items)} channels; expected exactly one")
    channel = items[0]
    actual_id = channel.get("id")
    actual_name = channel.get("snippet", {}).get("title", "")
    if actual_id != EXPECTED_CHANNEL_ID:
        fail(
            f"Expected {EXPECTED_CHANNEL_NAME} ({EXPECTED_CHANNEL_ID}), received "
            f"{actual_name!r} ({actual_id!r}). No upload was attempted."
        )
    return {"channel_id": actual_id, "channel_name": actual_name}


def safe_episode_asset(package_path: Path, relative: str) -> Path:
    episode_root = package_path.parent.parent.resolve()
    target = (episode_root / relative).resolve()
    try:
        target.relative_to(episode_root)
    except ValueError:
        fail(f"Package path escapes the episode directory: {relative}")
    return target


def load_package(package_path: Path) -> tuple[dict, Path, Path | None]:
    if not package_path.is_file():
        fail(f"YouTube package does not exist: {package_path}")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("schema_version") != "body-invention.youtube-package.v1":
        fail("Unsupported YouTube package schema")
    if package.get("status") != "READY_FOR_PRIVATE_UPLOAD":
        fail("Package status must be READY_FOR_PRIVATE_UPLOAD")
    if package.get("channel", {}).get("channel_id") != EXPECTED_CHANNEL_ID:
        fail("Package channel ID is not the locked 몸의 발명사 channel")
    if package.get("visibility") != "private":
        fail("The initial API upload must be private")
    if not package.get("source_ids"):
        fail("source_ids are missing")
    if package.get("rights_review_required") and not package.get("rights_review_completed"):
        fail("Rights review is incomplete")
    if not package.get("idempotency_key"):
        fail("idempotency_key is missing")
    ai_use = package.get("ai_use", {})
    if ai_use.get("required") and ai_use.get("selection") != "Yes":
        fail("AI use must be locked to Yes")

    release = package.get("release_candidate", {})
    video_path = safe_episode_asset(package_path, release.get("path", ""))
    if not video_path.is_file() or sha256(video_path) != release.get("sha256"):
        fail("Release candidate is missing or its SHA-256 differs")

    sync_rel = package.get("final_sync_path")
    if not sync_rel:
        fail("final_sync_path is missing")
    sync_path = safe_episode_asset(package_path, sync_rel)
    if not sync_path.is_file():
        fail("final-sync lock is missing")
    sync = json.loads(sync_path.read_text(encoding="utf-8"))
    if sync.get("status") != "PASS":
        fail("final-sync lock is not PASS")

    thumbnail_path = None
    thumbnail = package.get("thumbnail", {})
    if thumbnail.get("path"):
        thumbnail_path = safe_episode_asset(package_path, thumbnail["path"])
        if not thumbnail_path.is_file() or sha256(thumbnail_path) != thumbnail.get("sha256"):
            fail("Thumbnail is missing or its SHA-256 differs")
    return package, video_path, thumbnail_path


def ledger_contains(idempotency_key: str) -> bool:
    if not LEDGER_FILE.is_file():
        return False
    for line in LEDGER_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            fail("Upload ledger contains invalid JSON")
        if record.get("idempotency_key") == idempotency_key:
            return True
    return False


def append_ledger(record: dict) -> None:
    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    with LEDGER_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def upload_private(youtube, package: dict, video_path: Path, thumbnail_path: Path | None) -> dict:
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": package["selected_title"],
            "description": package["description"],
            "categoryId": "27" if package.get("category") == "Education" else "22",
            "defaultLanguage": package.get("language", "ko"),
            "defaultAudioLanguage": package.get("language", "ko"),
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": package.get("audience") == "made_for_kids",
            "containsSyntheticMedia": bool(package.get("ai_use", {}).get("required")),
            "embeddable": True,
            "license": "youtube",
        },
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(
            str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True
        ),
        notifySubscribers=False,
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]

    items = youtube.videos().list(
        part="snippet,status,processingDetails", id=video_id
    ).execute().get("items", [])
    if len(items) != 1:
        fail(f"Private upload {video_id} could not be verified")
    delivered = items[0]
    delivered_channel_id = delivered.get("snippet", {}).get("channelId")
    if delivered_channel_id != EXPECTED_CHANNEL_ID:
        fail(f"Post-upload channel mismatch for private video {video_id}; publishing is blocked")

    if thumbnail_path:
        youtube.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))
        ).execute()
    return {
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "channel_id": delivered_channel_id,
        "privacy_status": delivered.get("status", {}).get("privacyStatus"),
        "processing_status": delivered.get("processingDetails", {}).get("processingStatus"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="몸의 발명사 전용 YouTube API 업로더")
    parser.add_argument("--auth", action="store_true", help="Create the dedicated OAuth token")
    parser.add_argument("--whoami", action="store_true", help="Verify the token and channel ID")
    parser.add_argument("--package", type=Path, help="Locked YouTube package JSON")
    parser.add_argument("--run", action="store_true", help="Perform the private upload")
    args = parser.parse_args()

    if args.auth:
        identity = require_body_invention_channel(youtube_service(force_consent=True))
        print(json.dumps({"status": "PASS", **identity}, ensure_ascii=False, indent=2))
        return 0
    if args.whoami:
        identity = require_body_invention_channel(youtube_service())
        print(json.dumps({"status": "PASS", **identity}, ensure_ascii=False, indent=2))
        return 0
    if not args.package:
        parser.error("Use --auth, --whoami, or --package")

    package_path = args.package.resolve()
    package, video_path, thumbnail_path = load_package(package_path)
    if ledger_contains(package["idempotency_key"]):
        fail("The idempotency key already exists in the private upload ledger")
    print(json.dumps({
        "status": "VALIDATED",
        "episode_id": package["episode_id"],
        "channel_id": package["channel"]["channel_id"],
        "video_sha256": package["release_candidate"]["sha256"],
        "title": package["selected_title"],
        "visibility": "private",
        "idempotency_key": package["idempotency_key"],
    }, ensure_ascii=False, indent=2))
    if not args.run:
        return 0

    youtube = youtube_service()
    identity = require_body_invention_channel(youtube)
    result = upload_private(youtube, package, video_path, thumbnail_path)
    record = {
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "episode_id": package["episode_id"],
        "idempotency_key": package["idempotency_key"],
        "release_sha256": package["release_candidate"]["sha256"],
        "oauth_channel_id": identity["channel_id"],
        **result,
    }
    append_ledger(record)
    print(json.dumps({"status": "PRIVATE_UPLOAD_VERIFIED", **record}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
