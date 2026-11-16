#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""series_join.py — the fan-in gate: the one stage in the pipeline that trusts no branch.

Per-episode QA checks an episode against ITSELF. Nothing else in the skill checks the episodes
against EACH OTHER, and that is precisely the defect parallelism introduces: N branches each
individually clean, collectively inconsistent. This gate runs once, after every branch reports and
before anything ships. See ../references/series-parallel.md section 6.

The framing is borrowed and deliberate — "you never trust the prior stage." A join that reads the
branches' own verdicts is not a gate, it is a summary.

  check   — run the comparative checks over a batch and write JOIN.md

What it checks (all of it comparative — none of it visible inside one episode)
-----------------------------------------------------------------------------
  1. EVERY branch reported. ⛔ Silence is a FAIL, not a pass — the dropped-branch failure mode.
  2. Invariants version identical across every branch and equal to the batch's.
  3. Every declared master exists on disk and is non-empty.
  4. Integrated loudness spread ACROSS episodes (ffmpeg loudnorm, measure only, no re-encode).
     Each file can pass its own spec while episode 2 sits audibly hotter than episode 1.
  5. Hook and persona collisions across the batch — two episodes shipping the same hook to the
     same persona is a batch-level fact with no per-episode symptom.
  6. A recorded human observation of the identity comparison. Refused unless it NAMES AT LEAST TWO
     EPISODES, because a comparative claim that names one side is not a comparison. That sentence
     cannot be produced without putting the episodes next to each other.

What it cannot do
-----------------
- **It cannot see a face.** Identity, wardrobe and product drift across episodes are an eye check
  against a cross-episode contact sheet (contact_sheet.py). This tool makes recording that check
  the only way to get a verdict; it does not perform it.
- It does not re-run per-episode QA. The ship gate and full card of production-runbook.md section 5
  still apply to every episode. **The join is an addition, never a substitute.**
- It cannot judge whether two different hooks are actually different ideas (slop_check.py cannot
  either — that stays human).
- Per-file spec compliance is export_qc.py's job; single-batch variance is slop_check.py's. This
  gate only asks whether the EPISODES agree with each other.

Usage
-----
  python3 series_join.py check --batch _series/ACME/BATCH-2026-09-A \\
      --obs "ep-04 and ep-06 side by side: same jaw width and brow, guest's collar green in both"
  python3 series_join.py check --batch <dir> --skip-loudness --json

Exit codes: 0 PASS (batch released) · 1 FAIL/refused · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, subprocess, sys

MAX_LUFS_SPREAD = 1.5   # LU across episodes; beyond this the batch is audibly uneven
MIN_OBS_WORDS = 6
INTENTION = re.compile(r"^\s*(looks?\s+(good|fine|ok(ay)?)|consistent|the\s+same|matches|"
                       r"seems?\s+(good|fine|ok)|all\s+good|ok|fine|good|approved|no\s+drift)\s*[.!]?\s*$",
                       re.IGNORECASE)


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def _read_json(p: str) -> dict:
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def measure_lufs(path: str) -> float | None:
    """Integrated loudness, ffmpeg loudnorm measure pass. Mirrors slop_check.py deliberately —
    the scripts are standalone by charter, so the call is repeated rather than imported."""
    try:
        out = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-af", "loudnorm=print_format=json",
                              "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    m = re.findall(r'"input_i"\s*:\s*"(-?[\d.]+)"', out.stderr)
    try:
        return round(float(m[-1]), 1) if m else None
    except ValueError:
        return None


def validate_observation(obs: str, slugs: list[str]) -> str | None:
    """Return a refusal reason, or None if the observation is real. The un-fakeable part is that a
    comparison must name both sides."""
    o = (obs or "").strip()
    if len(o.split()) < MIN_OBS_WORDS:
        return ("the observation is the evidence, and this one is missing or too thin.\n"
                "  Write what you actually saw when the episodes were side by side — e.g.\n"
                "  \"ep-04 and ep-06: same jaw width and brow height, collar green in both, "
                "ep-06 key is a stop warmer\"")
    if INTENTION.match(o):
        return (f"{o!r} is a verdict, not an observation. Name what is IN the frames, in both "
                f"episodes.")
    named = [s for s in slugs if s.lower() in o.lower()]
    if len(named) < 2:
        return ("a comparative check must NAME AT LEAST TWO EPISODES.\n"
                f"  This batch holds: {', '.join(slugs)}\n"
                "  Drift does not exist inside one episode — one episode is self-consistent by\n"
                "  definition. An observation naming one side was not made from a comparison, and\n"
                "  a sentence naming two cannot be written without putting them next to each other.\n"
                "  (series-parallel.md section 3.1)")
    return None


def check(bd: str, obs: str, skip_loudness: bool) -> dict:
    b = _read_json(os.path.join(bd, "BATCH.json"))
    slugs = [e["slug"] for e in b["episodes"]]
    findings: list[str] = []
    branches = []

    for e in b["episodes"]:
        sp = os.path.join(bd, f"ep-{e['slug']}.state")
        if not os.path.isfile(sp):
            findings.append(f"FAIL {e['slug']}: no state file. The branch never reported. "
                            f"Silence is a FAIL — this is the dropped-branch failure.")
            continue
        s = _read_json(sp)
        branches.append(s)
        if not s.get("closed"):
            findings.append(f"FAIL {e['slug']}: branch still open at stage {s.get('stage')!r}. "
                            f"Nothing in the batch ships until every branch reports.")
        if s.get("invariants_version") != b["invariants_version"]:
            findings.append(f"FAIL {e['slug']}: cut under invariants v{s.get('invariants_version')}, "
                            f"batch is v{b['invariants_version']}. A mid-batch bible edit is "
                            f"invisible inside a branch and only visible here.")
        m = s.get("master")
        if not m:
            findings.append(f"FAIL {e['slug']}: no master declared.")
        elif not (os.path.isfile(m) and os.path.getsize(m) > 0):
            findings.append(f"FAIL {e['slug']}: declared master {m!r} is missing or empty.")

    # hook / persona collision — a batch-level fact with no per-episode symptom
    seen: dict[tuple, str] = {}
    for e in b["episodes"]:
        key = (e.get("hook_id"), e.get("persona"))
        if key != (None, None) and key in seen:
            findings.append(f"FAIL {e['slug']} and {seen[key]}: same hook {e.get('hook_id')!r} to the "
                            f"same persona {e.get('persona')!r} in one batch. Shipping both sends the "
                            f"same idea twice to the same audience (series-continuity.md section 4).")
        seen[key] = e["slug"]

    loudness = {}
    if not skip_loudness:
        vals = {}
        for s in branches:
            m = s.get("master")
            if m and os.path.isfile(m):
                v = measure_lufs(m)
                if v is not None:
                    vals[s["slug"]] = v
        loudness = vals
        if len(vals) >= 2:
            spread = max(vals.values()) - min(vals.values())
            loudness["_spread"] = round(spread, 1)
            if spread > MAX_LUFS_SPREAD:
                hi = max(vals, key=vals.get); lo = min(vals, key=vals.get)
                findings.append(f"FAIL loudness spread {spread:.1f} LU across the batch "
                                f"({hi} {vals[hi]}, {lo} {vals[lo]}). Every file can pass its own "
                                f"spec and the batch still play unevenly.")
        elif branches:
            findings.append("NOTE loudness not measured (ffmpeg unavailable, or fewer than two "
                            "masters readable) — the cross-episode level check did not run.")

    refusal = validate_observation(obs, slugs)
    return {"batch": bd, "brand": b["brand"], "invariants_version": b["invariants_version"],
            "episodes": slugs, "branches_reported": len(branches), "loudness": loudness,
            "findings": findings, "observation": obs, "observation_refusal": refusal,
            "verdict": None}


def write_join_md(bd: str, r: dict) -> None:
    with open(os.path.join(bd, "JOIN.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Join gate — {r['brand']} {os.path.basename(bd)}\n\n"
                 f"- run: {now()}\n- invariants: v{r['invariants_version']}\n"
                 f"- episodes: {', '.join(r['episodes'])}\n"
                 f"- branches reported: {r['branches_reported']}/{len(r['episodes'])}\n"
                 f"- **verdict: {r['verdict']}**\n\n## Identity comparison (human)\n\n"
                 f"> {r['observation']}\n\n")
        if r["loudness"]:
            fh.write("## Loudness across episodes\n\n")
            for k, v in r["loudness"].items():
                fh.write(f"- {k}: {v}\n")
            fh.write("\n")
        fh.write("## Findings\n\n")
        fh.write("\n".join(f"- {f}" for f in r["findings"]) if r["findings"]
                 else "- none — the batch is consistent with itself\n")
        fh.write("\n\n⛔ The join is an addition, not a substitute: every episode still carries its\n"
                 "own ship gate and full card (production-runbook.md section 5).\n")


def selftest() -> int:
    import tempfile, shutil
    slugs = ["ep-04", "ep-06"]
    assert validate_observation("", slugs)
    assert validate_observation("looks good", slugs)
    assert validate_observation("consistent", slugs)
    # names only one side -> refused
    assert validate_observation("ep-04 jaw and brow read exactly as the locked reference does", slugs)
    # names both -> accepted
    assert validate_observation(
        "ep-04 and ep-06 side by side: same jaw width, collar green in both, ep-06 key a stop warmer",
        slugs) is None
    root = tempfile.mkdtemp()
    try:
        bd = os.path.join(root, "BATCH-T"); os.makedirs(bd)
        json.dump({"brand": "T", "batch_id": "T", "invariants_version": 3, "max_group": 12,
                   "episodes": [{"slug": "ep-04", "lines": 4, "shots": 4, "variants": 2,
                                 "hook_id": "H1", "persona": "P1"},
                                {"slug": "ep-06", "lines": 4, "shots": 4, "variants": 2,
                                 "hook_id": "H1", "persona": "P1"}]},
                  open(os.path.join(bd, "BATCH.json"), "w"))
        master = os.path.join(root, "m.mp4"); open(master, "w").write("x")
        json.dump({"slug": "ep-04", "invariants_version": 3, "stage": "qa", "closed": True,
                   "master": master}, open(os.path.join(bd, "ep-ep-04.state"), "w"))
        r = check(bd, "ep-04 and ep-06 side by side: jaw and collar match, ep-06 warmer", True)
        assert any("never reported" in f for f in r["findings"]), "silence must FAIL"
        assert any("same hook" in f for f in r["findings"]), "hook collision must FAIL"
        json.dump({"slug": "ep-06", "invariants_version": 2, "stage": "qa", "closed": True,
                   "master": master}, open(os.path.join(bd, "ep-ep-06.state"), "w"))
        r = check(bd, "ep-04 and ep-06 side by side: jaw and collar match, ep-06 warmer", True)
        assert any("batch is v3" in f for f in r["findings"]), "version drift must FAIL"
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("selftest OK — observation refusals (thin / verdict / one-sided), two-episode requirement, "
          "silence-is-FAIL, hook collision, invariants drift")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="run the comparative checks and write JOIN.md")
    c.add_argument("--batch", required=True, help="path to _series/<BRAND>/BATCH-<ID>/")
    c.add_argument("--obs", default="", help="what you saw with the episodes side by side")
    c.add_argument("--skip-loudness", action="store_true", help="skip the ffmpeg pass (slow)")
    c.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd != "check":
        ap.print_help(); return 2
    if not os.path.isfile(os.path.join(a.batch, "BATCH.json")):
        print(f"REFUSED: no BATCH.json in {a.batch}.", file=sys.stderr); return 2

    r = check(a.batch, a.obs, a.skip_loudness)
    if r["observation_refusal"]:
        print(f"REFUSED: {r['observation_refusal']}", file=sys.stderr)
        if r["findings"]:
            print("\n  (mechanical findings, for information — no verdict was issued)", file=sys.stderr)
            for f in r["findings"]:
                print(f"  ! {f}", file=sys.stderr)
        return 1
    r["verdict"] = "FAIL" if r["findings"] else "PASS"
    write_join_md(a.batch, r)
    if a.json:
        print(json.dumps(r, indent=2)); return 1 if r["findings"] else 0
    print(f"\nJOIN — {r['brand']} {os.path.basename(a.batch)}, invariants v{r['invariants_version']}, "
          f"{r['branches_reported']}/{len(r['episodes'])} branches reported")
    if r["loudness"]:
        print("  loudness: " + ", ".join(f"{k} {v}" for k, v in r["loudness"].items()))
    for f in r["findings"]:
        print(f"  ! {f}")
    print(f"\n  VERDICT: {r['verdict']}  (written to JOIN.md)")
    if r["verdict"] == "PASS":
        print("  Batch released. Each episode still ships on its own per-episode evidence.")
    else:
        print("  ⛔ Nothing in this batch ships until the findings are closed. Partial ship is the\n"
              "     failure this gate exists to prevent.")
    return 1 if r["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
