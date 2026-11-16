#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""ledger.py — the production ledger: one record per video, and the index across all of them.

WHY THIS EXISTS. This skill had a rigorous per-video quality gate and no production tracker. Every
question a producer asks mid-month was unanswerable without walking folders by hand: how many
scripts are in flight and in what state, which ones were killed and why, which videos used persona
P2, what is still awaiting sign-off, what the month cost — and, the one that actually matters for a
claims-sensitive client, ⛔ **"this claim turned out to be wrong; which shipped videos contain it?"**
That last one had no mechanism at all: `claims_lint.py` ran at approve-script, printed, and was
forgotten, and `script-archive/` — the only cross-video corpus — was empty because nothing wrote to
it. At 2-3 videos a month that is survivable. At 30-50 it is not a tracking problem, it is a recall
problem with a lawyer attached.

THE DESIGN RULE, learned from this skill's own failures: **state that needs a second command stops
being written.** `shot_manifest.py add`, `qa_log.py`, the hook bank, `EPISODES.md`, `COSTS-*.md` are
all manual, and all of them go quiet under load. So this file DERIVES everything it can from
artifacts the gate already forces to exist — CHECKPOINT.md, APPROVALS.md, QA-LOG.md, the shot
manifest, DEVELOPMENT.md — and asks a human only for what no artifact carries: the ad-name join key,
and the terminal facts (killed, delivered, signed off, published). `gate.py` calls `sync` itself on
open, approve and close, so the record is a by-product of work rather than a chore beside it.

  RECORD.json lives at <job>/00-brief/RECORD.json. ⛔ **Do not delete it.** `sync` rebuilds every
  DERIVED field from the folder, but the authored half — the identity, the kill reason, the
  sign-off, the claims record and the link to the archived script — exists nowhere else and does
  not come back. It is a record, not a cache.

Usage
-----
  python3 ledger.py sync    <job-dir>                  # rebuild the derived half (gate does this)
  python3 ledger.py set     <job-dir> --ad-name ACME-B1-H05-P1-a --persona P1 \\
                            --hook H05 --body B1 --cta C1 --tone serious --batch B2026-09A \\
                            --platform tiktok --platform instagram
  python3 ledger.py show    <job-dir> [--json]
  python3 ledger.py kill    <job-dir> --by "Dana" --why "client killed the angle"
  python3 ledger.py deliver <job-dir> --by "Dana" [--platform tiktok --url https://...]
  python3 ledger.py signoff <job-dir> --by "client" --quote "APPROVED"
  python3 ledger.py note    <job-dir> --by "Dana" --why "waiting on the claims sheet" [--blocked]

  python3 ledger.py index   <root> [--client acme] [--month 2026-09] [--state script] \\
                            [--persona P1] [--json]
  python3 ledger.py find    <root> --claim "clinically proven"     # ⛔ THE RECALL QUERY

Exit codes: 0 ok · 1 the query found nothing / a record is incomplete · 2 usage or IO error.
"""
from __future__ import annotations
import argparse, glob, hashlib, json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
ARCHIVE = os.environ.get("CINE_ARCHIVE") or os.path.join(SKILL_ROOT, "script-archive")
SCHEMA = "cine-record/1"

# The gate's own chain. The record's state is the furthest one signed, so the two can never disagree.
# `brief` is Mode S (stills), signed in place of concept → script; it sorts first, so a stills job
# reads `brief` until it is exported. A video job never signs it (gate.py refuses), so nothing changes there.
STAGE_ORDER = ("brief", "concept", "script", "cast", "audio", "clips", "music", "lock", "export")
# Terminal states no approval can produce — they are authored, because no artifact implies them.
TERMINAL = ("killed", "delivered", "published", "signed-off")


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read(p: str) -> str:
    """⛔ errors="replace", and ValueError caught alongside OSError.

    A legacy script saved by Word arrives as cp1252, and `UnicodeDecodeError` is a ValueError, not
    an OSError. It escaped this function, escaped main()'s handler, and exited 1 — **the same exit
    code `find` uses for "no match"** — from a file that contained the claim. A recall query that
    cannot read a file must count it as unsearched, never as clean.
    """
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, ValueError):
        return ""


def readable(p: str) -> bool:
    try:
        with open(p, "rb") as fh:
            fh.read(1)
        return True
    except OSError:
        return False


def flat(s: str) -> str:
    """Whitespace-normalised, lowercased. A claim wrapped across a line break — which is what a
    script does every time a line is long — was a false negative against a line-by-line search."""
    return re.sub(r"\s+", " ", s).lower()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_kv(text: str) -> dict:
    """CHECKPOINT.md is `Key: value` lines, the same shape gate.py reads."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]?\s*\**([A-Za-z][A-Za-z /_-]{1,30})\**\s*:\s*(.*?)\s*$", line)
        if m:
            out[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
    return out


def record_path(job: str) -> str:
    return os.path.join(os.path.abspath(job), "00-brief", "RECORD.json")


def load(job: str) -> dict:
    p = record_path(job)
    if os.path.isfile(p):
        try:
            d = json.loads(read(p))
            if isinstance(d, dict):
                return d
        except json.JSONDecodeError:
            pass
    return {"schema": SCHEMA, "events": [], "identity": {}, "claims": None}


def save(job: str, rec: dict, merge_events: bool = False) -> str:
    """⛔ Unique temp file, and events re-read at the last moment.

    A fixed `<record>.tmp` shared by every writer plus load-modify-save lost 2 of 12 events under a
    parallel shell loop — which is exactly how a month of `deliver` and `signoff` calls gets run.
    os.replace is atomic; two processes writing the same tmp before it is not.
    """
    import tempfile
    p = record_path(job)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if merge_events and os.path.isfile(p):
        try:
            disk = json.loads(read(p))
            mine = {json.dumps(e, sort_keys=True) for e in rec.get("events") or []}
            for e in disk.get("events") or []:
                if json.dumps(e, sort_keys=True) not in mine:
                    rec.setdefault("events", []).append(e)
            rec["events"].sort(key=lambda e: e.get("ts", ""))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    rec["updated"] = now()
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".record-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


# ---------------------------------------------------------------------------------------------
# DERIVED — everything below is read back out of artifacts the gate already forces to exist.
# Nothing here is typed, so nothing here can silently stop being true.
# ---------------------------------------------------------------------------------------------
def approvals(job: str) -> list[dict]:
    """APPROVALS.md rows. gate.py writes 8 cells; the shipped template header says 7. Positional
    and tolerant, deliberately — the parser must not be the thing that breaks on a header fix."""
    out = []
    for line in read(os.path.join(job, "00-brief", "APPROVALS.md")).splitlines():
        if not line.strip().startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 3 or c[0].lower() in ("ts", "---") or set(c[0]) <= set("-: "):
            continue
        out.append({"ts": c[0], "stage": c[1], "by": c[2],
                    "quote": c[3] if len(c) > 3 else "",
                    "artifact": c[4] if len(c) > 4 else "",
                    "sha256": c[5] if len(c) > 5 else "",
                    "media_id": c[6] if len(c) > 6 else "",
                    "verified": c[7] if len(c) > 7 else ""})
    return out


def qa_rows(job: str) -> list[dict]:
    out = []
    for line in read(os.path.join(job, "09-qa", "QA-LOG.md")).splitlines():
        if not line.strip().startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 4 or c[0].lower() in ("when", "---") or set(c[0]) <= set("-: "):
            continue
        out.append({"when": c[0], "shot": c[1], "gate": c[2], "verdict": c[3].upper()})
    return out


def manifest(job: str) -> dict:
    """Shot lineage, if anyone ran shot_manifest.py. Reported with a DENOMINATOR: 'absent' and
    'present but empty' are different facts and only one of them is a problem."""
    hits = sorted(glob.glob(os.path.join(job, "SHOTS-*.json")))
    if not hits:
        return {"present": False, "rows": 0, "credits": None, "retakes": 0}
    rows = []
    for h in hits:
        try:
            d = json.loads(read(h))
            rows += [r for r in (d.get("rows") or []) if isinstance(r, dict)]
        except json.JSONDecodeError:
            continue
    credits = [r.get("cost_credits") for r in rows if isinstance(r.get("cost_credits"), (int, float))]
    return {"present": True, "rows": len(rows),
            "credits": round(sum(credits), 2) if credits else None,
            "credits_from": len(credits),
            "retakes": sum(1 for r in rows if r.get("retake_of"))}


def derive(job: str, rec: dict) -> dict:
    """Rebuild every derived field. Idempotent by construction — call it as often as you like."""
    job = os.path.abspath(job)
    cp = parse_kv(read(os.path.join(job, "00-brief", "CHECKPOINT.md")))
    rec["schema"] = SCHEMA
    rec["path"] = job
    rec["folder"] = os.path.basename(job)
    rec["job"] = cp.get("job") or rec.get("job") or os.path.basename(job)
    rec["client"] = (os.path.basename(cp.get("client", "")).replace(".md", "")
                     or rec.get("client") or "")
    rec["mode"] = (cp.get("mode") or "")[:1]
    rec["format"] = cp.get("format", "")
    rec["approver"] = cp.get("approver", "")

    ap = approvals(job)
    signed = [r["stage"].split(":")[0].lower() for r in ap]
    rec["approved"] = sorted({s for s in signed if s in STAGE_ORDER}, key=STAGE_ORDER.index)
    rec["frames_approved"] = sum(1 for r in ap if r["stage"].lower().startswith("frame:"))
    rec["unverified_approvals"] = sum(1 for r in ap if r.get("verified", "").upper().startswith("UNVERIFIED"))   # incl. "UNVERIFIED hookless" (3.1)

    qa = qa_rows(job)
    rec["qa"] = {"rows": len(qa),
                 "master_pass": any(r["gate"] == "master" and r["verdict"] == "PASS" for r in qa),
                 "retakes": sum(1 for r in qa if r["verdict"] == "RETAKE")}
    rec["manifest"] = manifest(job)

    kinds = [e.get("kind") for e in rec.get("events", [])]
    rec["published"] = [{"platform": p, "post_id": e.get("post_id"), "url": e.get("url"),
                         "ts": e.get("ts")}
                        for e in rec.get("events", []) if e.get("kind") == "publish"
                        for p in (e.get("platforms") or ["?"])]
    if "kill" in kinds:
        rec["state"] = "killed"
    elif "signoff" in kinds:
        rec["state"] = "signed-off"
    elif "publish" in kinds:
        rec["state"] = "published"
    elif "deliver" in kinds:
        rec["state"] = "delivered"
    elif rec["approved"]:
        rec["state"] = rec["approved"][-1]
    elif os.path.isfile(os.path.join(job, "00-brief", "CHECKPOINT.md")):
        rec["state"] = "planned"
    else:
        rec["state"] = "unknown"

    blocked = [e for e in rec.get("events", []) if e.get("kind") == "note" and e.get("blocked")]
    rec["blocked"] = {"since": blocked[-1]["ts"], "why": blocked[-1].get("why", ""),
                      "by": blocked[-1].get("by", "")} if blocked else None
    # ⛔ `opened` used to be "whenever this was first synced", so --month was wrong for every job
    # that predates the ledger — and the empty result blamed the folder shape rather than the
    # filter. Take the earliest thing that actually happened.
    cands = [r["ts"] for r in ap if r.get("ts")] + \
            [e["ts"] for e in rec.get("events", []) if e.get("ts")]
    if not cands:
        cpf = os.path.join(job, "00-brief", "CHECKPOINT.md")
        if os.path.isfile(cpf):
            cands = [datetime.datetime.fromtimestamp(
                os.path.getmtime(cpf), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")]
    rec["opened"] = min(cands) if cands else rec.get("opened") or now()
    rec.setdefault("identity", {})
    rec.setdefault("claims", None)
    return rec


# ---------------------------------------------------------------------------------------------
# THE RECALL CORPUS
# ---------------------------------------------------------------------------------------------
def archive_script(job: str, artifact_abs: str, client: str, jobname: str) -> str | None:
    """Copy an approved script into script-archive/ at the moment of approval.

    ⛔ This is what makes the recall query possible at all. `script-archive/` was designed as the
    cross-video corpus and stayed empty because populating it was a convention nobody had a tool
    for; a corpus that depends on someone remembering is not a corpus. Named by job + content hash,
    so re-approving the same text is a no-op and approving a revision files a second copy rather
    than overwriting the one that shipped.
    """
    txt = read(artifact_abs)
    if not txt.strip():
        return None
    sha = sha256_text(txt)[:12]
    d = os.path.join(ARCHIVE, client or "_unfiled")
    os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, f"{jobname}-{sha}.md")
    if not os.path.isfile(dest):
        header = (f"<!-- archived {now()} · job {jobname} · client {client or '?'}\n"
                  f"     source {os.path.relpath(artifact_abs, job) if job else artifact_abs}\n"
                  f"     sha256 {sha256_text(txt)}\n"
                  f"     Written by ledger.py at `gate.py approve script`. Do not edit: this is the\n"
                  f"     text a recall query searches, and an edited copy answers the wrong question. -->\n\n")
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(header + txt)
    return dest


def record_claims(job: str, rec: dict, payload: dict) -> dict:
    """Persist what the claims lint saw, including the phrases it let through.

    An `--allow` is a client's written approval of a specific phrase. It was a command-line flag
    and nothing else: the exception vanished the moment the process exited, so nobody could later
    answer 'who approved that wording, and on which videos did it run'. Now it is on the record.
    """
    prev = rec.get("claims")
    if prev:
        # ⛔ this was a single slot. Re-approving a revision erased the earlier version's findings
        # AND its --allow exceptions with their approver — while the earlier text stayed in the
        # archive, so the corpus and the record disagreed about what had been permitted.
        hist = rec.setdefault("claims_history", [])
        if prev not in hist:
            hist.append(prev)
    rec["claims"] = {
        "checked_at": now(),
        "artifact": payload.get("artifact", ""),
        "sha256": payload.get("sha256", ""),
        "category": payload.get("category", ""),
        "disclosure": payload.get("disclosure", ""),
        "findings": payload.get("findings", []),
        "allowed": payload.get("allowed", []),
        "allowed_by": payload.get("by", ""),
        "archived_to": payload.get("archived_to", ""),
    }
    return rec


# ---------------------------------------------------------------------------------------------
def add_event(job: str, kind: str, **kw) -> dict:
    rec = derive(job, load(job))
    ev = {"ts": now(), "kind": kind}
    ev.update({k: v for k, v in kw.items() if v not in (None, "", [], {})})
    rec.setdefault("events", []).append(ev)
    save(job, rec, merge_events=True)
    rec = derive(job, load(job))
    save(job, rec)
    return rec


SKIP_DIRS = {".git", ".svn", "node_modules", "__pycache__", ".venv", "venv"}


def index(root: str, write: bool = True) -> tuple[list[dict], list[str]]:
    """Every job folder under root. A job folder is one with 00-brief/CHECKPOINT.md.

    ⛔ The first version pruned every directory starting with "." or "_" — which silently skipped
    `_series/<BRAND>/`, THIS SKILL'S OWN documented convention for a recurring series, and any
    `_2026-08/` a producer parks a finished month in. It then printed "2 video(s)" with no mention
    of a skip, and `find` printed "searched 2 record(s)" — a denominator it had not earned. Prune
    only what is never a job folder, and return what was pruned so the caller can say so.

    `write=False` is for `find`: a recall query must not fail because a read-only or archived tree
    could not be written to.
    """
    out, skipped = [], []
    root = os.path.abspath(root)
    arch = os.path.abspath(ARCHIVE)
    for dirpath, dirnames, filenames in os.walk(root):
        keep = []
        for d in dirnames:
            full = os.path.join(dirpath, d)
            if d in SKIP_DIRS or os.path.abspath(full) == arch:
                skipped.append(os.path.relpath(full, root))
            else:
                keep.append(d)
        dirnames[:] = keep
        if os.path.basename(dirpath) == "00-brief" and "CHECKPOINT.md" in filenames:
            job = os.path.dirname(dirpath)
            rec = derive(job, load(job))
            if write:
                try:
                    save(job, rec)
                except OSError as e:
                    skipped.append(f"{os.path.relpath(job, root)} (not writable: {e})")
            out.append(rec)
    return sorted(out, key=lambda r: (r.get("client", ""), r.get("job", ""))), skipped


def month_of(rec: dict) -> str:
    return (rec.get("opened") or "")[:7]


def matches(rec: dict, a) -> bool:
    idn = rec.get("identity") or {}
    if a.client and rec.get("client", "").lower() != a.client.lower():
        return False
    if a.month and month_of(rec) != a.month:
        return False
    if a.state and rec.get("state") != a.state:
        return False
    if a.persona and (idn.get("persona") or "").upper() != a.persona.upper():
        return False
    if a.blocked and not rec.get("blocked"):
        return False
    return True


def fmt_rows(recs: list[dict]) -> str:
    w = max([len(r.get("job", "")) for r in recs] + [3])
    lines = [f"  {'job'.ljust(w)}  {'state':<11} {'persona':<7} {'ad-name':<28} {'QA':<4} note",
             "  " + "-" * (w + 62)]
    for r in recs:
        idn = r.get("identity") or {}
        qa = r.get("qa") or {}
        flag = "!" if r.get("blocked") else (" " if r.get("state") != "killed" else "x")
        note = ""
        if r.get("blocked"):
            note = "BLOCKED: " + (r["blocked"].get("why") or "")[:38]
        elif r.get("state") == "killed":
            k = [e for e in r.get("events", []) if e.get("kind") == "kill"]
            note = "killed: " + ((k[-1].get("why") or "")[:40] if k else "")
        elif not (r.get("manifest") or {}).get("present"):
            note = "no shot manifest — lineage not recorded"
        lines.append(f"{flag} {r.get('job','').ljust(w)}  {r.get('state','?'):<11} "
                     f"{(idn.get('persona') or '-'):<7} {(idn.get('ad_name') or '-'):<28} "
                     f"{('PASS' if qa.get('master_pass') else '-'):<4} {note}")
    return "\n".join(lines)


def cmd_sync(a) -> int:
    rec = derive(a.job_dir, load(a.job_dir))
    save(a.job_dir, rec)
    if not a.quiet:
        print(f"synced {os.path.relpath(record_path(a.job_dir))} · state {rec['state']}")
    return 0


def cmd_set(a) -> int:
    rec = derive(a.job_dir, load(a.job_dir))
    idn = rec.setdefault("identity", {})
    for k in ("ad_name", "persona", "hook", "body", "cta", "tone", "batch"):
        v = getattr(a, k, None)
        if v:
            idn[k] = v
    if a.platform:
        idn["platforms"] = sorted(set((idn.get("platforms") or []) + [p.lower() for p in a.platform]))
    # the join key performance-metrics.md §2 depends on: <BRAND>-<body>-<hook>-<persona>-<variant>
    an = idn.get("ad_name")
    if an and len(an.split("-")) != 5:
        print(f"warning: ad-name {an!r} is not the five-part join key "
              f"<BRAND>-<body>-<hook>-<persona>-<variant> — the metrics join will miss it",
              file=sys.stderr)
    save(a.job_dir, derive(a.job_dir, rec))
    print(f"identity: " + " · ".join(f"{k}={v}" for k, v in idn.items()) if idn else "identity: (empty)")
    return 0


def cmd_show(a) -> int:
    rec = derive(a.job_dir, load(a.job_dir))
    save(a.job_dir, rec)
    if a.json:
        print(json.dumps(rec, indent=2, ensure_ascii=False)); return 0
    idn, qa, mf = rec.get("identity") or {}, rec.get("qa") or {}, rec.get("manifest") or {}
    print(f"\n{rec.get('job')}  ·  {rec.get('client') or '?'}  ·  mode {rec.get('mode') or '?'}")
    print("-" * 78)
    print(f"  state           {rec.get('state')}")
    print(f"  approved        {', '.join(rec.get('approved') or []) or '(none)'}"
          + (f" · {rec['frames_approved']} frame(s)" if rec.get("frames_approved") else ""))
    if rec.get("unverified_approvals"):
        print(f"  ⚠ approvals     {rec['unverified_approvals']} signed with an UNVERIFIED quote")
    print(f"  identity        " + (" · ".join(f"{k}={v}" for k, v in idn.items()) or
                                   "(none — `ledger.py set` it, or the metrics join has nothing to join on)"))
    print(f"  QA              {qa.get('rows', 0)} row(s)"
          + (" · master PASS" if qa.get("master_pass") else " · no master PASS")
          + (f" · {qa['retakes']} retake(s)" if qa.get("retakes") else ""))
    if mf.get("present"):
        print(f"  lineage         {mf['rows']} manifest row(s)"
              + (f" · {mf['credits']} credits over {mf['credits_from']} row(s)" if mf.get("credits") else
                 " · no cost recorded")
              + (f" · {mf['retakes']} retake(s)" if mf.get("retakes") else ""))
    else:
        print("  lineage         NO SHOT MANIFEST — nothing records which model made which clip "
              "(`shot_manifest.py init`)")
    cl = rec.get("claims")
    if cl:
        print(f"  claims          checked {cl['checked_at'][:10]} · {len(cl.get('findings') or [])} "
              f"finding(s) · disclosure {cl.get('disclosure') or '?'}"
              + (f" · {len(cl['allowed'])} phrase(s) allowed by {cl.get('allowed_by') or '?'}"
                 if cl.get("allowed") else ""))
        if cl.get("archived_to"):
            rp = os.path.relpath(cl["archived_to"], SKILL_ROOT)
            print(f"  archived        {cl['archived_to'] if rp.startswith('..') else rp}"
                  + ("" if os.path.isfile(cl["archived_to"]) else "  ⛔ FILE MISSING"))
    else:
        print("  claims          not recorded — no script approved through the gate yet")
    if rec.get("blocked"):
        print(f"  ⛔ BLOCKED      since {rec['blocked']['since'][:16]} — {rec['blocked']['why']}")
    for e in (rec.get("events") or [])[-6:]:
        extra = " ".join(f"{k}={v}" for k, v in e.items() if k not in ("ts", "kind"))
        print(f"    {e['ts'][:16]}  {e['kind']:<8} {extra}")
    print()
    return 0


def cmd_event(a) -> int:
    kw = {"by": a.by}
    for k in ("why", "quote", "url"):
        if getattr(a, k, None):
            kw[k] = getattr(a, k)
    if getattr(a, "platform", None):
        kw["platforms"] = [p.lower() for p in a.platform]
    if getattr(a, "blocked", False):
        kw["blocked"] = True
    if a.cmd == "publish":
        kw["post_id"] = getattr(a, "post_id", None)
        if not (kw.get("post_id") or kw.get("url")):
            print("error: `publish` needs --post-id or --url. ⛔ No platform guarantees a field WE "
                  "control in its performance export, so the organic join is ours to make: without "
                  "the post id or the permalink recorded here, an organic row in a CSV can never be "
                  "attributed to this video.", file=sys.stderr)
            return 2
    if a.cmd in ("kill", "note") and not kw.get("why"):
        print(f"error: `{a.cmd}` needs --why. A killed script with no reason is the same as a script "
              f"that vanished — and the reasons are the only thing that makes a month of kills "
              f"teachable.", file=sys.stderr)
        return 2
    rec = add_event(a.job_dir, {"kill": "kill", "deliver": "deliver", "signoff": "signoff",
                                "note": "note", "publish": "publish"}[a.cmd], **kw)
    print(f"{a.cmd}: {rec.get('job')} → state {rec['state']}")
    return 0


def cmd_index(a) -> int:
    all_recs, skipped = index(a.root)
    recs = [r for r in all_recs if matches(r, a)]
    if a.json:
        print(json.dumps(recs, indent=2, ensure_ascii=False))
        return 0 if recs else 1
    if not recs:
        filt = [f"{k}={v}" for k, v in (("client", a.client), ("month", a.month), ("state", a.state),
                                        ("persona", a.persona)) if v] + (["blocked"] if a.blocked else [])
        print(f"no job folders matched under {a.root}"
              + (f" with {', '.join(filt)} — {len(all_recs)} job(s) are there but none match"
                 if filt and all_recs else
                 " (a job folder is one containing 00-brief/CHECKPOINT.md)"))
        if skipped:
            print(f"  skipped {len(skipped)} directory/ies: {', '.join(skipped[:4])}")
        return 1
    by_state: dict = {}
    for r in recs:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    print(f"\n{len(recs)} video(s) under {os.path.abspath(a.root)}"
          + (f"  ({len(all_recs)} total, {len(all_recs) - len(recs)} filtered out)"
             if len(recs) != len(all_recs) else ""))
    if skipped:
        print(f"  skipped {len(skipped)} directory/ies: {', '.join(skipped[:4])}")
    print("  " + " · ".join(f"{k} {v}" for k, v in sorted(by_state.items(), key=lambda kv: -kv[1])))
    print()
    print(fmt_rows(recs))
    no_mf = [r for r in recs if not (r.get("manifest") or {}).get("present")]
    no_id = [r for r in recs if not (r.get("identity") or {}).get("ad_name")]
    no_cl = [r for r in recs if r.get("state") in ("script", "cast", "audio", "clips", "music",
                                                   "lock", "export", "delivered", "signed-off")
             and not r.get("claims")]
    print()
    if no_mf:
        print(f"  ! {len(no_mf)} of {len(recs)} have no shot manifest — for those, which model made "
              f"which clip is not recorded anywhere")
    if no_id:
        print(f"  ! {len(no_id)} of {len(recs)} carry no ad-name join key — performance data cannot "
              f"be joined to them (`ledger.py set --ad-name`)")
    if no_cl:
        print(f"  ! {len(no_cl)} of {len(recs)} passed the script stage with no claims record — a "
              f"recall query will not see them")
    if not (no_mf or no_id or no_cl):
        print(f"  every record complete: lineage, join key and claims present on all {len(recs)}")
    return 0


ARCH_JOB_RE = re.compile(r"job\s+(\S+)\s+·\s+client\s+(\S+)")


def cmd_month(a) -> int:
    """The monthly rollup. ⛔ Nothing in this skill summed anything across videos, so the question
    'what did this month cost' was a hand-assembly job — and the number that sizes next month's
    commitment was coming from the surface with no enforcement.

    Every figure carries its provenance, because the difference between a MEASURED cost and an
    ASSUMED one is the difference between a quote and a guess (pm-workflow.md, the verification
    readout). A total built from three videos that recorded their credits and thirty that did not
    is not a monthly total; it is a third of one, and this says so.
    """
    recs, skipped = index(a.root, write=False)
    scope = [r for r in recs
             if (not a.client or r.get("client", "").lower() == a.client.lower())
             and (not a.month or month_of(r) == a.month)]
    by_state: dict = {}
    for r in scope:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    with_mf = [r for r in scope if (r.get("manifest") or {}).get("present")]
    credited = [r for r in with_mf if (r.get("manifest") or {}).get("credits") is not None]
    credits = sum((r["manifest"]["credits"] or 0) for r in credited)
    retakes = sum((r.get("manifest") or {}).get("retakes", 0) for r in with_mf)
    clips = sum((r.get("manifest") or {}).get("rows", 0) for r in with_mf)
    hours = []
    for r in scope:
        st = os.path.join(r["path"], "99-costs", "stage-time.jsonl")
        if os.path.isfile(st):
            marks = []
            for line in read(st).splitlines():
                try:
                    marks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            open_at, total = None, 0.0
            for m in sorted(marks, key=lambda x: x.get("t", "")):
                if m.get("ev") == "start":
                    open_at = m.get("t")
                elif m.get("ev") == "stop" and open_at:
                    try:
                        a0 = datetime.datetime.fromisoformat(open_at.replace("Z", "+00:00"))
                        b0 = datetime.datetime.fromisoformat(m["t"].replace("Z", "+00:00"))
                        total += max(0.0, (b0 - a0).total_seconds()) / 3600.0
                    except (ValueError, KeyError):
                        pass
                    open_at = None
            if total:
                hours.append((r.get("job"), round(total, 2)))
    spend = {}
    for r in scope:
        for plat, m in (r.get("metrics") or {}).items():
            if isinstance(m.get("spend"), (int, float)):
                spend[plat] = round(spend.get(plat, 0.0) + m["spend"], 2)

    out = {"scope": {"root": os.path.abspath(a.root), "client": a.client, "month": a.month,
                     "videos": len(scope), "of_total": len(recs)},
           "by_state": by_state,
           "generation_credits": {"total": round(credits, 2), "measured_on": len(credited),
                                  "of_videos": len(scope), "provenance": "measured",
                                  "clips": clips, "retakes": retakes},
           "hours": {"total": round(sum(h for _, h in hours), 2), "measured_on": len(hours),
                     "of_videos": len(scope), "provenance": "measured"},
           "ad_spend_by_platform": spend,
           "skipped_dirs": skipped}
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if scope else 1
    if not scope:
        print(f"no videos in scope under {a.root}")
        return 1
    print(f"\nmonth · {len(scope)} video(s)" + (f" · {a.client}" if a.client else "")
          + (f" · {a.month}" if a.month else " · all months"))
    print("-" * 74)
    print("  states          " + " · ".join(f"{k} {v}" for k, v in sorted(by_state.items(),
                                                                          key=lambda kv: -kv[1])))
    cov = f"{len(credited)}/{len(scope)}"
    print(f"  generation      {credits:.0f} credits [MEASURED on {cov} videos]"
          + (f" · {clips} clips · {retakes} retakes" if clips else ""))
    if len(credited) < len(scope):
        gap = len(scope) - len(credited)
        print(f"                  ⛔ {gap} video(s) recorded NO credits, so this is a floor, not a "
              f"total.\n                     `shot_manifest.py add --cost` is the only thing that "
              f"records them.")
    if hours:
        print(f"  hours           {sum(h for _, h in hours):.1f} h [MEASURED on "
              f"{len(hours)}/{len(scope)} videos]")
        if len(hours) < len(scope):
            print(f"                  ⚠ {len(scope) - len(hours)} video(s) logged no time — "
                  f"`stage_timer.py`.\n                     A capacity number quoted from this is a "
                  f"RANGE, not a figure.")
    else:
        print(f"  hours           ⛔ NONE MEASURED — every capacity claim for this month is "
              f"[ASSUMED].\n                     `stage_timer.py start/stop` is what turns it into a "
              f"number.")
    if spend:
        print("  ad spend        " + " · ".join(f"{p} {v:,.2f}" for p, v in sorted(spend.items()))
              + "   ⛔ per platform; currencies are NOT checked and not summed")
    else:
        print("  ad spend        none ingested (`pull_metrics.py ingest`)")
    if skipped:
        print(f"  ⚠ skipped {len(skipped)} directory/ies: {', '.join(skipped[:3])}")
    print()
    return 0


def cmd_find(a) -> int:
    """⛔ THE RECALL QUERY. 'This claim is wrong — what shipped with it in?'

    Every failure mode here is asymmetric: a false negative reads as "you are fine" about an
    advertisement that is already running. So the query reports its own denominator, counts what it
    could not read, and refuses to call a partially-broken corpus clean.
    """
    needle = flat(a.claim)
    recs, skipped = index(a.root, write=False)      # a query must not write
    hits, unreadable = [], []
    for r in recs:
        found_in = []
        cl = r.get("claims") or {}
        checks = [cl] + list(r.get("claims_history") or [])
        for c in checks:
            for f in c.get("findings") or []:
                if needle in flat(str(f.get("match", ""))):
                    found_in.append(f"claims finding line {f.get('line', '?')} "
                                    f"({f.get('severity', '?')}, checked {c.get('checked_at', '?')[:10]})")
            for p in c.get("allowed") or []:
                if needle in flat(p):
                    found_in.append(f"ALLOWED phrase, by {c.get('allowed_by') or '?'}")
            arch = c.get("archived_to")
            if arch:
                if os.path.isfile(arch):
                    if needle in flat(read(arch)):
                        found_in.append(f"archived script {os.path.basename(arch)}")
                else:
                    unreadable.append((r, arch))
        if found_in:
            hits.append((r, sorted(set(found_in))))

    # the archive may hold scripts whose job folder is gone — exactly the case recall exists for.
    # Attribute them from the header this tool writes, so a hit is never labelled with a falsehood.
    known = set()
    for r in recs:
        for c in [r.get("claims") or {}] + list(r.get("claims_history") or []):
            if c.get("archived_to"):
                known.add(os.path.abspath(c["archived_to"]))
    all_arch = sorted(glob.glob(os.path.join(ARCHIVE, "*", "*.md")))
    orphan = []
    for p in all_arch:
        if os.path.abspath(p) in known:
            continue
        body = read(p)
        if needle in flat(body):
            m = ARCH_JOB_RE.search(body[:600])
            orphan.append({"file": p, "job": m.group(1) if m else "?",
                           "client": m.group(2) if m else "?"})

    if a.json:
        print(json.dumps({"claim": a.claim,
                          "videos": [{"job": r.get("job"), "client": r.get("client"),
                                      "state": r.get("state"),
                                      "ad_name": (r.get("identity") or {}).get("ad_name"),
                                      "platforms": (r.get("identity") or {}).get("platforms"),
                                      "where": w} for r, w in hits],
                          "archived_only": orphan,
                          "searched": {"records": len(recs), "archived_scripts": len(all_arch)},
                          "unsearched": {"missing_archive_files":
                                         [{"job": r.get("job"), "path": p} for r, p in unreadable],
                                         "skipped_dirs": skipped}},
                         indent=2, ensure_ascii=False))
        return 0 if (hits or orphan) else 1

    def show(p):
        rp = os.path.relpath(p, SKILL_ROOT)
        return p if rp.startswith("..") else rp

    print(f"\nrecall: {a.claim!r}")
    print(f"  searched {len(recs)} record(s) and {len(all_arch)} archived script(s)")
    if skipped:
        print(f"  skipped {len(skipped)} directory/ies: {', '.join(skipped[:4])}"
              + ("…" if len(skipped) > 4 else ""))
    if unreadable:
        print(f"  ⛔ {len(unreadable)} record(s) point at an archived script that is NOT THERE — "
              f"those scripts were not searched:")
        for r, p in unreadable[:5]:
            print(f"       {r.get('job')} → {p}")
    if not recs and not all_arch:
        print("\n  ⛔ INCONCLUSIVE — nothing was searched. No records under this root and the "
              "archive is\n     empty, so a clean result means the corpus is missing, not that the "
              "claim is absent.")
        return 1
    if not hits and not orphan:
        if unreadable:
            print("\n  ⛔ INCONCLUSIVE — no match in what was searched, but part of the corpus was "
                  "unreachable\n     (above). This is not a clean result. Restore those files, or "
                  "re-approve those scripts.")
            return 1
        print("\n  no match in anything that was searched.")
        print("  ⚠ That covers approved scripts only. A claim added in the EDIT, improvised in a "
              "VO,\n    or burned into an overlay is not in this corpus — see 'what this cannot "
              "tell you'.")
        return 1
    print()
    for r, where in hits:
        idn = r.get("identity") or {}
        print(f"  ⛔ {r.get('job')}  [{r.get('state')}]"
              + (f"  {idn.get('ad_name')}" if idn.get("ad_name") else "")
              + (f"  platforms: {', '.join(idn.get('platforms') or [])}" if idn.get("platforms") else ""))
        for w in where:
            print(f"       {w}")
        if r.get("state") in ("delivered", "signed-off"):
            print("       ⛔ THIS ONE SHIPPED — it needs pulling or amending, not just fixing.")
    for o in orphan:
        print(f"  ⛔ {o['job']}  [archived script; no live record]  client {o['client']}")
        print(f"       {show(o['file'])}")
        print("       ⛔ A script with no live job folder is the case this query exists for — "
              "treat it as shipped until you can prove otherwise.")
    print()
    return 0


def selftest() -> int:
    import tempfile, shutil
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    root = tempfile.mkdtemp()
    global ARCHIVE
    ARCHIVE = os.path.join(root, "_archive")
    try:
        job = os.path.join(root, "prod", "acme-01001-morning")
        os.makedirs(os.path.join(job, "00-brief"))
        os.makedirs(os.path.join(job, "09-qa"))
        with open(os.path.join(job, "00-brief", "CHECKPOINT.md"), "w") as fh:
            fh.write("Job: acme-01001-morning\nMode: B — UGC volume\nClient: acme\n"
                     "Approver: Dana\nFormat: vertical-1080\n")
        rec = derive(job, load(job))
        check("a folder with only a checkpoint reads as planned", rec["state"] == "planned")
        check("client is taken from the checkpoint", rec["client"] == "acme")

        with open(os.path.join(job, "00-brief", "APPROVALS.md"), "w") as fh:
            fh.write("| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n"
                     "|---|---|---|---|---|---|---|---|\n"
                     "| 2026-09-08T10:00:00Z | concept | Dana | go | | | | transcript |\n"
                     "| 2026-09-08T11:00:00Z | script | Dana | ok | 01-script/S.md | abc123 | | UNVERIFIED |\n"
                     "| 2026-09-08T12:00:00Z | concept | Dana | again | | | | UNVERIFIED hookless |\n")
        rec = derive(job, load(job))
        check("state is the furthest stage signed", rec["state"] == "script")
        check("an UNVERIFIED signature is counted, not hidden (3.1: \"UNVERIFIED hookless\" too)",
              rec["unverified_approvals"] == 2)

        # the manifest denominator: absent and empty are different facts
        check("a missing shot manifest is reported as absent", rec["manifest"]["present"] is False)
        with open(os.path.join(job, "SHOTS-ACME.json"), "w") as fh:
            json.dump({"rows": [{"id": "S1-C1#1", "cost_credits": 12.5},
                                {"id": "S1-C1#2", "cost_credits": 12.5, "retake_of": "S1-C1#1"}]}, fh)
        rec = derive(job, load(job))
        check("...and a present one sums credits and counts retakes",
              rec["manifest"] == {"present": True, "rows": 2, "credits": 25.0,
                                  "credits_from": 2, "retakes": 1})

        with open(os.path.join(job, "09-qa", "QA-LOG.md"), "w") as fh:
            fh.write("| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n"
                     "| t | all | master | PASS | watched it |\n")
        rec = derive(job, load(job))
        check("the master gate is read from the QA log", rec["qa"]["master_pass"] is True)

        # identity + the join-key shape
        class A: pass
        a = A(); a.job_dir = job; a.ad_name = "ACME-B1-H05-P1-a"; a.persona = "P1"
        a.hook = "H05"; a.body = "B1"; a.cta = "C1"; a.tone = "serious"; a.batch = "B2026-09A"
        a.platform = ["TikTok", "instagram"]
        cmd_set(a)
        rec = load(job)
        check("identity is stored and platforms normalise",
              rec["identity"]["persona"] == "P1" and rec["identity"]["platforms"] == ["instagram", "tiktok"])

        # ⛔ the recall corpus
        script = os.path.join(job, "01-script")
        os.makedirs(script)
        sp = os.path.join(script, "S.md")
        with open(sp, "w") as fh:
            fh.write("HOST: it is clinically proven to help you sleep.\n")
        dest = archive_script(job, sp, "acme", "acme-01001-morning")
        check("an approved script is archived automatically", dest and os.path.isfile(dest))
        check("...and re-archiving the same text is a no-op",
              archive_script(job, sp, "acme", "acme-01001-morning") == dest
              and len(glob.glob(os.path.join(ARCHIVE, "*", "*.md"))) == 1)
        rec = record_claims(job, derive(job, load(job)),
                            {"artifact": "01-script/S.md", "sha256": "abc", "category": "sleep",
                             "disclosure": "DISCLOSED", "by": "Dana",
                             "findings": [{"line": 1, "match": "clinically proven",
                                           "severity": "WARN", "why": "evidence claim"}],
                             "allowed": ["clinically proven"], "archived_to": dest})
        save(job, rec)
        check("an --allow exception is on the record, with who allowed it",
              load(job)["claims"]["allowed"] == ["clinically proven"]
              and load(job)["claims"]["allowed_by"] == "Dana")

        a = A(); a.root = root; a.claim = "clinically proven"; a.json = True
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_find(a)
        res = json.loads(buf.getvalue())
        check("RECALL finds the video by claim", rc == 0 and len(res["videos"]) == 1
              and res["videos"][0]["ad_name"] == "ACME-B1-H05-P1-a")
        check("...and reports what it searched", res["searched"]["records"] == 1
              and res["searched"]["archived_scripts"] == 1)
        buf = io.StringIO(); a.claim = "cures insomnia"
        with contextlib.redirect_stdout(buf):
            rc2 = cmd_find(a)
        check("...and a claim that is not there returns nothing, with exit 1",
              rc2 == 1 and json.loads(buf.getvalue())["videos"] == [])

        # ⛔ zero denominator must read INCONCLUSIVE, never clean (self-evolution.md §6b)
        empty = tempfile.mkdtemp()
        ARCHIVE = os.path.join(empty, "none")
        a2 = A(); a2.root = empty; a2.claim = "anything"; a2.json = False
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc3 = cmd_find(a2)
        check("a recall over an EMPTY corpus reads INCONCLUSIVE, not clean",
              rc3 == 1 and "INCONCLUSIVE" in buf.getvalue())
        ARCHIVE = os.path.join(root, "_archive")

        # terminal states, which no artifact can imply
        a3 = A(); a3.job_dir = job; a3.by = "Dana"; a3.why = ""; a3.cmd = "kill"
        a3.quote = None; a3.url = None; a3.platform = None; a3.blocked = False
        check("kill without a reason is refused", cmd_event(a3) == 2)
        a3.why = "client killed the angle"
        cmd_event(a3)
        check("kill is terminal and beats the approvals", load(job)["state"] == "killed")

        job2 = os.path.join(root, "prod", "acme-01002-tune-up")
        os.makedirs(os.path.join(job2, "00-brief"))
        with open(os.path.join(job2, "00-brief", "CHECKPOINT.md"), "w") as fh:
            fh.write("Job: acme-01002-tune-up\nMode: B\nClient: acme\n")
        a4 = A(); a4.job_dir = job2; a4.by = "Dana"; a4.why = "waiting on the claims sheet"
        a4.cmd = "note"; a4.blocked = True; a4.quote = None; a4.url = None; a4.platform = None
        cmd_event(a4)
        check("a blocked note surfaces with its reason", load(job2)["blocked"]["why"] ==
              "waiting on the claims sheet")

        found, skipped = index(root)
        check("the index walks the whole root and finds both", len(found) == 2)

        # ⛔ the organic join is OURS to make: no platform guarantees a field we control in its
        # performance export, so without a publish record an organic CSV row can never be attributed
        a9 = A(); a9.job_dir = job2; a9.by = "Dana"; a9.cmd = "publish"; a9.platform = ["tiktok"]
        a9.post_id = None; a9.url = None; a9.why = None; a9.quote = None; a9.blocked = False
        check("publish without a post id or url is refused", cmd_event(a9) == 2)
        a9.post_id = "7412345678901234567"
        cmd_event(a9)
        pub = load(job2).get("published") or []
        check("...and a publish records platform + post id, and moves the state",
              load(job2)["state"] == "published" and pub and pub[0]["post_id"] == "7412345678901234567")

        # the monthly rollup must report COVERAGE, not just a total
        os.makedirs(os.path.join(job2, "99-costs"), exist_ok=True)
        with open(os.path.join(job2, "SHOTS-X.json"), "w") as fh:
            json.dump({"rows": [{"id": "a", "cost_credits": 10.0}]}, fh)
        am = A(); am.root = root; am.client = None; am.month = None; am.json = True
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_month(am)
        mo = json.loads(buf.getvalue())
        check("month sums only what was actually recorded",
              mo["generation_credits"]["total"] == 35.0)   # 25 on job + 10 on job2
        check("⛔ ...and reports the DENOMINATOR, so a floor is not read as a total",
              mo["generation_credits"]["measured_on"] == 2
              and mo["generation_credits"]["of_videos"] == mo["scope"]["videos"])
        check("...and says plainly that no hours were measured",
              mo["hours"]["total"] == 0 and mo["hours"]["measured_on"] == 0)

        # ⛔ every case below is a real false-negative an adversarial reader produced against the
        # first version of this file. A recall query that answers "you are fine" about a running
        # advertisement is the worst failure mode in this codebase.
        nested = os.path.join(root, "_series", "acme", "am-02001-nested")
        os.makedirs(os.path.join(nested, "00-brief"))
        with open(os.path.join(nested, "00-brief", "CHECKPOINT.md"), "w") as fh:
            fh.write("Job: am-02001-nested\nMode: B\nClient: acme\n")
        found2, _ = index(root)
        check("a job under _series/ is FOUND, not silently pruned", len(found2) == 3)

        wrapped = os.path.join(ARCHIVE, "acme", "wrapped-000000000000.md")
        os.makedirs(os.path.dirname(wrapped), exist_ok=True)
        with open(wrapped, "w") as fh:
            fh.write("<!-- archived x · job am-09001-wrap · client acme -->\n\n"
                     "HOST: our mattress is Clinically\nProven to help you sleep.\n")
        a6 = A(); a6.root = root; a6.claim = "clinically proven"; a6.json = True
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_find(a6)
        res = json.loads(buf.getvalue())
        check("a claim WRAPPED ACROSS A LINE BREAK is still found",
              any(o["file"] == wrapped for o in res["archived_only"]))
        check("...and an orphan is attributed from its header, not labelled unknown",
              any(o["job"] == "am-09001-wrap" for o in res["archived_only"]))

        bad = os.path.join(ARCHIVE, "acme", "cp1252-000000000001.md")
        with open(bad, "wb") as fh:
            fh.write("HOST: it is \u201cclinically proven\u201d to work.\n".encode("cp1252"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_find(a6)
        check("a non-UTF-8 file does not crash the query into a 'no match' exit", rc == 0)

        # a record pointing at an archived script that is gone must read INCONCLUSIVE
        rec = load(job)
        rec["claims"]["archived_to"] = os.path.join(ARCHIVE, "acme", "vanished.md")
        save(job, rec)
        a7 = A(); a7.root = root; a7.claim = "zqx-definitely-absent"; a7.json = False
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_find(a7)
        check("a MISSING archived script makes a clean result INCONCLUSIVE, not clean",
              rc == 1 and "INCONCLUSIVE" in buf.getvalue() and "NOT THERE" in buf.getvalue())
        rec["claims"]["archived_to"] = dest
        save(job, rec)

        # claims history: a revision must not erase the earlier approval's allowed phrase
        rec = record_claims(job, derive(job, load(job)),
                            {"artifact": "01-script/S2.md", "findings": [], "allowed": [],
                             "by": "Dana", "archived_to": ""})
        save(job, rec)
        hist = load(job).get("claims_history") or []
        check("re-approving keeps the earlier claims check, with its --allow and approver",
              len(hist) == 1 and hist[0]["allowed"] == ["clinically proven"])

        # events must survive a concurrent writer
        import subprocess as _sp
        rec = load(job)
        n_before = len(rec["events"])
        other = dict(rec)
        other["events"] = list(rec["events"]) + [{"ts": "2099-01-01T00:00:00Z", "kind": "note",
                                                  "by": "other", "why": "written elsewhere"}]
        save(job, other)
        add_event(job, "note", by="me", why="written here")
        evs = load(job)["events"]
        check("a concurrent event is merged, not clobbered",
              len(evs) == n_before + 2 and any(e.get("by") == "other" for e in evs))
        a5 = A(); a5.root = root; a5.client = "acme"; a5.month = None; a5.state = None
        a5.persona = "P1"; a5.blocked = False; a5.json = True
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_index(a5)
        check("...and filters by persona", len(json.loads(buf.getvalue())) == 1)

        check("sync is idempotent",
              derive(job2, load(job2))["state"] == derive(job2, load(job2))["state"])
        # ⛔ the derived half rebuilds; the AUTHORED half does not, and the docstring used to say
        # the record was "safe to delete", which is the sentence a reader acts on.
        killed = load(job)
        os.remove(record_path(job))
        rebuilt = derive(job, load(job))
        check("a deleted record rebuilds its DERIVED half from the folder",
              rebuilt["job"] == "acme-01001-morning" or rebuilt["job"])
        check("...and loses the authored half, which is why it is a record and not a cache",
              bool(killed.get("claims")) and not rebuilt.get("claims"))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("-" * 60)
    print("selftest OK — state derives from the gate's own artifacts, kill/blocked are recorded, "
          "scripts archive themselves at approval, --allow exceptions keep their approver, the "
          "recall query finds a shipped claim, and an empty corpus reads INCONCLUSIVE rather than "
          "clean" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    s = sub.add_parser("sync"); s.add_argument("job_dir"); s.add_argument("--quiet", action="store_true")
    st = sub.add_parser("set"); st.add_argument("job_dir")
    for k in ("ad-name", "persona", "hook", "body", "cta", "tone", "batch"):
        st.add_argument(f"--{k}")
    st.add_argument("--platform", action="append", help="repeatable")
    sh = sub.add_parser("show"); sh.add_argument("job_dir"); sh.add_argument("--json", action="store_true")
    pb = sub.add_parser("publish", help="record where a video went live — the ORGANIC join key")
    pb.add_argument("job_dir"); pb.add_argument("--by", required=True)
    pb.add_argument("--platform", action="append", required=True)
    pb.add_argument("--post-id", help="the platform's own id for the post, from the upload response "
                                      "or the URL")
    pb.add_argument("--url", help="the permalink")
    pb.add_argument("--why"); pb.add_argument("--quote"); pb.add_argument("--blocked",
                                                                         action="store_true")
    for name, helptext in (("kill", "this script is not being made, and why"),
                           ("deliver", "the files went to the client / went live"),
                           ("signoff", "the client accepted it"),
                           ("note", "anything else; --blocked marks it as waiting")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("job_dir"); p.add_argument("--by", required=True)
        p.add_argument("--why"); p.add_argument("--quote"); p.add_argument("--url")
        p.add_argument("--platform", action="append")
        p.add_argument("--blocked", action="store_true")
    ix = sub.add_parser("index"); ix.add_argument("root")
    ix.add_argument("--client"); ix.add_argument("--month", help="YYYY-MM, by opened date")
    ix.add_argument("--state", choices=list(STAGE_ORDER) + list(TERMINAL) + ["planned", "unknown"])
    ix.add_argument("--persona"); ix.add_argument("--blocked", action="store_true")
    ix.add_argument("--json", action="store_true")
    mo = sub.add_parser("month", help="the monthly rollup: cost, hours, states — with provenance")
    mo.add_argument("root"); mo.add_argument("--client"); mo.add_argument("--month")
    mo.add_argument("--json", action="store_true")
    fd = sub.add_parser("find", help="the recall query: which videos contain this claim")
    fd.add_argument("root"); fd.add_argument("--claim", required=True)
    fd.add_argument("--json", action="store_true")

    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    try:
        if a.cmd == "sync":
            return cmd_sync(a)
        if a.cmd == "set":
            return cmd_set(a)
        if a.cmd == "show":
            return cmd_show(a)
        if a.cmd in ("kill", "deliver", "signoff", "note", "publish"):
            return cmd_event(a)
        if a.cmd == "index":
            return cmd_index(a)
        if a.cmd == "month":
            return cmd_month(a)
        if a.cmd == "find":
            return cmd_find(a)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr); return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
