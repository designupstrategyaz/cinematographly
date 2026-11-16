#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""series_batch.py — the cross-episode accumulator: N episodes, three sync points, one durable state.

The runbook batches WITHIN one episode (VO -> frames -> clips, three sync points). This batches
ACROSS episodes: every line of every episode in one audio batch, every shot of every episode in one
image batch, one frame gate for the lot, then one video batch. Human sync points go 3N -> 3.
See ../references/series-parallel.md.

Why the state lives in files
----------------------------
Parallel branches cannot share a conversation; there is only one. They can only share files. A
five-episode batch spans hours and will cross at least one context reset, so a branch that exists
only in the transcript is a branch that is lost. If it is not in `ep-<SLUG>.state`, it did not happen.

  init     — open a batch under _series/<BRAND>/BATCH-<ID>/; REFUSES unless the invariants are frozen
  add      — accumulate one episode into the batch
  plan     — emit the three batches, split into jobs_wait groups of <= 12; stamps planned_at
  advance  — record a branch reaching a stage (job ids, notes)
  close    — close a branch (its master exists and its per-episode QA is done)
  status   — read the files and report; runs the P57 max-age sweep

Refusals (loud, never silent)
-----------------------------
  * `init` when INVARIANTS.md is missing or declares no `invariants-version:` — fanning out before
    the freeze parallelises drift, not production (series-parallel.md section 2).
  * `plan` with fewer than 2 episodes — at N=1 this machinery costs ~10 minutes and buys nothing;
    a single video routes through production-runbook.md unchanged.
  * `add` after `plan` has stamped the batch, unless --reopen (and the reopen is ledgered).
  * `status` reports STALE when a planned batch has sat past --max-age-hours with branches open —
    the orphaned-accumulator failure P57 names by that name.

What it cannot do
-----------------
- **It cannot look at a frame, and it never decides the batch is good.** Every comparative check
  that needs an eye is series_join.py's, and the identity comparison there is a human observation.
- It does not fire anything. It plans groups and records what you say happened; the generation calls
  are the Higgsfield batch tools, and a job id in here is a claim, not proof.
- It cannot tell you N is too large for your attention. The cap of 5 in series-parallel.md is a
  judgement about a reviewable frame gate, not a measurement, and this tool only warns at it.

Exit codes: 0 done · 1 refused/findings · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, sys

MAX_GROUP = 12                 # jobs_wait hard cap
SOFT_EPISODE_CAP = 5           # series-parallel.md section 9 — a gate you cannot review is not a gate
DEFAULT_MAX_AGE_H = 24         # P57 max-age sweep
STAGES = ["planned", "vo", "frames", "frame-gate", "clips", "selects", "edit", "qa", "delivered"]
VERSION_RE = re.compile(r"^invariants-version:\s*(\d+)\s*$", re.M)
# Canonical show id, ETC/MovieLabs episodic form (pm-workflow.md, Naming convention). WARNED, never
# refused: blocking real work over a naming nit is the wrong severity — the registry lint is where it
# is a finding, and name_lint.py is where a FILE name is one.
EPISODE_ID_RE = re.compile(r"^[a-z0-9]{2,8}-\d{5}$")


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def _read_json(p: str) -> dict:
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(p: str, d: dict) -> None:
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2)
        fh.write("\n")


def ledger(batch_dir: str, line: str) -> None:
    p = os.path.join(batch_dir, "LEDGER.md")
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# Batch ledger — append-only\n\n"
                     "One line per dispatcher decision. The dispatcher owns the join; no branch\n"
                     "ships itself (series-parallel.md section 4).\n\n")
        fh.write(f"- {now()} — {line}\n")


def frozen_version(series_dir: str) -> int | None:
    p = os.path.join(series_dir, "INVARIANTS.md")
    if not os.path.isfile(p):
        return None
    m = VERSION_RE.search(open(p, encoding="utf-8").read())
    return int(m.group(1)) if m else None


def groups(n: int, cap: int = MAX_GROUP) -> list[int]:
    """Split n jobs into jobs_wait groups of at most `cap`."""
    out = []
    while n > 0:
        out.append(min(cap, n)); n -= min(cap, n)
    return out


# ---------------------------------------------------------------- commands
def cmd_init(series_dir: str, batch_id: str) -> int:
    if not os.path.isdir(series_dir):
        print(f"REFUSED: {series_dir} is not a series folder. "
              f"Run series_registry.py init --brand <BRAND> first.", file=sys.stderr)
        return 1
    v = frozen_version(series_dir)
    if v is None:
        print("REFUSED: the invariants are not frozen.\n"
              f"  {os.path.join(series_dir, 'INVARIANTS.md')} is missing or declares no "
              "'invariants-version: N'.\n"
              "  Fanning out before the freeze does not parallelise production — it parallelises\n"
              "  drift, and you find it at the join, after the credits are spent.\n"
              "  (series-parallel.md section 2; series-continuity.md section 6.1)", file=sys.stderr)
        return 1
    bd = os.path.join(series_dir, f"BATCH-{batch_id}")
    if os.path.exists(bd):
        print(f"REFUSED: {bd} already exists.", file=sys.stderr); return 1
    os.makedirs(bd)
    _write_json(os.path.join(bd, "BATCH.json"), {
        "brand": os.path.basename(os.path.normpath(series_dir)),
        "batch_id": batch_id, "series_dir": series_dir, "created": now(),
        "invariants_version": v, "max_group": MAX_GROUP, "planned_at": None, "episodes": [],
    })
    ledger(bd, f"batch opened under invariants v{v}")
    print(f"{bd} — opened under invariants v{v}\n"
          f"  add episodes with: series_batch.py add --batch {bd} --episode <SLUG> "
          f"--lines <N> --shots <N>")
    return 0


def cmd_add(bd: str, slug: str, lines: int, shots: int, variants: int,
            hook: str | None, persona: str | None, reopen: bool) -> int:
    bp = os.path.join(bd, "BATCH.json")
    if not os.path.isfile(bp):
        print(f"REFUSED: no BATCH.json in {bd}.", file=sys.stderr); return 2
    b = _read_json(bp)
    if b.get("planned_at") and not reopen:
        print(f"REFUSED: this batch was planned at {b['planned_at']}; adding an episode now changes\n"
              "  a plan the branches are already working from. Re-run with --reopen if that is\n"
              "  genuinely what you mean — the reopen is written to the ledger.", file=sys.stderr)
        return 1
    if any(e["slug"] == slug for e in b["episodes"]):
        print(f"REFUSED: episode {slug} is already in this batch.", file=sys.stderr); return 1
    b["episodes"].append({"slug": slug, "lines": lines, "shots": shots, "variants": variants,
                          "hook_id": hook, "persona": persona, "added": now()})
    if reopen:
        b["planned_at"] = None
    _write_json(bp, b)
    _write_json(os.path.join(bd, f"ep-{slug}.state"), {
        "slug": slug, "invariants_version": b["invariants_version"], "stage": "planned",
        "job_ids": {}, "approved_frames": 0, "master": None, "notes": [],
        "closed": False, "updated": now(),
    })
    ledger(bd, f"episode {slug} accumulated ({lines} lines, {shots} shots x{variants})"
               + (" [REOPENED PLAN]" if reopen else ""))
    n = len(b["episodes"])
    print(f"{slug} added — batch now holds {n} episode(s)")
    if not EPISODE_ID_RE.match(slug):
        print(f"  ! {slug!r} is not the canonical <brand>-<SS><EEE> show id (e.g. acme-01007).\n"
              f"    Accepted anyway — but every generated file is prefixed with this, and a batch\n"
              f"    returns all episodes' clips into one place, where two shots called S1-C1 are a\n"
              f"    collision rather than a set. (pm-workflow.md, Naming convention.)")
    if n > SOFT_EPISODE_CAP:
        print(f"  ! {n} episodes exceeds the soft cap of {SOFT_EPISODE_CAP}. The frame gate is one\n"
              f"    human review of every episode side by side; past ~{SOFT_EPISODE_CAP} it stops\n"
              f"    being a gate and becomes paperwork (series-parallel.md section 9).")
    return 0


def plan(bd: str) -> dict:
    b = _read_json(os.path.join(bd, "BATCH.json"))
    eps = b["episodes"]
    a_jobs = sum(e["lines"] for e in eps)
    b_jobs = sum(e["shots"] * e["variants"] for e in eps)
    c_jobs = sum(e["shots"] for e in eps)
    seq_groups = sum(len(groups(e["lines"])) + len(groups(e["shots"] * e["variants"]))
                     + len(groups(e["shots"])) for e in eps)
    acc_groups = len(groups(a_jobs)) + len(groups(b_jobs)) + len(groups(c_jobs))
    return {
        "brand": b["brand"], "batch_id": b["batch_id"], "invariants_version": b["invariants_version"],
        "episodes": [e["slug"] for e in eps],
        "batches": {
            "A_vo": {"jobs": a_jobs, "groups": groups(a_jobs)},
            "B_frames": {"jobs": b_jobs, "groups": groups(b_jobs)},
            "C_clips": {"jobs": c_jobs, "groups": groups(c_jobs)},
        },
        "human_sync_points": {"sequential": 3 * len(eps), "accumulated": 3},
        "wait_groups": {"sequential": seq_groups, "accumulated": acc_groups},
    }


def cmd_plan(bd: str, as_json: bool) -> int:
    bp = os.path.join(bd, "BATCH.json")
    if not os.path.isfile(bp):
        print(f"REFUSED: no BATCH.json in {bd}.", file=sys.stderr); return 2
    b = _read_json(bp)
    if len(b["episodes"]) < 2:
        print("REFUSED: a batch of one is not a batch.\n"
              "  At N=1 the freeze check and the state files cost about ten minutes and buy nothing\n"
              "  (series-parallel.md section 1.3 — N=1 is measurably WORSE than the plain route).\n"
              "  Route a single video through references/production-runbook.md unchanged.",
              file=sys.stderr)
        return 1
    r = plan(bd)
    b["planned_at"] = now()
    _write_json(bp, b)
    ledger(bd, f"planned: {len(r['episodes'])} episodes, "
               f"A={r['batches']['A_vo']['jobs']} B={r['batches']['B_frames']['jobs']} "
               f"C={r['batches']['C_clips']['jobs']}")
    if as_json:
        print(json.dumps(r, indent=2)); return 0
    print(f"\nBATCH {r['batch_id']} — {r['brand']}, invariants v{r['invariants_version']}, "
          f"{len(r['episodes'])} episodes: {', '.join(r['episodes'])}\n")
    for key, label in (("A_vo", "A · VO           generate_audio_batch"),
                       ("B_frames", "B · Start frames generate_image_batch"),
                       ("C_clips", "C · Clips        generate_video_batch")):
        d = r["batches"][key]
        print(f"  {label}  {d['jobs']:>3} jobs -> {len(d['groups'])} group(s) {d['groups']}")
        if key == "B_frames":
            print("     ⛔ FRAME GATE — one gate, ALL episodes side by side. Drift is comparative:\n"
                  "        it does not exist inside a single episode. contact_sheet.py across the\n"
                  "        batch, then look. This is the one place to spend.")
    print(f"\n  human sync points  {r['human_sync_points']['sequential']} -> "
          f"{r['human_sync_points']['accumulated']}")
    print(f"  jobs_wait groups   {r['wait_groups']['sequential']} -> {r['wait_groups']['accumulated']}")
    print("\n  ⛔ jobs_wait takes at most 12 jobs. Collect indexed job ids and finish with ONE\n"
          "     show_generation_by_ids — never job_display per job.")
    print("  ⛔ No branch ships itself. Delivery is released by series_join.py.\n")
    return 0


def cmd_advance(bd: str, slug: str, stage: str, jobs: str | None, note: str | None) -> int:
    sp = os.path.join(bd, f"ep-{slug}.state")
    if not os.path.isfile(sp):
        print(f"REFUSED: {slug} is not in this batch.", file=sys.stderr); return 1
    if stage not in STAGES:
        print(f"REFUSED: unknown stage {stage!r}. Valid: {', '.join(STAGES)}", file=sys.stderr); return 2
    s = _read_json(sp)
    s["stage"] = stage
    if jobs:
        s["job_ids"][stage] = [j.strip() for j in jobs.split(",") if j.strip()]
    if note:
        s["notes"].append(f"{now()} {stage}: {note}")
    s["updated"] = now()
    _write_json(sp, s)
    ledger(bd, f"{slug} -> {stage}" + (f" ({note})" if note else ""))
    print(f"{slug} -> {stage}")
    return 0


def cmd_close(bd: str, slug: str, master: str) -> int:
    sp = os.path.join(bd, f"ep-{slug}.state")
    if not os.path.isfile(sp):
        print(f"REFUSED: {slug} is not in this batch.", file=sys.stderr); return 1
    s = _read_json(sp)
    s.update({"closed": True, "master": master, "stage": "qa", "updated": now()})
    _write_json(sp, s)
    ledger(bd, f"{slug} CLOSED — master {master} (awaiting join)")
    print(f"{slug} closed. ⛔ Closed is not shipped — series_join.py gates the batch.")
    return 0


def status(bd: str, max_age_h: float) -> dict:
    b = _read_json(os.path.join(bd, "BATCH.json"))
    branches, findings = [], []
    for e in b["episodes"]:
        sp = os.path.join(bd, f"ep-{e['slug']}.state")
        if not os.path.isfile(sp):
            findings.append(f"{e['slug']}: state file missing — the branch has no durable record")
            continue
        s = _read_json(sp)
        branches.append({"slug": s["slug"], "stage": s["stage"], "closed": s["closed"],
                         "invariants_version": s["invariants_version"], "updated": s["updated"]})
        if s["invariants_version"] != b["invariants_version"]:
            findings.append(f"{e['slug']}: cut under invariants v{s['invariants_version']}, "
                            f"batch is v{b['invariants_version']} — STALE branch, do not join")
    open_n = sum(1 for x in branches if not x["closed"])
    stale = False
    if b.get("planned_at") and open_n:
        age = (dt.datetime.now() - dt.datetime.fromisoformat(b["planned_at"])).total_seconds() / 3600
        if age > max_age_h:
            stale = True
            findings.append(f"ORPHANED ACCUMULATOR: planned {age:.1f}h ago, {open_n} branch(es) "
                            f"still open. P57's named failure — the flush never fired. Either fire "
                            f"the batch or close it out; do not let it sit.")
    return {"batch": bd, "brand": b["brand"], "invariants_version": b["invariants_version"],
            "planned_at": b.get("planned_at"), "episodes": len(b["episodes"]),
            "open": open_n, "stale": stale, "branches": branches, "findings": findings}


def cmd_status(bd: str, max_age_h: float, as_json: bool) -> int:
    if not os.path.isfile(os.path.join(bd, "BATCH.json")):
        print(f"REFUSED: no BATCH.json in {bd}.", file=sys.stderr); return 2
    r = status(bd, max_age_h)
    if as_json:
        print(json.dumps(r, indent=2)); return 1 if r["findings"] else 0
    print(f"\nBATCH {os.path.basename(bd)} — {r['brand']}, invariants v{r['invariants_version']}, "
          f"{r['episodes']} episode(s), {r['open']} open")
    for x in r["branches"]:
        print(f"  {'[closed]' if x['closed'] else '[ open ]'} {x['slug']:<16} {x['stage']:<12} "
              f"v{x['invariants_version']}  {x['updated']}")
    for f in r["findings"]:
        print(f"  ! {f}")
    if not r["findings"]:
        print("  accumulator healthy")
    print("  (state only — nothing here looked at a frame; series_join.py gates the batch)\n")
    return 1 if r["findings"] else 0


# ---------------------------------------------------------------- selftest
def selftest() -> int:
    import tempfile, shutil
    assert groups(0) == [] and groups(5) == [5] and groups(12) == [12]
    assert groups(13) == [12, 1] and groups(48) == [12, 12, 12, 12]
    root = tempfile.mkdtemp()
    try:
        sd = os.path.join(root, "_series", "TESTBRAND")
        os.makedirs(sd)
        # unfrozen invariants must refuse
        assert cmd_init(sd, "X") == 1, "init must refuse without a frozen invariants version"
        open(os.path.join(sd, "INVARIANTS.md"), "w").write("# t\n\ninvariants-version: 3\n")
        assert cmd_init(sd, "X") == 0
        bd = os.path.join(sd, "BATCH-X")
        assert cmd_add(bd, "test-01001", 6, 8, 2, "H1", "P1", False) == 0
        assert not EPISODE_ID_RE.match("ep-01") and EPISODE_ID_RE.match("test-01001")
        # a batch of one must refuse to plan
        assert cmd_plan(bd, True) == 1, "plan must refuse at N=1"
        assert cmd_add(bd, "test-01002", 6, 8, 2, "H2", "P1", False) == 0
        assert cmd_add(bd, "test-01003", 6, 8, 2, "H3", "P2", False) == 0
        r = plan(bd)
        assert r["batches"]["B_frames"]["jobs"] == 48 and r["batches"]["B_frames"]["groups"] == [12] * 4
        assert r["human_sync_points"] == {"sequential": 9, "accumulated": 3}
        assert r["wait_groups"]["sequential"] == 12 and r["wait_groups"]["accumulated"] == 8
        assert cmd_plan(bd, True) == 0
        assert cmd_add(bd, "test-01004", 6, 8, 2, None, None, False) == 1, "add after plan must refuse"
        assert cmd_advance(bd, "test-01001", "frames", "j1,j2", "fired") == 0
        assert cmd_close(bd, "test-01001", "out/test-01001_master_v001_9x16.mp4") == 0
        st = status(bd, 24.0)
        assert st["open"] == 2 and not st["findings"]
        # drift a branch and confirm the join-blocking finding
        p = os.path.join(bd, "ep-test-01002.state"); s = _read_json(p); s["invariants_version"] = 2
        _write_json(p, s)
        assert any("STALE branch" in f for f in status(bd, 24.0)["findings"])
        # max-age sweep
        assert any("ORPHANED" in f for f in status(bd, 0.0)["findings"])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("selftest OK — group split, freeze refusal, N=1 refusal, plan arithmetic, "
          "post-plan add refusal, stale-branch finding, max-age sweep, episode-ID shape")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init", help="open a batch under a frozen series")
    i.add_argument("--series", required=True, help="path to _series/<BRAND>/")
    i.add_argument("--batch-id", required=True)
    a_ = sub.add_parser("add", help="accumulate one episode")
    a_.add_argument("--batch", required=True); a_.add_argument("--episode", required=True)
    a_.add_argument("--lines", type=int, required=True); a_.add_argument("--shots", type=int, required=True)
    a_.add_argument("--variants", type=int, default=2)
    a_.add_argument("--hook"); a_.add_argument("--persona")
    a_.add_argument("--reopen", action="store_true", help="add after planning (ledgered)")
    p = sub.add_parser("plan", help="emit the three batches and their jobs_wait groups")
    p.add_argument("--batch", required=True); p.add_argument("--json", action="store_true")
    ad = sub.add_parser("advance", help="record a branch reaching a stage")
    ad.add_argument("--batch", required=True); ad.add_argument("--episode", required=True)
    ad.add_argument("--stage", required=True, choices=STAGES)
    ad.add_argument("--jobs"); ad.add_argument("--note")
    cl = sub.add_parser("close", help="close a branch (master exists, per-episode QA done)")
    cl.add_argument("--batch", required=True); cl.add_argument("--episode", required=True)
    cl.add_argument("--master", required=True)
    st = sub.add_parser("status", help="read the state files; run the max-age sweep")
    st.add_argument("--batch", required=True)
    st.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_H)
    st.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "init":
        return cmd_init(a.series, a.batch_id)
    if a.cmd == "add":
        return cmd_add(a.batch, a.episode, a.lines, a.shots, a.variants, a.hook, a.persona, a.reopen)
    if a.cmd == "plan":
        return cmd_plan(a.batch, a.json)
    if a.cmd == "advance":
        return cmd_advance(a.batch, a.episode, a.stage, a.jobs, a.note)
    if a.cmd == "close":
        return cmd_close(a.batch, a.episode, a.master)
    if a.cmd == "status":
        return cmd_status(a.batch, a.max_age_hours, a.json)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
