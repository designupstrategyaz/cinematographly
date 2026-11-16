#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
job_tier.py — is this job, or this file, an EVALUATION? The one place that answers it.

House decision 2026-10-25 (the direct-response trial proposal's P9, "Adopt, ship-refusal enforced"): a job whose
checkpoint says `Tier: evaluation` may generate below the 1080p floor to answer a route, prompt or
model question. Nothing it makes ever ships. That is safe only if the refusal is MECHANICAL, so every
tool that files, exports or approves for delivery asks this module, and this module answers from the
file system alone:

  * a job is an evaluation when 00-brief/CHECKPOINT.md carries `Tier: evaluation` (a missing line is
    production — the floor is the default, never the exception);
  * a file is evaluation material when it sits under an `_eval/` folder, carries an `EVAL` token in
    its name, or belongs to an evaluation job.

Used by gate.py (approve lock/export refused, log-external), prompt_lint.py (the floor becomes a
WARN), pull_finals.py (files into _eval/ with EVAL in the name) and export_qc.py (refuses).

  python3 job_tier.py check <file-or-job-dir>     # prints the verdict; exit 1 = evaluation material
  python3 job_tier.py --selftest
"""
import argparse
import os
import re
import sys
import tempfile

TIERS = ("production", "evaluation")
EVAL_DIR = "_eval"
TIER_RE = re.compile(r"^Tier:\s*`?([A-Za-z-]+)", re.I | re.M)
# (v2.72.0) THE EVALUATION LANE. Opt-in: `Lane: eval` beside `Tier: evaluation`. An evaluation job without the line
# keeps the old behaviour (the script chain, the floor bent). In the lane ONE approved plan, `eval`, stands where the
# concept and the script stood (as `brief` does for Mode S), and the gate binds its shots, takes and budget per call.
LANE_RE = re.compile(r"^Lane:\s*`?([A-Za-z-]+)", re.I | re.M)
PLAN_FILE = os.path.join("00-brief", "EVAL-PLAN.md")
PLAN_REQUIRED = ("question", "shots", "takes per shot", "budget")
PLAN_WARNED = ("arms", "variable", "held fixed", "decision rule", "judging")
MAX_TAKES = 8
CK_KEYS = ("tier", "lane", "question", "budget", "policy", "mode", "format", "client")
_PLAN_LINE_RE = re.compile(r"^\s*[-*]?\s*\**([A-Za-z][A-Za-z ]{1,24}?)\**\s*:\s*(.*?)\s*$")
_PLACEHOLDER_RE = re.compile(r"<[^>]*>|\bTODO\b|\bTBD\b|^\s*$|^\.\.\.$", re.I)
_SHOT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
EVAL_TOKEN_RE = re.compile(r"(?:^|[_\-. ])EVAL(?:[_\-. ]|$)")


def job_root(path: str) -> str:
    """The folder holding 00-brief/CHECKPOINT.md, walking up from `path` (a file or a dir); '' if
    none is found within eight levels."""
    d = os.path.abspath(path)
    if os.path.isfile(d):
        d = os.path.dirname(d)
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "00-brief", "CHECKPOINT.md")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return ""


def declared_tier(root: str) -> str:
    """The checkpoint's `Tier:` value as written, lower-cased; '' when the line is absent."""
    cp = os.path.join(root, "00-brief", "CHECKPOINT.md") if root else ""
    if not cp or not os.path.isfile(cp):
        return ""
    try:
        m = TIER_RE.search(open(cp, encoding="utf-8", errors="ignore").read())
    except OSError:
        return ""
    return m.group(1).strip().lower() if m else ""


def tier(root: str) -> str:
    """'evaluation' or 'production'. Anything but an explicit evaluation is production."""
    return "evaluation" if declared_tier(root) == "evaluation" else "production"


def _checkpoint_text(root: str) -> str:
    cp = os.path.join(root, "00-brief", "CHECKPOINT.md") if root else ""
    try:
        return open(cp, encoding="utf-8", errors="ignore").read() if cp and os.path.isfile(cp) else ""
    except OSError:
        return ""


def lane(root: str) -> str:
    """'eval' when the checkpoint opts into the evaluation lane (`Lane: eval` with `Tier: evaluation`), else ''."""
    m = LANE_RE.search(_checkpoint_text(root))
    return "eval" if m and m.group(1).strip().lower() == "eval" and tier(root) == "evaluation" else ""


def parse_kv_lines(text: str) -> dict:
    """`Key: value` lines → {lower key: value}; the first occurrence wins."""
    out: dict = {}
    for ln in (text or "").splitlines():
        m = _PLAN_LINE_RE.match(ln)
        if m and m.group(1).strip().lower() not in out:
            out[m.group(1).strip().lower()] = m.group(2).strip().strip("`")
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\u201c", '"').replace("\u201d", '"')).strip().lower()


def plan_shots(text: str) -> list:
    """The shot IDs on the plan's `Shots:` line only (never a token found elsewhere in the plan)."""
    v = parse_kv_lines(text).get("shots", "")
    return [x.strip() for x in re.split(r"[,\s]+", v) if x.strip() and _SHOT_ID_RE.match(x.strip())]


def plan_numbers(text: str) -> dict:
    """{'takes': int|None, 'budget': float|None} from the plan."""
    kv = parse_kv_lines(text)
    tk = re.search(r"\d+", kv.get("takes per shot", ""))
    bd = re.search(r"\d+(?:\.\d+)?", kv.get("budget", ""))
    return {"takes": int(tk.group(0)) if tk else None, "budget": float(bd.group(0)) if bd else None}


def plan_problems(text: str, checkpoint_question: str, envelope) -> tuple:
    """(fails, warns) for 00-brief/EVAL-PLAN.md. Fails: the four lines a call is bound by; warns: the discipline lines."""
    kv = parse_kv_lines(text)
    fails, warns = [], []
    for k in PLAN_REQUIRED:
        if _PLACEHOLDER_RE.search(kv.get(k, "")):
            fails.append(f"`{k.capitalize()}:` is missing or a placeholder")
    if kv.get("question") and not _PLACEHOLDER_RE.search(kv["question"]) and \
            _norm(kv["question"]) != _norm(checkpoint_question):
        fails.append("`Question:` differs from the checkpoint's `Question:` — one question, written once, in both")
    if kv.get("shots") and not plan_shots(text):
        fails.append("`Shots:` names no valid shot ID (letters, digits, - and _, comma-separated)")
    n = plan_numbers(text)
    if kv.get("takes per shot") and (n["takes"] is None or not 1 <= n["takes"] <= MAX_TAKES):
        fails.append(f"`Takes per shot:` must be a number from 1 to {MAX_TAKES} — more is a production question")
    if kv.get("budget") and n["budget"] is None:
        fails.append("`Budget:` needs a credit figure (rate_card.py, or a get_cost probe)")
    elif n["budget"] is not None and envelope is not None and n["budget"] > float(envelope):
        fails.append(f"`Budget:` {n['budget']:g} cr is over the checkpoint envelope {float(envelope):g} cr")
    for k in PLAN_WARNED:
        if _PLACEHOLDER_RE.search(kv.get(k, "")):
            warns.append(f"`{k.capitalize()}:` is empty — the answer is easier to trust when it is written before the run")
    return fails, warns


def checkpoint_key_sha(text_or_fields) -> str:
    """A hash of the checkpoint lines an evaluation plan depends on — an unrelated edit does not change it. The gate
    passes ITS parsed fields (gate.parse_kv skips comments, quotes and fences), so a decoy line cannot split the hash
    from what the gate reads (build review 1, Sonnet); a text is parsed here for the self-test."""
    import hashlib
    kv = text_or_fields if isinstance(text_or_fields, dict) else parse_kv_lines(text_or_fields)
    return hashlib.sha256("\n".join(f"{k}={_norm(kv.get(k, ''))}" for k in CK_KEYS).encode()).hexdigest()[:16]


def ever_evaluated(root: str) -> bool:
    """True once the job has an `eval` approval row (append-only): it stays evaluation material whatever its
    checkpoint says later. A marker file could be deleted; the approval ledger is the record the gate trusts."""
    ap = os.path.join(root, "00-brief", "APPROVALS.md") if root else ""
    try:
        txt = open(ap, encoding="utf-8", errors="ignore").read() if ap and os.path.isfile(ap) else ""
    except OSError:
        return False
    return any(re.match(r"^\|[^|]*\|\s*eval\s*\|", ln) for ln in txt.splitlines())


def files_as_eval(root: str) -> bool:
    """Whether this job's media is evaluation material: the tier says so, or it ever ran in the lane."""
    return bool(root) and (tier(root) == "evaluation" or ever_evaluated(root))


def eval_marked(path: str) -> bool:
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    return EVAL_DIR in parts or bool(EVAL_TOKEN_RE.search(os.path.basename(path)))


def ship_refusal(path: str) -> str:
    """'' when the file may ship; otherwise the reason it may not."""
    if eval_marked(path):
        return (f"{os.path.basename(path)} is evaluation material (an `{EVAL_DIR}/` folder or an EVAL "
                f"name) — an evaluation answers a question, it never ships (references/ai-generation.md, "
                f"the evaluation tier)")
    root = job_root(path)
    if root and ever_evaluated(root) and tier(root) != "evaluation":
        return (f"{os.path.basename(path)} belongs to a job that ran in the evaluation lane (an `eval` approval in "
                f"its APPROVALS.md) — it stays evaluation material even with the tier line removed")
    if root and tier(root) == "evaluation":
        return (f"{os.path.basename(path)} belongs to an evaluation job (`Tier: evaluation` in "
                f"{os.path.relpath(os.path.join(root, '00-brief', 'CHECKPOINT.md'))}) — nothing an "
                f"evaluation makes is exported, upscaled into a deliverable or cut into one")
    return ""


def eval_name(filename: str) -> str:
    """S3_hands_kling_v1.mp4 → S3_hands_kling_EVAL_v1.mp4 (idempotent)."""
    if EVAL_TOKEN_RE.search(filename):
        return filename
    stem, ext = os.path.splitext(filename)
    m = re.match(r"^(.*?)(_v\d+)$", stem)
    return (f"{m.group(1)}_EVAL{m.group(2)}{ext}" if m else f"{stem}_EVAL{ext}")


def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    with tempfile.TemporaryDirectory() as td:
        prod = os.path.join(td, "prod"); ev = os.path.join(td, "ev")
        for j, extra in ((prod, ""), (ev, "Tier:       evaluation\n")):
            os.makedirs(os.path.join(j, "00-brief")); os.makedirs(os.path.join(j, "03-clips"))
            open(os.path.join(j, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\n" + extra)
        clip_p = os.path.join(prod, "03-clips", "S1_host_kling_v1.mp4"); open(clip_p, "w").write("x")
        clip_e = os.path.join(ev, "03-clips", "S1_host_kling_v1.mp4"); open(clip_e, "w").write("x")
        check("a checkpoint with no Tier: line is production", tier(prod) == "production")
        check("`Tier: evaluation` is evaluation", tier(ev) == "evaluation")
        check("the root is found from a file two levels down", job_root(clip_e) == os.path.abspath(ev))
        check("a production clip may ship", ship_refusal(clip_p) == "")
        check("any file of an evaluation job is refused", "evaluation job" in ship_refusal(clip_e))
        d = os.path.join(prod, "_eval", "03-clips"); os.makedirs(d)
        f = os.path.join(d, "S1_x_v1.mp4"); open(f, "w").write("x")
        check("an _eval/ file is refused even in a production job", "evaluation material" in ship_refusal(f))
        check("an EVAL name is refused", eval_marked("S1_host_kling_EVAL_v2.mp4"))
        check("a word that merely contains EVAL is not a token", not eval_marked("S1_MEDIEVAL_v1.mp4"))
        check("eval_name inserts the token before the version", eval_name("S1_h_k_v3.mp4") == "S1_h_k_EVAL_v3.mp4")
        check("eval_name is idempotent", eval_name("S1_h_k_EVAL_v3.mp4") == "S1_h_k_EVAL_v3.mp4")
        open(os.path.join(prod, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\nTier: production\n")
        check("an explicit production tier stays production", tier(prod) == "production")
        open(os.path.join(prod, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\nTier: eval-ish\n")
        check("an unknown tier word is production, never a quiet evaluation", tier(prod) == "production")
        # (v2.72.0) the lane is opt-in, the plan is parsed line by line, and an eval row sticks
        open(os.path.join(ev, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\nTier: evaluation\n")
        check("an evaluation job without `Lane: eval` is not in the lane (old behaviour kept)", lane(ev) == "")
        open(os.path.join(ev, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\nTier: evaluation\nLane: eval\n")
        check("`Lane: eval` with `Tier: evaluation` is the lane", lane(ev) == "eval")
        open(os.path.join(prod, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\nLane: eval\n")
        check("`Lane: eval` without the evaluation tier is not the lane", lane(prod) == "")
        q = "Does the tail help?"
        good = (f"Question: {q}\nShots: B2cA, B2cB\nTakes per shot: 4\nBudget: 80 cr\nArms: A full, B minus\n"
                f"Variable: the tail\nHeld fixed: model\nDecision rule: more usable wins twice\nJudging: blind\n")
        fl, wr = plan_problems(good, q, 100)
        check("a complete plan has no fails and no warns", not fl and not wr)
        check("Shots: parsed from its own line only", plan_shots(good + "Decision rule: not B2cC\n") == ["B2cA", "B2cB"])
        check("takes over 8 refused", any("1 to 8" in x for x in plan_problems(good.replace("4\n", "9\n", 1), q, 100)[0]))
        check("budget over the envelope refused", any("over the checkpoint envelope" in x for x in plan_problems(good, q, 50)[0]))
        check("a different question refused", any("differs" in x for x in plan_problems(good, "Another?", 100)[0]))
        check("a missing Shots: refused", any("Shots" in x for x in plan_problems(good.replace("Shots: B2cA, B2cB\n", ""), q, 100)[0]))
        _w = plan_problems(good.replace("Judging: blind\n", ""), q, 100)
        check("a missing Judging: only warns", not _w[0] and any("Judging" in x for x in _w[1]))
        check("the key-line hash ignores an unrelated line",
              checkpoint_key_sha("Tier: evaluation\nBudget: 80\n") == checkpoint_key_sha("Tier: evaluation\nBudget: 80\nNext: x\n"))
        check("the key-line hash sees a budget change",
              checkpoint_key_sha("Tier: evaluation\nBudget: 80\n") != checkpoint_key_sha("Tier: evaluation\nBudget: 800\n"))
        open(os.path.join(prod, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\n")
        open(os.path.join(prod, "00-brief", "APPROVALS.md"), "w").write(
            "| ts | stage | by | quote |\n|---|---|---|---|\n| 2026 | eval | o | run it now |\n")
        check("a job with an eval row is evaluation material even with no tier line",
              ever_evaluated(prod) and files_as_eval(prod) and "evaluation lane" in ship_refusal(clip_p))
    print("-" * 60)
    print("selftest OK — tier from the checkpoint (absent = production, unknown = production), the job "
          "root from a nested file, the ship refusal for an evaluation job, an _eval/ folder and an EVAL "
          "token, and the EVAL file name; the evaluation lane (opt-in, the plan's four bound lines, an eval row "
          "that sticks)" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="is this file or job evaluation material?")
    c.add_argument("path")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd != "check":
        ap.print_help(); return 2
    p = os.path.abspath(os.path.expanduser(a.path))
    if os.path.isdir(p) and os.path.isfile(os.path.join(p, "00-brief", "CHECKPOINT.md")):
        t = tier(p)
        print(f"job {p}: tier {t}")
        return 1 if t == "evaluation" else 0
    why = ship_refusal(p)
    print(why or f"{p}: production — may ship")
    return 1 if why else 0


if __name__ == "__main__":
    sys.exit(main())
