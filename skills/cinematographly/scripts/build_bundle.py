#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
build_bundle.py — build the installable bundle (`<name>.plugin`, a zip) from an ALLOW-LIST.

Until v2.58.0 there was no builder in the repository: each release was zipped by hand, taking the plugin
folder and leaving out what someone remembered to leave out. A folder nobody remembered (a lab, a trash
folder, a studio's history, a client file) would ship. Here nothing ships unless the list below names it,
and the selftest fails if anything else gets in.

What ships (paths from the plugin root):
  .claude-plugin/plugin.json · hooks/hooks.json · agents/*.md · README.md · requirements.txt (v2.63.0) · LICENSE (v2.64.0)
  skills/cinematographly/ — the five top-level pages, assets/, modes/, references/, scripts/,
    clients/ (templates, the test bench and the invented sample only), memory/ (templates only),
    evals/README.md, script-archive/README.md
Never, even inside an allowed folder: __pycache__, *.pyc, .DS_Store, node_modules, *.env, *.key.

Refuses to write (exit 1) when:
  - a file carries a key-shaped token (an API key, a token, a private key block);
  - the change list's newest row does not name the manifest's version;
  - with --names FILE (a private list kept OUTSIDE the plugin, one `term<TAB>kind<TAB>ci|cs|re|rei` per line; re/rei = a regular expression),
    any listed term is found. It prints the count and the file, never the term.

  python3 build_bundle.py --out PATH [--names FILE]     # write the bundle
  python3 build_bundle.py --list                        # print what would ship; write nothing
  python3 build_bundle.py --selftest
"""
from __future__ import annotations
import argparse
import fnmatch
import json
import os
import re
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_DIR))
SK = "skills/cinematographly/"

# Exact files, and folders taken whole. Order matters only for the zip: the manifest first, then the hooks.
FIRST = [".claude-plugin/plugin.json", "hooks/hooks.json"]
EXACT = set(FIRST) | {"README.md", "requirements.txt", "LICENSE", "NOTICE", "COMMERCIAL.md", "REUSE.toml",
                      "LICENSES/LicenseRef-Cinematographly-Studio.txt"} | {SK + f for f in ("SKILL.md", "PIPELINE.md", "START-HERE.md", "GLOSSARY.md", "CHANGELOG.md",
                                         "evals/README.md", "script-archive/README.md",
                                         "memory/README.md", "memory/episodes/_TEMPLATE.md", "memory/proposals/README.md")}
FOLDERS = [SK + d for d in ("assets/", "modes/", "references/", "scripts/")]
PATTERNS = ["agents/*.md", "commands/*.md",                          # (3.0.0) the slash commands
            SK + "clients/_*.md", SK + "clients/acme.md", SK + "clients/*._TEMPLATE.json", SK + "clients/*.acme.json"]
JUNK_DIRS = {"__pycache__", "node_modules", ".git"}
SPDX_MARK = "SPDX-License-Identifier: LicenseRef-Cinematographly-Studio"   # (3.0.0) every shipped script carries it
JUNK_FILES = ("*.pyc", ".DS_Store", "*.env", ".env*", "*.key", "*-key.txt")
KEY_RE = re.compile(r"sk-(?:ant-)?[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|"
                    r"AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----")


def allowed(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in JUNK_DIRS for p in parts) or any(fnmatch.fnmatch(parts[-1], j) for j in JUNK_FILES):
        return False
    if rel in EXACT or any(rel.startswith(f) for f in FOLDERS):
        return True
    return any(fnmatch.fnmatchcase(rel, p) and rel.count("/") == p.count("/") for p in PATTERNS)


def collect(root: str) -> list[str]:
    """Every file under `root` the allow-list takes, as plugin-relative paths, the manifest and hooks first."""
    out = []
    for dp, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in JUNK_DIRS)
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")
            if allowed(rel):
                out.append(rel)
    first = [f for f in FIRST if f in out]
    return first + sorted(f for f in out if f not in first)


def load_names(path: str) -> list[tuple[re.Pattern, str]]:
    out = []
    for raw in open(path, encoding="utf-8"):
        raw = raw.rstrip("\n")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t")
        term, flags = parts[0].strip(), (parts[2].strip() if len(parts) > 2 else "ci")
        if term and flags in ("re", "rei"):      # (3.0.0) a regular expression: `re` case-sensitive, `rei` not
            out.append((re.compile(term, re.I if flags == "rei" else 0), parts[1].strip() if len(parts) > 1 else "term"))
        elif term:
            rx = re.compile(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", 0 if flags == "cs" else re.I)
            out.append((rx, parts[1].strip() if len(parts) > 1 else "term"))
    return out


# (v2.64.0, house decision 4) The credit the publisher chose is declared in the manifest's `author` and `homepage`.
# Those exact strings may appear in the manifest and the LICENSE, and nowhere else: a listed name anywhere else, or
# any OTHER listed name in those two files, still refuses the build.
CREDIT_FILES = (".claude-plugin/plugin.json", "LICENSE", "LICENSES/LicenseRef-Cinematographly-Studio.txt", "NOTICE",
                "REUSE.toml", "README.md", "COMMERCIAL.md",   # (3.0.0) + the licence copies and the public pages
                "CONTRIBUTING.md", "SECURITY.md", ".claude-plugin/marketplace.json")   # the public repo's own (overlay)


def declared_credit(root: str) -> list[str]:
    try:
        d = json.load(open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return []
    a = d.get("author") or {}
    name = a.get("name") if isinstance(a, dict) else str(a)
    repo = d.get("repository")
    repo = repo.get("url") if isinstance(repo, dict) else repo
    slug = re.sub(r"^https?://github\.com/|\.git$", "", repo) if isinstance(repo, str) and "github.com/" in repo else None
    out = [s for s in (name, a.get("url") if isinstance(a, dict) else None, a.get("email") if isinstance(a, dict) else None,
                       d.get("homepage"), repo, slug) if s]
    out += [part.strip() for part in str(name or "").split(",") if part.strip()]
    return sorted(set(out), key=len, reverse=True)


def problems(root: str, files: list[str], names: list | None = None) -> list[str]:
    P = []
    try:
        version = json.load(open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError) as e:
        return [f"the manifest cannot be read: {e}"]
    for f in FIRST:
        if f not in files:
            P.append(f"{f} is missing")
    lic, lic2 = os.path.join(root, "LICENSE"), os.path.join(root, "LICENSES", "LicenseRef-Cinematographly-Studio.txt")
    if os.path.isfile(lic) and os.path.isfile(lic2) and open(lic, encoding="utf-8").read() != open(lic2, encoding="utf-8").read():
        P.append("LICENSE and LICENSES/LicenseRef-Cinematographly-Studio.txt differ: they must be the same text")
    cl = os.path.join(root, SK + "CHANGELOG.md")
    rows = [l for l in open(cl, encoding="utf-8")] if os.path.isfile(cl) else []
    first_row = next((l for l in rows if re.match(r"^\|\s*\d+\.\d+", l)), "")
    if not first_row.startswith(f"| {version} |"):
        P.append(f"the change list's newest row does not name version {version}: add a line to {SK}CHANGELOG.md")
    for rel in files:
        try:
            txt = open(os.path.join(root, rel), encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue                                   # binaries: the allow-list is their check
        if KEY_RE.search(txt):
            P.append(f"{rel}: a key-shaped token")
        if rel.endswith((".py", ".mjs", ".js")) and SPDX_MARK not in txt[:400]:
            P.append(f"{rel}: no licence header (the provenance marks, NOTICE) — add the two SPDX / project-id lines")
        if names and rel in CREDIT_FILES:
            for s in declared_credit(root):
                txt = re.sub(re.escape(s), " ", txt, flags=re.I)
        for rx, kind in names or []:
            n = len(rx.findall(txt))
            if n:
                P.append(f"{rel}: {n} match(es) of a listed {kind}")
    return P


def build(root: str, out: str, names_file: str | None = None) -> tuple[int, list[str], list[str]]:
    files = collect(root)
    P = problems(root, files, load_names(names_file) if names_file else None)
    if P:
        return 1, files, P
    tmp = out + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(os.path.join(root, rel), rel)
    os.replace(tmp, out)
    return 0, files, []


def selftest() -> int:
    fails: list[str] = []

    def check(name: str, cond: bool, info: str = "") -> None:
        print(f"  {'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  — {info}"))
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "plugin")

        def put(rel: str, text: str | None = None) -> None:
            if text is None:
                text = (f"# {SPDX_MARK}\nx\n" if rel.endswith((".py", ".mjs", ".js")) else "x\n")
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(text)

        put(".claude-plugin/plugin.json", json.dumps({"name": "cinematographly", "version": "9.9.0"}))
        put("hooks/hooks.json", "{}")
        put("agents/a.md")
        for rel in ("commands/next.md", "NOTICE", "COMMERCIAL.md", "REUSE.toml", "LICENSE",
                    "LICENSES/LicenseRef-Cinematographly-Studio.txt"):
            put(rel)                                               # (3.0.0) the commands and the licence files
        put(SK + "SKILL.md")
        put(SK + "CHANGELOG.md", "| Version | Date | What |\n|---|---|---|\n| 9.9.0 | d | x |\n| 9.8.0 | d | y |\n")
        for rel in ("assets/a.json", "assets/sub/b.js", "modes/m.md", "references/r.md", "scripts/s.py",
                    "clients/_TEMPLATE.md", "clients/_lab.md", "clients/acme.md", "clients/costs._TEMPLATE.json",
                    "clients/costs.acme.json", "memory/README.md", "memory/episodes/_TEMPLATE.md", "memory/proposals/README.md"):
            put(SK + rel)
        should_ship = {".claude-plugin/plugin.json", "hooks/hooks.json", "agents/a.md", SK + "SKILL.md", SK + "CHANGELOG.md",
                       "commands/next.md", "NOTICE", "COMMERCIAL.md", "REUSE.toml", "LICENSE",
                       "LICENSES/LicenseRef-Cinematographly-Studio.txt"} | {
            SK + r for r in ("assets/a.json", "assets/sub/b.js", "modes/m.md", "references/r.md", "scripts/s.py",
                             "clients/_TEMPLATE.md", "clients/_lab.md", "clients/acme.md", "clients/costs._TEMPLATE.json",
                             "clients/costs.acme.json", "memory/README.md", "memory/episodes/_TEMPLATE.md", "memory/proposals/README.md")}
        stray = ["/".join(("_lab", "lab-00001", "notes.md")), "_dist/old.plugin", "_backup-x/SKILL.md", "evals/case-1/case.json",
                 SK + "_to_delete/old.md", SK + "private/notes.md", SK + "memory/LEDGER.md",
                 SK + "memory/episodes/2026-01-01-job.md", SK + "memory/proposals/2026-01-01/PROPOSAL.md",
                 SK + "clients/realbrand.md", SK + "clients/costs.realbrand.json", SK + "clients/sub/acme.md",
                 SK + "scripts/__pycache__/s.cpython-312.pyc", SK + "assets/.DS_Store", SK + "assets/node_modules/x/index.js",
                 SK + "scripts/.env", SK + "references/x.key", "agents/sub/b.md", "README-dev.md",
                 "commands/sub/x.md", "_public/overlay/.github/workflows/ci.yml", "_public/publish_public.py"]
        for rel in stray:
            put(rel)
        files = collect(root)
        check("everything the allow-list names ships", should_ship <= set(files), str(sorted(should_ship - set(files))))
        leaked = sorted(set(files) - should_ship)
        check("nothing else ships: labs, trash, history, real clients, stray folders, caches, keys", not leaked, str(leaked))
        check("the manifest is first and the hooks second", files[:2] == FIRST, str(files[:2]))
        out = os.path.join(td, "b.plugin")
        rc, _f, P = build(root, out)
        names = zipfile.ZipFile(out).namelist() if rc == 0 else []
        check("a clean tree builds, and the zip holds exactly the allowed files", rc == 0 and set(names) == should_ship, str(P))

        put("LICENSES/LicenseRef-Cinematographly-Studio.txt", "different\n")
        rc, _f, P = build(root, out + "L")
        check("SABOTAGE two licence copies that differ refuse", rc == 1 and any("must be the same text" in p for p in P), str(P))
        put("LICENSES/LicenseRef-Cinematographly-Studio.txt")
        put(SK + "scripts/s.py", "print('no header')\n")
        rc, _f, P = build(root, out + "h")
        check("SABOTAGE a shipped script without its licence header refuses", rc == 1 and any("licence header" in p for p in P), str(P))
        put(SK + "scripts/s.py")
        put(SK + "references/r.md", "token: sk-ant-" + "a" * 40 + "\n")
        rc, _f, P = build(root, out + "2")
        check("SABOTAGE a key-shaped token refuses, and nothing is written",
              rc == 1 and any("key-shaped" in p for p in P) and not os.path.exists(out + "2"), str(P))
        put(SK + "references/r.md")

        put(SK + "references/r.md", "made for Zorblax Mattress in 2026\n")
        nf = os.path.join(td, "names.txt")
        open(nf, "w", encoding="utf-8").write("# private\nzorblax\tclient or brand\tci\n")
        rc, _f, P = build(root, out + "3", nf)
        check("SABOTAGE a listed name refuses, saying the file and the kind, never the name",
              rc == 1 and any("references/r.md" in p and "client or brand" in p for p in P)
              and not any("zorblax" in p.lower() for p in P), str(P))
        put(SK + "references/r.md")
        # (3.0.0) a `re` line is a regular expression: a course id shape, not one fixed word
        put(SK + "references/r.md", "as the course showed (XYZ-042)\n")
        open(nf, "w", encoding="utf-8").write("XYZ-\\d+\tcourse id\tre\n")
        rc, _f, P = build(root, out + "3r", nf)
        check("SABOTAGE a regex pattern line refuses a match of its shape",
              rc == 1 and any("course id" in p for p in P), str(P))
        put(SK + "references/r.md")

        # (v2.64.0) the declared credit may sit in the manifest and the LICENSE, and nowhere else
        open(nf, "w", encoding="utf-8").write("jane roe\tperson\tci\nroe films\tstudio\tci\nbob client\tperson\tci\n")
        put(".claude-plugin/plugin.json", json.dumps({"name": "cinematographly", "version": "9.9.0",
                                                      "author": {"name": "Jane Roe, Roe Films LLC", "url": "https://roe.example"},
                                                      "homepage": "https://roe.example"}))
        put("LICENSE", "Copyright (c) 2026 Roe Films LLC.\nMade by Jane Roe, Roe Films LLC.\n")
        put("LICENSES/LicenseRef-Cinematographly-Studio.txt", "Copyright (c) 2026 Roe Films LLC.\nMade by Jane Roe, Roe Films LLC.\n")
        rc, _f, P = build(root, out + "6", nf)
        check("(v2.64.0) the declared author credit in the manifest and the LICENSE builds", rc == 0, str(P))
        put(SK + "references/r.md", "thanks to Jane Roe\n")
        rc, _f, P = build(root, out + "7", nf)
        check("(v2.64.0) SABOTAGE the same name anywhere else still refuses", rc == 1 and any("references/r.md" in p for p in P), str(P))
        put(SK + "references/r.md")
        put("LICENSE", "Copyright (c) 2026 Roe Films LLC.\nLicensed to Bob Client.\n")
        put("LICENSES/LicenseRef-Cinematographly-Studio.txt", "Copyright (c) 2026 Roe Films LLC.\nLicensed to Bob Client.\n")
        rc, _f, P = build(root, out + "8", nf)
        check("(v2.64.0) SABOTAGE another listed name in the LICENSE still refuses", rc == 1 and any("LICENSE" in p for p in P), str(P))
        os.remove(os.path.join(root, "LICENSE"))
        os.remove(os.path.join(root, "LICENSES", "LicenseRef-Cinematographly-Studio.txt"))
        put(".claude-plugin/plugin.json", json.dumps({"name": "cinematographly", "version": "9.9.0"}))
        put(SK + "references/r.md", "made for Zorblaxian lighting\n")
        rc, _f, P = build(root, out + "4", nf)
        check("a name glued to other letters is not a match", rc == 0, str(P))
        put(SK + "references/r.md")

        put(".claude-plugin/plugin.json", json.dumps({"name": "cinematographly", "version": "9.9.1"}))
        rc, _f, P = build(root, out + "5")
        check("SABOTAGE a version the change list does not name refuses", rc == 1 and any("9.9.1" in p for p in P), str(P))

    # the real plugin, as it stands
    real = collect(PLUGIN_ROOT)
    bad = [f for f in real if (f.split("/")[0] not in (".claude-plugin", "hooks", "agents", "skills", "commands")
                               and f not in EXACT)
           or "/_to_delete/" in f or "/__pycache__/" in f or f.startswith(SK + "memory/") and f not in EXACT]
    check("this plugin: nothing outside the allow-list, no trash folder, no history, no caches", not bad, str(bad[:6]))
    check("(v2.63.0) the install guide and the requirements ship", "README.md" in real and "requirements.txt" in real,
          str([f for f in real if "/" not in f]))
    check("this plugin: the manifest, the hooks, the router and the gate are in", all(
        f in real for f in FIRST + [SK + "SKILL.md", SK + "scripts/gate.py"]))
    clients = sorted(f.rsplit("/", 1)[1] for f in real if f.startswith(SK + "clients/"))
    check("this plugin: clients/ ships the templates, the test bench and the invented sample only",
          all(c.startswith("_") or "acme" in c or "_TEMPLATE" in c for c in clients) and "acme.md" in clients, str(clients))
    with tempfile.TemporaryDirectory() as td:
        rc, files, P = build(PLUGIN_ROOT, os.path.join(td, "real.plugin"))
        check("this plugin builds: no key-shaped token, and the change list names the version", rc == 0, str(P[:4]))
    print(f"SELFTEST: {'OK' if not fails else 'FAIL'} ({len(fails)} failed)")
    return 1 if fails else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="where to write the bundle (required unless --list)")
    ap.add_argument("--names", help="a private list of names that must not ship (kept outside the plugin)")
    ap.add_argument("--list", action="store_true", help="print what would ship; write nothing")
    ap.add_argument("--root", default=PLUGIN_ROOT, help="the plugin root (default: the one this script is in)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.list:
        files = collect(a.root)
        print("\n".join(files))
        print(f"\n{len(files)} files", file=sys.stderr)
        return 0
    if not a.out:
        ap.error("--out is required (the bundle is never written to a default place)")
    rc, files, P = build(a.root, os.path.abspath(a.out), a.names)
    if rc:
        print("REFUSED: the bundle was not written.", file=sys.stderr)
        for p in P:
            print(f"  - {p}", file=sys.stderr)
        return rc
    print(f"wrote {a.out}: {len(files)} files, {os.path.getsize(a.out):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
