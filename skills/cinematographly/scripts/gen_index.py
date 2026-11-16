#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""gen_index.py — build scripts/INDEX.md, the one-row-per-script index, from the files themselves.

A count written by hand goes stale: four were wrong at v2.51.0 ("39 files", "forty-odd", "twenty-odd
tools", "45 scripts"). This writes the index and the counts from what is on disk, and run_tests.py
runs it with --check, so a script added without regenerating fails the suite.

  python3 -B gen_index.py             # write scripts/INDEX.md, print the counts
  python3 -B gen_index.py --check     # write nothing; exit 1 if scripts/INDEX.md is out of date
  python3 -B gen_index.py --report    # print the long sheets (lines, where each script is named,
                                      # the references check); write nothing
  python3 -B gen_index.py --root DIR  # another skill root (default: the folder above scripts/)
  python3 -B gen_index.py --selftest

What it reads
    scripts/*.py, scripts/run_tests.py (SUITES, SELFTEST, CONSOLE_PASTE), scripts/README.md,
    references/*.md, references/_INDEX.md, SKILL.md, PIPELINE.md, modes/, clients/*.md, assets/,
    and, when present, the plugin's agents/, hooks/ and .claude-plugin/plugin.json.

What it writes
    scripts/INDEX.md and nothing else. The file holds only what changes when a script changes: its
    name, kind, selftest, network hint and first docstring line. No date, no plugin version, no
    line count and no "named in" column, so a release bump or an edit to a guide never makes it
    stale. Those live in --report, which is printed and never saved.

What it cannot do
    - It runs no script. "Selftest: yes" means the name is in run_tests.py's SELFTEST list. It does
      not show that the selftest passes.
    - "Network" is a text search for imports of network libraries. A hint, not proof.
    - "Named in" is a search for the file name. A script described without its name is missed.
    - It cannot say what a script is for beyond the first line of its docstring.
    - It does not own references/_INDEX.md. That registry stays hand-written ("Loaded when" and
      "Owns" cannot be generated) and skill_audit.py is the check that fails on a reference the
      registry misses. Here a mismatch is a note, never a failure.

Exit codes
    0  written (or --check: up to date), no findings. Notes do not change the exit code.
    1  a finding (a run_tests.py entry with no file; a tool named in no guide, no reference and no
       other script), or --check found scripts/INDEX.md out of date
    2  usage or IO error
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

INDEX = "INDEX.md"
NET_RE = re.compile(r"^\s*(?:import|from)\s+(urllib|http|socket|requests|httpx|ftplib|smtplib)\b", re.M)
LEAD_RE = re.compile(r"^[\w.-]+\.py\s*[—–-]+\s*")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def named(name: str, text: str) -> bool:
    """True when the exact file name appears, not as the tail of a longer name."""
    if name not in text:
        return False
    return re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])", text) is not None


def cell(text: str, limit: int = 150) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def runner_lists(run_tests: Path) -> dict:
    """SUITES, SELFTEST and CONSOLE_PASTE, read from run_tests.py's source without running it."""
    out = {"SUITES": [], "SELFTEST": [], "CONSOLE_PASTE": []}
    try:
        tree = ast.parse(read(run_tests))
    except SyntaxError:
        return out
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        for target in targets:
            if isinstance(target, ast.Name) and target.id in out:
                try:
                    out[target.id] = sorted(ast.literal_eval(value))
                except (ValueError, SyntaxError):
                    pass
    return out


def first_doc_line(src: str) -> str:
    try:
        doc = ast.get_docstring(ast.parse(src))
    except SyntaxError:
        return "(not parseable as Python)"
    if not doc or not doc.strip():
        return "(no docstring)"
    return LEAD_RE.sub("", doc.strip().splitlines()[0].strip())


def scan(root: Path) -> dict:
    sdir, rdir = root / "scripts", root / "references"
    plugin = root.parent.parent
    lists = runner_lists(sdir / "run_tests.py")
    readme, skill = read(sdir / "README.md"), read(root / "SKILL.md")

    doc_paths = sorted(rdir.glob("*.md")) + sorted((root / "modes").glob("*.md"))
    doc_paths += sorted((root / "clients").glob("*.md")) + sorted((root / "assets").glob("*.md"))
    doc_paths += [root / "PIPELINE.md"] + sorted((plugin / "agents").glob("*.md"))
    doc_paths += sorted((plugin / "hooks").glob("*.json"))
    docs = {p: read(p) for p in doc_paths if p.is_file()}

    sources = {p.name: read(p) for p in sorted(sdir.glob("*.py"))}
    scripts = []
    for name, src in sources.items():
        stem = name[:-3]
        if name == "run_tests.py":
            kind = "runner"
        elif name in lists["SUITES"]:
            kind = "suite"
        elif name.startswith("test_"):
            kind = "test, not in the runner"
        elif name in lists["CONSOLE_PASTE"]:
            kind = "console paste"
        else:
            kind = "tool"
        if name in lists["SELFTEST"]:
            selftest = "yes"
        elif "--selftest" in src and kind == "tool":
            selftest = "has the flag, not in the runner"
        else:
            selftest = "–"
        imp = re.compile(r"^\s*(?:import|from)\s+" + re.escape(stem) + r"\b", re.M)
        scripts.append({
            "name": name, "lines": src.count("\n") + (0 if src.endswith("\n") or not src else 1),
            "kind": kind, "selftest": selftest,
            "readme": named(name, readme), "skill": named(name, skill),
            "docs": sum(1 for t in docs.values() if named(name, t)),
            "scripts": sum(1 for other, t in sources.items()
                           if other != name and (named(name, t) or imp.search(t))),
            "net": bool(NET_RE.search(src)), "what": first_doc_line(src),
        })

    classes = {}
    for line in read(rdir / "_INDEX.md").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.split("|")]
        match = re.match(r"`([^`]+)`", cells[1]) if len(cells) > 2 else None
        if match:
            classes[match.group(1)] = cells[2].strip("* ").lower()
    refs = []
    for path in sorted(rdir.glob("*.md")):
        if path.name == "_INDEX.md":
            continue
        text = read(path)
        title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), "(no title)")
        refs.append({
            "name": path.name, "lines": text.count("\n"), "title": title,
            "sections": sum(1 for ln in text.splitlines() if ln.startswith("## ")),
            "class": classes.get(path.name, "NOT LISTED"), "skill": named(path.name, skill),
        })

    version = "unknown"
    try:
        version = json.loads(read(plugin / ".claude-plugin" / "plugin.json")).get("version", "unknown")
    except (ValueError, AttributeError):
        pass

    # A FINDING fails the run. Both kinds are things no other check owns.
    findings = []
    for key in ("SUITES", "SELFTEST", "CONSOLE_PASTE"):
        gone = [n for n in lists[key] if n not in sources]
        if gone:
            findings.append(f"`run_tests.py` {key} names files that do not exist: " + ", ".join(f"`{n}`" for n in gone))
    nowhere = [s["name"] for s in scripts
               if not (s["readme"] or s["skill"] or s["docs"] or s["scripts"]) and s["kind"] == "tool"]
    if nowhere:
        findings.append(f"{len(nowhere)} tools are named in no guide, no reference and no other script: "
                        + ", ".join(f"`{n}`" for n in nowhere))

    # A NOTE is printed and never fails: either a judgement (the scripts guide is hand-written and
    # need not name every script) or a check skill_audit.py already owns (the reference registry).
    notes = []
    missing = [s["name"] for s in scripts if not s["readme"]]
    if missing:
        notes.append(f"{len(missing)} scripts are not named in `scripts/README.md`: " + ", ".join(f"`{n}`" for n in missing))
    ref_names = {r["name"] for r in refs}
    unlisted = [r["name"] for r in refs if r["class"] == "NOT LISTED"]
    if unlisted:
        notes.append(f"{len(unlisted)} references are not listed in `references/_INDEX.md` "
                     "(skill_audit.py fails on this): " + ", ".join(f"`{n}`" for n in unlisted))
    ghost = sorted(n for n in classes if n not in ref_names)
    if ghost:
        notes.append("`references/_INDEX.md` has rows with no file (skill_audit.py fails on this): "
                     + ", ".join(f"`{n}`" for n in ghost))

    # What the written index states. Every one changes only when a script or the runner's lists change.
    counts = [
        ("Python files in `scripts/`", len(scripts)),
        ("Scripts as the test runner counts them (every one but itself)", max(len(scripts) - 1, 0)),
        ("Test suites in the runner", len(lists["SUITES"])),
        ("Selftests in the runner", len(lists["SELFTEST"])),
        ("Console-paste scripts", len(lists["CONSOLE_PASTE"])),
    ]
    # Printed and in --report only: these move with the guides, the references and every edited line.
    per_class = {}
    for r in refs:
        per_class[r["class"]] = per_class.get(r["class"], 0) + 1
    more = [
        ("Scripts with a `--selftest` flag that the runner does not list",
         sum(1 for s in scripts if s["selftest"].startswith("has"))),
        ("Scripts named in `scripts/README.md`", sum(1 for s in scripts if s["readme"])),
        ("Scripts named in `SKILL.md`", sum(1 for s in scripts if s["skill"])),
        ("Reference files (not counting `_INDEX.md`)", len(refs)),
    ]
    more += [(f"References classed {k}", v) for k, v in sorted(per_class.items())]
    more += [
        ("References named in `SKILL.md`", sum(1 for r in refs if r["skill"])),
        ("Lines in all references", sum(r["lines"] for r in refs)),
        ("Lines in all scripts", sum(s["lines"] for s in scripts)),
        ("Agents", len(list((plugin / "agents").glob("*.md")))),
        ("Mode files (not counting `_INDEX.md`)",
         len([p for p in (root / "modes").glob("*.md") if p.name != "_INDEX.md"])),
    ]
    return {"version": version, "scripts": scripts, "refs": refs, "counts": counts, "more": more,
            "findings": findings, "notes": notes}


def _yes(flag: bool) -> str:
    return "yes" if flag else "–"


def render_index(data: dict) -> str:
    """scripts/INDEX.md. Only columns that change when a script changes (see the docstring)."""
    out = ["# Scripts index", "",
           "> **Generated by `gen_index.py` from the files themselves.** Do not edit by hand. After adding, "
           "removing or re-describing a script, run `python3 -B scripts/gen_index.py`. `run_tests.py` fails "
           "while this file is out of date.", "",
           "`README.md` in this folder is the guide: the conventions, and what the main tools are for. This page "
           "is the full list. For the long sheets (lines, where each script is named, the references "
           "check), run `python3 -B scripts/gen_index.py --report`.", "",
           "## Counts", "", "| What | Count |", "|---|---|"]
    out += [f"| {k} | {v:,} |" for k, v in data["counts"]]
    out += ["", "## Every script", "",
            "- **Kind:** tool, suite (a test file the runner runs), console paste (pasted into Resolve's "
            "console), runner.",
            "- **Selftest:** whether the test runner runs this script's own `--selftest`.",
            "- **Network:** it imports a network library (a text search, not proof).", "",
            "| Script | Kind | Selftest | Network | What it does (first line of its docstring) |",
            "|---|---|---|---|---|"]
    for r in data["scripts"]:
        out.append(f"| `{r['name']}` | {r['kind']} | {r['selftest']} | {_yes(r['net'])} | {cell(r['what'])} |")
    return "\n".join(out) + "\n"


def render_report(data: dict) -> str:
    """The long sheets, for a person. Printed, never saved, because they move with every edit."""
    counts = ["| What | Count |", "|---|---|"]
    counts += [f"| {k} | {v:,} |" for k, v in data["counts"] + data["more"]]
    out = [f"# Scripts and references report (plugin v{data['version']})", "", "## Counts", ""] + counts
    out += ["", "## Findings (these fail the run)", ""] + ([f"- {f}" for f in data["findings"]] or ["- None."])
    out += ["", "## Notes (these do not)", ""] + ([f"- {n}" for n in data["notes"]] or ["- None."])
    out += ["", "## Every script", "",
            "| Script | Lines | Kind | Selftest | In the scripts guide | In `SKILL.md` | Other docs | "
            "Other scripts | Network | What it does |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in data["scripts"]:
        out.append(f"| `{r['name']}` | {r['lines']:,} | {r['kind']} | {r['selftest']} | {_yes(r['readme'])} | "
                   f"{_yes(r['skill'])} | {r['docs']} | {r['scripts']} | {_yes(r['net'])} | {cell(r['what'])} |")
    out += ["", "## Every reference", "",
            "`references/_INDEX.md` stays the registry. This sheet adds the measured columns.", "",
            "| File | Lines | `##` sections | Class in `_INDEX.md` | Named in `SKILL.md` | Title |",
            "|---|---|---|---|---|---|"]
    for r in data["refs"]:
        out.append(f"| `{r['name']}` | {r['lines']:,} | {r['sections']} | {r['class']} | {_yes(r['skill'])} | "
                   f"{cell(r['title'], 110)} |")
    return "\n".join(out) + "\n"


def run(root: Path, check: bool = False, report: bool = False) -> int:
    if not (root / "SKILL.md").is_file() or not (root / "scripts").is_dir():
        print(f"gen_index: {root} is not a skill root (no SKILL.md or no scripts/)", file=sys.stderr)
        return 2
    data = scan(root)
    if report:
        print(render_report(data), end="")
        return 1 if data["findings"] else 0
    target, text, stale = root / "scripts" / INDEX, render_index(data), False
    if check:
        stale = read(target) != text
    else:
        try:
            target.write_text(text, encoding="utf-8")
        except OSError as err:
            print(f"gen_index: cannot write {target}: {err}", file=sys.stderr)
            return 2
    print(f"plugin v{data['version']}" + ("" if check else f" · wrote {target}"))
    for key, value in data["counts"] + data["more"]:
        print(f"  {value:>7,}  {key.replace('`', '')}")
    for note in data["notes"]:
        print("NOTE: " + note.replace("`", "")[:400])
    for finding in data["findings"]:
        print("FINDING: " + finding.replace("`", "")[:400])
    if stale:
        print(f"STALE: scripts/{INDEX} does not match the files. Run: python3 -B scripts/gen_index.py")
    return 1 if (data["findings"] or stale) else 0


def selftest() -> int:
    failed = []

    def check(label: str, got, want) -> None:
        if got != want:
            failed.append(f"FAIL {label}: got {got!r}, want {want!r}")

    # run() prints its counts on every call. Kept off the screen here, so a FAIL line is the last
    # thing printed: run_tests.py shows only the tail of a failing selftest.
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        plugin = Path(tmp) / "plugin"
        root = plugin / "skills" / "demo"
        for sub in ("scripts", "references", "modes", "assets"):
            (root / sub).mkdir(parents=True)
        (plugin / ".claude-plugin").mkdir()
        (plugin / ".claude-plugin" / "plugin.json").write_text('{"version": "9.8.7"}')
        (root / "SKILL.md").write_text("Run `scripts/a.py`. Read `references/one.md`.\n")
        sdir = root / "scripts"
        (sdir / "a.py").write_text('"""a.py — does a thing."""\nimport urllib.request\n')
        (sdir / "b_a.py").write_text('"""b_a.py — second."""\nimport sys  # --selftest\n')
        (sdir / "lonely.py").write_text('"""lonely.py — nobody names this."""\n')
        (sdir / "test_x.py").write_text('"""suite."""\n')
        (sdir / "run_tests.py").write_text(
            'SUITES = ["test_x.py", "test_gone.py"]\nSELFTEST = ["a.py"]\nCONSOLE_PASTE = set()\n')
        (sdir / "README.md").write_text("`a.py` and `b_a.py` and `test_x.py`.\n")
        (root / "references" / "_INDEX.md").write_text(
            "| File | Class | Loaded when | Owns |\n|---|---|---|---|\n"
            "| `one.md` | **core** | always | x |\n| `ghost.md` | extended | never | y |\n")
        (root / "references" / "one.md").write_text("# One\n\n## A\n\n## B\n")
        (root / "references" / "two.md").write_text("# Two\n")

        # 1 · the scan reads what is on disk
        data = scan(root)
        by = {s["name"]: s for s in data["scripts"]}
        counts = dict(data["counts"] + data["more"])
        check("scripts", counts["Python files in `scripts/`"], 5)
        check("runner's own count", counts["Scripts as the test runner counts them (every one but itself)"], 4)
        check("suites", counts["Test suites in the runner"], 2)
        check("selftests", counts["Selftests in the runner"], 1)
        check("a.py purpose", by["a.py"]["what"], "does a thing.")
        check("a.py network", by["a.py"]["net"], True)
        check("a.py is not matched inside b_a.py", by["a.py"]["readme"] and by["b_a.py"]["readme"], True)
        check("named() rejects a longer name", named("a.py", "see b_a.py"), False)
        check("b_a.py selftest flag", by["b_a.py"]["selftest"], "has the flag, not in the runner")
        check("the runner is not flagged for its own flag", by["run_tests.py"]["selftest"], "–")
        check("references", counts["Reference files (not counting `_INDEX.md`)"], 2)
        check("class", {r["name"]: r["class"] for r in data["refs"]}, {"one.md": "core", "two.md": "NOT LISTED"})
        check("sections", data["refs"][0]["sections"], 2)

        # 2 · what fails the run, and what is only a note
        found, noted = " ".join(data["findings"]), " ".join(data["notes"])
        check("a runner entry with no file is a finding", "test_gone.py" in found, True)
        check("a tool named nowhere is a finding", "lonely.py" in found, True)
        check("a script outside the guide is a note, not a finding",
              ("run_tests.py" in noted, "README" in found), (True, False))
        check("the reference registry is a note, not a finding",
              ("two.md" in noted and "ghost.md" in noted, "two.md" in found or "ghost.md" in found), (True, False))
        check("findings make the run exit 1", run(root), 1)
        check("--report writes nothing and exits 1 on a finding", run(root, report=True), 1)

        # 3 · a clean skill: write, then --check, and what does and does not make the index stale
        (sdir / "run_tests.py").write_text('SUITES = ["test_x.py"]\nSELFTEST = ["a.py"]\nCONSOLE_PASTE = set()\n')
        (sdir / "README.md").write_text("`a.py`, `b_a.py`, `test_x.py` and `lonely.py`.\n")
        index = sdir / INDEX
        check("a clean skill writes and exits 0", run(root), 0)
        text = read(index)
        check("the index lists every script", all(f"`{n}`" in text for n in by), True)
        check("the index carries no plugin version", "9.8.7" in text, False)
        check("--check passes straight after a write", run(root, check=True), 0)
        check("same input, same output", render_index(scan(root)), text)
        (plugin / ".claude-plugin" / "plugin.json").write_text('{"version": "9.9.0"}')
        (sdir / "README.md").write_text("`a.py`, `b_a.py`, `test_x.py`, `lonely.py`. A new paragraph.\n")
        (root / "references" / "two.md").write_text("# Two\n\nmore lines\n")
        check("a version bump, a guide edit and a reference edit leave it current", run(root, check=True), 0)
        (sdir / "new_tool.py").write_text('"""new_tool.py — added after the index."""\n# see lonely.py\n')
        (sdir / "README.md").write_text("`a.py`, `b_a.py`, `test_x.py`, `lonely.py`, `new_tool.py`.\n")
        check("a new script makes it stale", run(root, check=True), 1)
        check("--check wrote nothing", read(index), text)
        check("writing again clears it", (run(root), run(root, check=True)), (0, 0))
        (sdir / "a.py").write_text('"""a.py — does a different thing."""\nimport urllib.request\n')
        check("a changed docstring makes it stale", run(root, check=True), 1)

        # 4 · usage
        check("not a skill root", run(Path(tmp) / "nope"), 2)
    for line in failed:
        print(line)
    print("selftest: FAIL" if failed else "selftest: PASS")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent),
                    help="the skill root (default: the folder above this script's folder)")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if scripts/INDEX.md is stale")
    ap.add_argument("--report", action="store_true", help="print the long sheets; write nothing")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return run(Path(a.root), check=a.check, report=a.report)


if __name__ == "__main__":
    sys.exit(main())
