#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""demo.py — a finished, text-only sample job to read before your first real one. (3.1)

  demo.py [--jobs-dir DIR]      # makes acme-00000-demo-spring-tuneup in your jobs folder (never takes a real job number)
  demo.py --selftest

The job is made by new_job.py for the invented sample client `acme` (concept only: budget 0, no approvals), then the
sample's brief, development record, script, shot list and estimate (`assets/demo-job/`) are copied in. Nothing was
generated and nothing can spend: the gate refuses every paid call on it. Read `README-DEMO.md` in the job first.
"""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import new_job  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(HERE), "assets", "demo-job")
SLUG = "demo-spring-tuneup"


def make(jobs_dir: str) -> tuple[str, list]:
    job, probs = new_job.make("acme", SLUG, jobs_dir, mode="A", approver="Sam Reyes", number=0)   # (3.1.1) acme-00000
    if probs:
        return "", probs
    for root, _dirs, files in os.walk(SAMPLE):
        rel = os.path.relpath(root, SAMPLE)
        dst = job if rel == "." else os.path.join(job, rel)
        os.makedirs(dst, exist_ok=True)
        for f in files:
            if not os.path.exists(os.path.join(dst, f)):
                shutil.copy2(os.path.join(root, f), os.path.join(dst, f))
    return job, []


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        jobs = os.path.join(td, "jobs"); os.makedirs(jobs)
        env = {**os.environ, "CINE_HOME": os.path.join(td, "home")}
        for k in ("CINE_CLIENTS", "CINE_STUDIO", "CINE_JOB"):
            env.pop(k, None)
        old = {k: os.environ.pop(k, None) for k in ("CINE_CLIENTS", "CINE_STUDIO")}
        try:
            job, p = make(jobs)
        finally:
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v
        assert not p and os.path.basename(job) == f"acme-00000-{SLUG}", (p, job)
        for rel in ("README-DEMO.md", "00-brief/DEVELOPMENT.md", "01-script/SCRIPT-spring-tuneup-v1.md",
                    "01-script/SHOTLIST.md", "99-costs/ESTIMATE.md", "00-brief/CHECKPOINT.md"):
            assert os.path.isfile(os.path.join(job, rel)), rel
        gate = os.path.join(HERE, "gate.py")
        r = subprocess.run([sys.executable, gate, "open", job], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        r = subprocess.run([sys.executable, gate, "preflight", "S1", "--kind", "clip"], capture_output=True, text=True,
                           env=env)
        assert r.returncode != 0 and "budget envelope of 0 cr" in (r.stdout + r.stderr), \
            "a paid call on the demo job must be refused FOR its budget of 0 (build review 2): " \
            + r.stdout + r.stderr
        cp = open(os.path.join(job, "00-brief", "CHECKPOINT.md"), encoding="utf-8").read()
        assert "envelope 0 cr" in cp, "concept only: nothing can spend"
    print("selftest OK — the demo job is made by new_job for the sample client, carries the brief, development, "
          "script, shot list and estimate, opens at the gate, and its paid-call preflight is refused (budget 0)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs-dir"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    jobs = os.path.abspath(a.jobs_dir or new_job.config_jobs_dir() or os.getcwd())
    job, probs = make(jobs)
    if probs:
        print("REFUSED:\n  - " + "\n  - ".join(probs), file=sys.stderr); return 1
    print(f"demo job: {job}\nread {os.path.join(job, 'README-DEMO.md')} first — nothing in it can spend")
    return 0


if __name__ == "__main__":
    sys.exit(main())
