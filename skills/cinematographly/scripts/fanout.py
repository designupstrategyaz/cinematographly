#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""fanout.py — the dispatcher's ledger for parallel agents: plan the units, record the reports, check the join.

Author, 2026-11-05: *"This massive plugin, needs to use parallel agents for many of it's tasks when possible."* The
design is `references/parallel-agents.md`: the main session dispatches one plugin agent per unit (`agents/*.md`),
side by side, and owns the join. This script makes the join mechanical: *silence is a FAIL* (a unit with no file
failed, whatever its agent said), every report carries a typed header with an allowed verdict,
and a file the round was not given changed is a scope leak.

  plan <job> --stage S --agent A --unit ID [--unit ID …] [--run RUN] [--json]
        09-qa/fanout/<run>/PLAN.json: each unit's output path, and a snapshot of the job's text files (for the
        scope check). Prints the paths to put in each agent's brief. More than 6 units: a warning to run rounds.
  record <job> <run> <unit> --from FILE|-
        save a read-only agent's returned report (it has no write tool) at its unit's path.
  check <job> <run> [--json]
        every unit: its file exists, its `fanout` header parses (a ```fanout block in .md, a top-level "fanout"
        object in .json), names this unit and agent, and carries one of the agent's verdicts; every text file that
        changed since `plan` is a unit's output or a file a writer's header lists. Writes RESULT.json, prints the
        questions the round raised (ask the owner once). Exit 1 on anything missing, malformed or out of scope.
  agents [--dir PLUGIN/agents] [--json]
        lint the plugin's agent files: frontmatter, minimal tools (reviewers read-only, nobody with a generation,
        Resolve, browser or agent-launch tool), the body's sections, every verdict in the output contract, and
        every agent named in references/parallel-agents.md.
  --selftest
"""
from __future__ import annotations
import argparse, datetime as _dt, json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
FANOUT_DIR = os.path.join("09-qa", "fanout")
ROUND_CAP = 6                                   # [ASSUMED] past this the merge becomes a skim (parallel-agents.md §4)

# the plugin's agents: allowed verdicts, read-only or not, the output file's kind
AGENTS = {
    "cine-researcher":       {"verdicts": ["DONE", "PARTIAL"], "readonly": False, "ext": "md"},
    "cine-draft-writer":     {"verdicts": ["DONE"], "readonly": False, "ext": "md"},
    "cine-script-critic":    {"verdicts": ["PASS", "FAIL"], "readonly": True, "ext": "md"},
    "cine-cold-reader":      {"verdicts": ["DONE"], "readonly": False, "ext": "md"},       # (v2.67.0) one script file
    "cine-shot-writer":      {"verdicts": ["LINT-CLEAN", "LINT-FAIL"], "readonly": False, "ext": "md"},
    "cine-take-reviewer":    {"verdicts": ["PASS", "RETAKE", "HOLD"], "readonly": True, "ext": "md"},
    "cine-scene-continuity": {"verdicts": ["PASS", "FAIL", "ASK"], "readonly": True, "ext": "md"},
    "cine-sfx-spotter":      {"verdicts": ["DONE", "PARTIAL"], "readonly": False, "ext": "json"},
}
READONLY_TOOLS = {"Read", "Grep", "Glob"}
ALLOWED_TOOLS = READONLY_TOOLS | {"Write", "Edit", "Bash", "WebSearch", "WebFetch"}
# Bash is unrestricted once granted (a prose rule is not a scope, AP-3), so ONE agent holds it: the shot writer, for its
# own prompt_lint loop. Every other agent's measurements are run by the dispatcher before or after the round.
BASH_OK = {"cine-shot-writer"}
MODELS = {"sonnet", "opus", "haiku", "inherit"}
SECTIONS = ["## Core responsibilities", "## Workflow", "## Output contract", "## Examples", "## Rules",
            "## When not to use"]
TEXT_EXT = (".md", ".json", ".txt", ".yaml", ".yml", ".csv", ".srt", ".ok", ".py", ".toml", ".js", ".sh", ".edl", ".xml")
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
HEADER_RE = re.compile(r"```fanout\s*\n(\{.*?\})\s*\n```", re.S)
UNIT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+-]{0,80}$")


class Refused(Exception):
    pass


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_dir(job: str, run: str) -> str:
    return os.path.join(job, FANOUT_DIR, run)


def _safe_name(unit: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.@+-]", "_", unit)


def _rel(path: str) -> str:
    """A job-relative path, normalised: separators, a leading './', never a leading '../' trimmed away."""
    p = str(path or "").replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return p


def _globs_for(writes: list, unit: str) -> list:
    return [_rel(w.replace("{unit}", unit)) for w in writes or []]


def snapshot(job: str) -> dict:
    """{relpath: [size, mtime_ns]} for the job's text files, outside 09-qa/fanout/ (the scope check's baseline)."""
    out = {}
    for d, ds, fs in os.walk(job):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        rel_d = os.path.relpath(d, job)
        if rel_d.replace("\\", "/").startswith(FANOUT_DIR.replace("\\", "/")):
            ds[:] = []
            continue
        for f in fs:
            if f.lower().endswith(TEXT_EXT):
                p = os.path.join(d, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                out[os.path.relpath(p, job).replace("\\", "/")] = [st.st_size, st.st_mtime_ns]
    return out


def plan(job: str, stage: str, agent: str, units: list, run: str | None = None, writes: list | None = None,
         writes_for: dict | None = None, sheets_sent: list | None = None) -> dict:
    """`writes`: glob patterns (job-relative, `{unit}` filled in per unit) a WRITER may change besides its output —
    e.g. `01-script/prompts/{unit}-*.clip.prompt.md`. The scope check allows only these; a writer's own header can
    narrow them, never widen them . `writes_for`: {unit: [globs]} for files named per unit (the shot ids of
    one scene: `S2=01-script/prompts/S4.clip.prompt.*`)."""
    if agent not in AGENTS:
        raise Refused(f"unknown agent {agent!r} — the plugin's agents are {', '.join(AGENTS)}")
    if not units:
        raise Refused("no units — a fan-out needs at least one")
    if len(set(units)) != len(units):
        raise Refused("a unit id appears twice — each unit is one agent and one output")
    if len({_safe_name(u) for u in units}) != len(units):
        raise Refused("two unit ids map to the same file name (`:` and `_` both become `_`) — rename one")
    writes_for = {k: list(v) for k, v in (writes_for or {}).items()}
    for k in writes_for:
        if k not in units:
            raise Refused(f"--writes-for names unit {k!r}, which is not in --unit")
    if (writes or writes_for) and AGENTS.get(agent, {}).get("readonly"):
        raise Refused(f"{agent} is read-only — it writes nothing, so --writes does not apply")
    for w in list(writes or []) + [g for v in writes_for.values() for g in v]:
        if w.startswith("/") or ".." in w.replace("\\", "/").split("/"):
            raise Refused(f"--writes {w!r}: a job-relative pattern, never absolute or with '..'")
    for u in units:
        if not UNIT_RE.match(u):
            raise Refused(f"unit id {u!r}: letters, digits and . _ : @ + - only")
    if not os.path.isdir(job):
        raise Refused(f"no job folder at {job}")
    run = run or f"{re.sub(r'[^A-Za-z0-9-]', '-', stage)}-{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    rd = _run_dir(job, run)
    if os.path.exists(os.path.join(rd, "PLAN.json")):
        raise Refused(f"run {run} already has a plan — pick another run id")
    os.makedirs(rd, exist_ok=True)
    ext = AGENTS[agent]["ext"]
    if sheets_sent is not None:           # (v2.70.0) the DISPATCHER says which units got the approved sheets
        bad = [x for x in sheets_sent if x != "all" and x not in units]
        if bad:
            raise Refused(f"--sheets-sent names {', '.join(bad)}, not in --unit")
    P = {"run": run, "stage": stage, "agent": agent, "created": _now(),
         "units": [{"id": u, "out": os.path.join(FANOUT_DIR, run, f"{_safe_name(u)}.{ext}").replace("\\", "/"),
                    "writes": _globs_for(writes or [], u) + [_rel(g) for g in writes_for.get(u, [])],
                    **({} if sheets_sent is None else {"sheet_sent": "all" in sheets_sent or u in sheets_sent})}
                   for u in units],
         "snapshot": snapshot(job), "rounds": -(-len(units) // ROUND_CAP)}
    json.dump(P, open(os.path.join(rd, "PLAN.json"), "w", encoding="utf-8"), indent=1)
    return P


def load_plan(job: str, run: str) -> dict:
    p = os.path.join(_run_dir(job, run), "PLAN.json")
    if not os.path.isfile(p):
        raise Refused(f"no plan for run {run} — `fanout.py plan` first")
    return json.load(open(p, encoding="utf-8"))


def record(job: str, run: str, unit: str, text: str, force: bool = False) -> str:
    P = load_plan(job, run)
    row = next((u for u in P["units"] if u["id"] == unit), None)
    if not row:
        raise Refused(f"unit {unit!r} is not in run {run} ({', '.join(u['id'] for u in P['units'])})")
    out = os.path.join(job, row["out"])
    if os.path.exists(out) and not force:
        raise Refused(f"{row['out']} exists — the unit already reported (--force to replace it)")
    if not text.strip():
        raise Refused("the report is empty — an empty reply is a missing unit, not a report")
    open(out, "w", encoding="utf-8").write(text if text.endswith("\n") else text + "\n")
    return row["out"]


def read_header(path: str) -> tuple:
    """(header dict | None, problem | None)."""
    try:
        src = open(path, encoding="utf-8").read()
    except OSError as e:
        return None, f"unreadable: {e}"
    if path.endswith(".json"):
        try:
            d = json.loads(src)
        except json.JSONDecodeError as e:
            return None, f"not JSON: {e.msg} at line {e.lineno}"
        h = d.get("fanout") if isinstance(d, dict) else None
        return (h, None) if isinstance(h, dict) else (None, "no top-level `fanout` object")
    m = HEADER_RE.search(src)
    if not m:
        return None, "no ```fanout header block"
    try:
        h = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return None, f"the fanout header is not JSON: {e.msg}"
    return (h, None) if isinstance(h, dict) else (None, "the fanout header is not an object")


IDENTITY = ("held", "drifted", "unknown")


HIGH_ROW_RE = re.compile(r"^\|\s*\d+\s*\|\s*(?:CRITICAL|HIGH)\s*\|(.*)$", re.M | re.I)


def high_rows(body: str) -> int:
    """CRITICAL or HIGH rows in a take report's findings table, not counting an identity finding."""
    n = 0
    for m in HIGH_ROW_RE.finditer(body or ""):
        cells = [c.strip().lower() for c in m.group(1).split("|")]       # confidence | check | frame | finding
        if len(cells) > 1 and re.search(r"\bidentity\b", cells[1]):     # "identity", "identity (face)", "V2 identity"
            continue                       # the identity line itself, by its Check cell, never by wording (Grok r2)
        n += 1
    return n


def take_identity_problem(h: dict, sheet_sent=None, body: str | None = None) -> str | None:
    """(v2.70.0, Wave 5 A5) The take reviewer's identity rules, checked on every report instead of trusted:
    `identity` is held / drifted / unknown; with no approved sheet seen it is `unknown`; `drifted` puts the take in
    front of the person (HOLD) and never makes a RETAKE by itself — a glance at a contact sheet is not a measurement,
    so a retake needs another CRITICAL or HIGH finding (`high_findings`)."""
    idv = str(h.get("identity") or "").strip().lower()
    if idv not in IDENTITY:
        return f"`identity` is {h.get('identity')!r}: one of {', '.join(IDENTITY)} (unknown when in doubt)"
    seen = h.get("sheet_seen")
    if seen is not None and not isinstance(seen, bool):     # "false" is a truthy string (build review 1, Sonnet)
        return f"`sheet_seen` is {seen!r}: true or false, not a string"
    hf = h.get("high_findings", 0)
    if isinstance(hf, bool) or not isinstance(hf, int) or hf < 0:
        return f"`high_findings` is {hf!r}: a whole number (the CRITICAL and HIGH findings other than identity)"
    if sheet_sent is not None:          # the plan's stamp wins over what the report says (build review 1, Sonnet)
        seen = bool(sheet_sent)
    if not seen and idv != "unknown":
        return f"`identity: {idv}` with no approved sheet {'sent' if sheet_sent is not None else 'seen'} — without the sheet it can only be unknown"
    if body is not None and hf > high_rows(body):   # the table, not a count the agent wrote, unlocks a retake (Grok r1)
        return (f"`high_findings: {hf}` but the findings table has {high_rows(body)} CRITICAL or HIGH row(s) besides "
                f"identity — count what the table shows")
    if idv == "drifted" and h.get("verdict") == "RETAKE" and not hf:
        return ("`identity: drifted` is the only reason for this RETAKE — drift goes to the person as HOLD; a retake "
                "needs another CRITICAL or HIGH finding")
    if idv == "drifted" and h.get("verdict") == "PASS":
        return "`identity: drifted` with PASS — a drifted face is shown to the person (HOLD)"
    return None


def check(job: str, run: str) -> dict:
    P = load_plan(job, run)
    agent = P["agent"]
    allowed = AGENTS.get(agent, {}).get("verdicts", [])
    import fnmatch
    rows, questions, allowed_paths = [], [], {u["out"] for u in P["units"]}
    globs = [g for u in P["units"] for g in u.get("writes") or []]
    for u in P["units"]:
        out = os.path.join(job, u["out"])
        r = {"unit": u["id"], "out": u["out"]}
        if not os.path.isfile(out):
            r.update(status="MISSING", problem="no report — silence is a FAIL; re-run this unit once, alone")
            rows.append(r)
            continue
        h, prob = read_header(out)
        if prob:
            r.update(status="BAD-HEADER", problem=prob)
        elif str(h.get("unit")) != u["id"]:
            r.update(status="WRONG-UNIT", problem=f"the header names unit {h.get('unit')!r}, not {u['id']!r}")
        elif h.get("agent") not in (agent, None, ""):
            r.update(status="WRONG-AGENT", problem=f"the header names agent {h.get('agent')!r}, not {agent!r}")
        elif h.get("verdict") not in allowed:
            r.update(status="BAD-VERDICT", problem=f"verdict {h.get('verdict')!r} is not one of {', '.join(allowed)}")
        elif agent == "cine-take-reviewer" and take_identity_problem(h, u.get("sheet_sent"), open(out, encoding="utf-8").read()):
            r.update(status="BAD-IDENTITY", problem=take_identity_problem(h, u.get("sheet_sent"),
                                                                          open(out, encoding="utf-8").read()))
        else:
            r.update(status="OK", verdict=h["verdict"])
        if isinstance(h, dict):
            for q in h.get("questions") or []:
                if str(q).strip():
                    questions.append({"unit": u["id"], "question": str(q).strip()})
            outside = [f for f in (h.get("files") or []) if not any(fnmatch.fnmatch(_rel(f), g) for g in u.get("writes") or [])]
            if outside and r.get("status") == "OK":
                r.update(status="OUT-OF-BRIEF", problem=f"the header lists files outside this unit's --writes: "
                                                        f"{', '.join(map(str, outside[:4]))}")
        rows.append(r)
    before, now = P.get("snapshot") or {}, snapshot(job)
    changed = sorted(p for p in now if before.get(p) != now[p])
    leaks = [p for p in changed if p not in allowed_paths and not any(fnmatch.fnmatch(p, g) for g in globs)]
    res = {"run": P["run"], "stage": P["stage"], "agent": agent, "checked": _now(), "units": rows,
           "questions": questions, "changed": changed, "scope_leaks": leaks,
           "verdicts": {k: sum(1 for r in rows if r.get("verdict") == k) for k in allowed},
           "ok": all(r["status"] == "OK" for r in rows) and not leaks}
    json.dump(res, open(os.path.join(_run_dir(job, run), "RESULT.json"), "w", encoding="utf-8"), indent=1)
    return res


# ── the agent files ────────────────────────────────────────────────────────────────────────────────────────────
def _frontmatter(src: str) -> tuple:
    if not src.startswith("---\n"):
        return {}, src
    end = src.find("\n---", 4)
    if end < 0:
        return {}, src
    fm = {}
    for line in src[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm, src[end + 4:]


def lint_agents(adir: str | None = None, doc: str | None = None) -> dict:
    adir = adir or os.path.join(PLUGIN_ROOT, "agents")
    doc = doc if doc is not None else os.path.join(SKILL_ROOT, "references", "parallel-agents.md")
    probs, seen = [], {}
    if not os.path.isdir(adir):
        return {"ok": False, "problems": [f"no agents folder at {adir}"], "agents": []}
    for f in sorted(os.listdir(adir)):
        if not f.endswith(".md"):
            continue
        src = open(os.path.join(adir, f), encoding="utf-8").read()
        fm, body = _frontmatter(src)
        name = fm.get("name", "")
        where = f"agents/{f}"
        seen[name] = f
        if name != f[:-3]:
            probs.append(f"{where}: name {name!r} must equal the file name {f[:-3]!r}")
        if name not in AGENTS:
            probs.append(f"{where}: {name!r} is not in fanout.AGENTS — register it (verdicts, read-only, output kind)")
            continue
        spec = AGENTS[name]
        desc = fm.get("description", "")
        if not desc or len(desc) > 1024:
            probs.append(f"{where}: description missing or over 1024 characters ({len(desc)})")
        if fm.get("model") not in MODELS:
            probs.append(f"{where}: model {fm.get('model')!r} is not one of {', '.join(sorted(MODELS))}")
        tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
        if not tools:
            probs.append(f"{where}: no tools line — an agent without one inherits every tool (AP-3)")
        bad = sorted(t for t in tools if t not in ALLOWED_TOOLS)
        if bad:
            probs.append(f"{where}: tools outside the allowed set: {', '.join(bad)} — no generation, Resolve, browser, "
                         f"MCP or agent-launch tool in a parallel agent (parallel-agents.md §0)")
        if "Bash" in tools and name not in BASH_OK:
            probs.append(f"{where}: Bash is unrestricted once granted — only {', '.join(sorted(BASH_OK))} holds it; the "
                         f"dispatcher runs this agent's measurements before or after the round (AP-3)")
        if spec["readonly"] and not tools <= READONLY_TOOLS:
            probs.append(f"{where}: a reviewer is read-only — {', '.join(sorted(tools - READONLY_TOOLS))} must go "
                         f"(tool absence is the hard scope, AP-3)")
        if spec["readonly"] and fm.get("model") not in ("sonnet", "haiku"):
            probs.append(f"{where}: a reviewer runs on another model family than the writer (AP-4) — sonnet")
        for s in SECTIONS:
            if s not in body:
                probs.append(f"{where}: missing section {s!r}")
        if "## Output contract" in body:
            oc = body.split("## Output contract", 1)[1].split("## Examples", 1)[0]
            if "fanout" not in oc:
                probs.append(f"{where}: the output contract carries no `fanout` header")
            for v in spec["verdicts"]:
                if v not in oc:
                    probs.append(f"{where}: the output contract never names verdict {v}")
        tail = [ln for ln in body.strip().splitlines() if ln.strip()][-2:]
        if not any(ln.strip().endswith("**") for ln in tail):
            probs.append(f"{where}: no closing line (a bold sentence at the end)")
    for a in AGENTS:
        if a not in seen:
            probs.append(f"agents/{a}.md is missing (registered in fanout.AGENTS)")
    if doc and os.path.isfile(doc):
        d = open(doc, encoding="utf-8").read()
        for a in AGENTS:
            if f"`{a}`" not in d:
                probs.append(f"references/parallel-agents.md never names `{a}`")
    elif doc:
        probs.append("references/parallel-agents.md is missing")
    return {"ok": not probs, "problems": probs, "agents": sorted(seen)}


# ── CLI ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _print_check(res: dict) -> None:
    print(f"FANOUT {res['run']} ({res['agent']}, stage {res['stage']}): {'OK' if res['ok'] else 'NOT OK'}")
    for r in res["units"]:
        print(f"  [{r['status']:<11}] {r['unit']:<18} {r.get('verdict') or r.get('problem')}")
    if res["scope_leaks"]:
        print("  [SCOPE      ] changed outside the units' paths: " + ", ".join(res["scope_leaks"][:12]))
    if res["questions"]:
        print("  questions for the owner (ask once, batched):")
        for q in res["questions"]:
            print(f"    - [{q['unit']}] {q['question']}")
    print("  verdicts: " + ", ".join(f"{k} {v}" for k, v in res["verdicts"].items()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan"); p.add_argument("job"); p.add_argument("--stage", required=True)
    p.add_argument("--agent", required=True, choices=sorted(AGENTS)); p.add_argument("--unit", action="append", default=[])
    p.add_argument("--run"); p.add_argument("--json", action="store_true")
    p.add_argument("--writes", action="append", default=[], metavar="GLOB",
                   help="a job-relative glob a writer may change besides its output ({unit} filled in), e.g. "
                        "01-script/prompts/{unit}-*.clip.prompt.md")
    p.add_argument("--sheets-sent", metavar="UNITS", help="(v2.70.0, take reviewer) the units whose brief carried the "
                                                           "approved sheets, comma-separated, or `all`; check holds each "
                                                           "report's identity to this, not to what it says")
    p.add_argument("--writes-for", action="append", default=[], metavar="UNIT=GLOB",
                   help="a glob for one unit only (repeatable), e.g. S2=01-script/prompts/S4.clip.prompt.*")
    r = sub.add_parser("record"); r.add_argument("job"); r.add_argument("run"); r.add_argument("unit")
    r.add_argument("--from", dest="src", required=True); r.add_argument("--force", action="store_true")
    c = sub.add_parser("check"); c.add_argument("job"); c.add_argument("run"); c.add_argument("--json", action="store_true")
    g = sub.add_parser("agents"); g.add_argument("--dir"); g.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        if a.cmd == "plan":
            wf = {}
            for item in a.writes_for:
                if "=" not in item:
                    raise Refused(f"--writes-for {item!r}: UNIT=GLOB")
                k, g = item.split("=", 1)
                wf.setdefault(k, []).append(g)
            ss = None if a.sheets_sent is None else [x.strip() for x in a.sheets_sent.split(",") if x.strip()]
            P = plan(a.job, a.stage, a.agent, a.unit, a.run, a.writes, wf, ss)
            if a.json:
                print(json.dumps({k: v for k, v in P.items() if k != "snapshot"}, indent=1))
            else:
                print(f"run {P['run']} — {len(P['units'])} unit(s) for {a.agent}"
                      + (f"; ⚠ more than {ROUND_CAP}: launch {P['rounds']} rounds of ≤ {ROUND_CAP}" if P["rounds"] > 1 else ""))
                for u in P["units"]:
                    print(f"  {u['id']:<18} → {u['out']}")
                print(f"After the round: fanout.py check {a.job} {P['run']}")
            return 0
        if a.cmd == "record":
            text = sys.stdin.read() if a.src == "-" else open(a.src, encoding="utf-8").read()
            print(f"recorded {record(a.job, a.run, a.unit, text, a.force)}")
            return 0
        if a.cmd == "check":
            res = check(a.job, a.run)
            print(json.dumps(res, indent=1)) if a.json else _print_check(res)
            return 0 if res["ok"] else 1
        if a.cmd == "agents":
            res = lint_agents(a.dir)
            if a.json:
                print(json.dumps(res, indent=1))
            else:
                print(f"AGENTS: {'OK' if res['ok'] else 'NOT OK'} — {len(res['agents'])}: {', '.join(res['agents'])}")
                for pr in res["problems"]:
                    print(f"  - {pr}")
            return 0 if res["ok"] else 1
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    ap.print_help()
    return 2


def selftest() -> int:
    ok = True
    # (v2.70.1) the glossary's agent count and list follow the agent files (it said seven after the eighth was added)
    _g = open(os.path.join(SKILL_ROOT, "GLOSSARY.md"), encoding="utf-8").read()
    _row = re.search(r"^\| \*\*Agents\*\* \|([^|]+)\|", _g, re.M)
    _n = len([f for f in os.listdir(os.path.join(PLUGIN_ROOT, "agents")) if f.endswith(".md")])
    _words = {6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve"}
    assert _row and _words.get(_n, str(_n)) in _row.group(1) and _row.group(1).split(":", 1)[-1].count(",") == _n - 1, \
        f"GLOSSARY.md's Agents row does not match the {_n} files in agents/: {_row.group(1) if _row else None!r}"

    def chk(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  {detail}"))

    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("00-brief", "01-script/scenes", "01-script/prompts", "09-qa"):
            os.makedirs(os.path.join(job, d))
        open(os.path.join(job, "01-script/scenes/S1.scene.md"), "w").write("[LOCATION MAP]\nthe kitchen\n")
        open(os.path.join(job, "00-brief/CHECKPOINT.md"), "w").write("Job: t-1\n")
        P = plan(job, "selects", "cine-take-reviewer", ["T1", "T2", "T3"], run="sel-1")
        chk("plan: one output path per unit, inside 09-qa/fanout/<run>/, and a snapshot of the text files",
            [u["out"] for u in P["units"]] == [f"09-qa/fanout/sel-1/T{i}.md" for i in (1, 2, 3)]
            and "01-script/scenes/S1.scene.md" in P["snapshot"])
        for bad, why in ((("cine-oracle", ["A"]), "unknown agent"), (("cine-take-reviewer", ["A", "A"]), "twice"),
                         (("cine-take-reviewer", ["S2:logic", "S2_logic"]), "same file name"),
                         (("cine-take-reviewer", []), "no units"), (("cine-take-reviewer", ["a b"]), "letters")):
            try:
                plan(job, "x", bad[0], bad[1], run=f"bad-{why[:3]}")
                chk(f"plan refuses: {why}", False)
            except Refused as e:
                chk(f"plan refuses: {why}", why in str(e), str(e))
        good = lambda u, v="PASS": (f"```fanout\n{{\"unit\": \"{u}\", \"agent\": \"cine-take-reviewer\", \"verdict\": \"{v}\", "
                                    f"\"findings\": 0, \"identity\": \"unknown\", \"questions\": []}}\n```\n**Function:** met\n")
        record(job, "sel-1", "T1", good("T1"))
        record(job, "sel-1", "T2", good("T2", "RETAKE").replace('"questions": []', '"questions": ["is the mug meant to move?"]'))
        res = check(job, "sel-1")
        chk("check: a unit that never reported is MISSING and the round is NOT OK (silence is a FAIL)",
            not res["ok"] and [r["status"] for r in res["units"]] == ["OK", "OK", "MISSING"], res["units"])
        chk("check: the questions are collected for one batched ask", res["questions"] == [
            {"unit": "T2", "question": "is the mug meant to move?"}], res["questions"])
        record(job, "sel-1", "T3", good("T3", "LOOKS-FINE"))
        chk("check: a verdict outside the agent's set is BAD-VERDICT",
            check(job, "sel-1")["units"][2]["status"] == "BAD-VERDICT")
        record(job, "sel-1", "T3", good("T1"), force=True)
        chk("check: a header naming another unit is WRONG-UNIT", check(job, "sel-1")["units"][2]["status"] == "WRONG-UNIT")
        record(job, "sel-1", "T3", "Looks good to me!", force=True)
        chk("check: prose with no header is BAD-HEADER", check(job, "sel-1")["units"][2]["status"] == "BAD-HEADER")
        record(job, "sel-1", "T3", good("T3", "HOLD"), force=True)
        res = check(job, "sel-1")
        chk("check: all three reported with allowed verdicts → OK, verdicts counted",
            res["ok"] and res["verdicts"] == {"PASS": 1, "RETAKE": 1, "HOLD": 1}, res)
        # (v2.70.0, Wave 5 A5) the identity rules, checked on every take reviewer's report
        P2 = plan(job, "selects", "cine-take-reviewer", [f"I{i}" for i in range(1, 8)], run="sel-id")
        def idh(u, v, idv, seen, high=0, table=True):
            rows_ = "".join(f"| {k + 1} | HIGH | 90 | V7 | 2.4 s | six fingers on the left hand |\n" for k in range(high)) \
                if table else ""
            return (f"```fanout\n{{\"unit\": \"{u}\", \"agent\": \"cine-take-reviewer\", \"verdict\": \"{v}\", "
                    f"\"findings\": 1, \"identity\": \"{idv}\", \"sheet_seen\": {str(seen).lower()}, "
                    f"\"high_findings\": {high}, \"questions\": []}}\n```\n| # | Severity | Confidence | Check | "
                    f"Frame / time | Finding |\n|---|---|---|---|---|---|\n| 0 | MEDIUM | 70 | identity | 1.0 s | "
                    f"face drift from the sheet |\n" + rows_)
        cases = [("I1", "PASS", "held", True, 0, "OK"),            # the same face, sheet seen
                 ("I2", "HOLD", "drifted", True, 0, "OK"),         # a wrong face (or an unplanned wardrobe/prop change): HOLD
                 ("I3", "RETAKE", "drifted", True, 0, "BAD-IDENTITY"),   # drift alone never makes a retake
                 ("I4", "RETAKE", "drifted", True, 1, "OK"),       # ...but drift plus a HIGH finding (six fingers) can
                 ("I5", "PASS", "held", False, 0, "BAD-IDENTITY"),       # no sheet given: it can only be unknown
                 ("I6", "PASS", "unknown", False, 0, "OK"),        # face hidden or no sheet: unknown can pass
                 ("I7", "PASS", "drifted", True, 0, "BAD-IDENTITY")]     # a drifted face is never waved through
        for u, v, idv, seen, high, _ in cases:
            record(job, "sel-id", u, idh(u, v, idv, seen, high))
        st_ = {r["unit"]: r["status"] for r in check(job, "sel-id")["units"]}
        chk("(2.70) take reviewer identity: drifted → HOLD, never a RETAKE or PASS by itself; no sheet → unknown; "
            "unknown can pass", all(st_[u] == want for u, *_r, want in cases), st_)
        # (build review 1, Sonnet) bad types are a BAD-IDENTITY, never a crash; the plan's stamp beats the report
        P3 = plan(job, "selects", "cine-take-reviewer", ["J1", "J2", "J3"], run="sel-st", sheets_sent=["J1"])
        record(job, "sel-st", "J1", idh("J1", "RETAKE", "drifted", True, 0).replace('"high_findings": 0', '"high_findings": "none"'))
        record(job, "sel-st", "J2", idh("J2", "PASS", "held", True))            # says it saw a sheet; the plan sent none
        record(job, "sel-st", "J3", idh("J3", "PASS", "held", True).replace('"sheet_seen": true', '"sheet_seen": "false"'))
        st3 = {r["unit"]: (r["status"], r.get("problem", "")) for r in check(job, "sel-st")["units"]}
        plan(job, "selects", "cine-take-reviewer", ["K1"], run="sel-str")              # no stamp: the report's own type
        record(job, "sel-str", "K1", idh("K1", "PASS", "held", True).replace('"sheet_seen": true', '"sheet_seen": "true"'))
        k1 = check(job, "sel-str")["units"][0]
        plan(job, "selects", "cine-take-reviewer", ["L1"], run="sel-tab")              # a count with no table behind it
        record(job, "sel-tab", "L1", idh("L1", "RETAKE", "drifted", True, 1, table=False))
        l1 = check(job, "sel-tab")["units"][0]
        chk("(2.70) a RETAKE unlocked by a high_findings count the findings table does not show is refused",
            l1["status"] == "BAD-IDENTITY" and "findings table" in l1.get("problem", ""), l1)
        chk("(2.70) a HIGH row that only USES the word drift still counts; the identity row (by its Check cell) does not",
            high_rows("| 1 | HIGH | 90 | V12 | 3.1 s | the key light drifts from camera-left to camera-right |\n"
                      "| 2 | HIGH | 80 | identity | 1.0 s | the face drifted from the sheet |\n"
                      "| 3 | HIGH | 80 | identity (face) | 1.2 s | the jaw is wider than the sheet's |\n") == 1)
        chk("(2.70) with no stamp, a string sheet_seen is refused for its type", k1["status"] == "BAD-IDENTITY"
            and "not a string" in k1.get("problem", ""), k1)
        chk("(2.70) a non-number high_findings and a string sheet_seen are BAD-IDENTITY (no crash); the dispatcher's "
            "--sheets-sent stamp beats what the report claims",
            st3["J1"][0] == "BAD-IDENTITY" and "whole number" in st3["J1"][1] and st3["J2"][0] == "BAD-IDENTITY"
            and "no approved sheet sent" in st3["J2"][1] and st3["J3"][0] == "BAD-IDENTITY", st3)
        try:
            record(job, "sel-1", "T3", good("T3"))
            chk("record refuses to overwrite a report without --force", False)
        except Refused:
            chk("record refuses to overwrite a report without --force", True)
        # scope: a writer may change only its outputs and the files its header lists
        P2 = plan(job, "prompts", "cine-shot-writer", ["S1"], run="sw-1",
                  writes_for={"S1": ["01-script/prompts/S1-01.clip.prompt.*"]})
        open(os.path.join(job, "01-script/prompts/S1-01.clip.prompt.md"), "w").write("[SCENE CONTEXT]\nx\n")
        open(os.path.join(job, "01-script/prompts/S1-01.clip.prompt.ok"), "w").write("{}\n")
        open(os.path.join(job, P2["units"][0]["out"]), "w").write(
            "```fanout\n{\"unit\": \"S1\", \"agent\": \"cine-shot-writer\", \"verdict\": \"LINT-CLEAN\", "
            "\"files\": [\"01-script/prompts/S1-01.clip.prompt.md\"]}\n```\n")
        chk("check: a writer's own files, inside its --writes, are in scope", check(job, "sw-1")["ok"])
        open(os.path.join(job, P2["units"][0]["out"]), "w").write(
            "```fanout\n{\"unit\": \"S1\", \"agent\": \"cine-shot-writer\", \"verdict\": \"LINT-CLEAN\", "
            "\"files\": [\"01-script/scenes/S1.scene.md\"]}\n```\n")
        chk("check: a header that lists a file outside the brief cannot widen the scope (OUT-OF-BRIEF)",
            check(job, "sw-1")["units"][0]["status"] == "OUT-OF-BRIEF")
        open(os.path.join(job, P2["units"][0]["out"]), "w").write(
            "```fanout\n{\"unit\": \"S1\", \"agent\": \"cine-shot-writer\", \"verdict\": \"LINT-CLEAN\"}\n```\n")
        open(os.path.join(job, "01-script/scenes/S1.scene.md"), "a").write("the table moved\n")
        res = check(job, "sw-1")
        chk("check: the shared scene file changed during the round → a scope leak, NOT OK",
            not res["ok"] and res["scope_leaks"] == ["01-script/scenes/S1.scene.md"], res["scope_leaks"])
        # JSON outputs (the spotter's placement proposal)
        P3 = plan(job, "sound", "cine-sfx-spotter", ["S1"], run="sp-1")
        chk("plan: the spotter's unit is a .json file", P3["units"][0]["out"].endswith("S1.json"))
        json.dump({"fanout": {"unit": "S1", "agent": "cine-sfx-spotter", "verdict": "DONE"},
                   "events": [{"sfx": "mug", "frame": 313, "file": "/x.wav", "volume_db": -18}]},
                  open(os.path.join(job, P3["units"][0]["out"]), "w"))
        chk("check: a JSON proposal's top-level fanout object is read", check(job, "sp-1")["ok"])
        json.dump({"events": []}, open(os.path.join(job, P3["units"][0]["out"]), "w"))
        chk("check: JSON with no fanout object is BAD-HEADER", check(job, "sp-1")["units"][0]["status"] == "BAD-HEADER")
        # the agent files
        res = lint_agents()
        chk("agents: the plugin's seven agent files lint clean (frontmatter, tools, sections, verdicts, the doc)",
            res["ok"] and len(res["agents"]) == len(AGENTS), res["problems"])
        ad = os.path.join(td, "agents")
        os.makedirs(ad)
        src = open(os.path.join(PLUGIN_ROOT, "agents", "cine-take-reviewer.md"), encoding="utf-8").read()
        open(os.path.join(ad, "cine-take-reviewer.md"), "w").write(
            src.replace("tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Write, mcp__Higgsfield__generate_video"))
        r2 = lint_agents(ad, doc="")
        chk("agents: a reviewer given Write and a generation tool fails, naming both",
            any("read-only" in p for p in r2["problems"]) and any("outside the allowed set" in p for p in r2["problems"]),
            r2["problems"])
        open(os.path.join(ad, "cine-take-reviewer.md"), "w").write(src.replace("## Rules", "## Notes"))
        chk("agents: a missing section fails", any("missing section '## Rules'" in p for p in lint_agents(ad, doc="")["problems"]))
        sp_src = open(os.path.join(PLUGIN_ROOT, "agents", "cine-sfx-spotter.md"), encoding="utf-8").read()
        open(os.path.join(ad, "cine-sfx-spotter.md"), "w").write(
            re.sub(r"(?m)^tools: .*$", "tools: Read, Grep, Glob, Write, Bash", sp_src))
        chk("agents: Bash on any agent but the shot writer fails (unrestricted once granted, AP-3)",
            any("Bash is unrestricted" in p for p in lint_agents(ad, doc="")["problems"]))
    print("-" * 60)
    print("selftest OK — plan, record, check (silence is a FAIL; a bad, wrong or missing header; the scope leak), JSON "
          "proposals, and the plugin's agent files linted" if ok else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
