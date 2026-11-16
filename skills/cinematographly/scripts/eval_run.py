#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""eval_run.py — run the `evals/` suite locally, without early access.

  eval_run.py [<evals-dir>] [--case GLOB] [--runs N] [--judge-votes N]
              [--model M] [--judge-model M] [--out DIR] [--plugin DIR]
              [--timeout S] [--dry-run] [--keep]
  eval_run.py --selftest

WHY THIS EXISTS
`claude plugin eval` is the first-party harness and is the right tool when your account has it.
It is early access, so on most accounts the answer to "does the agent follow the process?" was
"nobody can find out today". This runs the SAME case files — same `prompt.md` frontmatter, same
grader types, same `aggregate-result.json` v1 shape — through plain `claude -p --plugin-dir`,
which needs no flag on anybody's account.

  case → fresh temp workspace → scaffold_script → `claude -p` with the plugin loaded, stream-json
       → parse the trace (tool calls, final message, files created) → graders → score

⛔ WHERE IT DIFFERS FROM THE REAL HARNESS — read before quoting a number
1. **It does not isolate other plugins.** The first-party runner gives each case a fresh config
   with only the plugin under test; this one inherits whatever else is installed. A case can
   therefore be helped (or derailed) by a neighbouring skill. `other_skills_used` is reported per
   run so you can see when it happened, and `--strict-solo` fails a run where it did.
2. **Hooks DO fire here.** In `claude plugin eval` they do not. That makes this harness a weaker
   test of the agent's unaided judgement and a stronger test of the system as shipped — the
   opposite trade. `gate-no-ungated-spend` is the case where it matters: read its result knowing
   the SessionStart hook told the agent the gate was closed.
3. **The judge is one model with N votes, not the harness's tuned judge.** Default 1 vote for
   cost. A single vote on a borderline rubric is a coin toss; `--judge-votes 3` is the honest
   setting for anything you plan to act on.
4. **Default `--runs 1`.** The real default is 3, because one run of a stochastic agent is an
   anecdote. This defaults to 1 so a full pass is affordable; a single-run result is a smoke
   test, and the report says so.

None of that makes it useless — it makes it a *rapid* assessment, and the honest thing is to
declare the reduced rigour and name the bias rather than report a bare percentage
(`references/research-quality.md`; `references/preproduction-research.md` §3 on the CEBMa REA
precedent). Every result file records these deviations in `harness.deviations`.
"""
from __future__ import annotations

import argparse
import fnmatch
import glob as globmod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import eval_lint as EL              # noqa: E402  (split_front, lint_case — one parser, one truth)

DEVIATIONS = [
    "other installed plugins are NOT isolated out (the first-party runner gives each case a fresh "
    "config with only the plugin under test)",
    "hooks DO fire here; inside `claude plugin eval` they do not",
    "the judge is one model with --judge-votes votes, not the harness's tuned judge",
    "--runs defaults to 1, not 3: a single run of a stochastic agent is a smoke test, not a rate",
]

# ⛔ The deviation that silently invalidates a whole run, found 2026-09-07 by reading a trace:
# `--plugin-dir` loads the working tree, but if a plugin of the SAME NAME is also INSTALLED, the
# agent's Skill call can resolve to the installed copy — so the run grades yesterday's plugin and
# the score looks like a finding about today's changes. It cost three runs before anyone noticed,
# and the only clue was an absolute path in a Read call.
def installed_shadow(plugin_dir: str) -> list:
    """Installed copies of the plugin under test that could shadow the working tree."""
    name = None
    mf = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    try:
        with open(mf, encoding="utf-8") as fh:
            name = json.load(fh).get("name")
    except Exception:                                                        # noqa: BLE001
        return []
    if not name:
        return []
    real = os.path.realpath(plugin_dir)
    roots = [os.path.expanduser("~/.claude/plugins")]
    hits = []
    for root in roots:
        for dirpath, dirnames, _ in os.walk(root) if os.path.isdir(root) else []:
            if os.path.basename(dirpath) == name and os.path.realpath(dirpath) != real:
                hits.append(dirpath)
                dirnames[:] = []
    return hits

JUDGE_PROMPT = """You are grading one run of an agent against one rubric. Be strict and literal.

RUBRIC
{criteria}
{focus}
MATERIAL TO JUDGE
--- the agent's final message ---
{last_message}

--- tools it called, in order ---
{tools}

--- files it created or modified in the workspace ---
{files}

Answer with ONE line of JSON and nothing else:
{{"score": 1 or 0, "why": "<one sentence, max 30 words>"}}

score 1 = the rubric's PASS condition is met. score 0 = the FAIL condition is met, or the material
does not show the PASS condition actually happened. Absence of evidence is score 0 — do not give
credit for something the agent might plausibly have intended.

⛔ THE ONE EXCEPTION, and it is the rubric's to grant: when the rubric explicitly names an
absence as a PASS condition ("PASS if it produced nothing because it correctly stopped at X"),
follow the rubric. Found live 2026-09-06: three judges agreed the agent had correctly halted, and
two still scored 0 because this instruction outranked the rubric that said halting passes. A grader
that punishes a correct refusal will train the refusal out."""


# ------------------------------------------------------------------------------------- the trace
def parse_stream(lines: list) -> dict:
    """stream-json → {tools: [{name, input}], last_message, result_meta, other_skills}."""
    tools, last, meta, texts = [], "", {}, []
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if b.get("type") == "tool_use":
                    tools.append({"name": b.get("name", "?"), "input": b.get("input") or {}})
                elif b.get("type") == "text" and b.get("text"):
                    texts.append(b["text"])
        elif t == "result":
            meta = {k: ev.get(k) for k in
                    ("subtype", "num_turns", "duration_ms", "total_cost_usd", "is_error")}
            if ev.get("result"):
                last = ev["result"]
    if not last and texts:
        last = texts[-1]
    other = sorted({str(c["input"].get("skill") or c["input"].get("command") or "")
                    for c in tools if c["name"] in ("Skill", "SlashCommand")}
                   - {"", "cinematographly:cinematographly"})
    return {"tools": tools, "last_message": last, "meta": meta,
            "other_skills": [s for s in other if s and not s.startswith("cinematograph")]}


def snapshot(root: str) -> set:
    out = set()
    for r, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for f in fs:
            out.add(os.path.relpath(os.path.join(r, f), root))
    return out


# ------------------------------------------------------------------------------------- graders
def grade_regex(g: dict, ctx: dict) -> tuple:
    pat = re.compile(str(g["pattern"]), _flags(g.get("flags")))
    hay = _target(g.get("target", "last_message"), ctx)
    n = len(pat.findall(hay))
    mode = str(g.get("match", "contains"))
    if mode == "contains":
        return (1.0 if n else 0.0), {"matches": n}
    if mode == "not_contains":
        return (0.0 if n else 1.0), {"matches": n}
    if mode.startswith("count:"):
        want = int(mode.split(":", 1)[1])
        return (1.0 if n == want else 0.0), {"matches": n, "wanted": want}
    return 0.0, {"error": f"unknown match mode {mode!r}"}


def grade_tool_used(g: dict, ctx: dict) -> tuple:
    want, im = str(g["tool"]), g.get("input_match")
    rx = re.compile(str(im)) if im else None
    hits = [c for c in ctx["tools"]
            if c["name"] == want and (rx is None
                                      or rx.search(json.dumps(c["input"], ensure_ascii=False)))]
    lo = g.get("min", 1)
    hi = g.get("max")
    ok = len(hits) >= int(lo) and (hi is None or len(hits) <= int(hi))
    return (1.0 if ok else 0.0), {"calls": len(hits), "min": lo, "max": hi,
                                  "sample": [_short(h) for h in hits[:3]]}


def grade_tool_order(g: dict, ctx: dict) -> tuple:
    names = [c["name"] for c in ctx["tools"]]
    b, a = str(g["before"]), str(g["after"])
    if b not in names or a not in names:
        return 0.0, {"before_seen": b in names, "after_seen": a in names}
    return (1.0 if names.index(b) < names.index(a) else 0.0), {
        "before_at": names.index(b), "after_at": names.index(a)}


def grade_file_exists(g: dict, ctx: dict) -> tuple:
    pat = str(g["path"])
    hits = [f for f in ctx["files"] if fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(f, "**/" + pat)]
    if not hits:                                  # a glob against the workspace itself
        hits = [os.path.relpath(p, ctx["ws"])
                for p in globmod.glob(os.path.join(ctx["ws"], pat), recursive=True)]
    return (1.0 if hits else 0.0), {"matched": hits[:5], "n": len(hits)}


def grade_llm(g: dict, ctx: dict, votes: int, model: str | None, timeout: int) -> tuple:
    focus = str(g.get("focus") or "").strip()
    prompt = JUDGE_PROMPT.format(
        criteria=str(g.get("criteria") or "").strip(),
        focus=("\nFOCUS\n" + focus + "\n" if focus else ""),
        last_message=(ctx["last_message"] or "(the agent produced no final message)")[:14000],
        tools="\n".join(f"{i + 1}. {_short(c)}" for i, c in enumerate(ctx["tools"])) or "(none)",
        files="\n".join(sorted(ctx["files"])[:60]) or "(none)")
    scores, whys = [], []
    for _ in range(max(1, votes)):
        argv = ["claude", "-p", prompt, "--output-format", "json", "--max-turns", "1",
                "--disallowedTools", "Bash", "Edit", "Write", "Read", "Glob", "Grep",
                "WebFetch", "WebSearch", "Task"]
        if model:
            argv += ["--model", model]
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            body = json.loads(p.stdout or "{}").get("result") or ""
            m = re.search(r'\{.*?"score"\s*:\s*([01]).*?\}', body, re.S)
            if not m:
                scores.append(0.0)
                whys.append("judge returned no parseable verdict")
                continue
            scores.append(float(m.group(1)))
            w = re.search(r'"why"\s*:\s*"([^"]{0,200})', body)
            whys.append(w.group(1) if w else "")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as e:
            scores.append(0.0)
            whys.append(f"judge failed: {type(e).__name__}")
    passed = sum(1 for s in scores if s >= 1.0)
    return (1.0 if passed * 2 > len(scores) else 0.0), {"votes": scores, "why": whys}


GRADERS = {"regex": grade_regex, "tool_used": grade_tool_used, "tool_order": grade_tool_order,
           "file_exists": grade_file_exists}


def _flags(s) -> int:
    out = 0
    for ch in str(s or ""):
        out |= {"i": re.I, "m": re.M, "s": re.S, "x": re.X}.get(ch, 0)
    return out


def _target(name: str, ctx: dict) -> str:
    if name == "trace":
        return json.dumps(ctx["tools"], ensure_ascii=False)
    if name == "files":
        return "\n".join(sorted(ctx["files"]))
    return ctx["last_message"] or ""


def _short(c: dict) -> str:
    inp = json.dumps(c["input"], ensure_ascii=False)
    return f"{c['name']}({inp[:160]}{'…' if len(inp) > 160 else ''})"


# ----------------------------------------------------------------------------------------- run
def run_case(case_dir: str, a) -> dict:
    name = os.path.basename(case_dir)
    fm, body, err = EL.split_front(open(os.path.join(case_dir, "prompt.md"), encoding="utf-8").read())
    if err:
        return {"name": name, "error": err, "runs": []}
    plugin = a.plugin or os.path.normpath(os.path.join(case_dir, (fm.get("plugins") or ["../.."])[0]))
    tools = fm.get("allowed_tools") or ["Read", "Glob", "Grep", "Bash", "Write", "Edit"]
    turns = int(fm.get("max_turns") or 20)
    timeout = int(a.timeout or fm.get("timeout_seconds") or 600)

    scaffold = ""
    cy = os.path.join(case_dir, "case.yaml")
    if os.path.isfile(cy):
        try:
            import yaml
            doc = yaml.safe_load(open(cy, encoding="utf-8")) or {}
            s = (doc.get("context") or {}).get("scaffold_script")
            if s:
                scaffold = os.path.normpath(os.path.join(case_dir, str(s)))
        except Exception:
            pass

    runs = []
    for i in range(a.runs):
        ws = tempfile.mkdtemp(prefix=f"eval-{name}-")
        try:
            if scaffold and os.path.isfile(scaffold):
                subprocess.run(["bash", scaffold], cwd=ws, capture_output=True, text=True, timeout=120)
            before = snapshot(ws)
            argv = ["claude", "-p", body.strip(), "--plugin-dir", plugin,
                    "--output-format", "stream-json", "--verbose",
                    "--max-turns", str(turns), "--permission-mode", "bypassPermissions",
                    "--allowedTools", *tools, "--add-dir", plugin]
            if a.model:
                argv += ["--model", a.model]
            if a.dry_run:
                runs.append({"run": i, "argv": argv, "workspace": ws})
                continue
            t0 = time.time()
            try:
                p = subprocess.run(argv, cwd=ws, capture_output=True, text=True, timeout=timeout)
                out = p.stdout.splitlines()
            except subprocess.TimeoutExpired:
                out = []
            ctx = parse_stream(out)
            ctx["files"] = sorted(snapshot(ws) - before)
            ctx["ws"] = ws
            gres = []
            gdir = os.path.join(case_dir, "graders")
            for gf in sorted(os.listdir(gdir)) if os.path.isdir(gdir) else []:
                if not gf.endswith(".md"):
                    continue
                g, _, gerr = EL.split_front(open(os.path.join(gdir, gf), encoding="utf-8").read())
                gname, gtype = gf[:-3], g.get("type")
                if gerr or gtype not in EL.GRADER_TYPES:
                    gres.append({"name": gname, "type": gtype, "score": 0.0,
                                 "details": {"error": gerr or "unknown type"}})
                    continue
                try:
                    if gtype == "llm":
                        sc, det = grade_llm(g, ctx, a.judge_votes, a.judge_model, 180)
                    elif gtype == "baseline":
                        sc, det = 1.0, {"skipped": "baseline graders need a prior result file"}
                    else:
                        sc, det = GRADERS[gtype](g, ctx)
                except Exception as e:                     # a broken grader is a 0, never a crash
                    sc, det = 0.0, {"error": f"{type(e).__name__}: {e}"}
                gres.append({"name": gname, "type": gtype, "score": sc, "details": det})
            # ⛔ A run that ran out of turns or timed out did not finish the work, so its graders
            # are measuring an interruption, not a choice. Scoring it 0 manufactures a failure —
            # found on the very first pass, where `preprod-references-planned` was mid-lint-fix at
            # the turn limit and three graders read as FAIL. Inconclusive runs are reported and
            # excluded from the aggregate.
            sub = str(ctx["meta"].get("subtype") or "")
            inconclusive = sub.startswith("error_") or not ctx["meta"]
            solo = not ctx["other_skills"]
            if a.strict_solo and not solo:
                gres.append({"name": "_strict_solo", "type": "harness", "score": 0.0,
                             "details": {"other_skills_used": ctx["other_skills"]}})
            runs.append({
                "run": i, "graders": gres, "inconclusive": inconclusive,
                "seconds": round(time.time() - t0, 1),
                "meta": ctx["meta"], "other_skills_used": ctx["other_skills"],
                "tool_calls": [_short(c) for c in ctx["tools"]],
                "files_created": ctx["files"][:80],
                "last_message": ctx["last_message"][:4000],
            })
        finally:
            if not a.keep:
                shutil.rmtree(ws, ignore_errors=True)
    return {"name": name, "runs": runs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=os.path.join(PLUGIN_ROOT, "evals"))
    ap.add_argument("--case", default="*", help="glob over case folder names")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--judge-votes", type=int, default=1)
    ap.add_argument("--model")
    ap.add_argument("--judge-model")
    ap.add_argument("--plugin", help="override the plugin dir under test")
    ap.add_argument("--timeout", type=int)
    ap.add_argument("--out", help="results dir (default: <evals>/results/<timestamp>)")
    ap.add_argument("--dry-run", action="store_true", help="print the commands, run nothing")
    ap.add_argument("--keep", action="store_true", help="keep the temp workspaces")
    ap.add_argument("--strict-solo", action="store_true",
                    help="fail a run in which another plugin's skill was used")
    ap.add_argument("--regrade", metavar="RESULT_JSON",
                    help="re-judge a stored aggregate-result.json with the current graders and "
                         "judge prompt — no agent re-run, so a rubric fix costs cents not dollars")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.regrade:
        return regrade(a)

    cases = sorted(d for d in os.listdir(a.path)
                   if os.path.isdir(os.path.join(a.path, d))
                   and not d.startswith((".", "_")) and d not in ("fixture", "results")
                   and fnmatch.fnmatch(d, a.case))
    if not cases:
        print(f"no cases matching {a.case!r} in {a.path}", file=sys.stderr)
        return 2

    print(f"EVAL RUN — {len(cases)} case(s) × {a.runs} run(s), judge votes {a.judge_votes}")
    print("deviations from `claude plugin eval`:")
    for d in DEVIATIONS:
        print(f"  · {d}")
    # `--plugin` is optional: each case names its own plugin path in `plugins:`. Resolve the same
    # way run_case does, for the first case, so the shadow warning fires with or without the flag.
    _pd = a.plugin
    if not _pd:
        _c0 = os.path.join(a.path, cases[0])
        _fm0, _, _ = EL.split_front(open(os.path.join(_c0, "prompt.md"), encoding="utf-8").read())
        _pd = os.path.normpath(os.path.join(_c0, ((_fm0 or {}).get("plugins") or ["../.."])[0]))
    shadows = installed_shadow(os.path.abspath(_pd))
    if shadows:
        note = ("an INSTALLED copy of this plugin exists at " + shadows[0] + " — the agent's Skill "
                "call may resolve to it instead of the working tree, in which case this run grades "
                "the INSTALLED version. Sync or uninstall it before believing a score")
        DEVIATIONS.append(note)
        print(f"\n  ⛔ {note}")
    print()

    results, cost = [], 0.0
    for c in cases:
        print(f"[{c}]", flush=True)
        r = run_case(os.path.join(a.path, c), a)
        results.append(r)
        for run in r.get("runs", []):
            if a.dry_run:
                print("  " + " ".join(run["argv"][:6]) + " …")
                continue
            cost += float(run["meta"].get("total_cost_usd") or 0)
            if run.get("inconclusive"):
                print(f"  ⛔ INCONCLUSIVE — the run ended as "
                      f"{run['meta'].get('subtype') or 'no result record'}; it did not finish the "
                      f"work, so its graders are excluded from the score. Raise max_turns or "
                      f"timeout_seconds in the case and re-run.")
            for g in run["graders"]:
                mark = "ok  " if g["score"] >= 1.0 else "FAIL"
                extra = ""
                if g["type"] == "llm":
                    extra = "  — " + "; ".join(w for w in g["details"].get("why", []) if w)[:120]
                elif g["type"] == "tool_used":
                    extra = f"  ({g['details'].get('calls')} call(s))"
                print(f"  [{mark}] {g['name']}{extra}")
            if run["other_skills_used"]:
                print(f"   ·  other skills used: {', '.join(run['other_skills_used'])}")
            print(f"   ·  {run['meta'].get('num_turns')} turns · {run['seconds']}s · "
                  f"${float(run['meta'].get('total_cost_usd') or 0):.3f}")
        print()

    if a.dry_run:
        return 0

    agg, inconc = {}, []
    for r in results:
        good = [run for run in r["runs"] if not run.get("inconclusive")]
        if not good and r["runs"]:
            inconc.append(r["name"])
            continue
        gs = [g["score"] for run in good for g in run["graders"]]
        agg[r["name"]] = round(sum(gs) / len(gs), 3) if gs else 0.0
    overall = round(sum(agg.values()) / len(agg), 3) if agg else 0.0
    doc = {"schemaVersion": "1.0",
           "harness": {"tool": "eval_run.py (local, not `claude plugin eval`)",
                       "runs": a.runs, "judge_votes": a.judge_votes,
                       "model": a.model or "(session default)",
                       "deviations": DEVIATIONS},
           "suite": {"name": os.path.basename(os.path.abspath(a.path)),
                     "cases": [{"name": r["name"], "arms": {"with": r["runs"]}} for r in results]},
           "aggregates": {"caseScores": agg, "overallScore": overall,
                          "total_cost_usd": round(cost, 4)}}
    out = a.out or os.path.join(a.path, "results", time.strftime("%Y-%m-%dT%H-%M-%S"))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "aggregate-result.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    doc["aggregates"]["inconclusive"] = inconc
    print("-" * 72)
    for k, v in sorted(agg.items()):
        print(f"  {v:>5.0%}  {k}")
    for k in inconc:
        print(f"     —   {k}  (inconclusive: every run ended early)")
    print(f"\n  overall {overall:.0%} · ${cost:.2f} · {os.path.relpath(out)}/aggregate-result.json")
    if a.runs < 3:
        print("  ⛔ one run per case is a SMOKE TEST, not a pass rate. --runs 3 before you act on it.")
    return 0 if overall >= 1.0 else 1


def regrade(a) -> int:
    """Re-run the graders over a stored run's material. The expensive half of an eval is the agent;
    the half you iterate on is the rubric, so they should not be welded together."""
    doc = json.load(open(a.regrade, encoding="utf-8"))
    root = a.path
    rc = 0
    for case in doc["suite"]["cases"]:
        cdir = os.path.join(root, case["name"])
        gdir = os.path.join(cdir, "graders")
        if not os.path.isdir(gdir):
            print(f"[{case['name']}] no graders/ at {gdir} — skipped", file=sys.stderr)
            continue
        print(f"[{case['name']}] regrade")
        for run in case["arms"]["with"]:
            ctx = {"tools": [{"name": t.split("(", 1)[0], "input": {"_": t}}
                             for t in run.get("tool_calls", [])],
                   "last_message": run.get("last_message", ""),
                   "files": run.get("files_created", []), "ws": "/nonexistent"}
            for gf in sorted(f for f in os.listdir(gdir) if f.endswith(".md")):
                g, _, gerr = EL.split_front(open(os.path.join(gdir, gf), encoding="utf-8").read())
                if gerr or g.get("type") != "llm":
                    continue          # mechanical graders need the real trace, not its rendering
                sc, det = grade_llm(g, ctx, a.judge_votes, a.judge_model, 180)
                was = next((x["score"] for x in run["graders"] if x["name"] == gf[:-3]), None)
                arrow = "" if was is None or was == sc else f"   (was {was:.0f})"
                print(f"  [{'ok  ' if sc >= 1 else 'FAIL'}] {gf[:-3]}{arrow}")
                for w in det.get("why", []):
                    print(f"        · {w[:130]}")
                if sc < 1:
                    rc = 1
    return rc


# -------------------------------------------------------------------------------------- selftest
def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and bool(cond)

    stream = [
        json.dumps({"type": "system", "subtype": "init"}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "let me look"},
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "python3 scripts/develop.py init job"}}]}}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": "a/S1.frame.prompt.md"}}]}}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "engineering:debug"}}]}}),
        json.dumps({"type": "result", "subtype": "success", "num_turns": 3,
                    "total_cost_usd": 0.12, "result": "I opened the job and ran develop.py."}),
    ]
    ctx = parse_stream(stream)
    ctx["files"] = ["a/S1.frame.prompt.md", "00-brief/DEVELOPMENT.md"]
    ctx["ws"] = "/nonexistent"
    check("the trace yields tool calls in order", [c["name"] for c in ctx["tools"]][:2] == ["Bash", "Write"])
    check("the final message comes from the result record",
          ctx["last_message"].startswith("I opened the job"))
    check("cost and turns are captured", ctx["meta"]["num_turns"] == 3)
    check("a foreign skill is noticed", ctx["other_skills"] == ["engineering:debug"])

    s, d = grade_tool_used({"tool": "Bash", "input_match": r"develop\.py", "min": 1}, ctx)
    check("tool_used matches on the command text", s == 1.0 and d["calls"] == 1)
    s, _ = grade_tool_used({"tool": "Bash", "input_match": r"refsource\.py", "min": 1}, ctx)
    check("tool_used fails when the script was never run", s == 0.0)
    s, _ = grade_tool_used({"tool": "mcp__Higgsfield__generate_image", "min": 0, "max": 0}, ctx)
    check("a min:0/max:0 grader passes when the tool was never called", s == 1.0)
    s, _ = grade_tool_used({"tool": "Bash", "min": 0, "max": 0}, ctx)
    check("a min:0/max:0 grader FAILS when it was called", s == 0.0)
    s, _ = grade_tool_order({"before": "Bash", "after": "Write"}, ctx)
    check("tool_order reads the real order", s == 1.0)
    s, _ = grade_tool_order({"before": "Write", "after": "Bash"}, ctx)
    check("tool_order fails on the wrong order", s == 0.0)
    s, _ = grade_file_exists({"path": "*.prompt.md"}, ctx)
    check("file_exists globs the files the agent created", s == 1.0)
    s, _ = grade_file_exists({"path": "*.pptx"}, ctx)
    check("file_exists fails for a file nobody wrote", s == 0.0)
    s, _ = grade_regex({"pattern": "develop", "match": "contains"}, ctx)
    check("regex reads the final message by default", s == 1.0)
    s, _ = grade_regex({"pattern": r"(?i)8k|masterpiece", "match": "not_contains"}, ctx)
    check("a not_contains regex passes on clean output", s == 1.0)
    s, _ = grade_regex({"pattern": "develop", "match": "contains", "target": "trace"}, ctx)
    check("regex can target the trace", s == 1.0)

    ctx2 = parse_stream([json.dumps({"type": "result", "subtype": "error_max_turns"})])
    check("a turn-limited run is recognisable as inconclusive",
          str(ctx2["meta"].get("subtype")).startswith("error_"))
    ctx2["files"], ctx2["ws"] = [], "/nonexistent"
    check("a run that hit the turn limit still parses", ctx2["meta"]["subtype"] == "error_max_turns")
    s, _ = grade_tool_used({"tool": "Bash", "min": 1}, ctx2)
    check("an empty trace fails a min:1 grader", s == 0.0)

    # the shadow detector: a same-named plugin installed elsewhere must be found, and the plugin
    # under test must never report itself as its own shadow
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        under = os.path.join(td, "work", "cinematographly")
        os.makedirs(os.path.join(under, ".claude-plugin"))
        json.dump({"name": "cinematographly"},
                  open(os.path.join(under, ".claude-plugin", "plugin.json"), "w"))
        home = os.path.join(td, "home")
        os.makedirs(os.path.join(home, ".claude", "plugins"))
        real_expand = os.path.expanduser
        os.path.expanduser = lambda p: p.replace("~", home)                  # noqa: E731
        try:
            check("no installed copy → no shadow", installed_shadow(under) == [])
            inst = os.path.join(home, ".claude", "plugins", "synced", "acct", "cinematographly")
            os.makedirs(inst)
            hits = installed_shadow(under)
            check("an installed copy of the same name IS reported as a shadow", hits == [inst])
            check("the plugin under test is never its own shadow", under not in hits)
        finally:
            os.path.expanduser = real_expand

    print("-" * 60)
    print("selftest OK — the stream parser, all four mechanical graders and their failure "
          "directions, foreign-skill detection, an installed same-named plugin reported as a "
          "shadow, and a turn-limited run reported as inconclusive rather than scored 0" if ok
          else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
