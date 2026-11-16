#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""prompt_lint.py — the prompt gate. A generation prompt is a FILE with a shape, linted before any
credit is spent, and the gate (gate.py) refuses a generate_* call whose text is not byte-identical
to a prompt this lint passed.

Why (2026-09-06). The skill's nine non-negotiables gated claims, compliance, disclosure, script,
quality floor, review tier, realism, persuasion and the join — and nothing gated the PROMPT. The
816-line prompting reference was "extended", reached by one table row, and a run that never opened
it produced generations that made no sense. QA fires AFTER generation; this fires before.

  prompt_lint.py 01-script/prompts/S3.clip.prompt.md        lint one file; writes S3.clip.prompt.ok
  prompt_lint.py 01-script/prompts/                          lint every *.prompt.md in a folder
  prompt_lint.py FILE --json                                 machine-readable findings
  prompt_lint.py 01-script/prompts/ --plan [--json]          THE REFERENCE PLAN: every shot's
                                                             references, what each carries, whether
                                                             it is sourced and cleared — before a
                                                             single credit is spent
  prompt_lint.py --template clip|frame|edit|multishot|family|genjutsu  print the file shape to start from
  prompt_lint.py --selftest

Exit codes: 0 pass · 1 findings · 2 usage/IO error.

The two shapes (prompting-craft.md §1 and §11 item 1 — the i2v/t2v fork, now applied)
--------------------------------------------------------------------------------------
  kind: frame  — authors the START FRAME with an image model. Carries the picture: [SUBJECT]
                 [ENVIRONMENT] [LIGHTING] [CAMERA] [STYLE] (+ [CHARACTER] fixed block, [SAFE ZONE]).
  kind: clip   — animates an APPROVED frame (i2v). Carries motion only: [MOTION] START/MID/END,
                 [CAMERA], [PERFORMANCE] for faces, [SPEECH] for native audio. It must NOT re-describe
                 the picture — every vendor names that as the error, and it is how a frame a human
                 approved gets overruled by an adjective.
  kind: edit   — (v2.45) an IMAGE EDIT: one concept changed in a picture that exists (`edit_of:`), the rest
                 kept: [SOURCE] [KEEP] [CHANGE] [LIGHT MATCH] [OUTPUT], + [REFERENCES] when refs exist. `use:
                 target` (the result becomes a model reference) needs `gate.py approve target:<SHOT>`.
  kind: genjutsu — (v2.46.1) a GENJUTSU SPEC, not a prompt: Higgsfield's motion transfer (copy a driving
                 video's motion onto reference subjects) or object swap (replace an object in a source video).
                 Frontmatter carries the whole call — model (full or Lite), mode, resolution, the ONE source
                 video, the reference images, rights, free_gens — plus [QA] (the measured check, never sent) and
                 an optional [PROMPT] (sent verbatim when present). `gate.py approve genjutsu:<SHOT>` signs it.
  Both may end with [SUPPRESS]: a comma-separated NOUN list (Veo's rule: describe what you don't
  want, never "no X"). It is kept OUT of the prompt text and emitted as `negative_prompt` by
  gate.py preflight, because a negative inside the positive prompt can summon the thing (§5.2).
  (v2.71.0) On a model with NO negative field the same noun list is [CONSTRAINTS], the prompt's last
  block, sent inside it (a [SUPPRESS] there is dropped). `--route <model>` says which.

What it checks (each finding cites the reference that owns the rule)
--------------------------------------------------------------------
  shape     required blocks per kind; forbidden picture-blocks in a clip; START/MID/END in [MOTION]
  casting   clip model on the roster; resolution row exists and is ≥ 1080p (the quality floor);
            duration inside the model's measured range (rate table, never clamped silently)
  frame     the clip's start_frame file exists (sha recorded, gate compares it to the approval)
  language  quality-word stacking · director/artist invocation · "begins to" hedging · command
            phrasing · "no X" negatives in positive blocks · more than one camera behaviour ·
            a dialogue line longer than the clip · a negative emotional STATE on a reference frame ·
            text/logo rendering asked of the model · the two-shot "X next to Y" trap
  identity  a [CHARACTER] block byte-identical to the job's locked _reference/CHARACTER-<name>.md
            when one exists (series-continuity.md §6.2 — the freeze)
  function  a B-roll clip declares `function:` (shot-handoff.md — every insert has a job)
  (v2.45)   the MODEL's prompt ceiling and negative cap (assets/higgsfield-rates.json → call_contract,
            prompt_limits; the band becomes a WARN where the ceiling is higher) · the detail score per kind ·
            filler words · "watermark" · signs under a bare text ban · "no music" on a sounding clip ·
            the framing line when video and image references share a call (prompting-craft.md §11g)

What it cannot do
-----------------
- It cannot tell you the prompt is GOOD. It catches the vendor-documented errors and the house
  shape; whether the motion beat is the right beat is direction.md's job and a human's.
- It cannot see the start frame. It records the file's hash so the gate can prove the clip was
  generated from the still that was approved, not that the still is right.
- Its word lists are finite. A director's name it does not recognise passes; write physical
  language (style-transfer.md) and it never comes up.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import job_tier as _JT  # noqa: E402  the evaluation tier (house decision 2026-10-25)
import switches as _SW  # noqa: E402  (v2.48.0, project switches: the `ramp:` field's speed-conform and music-led cases)
SKILL_ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(SKILL_ROOT, "assets")
LINT_VERSION = 1
SHOT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,30}$")   # identical to gate.SHOT_RE
IMAGE_MODEL_HINT = ("nano_banana", "soul", "flux", "seedream", "imagen", "gpt_image", "ideogram",
                    "marketing_studio_image", "higgsfield_image", "recraft", "midjourney")

# --- the reference plan (2026-09-06) -----------------------------------------------------------
# "Reference the nouns, prompt the verbs" (prompting-craft.md §6b; character-and-props.md §8).
# ONE reference carries ONE attribute (refinement-loop.md §1) — that is what keeps you inside the
# slot budget and what makes a failure attributable when the output is wrong. Each attribute below
# maps to the words that would RE-DESCRIBE it: if a reference carries wardrobe, wardrobe adjectives
# in the prompt do not add information, they compete with the pixels the reference already supplies.
REF_ATTRS = {
    "character": ["face", "cheekbone", "jawline", "eye colour", "eye color", "hair", "freckle",
                  "complexion", "age", "years old", "beard", "moustache", "eyebrow"],
    "wardrobe":  ["apron", "shirt", "jacket", "coat", "dress", "uniform", "hat", "scarf", "glasses",
                  "wearing", "collar", "sleeve", "knit", "denim", "linen", "boots", "shoes"],
    "prop":      ["bottle", "glass", "jar", "tin", "box", "pack", "label", "carton", "tool",
                  "phone", "cup", "tray", "knife", "basket"],
    "environment": ["room", "kitchen", "wall", "window", "floor", "counter", "shelf", "grove",
                    "field", "street", "office", "studio", "table", "background", "behind"],
    "light":     ["kelvin", "5200k", "3200k", "sunlight", "window light", "softbox", "backlit",
                  "golden hour", "overcast", "practical", "key light", "fill", "shadow"],
    "palette":   ["#", "hex", "colour palette", "color palette", "teal", "amber", "olive green"],
    "motion":    ["walks", "turns", "reaches", "lifts", "pours"],
    "style":     ["grain", "halation", "film stock", "anamorphic", "rolling shutter", "phone-real"],
    "voice":     [],
    # a grey 3D blocking render (references/blocking.md): it carries camera, cuts and positions, and no
    # words compete with it — the prompt's spatial text is computed from the same geometry
    "blocking":  [],
    # an APPROVED end frame bound as a reference, on a model with no true end frame (multishot.md §3).
    # gate.py refuses it unless its media id is the approved endframe:<SHOT>
    "endframe":  [],
}
# ⛔ A REFERENCE CARRIES MORE THAN THE ATTRIBUTE YOU ASKED IT FOR (2026-09-18). Declaring `what:`
# says which attribute a reference is FOR. It says nothing about the rest of the picture, and the
# rest of the picture arrives anyway: a character sheet shot on seamless grey brings the seamless
# grey, the three-panel layout and the studio key with it into a night interior. A practitioner's
# production prompts answer this with a NEGATIVE SCOPE on every reference: a sheet locks identity,
# face and wardrobe but not its studio background or layout; an environment reference controls
# environment, materials and mood but not its framing; a second location reference is kept off the
# first one's ground [SECONDARY · practitioner corpus]. `what:` is the
# positive half; `not:` is the half we were missing. A sheet-type reference used in a world shot
# without one is the single cheapest regeneration to prevent.
STUDIO_PLATE_ATTRS = {"character", "wardrobe", "prop"}
# A prompt is a WORLD shot when its environment block names somewhere real rather than a backdrop.
STUDIO_BG_RE = re.compile(r"\b(seamless|sweep|cyclorama|plain (?:grey|gray|white)|studio (?:grey|gray|backdrop|background)|"
                          r"neutral backdrop|limbo)\b", re.I)
# ⛔ A STATE CHANGE INSIDE ONE CLIP IS AN F, AND MORE WORDS DO NOT RAISE IT (2026-09-18). In the
# practitioner corpus a character's wardrobe is damaged at 3.2s, and the prompt defends it FOUR ways: a
# WARDROBE STATE TIMELINE, an insistence that the change is permanent, the state re-asserted at five
# named timestamps, and a POSITIVE LOCK. The author's own next revision throws all of it out and
# introduces a second reference asset for the post-change state. THAT is the lesson: a model has no
# state register (character-and-props.md §8.4, statelessness), so "torn from here on" has nothing to
# hold it — the fix is an ASSET, not more sentences.
STATE_CHANGE_RE = re.compile(
    r"\b(?:now|then|from (?:here|then|this point) on|for the rest of|afterwards?|permanently|"
    r"irreversibl[ey]|no longer|never (?:again )?(?:returns?|repairs?)|stays? (?:torn|ripped|"
    r"shredded|soaked|wet|muddy|bloodied|burnt|burned|broken|cracked|stained))\b"
    r"|\b(?:torn|ripped|shredded|soaked|singed|burnt|burned|smeared|bloodied|muddied|cracked|"
    r"shattered|stained|drenched)\b[^.\n]{0,40}\b(?:from|after|once|at)\b"
    r"|\bstate\s+(?:a|b|one|two)\b|\bstate timeline\b", re.I)
# The verbs that mean the change HAPPENS on screen rather than being a starting condition.
BECOMES_RE = re.compile(r"\b(tears?|rips?|shreds?|soaks?|drenches?|burns?|breaks?|cracks?|shatters?|"
                        r"stains?|smears?|splits?)\b|\bis (?:torn|ripped|shredded|soaked|burnt|"
                        r"burned|broken|cracked|shattered|stained)\b", re.I)

# ⛔ THE ROLE NAMES WERE NEVER THE API'S (found 2026-09-19). This vocabulary was copied from an
# older MiniMax References panel on 2026-08-29, and NOT ONE of these names is a role any roster model
# declares. The roster takes start_image / end_image / image_references / video_references /
# audio_references (Kling: start_image and end_image ONLY) — assets/higgsfield-rates.json →
# media_roles, read from models_explore. Start frames worked by accident: the server coerces a LONE
# `image` to `start_image`. The moment a second image joins the call — an end frame — nothing is
# unambiguous, and the end frame could not be expressed at all: `end_image` was refused here as
# "not an image/video/audio role". The legacy names stay ACCEPTED (every existing prompt file stays
# valid) and are translated by canonical_role(); only the API's names are ever emitted.
FRAME_ROLES = {"start_image", "end_image"}
IMAGE_ROLES = {"image_references", "image", "character", "reference", "element"}
VIDEO_ROLES = {"video_references", "video", "motion", "driving_video"}
AUDIO_ROLES = {"audio_references", "audio", "audio_reference", "voice"}
LEGACY_ROLE = {"start_frame": "start_image", "end_frame": "end_image",
               **{r: "image_references" for r in IMAGE_ROLES},
               **{r: "video_references" for r in VIDEO_ROLES},
               **{r: "audio_references" for r in AUDIO_ROLES}}


def canonical_role(role: str) -> str:
    """The API's name for a role, from either vocabulary. Unknown names come back unchanged, so the
    caller can refuse them by name instead of guessing."""
    r = (role or "image").strip().lower()
    return r if r in FRAME_ROLES else LEGACY_ROLE.get(r, r)


def _rates() -> dict | None:
    """The rate asset, or None when it cannot be read. ⛔ None means the lint FAILS: a roster check
    that quietly returns {} when its file is missing passes every model (found 2026-09-19 — the
    lint selftest, run from a copied scripts folder, lost its roster assertion without a word)."""
    try:
        return json.load(open(os.path.join(ASSETS, "higgsfield-rates.json"), encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def call_contract(model: str) -> dict:
    """One roster video model's contract (assets/higgsfield-rates.json → call_contract): its roles,
    whether start_image is a TRUE first frame, whether frames may share a call with references,
    its own modes, resolutions and audio switch. {} when there is no row."""
    t = _rates() or {}
    c = (t.get("call_contract") or {}).get(model)
    return dict(c) if isinstance(c, dict) else {}


def media_roles(model: str) -> set:
    return set(call_contract(model).get("roles") or [])


def call_shape(model: str, has_refs: bool, has_end: bool) -> dict:
    """⚡ THE ONE PLACE a clip call's shape is decided — gate.py checks against it and preflight
    emits it, so the two cannot disagree. Measured 2026-09-19 (a production job):
      · minimax_h3: start_image alone is a TRUE first frame (corr 1.00) — but frames and references
        in one call 422, so a clip WITH references binds its start still as a reference (0.97);
      · seedance_2_5: start_image is only accepted in omni_reference mode, where it becomes a
        reference (0.53 / 0.96) — it never has a true first frame, so it never has an end frame.
    An unmeasured `mix` is treated as False: a 422 costs a round trip, a wrong guess costs a take."""
    c = call_contract(model)
    roles = set(c.get("roles") or [])
    frames, mix = c.get("frames"), c.get("mix")
    reference_mode = frames is False or (has_refs and mix is not True)
    start_role = "image_references" if reference_mode else "start_image"
    if start_role not in roles:
        start_role = None                        # the model cannot take the still at all this way
    end_allowed = (not reference_mode) and "end_image" in roles
    mode = c.get("mode_refs") if reference_mode else c.get("mode_frames")
    why = ("its start_image is a reference, not a first frame" if frames is False else
           "frames and references cannot share one call" if reference_mode else "")
    return {"start_role": start_role, "end_role": "end_image" if end_allowed else None,
            "reference_mode": reference_mode, "why": why, "mode": mode,
            "mode_required": bool(c.get("mode_required")), "modes": list(c.get("modes") or []),
            "frames_measured": frames is not None, "resolutions": c.get("resolutions"),
            "audio": dict(c.get("audio") or {})}
CARD_STALE_DAYS = 90


def model_cards(today: str | None = None) -> list:
    """(v2.70.0, Wave 5 A8) One card per roster video model, built only from what the rates file already states (roles,
    whether the first frame is measured, reference caps, modes, audio switch, speech syntax and its status), with the
    date each was last checked; a card older than CARD_STALE_DAYS is said to be stale (an info line, never a WARN)."""
    import datetime as _dt
    t = _rates() or {}
    now = _dt.date.fromisoformat(today) if today else _dt.date.today()
    notes = t.get("model_capability_notes") or {}
    default_checked = (t.get("call_contract") or {}).get("_checked") or t.get("_checked") or t.get("_updated")
    out = []
    for m, c in (t.get("call_contract") or {}).items():
        if not isinstance(c, dict) or m.startswith("_"):
            continue
        # a model's own date, else the date the notes give for THAT model, else the rates file's update date
        # the capability's own date only: a price-table date says nothing about a model added later (Grok r1)
        checked = str(c.get("_checked") or (notes.get(m) and notes.get("_checked")) or "")[:10]
        try:
            age = (now - _dt.date.fromisoformat(checked)).days
        except ValueError:
            age = None
        out.append({"model": m, "first_frame": {True: "true first frame (measured)", False: "a reference, never a first "
                    "frame (measured)", None: "not measured"}[c.get("frames")], "roles": c.get("roles"),
                    "ref_caps": slot_caps(m), "modes": c.get("modes"), "audio": c.get("audio"),
                    "speech": (c.get("speech_syntax") or {}).get("form") or "not documented here",
                    "speech_status": (c.get("speech_syntax") or {}).get("status") or "—",
                    "speech_checked": (c.get("speech_syntax") or {}).get("checked") or "—",
                    "checked": checked or "unknown",
                    "stale": "unknown date" if age is None else (f"stale: checked {age} days ago" if age > CARD_STALE_DAYS else "")})
    return out


def noun_home(model: str) -> dict:
    """(v2.71.0, Wave 5 A3) Where a guardrail's defect nouns go for this model, from its call contract's `negative`:
    `field` → [SUPPRESS] (sent as negative_prompt); `none` → [CONSTRAINTS], the prompt's last block (a [SUPPRESS]
    would be dropped); `unknown` or no contract → [SUPPRESS], and check the take."""
    # prompt_limit reads call_contract first, then prompt_limits (the image models): build review 1, Grok
    neg = str(prompt_limit(model or "").get("negative") or "unknown").lower()
    if neg == "none":
        return {"block": "CONSTRAINTS", "negative": neg,
                "why": "no negative field: the nouns go in [CONSTRAINTS], the prompt's last block"}
    if neg == "field":
        return {"block": "SUPPRESS", "negative": neg, "why": "a negative field: the nouns go in [SUPPRESS]"}
    return {"block": "SUPPRESS", "negative": neg,
            "why": "negative field not documented: the nouns go in [SUPPRESS]; check the take"}


def route(model: str, has_refs: bool = False) -> dict:
    """(v2.71.0) The prompt form (below) plus where the guardrail nouns go (`noun_home`)."""
    r = _route_form(model, has_refs)
    r["nouns"] = noun_home(model)
    return r


def _route_form(model: str, has_refs: bool = False) -> dict:
    """(v2.70.0, Wave 5 A1) Which prompt to write for a clip, read from the call contract BEFORE any prose: a true
    first-frame model gets the motion-only i2v template (the approved still carries the look); a model whose start image
    is only a reference (Seedance) gets the scene form; an UNMEASURED model is said to be unmeasured, with what
    `call_shape` will actually send. A video reference is never required."""
    c = call_contract(model)
    if not c:
        return {"model": model, "form": None, "template": None, "why": "no call contract for this model"}
    sh = call_shape(model, has_refs, False)
    frames = c.get("frames")
    if has_refs and not ({"image_references", "video_references"} & set(c.get("roles") or [])):
        # the model takes no reference images at all (Kling 3.0): the scene form would lint FAIL there, and its
        # 2,500-character floor is that model's ceiling (build review 1, Sonnet)
        return {"model": model, "form": "i2v", "template": "clip", "measured": frames is not None,
                "start_role": "start_image", "end_role": "end_image" if "end_image" in (c.get("roles") or []) else None,
                "why": "this model takes no reference images: drop the references, and write the motion-only i2v "
                       "blocks from an approved start frame"}
    if frames is False:
        form, why = "scene", "its start image is a reference, never a first frame: write the scene form (§12)"
    elif sh["reference_mode"] and c.get("mix") is False:
        form, why = "scene", ("with references, frames and references cannot share one call (measured), so the still is "
                              "bound as a reference: write the scene form, or drop the references for a true first frame")
    elif sh["reference_mode"]:
        # an UNMEASURED limit is said as unmeasured, with what the call will send — never as a prohibition (Grok r1)
        form, why = "unmeasured", (f"unmeasured: whether frames and references can share one call is not measured here; "
                                   f"to be safe the call sends the still as {sh['start_role']}. Write the scene form if "
                                   f"the references stay, or drop them and write the i2v blocks")
    elif frames is True:
        form, why = "i2v", "a true first frame: write the motion-only i2v blocks; the approved still carries the look"
    else:
        form, why = "i2v", (f"unmeasured: whether its start_image is a true first frame is not measured here; "
                            f"`call_shape` sends the still as {sh['start_role']}" + ("" if has_refs else
                            ", so write the i2v blocks and check the first frame against the still (look_qa)"))
    return {"model": model, "form": form, "template": {"scene": "scene", "i2v": "clip"}.get(form), "measured":
            frames is not None, "start_role": sh["start_role"], "end_role": sh["end_role"], "why": why}


# MiniMax H3, verified in the References panel 2026-08-29: 9 images/elements, 3 videos, 3 audio.
# Conservative house caps — per-model, so over the cap is a WARN with the model named, not a FAIL.
SLOT_CAPS = {"image": 9, "video": 3, "audio": 3}


def slot_caps(model: str) -> dict:
    """The per-call reference caps for one model: its call_contract `ref_limits` where the row states
    them (Seedance 2.5: 30 / 10 / 10 [VENDOR]), else the house caps above."""
    lim = call_contract(model or "").get("ref_limits") or {}
    return {k: int(lim[k]) if isinstance(lim.get(k), (int, float)) else v for k, v in SLOT_CAPS.items()}
# ----------------------------------------------------------------------------------------------
# GENJUTSU (v2.46.1; 2026-11-03: "Include Genjutsu", then "Genjutsu has 2 versions, full and lite. Lite
# has 10 free gens, full just 1"). Four generate_video models that RE-RENDER a source video: motion transfer
# and object swap, each full and Lite. They are not clip models — no start frame, no duration, no prompt
# contract — so they get their own spec kind and are kept OUT of rate_table (a rate row would let a clip prompt
# cast them). The table is assets/higgsfield-rates.json → genjutsu; unreadable means the lint FAILS.
GENJUTSU_MODES = {"motion": "motion transfer", "swap": "object swap"}
GENJUTSU_BLOCKS = ("PROMPT", "QA")
GENJUTSU_RIGHTS = ("client-approved", "own")
GENJUTSU_FREE = ("prefer", "no")
GENJUTSU_SUFFIX = ".genjutsu.prompt.md"


def genjutsu_table() -> dict:
    t = _rates() or {}
    g = t.get("genjutsu")
    return dict(g) if isinstance(g, dict) else {}


def genjutsu_models() -> dict:
    """{model id: row} for the four Genjutsu models. {} when the asset cannot be read (the lint then fails)."""
    return {k: dict(v) for k, v in (genjutsu_table().get("models") or {}).items()
            if isinstance(v, dict) and not str(k).startswith("_")}


def is_genjutsu(model) -> bool:
    return str(model or "").strip() in genjutsu_models()


def _ffprobe_seconds(path: str) -> float | None:
    """The file's duration by ffprobe, or None (no ffprobe, or unreadable). Used for a WARN only."""
    import shutil, subprocess
    if not shutil.which("ffprobe"):
        return None
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


# A provenance sidecar (pixabay_search.py writes this shape) must answer the §5 blockers before an
# asset reaches FINAL footage. Reference-only use is defensible; shipping the likeness is not.
SIDECAR_REQUIRED = ("source", "licence", "clearance")

BLOCK_RE = re.compile(r"^\[([A-Z][A-Z /\-]{1,30})\]\s*$", re.M)
FRAME_REQUIRED = ["SUBJECT", "ENVIRONMENT", "LIGHTING", "CAMERA"]
CLIP_REQUIRED = ["MOTION", "CAMERA"]
# Camera verbs vs SUBJECT motion. The list is deliberately narrow and errs toward silence: a MOTION
# block naming any of these subject verbs is left alone, so the warning fires only on a block that
# is purely a camera instruction. motion-craft.md §6 item 6.
CAMERA_VERBS = (r"push(?:es|ing)?|pull(?:s|ing)?|doll(?:y|ies|ying)|zoom(?:s|ing)?|orbit(?:s|ing)?|"
                r"pan(?:s|ning)?|tilt(?:s|ing)?|track(?:s|ing)?|crane(?:s|ing)?|"
                r"drift(?:s|ing)?|glide(?:s|ing)?|circle(?:s|ing)?|rack(?:s|ing)?|"
                r"handheld|locked.?off|static|slider|steadicam|whip")
# The settle. Note `still` the adverb is NOT a settle word — "the tray is still moving" is the
# opposite — so only verb forms are listed. Caught by the selftest.
SETTLE_RE = re.compile(r"\bsettl\w*|\bcomes? to (?:a )?(?:rest|halt|stop)|\bhold\w*|\bslow\w*|"
                       r"\beas(?:e|es|ing)\b|\bland\w*|\bstead(?:y|ies|ying)\b|\bset down\b|"
                       r"\bstops?\b|\brests?\b|\bstill(?:s|ed|ing)\b", re.I)
SUBJECT_MOTION_RE = re.compile(
    r"\b(?!(?:" + CAMERA_VERBS + r")\b)"
    r"(?:reach\w*|lift\w*|set\w*|place\w*|pour\w*|turn\w*|step\w*|walk\w*|sit\w*|stand\w*|"
    r"lean\w*|glance\w*|look\w*|nod\w*|blink\w*|smile\w*|breath\w*|shift\w*|wipe\w*|"
    r"open\w*|close\w*|hand\w*|take\w*|drop\w*|catch\w*|push\w*ing\s+the|enter\w*|exit\w*|"
    r"cross\w*|rise\w*|fall\w*|settle\w*|steam\w*|ripple\w*|flutter\w*|sway\w*|spill\w*|"
    r"raise\w*|lower\w*|tip\w*|tilt\w*\s+her|press\w*|grip\w*|release\w*|pause\w*|"
    r"exhale\w*|inhale\w*|swallow\w*|straighten\w*|adjust\w*|brush\w*|slide\w*\s+the)\b",
    re.I)
CLIP_FORBIDDEN = ["START FRAME", "ENVIRONMENT", "LIGHTING", "SUBJECT", "STYLE", "SETTING", "LOCATION",
                  "COLORS", "LIGHTING/MOOD"]
PERF_KEYS = ["STATE", "BEAT", "FACE", "GAZE"]
# Stack tokens every vendor names as degrading: a FAIL. Loose adjectives are a WARN — "vibrant
# orange apron" is a colour, "high quality olive oil" is a product; the reviewer found both refused.
QUALITY_FAIL = ["8k", "masterpiece", "ultra realistic", "ultra-realistic", "hyper-realistic",
                "hyperrealistic", "hyper realistic", "best quality", "trending on"]
QUALITY_WARN = ["cinematic look", "vibrant", "whimsical", "beautiful", "amazing", "stunning",
                "breathtaking", "high quality", "highly detailed", "award-winning", "award winning",
                "photorealistic,"]
# Style-by-name: "in the style of X", "à la X", "<Proper Noun>-style", "shot/directed by <Proper Name>".
# Case-sensitive on purpose — "loft-style kitchen" and "shot by a friend" are fine.
NAME_INVOKE_RE = re.compile(r"(?i:in the style of)|à la [A-Z]|\b[A-Z][a-z]+(?: [A-Z][a-z]+)?-style\b|"
                            r"\b(?:directed|shot|cinematography|photographed) by [A-Z][a-z]+ [A-Z][a-z]+")
HEDGE_RE = re.compile(r"\b(begins?|beginning|starts?|starting) to (?!finish\b|the\b|a\b|an\b|her\b|"
                      r"his\b|their\b|its\b|end\b)[a-z]+", re.I)
COMMAND_RE = re.compile(r"^\s*(can you|could you|please|make (?:me|a|an|the)|create (?:a|an|the)|generate|"
                        r"i want|i need|give me)\b", re.I)
# (v2.71.0) the first form ended in \b straight after one letter, so "no head bobbing" never matched ("no h|ead" has
# no word boundary): only never/don't/avoid/without ever warned. Now "no X" and "not X" match the whole next word.
# Grammar, not a prohibition (build review 2, Sonnet + Grok): ", not X" (a contrast: "warm, not sinister", "the camera,
# not her hand"), "no longer / one / more / less", the idiom "no second thought",
# "not" + an article, pronoun or possessive ("the camera, not her hand"), "not at all / once / in / on / until / quite /
# so / too / even". Camera negations ("No pan, no tilt.") are the explicit form the camera rule asks for and are skipped
# in [CAMERA] where the loop runs.
# (build review 3, Grok) narrowed: "no one else", "no more X", "not at the lens", "not in frame", "not her face" and
# "not once" are real keep-out lines and warn; only these stay grammar
_NO_GRAMMAR = r"(?:longer|more than|less than|second thoughts?)"
_NOT_GRAMMAR = r"(?:an?|the|only|just|yet|at all|until|before|after|quite|so|very|always|enough)"
NEG_SENTENCE_RE = re.compile(rf"\b(?:no(?! {_NO_GRAMMAR}\b)|(?<!, )not(?! {_NOT_GRAMMAR}\b)) [a-z]+\b|"
                             r"\b(?:don't|do not|never|avoid|without)\b", re.I)
CAMERA_NEG_RE = re.compile(r"\bno (?:pan|tilt|zoom|cuts?|roll|rack(?: focus)?|dolly|track|push|pull|shake|move(?:ment)?|"
                           r"camera move(?:ment)?)\b", re.I)
# ⛔ A PROMPT THAT STILL CONTAINS A DECISION IS A DRAFT, AND A DRAFT THAT BILLS (2026-09-17).
# Adopted from Higgsfield's own Ad Multiplier workflow, which validates a finished prompt
# byte-for-byte before submission and refuses one carrying "branches, alternatives, or
# meta-conditions" or "bracketed placeholders or slash-separated alternatives"
# [SECONDARY · Higgsfield, ad-multiplier v1.4, live MCP catalog · 2026-09-17]. We had every
# quality check and no check that the writing was FINISHED: `[HERO NAME]`, "either the mug or the
# glass", "TBD" all passed the lint and the model would have rendered the brackets.
PLACEHOLDER_RE = re.compile(r"\[(?:[A-Z][A-Z0-9 _/-]{2,30}|[a-z ]{3,30})\]|<[a-z][a-z ._-]{2,30}>|"
                            r"\{\{[^}]{1,40}\}\}|\bTBD\b|\bTK\b|\bXX+\b|\bplaceholder\b|\bFIXME\b", re.I)
ALTERNATIVE_RE = re.compile(r"\beither\b[^.\n]{1,60}\bor\b|\b(?:or maybe|and/or|/ ?or\b)|"
                            r"\b(?:option|variant|alt)\s*[AB1-9]\b|\bpick (?:one|either)\b|"
                            r"\bwhichever\b|\bif (?:the|we|you|they)\b[^.\n]{1,60}\botherwise\b", re.I)
# A raw id, a job uuid or a URL inside a prompt is a note to self that the model will try to draw.
LEAKED_ID_RE = re.compile(r"https?://\S+|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|"
                          r"\b(?:job|media|element|preset)[_-]?(?:id)?[_:=-]\s*[A-Za-z0-9_-]{6,}\b", re.I)
# ⛔ "DIFFERENT FROM THE OTHER ONE" IS NOT A DESCRIPTION. Also from the Ad Multiplier contract,
# which states it as a gate: words such as "different" or "contrasting" without explicit positive
# traits do not satisfy it. A model cannot see what it is supposed to differ FROM.
# The thing being differed FROM, spelled the same way everywhere it is named.
_THE_OTHER = r"(?:source|original|other|others|first|previous|above|reference|him|her|them|it)"
COMPARATIVE_ONLY_RE = re.compile(
    # "unlike the original" — a direct object, no preposition to hang the first arm on
    r"\bunlike\s+(?:the\s+)?" + _THE_OTHER + r"\b|"
    # "different <anything> FROM the original/source/reference/her" — the comparison is explicit
    r"\b(?:different|contrasting|not the same|distinct)\b[^.\n]{0,40}?"
    r"\b(?:from|to|than|as)\s+(?:the\s+|that\s+of\s+the\s+)?" + _THE_OTHER + r"\b|"
    # or the bare "a different hairstyle" with no trait named at all
    r"\b(?:a|an)\s+(?:different|contrasting)\s+"
    r"(?:look|person|face|hair\w*|style|colou?r|build|outfit|wardrobe)\b(?!\s*[:,-])", re.I)
# Camera behaviours, by CLASS — a rig word (handheld, steadicam, gimbal, drone, tripod) is not a
# move, "slow dolly push-in" is one move, "whip pan" is one move, a Dutch tilt is an angle.
# ⛔ THE CITATION-FORM GAP (found 2026-09-08 by running the standard twelve-move list through this
# table). The patterns only matched the DICTIONARY form of each move — `push-in` but not `push`,
# `tracking` but not `tracks`, `truck` but not `trucking` — so nine of sixteen ordinary English
# phrasings matched NOTHING. A prompt reading "slow push along the rows" registered zero moves, which
# means the one-behaviour-per-clip rule silently did not apply to it. A rule that only fires on the
# citation form is a rule that fires on prompts nobody writes.
# `roll`, `rack focus` and `pedestal` were absent as classes entirely, so a roll could be stacked onto
# another move and nothing saw it — which is exactly what happened in a bench run the same day.
CAMERA_CLASSES = {
    "static": [r"\bstatic\b", r"\block(?:ed)?[- ]off\b", r"\btripod\b"],
    "dolly": [r"\bdoll(?:y|ies|ying)\b", r"\bpush(?:es|ing)?(?:[- ]in)?\b",
              r"\bpull(?:s|ing)?[- ]?out\b", r"\btrack(?:s|ing)?\b", r"\btruck(?:s|ing)?\b",
              r"\bcrab(?:s|bing)?\b", r"\bcreep(?:s|ing)? in\b"],
    "pan": [r"(?<!dutch )(?<!a )\bpan(?:s|ning)?\b(?! of\b)", r"\bwhip\b", r"\bswish\b"],
    "tilt": [r"(?<!dutch )\btilt(?:s|ing)?\b"],
    "orbit": [r"\borbit(?:s|ing)?\b", r"\barc(?:s|ing)?\b", r"\brevolv\w+\b"],
    "crane": [r"\bcrane(?:s|ing)?\b", r"\bjib\b", r"\bboom(?:s|ing)?\b", r"\bpedestal\b"],
    "zoom": [r"\bzoom(?:s|ing)?\b"],
    # A roll is a move. It was not in this table at all, and it is the one that degrades WORST in
    # 9:16 — the frame's own diagonal already sits ~29 degrees from vertical, so a tilt is read
    # against an already-steep reference (cinematography-craft.md §5.10, §3.8).
    "roll": [r"\broll(?:s|ing)?\b(?!\s*shutter)", r"\bcanted\b", r"\bdutch(?:ed|ing)?\b"],
    # A lens move, not a body move — but it is a camera behaviour and it competes for the same slot.
    "rack": [r"\brack(?:s|ing)?[- ]?focus\b", r"\bfocus[- ]pull\b", r"\bpulls? focus\b"],
}
# ⛔ TEXTURE, NOT PATH. Handheld is HOW the camera moves, not WHERE, so it does not consume the
# one-move budget — "handheld push-in" is one shot, not two instructions. It gets its own warning
# instead, because what a model returns for "handheld" is a gimbal: the path with none of the
# presence (cinematography-craft.md §3.4).
CAMERA_TEXTURE = {"handheld": [r"\bhand[- ]?held\b", r"\bsteadicam\b", r"\bgimbal\b",
                               r"\bshaky\b", r"\bshakes?\b", r"\bjitter\w*\b"]}
# ⛔ ONE NAMED MOVE THAT IS TWO MOVES, AND IS NOT OBTAINABLE. A dolly zoom is a simultaneous position
# change and focal-length change. No 2026 video model exposes a focal-length channel, so there is
# nothing to counter-rotate against the dolly — you get a push with a wobble. It must not be counted
# as "dolly + zoom = two moves" (it is one named move and the writer knows that); it must be refused
# on its own terms. cinematography-craft.md §3.8.
DOLLY_ZOOM_RE = re.compile(r"\bdolly[- ]zoom\b|\bzolly\b|\bvertigo (?:effect|shot|zoom)\b|"
                           r"\bcontra[- ]?zoom\b|\btrombone (?:shot|effect)\b", re.I)
# ⛔ THE DEAD SHOT (2026-09-08). F11 — "last frame against first: the audience learned nothing
# across the move" — existed, and ran at the CLIP gate, after the clip was generated and paid for.
# A hook written as "a bare mattress, and only dust moves" passed this linter clean: the
# only-camera-verbs rule did not fire, because *dust drifts* is not a camera verb. Nothing asked the
# one question that kills the shot. These three checks move F11 to the plan (direction.md §2b).
#
# An END: that ASSERTS nothing changed is the failure declaring itself in writing.
def flat_txt(x: str) -> str:
    """Whitespace-collapsed, lowercased — for comparing two written answers for sameness."""
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", str(x or "").strip().lower())).strip()


NO_CHANGE_RE = re.compile(
    r"nothing (?:else )?(?:has )?(?:moved|happened|changed|occurs|happens)"
    r"|nothing else (?:in|has|moves)"
    r"|(?:is|are|remains?|stays?) unchanged|no change|exactly as (?:it|they) (?:was|were)"
    r"|the same as (?:it|they) (?:was|were|started)|as at the start"
    # ⛔ "still" is two words in English. "remains still" is motionless; "is still sinking" is an
    # adverb and the exact opposite — a thing in the middle of changing. Bare "is/are still" is
    # therefore NOT a no-change signal; only the verbs that cannot take the adverb reading are.
    r"|(?:remains?|stays?) (?:the same|as before|static|still|motionless)"
    r"|(?:is|are) (?:the same|as before|static|motionless)"
    r"|holds? (?:its|their) (?:exact )?position|no (?:event|action|movement)", re.I)
# Atmosphere is not an event. A MOTION block whose only non-camera verbs are these is a still
# photograph someone left running.
AMBIENT_VERBS = (r"drift\w*|float\w*|hover\w*|hang\w*|waft\w*|swirl\w*|shimmer\w*|glow\w*|"
                 r"twinkl\w*|sparkl\w*|glisten\w*|sway\w*|ripple\w*|billow\w*|flicker\w*|"
                 r"settl\w*|dance\w*|turn\w*|curl\w*|rise\w*|fall\w*|catch\w*|play\w*")
# ⚡ INTENT (2026-10-26, relaying a direct-response agency's brief): "make everything with intent. So if the
# subject throws away sugar, it's not about focusing on how sugar pours even if that is part of the
# shot, but about the human being quick to do so, planned hand movement, shaking of cup", and "Most
# generations seem to have boring movements." When a person acts in a clip, [MOTION] says WHY they
# do it and the manner that forces (`INTENT:`), the person leads every line, and the material is the
# consequence of their force, never the subject. motion-craft.md §6b has the method and the bundles.
TRACK_RE = re.compile(r"^\s*([\w .-]+?)\s*(?:=|@)\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*$")
PRELAP_MIN_S, PRELAP_MAX_S = 0.25, 1.0   # (3.2.0) the lead of a pre-lap [PRACTITIONER, assumed range]


def parse_prelap(v) -> tuple:
    """(3.2.0) `prelap: 0.5s, knock, side=right` → ({"lead_s", "event", "side"}, None), or (None, why). The lead is in
    seconds so a frame rate cannot change it; the event is the next shot's sound by its read word or id; the side is
    optional (left, right, off-left, off-right)."""
    parts = [x.strip() for x in str(v or "").split(",") if x.strip()]
    if not parts:
        return None, "empty"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*s?", parts[0].lower())
    if not m:
        return None, "start with the lead in seconds: \"0.5s, knock\""
    lead = float(m.group(1))
    if not PRELAP_MIN_S <= lead <= PRELAP_MAX_S:
        return None, f"a lead of {lead:g} s is outside {PRELAP_MIN_S:g}–{PRELAP_MAX_S:g} s"
    ev, side = "", None
    for x in parts[1:]:
        if x.lower().startswith("side="):
            side = x.split("=", 1)[1].strip().lower()
            if side not in ("left", "right", "off-left", "off-right"):
                return None, f"side={side!r}: left, right, off-left or off-right"
        elif not ev:
            ev = x
    if not ev:
        return None, "name the next shot's sound event by its read word or id: \"0.5s, knock\""
    return {"lead_s": lead, "event": ev, "side": side}, None
# shot-handoff.md §4b: a `join:` that carries motion across the cut, and what counts as a screen direction
HANDOFF_MOTION_RE = re.compile(r"(?i)\b(motion|action|whip|vector|push-through|carry|carries|continu)")
HANDOFF_DIR_RE = re.compile(r"(?i)\b(left|right|up|down|upward|downward|toward|towards|away|into (?:the )?lens|"
                            r"out of frame|frame (?:left|right))\b")
AGENT_RE = re.compile(r"(?i)\b(?:hand|hands|fingers?|thumb|palm|wrist|arm|arms|she|he|her|his|"
                      r"woman|man|person|someone|girl|guy|mother|father|presenter|host)\b")
MATERIAL_RE = re.compile(r"(?i)^\s*(?:the |a |some |its |her |his )?(?:sugar|powder|salt|flour|liquid|"
                         r"water|coffee|tea|milk|juice|oil|cream|syrup|honey|smoke|steam|crumbs?|grains?|"
                         r"capsules?|pills?|tablets?|droplets?|drops?|bubbles?|foam|sauce|wine|soda|"
                         r"cereal|chips|sand|dust|ice|batter|dough|fluid)\b(?!\s+(?:jar|bag|bowl|bottle|box|packet|pot|"
                         r"cup|spoon|tin|can|carton|glass|mug|shaker|tub)\b)")
FLOAT_RE = re.compile(r"(?i)\b(?:slow(?:ly)?|gentl[ey]|graceful(?:ly)?|smooth(?:ly)?|elegant(?:ly)?|"
                      r"soft(?:ly)?|leisurely|in slow motion|slow-motion|slo-mo|cascad\w*|flow\w*|float\w*|"
                      r"glid\w*)\b")
TEMPO_RE = re.compile(r"(?i)\b(?:quick(?:ly)?|fast|sudden(?:ly)?|sharp(?:ly)?|snap\w*|flick\w*|jab\w*|"
                      r"brisk(?:ly)?|abrupt(?:ly)?|in one (?:quick )?(?:motion|move)|without (?:hesitat\w*|"
                      r"looking|thinking)|hesitat\w*|a beat|paus\w*|stops?|rush\w*|hurr\w*|decisive(?:ly)?|"
                      r"firm(?:ly)?|hard|tap\w*|slam\w*|yank\w*|toss\w*|shov\w*|grab\w*|dump\w*|jerk\w*|"
                      r"shak\w*|tugs?|tugg\w*|twice|again|bounc\w*|heav\w*|drag\w*|reluctant\w*|careful\w*|"
                      r"precise\w*|automatic\w*|habit\w*|impatien\w*)\b")
# ⛔ OBJECT PERMANENCE (a supplement ad job, 2026-10-28). "Tossed in passing" made the keys teleport: the model threw them out
# of frame, then put them back on the counter, and shot-level QA frames missed it. An object that is thrown, tossed or
# flung needs its release and its landing in the prompt ("fingers open, the keys drop straight down onto the counter
# below"), or the words that it leaves the frame for good. prompting-craft.md §6.4b; realism-qa.md V7b.
THROW_RE = re.compile(r"(?i)\b(?:toss\w*|throw\w*|threw|thrown|fling\w*|flung|chuck\w*|lob\w*|hurl\w*)\b")
THROW_IDIOM_RE = re.compile(r"(?i)\b(?:toss\w*|throw\w*|threw|thrown)\s+(?:a |an |his |her |their |the )?(?:punch|glance|look|"
                            r"smile|tantrum|fit|party|shade|jab|hook|kiss|wink|head|hands up|caution)\b")
LANDING_RE = re.compile(r"(?i)\b(?:lands?|landing|landed|onto|on to|comes? to rest|settles? (?:on|onto|in)|"
                        r"drops? straight down|falls? (?:onto|into|on)|into the (?:bin|basket|bowl|box|drawer|bag|sink)|"
                        r"(?:leaves?|out of) (?:the )?frame (?:for good|and (?:is|stays) (?:gone|out))|never (?:seen|returns?) again)\b")
# ⛔ OUT OF THE ADS LANE (house decision 2026-10-26, package D; motion-craft.md §7b). Three techniques
# all three jury models killed for realism: the environment mirroring the emotion, a world-state or
# texture shift inside the shot, and reflections as a mirror of the inner state.
AI_TELL_MOTION = [
    (re.compile(r"(?i)\b(?:shadows?|walls?|room|air|dust|light|background)\b[^.;\n]{0,40}\b(?:puls\w*|"
                r"breath\w*|writh\w*|vibrat\w*|throb\w*|heav(?:es|ing))\b|\binvisible (?:wind|force|current|pull)\b"),
     "the environment mirrors the emotion"),
    (re.compile(r"(?i)\b(?:texture|image|scene|picture|frame|world)\b[^.;\n]{0,30}\b(?:shifts?|turns?|becomes?|"
                r"melts?|morphs?|softens?|dissolves?)\b[^.;\n]{0,30}\b(?:dream\w*|painterl\w*|oil[- ]paint\w*|"
                r"impressionis\w*|watercolou?r\w*|abstract\w*)|\b(?:moss|flowers?|stains?|cracks?)\b[^.;\n]{0,20}"
                r"\b(?:grows?|spreads?|blooms?|wilts?|creeps?)\b"),
     "a world-state or texture change inside the shot"),
    (re.compile(r"(?i)\breflections?\b[^.;\n]{0,40}\b(?:ripple\w*|shatter\w*|fragment\w*|distort\w*|warp\w*|"
                r"breaks? apart)\b"),
     "a reflection as a mirror of the inner state"),
]
# ⚡ THE START FRAME IS MADE FOR ITS MOTION (house decision 2026-10-26, package A; the jury's first two).
# A still composed at rest makes the model invent the energy from zero, and it drifts. An action
# shot's frame is caught at the anticipation peak the clip completes (`caught:`), with room on the side
# the action travels to (`travel:`). Read from the sibling clip prompt: a person acting, not dialogue.
REST_RE = re.compile(r"(?i)\b(?:rests?|resting|at rest|stands? still|sits? still|neutral pose|relaxed pose|"
                     r"poses?|posing|motionless|hands? (?:resting|folded|at (?:her|his) sides?))\b")
NEGATIVE_STATES = ["stressed", "worried", "overwhelmed", "angry", "anxious", "furious", "terrified",
                   "devastated", "panicked", "frustrated"]
TEXT_RENDER_RE = re.compile(r"\blogo\b|reads? \"|says? \"|text (?:reading|that says)|lettering|"
                            r"typography|headline|watermark", re.I)
# ⛔ A WHIP PAN THAT CHANGES FRAME SIZE IS A DISGUISED CUT (2026-09-18). One continuous camera
# move cannot arrive at a different shot size than it left — a real operator swinging a lens does
# not also change focal length mid-swing. A take that opens on a medium and lands on a close-up is
# seen as a glitch, not a transition [SECONDARY · course notes — observed as a rejected take].
# Medium to medium, close-up to close-up.
WHIP_RE = re.compile(r"\bwhip[- ]?pan\b|\bwhip\b(?=[^.\n]{0,30}\bpan)|\bswish pan\b", re.I)
SHOT_SIZE_RE = re.compile(r"\b(ECU|XCU|CU|MCU|MS|MLS|WS|EWS|LS|close[- ]?up|medium (?:close[- ]?up|shot|long shot)|"
                          r"wide(?: shot)?|extreme (?:close[- ]?up|wide))\b", re.I)
_SIZE_CANON = {"ecu": "ECU", "xcu": "ECU", "extreme close-up": "ECU", "extreme closeup": "ECU",
               "cu": "CU", "close-up": "CU", "closeup": "CU",
               "mcu": "MCU", "medium close-up": "MCU", "medium closeup": "MCU",
               "ms": "MS", "medium shot": "MS", "mls": "MLS", "medium long shot": "MLS",
               "ws": "WS", "wide": "WS", "wide shot": "WS",
               "ews": "EWS", "ls": "EWS", "extreme wide": "EWS"}
# ⛔ AN ECU ON A BODY PART IS AN ANATOMY REFERENCE, NOT A MOOD (2026-09-18). Hands directed only as
# nervous came back with smooth, waxy CG skin that looks fake once it fills the frame [SECONDARY ·
# course notes]. The take that worked named structures (tendons, knuckle creases, pores, cuticles,
# nail edges). Affect gives the model nothing to render; anatomy does.
BODY_ECU_RE = re.compile(r"\b(hands?|fingers?|knuckles?|face|eyes?|feet|foot|neck|throat|mouth|lips?)\b", re.I)
AFFECT_ONLY_RE = re.compile(r"\b(nervous|anxious|tense|restless|worried|agitated|fidgety|uneasy|"
                            r"jittery|shaky|stressed)\b", re.I)
ANATOMY_RE = re.compile(r"\b(vein|tendon|knuckle|pore|callus|calluse|scar|cuticle|hangnail|nail|"
                        r"crease|wrinkle|vellus|freckle|mole|capillar|stubble|lash|iris|sclera|"
                        r"tempera|sinew|joint|crow'?s[- ]feet|masseter|flush)\w*", re.I)
# Text a model can actually render — diegetic writing — versus a brand mark, which it cannot.
# ⛔ AN EMOTION IS NOT A DIRECTION (2026-09-18). "Sad", "guilty", "devastated" are unactable by a
# person and unrenderable by a model — both can only play a MECHANISM: a named muscle, a physical
# act, or the word the delivery breaks on. The course names the stressed word, a nostril flare on it
# and a downward eye flick, never the emotion itself [SECONDARY · course notes].
AFFECT_STATE_RE = re.compile(r"\b(sad|guilty|guilt-ridden|devastated|heartbroken|angry|furious|"
                             r"terrified|afraid|scared|ashamed|proud|happy|joyful|excited|"
                             r"desperate|hopeful|nostalgic|bitter|resentful|anxious|nervous|"
                             r"emotional|moved|overwhelmed)\b", re.I)
PERF_MECHANISM_RE = re.compile(r"\b(swallow|blink|exhale|inhale|breath|flick|clench|clamp|tremble|"
                               r"tense|tighten|purse|flare|lift|drop|narrow|widen|jaw|brow|lash|"
                               r"throat|chest|nostril|masseter|corrugator|shoulder|lip|eyelid|"
                               r"micro-?paus|beat|stress(?:es)? (?:on|lands)|cracks? on|breaks? on|"
                               r"pitch drops?)\w*", re.I)
# ⛔ CARD v2 (2026-09-30) — acting-for-the-model.md §7. The model has no inner life, so a card line
# must name something the camera can see: the thing reacted to (STIMULUS), what the performance is
# aimed at (TARGET), and — at MS or wider, where a face is read slowly — the body (BODY).
# "The model may overreact to strong emotional cues" [PRIMARY · BytePlus Seedance 2.5 guide,
# 2026-09-28], so an intensity superlative is the overdrive, whatever emotion it modifies.
VAGUE_GAZE_RE = re.compile(r"\b(into (?:the )?(?:middle )?distance|middle distance|off[- ]?screen|"
                           r"off[- ]?camera|somewhere|nowhere|at nothing|unfocused|vacant(?:ly)?|"
                           r"blank(?:ly)?|away)\b", re.I)
OVERDRIVE_RE = re.compile(r"\b(extremely|intensely|incredibly|overwhelmingly|hysterical\w*|"
                          r"uncontrollabl\w*|wildly|violently|utterly|full[- ]blown|over[- ]the[- ]top|"
                          r"maximum|maximal)\b", re.I)
DIRECT_ADDRESS_RE = re.compile(r"\b(lens|into (?:the )?camera|at (?:the )?camera|to camera|"
                               r"the viewer|at us)\b(?![- ](?:left|right))", re.I)
OFF_EYE_RE = re.compile(r"\b(low[- ]angle|high[- ]angle|from below|from above|worm'?s[- ]eye|"
                        r"bird'?s[- ]eye|dutch|tilt(?:ed|s)? (?:up|down)|looking (?:up|down) at)\b", re.I)
WIDE_SIZES = {"MS", "MLS", "WS", "EWS"}
# ⛔ THE MODEL IS OBLIGING, SO A FAILURE MUST BE MADE NECESSARY (2026-09-18). "He misses" competes
# with the prior that stories resolve; reach for a prize and the model tends to hand it over. Any
# withheld outcome needs a stated mechanism — the corpus supplies one every time: how far a body can
# travel (about two metres in a dive) against how far the target is (about eight); or an obstacle
# that moves faster than the person and closes the gap first [SECONDARY · practitioner corpus].
WITHHELD_RE = re.compile(r"\b(misses|missed|falls? short|doesn'?t (?:reach|make|quite)|does not "
                         r"(?:reach|make)|fails? to (?:reach|catch|grab|touch)|never (?:reaches|"
                         r"touches|makes it|quite)|just out of reach|too late|short of|"
                         r"out of reach|cannot reach|can'?t reach)\b", re.I)
# ⛔ `50mm` IS NOT A DISTANCE (caught by this file's own selftest, 2026-09-18). The first version of
# this pattern read `\d+\s?m` and therefore matched the focal length in every CAMERA block — which
# silently satisfied the mechanism requirement on essentially every prompt and disabled the check
# it was written for. A unit needs a boundary that `mm` fails.
MECHANISM_RE = re.compile(r"\b\d+(?:\.\d+)?\s?(?:metres?|meters?|m(?![a-z])|cm(?![a-z])|km/h|mph|"
                          r"seconds?|secs?|s(?![a-z]))\b|"
                          r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|"
                          r"forty|fifty)\s+(?:metres?|meters?|centimetres?|seconds?|feet|foot)\b|"
                          r"\bfaster than\b|\bslower than\b|\bbefore (?:he|she|they|it) can\b|"
                          r"\bby the time\b|\bwhile .{0,40} still\b", re.I)
BRAND_MARK_RE = re.compile(r"\blogo\b|\bwatermark\b|\bbrand(?:ing|ed)?\b|\bwordmark\b|\bcrest\b", re.I)
QUOTED_RE = re.compile(r"[\"“'']([^\"”'']{2,60})[\"”'']")
# ⛔ THE CITATION-FORM GAP AGAIN (2026-09-18). TEXT_RENDER_RE matched `reads "…"` and `lettering`
# but not `writes "…"` — the most natural way to ask for handwriting, and the exact phrasing of the
# defect this rule exists for. A writing VERB alone is an action ("he writes in his journal") and
# needs nothing; a writing verb WITH quoted words is a render and needs the hold.
WRITING_VERB_RE = re.compile(r"\b(writes?|writing|written|hand-?writing|scrawls?|inscription|"
                             r"scoreboard|jots?|notes? down)\b", re.I)
TWO_SHOT_RE = re.compile(r"\b(next to|beside|, then |alongside)\b", re.I)
# --- length: the measured band, and why it does not contradict the vendors -----------------------
# ⛔ Three sources, and they only look like they disagree.
#
#   [PRIMARY · this account's own testing across many real generations · 2026-09-07]
#       1800–2100 characters keeps the error rate low AND is detailed enough for accurate
#       generation, on this roster, in the house block format.
#   [PRIMARY · vendor docs · 2026-08-28]  BFL 30–80 words · Luma ~100 · Runway "no ideal length,
#       focus on clarity" · Sora 2 frames it as a trade · Google publishes none.
#   [PRIMARY · T2I-CoreBench, 1,080 prompts]  all 28 models degrade as COMPOSITIONAL DENSITY rises
#       — a structural failure no rewrite recovers, only fewer simultaneous demands.
#
# The reconciliation, and it is the whole reason this file now measures per block:
# **the vendor numbers describe a different artifact.** BFL's 30–80 words is one free-text prompt
# describing one picture. The house format is seven LABELLED blocks, each a scoped demand with its
# own header. 2100 characters across seven blocks is ~45 words per block — which lands INSIDE
# BFL's band per demand. The measurements agree the moment you stop measuring the wrong unit.
#
# So: the prompt-level band is the operator's measured number, and the per-block budget is what
# keeps that length from becoming density. A long prompt made of short, scoped blocks is not the
# thing CoreBench found degrading; a long prompt made of long blocks is.
BAND_LO = 1800            # [PRIMARY · own testing · 2026-09-07] — below this is thinner than measured
BAND_HI = 2100            # the top of the measured band
THIN_PROMPT = 1400        # ~22% below the floor — meaningfully short of where errors were measured
                          # low, while leaving room for a legitimately spare frame. A WARN, never a
                          # fail: the band is an observation about this account's stack, not a law.
MAX_PROMPT = 2500         # ~20% past the top of the band; nobody has measured beyond it
MAX_SUPPRESS = 500
WORDS_PER_SEC = 2.5
# ⛔ A CLIP'S LENGTH COMES FROM ITS TIME IN THE CUT, NEVER FROM A DEFAULT (2026-10-26: "This 5
# second thing makes projects using the skill think all shots are 5 seconds"). The references said
# "base clip length is usually 5s" and nothing tied `duration:` to the shot list, so a direct-response job took
# 5 s for every clip. Now a clip says how long the edit holds it (`cut:`, the shot list's Dur) and the
# lint derives what to generate: lead-in (the model settles out of the start frame) + cut + handle
# (past the cut, for a planned transition), rounded up to a whole second and lifted to the model's
# minimum. Shorter cannot cover the shot; much longer buys a dead front (the model peaks in its last
# second, timing-and-performance.md §5), not more action.
LEAD_IN_S = 1.0          # image-to-video settle at the head (ai-generation.md, the settle row)
LEAD_IN_T2V_S = 0.5      # no start frame: a shorter head ramp
HANDLE_S = 1.0           # default handle; `handle: 0` for hard cuts both sides, up to 2 for a dissolve
CLIP_SLACK_S = 3.0       # more than this past the derived length is warned


def clip_length_need(cut: float, handle: float, lead: float, min_s: float = 0.0) -> int:
    import math
    return int(max(min_s, math.ceil(lead + cut + handle - 1e-9)))
# The minimum non-speech time in a dialogue clip. The course's rule of thumb is 1-2s before a
# character speaks after something lands on them; 1.0 is the floor below which there is no beat at
# all. [SECONDARY · course notes] — a default, not a measurement.
AIR_SECONDS = 1.0

# Per-block word budgets. A block over budget is where density actually accumulates — [CAMERA] is a
# lens, a height and one move; [SUBJECT] and [ENVIRONMENT] legitimately carry more. These are WARN,
# not FAIL: they are a calibration from the band above divided across the blocks, not a measurement
# of their own, and a block that earns its length should be able to keep it.
BLOCK_BUDGET = {
    "SUBJECT": 70, "CHARACTER": 70, "ENVIRONMENT": 70, "START FRAME": 70,
    "MOTION": 70, "PERFORMANCE": 75, "SPEECH": 40,   # PERFORMANCE 55 → 75 (2026-09-30): card v2
                                                     # adds three short lines — STIMULUS, TARGET, BODY
    "LIGHTING": 50, "LIGHTING/MOOD": 50, "STYLE": 35, "COLORS": 30,
    "CAMERA": 25, "SAFE ZONE": 25, "SETTING": 60, "LOCATION": 45,
}
# The arithmetic that sets those, and the direction it runs in. A frame prompt's descriptive blocks
# — SUBJECT · CHARACTER · ENVIRONMENT · LIGHTING · CAMERA · STYLE · SAFE ZONE — sum to 345 words,
# which at the ~5.9 chars/word this format actually measures is ~2035 characters: inside the band.
# ⛔ An earlier draft ran the derivation backwards and set them at 295 words (~1730 chars), so a
# prompt with EVERY block at budget could not reach the floor of the band it was supposedly derived
# from. Found by writing one and measuring it, 2026-09-07. The operator's measured band is
# [PRIMARY]; these budgets are [ASSUMED] and take their values FROM it, never the reverse.
# A demand is an independent thing the model must satisfy. Clauses split on these carry one each.
DEMAND_SPLIT_RE = re.compile(r"[,;.]|\band\b|\bwith\b|\bwhile\b", re.I)
# ⛔ Density is demands PER HUNDRED WORDS, not a demand count. An absolute count is just length
# again in a different unit, and it would fight the band above: a well-formed prompt at only 960
# chars already carries 29 demands, so any absolute threshold low enough to be meaningful would
# fire on every prompt inside the measured band. Found by measuring, 2026-09-07, after an earlier
# draft of this file set the count at 26 and immediately flagged a legitimate prompt.
#
# The rate is what CoreBench's finding is actually about, and it separates the two failure modes
# cleanly: run-on prose is long and NOT dense; a comma-list of nouns is dense and NOT long.
# Calibration [ASSUMED · house, derived from the band · 2026-09-07]: well-formed house prose
# measures ~18 per 100 words; a degenerate comma-list measures ~50. 30 sits between them and does
# not fire anywhere inside the band. ⛔ It is a house number, not a measured threshold — CoreBench
# established that density degrades, never at what value.
DENSITY_PER_100_WARN = 30

# --- v2.45 (2026-10-29): the model's ceiling, the image edit, the detail score, the Scenario refusals ----
# ⚡ THE CEILING IS THE MODEL'S; THE BAND IS OURS. MAX_PROMPT was one house number for every model. The vendors'
# own limits run from 1,500 characters (Wan 2.6, truncated without an error) to 26,000 (Kling 4.0, English)
# [the author's research notes, read 2026-10-29]. So the lint FAILS above the model's TRUE ceiling
# (assets/higgsfield-rates.json → call_contract, then prompt_limits), the measured band and the 2,500 house figure
# become WARNs where the ceiling is higher, and a model with no published cap keeps 2,500 as a FAIL that says it
# is the house's (Cinema Studio, Soul, FLUX). prompting-craft.md §11g carries the table and its sources.
HOUSE_CEILING = MAX_PROMPT
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff]")


def prompt_limit(model: str) -> dict:
    """The prompt and negative ceilings for one model id: call_contract first, then prompt_limits, then the longest
    matching `_families` prefix, else the house 2,500 marked as the house's. Never raises."""
    m = (model or "").strip()
    t = _rates() or {}
    row, where = None, "none"
    c = (t.get("call_contract") or {}).get(m)
    if isinstance(c, dict) and "prompt_max_chars" in c:
        row, where = c, "call_contract"
    else:
        pl = t.get("prompt_limits") or {}
        if isinstance(pl.get(m), dict):
            row, where = pl[m], "prompt_limits"
        else:
            fam = pl.get("_families") or {}
            for k in sorted((k for k in fam if not k.startswith("_")), key=len, reverse=True):
                if m.startswith(k) and isinstance(fam[k], dict):
                    row, where = fam[k], f"prompt_limits._families[{k}]"
                    break
    row = row or {}
    mx = row.get("prompt_max_chars")
    mixed = mx if isinstance(mx, dict) else None
    if mixed:
        mx = int(mixed.get("english") or HOUSE_CEILING)
    house = bool(row.get("house_ceiling")) or not isinstance(mx, (int, float))
    if not isinstance(mx, (int, float)):
        mx = HOUSE_CEILING
    neg = str(row.get("negative") or "unknown").lower()
    if neg not in ("field", "none", "unknown"):
        neg = "unknown"
    src = row.get("limit_source") or {}
    srcline = " · ".join(x for x in (str(src.get("confidence") or ""), str(src.get("url") or ""),
                                     f"read {src['read']}" if src.get("read") else "") if x) or \
        "no entry in assets/higgsfield-rates.json"
    return {"model": m, "from": where, "max": int(mx), "mixed": mixed, "house": house,
            "truncates": bool(row.get("truncates")), "negative": neg,
            "negative_max": int(row["negative_max_chars"]) if isinstance(row.get("negative_max_chars"), (int, float)) else None,
            "shot_max": row.get("shot_max_chars"), "max_shots": row.get("max_shots"),
            "warn_cjk_over": row.get("warn_cjk_over"), "warn_words_over": row.get("warn_words_over"),
            "warn_nonascii_over": row.get("warn_nonascii_over"), "source": srcline}


def ceiling_over(text: str, lim: dict) -> str:
    """'' when the text fits the model's ceiling, else what is over, in the vendor's own terms."""
    n = len(text or "")
    if lim.get("mixed"):
        en, ne = float(lim["mixed"].get("english") or 1), float(lim["mixed"].get("non_english") or 1)
        e = sum(1 for ch in (text or "") if ord(ch) < 128)
        share = e / en + (n - e) / ne
        if share > 1 + 1e-9:
            return (f"{e} English + {n - e} non-English characters use {share:.2f} of {lim['model']}'s mixed allowance "
                    f"(E/{en:.0f} + N/{ne:.0f} must stay ≤ 1; ASCII is counted as English, an assumption)")
        return ""
    return f"{n} chars > {lim['max']}" if n > lim["max"] else ""


def ceiling_name(lim: dict) -> str:
    if lim["house"]:
        return (f"house ceiling, unknown vendor cap — {lim['model'] or 'this model'} publishes no prompt limit "
                f"({lim['source']})")
    return (f"{lim['model']}'s ceiling [{lim['source']}]" +
            ("; over it the vendor truncates SILENTLY, with no error" if lim["truncates"] else ""))


# ⚡ THE IMAGE EDIT (`kind: edit`). An edit changes one concept in a picture that exists and keeps the rest; it is
# the source of the AI-edited target frame the owner allows as a gated per-shot opt-in (`gate.py approve
# target:<SHOT>`, 2026-10-28). Its structure is the one Scenario's edit pages and our own INPUT LOCK converge on: say
# what the source is, name everything that must survive (models protect what is named), one concept of change with
# its placement, size, material and how it meets the light, then the output [SECONDARY · scenario-alter-web-addendum
# §1.1, §2.2, §3.3 · scenario-alter-integration §5; specifics-catalogue.md §6.1].
EDIT_REQUIRED = ["SOURCE", "KEEP", "CHANGE", "LIGHT MATCH", "OUTPUT"]
EDIT_GRAMMAR_BLOCKS = {"SOURCE", "KEEP", "REFERENCES", "OUTPUT", "LIGHT MATCH"}   # "not its …" is the grammar here
EDIT_FLOOR_FAIL = 600      # [ASSUMED · house 2026-10-29] — calibrate against approved edits
EDIT_FLOOR_WARN = 1000     # [ASSUMED · house 2026-10-29]; Scenario's kept edit prompts ran 1,179–1,684
EDIT_USES = ("frame", "target")
MATERIAL_WORDS = (r"wood\w*|oak|walnut|pine|bamboo|stone|marble|granite|slate|limestone|concrete|brick|tiles?|tiled|plaster|"
                  r"stucco|steel|stainless|metal\w*|alumin(?:i)?um|brass|copper|iron|chrome|glass|ceramic|porcelain|clay|"
                  r"terracotta|linen|cotton|wool\w*|denim|leather|suede|silk|velvet|satin|felt|canvas|paper|cardboard|kraft|"
                  r"plastic|acrylic|resin|rubber|vinyl|enamel\w*|lacquer\w*|wicker|rattan|cork|grain|matte|gloss\w*|brushed|"
                  r"polished|weathered|worn|rough|smooth|frosted|textured|knit|woven|patina|rust\w*|condensation|fabric|"
                  r"gravel|sand|turf|fur|pores")
LIGHT_DIR_RE = re.compile(r"\b(?:left|right|above|overhead|behind|below|beneath|front|frontal|side|back|backlit|rim|top|"
                          r"north|south|east|west|o'clock|three[- ]quarter)\b|\d{1,3}\s?°", re.I)
LIGHT_SRC_RE = re.compile(r"\b\d{4}\s?K\b|\bkelvin\b|\b(?:warm|cool|cold|neutral|tungsten|daylight|sun|sunlight|window|lamp|"
                          r"candle\w*|neon|fluorescent|led|practical|overcast|golden hour|blue hour|moon\w*|fire\w*|skylight|"
                          r"streetlight|headlights?|softbox|strip ?light|ring ?light)\b", re.I)
KEEP_CATEGORIES = {
    "identity/face": r"\b(?:face|faces|identity|likeness|features|expression|skin(?: tone)?|hair\w*|eyes|freckles|beard)\b",
    "pose": r"\b(?:pose|posture|stance|gesture|hands?|fingers|arms?|grip|body position)\b",
    "framing/composition": r"\b(?:framing|composition|crop|frame edges?|headroom|layout|aspect|horizon line|"
                           r"(?:upper|lower|left|right|centre|center) third|\d{1,3}\s?% (?:height|width|of the frame))\b",
    "light direction + colour temperature": r"\b(?:light|lighting|key|shadows?|highlights?|colou?r temperature|white balance|"
                                            r"\d{4}\s?K|kelvin|exposure)\b",
    "lens/perspective": r"\b(?:lens|focal length|\d{2,3}\s?mm|perspective|camera (?:height|angle|position)|eye[- ]level|"
                        r"depth of field|focus|angle of view)\b",
    "background/set": r"\b(?:background|backdrop|set|setting|room|walls?|environment|shel(?:f|ves)|counter|floor|window|sky|"
                      r"surroundings|location|doorway|interior|exterior)\b",
    "wardrobe": r"\b(?:wardrobe|clothing|clothes|outfit|garments?|shirt|blouse|jacket|coat|dress|skirt|trousers|jeans|apron|"
                r"uniform|sleeves?|collar|hat|scarf|shoes|boots|sweater|hoodie)\b",
    "product/label": r"\b(?:product|labels?|pack|packaging|package|bottle|can|jar|box|carton|tube|logo|wordmark|brand mark|lid)\b",
}
KEEP_MIN = 4
EDIT_LANGUAGE_RE = re.compile(r"\b(?:an edit of|edit (?:the|this) (?:\w+ )?(?:reference|photo\w*|image|picture|frame)|"
                              r"exactly (?:the|as in the) reference|as in the reference|the source,? untouched|"
                              r"change nothing else|everything else (?:is|stays|as in) (?:the source|unchanged|untouched)|"
                              r"keep exactly as in)\b", re.I)
ADD_REPLACE_RE = re.compile(r"\b(?:add\w*|replac\w*|swap\w*|insert\w*|place[sd]?|put|puts|introduc\w*|instead of|in place of|"
                            r"becomes?|substitut\w*)\b", re.I)
CHANGE_SPECIFICS = {
    "placement in frame": r"\b(?:left|right|centre|center|middle|foreground|background|upper|lower|top|bottom|third|corner|"
                          r"edge|beside|next to|same (?:spot|place|position)|where the|in (?:her|his|their|the) (?:right |left )?hands?|"
                          r"on the \w+|at the \w+)\b",
    "size": r"\b\d+(?:\.\d+)?\s?(?:cm|mm|m|in|inch(?:es)?|ft)\b|\b(?:size|sized|scale|same (?:height|width|size)|"
            r"as (?:tall|wide|large|big) as|height|tall|width|wide)\b|\d{1,3}\s?% of the (?:frame|width|height)",
    "material": r"\b(?:" + MATERIAL_WORDS + r"|material)\b",
    "how it meets the light (contact, shadow, reflection)": r"\b(?:shadows?|reflect\w*|contact|rests? on|sits? on|stands? on|"
                                                            r"touch\w*|occlu\w*|highlights?|specular|glint\w*|"
                                                            r"catch(?:es)? the light|refract\w*)\b",
}

# ⚡ THE DETAIL SCORE. The band says how LONG; it cannot say whether the characters carry decisions. The score counts
# the concrete slots a prompt fills — the things a model otherwise fills in itself, differently every take. A FAIL
# below the per-kind minimum; the score and the missing slots go into the sidecar, to be calibrated against what was
# approved. Minimums [ASSUMED · house 2026-10-29], set so the house fixtures and the approved corpus pass.
DETAIL_MIN = {"frame": 5, "clip": 3, "edit": 7}
FRAME_SLOTS = [
    ("lens in mm", r"\b\d{2,3}\s?mm\b", None),
    ("light direction", LIGHT_DIR_RE.pattern, "LIGHTING"),
    ("light quality", r"\b(?:hard|soft|diffused?|diffusion|harsh|specular|dappled|bounced?|direct|filtered|crisp|wrapping|"
                      r"feathered|gentle|grazing|raking|broad|flat|contrasty|low[- ]contrast|high[- ]contrast)\b", "LIGHTING"),
    ("colour temperature or named source", LIGHT_SRC_RE.pattern, "LIGHTING"),
    ("camera height/angle", r"\b(?:eye[- ]level|low[- ]angle|high[- ]angle|overhead|top[- ]down|bird'?s[- ]eye|worm'?s[- ]eye|"
                            r"(?:waist|chest|hip|knee|shoulder|head|counter|table|ground|floor)[- ]height|ground[- ]level|"
                            r"from (?:above|below)|dutch|\d+(?:\.\d+)?\s?(?:m|cm|ft) (?:high|up|above|off the (?:ground|floor))|"
                            r"camera (?:height|at)|lens height|level with)\b", None),
    ("subject size in frame", r"\d{1,3}\s?%|\b(?:fills?|filling|occupies|occupying|takes? up)\b[^.\n]{0,30}\bframe\b|"
                              r"\b(?:a|one|two)[- ](?:third|quarter|half|fifth)s? of the frame\b|\bhalf (?:of )?the frame\b|"
                              r"\b(?:ECU|XCU|CU|MCU|MS|MLS|WS|EWS)\b|\b(?:extreme )?close[- ]?up\b|"
                              r"\bmedium (?:close[- ]?up|shot|wide|long shot)\b|\bwide shot\b|\bfull[- ](?:length|body|figure)\b|"
                              r"\bhead[- ]and[- ]shoulders\b|\bwaist[- ]up\b", None),
    ("materials/textures", r"\b(?:" + MATERIAL_WORDS + r")\b", None),
    ("time of day", r"\b(?:morning|noon|midday|afternoon|evening|dusk|dawn|sunrise|sunset|night\w*|midnight|golden hour|"
                    r"blue hour|twilight|daybreak|daytime|daylight)\b|\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b|\b\d{1,2}:\d{2}\b", None),
    ("background depth", r"\b(?:out of focus|defocus\w*|bokeh|shallow (?:depth|focus)|deep focus|depth of field|"
                         r"soft(?:ened)? (?:background|behind)|background (?:blur\w*|soft\w*|falls? off|recedes?)|blurr?(?:ed|y)|"
                         r"in the background|far wall|middle ?ground|foreground|receding|distant|in the distance|horizon)\b|"
                         r"\bf/\d+(?:\.\d+)?|\b\d+(?:\.\d+)?\s?m (?:behind|away|back|beyond)\b", None),
]
TIME_RE = re.compile(r"\b\d+(?:\.\d+)?\s?(?:s|sec|secs|seconds)\b|\b\d+(?:\.\d+)?\s?[-–—]\s?\d+(?:\.\d+)?\s?s\b|"
                     r"\b\d:\d{2}\b|\b(?:at|by|until|from) \d+(?:\.\d+)?\b|\bframe \d+\b", re.I)
CHANGE_VERB_RE = re.compile(r"\b(?:mov\w+|slid\w*|slides?|roll\w*|fall\w*|fell|ris\w+|rose|open\w*|spread\w*|fill\w*|empt\w+|"
                            r"land\w*|drop\w*|tip\w*|flip\w*|pour\w*|splash\w*|lift\w*|enter\w*|leav\w*|appear\w*|emerg\w*|"
                            r"swing\w*|sway\w*|stir\w*|flick\w*|shak\w*|spin\w*|twist\w*|bend\w*|fold\w*|crumbl\w*|melt\w*|"
                            r"drip\w*|steam\w*|smok\w*|flutter\w*|ripple\w*|crack\w*|break\w*|tear\w*|grow\w*|shrink\w*|"
                            r"dim\w*|brighten\w*|glint\w*|flash\w*|blink\w*|turn\w*|reach\w*|grab\w*|grip\w*|hold\w*|held|"
                            r"set\w*|plac\w+|press\w*|push\w*|pull\w*|tap\w*|wip\w+|cross\w*|walk\w*|step\w*|run\w*|jump\w*|"
                            r"settl\w*|sink\w*|float\w*|drift\w*|lower\w*|raise\w*|nod\w*|smil\w*|look\w*|glanc\w*|"
                            r"inhal\w*|exhal\w*|breath\w*|swallow\w*|bites?|biting|sips?|sipping|chew\w*|lean\w*|sit\w*|"
                            r"seated|stand\w*|kneel\w*|crouch\w*|catch\w*|caught|throw\w*|toss\w*|hand\w*|pass\w*|flow\w*|"
                            r"rock\w*|bounc\w*|jingl\w*|clatter\w*|travel\w*|track\w*|rush\w*|gather\w*|spill\w*|"
                            r"slump\w*|sag\w*|loosen\w*|tighten\w*|clench\w*|widen\w*|narrow\w*|shift\w*|arriv\w*)\b", re.I)
SPEED_RE = re.compile(r"\b(?:slow\w*|fast(?:er)?|quick\w*|steady|steadily|gentle|gently|gradual\w*|brisk\w*|rapid\w*|creep\w*|speed|pace|"
                      r"crawl\w*|smooth\w*|constant speed|even speed|whip\w*)\b|\b\d+(?:\.\d+)?\s?(?:m/s|cm/s|mm/s|°/s|deg/s|"
                      r"km/h|mph)\b|\bover (?:\d+(?:\.\d+)?\s?(?:s|sec|seconds)|the (?:whole|full) clip)\b|\bin \d+(?:\.\d+)?\s?s\b",
                      re.I)
STILL_RE = re.compile(r"\b(?:stays?|remains?|unchanged|unmoving|motionless|does not (?:move|change|shift)|doesn'?t (?:move|change)|"
                      r"never (?:moves|changes|shifts|drifts|leaves)|holds? (?:still|steady|its|their)|held (?:still|steady)|"
                      r"fixed|keeps? (?:its|their|the)|constant|in place|stock[- ]still|locked to|(?:frame|camera|shot) holds|then still|"
                      r"stays? still|the rest (?:stays|holds))\b", re.I)

# ⛔ FILLER IS NOT DETAIL. Praise words carry no decision a model can act on and the vendors name the stack as
# degrading (§2.1). A WARN lists them; past 5 % of the words the prompt is mostly praise and FAILS.
FILLER_WORDS = ("cinematic", "stunning", "beautiful", "gorgeous", "epic", "breathtaking", "masterpiece", "masterful", "8k",
                "16k", "ultra-detailed", "ultra detailed", "hyper-detailed", "hyper detailed", "highly detailed",
                "hyperrealistic", "hyper-realistic", "hyper realistic", "ultra-realistic", "ultra realistic",
                "award-winning", "award winning", "amazing", "incredible", "magnificent", "majestic", "spectacular",
                "mesmerizing", "mesmerising", "jaw-dropping", "best quality", "high quality", "trending on artstation",
                "octane render", "unreal engine")
FILLER_RE = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(w) for w in sorted(FILLER_WORDS, key=len, reverse=True))
                       + r")(?![a-z0-9])", re.I)
FILLER_FAIL_SHARE = 0.05

# ⛔ THE SCENARIO REFUSALS (the author's research notes E1, E6, E10, P3, P6).
# E10: a request carrying the word "watermark" was refused as watermark removal and STILL CHARGED.
WATERMARK_RE = re.compile(r"\bwater[- ]?mark(?:s|ed|ing)?\b", re.I)
WATERMARK_SUPPRESS_FAILS = False   # the positive text always FAILS; in [SUPPRESS] a WARN while existing lists are cleaned
#                                   (the gate refuses to send it either way). Flip to True once no fixture carries it.
# E1: "no logos" / "no text" does not stop invented lettering on signs, screens and scarves — saying what each one
# shows does.
SIGNAGE_RE = re.compile(r"\b(?:shop ?fronts?|store ?fronts?|signboards?|signage|billboards?|posters?|placards?|banners?|"
                        r"menu boards?|scoreboards?|(?:number|licen[cs]e) plates?|newspapers?|magazines?|book covers?|"
                        r"(?:neon |street |shop |road )?signs?(?!\s+of\b)|(?:tv|television|phone|laptop|computer|tablet) screens?|"
                        r"screens?(?![- ](?:left|right|direction|centre|center|space|time))|monitors?)\b", re.I)
SIGN_DESCRIBED_BEFORE_RE = re.compile(r"\b(?:blank|plain|unlettered|unmarked|dark|black|switched[- ]off|empty|matte|frosted|"
                                      r"out[- ]of[- ]focus|blurred|defocused|soft|faded|weathered)\b[^.\n,;]{0,20}$", re.I)
SIGN_DESCRIBED_AFTER_RE = re.compile(r"^[^.\n;]{0,60}\b(?:shows?|showing|reads?|displaying|carries|carrying|with (?:only|a|an|the)|"
                                     r"too (?:small|far|soft) to read|out of focus|blurred|dark|switched off|blank)\b", re.I)
TEXT_BAN_RE = re.compile(r"\bno (?:other |added |visible |readable )?(?:text|logos?|lettering|letters|words|writing|typography|"
                         r"branding|brand marks?|signage)\b|\bwithout (?:any )?(?:text|logos?|lettering|letters)\b|"
                         r"\b(?:text|logo)[- ]free\b", re.I)
SUP_TEXT_ITEMS = {"text", "logo", "logos", "lettering", "letters", "words", "writing", "typography", "captions",
                  "subtitles", "readable text", "brand marks", "branding"}
# E6 / P6: a clip whose model generates sound adds a score of its own unless told not to.
NO_MUSIC_RE = re.compile(r"\bno (?:background |added |other )?(?:music|score|soundtrack|songs?)\b|"
                         r"\bwithout (?:any )?(?:music|score)\b|\bmusic[- ]free\b", re.I)
# P3: when a video reference and image references share a call, one sentence says which input decides the framing.
FRAMING_LINE_RE = re.compile(
    r"\b(?:framing|composition|camera (?:path|position|move)|shot size)\b[^.\n]{0,80}?\b(?:from|follows?|comes? from|"
    r"(?:is|are) (?:set|decided|taken|owned) by|as in|matches?|of)\b[^.\n]{0,40}?"
    r"(?:@?(?:Image|Video)\s?\d|\bthe (?:video|blocking|plate|start frame|still|image|reference|first frame))|"
    r"(?:@?(?:Image|Video)\s?\d|\bthe (?:video|blocking|plate|start frame|still|image))[^.\n]{0,60}?"
    r"\b(?:decides?|sets?|owns?|controls?|wins? on|gives?|is|carries)\b[^.\n]{0,25}?\b(?:the )?(?:framing|composition|camera)\b",
    re.I)


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "on", "yes", "1")


def _beat(mo: str, key: str) -> str:
    m = re.search(rf"(?ms)^\s*{key}\s*:\s*(.+?)(?=^\s*(?:START|MID|END|INTENT|MOVES LIKE)\s*:|\Z)", mo or "")
    return m.group(1).strip() if m else ""


def detail_report(kind: str, bl: dict, positive: str) -> dict:
    """{score, of, min, filled, missing} — the concrete slots a prompt fills (see DETAIL_MIN)."""
    filled, missing = [], []

    def slot(name, ok):
        (filled if ok else missing).append(name)
    if kind == "frame":
        for name, rx, block in FRAME_SLOTS:
            where = bl.get(block, "") if block and bl.get(block) else positive
            slot(name, re.search(rx, where or "", re.I))
    elif kind == "clip":
        mo = bl.get("MOTION", "")
        for k in ("START", "MID", "END"):
            b = _beat(mo, k)
            slot(f"{k} with a time", TIME_RE.search(b))
            _words = len(re.findall(r"[A-Za-z][A-Za-z'-]{2,}", b))
            change = CHANGE_VERB_RE.search(b) or SUBJECT_MOTION_RE.search(b) or (k != "START" and SETTLE_RE.search(b)) or \
                (k == "START" and _words >= 4) or \
                (_words >= 4 and re.search(r"\b[a-z]{3,}(?:ing|ed|es)\b", b))   # a verb the lists do not know
            slot(f"{k} with a visible {'state' if k == 'START' else 'change'}", change)
        cam = re.sub(r"(?i)\b(?:no|not|never|without|avoid|zero)\b[^.;\n]*", " ", bl.get("CAMERA", ""))
        found = {c for c, pats in CAMERA_CLASSES.items() if any(re.search(p, cam, re.I) for p in pats)}
        hh = any(re.search(p, cam, re.I) for p in CAMERA_TEXTURE["handheld"])
        slot("one camera move with its speed (or a locked-off camera)",
             ("static" in found and len(found) == 1) or (len(found - {"static"}) == 1 and SPEED_RE.search(cam))
             or (hh and not (found - {"static"})))
        rest = "\n".join(v for k, v in bl.items() if k not in ("CAMERA", "SUPPRESS"))
        slot("a stillness line (what must not change)", STILL_RE.search(rest))
    elif kind == "edit":
        keep = bl.get("KEEP", "")
        for name, rx in KEEP_CATEGORIES.items():
            slot(f"KEEP: {name}", re.search(rx, keep, re.I))
        ch = bl.get("CHANGE", "")
        for name, rx in CHANGE_SPECIFICS.items():
            slot(f"CHANGE: {name}", re.search(rx, ch, re.I))
        lm = bl.get("LIGHT MATCH", "")
        slot("LIGHT MATCH: direction", LIGHT_DIR_RE.search(lm))
        slot("LIGHT MATCH: colour temperature or source", LIGHT_SRC_RE.search(lm))
    n = len(filled)
    return {"score": n, "of": n + len(missing), "min": DETAIL_MIN.get(kind, 0), "filled": filled, "missing": missing}


# ----------------------------------------------------------------------------------------------
def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_prompt(s: str) -> str:
    """Identical to gate.normalize_prompt — the hash on both sides must agree."""
    s = (s or "").replace("’", "'").replace("‘", "'").replace("“", '"') \
        .replace("”", '"').replace("—", "-").replace("–", "-").replace("\r", "")
    return re.sub(r"\s+", " ", s).strip()


def roster() -> dict | None:
    """The priced, approved video models. ⛔ None when the asset cannot be read — and None FAILS the
    lint. It used to return {} and the check read `if model and ro and model not in ro`, so a missing
    file passed every model silently: the §6b SILENT PASS, found 2026-09-19."""
    t = _rates()
    if t is None or not isinstance(t.get("rate_table"), dict):
        return None
    return {k: v for k, v in t["rate_table"].items() if not k.startswith("_")}


def res_px(res: str) -> int:
    """'1080p' → 1080, '2k' → 1440-ish class, '4k' → 2160, '768p' → 768."""
    r = res.lower().strip()
    if r.endswith("p") and r[:-1].isdigit():
        return int(r[:-1])
    return {"1k": 1024, "2k": 1440, "4k": 2160, "8k": 4320}.get(r, 0)


def split_front(text: str) -> tuple[dict, str]:
    """Frontmatter `key: value` lines between --- fences; `refs:` collects `- ` items."""
    fm: dict = {}
    body = text
    if text.startswith("---"):
        parts = text.split("\n---", 1)
        head = parts[0][3:]
        body = parts[1] if len(parts) > 1 else ""
        cur_list = None
        for line in head.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            if line.startswith((" ", "\t")) and cur_list is not None and line.strip().startswith("-"):
                item = {}
                for kv in re.split(r"\s*[·,]\s*", line.strip()[1:].strip()):
                    if ":" in kv:
                        k, v = kv.split(":", 1)
                        item[k.strip().lower()] = v.strip()
                fm.setdefault(cur_list, []).append(item)
                continue
            m = re.match(r"^([A-Za-z_][A-Za-z_ ]*):\s*(.*)$", line)
            if m:
                k, v = m.group(1).strip().lower(), m.group(2).strip()
                qm = re.match(r'^"((?:[^"\\]|\\.)*)"', v) or re.match(r"^'((?:[^'\\]|\\.)*)'", v)
                if qm:
                    v = qm.group(1)                      # a quoted value keeps its # and its spaces
                else:
                    v = re.sub(r"\s+#.*$", "", v).strip()
                    if v.startswith("#"):          # `refs:   # a comment` is still an empty value
                        v = ""
                if v == "":
                    cur_list = k
                    if not isinstance(fm.get(k), list):
                        fm[k] = []
                else:
                    cur_list = None; fm[k] = v
    return fm, body.lstrip("\n")


def _sidecar_of(asset: str) -> str:
    """The ONE sidecar resolver (provenance.find_sidecar): `<asset>.json` first, the legacy
    `<stem>.json` second. Two readers with opposite precedence is how a cleared asset reads back
    as NOT CLEARED — found live 2026-09-06."""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import provenance
        return provenance.find_sidecar(asset)
    except Exception:
        for c in (asset + ".json", os.path.splitext(asset)[0] + ".json"):
            if os.path.isfile(c):
                return c
        return ""


def blocks_of(body: str) -> dict:
    """{'MOTION': 'text…', …} in file order; text before the first block is '_lead'."""
    out, pos, name = {}, 0, "_lead"
    for m in BLOCK_RE.finditer(body):
        out[name] = body[pos:m.start()].strip()
        name, pos = m.group(1).strip(), m.end()
    out[name] = body[pos:].strip()
    return {k: v for k, v in out.items() if v or k != "_lead"}


def prompt_text(body: str) -> str:
    """Everything except the [SUPPRESS] block — that goes to negative_prompt, never the prompt."""
    kept = []
    for m in re.finditer(r"(?s)(\[[A-Z][A-Z /\-]{1,30}\]\s*\n)(.*?)(?=^\[[A-Z][A-Z /\-]{1,30}\]\s*$|\Z)",
                         body, re.M):
        if m.group(1).strip() == "[SUPPRESS]":
            continue
        kept.append(m.group(0))
    lead = body[: body.find("[")] if "[" in body else body
    return normalize_prompt(lead + "\n" + "\n".join(kept))


# --- form: multishot (2026-10-25, references/multishot.md) ------------------------------------------
# House decision: "Multi shot but planned at senior level, with reference videos, start and end frames
# etc". A planned multi-shot clip replaces START/MID/END with STAGES: one primary state change and one
# visible end state per stage, budgets that tile the duration, one camera behaviour per stage, every
# internal cut named (it is final — no handles can be added to a cut the model made).
# [VENDOR · Higgsfield Seedance 2.5 "New capabilities (Part 2)" deck, supplied 2026-10-25]
MULTISHOT_REQUIRED = ["GOAL", "STAGES", "CONSISTENCY"]
# Higgsfield's own Ad Multiplier workflow validates a Seedance 2.5 prompt at <= 3900 characters
# [PRIMARY · Higgsfield MCP, ad-multiplier workflow v1.5, read 2026-10-24]. Over the single-clip band
# (2500) is a WARN: multi-shot length is unmeasured here.
MAX_PROMPT_MULTISHOT = 3900
STAGE_RE = re.compile(r"^\s*Stage\s+(\d+)\s*\|\s*(\d+(?:\.\d+)?)\s*(?:s\s*)?[-–—]\s*(\d+(?:\.\d+)?)\s*s\b"
                      r"\s*(?:\|\s*(.*))?$", re.I | re.M)
CUT_KINDS = ("hard", "match", "whip", "smash", "occlusion", "hidden", "wipe", "jump", "insert",
             "reverse", "continuous", "none", "j-cut", "l-cut")
TAG_RE = re.compile(r"@(Image|Video|Audio)\s?(\d+)", re.I)
GROUP_LABEL_RE = re.compile(r"^\s*\[(?:Characters?|Props?|Scenes?|Frames?|Motion(?: and Audio)?|Audio)\]",
                            re.I | re.M)
RANGE_BIND_RE = re.compile(r"@(?:Image|Video|Audio)s?\s?\d+\s*(?:through|thru|to|[-–—])\s*(?:@?(?:Image|Video|Audio)s?\s?)?\d+",
                           re.I)
# "three actions in one second" — the deck's NO FREQUENCIES rule
FREQUENCY_RE = re.compile(r"\b(?:\d+|two|three|four|five|six|several|multiple)\s+(?:\w+\s+){0,2}"
                          r"(?:actions?|moves?|movements?|times|steps?|cuts?|blinks?|nods?|beats?|gestures?|"
                          r"bites?|sips?|taps?|claps?|jumps?|spins?|turns?|shakes?|waves?|words?)\s+"
                          r"(?:in|per|within)\s+(?:one|a|1|half a|a single)\s+seconds?\b", re.I)
EXACT_POINT_RE = re.compile(r"\b(?:exactly\s+)?at\s+(?:the\s+)?\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds)\b", re.I)
LINE_ENTRY_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:s\s*)?[-–—]\s*(\d+(?:\.\d+)?)\s*s\s+([^:\n\"]{1,40}?):\s*[\"“]([^\"”\n]+)[\"”]",
                           re.M)

# --- form: scene (v2.49.0; house decisions 2026-11-05, "do it as they do it") ----------------------------
# The festival winners' way (the author's research notes, 12 films, 4,712 video calls): a
# Seedance 2.5 / Cinema Studio clip built from APPROVED REFERENCE SHEETS (character:, prop:, world:) plus a long
# structured prompt in the vendor's block order — not from an approved start frame. No frame owns the look, so
# the prompt carries it: [LIGHTING], [COLOR] and [STYLE] are expected here, and CLIP_FORBIDDEN does not apply.
# The clip's native sound is kept (directed in [AUDIO]); speech still goes through the voice gate.
# A job can go back to the frame-led i2v route with the project switch `frame-led`.
SCENE_REQUIRED = ["SCENE CONTEXT", "ACTIVE REFERENCES", "LOCATION MAP", "FIRST FRAME", "CAMERA",
                  "ACTION TIMING", "LIGHTING", "AUDIO", "POSITIVE LOCKS"]
SCENE_OPTIONAL = ["FORMAT MODE", "OPTICS", "PERFORMANCE", "PHYSICS", "COLOR", "STYLE", "TONE", "SHOTS",
                  "WARDROBE", "OUTPUT SETTINGS", "SPEECH", "CONSTRAINTS", "SUPPRESS", "REPAIR"]
# (v2.71.0) anatomy words that must never be named inside the prompt (a [CONSTRAINTS] tail is inside it); "face" is
# left out on purpose: "a face in frame" on an insert means a person who should not be there, a peripheral thing
CON_ANATOMY_RE = re.compile(r"\b(?:fingers?|hands?|limbs?|arms?|legs?|teeth|eyes?|brows?|mouths?|smile|head bobbing)\b",
                            re.I)    # a separate name: ANATOMY_RE (skin structures, the ECU check) is another rule
DEFECT_NOUN_RE = re.compile(r"\b(?:extra|fused|missing|sixth) fingers?\b|\bwarped (?:hands?|grip|face|text)\b|"
                            r"\bz-fighting\b|\binterpenetrat\w*|\bclipping through\b|\bgarbled (?:text|letters)\b|"
                            r"\b(?:face|identity|features?) morph\w*|\bmorphing (?:face|identity|features?)\b|"
                            r"\bvacant (?:face|stare)\b|\bdeformed (?:hands?|face|limbs?|fingers?)\b", re.I)
# narrowed after build review 1 (Sonnet): "morphing from one logo to the next" or "deformed dough" are not defects
SCENE_MODELS = ("seedance_2_5",)   # cinematic_studio_video_4_0 joins when it is on the roster (it reads the same blocks)
# The winners' prompts ran a median 6.4k characters (2.7k–16.3k across 12 films; the web app took 45k). Under
# SCENE_THIN the look, the place and the blocking cannot all be written; over SCENE_HOUSE_MAX is unmeasured and
# the MCP's own ceiling is unverified [ASSUMED · house 2026-11-05 — the first job checks it with get_cost].
SCENE_THIN = 2500
VIDEO_FLOOR_PX = 720       # v2.49.0: the generation floor for video takes (frames stay at 1080)
SCENE_HOUSE_MAX = 20000
# Words that open a mouth. With native audio on, an open mouth is read as speech: a festival team's character
# talked in a no-dialogue film until "open-mouth smile" left the prompt (festival study §3, BALLAST).
MOUTH_OPEN_RE = re.compile(r"\b(?:open[- ]mouth(?:ed)?|mouths? (?:open|opens|opening|agape|wide)|laugh(?:s|ing|ed)?|"
                           r"shout(?:s|ing|ed)?|yell(?:s|ing|ed)?|scream(?:s|ing|ed)?|gasp(?:s|ing|ed)?|"
                           r"cheer(?:s|ing|ed)?|sing(?:s|ing)?|talk(?:s|ing|ed)?|speak(?:s|ing)?|"
                           r"chatter(?:s|ing)?|mutter(?:s|ing|ed)?|whisper(?:s|ing|ed)?|toothy grin|grins? widely)\b", re.I)
NEGATED_BEFORE_RE = re.compile(r"\b(?:no|not|never|without|nobody|none)\b[^.;\n]{0,24}$", re.I)
SCENE_SPEECH_RE = re.compile(r"^\s*[A-Z][\w .'-]{0,30}:\s*[\"“「]", re.M)
VOICE_LINE_RE = re.compile(r"^\s*VOICE\s*(?:\([^)]*\))?\s*:", re.M | re.I)
AMBIENCE_RE = re.compile(r"\b(?:ambien\w*|room tone|air tone|atmos\w*|bed)\b", re.I)


def mouth_open_hits(text: str) -> list:
    """Mouth-opening words that are not negated ("no talking" is fine; "she laughs" is not)."""
    hits = []
    for m in MOUTH_OPEN_RE.finditer(text or ""):
        if NEGATED_BEFORE_RE.search(text[max(0, m.start() - 40):m.start()]):
            continue
        hits.append(m.group(0))
    return hits


def stages_of(text: str) -> list:
    """[STAGES] → [{n, t0, t1, shot, body, use, event, end, cut}] in file order."""
    out = []
    heads = list(STAGE_RE.finditer(text or ""))
    for i, m in enumerate(heads):
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]

        def field(name):
            mm = re.search(rf"^\s*{name}\s*:\s*(.+)$", body, re.I | re.M)
            return mm.group(1).strip() if mm else ""
        out.append({"n": int(m.group(1)), "t0": float(m.group(2)), "t1": float(m.group(3)),
                    "shot": (m.group(4) or "").strip(), "body": body, "use": field("Use"),
                    "event": field("Event"), "end": field(r"End\s*state"), "cut": field("Cut")})
    return out


def tag_map(fm: dict, reference_mode: bool, start_role) -> dict:
    """What @Image N / @Video N / @Audio N point at, in the order gate.py preflight emits `medias`:
    the approved start still first when it binds as a reference, then the refs in file order."""
    refs = fm.get("refs") if isinstance(fm.get("refs"), list) else []
    images, videos, audios = [], [], []
    if reference_mode and start_role == "image_references" and fm.get("start_frame"):
        images.append("the approved start frame")
    for i, r in enumerate(refs, 1):
        if not isinstance(r, dict):
            continue
        role = canonical_role(str(r.get("role") or "image").lower())
        label = f"refs[{i}] {r.get('what') or '?'}"
        if role == "image_references":
            images.append(label)
        elif role == "video_references":
            videos.append(label)
        elif role == "audio_references":
            audios.append(label)
    return {"image": images, "video": videos, "audio": audios}


def multishot_checks(fm: dict, bl: dict, F, W, tmap: dict, extra: dict) -> None:
    """The planned multi-shot clip (references/multishot.md §5, §9)."""
    for b in MULTISHOT_REQUIRED:
        if b not in bl:
            F(f"[{b}] missing — a multi-shot clip carries [GOAL], [STAGES] and [CONSISTENCY] "
              f"(references/multishot.md §9)")
    refs = fm.get("refs") if isinstance(fm.get("refs"), list) else []
    if refs and "REFERENCES" not in bl:
        F("[REFERENCES] missing — every reference is bound on its own line: 'Mika corresponds to "
          "@Image 2. Use only the appearance, hairstyle, and clothing.' (multishot.md §4)")
    stages = stages_of(bl.get("STAGES", ""))
    dur = _num(fm.get("duration"))
    if len(stages) < 2:
        F(f"[STAGES] has {len(stages)} stage(s) — write each as 'Stage N | a–b s | <size, lens, height, "
          f"one move>' followed by Use:, Event:, End state:, Cut:. One stage is a single-action clip: "
          f"use the normal clip form (multishot.md §5)")
    else:
        if [s["n"] for s in stages] != list(range(1, len(stages) + 1)):
            F("stages are not numbered 1..N in order (multishot.md §5)")
        if abs(stages[0]["t0"]) > 0.05:
            F(f"Stage 1 starts at {stages[0]['t0']:g} s — the budgets tile the clip from 0")
        for a, b in zip(stages, stages[1:]):
            if abs(a["t1"] - b["t0"]) > 0.05:
                F(f"Stage {a['n']} ends at {a['t1']:g} s and Stage {b['n']} starts at {b['t0']:g} s — "
                  f"budgets are consecutive and never overlap or leave a gap (multishot.md §5)")
        if dur is not None and abs(stages[-1]["t1"] - dur) > 0.25:
            F(f"the last stage ends at {stages[-1]['t1']:g} s and `duration:` is {dur:g} s — the stage "
              f"budgets must add up to the clip")
        for st in stages:
            n, span = st["n"], st["t1"] - st["t0"]
            if span <= 0:
                F(f"Stage {n} has no duration ({st['t0']:g}–{st['t1']:g} s)")
            elif span < 2.0:
                W(f"Stage {n} is {span:g} s — a stage under ~2 s tends to be merged or dropped; the "
                  f"Short Drama Screenwriter plans one shot per 2–5 s [VENDOR] (multishot.md §5)")
            if not st["event"]:
                F(f"Stage {n} has no `Event:` — one primary state change per stage (multishot.md §5)")
            elif len(re.findall(r"\bthen\b", st["event"], re.I)) > 1:
                W(f"Stage {n} Event carries several changes (two 'then's) — give a stage ONE primary state "
                  f"change; a second change is a second stage [VENDOR · Part 2 deck p.15]")
            if not st["end"]:
                F(f"Stage {n} has no `End state:` — what must be visible when it closes: positions, who "
                  f"holds what, what stays in frame (multishot.md §5)")
            if not st["use"]:
                W(f"Stage {n} has no `Use:` — name the characters, props, places and motions this stage "
                  f"uses; the rest stay out of it")
            if not st["shot"]:
                F(f"Stage {n} names no shot — 'Stage {n} | a–b s | MS, 35 mm, eye level, slow push-in'. "
                  f"Every internal shot is a row of the shot table (sequence-grammar.md)")
            else:
                cam = re.sub(r"(?i)\b(?:no|not|never|without|avoid|zero)\b[^.;\n]*", " ", st["shot"])
                cam = DOLLY_ZOOM_RE.sub(" ", cam)
                found = {c for c, pats in CAMERA_CLASSES.items() if any(re.search(x, cam, re.I) for x in pats)}
                moves = found - {"static"}
                if "static" in found and moves:
                    F(f"Stage {n} is both static and moving ({', '.join(sorted(found))}) — one camera "
                      f"behaviour per stage")
                elif len(moves) > 1:
                    F(f"Stage {n} names {len(moves)} moves ({', '.join(sorted(moves))}) — one camera "
                      f"behaviour per stage; the single-action rule moves down a level, it does not go away")
            if st is not stages[-1]:
                if not st["cut"]:
                    F(f"Stage {n} has no `Cut:` — name how it hands to Stage {n + 1} (hard, match on an "
                      f"action, whip, occlusion, wipe, continuous). An internal cut is final: it cannot "
                      f"be re-cut or given handles (multishot.md §2)")
                elif not any(k in st["cut"].lower() for k in CUT_KINDS):
                    W(f"Stage {n} Cut {st['cut']!r} is not one of {', '.join(CUT_KINDS)}")
        extra["stages"] = [{k: st[k] for k in ("n", "t0", "t1", "shot", "cut")} for st in stages]
    whole = "\n".join(v for k, v in bl.items() if k != "SUPPRESS")
    m = RANGE_BIND_RE.search(whole)
    if m:
        F(f"range binding {m.group(0)!r} — bind each subject on its own line ('Mika corresponds to "
          f"@Image 2'); the vendor's own DO NOT [VENDOR · Part 2 deck p.6]")
    m = FREQUENCY_RE.search(whole)
    if m:
        F(f"a frequency demand ({m.group(0)!r}) — never ask for a rate of actions per second; give "
          f"the action a budget [VENDOR · Part 2 deck p.18]")
    pts = EXACT_POINT_RE.findall(bl.get("STAGES", ""))
    if len(pts) > 2:
        W(f"{len(pts)} exact time points in [STAGES] — use stage budgets by default and pin one or two "
          f"critical beats at most; anchor reactions to their cause, not the clock [VENDOR · Part 2 deck p.18]")
    # tags against what the call will actually carry
    counts = {k: len(v) for k, v in tmap.items()}
    used = {}
    for mm in TAG_RE.finditer(whole):
        kind, n = mm.group(1).lower(), int(mm.group(2))
        used.setdefault(kind, set()).add(n)
        if n < 1 or n > counts.get(kind, 0):
            F(f"@{mm.group(1)} {n} points past what the call carries — {counts.get(kind, 0)} "
              f"{kind} input(s): {', '.join(tmap.get(kind) or ['none'])} (multishot.md §4)")
    bound = "\n".join(bl.get(k, "") for k in ("REFERENCES", "GOAL", "STAGES"))
    for kind, labels in tmap.items():
        for i, lab in enumerate(labels, 1):
            if not re.search(rf"@{kind}\s?{i}\b", bound, re.I):
                W(f"@{kind.capitalize()} {i} ({lab}) is never bound or used — a reference with no line saying "
                  f"what to take from it is decoration (multishot.md §4)")
    extra["tag_map"] = tmap
    for st in stages:
        listed = {(x.group(1).lower(), int(x.group(2))) for x in TAG_RE.finditer(st["use"])}
        if not listed:
            continue
        for x in TAG_RE.finditer(st["body"]):
            if (x.group(1).lower(), int(x.group(2))) not in listed:
                W(f"Stage {st['n']} mentions @{x.group(1)} {x.group(2)} but its Use: does not list it — an "
                  f"@tag only goes where its subject is present [VENDOR · Seedance 2.5 Prompt Writer]")
                break
    # reference scopes the multi-shot form asks for
    chars = 0
    for i, r in enumerate(refs, 1):
        if not isinstance(r, dict):
            continue
        what = str(r.get("what") or "").lower()
        chars += what == "character"
        if what == "prop" and not str(r.get("owner") or "").strip():
            W(f"refs[{i}] is a prop with no `owner:` — each prop belongs to exactly one character "
              f"[VENDOR · Part 2 deck p.10]")
        if what in ("environment", "motion") and not str(r.get("not") or "").strip():
            W(f"refs[{i}] ({what}) declares no `not:` — " + (
                "a place plate brings its people with it: `not: people in the plate`" if what == "environment"
                else "a motion video brings its person and its scene: `not: the person, the scene`")
              + " [VENDOR · Part 2 deck p.10]")
        if what == "endframe" and canonical_role(str(r.get("role") or "image").lower()) != "image_references":
            F(f"refs[{i}] what: endframe must be an `image_references` entry (the approved end still, "
              f"bound as a reference on a model with no true end frame)")
    if chars >= 2 and "WHERE" not in bl:
        W(f"{chars} characters and no [WHERE] — fix the seats per location and say what is behind each "
          f"person, or they swap places between shots (multishot.md §5)")
    # lines: each spoken once, inside one stage
    lines = [(float(a), float(b), who.strip(), txt.strip())
             for a, b, who, txt in LINE_ENTRY_RE.findall(bl.get("SOUND", ""))]
    seen = {}
    for a, b, who, txt in lines:
        key = flat_txt(txt)
        if key in seen:
            F(f"the line {txt[:40]!r} is listed twice — each line is spoken exactly once (multishot.md §6)")
        seen[key] = 1
        if stages and not any(st["t0"] - 0.05 <= a and b <= st["t1"] + 0.05 for st in stages):
            W(f"{who}'s line at {a:g}–{b:g} s crosses a stage boundary — a line never spills across a "
              f"cut unless the transition depends on it (multishot.md §6)")
    if lines:
        extra["has_speech"] = True
        extra["lines"] = [{"t0": a, "t1": b, "who": w, "text": t} for a, b, w, t in lines]


# ----------------------------------------------------------------------------------------------
# (v2.49.0, 2026-11-05: "use GPT 2.6 on Higgsfield primarily") GPT Image 2.6 is the primary image model for
# frames, sheets and edits. Its defaults are traps: quality `low` and resolution `1k` (models_explore get
# gpt_image_2_6, 2026-11-05) — so the file states both, and the gate sends exactly what the file says.
GPT26 = "gpt_image_2_6"
GPT26_QUALITY_OK = ("high", "xhigh", "max")
GPT26_FORMATS = ("png", "jpeg", "webp", "gif", "svg")


def gpt26_checks(fm: dict, refs: list, F, W) -> None:
    if str(fm.get("model") or "") != GPT26:
        return
    q = str(fm.get("quality") or "").strip().lower()
    if not q:
        F("`quality:` missing on gpt_image_2_6 — its default is `low`; state high, xhigh or max (ai-generation.md, "
          "the image model)")
    elif q not in GPT26_QUALITY_OK:
        F(f"`quality: {q}` on gpt_image_2_6 — a picture the clips inherit is made at high, xhigh or max")
    of = str(fm.get("output_format") or "png").strip().lower()
    if of not in GPT26_FORMATS:
        F(f"`output_format: {of}` — gpt_image_2_6 writes {', '.join(GPT26_FORMATS)}")
    if of == "svg" and refs:
        F("`output_format: svg` with `refs:` — the model takes no reference image for SVG output")
    if of == "gif":
        fc = _num(fm.get("frame_count"))
        if fc is not None and not (2 <= fc <= 64):
            F(f"`frame_count: {fc:g}` — a GIF takes 2–64 frames")
        sz = str(fm.get("size") or "").strip()
        if sz and sz != "auto" and not re.match(r"^\d+x\d+$", sz):
            F(f"`size: {sz}` — WIDTHxHEIGHT, each divisible by 16")
        elif sz and sz != "auto" and any(int(x) % 16 for x in sz.split("x")):
            F(f"`size: {sz}` — GIF dimensions must divide by 16")
    if refs and len(refs) > 0 and str(fm.get("kind") or "") == "frame":
        pass


# --- the scene file and the project DNA (v2.49.0; 2026-11-05: "consistency across prompts and shots, sequences,
# scenes … learn from the long prompts") ------------------------------------------------------------------------
# MEASURED on five festival films (the author's research notes): 25–39 % of each long shot prompt was
# text pasted VERBATIM from the other shots of the same scene (CONTROL 39 %, Soulless 33 %, Listen to Meh 25 %).
# Style and format lines were identical in every prompt (100 %); the cast/element bindings 45–100 %; constraints 31–73 %;
# light, optics, camera and the location map about 30–40 %; the action, the first frame and the acting were written per
# shot (0–17 %). BALLAST, the one exception (5 %), kept the same block STRUCTURE but rewrote every shot.
# So the house writes the shared part ONCE and the lint pastes it: 01-script/scenes/_PROJECT.dna.md (project-wide
# blocks: style, format, output, project locks) and 01-script/scenes/<SCENE>.scene.md (the scene's cast bindings and
# refs, location map, base light, colour, the sound bed and voice strings, wardrobe, scene locks). A `form: scene` shot
# that names `scene: <SCENE>` is ASSEMBLED: per block, DNA text + scene text + the shot's own text, in the template's
# order. A shot that must REPLACE a shared block says so: `override: LIGHTING — <why, in words>`. Change the scene file
# and every shot in it re-lints to a different prompt, so the gate refuses the old ones until they are re-linted.
SCENE_DIR = os.path.join("01-script", "scenes")
DNA_FILE = "_PROJECT.dna.md"
SCENE_BLOCK_ORDER = ["SCENE CONTEXT", "STYLE", "FORMAT MODE", "ACTIVE REFERENCES", "LOCATION MAP", "WARDROBE",
                     "FIRST FRAME", "OPTICS", "CAMERA", "SHOTS", "ACTION TIMING", "PERFORMANCE", "PHYSICS", "LIGHTING",
                     "COLOR", "TONE", "AUDIO", "SPEECH", "OUTPUT SETTINGS", "POSITIVE LOCKS", "REPAIR", "CONSTRAINTS",
                     "SUPPRESS"]
OVERRIDE_RE = re.compile(r"^\s*([A-Z][A-Z /\-]{1,30}?)\s*[—–-]+\s*(.+)$")


def _scene_root(path: str, job_root: str | None) -> str:
    return job_root or _job_root_of(path)


def scene_sources(path: str, fm: dict, job_root: str | None) -> dict:
    """{'dna': (file, fm, blocks) | None, 'scene': (file, fm, blocks) | None, 'problems': [...]}"""
    out = {"dna": None, "scene": None, "problems": []}
    root = _scene_root(path, job_root)
    sd = os.path.join(root, SCENE_DIR)
    dna = os.path.join(sd, DNA_FILE)
    if os.path.isfile(dna):
        dfm, dbody = split_front(read(dna))
        out["dna"] = (dna, dfm, blocks_of(dbody))
    sid = str(fm.get("scene") or "").strip()
    if sid:
        sf = os.path.join(sd, f"{sid}.scene.md")
        if not os.path.isfile(sf):
            out["problems"].append(f"`scene: {sid}` but {os.path.join(SCENE_DIR, sid + '.scene.md')} does not exist — "
                                   f"write the scene file first (`prompt_lint.py --template scene-file`)")
        else:
            sfm, sbody = split_front(read(sf))
            out["scene"] = (sf, sfm, blocks_of(sbody))
    return out


def assemble_scene(path: str, fm: dict, body: str, job_root: str | None) -> tuple:
    """(fm, body, extra, problems): the shot's frontmatter with the scene's refs first, and the body with the DNA and
    scene blocks pasted in, block by block, in the template's order. extra carries the source hashes for the sidecar."""
    src = scene_sources(path, fm, job_root)
    probs = list(src["problems"])
    extra = {}
    if not src["dna"] and not src["scene"]:
        return fm, body, extra, probs
    shot = blocks_of(body)
    overrides = {}
    for item in [x for x in re.split(r"\s*;\s*", str(fm.get("override") or "")) if x.strip()]:
        m = OVERRIDE_RE.match(item)
        if not m or len(m.group(2).split()) < 3:
            probs.append(f"`override: {item}` — name the block and say why in at least three words "
                         f"(`override: LIGHTING — the door opens and daylight floods in`)")
            continue
        overrides[m.group(1).strip()] = m.group(2).strip()
    layers = []
    for key in ("dna", "scene"):
        if src[key]:
            f_, sfm, sbl = src[key]
            layers.append(sbl)
            extra[f"{key}_file"] = os.path.relpath(f_, _scene_root(path, job_root))
            extra[f"{key}_sha"] = sha256_file(f_)
    shared = set().union(*[set(b) for b in layers]) - {"_lead"}
    for b in overrides:
        if b not in shared:
            probs.append(f"`override: {b}` but no DNA or scene block [{b}] exists to replace")
        if b not in shot:
            probs.append(f"`override: {b}` but the shot writes no [{b}] to replace it with")
    names = [b for b in SCENE_BLOCK_ORDER if b in shared or b in shot] + \
            [b for b in list(shared) + list(shot) if b not in SCENE_BLOCK_ORDER and b != "_lead"]
    seen, parts = set(), []
    lead = shot.get("_lead", "")
    if lead:
        parts.append(lead)
    for b in names:
        if b in seen:
            continue
        seen.add(b)
        if b in overrides:
            texts = [shot.get(b, "")]
        else:
            texts = [L.get(b, "") for L in layers] + [shot.get(b, "")]
        txt = "\n".join(t for t in texts if t.strip())
        if txt.strip():
            parts.append(f"[{b}]\n{txt}")
    # refs: the scene's first (so @Image N is the same sheet in every shot of the scene), then the shot's own
    if src["scene"]:
        srefs = [r for r in (src["scene"][1].get("refs") or []) if isinstance(r, dict)]
        own = [r for r in (fm.get("refs") or []) if isinstance(r, dict)]
        vals = {str(r.get("value") or r.get("file") or "") for r in srefs}
        fm = dict(fm)
        fm["refs"] = srefs + [r for r in own if str(r.get("value") or r.get("file") or "") not in vals]
        for k in ("world", "aspect", "model"):
            if not fm.get(k) and src["scene"][1].get(k):
                fm[k] = src["scene"][1][k]
    extra["overrides"] = overrides
    return fm, "\n\n".join(parts) + "\n", extra, probs


def scene_report(job_root: str, sid: str) -> dict:
    """`prompt_lint.py --scene <SCENE>`: every shot that names the scene, linted, and the cross-shot checks a single
    file cannot make: shots on one `setup:` share their optics and camera position; one cast binds the same sheets."""
    pdir = os.path.join(job_root, "01-script", "prompts")
    shots, fails, warns = [], [], []
    for f in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if not f.endswith(".clip.prompt.md"):
            continue
        fp = os.path.join(pdir, f)
        fm, body = split_front(read(fp))
        if str(fm.get("scene") or "") != sid:
            continue
        r = lint(fp, job_root)
        afm, abody, _x, _p = assemble_scene(fp, fm, body, job_root)
        shots.append({"file": f, "shot": fm.get("shot"), "setup": str(fm.get("setup") or "").strip(), "ok": r["ok"],
                      "fails": r["fails"], "chars": len(prompt_text(abody)), "blocks": blocks_of(abody),
                      "refs": [str(x.get("value") or x.get("file") or "") for x in (afm.get("refs") or [])
                               if isinstance(x, dict)]})
    if not shots:
        fails.append(f"no clip prompt names `scene: {sid}`")
    by_setup = {}
    for s_ in shots:
        if s_["setup"]:
            by_setup.setdefault(s_["setup"], []).append(s_)
    for su, group in by_setup.items():
        for b in ("OPTICS",):
            vals = {re.sub(r"\s+", " ", g["blocks"].get(b, "")).strip() for g in group}
            if len(vals) > 1:
                fails.append(f"setup {su}: {len(vals)} different [{b}] blocks across {', '.join(g['shot'] or '?' for g in group)} "
                             f"— one camera setup has one lens and one distance; put it in the scene file, or give the "
                             f"shots different `setup:` ids")
    for s_ in shots:
        if not s_["setup"]:
            warns.append(f"{s_['shot']}: no `setup:` — name the camera setup (A, B, C …) so shots on the same setup are "
                         f"held to the same lens and distance")
    return {"scene": sid, "shots": [{k: v for k, v in x.items() if k != "blocks"} for x in shots],
            "fails": fails, "warns": warns, "ok": not fails and all(x["ok"] for x in shots)}


def scene_checks(fm: dict, bl: dict, positive: str, F, W, extra: dict, job_root: str | None) -> None:
    """`form: scene` (v2.49.0): the vendor block template, references instead of a start frame, kept native sound.
    prompting-craft.md §12 is the contract; the author's research notes is the evidence."""
    model = str(fm.get("model") or "")
    if model and model not in SCENE_MODELS:
        W(f"`form: scene` on {model} — the template is written for {', '.join(SCENE_MODELS)}; another model may not "
          f"read its blocks the same way (prompting-craft.md §12)")
    for b in SCENE_REQUIRED:
        if b not in bl:
            F(f"[{b}] missing — a scene clip carries {', '.join('[' + x + ']' for x in SCENE_REQUIRED)} "
              f"(prompting-craft.md §12)")
    unknown = [b for b in bl if b != "_lead" and b not in SCENE_REQUIRED and b not in SCENE_OPTIONAL]
    if unknown:
        W(f"block(s) {', '.join('[' + b + ']' for b in unknown)} are not in the scene template — fold them into the "
          f"named blocks so the model reads one structure (optional: {', '.join(SCENE_OPTIONAL[:-1])})")
    refs = [r for r in (fm.get("refs") or []) if isinstance(r, dict)]
    if not refs and not fm.get("start_frame"):
        F("a scene clip with no `refs:` and no `start_frame:` — identity comes from the approved sheets "
          "(character:, prop:, world:); with none, every take invents the cast and the place (prompting-craft.md §12)")
    ar = bl.get("ACTIVE REFERENCES", "")
    if refs and ar and not TAG_RE.search(ar) and not re.search(r"<<<|@[A-Za-z]", ar):
        W("[ACTIVE REFERENCES] binds no reference by tag (@Image 1 …) — name each sheet and what it controls, one "
          "subject per line ('@Image 1: the courier — face, hair, jacket only')")
    if not str(bl.get("FIRST FRAME", "")).strip():
        pass
    elif re.search(r"\b(empty|establishing|before (?:he|she|they) (?:enter|arrive))\b", bl.get("FIRST FRAME", ""), re.I):
        W("[FIRST FRAME] reads as an empty or establishing opening — the winners open with the action already under "
          "way and everyone in place; a model spends the head of a clip arriving (festival study §3)")
    # sound: kept by default since 2.49 (editing-and-audio.md §7d) — so it is directed, never left to the model
    aud = bl.get("AUDIO", "")
    audio_on = _truthy(fm.get("generate_audio")) if fm.get("generate_audio") is not None else True
    has_speech = bool(SCENE_SPEECH_RE.search(bl.get("SPEECH", "")) or SCENE_SPEECH_RE.search(aud))
    if has_speech:
        extra["has_speech"] = True
        if not VOICE_LINE_RE.search(bl.get("SPEECH", "") + "\n" + aud):
            W("lines are spoken and no `VOICE:` line fixes the voice — write the voice once in the cast sheet and paste "
              "it word for word into every clip, with the scene's emotion on its own line (prompting-craft.md §9.4)")
    if audio_on and aud:
        if not NO_MUSIC_RE.search(aud):
            W("[AUDIO] never says 'no music' — the model scores the clip on its own; music is chosen by the owner and "
              "laid in the edit (editing-and-audio.md §7d)")
        if not AMBIENCE_RE.search(aud):
            W("[AUDIO] names no ambience — say what the place sounds like (and what it must not sound like), then the "
              "effects; a clip whose air changes at every cut is the cheap-AI tell (editing-and-audio.md §7d–§7e)")
    if audio_on and not has_speech:
        body_for_mouth = "\n".join(bl.get(k, "") for k in ("PERFORMANCE", "ACTION TIMING", "SHOTS", "FIRST FRAME"))
        hits = mouth_open_hits(body_for_mouth)
        if hits:
            W(f"mouth-opening words with sound on and no lines ({', '.join(sorted(set(h.lower() for h in hits))[:4])}) — "
              f"the model reads an open mouth as speech and talks; keep expressions closed-mouthed (shot-handoff.md §1.3)")
    if not str(fm.get("resolution") or "").strip():
        F("`resolution:` missing — 720p is the video floor since 2.49 (one upscale on the final), 1080p preferred for "
          "wide plates and faces (ai-generation.md, the quality floor)")


def lint(path: str, job_root: str | None = None) -> dict:
    text = read(path)
    fm, body = split_front(text)
    fails, warns = [], []
    F = lambda s: fails.append(s)
    W = lambda s: warns.append(s)
    # (v2.49.0) a `form: scene` shot is assembled from the project DNA and its scene file before anything is checked,
    # so every rule below reads — and the gate compares — the prompt that will actually be sent
    _scene_extra = {}
    if (fm.get("form") or "").strip().lower() == "scene":
        fm, body, _scene_extra, _sp = assemble_scene(path, fm, body, job_root)
        for _p in _sp:
            F(_p)
    bl = blocks_of(body)
    # ⚡ THE EVALUATION TIER (house decision 2026-10-25, "Adopt, ship-refusal enforced"). In a job
    # whose checkpoint says `Tier: evaluation` the 1080p floor is a WARN, not a FAIL, on roster models
    # only — because nothing that job makes can ship (job_tier.py: export_qc refuses it, gate.py
    # refuses `lock` and `export`). Everywhere else the floor is exactly what it was.
    _jr = job_root or _job_root_of(path)
    evaluation = _JT.tier(_JT.job_root(_jr) or _jr) == "evaluation"
    if fm.get("generated_from"):
        _fam = os.path.join(os.path.dirname(os.path.abspath(path)), fm["generated_from"])
        if not os.path.isfile(_fam):
            F(f"generated from {fm['generated_from']}, which is gone — a member without its family is "
              f"an unlinted template instance")
        elif fm.get("family_sha") and sha256_file(_fam) != fm["family_sha"]:
            F(f"{fm['generated_from']} changed after this member was written — run prompt_lint.py on the "
              f"family again (it rewrites every member)")
    kind = (fm.get("kind") or "").lower()
    shot = fm.get("shot") or ""
    if not shot:
        F("frontmatter `shot:` missing (S3, S0B …)")
    elif not SHOT_RE.match(shot):
        F(f"`shot: {shot}` — a shot id is letters, digits, - and _ only (gate.py approve frame:<SHOT> "
          f"uses the same rule)")
    if kind == "genjutsu":
        return lint_genjutsu(path, fm, body, fails, warns, _jr, evaluation)
    if kind not in ("frame", "clip", "edit"):
        F("frontmatter `kind:` must be frame, clip, edit or genjutsu (prompting-craft.md §1 — the two prompt paths; "
          "§11g — the image edit; ai-generation.md — the Genjutsu spec)")
        return _result(path, fm, body, fails, warns, None)
    if kind == "frame" and str(fm.get("edit_of") or "").strip():
        F("`kind: frame` with `edit_of:` — an image edit is `kind: edit`: [SOURCE] what the picture is, [KEEP] the "
          "explicit list of what survives, [CHANGE] one concept, [LIGHT MATCH], [REFERENCES] when refs exist, "
          "[OUTPUT] (prompting-craft.md §11g; `prompt_lint.py --template edit`)")
    form = (fm.get("form") or "").strip().lower()
    multishot = form == "multishot"
    scene = form == "scene"
    if form and not (multishot or scene):
        F(f"`form: {form}` — the forms are `scene` (the default for Seedance 2.5 / Cinema Studio clips, "
          f"prompting-craft.md §12) and `multishot` (references/multishot.md); leave it out for a frame-led "
          f"single-action i2v clip")
    if (multishot or scene) and kind != "clip":
        F(f"`form: {form}` is a clip form — a frame is one picture")
    # (v2.49.0) the project switch `frame-led` takes a job back to the approved-start-frame route
    _frame_led = _SW.on(_JT.job_root(_jr) or _jr, "frame-led") if kind == "clip" else None
    if scene and _frame_led:
        F(f"`form: scene` in a job that turned on `frame-led` ({_frame_led}) — every clip here starts from an "
          f"approved frame: drop `form: scene` and write the i2v blocks (prompting-craft.md §1)")
    if kind == "clip" and not form and not _frame_led and (fm.get("model") or "") in SCENE_MODELS \
            and not fm.get("start_frame") and str(fm.get("mode") or "") not in ("video_edit", "video_extension"):
        W(f"{fm.get('model')} clip without `form:` and without a start frame — since 2.49 a Seedance clip is "
          f"written as `form: scene` (references + the block template, prompting-craft.md §12); the i2v form "
          f"needs an approved start frame")
    if not fm.get("model"):
        F("frontmatter `model:` missing — the model is cast in the file, never at call time")
    if not fm.get("aspect"):
        F("frontmatter `aspect:` missing (from the job's delivery preset)")
    txt = prompt_text(body)
    if not txt:
        F("empty prompt body")
    n_chars = len(txt)
    # ⛔ The band is a FRAME rule. A clip prompt carries motion only — the approved frame already
    # settled subject, environment, lighting and style — so a clip that reaches frame length is
    # re-describing the picture, which §11 item 1 forbids and CLIP_FORBIDDEN already refuses.
    # Applying the frame floor to clips would push a writer to pad exactly what the fork exists to
    # keep out. [ASSUMED · house, 2026-09-07 — the operator's measurement was on picture-carrying
    # prompts; if it was taken on clips too, this split is the thing to correct.]
    band_applies = (kind == "frame")
    # ⚡ the model's own ceiling (v2.45 — prompt_limit(); prompting-craft.md §11g)
    lim = prompt_limit(fm.get("model") or "")
    over = ceiling_over(txt or "", lim)
    if scene:
        # (v2.49.0) the winners' length, not the frame band: the look, the place and the blocking live here
        if over and not lim["house"]:
            F(f"scene prompt: {over} — {ceiling_name(lim)} (prompting-craft.md §11g)")
        elif n_chars > SCENE_HOUSE_MAX:
            F(f"scene prompt is {n_chars:,} chars > {SCENE_HOUSE_MAX:,} — past anything measured, and the MCP's own "
              f"ceiling is unverified; cut what a reference sheet already carries (prompting-craft.md §12)")
        elif txt and n_chars < SCENE_THIN:
            W(f"scene prompt is {n_chars:,} chars, under {SCENE_THIN:,} — the festival winners' prompts ran a median "
              f"of about 6,400 (2,700–16,300). With no start frame the prompt carries the look, the place and the "
              f"blocking; what it leaves out the model invents, differently each take (prompting-craft.md §12)")
    elif multishot:
        if over and not lim["house"] and lim["max"] < MAX_PROMPT_MULTISHOT:
            F(f"multi-shot prompt: {over} — {ceiling_name(lim)} (prompting-craft.md §11g)")
        elif n_chars > MAX_PROMPT_MULTISHOT:
            F(f"multi-shot prompt is {n_chars} chars > {MAX_PROMPT_MULTISHOT} — the ceiling Higgsfield's "
              f"own Ad Multiplier workflow validates a Seedance 2.5 prompt against (multishot.md §9)")
        elif n_chars > MAX_PROMPT:
            W(f"multi-shot prompt is {n_chars} chars — past the measured single-clip band; multi-shot "
              f"length is unmeasured here. Cut what the references already carry")
        if lim.get("shot_max"):
            _sts = stages_of(bl.get("STAGES", ""))
            if lim.get("max_shots") and len(_sts) > int(lim["max_shots"]):
                F(f"{len(_sts)} stages — {lim['model']} takes at most {lim['max_shots']} shots in one multi-shot "
                  f"prompt [{lim['source']}]")
            for _st in _sts:
                _sl = len(normalize_prompt(_st["shot"] + " " + _st["body"]))
                if _sl > int(lim["shot_max"]):
                    F(f"Stage {_st['n']} is {_sl} chars — {lim['model']} takes at most {lim['shot_max']} per shot "
                      f"[{lim['source']}]")
    elif over and lim["house"]:
        F(f"prompt is {over} — {ceiling_name(lim)}; that is past the top of the measured band "
          f"({BAND_LO}–{BAND_HI}) by more than 20%, and nobody has measured out here (prompting-craft.md §2.2, §11g)")
    elif over:
        F(f"prompt is {over} — {ceiling_name(lim)} (prompting-craft.md §11g)")
    elif n_chars > HOUSE_CEILING:
        W(f"prompt is {n_chars} chars — past the measured band ({BAND_LO}–{BAND_HI}) and the house {HOUSE_CEILING}: "
          f"inside {lim['model']}'s own ceiling ({lim['max']:,}{', mixed English/non-English rule' if lim['mixed'] else ''}), "
          f"but unmeasured territory here. Not wrong; cut what a reference already carries (prompting-craft.md §2.2, §11g)")
    elif band_applies and n_chars > BAND_HI:
        W(f"prompt is {n_chars} chars, above the measured band {BAND_LO}–{BAND_HI} "
          f"[PRIMARY · own testing · 2026-09-07]. Not wrong — unmeasured. If it is over because one "
          f"block is doing too much, the block budget below says which")
    elif band_applies and n_chars < THIN_PROMPT:
        W(f"prompt is {n_chars} chars, well under the measured band {BAND_LO}–{BAND_HI} "
          f"[PRIMARY · own testing · 2026-09-07] — where errors are low AND the detail is enough "
          f"for accurate generation. ⛔ Everything you leave out, the model fills in, and it fills "
          f"it in differently every take. Thin is not safe, it is unspecified")
    if kind == "edit" and txt:
        if n_chars < EDIT_FLOOR_FAIL:
            F(f"edit prompt is {n_chars} chars < {EDIT_FLOOR_FAIL} [ASSUMED · house 2026-10-29] — an edit that short "
              f"cannot name what it keeps, so the model re-draws what it was not told to protect (prompting-craft.md §11g)")
        elif n_chars < EDIT_FLOOR_WARN:
            W(f"edit prompt is {n_chars} chars < {EDIT_FLOOR_WARN} [ASSUMED · house 2026-10-29] — the published edits "
              f"that held ran 1,179–1,684; name more of what must survive (prompting-craft.md §11g)")
    _cjk = len(CJK_RE.findall(txt or ""))
    if lim.get("warn_cjk_over") and _cjk > int(lim["warn_cjk_over"]):
        W(f"{_cjk} CJK characters — {lim['model']}'s vendor recommends at most {lim['warn_cjk_over']} [{lim['source']}]")
    if lim.get("warn_words_over") and len((txt or "").split()) > int(lim["warn_words_over"]):
        W(f"{len((txt or '').split())} words — {lim['model']}'s vendor recommends at most {lim['warn_words_over']} "
          f"[{lim['source']}]")
    _nonascii = sum(1 for ch in (txt or "") if ord(ch) >= 128)
    if lim.get("warn_nonascii_over") and n_chars > int(lim["warn_nonascii_over"]) and _nonascii > n_chars / 2:
        W(f"a mostly non-English prompt of {n_chars} chars on {lim['model']} — one relay measured an 8,192-token cap past "
          f"which the whole prompt is ignored silently [SECONDARY · {lim['source']}]")
    if kind == "frame" and fm.get("shot"):
        _sib = os.path.join(os.path.dirname(os.path.abspath(path)), f"{fm.get('shot')}.clip.prompt.md")
        if os.path.isfile(_sib):
            _cfm, _cbody = split_front(read(_sib))
            _cmo = blocks_of(_cbody).get("MOTION", "")
            _cl = "\n".join(ln for ln in _cmo.splitlines() if not re.match(r"(?i)^\s*INTENT:", ln))
            if AGENT_RE.search(re.sub(r"(?i)\bcamera\b[^.;\n]*", " ", _cl)) and \
                    str(_cfm.get("type") or "").lower() != "dialogue":
                caught = str(fm.get("caught") or "").strip()
                if not caught:
                    W("no `caught:` — the clip has a person acting, so this frame is caught at the anticipation "
                      "peak the clip completes (\"wrist cocked, the jar tipped 20° over the bin\"), never at rest; "
                      "a still at rest makes the model invent the energy from zero (motion-craft.md §6c)")
                    _sj = bl.get("SUBJECT", "")
                    if REST_RE.search(_sj):
                        W(f"[SUBJECT] reads as a rest pose ({REST_RE.search(_sj).group(0)!r}) for an action shot — "
                          f"catch it mid-move instead (motion-craft.md §6c)")
                if not str(fm.get("travel") or "").strip():
                    W("no `travel:` — the direction the action goes (\"down-left into the bin, toward the lens\"); "
                      "compose the frame with room on that side and avoid a flat move across it (motion-craft.md §6c)")
    # --- density: the thing that actually degrades output ----------------------------------------
    _refs_for_density = fm.get("refs") if isinstance(fm.get("refs"), list) else []
    dens = density_report(bl, _refs_for_density)
    for bname, stat in sorted(dens["per_block"].items()):
        budget = BLOCK_BUDGET.get(bname)
        if budget and stat["words"] > budget:
            W(f"[{bname}] is {stat['words']} words against a {budget}-word budget "
              f"({stat['demands']} demand(s)) — length is fine, a block doing several jobs is not. "
              f"Split what belongs in another block, or move a noun into a reference (§6b)")
    if dens["per_100_words"] > DENSITY_PER_100_WARN:
        W(f"{dens['per_100_words']} demands per 100 words (> {DENSITY_PER_100_WARN}) — "
          f"{dens['demands']} demands in {dens['words']} words, after crediting "
          f"{dens['references_credited']} sourced reference(s). This is a LIST, not a description: "
          f"every model measured degrades as density rises and it is STRUCTURAL, so no rewrite "
          f"recovers it — only fewer simultaneous demands (T2I-CoreBench, prompting-craft.md "
          f"§2.2). Sourcing one more reference removes a demand; rewording removes none")

    lead = bl.get("_lead", "")
    opening = [lead] + [bl.get(k, "").split("\n", 1)[0] for k in ("SUBJECT", "MOTION")]
    if any(COMMAND_RE.search(x) for x in opening if x):
        F("command/conversational phrasing — a prompt is a specification, not a request (§2.5)")
    positive = "\n".join(v for k, v in bl.items() if k != "SUPPRESS")
    # --- is the writing FINISHED? ---------------------------------------------------------------
    # A multishot [REFERENCES] block groups its bindings under the vendor's own group labels
    # ([Characters] [Props] [Scenes] [Motion and Audio], plus this skill's [Frames]) — written text,
    # not a choice left open. Only THOSE labels, only at the start of a line, are exempt.
    for m in PLACEHOLDER_RE.finditer(GROUP_LABEL_RE.sub("", positive) if multishot else positive):
        F(f"unresolved placeholder {m.group(0)!r} — the model renders what is written, brackets "
          f"included. Resolve every choice BEFORE the prompt is final (§2.5)")
        break
    for m in ALTERNATIVE_RE.finditer(positive):
        F(f"an unresolved alternative ({m.group(0)!r}) — a final prompt states one resolved shot, "
          f"never a branch. The decision is yours to make here, not the model's to make for you")
        break
    for m in LEAKED_ID_RE.finditer(positive):
        F(f"a raw id or URL is inside the prompt text ({m.group(0)[:40]!r}) — references are "
          f"attached as media, not described. Whatever is in the prompt, the model tries to draw")
        break
    # --- a state change inside one clip needs an ASSET, not more sentences -----------------------
    _sc = STATE_CHANGE_RE.search(positive)
    _bc = BECOMES_RE.search(positive)
    if _sc and _bc:
        _post = [r for r in (fm.get("refs") or [])
                 if isinstance(r, dict) and str(r.get("state") or "").strip().lower()
                 in ("after", "post", "changed", "b")]
        if not _post:
            F(f"the prompt changes a state mid-clip ({_bc.group(0)!r}) and then defends it with "
              f"words ({_sc.group(0)!r}) — a model has no state register, so nothing holds it and "
              f"the change reverts between frames (character-and-props.md §8.4). The fix is an "
              f"ASSET: author the AFTER state as its own reference and declare it "
              f"`state: after`, or split the clip at the change. More sentences raise nothing "
              f"(prompting-craft.md §11d)")
    for m in COMPARATIVE_ONLY_RE.finditer(positive):
        F(f"{m.group(0)!r} describes by comparison — the model cannot see what it is meant to "
          f"differ from. Name the visible trait itself (hair length, texture and shape; the "
          f"garment; the colour), positively")
        break
    for w in QUALITY_FAIL:
        if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z])", positive, re.I):
            F(f"quality word {w!r} — vendors name it as degrading output; write the physical detail instead (§2.1)")
    for w in QUALITY_WARN:
        if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", positive, re.I):
            W(f"{w!r} reads as a quality word — if it is a colour or a product fact keep it; if it is "
              f"praise, replace it with the physical detail (§2.1)")
            break
    m = NAME_INVOKE_RE.search(positive)
    if m:
        F(f"style-by-name {m.group(0)!r} — no vendor recommends it; decompose the look into lens/light/palette "
          f"(style-transfer.md, prompting-craft.md §2.3)")
    m = HEDGE_RE.search(positive)
    if m:
        F(f"temporal hedge {m.group(0)!r} — mid-action verbs: 'running', not 'begins to run' (§2.5)")
    # ⛔ "watermark" (Scenario E10) and filler (§2.1) — v2.45
    m = WATERMARK_RE.search(positive)
    if m:
        F(f"the word {m.group(0)!r} is in the prompt — a request carrying it was refused as watermark removal and "
          f"STILL CHARGED (Scenario skills, error E10). Never write it; 'no text, no logos' covers what it meant "
          f"(prompting-craft.md §11g)")
    _fill = [x.group(0).lower() for x in FILLER_RE.finditer(positive)]
    if _fill:
        _nw = max(1, len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", positive)))
        _share = len(_fill) / _nw
        _msg = (f"filler word(s) {', '.join(sorted(set(_fill)))} — {len(_fill)} of {_nw} words "
                f"({100 * _share:.1f} %): praise carries no decision a model can act on; write the lens, the light, "
                f"the material instead (prompting-craft.md §2.1, §11g)")
        if _share > FILLER_FAIL_SHARE:
            F(_msg + f" — past {100 * FILLER_FAIL_SHARE:.0f} % the prompt is mostly praise")
        else:
            W(_msg)
    # (v2.70.0, Wave 5 A3) a defect NAMED in a positive block can prime it: the wanted state belongs there, the noun
    # in [SUPPRESS] (a model with a negative field) or [CONSTRAINTS] at the end (a model with none). WARN, never FAIL
    for k, v in bl.items():
        if k in ("SUPPRESS", "CONSTRAINTS", "_lead"):
            continue
        dm = DEFECT_NOUN_RE.search(v)
        if dm:
            W(f"[{k}] names a defect {dm.group(0)!r} — describe the state you want there; the noun goes in [SUPPRESS] "
              f"(a model with a negative field) or [CONSTRAINTS] at the end (one without), "
              f"ai-generation.md guardrails (v2.70.0)")
            break
    # (v2.70.0, Wave 5 A8) the dialogue form the model documents: a WARN only where the contract marks it documented
    _ss = call_contract(fm.get("model") or "").get("speech_syntax") or {}
    if kind == "clip" and bl.get("SPEECH") and _ss.get("status") == "documented" and _ss.get("pattern"):
        _off = [l_.strip() for l_ in bl["SPEECH"].splitlines() if l_.strip() and not re.search(_ss["pattern"], l_)]
        if _off:
            W(f"[SPEECH] line {_off[0][:60]!r} is not in {fm.get('model')}'s documented dialogue form — "
              f"{_ss.get('form')} ({_ss.get('source')})")
    for k, v in bl.items():
        if k in ("SUPPRESS", "_lead", "CHARACTER") or \
                (multishot and k in ("REFERENCES", "CONSISTENCY", "WHERE", "SOUND")) or \
                (kind == "edit" and k in EDIT_GRAMMAR_BLOCKS):
            continue                     # in a multi-shot, "use only …, never …" IS the binding grammar; in an
            #                              edit, "keep … — not its background" is
        v = NO_MUSIC_RE.sub(" ", v)      # "no music" is the instruction a sounding clip needs (Scenario P6)
        if k in ("CAMERA", "OPTICS"):
            v = CAMERA_NEG_RE.sub(" ", v)  # "Slow push. No pan, no tilt." is the explicit one-move form (§2.4)
        for mm in NEG_SENTENCE_RE.finditer(v):
            W(f"[{k}] carries a prohibition {mm.group(0)!r} — move the object to [{noun_home(fm.get('model') or '')['block']}] as a noun, "
              f"or restate positively (§2.6, §11 items 2 and 9)")
            break
    cam = bl.get("CAMERA", "")
    if cam and kind == "clip":
        # ⛔ A MOVE THAT IS FORBIDDEN IS NOT A MOVE THAT IS REQUESTED. "Slow push. No pan, no tilt."
        # counted three moves and FAILed a prompt whose whole point was that there is exactly one —
        # so the rule punished the writer for being explicit, which is the opposite of what §2.4
        # wants. Strip the negated tail before classifying, and warn only if nothing is left.
        # (Same mention-vs-use class as claims_lint.py's compliance-note defect, found the same day.)
        cam_positive = re.sub(r"(?i)\b(?:no|not|never|without|avoid|zero)\b[^.;\n]*", " ", cam)
        # A dolly zoom is ONE named move that happens to contain two words this table knows. Take it
        # out before classifying, so it is refused for the right reason instead of miscounted.
        dz = bool(DOLLY_ZOOM_RE.search(cam_positive))
        if dz:
            F("[CAMERA] asks for a dolly zoom — ⛔ not obtainable. It is a simultaneous position "
              "change and FOCAL-LENGTH change, and no 2026 video model exposes a focal-length "
              "channel, so there is nothing to counter-rotate against the dolly: you get a push "
              "with a wobble and you pay full price for it. Buy the meaning instead — the "
              "background relationship changing under a still subject — with two frames and a cut, "
              "or a scale change between interpolation endpoints "
              "(cinematography-craft.md §3.8; motion-design.md §2.1)")
            cam_positive = DOLLY_ZOOM_RE.sub(" ", cam_positive)
        found = {c for c, pats in CAMERA_CLASSES.items()
                 if any(re.search(p, cam_positive, re.I) for p in pats)}
        if any(re.search(p, cam_positive, re.I) for p in CAMERA_TEXTURE["handheld"]):
            W("[CAMERA] asks for handheld — what a model returns is a GIMBAL: the path of handheld "
              "with none of the presence, because presence is involuntary micro-correction and the "
              "model has no body to correct (cinematography-craft.md §3.4). If the shot needs a "
              "person holding the camera, supply it — motion transfer from a real handheld clip "
              "(motion-design.md §2.2) — or add the jitter in post. Do not expect it from the word")
        moves = found - {"static"}
        if "static" in found and moves:
            F(f"[CAMERA] is both static and moving ({', '.join(sorted(found))}) — one camera behaviour "
              f"per clip (§2.4; realism-qa.md V8)")
        elif len(moves) > 1:
            F(f"[CAMERA] names {len(moves)} moves ({', '.join(sorted(moves))}) — one primary camera "
              f"instruction per shot (§2.4)")
    sup = bl.get("SUPPRESS", "")
    if sup:
        # ⚡ the negative cap is the model's too (v2.45): Kling's legacy field takes 2,500, Wan 2.x truncates at 500,
        # and a model with no negative field never receives the list at all
        _ncap = lim["negative_max"] or MAX_SUPPRESS
        if len(sup) > _ncap:
            F(f"[SUPPRESS] is {len(sup)} chars > {_ncap} (" +
              (f"{lim['model']}'s negative cap [{lim['source']}]" if lim["negative_max"] else
               "the house cap: Wan 2.x truncates a negative at 500") + ", §5.1, §11g)")
        if lim["negative"] == "none":
            W(f"[SUPPRESS] on {lim['model'] or 'this model'}: it has NO negative field [{lim['source']}] — the list is "
              f"DROPPED, never sent: preflight leaves it out and the gate refuses a negative_prompt for it. Write what "
              f"IS there in the blocks, and move the nouns to [CONSTRAINTS], the prompt's last block (§5.1, §11g; "
              f"ai-generation.md guardrails, v2.71.0)")
        # ⛔ "watermark" in the noun list. The positive text FAILS above; here the word reaches a vendor only as a
        # negative_prompt, and gate.py refuses any call whose negative_prompt (or Kling argument) carries it — so the
        # word cannot leave the machine either way, and a WARN keeps every existing job's list lintable while it is
        # cleaned out (WATERMARK_SUPPRESS_FAILS flips it; prompting-craft.md §11g).
        _wm = WATERMARK_RE.search(sup)
        if _wm:
            _wmsg = (f"{_wm.group(0)!r} in [SUPPRESS] — " +
                     (f"dropped on {lim['model']} and never sent" if lim["negative"] == "none" else
                      "the gate refuses to send it as negative_prompt") +
                     ": a request carrying the word was refused as watermark removal and still charged (Scenario E10). "
                     "Take it out; 'text, logo' says the same (§11g)")
            (F if WATERMARK_SUPPRESS_FAILS else W)(_wmsg)
        items = [i.strip() for i in re.split(r"[,\n;]", sup) if i.strip()]
        for it in items:
            if re.match(r"^(no|not|never|avoid|without)\b", it, re.I) or len(it.split()) > 6:
                F(f"[SUPPRESS] item {it!r} is a sentence — a noun list of things to suppress, never "
                  f"'no X' (§2.6). Anatomy stays POSITIVE in the prompt, never negated (§5.2)")
                break
    # (v2.71.0, Wave 5 A3) [CONSTRAINTS]: the nouns' home on a model with NO negative field. It is sent INSIDE the
    # prompt, so it is the last sent block, a noun list, and never used where a negative field exists. WARN only.
    con = bl.get("CONSTRAINTS", "")
    if con:
        _sent = [k for k in bl if k not in ("SUPPRESS", "_lead")]
        if _sent and _sent[-1] != "CONSTRAINTS":
            W(f"[CONSTRAINTS] is not the prompt's last block (it is followed by [{_sent[-1]}]) — it goes at the end, "
              f"after the description (ai-generation.md guardrails, v2.71.0)")
        if lim["negative"] == "field":
            W(f"[CONSTRAINTS] on {lim['model'] or 'this model'}: it has a negative field [{lim['source']}] — move the "
              f"nouns to [SUPPRESS], which is sent as negative_prompt, not inside the prompt (v2.71.0)")
        _anat = CON_ANATOMY_RE.search(con)
        if _anat:
            W(f"[CONSTRAINTS] names anatomy ({_anat.group(0)!r}) — it is sent inside the prompt, and anatomy is never "
              f"named there (§5.2): describe the hands, face or body positively, and keep anatomy nouns for [SUPPRESS] "
              f"on a model with a negative field (ai-generation.md guardrails, v2.71.0)")
        for it in [i.strip() for i in re.split(r"[,\n;]", con) if i.strip()]:
            if re.match(r"^(no|not|never|avoid|without|don'?t|do not)\b", it, re.I) or len(it.split()) > 6:
                W(f"[CONSTRAINTS] item {it!r} is a sentence — a comma-separated noun list, never 'no X' (§2.6, v2.71.0)")
                break
    # an edit's [OUTPUT] bans text ("no text or logos other than the label's own words") — a ban, not a request
    # (v2.71.0) a [CONSTRAINTS] noun list names text and logos to keep OUT: never read as a request for them
    _txt_scope = "\n".join(v for k, v in bl.items() if k not in ("SUPPRESS", "OUTPUT", "CONSTRAINTS")) if kind == "edit" else \
        "\n".join(v for k, v in bl.items() if k not in ("SUPPRESS", "CONSTRAINTS"))
    _readable = TEXT_RENDER_RE.search(_txt_scope)
    _wants_text = _readable or (WRITING_VERB_RE.search(_txt_scope) and QUOTED_RE.search(_txt_scope))
    if _wants_text:
        if BRAND_MARK_RE.search(_txt_scope):
            W("prompt asks for a logo / brand mark — the model never renders a mark reliably; "
              "composite the real asset onto the start frame (SKILL.md on-screen text; "
              "ai-generation.md guardrails)")
        else:
            # ⛔ DIEGETIC TEXT IS DIFFERENT FROM A BRAND MARK, and the blanket refusal was hiding
            # that. Handwriting, a note, a scoreboard CAN render — on two conditions, both observed
            # as a fixed defect: the words are given VERBATIM (a vague "she writes something" comes
            # back as scribbles that read as slop on any real look), and the shot HOLDS long enough
            # for them to resolve (~2s) [SECONDARY · course notes].
            if _readable and not QUOTED_RE.search(positive):
                F("the prompt renders text but never says WHAT it says — an unquoted 'writes "
                  "something' comes back as scribble that reads as slop. Put the exact words in "
                  "quotes, line by line")
            _dur = fm.get("duration")
            try:
                _dur = float(_dur)
            except (TypeError, ValueError):
                _dur = None
            if _dur is not None and _dur < 2:
                F(f"the prompt renders readable text in a {_dur:g}s clip — hold it ~2s or the "
                  f"letters never resolve. Either lengthen the clip or carry the text on the "
                  f"start frame instead")

    # --- a withheld outcome has to be made mechanically necessary ---------------------------------
    _wh = WITHHELD_RE.search(positive)
    if _wh and not MECHANISM_RE.search(positive):
        W(f"the shot turns on something NOT happening ({_wh.group(0)!r}) and gives no mechanism — "
          f"generators are obliging, so a reach for a prize tends to be granted. Make the failure "
          f"necessary: a distance, a speed, a margin ('a dive covers two metres, the case lies "
          f"eight out'; 'the wall moves faster than he flies'). Write the causality, not just the "
          f"event (script-craft.md §6b)")

    # --- a whip pan is ONE move: it cannot change shot size ---------------------------------------
    if WHIP_RE.search(positive):
        _sizes = {_SIZE_CANON.get(m.group(1).lower().replace("close up", "close-up"), m.group(1).upper())
                  for m in SHOT_SIZE_RE.finditer(positive)}
        if len(_sizes) > 1:
            F(f"a whip pan that starts on {' and lands on '.join(sorted(_sizes))} is not a whip "
              f"pan — one continuous move cannot change frame size, so it reads as a cut hiding "
              f"inside a pan. Open and close on the SAME size (shot-handoff.md §7b)")

    # --- an ECU on a body part is an anatomy reference, not a mood ---------------------------------
    _cam = (bl.get("CAMERA") or "") + " " + (bl.get("_lead") or "")
    if re.search(r"\b(ECU|XCU|extreme close|CU\b|close[- ]?up)\b", _cam, re.I) \
            and BODY_ECU_RE.search(positive) and AFFECT_ONLY_RE.search(positive) \
            and not ANATOMY_RE.search(positive):
        W("a close-up on a body part described by AFFECT ('nervous', 'tense') and no anatomy — that "
          "returns smooth waxy CG skin. Name the structures the light has to land on: veins, "
          "tendons, knuckle creases, pores, a hangnail, uneven nails "
          "(character-and-props.md §8.3b)")

    # --- the reference plan: what each reference carries, and that it EXISTS and is cleared -------
    refs = fm.get("refs") if isinstance(fm.get("refs"), list) else []
    base_job = job_root or _job_root_of(path)
    seen_attrs, slots = {}, {"image": 0, "video": 0, "audio": 0}
    for i, r in enumerate(refs, 1):
        rid = f"refs[{i}]"
        role = (r.get("role") or "image").lower()
        what = (r.get("what") or "").strip().lower()
        if canonical_role(role) in FRAME_ROLES:
            F(f"{rid}: role {role!r} pins a FRAME, and a frame is not a reference — declare it with "
              f"`start_frame:` / `end_frame:` and approve it (`gate.py approve frame:<SHOT>` / "
              f"`endframe:<SHOT>`). A frame passed as a ref would reach the model unapproved")
            continue
        klass = ("video" if role in VIDEO_ROLES else "audio" if role in AUDIO_ROLES
                 else "image" if role in IMAGE_ROLES else None)
        if klass is None:
            F(f"{rid}: role {role!r} is not an image/video/audio role — the model's References panel "
              f"names the roles it takes (prompting-craft.md §6b)")
            continue
        if fm.get("kind") == "clip" and fm.get("model"):
            _takes = media_roles(fm.get("model"))
            if _takes and canonical_role(role) not in _takes:
                F(f"{rid}: {fm.get('model')} does not take {canonical_role(role)!r} — it accepts "
                  f"{', '.join(sorted(_takes))} (assets/higgsfield-rates.json → call_contract). "
                  f"Kling takes a start and an end frame and NOTHING else")
                continue
        slots[klass] += 1
        if not what:
            F(f"{rid}: no `what:` — every reference declares the ONE attribute it carries "
              f"(character/wardrobe/prop/environment/light/palette/motion/style/voice). A reference "
              f"with no declared job is decoration (refinement-loop.md §1)")
        elif what not in REF_ATTRS:
            W(f"{rid}: `what: {what}` is not one of {', '.join(REF_ATTRS)} — unknown attributes are "
              f"not checked against the prompt")
        elif what in seen_attrs:
            F(f"{rid} and {seen_attrs[what]} both carry {what!r} — one reference, one attribute; two "
              f"references for one attribute is how a failure stops being attributable "
              f"(refinement-loop.md §1)")
        if what:
            seen_attrs.setdefault(what, rid)
        if what in STUDIO_PLATE_ATTRS and not str(r.get("not") or "").strip():
            W(f"{rid}: carries {what!r} but declares no `not:` — what a reference must NOT bring "
              f"with it. A character sheet arrives with its seamless grey, its panel layout and its "
              f"studio key unless the prompt says otherwise, and that is how a night interior gets "
              f"a grey wall. Write `not: sheet background, panel layout, studio lighting` "
              f"(prompting-craft.md §11d)")
        if not r.get("value") and not r.get("file"):
            if r.get("need"):
                F(f"{rid}: `need: {str(r['need'])[:48]}` is a shopping-list entry, not a reference — "
                  f"the slot is DECLARED but not yet sourced. `refsource.py fill <prompts-dir> "
                  f"--execute` searches Pixabay for it, `refsource.py adopt` writes the chosen file "
                  f"back into this line. The prompt cannot run until it does")
            else:
                F(f"{rid}: needs `file:` (a path under _reference/), `value:` (a media/job id the "
                  f"call will bind), or `need:` (what to go and source — `refsource.py brief` reads "
                  f"it). A reference planned but not sourced is a plan, not a reference")
        fp = r.get("file")
        if fp:
            full = fp if os.path.isabs(fp) else os.path.join(base_job, fp)
            if not os.path.isfile(full):
                F(f"{rid}: file {fp!r} not found — source it BEFORE the prompt is written "
                  f"(`pixacbay_search.py` for stock, or the client's own asset)".replace("pixacbay", "pixabay"))
            else:
                side = None
                cand = _sidecar_of(full)
                if cand:
                    try:
                        side = json.load(open(cand, encoding="utf-8"))
                    except json.JSONDecodeError:
                        F(f"{rid}: provenance sidecar {os.path.basename(cand)} is not valid JSON")
                if side is None:
                    F(f"{rid}: {os.path.basename(fp)} has no provenance sidecar — every reference asset "
                      f"carries one (source, licence, clearance) written at download time "
                      f"(stock-sourcing.md §9). An asset with no provenance cannot be cleared, and an "
                      f"uncleared asset cannot ship")
                else:
                    miss = [k for k in SIDECAR_REQUIRED if k not in side]
                    if miss:
                        F(f"{rid}: sidecar is missing {', '.join(miss)}")
                    # ⛔ The sidecar records a sha256 and NOTHING on the enforced path ever
                    # compared it, while stock-sourcing.md §9 claimed an asset swapped after its
                    # record was written would be caught. It would not: a re-download, a hand-edit
                    # or a "better version" dropped over the file inherited the old clearance
                    # silently, so the cleared apron and the shipped apron need not be the same
                    # picture. `provenance.py audit` did check — and no gate ran it.
                    want = str(side.get("sha256", "") or "")
                    if want:
                        try:
                            got = sha256_file(full)
                        except OSError:
                            got = ""
                        if got and got != want:
                            F(f"{rid}: {os.path.basename(fp)} has CHANGED since its provenance was "
                              f"recorded (sha256 {got[:12]}… vs {want[:12]}…). The clearance on file "
                              f"was answered against a different picture — re-record it with "
                              f"`provenance.py record`, do not carry it over")
                    else:
                        W(f"{rid}: sidecar carries no sha256, so nothing can tell whether this file "
                          f"is still the one that was cleared (stock-sourcing.md §9)")
                    clr = str(side.get("clearance", ""))
                    ref_only = str(r.get("use", "")).lower().startswith("reference")
                    if clr.upper().startswith("NOT CLEARED") and not ref_only:
                        F(f"{rid}: {os.path.basename(fp)} is NOT CLEARED — answer the §5 blockers "
                          f"(recognisable face · trademark/logo · distinctive property · "
                          f"transformation) and record the verdict, or mark this reference "
                          f"`use: reference-only` and keep the likeness out of the output "
                          f"(stock-sourcing.md §5)")
                    sidecar_extra_refs = True
    # --- a BLOCKING render as a reference (2026-10-23, references/blocking.md §6–§7) ---------------
    # WARN-first by house decision until the blocking bake-off (lab-00011) measures which routes a
    # model follows. The two FAILs are structural: a blocking that is not a video reference cannot be
    # one, and a manifest that cannot be read cannot be checked by the gate.
    for r in refs:
        if not (isinstance(r, dict) and str(r.get("what") or "").strip().lower() == "blocking"):
            continue
        if canonical_role(str(r.get("role") or "image").lower()) != "video_references":
            F(f"a blocking reference goes in as `video_references` (got {r.get('role')!r}). A model that "
              f"takes none (kling3_0) gets the blocking's first and last frames through the frame gate "
              f"instead (references/blocking.md §5)")
        if not str(r.get("not") or "").strip():
            W("the blocking reference declares no `not:` — write `not: mannequins, flat colours, floor grid, "
              "grey boxes`, or the render's look arrives with its geometry")
        mf = str(r.get("manifest") or "").strip()
        if not mf:
            W("the blocking reference names no `manifest:` — the gate binds the approval to the manifest's "
              "hash, so generate_video will be refused until it names one (references/blocking.md §7)")
            continue
        mp = mf if os.path.isabs(mf) else os.path.join(base_job, mf)
        try:
            man = json.load(open(mp, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            F(f"blocking manifest {mf!r} is not readable ({e.__class__.__name__}) — build it with "
              f"`blocking.py build`")
            continue
        d, md = _num(fm.get("duration")), _num(man.get("duration"))
        if d is not None and md is not None and abs(d - md) > 0.05:
            W(f"duration {d:g} s ≠ the blocking's {md:g} s — every timed beat sits on the blocking's clock")
        if "LEGEND" in bl:
            said = bl.get("LEGEND", "").lower()
            missing = [c for c in (man.get("legend") or {}) if not re.search(r"\b" + re.escape(c.lower()) + r"\b", said)]
            if missing:
                W(f"[LEGEND] never names {', '.join(missing)} — the render shows those colours, so the model "
                  f"has to be told what they are")
    if any(isinstance(r, dict) and str(r.get("what") or "").strip().lower() == "blocking" for r in refs):
        for b in ("LEGEND", "PRECEDENCE"):
            if b not in bl:
                W(f"[{b}] missing on a blocked clip — `blocking.py prompt` computes it (references/blocking.md "
                  f"§6). WARN until the blocking bake-off (lab-00011)")
    _caps = slot_caps(fm.get("model") or "")
    for klass, n in slots.items():
        if n > _caps[klass]:
            W(f"{n} {klass} reference(s) — {fm.get('model')}'s cap is {_caps[klass]} "
              f"(call_contract → ref_limits, else the house cap; the model's References panel is the "
              f"authority; over the cap they are silently dropped, prompting-craft.md §6b)")
    # ⛔ the rule the whole plan exists for: do not re-describe what a reference already carries.
    # The [CHARACTER] block is the ONE documented exception — ai-generation.md Step 3 requires it
    # pasted verbatim into every prompt as belt-and-braces on identity, and prompting-craft.md §11
    # item 5 keeps it a fixed string. Everything else competes with the pixels.
    DESCRIBE_BLOCKS = ("_lead", "SUBJECT", "ENVIRONMENT", "LIGHTING", "STYLE", "SETTING",
                       "LOCATION", "COLORS", "LIGHTING/MOOD", "START FRAME")
    describing = "\n".join(v for k, v in bl.items() if k in DESCRIBE_BLOCKS)
    for what, rid in seen_attrs.items():
        hits = [w for w in REF_ATTRS.get(what, [])
                if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", describing, re.I)]
        if hits:
            F(f"{rid} carries {what!r}, and the prompt re-describes it ({', '.join(hits[:3])}) — "
              f"reference the nouns, prompt the verbs (prompting-craft.md §6b). Words that describe "
              f"what a reference supplies do not add information, they compete with its pixels")

    sidecar_extra = dict(_scene_extra)
    if kind == "clip" and scene:
        scene_checks(fm, bl, positive, F, W, sidecar_extra, _jr)
    if kind == "clip":
        for b in ([] if scene else CLIP_FORBIDDEN):
            if b in bl:
                F(f"[{b}] in an i2v clip prompt — the approved frame already settled it; a second "
                  f"description competes with the picture (prompting-craft.md §1, §11 item 1). It "
                  f"belongs in the FRAME prompt")
        if not scene and (re.match(r"^\s*(cinematic|photorealistic|documentary)", lead, re.I)
                          or re.search(r"^\s*STYLE\s*:", body, re.M)):
            F("t2v preamble / STYLE: line in a clip prompt — the frame carries the style (§1)")
        for b in ([] if (multishot or scene) else CLIP_REQUIRED):
            if b not in bl:
                F(f"[{b}] missing (ai-generation.md Step 2, the i2v set)")
        mo = bl.get("MOTION", "")
        for k in ([] if (multishot or scene) else ("START", "MID", "END")):
            if not re.search(rf"^\s*{k}\s*:", mo, re.M):
                F(f"[MOTION] has no {k}: line — the END is the aftermath the clip settles into, not where "
                  f"it happens to stop (shot-handoff.md §3–§4)")
        # ⛔ A [MOTION] block whose only verbs are CAMERA verbs is a filter over a photograph
        # (motion-design.md §1) — and it is the exact shape of "short and static", the one
        # combination no era of film ever produced (motion-craft.md §3: modern shot lengths came
        # with MORE motion inside them, r = -.46 coupling, Cutting et al. 2011). WARN, not FAIL: a
        # held product shot with a deliberate locked-off camera is legitimate, and a checker that
        # manufactures findings is how people learn to skip checkers.
        mo_body = re.sub(r"^\s*(START|MID|END)\s*:", " ", mo, flags=re.M | re.I)
        if mo_body.strip() and not SUBJECT_MOTION_RE.search(mo_body):
            W("[MOTION] moves the camera and nothing else — that is a filter over a photograph "
              "(motion-design.md §1), and at these shot lengths it is the whole of 'looks AI' "
              "(motion-craft.md §3). Give it something to move: a hand entering, a prop set down, "
              "a head turning, steam, a second body crossing behind")
        # The settle belongs in END: specifically — shot-handoff.md §3-§4 already says the END is
        # "the aftermath the clip settles into, not where it happens to stop", so scope the check
        # there rather than anywhere in the block.
        end_line = re.search(r"^\s*END\s*:\s*(.+)$", mo, re.M | re.I)
        if end_line and not SETTLE_RE.search(end_line.group(1)):
            W("[MOTION] END: names no settle — measured here, three clips out of three peaked in "
              "their final second and ended mid-motion: the model blocks the anticipation and the "
              "action and never the landing (timing-and-performance.md §5, motion-craft.md §1). "
              "Either write the settle into END:, or cut out of the peak deliberately and check "
              "the shot with `clip_qa.py --landing`")
        # ⛔ SELECTION PRESSURE. The frame gate generates TWO candidates and a human names one
        # media id; every stage above it kills options on purpose (5 concepts, ≥2 killed). The clip
        # stage — the expensive one, the one that IS the film — is single-take by default, so after
        # the frame gate nothing in this pipeline ever expresses a preference again: every verdict
        # downstream is a fault check. "Cut on emotion works BECAUSE gold takes are rare"
        # (editing-storytelling.md) — gold takes are rare in a PILE, and there is no pile.
        # Warn, not fail: a second take costs credits and the operator's cost rule is that cost is
        # never a lever, so this is a decision to take deliberately rather than a rule.
        ctype = (fm.get("type") or "").lower()
        if ctype == "dialogue":
            try:
                nvar = int(fm.get("variants") or 1)
            except (TypeError, ValueError):
                nvar = 1
            if nvar < 2:
                W("dialogue clip with `variants: 1` — the lines that carry the film are the only "
                  "shots in this pipeline generated once. The frame gate proves the pattern (two "
                  "candidates, a human names one); the selects pass has nothing to select between "
                  "unless you make two here. `qa_log.py --gate selects --verdict SELECT|BACKUP` is "
                  "where the choice gets recorded")
        if multishot:
            if ctype != "sequence":
                F("a multi-shot clip is `type: sequence` (references/multishot.md §9)")
        elif ctype not in ("dialogue", "reaction", "broll", "establishing", "insert"):
            F("frontmatter `type:` must be dialogue | reaction | broll | establishing | insert"
              + (" (`sequence` is the multi-shot form's type: add `form: multishot`)" if ctype == "sequence" else ""))
        if ctype in ("dialogue", "reaction"):
            perf = bl.get("PERFORMANCE", "")
            if not perf:
                F("[PERFORMANCE] missing — every dialogue/reaction clip carries a performance card "
                  "(direction.md §1): STATE as a transition, one BEAT, the FACE, the GAZE")
            else:
                for k in PERF_KEYS:
                    if not re.search(rf"\b{k}\s*:", perf):
                        F(f"[PERFORMANCE] has no {k}: (direction.md §1)")
                st = re.search(r"STATE\s*:\s*([^\n]+)", perf)
                if st and "→" not in st.group(1) and "->" not in st.group(1):
                    W("[PERFORMANCE] STATE is not a transition (`skeptical → curious`) — a held state "
                      "reads as a mask (emotional-journey.md §4)")
                if st and any(w in st.group(1).lower() for w in NEGATIVE_STATES):
                    W("[PERFORMANCE] STATE names a peak negative — the model returns a vacant face; put the "
                      "negative in the circumstance and the cut (emotional-journey.md §4.5)")
                # card v2 — each a WARN: a question for the director, pinned both ways in the selftest
                if ctype == "reaction" and not re.search(r"\bSTIMULUS\s*:", perf):
                    W("[PERFORMANCE] a reaction clip with no STIMULUS: — a reaction without its cause "
                      "reads as random. Write what they react to and when, or 'none — she starts it' "
                      "(acting-for-the-model.md §7; sequence-grammar.md §4.1)")
                _gz = re.search(r"GAZE\s*:\s*([^\n]+)", perf)
                _gz = _gz.group(1) if _gz else ""
                if VAGUE_GAZE_RE.search(_gz) and not re.search(r"\bTARGET\s*:", perf):
                    W(f"[PERFORMANCE] GAZE points nowhere ({VAGUE_GAZE_RE.search(_gz).group(0)!r}) and "
                      f"there is no TARGET: — a gaze with no target drifts, and drift is what 'vacant' "
                      f"looks like. Name who or what the performance is aimed at, and where "
                      f"(acting-for-the-model.md §7)")
                _bt = re.search(r"BEAT\s*:\s*([^\n]+)", perf)
                if _bt and len(re.findall(r"\bthen\b", _bt.group(1), re.I)) > 1:
                    W("[PERFORMANCE] BEAT carries two changes (two 'then's) — two events in one clip "
                      "reads as twitching. One change, in the second half; a second turn is a second "
                      "clip (direction.md §1)")
                _sizes = {_SIZE_CANON.get(x.lower(), x.upper())
                          for x in SHOT_SIZE_RE.findall(bl.get("CAMERA", ""))}
                if _sizes & WIDE_SIZES and not re.search(r"\bBODY\s*:", perf):
                    W(f"[PERFORMANCE] a {'/'.join(sorted(_sizes & WIDE_SIZES))} with no BODY: — at that "
                      f"size a face is read slowly and the body carries the feeling. Write one bundle "
                      f"in plain words: 'weight sinks, head drops, arms fold in' "
                      f"(acting-for-the-model.md §3–§4)")
                if DIRECT_ADDRESS_RE.search(_gz) and OFF_EYE_RE.search(bl.get("CAMERA", "")):
                    W(f"[PERFORMANCE] the gaze is on the lens and [CAMERA] is "
                      f"{OFF_EYE_RE.search(bl.get('CAMERA', '')).group(0)!r} — a face addressing the "
                      f"viewer from below was trusted less (eye level 5.03, from below 4.27; from above "
                      f"4.57, not significant — one study, sequence-grammar.md §3.3). Keep direct "
                      f"address at eye height, level, unless the angle is the point")
        _perf = bl.get("PERFORMANCE") or ""
        if _perf and OVERDRIVE_RE.search(_perf):
            W(f"[PERFORMANCE] {OVERDRIVE_RE.search(_perf).group(0)!r} is an intensity superlative — "
              f"'the model may overreact to strong emotional cues' (Seedance 2.5 guide), and real "
              f"screen actors mostly play partial expressions. Say what moves and what stays still; "
              f"'amazed', not 'extremely shocked' (acting-for-the-model.md §5)")
        if _perf and AFFECT_STATE_RE.search(_perf) and not PERF_MECHANISM_RE.search(_perf):
            _w = AFFECT_STATE_RE.search(_perf).group(0)
            W(f"[PERFORMANCE] names an emotion ({_w!r}) and no mechanism — an emotion is unactable "
              f"by a person and unrenderable by a model; both can only play a MECHANISM. Name the "
              f"muscle, the physical act, or the word the delivery breaks on: 'the pitch drops on "
              f"\"missed\", nostrils flare, eyes flick down' (script-craft.md §6b)")
        if ctype == "dialogue":
            line = fm.get("line") or ""
            if not line:
                F("dialogue clip has no `line:` — the spoken words are a locked script line (one line = one clip)")
            else:
                dur = _num(fm.get("duration"))
                need = len(line.split()) / WORDS_PER_SEC
                if dur and need > dur + 0.5:
                    F(f"the line needs ~{need:.1f}s of speech but the clip is {dur:g}s — duration is the "
                      f"real timing control (prompting-craft.md §9.1); split the line or lengthen the clip")
                # ⛔ FITTING IS NOT THE SAME AS BREATHING. This check used to ask only whether the
                # line fit, so a 6s clip carrying 5.8s of speech passed — which is exactly the
                # "lands in one breath" failure: no room before the line for the thing to land, none
                # after for it to register. An actor invents that pause; a model renders only what
                # is written, so the AIR has to be planned (script-craft.md §6b).
                elif dur and (dur - need) < AIR_SECONDS:
                    W(f"the line needs ~{need:.1f}s and the clip is {dur:g}s — only "
                      f"{dur - need:.1f}s of air. A clip packed wall-to-wall with speech has nowhere "
                      f"to react: no beat before the line lands, none after it registers. Budget "
                      f"~{AIR_SECONDS:g}s+ (script-craft.md §6b). ⚠️ Ignore deliberately for a fast "
                      f"UGC hook, where wall-to-wall is the form")
            if not fm.get("vo") and "SPEECH" not in bl:
                W("dialogue clip has neither `vo:` (Path A, audio-driven) nor a [SPEECH] block (Path B, "
                  "native audio) — route by language and stakes (ai-generation.md Step 4)")
        if ctype in ("broll", "establishing", "insert") and not fm.get("function"):
            F("B-roll/insert has no `function:` — every insert declares the job it does in the cut "
              "(shot-handoff.md: the required FUNCTION)")
        # --- THE SHOT EVENT CARD, enforced (direction.md §2b) ---------------------------------
        pay = str(fm.get("payload") or "").strip()
        if not pay:
            F("clip has no `payload:` — one sentence naming what the viewer knows at the END that "
              "they did not know at the START. ⛔ This is F11 asked on the PLAN instead of after "
              "the clip is paid for. A shot whose payload cannot be written is a shot to redesign, "
              "not to re-prompt (direction.md §2b)")
        elif len(pay) < 20:
            F(f"`payload:` is {len(pay)} chars — too short to be an answer. Name the CHANGE in the "
              f"viewer's knowledge, not the shot's subject (direction.md §2b)")
        elif fm.get("function") and flat_txt(pay) == flat_txt(str(fm.get("function"))):
            W("`payload:` restates `function:` — the job an insert does in the CUT is not the same "
              "as what the viewer LEARNS inside it. One of the two is unanswered (direction.md §2b)")
        # the event card's optional lines (direction.md §2b): an obstacle on a proof shot is the director's call
        if str(fm.get("obstacle") or "").strip() and \
                FAMILY_PROOF_RE.search(" ".join(str(fm.get(k) or "") for k in ("function", "payload"))):
            W("`obstacle:` on a shot that proves a claim — an imperfection there is the script's and the "
              "director's decision, per shot (2026-10-26: \"Depends on the script and director's "
              "decision\"); confirm it does not undercut the proof (direction.md §2b)")
        # ⚡ MOTION PLANNED FOR THE CUT (2026-10-26: "We can also plan motion in one shot, to
        # naturally enhance the transition"). `exit:` / `enter:` are the screen direction of what moves
        # in this clip's last / first moments; `join:` is how it hands off to the next shot
        # (shot-handoff.md §4b). motion_qa.py measures all three before picture lock.
        _join = str(fm.get("join") or "").strip().lower()
        _exit, _enter = str(fm.get("exit") or "").strip(), str(fm.get("enter") or "").strip()
        if _join and HANDOFF_MOTION_RE.search(_join) and not _exit:
            W(f"`join: {_join}` carries motion into the next shot and this clip has no `exit:` — name the "
              f"screen direction of what is still moving in the last frames (\"right, the hand leaving frame\"), "
              f"and write it into the MOTION block's END (shot-handoff.md §4b)")
        for _k, _v in (("exit", _exit), ("enter", _enter)):
            if _v and not HANDOFF_DIR_RE.search(_v):
                W(f"`{_k}: {_v[:40]}` names no screen direction (left, right, up, down, toward or away from "
                  f"the lens) — motion_qa.py cannot check a hand-off it cannot read (shot-handoff.md §4b)")
        if _exit and HANDOFF_MOTION_RE.search(_join) and bl.get("MOTION") and \
                re.search(r"(?i)\b(settles?|comes? to (?:a )?rest|rests?|stops?|holds? still|freezes|lands?|"
                          r"(?:sets?|puts?|placed?) (?:\w+ )?down)\b",
                          (re.search(r"(?mi)^\s*END:\s*(.+)$", bl.get("MOTION", "")) or [None, ""])[1]):
            W("`exit:` hands motion to the next shot and the MOTION END line settles — a motion hand-off cuts "
              "while the action is still running; let END keep moving, and the edit cuts before any settle "
              "(shot-handoff.md §4b)")
        # (3.2.0) the sound that leads the eye into the next shot: `prelap: 0.5s, knock, side=right`
        if str(fm.get("prelap") or "").strip():
            _pl, _why = parse_prelap(fm.get("prelap"))
            if _why:
                W(f"`prelap: {str(fm.get('prelap'))[:40]}` — {_why} (sfx_conform.py joins; editing-and-audio.md §7f)")
        # named objects motion_qa.py follows (2026-10-26: track a specific object, boxed on frame one)
        for _spec in [t for t in re.split(r"\s*;\s*", str(fm.get("track") or "")) if t.strip()]:
            _tm = TRACK_RE.match(_spec)
            if not _tm or not all(0 <= float(v) <= 1 for v in _tm.groups()[1:]) or \
                    float(_tm.group(4)) == 0 or float(_tm.group(5)) == 0:
                W(f"`track: {_spec[:50]}` — write name=x,y,w,h, the object's box on the start frame as fractions of "
                  f"the frame from the top-left (\"jar=0.42,0.55,0.12,0.20\"); motion_qa.py follows it (shot-handoff.md §4b)")
        # the sound the shot makes, for sfx_conform.py: `sfx: count=3, surface=wet, space=kitchen` (2026-10-26)
        _sfx = str(fm.get("sfx") or "").strip()
        if _sfx:
            _SFXV = {"surface": {"hard", "soft", "wet"}, "distance": {"close", "medium", "far"}, "pan": {"off", "follow"},
                     "space": {"dry", "exterior", "interior", "kitchen", "bathroom", "hall", "car", "street", "forest",
                               "studio"}}
            for _kv in [x for x in re.split(r"\s*[,;]\s*", _sfx) if x]:
                _k, _, _v = (y.strip().lower() for y in _kv.partition("="))
                if _k not in ("count", "material", "surface", "space", "distance", "hero", "pan") or not _v:
                    W(f"`sfx: {_kv}` — keys are count, material, surface, space, distance, hero, pan, as key=value "
                      f"(sfx_conform.py)")
                elif _k == "count" and not _v.isdigit():
                    W(f"`sfx: count={_v}` — a number: how many sound events the shot really has")
                elif _k in _SFXV and _v not in _SFXV[_k]:
                    W(f"`sfx: {_k}={_v}` — one of {', '.join(sorted(_SFXV[_k]))}")
        # ⚡ THE RAMP (house rule 2026-10-26, C4: "Keep burst speed-up + cap"). A speed ramp is planned on the
        # clip, not found in the edit: `ramp: kind=slow, speed=40, trigger=2.1, reveal=<what the slow-motion
        # shows>, sfx=<the cue>`. A burst may speed the action from onset to contact to 115–150 %; a slow-down
        # must name what it reveals (move-catalogue.md §24) and passes motion_qa.py warp; never on a speaking
        # or reacting person — slow motion reads as contrived on an endorser (Yin et al. 2021) and makes an
        # act look more intentional (Caruso et al. 2016). The per-video cap is checked at lock (motion_qa.py).
        _ramp = str(fm.get("ramp") or "").strip()
        # (v2.48.0, project switch speed-conform) `ramp: conform=<speed>%` or `conform=<src fps>/<timeline fps>` (a
        # whole-clip constant conform), or `ramp: ease=<min speed>%` on a shot with `join: whip` (85 or more): with the
        # job's switch on, no ramp — no cap, no `reveal=`, no cue — and checked here as one of the two cases
        # (motion_qa.speed_case). With the switch off the keys below refuse `conform` and `ease`, exactly as before.
        _swc = None
        if _ramp and re.search(r"(?i)(?:^|[,;])\s*(?:conform|ease)\s*=", _ramp):
            _swc = _SW.on(_JT.job_root(_jr) or _jr, "speed-conform")
        if _swc:
            import motion_qa as _MQ
            _ck = {}
            for _kv in [x for x in re.split(r"\s*[,;]\s*", _ramp) if x]:
                _k, _, _v = (y.strip() for y in _kv.partition("="))
                _ck[_k.lower()] = _v
            _c = _MQ.speed_case(_ck, fm)
            _bad = [k for k in _ck if k not in ("conform", "ease", "kind", "speed", "trigger", "sfx", "in", "out",
                                                "cut_in", "cut_out")]
            _trig = str(_ck.get("trigger", "0"))
            if _c["problem"]:
                F(f"`ramp:` {_c['problem']}. Project switch `speed-conform` lifts the ramp rules only for a "
                  f"whole-clip conform under 100 % or an ease of {_MQ.EASE_MIN:g} % or more inside a planned whip")
            elif _bad:
                F(f"`ramp:` with `{_c['case']}=` takes trigger, sfx and cut_in/cut_out (in/out) once cut — not "
                  f"{', '.join(_bad)}")
            elif not re.match(r"^\s*\d+(?:\.\d+)?\s*s?\s*$", _trig):
                F(f"`ramp: trigger={_trig}` — a trigger is a second in the clip")
            elif _c["case"] == "ease" and (ctype in ("dialogue", "reaction")
                                           or str(fm.get("grade") or "").lower() == "talking_head"):
                F("`ramp: ease=` on a speaking or reacting person — an ease changes the speed inside the clip and "
                  "breaks lip-sync")
            else:
                _lf = _SW.lifted("speed-conform", _swc)
                W(f"`ramp: {_ramp}` is " + ("a whole-clip conform" if _c["case"] == "conform" else
                                            "a shallow ease inside its whip")
                  + f" at {_c['speed']:g} %, not a ramp: the ramp rules (house rule C4: the cap, `reveal=`) are {_lf}; "
                    f"the frame-repeat floor still holds (motion_qa.py check)")
                sidecar_extra.setdefault("lifted", {})["speed-conform"] = _lf
        if _ramp and not _swc:
            _rk = {}
            for _kv in [x for x in re.split(r"\s*[,;]\s*", _ramp) if x]:
                _k, _, _v = (y.strip() for y in _kv.partition("="))
                _rk[_k.lower()] = _v
            _bad = [k for k in _rk if k not in ("kind", "speed", "trigger", "reveal", "sfx", "in", "out", "cut_in", "cut_out")]
            if _bad:
                F(f"`ramp:` keys are kind, speed, trigger, reveal, sfx (and in/out, cut_in/cut_out once cut) — not {', '.join(_bad)}")
            _kind = (_rk.get("kind") or "").lower()
            try:
                _spd = float(str(_rk.get("speed", "")).rstrip("%"))
            except ValueError:
                _spd = None
            if _kind not in ("slow", "burst"):
                F("`ramp: kind=` is slow (a slow-down on the hero moment) or burst (the action sped from onset to contact)")
            elif _spd is None:
                F("`ramp: speed=` is a percentage: 20–90 for a slow-down, 115–150 for a burst (house rule C4)")
            elif _kind == "burst" and not (115 <= _spd <= 150):
                F(f"`ramp: speed={_spd:g}` — a burst runs 115–150 % (house rule C4); above that the interpolation shows")
            elif _kind == "slow" and not (20 <= _spd <= 90):
                F(f"`ramp: speed={_spd:g}` — a slow-down runs 20–90 % of real speed")
            if _kind == "slow" and not (_rk.get("reveal") or "").strip():
                F("`ramp: kind=slow` with no `reveal=` — a ramp is a shot that only exists at that speed: name what "
                  "the slow-motion lets the viewer look at, or don't ramp (move-catalogue.md §24)")
            if not (_rk.get("sfx") or "").strip():
                F("`ramp:` with no `sfx=` cue — the ramp is heard as much as seen: the original audio is muted under it "
                  "and a cue carries it (editing-and-audio.md, the ramp)")
            try:
                float(_rk.get("trigger", ""))
            except ValueError:
                # (v2.48.0, project switch music-led) a burst cued to a sound in the song, `trigger=song@<s>`, instead
                # of onset to contact; it is still a ramp (motion_qa.py check counts it). Switch off: refused as before.
                import motion_qa as _MQ
                _swm = (_SW.on(_JT.job_root(_jr) or _jr, "music-led")
                        if _kind == "burst" and _MQ.SONG_CUE_RE.match(str(_rk.get("trigger", ""))) else None)
                if _swm:
                    _lf = _SW.lifted("music-led", _swm)
                    W(f"`ramp: trigger={_rk.get('trigger')}` cues the burst to the song, not onset to contact — {_lf}; "
                      f"it still counts against the ramp cap (motion_qa.py check)")
                    sidecar_extra.setdefault("lifted", {})["music-led"] = _lf
                else:
                    F("`ramp: trigger=` is the second in the clip where the ramp turns — the frame it is built around")
            if ctype in ("dialogue", "reaction") or str(fm.get("grade") or "").lower() == "talking_head":
                F("`ramp:` on a speaking or reacting person — never: slow motion reads as contrived on an endorser "
                  "(Yin et al. 2021) and breaks lip-sync")
        # ⚡ THE AERIAL DECLARATION (2026-10-26: aerial, FPV, insect and planet shots; the council's A1/A4,
        # rulings C1, C4, C6). `aerial: move=…, function=…, subject=…, final=…, place=real|invented` — the shot
        # names its job, its subject and its last frame; the words keep off what makes AI aerials fail; a real
        # place is pinned by a real photograph or a declared `chain:` from one. The rules are aerial_qa.py's.
        if fm.get("aerial") or fm.get("chain"):
            import aerial_qa as _AQ
            _AQ.lint_aerial(fm, txt, job_root or _job_root_of(path), ctype, F, W)
        # the grade profile, for grade_luts.py plan (2026-10-26): which of the template's nodes the clip gets
        _grade = str(fm.get("grade") or "").strip().lower()
        if _grade and _grade not in ("talking_head", "broll", "product", "anatomy", "clean"):
            W(f"`grade: {_grade}` — one of talking_head, broll, product, anatomy, clean (grade_luts.py: product, "
              f"anatomy and clean take no look and no texture)")
        # ⚡ THE MOVEMENT PERSONA (2026-10-26: "when a person or avatar is used, the skill should build
        # a persona like in UX or marketing, so the animation and prompt guides the output better").
        # A cast person has _reference/PERSONA-<name>.md with one `MOVES LIKE:` line; every clip of that
        # person carries the same line, so the whole batch moves like one person (acting-for-the-model.md §7b).
        _pbase = job_root or _job_root_of(path)
        _pdir = os.path.join(_pbase, "_reference") if _pbase else ""
        _pname = str(fm.get("persona") or "").strip()
        _moves_here = re.search(r"(?mi)^\s*MOVES LIKE:\s*(.+?)\s*$", body)
        _person = AGENT_RE.search(re.sub(r"(?i)\bcamera\b[^.;\n]*", " ", bl.get("MOTION", "") + "\n" +
                                         bl.get("PERFORMANCE", "")))
        if _pname:
            _pf = os.path.join(_pdir, f"PERSONA-{_pname}.md")
            if not os.path.isfile(_pf):
                W(f"`persona: {_pname}` and no _reference/PERSONA-{_pname}.md — build the movement persona first "
                  f"(assets/persona-brief-template.md, How they move)")
            else:
                _ml = re.search(r"(?mi)^\s*(?:[-*]\s*)?\**MOVES LIKE:?\**:?\s*(.+?)\s*$", read(_pf))
                if not _ml:
                    W(f"PERSONA-{_pname}.md has no `MOVES LIKE:` line — the one-line movement baseline every clip "
                      f"of this person carries (acting-for-the-model.md §7b)")
                elif not _moves_here:
                    W(f"no `MOVES LIKE:` line — paste PERSONA-{_pname}.md's into [MOTION] (or [PERFORMANCE]) so this "
                      f"clip moves like the same person as the others: {_ml.group(1)[:90]!r}")
                elif normalize_prompt(_moves_here.group(1)) != normalize_prompt(_ml.group(1)):
                    W(f"`MOVES LIKE:` differs from PERSONA-{_pname}.md — every clip of one person carries the same "
                      f"line; change the persona, not one clip (acting-for-the-model.md §7b)")
        elif _person and _pdir and os.path.isdir(_pdir) and \
                any(f.startswith("PERSONA-") and f.endswith(".md") for f in os.listdir(_pdir)):
            W("a person acts and the clip names no `persona:` — this job has movement personas; say whose this is "
              "(acting-for-the-model.md §7b)")
        mo = bl.get("MOTION", "")
        if mo:
            end = ""
            m_end = re.search(r"(?ms)^\s*END:\s*(.+?)(?=^\s*[A-Z][A-Z ]{2,}:|\Z)", mo)
            if m_end:
                end = m_end.group(1)
            if end and NO_CHANGE_RE.search(end):
                F("[MOTION] END: asserts that nothing changed — that is F11 failing, in the writer's "
                  "own words, before a credit is spent. If the stillness is the point, say what the "
                  "viewer LEARNS from it in `payload:`; otherwise the shot has no event and belongs "
                  "back at the event card (direction.md §2b; cinematography-craft.md §3.3)")
            # strip camera instructions, then ask whether anything in the WORLD did something
            world = re.sub(r"(?i)\bcamera\b[^.;\n]*", " ", mo)
            world = re.sub(rf"(?i)\b(?:{CAMERA_VERBS})\b", " ", world)
            verbs = re.findall(rf"(?i)\b(?:{AMBIENT_VERBS})\b", world)
            # a rough content check: are there verbs that are NOT in the ambient set?
            other = re.sub(rf"(?i)\b(?:{AMBIENT_VERBS})\b", " ", world)
            has_other_action = bool(re.search(r"(?i)\b(?:press\w*|lift\w*|reach\w*|pull\w*|push\w*|"
                                              r"open\w*|clos\w*|pour\w*|set\w*|place\w*|pick\w*|"
                                              r"turn\w+ to|hand\w*|walk\w*|step\w*|sit\w*|stand\w*|"
                                              r"strip\w*|tear\w*|drop\w*|throw\w*|slide\w*|enter\w*|"
                                              r"withdraw\w*|releas\w*|grip\w*|hold\w*|look\w*|glanc\w*|"
                                              r"speak\w*|say\w*|smil\w*|blink\w*|breath\w*|nod\w*)\b",
                                              other))
            if verbs and not has_other_action:
                W("[MOTION] carries only AMBIENT motion (" + ", ".join(sorted(set(v.lower() for v in verbs))[:4]) +
                  ") — drifting, rising, shimmering, settling. Atmosphere is not an event: this reads "
                  "as a still photograph left running, which is what it is. §3.8's five levers start "
                  "with a SUBJECT doing something (direction.md §2b, the ambient-only failure shape)")
            # --- INTENT: a person acting does it for a reason, and the reason sets the manner ---------
            m_int = re.search(r"(?mi)^\s*INTENT:\s*(.+)$", mo)
            intent = (m_int.group(1).strip() if m_int else "") or str(fm.get("intent") or "").strip()
            body_lines = [ln for ln in mo.splitlines() if not re.match(r"(?i)^\s*INTENT:", ln)]
            acts = AGENT_RE.search(re.sub(r"(?i)\bcamera\b[^.;\n]*", " ", "\n".join(body_lines)))
            if acts and ctype != "dialogue":
                if not intent:
                    W("[MOTION] has a person acting and no `INTENT:` line — why they do it, as an attitude, "
                      "and the manner it forces: \"done with sugar: fast, no second thought\". Without a "
                      "motive the model fills in its default: even speed, gentle, centred, presented to the "
                      "lens (motion-craft.md §6b)")
                elif not (TEMPO_RE.search(intent) or FLOAT_RE.search(intent) or TEMPO_RE.search(mo)):
                    W("`INTENT:` says why but not how — add the manner it forces (quick, hard, a beat then a "
                      "burst, careful, heavy), and its one change (motion-craft.md §6b)")
                for ln in body_lines:
                    mm = re.match(r"(?i)^\s*(START|MID|END):\s*(.+)$", ln)
                    if mm and MATERIAL_RE.match(mm.group(2)):
                        W(f"[MOTION] {mm.group(1)}: leads with {MATERIAL_RE.match(mm.group(2)).group(0).strip()!r} — "
                          f"the material is the CONSEQUENCE of the person's force, not the subject. Lead with "
                          f"the hand and its intent, and let the sugar fall in a clause after it (motion-craft.md §6b)")
                w_body = re.sub(rf"(?i)\b(?:{CAMERA_VERBS})\b", " ",
                                re.sub(r"(?i)\bcamera\b[^.;\n]*", " ", "\n".join(body_lines)))
                if FLOAT_RE.search(w_body) and not TEMPO_RE.search(w_body) and not FLOAT_RE.search(intent):
                    W(f"[MOTION] moves only slowly and evenly ({FLOAT_RE.search(w_body).group(0)!r}, no tempo or "
                      f"force word) — the floaty default of generated motion. If slow is the intent, say why in "
                      f"`INTENT:` and give it a stop or a change (motion-craft.md §6b)")
            mth = THROW_RE.search(THROW_IDIOM_RE.sub(" ", mo))
            if mth and not LANDING_RE.search(mo):
                F(f"[MOTION] {mth.group(0)!r} with no landing — a thrown object comes back: on a supplement ad job the model "
                  f"threw the keys out of frame, then put them back on the counter. Describe the release and where it "
                  f"lands (\"fingers open, the keys drop straight down onto the counter below\"), or that it leaves "
                  f"the frame for good (prompting-craft.md §6.4b)")
            for rx, what in AI_TELL_MOTION:
                mt = rx.search(mo)
                if mt:
                    W(f"[MOTION] {what} ({mt.group(0)!r}) — out of the ads lane: models render it as warping and "
                      f"it reads as AI; in a drama it needs the owner's sign-off for this shot (motion-craft.md §7b)")
        # casting against the roster
        ro = roster()
        model = fm.get("model") or ""
        if ro is None:
            F(f"cannot read {os.path.join(ASSETS, 'higgsfield-rates.json')} — the roster and the rates live "
              f"there, and a roster check that cannot run does not pass (it used to, silently)")
            ro = {}
        elif model and model not in ro:
            F(f"model {model!r} is not on the approved roster ({', '.join(ro)}) — a hard lock "
              f"(ai-generation.md, the roster). An off-roster model has no rate on purpose")
        res = (fm.get("resolution") or "").lower()
        if model in ro:
            if not res:
                F(f"`resolution:` missing — {model} rows: {', '.join(ro[model])}")
            elif res not in ro[model] and evaluation and res_px(res) and res_px(res) < 1080:
                W(f"EVALUATION TIER: {res} is under the 1080p floor and {model} has no {res!r} row in the "
                  f"rate table (production rows: {', '.join(ro[model])}). Allowed here only because this "
                  f"job never ships; price it from the UI reading (`Budget:` [measured]) and record the "
                  f"question it answers")
            elif res not in ro[model]:
                F(f"{model} has no {res!r} row — measured rows: {', '.join(ro[model])} (rate_card.py table)")
            else:
                # (v2.49.0, 2026-11-05: "720p finals + upscale") the VIDEO floor is 720p — the 3rd-place festival
                # film generated at 720p and was upscaled once on the final. Frames, sheets and edits keep 1080p. A job
                # that wants the old floor turns on the project switch `floor-1080`.
                _vfloor = 1080 if _SW.on(_JT.job_root(_jr) or _jr, "floor-1080") else VIDEO_FLOOR_PX
                if res_px(res) < _vfloor and evaluation:
                    W(f"EVALUATION TIER: {res} is under the {_vfloor}p video floor — allowed only because this job "
                      f"never ships (job_tier.py)")
                elif res_px(res) < _vfloor:
                    F(f"{res} is under the {_vfloor}p video floor" + (" (project switch `floor-1080`)" if _vfloor == 1080
                      else "") + " — cost never negotiates with the quality floor (ai-generation.md, the quality floor)")
                elif res_px(res) < 1080:
                    W(f"{res} take: allowed since 2.49 — plan ONE upscale on the final after the cut, never per clip; "
                      f"prefer 1080p for wide plates and close faces (ai-generation.md, the quality floor)")
                row = ro[model][res]
                dur = _num(fm.get("duration"))
                if dur is None:
                    F("`duration:` missing (seconds)")
                elif not (row.get("min_s", 0) <= dur <= row.get("max_s", 10 ** 6)):
                    F(f"duration {dur:g}s is outside {model} {res}'s measured range "
                      f"{row.get('min_s')}–{row.get('max_s')}s — never clamped silently (rate_card.py)")
                if dur is not None:
                    cut = _num(fm.get("cut")) if fm.get("cut") is not None else _num(fm.get("cut_max"))
                    lead = LEAD_IN_S if fm.get("start_frame") else LEAD_IN_T2V_S
                    hnd = _num(fm.get("handle"))
                    if hnd is None:
                        hnd = 0.0 if ctype == "dialogue" else HANDLE_S   # dialogue: the handle comes from the join
                    if cut is None:
                        W("`cut:` missing — the seconds the edit holds this shot (the shot list's Dur). Without "
                          "it `duration:` is a default and every clip comes out the same length; the lint "
                          f"derives duration = lead-in {lead:g} + cut + handle {hnd:g} (ai-generation.md, clip length)")
                    else:
                        need = clip_length_need(cut, hnd, lead, row.get("min_s", 0))
                        if dur < lead + cut - 1e-9:
                            F(f"duration {dur:g}s cannot cover lead-in {lead:g}s + {cut:g}s in the cut — generate "
                              f"{need} s (lead-in + cut + handle {hnd:g}s)")
                        elif dur < lead + cut + hnd - 1e-9:
                            W(f"duration {dur:g}s leaves no {hnd:g}s handle past the cut — generate {need} s, or "
                              f"`handle: 0` if both joins are hard cuts")
                        elif dur > need + CLIP_SLACK_S:
                            W(f"duration {dur:g}s is {dur - need:g}s past the {need} s this shot needs (cut {cut:g}s): "
                              f"the model peaks in its last second, so the extra buys a dead front, not more action")
        # ⚡ VIDEO EXTENSION (2026-09-26, the owner approved the patch). Seedance 2.5 `mode: video_extension`
        # extends an EXISTING approved take forward or backward, so the thing it starts from is a
        # video, not a still: the source goes in `refs` as `video_references` and is approved as
        # frame:<SHOT> with that video's job id. `extension_mode` (forward|backward) is REQUIRED by the
        # vendor for this mode and refused everywhere else. No other mode is read from the file.
        gen_mode = str(fm.get("mode") or "").strip()
        is_ext = gen_mode == "video_extension"
        if gen_mode and not is_ext:
            F(f"`mode: {gen_mode}` — the prompt file only declares `mode: video_extension`; every other "
              f"mode is decided by call_shape() from the model's contract")
        if is_ext:
            _mc = call_contract(fm.get("model") or "") or {}
            if "video_extension" not in (_mc.get("modes") or []):
                F(f"{fm.get('model')!r} does not document mode video_extension (call_contract → modes)")
            ext = str(fm.get("extension_mode") or "").strip()
            if ext not in ("forward", "backward"):
                F("`extension_mode:` must be forward or backward for mode video_extension (vendor-required)")
            _vr = [r for r in (fm.get("refs") if isinstance(fm.get("refs"), list) else [])
                   if isinstance(r, dict) and canonical_role(str(r.get("role") or "")) == "video_references"
                   and r.get("value")]
            if len(_vr) != 1:
                F("mode video_extension needs exactly one `refs` entry with role video_references and the "
                  "source take's job id as value — that take is what gets extended")
            if fm.get("start_frame") or fm.get("end_frame"):
                F("mode video_extension starts from the source video — drop start_frame/end_frame")
            sidecar_extra["gen_mode"] = gen_mode
            sidecar_extra["extension_mode"] = ext
        elif fm.get("extension_mode"):
            F("`extension_mode:` is only valid with `mode: video_extension`")
        sf = fm.get("start_frame") or ""
        if not sf:
            if not is_ext and not scene:
                F("`start_frame:` missing — every clip is i2v from an approved still (prompting-craft.md §1); "
                  "point at the file under 02-startframes/" + (" — a Seedance clip may instead be written as "
                  "`form: scene` from approved reference sheets (prompting-craft.md §12)" if not _frame_led else ""))
        else:
            base = job_root or _job_root_of(path)
            sp = sf if os.path.isabs(sf) else os.path.join(base, sf)
            if not os.path.isfile(sp):
                F(f"start_frame {sf!r} not found under the job")
            else:
                sidecar_extra["start_frame_sha"] = sha256_file(sp)
        # END FRAME — optional, and approved exactly like the start frame, because it fixes the
        # picture exactly as much. The guidance ranks a start+end pair as the most reliable control
        # of a move that needs GEOMETRY (motion-design.md §2.1); the 2026-08-29 run adds that FLF
        # gives exactly the move implied by the DIFFERENCE between the two frames, so an end frame
        # that differs from the start only in pose encodes no camera move at all.
        ef = fm.get("end_frame") or ""
        model_c = fm.get("model") or ""
        has_refs = any(isinstance(r, dict) and (r.get("value") or r.get("file")) for r in
                       (fm.get("refs") if isinstance(fm.get("refs"), list) else []))
        if not call_contract(model_c):
            F(f"no call_contract row for {model_c!r} in assets/higgsfield-rates.json — the lint cannot "
              f"say how this model takes a still, so it will not guess. Read models_explore get and add "
              f"the row")
        else:
            shape = call_shape(model_c, has_refs, bool(ef))
            sidecar_extra["call_shape"] = {k: shape[k] for k in ("start_role", "end_role", "mode",
                                                                 "reference_mode")}
            if shape["start_role"] is None:
                F(f"{model_c} cannot take the approved still in this call — it accepts "
                  f"{', '.join(sorted(media_roles(model_c)))}")
            elif shape["reference_mode"] and (sf or not scene):
                W(f"{model_c}: the start frame binds as `image_references` because {shape['why']} "
                  f"— the first frame will be CLOSE, not exact (measured 2026-09-19: 0.97 on minimax_h3 "
                  f"with image + video references; 0.53-0.96 on seedance_2_5). If it must match the "
                  f"approved still exactly, use a model with a true first frame and no references")
            elif not shape["frames_measured"]:
                W(f"{model_c}: first-frame fidelity has not been measured in this pipeline — check the "
                  f"first take's opening frame against the approved still before trusting it "
                  f"(assets/higgsfield-rates.json → call_contract → evidence)")
            aud = shape["audio"]
            if aud.get("default_on") and not aud.get("param") and fm.get("type") == "dialogue":
                W(f"{model_c} generates native audio and has NO off switch — on a dialogue clip it will "
                  f"animate the mouth to speech nobody approved. The gate refuses it until `audio` is "
                  f"approved; either way the track is stripped in the edit")
            if multishot:
                multishot_checks(fm, bl, F, W, tag_map(fm, shape["reference_mode"], shape["start_role"]),
                                 sidecar_extra)
            if ef:
                if shape["end_role"] is None and multishot:
                    F(f"`end_frame:` cannot be sent as a frame on {model_c} in this call ({shape['why'] or 'no end_image'}). "
                      f"In a multi-shot clip, bind the approved end still as a reference instead: "
                      f"`- role: image_references, what: endframe, value: <its approved media id>` and say "
                      f"in [REFERENCES] which @Image it is (multishot.md §3)")
                elif shape["end_role"] is None:
                    F(f"`end_frame:` cannot be sent on {model_c} in this call — "
                      + (f"{shape['why']}, so it has no first frame and no last one either "
                         f"(measured 2026-09-19)" if call_contract(model_c).get("frames") is False else
                         f"frames and references cannot share one call on it (422, measured 2026-09-19 on "
                         f"minimax_h3). Drop the `refs:` or drop the end frame" if shape["reference_mode"]
                         else f"it takes no `end_image`"))
                base = job_root or _job_root_of(path)
                ep = ef if os.path.isabs(ef) else os.path.join(base, ef)
                if not os.path.isfile(ep):
                    F(f"end_frame {ef!r} not found under the job")
                else:
                    sidecar_extra["end_frame_sha"] = sha256_file(ep)
                    if sf and os.path.isfile(sp) and sidecar_extra.get("start_frame_sha") == \
                            sidecar_extra["end_frame_sha"]:
                        F("`end_frame:` is the same file as `start_frame:` — FLF gives exactly the move "
                          "implied by the DIFFERENCE between the frames, so an identical pair encodes a "
                          "still (a studio note of 2026-08-29 [studio history])")
    elif kind == "frame":
        # ⛔ The 1080p floor lived inside the CLIP branch only, so every start frame in every job
        # could be generated at any tier with nothing objecting — on the half of the pipeline that
        # SETS the picture, and which every clip then inherits. SKILL.md non-negotiable 11 says
        # "from the first take"; the code said "from the first clip". Frames carry no rate-card row,
        # so this checks the declared resolution and nothing else.
        fres = (fm.get("resolution") or "").lower()
        if not fres:
            W("`resolution:` missing on a frame — the quality floor is unenforceable without it "
              "and the clip built on this frame inherits whatever came back (SKILL.md §4.11)")
        elif res_px(fres) and res_px(fres) < 1080 and evaluation:
            W(f"EVALUATION TIER: {fres} is under the 1080p floor — allowed only because this job never "
              f"ships (job_tier.py)")
        elif res_px(fres) and res_px(fres) < 1080:
            F(f"{fres} is under the 1080p floor — the frame sets the picture and every clip "
              f"inherits it (ai-generation.md, the quality floor)")
        for b in FRAME_REQUIRED:
            if b not in bl:
                F(f"[{b}] missing — a start frame carries subject · environment · lens · lighting · mood "
                  f"(ai-generation.md Step 1)")
        asp = fm.get("aspect") or ""
        if asp in ("9:16", "4:5") and "SAFE ZONE" not in bl and "safe zone" not in positive.lower():
            F(f"{asp} frame with no safe-zone note — every load-bearing element inside "
              f"y=15-65%, x=11-72% of frame, the MEASURED ad safe box "
              f"(assets/delivery-formats.json `safe_zone_pct`; cinematography-craft.md 5.10)")
        li = bl.get("LIGHTING", "")
        # ⛔ A KELVIN NUMBER IS NOT A SOURCE. The old rule accepted `\d{4}K` as satisfying this
        # check, which let "5200K, moody" pass while naming no object at all — and a Kelvin number
        # is decoration in a prompt anyway (cinematography-craft.md §7.0). What the model can act on
        # is a SOURCE OBJECT (a window, a lamp, the sun) or a whole-light-model token (overcast,
        # golden hour), optionally with a named face pattern.
        if li and not re.search(r"sun|window|overcast|golden hour|tungsten|lamp|bulb|candle|fire|"
                                r"practical|fluorescent|neon|dusk|dawn|noon|shade|moon|screen|"
                                r"streetlight|skylight|doorway|butterfly|loop|rembrandt|split|rim",
                                li, re.I):
            W("[LIGHTING] names no SOURCE — the model can render 'a lamp on the counter, switched on' "
              "or 'overcast'; it cannot render 'moody', and a bare Kelvin number is decoration "
              "(cinematography-craft.md §7.0, §1.5). Name the object, its direction and quality, and "
              "one pattern where a face is in frame (§1.4)")
        if cam and not re.search(r"\d{2,3}\s?mm", cam):
            W("[CAMERA] names no focal length — the lens is a style token the model does respond to "
              "(prompting-craft.md §4.1)")
        subj = bl.get("SUBJECT", "")
        if any(re.search(rf"\b{w}\b", subj, re.I) for w in NEGATIVE_STATES):
            F("[SUBJECT] briefs a negative emotional state — a reference frame at a negative peak comes "
              "back as a vacant mask; cast neutral-positive and put the negative in the structure "
              "(ai-generation.md Step 2 ⛔; emotional-journey.md §4.5)")
        if TWO_SHOT_RE.search(subj):
            W("[SUBJECT] phrases a two-shot as 'X next to Y' — the model may return a triptych; state "
              "'a single continuous photographic frame' up front and restate each wardrobe verbatim "
              "(ai-generation.md guardrail table)")
        fmodel = fm.get("model") or ""
        if fmodel and fmodel in (roster() or {}):
            F(f"`model: {fmodel}` is a VIDEO model — a start frame is authored with the profile's image "
              f"model (ai-generation.md, three model roles)")
        elif fmodel and not any(h in fmodel for h in IMAGE_MODEL_HINT):
            W(f"`model: {fmodel}` is not a known image model id — confirm with models_explore(type: image)")
        gpt26_checks(fm, refs, F, W)
        ftype = (fm.get("type") or "").lower()
        if ftype in ("character", "product") and not refs:
            F(f"a {ftype} frame with no `refs:` — identity and product are locked by a REFERENCE, "
              f"never by text alone (ai-generation.md Step 3; prompting-craft.md §6b). Source the "
              f"reference first, declare what it carries, then write the prompt")
        if ftype == "character" or fm.get("character"):
            if "CHARACTER" not in bl:
                F("character frame with no [CHARACTER] block — the fixed block is pasted verbatim into "
                  "every frame (ai-generation.md Step 3; series-continuity.md §6.2)")
            elif fm.get("character"):
                base = job_root or _job_root_of(path)
                ref = os.path.join(base, "_reference", f"CHARACTER-{fm['character']}.md")
                if os.path.isfile(ref):
                    if normalize_prompt(read(ref)) != normalize_prompt(bl["CHARACTER"]):
                        F(f"[CHARACTER] differs from the locked block {os.path.relpath(ref, base)} — the "
                          f"invariants are frozen; copy it byte-for-byte (series-continuity.md §6.2)")
                    sidecar_extra["character_ref_sha"] = sha256_file(ref)
                else:
                    W(f"no locked character block at _reference/CHARACTER-{fm['character']}.md — the "
                      f"first approved frame should produce one (series-continuity.md)")
    else:  # edit — one concept changed in a picture that exists (v2.45; prompting-craft.md §11g)
        _edit_checks(fm, bl, refs, positive, job_root or _job_root_of(path), evaluation, F, W, sidecar_extra)
    # --- v2.45: what every kind owes -------------------------------------------------------------------------
    # E1 (Scenario): "no logos" / "no text" on a picture with signs or screens — say what each one shows
    if kind in ("frame", "edit"):
        # (v2.71.0) the picture is the description blocks: a [CONSTRAINTS] noun ("modern signage") names what is NOT
        # there; its "text, logo" is the same ban as [SUPPRESS]'s
        _pic = "\n".join(v for k, v in bl.items() if k not in ("SUPPRESS", "CONSTRAINTS"))
        _ban = TEXT_BAN_RE.search(_pic) or any(
            i.strip().lower() in SUP_TEXT_ITEMS
            for i in re.split(r"[,\n;]", bl.get("SUPPRESS", "") + "\n" + bl.get("CONSTRAINTS", "")))
        _undescribed = [mm.group(0) for mm in SIGNAGE_RE.finditer(_pic)
                        if not SIGN_DESCRIBED_BEFORE_RE.search(_pic[max(0, mm.start() - 30):mm.start()])
                        and not SIGN_DESCRIBED_AFTER_RE.search(_pic[mm.end():mm.end() + 70])]
        if _ban and _undescribed:
            W(f"the picture has {', '.join(sorted(set(w.lower() for w in _undescribed))[:4])} and the prompt only bans "
              f"text — models letter signs and screens anyway (Scenario E1). Say what each one shows: 'a blank cream "
              f"enamel sign', 'a chalk menu board too far to read', 'the phone screen dark, the window reflected in it' "
              f"(prompting-craft.md §11g)")
    # E6 / P6 (Scenario): a clip that generates sound says "no music", or the model scores it
    if kind == "clip":
        _aud = call_contract(fm.get("model") or "").get("audio") or {}
        _on_by_file = any(_truthy(fm.get(k_)) for k_ in ("generate_audio", "sound", "audio", "native_audio"))
        _no_switch = bool(_aud.get("default_on")) and not _aud.get("param")
        if (_on_by_file or _no_switch) and not scene and not NO_MUSIC_RE.search(positive) and "SPEECH" not in bl:
            W(f"{fm.get('model') or 'the model'} generates sound on this clip "
              f"({'the file turns it on' if _on_by_file else 'it has no off switch'}) and the prompt never says "
              f"'no music' — a video model adds a score of its own unasked (Scenario P6/E6). Write it into [SOUND]: "
              f"'room tone and the pour only, no music' (prompting-craft.md §11g)")
    # P3 (Scenario): a video reference and image references in one call — which input decides the framing?
    _rr = [canonical_role(str(r.get("role") or "image").lower()) for r in refs if isinstance(r, dict)]
    _start_as_img = kind == "clip" and fm.get("start_frame") and (sidecar_extra.get("call_shape") or {}).get("reference_mode")
    if "video_references" in _rr and ("image_references" in _rr or _start_as_img) and not FRAMING_LINE_RE.search(positive):
        W("the call binds a video reference AND image references, and no line says which input decides the framing — "
          "the inputs fight over it. Name the winner: '@Video 1 sets the camera path and framing; @Image 1 carries "
          "the product's look only' (Scenario P3; prompting-craft.md §11g)")
    # ⚡ THE DETAIL SCORE — the concrete slots the prompt fills (prompting-craft.md §11g)
    if txt and not multishot and not scene:
        _det = detail_report(kind, bl, positive)
        sidecar_extra["detail_score"] = _det["score"]
        sidecar_extra["detail_of"] = _det["of"]
        sidecar_extra["detail_min"] = _det["min"]
        sidecar_extra["detail_missing"] = _det["missing"]
        if _det["score"] < _det["min"]:
            _as_edit = kind == "frame" and EDIT_LANGUAGE_RE.search(positive)
            F(f"detail score {_det['score']}/{_det['of']} < {_det['min']} for a {kind} [ASSUMED · house 2026-10-29] — "
              f"missing: {'; '.join(_det['missing'])}. Every slot left empty, the model fills in its own way, "
              f"differently each take (prompting-craft.md §11g)" +
              (f". ⚡ This reads as an IMAGE EDIT ({_as_edit.group(0)!r}): write it as `kind: edit` with `edit_of:` — "
               f"it is scored on what it keeps and what it changes, not on a frame's lens and light"
               if _as_edit else ""))
    sidecar_extra["prompt_ceiling"] = {"max": lim["max"], "mixed": lim["mixed"], "house": lim["house"],
                                       "from": lim["from"]}
    sidecar_extra["negative_channel"] = lim["negative"]
    if evaluation:
        sidecar_extra["tier"] = "evaluation"
    if fm.get("family"):
        sidecar_extra["family"] = fm.get("family")
        sidecar_extra["cut_max"] = _num(fm.get("cut_max"))
    # ⚡ THE WORLD (2026-10-27, lab-00020; the author: "don't focus on the golf itself, but how the plugin approached
    # the scenario"). An exterior is designed once, in 00-brief/world/<LOC>.world.json, approved by the owner, and every
    # frame and clip of it is held to the card: no uncast mover, no sky, wind or night word that contradicts it, no
    # mover added by an image edit, and the ⚑ warnings (the motion budget, an exterior with no card) answered before
    # spend. The rules are world.py's (references/world-design.md).
    import world as _WD
    # an edit makes a picture: the world reads it as a frame, so "an edit adds a mover" still refuses (jury B6)
    _wl = _WD.lint_prompt(path, fm, bl, txt or "", "frame" if kind == "edit" else kind, job_root or _job_root_of(path),
                          lambda s_: F("[world] " + s_), W, warns)
    if _wl.get("must"):
        sidecar_extra["answered"] = _wl["must"]
    res = _result(path, fm, body, fails, warns, txt, sidecar_extra)
    res["_must"], res["_txt_sha"] = _wl.get("must", []), _wl.get("txt_sha")
    if "detail_score" in sidecar_extra:
        res["detail"] = {k: sidecar_extra[k] for k in ("detail_score", "detail_of", "detail_min", "detail_missing")}
    return res


def _edit_checks(fm: dict, bl: dict, refs: list, positive: str, base: str, evaluation: bool, F, W, extra: dict) -> None:
    """`kind: edit` — the image edit (prompting-craft.md §11g). Sources: scenario-alter-web-addendum §1.1 (page A's
    recipe: one precise change, then the explicit list of what must stay; models protect what is named), §2.2-§3.3
    (the keep list, one named concept with numbered items, reactions, the label lock, the no-OTHER-text close);
    scenario-alter-integration §5 (the target frame, gated per shot); house decision 2026-10-28."""
    src = str(fm.get("edit_of") or "").strip()
    if not src:
        F("`edit_of:` missing — the picture this edit changes, as a path under the job (02-startframes/…, "
          "_reference/plate/…); its hash is recorded so the gate can prove which picture was edited")
    else:
        sp = src if os.path.isabs(src) else os.path.join(base, src)
        if not os.path.isfile(sp):
            F(f"edit_of {src!r} not found under the job — the source picture exists before its edit is written")
        else:
            extra["edit_of_sha"] = sha256_file(sp)
            extra["edit_of"] = src
    if str(fm.get("edit_of_media") or "").strip():
        extra["edit_of_media"] = str(fm["edit_of_media"]).strip()
    else:
        W("no `edit_of_media:` — the media id the call binds as the picture being edited; the gate refuses the call "
          "until the file names it")
    use = str(fm.get("use") or "frame").strip().lower()
    if use not in EDIT_USES:
        F(f"`use: {use}` — an edit's result is a `frame` (it goes to the frame gate like any start frame) or a `target` "
          f"(it becomes a model reference)")
    extra["use"] = use
    if use == "target":
        W("`use: target` — the result becomes a MODEL REFERENCE: an AI-edited target frame of our own footage is allowed "
          "only as a gated per-shot opt-in (2026-10-28). The gate refuses this edit until `gate.py approve "
          f"target:{fm.get('shot') or '<SHOT>'} --by <name> --quote \"…\"`")
        if src:
            sp = src if os.path.isabs(src) else os.path.join(base, src)
            cand = _sidecar_of(sp) if os.path.isfile(sp) else ""
            side = None
            if cand:
                try:
                    side = json.load(open(cand, encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    side = None
            if side and str(side.get("source") or "").strip().lower() == "ai-generated":
                F(f"`use: target` on {os.path.basename(src)}, whose provenance says ai-generated — a target frame is an "
                  f"edit of OUR OWN footage (house decision 2026-10-28), never an edit of a generated picture "
                  f"(character-and-props.md §8.7b)")
            elif side is None and os.path.isfile(sp):
                W(f"`use: target` and {os.path.basename(src)} has no provenance sidecar — record that it is our own "
                  f"footage (`provenance.py record`) before its edit becomes a reference")
    # the result's floor and model are a frame's
    fres = (fm.get("resolution") or "").lower()
    if not fres:
        W("`resolution:` missing on an edit — the quality floor is unenforceable without it (SKILL.md §4.11)")
    elif res_px(fres) and res_px(fres) < 1080:
        (W if evaluation else F)(f"{fres} is under the 1080p floor — an edit makes a picture every clip inherits"
                                 + (" (EVALUATION TIER: allowed, this job never ships)" if evaluation else ""))
    fmodel = fm.get("model") or ""
    if fmodel and fmodel in (roster() or {}):
        F(f"`model: {fmodel}` is a VIDEO model — an image edit runs on an image model (ai-generation.md, three model roles)")
    elif fmodel and not any(h in fmodel for h in IMAGE_MODEL_HINT):
        W(f"`model: {fmodel}` is not a known image model id — confirm with models_explore(type: image)")
    gpt26_checks(fm, refs if isinstance(refs, list) else [], F, W)
    for b in EDIT_REQUIRED:
        if b not in bl:
            F(f"[{b}] missing — an edit carries [SOURCE] [KEEP] [CHANGE] [LIGHT MATCH] [OUTPUT], and [REFERENCES] when "
              f"refs exist (prompting-craft.md §11g)")
    if "SOURCE" in bl and len(bl["SOURCE"].split()) < 8:
        W("[SOURCE] is under 8 words — say what the source picture IS: who or what, where, the light, the framing")
    keep = bl.get("KEEP", "")
    if keep:
        hit = [n for n, rx in KEEP_CATEGORIES.items() if re.search(rx, keep, re.I)]
        if len(hit) < KEEP_MIN:
            miss = [n for n in KEEP_CATEGORIES if n not in hit]
            F(f"[KEEP] names {len(hit)} of the 8 things an edit must protect ({', '.join(hit) or 'none'}) — name at "
              f"least {KEEP_MIN}; models protect what is named, and 'keep everything else' alone protects less "
              f"(scenario-alter-web-addendum §1.1, §3.3). Not named: {', '.join(miss)}")
        extra["keep_named"] = hit
    ch = bl.get("CHANGE", "")
    if ch:
        if ADD_REPLACE_RE.search(ch):
            miss = [n for n, rx in CHANGE_SPECIFICS.items() if not re.search(rx, ch, re.I)]
            if miss:
                F(f"[CHANGE] adds or replaces an object and does not state its {', '.join(miss)} — an object dropped in "
                  f"without a place, a size, a material and contact with the light reads as a sticker "
                  f"(scenario-alter-web-addendum §3.3, the reactions)")
        lines = [ln for ln in ch.splitlines() if ln.strip()]
        loose = [ln for ln in lines[1:] if not re.match(r"^\s*(?:\d+[.)]|[-*•])\s", ln)]
        if len(lines) > 1 and loose:
            W("[CHANGE] runs past its first line without numbering — one concept per edit: name it in the first line, "
              "then its parts as numbered items ('1) … 2) …'); two unrelated changes are two edits "
              "(scenario-alter-web-addendum §3.2)")
        if re.search(r"\b(?:also|additionally|as well as|and then)\b", lines[0] if lines else "", re.I):
            W("[CHANGE] opens on more than one change ('also', 'as well as') — one concept per edit; a second change is "
              "a second edit from the approved first (scenario-alter-web-addendum §3.2)")
    lm = bl.get("LIGHT MATCH", "")
    if lm and not (LIGHT_DIR_RE.search(lm) and LIGHT_SRC_RE.search(lm)):
        W("[LIGHT MATCH] does not name both the light's direction and its colour temperature or source — the change "
          "takes the SOURCE's light, so say which: 'key from the left window, warm morning sun'")
    img_refs = [r for r in refs if isinstance(r, dict)
                and canonical_role(str(r.get("role") or "image").lower()) == "image_references"]
    if img_refs:
        if "REFERENCES" not in bl:
            F(f"{len(img_refs)} image reference(s) and no [REFERENCES] block — each reference gets one line: its job and "
              f"what it must NOT bring ('Image 2 is the product: shape, glass and label only — not its white sweep, not "
              f"its studio reflections') (scenario-give-each-picture-a-job §0, §6c)")
        else:
            rl = [ln for ln in bl["REFERENCES"].splitlines() if ln.strip()]
            if len(rl) < len(img_refs):
                F(f"[REFERENCES] has {len(rl)} line(s) for {len(img_refs)} image reference(s) — one line each, in order")
            for i, ln in enumerate(rl[:len(img_refs)], 1):
                if not re.search(r"\b(?:not|never|nothing)\b", ln, re.I):
                    F(f"[REFERENCES] line {i} gives no 'not' — say what that picture must NOT bring (its background, its "
                      f"light, its own subject); a reference leaks more than its job (Scenario E2)")
                what = str(img_refs[i - 1].get("what") or "").strip().lower()
                if what and what not in ln.lower() and "only" not in ln.lower():
                    W(f"[REFERENCES] line {i} does not name its job ({what!r}) or limit it ('… only')")
    out = bl.get("OUTPUT", "")
    if out:
        if not re.search(r"\b\d{1,2}\s?:\s?\d{1,2}\b|\b\d{3,4}p\b|\b[248]k\b|\b\d{3,4}\s?[x×]\s?\d{3,4}\b", out, re.I):
            F("[OUTPUT] names no aspect or resolution — '9:16, 2k, one photographic frame'")
        if not TEXT_BAN_RE.search(out):
            F("[OUTPUT] does not ban text — 'no text, letters or logos' (or, with a labelled product in frame, 'no text "
              "or logos other than the label's own words \"…\"')")
        elif re.search(r"\blabel\w*\b", keep + "\n" + ch, re.I) and not \
                re.search(r"\bother\b|\bexcept\b|\bbut\b|\bapart from\b", out, re.I):
            W("[OUTPUT] bans ALL text while the picture keeps or adds a label — a total ban contradicts a printed product: "
              "ban only OTHER text and write the label's exact words (scenario-alter-web-addendum §3.1)")
        if re.search(r"\blabel\w*\b", out, re.I) and not QUOTED_RE.search(out + "\n" + ch):
            W("[OUTPUT] lets a label through without its exact words in quotes — name them, spelled as printed")


def _num(v):
    try:
        return float(str(v).rstrip("s")) if v not in (None, "") else None
    except ValueError:
        return None


JOB_MARKERS = ("00-brief", "_reference", "01-script", "02-startframes")


def lint_genjutsu(path: str, fm: dict, body: str, fails: list, warns: list, job_root: str,
                  evaluation: bool = False) -> dict:
    """`kind: genjutsu` (v2.46.1). The spec carries the whole call, because the call carries almost nothing the
    gate could read otherwise: the model, its mode, the resolution, the ONE source video and the reference
    images. [QA] is the measured check the take must pass (never sent); [PROMPT] is optional and sent verbatim.
    The gate matches a generate_video call to this file field by field and needs `genjutsu:<SHOT>` approved."""
    F = lambda x: fails.append(x)
    W = lambda x: warns.append(x)
    shot = fm.get("shot") or "?"
    models = genjutsu_models()
    model = str(fm.get("model") or "").strip()
    row = models.get(model) or {}
    if not models:
        F("assets/higgsfield-rates.json → genjutsu cannot be read — the Genjutsu roster fails closed")
    elif not model:
        F("frontmatter `model:` missing — one of " + ", ".join(sorted(models)))
    elif not row:
        F(f"model {model!r} is not a Genjutsu model ({', '.join(sorted(models))})" +
          (" — it is a clip model: a clip is `kind: clip`" if model in (roster() or {}) else ""))
    if not path.endswith(GENJUTSU_SUFFIX):
        F(f"name the file <SHOT>{GENJUTSU_SUFFIX} (gate.py preflight and approve genjutsu:<SHOT> find it by that name)")
    mode = str(fm.get("mode") or "").strip().lower()
    if mode not in GENJUTSU_MODES:
        F(f"`mode:` must be motion (motion transfer: a driving video's motion onto the reference subjects) or swap "
          f"(object swap: replace an object in the source video) — got {mode or 'nothing'!r}")
    elif row and row.get("mode") != mode:
        F(f"`mode: {mode}` but {model} is {GENJUTSU_MODES.get(row.get('mode'), row.get('mode'))} — the model decides the "
          f"mode; pick the matching one")
    res = str(fm.get("resolution") or "").strip()
    opts = [str(o) for o in (row.get("resolutions") or [])]
    if not res:
        F("`resolution:` missing — Genjutsu has a default the spec never chose; the spec states it and the call sends it "
          "(the video floor is 720p since 2.49, 1080p with `floor-1080`)")
    elif opts and res.lower() not in [o.lower() for o in opts]:
        F(f"resolution {res} is not one {model} offers ({', '.join(opts)})")
    elif res_px(res) < (_gfloor := (1080 if _SW.on(_JT.job_root(job_root) or job_root, "floor-1080") else VIDEO_FLOOR_PX)):
        (W if evaluation else F)(f"resolution {res} is under the {_gfloor}p video floor (ai-generation.md, the quality floor)" +
                                 (" — an evaluation job: WARN only, nothing it makes ships" if evaluation else ""))
    dur = _num(fm.get("duration"))
    lo, hi = row.get("min_s"), row.get("max_s")
    if dur is None:
        F("`duration:` missing — the seconds of the source video the shot uses. Genjutsu takes no duration (the output "
          "follows the source), but the quote and the model's range need it")
    elif lo is not None and hi is not None and not (float(lo) <= dur <= float(hi)):
        F(f"duration {dur:g} s is outside {model}'s {lo}–{hi} s source range (assets/higgsfield-rates.json → genjutsu) — "
          f"trim the source, or use the model that takes it" +
          (" (Lite motion transfer stops at 15 s; full takes 30)" if model.endswith("_flash") and mode == "motion" else ""))
    sv = str(fm.get("source_video") or "").strip()
    if not sv or re.search(r"[<>]|NEEDS INPUT|\bTBD\b|\?\?\?", sv):
        F("`source_video:` — the media id of the ONE " + ("driving video whose motion is copied" if mode == "motion" else
          "source video whose object is replaced") + ": upload it (gated, a confirmed media id), then write the id here")
    sf = str(fm.get("source_file") or "").strip()
    src_sha = None
    if not sf:
        F("`source_file:` missing — the local file behind `source_video:` (its hash is recorded, so the approval binds "
          "the exact video the human looked at)")
    else:
        sp = sf if os.path.isabs(sf) else os.path.join(job_root, sf)
        if not os.path.isfile(sp):
            F(f"source_file {sf} not found under the job")
        else:
            src_sha = sha256_file(sp)
            # ⛔ the spec binds the EXACT video (v2.46.1): its hash is written into the spec, so the approval of the
            # spec covers the video too — a different file under the same name fails this lint, and the gate with it
            dsha = str(fm.get("source_hash") or "").strip().lower()
            if not dsha or re.search(r"[<>]", dsha):
                F(f"`source_hash:` missing — write {src_sha} (the hash of {sf}): the approved spec then binds that "
                  f"exact video, and a different one under the same name is refused")
            elif len(dsha) < 16 or not re.fullmatch(r"[0-9a-f]+", dsha) or not src_sha.startswith(dsha):
                F(f"source_hash {dsha[:16]}… ≠ {sf}'s {src_sha[:16]}… — the video is not the one this spec was written "
                  f"(and approved) for; a different driving/source video needs the spec rewritten and approved again")
            secs = _ffprobe_seconds(sp)
            if secs is not None and dur is not None and abs(secs - dur) > 0.5:
                W(f"{sf} runs {secs:.2f} s by ffprobe and `duration:` says {dur:g} s — the output follows the source; "
                  f"make them agree")
    rights = str(fm.get("rights") or "").strip().lower()
    if rights not in GENJUTSU_RIGHTS:
        F("`rights:` must be client-approved or own — ⛔ every Genjutsu call uploads the source video to Higgsfield, and "
          "only client-approved material goes (ai-generation.md, \"Rights before any of these\"). A scene from a film "
          "is measured locally, never sent")
    refs = fm.get("refs") if isinstance(fm.get("refs"), list) else []
    bound = []
    for i, r in enumerate(refs):
        if not isinstance(r, dict):
            continue
        role = canonical_role(str(r.get("role") or "image_references"))
        v = str(r.get("value") or "").strip()
        if role == "video_references":
            F(f"refs[{i}] is a video — the one video is `source_video:`; a Genjutsu call takes exactly one")
        elif role != "image_references":
            F(f"refs[{i}] has role {r.get('role')!r} — Genjutsu takes image references and one video "
              f"(assets/higgsfield-rates.json → genjutsu.roles)")
        if not v or re.search(r"[<>]", v):
            F(f"refs[{i}] has no media id (`value:`) — the gate binds the reference by its id")
        else:
            bound.append(v)
        if not str(r.get("what") or "").strip():
            W(f"refs[{i}] says no `what:` — name what it carries (the subject, the replacement product)")
    if not bound:
        F("no reference image — " + ("motion transfer needs the subject(s) the motion lands on" if mode != "swap" else
          "object swap needs the replacement object"))
    elif len(bound) > SLOT_CAPS["image"]:
        W(f"{len(bound)} reference images — over the house cap of {SLOT_CAPS['image']}; Genjutsu states no cap")
    if len(set(bound)) != len(bound):
        F("the same media id is listed twice in refs")
    fg = str(fm.get("free_gens") or "").strip().lower()
    if fg not in GENJUTSU_FREE:
        F("`free_gens:` must be prefer (send `use_free_gens: true` while the account has free Genjutsu generations) or no")
    if row.get("tier") == "full" and row.get("lite"):
        lite = models.get(row["lite"]) or {}
        W(f"{model} is Genjutsu full: Lite ({row['lite']}) has {lite.get('free_gens_stated', '?')} free generations "
          f"against full's {row.get('free_gens_stated', '?')} [stated · 2026-11-03] — plan Lite first unless "
          f"Lite already failed this shot, and say why in [QA]")
    var = int(_num(fm.get("variants")) or 1)
    if var > 1:
        W(f"variants: {var} — every Genjutsu take is billed in full (about 6× Kling 4.0 per 5 s [stated · owner, "
          f"2026-11-03]); judge one take before asking for another")
    bl = blocks_of(body)
    extra_blocks = [k for k in bl if k not in GENJUTSU_BLOCKS and k != "_lead"]
    if "SUPPRESS" in extra_blocks:
        F("[SUPPRESS] — Genjutsu has no negative field; a suppress list would be dropped, never sent")
    others = [k for k in extra_blocks if k != "SUPPRESS"]
    if others:
        F(f"blocks {', '.join('[' + k + ']' for k in others)} — a Genjutsu spec has [QA] and an optional [PROMPT] only: "
          f"the picture comes from the source video and the references, not from words")
    if bl.get("_lead", "").strip():
        F("text before the first block — put it in [QA] (never sent) or [PROMPT] (sent)")
    qa = (bl.get("QA") or "").strip()
    if not qa:
        F("[QA] missing — the measured check this take must pass (ai-generation.md, the Genjutsu rows): " +
          ("does the output hold the driving video's camera path and timing? motion_track.py / film_breakdown.py on "
           "source and output, compared per frame; identity against the references at 1080p" if mode != "swap" else
           "label and logo fidelity across the whole clip; untargeted parts of the source untouched"))
    elif mode == "motion" and not re.search(r"motion_track|film_breakdown", qa):
        W("[QA] names no measurement of the motion — motion_track.py / film_breakdown.py on source and output")
    elif mode == "swap" and not re.search(r"label|logo|fidelity|clip_qa|look_qa", qa, re.I):
        W("[QA] names no check of the swapped object — label/logo fidelity across the clip")
    txt = normalize_prompt(bl.get("PROMPT") or "")
    if "PROMPT" in bl and not txt:
        F("[PROMPT] is empty — leave the block out to send no prompt")
    if WATERMARK_RE.search(txt):
        F("the [PROMPT] carries the word 'watermark' — a request carrying it was refused as watermark removal and still "
          "charged (Scenario E10; prompting-craft.md §11g)")
    if len(txt) > MAX_PROMPT:
        F(f"[PROMPT] is {len(txt)} characters — over the house {MAX_PROMPT} (Genjutsu documents no ceiling)")
    if txt:
        W("[PROMPT] present — Genjutsu documents no prompt; the first call shows whether it reads one")
    extra = {"genjutsu_mode": mode, "tier": row.get("tier"), "genjutsu_name": row.get("name"),
             "source_video": sv, "source_file": sf, "source_sha256": src_sha, "rights": rights,
             "free_gens": fg, "free_gens_stated": row.get("free_gens_stated"), "qa": qa, "lite": row.get("lite"),
             "negative_channel": "none", "has_prompt": bool(txt)}
    return _result(path, fm, body, fails, warns, txt, extra)


def _job_root_of(path: str) -> str:
    """01-script/prompts/X.md → the job folder. Recognised by ANY of the pm-workflow.md layout
    folders, not just 00-brief — a job mid-setup may not have every one of them yet, and resolving
    to the wrong root made every `file:` reference read as NOT SOURCED (found in a live run
    2026-09-06)."""
    d = os.path.dirname(os.path.abspath(path))
    for _ in range(5):
        if any(os.path.isdir(os.path.join(d, m)) for m in JOB_MARKERS):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.abspath(path))


def demands_of(text: str) -> int:
    """How many independent things this text asks the model to satisfy.

    ⛔ This is the measurement T2I-CoreBench actually made — compositional DENSITY, not length —
    and until 2026-09-07 this file printed CoreBench's finding in a warning fired by a character
    count. Two different measurements wearing one message.

    The proxy: clauses separated by punctuation or a coordinator, each carrying at least one
    content word. It is a proxy and says so — an em-dash aside is counted as its own demand and a
    long noun phrase as one, which over- and under-counts in opposite directions. What it is good
    at is the comparison that matters: this block against its budget, and this prompt against the
    one that worked."""
    n = 0
    for part in DEMAND_SPLIT_RE.split(text or ""):
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", part) if len(w) > 2]
        if words:
            n += 1
    return n


def density_report(bl: dict, refs: list) -> dict:
    """Per-block demands and words, plus the whole-prompt total with references credited.

    A filled reference slot REMOVES a demand: the noun arrives as pixels instead of as words the
    model has to reconcile with everything else (prompting-craft.md §6b). That is the reference
    plan and the length rule finally measuring the same thing — sourcing a reference should make
    the prompt cheaper, and here it visibly does."""
    per = {}
    total = 0
    for name, text in bl.items():
        if name in ("SUPPRESS", "_lead") and name != "_lead":
            continue
        d = demands_of(text)
        per[name] = {"demands": d, "words": len(str(text).split())}
        total += d
    sourced = sum(1 for r in refs
                  if isinstance(r, dict) and (r.get("file") or r.get("value")) and r.get("what"))
    net = max(0, total - sourced)
    words = sum(v["words"] for v in per.values())
    return {"per_block": per, "demands_raw": total, "references_credited": sourced,
            "demands": net, "words": words,
            "per_100_words": round(100 * net / words, 1) if words else 0.0}


def _result(path, fm, body, fails, warns, txt, extra=None) -> dict:
    ok = not fails
    sidecar = None
    if ok and txt is not None:
        bl = blocks_of(body)
        refs = fm.get("refs") if isinstance(fm.get("refs"), list) else []
        sidecar = {"lint_version": LINT_VERSION, "linted_at": dt.datetime.now().astimezone()
                   .replace(microsecond=0).isoformat(),
                   "shot": fm.get("shot"), "kind": fm.get("kind"), "type": fm.get("type"),
                   "form": fm.get("form") or None, "model": fm.get("model"), "resolution": fm.get("resolution"),
                   "duration": _num(fm.get("duration")), "aspect": fm.get("aspect"),
                   "start_frame": fm.get("start_frame"), "start_frame_media": fm.get("start_frame_media"),
                   "end_frame": fm.get("end_frame") or None,
                   "line": fm.get("line"), "vo": fm.get("vo"), "function": fm.get("function"),
                   "payload": fm.get("payload"),
                   "quality": fm.get("quality") or None, "output_format": fm.get("output_format") or None,
                   "generate_audio": fm.get("generate_audio"),
                   "variants": int(_num(fm.get("variants")) or 1),
                   "ref_plan": [{"role": r.get("role", "image"), "what": r.get("what"),
                                 "value": r.get("value"), "file": r.get("file"),
                                 "use": r.get("use")} for r in (fm.get("refs") or [])
                                if isinstance(r, dict)],
                   "refs": refs, "negative": ", ".join(i.strip() for i in
                                                        re.split(r"[,\n;]", bl.get("SUPPRESS", "")) if i.strip()),
                   "prompt": txt, "prompt_sha256": sha256_text(txt), "prompt_len": len(txt),
                   "prompt_words": len(txt.split()), "density": density_report(bl, refs),
                   "band": [BAND_LO, BAND_HI],
                   "file_sha256": sha256_file(path), **(extra or {})}
    return {"file": path, "ok": ok, "fails": fails, "warns": warns, "prompt": txt, "sidecar": sidecar}


# ----------------------------------------------------------------------------------------------
# THE INSERT LANE — one template, linted once, for a FAMILY of short inserts
# (house decision 2026-10-25 on the direct-response trial proposal's P7, "Family approval"). A long DR body needs
# dozens of 1–2.5 s inserts, and the per-shot paperwork that is right for a hero shot is wrong for
# eighty hands-with-the-bottle. A `<FAMILY>.family.md` file is ONE prompt with `{{slot}}` holes and
# a member list; this lints it once, writes one ordinary `<SHOT>.<kind>.prompt.md` per member (so
# every call still matches its own linted prompt and its own approved still), and `gate.py approve
# family:<FAMILY>` signs the members' start frames on one contact sheet.
# ⛔ Never for dialogue, a character's identity, or a shot that carries proof of a claim.
FAMILY_MAX = 12            # members per family approval (the proposal's cap)
FAMILY_CUT_MAX = 2.5       # seconds of each member the cut may use
FAMILY_SUFFIX = ".family.md"
FAMILY_TYPES = ("insert", "broll")
FAMILY_KEYS = ("family", "slots", "members", "cut_max")
FAMILY_PROOF_RE = re.compile(r"\b(?:proof|prove[sn]?|claim|testimon\w*|before[- ]and[- ]after|"
                             r"before/after|result|results|evidence|review|rating)\b", re.I)
SLOT_RE = re.compile(r"\{\{\s*([a-z][a-z0-9_]{0,30})\s*\}\}")


def _family_header_without_family_keys(text: str) -> str:
    """The family file's frontmatter lines minus family-only keys and the member list."""
    head = text.split("\n---", 1)[0][3:]
    out, skipping = [], False
    for line in head.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z_ ]*):", line)
        if m:
            skipping = m.group(1).strip().lower() in FAMILY_KEYS
            if skipping:
                continue
        elif skipping and (line.startswith((" ", "\t")) or not line.strip()):
            continue
        else:
            skipping = False
        out.append(line)
    return "\n".join(out).strip("\n")


def lint_family(path: str, job_root: str | None = None, write: bool = True) -> dict:
    """Lint a family file, write its members, lint each. ok only when the family AND every member
    pass; sidecars are written only then (all or nothing)."""
    text = read(path)
    fm, body = split_front(text)
    fails, warns = [], []
    F = lambda x: fails.append(x)
    W = lambda x: warns.append(x)
    name = fm.get("family") or ""
    want_name = os.path.basename(path)[: -len(FAMILY_SUFFIX)] if path.endswith(FAMILY_SUFFIX) else ""
    if not name:
        F("`family:` missing — the family's name, which `gate.py approve family:<NAME>` signs")
    elif not SHOT_RE.match(name):
        F(f"`family: {name}` — letters, digits, - and _ only")
    elif want_name and name != want_name:
        F(f"`family: {name}` but the file is {os.path.basename(path)} — name the file <family>{FAMILY_SUFFIX}")
    kind = (fm.get("kind") or "").lower()
    if kind not in ("clip", "frame"):
        F("`kind:` must be clip or frame")
    typ = (fm.get("type") or "").lower()
    if kind == "clip" and typ not in FAMILY_TYPES:
        F(f"`type: {typ or '?'}` — the insert lane is for {' / '.join(FAMILY_TYPES)} only. Dialogue, "
          f"reactions and hero shots keep their own prompt and their own approval")
    if (fm.get("form") or "").strip():
        F("a family carries no `form:` — a multi-shot clip is planned on its own (multishot.md)")
    for k in ("shot", "start_frame", "start_frame_media", "generated_from", "family_sha"):
        if fm.get(k):
            F(f"`{k}:` belongs to each member, not to the family")
    for k in ("line", "vo"):
        if fm.get(k):
            F(f"`{k}:` — a family never speaks (the voice gate owns every line)")
    bl = blocks_of(body)
    if any(b in bl for b in ("SPEECH", "SOUND", "LINE", "DIALOGUE")):
        F("a family has no speech block — no line is ever spoken in the insert lane")
    func = fm.get("function") or ""
    if kind == "clip" and not func:
        F("`function:` missing — what the inserts do for the cut (direction.md)")
    if FAMILY_PROOF_RE.search(func):
        F(f"`function: {func}` — a shot that carries PROOF of a claim (a result, a review, a "
          f"before/after) is approved on its own, never in a family (compliance.md)")
    refs = fm.get("refs") if isinstance(fm.get("refs"), list) else []
    for r in refs:
        if isinstance(r, dict) and str(r.get("what") or "").strip().lower() in ("character", "face"):
            F("a family binds no character reference — identity is approved shot by shot "
              "(character-and-props.md §8.7b); hands and objects are fine")
            break
    cut = _num(fm.get("cut_max"))
    if kind == "clip":
        if cut is None:
            F(f"`cut_max:` missing — the seconds of each member the cut may use (≤ {FAMILY_CUT_MAX:g})")
        elif cut > FAMILY_CUT_MAX:
            F(f"`cut_max: {cut:g}` — the insert lane is for shots the cut uses ≤ {FAMILY_CUT_MAX:g} s; a "
              f"longer shot is a hero shot and gets its own approval")
    slots = [x.strip().lower() for x in re.split(r"[,·]", fm.get("slots") or "") if x.strip()]
    used = set(SLOT_RE.findall(body))
    undeclared = sorted(used - set(slots))
    if undeclared:
        F(f"the template uses {', '.join('{{' + u + '}}' for u in undeclared)} but `slots:` does not "
          f"declare it — a member fills declared slots only")
    for sl in slots:
        if sl not in used:
            W(f"slot `{sl}` is declared and never used in the template")
    members = fm.get("members") if isinstance(fm.get("members"), list) else []
    if not members:
        F("`members:` is empty — list each shot: `- shot: S12a · start_frame: 02-startframes/S12a.png · "
          "<slot>: <value>`")
    if len(members) > FAMILY_MAX:
        F(f"{len(members)} members — a family approval covers at most {FAMILY_MAX}; split it")
    allowed_keys = {"shot", "start_frame", "start_frame_media"} | set(slots)
    seen = set()
    for i, mbr in enumerate(members, 1):
        sh = mbr.get("shot") or ""
        if not SHOT_RE.match(sh):
            F(f"member {i}: `shot:` {sh!r} is not a shot id")
        elif sh in seen:
            F(f"member {i}: shot {sh} listed twice")
        seen.add(sh)
        extra = sorted(k for k in mbr if k not in allowed_keys)
        if extra:
            F(f"member {sh or i}: sets {', '.join(extra)} — a member fills its declared slots and its "
              f"start frame, nothing else; anything shared is written once in the family")
        missing = sorted(sl for sl in used & set(slots) if not str(mbr.get(sl) or "").strip())
        if missing:
            F(f"member {sh or i}: no value for {', '.join(missing)}")
        if kind == "clip" and not mbr.get("start_frame"):
            F(f"member {sh or i}: `start_frame:` missing — every clip binds its own approved still")
    members_out = []
    if fails:
        return {"file": path, "ok": False, "fails": fails, "warns": warns, "members": members_out}
    prompts_dir = os.path.dirname(os.path.abspath(path))
    fam_sha = sha256_file(path)
    shared = _family_header_without_family_keys(text)
    plan = []
    for mbr in members:
        sh = mbr["shot"]
        dest = os.path.join(prompts_dir, f"{sh}.{kind}.prompt.md")
        if os.path.isfile(dest):
            prev, _ = split_front(read(dest))
            if prev.get("generated_from") != os.path.basename(path):
                F(f"{os.path.basename(dest)} exists and was not generated from this family — rename the "
                  f"member or move the hand-written prompt; a family never overwrites one")
                continue
        filled = SLOT_RE.sub(lambda m_: str(mbr.get(m_.group(1)) or ""), body)
        head = (f"shot: {sh}\nfamily: {name}\ngenerated_from: {os.path.basename(path)}\n"
                f"family_sha: {fam_sha}\n" + (f"cut_max: {cut:g}\n" if cut is not None else "")
                + (f"start_frame: {mbr['start_frame']}\n" if mbr.get("start_frame") else "")
                + (f"start_frame_media: {mbr['start_frame_media']}\n" if mbr.get("start_frame_media") else "")
                + shared + "\n")
        plan.append((sh, dest, "---\n" + head + "---\n" + filled.lstrip("\n")))
    if fails:
        return {"file": path, "ok": False, "fails": fails, "warns": warns, "members": members_out}
    if not write:
        return {"file": path, "ok": True, "fails": [], "warns": warns, "members": [p_[0] for p_ in plan]}
    for sh, dest, txt in plan:
        open(dest, "w", encoding="utf-8").write(txt)
    results = [lint(dest, job_root) for _, dest, _ in plan]
    for (sh, dest, _), r in zip(plan, results):
        members_out.append({"shot": sh, "file": dest, "ok": r["ok"], "fails": r["fails"], "warns": r["warns"],
                            "result": r})
        for x in r["fails"]:
            F(f"{sh}: {x}")
    ok = not fails
    for m_ in members_out:
        write_sidecar(m_["file"], m_["result"]["sidecar"] if ok else None)
    return {"file": path, "ok": ok, "fails": fails, "warns": warns, "members": members_out}


def family_members(path: str) -> list:
    """[(shot, start_frame)] as the family file declares them — what `approve family:` signs."""
    fm, _ = split_front(read(path))
    return [(m.get("shot") or "", m.get("start_frame") or "")
            for m in (fm.get("members") if isinstance(fm.get("members"), list) else [])]


def write_sidecar(path: str, sidecar: dict | None) -> str | None:
    ok_path = path[:-3] + ".ok" if path.endswith(".md") else path + ".ok"
    if sidecar is None:
        if os.path.isfile(ok_path):
            os.remove(ok_path)
        return None
    with open(ok_path, "w", encoding="utf-8") as fh:
        json.dump(sidecar, fh, indent=2, ensure_ascii=False)
    return ok_path


TEMPLATES = {
"family": """---
family: hands-bottle      # the file is 01-script/prompts/hands-bottle.family.md; `gate.py approve
                          # family:hands-bottle` signs the members' start frames on ONE contact sheet
kind: clip
type: insert              # insert | broll only — never dialogue, a reaction or a hero shot
function: the bottle in daily use between the mechanism lines   # never proof of a claim
model: kling4_0
resolution: 1080p
duration: 5               # generated with handles; the cut uses at most cut_max of it
aspect: 9:16
variants: 1
cut_max: 2.5              # seconds of each member the edit may use (≤ 2.5)
slots: surface, light     # the ONLY words a member may set; each is a {{slot}} in the body
members:                  # ≤ 12. Each: its shot, its own start frame, its slot values (no commas)
  - shot: S12a · start_frame: 02-startframes/S12a_bottle_v1.png · surface: kitchen counter · light: morning window light
  - shot: S12b · start_frame: 02-startframes/S12b_bottle_v1.png · surface: bedside table · light: warm lamp light
payload: <what this family adds to the cut, in one line>
---
[MOTION]
INTENT: her daily habit, done on autopilot: quick and sure, the hand knows where the bottle is
START: her hand comes in fast and takes the bottle off the {{surface}} straight away, {{light}}
MID:   her thumb flicks the cap open in the same move and she tips two capsules into her palm, one shake
END:   she sets the bottle back down with a light tap, label facing out where it lands, and the hand leaves

[CAMERA]
locked-off, eye level, close

[CONSTRAINTS]
text, a face in frame
""",
"scene": """---
shot: S4
kind: clip
form: scene               # v2.49 default for Seedance 2.5 / Cinema Studio: approved reference sheets + the block
                          # template (prompting-craft.md §12). No start frame needed; identity comes from the sheets
type: broll               # dialogue | reaction | broll | establishing | insert
model: seedance_2_5
resolution: 1080p         # 720p allowed (one upscale on the final, after the cut); 1080p for wide plates and faces
cut: 8                    # seconds the edit holds the shot (the shot list's Dur)
duration: 10
aspect: 16:9
variants: 1
generate_audio: true      # kept: the clip's own diegetic sound is production sound (editing-and-audio.md §7d)
scene: <the scene file id>   # optional but the house way: 01-script/scenes/<id>.scene.md supplies the shared blocks
setup: <camera setup id: A, B …>   # shots on one setup share one lens and one distance (prompt_lint.py --scene)
function: <what this shot does in the story, in one line>
payload: <what the viewer knows at the end of the shot that they did not know at the start>
world: <the location's world card id, or `none (<why>)`>   # world.py — an exterior needs one
refs:                     # @Image N follows THIS order; every one an approved sheet (character:, prop:, world:)
  - role: image_references, what: character, value: <media id>, not: sheet background, panel layout, studio lighting
  - role: image_references, what: prop, value: <media id>, not: studio background
  - role: image_references, what: environment, value: <media id>, not: people in the plate
---
[SCENE CONTEXT]
<two or three sentences: where we are in the story, what this shot is for, the one thing that happens>

[ACTIVE REFERENCES]
@Image 1: <character> — face, hair and wardrobe only
@Image 2: <prop> — shape, material and colour only
@Image 3: <location> — the space and its materials only; the light comes from the lighting block

[LOCATION MAP]
<the space as the camera sees it: what is screen-left, screen-right and behind; distances in metres; where the
 light enters>

[FIRST FRAME]
<the opening frame with the action already under way: who is where, facing which way, holding what — never an
 empty establishing beat>

[FORMAT MODE]
<one continuous take in real time, at normal speed — or the cut list in [SHOTS]>

[OPTICS]
<field of view in degrees and the focal length, camera distance in metres, depth of field>

[CAMERA]
<one camera behaviour: who operates it (a person walking backwards, a locked tripod), height, how it follows>

[ACTION TIMING]
0–3 s: <the first beat>
3–7 s: <the second beat>
7–10 s: <how it settles: the end state>

[PERFORMANCE]
<one held state per character, shown through the body: jaw, eyes, breath, posture; restraint, eyes off the lens;
 mouths closed unless a line is scripted in [SPEECH]>

[PHYSICS]
<weight and contact, cloth and hair, what moves because of what>

[LIGHTING]
<the motivated source, its direction and hardness, what it does across the frame>

[COLOR]
<the palette in plain words, and what holds steady>

[AUDIO]
This clip sounds like <the place>, not <the place it must not sound like>.
AMBIENCE: <the bed: air, room tone, distant sources>
SFX: <sounds tied to the action; off-screen sources with their direction; any cue at a stated second>
MUSIC: none. No music; the owner chooses music in the edit.

[STYLE]
<capture medium and texture in plain words, never a film's or a director's name>

[POSITIVE LOCKS]
<restate, as the wanted state, every fact at risk of drifting: counts, positions, hands, wardrobe, direction>

[CONSTRAINTS]
text, extra people, morphing background figures
""",
"scene-file": """---
scene: S2                 # shots name it with `scene: S2`; this file is 01-script/scenes/S2.scene.md
model: seedance_2_5
aspect: 16:9
world: <the location's world card id, or `none (<why>)`>
time: <time of day and where the sun or the main source sits>
refs:                     # in THIS order they are @Image 1, 2, 3 … in every shot of the scene (each an approved sheet)
  - role: image_references, what: character, value: <media id>, not: sheet background, panel layout, studio lighting
  - role: image_references, what: prop, value: <media id>, not: studio background
  - role: image_references, what: environment, value: <media id>, not: people in the plate
---
[ACTIVE REFERENCES]
@Image 1: <character> — face, hair and wardrobe only
@Image 2: <prop> — shape, material and colour only
@Image 3: <location> — the space and its materials only

[LOCATION MAP]
<the place once, for every shot: what stands where, distances in metres, which side of the action line the camera
 keeps, which way each door and window faces>

[WARDROBE]
<what each character wears in THIS scene, item by item, and what each one carries>

[LIGHTING]
<the scene's light: the motivated source, its direction against the location map, the time of day; a shot adds only
 what changes>

[COLOR]
<the scene's palette, and what holds steady>

[AUDIO]
This scene sounds like <the place>, not <the place it must not sound like>.
AMBIENCE: <the bed every shot of the scene shares>
VOICE (<name>): <the voice identity string, word for word in every shot that speaks>
MUSIC: none. No music; the owner chooses music in the edit.

[POSITIVE LOCKS]
<what holds in every shot of the scene: counts, fixed objects and where they stand, wardrobe, the side of the line>
""",
"dna": """---
project: <job slug>       # 01-script/scenes/_PROJECT.dna.md — pasted into EVERY scene-form shot of the film
---
[STYLE]
<capture medium and texture in plain words: the line every prompt of the film carries, never a film's or a name>

[FORMAT MODE]
<the film's default: one continuous take in real time unless a shot lists its cuts in [SHOTS]>

[OUTPUT SETTINGS]
<the frame carries only the picture: captions and titles are added in the edit; the film's frame>

[POSITIVE LOCKS]
<what holds across the whole film>
""",
"multishot": """---
shot: S4
kind: clip
form: multishot           # a PLANNED multi-shot clip (references/multishot.md) — several shots in one
                          # generation. Every internal cut is FINAL: no handles, no re-cut. Lock the cut
                          # list and the blocking before writing this
type: sequence
model: seedance_2_5       # route by the lock that matters (multishot.md §3): exact frames → kling3_0
                          # (≤15 s, no refs); blocking + cast → seedance_2_5 (≤30 s, frames bind as refs)
resolution: 1080p
cut: 22                   # seconds the edit holds the sequence (the shot list's Dur)
duration: 24              # = the last stage's end; inside the model's range
aspect: 9:16
variants: 1
start_frame: 02-startframes/S4_open_v2.png    # APPROVED. On a reference-mode model it binds as @Image 1
end_frame:                # a TRUE end frame only where call_shape allows it (kling3_0); otherwise bind the
                          # approved end still in refs as `what: endframe` (the gate checks it)
payload: <what the viewer knows at the end of the sequence that they did not know at the start>
refs:                     # @Image N / @Video N / @Audio N follow THIS order (start still first when it is
                          # a reference); prompt_lint prints the map. One subject per reference
  - role: video_references, what: blocking, file: 03-blocking/S4.mp4, manifest: 03-blocking/S4.json, not: mannequins, flat colours, floor grid
  - role: image_references, what: character, value: <media id>, not: sheet background, panel layout, studio lighting
  - role: image_references, what: prop, value: <media id>, owner: Mika, not: studio background
  - role: image_references, what: environment, value: <media id>, not: people in the plate
  - role: image_references, what: endframe, value: <approved end frame media id>
---
[GOAL]
<one or two sentences: the kind of sequence, the central subject, the one arc it carries>

[REFERENCES]
[Characters] Mika corresponds to @Image 2. Use only the appearance, hairstyle, and clothing.
[Props] The phone corresponds to @Image 3 and belongs only to Mika. Use only the shape, material, and colour.
[Scenes] The terrace corresponds to @Image 4. Use only the space, materials, and lighting, never the people in it.
[Frames] @Image 1 is the first frame of Stage 1; match its composition. @Image 5 is the final frame of the last stage.
[Motion] @Video 1 is the blocking: camera path, positions and timing only, never its grey figures or floor grid.

[WHERE]
<per location: who sits where (clock face, or screen-left/centre/right from a named camera side), and
 what is behind each of them>

[STAGES]
Stage 1 | 0–8 s | MS, 35 mm, eye level, slow push-in
Use: Mika, @Image 2, @Image 3, @Video 1
Event: <one primary state change>
End state: <positions, who holds what, what stays in frame>
Cut: match cut on the tap

Stage 2 | 8–16 s | MCU, 50 mm, eye level, locked-off
Use: Mika, @Image 2, @Image 4
Event: <one primary state change>
End state: <…>
Cut: hard

Stage 3 | 16–24 s | WS, 24 mm, eye level, slow pull-back
Use: Mika, @Image 4, @Image 5
Event: <one primary state change, landing on the end frame>
End state: <the final picture>

[SOUND]
Lines, each spoken exactly once and nothing else:
10.0–11.1 s Mika: "<the exact scripted line>"
No added words, interjections, laughter or humming. Ambience changes on the cut frames.

[CONSISTENCY]
<identity and the number of people · clothing · who owns which prop · the seats · screen direction ·
 the light source — positively, once each>

[CONSTRAINTS]
text, extra people, duplicated props
""",
"clip": """---
shot: S3
kind: clip
type: dialogue            # dialogue | reaction | broll | establishing | insert
model: minimax_h3         # roster only: kling3_0 | kling4_0 | minimax_h3 | seedance_2_5 | gemini_omni_flash_1_1 | wan3_0
resolution: 2k            # a measured row for the model; never under 1080p
cut: 4.5                  # seconds the EDIT holds this shot — the shot list's Dur, never a default
handle: 0                 # past the cut: 1–2 s before a dissolve/wipe, 0 at hard cuts (dialogue: 0)
duration: 6               # DERIVED: lead-in 1 + cut + handle, rounded up; a dialogue line must fit
aspect: 9:16              # from the job's delivery preset
variants: 1               # count the call may request; >1 multiplies the spend, so declare it
start_frame: 02-startframes/S3_hero_v2.png   # the APPROVED still this clip animates
start_frame_media:        # optional here — `gate.py approve frame:S3 --media-id` is authoritative
end_frame:                # OPTIONAL — the approved still the clip must ARRIVE at (`approve endframe:S3`).
                          # The most reliable control of a move that needs geometry; it adds nothing
                          # to a simple dolly the prompt already gets. The move you get is the one
                          # implied by the DIFFERENCE between the two frames — change only the pose
                          # and you have encoded no camera move (episode 2026-08-29)
line: "The exact scripted line, verbatim."   # dialogue only
vo: 05-voice/S3.wav       # Path A (audio-driven) — omit for Path B and write [SPEECH]
function:                 # broll/insert only: the job this insert does in the cut
payload:                  # REQUIRED. One sentence: what does the viewer know at the END that they
                          # did not know at the START? ⛔ This is F11 (cinematography-craft.md §8)
                          # asked on the PLAN instead of after the clip is paid for. If you cannot
                          # write it, the shot has no event — go back to the event card
                          # (direction.md §2b) and redesign it. Do not re-prompt a dead shot.
tell:                     # OPTIONAL — the decision tell before the action: "eyes to the jar, a breath"
obstacle:                 # OPTIONAL — the one resistance the intent beats: "the wet sugar sticks"
witness:                  # OPTIONAL — the prop that holds the state and the action changes: "the full jar"
persona:                  # the person's movement persona (_reference/PERSONA-<name>.md), when one is cast
enter:                    # OPTIONAL — screen direction of what moves in the first moments: "from left, the hand in"
exit:                     # OPTIONAL — screen direction of what still moves in the last frames: "right, the jar leaving"
join:                     # OPTIONAL — the hand-off to the next shot: motion-match | match-on-action | whip |
                          # graphic-match | camera-carry | flip (a deliberate reversal) — shot-handoff.md §4b
prelap:                   # OPTIONAL (3.2.0) — the next shot's sound starts before the cut: "0.5s, knock, side=right"
                          # (lead 0.25–1.0 s; the event by its read word, e.g. knock / open, or id, e.g. E2, in the
                          # NEXT shot's read; side optional)
                          # — sfx_conform.py joins; editing-and-audio.md §7f
track:                    # OPTIONAL — objects motion_qa.py follows: "jar=0.42,0.55,0.12,0.20; cup=…" (the box on
                          # the start frame, fractions from the top-left)
sfx:                      # OPTIONAL — the sound the shot makes, for sfx_conform.py: "count=3, surface=wet,
                          # space=kitchen, distance=close, hero=jar" (the read fills the rest from the frames)
ramp:                     # OPTIONAL — a planned speed ramp: "kind=slow, speed=40, trigger=2.1, reveal=<what the
                          # slow-motion shows>, sfx=<cue>" or "kind=burst, speed=130, trigger=1.4, sfx=<cue>".
                          # Never on dialogue or reaction clips; at most 2 per video, 1 per 20 s (motion_qa.py)
                          # (v2.48.0, project switch speed-conform, music-led) Only with the job's switch:
                          # speed-conform → "conform=60/24" or
                          # "conform=40%" (a whole-clip conform), "ease=90%" on a join: whip shot; music-led →
                          # a burst's "trigger=song@12.4" (switches.py)
aerial:                   # aerial, FPV, insect or planet shots ONLY (aerial-and-fpv.md): "move=orbit, function=reveal,
                          # subject=the clubhouse roof, final=the clubhouse with the sea beyond, place=real,
                          # landmarks=the Swilcan Bridge" — move from assets/aerial-moves.json (an alias or DJI preset
                          # works); function is its job; place=real needs a real cleared photograph as the start frame
chain:                    # OPTIONAL — a declared aerial chain (house rule C1): "root=02-startframes/<real>.jpg,
                          # stage=1, from=S3" — the start frame pulled by `aerial_qa.py chain-frame`, 3 links at most
grade:                    # OPTIONAL — the grade profile for grade_luts.py plan: talking_head | broll | product |
                          # anatomy | clean (product, anatomy and clean stay clean: no look, no texture).
                          # Left out: dialogue and reaction → talking_head, anything else → broll
refs:                     # OPTIONAL extra references beyond the start frame — the frame is the
                          # clip's main reference. ONE attribute each, and whatever a reference
                          # carries the prompt does NOT re-describe (prompting-craft.md §6b):
                          #   - role: image_references, what: prop, value: <media_or_job_id>
                          #   - role: video_references, what: motion, file: _reference/motion/pour.mp4
                          # Roles are the MODEL's (assets/higgsfield-rates.json -> media_roles);
                          # kling3_0 takes NO references, only the start and end frame.
                          # LENGTH: the measured band is 1800–2100 chars for the WHOLE prompt
                          # [PRIMARY · own testing across many real generations · 2026-09-07] —
                          # low error rate AND enough detail for accurate generation. Thin is not
                          # safe: everything you leave out, the model fills in, differently every
                          # take. The per-block budgets below are that band divided across the
                          # blocks, which is what keeps length from becoming DENSITY — the thing
                          # every model measured actually degrades on (prompting-craft.md §2.2).
                          # A sourced reference REMOVES a demand; rewording removes none.
                          # Per-block word budgets: SUBJECT/CHARACTER/ENVIRONMENT/MOTION 70 ·
                          # SETTING 60 · PERFORMANCE 75 · LIGHTING 50 · LOCATION 45 · SPEECH 40 ·
                          # STYLE 35 · COLORS 30 · CAMERA/SAFE ZONE 25 (a lens, a height, ONE move).
                          # The band applies to FRAME prompts; a clip carries motion only and is
                          # structurally shorter. Density warns above 30 demands per 100 words.
---
[MOTION]
INTENT: <why they do it, as an attitude, and the manner it forces — "done with sugar: fast, no second thought">
START: <opening pose / framing — the frame as approved; the PERSON leads, never the material>
MID:   <the one movement / gesture / expression change, mid-action verbs with tempo and force>
END:   <the aftermath the clip settles into — what the objects do BECAUSE of that force>

[CAMERA]
<one behaviour: e.g. "locked-off, eye level" or "slow push in, 50mm">

[PERFORMANCE]
STATE:    <from → to>
STIMULUS: <what they react to, and when — or "none — she starts it">
TARGET:   <who or what they play towards, and where>
BEAT:     <the before, held>, then <the one change>
BODY:     <MS or wider: one bundle in plain words — delete this line at MCU and closer>
FACE:     <what the face does, said as a state: "the head stays still">
GAZE:     <where the eyes are, and when they move>

[SPEECH]
<Path B only: delivery notes — pace, warmth; the words come from line:>

[CONSTRAINTS]
text, morphing background figures
""",
"frame": """---
shot: S3
kind: frame
type: character           # character | environment | product | two-shot
model: nano_banana_pro    # the client profile's start-frame image model
resolution: 2k            # ⛔ the quality floor applies HERE too: the frame sets the picture and
                          # every clip inherits it. >= 1080p, and >= the delivery resolution
aspect: 9:16
variants: 2               # two candidates for the frame gate is the house default
character: hero           # optional — locks [CHARACTER] to _reference/CHARACTER-hero.md
caught:                   # an ACTION shot: the anticipation peak the clip completes — "wrist cocked, the
                          # jar tipped 20° over the bin". Never a rest pose (motion-craft.md §6c)
travel:                   # where the action goes — "down-left into the bin, toward the lens"; leave room
                          # on that side, and prefer diagonal or depth over a flat move across the frame
refs:                     # THE REFERENCE PLAN — sourced BEFORE this prompt is written, never
                          # judged after the render. One reference carries ONE attribute, and
                          # whatever it carries the prompt does NOT re-describe (prompting-craft.md
                          # §6b: reference the nouns, prompt the verbs). A `file:` must exist with a
                          # provenance sidecar beside it; an uncleared asset needs `use: reference-only`
                          # and its likeness must not reach the output (stock-sourcing.md §5).
  - role: image, what: character, value: <media_or_job_id>, not: sheet background, panel layout, studio lighting
                          # `not:` is the NEGATIVE SCOPE — what this reference must NOT bring with
                          # it. `what:` says which attribute it is FOR; the rest of the picture
                          # arrives anyway. A character sheet carries its seamless grey, its panel
                          # layout and its studio key into a night interior unless you say
                          # otherwise (prompting-craft.md §11d). Required on character/wardrobe/prop.
                          #   - role: image, what: wardrobe, file: _reference/wardrobe/apron-front.jpg, not: sheet background
                          #   - role: image, what: environment, file: _reference/environment/room.jpg, use: reference-only, not: framing, camera height
                          #   - role: video, what: motion, file: _reference/motion/pour.mp4
                          # `state: after` marks a reference that carries the POST-change look of
                          # something that changes on screen (torn, soaked, broken). A state change
                          # inside one clip is an F — the model has no state register, so the
                          # change reverts between frames and no amount of restatement holds it
                          # (cinematography-craft.md §7.1). The fix is this asset, or a cut at the
                          # change. Nothing else works:
                          #   - role: image, what: wardrobe, value: <id>, state: after, not: sheet background
                          # `need:` is the SHOPPING LIST entry — the slot is designed here, at the
                          # shot, and sourced before the prompt runs. `refsource.py brief` reads it
                          # (and falls back to the prompt's own words), `fill --execute` searches
                          # Pixabay, `adopt` writes the chosen file back into this line:
                          #   - role: image, what: environment, need: rustic kitchen window light
                          # LENGTH: the measured band is 1800–2100 chars for the WHOLE prompt
                          # [PRIMARY · own testing across many real generations · 2026-09-07] —
                          # low error rate AND enough detail for accurate generation. Thin is not
                          # safe: everything you leave out, the model fills in, differently every
                          # take. The per-block budgets below are that band divided across the
                          # blocks, which is what keeps length from becoming DENSITY — the thing
                          # every model measured actually degrades on (prompting-craft.md §2.2).
                          # A sourced reference REMOVES a demand; rewording removes none.
                          # Per-block word budgets: SUBJECT/CHARACTER/ENVIRONMENT/MOTION 70 ·
                          # SETTING 60 · PERFORMANCE 75 · LIGHTING 50 · LOCATION 45 · SPEECH 40 ·
                          # STYLE 35 · COLORS 30 · CAMERA/SAFE ZONE 25 (a lens, a height, ONE move).
                          # The band applies to FRAME prompts; a clip carries motion only and is
                          # structurally shorter. Density warns above 30 demands per 100 words.
---
[SUBJECT]
<who/what, pose, action as a mid-action verb, wardrobe stated verbatim>

[CHARACTER]
<the fixed character block, pasted byte-for-byte across every frame>

[ENVIRONMENT]
<location, props, season, time of day — concrete and authentic>

[LIGHTING]
<the SOURCE as an object, its direction and quality, and — where a face is in frame — one named
 pattern: "high sun through the left window, hard, long diagonal shadows; loop key on her face;
 a switched-on lamp on the counter behind">

[CAMERA]
<lens mm, height, angle: "50mm, eye level, slight low angle">

[STYLE]
<phone-real or cinema-real, film stock or sensor — physical language, no names>

[SAFE ZONE]
every load-bearing element inside y=15-65%, x=11-72% of frame (the MEASURED ad safe box:
top 15% profile row, bottom 35% captions + CTA, right 28% action rail)

[CONSTRAINTS]
text, logo, second panel, frame border
""",
"edit": """---
shot: S4
kind: edit                # an IMAGE EDIT: one concept changed in a picture that exists (prompting-craft.md §11g)
type: product
model: nano_banana_pro    # an image model; its ceiling is in assets/higgsfield-rates.json → prompt_limits
resolution: 2k            # the 1080p floor applies: the result is a picture every clip inherits
aspect: 9:16
variants: 2
edit_of: 02-startframes/S4_kitchen_v2.png   # the source picture, under the job (its hash is recorded)
edit_of_media: <the media id the call binds as the picture being edited>
use: frame                # frame = the result goes to the frame gate · target = it becomes a MODEL REFERENCE,
                          # allowed only as the owner's gated per-shot opt-in: `gate.py approve target:S4` first
refs:                     # each reference: ONE job, and in [REFERENCES] one line saying what it must NOT bring
  - role: image, what: prop, value: <media id of the real product photo>, not: white sweep, softbox reflections
---
[SOURCE]
Image 1 is the approved start frame for S4: a woman in her forties at a pale limestone kitchen counter at about
ten in the morning, holding a plain unlabelled glass bottle of olive oil in her right hand, photographed at eye level.

[KEEP]
Keep exactly as in Image 1:
- her face, hair and expression
- her pose: right hand around the bottle's neck, left hand flat on the counter
- the framing and composition: her head in the upper third, the counter edge at 70 % of the frame height
- the light: hard morning sun from the left window, warm, long shadows falling to the right
- the lens and perspective: a 50 mm look from eye level
- the background: the open oak shelves, the jar of olives, the doorway soft and out of focus
- her wardrobe: the green linen apron over a white cotton shirt

[CHANGE]
Replace only the bottle in her right hand with the product in Image 2:
1) placement: the same spot in her right hand, lower-left third of the frame, its base on the counter
2) size: 24 cm tall, the same height as the bottle it replaces, about 18 % of the frame height
3) material: dark amber glass, a matte black aluminium cap, a cream paper label printed "Kalamata 500 ml"
4) contact with the light: her fingers wrap the neck and cover the label's left edge; its shadow falls to the right
   on the stone like the jar's; the window shows as a narrow highlight down the bottle's left shoulder

[LIGHT MATCH]
The product takes the frame's own light: the key from the left window, warm morning sun, hard, with the same
shadow direction and softness as the olive jar beside it; none of the studio highlights of Image 2.

[REFERENCES]
Image 2 is the product (prop): its shape, glass colour, cap and label only, not its white sweep, not its softbox reflections, not its shadow.

[OUTPUT]
9:16, 2k, one photographic frame. No text, letters or logos other than the label's own words "Kalamata 500 ml",
spelled exactly as printed.
""",
}


def lint_str(text: str, tmpdir: str, name: str) -> dict:
    """selftest convenience: lint a prompt held as a string, inside a job-shaped tmpdir."""
    p = os.path.join(tmpdir, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return lint(p)


SCENE_FIXTURE = "---\nshot: S4\nkind: clip\nform: scene               # v2.49 default for Seedance 2.5 / Cinema Studio: approved reference sheets + the block\n                          # template (prompting-craft.md §12). No start frame needed; identity comes from the sheets\ntype: broll               # dialogue | reaction | broll | establishing | insert\nmodel: seedance_2_5\nresolution: 1080p         # 720p allowed (one upscale on the final, after the cut); 1080p for wide plates and faces\ncut: 8                    # seconds the edit holds the shot (the shot list's Dur)\nduration: 10\naspect: 16:9\nvariants: 1\ngenerate_audio: true      # kept: the clip's own diegetic sound is production sound (editing-and-audio.md §7d)\nfunction: the courier commits to the rooftop run\npayload: he will risk the jump to get the drone back\nworld: none (test fixture, no world card in a temp job)   # world.py — an exterior needs one\nrefs:                     # @Image N follows THIS order; every one an approved sheet (character:, prop:, world:)\n  - role: image_references, what: character, value: job_ref01, not: sheet background, panel layout, studio lighting\n  - role: image_references, what: prop, value: job_ref01, not: studio background\n  - role: image_references, what: environment, value: job_ref01, not: people in the plate\n---\n[SCENE CONTEXT]\nNight, a rooftop in an old district. The courier has just lost the drone and decides to chase it on foot. He crosses the roof and vaults the low wall at the far edge.\n\n[ACTIVE REFERENCES]\n@Image 1: the courier — face, hair and wardrobe only\n@Image 2: the satchel — shape, material and colour only\n@Image 3: the rooftop — the space and its materials only; the light comes from the lighting block\n\n[LOCATION MAP]\nCamera stands on the roof's centre line, 6 m from the courier, facing the far wall. Screen-left: a row of water tanks. Screen-right: the street drop behind a rail. Behind him: the stairwell door, 3 m back. Light from a sign below screen-right.\n\n[FIRST FRAME]\nHe is already running, two strides from the stairwell door, satchel strap in his right fist, heading away from camera toward the wall.\n\n[FORMAT MODE]\nOne continuous take in real time, at normal speed.\n\n[OPTICS]\n47 degrees field of view, about a 40 mm lens, 6 m from him, background soft but readable.\n\n[CAMERA]\nHandheld by a person running behind him at chest height, keeping the distance, slightly late on every turn.\n\n[ACTION TIMING]\n0–3 s: he runs the length of the roof, past the tanks.\n3–7 s: he plants a hand on the wall and vaults it, satchel swinging out.\n7–10 s: he lands on the next roof, crouched, and looks up at the sky ahead.\n\n[PERFORMANCE]\nSet jaw, eyes fixed ahead, breath hard through the nose, gaze off the lens, mouth closed.\n\n[PHYSICS]\nReal weight in each footfall on tar paper; the satchel lags his body and slaps his hip on landing; the jacket hem lifts on the vault.\n\n[LIGHTING]\nA red neon sign below screen-right lights him from the side and below; the sky is deep blue and brighter than the roofs; the moon is the only light.\n\n[COLOR]\nDeep blue night, red sign light on skin and jacket; the jacket stays olive.\n\n[AUDIO]\nThis clip sounds like a rooftop above a busy street at night, not an empty studio.\nAMBIENCE: wind across the roof, the street a storey below, a far siren\nSFX: his footfalls on tar paper, the satchel buckle, the scrape of his hand on the wall at 4 s, a dog barking off screen-left\nMUSIC: none. No music; the owner chooses music in the edit.\n\n[STYLE]\nDigital cinema camera at night, fine grain, slight halation on the sign.\n\n[POSITIVE LOCKS]\nOne man only, running away from camera the whole take; satchel on his right shoulder; olive jacket; the wall is on the far edge, the drop stays screen-right.\n"


def _selftest_scene() -> None:
    """v2.49.0: `form: scene` (references + the block template), kept native sound, the 720p video floor, the
    `frame-led` and `floor-1080` switches, GPT Image 2.6's trap defaults."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d_ in ("00-brief", "01-script/prompts", "02-startframes"):
            os.makedirs(os.path.join(job, d_))
        P = os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md")
        L = lambda t: (open(P, "w", encoding="utf-8").write(t), lint(P, job))[1]
        r = L(SCENE_FIXTURE)
        assert r["ok"], r["fails"]
        assert r["sidecar"]["form"] == "scene" and r["sidecar"]["generate_audio"] == "true", r["sidecar"]
        assert not any("start_frame" in f for f in r["fails"])
        # a scene clip carries look blocks freely: CLIP_FORBIDDEN is the i2v fork's rule
        assert not any("in an i2v clip prompt" in f for f in r["fails"])
        # every required block is required
        r = L(SCENE_FIXTURE.replace("[LOCATION MAP]", "[PLACE]"))
        assert any("[LOCATION MAP] missing" in f for f in r["fails"]), r["fails"]
        # no references and no start frame: identity is unanchored
        nore = re.sub(r"(?ms)^refs:.*?(?=^---)", "", SCENE_FIXTURE)
        assert any("no `refs:` and no `start_frame:`" in f for f in L(nore)["fails"])
        # sound kept: "no music" and an ambience are asked for
        nomus = SCENE_FIXTURE.replace("MUSIC: none. No music; the owner chooses music in the edit.", "MUSIC: a soft piano.")
        assert any("never says 'no music'" in w for w in L(nomus)["warns"])
        # mouth-opening words with sound on and no lines
        laugh = SCENE_FIXTURE.replace("mouth closed.", "and he laughs as he runs.")
        assert any("mouth-opening words" in w for w in L(laugh)["warns"]), L(laugh)["warns"]
        assert not any("mouth-opening words" in w for w in L(SCENE_FIXTURE)["warns"])
        # spoken lines without a VOICE: line
        sp = SCENE_FIXTURE.replace("[STYLE]", '[SPEECH]\nCOURIER: "Not this time."\n\n[STYLE]')
        rs = L(sp)
        assert any("no `VOICE:` line" in w for w in rs["warns"]) and rs["sidecar"] and rs["sidecar"].get("has_speech")
        # length: the scene band, not the frame band
        assert any("under 2,500" in w for w in L(SCENE_FIXTURE)["warns"])
        big = SCENE_FIXTURE.replace("[POSITIVE LOCKS]", "[PHYSICS]\n" + ("Real weight in every step. " * 900) + "\n\n[POSITIVE LOCKS]")
        assert any(("> 20,000" in f or "> 20000" in f) for f in L(big)["fails"]), L(big)["fails"]
        # 720p is a legal take since 2.49; 480p is not
        assert L(SCENE_FIXTURE.replace("resolution: 1080p", "resolution: 720p"))["ok"]
        assert any("480p" in f for f in L(SCENE_FIXTURE.replace("resolution: 1080p", "resolution: 480p"))["fails"])
        # the switches: floor-1080 restores the old floor, frame-led refuses the scene form
        ck = os.path.join(job, "00-brief", "CHECKPOINT.md")
        open(ck, "w", encoding="utf-8").write("Switches: floor-1080 — a hero film, native 1080p throughout\n")
        assert any("1080p video floor" in f for f in L(SCENE_FIXTURE.replace("resolution: 1080p", "resolution: 720p"))["fails"])
        open(ck, "w", encoding="utf-8").write("Switches: frame-led — the client approved every still already\n")
        assert any("frame-led" in f for f in L(SCENE_FIXTURE)["fails"])
        os.remove(ck)
        # GPT Image 2.6: its defaults (quality low, 1k) are refused unless stated
        F = os.path.join(job, "01-script", "prompts", "S4.frame.prompt.md")
        fr = TEMPLATES["frame"] if "frame" in TEMPLATES else None
        if fr:
            fixed = re.sub(r"(?m)^model: .*$", "model: gpt_image_2_6", fr)
            open(F, "w", encoding="utf-8").write(fixed)
            ff = lint(F, job)["fails"]
            assert any("`quality:` missing on gpt_image_2_6" in f for f in ff), ff
            open(F, "w", encoding="utf-8").write(fixed.replace("model: gpt_image_2_6", "model: gpt_image_2_6\nquality: low"))
            assert any("`quality: low`" in f for f in lint(F, job)["fails"])
            low = re.sub(r"(?m)^resolution: .*$", "resolution: 1k", fixed)
            open(F, "w", encoding="utf-8").write(low)
            assert any("under the 1080p floor" in f for f in lint(F, job)["fails"]), lint(F, job)["fails"]
    print("  [PASS] v2.49 scene form, kept sound, 720p video floor, frame-led/floor-1080 switches, GPT Image 2.6 defaults")
    # (v2.70.0, Wave 5 A1) the route, per roster model, with and without references
    exp = {("kling3_0", False): ("i2v", True), ("minimax_h3", False): ("i2v", True), ("minimax_h3", True): ("scene", True),
           ("seedance_2_5", False): ("scene", True), ("seedance_2_5", True): ("scene", True)}
    for (m_, refs_), (form_, meas_) in exp.items():
        r_ = route(m_, refs_)
        assert r_["form"] == form_ and r_["measured"] == meas_, (m_, refs_, r_)
    assert not DEFECT_NOUN_RE.search("the logo morphing into the next one, deformed dough, plastic sheeting") \
        and DEFECT_NOUN_RE.search("deformed hands") and DEFECT_NOUN_RE.search("no face morphing")
    rk = route("kling3_0", True)
    assert rk["form"] == "i2v" and "no reference images" in rk["why"], rk     # never the scene form on a no-ref model
    for m_ in ("wan3_0", "kling4_0", "gemini_omni_flash_1_1", "minimax_h3_max"):
        r0, r1 = route(m_, False), route(m_, True)
        assert not r0["measured"] and "unmeasured" in r0["why"] and r0["start_role"] == "start_image", (m_, r0)
        assert r1["form"] == "unmeasured" and "unmeasured" in r1["why"] and r1["start_role"] == "image_references", (m_, r1)
    assert route("no_such_model")["form"] is None
    # (v2.70.0, Wave 5 A2) every model motion-design.md lists for first + last frame has a true first frame and an end
    # role in its FRAMES-ONLY call shape (MiniMax H3 cannot mix frames and references), and Seedance is not listed
    _md = open(os.path.join(SKILL_ROOT, "references", "motion-design.md"), encoding="utf-8").read()
    _tab = _md.split("<!-- ffl-models", 1)[1].split("<!-- /ffl-models", 1)[0]
    _listed = re.findall(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*yes", _tab, re.M)
    assert _listed and "seedance_2_5" not in _listed, _listed
    # (v2.70.0, Wave 5 A4) §12's example card passes the lint's own card rules, so the doc never contradicts the lint
    _pc = open(os.path.join(SKILL_ROOT, "references", "prompting-craft.md"), encoding="utf-8").read()
    _ex = _pc.split("<!-- perf-example -->", 1)[1].split("<!-- /perf-example -->", 1)[0]
    assert all(re.search(rf"\b{k}\s*:", _ex) for k in PERF_KEYS), _ex
    _st = re.search(r"STATE\s*:\s*([^\n]+)", _ex).group(1)
    assert "→" in _st and not any(w in _st.lower() for w in NEGATIVE_STATES), _st
    assert "one held state per character" not in _pc, "§12 still asks for one held state"
    for m_ in _listed:
        assert call_contract(m_).get("frames") is True and call_shape(m_, False, True)["end_role"] == "end_image", m_
    # (v2.70.0, Wave 5 A8) cards from the rates file, dated; staleness is information
    cards = {c["model"]: c for c in model_cards("2026-11-16")}
    assert cards["seedance_2_5"]["speech_status"] == "unverified" and cards["kling3_0"]["speech_status"] == "documented"
    assert cards["kling3_0"]["first_frame"].startswith("true first frame") and cards["wan3_0"]["first_frame"] == "not measured"
    assert cards["wan3_0"]["checked"] == "unknown" and cards["wan3_0"]["stale"] == "unknown date", cards["wan3_0"]
    assert not cards["minimax_h3"]["stale"] and "stale" in {c["model"]: c for c in model_cards("2027-06-01")}["minimax_h3"]["stale"]
    _kp = (call_contract("kling3_0").get("speech_syntax") or {}).get("pattern")
    assert re.search(_kp, 'Mom (softly): "We have to leave."') and re.search(_kp, 'ANA: "Read the date."') \
        and not re.search(_kp, 'she says we have to leave "now"'), _kp
    # (v2.70.0, Wave 5 A3) a defect named in a positive block warns; in [SUPPRESS] or [CONSTRAINTS] it does not
    import tempfile
    with tempfile.TemporaryDirectory() as td3:
        job3 = os.path.join(td3, "job")
        for d_ in ("00-brief", "01-script/prompts", "02-startframes"):
            os.makedirs(os.path.join(job3, d_))
        P3 = os.path.join(job3, "01-script", "prompts", "S4.clip.prompt.md")
        L3 = lambda t: (open(P3, "w", encoding="utf-8").write(t), lint(P3, job3))[1]       # noqa: E731
        dfx = SCENE_FIXTURE.replace("[POSITIVE LOCKS]\nOne man only", "[POSITIVE LOCKS]\nNo extra fingers. One man only", 1)
        assert any("names a defect" in w for w in L3(dfx)["warns"]), L3(dfx)["warns"]
        ok_ = SCENE_FIXTURE.rstrip("\n") + "\n\n[CONSTRAINTS]\nextra fingers, warped hands, interpenetration\n"
        sup_ = SCENE_FIXTURE.rstrip("\n") + "\n\n[SUPPRESS]\nextra fingers, warped hands\n"
        assert not any("names a defect" in w for w in L3(sup_)["warns"]), "a defect noun in [SUPPRESS] is where it belongs"
        r_ok = L3(ok_)
        assert not any("names a defect" in w for w in r_ok["warns"]) and not r_ok["fails"], (r_ok["warns"], r_ok["fails"])
        # (v2.70.0, A8) a documented dialogue form warns when a [SPEECH] line breaks it; an unverified one never does
        kl = SCENE_FIXTURE.replace("model: seedance_2_5", "model: kling3_0").replace(
            "[POSITIVE LOCKS]", "[SPEECH]\nhe shouts that it is \"gone\"\n\n[POSITIVE LOCKS]", 1)
        assert any("documented dialogue form" in w for w in L3(kl)["warns"]), L3(kl)["warns"]
        assert any("documented dialogue form" in w for w in L3(kl.replace('he shouts that it is "gone"', "COURIER: gone"))["warns"])
        assert not any("documented dialogue form" in w for w in L3(kl.replace('he shouts that it is "gone"',
                                                                             'COURIER (breathless): "Gone."'))["warns"])
        sd = kl.replace("model: kling3_0", "model: seedance_2_5")
        assert not any("documented dialogue form" in w for w in L3(sd)["warns"]), "an unverified form never warns"
    print("  [PASS] v2.70 route per roster model (measured, unmeasured, with and without references); defect nouns warn "
          "outside [SUPPRESS] and [CONSTRAINTS]")
    _selftest_v271()


def _selftest_v271() -> None:
    """(v2.71.0, Wave 5 A3) The writer text agrees with the lint: the guardrail table's prompt column names no defect
    and quotes no "no X"; its noun column passes the [SUPPRESS] item rule; direction.md no longer says "write the
    negative"; --route names the nouns' block; [CONSTRAINTS] warns when misplaced, misused or a sentence."""
    import tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "..", "references", "ai-generation.md"), encoding="utf-8").read()
    assert "<!-- guardrails -->" in src and "<!-- /guardrails -->" in src, "the guardrail table lost its markers"
    tbl = src[src.index("<!-- guardrails -->"):src.index("<!-- /guardrails -->")]
    rows = [[c.strip() for c in l.strip().strip("|").split(" | ")] for l in tbl.splitlines()
            if l.startswith("| ") and not l.startswith("| Shot has") and not l.startswith("|---")]
    assert len(rows) >= 10 and all(len(r) == 4 for r in rows), [len(r) for r in rows]
    for r in rows:
        dm = DEFECT_NOUN_RE.search(r[2])
        assert not dm, ("prompt column names a defect", r[0][:40], dm.group(0))
        nm = NEG_SENTENCE_RE.search(r[2])
        assert not nm, ("prompt column carries a prohibition the lint warns on", r[0][:40], nm.group(0))
        for q in re.findall(r'"([^"]+)"', r[2]):
            assert not re.search(r"\b(no|not|never)\b", q, re.I), ("a quoted prompt line says no", r[0][:40], q)
        if r[3] != "—":
            assert not WATERMARK_RE.search(r[3]), ("watermark in a noun list", r[0][:40])
            # anatomy nouns may only stand in a † row ([SUPPRESS] only, never the [CONSTRAINTS] tail)
            assert r[3].startswith("†") or not CON_ANATOMY_RE.search(r[3]), ("anatomy in an unmarked noun list", r[0][:40])
            for it in [i.strip() for i in re.split(r"[,\n;]", r[3].lstrip("† ")) if i.strip()]:
                assert not re.match(r"^(no|not|never|avoid|without)\b", it, re.I) and len(it.split()) <= 6, \
                    ("a noun-list item the [SUPPRESS] rule refuses", r[0][:40], it)
    dr = open(os.path.join(here, "..", "references", "direction.md"), encoding="utf-8").read()
    # the prohibition pattern matches a whole "no X" (it once stopped after one letter, so "no head" never warned)
    assert NEG_SENTENCE_RE.search("smile stays; no head bobbing") and NEG_SENTENCE_RE.search("not move")
    assert NEG_SENTENCE_RE.search("no harsh light") and NEG_SENTENCE_RE.search("no people in the street")
    for _ok in ("no longer lit", "the camera, not the object", "the camera, not her hand", "no more than two",
                "not at all", "fast, no second thought", "warm, not sinister", "mouth closed, not smiling"):
        assert not NEG_SENTENCE_RE.search(_ok), _ok
    for _bad in ("no one else in frame", "no more head bobbing", "gaze not at the lens", "not in frame", "not too close",
                 "not even a blink", "not her face", "not once looks away"):
        assert NEG_SENTENCE_RE.search(_bad), _bad                    # real keep-out lines (build review 3, Grok)
    assert CAMERA_NEG_RE.sub(" ", "Slow push. No pan, no tilt.").strip(" .,") == "Slow push"
    assert not NEG_SENTENCE_RE.search(CAMERA_NEG_RE.sub(" ", "Slow push-in along the rows, 100mm. No pan, no tilt, no "
                                                               "roll, no rack focus."))
    # (build review 2, Grok) the templates and the scene fixture writers copy carry no prohibition the lint warns on
    # <placeholders> are the writer's instructions, replaced before anything is sent; the blocks the lint skips are skipped
    for _t in ("clip", "scene", "scene-file", "dna", "frame", "multishot", "family"):
        _bl = blocks_of(re.sub(r"(?s)<[^<>]*>", " ", re.sub(r"(?s)^---.*?---", "", TEMPLATES.get(_t, ""), count=1)))
        _skip = {"SUPPRESS", "CONSTRAINTS", "_lead", "CHARACTER"} | ({"REFERENCES", "CONSISTENCY", "WHERE", "SOUND"}
                                                                    if _t == "multishot" else set())
        _hits = [m.group(0) for k_, v_ in _bl.items() if k_ not in _skip
                 for m in NEG_SENTENCE_RE.finditer(NO_MUSIC_RE.sub(" ", v_))]
        assert not _hits, (_t, _hits)
    _fx = re.sub(r"(?s)^---.*?---", "", SCENE_FIXTURE, count=1)
    assert not [m.group(0) for m in NEG_SENTENCE_RE.finditer(NO_MUSIC_RE.sub(" ", _fx))], "SCENE_FIXTURE"
    assert "Write the negative" not in dr and "Write the stillness as a state" in dr
    _card = [l for l in dr.splitlines() if l.startswith(("FACE:", "GAZE:"))]
    assert _card and not any(NEG_SENTENCE_RE.search(l) for l in _card), _card       # the card writers copy
    _pc = open(os.path.join(here, "..", "references", "prompting-craft.md"), encoding="utf-8").read()
    _cb = [l for l in _pc.splitlines() if l.startswith("- **[CONSTRAINTS]**")]
    assert _cb and "defect nouns" not in _pc[_pc.index(_cb[0]):_pc.index(_cb[0]) + 400], "the Seedance block list sends anatomy"
    _sl = open(os.path.join(here, "..", "assets", "shotlist-template.md"), encoding="utf-8").read()
    assert "incl. the negative" not in _sl and "no head bobbing" not in _sl
    assert route("nano_banana_pro")["nouns"]["block"] == "CONSTRAINTS", "image models read prompt_limits too"
    for _t in ("clip", "frame", "scene", "multishot", "family"):                      # templates on no-field models
        _tb = TEMPLATES[_t]
        _m = re.search(r"^model:\s*(\S+)", _tb, re.M)
        if _m and noun_home(_m.group(1))["block"] == "CONSTRAINTS":
            assert "\n[SUPPRESS]" not in _tb and "\n[CONSTRAINTS]" in _tb, (_t, _m.group(1))
    assert route("seedance_2_5")["nouns"]["block"] == "CONSTRAINTS"
    assert route("kling3_0")["nouns"]["block"] == "SUPPRESS"
    assert route("no-such-model")["nouns"]["block"] == "SUPPRESS" and "check the take" in route("no-such-model")["nouns"]["why"]
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d_ in ("00-brief", "01-script/prompts", "02-startframes"):
            os.makedirs(os.path.join(job, d_))
        P = os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md")
        L = lambda t: (open(P, "w", encoding="utf-8").write(t), lint(P, job))[1]       # noqa: E731
        con = lambda w: [x for x in w if x.startswith("[CONSTRAINTS]")]                # noqa: E731
        tail = SCENE_FIXTURE.rstrip("\n") + "\n\n[CONSTRAINTS]\ntriptych, panel borders, modern signage, logo\n"
        assert not con(L(tail)["warns"]), con(L(tail)["warns"])
        assert not any("logo / brand mark" in x for x in L(tail)["warns"]), "a noun list's 'logo' is not a request"
        anat = tail.replace("triptych, panel borders, modern signage, logo", "extra fingers, warped grip")
        assert any("names anatomy" in x for x in con(L(anat)["warns"])), L(anat)["warns"]
        mid = SCENE_FIXTURE.replace("[POSITIVE LOCKS]", "[CONSTRAINTS]\nextra fingers\n\n[POSITIVE LOCKS]", 1)
        assert any("not the prompt's last block" in x for x in con(L(mid)["warns"])), L(mid)["warns"]
        sent = tail.replace("triptych, panel borders, modern signage, logo", "no triptych, panels")
        assert any("is a sentence" in x for x in con(L(sent)["warns"])), L(sent)["warns"]
        kl = tail.replace("model: seedance_2_5", "model: kling3_0")
        assert any("has a negative field" in x for x in con(L(kl)["warns"])), L(kl)["warns"]
        # (build review 2, Sonnet) the [CONSTRAINTS] anatomy list must not shadow ANATOMY_RE: the ECU skin check still fires
        ecu = SCENE_FIXTURE.replace("[CAMERA]\n", "[CAMERA]\nextreme close-up on her hands, nervous and tense. ", 1)
        assert ecu != SCENE_FIXTURE and any("smooth waxy CG skin" in x for x in L(ecu)["warns"]), L(ecu)["warns"]
        cam1 = SCENE_FIXTURE.replace("[CAMERA]\n", "[CAMERA]\nSlow push. No pan, no tilt. ", 1)
        assert not any(x.startswith("[CAMERA] carries a prohibition") for x in L(cam1)["warns"]), L(cam1)["warns"]
    print("  [PASS] v2.71 guardrail table agrees with the lint (prompt column positive, noun column a [SUPPRESS] list); "
          "--route names the nouns' block; [CONSTRAINTS] warns when not last, a sentence, or on a model with a negative field")


def _selftest_scene_file() -> None:
    """v2.49.0: the scene file and the project DNA — the shared blocks written once and pasted by the lint."""
    import tempfile
    fmt, body = split_front(SCENE_FIXTURE)
    bl = blocks_of(body)
    head = SCENE_FIXTURE.split("\n---", 1)[0]
    refs_txt = head[head.index("refs:"):]
    shared = ("ACTIVE REFERENCES", "LOCATION MAP", "LIGHTING", "COLOR", "AUDIO", "POSITIVE LOCKS")
    scene_file = ("---\nscene: S2\nmodel: seedance_2_5\naspect: 16:9\n" + refs_txt + "\n---\n" +
                  "\n\n".join(f"[{b}]\n{bl[b]}" for b in shared) + "\n")
    dna = "---\nproject: test\n---\n[STYLE]\n" + bl["STYLE"] + "\n\n[FORMAT MODE]\n" + bl["FORMAT MODE"] + "\n"
    shot_head = re.sub(r"(?ms)^refs:.*", "", head).rstrip() + "\nscene: S2\nsetup: A\n"
    own = [b for b in bl if b not in shared and b not in ("STYLE", "FORMAT MODE", "_lead")]
    shot = shot_head + "\n---\n" + "\n\n".join(f"[{b}]\n{bl[b]}" for b in own) + "\n"
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d_ in ("00-brief", "01-script/prompts", "01-script/scenes"):
            os.makedirs(os.path.join(job, d_))
        sd = os.path.join(job, "01-script", "scenes")
        open(os.path.join(sd, "S2.scene.md"), "w", encoding="utf-8").write(scene_file)
        open(os.path.join(sd, DNA_FILE), "w", encoding="utf-8").write(dna)
        P = os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md")
        open(P, "w", encoding="utf-8").write(shot)
        r = lint(P, job)
        assert r["ok"], r["fails"]
        sc = r["sidecar"]
        assert len(sc["refs"]) == 3 and sc.get("scene_sha") and sc.get("dna_sha"), sc
        assert bl["LOCATION MAP"].split("\n")[0][:40] in sc["prompt"] and bl["STYLE"][:30] in sc["prompt"]
        sha1 = sc["prompt_sha256"]
        # a second shot on the same setup with a different lens: the scene report refuses it
        P2 = os.path.join(job, "01-script", "prompts", "S5.clip.prompt.md")
        open(P2, "w", encoding="utf-8").write(shot.replace("shot: S4", "shot: S5").replace(
            bl["OPTICS"].split("\n")[0], "84 degrees field of view, about a 21 mm lens, 2 m from him."))
        rep = scene_report(job, "S2")
        assert not rep["ok"] and any("setup A" in f and "[OPTICS]" in f for f in rep["fails"]), rep
        open(P2, "w", encoding="utf-8").write(shot.replace("shot: S4", "shot: S5").replace("setup: A", "setup: B"))
        assert scene_report(job, "S2")["ok"], scene_report(job, "S2")
        # change the scene file: the same shot now lints to a different prompt (the gate refuses the old one)
        open(os.path.join(sd, "S2.scene.md"), "w", encoding="utf-8").write(
            scene_file.replace("[POSITIVE LOCKS]\n", "[POSITIVE LOCKS]\nThe stairwell door stays shut.\n"))
        assert lint(P, job)["sidecar"]["prompt_sha256"] != sha1
        # an override needs a reason, and replaces the shared block
        ov = shot.replace("setup: A\n", "setup: A\noverride: LIGHTING — the sign flickers off\n")
        open(P, "w", encoding="utf-8").write(ov)
        assert any("override: LIGHTING" in f for f in lint(P, job)["fails"])
        ov = shot.replace("setup: A\n", "setup: A\noverride: LIGHTING — the sign flickers off for good\n") + \
            "\n[LIGHTING]\nOnly the sky light remains, deep blue, from above.\n"
        open(P, "w", encoding="utf-8").write(ov)
        r = lint(P, job)
        assert r["ok"], r["fails"]
        assert "Only the sky light remains" in r["sidecar"]["prompt"] and bl["LIGHTING"][:30] not in r["sidecar"]["prompt"]
        # a missing scene file is named
        open(P, "w", encoding="utf-8").write(shot.replace("scene: S2", "scene: S9"))
        assert any("S9.scene.md does not exist" in f for f in lint(P, job)["fails"])
    print("  [PASS] v2.49 scene file + project DNA pasted per block, refs inherited in order, one setup = one lens, "
          "a changed scene file changes every shot's prompt, overrides need a reason")


def selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job"); os.makedirs(os.path.join(job, "00-brief"))
        os.makedirs(os.path.join(job, "01-script", "prompts")); os.makedirs(os.path.join(job, "02-startframes"))
        open(os.path.join(job, "02-startframes", "S3_hero_v2.png"), "wb").write(b"\x89PNG fake")
        good = TEMPLATES["clip"].replace("<opening pose / framing — the frame as approved; the PERSON leads, never the material>", "seated, hands on the table") \
            .replace("<the one movement / gesture / expression change, mid-action verbs with tempo and force>", "leaning in, right hand lifting the glass") \
            .replace("<the aftermath the clip settles into — what the objects do BECAUSE of that force>", "glass held still at chest height, eyes on the camera") \
            .replace("<why they do it, as an attitude, and the manner it forces — \"done with sugar: fast, no second thought\">",
                     "she has made up her mind: quick and sure, in one move") \
            .replace("<one behaviour: e.g. \"locked-off, eye level\" or \"slow push in, 50mm\">", "locked-off, eye level") \
            .replace("<from → to>", "skeptical → curious") \
            .replace("<what they react to, and when — or \"none — she starts it\">", "the host's question, before the clip") \
            .replace("<who or what they play towards, and where>", "the viewer, through the lens") \
            .replace("<the before, held>, then <the one change>", "still, then a half-smile") \
            .replace("BODY:     <MS or wider: one bundle in plain words — delete this line at MCU and closer>\n", "") \
            .replace("<what the face does, said as a state: \"the head stays still\">", "eyebrows lift once") \
            .replace("<where the eyes are, and when they move>", "on the lens") \
            .replace("<Path B only: delivery notes — pace, warmth; the words come from line:>", "warm, unhurried") \
            .replace("payload:                  # REQUIRED.",
                     "payload: she goes from holding the glass to committing to the answer.  #")
        p = os.path.join(job, "01-script", "prompts", "S3.clip.prompt.md")
        open(p, "w", encoding="utf-8").write(good)
        r = lint(p)
        assert r["ok"], r["fails"]
        # (v2.71.0) minimax_h3 has no negative field: the template's nouns are [CONSTRAINTS], sent at the prompt's end
        assert r["prompt"].rstrip().endswith("morphing background figures") and not r["sidecar"].get("negative")
        assert not any(w.startswith("[CONSTRAINTS]") for w in r["warns"]), r["warns"]
        # object permanence (a supplement ad job): a toss with no landing refuses; the landing, or a punch, passes
        open(p, "w", encoding="utf-8").write(good.replace("right hand lifting the glass", "right hand tossing the keys in passing"))
        assert any("no landing" in f for f in lint(p)["fails"]), lint(p)["fails"]
        open(p, "w", encoding="utf-8").write(good.replace("right hand lifting the glass",
                                                          "fingers open, the keys drop straight down onto the counter below"))
        assert not any("no landing" in f for f in lint(p)["fails"])
        open(p, "w", encoding="utf-8").write(good.replace("right hand lifting the glass", "she throws a glance at the door"))
        assert not any("no landing" in f for f in lint(p)["fails"])
        open(p, "w", encoding="utf-8").write(good)
        bad = good.replace("[MOTION]", "[ENVIRONMENT]\nsunny kitchen\n\n[MOTION]") \
            .replace("leaning in", "begins to lean in").replace("model: minimax_h3", "model: wan2_7")
        open(p, "w", encoding="utf-8").write(bad)
        r = lint(p)
        assert not r["ok"]
        joined = " ".join(r["fails"])
        assert "[ENVIRONMENT] in an i2v" in joined and "temporal hedge" in joined and "roster" in joined, r["fails"]
        fr = TEMPLATES["frame"].replace("<who/what, pose, action as a mid-action verb, wardrobe stated verbatim>",
                                        "a woman in a green apron pouring olive oil, mid-pour") \
            .replace("<the fixed character block, pasted byte-for-byte across every frame>", "green apron, silver hair, tortoiseshell glasses") \
            .replace("<location, props, season, time of day — concrete and authentic>", "stone kitchen, late summer, 10am") \
            .replace(TEMPLATES["frame"].split("[LIGHTING]\n")[1].split("\n\n")[0],
                     "sun through the left window, hard, long shadows; loop key") \
            .replace("<lens mm, height, angle: \"50mm, eye level, slight low angle\">", "50mm, eye level") \
            .replace("<phone-real or cinema-real, film stock or sensor — physical language, no names>", "phone-real, slight rolling shutter")
        p2 = os.path.join(job, "01-script", "prompts", "S3.frame.prompt.md")
        # a character frame with no reference must FAIL — identity is never text alone
        import re as _re
        norefs = _re.sub(r"(?ms)^refs:.*?(?=^---$)", "", fr)
        open(p2, "w", encoding="utf-8").write(norefs)
        assert any("no `refs:`" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        REFS = "refs:\n  - role: image, what: character, value: media_hero_01\n"
        fr_r = norefs.replace("---\n[SUBJECT]", REFS + "---\n[SUBJECT]", 1)
        open(p2, "w", encoding="utf-8").write(fr_r)
        r = lint(p2)
        assert r["ok"], r["fails"]
        assert r["sidecar"]["ref_plan"][0]["what"] == "character"
        assert any("no locked character block" in w for w in r["warns"])
        # ⚡ THE START FRAME IS MADE FOR ITS MOTION (2026-10-26): an action shot's frame names the
        # anticipation peak and the direction of travel; a dialogue clip's frame is not asked
        open(os.path.join(job, "01-script", "prompts", "S5.clip.prompt.md"), "w", encoding="utf-8").write(
            "---\nshot: S5\nkind: clip\ntype: broll\n---\n[MOTION]\nINTENT: done with sugar: fast\n"
            "START: her hand grabs the jar\nMID: she flips it over the bin\nEND: she turns away\n")
        p5 = os.path.join(job, "01-script", "prompts", "S5.frame.prompt.md")
        f5 = fr_r.replace("shot: S3", "shot: S5", 1)
        open(p5, "w", encoding="utf-8").write(f5)
        w5 = lint(p5)["warns"]
        assert any("no `caught:`" in w for w in w5) and any("no `travel:`" in w for w in w5), w5
        open(p5, "w", encoding="utf-8").write(f5.replace("a woman in a green apron pouring olive oil, mid-pour",
                                                          "a woman in a green apron, her hand resting beside the jar"))
        assert any("reads as a rest pose" in w for w in lint(p5)["warns"])
        open(p5, "w", encoding="utf-8").write(f5.replace("caught:   ", "caught: wrist cocked, the jar tipped over the bin  ", 1)
                                                .replace("travel:   ", "travel: down-left into the bin  ", 1))
        w5 = lint(p5)["warns"]
        assert not any("`caught:`" in w or "`travel:`" in w for w in w5), w5
        assert not any("`caught:`" in w for w in r["warns"]), "the S3 sibling is a dialogue clip: not asked"
        # ⛔ IS THE WRITING FINISHED? Four checks adopted from Higgsfield's own Ad Multiplier
        # prompt validator [SECONDARY · ad-multiplier v1.4 · 2026-09-17], each pinned in BOTH
        # directions — the bad form fails, and a plausible innocent phrasing does not. The
        # false-positive half is the half that gets skipped and the half that makes a lint
        # something people route around.
        for _inject, _needle in (
                ("[HERO NAME] steps into the light", "unresolved placeholder"),
                ("she holds either the mug or the glass", "unresolved alternative"),
                ("matching https://cdn.example.com/ref/42.png", "raw id or URL"),
                ("a different hairstyle from the original woman", "by comparison"),
                ("her posture unlike the original", "by comparison")):
            _b = fr_r.replace("stone kitchen, late summer, 10am",
                              "stone kitchen, late summer, 10am. " + _inject)
            open(p2, "w", encoding="utf-8").write(_b)
            assert any(_needle in f for f in lint(p2)["fails"]), (_inject, lint(p2)["fails"])
        # ⛔ THE STATE CHANGE AND THE NEGATIVE SCOPE (2026-09-18), both from the Higgsfield
        # production corpus. The state check must fire on a change DEFENDED WITH WORDS and go
        # quiet once the AFTER state exists as its own asset — which is the corpus author's own
        # fix after four sentences of defence failed. The false-positive half matters more here
        # than usual: "a torn shirt" as a starting condition is not a change, and a lint that
        # cannot tell those apart is a lint people stop reading.
        _chg = fr_r.replace("stone kitchen, late summer, 10am",
                            "stone kitchen, late summer, 10am. Her apron tears on the hook and the "
                            "torn state is permanent and irreversible from here on")
        open(p2, "w", encoding="utf-8").write(_chg)
        assert any("changes a state mid-clip" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        _fixed = _chg.replace("refs:\n", "refs:\n  - role: image, what: wardrobe, "
                              "value: media_torn_01, state: after, not: sheet background\n", 1)
        open(p2, "w", encoding="utf-8").write(_fixed)
        assert not any("changes a state mid-clip" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        for _start in ("she wears a torn linen apron", "she tears open the envelope and reads it"):
            _g = fr_r.replace("stone kitchen, late summer, 10am",
                              "stone kitchen, late summer, 10am. " + _start)
            open(p2, "w", encoding="utf-8").write(_g)
            assert not any("changes a state mid-clip" in f for f in lint(p2)["fails"]), \
                (_start, lint(p2)["fails"])
        # ⛔ THE THREE THINGS A LIVE PRODUCTION SUPPLIES FOR FREE (script-craft.md §6b). These
        # landed as prose first, which was the weak answer: an actor invents the pause, a stunt
        # performer actually misses, a director names the break — none of that exists here, so all
        # three are ABSENCES, and an absence is exactly what a lint can see.
        #
        # A · AIR. The old check asked only whether a line FIT, so a 6s clip carrying 5.8s of
        #     speech passed — the "lands in one breath" failure, in code.
        _air = _re.sub(r"(?m)^line:.*$",
                       'line: "The guys believed in me and a whole country believed and I missed"', good)
        open(p, "w", encoding="utf-8").write(_air)
        assert any("of air" in w for w in lint(p)["warns"]), lint(p)["warns"]
        _air_ok = _re.sub(r"(?m)^line:.*$", 'line: "A whole country believed."', good)
        open(p, "w", encoding="utf-8").write(_air_ok)
        assert not any("of air" in w for w in lint(p)["warns"]), lint(p)["warns"]
        # B · AN EMOTION IS NOT A DIRECTION. Replace the performance card's body with pure affect.
        _emo = _re.sub(r"(?ms)^\[PERFORMANCE\]\n.*?(?=^\[)", "[PERFORMANCE]\nSTATE: guilty → "
                       "devastated\nHe is guilty and devastated, deeply emotional.\n\n", good)
        open(p, "w", encoding="utf-8").write(_emo)
        assert any("names an emotion" in w for w in lint(p)["warns"]), lint(p)["warns"]
        _emo_ok = _emo.replace("He is guilty and devastated, deeply emotional.",
                               "The masseter tightens, one delayed swallow travels the throat, the "
                               "pitch drops on the last word.")
        open(p, "w", encoding="utf-8").write(_emo_ok)
        assert not any("names an emotion" in w for w in lint(p)["warns"]), lint(p)["warns"]
        # D · CARD v2 (2026-09-30, acting-for-the-model.md §7). Six warnings, each pinned BOTH ways:
        # the bad card warns, and the nearest innocent phrasing does not — a lint that fires on
        # "camera-left" or on "eyes go wide" is a lint people stop reading.
        def _w(txt):
            open(p, "w", encoding="utf-8").write(txt)
            return " ".join(lint(p)["warns"])
        _stim_line = "STIMULUS: the host's question, before the clip\n"
        assert _stim_line in good, "fixture drift: the v2 STIMULUS line moved"
        _react = good.replace("type: dialogue", "type: reaction", 1)
        assert "no STIMULUS" in _w(_react.replace(_stim_line, "")), "a reaction with no cause must warn"
        assert "no STIMULUS" not in _w(_react)
        _tgt_line = "TARGET:   the viewer, through the lens\n"
        _vague = good.replace("GAZE:     on the lens", "GAZE:     into the distance")
        assert "points nowhere" in _w(_vague.replace(_tgt_line, "")), "a vague gaze with no target must warn"
        assert "points nowhere" not in _w(_vague), "the same gaze WITH a target is a choice"
        assert "two changes" in _w(good.replace("still, then a half-smile", "still, then a half-smile, then a laugh"))
        assert "two changes" not in _w(good)
        _ms = good.replace("locked-off, eye level", "locked-off, eye level, medium shot")
        assert "no BODY" in _w(_ms), "an MS with no BODY must warn"
        assert "no BODY" not in _w(_ms.replace("GAZE:", "BODY:     weight forward, hands still\nGAZE:", 1))
        assert "no BODY" not in _w(good.replace("leaning in, right hand lifting the glass",
                                                "leaning in, eyes going wide")), "'wide' in MOTION is not a shot size"
        _low = good.replace("locked-off, eye level", "locked-off, low angle")
        assert "gaze is on the lens" in _w(_low), "direct address from below must warn"
        assert "gaze is on the lens" not in _w(_low.replace("GAZE:     on the lens", "GAZE:     on the guest, camera-left")), \
            "'camera-left' is a direction, not direct address"
        assert "intensity superlative" in _w(good.replace("eyebrows lift once", "extremely shocked, eyebrows lift"))
        assert "intensity superlative" not in _w(good.replace("eyebrows lift once", "amazed, eyebrows lift once"))
        open(p, "w", encoding="utf-8").write(good)
        # C · A WITHHELD OUTCOME NEEDS A MECHANISM, because the model is obliging.
        _wh = fr_r.replace("stone kitchen, late summer, 10am",
                           "stone kitchen, late summer, 10am. She reaches and falls short, fingers "
                           "just out of reach")
        open(p2, "w", encoding="utf-8").write(_wh)
        assert any("NOT happening" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        _wh_ok = _wh.replace("fingers just out of reach",
                             "her reach covers two metres and the shelf lies three metres out")
        open(p2, "w", encoding="utf-8").write(_wh_ok)
        assert not any("NOT happening" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        open(p2, "w", encoding="utf-8").write(fr_r)
        open(p, "w", encoding="utf-8").write(good)

        # ⛔ THREE RULES FROM REJECTED TAKES (2026-09-18, practitioner corpus). Each one is a defect
        # somebody shot, looked at, and threw away — which is better evidence than a guide.
        _whip = fr_r.replace("stone kitchen, late summer, 10am",
                             "stone kitchen, late summer, 10am. The camera whip-pans from a medium "
                             "shot of her across to a close-up of him")
        open(p2, "w", encoding="utf-8").write(_whip)
        assert any("is not a whip pan" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        _whip_ok = _whip.replace("from a medium shot of her across to a close-up of him",
                                 "from a close-up of her across to a close-up of him")
        open(p2, "w", encoding="utf-8").write(_whip_ok)
        assert not any("is not a whip pan" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        _txt = fr_r.replace("stone kitchen, late summer, 10am",
                            "stone kitchen, late summer, 10am. She writes something in the "
                            "notebook, the lettering visible to camera")
        open(p2, "w", encoding="utf-8").write(_txt)
        assert any("never says WHAT it says" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        _txt_ok = _txt.replace("She writes something in the notebook, the lettering visible to "
                               "camera", 'the lettering reads "SORRY - see you at eight"')
        open(p2, "w", encoding="utf-8").write(_txt_ok)
        assert not any("never says WHAT it says" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        # writing as an ACTION asks for nothing to be legible and needs no words
        _act = fr_r.replace("stone kitchen, late summer, 10am",
                            "stone kitchen, late summer, 10am. He writes in his journal a moment")
        open(p2, "w", encoding="utf-8").write(_act)
        assert not any("never says WHAT" in f or "letters never resolve" in f
                       for f in lint(p2)["fails"]), lint(p2)["fails"]
        open(p2, "w", encoding="utf-8").write(fr_r)
        # the negative scope: a character reference must say what it does NOT bring
        open(p2, "w", encoding="utf-8").write(fr_r)
        assert any("declares no `not:`" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        _scoped = fr_r.replace("what: character, value: media_hero_01",
                               "what: character, value: media_hero_01, not: sheet background, "
                               "panel layout, studio lighting")
        open(p2, "w", encoding="utf-8").write(_scoped)
        assert not any("declares no `not:`" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        open(p2, "w", encoding="utf-8").write(fr_r)
        for _innocent in ("light falls differently from the window each morning",
                          "a colour distinct from the wall behind her",
                          "she moves into a different room"):
            _g = fr_r.replace("stone kitchen, late summer, 10am",
                              "stone kitchen, late summer, 10am. " + _innocent)
            open(p2, "w", encoding="utf-8").write(_g)
            assert not any("by comparison" in f or "unresolved" in f for f in lint(p2)["fails"]), \
                (_innocent, lint(p2)["fails"])
        open(p2, "w", encoding="utf-8").write(fr_r)
        # ⛔ A KELVIN NUMBER IS NOT A SOURCE. The old regex accepted `\d{4}K`, so "5200K, moody"
        # passed while naming no object the model could render — and a Kelvin number is decoration
        # in a prompt anyway (cinematography-craft.md §7.0). Pin both directions.
        kelvin_only = fr_r.replace("sun through the left window, hard, long shadows; loop key",
                                   "5200K, moody, cinematic")
        open(p2, "w", encoding="utf-8").write(kelvin_only)
        assert any("names no SOURCE" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        lamp = fr_r.replace("sun through the left window, hard, long shadows; loop key",
                            "a lamp on the counter, switched on, warm, camera-left")
        open(p2, "w", encoding="utf-8").write(lamp)
        assert not any("names no SOURCE" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        # and the safe-zone note the template ships is the MEASURED box, not "top 35%"
        assert "y=15-65%" in TEMPLATES["frame"] and "top 35%" not in TEMPLATES["frame"]
        # ⛔ A FORBIDDEN MOVE IS NOT A REQUESTED MOVE. "Slow push. No pan, no tilt, no roll." names
        # ONE move and rules out three; the old counter read four and FAILed the prompt for being
        # explicit. Pin both directions — the negation is ignored, a real second move still FAILs.
        clip_ok = TEMPLATES["clip"]
        def _cam(body):
            t = clip_ok.replace('<one behaviour: e.g. "locked-off, eye level" or "slow push in, 50mm">', body)
            t = t.replace("<opening pose / framing — the frame as approved>", "the frame as approved") \
                 .replace("<the one movement / gesture / expression change, mid-action verbs>", "the hand withdraws") \
                 .replace("<the aftermath the clip settles into — where motion comes to rest>", "the tag lies flat")
            pc = os.path.join(job, "01-script", "prompts", "S9.clip.prompt.md")
            open(pc, "w", encoding="utf-8").write(t)
            return lint(pc)
        r_neg = _cam("Slow push-in along the rows, 100mm. No pan, no tilt, no roll, no rack focus.")
        assert not any("names 2 moves" in f or "names 3 moves" in f or "names 4 moves" in f
                       for f in r_neg["fails"]), r_neg["fails"]
        r_two = _cam("Slow push-in along the rows, then pan right, 100mm.")
        assert any("names 2 moves" in f for f in r_two["fails"]), r_two["fails"]
        # ⛔ THE CITATION-FORM GAP. Every phrasing below matched NOTHING before 2026-09-08, so the
        # one-move rule did not apply to any prompt written in ordinary English. Each pair is
        # (the phrasing, the class it must resolve to) — the dictionary form and the one people type.
        for phrase, want in [("Slow push along the rows.", "dolly"),
                             ("The camera tracks left.", "dolly"),
                             ("Trucking right alongside her.", "dolly"),
                             ("Crab left past the counter.", "dolly"),
                             ("The camera arcs around her.", "orbit"),
                             ("Pedestal up to the shelf.", "crane"),
                             ("Panning right across the room.", "pan"),
                             ("Tilts up the wall.", "tilt"),
                             ("The camera rolls 8 degrees.", "roll"),
                             ("Rack focus to the tag.", "rack")]:
            r1 = _cam(phrase)
            got = {c for c, pats in CAMERA_CLASSES.items()
                   if any(re.search(pp, phrase, re.I) for pp in pats)}
            assert want in got, (phrase, got)
            assert not any("names" in f and "moves" in f for f in r1["fails"]), (phrase, r1["fails"])
        # ⛔ ROLL IS A MOVE. It was not a class at all, so "an 8-degree roll while pushing in" — two
        # simultaneous moves, the documented warping case — passed silently. It must not.
        r_roll = _cam("Dolly forward combined with an 8-degree roll.")
        assert any("names 2 moves" in f for f in r_roll["fails"]), r_roll["fails"]
        # "rolling shutter" is a sensor artifact, not a camera move
        assert not any(re.search(pp, "rolling shutter, phone-real", re.I)
                       for pp in CAMERA_CLASSES["roll"])
        # ⛔ A DOLLY ZOOM is ONE named move and it is UNOBTAINABLE. It must be refused on its own
        # terms, not miscounted as "dolly + zoom = two moves" — the writer knows it is two words.
        r_dz = _cam("Slow dolly zoom on her face, 40mm.")
        assert any("not obtainable" in f for f in r_dz["fails"]), r_dz["fails"]
        assert not any("names 2 moves" in f for f in r_dz["fails"]), r_dz["fails"]
        # handheld is TEXTURE, not path: it does not consume the one-move budget, and it warns
        r_hh = _cam("Handheld, slow push-in, 35mm.")
        assert not any("names 2 moves" in f for f in r_hh["fails"]), r_hh["fails"]
        assert any("GIMBAL" in w for w in r_hh["warns"]), r_hh["warns"]
        # ⛔ the 1080p floor reaches FRAMES, not only clips — the frame sets the picture
        low = fr_r.replace("resolution: 2k", "resolution: 720p")
        open(p2, "w", encoding="utf-8").write(low)
        assert any("under the 1080p floor" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        # ...and a frame that declares no resolution at all cannot be checked, so it says so
        nores = _re.sub(r"(?m)^resolution: 2k.*$", "", fr_r)
        open(p2, "w", encoding="utf-8").write(nores)
        assert any("quality floor is unenforceable" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        open(p2, "w", encoding="utf-8").write(fr_r)
        # two references for one attribute must FAIL
        dup = fr_r.replace(REFS, REFS + "  - role: image, what: character, value: media_hero_02\n")
        open(p2, "w", encoding="utf-8").write(dup)
        assert any("both carry" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        # a reference with no attribute must FAIL
        nowhat = fr_r.replace("what: character, value: media_hero_01", "value: media_hero_01")
        open(p2, "w", encoding="utf-8").write(nowhat)
        assert any("no `what:`" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        # a file reference that was never sourced must FAIL
        missing = fr_r.replace(REFS, "refs:\n  - role: image, what: wardrobe, file: _reference/wardrobe/apron.jpg\n")
        open(p2, "w", encoding="utf-8").write(missing)
        assert any("not found" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        # ⛔ an asset SWAPPED after its provenance was recorded must FAIL — the clearance on file
        # was answered against a different picture
        # (set up further down, once a cleared file + sidecar exist)
        # sourced but no provenance sidecar must FAIL
        os.makedirs(os.path.join(job, "_reference", "wardrobe"))
        ap_ = os.path.join(job, "_reference", "wardrobe", "apron.jpg")
        open(ap_, "wb").write(b"\xff\xd8 fake jpeg")
        assert any("no provenance sidecar" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        # an UNCLEARED asset must FAIL unless it is marked reference-only
        json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                   "clearance": "NOT CLEARED — per-asset checks below are outstanding"},
                  open(ap_ + ".json", "w"))
        assert any("NOT CLEARED" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        refonly = missing.replace("file: _reference/wardrobe/apron.jpg",
                                  "file: _reference/wardrobe/apron.jpg, use: reference-only")
        open(p2, "w", encoding="utf-8").write(refonly)
        r = lint(p2)
        # …and the prompt must not re-describe what that reference carries ("apron" is wardrobe)
        assert any("re-describes it" in f for f in r["fails"]), r["fails"]
        clean = refonly.replace("a woman in a green apron pouring olive oil, mid-pour",
                                "the host pouring olive oil, mid-pour")
        open(p2, "w", encoding="utf-8").write(clean)
        r = lint(p2)
        assert r["ok"], r["fails"]
        # a sidecar with no sha256 cannot prove the file is the one that was cleared — it WARNS
        assert any("no sha256" in w for w in r["warns"]), r["warns"]
        # ⛔ with a hash recorded, the same file passes...
        json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                   "clearance": "NOT CLEARED — per-asset checks below are outstanding",
                   "sha256": sha256_file(ap_)}, open(ap_ + ".json", "w"))
        r = lint(p2)
        assert r["ok"] and not any("no sha256" in w for w in r["warns"]), (r["fails"], r["warns"])
        # ...and the SAME sidecar over a SWAPPED file must FAIL: the clearance on record was
        # answered against a different picture. Nothing on the enforced path checked this until
        # 2026-09-07, while stock-sourcing.md §9 claimed it did.
        open(ap_, "wb").write(b"\xff\xd8 a different jpeg entirely")
        r = lint(p2)
        assert any("has CHANGED since its provenance" in f for f in r["fails"]), r["fails"]
        json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                   "clearance": "NOT CLEARED — per-asset checks below are outstanding",
                   "sha256": sha256_file(ap_)}, open(ap_ + ".json", "w"))
        assert lint(p2)["ok"], lint(p2)["fails"]
        open(p2, "w", encoding="utf-8").write(fr_r.replace("mid-pour", "mid-pour, stressed, in the style of Roger Deakins"))
        r = lint(p2); j = " ".join(r["fails"])
        assert "negative emotional state" in j and "style-by-name" in j, r["fails"]
        # --- LENGTH and DENSITY -------------------------------------------------------------
        # A demand is a clause carrying content; a sourced reference removes one.
        assert demands_of("a baker slides a tray forward") == 1
        assert demands_of("a baker slides a tray, flour on the counter, a window behind") == 3
        assert demands_of("") == 0 and demands_of(", , .") == 0
        d = density_report({"SUBJECT": "a baker, a tray, a window"},
                           [{"what": "wardrobe", "file": "x.jpg"}, {"what": "prop", "value": "id"}])
        assert d["demands_raw"] == 3 and d["references_credited"] == 2 and d["demands"] == 1, d
        # density is a RATE, so it is scale-invariant — the same prose twice over scores the same
        one = density_report({"SUBJECT": "a baker, a tray, a window"}, [])
        twice = density_report({"SUBJECT": "a baker, a tray, a window, a baker, a tray, a window"}, [])
        assert one["per_100_words"] == twice["per_100_words"], (one, twice)
        # and the two failure modes stay separable
        listy = density_report({"E": ", ".join(f"a thing{i}" for i in range(1, 34))}, [])
        runon = density_report({"E": " ".join(f"detail{i} of the room" for i in range(1, 90))}, [])
        assert listy["per_100_words"] > DENSITY_PER_100_WARN, listy
        assert runon["per_100_words"] < DENSITY_PER_100_WARN, runon
        # a declared-but-unsourced slot is NOT a credit — it removes nothing yet
        d2 = density_report({"SUBJECT": "a baker, a tray, a window"},
                            [{"what": "wardrobe", "need": "white apron"}])
        assert d2["references_credited"] == 0 and d2["demands"] == 3, d2

        base = fr_r.replace("shot: S3", "shot: S9")
        thin = lint_str(base, td, "S9.frame.prompt.md")
        assert any("well under the measured band" in w for w in thin["warns"]), thin["warns"]
        assert not any("above the measured band" in w for w in thin["warns"])
        # ⛔ the band is a FRAME rule — a clip carries motion only, so the floor must not push a
        # writer to pad the very thing the i2v fork exists to keep out
        cl_ok = ("---\nshot: S9\nkind: clip\ntype: broll\nmodel: kling3_0\nresolution: 4k\n"
                 "duration: 5\naspect: 9:16\nstart_frame: 02-startframes/S9.png\n"
                 "function: establish the room\n"
                 "payload: the bench is now occupied and the room has someone in it\n---\n"
                 "[MOTION]\nSTART: tray level at hip height\nMID: the step lands\n"
                 "END: tray set down on the bench\n\n[CAMERA]\nlocked-off, chest height\n\n"
                 "[SUPPRESS]\nextra hands, text\n")
        clip_thin = lint_str(cl_ok, td, "S9.clip.prompt.md")
        assert not any("measured band" in w for w in clip_thin["warns"]), clip_thin["warns"]
        # ⛔ CLIP LENGTH FROM THE CUT (2026-10-26). No `cut:` → the default is named; a clip shorter than
        # lead-in + cut FAILS; no room for the handle WARNS; far longer than needed WARNS.
        assert any("`cut:` missing" in w for w in clip_thin["warns"]), clip_thin["warns"]
        assert clip_length_need(2.0, 1.0, 1.0) == 4 and clip_length_need(4.5, 0.0, 1.0) == 6
        assert clip_length_need(0.5, 0.0, 1.0, 5) == 5, "the model's minimum lifts a short need"
        _len = lambda d, extra: lint_str(cl_ok.replace("duration: 5\n", f"duration: {d}\n{extra}"), td,
                                         "S9.clip.prompt.md")
        r = _len(5, "cut: 2\n")
        assert not any("cut:" in w or "past the" in w or "handle" in w for w in r["warns"]) and \
            not any("cannot cover" in f for f in r["fails"]), (r["warns"], r["fails"])
        assert any("cannot cover lead-in 1s + 4.5s" in f and "generate 7 s" in f
                   for f in _len(5, "cut: 4.5\n")["fails"]), "5 s cannot hold a 4.5 s shot after its settle"
        assert any("leaves no 1s handle" in w for w in _len(5, "cut: 3.5\n")["warns"])
        assert not any("handle" in w for w in _len(5, "cut: 3.5\nhandle: 0\n")["warns"]), "handle: 0 = hard cuts"
        assert any("past the 3 s this shot needs" in w for w in _len(10, "cut: 1\n")["warns"]), \
            "10 s for a 1 s insert buys a dead front"
        # ⚡ INTENT (2026-10-26): the person leads, the material is the consequence, the manner is named
        _mo = lambda body: lint_str(re.sub(r"(?ms)^\[MOTION\]\n.*?(?=^\[CAMERA\])", "[MOTION]\n" + body + "\n\n",
                                           cl_ok.replace("duration: 5\n", "duration: 5\ncut: 3\n")),
                                    td, "S9.clip.prompt.md")["warns"]
        wb = _mo("START: the sugar jar in her hand over the bin\nMID: the sugar pours out slowly in a stream\n"
                 "END: the last grains settle in the bin, her hand still")
        assert any("no `INTENT:` line" in w for w in wb), wb
        assert any("MID: leads with 'the sugar'" in w for w in wb), wb
        assert not any("START: leads with" in w for w in wb), "'the sugar jar' is the container, not the material"
        assert any("moves only slowly and evenly" in w for w in wb), wb
        wg = _mo("INTENT: done with sugar for good: she gets rid of it fast, no second thought\n"
                 "START: her hand grabs the sugar jar off the counter without looking\n"
                 "MID: in one quick motion she flips it over the bin and shakes it twice, hard; the sugar drops in a clump\n"
                 "END: she sets the empty jar down with a tap and turns away, a few grains still falling")
        assert not any(k in w for w in wg for k in ("INTENT", "leads with", "slowly and evenly", "says why")), wg
        wn = _mo("START: capsules sit in a glass dish\nMID: the capsules tumble and spread\nEND: they come to rest")
        assert not any(k in w for w in wn for k in ("INTENT", "leads with")), "no person, no intent rule"
        _ob = lint_str(cl_ok.replace("duration: 5\n", "duration: 5\ncut: 3\nobstacle: the lid sticks\n")
                       .replace("function: establish the room", "function: proof that the capsules are easy to take"),
                       td, "S9.clip.prompt.md")["warns"]
        assert any("`obstacle:` on a shot that proves a claim" in w for w in _ob), _ob
        assert not any("`obstacle:`" in w for w in lint_str(cl_ok.replace("duration: 5\n",
                       "duration: 5\ncut: 3\nobstacle: the lid sticks\n"), td, "S9.clip.prompt.md")["warns"])
        # shot-handoff.md §4b: motion planned for the cut
        _ho = lambda extra, end=None: lint_str(
            (cl_ok if end is None else cl_ok.replace("END: tray set down on the bench", f"END: {end}"))
            .replace("duration: 5\n", "duration: 5\ncut: 3\n" + extra), td, "S9.clip.prompt.md")["warns"]
        assert any("has no `exit:`" in w for w in _ho("join: motion-match\n")), "a motion join with no exit"
        # (3.2.0) the pre-lap field
        assert parse_prelap("0.5s, door, side=right") == ({"lead_s": 0.5, "event": "door", "side": "right"}, None)
        assert parse_prelap("2s, door")[0] is None and parse_prelap("door")[0] is None and parse_prelap("0.5")[0] is None
        assert parse_prelap("0.5s, door, side=up")[0] is None
        assert parse_prelap("0.25s, E2")[0] and parse_prelap("1s, knock, side=off-left")[0]["side"] == "off-left"
        assert any("`prelap:" in w for w in _ho("prelap: 3s, door\n")), "a lead outside 0.25–1 s warns"
        assert not any("`prelap:" in w for w in _ho("prelap: 0.5s, door\n")), "a good pre-lap is quiet"
        assert not any("`exit:`" in w or "screen direction" in w
                       for w in _ho("join: motion-match\nexit: right, the tray leaving frame\n",
                                    "the tray still sliding right as the clip ends")), "a planned hand-off lints clean"
        assert any("names no screen direction" in w for w in _ho("exit: with the tray\n")), "an exit with no direction"
        assert any("END line settles" in w for w in _ho("join: match-on-action\nexit: right\n")), \
            "a motion hand-off whose END comes to rest"
        assert not any("exit" in w.lower() for w in _ho("join: flip\n")), "a flip needs no exit"
        assert not any("`track:" in w for w in _ho("track: jar=0.42,0.55,0.12,0.20; the cup @ 0.1,0.1,0.2,0.2\n"))
        assert any("`track: jar" in w for w in _ho("track: jar at the left\n")), "a track with no box"
        assert any("`track: jar" in w for w in _ho("track: jar=1.4,0.5,0.1,0.1\n")), "a box off the frame"
        assert not any("`sfx:" in w for w in _ho("sfx: count=3, surface=wet, space=kitchen, hero=jar\n"))
        assert any("`sfx: surface=slimy`" in w for w in _ho("sfx: surface=slimy\n")), "an sfx value off its list"
        assert any("`sfx: count=three`" in w for w in _ho("sfx: count=three\n")), "a count that is not a number"
        _rp = lambda extra: lint_str(cl_ok.replace("duration: 5\n", "duration: 5\ncut: 3\n" + extra), td, "S9.clip.prompt.md")
        assert not [f for f in _rp("ramp: kind=slow, speed=40, trigger=2.1, reveal=the sugar hanging in the air, sfx=whoosh-down\n")["fails"]
                    if "ramp" in f], "a planned slow-down with its reveal and cue"
        assert any("115–150" in f for f in _rp("ramp: kind=burst, speed=200, trigger=1, sfx=hit\n")["fails"]), "a burst over 150 %"
        assert any("no `reveal=`" in f for f in _rp("ramp: kind=slow, speed=40, trigger=1, sfx=hit\n")["fails"]), "a slow-down with no reveal"
        assert any("no `sfx=`" in f for f in _rp("ramp: kind=burst, speed=130, trigger=1\n")["fails"]), "a ramp with no cue"
        assert any("speaking or reacting" in f for f in _rp("ramp: kind=slow, speed=40, trigger=1, reveal=x, sfx=y\ngrade: talking_head\n")["fails"]), \
            "a ramp on a talking head"
        # (v2.48.0, project switches speed-conform and music-led) off → refused as before; on → lifted, named; on but
        # outside what the switch allows → still refused
        _swj = os.path.join(td, "swjob")
        os.makedirs(os.path.join(_swj, "00-brief")); os.makedirs(os.path.join(_swj, "01-script", "prompts"))
        _swp = os.path.join(_swj, "01-script", "prompts", "S9.clip.prompt.md")

        def _sw(extra):
            open(_swp, "w", encoding="utf-8").write(cl_ok.replace("duration: 5\n", "duration: 5\ncut: 3\n" + extra))
            _r = lint(_swp, _swj)
            return [f for f in _r["fails"] if "ramp" in f], _r["warns"]
        _f, _w = _sw("ramp: conform=60/24\n")
        assert any("— not conform" in f for f in _f) and not any("project switch" in w for w in _w), \
            ("switch off: conform is a ramp key it does not know, as before", _f)
        _f, _ = _sw("ramp: ease=90%\njoin: whip\n")
        assert any("— not ease" in f for f in _f), ("switch off: ease is a ramp key it does not know, as before", _f)
        _f, _ = _sw("ramp: kind=burst, speed=130, trigger=song@12.4, sfx=hit\n")
        assert any("`ramp: trigger=` is the second" in f for f in _f), ("switch off: a song cue is no trigger", _f)
        open(os.path.join(_swj, "00-brief", "CHECKPOINT.md"), "w").write(
            "Job:        sw-1\nSwitches:   speed-conform — the pour is real 60 fps footage; "
            "music-led — the song is the deliverable\n")
        for _x, _what in (("ramp: conform=60/24\n", "whole-clip conform at 40 %"),
                          ("ramp: conform=40%, sfx=pour, cut_in=3.0, cut_out=5.5\n", "whole-clip conform at 40 %"),
                          ("ramp: ease=90%\njoin: whip\n", "ease inside its whip at 90 %"),
                          ("ramp: conform=50%\ngrade: talking_head\n", "whole-clip conform at 50 %")):   # a lip-sync take
            _f, _w = _sw(_x)
            assert not _f and any(_what in w and "lifted by project switch `speed-conform` (the pour" in w for w in _w), \
                ("speed-conform on: lifted", _x, _f, _w)
        _f, _w = _sw("ramp: kind=burst, speed=130, trigger=song@12.4, sfx=hit\n")
        assert not _f and any("cues the burst to the song" in w and "lifted by project switch `music-led`" in w
                              for w in _w), ("music-led on: a song-cued burst", _f, _w)
        for _x, _needle in (("ramp: ease=80%\njoin: whip\n", "no lower than 85 %"),
                            ("ramp: ease=90%\n", "no `join: whip`"),
                            ("ramp: conform=24/60\n", "under 100 %"),
                            ("ramp: conform=40%, kind=slow, speed=40\n", "still a ramp"),
                            ("ramp: conform=40%, reveal=the pour\n", "— not reveal"),
                            ("ramp: ease=90%\njoin: whip\ngrade: talking_head\n", "speaking or reacting"),
                            ("ramp: kind=slow, speed=40, trigger=song@12.4, reveal=x, sfx=y\n", "`ramp: trigger=` is the second"),
                            ("ramp: kind=burst, speed=130, trigger=song@soon, sfx=hit\n", "`ramp: trigger=` is the second")):
            _f, _ = _sw(_x)
            assert any(_needle in f for f in _f), ("a switch on, the case outside what it allows: still refused", _x, _f)
        _aer = ("aerial: move=orbit, function=reveal, subject=the clubhouse roof, final=the clubhouse and the sea, place=invented\n"
                "world: none (a lint fixture outside any job)\n")
        assert not [f for f in _rp(_aer)["fails"] if "aerial" in f.lower() or "subject" in f], "a declared aerial"
        # ⚡ the world (2026-10-27): an aerial is all world — no card, no lint; and the motion budget is a ⚑ to answer
        assert any("[world] an aerial with no `world:`" in f for f in _rp(_aer.split("world:")[0])["fails"]), "an aerial with no world"
        _route = ("aerial: move=hole_flyover, function=geography, subject=the 17th green, final=the green and the flag, "
                  "place=invented, path_m=402\nworld: none (a lint fixture outside any job)\n")
        assert any("unanswered: ⚑ MOTION: 402 m in 5 s" in f and "12.0×" in f for f in _rp(_route)["fails"]), \
            "a route squeezed into one clip is a must-answer warning"
        assert any("route move with no `path_m=`" in f for f in _rp(_route.replace(", path_m=402", ""))["fails"]), \
            "a route move with no distance is asked for one"
        assert any("is not a subject" in f for f in _rp(_aer.replace("the clubhouse roof", "landscape"))["fails"]), "a generic aerial subject"
        assert any("without `aerial:`" in f for f in _rp("chain: root=x.jpg, stage=1, from=S1\n")["fails"]), "a chain with no aerial"
        assert not any("`grade:" in w for w in _ho("grade: product\n")), "a grade profile on its list"
        assert any("`grade: moody`" in w for w in _ho("grade: moody\n")), "a grade profile off its list"
        for _bad, _what in (("the shadows on the wall pulse with her breathing", "mirrors the emotion"),
                            ("the scene slowly shifts into a dreamlike oil painting", "texture change"),
                            ("her reflection in the window ripples and shatters", "a reflection")):
            assert any(_what in w for w in _mo(f"START: the kitchen at night\nMID: {_bad}\nEND: it settles")), _bad
        assert not any("out of the ads lane" in w for w in _mo("START: light from the window on the table\n"
                                                               "MID: a cloud passes and the light dims\nEND: the room cooler")), \
            "a motivated light change is not the pulsing environment"
        assert any("says why but not how" in w for w in _mo("INTENT: she wants it gone\nSTART: her hand on the jar\n"
                                                            "MID: she empties the jar into the bin\n"
                                                            "END: the jar on the counter, she turns away"))

        # ---------------------------------------------------- THE SHOT EVENT CARD (direction.md §2b)
        # ⛔ THE DEAD SHOT. A hook written as "a bare mattress, and only dust moves" passed this
        # linter clean on 2026-09-08: the only-camera-verbs rule did not fire, because *dust drifts*
        # is not a camera verb. F11 would have caught it — at the CLIP gate, after the credits were
        # spent. These three checks ask it on the plan.
        no_pay = cl_ok.replace("payload: the bench is now occupied and the room has someone in it\n", "")
        r_np = lint_str(no_pay, td, "S9.clip.prompt.md")
        assert any("no `payload:`" in f for f in r_np["fails"]), r_np["fails"]
        short_pay = cl_ok.replace("payload: the bench is now occupied and the room has someone in it",
                                  "payload: a room")
        assert any("too short to be an answer" in f
                   for f in lint_str(short_pay, td, "S9.clip.prompt.md")["fails"])
        same = cl_ok.replace("function: establish the room",
                             "function: establish the room and who is in it").replace(
                             "payload: the bench is now occupied and the room has someone in it",
                             "payload: establish the room and who is in it")
        assert any("restates `function:`" in w
                   for w in lint_str(same, td, "S9.clip.prompt.md")["warns"])

        # ⛔ An END: that ASSERTS nothing changed is F11 failing in the writer's own words.
        dead = cl_ok.replace("END: tray set down on the bench",
                             "END: the dust settles lower in the beam. Nothing else has happened "
                             "for six seconds, and that is the point")
        r_dead = lint_str(dead, td, "S9.clip.prompt.md")
        assert any("asserts that nothing changed" in f for f in r_dead["fails"]), r_dead["fails"]
        for phrase in ("the hollow's shadow is unchanged", "the room remains the same",
                       "the frame is exactly as it was", "the tray remains still"):
            d2 = cl_ok.replace("END: tray set down on the bench", "END: " + phrase)
            assert any("asserts that nothing changed" in f
                       for f in lint_str(d2, td, "S9.clip.prompt.md")["fails"]), phrase
        # ...and a real END is not flagged
        assert not any("asserts that nothing changed" in f for f in clip_thin["fails"]), clip_thin["fails"]
        # ⛔ "still" is an adverb as often as it is an adjective. "is still sinking" describes a
        # thing MID-CHANGE and must not trip the no-change rule — caught as a false positive on the
        # first real prompt this check ever saw, 2026-09-08.
        for alive in ("the second one is still sinking", "the foam is still settling",
                      "she is still reaching for it"):
            a2 = cl_ok.replace("END: tray set down on the bench", "END: " + alive)
            assert not any("asserts that nothing changed" in f
                           for f in lint_str(a2, td, "S9.clip.prompt.md")["fails"]), alive

        # ⛔ AMBIENT-ONLY: atmosphere is not an event. This is the exact dust prompt.
        amb = cl_ok.replace("[MOTION]\nSTART: tray level at hip height\nMID: the step lands\n"
                            "END: tray set down on the bench",
                            "[MOTION]\nSTART: the frame as approved\n"
                            "MID: only dust moves, motes drift and turn through the shaft of light\n"
                            "END: the dust settles lower in the beam")
        r_amb = lint_str(amb, td, "S9.clip.prompt.md")
        assert any("only AMBIENT motion" in w for w in r_amb["warns"]), r_amb["warns"]
        # a subject ACTION alongside the drift clears it — the check is about absence, not presence
        act = amb.replace("MID: only dust moves, motes drift and turn through the shaft of light",
                          "MID: a hand presses into the foam and withdraws; dust drifts where it landed")
        assert not any("only AMBIENT motion" in w
                       for w in lint_str(act, td, "S9.clip.prompt.md")["warns"])

        # --- MOTION: what the move must CONTAIN (motion-craft.md) ---------------------------
        # a block whose only verbs are camera verbs WARNS — and does not fail
        cam_only = cl_ok.replace(
            "START: tray level at hip height\nMID: the step lands\nEND: tray set down on the bench",
            "START: slow push in from wide\nMID: the push continues\nEND: the camera slows and holds")
        r_cam = lint_str(cam_only, td, "S9.clip.prompt.md")
        assert any("moves the camera and nothing else" in w for w in r_cam["warns"]), r_cam["warns"]
        assert not any("moves the camera and nothing else" in f for f in r_cam["fails"])
        # ...and the same block with ONE thing moving in it does not warn — the check must not
        # manufacture a finding on a legitimate locked-off shot that has life in the frame
        cam_plus = cl_ok.replace(
            "START: tray level at hip height\nMID: the step lands\nEND: tray set down on the bench",
            "START: locked-off on the cup\nMID: steam rises across the rim\n"
            "END: the steam thins and settles")
        r_plus = lint_str(cam_plus, td, "S9.clip.prompt.md")
        assert not any("moves the camera and nothing else" in w for w in r_plus["warns"]), r_plus["warns"]
        # ⛔ selection pressure: a dialogue clip shot once WARNS; two takes does not
        dlg = cl_ok.replace("type: broll", "type: dialogue").replace(
            "function: establish the room\n", "line: \"We taste it before you see it.\"\n"
            "vo: 05-voice/S9.wav\n") + (
            "\n[PERFORMANCE]\nSTATE: guarded → open\nBEAT: the glass lands\nFACE: a slow blink\n"
            "GAZE: to the lens on the last word\n\n[SPEECH]\nWe taste it before you see it.\n")
        r_one = lint_str(dlg, td, "S9.clip.prompt.md")
        assert any("variants: 1" in w for w in r_one["warns"]), r_one["warns"]
        r_two = lint_str(dlg.replace("duration: 5\n", "duration: 5\nvariants: 2\n"),
                         td, "S9.clip.prompt.md")
        assert not any("variants: 1" in w for w in r_two["warns"]), r_two["warns"]
        # ...and a B-ROLL clip shot once is not nagged: it is not what carries the film
        assert not any("variants: 1" in w for w in clip_thin["warns"]), clip_thin["warns"]

        # the settle warning: the house fixture names one ("set down"), a mid-motion block does not
        no_settle = cl_ok.replace("END: tray set down on the bench",
                                  "END: the tray is still moving toward the bench")
        r_ns = lint_str(no_settle, td, "S9.clip.prompt.md")
        assert any("names no settle" in w for w in r_ns["warns"]), r_ns["warns"]
        # ...and the house fixture, whose END: IS a settle, must not warn — "still" the adverb is
        # not a settle word and "set down" is
        assert not any("names no settle" in w for w in clip_thin["warns"]), clip_thin["warns"]
        # and the blocks must be able to REACH the band they were derived from
        frame_blocks = ("SUBJECT", "CHARACTER", "ENVIRONMENT", "LIGHTING", "CAMERA", "STYLE",
                        "SAFE ZONE")
        at_budget = sum(BLOCK_BUDGET[b] for b in frame_blocks)
        assert BAND_LO / 6.2 <= at_budget <= BAND_HI / 5.6, (
            f"{at_budget} words at budget cannot land inside {BAND_LO}-{BAND_HI} chars")

        # ⛔ LENGTH AND DENSITY ARE INDEPENDENT, and the checks must not be able to stand in for
        # each other. Found while writing this test: 361 words of run-on prose scored 2 demands.
        # long but NOT dense — one run-on clause, no coordinators
        runon = " ".join(f"detail{i} of the room" for i in range(1, 90))
        fat = base.replace("[ENVIRONMENT]", "[ENVIRONMENT]\n" + runon)
        r_fat = lint_str(fat, td, "S9.frame.prompt.md")
        j = " ".join(r_fat["warns"])
        assert "[ENVIRONMENT] is" in j and "word budget" in j, r_fat["warns"]
        assert "above the measured band" in j, r_fat["warns"]
        assert "demands per 100 words" not in j, "run-on prose is long, not dense"
        # dense but NOT over-long — many short clauses, well inside the band
        dense = base.replace("[ENVIRONMENT]",
                             "[ENVIRONMENT]\n" + ", ".join(f"a thing{i}" for i in range(1, 34)))
        r_dense = lint_str(dense, td, "S9.frame.prompt.md")
        jd = " ".join(r_dense["warns"])
        assert "demands per 100 words" in jd, r_dense["warns"]
        assert "above the measured band" not in jd, "this one is dense, not long"
        # ⚡ past 2,500 (v2.45): the ceiling is the MODEL's. nano_banana_pro takes 50,000, so a long frame only WARNS
        # that it has left the measured band; a model with no published cap keeps the house 2,500 as a FAIL that
        # says so, naming the band rather than a bare number
        huge = base.replace("[ENVIRONMENT]", "[ENVIRONMENT]\n" + runon * 4)
        r_huge = lint_str(huge, td, "S9.frame.prompt.md")
        assert not any("chars >" in f for f in r_huge["fails"]), r_huge["fails"]
        assert any("past the measured band" in w and "unmeasured territory" in w for w in r_huge["warns"]), r_huge["warns"]
        r_huge = lint_str(huge.replace("model: nano_banana_pro", "model: soul_2"), td, "S9.frame.prompt.md")
        assert any("past the top of the measured band" in f and "house ceiling, unknown vendor cap" in f
                   for f in r_huge["fails"]), r_huge["fails"]
        r_huge = lint_str(huge.replace("model: nano_banana_pro", "model: flux_3_image"), td, "S9.frame.prompt.md")
        assert any("house ceiling, unknown vendor cap" in f for f in r_huge["fails"]), r_huge["fails"]
        r_huge = lint_str(base.replace("[ENVIRONMENT]", "[ENVIRONMENT]\n" + runon * 20)
                          .replace("model: nano_banana_pro", "model: gpt_image_2"), td, "S9.frame.prompt.md")
        assert any("> 32000" in f and "gpt_image_2's ceiling" in f for f in r_huge["fails"]), r_huge["fails"]
        # the sidecar carries the numbers, so the band can be re-measured from real jobs
        ok_one = lint_str(clean, td, "S9.frame.prompt.md")
        if ok_one["sidecar"]:
            sc = ok_one["sidecar"]
            assert sc["band"] == [BAND_LO, BAND_HI] and "density" in sc and "prompt_words" in sc

        # --- FORM: MULTISHOT (references/multishot.md) ------------------------------------------
        open(os.path.join(job, "02-startframes", "S4_open_v2.png"), "wb").write(b"\x89PNG open")
        open(os.path.join(job, "02-startframes", "S4_close_v1.png"), "wb").write(b"\x89PNG close")
        ms = """---
shot: S4
kind: clip
form: multishot
type: sequence
model: seedance_2_5
resolution: 1080p
duration: 24
aspect: 9:16
start_frame: 02-startframes/S4_open_v2.png
payload: the viewer learns that the app moved Mika's dinner to Venice, and that she chose it
refs:
  - role: video_references, what: blocking, value: vid-blocking-0001, not: mannequins, flat colours, floor grid
  - role: image_references, what: character, value: img-mika-0001, not: sheet background, panel layout
  - role: image_references, what: prop, value: img-phone-0001, owner: Mika, not: studio background
  - role: image_references, what: environment, value: img-terrace-0001, not: people in the plate
  - role: image_references, what: endframe, value: img-close-0001
---
[GOAL]
A 24-second sequence on a sofa and then a Venice terrace: Mika taps her phone and the world changes around her.

[REFERENCES]
[Characters] Mika corresponds to @Image 2. Use only the appearance, hairstyle, and clothing.
[Props] The phone corresponds to @Image 3 and belongs only to Mika. Use only the shape, material, and colour.
[Scenes] The terrace corresponds to @Image 4. Use only the space, materials, and lighting, never the people in it.
[Frames] @Image 1 is the first frame of Stage 1; match its composition. @Image 5 is the final frame of Stage 3.
[Motion] @Video 1 is the blocking: camera path, positions and timing only.

[STAGES]
Stage 1 | 0–8 s | MS, 35 mm, eye level, slow push-in
Use: Mika, @Image 2, @Image 3, @Video 1
Event: Mika reads the screen and taps it once with her index finger.
End state: phone in Mika's right hand, screen toward her, her eyes on it.
Cut: match cut on the tap

Stage 2 | 8–16 s | MS, 35 mm, eye level, locked-off
Use: Mika, @Image 2, @Image 4
Event: Mika lowers the phone and looks at the plate of spaghetti in front of her.
End state: phone face down on the table, fork in her right hand.
Cut: hard

Stage 3 | 16–24 s | WS, 24 mm, eye level, slow pull-back
Use: Mika, @Image 4, @Image 5
Event: Mika lifts the first forkful, the terrace opening out around her.
End state: Mika small in frame at the terrace table, hard midday sun on the plaster wall.

[SOUND]
Lines, each spoken exactly once and nothing else:
6.0–7.0 s Mika: "Ooh."
9.0–9.6 s Mika: "Pasta!"
Ambience changes on the cut frames.

[CONSISTENCY]
One woman throughout, the same clothes in every stage; the phone stays Mika's; screen direction left to right.
"""
        mp = os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md")
        r = lint_str(ms, os.path.dirname(mp), "S4.clip.prompt.md")
        assert r["ok"], r["fails"]
        sc_ = r["sidecar"]
        assert [x["n"] for x in sc_["stages"]] == [1, 2, 3] and sc_["has_speech"], sc_.get("stages")
        assert len(sc_["tag_map"]["image"]) == 5 and sc_["tag_map"]["image"][0] == "the approved start frame"
        assert not any("prohibition" in w for w in r["warns"]), r["warns"]   # "never the people" is grammar

        def ms_fails(old, new):
            rr = lint_str(ms.replace(old, new), os.path.dirname(mp), "S4.clip.prompt.md")
            return " ".join(rr["fails"]), " ".join(rr["warns"])
        f_, _ = ms_fails("Stage 2 | 8–16 s", "Stage 2 | 9–16 s")
        assert "consecutive" in f_, f_
        f_, _ = ms_fails("Stage 3 | 16–24 s", "Stage 3 | 16–22 s")
        assert "add up to the clip" in f_, f_
        f_, _ = ms_fails("End state: phone face down on the table, fork in her right hand.\n", "")
        assert "Stage 2 has no `End state:`" in f_, f_
        f_, _ = ms_fails("eye level, locked-off", "eye level, slow pan left then a tilt up")
        assert "Stage 2 names 2 moves" in f_, f_
        f_, _ = ms_fails("Cut: hard\n", "")
        assert "Stage 2 has no `Cut:`" in f_, f_
        f_, _ = ms_fails("@Image 5 is the final frame", "@Image 9 is the final frame")
        assert "@Image 9 points past" in f_, f_
        f_, _ = ms_fails("[Characters] Mika corresponds to @Image 2.", "[Characters] @Images 2 through 3 define two characters respectively. Mika corresponds to @Image 2.")
        assert "range binding" in f_, f_
        f_, _ = ms_fails("Mika lifts the first forkful", "Mika takes three bites in one second, lifting the first forkful")
        assert "frequency demand" in f_, f_
        f_, _ = ms_fails('9.0–9.6 s Mika: "Pasta!"', '9.0–9.6 s Mika: "Pasta!"\n12.0–12.6 s Mika: "Pasta!"')
        assert "listed twice" in f_, f_
        f_, _ = ms_fails("start_frame: 02-startframes/S4_open_v2.png", "start_frame: 02-startframes/S4_open_v2.png\nend_frame: 02-startframes/S4_close_v1.png")
        assert "bind the approved end still as a reference" in f_, f_
        f_, _ = ms_fails("type: sequence", "type: dialogue")
        assert "`type: sequence`" in f_, f_
        f_, _ = ms_fails("form: multishot\n", "")
        assert "add `form: multishot`" in f_, f_
        _, w_ = ms_fails(", owner: Mika", "")
        assert "no `owner:`" in w_, w_
        _, w_ = ms_fails('6.0–7.0 s Mika: "Ooh."', '7.5–8.5 s Mika: "Ooh."')
        assert "crosses a stage boundary" in w_, w_

        # ==========================================================================================
        # v2.45 (2026-10-29) — prompting-craft.md §11g. Each rule pinned both ways.
        # --- 1 · THE MODEL'S CEILING ---------------------------------------------------------------
        assert prompt_limit("kling3_0")["max"] == 2500 and prompt_limit("kling3_0")["negative_max"] == 2500
        assert prompt_limit("minimax_h3")["max"] == 7000 and prompt_limit("minimax_h3")["negative"] == "none"
        k4 = prompt_limit("kling4_0")
        assert k4["mixed"] == {"english": 26000, "non_english": 11000} and not k4["house"], k4
        assert ceiling_over("a" * 26000, k4) == "" and ceiling_over("a" * 26001, k4)
        assert ceiling_over("a" * 13000 + "字" * 5500, k4) == ""                       # 0.5 + 0.5 = 1.0
        assert "mixed allowance" in ceiling_over("a" * 13000 + "字" * 5600, k4)
        assert prompt_limit("wan3_0")["truncates"] and prompt_limit("wan3_0")["max"] == 20000
        assert prompt_limit("wan2_2")["max"] == 800 and "_families[wan2]" in prompt_limit("wan2_2")["from"]
        for _h in ("soul_2", "cinematic_studio_video_4_0", "flux_3_video", "nano_banana_2", "no_such_model"):
            assert prompt_limit(_h)["house"] and prompt_limit(_h)["max"] == 2500, _h
        assert prompt_limit("nano_banana_pro")["max"] == 50000 and prompt_limit("gpt_image_2_5")["max"] == 32000
        assert prompt_limit("wan2_6")["negative_max"] == 500 and prompt_limit("seedance_2_5")["max"] == 20000
        _pad = lambda n_: " ".join(f"the tray{i} stays level" for i in range(n_))
        _cl = lambda model, extra="": cl_ok.replace("model: kling3_0", f"model: {model}") \
            .replace("MID: the step lands", "MID: the step lands. " + extra)
        _rk = lint_str(_cl("kling3_0", _pad(150)), td, "S9.clip.prompt.md")
        assert any("kling3_0's ceiling" in f and "> 2500" in f for f in _rk["fails"]), _rk["fails"]
        _rm = lint_str(_cl("minimax_h3", _pad(150)), td, "S9.clip.prompt.md")
        assert not any("ceiling" in f for f in _rm["fails"]), _rm["fails"]
        assert any("past the measured band" in w and "minimax_h3's own ceiling (7,000" in w for w in _rm["warns"]), _rm["warns"]
        _rm = lint_str(_cl("minimax_h3", _pad(400)), td, "S9.clip.prompt.md")
        assert any("minimax_h3's ceiling" in f and "> 7000" in f for f in _rm["fails"]), _rm["fails"]
        _rw = lint_str(_cl("wan3_0", _pad(1000)), td, "S9.clip.prompt.md")
        assert any("wan3_0's ceiling" in f and "truncates SILENTLY" in f for f in _rw["fails"]), _rw["fails"]
        _r4 = lint_str(_cl("kling4_0", _pad(150)), td, "S9.clip.prompt.md")
        assert not any("ceiling" in f for f in _r4["fails"]) and any("past the measured band" in w for w in _r4["warns"])
        _r4 = lint_str(_cl("kling4_0", "字" * 11500), td, "S9.clip.prompt.md")
        assert any("mixed allowance" in f for f in _r4["fails"]), _r4["fails"]
        # the multi-shot form keeps its 3,900 — and Kling's own shot limits under it
        _ms_k = ms.replace("model: seedance_2_5", "model: kling3_0").replace(
            "Event: Mika reads the screen and taps it once with her index finger.",
            "Event: Mika reads the screen and taps it once with her index finger. " + _pad(25))
        _rr = lint_str(_ms_k, os.path.dirname(mp), "S4.clip.prompt.md")
        assert any("Stage 1 is" in f and "at most 512 per shot" in f for f in _rr["fails"]), _rr["fails"]
        assert not any("Stage 2 is" in f and "per shot" in f for f in _rr["fails"]), _rr["fails"]
        _rr = lint_str(ms + "\n", os.path.dirname(mp), "S4.clip.prompt.md")
        assert _rr["ok"], _rr["fails"]
        # the negative cap is the model's; a model with no negative field never receives the list
        _sup = lambda model, items: lint_str(cl_ok.replace("model: kling3_0", f"model: {model}")
                                             .replace("[SUPPRESS]\nextra hands, text\n", "[SUPPRESS]\n" + items + "\n"),
                                             td, "S9.clip.prompt.md")
        _six = ", ".join(f"a stray prop number {i}" for i in range(30))          # ~620 chars of nouns
        assert not any("[SUPPRESS] is" in f for f in _sup("kling3_0", _six)["fails"])
        assert any("[SUPPRESS] is" in f and "> 500" in f for f in _sup("gemini_omni_flash_1_1", _six)["fails"])
        _rs = _sup("minimax_h3", "extra hands, text")
        assert any("NO negative field" in w and "DROPPED" in w for w in _rs["warns"]), _rs["warns"]
        assert not any("NO negative field" in w for w in _sup("kling3_0", "extra hands, text")["warns"])
        # --- 4 · THE SCENARIO REFUSALS ----------------------------------------------------------
        _rwm = lint_str(cl_ok.replace("MID: the step lands", "MID: the step lands, no watermark on the tray"),
                        td, "S9.clip.prompt.md")
        assert any("'watermark' is in the prompt" in f and "STILL CHARGED" in f for f in _rwm["fails"]), _rwm["fails"]
        _rwm = _sup("kling3_0", "extra hands, watermark")
        assert any("'watermark' in [SUPPRESS]" in w and "refuses to send it" in w for w in _rwm["warns"])
        assert not any("watermark" in f for f in _rwm["fails"]), _rwm["fails"]
        assert any("dropped on minimax_h3" in w for w in _sup("minimax_h3", "extra hands, watermark")["warns"])
        _sg = fr_r.replace("stone kitchen, late summer, 10am",
                           "stone kitchen, late summer, 10am, a shop sign over the door outside, no text anywhere")
        open(p2, "w", encoding="utf-8").write(_sg)
        assert any("only bans text" in w and "shop sign" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        open(p2, "w", encoding="utf-8").write(_sg.replace("a shop sign", "a blank cream enamel shop sign"))
        assert not any("only bans text" in w for w in lint(p2)["warns"]), lint(p2)["warns"]
        open(p2, "w", encoding="utf-8").write(_sg.replace(", no text anywhere", "")
                                              .replace("[CONSTRAINTS]\ntext, logo, ", "[CONSTRAINTS]\n"))
        assert not any("only bans text" in w for w in lint(p2)["warns"]), "no text ban, nothing to warn"
        open(p2, "w", encoding="utf-8").write(_sg.replace(", no text anywhere", ""))
        assert any("only bans text" in w for w in lint(p2)["warns"]), "[CONSTRAINTS] text, logo is the same ban"
        open(p2, "w", encoding="utf-8").write(fr_r.replace("[CONSTRAINTS]\ntext, logo, ", "[CONSTRAINTS]\ntext, logo, modern signage, "))
        assert not any("only bans text" in w for w in lint(p2)["warns"]), "a [CONSTRAINTS] noun is not a sign in the picture"
        open(p2, "w", encoding="utf-8").write(fr_r)
        _ga = cl_ok.replace("model: kling3_0", "model: gemini_omni_flash_1_1")
        assert any("never says 'no music'" in w and "no off switch" in w
                   for w in lint_str(_ga, td, "S9.clip.prompt.md")["warns"])
        _gm = lint_str(_ga.replace("[SUPPRESS]", "[SOUND]\nroom tone and the tray only, no music\n\n[SUPPRESS]"),
                       td, "S9.clip.prompt.md")
        assert not any("no music" in w for w in _gm["warns"]), _gm["warns"]
        assert not any("prohibition" in w and "SOUND" in w for w in _gm["warns"]), "'no music' is the instruction"
        assert any("the file turns it on" in w for w in lint_str(cl_ok.replace("model: kling3_0", "model: wan3_0")
                   .replace("duration: 5\n", "duration: 5\ngenerate_audio: true\n"), td, "S9.clip.prompt.md")["warns"])
        assert not any("no music" in w for w in lint_str(cl_ok, td, "S9.clip.prompt.md")["warns"]), "kling3_0 is silenced"
        _vr = ms.replace("[Motion] @Video 1 is the blocking: camera path, positions and timing only.",
                         "[Motion] @Video 1 is the blocking: positions and timing only.")
        _vw = lint_str(_vr, os.path.dirname(mp), "S4.clip.prompt.md")["warns"]
        assert any("which input decides the framing" in w for w in _vw), _vw
        assert not any("which input decides the framing" in w
                       for w in lint_str(ms, os.path.dirname(mp), "S4.clip.prompt.md")["warns"])
        # --- 3 · THE DETAIL SCORE and FILLER ----------------------------------------------------
        _rf = lint(p2)
        assert _rf["ok"] and _rf["sidecar"]["detail_score"] >= DETAIL_MIN["frame"], (_rf["fails"], _rf.get("detail"))
        assert isinstance(_rf["sidecar"]["detail_missing"], list) and _rf["detail"]["detail_of"] == len(FRAME_SLOTS)
        _bare = re.sub(r"(?ms)^\[LIGHTING\]\n.*?(?=^\[CAMERA\])", "[LIGHTING]\nnatural\n\n", fr_r) \
            .replace("50mm, eye level", "a nice angle").replace("stone kitchen, late summer, 10am", "a kitchen")
        open(p2, "w", encoding="utf-8").write(_bare)
        _rb = lint(p2)
        assert any(f.startswith("detail score") and "lens in mm" in f and "time of day" in f for f in _rb["fails"]), \
            (_rb["fails"], _rb.get("detail"))
        open(p2, "w", encoding="utf-8").write(_bare.replace("a woman in a green apron pouring olive oil",
                                                           "Exactly the reference, unchanged, with one change: the oil"))
        assert any("reads as an IMAGE EDIT" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        _rc = lint_str(cl_ok, td, "S9.clip.prompt.md")
        assert _rc["detail"]["detail_score"] >= DETAIL_MIN["clip"], _rc["detail"]
        _thin_c = cl_ok.replace("START: tray level at hip height\nMID: the step lands\nEND: tray set down on the bench",
                                "START: a tray\nMID: a step\nEND: a bench").replace("locked-off, chest height", "a nice shot")
        _rt = lint_str(_thin_c, td, "S9.clip.prompt.md")
        assert any(f.startswith("detail score") and "START with a time" in f for f in _rt["fails"]), _rt["fails"]
        _timed = cl_ok.replace("START: tray level", "START: 0–1 s, tray level").replace(
            "MID: the step lands", "MID: 1–3 s, the step lands").replace("END: tray set", "END: 3–5 s, tray set")
        assert lint_str(_timed, td, "S9.clip.prompt.md")["detail"]["detail_score"] == \
            _rc["detail"]["detail_score"] + 3, "a time on each beat is three slots"
        open(p2, "w", encoding="utf-8").write(fr_r.replace("mid-pour", "mid-pour, a stunning, breathtaking moment"))
        _fw = lint(p2)
        assert any("filler word(s) breathtaking, stunning" in w for w in _fw["warns"]), _fw["warns"]
        assert not any("filler" in f for f in _fw["fails"]), _fw["fails"]
        open(p2, "w", encoding="utf-8").write(fr_r.replace("mid-pour", "mid-pour, epic stunning beautiful cinematic "
                                                                       "gorgeous breathtaking masterful"))
        assert any("filler word(s)" in f and "mostly praise" in f for f in lint(p2)["fails"]), lint(p2)["fails"]
        open(p2, "w", encoding="utf-8").write(fr_r)
        # --- 2 · THE IMAGE EDIT (`kind: edit`) ----------------------------------------------------
        open(os.path.join(job, "02-startframes", "S4_kitchen_v2.png"), "wb").write(b"\x89PNG kitchen")
        _ed = TEMPLATES["edit"]
        _pe = os.path.join(job, "01-script", "prompts", "S4.edit.prompt.md")
        _le = lambda t_: (open(_pe, "w", encoding="utf-8").write(t_), lint(_pe))[1]
        _re = _le(_ed)
        assert _re["ok"], _re["fails"]
        _se = _re["sidecar"]
        assert _se["kind"] == "edit" and _se["use"] == "frame" and _se["edit_of_sha"] == \
            sha256_file(os.path.join(job, "02-startframes", "S4_kitchen_v2.png")), _se
        assert _se["detail_score"] >= DETAIL_MIN["edit"] and len(_se["keep_named"]) >= KEEP_MIN, _se
        assert EDIT_FLOOR_WARN <= _se["prompt_len"] <= HOUSE_CEILING, _se["prompt_len"]
        assert not any("prohibition" in w for w in _re["warns"]), _re["warns"]   # "not its sweep" is the grammar
        # (v2.71.0, build review 2, Grok) an edit's [CONSTRAINTS] "text, logo" is a noun list, never a request for a logo
        _rc = _le(_ed.rstrip("\n") + "\n\n[CONSTRAINTS]\ntext, logo\n")
        assert not any("logo / brand mark" in w for w in _rc["warns"]), _rc["warns"]
        # an edit written as a frame points to `kind: edit`
        _fe = fr_r.replace("kind: frame", "kind: frame\nedit_of: 02-startframes/S4_kitchen_v2.png")
        open(p2, "w", encoding="utf-8").write(_fe)
        assert any("`kind: frame` with `edit_of:`" in f and "kind: edit" in f for f in lint(p2)["fails"])
        open(p2, "w", encoding="utf-8").write(fr_r)
        for _blk in ("SOURCE", "KEEP", "CHANGE", "LIGHT MATCH", "OUTPUT"):
            _cut = re.sub(rf"(?ms)^\[{_blk}\]\n.*?(?=^\[|\Z)", "", _ed)
            assert any(f"[{_blk}] missing" in f for f in _le(_cut)["fails"]), _blk
        _k2 = re.sub(r"(?ms)^\[KEEP\]\n.*?(?=^\[CHANGE\])", "[KEEP]\nKeep her face and her pose exactly as in Image 1.\n\n", _ed)
        assert any("[KEEP] names 2 of the 8" in f for f in _le(_k2)["fails"]), _le(_k2)["fails"]
        _c2 = re.sub(r"(?ms)^\[CHANGE\]\n.*?(?=^\[LIGHT MATCH\])",
                     "[CHANGE]\nReplace only the bottle in her right hand with the product in Image 2, in the same spot.\n\n", _ed)
        _fc = " ".join(_le(_c2)["fails"])
        assert "does not state its size, material, how it meets the light" in _fc, _fc
        _r2 = _ed.replace("not its white sweep, not its softbox reflections, not its shadow", "and its white sweep")
        assert any("[REFERENCES] line 1 gives no 'not'" in f for f in _le(_r2)["fails"])
        _r3 = re.sub(r"(?ms)^\[REFERENCES\]\n.*?(?=^\[OUTPUT\])", "", _ed)
        assert any("no [REFERENCES] block" in f for f in _le(_r3)["fails"])
        _o2 = _ed.replace("9:16, 2k, one photographic frame. ", "One photographic frame. ")
        assert any("[OUTPUT] names no aspect" in f for f in _le(_o2)["fails"])
        _o3 = re.sub(r"(?ms)^\[OUTPUT\]\n.*?\Z", "[OUTPUT]\n9:16, 2k, one photographic frame.\n", _ed)
        assert any("[OUTPUT] does not ban text" in f for f in _le(_o3)["fails"])
        _o4 = re.sub(r"(?ms)^\[OUTPUT\]\n.*?\Z", "[OUTPUT]\n9:16, 2k, one photographic frame. No text, letters or logos.\n", _ed)
        assert any("bans ALL text while the picture keeps or adds a label" in w for w in _le(_o4)["warns"])
        _short = ("---\nshot: S4\nkind: edit\nmodel: nano_banana_pro\nresolution: 2k\naspect: 9:16\n"
                  "edit_of: 02-startframes/S4_kitchen_v2.png\nedit_of_media: m1\n---\n[SOURCE]\nThe approved S4 frame, "
                  "a woman at a stone counter in morning light.\n\n[KEEP]\nher face, her pose, the framing, the light, the "
                  "lens\n\n[CHANGE]\nthe bottle turns amber glass\n\n[LIGHT MATCH]\nkey from the left window, warm sun\n\n"
                  "[OUTPUT]\n9:16, 2k. No text or logos.\n")
        assert any(f"< {EDIT_FLOOR_FAIL}" in f for f in _le(_short)["fails"]), _le(_short)["fails"]
        _mid = _short.replace("a woman at a stone counter in morning light.",
                              "a woman in a green linen apron at a pale limestone counter at ten in the morning, holding a "
                              "plain glass bottle of olive oil in her right hand, the open oak shelves and a jar of olives "
                              "behind her, photographed at eye level with a 50 mm look, hard sun from the left window.") \
            .replace("her face, her pose, the framing, the light, the lens",
                     "her face and expression, her pose, the framing and composition, the hard warm light from the left "
                     "window, the 50 mm lens and eye-level perspective, the shelves behind her")
        _rmid = _le(_mid)
        assert EDIT_FLOOR_FAIL <= len(_rmid["prompt"]) < EDIT_FLOOR_WARN, len(_rmid["prompt"])
        assert any(f"< {EDIT_FLOOR_WARN}" in w for w in _rmid["warns"]) and \
            not any(f"< {EDIT_FLOOR_FAIL}" in f for f in _rmid["fails"]), (_rmid["warns"], _rmid["fails"])
        assert any("`use: target`" in w and "approve target:S4" in w for w in _le(_ed.replace("use: frame ", "use: target "))["warns"])
        assert any("`use: lookbook`" in f for f in _le(_ed.replace("use: frame ", "use: lookbook "))["fails"])
        json.dump({"source": "ai-generated", "licence": "own", "clearance": "CLEARED"},
                  open(os.path.join(job, "02-startframes", "S4_kitchen_v2.png.json"), "w"))
        assert any("whose provenance says ai-generated" in f for f in _le(_ed.replace("use: frame ", "use: target "))["fails"])
        assert _le(_ed)["ok"], "use: frame on a generated source is an ordinary frame edit"
        os.remove(os.path.join(job, "02-startframes", "S4_kitchen_v2.png.json"))
        assert any("edit_of 'nope.png' not found" in f for f in _le(_ed.replace("02-startframes/S4_kitchen_v2.png", "nope.png"))["fails"])
        assert any("is a VIDEO model" in f for f in _le(_ed.replace("model: nano_banana_pro", "model: kling3_0"))["fails"])
        os.remove(_pe)

    # ------------------------------------------------------------------------------------------
    # CALL SHAPES (2026-09-19) — the one decision the gate and preflight both read, per model.
    assert canonical_role("image") == "image_references" and canonical_role("start_frame") == "start_image"
    assert canonical_role("voice") == "audio_references" and canonical_role("end_image") == "end_image"
    k = call_shape("kling3_0", False, True)
    assert (k["start_role"], k["end_role"], k["mode"]) == ("start_image", "end_image", None), k
    m = call_shape("minimax_h3", False, True)                   # frames alone: a TRUE first frame (1.00)
    assert (m["start_role"], m["end_role"], m["reference_mode"]) == ("start_image", "end_image", False), m
    mr = call_shape("minimax_h3", True, True)                   # frames + refs: 422 — so reference mode
    assert mr["reference_mode"] and mr["start_role"] == "image_references" and mr["end_role"] is None, mr
    sd = call_shape("seedance_2_5", False, False)               # never a true first frame (0.53 / 0.96)
    assert sd["reference_mode"] and sd["start_role"] == "image_references" and sd["mode"] == "omni_reference", sd
    assert call_shape("seedance_2_5", False, True)["end_role"] is None
    g = call_shape("gemini_omni_flash_1_1", False, True)
    assert g["start_role"] == "start_image" and g["mode"] == "image-to-video" and g["mode_required"], g
    assert not g["frames_measured"]                             # schema only — the lint warns
    gr = call_shape("gemini_omni_flash_1_1", True, False)       # unmeasured `mix` is treated as False
    assert gr["reference_mode"] and gr["mode"] == "reference-to-video", gr
    assert call_shape("no_such_model", False, False)["start_role"] is None
    # per-model reference caps: Seedance 2.5 states its own; a row without them gets the house caps
    assert slot_caps("seedance_2_5") == {"image": 30, "video": 10, "audio": 10}, slot_caps("seedance_2_5")
    assert slot_caps("minimax_h3") == SLOT_CAPS and slot_caps("kling3_0") == SLOT_CAPS
    # ⛔ THE ROSTER FAILS CLOSED. With the rate asset unreadable, roster() used to return {} and the
    # check `if model and ro and model not in ro` passed every model without a word.
    global ASSETS
    _real = ASSETS
    try:
        ASSETS = os.path.join(_real, "__nowhere__")
        assert roster() is None and call_contract("kling3_0") == {}
        with tempfile.TemporaryDirectory() as td0:
            j0 = os.path.join(td0, "job"); os.makedirs(os.path.join(j0, "00-brief"))
            os.makedirs(os.path.join(j0, "01-script", "prompts")); os.makedirs(os.path.join(j0, "02-startframes"))
            open(os.path.join(j0, "02-startframes", "S3_hero_v2.png"), "wb").write(b"\x89PNG fake")
            pp = os.path.join(j0, "01-script", "prompts", "S3.clip.prompt.md")
            open(pp, "w", encoding="utf-8").write(good)
            r0 = lint(pp)
            assert not r0["ok"] and any("cannot read" in f for f in r0["fails"]), r0["fails"]
    finally:
        ASSETS = _real
    assert roster() and "gemini_omni_flash_1_1" in roster()
    # the 2026-10-23 owner additions: priced rows, 1080p only, and their contracts name the traps
    assert {"wan3_0", "kling4_0"} <= set(roster()) and set(roster()["wan3_0"]) == {"1080p"} \
        and set(roster()["kling4_0"]) == {"1080p"}
    assert call_shape("wan3_0", False, False)["audio"] == {"param": "generate_audio", "off": False, "default_on": True}
    assert call_shape("kling4_0", False, False)["mode"] == "image-to-video" and call_shape("kling4_0", True, False)["mode"] == "reference-to-video"

    # ------------------------------------------------------------------------------------------
    # THE ONE-VARIABLE CORRECTION — tested against the corpus case it was written from.
    # Guard first: the block-kind map must classify the names TEMPLATES actually EMITS. A map
    # written for block names nobody uses is a dead check (the citation-form gap, hit 3x on
    # 2026-09-17), so this asserts against the templates rather than against a wish list.
    emitted = set()
    for tmpl in TEMPLATES.values():
        emitted |= {m.group(1).strip() for m in BLOCK_RE.finditer(tmpl)}
    assert emitted, "no blocks parsed out of TEMPLATES"
    want = {"MOTION": ("personal", "STAGING"), "CAMERA": ("impersonal", "CAMERA"),
            "PERFORMANCE": ("personal", "STAGING"), "SPEECH": ("dialogue", "DIALOGUE"),
            "SUPPRESS": ("impersonal", "SUPPRESS"), "CONSTRAINTS": ("impersonal", "SUPPRESS"),
            "SUBJECT": ("personal", "STAGING"),
            "CHARACTER": ("personal", "STAGING"), "ENVIRONMENT": ("impersonal", "SETTING"),
            "LIGHTING": ("impersonal", "LIGHT"), "STYLE": ("impersonal", "STYLE"),
            "SAFE ZONE": ("impersonal", "SAFE ZONE"),
            # form: multishot
            "GOAL": ("impersonal", "GOAL"), "REFERENCES": ("impersonal", "REFERENCES"),
            "WHERE": ("impersonal", "GEOGRAPHY"), "STAGES": ("personal", "STAGING"),
            "SOUND": ("impersonal", "AUDIO"), "CONSISTENCY": ("impersonal", "CONSISTENCY"),
            # kind: edit (v2.45)
            "SOURCE": ("impersonal", "SOURCE"), "KEEP": ("impersonal", "KEEP"),
            "CHANGE": ("personal", "STAGING"), "LIGHT MATCH": ("impersonal", "LIGHT"),
            "OUTPUT": ("impersonal", "OUTPUT"),
            # form: scene (v2.49.0)
            "SCENE CONTEXT": ("impersonal", "GOAL"), "ACTIVE REFERENCES": ("impersonal", "REFERENCES"),
            "LOCATION MAP": ("impersonal", "SETTING"), "FIRST FRAME": ("personal", "STAGING"),
            "FORMAT MODE": ("impersonal", "TECHNICAL"), "OPTICS": ("impersonal", "CAMERA"),
            "ACTION TIMING": ("personal", "STAGING"), "PHYSICS": ("impersonal", "PHYSICS"),
            "COLOR": ("impersonal", "LIGHT"), "AUDIO": ("impersonal", "AUDIO"),
            "POSITIVE LOCKS": ("impersonal", "CONSISTENCY"),
            # the scene file and the project DNA (v2.49.0)
            "WARDROBE": ("personal", "STAGING"), "OUTPUT SETTINGS": ("impersonal", "OUTPUT")}
    assert emitted <= set(want), f"TEMPLATES emit blocks the correction map has no opinion on: {emitted - set(want)}"
    for b in sorted(emitted):
        assert _block_kind(b) == want[b], f"[{b}] classified {_block_kind(b)}, expected {want[b]}"
    # MOTION is the SUBJECT's motion in this skill, not the camera's — the easy mistake.
    assert _block_kind("MOTION")[1] != "CAMERA"

    with tempfile.TemporaryDirectory() as td:
        base = ("---\nmodel: minimax_h3\nrefs:\n  - name: @hero · attribute: face\n"
                "  - name: @girl · attribute: face\n---\n"
                "[CAMERA]\nCamera inside @car from the rear seat, locked off, no camera movement.\n\n"
                "[PERFORMANCE]\n@hero whips his head back with keen interest. "
                "His emotion is engagement fused with sly irony, a mischievous glint in his eyes.\n"
                "@girl braces a hand on the ceiling. She is annoyed by the question, brows knitting.\n\n"
                "[SPEECH]\n\"Got any change on you?\" \"Change what? No.\"\n\n"
                "[SUPPRESS]\nhead bobbing\n")
        a = os.path.join(td, "v3.prompt.md"); open(a, "w", encoding="utf-8").write(base)
        # iteration four: her state AND her line — the corpus calls this ONE variable, because a
        # line is spoken BY a performer and the pass corrects exactly one performer.
        four = base.replace("She is annoyed by the question, brows knitting.",
                            "She is pressed back, breathless and in light shock.") \
                   .replace('"Change what? No."', '"Change? No."')
        b = os.path.join(td, "v4.prompt.md"); open(b, "w", encoding="utf-8").write(four)
        r = correction_diff(b, a)
        assert r["ok"], r["fails"]
        assert r["variables"] == 1 and list(r["subjects"]) == ["@girl"], r["subjects"]
        assert "PERFORMANCE" in r["subjects"]["@girl"] and "SPEECH" in r["subjects"]["@girl"]
        assert 0 < r["preserved_pct"] < 100
        # the sticky attribution is what makes that work: the state sentence names nobody
        assert _subject_of("She is pressed back, breathless.", "PERFORMANCE") == {"STAGING"}

        # iteration two: improves her AND flattens his irony — the corpus's own overcorrection
        two = base.replace("His emotion is engagement fused with sly irony, a mischievous glint in his eyes.",
                           "His emotion is urgent excitement, eyes wide, mouth open in a grin.") \
                  .replace("She is annoyed by the question, brows knitting.",
                           "She is pressed back, breath quickened.")
        c = os.path.join(td, "v2.prompt.md"); open(c, "w", encoding="utf-8").write(two)
        r2 = correction_diff(c, a)
        assert not r2["ok"] and r2["variables"] == 2, r2["subjects"]
        assert set(r2["subjects"]) == {"@hero", "@girl"}, r2["subjects"]
        assert any("2 variables changed" in f for f in r2["fails"])
        # ...and declaring it makes it legal, because the declaration is the information
        assert correction_diff(c, a, allow=2)["ok"]

        # a camera change is a CAMERA variable even though the block names @car
        cam = base.replace("locked off, no camera movement", "slow dolly push in, crane up at the end")
        d = os.path.join(td, "v5.prompt.md"); open(d, "w", encoding="utf-8").write(cam)
        assert list(correction_diff(d, a)["subjects"]) == ["CAMERA"], correction_diff(d, a)["subjects"]

        # a reference swap in the same pass as a body change: two grounds moved at once
        ref = base.replace("- name: @girl · attribute: face", "- name: @girl_v2 · attribute: face") \
                  .replace("She is annoyed by the question, brows knitting.", "She is pressed back.")
        e = os.path.join(td, "v6.prompt.md"); open(e, "w", encoding="utf-8").write(ref)
        r6 = correction_diff(e, a)
        assert any("two grounds moved at once" in f for f in r6["fails"]), r6["fails"]

        # a total rewrite keeps nothing
        blank = base.split("[CAMERA]")[0] + "[CAMERA]\nA completely different shot of a boat.\n"
        f_ = os.path.join(td, "v7.prompt.md"); open(f_, "w", encoding="utf-8").write(blank)
        assert any("rewrite, not a correction" in x for x in correction_diff(f_, a)["fails"])

        # the note: "make it better" fails even when the diff is clean
        rn = correction_diff(b, a, note="just make it better and more natural")
        assert not rn["ok"] and any("cannot protect a solved choice" in x for x in rn["fails"])
        # a note that names the miss and the replacement state passes
        rg = correction_diff(b, a, note="Keep the solved visuals. Change only @girl: pressed back, "
                                        "breathless, light shock. Shorten her line.")
        assert rg["ok"] and not rg["warns"], (rg["fails"], rg["warns"])
        # ...and re-running the same prompt is a reroll, not an iteration
        assert any("reroll" in w for w in correction_diff(a, a)["warns"])
        # a quoted line is one sentence, not two — "Change what? No." must not split
        assert _sentences('"Got any change on you?" "Change what? No." He shrugs.') == \
            ['"Got any change on you?"', '"Change what? No."', "He shrugs."]

        # --- the one-variable correction on a MULTISHOT: [STAGES] is diffed field by field ------
        msb = ("---\nmodel: seedance_2_5\nform: multishot\nrefs:\n"
               "  - role: image_references, what: character, value: m1\n"
               "  - role: image_references, what: character, value: j1\n---\n"
               "[REFERENCES]\n[Characters] Mika corresponds to @Image 2. Use only the appearance.\n"
               "[Characters] Jon corresponds to @Image 3. Use only the appearance.\n\n"
               "[STAGES]\nStage 1 | 0-8 s | MS, 35 mm, eye level, slow push-in\n"
               "Use: Mika, @Image 2\nEvent: Mika lifts the phone from the table.\n"
               "End state: Mika holds the phone in her right hand.\nCut: hard\n\n"
               "Stage 2 | 8-16 s | MCU, 50 mm, locked-off\nUse: Mika, Jon, @Image 2, @Image 3\n"
               "Event: Mika hands the phone to Jon.\nEnd state: Jon holds the phone; Mika sits back.\n"
               "Cut: match cut on the tap\n\n"
               "Stage 3 | 16-24 s | WS, 24 mm, slow pull-back\nUse: Mika, @Image 2\n"
               "Event: Mika turns to the window.\nEnd state: Mika alone at the window.\n\n"
               "[SOUND]\nLines, each spoken exactly once and nothing else:\n"
               "10.0-11.1 s Mika: \"Take it.\"\nAmbience changes on the cut frames.\n")
        ma = os.path.join(td, "ms_v1.prompt.md"); open(ma, "w", encoding="utf-8").write(msb)
        assert _cast_names(msb) == {"Mika", "Jon"}, _cast_names(msb)
        # one character fixed in TWO stages, plus her line: still one variable (@Mika)
        m2 = msb.replace("End state: Mika holds the phone in her right hand.",
                         "End state: Mika holds the phone in her left hand.") \
                .replace("Event: Mika turns to the window.", "Event: Mika turns slowly to the window.") \
                .replace('"Take it."', '"Here. Take it."')
        mb = os.path.join(td, "ms_v2.prompt.md"); open(mb, "w", encoding="utf-8").write(m2)
        rm = correction_diff(mb, ma)
        assert rm["ok"] and list(rm["subjects"]) == ["@Mika"], (rm["subjects"], rm["fails"])
        # a hand-off names two people: ONE variable of that stage, not two characters
        m3 = msb.replace("Event: Mika hands the phone to Jon.", "Event: Mika slides the phone across to Jon.")
        mc = os.path.join(td, "ms_v3.prompt.md"); open(mc, "w", encoding="utf-8").write(m3)
        assert list(correction_diff(mc, ma)["subjects"]) == ["STAGE 2"], correction_diff(mc, ma)["subjects"]
        # the camera of one stage AND the event of another: two variables
        m4 = msb.replace("MCU, 50 mm, locked-off", "MCU, 50 mm, slow push-in") \
                .replace("Event: Mika turns to the window.", "Event: Mika stands and turns to the window.")
        md = os.path.join(td, "ms_v4.prompt.md"); open(md, "w", encoding="utf-8").write(m4)
        r4 = correction_diff(md, ma)
        assert not r4["ok"] and set(r4["subjects"]) == {"CAMERA", "@Mika"}, r4["subjects"]
        # re-timing a boundary moves BOTH headers but is one TIMING variable; a cut swap is TRANSITIONS
        m5 = msb.replace("Stage 1 | 0-8 s", "Stage 1 | 0-7 s").replace("Stage 2 | 8-16 s", "Stage 2 | 7-16 s")
        me = os.path.join(td, "ms_v5.prompt.md"); open(me, "w", encoding="utf-8").write(m5)
        assert list(correction_diff(me, ma)["subjects"]) == ["TIMING"], correction_diff(me, ma)["subjects"]
        m6 = msb.replace("Cut: match cut on the tap", "Cut: hard")
        mf = os.path.join(td, "ms_v6.prompt.md"); open(mf, "w", encoding="utf-8").write(m6)
        assert list(correction_diff(mf, ma)["subjects"]) == ["TRANSITIONS"], correction_diff(mf, ma)["subjects"]
        # ambience is AUDIO, not the line
        m7 = msb.replace("Ambience changes on the cut frames.", "Room tone stays constant across the cuts.")
        mg = os.path.join(td, "ms_v7.prompt.md"); open(mg, "w", encoding="utf-8").write(m7)
        assert list(correction_diff(mg, ma)["subjects"]) == ["AUDIO"], correction_diff(mg, ma)["subjects"]
        # a reference swap that re-words only its own binding line: one ground, ok
        m8 = msb.replace("value: j1", "value: j2").replace(
            "Jon corresponds to @Image 3. Use only the appearance.",
            "Jon corresponds to @Image 3. Use only the appearance and the jacket.")
        mh = os.path.join(td, "ms_v8.prompt.md"); open(mh, "w", encoding="utf-8").write(m8)
        r8 = correction_diff(mh, ma)
        assert r8["ok"] and list(r8["subjects"]) == ["REFERENCES"], (r8["subjects"], r8["fails"])
        # ...but with a stage change alongside it, two grounds moved
        m9 = m8.replace("Event: Mika turns to the window.", "Event: Mika stands at the window.")
        mi = os.path.join(td, "ms_v9.prompt.md"); open(mi, "w", encoding="utf-8").write(m9)
        assert any("two grounds moved at once" in f for f in correction_diff(mi, ma)["fails"])
        # adding a stage re-plans the cut
        m10 = msb.replace("Stage 3 | 16-24 s", "Stage 3 | 16-20 s").replace(
            "End state: Mika alone at the window.\n",
            "End state: Mika alone at the window.\nCut: hard\n\nStage 4 | 20-24 s | CU, 85 mm, locked-off\n"
            "Use: Mika, @Image 2\nEvent: Mika exhales.\nEnd state: Mika's face in profile.\n")
        mj = os.path.join(td, "ms_v10.prompt.md"); open(mj, "w", encoding="utf-8").write(m10)
        assert "STAGE PLAN" in correction_diff(mj, ma)["subjects"]

        # ⚡ THE MOVEMENT PERSONA (2026-10-26): one MOVES LIKE line per cast person, carried by every clip
        _P = os.path.join(job, "01-script", "prompts", "S6.clip.prompt.md")
        os.makedirs(os.path.dirname(_P), exist_ok=True)
        _mk = lambda extra_fm, motion: ("---\nshot: S6\nkind: clip\ntype: broll\nmodel: kling3_0\nresolution: 4k\n"
                                        "duration: 5\ncut: 3\naspect: 9:16\nstart_frame: 02-startframes/S6.png\n"
                                        "function: the morning routine\npayload: she takes the capsules without a thought, "
                                        "it is part of her day now\n" + extra_fm + "---\n[MOTION]\n" + motion +
                                        "INTENT: her daily habit: quick and sure\nSTART: her hand takes the bottle without looking\n"
                                        "MID: her thumb flicks the cap open and she tips two capsules out, one shake\n"
                                        "END: she sets the bottle down with a light tap and turns away\n\n[CAMERA]\nlocked-off, chest height\n\n"
                                        "[SUPPRESS]\nextra fingers, text\n")
        _pw = lambda t: (open(_P, "w", encoding="utf-8").write(t), lint(_P)["warns"])[1]
        assert any("no _reference/PERSONA-maria.md" in w for w in _pw(_mk("persona: maria\n", ""))), "persona file missing"
        os.makedirs(os.path.join(job, "_reference"), exist_ok=True)
        _pp = os.path.join(job, "_reference", "PERSONA-maria.md")
        open(_pp, "w", encoding="utf-8").write("# Persona — Maria\n## How they move\n- **MOVES LIKE:** brisk and "
                                               "economical, a mother of three who never wastes a move\n")
        assert any("no `MOVES LIKE:` line" in w for w in _pw(_mk("persona: maria\n", "")))
        _same = "MOVES LIKE: brisk and economical, a mother of three who never wastes a move\n"
        assert not any("persona" in w.lower() or "MOVES LIKE" in w for w in _pw(_mk("persona: maria\n", _same)))
        assert any("differs from PERSONA-maria.md" in w for w in _pw(_mk("persona: maria\n", "MOVES LIKE: slow and careful\n")))
        assert any("names no `persona:`" in w for w in _pw(_mk("", ""))), "a job with personas asks whose this is"
        os.remove(_pp); os.remove(_P)


    _selftest_genjutsu()
    _selftest_scene()
    _selftest_scene_file()
    print("selftest OK — clip pass/fail (i2v fork, hedge, roster), clip length from the cut (cut: missing named, too short fails, no handle and dead front warned), intent (a person acting needs INTENT: with a manner, the material never leads, the floaty default warned), the start frame for its motion (caught:/travel:), the ads-lane AI tells, an obstacle on a proof shot, the movement persona (one MOVES LIKE line per person), motion planned for the cut (exit:/enter:/join:, track:), the shot's sound (sfx:), a toss with no landing (object permanence) · frame pass/fail (state, name) · "
          "suppress split · the REFERENCE PLAN: no-refs, duplicate attribute, no attribute, "
          "unsourced, no provenance, uncleared, and re-describing what a reference carries · "
          "LENGTH against the measured band (thin, over, and the ceiling) · DENSITY per block and "
          "per prompt, with a sourced reference crediting a demand away · THE ONE-VARIABLE "
          "CORRECTION: block-kind map checked against the blocks TEMPLATES emit, the corpus's "
          "iteration four (state + line = one variable), its iteration two (two = fail), camera "
          "vs @reference, a reference swap, a rewrite, the 'better' note, and a reroll · the MULTISHOT correction, [STAGES] field by field (one character across two stages plus her line, a hand-off, camera + event = two, timing, transitions, ambience vs line, a binding-only reference swap, an added stage) · FORM MULTISHOT: "
          "a clean 3-stage sequence and the tag map, then budgets that gap or miss the duration, a "
          "stage with no end state, two moves in a stage, a missing cut, a tag past the inputs, a "
          "range binding, a frequency, a line twice, an end frame on a reference-mode model, the "
          "type/form pairing, a prop with no owner, a line across a boundary · v2.45: the MODEL's ceiling (Kling 3.0 2,500, "
          "MiniMax H3 7,000, Wan 3.0 20,000 truncating, Kling 4.0's mixed English/non-English rule, the house 2,500 for "
          "Soul/FLUX/Cinema Studio, multi-shot 3,900 and Kling's 512-per-shot), the negative cap and channel, the IMAGE EDIT "
          "(kind: edit — blocks, KEEP coverage, CHANGE specifics, REFERENCES nots, OUTPUT, the floor, use: target, an "
          "edit written as a frame), the DETAIL SCORE (frame, clip, edit; an edit-as-frame named), filler, 'watermark', "
          "signs under a text ban, a sounding clip with no 'no music', the framing line for video + image references · "
          "v2.46.1: the GENJUTSU spec (kind: genjutsu — full and Lite, motion and swap, the floor, the source range, the one "
          "source video, rights, references, free_gens, [QA], [PROMPT], the roster failing closed)")
    return 0


def _selftest_genjutsu() -> None:
    """v2.46.1 — `kind: genjutsu`: the template passes; every field that is wrong fails by name; full points at Lite."""
    import tempfile
    global _rates
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d_ in ("00-brief", "01-script/prompts", "02-startframes", "04-plates"):
            os.makedirs(os.path.join(job, d_))
        open(os.path.join(job, "04-plates", "B1_real_setdown.mov"), "wb").write(b"clip")
        fp = os.path.join(job, "01-script", "prompts", "B1.genjutsu.prompt.md")
        ok = GENJUTSU_TEMPLATE.replace("source_video: <media id>", "source_video: job_src01") \
            .replace("value: <media id>", "value: job_ref01") \
            .replace("source_hash: <sha256 of source_file>",
                     "source_hash: " + sha256_file(os.path.join(job, "04-plates", "B1_real_setdown.mov")))
        L = lambda t_, f_=fp: (open(f_, "w", encoding="utf-8").write(t_), lint(f_, job))[1]
        r = L(ok)
        assert r["ok"], r["fails"]
        sc = r["sidecar"]
        assert sc["kind"] == "genjutsu" and sc["model"] == "hf_mult_motion_control_flash" and sc["tier"] == "lite" \
            and sc["genjutsu_mode"] == "motion" and sc["prompt"] == "" and sc["source_sha256"] and sc["free_gens"] == "prefer" \
            and sc["free_gens_stated"] == 10 and sc["negative_channel"] == "none", sc
        assert not any("plan Lite first" in w for w in r["warns"]), r["warns"]
        cases = [
            (ok.replace("model: hf_mult_motion_control_flash", "model: kling4_0"), "it is a clip model"),
            (ok.replace("model: hf_mult_motion_control_flash", "model: hf_mult_replace_object_flash"), "the model decides the mode"),
            (ok.replace("resolution: 1080p", "resolution: 480p"), "under the 720p video floor"),
            (ok.replace("resolution: 1080p ", "resolution:  "), "Genjutsu has a default the spec never chose"),
            (ok.replace("duration: 5 ", "duration: 20 "), "Lite motion transfer stops at 15 s"),
            (ok.replace("duration: 5 ", "duration: 2 "), "outside hf_mult_motion_control_flash's 4–15 s"),
            (ok.replace("source_video: job_src01", "source_video: <media id>"), "`source_video:`"),
            (ok.replace("04-plates/B1_real_setdown.mov", "04-plates/missing.mov"), "not found under the job"),
            (ok.replace("rights: client-approved", "rights: found online"), "`rights:` must be client-approved or own"),
            (ok.replace("role: image_references, what: subject", "role: video_references, what: subject"), "is a video"),
            (ok.replace("value: job_ref01", "value: <media id>"), "has no media id"),
            (ok.replace("free_gens: prefer", "free_gens: maybe"), "`free_gens:` must be prefer"),
            (ok + "\n[SUPPRESS]\nextra hands\n", "no negative field"),
            (ok + "\n[MOTION]\nshe dances\n", "[QA] and an optional [PROMPT] only"),
            (re.sub(r"(?ms)^\[QA\]\n.*\Z", "", ok), "[QA] missing"),
            (ok.replace("mode: motion ", "mode: dance "), "`mode:` must be motion"),
            (re.sub(r"source_hash: \S+", "source_hash: <sha256 of source_file>", ok), "`source_hash:` missing"),
            (re.sub(r"source_hash: (\S{16})\S*", lambda m_: "source_hash: " + ("0" if m_.group(1)[0] != "0" else "1")
                    + m_.group(1)[1:], ok), "is not the one this spec was written"),
            (ok.replace("mode: motion ", "mode: swap ").replace("model: hf_mult_motion_control_flash",
                        "model: hf_mult_replace_object_flash").replace("resolution: 1080p", "resolution: 480p"),
             "is not one hf_mult_replace_object_flash offers"),
        ]
        for t_, why in cases:
            r_ = L(t_)
            assert not r_["ok"] and any(why in f for f in r_["fails"]), (why, r_["fails"])
        # the file name is part of the contract
        r_ = L(ok, os.path.join(job, "01-script", "prompts", "B1.clip.prompt.md"))
        assert any(GENJUTSU_SUFFIX in f for f in r_["fails"]), r_["fails"]
        # full points at Lite; a [PROMPT] is sent verbatim and warned
        rf = L(ok.replace("model: hf_mult_motion_control_flash", "model: hf_mult_motion_control"))
        assert rf["ok"] and any("plan Lite first" in w and "hf_mult_motion_control_flash" in w and "10 free" in w
                                for w in rf["warns"]), rf["warns"]
        rp = L(ok.replace("[QA]", "[PROMPT]\nShe sets the cup down on the table.\n\n[QA]"))
        assert rp["ok"] and rp["sidecar"]["prompt"] == "She sets the cup down on the table." \
            and rp["sidecar"]["has_prompt"] and any("documents no prompt" in w for w in rp["warns"]), rp
        # the roster fails closed
        _keep = _rates
        try:
            _rates = lambda: None
            assert not genjutsu_models() and not is_genjutsu("hf_mult_motion_control_flash")
            assert any("fails closed" in f for f in L(ok)["fails"])
        finally:
            _rates = _keep


# ----------------------------------------------------------------------------------------------
# THE ONE-VARIABLE CORRECTION
# `[SECONDARY · course notes]`
# A correction is not a rewrite. It names ONE visible miss, states the replacement state, and
# leaves every solved choice byte-identical. The mechanical test the course states: another
# reviewer can identify the single changed variable without searching for unrelated differences.
# This implements that test as a diff between two versions of the same prompt.

VAGUE_RE = re.compile(
    r"\b(?:make it better|better|improve[ds]?|improvement|nicer|more natural(?:ly)?|"
    r"polish(?:ed)?|enhance[ds]?|clean(?:ed)? it up|fix it up|tighten it up|more cinematic|"
    r"more dynamic|punch(?:ier|y)|elevate[ds]?)\b", re.I)

REF_MENTION_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_]{1,40})")

# Blocks whose changes are attributed to a pseudo-subject rather than to a character.
# IMPERSONAL blocks are ABOUT the camera / light / setting, so an @reference appearing in one is a
# thing being referred TO, not the subject being corrected — "Camera inside @car_sheet" is a CAMERA
# variable, not a @car_sheet variable. Found live 2026-09-17: without this split, a pass that moved
# the camera and separately restyled the car read as one variable.
_IMPERSONAL = {
    "CAMERA": "CAMERA", "LENS": "CAMERA", "SHOT": "CAMERA", "FRAMING": "CAMERA",
    "LIGHT": "LIGHT", "LIGHTING": "LIGHT", "GRADE": "LIGHT", "COLOUR": "LIGHT", "COLOR": "LIGHT",
    "ENVIRONMENT": "SETTING", "LOCATION": "SETTING", "SET": "SETTING", "BACKGROUND": "SETTING",
    "AUDIO": "AUDIO", "SFX": "AUDIO", "SOUND": "AUDIO", "MUSIC": "AUDIO",
    "STYLE": "STYLE", "TECHNICAL": "TECHNICAL", "SAFE ZONE": "SAFE ZONE", "SUPPRESS": "SUPPRESS",
    "CONSTRAINTS": "SUPPRESS",   # (v2.71.0) the nouns' home on a model with no negative field
    # form: multishot (references/multishot.md). [STAGES] is personal and diffed FIELD BY FIELD
    # (_stage_subjects); a scripted line inside [SOUND] is DIALOGUE, the rest of [SOUND] is AUDIO.
    "GOAL": "GOAL", "REFERENCES": "REFERENCES", "WHERE": "GEOGRAPHY", "CONSISTENCY": "CONSISTENCY",
    # kind: edit (v2.45) — what the source is, what survives, how it looks out; [CHANGE] stays personal
    "SOURCE": "SOURCE", "KEEP": "KEEP", "OUTPUT": "OUTPUT",
    # form: scene (v2.49.0) — the vendor block template; [FIRST FRAME], [ACTION TIMING] and [PERFORMANCE] stay personal
    "SCENE CONTEXT": "GOAL", "OPTICS": "CAMERA", "FORMAT MODE": "TECHNICAL", "PHYSICS": "PHYSICS",
    "POSITIVE LOCKS": "CONSISTENCY", "TONE": "STYLE", "OUTPUT SETTINGS": "OUTPUT",
}
# PERSONAL blocks are about a performer: attribute to the @reference, sticky across sentences.
# `MOTION` in this skill's clip template is the SUBJECT's motion, not the camera's — the block
# names here are the ones TEMPLATES actually emits, checked against them in selftest().
_DIALOGUE = {"SPEECH", "LINE", "DIALOGUE", "VO", "VOICEOVER"}
_PERSONAL_FALLBACK = "STAGING"


def _block_kind(block: str) -> tuple:
    """(kind, name) — kind is 'impersonal', 'dialogue' or 'personal'."""
    b = (block or "").strip().upper()
    if b in _IMPERSONAL:                      # an exact name first: OUTPUT SETTINGS is not a SET(ting)
        return ("impersonal", _IMPERSONAL[b])
    for k, v in _IMPERSONAL.items():
        if k in b:
            return ("impersonal", v)
    for k in _DIALOGUE:
        if k in b:
            return ("dialogue", "DIALOGUE")
    return ("personal", _PERSONAL_FALLBACK)


# A scripted line as the multishot [SOUND] block writes it, AFTER normalize_prompt (– → -, “ → ").
_SPOKEN_LINE_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:s\s*)?-\s*\d+(?:\.\d+)?\s*s\s+[^:\"]{1,40}:\s*\"")
_CAST_BIND_RE = re.compile(r"^\s*\[Characters?\]\s*(.+?)\s+corresponds?\s+to\b", re.I | re.M)


def _cast_names(*texts) -> set:
    """Character names a multishot [REFERENCES] block binds ('[Characters] Mika corresponds to …')."""
    names = set()
    for t in texts:
        for m in _CAST_BIND_RE.finditer(t or ""):
            for n in re.split(r"\s*(?:,|\band\b|&)\s*", m.group(1)):
                n = n.strip()
                if n and len(n) <= 40 and not n.startswith("@"):
                    names.add(n)
    return names


def _stage_subjects(text_a: str, text_b: str, cast: set) -> set:
    """What a correction to [STAGES] changed, field by field. A stage header carries TIMING and
    CAMERA, the Cut line is a TRANSITIONS variable, and Use / Event / End state are a performance
    change: attributed to the one character it names (so one character fixed across two stages is
    still ONE variable, as in a clip's [PERFORMANCE]), or to that stage when it names none or two
    (a hand-off is one variable of the stage, not two characters). Adding or removing a stage
    re-plans the cut: STAGE PLAN."""
    sa = {s["n"]: s for s in stages_of(text_a or "")}
    sb = {s["n"]: s for s in stages_of(text_b or "")}
    out = set()
    if set(sa) != set(sb):
        out.add("STAGE PLAN")
    norm = lambda s: normalize_prompt(s or "").lower()
    strip_fields = lambda body: re.sub(r"^\s*(?:Use|Event|End\s*state|Cut)\s*:.*$", "", body or "",
                                       flags=re.I | re.M)
    for n in sorted(set(sa) & set(sb)):
        x, y = sa[n], sb[n]
        if (x["t0"], x["t1"]) != (y["t0"], y["t1"]):
            out.add("TIMING")
        if norm(x["shot"]) != norm(y["shot"]):
            out.add("CAMERA")
        if norm(x["cut"]) != norm(y["cut"]):
            out.add("TRANSITIONS")
        touched = []
        for k in ("event", "end"):
            if norm(x[k]) != norm(y[k]):
                touched += [x[k], y[k]]
        ua = {norm(i) for i in (x["use"] or "").split(",") if i.strip()}
        ub = {norm(i) for i in (y["use"] or "").split(",") if i.strip()}
        touched += sorted(ua ^ ub)
        if norm(strip_fields(x["body"])) != norm(strip_fields(y["body"])):
            touched += [strip_fields(x["body"]), strip_fields(y["body"])]
        if not touched:
            continue
        blob = " ".join(touched)
        named = {c for c in cast if re.search(rf"(?<![\w@]){re.escape(c)}\b", blob, re.I)}
        out.add("@" + named.pop() if len(named) == 1 else f"STAGE {n}")
    return out


def _sentences(text: str) -> list:
    """Normalised sentences. The unit of a correction: small enough that a one-clause change is
    visible, large enough that re-wrapping a paragraph is not reported as a change."""
    t = normalize_prompt(text or "")
    if not t:
        return []
    parts, buf = [], ""
    # a sentence may end INSIDE a quotation — `…on you?"` ends a line as surely as `…on you?`
    for piece in re.split(r"(?:(?<=[.;!?])|(?<=[.;!?]\")|(?<=[.;!?]'))\s+(?=[A-Z@\"'(\[])", t):
        buf = (buf + " " + piece).strip() if buf else piece
        # never split inside a quotation: "Change what? No." is ONE line, not two sentences.
        if buf.count(chr(34)) % 2 == 0:
            parts.append(buf); buf = ""
    if buf:
        parts.append(buf)
    return [x.strip() for x in parts if x.strip()]


def _subject_of(sentence: str, block: str) -> set:
    """Who or what this sentence is about. In a personal block, named references win — a change to
    a sentence carrying @hero is a change to @hero wherever in the film it sits, which is why a
    performance note touching three shots of one character is still ONE variable."""
    kind, name = _block_kind(block)
    if kind != "personal":
        return {name}
    refs = {"@" + m.group(1) for m in REF_MENTION_RE.finditer(sentence)}
    return refs or {name}


def correction_diff(new_path: str, old_path: str, note: str | None = None,
                    allow: int = 1) -> dict:
    """Compare two versions of one prompt and report what the correction actually did."""
    fails, warns = [], []
    fm_a, body_a = split_front(read(old_path))
    fm_b, body_b = split_front(read(new_path))
    bl_a, bl_b = blocks_of(body_a), blocks_of(body_b)

    # --- frontmatter: the ground the shot stands on -------------------------------------------
    IGNORE_FM = {"version", "v", "date", "iteration", "note", "notes", "supersedes", "hash"}
    fm_changed = []
    for k in sorted(set(fm_a) | set(fm_b)):
        if k in IGNORE_FM:
            continue
        va, vb = fm_a.get(k), fm_b.get(k)
        if va != vb:
            fm_changed.append((k, va, vb))
    refs_changed = [k for k, _, _ in fm_changed if k in ("refs", "reference", "references",
                                                         "elements", "start_frame", "image")]
    tech_changed = [k for k, _, _ in fm_changed if k in ("model", "resolution", "duration",
                                                         "aspect", "fps", "seed", "mode")]

    # --- body: sentence sets per block ---------------------------------------------------------
    kept = changed = added = removed = 0
    subjects: dict = {}
    per_block = []
    cast = _cast_names(bl_a.get("REFERENCES", ""), bl_b.get("REFERENCES", ""))
    for b in sorted(set(bl_a) | set(bl_b)):
        sa, sb = _sentences(bl_a.get(b, "")), _sentences(bl_b.get(b, ""))
        set_a, set_b = set(sa), set(sb)
        same = set_a & set_b
        gone, new = set_a - set_b, set_b - set_a
        kept += len(same); removed += len(gone); added += len(new)
        changed += max(len(gone), len(new))
        if gone or new:
            per_block.append({"block": b, "kept": len(same),
                              "removed": sorted(gone), "added": sorted(new)})
        # Subject attribution is STICKY within a block: a sentence with no @reference is about
        # whoever the previous sentence was about. Found live 2026-09-17 — the corpus's own
        # one-variable pass reads as TWO variables without this, because the performance note
        # ("She is pressed back into the seat...") sits in the sentence AFTER the one naming her.
        kind, pseudo = _block_kind(b)
        if b.strip().upper() == "STAGES":
            if gone or new:
                for subj in _stage_subjects(bl_a.get(b, ""), bl_b.get(b, ""), cast) or {"STAGING"}:
                    subjects.setdefault(subj, set()).add(b)
            continue
        if pseudo == "AUDIO":
            for sent in list(gone) + list(new):
                subj = "DIALOGUE" if _SPOKEN_LINE_RE.search(sent) else "AUDIO"
                subjects.setdefault(subj, set()).add(b)
            continue
        flow, last = {}, None
        if kind == "personal":
            for sent in sa + sb:
                refs = {"@" + m.group(1) for m in REF_MENTION_RE.finditer(sent)}
                if refs:
                    last = refs
                flow[sent] = refs or last
        for sent in list(gone) + list(new):
            for subj in (flow.get(sent) or _subject_of(sent, b)):
                subjects.setdefault(subj, set()).add(b)

    if refs_changed:
        subjects.setdefault("REFERENCES", set()).add("frontmatter")
    if tech_changed:
        subjects.setdefault("TECHNICAL", set()).add("frontmatter")

    # A line change RIDES ALONG with a performance change when exactly ONE character is being
    # corrected — the corpus's iteration four changes "breathlessness, shock, and the shorter
    # line" and calls that one variable, because a line is spoken BY a performer. With zero or
    # two characters in the pass, do not guess a speaker: dialogue stays its own variable.
    _chars = [k for k in subjects if k.startswith("@")]
    if "DIALOGUE" in subjects and len(_chars) == 1:
        subjects[_chars[0]] |= subjects.pop("DIALOGUE")

    total_a = sum(len(_sentences(v)) for v in bl_a.values())
    preserved = round(100.0 * kept / total_a, 1) if total_a else 0.0

    # --- the findings --------------------------------------------------------------------------
    nsub = len(subjects)
    if nsub == 0:
        warns.append("no change: this correction is identical to the version it supersedes — "
                     "nothing was corrected, and a regenerate at the same prompt is a reroll, "
                     "not an iteration (ai-generation.md: say which one you are doing)")
    if nsub > allow:
        fails.append(
            f"{nsub} variables changed in one pass ({', '.join(sorted(subjects))}) — a correction "
            f"changes {allow}. Split it: the pass that fixes two things at once cannot tell you "
            f"which fix worked, and it will quietly unsolve a choice you already paid for "
            f"(refinement-loop.md §1b). If this really is a deliberate multi-variable pass, "
            f"declare it with --allow {nsub} and say why in the note.")
    # A multishot binds each reference in [REFERENCES] too, so a reference swap that only re-words
    # its own binding line is still ONE ground moving; any other body change alongside it is two.
    body_outside_refs = any(pb["block"].strip().upper() != "REFERENCES" for pb in per_block)
    if refs_changed and body_outside_refs:
        fails.append(
            f"a reference definition changed ({', '.join(refs_changed)}) in the same pass as the "
            f"prompt body — two grounds moved at once. Change the reference, regenerate, SEE what "
            f"the new reference gives you, and only then write a prompt note against it "
            f"(character-and-props.md §8.3b: make the reference more specific instead of "
            f"reopening the shot).")
    if total_a and preserved == 0.0:
        fails.append(
            "0% of the previous prompt survived verbatim — this is a rewrite, not a correction. "
            "Every solved choice in the old version has been re-opened, including the ones nobody "
            "complained about (refinement-loop.md §1b).")
    elif total_a and preserved < 50.0:
        warns.append(f"only {preserved}% of the previous prompt survived verbatim — a correction "
                     f"that keeps less than half is close to a rewrite; check that each re-typed "
                     f"sentence is one you MEANT to reopen")
    if note:
        vm = VAGUE_RE.search(note)
        if vm:
            fails.append(
                f'the correction note says "{vm.group(0)}" — that cannot protect a solved choice. '
                f'Name the visible miss and the intended replacement state instead '
                f'("keep the solved visuals; restore the slight smirk; change only her state to '
                f'pressed back, breathless, light shock"). A generative model given "better" '
                f're-decides everything it was not told to keep.')
        if not REF_MENTION_RE.search(note) and not re.search(r"\b[A-Z]{3,}\b", note):
            warns.append("the correction note names no subject (@reference or BLOCK) — the reviewer "
                         "test is that someone else can find the changed variable without hunting")

    return {"ok": not fails, "fails": fails, "warns": warns,
            "new": new_path, "old": old_path,
            "subjects": {k: sorted(v) for k, v in sorted(subjects.items())},
            "variables": nsub, "allow": allow,
            "kept": kept, "added": added, "removed": removed,
            "preserved_pct": preserved, "blocks": per_block,
            "frontmatter_changed": [{"key": k, "from": a, "to": b} for k, a, b in fm_changed]}


def cmd_correction(new_path: str, old_path: str, note: str | None, allow: int,
                   as_json: bool = False) -> int:
    r = correction_diff(new_path, old_path, note, allow)
    if as_json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["ok"] else 1
    print(f"CORRECTION  {os.path.relpath(r['new'])}  ←  {os.path.relpath(r['old'])}")
    print(f"  variables changed : {r['variables']} (allowed {r['allow']})")
    for k, v in r["subjects"].items():
        print(f"      · {k:<24} in {', '.join(v)}")
    print(f"  preserved verbatim: {r['preserved_pct']}%  "
          f"({r['kept']} sentences kept, {r['added']} added, {r['removed']} removed)")
    for f in r["frontmatter_changed"]:
        print(f"  frontmatter       : {f['key']}: {f['from']!r} → {f['to']!r}")
    for b in r["blocks"]:
        print(f"  [{b['block']}]  kept {b['kept']}")
        for x in b["removed"]:
            print(f"      - {x[:150]}")
        for x in b["added"]:
            print(f"      + {x[:150]}")
    print("  PASS" if r["ok"] else f"  FAIL ({len(r['fails'])} finding(s))")
    for x in r["fails"]:
        print(f"  ✗ {x}")
    for x in r["warns"]:
        print(f"  ~ {x}")
    return 0 if r["ok"] else 1


def plan_rows(folder: str, job_root: str | None = None) -> list:
    """The reference plan as DATA, so the printer, the gate and refsource.py all read one truth.

    One row per planned reference: which shot needs it, what attribute it carries, where it is meant
    to come from, and whether that source exists and is cleared. `state` is the machine-readable
    verdict — `ok` (sourced, has provenance, cleared), `bound` (a media/job id resolved at call
    time), `gap` (declared, nothing behind it yet) or `blocked` (a file exists but cannot be used
    as-is)."""
    files = sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".prompt.md")) \
        if os.path.isdir(folder) else []
    base = job_root or (_job_root_of(files[0]) if files else folder)
    rows = []
    for f in files:
        fm, _ = split_front(read(f))
        shot, kind = fm.get("shot", "?"), fm.get("kind", "?")
        refs = fm.get("refs") if isinstance(fm.get("refs"), list) else []
        if not refs:
            rows.append({"prompt": f, "shot": shot, "kind": kind, "what": "(none)", "role": "—",
                         "source": "—", "state": "none", "detail": "no references planned",
                         "need": "", "path": "", "sidecar": "", "use": ""})
            continue
        for i, r in enumerate(refs, 1):
            what = (r.get("what") or "?").strip().lower()
            role = (r.get("role") or "image").strip().lower()
            use = str(r.get("use", "")).strip().lower()
            need = str(r.get("need", "")).strip()
            row = {"prompt": f, "shot": shot, "kind": kind, "what": what, "role": role,
                   "index": i, "need": need, "use": use, "path": "", "sidecar": ""}
            if r.get("file"):
                src = r["file"]
                full = src if os.path.isabs(src) else os.path.join(base, src)
                row["path"] = full
                if not os.path.isfile(full):
                    row.update(source=src, state="gap", detail="⛔ NOT SOURCED — file missing")
                else:
                    side = _sidecar_of(full) or None
                    row["sidecar"] = side or ""
                    if not side:
                        row.update(source=src, state="blocked", detail="⛔ no provenance")
                    else:
                        try:
                            clr = str(json.load(open(side, encoding="utf-8")).get("clearance", ""))
                        except (json.JSONDecodeError, OSError):
                            clr = "unreadable"
                        if clr.upper().startswith("NOT CLEARED"):
                            if use.startswith("reference"):
                                row.update(source=src, state="ok", detail="reference-only")
                            else:
                                row.update(source=src, state="blocked", detail="⛔ NOT CLEARED")
                        else:
                            row.update(source=src, state="ok", detail="cleared")
            elif r.get("value"):
                row.update(source=str(r["value"]), state="bound",
                           detail="id (bound at call time)")
            elif need:
                row.update(source=f"need: {need}"[:60], state="gap",
                           detail="⛔ NOT SOURCED — declared only")
            else:
                row.update(source="—", state="gap",
                           detail="⛔ NOT PLANNED — no file:, no value:, no need:")
            rows.append(row)
    return rows


def cmd_plan(folder: str, job_root: str | None, as_json: bool = False) -> int:
    """The reference plan across every prompt in a job: what each shot binds, what it carries,
    whether it exists and is cleared. This is the view that makes references a PLANNING artifact
    rather than something judged after the render."""
    if not os.path.isdir(folder) or not any(f.endswith(".prompt.md") for f in os.listdir(folder)):
        print(f"no *.prompt.md in {folder}", file=sys.stderr); return 2
    rows = plan_rows(folder, job_root)
    gaps = [r for r in rows if r["state"] == "gap"]
    blocked = [r for r in rows if r["state"] == "blocked"]
    if as_json:
        json.dump({"folder": folder, "rows": rows, "gaps": len(gaps), "blocked": len(blocked),
                   "ok": not (gaps or blocked)}, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 1 if (gaps or blocked) else 0
    print(f"REFERENCE PLAN — {os.path.relpath(folder)}\n")
    print(f"  {'shot':<8} {'kind':<6} {'attribute':<12} {'role':<7} {'source':<34} status")
    print("  " + "-" * 86)
    for r in rows:
        print(f"  {r['shot']:<8} {r['kind']:<6} {r['what'][:12]:<12} {r['role'][:7]:<7} "
              f"{str(r['source'])[-34:]:<34} {r['detail']}")
    attrs = {}
    for r in rows:
        if r["what"] not in ("(none)", "?"):
            attrs.setdefault(r["what"], set()).add(r["shot"])
    print(f"\n  attributes covered: " + (", ".join(f"{a} ({len(s)} shot{'s' if len(s) > 1 else ''})"
                                                    for a, s in sorted(attrs.items())) or "none"))
    print(f"  {len(gaps)} reference(s) not sourced · {len(blocked)} not cleared")
    if gaps or blocked:
        print("  ⛔ Source and clear every reference BEFORE generating. An asset judged after the "
              "render has already cost credits (stock-sourcing.md §5, §9).")
        if gaps:
            print("  → `refsource.py brief <this folder>` turns each gap into a Pixabay search "
                  "derived from the prompt's own words.")
    return 1 if (gaps or blocked) else 0


GENJUTSU_TEMPLATE = """---
shot: B1                  # the file is 01-script/prompts/B1.genjutsu.prompt.md
kind: genjutsu
mode: motion              # motion = copy the driving video's motion, timing and camera path onto the reference
                          # subjects · swap = replace an object, product, garment or character in the source video
model: hf_mult_motion_control_flash   # Genjutsu Lite (Wan 3.0, source up to 15 s). Full: hf_mult_motion_control.
                          # Swap: hf_mult_replace_object_flash (Lite, Kling 4.0, 720p/1080p) · hf_mult_replace_object
                          # Free generations [stated · 2026-11-03]: Lite 10, full 1 — plan Lite first
resolution: 1080p         # Genjutsu defaults to 720p, under the floor: the spec states it, the call sends it
duration: 5               # seconds of the source video (no duration is sent: the output follows the source)
aspect: 9:16
variants: 1
source_video: <media id>  # the ONE driving/source video, uploaded through the gated media_upload
source_file: 04-plates/B1_real_setdown.mov   # the local file behind it
source_hash: <sha256 of source_file>   # the lint prints it; the approved spec binds this exact video
rights: client-approved   # client-approved | own — only client-approved material is uploaded
free_gens: prefer         # prefer = send use_free_gens:true while free generations last · no
refs:                     # image references only (the subject the motion lands on / the replacement object)
  - role: image_references, what: subject, value: <media id>, file: 02-startframes/B1_subject_v1.png
---
[QA]
Does the output hold the driving video's camera path and timing? motion_track.py on the source and on the take,
compared per frame (t10/t50/t90 of the set-down). Identity and hands against the reference at 1080p. Compare
against the Kling 4.0 take of the same shot before choosing.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="a *.prompt.md file or a folder of them")
    ap.add_argument("--plan", action="store_true",
                    help="print the REFERENCE PLAN across a folder of prompts: what each shot binds, "
                         "what attribute it carries, whether it is sourced and cleared")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--job-root", help="job folder (default: walk up to the folder holding 00-brief/)")
    ap.add_argument("--template", choices=["scene", "scene-file", "dna", "clip", "frame", "edit", "multishot", "family",
                                           "genjutsu"])
    ap.add_argument("--scene", metavar="SCENE", help="lint every shot that names `scene: SCENE` and run the cross-shot checks "
                                                    "(one setup = one lens and distance; the assembled length per shot)")
    ap.add_argument("--against", metavar="OLD.prompt.md",
                    help="THE ONE-VARIABLE CORRECTION: diff this prompt against the version it "
                         "supersedes and report how many variables the pass actually changed, "
                         "and how much solved work it preserved verbatim")
    ap.add_argument("--note", help="the correction note you would send with it — linted for "
                                   "'make it better' language, which cannot protect a solved choice")
    ap.add_argument("--allow", type=int, default=1, metavar="N",
                    help="how many variables this pass INTENDS to change (default 1)")
    ap.add_argument("--route", metavar="MODEL", help="(v2.70.0) which prompt form to write for this model, from its call "
                                                     "contract, before any prose")
    ap.add_argument("--with-refs", action="store_true", help="with --route: the clip binds reference sheets too")
    ap.add_argument("--cards", action="store_true", help="(v2.70.0) one card per roster video model, from the rates "
                                                         "file, with when it was last checked")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cards:
        for c_ in model_cards():
            print(json.dumps(c_, ensure_ascii=False) if a.json else
                  f"{c_['model']}: first frame {c_['first_frame']} · speech {c_['speech']} [{c_['speech_status']}] · "
                  f"capability checked {c_['checked']}" + (f" · {c_['stale']}" if c_['stale'] else ""))
        return 0
    if a.route:
        r = route(a.route, a.with_refs)
        print(json.dumps(r, indent=1) if a.json else
              (f"{a.route}: write the {r['form']} form (`--template {r['template']}`) — {r['why']}" if r.get("template") else
               f"{a.route}: no template chosen ({r['form'] or 'no contract'}) — {r['why']}")
              + f"\n  guardrail nouns: [{r['nouns']['block']}] — {r['nouns']['why']}")
        return 0 if r["form"] else 1
    if a.against:
        if not a.path:
            ap.error("--against needs the new prompt as the positional argument")
        return cmd_correction(a.path, a.against, a.note, a.allow, a.json)
    if a.template:
        print(GENJUTSU_TEMPLATE if a.template == "genjutsu" else TEMPLATES[a.template]); return 0
    if a.scene:
        root = a.job_root or (_job_root_of(a.path) if a.path else os.getcwd())
        rep = scene_report(root, a.scene)
        if a.json:
            print(json.dumps(rep, indent=2, ensure_ascii=False))
        else:
            print(f"SCENE {a.scene}: {'OK' if rep['ok'] else 'NOT OK'} — {len(rep['shots'])} shot(s)")
            for x in rep["shots"]:
                print(f"  {'ok ' if x['ok'] else 'FAIL'} {x['shot']} setup={x['setup'] or '-'} {x['chars']:,} chars, "
                      f"{len(x['refs'])} ref(s)" + ("" if x["ok"] else f" — {x['fails'][0][:140]}"))
            for f_ in rep["fails"]:
                print(f"  FAIL {f_}")
            for w_ in rep["warns"]:
                print(f"  WARN {w_}")
        return 0 if rep["ok"] else 1
    if not a.path:
        ap.print_help(); return 2
    if a.plan:
        return cmd_plan(a.path, a.job_root, a.json)
    files = [a.path] if os.path.isfile(a.path) else \
        sorted(os.path.join(a.path, f) for f in os.listdir(a.path) if f.endswith(".prompt.md")) \
        if os.path.isdir(a.path) else []
    if not files:
        print(f"error: {a.path} is not a prompt file or a folder with *.prompt.md", file=sys.stderr); return 2
    if len(files) == 1 and files[0].endswith(FAMILY_SUFFIX):
        r = lint_family(files[0], a.job_root)
        if a.json:
            print(json.dumps({k: v for k, v in r.items() if k != "members"} |
                             {"members": [{k: v for k, v in m_.items() if k != "result"} for m_ in r["members"]]},
                             indent=2, ensure_ascii=False))
            return 0 if r["ok"] else 1
        print(f"FAMILY {'PASS' if r['ok'] else 'FAIL'}  {os.path.relpath(files[0])}  "
              f"({len(r['members'])} member(s) written and linted)")
        for x in r["fails"]:
            print(f"  ✗ {x}")
        for x in r["warns"]:
            print(f"  ~ {x}")
        for m_ in r["members"]:
            print(f"  {'✓' if m_['ok'] else '✗'} {m_['shot']:<10} {os.path.relpath(m_['file'])}")
        if r["ok"]:
            print("\nEach member is an ordinary linted prompt: `gate.py preflight <SHOT> --kind <kind>` prints "
                  "its call. Sign the start frames on one contact sheet: `gate.py approve family:<NAME> --by "
                  "<name> --quote \"...\" --artifact <sheet> --media-ids S12a=<id>,S12b=<id>`")
        return 0 if r["ok"] else 1
    rc = 0
    results = []
    for f in files:
        r = lint(f, a.job_root)
        ok_path = write_sidecar(f, r["sidecar"])
        r["sidecar_path"] = ok_path
        results.append(r)
        if not r["ok"]:
            rc = 1
        if a.json:
            continue
        rel = os.path.relpath(f)
        if r["ok"]:
            print(f"LINT PASS  {rel}  → {os.path.relpath(ok_path)}")
        else:
            print(f"LINT FAIL  {rel}  ({len(r['fails'])} finding(s))")
        for x in r["fails"]:
            print(f"  ✗ {x}")
        for x in r["warns"]:
            print(f"  ~ {x}")
        if r["ok"] and len(files) == 1 and (r["sidecar"] or {}).get("kind") == "genjutsu":
            sc_ = r["sidecar"]
            print(f"\nGENJUTSU SPEC · {sc_.get('genjutsu_name')} ({sc_.get('tier')}) · {sc_.get('model')} {sc_.get('resolution')} · "
                  f"{GENJUTSU_MODES.get(sc_.get('genjutsu_mode'), '?')}. Next: `gate.py approve genjutsu:{sc_.get('shot')} --by "
                  f"<name> --quote \"...\" --artifact <this file>`, then `gate.py preflight {sc_.get('shot')} --kind genjutsu` "
                  f"prints the whole call" + (" (its PROMPT is the [PROMPT] block)" if sc_.get("has_prompt") else
                                              " (no prompt is sent)"))
        elif r["ok"] and len(files) == 1:
            print("\nPROMPT (paste verbatim — the gate hashes it):")
            print(r["prompt"])
            if r["sidecar"]["negative"]:
                print("\nNEGATIVE (negative_prompt param, where the model exposes one — models_explore):")
                print(r["sidecar"]["negative"])
    if a.json:
        print(json.dumps([{k: v for k, v in r.items() if k != "sidecar"} | {"sidecar": r["sidecar"]}
                          for r in results], indent=2, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
