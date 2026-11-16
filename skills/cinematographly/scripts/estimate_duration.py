#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
estimate_duration.py — estimate speech length, video/clip durations, AND generation
credit cost for a promo-video script — and the USD figure when the account's
per-credit price is on file (plan.credit_price_usd).

Cost numbers come from ONE source of truth: costs.<client>.json, read from your client folder
(CINE_CLIENTS, or a `_cine-clients/` folder above the script) and then from the plugin's clients/.
The client profile and SKILL.md reference that file; they do not restate the numbers. Override
per run with --frame / --kling-* (legacy flag names; they set the dialogue-clip and B-roll
rates whatever model is in use) / --retry, or edit the JSON. Verify live spend via the
Higgsfield MCP `transactions` / `balance` — this is a STATIC estimate.

DURATION: parses the house format ([INTRO], [SCENE|SCENĂ N ...], [CTA] blocks with
`Name: dialogue` lines — ANY case), counts spoken words (ignoring (stage directions) and TEXT
overlays), converts to seconds at a conversational rate, adds the settle pad and rounds each line
up to a whole-second clip (never a 5 s grid: B-roll lengths come from the shot list's Dur).
One line = one clip; two speakers in a scene = two clips.

COST: default preset is QUALITY (2026-08-30). The economy preset is still computed and shown for
comparison, but it is NOT a recommendation: a cheaper generation is not a draft of the expensive one,
it is a different take, so the saving buys a different video rather than the same video for less.
Pass --economy only to see what a degraded run would have cost -- e.g. to explain to a client why
the floor costs what it does. See ../references/ai-generation.md -> the quality floor.
B-roll defaults to dialogue_clips + 2. Each clip needs a start frame. A retry factor covers
regenerations. Checks the video against the per-video envelope and (optionally) the monthly total.

Usage:
    python3 estimate_duration.py SCRIPT.md
    python3 estimate_duration.py --economy SCRIPT.md    # comparison only, not a plan
    python3 estimate_duration.py --client acme --broll 8 --monthly-used 1400 SCRIPT.md
    echo "the host: ..." | python3 estimate_duration.py -
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client_files  # noqa: E402  (where a client's cost file is on this machine)
import cost_model    # noqa: E402  (v2.62.0: the one pricing formula, shared with batch_plan.py)

# There is NO built-in cost fallback, deliberately. A missing cost file used to silently borrow one
# client's credit prices for another's quote — a wrong number that looked authoritative. Costs are
# per-account MEASURED actuals, not a vendor rate card (the generation API publishes no per-model
# price), so they can only come from clients/costs.<client>.json. See scripts/refresh_costs.md.
COST_STALE_DAYS = 45


def load_costs(client, *starts):
    """The client's measured costs and where they were read from. `starts`: the script file or the job,
    so a `_cine-clients/` folder above it is found (client_files.py has the order)."""
    path = client_files.find(f"costs.{client}.json", *starts)
    try:
        if not path:
            raise FileNotFoundError(client)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"error: no cost profile costs.{client}.json — refusing to quote.\n"
              f"       ({client_files.where_looked(*starts)})\n"
              f"       Costs are measured per account and are never borrowed from another client.\n"
              f"       Create it from real transactions: see scripts/refresh_costs.md.", file=sys.stderr)
        raise SystemExit(2)
    checked = str(data.get("last_verified") or data.get("checked") or "")
    if checked:
        try:
            import datetime as _dt
            age = (_dt.date.today() - _dt.date.fromisoformat(checked[:10])).days
            if age > COST_STALE_DAYS:
                print(f"warning: costs.{client}.json was last verified {checked} ({age} days ago). "
                      f"Vendor pricing drifts — re-measure before quoting (scripts/refresh_costs.md).",
                      file=sys.stderr)
        except ValueError:
            pass
    else:
        print(f"warning: costs.{client}.json carries no last_verified date — its age is unknown, so "
              f"treat this estimate as ASSUMED, not measured.", file=sys.stderr)
    return data, path


# Name: dialogue — ANY case (fixes the all-caps-only bug). Letters + space/apostrophe/hyphen,
# then ": " (space after colon rules out "0:03" timecodes and TEXT: overlays without a space).
CHAR_RE = re.compile(r"^\s*(?:\*\*)?([A-Za-zĂÂÎȘȚăâîșț][A-Za-zĂÂÎȘȚăâîșț '’\-]{0,29})(?:\*\*)?\s*:\s+(.+)$")
# Recognize English SCENE and Romanian SCENĂ/SCENA as scene blocks.
# (v2.67.0) HOOK is the script-format template's name for the opening block; until now its spoken lines were
# dropped from the estimate (found by the Wave 3 plan review). Read exactly like INTRO, as script_score.py does.
BLOCK_RE = re.compile(r"^\s*(?:\*\*)?\[\s*(INTRO|HOOK|SCEN[EĂA]\s*\d+|CTA)[^\]]*\]", re.IGNORECASE)
# A markdown header / rule / italic-meta line ends the script body — dialogue is only counted
# INSIDE scene blocks, so post-script sections (Wardrobe, Director's note, B-roll, FLAGS) that use
# "Name: description" prose are never mis-counted as spoken lines.
HEADER_RE = re.compile(r"^\s*(#{1,6}\s|-{3,}\s*$|_)")
PAREN_RE = re.compile(r"\([^)]*\)")
# Editorial annotations like "[LOCKED]" / "[LOCKED — verbatim din brief]" trailing a dialogue
# line — production bookkeeping, never spoken and never meant to reach a caption. Distinct from
# BLOCK_RE's "[SCENE n ...]" match, which runs on the scene-header line, not the dialogue text.
BRACKET_RE = re.compile(r"\[[^\]]*\]")
TEXT_OVERLAY_RE = re.compile(r"\bTEXT\b\s*:.*", re.IGNORECASE)
# Words that look like "Name:" but are NOT speakers.
STOP = {"TEXT", "NOTE", "NOTA", "NOTĂ", "INTRO", "HOOK", "CARRIED BY", "CTA", "SCENE", "SCENA", "SCENĂ", "B-ROLL",
        "BROLL", "FIX", "SEV", "TITLE", "LOGO", "CUT", "VISUAL", "VIZUAL", "DECOR", "REGIE",
        "WARDROBE", "BRIEF", "SAVED", "STYLE", "MOTION", "CAMERA", "LIGHTING", "ENVIRONMENT",
        "LOC", "LOCATIE", "LOCAȚIE", "INSERT", "INSERTURI", "DIALOG", "SCENARIU", "CONTROL"}


def is_speaker(name: str) -> bool:
    n = name.strip()
    return n.upper() not in STOP and 1 <= len(n.split()) <= 4


def count_spoken_words(line: str) -> int:
    line = BRACKET_RE.sub(" ", PAREN_RE.sub(" ", line)).replace("„", "").replace("”", "").replace('"', "")
    return len([w for w in re.split(r"\s+", line.strip()) if re.search(r"[A-Za-zĂÂÎȘȚăâîșț0-9]", w)])


def _dialogue(line):
    m = CHAR_RE.match(line)
    if m and is_speaker(m.group(1)):
        return m.group(1).strip(), count_spoken_words(m.group(2))
    return None


def parse(text):
    """Collect dialogue ONLY inside [INTRO]/[SCENE]/[CTA] blocks. A block runs until the next
    block or a markdown header/rule. The scene-header line itself carries visual + TEXT (not
    dialogue), so it isn't parsed for a speaker."""
    scenes, current, in_block = [], None, False
    for raw in text.splitlines():
        mb = BLOCK_RE.match(raw)
        if mb:
            if current and current["lines"]:
                scenes.append(current)
            current = {"name": mb.group(1).upper().replace("SCENA", "SCENĂ"), "lines": []}
            in_block = True
            continue
        if HEADER_RE.match(raw):  # markdown header / --- / _meta ends the script body
            if current and current["lines"]:
                scenes.append(current)
            current, in_block = None, False
            continue
        if not in_block:
            continue
        if TEXT_OVERLAY_RE.match(raw.strip()):
            continue
        d = _dialogue(raw)
        if d:
            current["lines"].append(d)
    if current and current["lines"]:
        scenes.append(current)
    return scenes


def clip_len(sec, clip):
    return max(1, -(-int(sec + 0.999) // clip)) * clip


def main():
    ap = argparse.ArgumentParser(description="Estimate duration + generation credit cost for a "
                                 "promo-video script — plus the USD figure when the account's "
                                 "per-credit price is on file (plan.credit_price_usd).")
    ap.add_argument("path", help="script file, or - for stdin")
    ap.add_argument("--client", required=True,
                    help="REQUIRED. Cost profile: loads clients/costs.<client>.json. There is no "
                         "default and no fallback — quoting one client at another's prices is the "
                         "error this guards against.")
    ap.add_argument("--quality", action="store_true",
                    help="(default since 2026-08-30) use the QUALITY preset")
    ap.add_argument("--economy", action="store_true",
                    help="price the ECONOMY preset instead. NOT a plan: a cheaper generation is a "
                         "different take, not a draft of the expensive one. Use it to show a client "
                         "what the floor is worth, never to choose it")
    ap.add_argument("--wps", type=float, default=2.4)
    # ⛔ 2026-10-26: this was a 5 s grid (every line rounded up to 5, 10, 15 s), so every estimate read as
    # 5 s clips. Roster models take whole seconds; a clip is its line + the leading settle pad, rounded up.
    ap.add_argument("--clip", type=int, default=1,
                    help="round each dialogue clip up to this step in seconds (default 1: roster models take "
                         "whole seconds)")
    ap.add_argument("--lead-in", type=float, default=1.0,
                    help="the settle pad before the line, in seconds (ai-generation.md: the model settles out "
                         "of the start frame)")
    ap.add_argument("--pause", type=float, default=0.6)
    ap.add_argument("--intro", type=float, default=None,
                    help="hook length in seconds. Default comes from the client profile's "
                         "script_params.hook_seconds; there is no house figure — 6-7s is one "
                         "client's answer, not a rule (references/persuasion-psychology.md section 1).")
    ap.add_argument("--cta", type=float, default=None,
                    help="CTA length in seconds. Default from the client profile's "
                         "script_params.cta_seconds. Note a CTA *card* is forbidden by some client "
                         "profiles — this is spoken-CTA time, not an end card.")
    ap.add_argument("--broll", type=int, default=None, help="B-roll clip count (default: dialogue clips + 2)")
    ap.add_argument("--retry", type=float, default=None)
    ap.add_argument("--kling-dialogue", type=float, default=None)
    ap.add_argument("--kling-broll", type=float, default=None)
    ap.add_argument("--frame", type=float, default=None)
    ap.add_argument("--vo", type=float, default=None)
    ap.add_argument("--monthly-used", type=float, default=None)
    a = ap.parse_args()

    costs, cost_src = load_costs(a.client, a.path)
    plan = costs["plan"]
    P = costs["presets"]
    # Quality is the floor (2026-08-30). --economy is an explicit, loud opt-out for comparison only.
    # (v2.62.0) cost_model picks the preset and prices it, the same way batch_plan.py does.
    try:
        active_name, act = cost_model.pick_preset(costs, economy=a.economy)
    except KeyError as e:
        print(f"error: costs.{a.client}.json: {e.args[0]}.\n       See clients/costs._TEMPLATE.json for the shape.",
              file=sys.stderr)
        raise SystemExit(2)
    alt_name = "quality" if active_name == "economy" else "economy"
    alt = P.get(alt_name)
    monthly = plan["monthly_credits"]
    # ⛔ These divisors come from a client-authored JSON. A profile that is not a per-video pipeline
    # (a media/stills retainer, a one-off) legitimately has 0 or omits them, and an unguarded divide
    # turns that into a crash instead of an answer. Found by external review 2026-08-30.
    vpm_max = plan.get("videos_per_month_max") or 0
    vpm_min = plan.get("videos_per_month_min") or 0
    envelope = vpm_max > 0 and vpm_min > 0
    env_low = monthly / vpm_max if vpm_max > 0 else None
    env_high = monthly / vpm_min if vpm_min > 0 else None

    # per-unit costs (CLI overrides > active preset)
    # A client JSON missing a preset key must say WHICH key. A KeyError names a Python dict, not the
    # file the user has to edit. (Found 2026-09-01 when a bulk edit dropped a key and every unit test
    # still passed — they exercised load_costs(), never a full run.)
    def with_overrides(preset: dict) -> dict:
        p = dict(preset)
        for key, val in (("start_frame", a.frame), ("broll", a.kling_broll), ("voiceover_line", a.vo), ("retry", a.retry)):
            if val is not None:
                p[key] = val
        if a.kling_dialogue is not None:          # a flat per-clip dialogue price, given on the command line
            p["kling_dialogue"] = a.kling_dialogue
            p.pop("dialogue_clip_per_second", None)
        return p

    eff = with_overrides(act)

    text = sys.stdin.read() if a.path == "-" else open(a.path, encoding="utf-8").read()
    scenes = parse(text)

    total_words = total_speech = 0.0
    open_speech = close_speech = 0.0          # (v2.67.0) the opening and CTA blocks' own speech
    total_clip_s = n_lines = 0
    print(f"{'SCENE':<12}{'lines':>6}{'words':>7}{'speech s':>10}{'clip s':>8}")
    print("-" * 43)
    for s in scenes:
        if not s["lines"]:
            continue
        w = sum(x[1] for x in s["lines"])
        speech = w / a.wps + a.pause * len(s["lines"])
        cl = sum(clip_len(a.lead_in + wl / a.wps + a.pause, a.clip) for _, wl in s["lines"])
        total_words += w; total_speech += speech; total_clip_s += cl; n_lines += len(s["lines"])
        if s["name"].upper() in ("INTRO", "HOOK"):
            open_speech += speech
        elif s["name"].upper() == "CTA":
            close_speech += speech
        print(f"{s['name']:<12}{len(s['lines']):>6}{int(w):>7}{speech:>9.1f}{cl:>8}")
    print("-" * 43)
    print(f"{'TOTAL':<12}{n_lines:>6}{int(total_words):>7}{total_speech:>9.1f}{total_clip_s:>8}")

    if n_lines == 0:
        print()
        print("⚠️  NO DIALOGUE LINES PARSED — this is NOT a $0 video, the parser found nothing.")
        print("    Write each spoken line as `Name: line` on its own line (any case), and use")
        print("    [SCENE n ...] / [SCENĂ n ...] scene headers. Fix the script and re-run.")
        return

    # intro/CTA seconds are per-client (script.<client>.json, or --intro/--cta). ⛔ Same class of bug
    # as the envelope divide: a client-supplied value used without a guard. Refuse with the fix
    # rather than crashing on None.
    if a.intro is None or a.cta is None:
        # (v2.62.0) the message below always pointed here; the numbers are now actually read from it
        sp = client_files.find(f"script.{a.client}.json", a.path)
        if sp and not str(a.client).startswith("_"):     # a template's numbers are placeholders, never a default
            try:
                spec = json.load(open(sp, encoding="utf-8"))
            except (OSError, ValueError):
                spec = {}
            if a.intro is None and isinstance(spec.get("hook_seconds_min"), (int, float)):
                a.intro = float(spec["hook_seconds_min"])
            if a.cta is None and isinstance(spec.get("cta_seconds"), (int, float)):
                a.cta = float(spec["cta_seconds"])
    if a.intro is None or a.cta is None:
        print("error: intro and CTA seconds are per-client and are not set.\n"
              "       Pass --intro <s> --cta <s>, or put hook_seconds_min / cta_seconds in\n"
              "       clients/script.<client>.json (see clients/script._TEMPLATE.json).\n"
              "       ⛔ There is no house default — a 6s hook floor is right for one brief and\n"
              "       fails every script in another. scripts/beat_plan.py derives the structure\n"
              "       from the same numbers.", file=sys.stderr)
        raise SystemExit(2)
    # ⚠ OPEN QUESTION for the owner (Wave 3 build review, 2026-11-14): the client's intro and CTA seconds are added on
    # top of ALL speech, including the opening and CTA blocks' own speech, which may count those seconds twice. Left
    # as it was: changing it changes every quote, so it is a decision of its own. open_speech/close_speech are kept
    # so the answer is one line either way.
    rec = a.intro + total_speech + a.cta
    dialogue_clips = n_lines
    broll = a.broll if a.broll is not None else dialogue_clips + 2

    print()
    print("── Duration ─────────────────────────────")
    print(f"Spoken words:          {int(total_words)}")
    print(f"Est. speech time:      {total_speech:.0f}s  (@ {a.wps} w/s + {a.pause}s/line)")
    print(f"Recommended video len: {rec*1.12:.0f}s  (intro {a.intro:.0f} + speech + CTA {a.cta:.0f} + ~12%)")
    if rec * 1.12 > 62:
        print("⚠ Over ~60s — trim a line or scene; short-form retention drops past 60s.")

    frames = dialogue_clips + broll
    r = cost_model.video_credits(eff, dialogue_clips, float(total_clip_s), broll)
    total = r["total"]

    print()
    print(f"── Credit cost — ACTIVE preset: {active_name.upper()} (client: {a.client}) ──")
    print(f"Dialogue clips:  {dialogue_clips:>3} ({r['dialogue_basis']}) = {r['dialogue']:>7.0f}")
    print(f"B-roll clips:    {broll:>3} × {float(eff['broll']):g}   = {r['broll']:>7.0f}")
    print(f"Start frames:    {frames:>3} × {float(eff['start_frame']):g}    = {r['frames']:>7.0f}")
    print(f"Voiceover:       {dialogue_clips:>3} × {float(eff['voiceover_line']):g}  = {r['voiceover']:>7.1f}")
    print(f"Retry ×{r['retry']:g} on clips+frames             = {r['retakes']:>7.0f}")
    print(f"{'':─<41}")
    print(f"ESTIMATED TOTAL ({active_name}):        {total:>7.0f} credits")

    # comparison with the other preset (same script)
    if alt:
        other_total = cost_model.video_credits(with_overrides(alt), dialogue_clips, float(total_clip_s), broll)["total"]
        econ, qual = (total, other_total) if active_name == "economy" else (other_total, total)
        print()
        print("── Economy vs Quality (NOT the same video — see the quality floor) ──")
        print(f"Economy: {econ:>6.0f} cr   |   Quality: {qual:>6.0f} cr   |   saving: {qual-econ:>4.0f} cr "
              f"({(100*(qual-econ)/qual) if qual else 0:.0f}%)")
    print("Note: the DIALOGUE MODEL is now the dominant lever — audio-driven lipsync is a more")
    print("      expensive tier than a silent generation, and it is not the place to economise.")
    print("      Save on B-roll and retries instead — and check the client profile before dropping")
    print("      generation resolution; some accounts require generating at exactly delivery size.")

    # ⛔ Credits are not money. The same generation costs ~2.1x more on an entry plan than on annual
    # top tier, so a client quote in credits is not a quote. Printed only when the account's real
    # per-credit price is on file — never derived from a published plan table (they disagree with
    # each other and with the account).
    usd = plan.get("credit_price_usd") or 0
    if usd <= 0:      # (v2.62.0) say it, rather than silently printing credits only
        print()
        print("⚠ No per-credit price on file (plan.credit_price_usd is 0), so this is credits, not money. "
              "Derive it from the invoice (monthly price ÷ monthly credits) before quoting a client.")
    if usd > 0:
        print()
        print(f"In money: {total * usd:,.2f} USD at {usd:.4f}/credit "
              f"({monthly * usd:,.0f}/mo for {monthly:,} credits)")
        print("   ⛔ Per-credit price is plan-dependent — the same video costs about twice as much\n"
              "   on an entry tier. Confirm against the invoice before quoting.")
    print()
    if not envelope:
        print(f"Per-video envelope: not applicable — {a.client} declares no videos/month "
              f"(videos_per_month_min/max is 0 or absent).")
        print("   A profile without a per-video cadence is a retainer or a one-off, not a pipeline;\n"
              "   the per-video budget check is skipped rather than invented.")
    else:
        print(f"Per-video envelope: {env_low:.0f}–{env_high:.0f} cr "
              f"({monthly}/mo ÷ {vpm_max}→{env_low:.0f}, ÷ {vpm_min}→{env_high:.0f})")
        if total <= env_low:
            print(f"✅ Fits the {vpm_max}-videos/month pace (≤{env_low:.0f}).")
        elif total <= env_high:
            print(f"🟡 Fits {vpm_min}/mo but not {vpm_max}/mo. Trim clips/retries.")
        else:
            print(f"🔴 OVER the per-video budget (>{env_high:.0f}). Cut B-roll, drop a line, or lower --retry.")

    if a.monthly_used is not None:
        remaining = monthly - a.monthly_used
        after = remaining - total
        print()
        print(f"Monthly: used {a.monthly_used:.0f} / {monthly} → {remaining:.0f} left; after this video: {after:.0f}")
        print("🔴 Would exceed the monthly budget." if after < 0 else f"   ~{remaining/total:.1f} more videos affordable this month.")

    print()
    print(f"(Static estimate. Costs from {os.path.basename(cost_src)}; verify live via Higgsfield `transactions`/`balance`.)")


if __name__ == "__main__":
    main()
