#!/usr/bin/env python3
"""Create script-anchored Korean word and sentence timestamps from approved TTS."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass
class ScriptToken:
    sentence_id: str
    index: int
    text: str
    normalized: str
    char_start: int
    char_end: int


def load_script(path: Path, expected_sentences: int) -> tuple[list[ScriptToken], list[dict], str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != expected_sentences:
        raise ValueError(
            f"expected {expected_sentences} non-empty script lines, got {len(lines)}"
        )
    tokens: list[ScriptToken] = []
    sentences: list[dict] = []
    cursor = 0
    token_index = 0
    chars: list[str] = []
    for sentence_index, line in enumerate(lines, 1):
        sid = f"s{sentence_index:02d}"
        start_index = token_index
        for raw in line.split():
            normalized = norm(raw)
            if not normalized:
                continue
            start = cursor
            cursor += len(normalized)
            chars.append(normalized)
            tokens.append(ScriptToken(sid, token_index, raw, normalized, start, cursor))
            token_index += 1
        sentences.append(
            {
                "sentence_id": sid,
                "text": line,
                "token_start_index": start_index,
                "token_end_index": token_index - 1,
            }
        )
    return tokens, sentences, "".join(chars)


def build_char_time_map(script_chars: str, asr_words: list[dict]) -> tuple[list[float | None], list[float | None], str, float]:
    asr_chars_parts: list[str] = []
    asr_char_times: list[tuple[float, float]] = []
    for word in asr_words:
        normalized = norm(word["text"])
        if not normalized:
            continue
        duration = max(0.001, float(word["end"]) - float(word["start"]))
        for i, ch in enumerate(normalized):
            asr_chars_parts.append(ch)
            asr_char_times.append(
                (
                    float(word["start"]) + duration * i / len(normalized),
                    float(word["start"]) + duration * (i + 1) / len(normalized),
                )
            )
    asr_chars = "".join(asr_chars_parts)
    matcher = difflib.SequenceMatcher(a=script_chars, b=asr_chars, autojunk=False)
    starts: list[float | None] = [None] * len(script_chars)
    ends: list[float | None] = [None] * len(script_chars)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            script_pos = block.a + offset
            asr_pos = block.b + offset
            starts[script_pos], ends[script_pos] = asr_char_times[asr_pos]
    ratio = matcher.ratio()
    return starts, ends, asr_chars, ratio


def interpolate_missing(values: list[float | None], fallback_end: float) -> list[float]:
    known = [i for i, value in enumerate(values) if value is not None]
    if not known:
        raise ValueError("alignment produced no matched character timestamps")
    result = [0.0] * len(values)
    for i, value in enumerate(values):
        if value is not None:
            result[i] = float(value)
            continue
        left = max((k for k in known if k < i), default=None)
        right = min((k for k in known if k > i), default=None)
        if left is None and right is not None:
            result[i] = max(0.0, float(values[right]) - 0.045 * (right - i))
        elif right is None and left is not None:
            result[i] = min(fallback_end, float(values[left]) + 0.045 * (i - left))
        elif left is not None and right is not None:
            span = right - left
            alpha = (i - left) / span
            result[i] = float(values[left]) * (1 - alpha) + float(values[right]) * alpha
    for i in range(1, len(result)):
        result[i] = max(result[i], result[i - 1])
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    parser.add_argument("--model", default="small")
    parser.add_argument("--download-root", type=Path, default=Path(".local-tools/models"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--episode-id", default="gas-hwalmyeongsu")
    parser.add_argument("--script-rel", default="final-script-v6.txt")
    parser.add_argument(
        "--audio-rel", default="tts/gas-hwalmyeongsu-v6-elevenlabs-take2.mp3"
    )
    parser.add_argument(
        "--receipt-rel",
        default="tts/gas-hwalmyeongsu-v6-elevenlabs-take2.receipt.json",
    )
    parser.add_argument(
        "--output-rel", default="tts/gas-hwalmyeongsu-v6-alignment.json"
    )
    parser.add_argument("--expected-sentences", type=int, default=37)
    args = parser.parse_args()

    episode = args.episode.resolve()
    script_path = episode / args.script_rel
    audio_path = episode / args.audio_rel
    receipt_path = episode / args.receipt_rel
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    audio_duration = float(receipt["duration_seconds"])
    if sha256(script_path) != receipt["script_sha256"]:
        raise ValueError("script hash does not match TTS receipt")
    if sha256(audio_path) != receipt["audio_sha256"]:
        raise ValueError("audio hash does not match TTS receipt")

    from faster_whisper import WhisperModel

    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
        download_root=str(args.download_root.resolve()),
        cpu_threads=8,
    )
    script_text = script_path.read_text(encoding="utf-8").strip()
    segments_iter, info = model.transcribe(
        str(audio_path),
        language="ko",
        beam_size=5,
        best_of=5,
        temperature=0.0,
        condition_on_previous_text=True,
        initial_prompt=script_text,
        word_timestamps=True,
        vad_filter=False,
    )
    raw_segments: list[dict] = []
    asr_words: list[dict] = []
    for segment in segments_iter:
        segment_words = []
        for word in segment.words or []:
            item = {
                "text": word.word,
                "start": round(float(word.start), 3),
                "end": round(float(word.end), 3),
                "probability": round(float(word.probability), 6),
            }
            segment_words.append(item)
            asr_words.append(item)
        raw_segments.append(
            {
                "id": segment.id,
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": segment.text,
                "words": segment_words,
            }
        )

    tokens, sentence_defs, script_chars = load_script(
        script_path, args.expected_sentences
    )
    char_starts, char_ends, asr_chars, similarity = build_char_time_map(script_chars, asr_words)
    starts = interpolate_missing(char_starts, audio_duration)
    ends = interpolate_missing(char_ends, audio_duration)

    aligned_tokens: list[dict] = []
    for token in tokens:
        start = starts[token.char_start]
        end = ends[token.char_end - 1]
        if end <= start:
            end = min(audio_duration, start + max(0.08, 0.045 * len(token.normalized)))
        aligned_tokens.append(
            {
                "token_index": token.index,
                "sentence_id": token.sentence_id,
                "text": token.text,
                "normalized": token.normalized,
                "start": round(start, 3),
                "end": round(end, 3),
            }
        )

    sentence_alignment: list[dict] = []
    for sentence in sentence_defs:
        start_i = sentence["token_start_index"]
        end_i = sentence["token_end_index"]
        sentence_alignment.append(
            {
                **sentence,
                "start": aligned_tokens[start_i]["start"],
                "end": aligned_tokens[end_i]["end"],
                "duration": round(aligned_tokens[end_i]["end"] - aligned_tokens[start_i]["start"], 3),
            }
        )

    coverage = sum(1 for value in char_starts if value is not None) / max(1, len(char_starts))
    errors = []
    if similarity < 0.90:
        errors.append(f"normalized character similarity too low: {similarity:.4f}")
    if coverage < 0.88:
        errors.append(f"matched character coverage too low: {coverage:.4f}")
    if len(aligned_tokens) == 0 or len(sentence_alignment) != args.expected_sentences:
        errors.append("incomplete token or sentence alignment")
    for i in range(1, len(aligned_tokens)):
        if aligned_tokens[i]["start"] + 0.001 < aligned_tokens[i - 1]["start"]:
            errors.append(f"non-monotonic token start at {i}")
            break
    if sentence_alignment[-1]["end"] > audio_duration + 0.05:
        errors.append("last sentence exceeds audio duration")

    output = {
        "schema_version": "body-invention.voice-alignment.v1",
        "episode_id": args.episode_id,
        "stage_id": "11_voice_alignment",
        "status": "PASS" if not errors else "FAIL",
        "provider": "local_faster_whisper_script_anchored_alignment",
        "model": args.model,
        "language": info.language,
        "language_probability": round(float(info.language_probability), 6),
        "script_path": args.script_rel,
        "script_sha256": sha256(script_path),
        "audio_path": args.audio_rel,
        "audio_sha256": sha256(audio_path),
        "audio_duration_seconds": audio_duration,
        "full_script_single_request": True,
        "sentence_level_stitching": False,
        "normalized_character_similarity": round(similarity, 6),
        "matched_character_coverage": round(coverage, 6),
        "recognized_normalized_character_count": len(asr_chars),
        "script_normalized_character_count": len(script_chars),
        "token_count": len(aligned_tokens),
        "sentence_count": len(sentence_alignment),
        "errors": errors,
        "words": aligned_tokens,
        "sentence_alignment": sentence_alignment,
        "raw_asr_segments": raw_segments,
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    out_path = episode / args.output_rel
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ["status", "normalized_character_similarity", "matched_character_coverage", "token_count", "sentence_count", "errors"]}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
