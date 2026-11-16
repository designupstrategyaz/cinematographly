#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""stage_timer.py — measure where the hours actually go in one video's production.

The capacity model quotes 6.5 h per from-scratch video. That number is MEASURED in aggregate and
completely unallocated: nobody knows which stage eats it. Every optimisation proposed without that
breakdown is a guess, and this skill's own rule is that a check satisfiable without the work gets
satisfied without the work.

So: declare a stage when you start it, and the log writes itself. After a handful of videos the
budget in ../references/production-runbook.md stops being a target and becomes a finding — or gets
falsified, which is more useful.

  start <stage>   begin a stage (implicitly closes the open one)
  stop            close the open stage (use at a real break, or you are timing your lunch)
  note <text>     annotate the open stage
  report          per-stage actuals against the budget, and the total

Stages (the runbook's, in order): route script shotplan vo frames frame-gate clips selects edit
qa deliver.  Anything else is accepted and reported under `other:<name>`.

What it cannot do
-----------------
- **It measures declared wall-clock, not work.** If you leave the desk without `stop`, it charges you
  for the walk. That is the honest trade for a tool with no daemon and no telemetry.
- It cannot attribute time to a CAUSE. A blown `frames` budget could be a bad brief, a bad reference
  or a slow model; the log says which stage, the episode note says why.
- One log per video. It knows nothing about a batch, a month, or a series.

Exit codes: 0 ok - 1 report shows an over-budget total - 2 usage/IO error.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys

LOG = "99-costs/stage-time.jsonl"
ORDER = ["route", "script", "shotplan", "vo", "frames", "frame-gate", "clips", "selects",
         "edit", "qa", "deliver"]
# Minutes. The runbook's variant budget for a 20-40s video on a LOCKED brand. Not measured yet.
BUDGET = {"route": 15, "script": 30, "shotplan": 40, "vo": 10, "frames": 30, "frame-gate": 25,
          "clips": 25, "selects": 20, "edit": 55, "qa": 20, "deliver": 15}
TARGET_MIN = sum(BUDGET.values())  # 285 = 4h45


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def path(root: str) -> str:
    return os.path.join(root, LOG)


def append(root: str, rec: dict) -> None:
    p = path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def read(root: str) -> list[dict]:
    p = path(root)
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def totals(events: list[dict]) -> tuple[dict, str | None]:
    """Sum minutes per stage from an append-only start/stop log. Returns (per-stage, open stage)."""
    per: dict[str, float] = {}
    open_stage, open_at = None, None
    for e in events:
        t = dt.datetime.fromisoformat(e["t"])
        if open_stage is not None:
            per[open_stage] = per.get(open_stage, 0.0) + (t - open_at).total_seconds() / 60.0
            open_stage, open_at = None, None
        if e["ev"] == "start":
            open_stage, open_at = e["stage"], t
    return per, open_stage


def report(root: str, budget: dict) -> int:
    ev = read(root)
    if not ev:
        print(f"no log at {path(root)} — nothing measured yet", file=sys.stderr)
        return 2
    per, still_open = totals(ev)
    if still_open:
        t = dt.datetime.fromisoformat([e for e in ev if e["ev"] == "start"][-1]["t"])
        per[still_open] = per.get(still_open, 0.0) + (dt.datetime.now().astimezone() - t).total_seconds() / 60.0
    names = [s for s in ORDER if s in per] + sorted(k for k in per if k not in ORDER)
    print(f"\n{root} — stage time (minutes)\n" + "-" * 58)
    print(f"  {'stage':<12}{'actual':>8}{'budget':>8}{'delta':>8}")
    worst, worst_d = None, 0.0
    for s in names:
        a = per[s]
        b = budget.get(s)
        d = (a - b) if b is not None else None
        if d is not None and d > worst_d:
            worst, worst_d = s, d
        print(f"  {s:<12}{a:>8.0f}{(b if b is not None else '-'):>8}"
              f"{(f'{d:+.0f}' if d is not None else '-'):>8}")
    tot = sum(per.values())
    tgt = sum(budget.values())
    print("-" * 58)
    print(f"  {'TOTAL':<12}{tot:>8.0f}{tgt:>8}{tot - tgt:>+8.0f}   ({tot/60:.2f} h vs {tgt/60:.2f} h)")
    if still_open:
        print(f"  note: `{still_open}` is still open and is being counted to now")
    if worst:
        print(f"  biggest overrun: {worst} (+{worst_d:.0f} min) <- the stage to attack next")
    print("  (declared wall-clock, not work — see the docstring before drawing conclusions)")
    return 1 if tot > tgt else 0


def selftest() -> int:
    ev = [{"t": "2026-08-29T09:00:00+00:00", "ev": "start", "stage": "script"},
          {"t": "2026-08-29T09:30:00+00:00", "ev": "start", "stage": "frames"},
          {"t": "2026-08-29T10:15:00+00:00", "ev": "stop", "stage": None}]
    per, open_s = totals(ev)
    assert open_s is None
    assert round(per["script"]) == 30 and round(per["frames"]) == 45
    per2, open2 = totals(ev[:2])
    assert open2 == "frames" and round(per2["script"]) == 30 and "frames" not in per2
    assert totals([]) == ({}, None)
    # A stage entered twice accumulates rather than overwriting.
    ev2 = ev[:2] + [{"t": "2026-08-29T09:45:00+00:00", "ev": "start", "stage": "script"},
                    {"t": "2026-08-29T10:00:00+00:00", "ev": "stop", "stage": None}]
    per3, _ = totals(ev2)
    assert round(per3["script"]) == 45 and round(per3["frames"]) == 15
    assert TARGET_MIN == 285
    print("selftest OK — accumulation, open-stage handling, empty log, re-entered stage")
    print(f"NOTE: the {TARGET_MIN}-minute budget is a TARGET, not a measurement. That is the point.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["start", "stop", "note", "report"])
    ap.add_argument("arg", nargs="?", help="stage name for start, text for note")
    ap.add_argument("--root", default=".", help="project folder (default: cwd)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    if a.cmd == "report":
        return report(a.root, BUDGET)
    if a.cmd == "start":
        if not a.arg:
            print("error: start needs a stage name", file=sys.stderr); return 2
        stage = a.arg if a.arg in ORDER else f"other:{a.arg}"
        append(a.root, {"t": now(), "ev": "start", "stage": stage})
        print(f"{stage} started  (budget {BUDGET.get(stage, '-')} min)")
        return 0
    if a.cmd == "stop":
        append(a.root, {"t": now(), "ev": "stop", "stage": None})
        print("stopped"); return 0
    if a.cmd == "note":
        if not a.arg:
            print("error: note needs text", file=sys.stderr); return 2
        append(a.root, {"t": now(), "ev": "note", "stage": None, "text": a.arg})
        print("noted"); return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
