#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


ROLES = [
    "hook_present",
    "hook_feeling",
    "hook_contradiction",
    "past_entry",
    "mechanism",
    "escalation_1",
    "escalation_2",
    "dilemma",
    "impasse",
    "reversal_question",
    "reversal_action",
    "solution",
    "unexpected",
    "proof",
    "meaning",
    "loop",
]

CONTRACT_FIELDS = [
    "intent",
    "present_anchor",
    "assumption",
    "contradiction",
    "protagonist",
    "unavoidable_mechanism",
    "escalation",
    "double_bind",
    "old_question",
    "new_question",
    "concrete_action",
    "unexpected_result",
    "proof",
    "present_return",
    "meaning",
]

BEAT_TEXT_FIELDS = [
    "role",
    "narration",
    "emotion",
    "purpose",
    "transition",
    "fact_status",
    "media_kind",
]

SHOT_TEXT_FIELDS = [
    "shot_id",
    "trigger_phrase",
    "subject_focus",
    "anchor_id",
    "camera_move",
    "camera_easing",
    "overlay",
    "transition",
    "causal_purpose",
    "asset_route",
]

SOUND_TEXT_FIELDS = [
    "sound_id",
    "trigger_phrase",
    "kind",
    "asset_key",
    "source_policy",
    "sync",
    "duration_policy",
    "causal_purpose",
]

SOUND_KINDS = {"diegetic", "editorial", "transition", "music", "intentional_silence"}
SOUND_SOURCE_POLICIES = {
    "generated_native_if_clean_else_edit",
    "edit_primary",
    "intentional_silence",
}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def ending_family(line):
    spoken = line.strip().rstrip('"”’')
    if spoken.endswith("?"):
        return "question"
    clean = re.sub(r"[\s.!?,…'\"”’]+$", "", spoken)
    if clean.endswith("죠"):
        return "jyo"
    if clean.endswith("요"):
        return "yo"
    if clean.endswith("니다"):
        return "nida"
    if clean.endswith("다"):
        return "da"
    if len(clean.split()) <= 3:
        return "short_declaration"
    return "other"


def longest_family_run(families, target=None):
    longest = 0
    current = 0
    previous = None
    for family in families:
        if target is not None:
            current = current + 1 if family == target else 0
        elif family == previous:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        previous = family
    return longest


def main():
    if len(sys.argv) != 2:
        print("usage: validate_episode.py <episode.json>")
        return 2

    path = Path(sys.argv[1])
    errors = []
    warnings = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"valid": False, "errors": [f"JSON read error: {exc}"]}, ensure_ascii=False, indent=2))
        return 1

    if data.get("brand") != "몸의 발명사":
        warnings.append("brand should be ‘몸의 발명사’; keep timemedic only as the invocation name")

    contract = data.get("story_contract", {})
    for field in CONTRACT_FIELDS:
        if not nonempty(contract.get(field)):
            errors.append(f"story_contract.{field} is required")
    if contract.get("old_question") == contract.get("new_question"):
        errors.append("old_question and new_question must be different")

    research = data.get("research", [])
    if len(research) < 2:
        errors.append("at least two research sources are required")
    if research and not any(item.get("source_type") == "primary" for item in research):
        warnings.append("include at least one primary or official source when possible")

    approval = data.get("approval", {})
    if approval.get("requires_human_approval") is not True:
        errors.append("approval.requires_human_approval must be true")
    if approval.get("human_approved") is not False:
        warnings.append("episode blueprint should remain human_approved=false until the user approves it")
    if approval.get("publishable") is not False:
        warnings.append("episode blueprint should remain publishable=false until final checks pass")

    beats = data.get("beats", [])
    if len(beats) != 16:
        errors.append(f"exactly 16 beats are required; found {len(beats)}")
    roles = [beat.get("role") for beat in beats]
    if roles != ROLES:
        errors.append("beat roles must match the required 16-role order")

    shot_ids = set()
    total_shots = 0
    camera_events = 0
    generative_video_events = 0

    for index, beat in enumerate(beats, start=1):
        if beat.get("id") is None:
            errors.append(f"beat {index}: id is required")
        for field in BEAT_TEXT_FIELDS:
            if not nonempty(beat.get(field)):
                errors.append(f"beat {index}: {field} is required")
        if "tts_tag" not in beat:
            errors.append(f"beat {index}: tts_tag key is required; use an empty string when no tag is needed")

        narration = beat.get("narration", "")
        direction_track = beat.get("direction_track")
        if not isinstance(direction_track, list):
            errors.append(f"beat {index}: direction_track must be an array")
            continue
        if not 1 <= len(direction_track) <= 3:
            errors.append(f"beat {index}: direction_track must contain 1-3 semantic shots; found {len(direction_track)}")

        total_shots += len(direction_track)
        for shot_index, shot in enumerate(direction_track, start=1):
            label = f"beat {index} shot {shot_index}"
            for field in SHOT_TEXT_FIELDS:
                if not nonempty(shot.get(field)):
                    errors.append(f"{label}: {field} is required")

            shot_id = shot.get("shot_id")
            if nonempty(shot_id):
                if shot_id in shot_ids:
                    errors.append(f"{label}: duplicate shot_id {shot_id}")
                shot_ids.add(shot_id)

            phrase = shot.get("trigger_phrase", "")
            if nonempty(phrase) and phrase not in narration:
                errors.append(f"{label}: trigger_phrase must occur verbatim in narration: {phrase}")

            duration = shot.get("duration_seconds")
            if not isinstance(duration, (int, float)) or isinstance(duration, bool):
                errors.append(f"{label}: duration_seconds must be numeric")
            elif not 0.6 <= float(duration) <= 3.2:
                warnings.append(f"{label}: duration_seconds {duration} is outside the normal 0.6-3.2 range")

            if shot.get("camera_move") not in (None, "hold"):
                camera_events += 1
            if shot.get("asset_route") == "generative_video":
                generative_video_events += 1
            if "random" in str(shot.get("camera_move", "")).lower():
                errors.append(f"{label}: random camera motion is forbidden")
            if len(str(shot.get("causal_purpose", "")).strip()) < 12:
                warnings.append(f"{label}: causal_purpose may be too vague")

    if not 28 <= total_shots <= 40:
        errors.append(f"28-40 semantic shots are required; found {total_shots}")

    storyboard_contract = data.get("storyboard_contract", {})
    if storyboard_contract.get("one_sentence_one_scene") is not True:
        errors.append("storyboard_contract.one_sentence_one_scene must be true")
    required_triplet = storyboard_contract.get("required_triplet", [])
    if set(required_triplet) != {"dialogue", "scene", "emotion"}:
        errors.append("storyboard_contract.required_triplet must contain dialogue, scene, emotion")

    typography = data.get("typography", {})
    if typography.get("font_family") != "Gmarket Sans Bold":
        errors.append("typography.font_family must be Gmarket Sans Bold")
    if typography.get("main_text_size_px", typography.get("font_size_px")) != 100:
        errors.append("typography main text size must be 100px")
    if typography.get("stroke_width_px") != 30:
        errors.append("typography.stroke_width_px must be 30px")
    if typography.get("shadow_required") is not True:
        errors.append("typography.shadow_required must be true")
    if typography.get("anchor_x_px") != 540 or typography.get("anchor_y_px") != 1200:
        errors.append("typography caption center must be x=540px, y=1200px")
    if typography.get("anchor_y_ratio") != 0.625:
        errors.append("typography.anchor_y_ratio must be 0.625 (10/16 from top)")

    script_ref = data.get("approved_script_path")
    script_candidates = []
    ending_counts = {}
    ending_families = []
    if nonempty(script_ref):
        script_candidates.extend([Path.cwd() / script_ref, path.parent / script_ref])
    script_path = next((candidate for candidate in script_candidates if candidate.exists()), None)
    if script_path is None:
        errors.append("approved_script_path could not be resolved")
    else:
        sentence_lines = [
            line.strip()
            for line in script_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(sentence_lines) != total_shots:
            errors.append(
                f"one-sentence-one-scene mismatch: {len(sentence_lines)} script lines for {total_shots} shots"
            )
        ending_families = [ending_family(line) for line in sentence_lines]
        ending_counts = {
            family: ending_families.count(family)
            for family in sorted(set(ending_families))
        }
        nida_count = ending_counts.get("nida", 0)
        if longest_family_run(ending_families, "nida") >= 3:
            errors.append("spoken-ending rhythm failed: ~니다 family appears 3 or more sentences in a row")
        if len(sentence_lines) >= 10 and nida_count / len(sentence_lines) > 0.45:
            errors.append(
                f"spoken-ending rhythm failed: ~니다 family is {nida_count}/{len(sentence_lines)} sentences (>45%)"
            )
        varied_families = {
            family
            for family in ending_families
            if family in {"nida", "jyo", "yo", "da", "question", "short_declaration"}
        }
        if len(sentence_lines) >= 10 and len(varied_families) < 3:
            errors.append(
                "spoken-ending rhythm failed: use at least 3 ending families among ~니다, ~죠, ~요, ~다, question, and short declaration"
            )
        if longest_family_run(ending_families) >= 4:
            warnings.append("spoken-ending rhythm may sound mechanical: the same ending family repeats 4 or more times")
    if camera_events < 16:
        warnings.append(f"camera event density may be too low; found {camera_events}")
    if not 4 <= generative_video_events <= 14:
        warnings.append(f"use about 4-14 generative video shot events; found {generative_video_events}")

    by_role = {beat.get("role"): beat for beat in beats}
    all_narration = " ".join(beat.get("narration", "") for beat in beats)
    if "환장할 노릇" in all_narration:
        errors.append("body invention scripts must not use the retired phrase ‘환장할 노릇이었죠’")
    impasse_signature = "여러분, 이거 정말 미치고 팔짝 뛸 노릇 아니겠습니까?"
    if by_role.get("impasse", {}).get("narration", "").count(impasse_signature) != 1:
        errors.append(
            "impasse beat must contain the body-invention impasse signature exactly once: "
            f"‘{impasse_signature}’"
        )
    reversal_narration = " ".join(
        [
            by_role.get("reversal_question", {}).get("narration", ""),
            by_role.get("reversal_action", {}).get("narration", ""),
        ]
    )
    middle_signature = "그래서, 사람을 살리는 질문부터 뒤집습니다."
    if reversal_narration.count(middle_signature) != 1:
        warnings.append(
            "reversal question/action beats should contain the body-invention middle signature exactly once: "
            f"‘{middle_signature}’"
        )
    if "예상하지 못한" not in by_role.get("unexpected", {}).get("narration", ""):
        warnings.append("unexpected beat should mark the result beyond the original intent")
    loop_narration = by_role.get("loop", {}).get("narration", "")
    valid_signature_ending = loop_narration.endswith("은 이렇게 탄생했습니다.") or loop_narration.endswith(
        "는 이렇게 탄생했습니다."
    )
    if "몸을 살린 생각의 전환," not in loop_narration or not valid_signature_ending:
        warnings.append(
            "loop beat should use the body-invention ending signature: "
            "‘몸을 살린 생각의 전환, [대상]은/는 이렇게 탄생했습니다.’"
        )

    video_count = sum(beat.get("media_kind") == "video" for beat in beats)
    if not 4 <= video_count <= 6:
        warnings.append(f"use 4-6 generative-video story beats for cost control; found {video_count}")

    narration = " ".join(beat.get("narration", "").strip() for beat in beats)
    if len(narration) < 300:
        warnings.append(f"narration may be too thin for a complete story: {len(narration)} characters")
    if len(narration) > 1100:
        warnings.append(f"narration may be too dense for short-form delivery: {len(narration)} characters")

    sound_design = data.get("sound_design")
    if not isinstance(sound_design, dict):
        errors.append("sound_design object is required")
    elif sound_design.get("enabled") is not True:
        errors.append("sound_design.enabled must be true")

    sound_events = data.get("sound_events", [])
    if not isinstance(sound_events, list):
        errors.append("sound_events must be an array")
        sound_events = []
    elif not 8 <= len(sound_events) <= 24:
        errors.append(f"8-24 semantic sound events are required; found {len(sound_events)}")

    beat_by_id = {beat.get("id"): beat for beat in beats}
    sound_ids = set()
    for index, event in enumerate(sound_events, start=1):
        label = f"sound event {index}"
        for field in SOUND_TEXT_FIELDS:
            if not nonempty(event.get(field)):
                errors.append(f"{label}: {field} is required")

        sound_id = event.get("sound_id")
        if nonempty(sound_id):
            if sound_id in sound_ids:
                errors.append(f"{label}: duplicate sound_id {sound_id}")
            sound_ids.add(sound_id)

        beat = beat_by_id.get(event.get("beat_id"))
        if beat is None:
            errors.append(f"{label}: beat_id must refer to an existing beat")
        else:
            phrase = event.get("trigger_phrase", "")
            if nonempty(phrase) and phrase not in beat.get("narration", ""):
                errors.append(f"{label}: trigger_phrase must occur verbatim in its beat narration: {phrase}")

        if event.get("kind") not in SOUND_KINDS:
            errors.append(f"{label}: unsupported kind {event.get('kind')}")
        if event.get("source_policy") not in SOUND_SOURCE_POLICIES:
            errors.append(f"{label}: unsupported source_policy {event.get('source_policy')}")

        lead_frames = event.get("lead_frames")
        if not isinstance(lead_frames, int) or isinstance(lead_frames, bool) or not 0 <= lead_frames <= 6:
            errors.append(f"{label}: lead_frames must be an integer from 0 to 6")

        gain_db = event.get("gain_db")
        if not isinstance(gain_db, (int, float)) or isinstance(gain_db, bool) or not -48 <= float(gain_db) <= 3:
            errors.append(f"{label}: gain_db must be numeric from -48 to 3")

        duck_music_db = event.get("duck_music_db")
        if not isinstance(duck_music_db, (int, float)) or isinstance(duck_music_db, bool) or not -18 <= float(duck_music_db) <= 0:
            errors.append(f"{label}: duck_music_db must be numeric from -18 to 0")

        if len(str(event.get("causal_purpose", "")).strip()) < 12:
            warnings.append(f"{label}: causal_purpose may be too vague")

    result = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "beats": len(beats),
            "semantic_shots": total_shots,
            "camera_events": camera_events,
            "generative_video_shots": generative_video_events,
            "video_beats": video_count,
            "narration_characters": len(narration),
            "research_sources": len(research),
            "sound_events": len(sound_events),
            "ending_families": ending_counts,
            "longest_same_ending_run": longest_family_run(ending_families) if ending_families else 0,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
