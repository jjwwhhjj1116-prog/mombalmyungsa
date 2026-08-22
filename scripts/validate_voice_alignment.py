#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return "".join(ch for ch in text if ch.isalnum() or "가" <= ch <= "힣")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    args = parser.parse_args()
    episode = args.episode.resolve()
    script_path = episode / "final-script-v6.txt"
    audio_path = episode / "tts" / "gas-hwalmyeongsu-v6-elevenlabs-take2.mp3"
    receipt_path = episode / "tts" / "gas-hwalmyeongsu-v6-elevenlabs-take2.receipt.json"
    alignment_path = episode / "tts" / "gas-hwalmyeongsu-v6-alignment.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    errors = []
    if alignment.get("status") != "PASS":
        errors.append("alignment status must be PASS")
    if sha256(script_path) != receipt.get("script_sha256") or sha256(script_path) != alignment.get("script_sha256"):
        errors.append("script hash mismatch")
    if sha256(audio_path) != receipt.get("audio_sha256") or sha256(audio_path) != alignment.get("audio_sha256"):
        errors.append("audio hash mismatch")
    if receipt.get("generation_strategy") != "full_script_single_request" or receipt.get("sentence_level_stitching") is not False:
        errors.append("TTS must be one full-script request with no sentence stitching")
    lines = [line.strip() for line in script_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_tokens = [token for line in lines for token in line.split() if norm(token)]
    words = alignment.get("words", [])
    sentences = alignment.get("sentence_alignment", [])
    if len(lines) != 37 or len(sentences) != 37:
        errors.append("script and alignment must both contain 37 sentences")
    if len(words) != len(expected_tokens):
        errors.append(f"token count mismatch: {len(words)} != {len(expected_tokens)}")
    for i, (expected, word) in enumerate(zip(expected_tokens, words)):
        if norm(expected) != word.get("normalized"):
            errors.append(f"token {i} normalized text mismatch")
            break
        if word.get("token_index") != i:
            errors.append(f"token {i} index mismatch")
            break
        if float(word.get("end", -1)) <= float(word.get("start", -1)):
            errors.append(f"token {i} has non-positive duration")
            break
        if i and float(word.get("start", 0)) + 0.001 < float(words[i - 1].get("start", 0)):
            errors.append(f"token {i} starts before previous token")
            break
    previous_end = -1.0
    for i, sentence in enumerate(sentences, 1):
        if sentence.get("sentence_id") != f"s{i:02d}":
            errors.append(f"sentence order mismatch at {i}")
            break
        start = float(sentence.get("start", -1))
        end = float(sentence.get("end", -1))
        if end <= start:
            errors.append(f"s{i:02d} has non-positive duration")
        if start + 0.001 < previous_end:
            errors.append(f"s{i:02d} overlaps prior sentence")
        previous_end = end
    duration = float(receipt.get("duration_seconds"))
    if sentences and abs(float(sentences[-1].get("end")) - duration) > 0.30:
        errors.append("last spoken word must end within 300ms of audio duration")
    if float(alignment.get("normalized_character_similarity", 0)) < 0.90:
        errors.append("normalized character similarity below 0.90")
    if float(alignment.get("matched_character_coverage", 0)) < 0.88:
        errors.append("matched character coverage below 0.88")
    result = {"status": "PASS" if not errors else "FAIL", "errors": errors, "token_count": len(words), "sentence_count": len(sentences)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
