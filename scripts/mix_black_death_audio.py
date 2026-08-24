#!/usr/bin/env python3
"""Mix the approved narration and frame-aligned edit SFX into the chunked video."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "black-death-quarantine"
PUBLIC = ROOT / "video" / "public"
SEMANTIC = json.loads((ROOT / "video" / "src" / "data" / "black-death-v1-semantic.json").read_text(encoding="utf-8"))
TIMELINE = json.loads((ROOT / "video" / "src" / "data" / "black-death-v1-timeline.json").read_text(encoding="utf-8"))


def main() -> int:
    video = EPISODE / "renders" / "black-death-v1-video-only.mp4"
    voice = PUBLIC / TIMELINE["audio_asset"]
    output = EPISODE / "renders" / "black-death-v1-final.mp4"
    command = ["ffmpeg", "-y", "-i", str(video), "-i", str(voice)]
    filters = ["[1:a]aresample=48000,volume=1.0[voice]"]
    mix_inputs = ["[voice]"]
    for index, event in enumerate(SEMANTIC["semantic_events"]):
        sound = PUBLIC / "sfx" / event["sound_asset"]
        command.extend(["-i", str(sound)])
        delay = round(event["start_frame"] / TIMELINE["fps"] * 1000)
        volume = 0.16 if event["kind"] == "death_toll" else 0.105
        label = f"sfx{index}"
        filters.append(f"[{index + 2}:a]aresample=48000,volume={volume},adelay={delay}|{delay}[{label}]")
        mix_inputs.append(f"[{label}]")
    duration = TIMELINE["total_frames"] / TIMELINE["fps"]
    filters.append(
        "".join(mix_inputs)
        + f"amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=0:normalize=0,"
        + f"alimiter=limit=0.95,apad=pad_dur=0.05,atrim=0:{duration:.6f}[aout]"
    )
    command.extend(
        [
            "-filter_complex", ";".join(filters),
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-metadata", "comment=몸의 발명사 흑사병 v1",
            str(output),
        ]
    )
    subprocess.run(command, check=True)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
