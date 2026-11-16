#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""new_job.py — make a job folder and a checkpoint the gate accepts, from a client profile.

The job layout (00-brief … 10-export, 99-costs) and 00-brief/CHECKPOINT.md, filled from the profile: mode, policy,
approver and delivery format. Every input starts MISSING with an accepted risk ("concept only") and the budget starts
at `envelope 0 cr · estimate UNPRICED [unpriced]`, so a concept and a script can be developed before anything is
priced; raise the envelope before the first paid call. Then it runs `gate.py open` on the job.

  new_job.py <client> <slug> [--mode A|B|C|D|S] [--jobs-dir DIR] [--approver "Name"] [--format PRESET] [--no-open]

<client> is a profile name (`acme` → acme.md, looked up like the gate does). The job id is <client>-<NNNNN>-<slug>,
numbered after the client's existing jobs in --jobs-dir (default: the configured jobs folder, else here).
A profile whose approver is a role ("the shop's owner") needs --approver with a person's name.
"""
from __future__ import annotations
import argparse, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import client_files  # noqa: E402

LAYOUT = ("00-brief", "01-script/prompts", "02-startframes", "03-clips", "04-broll", "05-voice", "06-music",
          "07-edit", "08-captions", "09-qa", "10-export", "99-costs")
INPUTS = ("approved-language", "archive+licensing", "personas", "brand assets", "music library", "spend context",
          "reference images")
GATES = ("ideation kill tests → script scorecard + claims lint → blocking cards → frame gate →\n"
         "            prompt lint → QA card + selects → compliance → slop/export QC → verification readout")
from studio import ROLE_RE  # noqa: E402  (3.1 review: one rule for a person's name, shared with studio and new_client)
MODE_WHY = {"A": "one hero film carrying the message", "B": "a batch of short one-idea videos",
            "C": "an editorial explainer", "D": "a repurpose cut of existing footage", "S": "stills only"}


def config_jobs_dir() -> str | None:
    import cine_home
    return cine_home.config_dir("jobs_dir")


def profile_fields(text: str) -> dict:
    def grab(rx):
        m = re.search(rx, text, re.M)
        return m.group(1).strip() if m else ""
    return {"mode": grab(r"^\*\*Default mode:\*\*\s*([A-DS])\b"),
            "policy": grab(r"^\*\*Verification policy:\*\*\s*`([^`]+)`"),
            "approver": grab(r"^\*\*Named approver:\*\*\s*([^,.(\n]+)"),     # the name, before any comma or note
            "format": grab(r"^### Delivery format\s*—\s*`([^`]+)`")}


def next_id(jobs_dir: str, client: str, slug: str) -> str:
    n = 1000
    if os.path.isdir(jobs_dir):
        for d in os.listdir(jobs_dir):
            m = re.match(rf"^{re.escape(client)}-(\d{{5}})-", d)
            if m:
                n = max(n, int(m.group(1)))
    return f"{client}-{n + 1:05d}-{slug}"


def studio_switches() -> tuple[str, list]:
    """(3.1) The studio's default finishing looks as a `Switches:` value — finishing looks ONLY, each with its
    reason, checked by switches.parse exactly as the gate will read it. ('none', []) when there are none."""
    import studio, switches
    looks = studio.load_raw().get("finishing_looks")  # raw: a bad look refuses here
    if not isinstance(looks, dict) or not looks:
        return "none", []
    bad = [k for k in looks if k not in switches.FINISH_LOOKS]
    if bad:
        return "none", [f"studio.json finishing_looks may only pre-fill {', '.join(switches.FINISH_LOOKS)}; "
                        f"refused: {', '.join(bad)}"]
    line = "; ".join(f"{k} — {v}" for k, v in sorted(looks.items()))
    on, probs = switches.parse(line)
    if probs or set(on) != set(looks):
        return "none", [f"studio.json finishing_looks: {p_}" for p_ in probs] or ["studio finishing looks did not parse"]
    return line, []


def checkpoint(job_id: str, client: str, f: dict, mode: str, approver: str, fmt: str, sw: str = "none") -> str:
    inputs = " ·\n            ".join(f"{k} MISSING (accepted risk: concept only, before any paid call)" for k in INPUTS)
    return (f"# PRODUCTION CHECKPOINT\n\n"
            f"Job:        {job_id}\n"
            f"Mode:       {mode} — {MODE_WHY.get(mode, 'see the brief')}\n"
            f"Client:     clients/{client}.md\n"
            f"Policy:     {f['policy']}\n"
            f"Format:     {fmt} (master) · derived: none\n"
            f"            generation: 1080p minimum, the tier per model\n"
            f"Voice:      none — house register, flagged\n"
            f"Inputs:     {inputs}\n"
            f"Gates:      {GATES}\n"
            f"Skips:      none\n"
            f"Switches:   {sw}\n"
            f"Budget:     envelope 0 cr (concept only: raise it before the first paid call) · estimate UNPRICED "
            f"[unpriced] · preflight none yet\n"
            f"Approver:   {approver}\n"
            f"Next:       develop the concept (develop.py init), then approve it\n")


def make(client: str, slug: str, jobs_dir: str, mode: str | None = None, approver: str | None = None,
         fmt: str | None = None) -> tuple[str, list]:
    """Returns (job path, problems). Writes nothing when there is a problem."""
    probs: list = []
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,40}$", slug or ""):
        probs.append("the slug is lower-case letters, digits and hyphens (e.g. first-promo)")
    prof = client_files.find(f"{client}.md", jobs_dir)
    if not prof:
        probs.append(f"no client profile {client}.md — {client_files.where_looked(jobs_dir)}")
        return "", probs
    f = profile_fields(open(prof, encoding="utf-8").read())
    mode = (mode or f["mode"] or "").upper()
    if mode not in MODE_WHY:
        probs.append("no mode: pass --mode A|B|C|D|S (the profile has no `**Default mode:**`)")
    if not f["policy"]:
        probs.append("the profile has no `**Verification policy:**` — answer its section 0 first")
    _ptxt = open(prof, encoding="utf-8").read()
    if not (approver or "").strip() and "(an invented sample" in _ptxt.split("\n", 1)[0]:
        probs.append(f"{client} is the invented sample client: its approver ({f['approver'] or 'none'}) is not a real "
                     f"person, so nothing could be approved. Pass --approver \"<your own name>\" (3.1 review)")
    appr = (approver or f["approver"] or "").strip()
    if not appr or ROLE_RE.search(appr):
        probs.append(f"the approver must be a person's name, not a role ({appr or 'none in the profile'!r}): "
                     f"pass --approver \"Name\"")
    fmt = fmt or f["format"] or ""
    if not fmt:
        probs.append("no delivery format: pass --format (a preset from assets/delivery-formats.json)")
    if mode == "S" and fmt != "stills":
        probs.append("Mode S needs --format stills")
    sw, sw_probs = studio_switches()
    probs += sw_probs
    if probs:
        return "", probs
    job_id = next_id(jobs_dir, client, slug)
    job = os.path.join(jobs_dir, job_id)
    for d in LAYOUT:
        os.makedirs(os.path.join(job, d), exist_ok=True)
    cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
    if not os.path.exists(cp):
        open(cp, "w", encoding="utf-8").write(checkpoint(job_id, client, f, mode, appr, fmt, sw))
    return job, []


def selftest() -> int:
    py = sys.executable
    with tempfile.TemporaryDirectory() as td:
        jobs = os.path.join(td, "jobs"); os.makedirs(jobs)
        env = {**os.environ, "CINE_HOME": os.path.join(td, "home")}
        env.pop("CINE_CLIENTS", None); os.environ.pop("CINE_CLIENTS", None)
        job, p = make("acme", "first-promo", jobs, mode="A", approver="Sam Reyes")
        assert not p and os.path.basename(job) == "acme-01001-first-promo", (job, p)
        r = subprocess.run([py, os.path.join(HERE, "gate.py"), "open", job], capture_output=True, text=True, env=env)
        assert r.returncode == 0 and "OPEN" in r.stdout, r.stdout + r.stderr
        job2, _ = make("acme", "second", jobs, mode="A", approver="Sam Reyes")
        assert os.path.basename(job2) == "acme-01002-second", job2
        _, p = make("acme", "third", jobs, mode="A")     # the sample names an invented person: never copied silently
        assert any("invented sample client" in x for x in p), p
        job3, p = make("acme", "third", jobs, mode="A", approver="Dana Ito")
        assert not p and "Approver:   Dana Ito\n" in open(os.path.join(job3, "00-brief", "CHECKPOINT.md")).read(), p
        roles = os.path.join(td, "roles"); os.makedirs(roles)
        acme = open(client_files.find("acme.md", jobs), encoding="utf-8").read()
        open(os.path.join(roles, "rolecase.md"), "w", encoding="utf-8").write(
            re.sub(r"(?m)^\*\*Named approver:\*\*.*$", "**Named approver:** the shop's owner.", acme))
        os.environ["CINE_CLIENTS"] = roles
        try:
            _, p = make("rolecase", "x", jobs, mode="A")    # a role is not a name
        finally:
            os.environ.pop("CINE_CLIENTS")
        assert any("a person's name" in x for x in p), p
        _, p = make("acme", "Bad Slug", jobs, mode="A", approver="Sam Reyes")
        assert any("slug" in x for x in p), p
        _, p = make("nosuch", "x", jobs)
        assert any("no client profile" in x for x in p), p
        _, p = make("acme", "s", jobs, mode="S", approver="Sam Reyes")
        assert any("Mode S needs" in x for x in p), p
        # (3.1) studio finishing looks pre-fill a NEW job's Switches line, finishing looks only
        st = os.path.join(td, "studio"); os.makedirs(st); os.environ["CINE_STUDIO"] = st
        try:
            import json as _j, switches as _sw
            _j.dump({"finishing_looks": {"finish-texture": "grain on every master we ship"}}, open(os.path.join(st, "studio.json"), "w"))
            j4, p = make("acme", "looks", jobs, mode="A", approver="Sam Reyes")
            cp4 = open(os.path.join(j4, "00-brief", "CHECKPOINT.md"), encoding="utf-8").read()
            assert "Switches:   finish-texture — grain on every master we ship\n" in cp4, cp4
            assert _sw.for_job(j4) == {"finish-texture": "grain on every master we ship"}, "the gate reads exactly it"
            assert _sw.for_job(job) == {}, "a job made before the studio setting lifts nothing"
            _j.dump({"finishing_looks": {"floor-1080": "we prefer it this way"}}, open(os.path.join(st, "studio.json"), "w"))
            _, p = make("acme", "spend", jobs, mode="A", approver="Sam Reyes")
            assert any("may only pre-fill" in x for x in p), "a switch that is not a finishing look is refused"
        finally:
            os.environ.pop("CINE_STUDIO", None)
    print("selftest OK — a job from the sample profile opens at the gate with no edit (concept only: inputs MISSING "
          "with an accepted risk, envelope 0, UNPRICED); ids number after existing jobs; a role is refused as approver; "
          "a bad slug, a missing profile and Mode S without stills are refused before anything is written")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("client", nargs="?"); ap.add_argument("slug", nargs="?")
    ap.add_argument("--mode"); ap.add_argument("--jobs-dir"); ap.add_argument("--approver"); ap.add_argument("--format")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.client or not a.slug:
        ap.print_help(); return 2
    jobs = os.path.abspath(a.jobs_dir or config_jobs_dir() or os.getcwd())
    job, probs = make(a.client, a.slug, jobs, a.mode, a.approver, a.format)
    if probs:
        print("REFUSED:\n  - " + "\n  - ".join(probs), file=sys.stderr); return 1
    print(f"made {job}")
    if a.no_open:
        return 0
    r = subprocess.run([sys.executable, os.path.join(HERE, "gate.py"), "open", job], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode == 0:
        print("next: develop the concept — say \"develop the concept for this job\" (develop.py init), then approve it")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
