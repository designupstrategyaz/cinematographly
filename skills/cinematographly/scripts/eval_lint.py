#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""eval_lint.py — validate the `evals/` suite without running it.

  eval_lint.py [<evals-dir>]        default: the plugin root's evals/
  eval_lint.py --selftest           offline checks on synthetic fixtures

Run: `python3 scripts/eval_lint.py` (stdlib + pyyaml; no network, no credits, no early access)

WHY
`claude plugin eval` is gated on early access, costs model credits per run, and takes minutes. A
malformed case — a grader type that does not exist, a `plugins:` path that resolves to nothing, a
scaffold script that is not executable — fails at the far end of all that. This reads the suite
statically and says so in a second, so `run_tests.py` catches a broken eval case on every commit
whether or not anyone can run the real thing today.

⛔ WHAT THIS CANNOT TELL YOU
It checks that a case is well FORMED, never that it is well AIMED. A grader whose rubric is so
loose that everything passes is structurally perfect and worthless — and a suite of those is worse
than no suite, because it reports a number. The house rule from `SKILL.md` §4 applies to graders
too: ask what it would take to pass this check without doing the work. Two mechanical proxies for
that judgement ARE enforced here, because they catch the common version of it:
  - a case graded ONLY by LLM judges is warned about (an llm judge is the one grader that can be
    talked into a pass; pair it with a tool_used / file_exists / regex that cannot be)
  - a judge rubric with no FAIL condition is warned about (a rubric that only describes success
    tells the judge nothing about what to reject)
"""
from __future__ import annotations

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:                                      # pragma: no cover
    yaml = None

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))

# The grader types the harness understands. A typo here is a grader that silently never runs.
GRADER_TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
REGEX_MATCH = {"contains", "not_contains"}               # plus `count:N`
GRADER_TARGETS = {"last_message", "trace", "files", "mock_calls"}
# Anything write-capable or networked has to be granted explicitly; a case that expects the agent
# to run scripts and never allows Bash grades a hand tied behind its back.
KNOWN_TOOLS = {"Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebSearch", "WebFetch",
               "NotebookEdit", "Task", "TodoWrite", "AskUserQuestion"}
FAIL_WORDS = ("fail", "reject", "must not", "should not", "never")


def split_front(text: str) -> tuple:
    """`---` fenced YAML frontmatter + body. Returns (dict, body, error|'')."""
    if not text.startswith("---"):
        return {}, text, "no `---` frontmatter fence"
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text, "frontmatter is not closed with `---`"
    head, body = text[3:end], text[end + 4:]
    if yaml is None:
        return {}, body, "pyyaml is not installed, cannot parse frontmatter"
    try:
        fm = yaml.safe_load(head) or {}
    except yaml.YAMLError as e:
        return {}, body, f"frontmatter is not valid YAML: {str(e).splitlines()[0]}"
    if not isinstance(fm, dict):
        return {}, body, "frontmatter is not a mapping"
    return fm, body, ""


def lint_case(case_dir: str) -> tuple:
    """(fails, warns) for one eval case directory."""
    F, W = [], []
    name = os.path.basename(case_dir)

    def f(m):
        F.append(f"{name}: {m}")

    def w(m):
        W.append(f"{name}: {m}")

    pfile = os.path.join(case_dir, "prompt.md")
    if not os.path.isfile(pfile):
        f("no prompt.md — a case is a prompt plus its graders")
        return F, W
    fm, body, err = split_front(open(pfile, encoding="utf-8").read())
    if err:
        f(f"prompt.md {err}")
        return F, W

    if not str(fm.get("name") or "").strip():
        f("prompt.md frontmatter has no `name:`")
    elif fm["name"] != name:
        w(f"`name: {fm['name']}` does not match the folder — the report is keyed by folder")
    if not body.strip():
        f("prompt.md has no body — the case would send an empty prompt")

    plugins = fm.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        f("no `plugins:` list — the case would run with NO plugin loaded and grade a bare model")
    else:
        for rel in plugins:
            p = os.path.normpath(os.path.join(case_dir, str(rel)))
            if not os.path.isfile(os.path.join(p, ".claude-plugin", "plugin.json")):
                f(f"`plugins: {rel}` → {p} has no .claude-plugin/plugin.json")

    tools = fm.get("allowed_tools")
    if tools is not None and not isinstance(tools, list):
        f("`allowed_tools:` is not a list")
    elif isinstance(tools, list):
        for t in tools:
            if t not in KNOWN_TOOLS and not str(t).startswith("mcp__"):
                w(f"`allowed_tools` lists {t!r}, which is not a tool this skill's cases use")

    for key, lo, hi in (("runs", 1, 20), ("max_turns", 1, 200), ("timeout_seconds", 30, 3600)):
        v = fm.get(key)
        if v is not None and (not isinstance(v, int) or not lo <= v <= hi):
            f(f"`{key}: {v!r}` is not an int in {lo}..{hi}")

    cy = os.path.join(case_dir, "case.yaml")
    if os.path.isfile(cy) and yaml is not None:
        try:
            doc = yaml.safe_load(open(cy, encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            doc = None
            f(f"case.yaml is not valid YAML: {str(e).splitlines()[0]}")
        if isinstance(doc, dict):
            scaf = (doc.get("context") or {}).get("scaffold_script")
            if scaf:
                sp = os.path.normpath(os.path.join(case_dir, str(scaf)))
                if not os.path.isfile(sp):
                    f(f"case.yaml scaffold_script {scaf} → {sp} does not exist")
                elif not os.access(sp, os.X_OK):
                    f(f"scaffold_script {scaf} is not executable (chmod +x)")

    gdir = os.path.join(case_dir, "graders")
    graders = sorted(g for g in os.listdir(gdir) if g.endswith(".md")) if os.path.isdir(gdir) else []
    if not graders:
        f("no graders/ — an ungraded case runs the model and reports nothing")
        return F, W

    kinds = []
    for g in graders:
        gp = os.path.join(gdir, g)
        gfm, gbody, gerr = split_front(open(gp, encoding="utf-8").read())
        gn = f"graders/{g}"
        if gerr:
            f(f"{gn} {gerr}")
            continue
        t = gfm.get("type")
        if t not in GRADER_TYPES:
            f(f"{gn} `type: {t!r}` is not one of {', '.join(sorted(GRADER_TYPES))}")
            continue
        kinds.append(t)
        tgt = gfm.get("target")
        if isinstance(tgt, str) and tgt not in GRADER_TARGETS:
            f(f"{gn} `target: {tgt}` is not one of {', '.join(sorted(GRADER_TARGETS))}")
        if t == "regex":
            pat = gfm.get("pattern")
            if not pat:
                f(f"{gn} regex grader with no `pattern:`")
            else:
                try:
                    re.compile(str(pat))
                except re.error as e:
                    f(f"{gn} `pattern:` does not compile: {e}")
            m = gfm.get("match")
            if m is not None and str(m) not in REGEX_MATCH and not str(m).startswith("count:"):
                f(f"{gn} `match: {m}` is not contains / not_contains / count:N")
            # ⛔ `min:`/`max:` belong to tool_used. On a regex grader they are silently ignored and
            # `match:` falls back to `contains` — so an author writing `min: 0 / max: 0` to mean
            # "this string must NOT appear" gets a grader that fails every correct answer. Found by
            # running the suite: `no-three-second-rule` scored 0 with `matches: 0`.
            for k in ("min", "max"):
                if gfm.get(k) is not None:
                    f(f"{gn} regex grader carries `{k}:` — that is tool_used's schema and is "
                      f"ignored here, leaving `match:` at its `contains` default. To assert a "
                      f"string is ABSENT write `match: not_contains`")
        elif t == "tool_used":
            if not gfm.get("tool"):
                f(f"{gn} tool_used grader with no `tool:`")
            for k in ("min", "max"):
                if gfm.get(k) is not None and not isinstance(gfm[k], int):
                    f(f"{gn} `{k}:` is not an integer")
            if isinstance(gfm.get("min"), int) and isinstance(gfm.get("max"), int) \
                    and gfm["min"] > gfm["max"]:
                f(f"{gn} min {gfm['min']} > max {gfm['max']} — nothing can satisfy it")
            im = gfm.get("input_match")
            if im:
                try:
                    re.compile(str(im))
                except re.error as e:
                    f(f"{gn} `input_match:` does not compile: {e}")
        elif t == "tool_order":
            if not (gfm.get("before") and gfm.get("after")):
                f(f"{gn} tool_order needs both `before:` and `after:`")
        elif t == "file_exists":
            if not gfm.get("path"):
                f(f"{gn} file_exists grader with no `path:`")
        elif t == "llm":
            crit = str(gfm.get("criteria") or "").strip()
            if not crit:
                f(f"{gn} llm grader with no `criteria:`")
            else:
                if len(crit.split()) < 12:
                    w(f"{gn} rubric is {len(crit.split())} words — too thin to judge consistently")
                if not any(k in crit.lower() for k in FAIL_WORDS):
                    w(f"{gn} rubric never says what FAILS — a judge told only what success looks "
                      f"like will find it")
        elif t == "baseline":
            bf = gfm.get("baseline_file")
            if bf and not os.path.isfile(os.path.normpath(os.path.join(case_dir, str(bf)))):
                f(f"{gn} baseline_file {bf} does not exist")

    if kinds and set(kinds) == {"llm"}:
        w("graded only by LLM judges — pair at least one with a tool_used / file_exists / regex "
          "that cannot be talked into a pass (SKILL.md §4: what would it take to pass this "
          "without doing the work?)")
    return F, W


def lint_suite(root: str) -> tuple:
    if not os.path.isdir(root):
        return [f"{root} is not a directory"], [], 0
    cases = sorted(d for d in os.listdir(root)
                   if os.path.isdir(os.path.join(root, d))
                   and not d.startswith((".", "_"))
                   and d != "fixture"
                   and d != "results")
    F, W = [], []
    for c in cases:
        cf, cw = lint_case(os.path.join(root, c))
        F += cf
        W += cw
    if not cases:
        F.append(f"no eval cases in {root}")
    return F, W, len(cases)


# -------------------------------------------------------------------------------------- selftest
def selftest() -> int:
    import json  # noqa: F401
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and bool(cond)

    with tempfile.TemporaryDirectory() as td:
        plug = os.path.join(td, "plug")
        os.makedirs(os.path.join(plug, ".claude-plugin"))
        open(os.path.join(plug, ".claude-plugin", "plugin.json"), "w").write('{"name":"x"}')
        ev = os.path.join(plug, "evals")

        def case(name, prompt_fm, graders, scaffold=None):
            d = os.path.join(ev, name)
            os.makedirs(os.path.join(d, "graders"), exist_ok=True)
            open(os.path.join(d, "prompt.md"), "w").write(f"---\n{prompt_fm}\n---\nthe brief\n")
            for gn, g in graders.items():
                open(os.path.join(d, "graders", gn + ".md"), "w").write(f"---\n{g}\n---\nwhy\n")
            if scaffold is not None:
                open(os.path.join(d, "case.yaml"), "w").write(
                    'schema_version: "1.1"\nname: %s\ncontext:\n  scaffold_script: %s\n'
                    % (name, scaffold))
            return d

        GOOD_FM = 'name: good\nplugins: ["../.."]\nruns: 3\nallowed_tools: [Bash, Read]'
        GOOD_G = {"ran": "type: tool_used\ntool: Bash\ninput_match: develop\\.py\nmin: 1",
                  "judged": ("type: llm\ncriteria: |\n  Did the agent hold the process?\n"
                             "  FAIL if it wrote a script before development.\n")}
        case("good", GOOD_FM, GOOD_G)
        F, W, n = lint_suite(ev)
        check("a well-formed case passes clean", not F and n == 1)

        case("no-plugins", 'name: no-plugins\nruns: 3', GOOD_G)
        F, _, _ = lint_suite(ev)
        check("a case with no `plugins:` FAILS (it would grade a bare model)",
              any("no `plugins:` list" in x for x in F))
        os.rename(os.path.join(ev, "no-plugins"), os.path.join(td, "away1"))

        case("bad-plugin-path", 'name: bad-plugin-path\nplugins: ["../nope"]', GOOD_G)
        F, _, _ = lint_suite(ev)
        check("a `plugins:` path with no plugin.json FAILS",
              any("no .claude-plugin/plugin.json" in x for x in F))
        os.rename(os.path.join(ev, "bad-plugin-path"), os.path.join(td, "away2"))

        case("bad-type", GOOD_FM.replace("good", "bad-type"),
             {"g": "type: vibes\ncriteria: x"})
        F, _, _ = lint_suite(ev)
        check("an unknown grader type FAILS", any("is not one of" in x for x in F))
        os.rename(os.path.join(ev, "bad-type"), os.path.join(td, "away3"))

        case("bad-regex", GOOD_FM.replace("good", "bad-regex"),
             {"g": "type: regex\npattern: '([unclosed'\nmatch: contains"})
        F, _, _ = lint_suite(ev)
        check("a regex that does not compile FAILS", any("does not compile" in x for x in F))
        os.rename(os.path.join(ev, "bad-regex"), os.path.join(td, "away-badregex"))

        # the min/max confusion: silently graded as `contains`, so it fails every correct answer
        case("regex-minmax", GOOD_FM.replace("good", "regex-minmax"),
             {"g": "type: regex\npattern: 'three-second rule'\nmin: 0\nmax: 0"})
        F, _, _ = lint_suite(ev)
        check("a regex grader carrying tool_used's min/max FAILS",
              any("that is tool_used's schema" in x for x in F))
        os.rename(os.path.join(ev, "regex-minmax"), os.path.join(td, "away-minmax"))
        case("bad-regex", GOOD_FM.replace("good", "bad-regex"),
             {"g": "type: regex\npattern: '([unclosed'\nmatch: contains"})
        os.rename(os.path.join(ev, "bad-regex"), os.path.join(td, "away4"))

        case("impossible", GOOD_FM.replace("good", "impossible"),
             {"g": "type: tool_used\ntool: Bash\nmin: 2\nmax: 1"})
        F, _, _ = lint_suite(ev)
        check("min > max FAILS — nothing can satisfy it", any("nothing can satisfy" in x for x in F))
        os.rename(os.path.join(ev, "impossible"), os.path.join(td, "away5"))

        case("judge-only", GOOD_FM.replace("good", "judge-only"),
             {"j": ("type: llm\ncriteria: |\n  Did the agent hold the whole process end to end?\n"
                    "  FAIL if it skipped development.\n")})
        _, W, _ = lint_suite(ev)
        check("a case graded only by LLM judges WARNS",
              any("only by LLM judges" in x for x in W))
        os.rename(os.path.join(ev, "judge-only"), os.path.join(td, "away6"))

        case("no-fail-clause", GOOD_FM.replace("good", "no-fail-clause"),
             {"ran": "type: tool_used\ntool: Bash\nmin: 1",
              "j": ("type: llm\ncriteria: |\n  Check that the agent produced a nice script with a\n"
                    "  clear hook and a good structure throughout the piece.\n")})
        _, W, _ = lint_suite(ev)
        check("a judge rubric with no FAIL condition WARNS",
              any("never says what FAILS" in x for x in W))
        os.rename(os.path.join(ev, "no-fail-clause"), os.path.join(td, "away7"))

        d = case("bad-scaffold", GOOD_FM.replace("good", "bad-scaffold"), GOOD_G,
                 scaffold="../fixture/nope.sh")
        F, _, _ = lint_suite(ev)
        check("a missing scaffold script FAILS", any("does not exist" in x for x in F))
        os.makedirs(os.path.join(ev, "fixture"), exist_ok=True)
        sp = os.path.join(ev, "fixture", "nope.sh")
        open(sp, "w").write("#!/bin/sh\n")
        F, _, _ = lint_suite(ev)
        check("a scaffold script that is not executable FAILS",
              any("not executable" in x for x in F))
        os.chmod(sp, 0o755)
        F, _, _ = lint_suite(ev)
        check("an executable scaffold passes", not any("scaffold" in x for x in F))
        os.rename(d, os.path.join(td, "away8"))

        case("no-graders", GOOD_FM.replace("good", "no-graders"), {})
        F, _, _ = lint_suite(ev)
        check("a case with no graders FAILS", any("no graders/" in x for x in F))

    # And the REAL suite, when this checkout has one — a selftest that only ever sees synthetic
    # fixtures is a selftest of the fixtures.
    real = os.path.join(PLUGIN_ROOT, "evals")
    if os.path.isdir(real):
        F, W, n = lint_suite(real)
        for x in F:
            print(f"  [FAIL] evals/: {x}")
        check(f"the shipped suite is well formed ({n} case(s))", not F)
        for x in W:
            print(f"         warn: {x}")

    print("-" * 60)
    print("selftest OK — malformed frontmatter, a missing/bad `plugins:` path, unknown grader "
          "types, an uncompilable regex, a regex grader carrying tool_used's min/max, an "
          "unsatisfiable min/max, a missing or non-executable "
          "scaffold and an ungraded case all fail; judge-only suites and rubrics with no FAIL "
          "clause warn; and the shipped suite lints clean" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=os.path.join(PLUGIN_ROOT, "evals"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if yaml is None:
        print("error: pyyaml is not installed (pip install pyyaml)", file=sys.stderr)
        return 2
    F, W, n = lint_suite(a.path)
    print(f"EVAL SUITE — {os.path.relpath(a.path)}  ({n} case(s))")
    for x in F:
        print(f"  ⛔ {x}")
    for x in W:
        print(f"  ·  {x}")
    if not F and not W:
        print("  clean — every case is well formed. Whether it is well AIMED is a read, not a lint.")
    print(f"\n  {len(F)} failure(s) · {len(W)} warning(s)")
    if not F:
        print("  Run them for real:  claude plugin eval .   (early access; costs credits)")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
