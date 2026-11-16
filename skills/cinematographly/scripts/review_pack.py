#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""review_pack.py — show a stage to a client outside the chat, without opening a second way to approve. (3.1)

  review_pack.py make <job> <stage> --file F [--file F …]   # 07-review/<stage>/<code>/index.html + the files
  review_pack.py latest <job> <stage>                        # the code of the newest pack for that stage
  review_pack.py --selftest

The pack is a static page (concept options, a script, a storyboard, a rough cut) you send however you like. The
client's reply is EVIDENCE, kept beside the pack if you wish; it is never read as an approval. The approval is still
the named approver's own sentence in the chat, and once a stage has a pack it must carry the pack's 16-character code
("Approved, pack 3f9c1e7a20b4c5d6.") and be recorded with `gate.py approve <stage> --pack <code> --quote "…"`. The
gate refuses: no --pack, a code not in the quote, another pack's code, or files changed since the pack was made.
"""
from __future__ import annotations
import urllib.parse
import argparse, datetime as dt, hashlib, html, json, os, re, shutil, sys, tempfile

DIR = "07-review"
IMG = (".png", ".jpg", ".jpeg", ".webp", ".gif")
VID = (".mp4", ".mov", ".m4v", ".webm")


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe(stage: str) -> str:
    # lower-cased (build review 2): `FAMILY:hero` and `family:hero` are one stage on a case-sensitive disk too
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stage.lower())


def packs(job: str, stage: str) -> list:
    """[pack.json dicts] for a stage, oldest first."""
    d = os.path.join(job, DIR, _safe(stage))
    out = []
    for code in (os.listdir(d) if os.path.isdir(d) else []):
        try:
            out.append(json.load(open(os.path.join(d, code, "pack.json"), encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return sorted(out, key=lambda p: p.get("made", ""))


def broken(job: str, stage: str) -> list:
    """(3.1 build review 1) Pack folders for a stage whose pack.json cannot be read. A corrupt pack is not "no pack":
    the approval refuses until it is remade or a person removes the broken folder."""
    d = os.path.join(job, DIR, _safe(stage))
    bad = []
    for code in (os.listdir(d) if os.path.isdir(d) else []):
        if not os.path.isdir(os.path.join(d, code)):
            continue
        try:
            pk = json.load(open(os.path.join(d, code, "pack.json"), encoding="utf-8"))
            if not (isinstance(pk, dict) and pk.get("code") and isinstance(pk.get("files"), list)):
                raise ValueError("not a pack")
        except (OSError, ValueError):
            bad.append(code)
    return bad


def make(job: str, stage: str, files: list) -> tuple[dict | None, list]:
    job = os.path.realpath(job)
    probs, rows = [], []
    for f in files:
        # (3.1 review) realpath: a symlink inside the job that points outside it is outside the job
        p = os.path.realpath(f if os.path.isabs(f) else os.path.join(job, f))
        if not p.startswith(job + os.sep):
            probs.append(f"{f}: outside the job")
        elif not os.path.isfile(p):
            probs.append(f"{f}: not a file")
        else:
            rows.append({"rel": os.path.relpath(p, job), "sha256": _sha(p)})
    if not rows and not probs:
        probs.append("no files: pass --file for each thing the client should see")
    if probs:
        return None, probs
    code = hashlib.sha256((stage + "\n" + "\n".join(f"{r['rel']} {r['sha256']}" for r in sorted(
        rows, key=lambda r: r["rel"]))).encode()).hexdigest()[:16]
    d = os.path.join(job, DIR, _safe(stage), code)
    os.makedirs(os.path.join(d, "files"), exist_ok=True)
    items = []
    for r in rows:
        src = os.path.join(job, r["rel"])
        name = r["rel"].replace(os.sep, "__")
        shutil.copy2(src, os.path.join(d, "files", name))
        rel = "files/" + urllib.parse.quote(name)          # (3.1 review) a `#`, `?` or space in a name still loads
        ext = os.path.splitext(name)[1].lower()
        if ext in IMG:
            body = f'<img src="{html.escape(rel)}" alt="{html.escape(r["rel"])}" style="max-width:100%">'
        elif ext in VID:
            body = f'<video src="{html.escape(rel)}" controls style="max-width:100%"></video>'
        else:
            try:
                body = "<pre>" + html.escape(open(src, encoding="utf-8").read()) + "</pre>"
            except UnicodeDecodeError:
                body = f'<a href="{html.escape(rel)}">{html.escape(r["rel"])}</a>'
        items.append(f"<section><h2>{html.escape(r['rel'])}</h2>{body}</section>")
    page = (f"<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
            f"<title>Review — {html.escape(stage)}</title><body style='font-family:system-ui;max-width:860px;"
            f"margin:auto;padding:16px'><h1>Review: {html.escape(stage)}</h1>" + "".join(items) +
            f"<p><b>To approve, reply in your own words and include this pack code: {code}</b></p></body>")
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    pk = {"stage": stage, "code": code, "files": rows, "made": dt.datetime.now().isoformat(timespec="seconds")}
    json.dump(pk, open(os.path.join(d, "pack.json"), "w", encoding="utf-8"), indent=1)
    return pk, []


def approval_refusal(job: str, stage: str, pack: str | None, quote: str) -> str | None:
    """None when the approval may be recorded (no pack for the stage, or the newest pack named, in the quote, and
    current); else which part failed."""
    bad = broken(job, stage)
    if bad:
        return (f"the review pack(s) {', '.join(bad)} for `{stage}` cannot be read — make a new pack "
                f"(`review_pack.py make`) or have a person remove the broken folder; the approval waits")
    ps = packs(job, stage)
    if not ps:
        return None
    newest = ps[-1]
    if not pack:
        return (f"`{stage}` has a review pack ({newest['code']}): pass --pack {newest['code']}, with the approver's "
                f"sentence containing that code")
    pack = pack.strip().lower()
    if pack != newest["code"]:
        older = any(p["code"] == pack for p in ps)
        return (f"--pack {pack} is {'an older pack' if older else 'not a pack'} for `{stage}`; the newest is "
                f"{newest['code']}")
    if pack not in (quote or "").lower():
        return f"the approver's words do not contain the pack code {pack} — ask them to include it"
    for r in newest["files"]:
        p = os.path.join(job, r["rel"])
        if not os.path.isfile(p) or _sha(p) != r["sha256"]:
            return f"{r['rel']} changed after pack {pack} was made — make a new pack and show it again"
    return None


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "j"); os.makedirs(os.path.join(job, "01-script"))
        sp = os.path.join(job, "01-script", "SCRIPT-x-v1.md"); open(sp, "w").write("HOOK: a line\n")
        assert approval_refusal(job, "script", None, "approved") is None, "no pack: nothing changes"
        pk, P = make(job, "script", ["01-script/SCRIPT-x-v1.md"])
        assert pk and not P and len(pk["code"]) == 16 and os.path.isfile(os.path.join(job, DIR, "script", pk["code"], "index.html"))
        c = pk["code"]
        assert "pass --pack" in approval_refusal(job, "script", None, f"approved {c}"), "a pack exists: --pack required"
        assert "do not contain" in approval_refusal(job, "script", c, "approved, ship it"), "the code must be in the quote"
        assert approval_refusal(job, "script", c, f"Approved, pack {c}.") is None
        assert "not a pack" in approval_refusal(job, "script", "0" * 16, f"approved {'0' * 16}")
        open(sp, "a").write("a late edit\n")
        assert "changed after pack" in approval_refusal(job, "script", c, f"Approved, pack {c}."), "stale"
        pk2, _ = make(job, "script", ["01-script/SCRIPT-x-v1.md"])
        assert "an older pack" in approval_refusal(job, "script", c, f"Approved, pack {c}."), "another pack's code"
        assert approval_refusal(job, "script", pk2["code"], f"yes — pack {pk2['code']} is approved") is None
        _, P = make(job, "script", [os.path.join(td, "outside.md")])
        assert P and "outside the job" in P[0]
        pkf, P = make(job, "FAMILY:Hero", ["01-script/SCRIPT-x-v1.md"])
        assert not P and "has a review pack" in (approval_refusal(job, "family:hero", None, "fine") or ""), \
            "(build review 2) a pack made as FAMILY:Hero binds family:hero (one stage on a case-sensitive disk)"
        assert "family_hero" in os.listdir(os.path.join(job, DIR)), \
            "the folder is written lower-case, so a case-sensitive disk (Linux) finds it too"
        _bd = os.path.join(job, DIR, "script", "deadbeefdeadbeef"); os.makedirs(_bd)
        open(os.path.join(_bd, "pack.json"), "w").write("{")
        assert "cannot be read" in (approval_refusal(job, "script", pk2["code"], f"yes, pack {pk2['code']}") or ""), \
            "(3.1 review) a corrupt pack refuses, it is not 'no pack'"
        shutil.rmtree(_bd)
        open(os.path.join(td, "secret.md"), "w").write("not for the client\n")
        os.symlink(os.path.join(td, "secret.md"), os.path.join(job, "01-script", "link.md"))
        _, P = make(job, "script", ["01-script/link.md"])
        assert P and "outside the job" in P[0], "(3.1 review) a symlink out of the job is outside the job"
        open(os.path.join(job, "01-script", "take #2 v?.png"), "wb").write(b"PNG")
        pk3, P = make(job, "script", ["01-script/take #2 v?.png"])
        assert not P and "take%20%232%20v%3F.png" in open(os.path.join(job, DIR, "script", pk3["code"], "index.html")).read(), \
            "(3.1 review) the link to an odd file name is encoded"
    print("selftest OK — a pack is a static page with a 16-character code; with a pack, --pack is required, the code "
          "must be in the approver's words, another or older pack's code is refused, and a file changed since the "
          "pack refuses; no pack, nothing changes")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=("make", "latest")); ap.add_argument("job", nargs="?")
    ap.add_argument("stage", nargs="?"); ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.cmd and a.job and a.stage):
        ap.print_help(); return 2
    if a.cmd == "latest":
        ps = packs(a.job, a.stage)
        print(ps[-1]["code"] if ps else "none"); return 0 if ps else 1
    pk, P = make(a.job, a.stage, a.file)
    if P:
        print("REFUSED:\n  - " + "\n  - ".join(P), file=sys.stderr); return 1
    print(f"pack {pk['code']}: {os.path.join(a.job, DIR, _safe(a.stage), pk['code'], 'index.html')}\n"
          f"send it; to approve, the approver replies in the chat with the code in their words, then\n"
          f"  gate.py approve {a.stage} --pack {pk['code']} --by <approver> --quote \"<their words>\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
