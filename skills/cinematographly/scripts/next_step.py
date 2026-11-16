#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""next_step.py — what the open job needs next, in one line, and how to give an approval when one is owed.

  next_step.py            # reads the gate's status of the open job
  next_step.py --selftest

It reads `gate.py status --json` and changes nothing. When the next step is an approval, it says how to give it:
in your own words, in this conversation (the gate records an approval only when the words quoted are yours).
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APPROVE_RE = re.compile(r"\bapprove ([a-z]+(?::[A-Za-z0-9_-]+)?)", re.I)
SAY = {"concept": "Approved: go with concept <ID>.", "script": "The script is approved.",
       "storyboard": "Storyboard approved.", "audio": "The voice is approved.", "lock": "Picture is locked.",
       "export": "Approved for delivery."}


def status(env: dict | None = None) -> tuple[int, dict | None, str]:
    r = subprocess.run([sys.executable, os.path.join(HERE, "gate.py"), "status", "--json"], capture_output=True,
                       text=True, env=env)
    try:
        return r.returncode, json.loads(r.stdout), ""
    except ValueError:
        return r.returncode, None, (r.stdout or r.stderr).strip()


def advice(st: dict | None, raw: str) -> list:
    if st is None:
        if "no active job" in raw:
            return [raw.split(" — ")[0] + ".",
                    "Start one: /cinematographly:new-job <client> <slug>  (or re-open a job: gate.py open <job-dir>)"]
        return [f"the gate did not answer: {raw[:200]}", "run /cinematographly:doctor"]
    out = [f"job {st.get('job')} · tier {st.get('tier')} · policy {st.get('policy')}"]
    probs = st.get("checkpoint_problems") or []
    if probs:
        out.append(f"fix the checkpoint first: {probs[0]}")
    steps = st.get("next") or []
    if not steps:
        return out + ["nothing owed — the gate reports no next step"]
    out.append(f"next: {steps[0]}")
    m = APPROVE_RE.search(steps[0])
    if m:
        stage = m.group(1).lower()
        eg = SAY.get(stage.split(":")[0], f"{stage} approved.")
        out.append(f"to approve: look at it, then tell Claude in your own words — for example “{eg}” — and the gate "
                   f"records `approve {stage}` with your words quoted (it checks they are in this conversation)")
    first = APPROVE_RE.search(steps[0])
    rest = [x for x in steps[1:] if not (first and (APPROVE_RE.search(x) or [None, None])[1] == first.group(1))]
    if rest:
        out.append(f"after that: {len(rest)} more ({'; '.join(rest[:2])}{' …' if len(rest) > 2 else ''})")
    return out


def selftest() -> int:
    import new_job
    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "CINE_HOME": os.path.join(td, "home")}
        for k in ("CINE_JOB", "CINE_CLIENTS"):
            env.pop(k, None)
        rc, st, raw = status(env)
        lines = advice(st, raw)
        assert st is None and any("new-job" in x for x in lines), (raw, lines)
        jobs = os.path.join(td, "jobs"); os.makedirs(jobs)
        job, p = new_job.make("acme", "first-promo", jobs, mode="A", approver="Sam Reyes")
        assert not p, p
        r = subprocess.run([sys.executable, os.path.join(HERE, "gate.py"), "open", job], capture_output=True,
                           text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        rc, st, raw = status(env)
        lines = advice(st, raw)
        assert st and lines[0].startswith("job acme-01001-first-promo"), (raw, lines)
        assert any(x.startswith("next: ") for x in lines), lines
    # the approval wording, on a status that owes one
    lines = advice({"job": "j", "tier": "full", "policy": "per-stage-human",
                    "next": ["approve script", "write and lint the prompt for S1"]}, "")
    assert any("to approve" in x and "approve script" in x and "own words" in x for x in lines), lines
    assert any("after that: 1 more" in x for x in lines), lines
    lines = advice({"job": "j", "next": ["development → approve concept", "approve script", "approve concept"]}, "")
    assert any("after that: 1 more (approve script)" in x for x in lines), "the owed approval is not listed twice"
    assert not any("to approve" in x for x in advice({"job": "j", "next": ["re-lint x.prompt.md"]}, "")), "no approval owed"
    print("selftest OK — no job: says how to start one; an opened sample job: reports its next step; an approval owed: "
          "says how to give it in the person's own words; no approval owed: says nothing about approving")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rc, st, raw = status()
    print("\n".join(advice(st, raw)))
    return 0 if st is not None else 1


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    sys.exit(main())
