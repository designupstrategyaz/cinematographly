#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""shot_manifest.py — create, append to, validate, and report on a project's shot manifest.

The manifest (pm-workflow.md § The shot manifest) is the lineage record: every generated asset,
linked to the exact payload that produced it. This tool is the manifest's CONSUMER — the thing that
makes it fail loudly instead of rotting — and the producer of the cost actuals that calibrate
estimates and the retake-economics table.

Usage
-----
  python3 shot_manifest.py init   --project <dir>
  python3 shot_manifest.py add    --project <dir> --shot S1-C1 --kind dialogue \\
        --file 03-clips/S1-C1_host_seedance_v1.mp4 --model seedance_2_5 --model-date 2026-08 \\
        --prompt-file 01-script/MASTER-image-prompts-all-scenes.md --start-frame 02-startframes/S1-C1_...png \\
        --vo 05-voice/S1-C1_host_tasha_v1.wav --cost 12.5 [--seed 1234] [--retake-of S1-C1#1] [--note "..."]
  python3 shot_manifest.py status --project <dir> --shot S1-C1 --set select   # pending/pass/retake/select/backup
  python3 shot_manifest.py validate --project <dir>       # schema + files exist + retake chains resolve
  python3 shot_manifest.py report --project <dir>         # cost actuals per kind, retake rates
  python3 shot_manifest.py report --project <dir> --json
  python3 shot_manifest.py scorecard --project <dir>   # (3.1) at close: yield, retakes, cost per kept take/second

The file is memory/…-independent: SHOTS-<SLUG>.json in the project root (slug inferred from the
folder name after 'Proiect-Video-N-'). Append-only in spirit: 'add' never overwrites an id — a
regeneration is a NEW row with --retake-of pointing at the old one, which is what makes the
one-variable-per-retake rule auditable and the retake counter countable.

Exit codes: 0 ok · 1 validation problems · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys

KINDS = ("dialogue", "reaction", "insert", "broll", "frame", "voice")
STATUSES = ("pending", "pass", "retake", "select", "backup")


def manifest_path(project: str) -> str:
    slug = os.path.basename(os.path.normpath(project))
    for pre in ("Proiect-Video-", "Project-"):
        if slug.startswith(pre):
            parts = slug[len(pre):].split("-", 1)
            slug = parts[1] if len(parts) == 2 else parts[0]
    return os.path.join(project, f"SHOTS-{slug.upper()}.json")


def load(project: str) -> tuple[str, dict]:
    p = manifest_path(project)
    if not os.path.exists(p):
        print(f"error: no manifest at {p} — run: shot_manifest.py init --project <dir>", file=sys.stderr)
        raise SystemExit(2)
    with open(p, encoding="utf-8") as fh:
        return p, json.load(fh)


def save(p: str, data: dict) -> None:
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, p)


def next_id(rows: list, shot: str) -> str:
    n = sum(1 for r in rows if r["shot"] == shot)
    return f"{shot}#{n + 1}"


def cmd_init(a) -> int:
    p = manifest_path(a.project)
    if os.path.exists(p):
        print(f"already exists: {p}")
        return 0
    save(p, {"created": dt.date.today().isoformat(),
             "note": "Lineage per generated asset. A regeneration is a NEW row with retake_of set. "
                     "See references/pm-workflow.md § The shot manifest.",
             "rows": []})
    print(f"created {p}")
    return 0


def cmd_add(a) -> int:
    p, d = load(a.project)
    rid = next_id(d["rows"], a.shot)
    row = {"id": rid, "shot": a.shot, "kind": a.kind, "file": a.file,
           "model": a.model, "model_date": a.model_date, "seed": a.seed,
           "prompt_file": a.prompt_file, "start_frame": a.start_frame,
           "references": a.reference or [], "vo": a.vo,
           "cost_credits": a.cost, "qa_status": "pending",
           "retake_of": a.retake_of, "note": a.note,
           "added": dt.datetime.now().isoformat(timespec="seconds")}
    d["rows"].append(row)
    save(p, d)
    retakes = rid.split("#")[1]
    print(f"added {rid}" + (f"  (attempt {retakes} of this shot"
          + (" — RETAKE CAP: past 2, change the shot concept, don't re-roll)" if int(retakes) > 2 else ")")))
    return 0


def cmd_status(a) -> int:
    if a.set not in STATUSES:
        print(f"error: status must be one of {STATUSES}", file=sys.stderr)
        return 2
    p, d = load(a.project)
    hits = [r for r in d["rows"] if r["shot"] == a.shot or r["id"] == a.shot]
    if not hits:
        print(f"error: no row for {a.shot}", file=sys.stderr)
        return 2
    hits[-1]["qa_status"] = a.set          # latest attempt of that shot
    save(p, d)
    print(f"{hits[-1]['id']} -> {a.set}")
    if a.set in ("pass", "select"):
        print("  reminder: a pass needs its observation line in 09-qa/QA-LOG.md (qa_log.py) — "
              "the checkmark is not the evidence, the observation is.")
    return 0


def cmd_validate(a) -> int:
    p, d = load(a.project)
    probs = []
    ids = {r["id"] for r in d["rows"]}
    for r in d["rows"]:
        for k in ("id", "shot", "kind", "file", "model", "qa_status"):
            if not r.get(k):
                probs.append(f"{r.get('id','?')}: missing {k}")
        if r.get("kind") not in KINDS:
            probs.append(f"{r['id']}: unknown kind {r.get('kind')!r}")
        if r.get("qa_status") not in STATUSES:
            probs.append(f"{r['id']}: unknown qa_status {r.get('qa_status')!r}")
        if r.get("file") and not os.path.exists(os.path.join(a.project, r["file"])):
            probs.append(f"{r['id']}: file not on disk: {r['file']}")
        if r.get("retake_of") and r["retake_of"] not in ids:
            probs.append(f"{r['id']}: retake_of {r['retake_of']!r} not in manifest")
        if r.get("kind") == "dialogue" and not r.get("vo"):
            probs.append(f"{r['id']}: dialogue row with no vo — Path A needs the VO file; "
                         f"Path B note it in 'note' (native audio)")
    print(f"validate — {len(d['rows'])} row(s) in {os.path.basename(p)}")
    for x in probs:
        print("  PROBLEM:", x)
    print("  " + ("FAIL" if probs else "OK"))
    return 1 if probs else 0


def cmd_report(a) -> int:
    p, d = load(a.project)
    rows = d["rows"]
    by = {}
    for r in rows:
        k = r["kind"]
        b = by.setdefault(k, {"n": 0, "cost": 0.0, "retakes": 0, "selects": 0})
        b["n"] += 1
        b["cost"] += float(r.get("cost_credits") or 0)
        if r.get("retake_of"):
            b["retakes"] += 1
        if r["qa_status"] == "select":
            b["selects"] += 1
    out = {k: {"assets": v["n"], "total_credits": round(v["cost"], 1),
               "avg_credits_incl_retakes": round(v["cost"] / max(1, v["n"] - v["retakes"]), 1),
               "retake_rate": round(v["retakes"] / v["n"], 2) if v["n"] else 0.0,
               "selects": v["selects"]} for k, v in sorted(by.items())}
    total = round(sum(float(r.get("cost_credits") or 0) for r in rows), 1)
    if a.json:
        print(json.dumps({"per_kind": out, "total_credits": total, "rows": len(rows)}, indent=2))
        return 0
    print(f"cost actuals — {os.path.basename(p)}  ({len(rows)} rows, {total} cr total)\n" + "-" * 66)
    print(f"  {'kind':<10} {'assets':>6} {'credits':>9} {'avg/shot*':>10} {'retake%':>8} {'selects':>8}")
    for k, v in out.items():
        print(f"  {k:<10} {v['assets']:>6} {v['total_credits']:>9} {v['avg_credits_incl_retakes']:>10}"
              f" {int(v['retake_rate']*100):>7}% {v['selects']:>8}")
    print("  (*avg per final shot, retake cost folded in — this is the number that calibrates")
    print("   estimate_duration.py and the quote. Provenance: MEASURED. Reconcile against the")
    print("   Higgsfield ledger with reconcile_costs.py; this file is lineage, that one is money.)")
    return 0


def probe_seconds(path: str) -> float | None:
    import subprocess
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1",
                            path], capture_output=True, text=True, timeout=20)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def scorecard(project: str, rows: list, seconds=probe_seconds) -> dict:
    """(3.1) The job-close scorecard, derived from the manifest (one row per take): what was generated, what was kept,
    what a kept take and a kept second cost. Kept = every `select`; a shot with no select keeps ONE `pass` take (3.1
    review: several passing takes of one shot are not several kept takes). Nothing here is typed by hand."""
    vids = [r for r in rows if r.get("kind") != "voice" and r.get("shot")]      # a row without a shot is not a take
    kept = [r for r in vids if r.get("qa_status") == "select"]
    _sel = {r["shot"] for r in kept}
    for sh in sorted({r["shot"] for r in vids} - _sel):
        _p = [r for r in vids if r["shot"] == sh and r.get("qa_status") == "pass"]
        kept += _p[-1:]
    cost = round(sum(float(r.get("cost_credits") or 0) for r in rows), 2)
    shots = sorted({r["shot"] for r in vids})
    retakes = {sh: sum(1 for r in vids if r["shot"] == sh and r.get("retake_of")) for sh in shots}
    secs = [seconds(os.path.join(project, r["file"])) for r in kept if r.get("file")]
    known = [x for x in secs if x]
    return {"takes": len(vids), "kept": len(kept), "shots": len(shots), "credits": cost,
            "yield_pct": round(100.0 * len(kept) / len(vids), 1) if vids else None,
            "retakes_per_shot": round(sum(retakes.values()) / len(shots), 2) if shots else None,
            "credits_per_kept_take": round(cost / len(kept), 2) if kept else None,
            "kept_seconds": round(sum(known), 2) if known else None,
            "credits_per_kept_second": round(cost / sum(known), 2) if known and len(known) == len(kept) else None,
            "most_retaken": sorted(retakes.items(), key=lambda kv: -kv[1])[:3]}


def write_scorecard(project: str, sc: dict) -> str:
    d = os.path.join(project, "99-costs"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "SCORECARD.md")
    rows = [("Takes generated", sc["takes"]), ("Takes kept", sc["kept"]),
            ("Yield", f"{sc['yield_pct']} %" if sc["yield_pct"] is not None else "n/a (no takes)"),
            ("Retakes per shot", sc["retakes_per_shot"]), ("Credits spent (manifest)", sc["credits"]),
            ("Credits per kept take", sc["credits_per_kept_take"]),
            ("Kept seconds", sc["kept_seconds"] if sc["kept_seconds"] is not None else "unknown (files not probed)"),
            ("Credits per kept second", sc["credits_per_kept_second"] if sc["credits_per_kept_second"] is not None
             else "unknown")]
    body = ("# Job scorecard (derived from the shot manifest at close)\n\n| | |\n|---|---|\n"
            + "".join(f"| {k} | {v} |\n" for k, v in rows)
            + ("\nMost retaken: " + ", ".join(f"{s} ({n})" for s, n in sc["most_retaken"] if n) + "\n"
               if any(n for _, n in sc["most_retaken"]) else ""))
    open(p, "w", encoding="utf-8").write(body)
    return p


def cmd_scorecard(a) -> int:
    _, d = load(a.project)
    sc = scorecard(a.project, d.get("rows") or [])
    p = write_scorecard(a.project, sc)
    print(json.dumps(sc, indent=1) if a.json else open(p, encoding="utf-8").read())
    return 0


def selftest() -> int:
    rows = [{"shot": "S1", "kind": "dialogue", "file": "a.mp4", "cost_credits": 10, "qa_status": "retake"},
            {"shot": "S1", "kind": "dialogue", "file": "b.mp4", "cost_credits": 10, "qa_status": "select",
             "retake_of": "S1#1"},
            {"shot": "S2", "kind": "broll", "file": "c.mp4", "cost_credits": 5, "qa_status": "pass"},
            {"shot": "S2", "kind": "voice", "file": "v.wav", "cost_credits": 1, "qa_status": "pending"}]
    sc = scorecard("/x", rows, seconds=lambda p: {"/x/b.mp4": 4.0, "/x/c.mp4": 2.0}.get(p))
    assert sc["takes"] == 3 and sc["kept"] == 2 and sc["credits"] == 26 and sc["yield_pct"] == 66.7, sc
    assert sc["retakes_per_shot"] == 0.5 and sc["credits_per_kept_take"] == 13 and sc["kept_seconds"] == 6.0, sc
    assert sc["credits_per_kept_second"] == 4.33 and sc["most_retaken"][0] == ("S1", 1), sc
    sc3 = scorecard("/x", rows + [{"shot": "S2", "kind": "broll", "file": "d.mp4", "cost_credits": 5, "qa_status": "pass"},
                                  {"kind": "broll", "file": "e.mp4", "qa_status": "select"}], seconds=lambda p: None)
    assert sc3["kept"] == 2 and sc3["takes"] == 4, "(3.1 review) two passes of one shot keep one; a shotless row is skipped"
    import tempfile as _t0
    with _t0.TemporaryDirectory() as _td0:
        assert "n/a (no takes)" in open(write_scorecard(_td0, scorecard(_td0, []))).read(), "no takes: no 'None %'"
    sc2 = scorecard("/x", rows, seconds=lambda p: None)
    assert sc2["credits_per_kept_second"] is None, "unknown durations are said, never guessed"
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = write_scorecard(td, sc)
        assert "| Yield | 66.7 % |" in open(p).read()
    print("selftest OK — the scorecard derives takes, kept takes, yield, retakes per shot and cost per kept take and "
          "second from the manifest; unknown durations are said, never guessed")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc_ = sub.add_parser("scorecard", help="(3.1) the job-close scorecard → 99-costs/SCORECARD.md")
    sc_.add_argument("--project", required=True); sc_.add_argument("--json", action="store_true")
    for name in ("init", "validate", "report"):
        s = sub.add_parser(name); s.add_argument("--project", required=True)
        if name == "report":
            s.add_argument("--json", action="store_true")
    s = sub.add_parser("add"); s.add_argument("--project", required=True)
    s.add_argument("--shot", required=True); s.add_argument("--kind", required=True, choices=KINDS)
    s.add_argument("--file", required=True); s.add_argument("--model", required=True)
    s.add_argument("--model-date", default=None); s.add_argument("--seed", default=None)
    s.add_argument("--prompt-file", default=None); s.add_argument("--start-frame", default=None)
    s.add_argument("--reference", default=None, action="append",
                   help="a file in _reference/ that drove this shot (repeatable). Without it, a "
                        "drifting wardrobe or prop cannot be traced back to the reference that was "
                        "supposed to hold it, and 'which reference produced the good one' becomes "
                        "a memory question.")
    s.add_argument("--vo", default=None); s.add_argument("--cost", type=float, default=None)
    s.add_argument("--retake-of", default=None); s.add_argument("--note", default=None)
    s = sub.add_parser("status"); s.add_argument("--project", required=True)
    s.add_argument("--shot", required=True); s.add_argument("--set", required=True)
    a = ap.parse_args()
    return {"init": cmd_init, "add": cmd_add, "status": cmd_status, "scorecard": cmd_scorecard,
            "validate": cmd_validate, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
