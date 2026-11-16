#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""evaluate_promotion.py — the gate a proposed skill edit must clear before it is applied.

Autonomous self-modification of a production skill is how one wrong inference becomes permanent. So
consolidate.py can only PROPOSE, and this script runs the mechanical gates from
../references/self-evolution.md section 4 before a human reads the diff and decides.

Gates (mechanical here):
  freshness      no skill file changed since the proposal read it (hash compare-and-swap)
  cross-refs     every file path mentioned in the proposal resolves
  surface budget total skill size stays inside the ceiling, growth per pass is bounded
  client locks   the proposal does not touch text inside a client profile's hard-locks section
  evidence       every proposed edit names its evidence; single-witness edits are flagged
  surface budget the ALWAYS-LOADED surface (router + mode files + client index) and the largest
                 single reference, not the whole corpus — references load on demand
  eval set       the plugin root's evals/ case folders exist, did not SHRINK, and were NOT edited in this
                 proposal. This is set integrity, NOT regression — see the NOTE row it prints

The human review gate is NOT mechanical and is never waived. This script exits 0 meaning
"nothing mechanical blocks it", not "approved".

Usage
-----
  python3 evaluate_promotion.py 2026-09-01            # a folder under proposals/ in the studio's history folder
  python3 evaluate_promotion.py 2026-09-01 --max-growth 0.15
Exit codes: 0 gates pass · 1 a gate blocks · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import client_files, memory_home  # noqa: E402,E401  (the studio's own client and history folders)
# Budget what is ALWAYS LOADED, not the corpus. references/ are loaded on demand — one file at a
# time, when the router sends you there — so their total size is not what costs a session its
# context. The router surface (SKILL.md + modes/ + the client index) IS paid on every single run,
# and that is the number worth defending. The old whole-corpus ceiling blocked every proposal
# permanently once the craft references landed, which is a gate that fails safe into uselessness.
ROUTER_CEILING_BYTES = 120_000   # SKILL.md + modes/ + clients/_INDEX.md — paid on every run
FILE_CEILING_BYTES = 140_000     # no single reference may become un-loadable on its own
CORPUS_ADVISORY_BYTES = 1_500_000  # advisory only: warns, never blocks
LOCK_MARKERS = ("hard lock", "⛔")
PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|py))`")


def sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def skill_md_bytes() -> int:
    """Total markdown. Advisory only — see the ceilings above for what actually gates."""
    total = 0
    for root, dirs, files in os.walk(SKILL):
        dirs[:] = [d for d in dirs if d not in ("memory", "script-archive", "__pycache__")]
        for f in files:
            if f.endswith(".md"):
                total += os.path.getsize(os.path.join(root, f))
    return total


def router_bytes() -> int:
    """What every run pays: the router, the mode files, and the client index."""
    total = 0
    for rel in ("SKILL.md", os.path.join("clients", "_INDEX.md")):
        p = os.path.join(SKILL, rel)
        if os.path.exists(p):
            total += os.path.getsize(p)
    mdir = os.path.join(SKILL, "modes")
    if os.path.isdir(mdir):
        total += sum(os.path.getsize(os.path.join(mdir, f))
                     for f in os.listdir(mdir) if f.endswith(".md"))
    return total


def biggest_reference() -> tuple[str, int]:
    rdir = os.path.join(SKILL, "references")
    if not os.path.isdir(rdir):
        return ("", 0)
    sizes = [(f, os.path.getsize(os.path.join(rdir, f))) for f in os.listdir(rdir) if f.endswith(".md")]
    return max(sizes, key=lambda t: t[1]) if sizes else ("", 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proposal", help="folder name under proposals/ in the studio's history folder (scripts/memory_home.py)")
    ap.add_argument("--max-growth", type=float, default=0.20, help="max fractional growth of the md surface")
    a = ap.parse_args()

    d = os.path.join(memory_home.require(), "proposals", a.proposal)   # the studio's folder; refuses with the fix
    man_p = os.path.join(d, "MANIFEST.json")
    if not os.path.isfile(man_p):
        print(f"error: no MANIFEST.json in {d} — run consolidate.py first", file=sys.stderr)
        return 2
    man = json.load(open(man_p, encoding="utf-8"))
    prop_p = os.path.join(d, "PROPOSAL.md")
    proposal = open(prop_p, encoding="utf-8").read() if os.path.isfile(prop_p) else ""
    results: list[tuple[str, bool, str]] = []

    # --- freshness (CAS) ---
    drifted, missing = [], []
    for rel, h in man.get("baseline_hashes", {}).items():
        p = os.path.join(SKILL, rel)
        if not os.path.exists(p):
            missing.append(rel)
        elif sha(p) != h:
            drifted.append(rel)
    results.append(("freshness (CAS)", not drifted and not missing,
                    "clean" if not (drifted or missing) else
                    f"{len(drifted)} changed since the pass read them ({', '.join(drifted[:4])})"
                    + (f"; {len(missing)} missing" if missing else "")
                    + " — re-run consolidate.py against the current files"))

    # --- proposal present ---
    results.append(("proposal drafted", bool(proposal.strip()),
                    "PROPOSAL.md present" if proposal.strip() else "no PROPOSAL.md yet — draft it using PROMPT.md"))

    # --- cross-references resolve ---
    bad = sorted({m for m in PATH_RE.findall(proposal)
                  if not os.path.exists(os.path.join(SKILL, m)) and not m.startswith(("memory/", "clients/costs."))})
    results.append(("cross-references", not bad,
                    "all resolve" if not bad else f"unresolved: {', '.join(bad[:6])}"))

    # --- surface budget: the always-loaded surface, not the corpus ---
    now = skill_md_bytes()
    was = man.get("skill_bytes", now)
    growth = (now - was) / was if was else 0.0
    router = router_bytes()
    big_name, big_bytes = biggest_reference()
    surface_ok = (router <= ROUTER_CEILING_BYTES
                  and big_bytes <= FILE_CEILING_BYTES
                  and growth <= a.max_growth)
    detail = (f"router {router:,}B / {ROUTER_CEILING_BYTES:,} · largest reference {big_name} "
              f"{big_bytes:,}B / {FILE_CEILING_BYTES:,} · growth {growth:+.1%} (max {a.max_growth:+.0%})")
    if now > CORPUS_ADVISORY_BYTES:
        detail += f" · corpus {now:,}B is past the {CORPUS_ADVISORY_BYTES:,}B advisory — consider splitting"
    results.append(("surface budget", surface_ok, detail))

    # --- client hard locks ---
    lock_hits = []
    # every client folder the gate would read (client_files.py has the order), not the plugin's alone:
    # since v2.53.0 the plugin's clients/ holds no real client, so reading only it checked nothing
    # (v2.59.2) the search starts at the proposal too: it sits in the studio's history folder, and the
    # studio's `_cine-clients/` is usually beside that, wherever the tool is run from
    profiles: dict[str, str] = {}
    for cdir in client_files.search_dirs(d):
        if os.path.isdir(cdir):
            for f in sorted(os.listdir(cdir)):
                if f.endswith(".md") and not f.startswith("_"):
                    profiles.setdefault(f, os.path.join(cdir, f))
    studio_profiles = [p for p in profiles.values()
                       if os.path.dirname(os.path.abspath(p)) != os.path.abspath(client_files.PLUGIN_CLIENTS)]
    for f, fpath in sorted(profiles.items()):
        if f in proposal or f.replace(".md", "") in proposal:
            body = open(fpath, encoding="utf-8").read().lower()
            locked = [ln.strip() for ln in body.splitlines()
                      if any(k in ln for k in LOCK_MARKERS) and len(ln.strip()) > 12]
            for ln in locked:
                sig = re.findall(r"[a-z0-9_]{5,}", ln)[:3]
                if sig and all(s in proposal.lower() for s in sig):
                    lock_hits.append(f"{f}: {ln[:70]}")
    if not studio_profiles and not lock_hits:
        # (v2.59.2) no client profile outside the plugin was found, so nothing was checked: say so and block,
        # never report "untouched" for a check that did not run
        results.append(("client hard locks", False,
                        "NOT CHECKED — no client profile found outside the plugin (" +
                        client_files.where_looked(d) + "). Set CINE_CLIENTS to your client folder and re-run"))
    else:
        results.append(("client hard locks", not lock_hits,
                        "untouched" if not lock_hits else
                        f"{len(lock_hits)} proposed edit(s) overlap a lock — needs the client, not this pass: "
                        + "; ".join(lock_hits[:3])))

    # --- evidence named ---
    edits = [b for b in re.split(r"\n(?=##\s)", proposal) if b.strip().startswith("##")] if proposal else []
    unsourced = [b.splitlines()[0][:60] for b in edits if "evidence" not in b.lower()]
    results.append(("evidence named", not unsourced,
                    f"{len(edits)} edit section(s), all sourced" if not unsourced else
                    f"{len(unsourced)} without an Evidence line: {', '.join(unsourced[:3])}"))

    # --- eval set integrity + isolation ---
    # The suite moved to the PLUGIN ROOT on 2026-08-30 (evals/README.md in this skill says why): one
    # folder per case, each with a case.yaml, run by `claude plugin eval` and validated by eval_lint.py.
    # This gate read the old single-file path until 2026-10-21, so it blocked every proposal as
    # "unreadable" — a gate that fails closed for a reason unrelated to the proposal.
    plugin_evals = os.path.join(os.path.dirname(os.path.dirname(SKILL)), "evals")
    cases = sorted(c for c in (os.listdir(plugin_evals) if os.path.isdir(plugin_evals) else [])
                   if os.path.isfile(os.path.join(plugin_evals, c, "case.yaml")))
    well_formed = len(cases) >= 1
    detail = (f"{len(cases)} case(s) at the plugin root's evals/ (eval_lint.py checks their form)"
              if well_formed else f"no case folders with a case.yaml under {plugin_evals}")
    # Case count must not shrink: deleting a failing case is the cheapest way to make a gate pass.
    n_now = len(cases)
    n_base = int(man.get("eval_cases", 0) or 0)
    shrank = bool(n_base) and n_now < n_base
    if shrank:
        detail += f" — BUT the set shrank from {n_base} to {n_now}: cases were removed, not added"
    touched = "case.yaml" in proposal or any(f"evals/{c}" in proposal for c in cases)
    results.append(("eval set", well_formed and not touched and not shrank,
                    detail + ("" if not touched else
                              " — BUT the proposal edits the eval set. Keep the tests outside what this "
                              "pass optimises, or it will make the tests pass instead of the skill better")))
    # Say plainly what this gate is NOT. It checks the set's integrity, not the skill's behaviour.
    results.append(("eval non-regression", None,
                    "NOT AUTOMATED — no runner exists, so nothing here proves the skill still answers "
                    "these cases correctly. This is a MANUAL read of the affected cases before you "
                    "promote. Treating the integrity check above as a regression test is the exact "
                    "self-satisfying gate this skill warns about (scripts/README.md rule 8)."))

    print(f"\nevaluate_promotion — {d}\n" + "=" * 76)
    for name, ok, detail in results:
        tag = "NOTE" if ok is None else ("PASS" if ok else "BLOCK")
        print(f"  [{tag}] {name:<20} {detail}")
    print("-" * 76)
    blocked = [n for n, ok, _ in results if ok is False]
    if blocked:
        print(f"  RESULT: BLOCKED — {', '.join(blocked)}")
        return 1
    print("  RESULT: mechanical gates pass.")
    print("  NOT approved. A human still reads proposal.diff and decides — that gate is never waived.")
    print("  On acceptance: apply the edit, add a line to your ledger (LEDGER.md in the history folder) with its evidence, and move the")
    print("  consumed episodes to episodes/_promoted/ in that folder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
