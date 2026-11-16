#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""provenance.py — write and audit the provenance record for ANY reference asset, whatever it came
from: the client's own files, your own shoot, licensed stock, a Pixabay download, or an AI
generation. `prompt_lint.py` refuses a reference with no sidecar, so this is how an asset becomes
usable — and clearance is not something you type, it is the four §5 blockers answered.

Why (2026-09-06). The reference plan landed the same morning and only `pixabay_search.py` could
write a sidecar, which meant a CLIENT-SUPPLIED photo could never satisfy the lint — a deadlock, and
on the only live account at the time, the references ARE the client's fifteen renders. This closes
it without loosening anything: an asset still cannot be cleared by assertion.

  provenance.py record <file> --source <kind> [options]     write/replace the sidecar
  provenance.py audit <dir> [--json]                        every asset under a folder: sidecar?
                                                            cleared? which blockers are unanswered
  provenance.py --selftest

Exit codes: 0 ok · 1 findings (audit) or refusal (record) · 2 usage/IO error.

The four blockers (`references/stock-sourcing.md` §5) — each MUST be answered to reach CLEARED
-----------------------------------------------------------------------------------------------
  Two prefixes clear a blocker instead of `none`: **`released:<who holds it>`** (a release exists)
  and **`owned:<who owns it>`** (the rights holder who granted the asset owns the thing itself — a
  client's own logo on their own pack-shot is not a third-party mark). Anything else is a note, and
  a note is an outstanding blocker.

  --face          a recognisable face. `none` · `released:<who holds it>` · a note = NOT cleared.
                  ⛔ No release, none obtainable in practice → hard block for FINAL footage.
                  Reference-only is defensible provided the output does not reproduce the likeness.
  --trademark     a visible mark, logo or brand. `none` · `removed` · `owned:<the client>` · a note.
                  Third-party marks: flat licence prohibition for commercial use, and not cured by
                  cropping to "mostly gone". The client's own mark on their own asset is `owned:`.
  --property      a distinctive building or private property. `none` · `released:<who>` ·
                  `owned:<who>` · a note.
  --transformation how the finished frame is a new work, not a near-raw redistribution. Required
                  prose — `--transformation none` is refused, because "none" is not an answer here.

Clearance is DERIVED, never asserted:
  every blocker answered and none outstanding + --cleared-by --cleared-date  → "CLEARED by X on D"
  any blocker outstanding, or no --cleared-by                                → "NOT CLEARED — <what>"
  --reference-only                                                          → "REFERENCE-ONLY — the
                                                                              likeness/mark must not
                                                                              reach the output"

What it cannot do
-----------------
- **It is a record, not a licence and not legal advice.** It writes down who says what, and when.
  Whether the client actually holds the rights they assert is a question for the client, in writing.
- It cannot look at the picture. `--face none` on an image with a face in it is a false record, and
  the only thing standing behind it is the name in `--cleared-by`. That is the point of the name.
- It cannot clear an AI generation's inheritance for you — a generation made FROM a blocked asset
  inherits the block (stock-sourcing.md §5, last row). Record the parent in `--derived-from`.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ("client-supplied", "own-shoot", "pixabay", "licensed", "ai-generated", "public-domain")
BLOCKERS = ("face", "trademark", "property", "transformation")
CLEAR_WORDS = {"none", "absent", "no", "removed", "n/a", "na"}
SCHEMA = 1


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def today() -> str:
    return dt.date.today().isoformat()


def sidecar_path(asset: str) -> str:
    """The convention: `<asset filename>.json`, appended, never `<stem>.json`.

    Appending cannot collide — a JPEG's record and a PNG's record of the same
    stem stay two files, where a shared stem would collapse them into one. The stem form is still READ (see find_sidecar) because assets
    downloaded before 2026-09-06 carry it."""
    return asset + ".json"


def legacy_sidecar_path(asset: str) -> str:
    return os.path.splitext(asset)[0] + ".json"


def find_sidecar(asset: str) -> str:
    """The sidecar an asset actually has, current convention first. Empty string if it has none.

    ⛔ Every reader in the skill calls this. A live run on 2026-09-06 found `provenance.py record`
    writing the appended form while `pixabay_search.py` had written the stem form for the same
    file, and two readers disagreeing about which one wins — so a freshly cleared asset was read
    back as NOT CLEARED. One resolver, one precedence, everywhere."""
    for c in (sidecar_path(asset), legacy_sidecar_path(asset)):
        if os.path.isfile(c):
            return c
    return ""


def _clears(v: str) -> bool:
    """A blocker is answered-and-clear when it is a clear word — bare, or followed by the reason
    ("none — no people anywhere in frame", which is better evidence than bare "none") — or carries
    a `released:` / `owned:` prefix."""
    t = v.strip().lower()
    if t.startswith(("released:", "owned:")):
        return True
    if t in CLEAR_WORDS:
        return True
    for w in CLEAR_WORDS:
        if t.startswith(w) and len(t) > len(w) and t[len(w)] in " ,;:—–-(":
            return True
    return False


def outstanding(blockers: dict) -> list:
    """Which blockers are unanswered or answered with something that still blocks."""
    out = []
    for b in BLOCKERS:
        v = (blockers.get(b) or "").strip()
        if not v:
            out.append(f"{b} (unanswered)")
        elif b == "transformation":
            if v.lower() in CLEAR_WORDS or len(v.split()) < 4:
                out.append(f"{b} (needs a sentence saying how the frame is a new work)")
        elif _clears(v):
            continue
        else:
            out.append(f"{b}: {v}")
    return out


def build(asset: str, a) -> dict:
    blockers = {b: (getattr(a, b) or "") for b in BLOCKERS}
    out = outstanding(blockers)
    if a.reference_only:
        clearance = ("REFERENCE-ONLY — may condition a generation; the likeness, mark or façade must "
                     "not be reproduced in the output (stock-sourcing.md §5)")
    elif out:
        clearance = "NOT CLEARED — outstanding: " + "; ".join(out)
    elif not a.cleared_by:
        clearance = ("NOT CLEARED — every blocker is answered but nobody signed it; pass --cleared-by "
                     "and --cleared-date")
    else:
        clearance = f"CLEARED by {a.cleared_by} on {a.cleared_date or today()}"
    rec = {
        "schema": SCHEMA,
        "file": os.path.basename(asset),
        "sha256": sha256_file(asset),
        "bytes": os.path.getsize(asset),
        "source": a.source,
        "holder": a.holder or "",
        "url": a.url or "",
        "licence": {"name": a.licence or ("client grant" if a.source == "client-supplied" else ""),
                    "terms": a.terms or "", "recorded": today()},
        "derived_from": a.derived_from or "",
        "blockers": blockers,
        "blockers_outstanding": out,
        "clearance": clearance,
        # The signature as a FIELD, not only inside the prose of `clearance` — a reader that has to
        # parse an English sentence to find out who signed cannot check that anybody did.
        "cleared_by": (a.cleared_by or "") if (not out and not a.reference_only) else "",
        "cleared_date": ((a.cleared_date or today()) if (a.cleared_by and not out
                                                         and not a.reference_only) else ""),
        "recorded_by": a.recorded_by or "",
        "recorded_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "reference": "references/stock-sourcing.md §5, §9",
    }
    return rec


def cmd_record(a) -> int:
    asset = os.path.abspath(a.file)
    if not os.path.isfile(asset):
        print(f"error: {a.file} is not a file — source the asset first", file=sys.stderr); return 2
    if a.source not in SOURCES:
        print(f"error: --source must be one of {', '.join(SOURCES)}", file=sys.stderr); return 2
    if a.source == "client-supplied" and not a.holder:
        print("REFUSED: a client-supplied asset needs --holder (who says they hold the rights). "
              "'The client sent it' is not a grant; the name is what a later reader checks.",
              file=sys.stderr)
        return 1
    if a.source == "licensed" and not (a.licence and a.url):
        print("REFUSED: --source licensed needs --licence and --url (the licence and where it lives)",
              file=sys.stderr)
        return 1
    if a.source == "ai-generated" and not a.derived_from:
        print("REFUSED: --source ai-generated needs --derived-from — a generation inherits every "
              "block its inputs carried (stock-sourcing.md §5, last row). Name the parent asset or "
              "write 'none — text only'.", file=sys.stderr)
        return 1
    rec = build(asset, a)
    sp = sidecar_path(asset)
    if os.path.isfile(sp) and not a.force:
        try:
            old = json.load(open(sp, encoding="utf-8"))
            if old.get("sha256") == rec["sha256"] and not a.force:
                pass
        except json.JSONDecodeError:
            old = {}
        print(f"REFUSED: {os.path.basename(sp)} exists — --force to replace it. A provenance record "
              f"that is quietly overwritten is not a record.", file=sys.stderr)
        return 1
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"WROTE {os.path.relpath(sp)}")
    print(f"  source: {rec['source']}" + (f" · holder: {rec['holder']}" if rec['holder'] else ""))
    print(f"  clearance: {rec['clearance']}")
    if rec["blockers_outstanding"]:
        print("  ⛔ outstanding: " + "; ".join(rec["blockers_outstanding"]))
        print("  → this asset may be planned into a prompt only as `use: reference-only`, and its "
              "likeness/mark must not reach the output.")
    return 0


def cmd_audit(a) -> int:
    root = os.path.abspath(a.dir)
    if not os.path.isdir(root):
        print(f"error: {a.dir} is not a directory", file=sys.stderr); return 2
    media = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".m4v", ".wav", ".mp3")
    rows, missing, notcleared = [], 0, 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in sorted(fn):
            if not f.lower().endswith(media):
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root)
            sp = sidecar_path(full)
            alt = os.path.splitext(full)[0] + ".json"
            side = sp if os.path.isfile(sp) else (alt if os.path.isfile(alt) else None)
            if not side:
                rows.append((rel, "—", "⛔ NO SIDECAR")); missing += 1; continue
            try:
                rec = json.load(open(side, encoding="utf-8"))
            except json.JSONDecodeError:
                rows.append((rel, "—", "⛔ unreadable sidecar")); missing += 1; continue
            clr = str(rec.get("clearance", ""))
            short = ("cleared" if clr.startswith("CLEARED")
                     else "reference-only" if clr.startswith("REFERENCE-ONLY") else "⛔ NOT CLEARED")
            if short.startswith("⛔"):
                notcleared += 1
            drift = ""
            if rec.get("sha256") and os.path.isfile(full) and rec["sha256"] != sha256_file(full):
                drift = " · ⛔ FILE CHANGED SINCE RECORD"
            rows.append((rel, rec.get("source", "?"), short + drift))
    if a.json:
        print(json.dumps({"root": root, "assets": len(rows), "no_sidecar": missing,
                          "not_cleared": notcleared,
                          "rows": [{"file": r, "source": s, "status": st} for r, s, st in rows]},
                         indent=2, ensure_ascii=False))
        return 1 if (missing or notcleared) else 0
    print(f"REFERENCE SET — {os.path.relpath(root)}\n")
    print(f"  {'asset':<46} {'source':<16} status")
    print("  " + "-" * 84)
    for r, s, st in rows:
        print(f"  {r[-46:]:<46} {s:<16} {st}")
    print(f"\n  {len(rows)} asset(s) · {missing} without a provenance record · {notcleared} not cleared")
    if missing or notcleared:
        print("  → `provenance.py record <file> --source ...` for each. prompt_lint.py refuses a "
              "reference with no sidecar, and an uncleared one unless it is `use: reference-only`.")
    return 1 if (missing or notcleared) else 0


def selftest() -> int:
    import tempfile
    class A:  # argparse stand-in
        def __init__(self, **kw):
            d = dict(source="client-supplied", holder="", url="", licence="", terms="",
                     derived_from="", face="", trademark="", property="", transformation="",
                     cleared_by="", cleared_date="", recorded_by="", reference_only=False, force=False)
            d.update(kw); self.__dict__.update(d)
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "bottle.jpg"); open(f, "wb").write(b"\xff\xd8 fixture")
        # unanswered blockers cannot be cleared, even with a signer
        r = build(f, A(holder="Acme Cycle Works", cleared_by="Dana"))
        assert r["clearance"].startswith("NOT CLEARED") and len(r["blockers_outstanding"]) == 4, r
        # answering them all, but nobody signed
        base = dict(holder="Acme Cycle Works", face="none", trademark="none", property="none",
                    transformation="regraded, recomposed and composited into a new frame")
        r = build(f, A(**base))
        assert "nobody signed it" in r["clearance"], r["clearance"]
        # signed → cleared
        r = build(f, A(**base, cleared_by="Dana", cleared_date="2026-09-06"))
        assert r["clearance"] == "CLEARED by Dana on 2026-09-06", r["clearance"]
        # a face that is present, not released, still blocks even when signed
        r = build(f, A(**{**base, "face": "the host is recognisable"}, cleared_by="Dana"))
        assert r["clearance"].startswith("NOT CLEARED") and "face" in r["clearance"], r["clearance"]
        # a released face passes
        r = build(f, A(**{**base, "face": "released:model release on file 2026-08-01"}, cleared_by="Dana"))
        assert r["clearance"].startswith("CLEARED"), r["clearance"]
        # the client's OWN mark on their own asset is not a third-party blocker
        r = build(f, A(**{**base, "trademark": "owned:Acme Cycle Works, their own wheel mark"},
                       cleared_by="Dana"))
        assert r["clearance"].startswith("CLEARED"), r["clearance"]
        # …but an unqualified note about a mark still blocks
        r = build(f, A(**{**base, "trademark": "a Coca-Cola can on the shelf"}, cleared_by="Dana"))
        assert r["clearance"].startswith("NOT CLEARED"), r["clearance"]
        # "transformation: none" is not an answer
        r = build(f, A(**{**base, "transformation": "none"}, cleared_by="Dana"))
        assert any("transformation" in o for o in r["blockers_outstanding"]), r
        # "none — <the reason>" clears, and is better evidence than a bare "none"
        r = build(f, A(**{**base, "face": "none — no people anywhere in frame",
                          "property": "none, vernacular terracing with no identifiable building"},
                       cleared_by="Dana"))
        assert r["clearance"].startswith("CLEARED"), r["clearance"]
        # a bare "no" plus a real concern still blocks
        r = build(f, A(**{**base, "face": "nobody released the man on the left"}, cleared_by="Dana"))
        assert r["clearance"].startswith("NOT CLEARED"), r["clearance"]
        # reference-only wins regardless
        r = build(f, A(**base, reference_only=True))
        assert r["clearance"].startswith("REFERENCE-ONLY"), r["clearance"]
        assert r["sha256"] == sha256_file(f)
    print("selftest OK — clearance is derived from the four blockers, never asserted: unanswered "
          "blocks, unsigned blocks, a present face blocks, a released face passes, "
          "'transformation: none' is refused, 'none — why' clears while a real concern still blocks, owned: clears a client's own mark, a third-party mark still blocks, reference-only always wins")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("record")
    r.add_argument("file")
    r.add_argument("--source", required=True, help=" | ".join(SOURCES))
    r.add_argument("--holder", help="who asserts the rights (required for client-supplied)")
    r.add_argument("--url"); r.add_argument("--licence"); r.add_argument("--terms")
    r.add_argument("--derived-from", help="the parent asset, for an AI generation")
    for b in BLOCKERS:
        r.add_argument(f"--{b}", help=f"§5 blocker: {b}")
    r.add_argument("--cleared-by"); r.add_argument("--cleared-date")
    r.add_argument("--recorded-by"); r.add_argument("--reference-only", action="store_true")
    r.add_argument("--force", action="store_true")
    au = sub.add_parser("audit"); au.add_argument("dir"); au.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    return {"record": cmd_record, "audit": cmd_audit}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
