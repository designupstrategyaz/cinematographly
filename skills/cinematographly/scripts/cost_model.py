#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
cost_model.py — the ONE formula that turns a video's shape into credits, used by both quoting tools.

Until v2.62.0 the per-video estimator (estimate_duration.py) and the batch planner (batch_plan.py) priced
the same video differently: one on the quality preset with a flat price per dialogue line, the other on
the client's `default_preset` (economy in the template) per second of dialogue, with the retake factor
applied to different things. On the sample client they answered 543 and 146.5 credits for comparable
videos [measured 2026-11-14]. A studio quoting from either tool got a different number for one job.

The rules this module holds, in one place:

  * The preset is QUALITY unless the caller asks for economy by name. The quality floor (SKILL.md §4,
    item 11) means a cheaper preset is a different picture, so economy is only ever a labelled comparison.
  * Dialogue is priced per second of generated clip (`dialogue_clip_per_second`). Only a cost file without
    that key falls back to a flat price per clip (`kling_dialogue`), and the result says which basis it used.
  * Every clip, dialogue and B-roll, needs a start frame.
  * The retake factor (`retry`) applies to what is generated: clips and frames. Voice-over is not re-rolled
    with the picture, so it is added after.

  python3 cost_model.py --selftest

What it cannot do: it does not know which model a preset stands for. The preset's numbers come from
`rate_card.py` (assets/higgsfield-rates.json); this module only adds them up the same way every time.
"""
from __future__ import annotations
import sys

FLOOR_PRESET = "quality"
REQUIRED = ("start_frame", "broll", "voiceover_line", "retry")


def pick_preset(costs: dict, economy: bool = False) -> tuple[str, dict]:
    """(name, preset). Quality unless economy is asked for by name; a cost file's `default_preset` is not
    consulted, because a default below the floor is how the two tools came to disagree."""
    name = "economy" if economy else FLOOR_PRESET
    presets = (costs or {}).get("presets") or {}
    if name not in presets:
        raise KeyError(f"the cost file has no {name!r} preset (it needs 'quality', and 'economy' for comparisons)")
    missing = [k for k in REQUIRED if k not in presets[name]]
    if "dialogue_clip_per_second" not in presets[name] and "kling_dialogue" not in presets[name]:
        missing.append("dialogue_clip_per_second")
    if missing:
        raise KeyError(f"preset {name!r} is missing {', '.join(missing)}")
    return name, presets[name]


def video_credits(preset: dict, dialogue_clips: int, dialogue_seconds: float, broll_clips: int) -> dict:
    """Credits for one video of this shape, with the parts and the dialogue basis named."""
    per_s = preset.get("dialogue_clip_per_second")
    if per_s is not None:
        dialogue, basis = dialogue_seconds * float(per_s), f"{float(per_s):g} cr/s x {dialogue_seconds:g} s"
    else:
        dialogue, basis = dialogue_clips * float(preset["kling_dialogue"]), \
            f"{float(preset['kling_dialogue']):g} cr/clip x {dialogue_clips} (no per-second rate in the cost file)"
    frames = (dialogue_clips + broll_clips) * float(preset["start_frame"])
    broll = broll_clips * float(preset["broll"])
    generated = dialogue + broll + frames
    retry = float(preset["retry"])
    vo = dialogue_clips * float(preset["voiceover_line"])
    return {"dialogue": dialogue, "dialogue_basis": basis, "broll": broll, "frames": frames,
            "retakes": generated * retry - generated, "voiceover": vo, "retry": retry,
            "total": generated * retry + vo}


def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    costs = {"default_preset": "economy", "presets": {
        "economy": {"start_frame": 2, "broll": 10, "voiceover_line": 0.6, "retry": 1.15, "dialogue_clip_per_second": 2.5},
        "quality": {"start_frame": 2, "broll": 36, "voiceover_line": 0.6, "retry": 1.3, "dialogue_clip_per_second": 2.5}}}
    name, p = pick_preset(costs)
    check("quality is chosen although the file's default_preset says economy", name == "quality" and p["broll"] == 36)
    check("economy only when asked for by name", pick_preset(costs, economy=True)[0] == "economy")
    r = video_credits(p, dialogue_clips=4, dialogue_seconds=20.0, broll_clips=6)
    # dialogue 2.5 x 20 = 50; broll 6 x 36 = 216; frames 10 x 2 = 20; generated 286; x1.3 = 371.8; vo 4 x 0.6 = 2.4
    check("the arithmetic: (50 + 216 + 20) x 1.3 + 2.4 = 374.2", abs(r["total"] - 374.2) < 1e-6)
    check("voice-over is not multiplied by the retake factor", abs(r["voiceover"] - 2.4) < 1e-9 and abs(r["retakes"] - 85.8) < 1e-6)
    check("dialogue is priced per second and says so", r["dialogue"] == 50 and "cr/s" in r["dialogue_basis"])
    flat = dict(p); flat.pop("dialogue_clip_per_second"); flat["kling_dialogue"] = 45
    rf = video_credits(flat, 4, 20.0, 6)
    check("a file with no per-second rate falls back to per clip, and says so", rf["dialogue"] == 180 and "no per-second" in rf["dialogue_basis"])
    bad = {"presets": {"quality": {"start_frame": 2, "broll": 36, "retry": 1.3}}}
    try:
        pick_preset(bad); check("a preset missing keys is refused, naming them", False)
    except KeyError as e:
        check("a preset missing keys is refused, naming them", "voiceover_line" in str(e) and "dialogue_clip_per_second" in str(e))
    print("-" * 60)
    print("selftest OK" if ok else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
