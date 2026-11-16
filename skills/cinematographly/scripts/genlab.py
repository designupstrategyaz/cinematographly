#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""genlab.py — the take log, a blind A/B harness for prompt styles, and a drift-pairs runner (v2.70.0, Wave 5 A11, B1, B2).

Nothing here spends. It prepares and scores tests whose generations a person approves and runs (the gate still
gates every call); it works for any project that calls a generative model, not only this plugin.

Why: no study measures whether a prompt's length, its blocks or its wording make better takes (research note R4).
The only honest way to know is one change at a time, on one approved frame, judged blind, with raw counts. And a good
take must be reproducible, so every take is logged with what made it.

  genlab.py log add <log.jsonl> --arm A --model M --prompt FILE [--seed N] [--settings JSON] [--credits N] [--take FILE]
  genlab.py log show <log.jsonl>
      One row per take: arm, model, the prompt's sha256, seed and settings, credits, the take file, and `usable`
      left blank for the judge.
  genlab.py ab make <prompt.md> <outdir> --arms full,short | full,minus:SUPPRESS [--takes 4] [--credits-per-take N]
      Writes one prompt file per arm (ONE change per run: two arms), the plan, and the cost line (credits × takes ×
      arms, spends nothing). `short` keeps each [BLOCK]'s first sentence; `minus:NAME` drops the [NAME] block.
  genlab.py ab sheet <log.jsonl> <sheet.md>       a blind sheet: takes shuffled, arms hidden (the key sits beside it)
  genlab.py ab score <sheet.md>                    usable counts per arm, raw; no significance below 20 per arm
  genlab.py drift check <pairs.csv>                validate a pairs file: still, take, label (held|drifted), lens, light, wardrobe
  genlab.py drift run <pairs.csv> [--metric module:function] [--at first|middle|last]
      Runs a metric on every pair (default: look_qa.first_frame_match) and prints it by label — no threshold is set
      here; a studio learns one on a different set from the one it scores.
  genlab.py --selftest
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, random, re, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
BLOCK_RE = re.compile(r"^\[([A-Z][A-Z0-9 _-]*)\]\s*$", re.M)
MIN_FOR_STATS = 20          # below this many takes per arm, counts are reported raw and only a large gap means anything


def sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# ---------------------------------------------------------------------------------------------- the take log (A11)
def log_add(log: str, arm: str, model: str, prompt: str, seed=None, settings=None, credits=None, take=None) -> dict:
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arm": arm, "model": model,
           "prompt": os.path.basename(prompt), "prompt_sha256": sha(prompt), "seed": seed,
           "settings": settings or {}, "credits": credits, "take": take, "usable": None, "judge": None}
    os.makedirs(os.path.dirname(os.path.abspath(log)), exist_ok=True)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def log_rows(log: str) -> list:
    return [json.loads(l) for l in open(log, encoding="utf-8") if l.strip()] if os.path.isfile(log) else []


# ---------------------------------------------------------------------------------------------- A/B (B2)
def blocks(text: str) -> list:
    """[(name, start, end)] of each [BLOCK] section in a prompt body."""
    ms = list(BLOCK_RE.finditer(text))
    return [(m.group(1).strip(), m.start(), ms[i + 1].start() if i + 1 < len(ms) else len(text)) for i, m in enumerate(ms)]


def variant(text: str, arm: str) -> str:
    if arm == "full":
        return text
    bl = blocks(text)
    if not bl:
        raise SystemExit("the prompt has no [BLOCK] sections: `short` and `minus:` need them")
    if arm == "short":
        out = text[: bl[0][1]]
        for name, a, b in bl:
            body = text[a:b].split("\n", 1)[1] if "\n" in text[a:b] else ""
            first = re.split(r"(?<=[.!?])\s", body.strip(), maxsplit=1)[0] if body.strip() else ""
            out += f"[{name}]\n{first}\n\n"
        return out
    if arm.startswith("minus:"):
        drop = arm.split(":", 1)[1].strip().upper()
        hit = [x for x in bl if x[0].upper() == drop]
        if not hit:
            raise SystemExit(f"no [{drop}] block in the prompt (it has: {', '.join(n for n, _, _ in bl)})")
        _, a, b = hit[0]
        return text[:a] + text[b:]
    raise SystemExit(f"unknown arm {arm!r}: full, short or minus:<BLOCK>")


def required_blocks(text: str) -> list:
    """The blocks the pipeline's own lint requires for this prompt's form, when the lint is available (this plugin's
    prompt_lint.py); an arm may never drop one, or the gate would refuse it (build review 1, Sonnet)."""
    try:
        import prompt_lint as PL
    except ImportError:
        return []
    fm = re.search(r"^form:\s*(\w+)", text, re.M)
    kind = re.search(r"^kind:\s*(\w+)", text, re.M)
    form = fm.group(1).lower() if fm else ""
    if form == "scene":
        return list(PL.SCENE_REQUIRED)
    if form == "multishot":
        return list(PL.MULTISHOT_REQUIRED)
    return list(PL.FRAME_REQUIRED if (kind and kind.group(1) == "frame") else PL.CLIP_REQUIRED)


def ab_make(prompt: str, outdir: str, arms: list, takes: int = 4, credits_per_take=None, job_root=None) -> dict:
    if len(arms) != 2:
        raise SystemExit("one change per run: exactly two arms (e.g. full,short or full,minus:SUPPRESS)")
    text = open(prompt, encoding="utf-8").read()
    req = {b.upper() for b in required_blocks(text)}
    for arm in arms:
        if arm.startswith("minus:") and arm.split(":", 1)[1].strip().upper() in req:
            raise SystemExit(f"{arm}: [{arm.split(':', 1)[1].strip().upper()}] is a required block for this prompt's form; "
                             f"the lint would refuse the arm, so the gate would never send it. Drop an optional block")
    os.makedirs(outdir, exist_ok=True)
    files = {}
    stem = os.path.splitext(os.path.basename(prompt))[0]
    for arm in arms:
        p = os.path.join(outdir, f"{stem}.{arm.replace(':', '-')}.md")
        open(p, "w", encoding="utf-8").write(variant(text, arm))
        files[arm] = p
    lint = {}
    try:                                    # lint each arm the way the gate will, and say what it found
        import prompt_lint as PL
        for arm, p in files.items():
            r = PL.lint(p, job_root)
            lint[arm] = {"ok": r.get("ok"), "fails": (r.get("fails") or [])[:3]}
    except Exception as e:                  # noqa: BLE001 — no lint here (another project): say so
        lint = {"note": f"not linted ({type(e).__name__}): lint each arm before spending"}
    n = takes * len(arms)
    cost = None if credits_per_take is None else round(float(credits_per_take) * n, 2)
    plan = {"prompt": prompt, "arms": files, "lint": lint, "takes_per_arm": takes, "generations": n, "credits": cost,
            "note": (f"{n} generations; {takes} per arm shows only a large gap (e.g. 4 of 4 against 1 of 4). A house "
                     f"rule waits until the same arm wins a second run. Nothing is spent by this tool: each generation "
                     f"goes through the gate, after the owner's yes on this cost")}
    json.dump(plan, open(os.path.join(outdir, "ab-plan.json"), "w"), indent=1)
    return plan


def ab_sheet(log: str, sheet: str, seed: int = 11) -> dict:
    rows = [r for r in log_rows(log) if r.get("take")]
    rng = random.Random(seed)
    order = list(range(len(rows)))
    rng.shuffle(order)
    key, lines = {}, ["# Which takes are usable?", "", "Tick each take you would use: `- [x]`. The order is shuffled and "
                      "nothing says how a take was made.", ""]
    links = os.path.splitext(sheet)[0] + "_takes"         # neutral names: a file name can give the arm away
    os.makedirs(links, exist_ok=True)
    for k, i in enumerate(order, 1):
        lab = f"T{k:02d}"
        key[lab] = {"arm": rows[i]["arm"], "take": rows[i]["take"]}
        ln = os.path.join(links, lab + os.path.splitext(rows[i]["take"])[1])
        if os.path.lexists(ln):
            os.remove(ln)
        try:                       # a hard link (or a copy) has no target name to read back (build review 1, Grok)
            os.link(rows[i]["take"], ln)
        except OSError:
            shutil.copyfile(rows[i]["take"], ln)
        lines.append(f"- [ ] {lab} · `{os.path.relpath(ln, os.path.dirname(os.path.abspath(sheet)))}`")
    open(sheet, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(key, open(sheet + ".key.json", "w"), indent=1)
    return {"sheet": sheet, "takes": len(key)}


def ab_score(sheet: str) -> dict:
    key = json.load(open(sheet + ".key.json", encoding="utf-8"))
    kept = set(re.findall(r"^- \[[xX]\] (\S+)", open(sheet, encoding="utf-8").read(), re.M))
    out = {}
    for lab, v in key.items():
        a = out.setdefault(v["arm"], {"takes": 0, "usable": 0})
        a["takes"] += 1
        a["usable"] += lab in kept
    small = any(v["takes"] < MIN_FOR_STATS for v in out.values())
    out["_note"] = ("raw counts; fewer than %d takes per arm: only a large gap means anything, and no house rule until "
                    "the same arm wins a second run" % MIN_FOR_STATS) if small else "raw counts"
    return out


# ---------------------------------------------------------------------------------------------- drift pairs (B1)
PAIR_COLS = ("still", "take", "label", "lens", "light", "wardrobe")


def drift_check(pairs: str) -> list:
    P = []
    rows = list(csv.DictReader(open(pairs, encoding="utf-8")))
    base = os.path.dirname(os.path.abspath(pairs))
    if not rows:
        return ["no rows"]
    miss = [c for c in PAIR_COLS if c not in rows[0]]
    if miss:
        return [f"missing column(s): {', '.join(miss)} — lens, light and wardrobe tell colour drift from a grade change"]
    for i, r in enumerate(rows, 2):
        if r["label"] not in ("held", "drifted"):
            P.append(f"line {i}: label {r['label']!r} is not held or drifted")
        for c in ("still", "take"):
            if not os.path.isfile(os.path.join(base, r[c])):
                P.append(f"line {i}: {c} {r[c]!r} is not on disk")
        for c in ("lens", "light", "wardrobe"):
            if not (r.get(c) or "").strip():
                P.append(f"line {i}: {c} is blank — it is what tells drift from a grade change")
    return P


def _metric(spec: str):
    mod, fn = spec.split(":", 1)
    return getattr(__import__(mod), fn)


AT_FRAMES = ("first", "middle", "last")


def _pick_frame(frames: list, at: str = "first"):
    """(v2.71.0) Which frame of a take the metric sees. `first` measures the start (on a frame-led model it is nearly the
    still itself); drift happens later, so `middle` and `last` exist. B1 found the first frame alone cannot show it."""
    if not frames:
        return None
    if at not in AT_FRAMES:
        raise SystemExit(f"--at {at!r}: one of {', '.join(AT_FRAMES)}")
    return frames[{"first": 0, "middle": len(frames) // 2, "last": -1}[at]][1]


def drift_run(pairs: str, metric: str = "look_qa:first_frame_match", at: str = "first") -> dict:
    P = drift_check(pairs)
    if P:
        raise SystemExit("pairs file problems:\n  " + "\n  ".join(P))
    import look_qa as LQ
    f = _metric(metric)
    base = os.path.dirname(os.path.abspath(pairs))
    by = {"held": [], "drifted": []}
    for r in csv.DictReader(open(pairs, encoding="utf-8")):
        still = LQ._read_still(os.path.join(base, r["still"]))
        tk = os.path.join(base, r["take"])
        frame = LQ._read_still(tk) if tk.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) else \
            _pick_frame(LQ.rgb_frames(tk, 8.0, 240), at)
        by[r["label"]].append({"take": r["take"], **(f(still, frame) or {})})
    return {"metric": metric, "at": at, "pairs": by,
            "note": "no threshold is set here: learn one on a different labelled set from the one you score. A layout "
                    "metric on the last frame mostly measures the camera move, not identity"}


# ---------------------------------------------------------------------------------------------- selftest
def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        pr = os.path.join(td, "S1.clip.prompt.md")
        open(pr, "w").write("---\nshot: S1\n---\n[SUBJECT]\nAna, 34. She looks up. Then she smiles.\n\n"
                            "[CAMERA]\nA slow push in. It stops at MCU.\n\n[SUPPRESS]\nextra fingers, warped hands\n")
        assert variant(open(pr).read(), "full") == open(pr).read()
        sh = variant(open(pr).read(), "short")
        assert "She looks up" not in sh and "Ana, 34." in sh and "A slow push in." in sh and "It stops" not in sh, sh
        mn = variant(open(pr).read(), "minus:SUPPRESS")
        assert "[SUPPRESS]" not in mn and "[CAMERA]" in mn, mn
        try:
            ab_make(pr, os.path.join(td, "ab"), ["full", "short", "minus:CAMERA"])
            raise AssertionError("three arms must be refused: one change per run")
        except SystemExit as e:
            assert "one change per run" in str(e)
        try:
            ab_make(pr, os.path.join(td, "ab"), ["full", "minus:CAMERA"])
            raise AssertionError("dropping a required block must be refused")
        except SystemExit as e:
            assert "required block" in str(e), e
        plan = ab_make(pr, os.path.join(td, "ab"), ["full", "short"], 4, 12)
        assert set(plan["lint"]) == {"full", "short"} or "note" in plan["lint"], plan["lint"]
        assert plan["generations"] == 8 and plan["credits"] == 96 and "Nothing is spent" in plan["note"], plan
        lg = os.path.join(td, "takes.jsonl")
        for arm in ("full", "short"):
            for k in range(4):
                tk = os.path.join(td, f"{arm}{k}.mp4"); open(tk, "wb").write(b"x")
                r = log_add(lg, arm, "kling3_0", plan["arms"][arm], seed=k, settings={"duration": 5}, credits=12, take=tk)
        assert len(log_rows(lg)) == 8 and r["usable"] is None and len(r["prompt_sha256"]) == 64
        sp = os.path.join(td, "blind.md")
        ab_sheet(lg, sp)
        txt = open(sp).read()
        assert "full" not in txt.split("\n", 3)[3] and "short" not in txt.split("\n", 3)[3], txt
        key = json.load(open(sp + ".key.json"))
        tk_dir = os.path.join(td, "blind_takes")
        assert not any(os.path.islink(os.path.join(tk_dir, f)) for f in os.listdir(tk_dir)), "a symlink names its target"
        full_labs = [l for l, v in key.items() if v["arm"] == "full"]
        for l in full_labs:
            txt = txt.replace(f"- [ ] {l} ", f"- [x] {l} ")
        open(sp, "w").write(txt)
        sc = ab_score(sp)
        assert sc["full"] == {"takes": 4, "usable": 4} and sc["short"]["usable"] == 0 and "large gap" in sc["_note"], sc
        # drift pairs: the columns that tell drift from a grade are required
        pc = os.path.join(td, "pairs.csv")
        open(pc, "w").write("still,take,label\na.png,b.png,held\n")
        assert any("lens, light and wardrobe" in p for p in drift_check(pc))
        open(pc, "w").write("still,take,label,lens,light,wardrobe\na.png,b.png,held,,,\n")
        assert any("is blank" in p for p in drift_check(pc))
        try:
            import numpy as np
            import look_qa as LQ, shot_graph as SG
            _, cv2 = SG._need()
            rng = np.random.default_rng(3)
            img = (rng.random((180, 320, 3)) * 255).astype(np.uint8)
            img = cv2.GaussianBlur(img, (0, 0), 6)
            cv2.imwrite(os.path.join(td, "still.png"), img)
            cv2.imwrite(os.path.join(td, "held.png"), img)
            cv2.imwrite(os.path.join(td, "drift.png"), np.roll(img, 90, axis=1))
            open(pc, "w").write("still,take,label,lens,light,wardrobe\nstill.png,held.png,held,35mm,day,coat\n"
                                "still.png,drift.png,drifted,35mm,day,coat\n")
            assert drift_check(pc) == []
            dr = drift_run(pc)
            fr_ = [(0, "a"), (1, "b"), (2, "c"), (3, "d")]
            assert (_pick_frame(fr_, "first"), _pick_frame(fr_, "middle"), _pick_frame(fr_, "last")) == ("a", "c", "d")
            assert _pick_frame([], "last") is None and dr.get("at") == "first"
            assert dr["pairs"]["held"][0]["luma_corr"] > dr["pairs"]["drifted"][0]["luma_corr"], dr
        except ImportError:
            print("  (drift run skipped: numpy or OpenCV missing)")
    print("selftest OK — arms: full, short (first sentence per block), minus one block; exactly two arms per run; the "
          "cost line counts takes × arms and spends nothing; the take log keeps the prompt hash, seed and settings; "
          "the blind sheet hides the arms and the score gives raw counts with the small-sample note; a pairs file needs "
          "lens, light and wardrobe, and the drift runner scores pairs by label with no threshold")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    lg = sub.add_parser("log"); lsub = lg.add_subparsers(dest="act")
    la = lsub.add_parser("add"); la.add_argument("log"); la.add_argument("--arm", required=True)
    la.add_argument("--model", required=True); la.add_argument("--prompt", required=True); la.add_argument("--seed")
    la.add_argument("--settings", default="{}"); la.add_argument("--credits", type=float); la.add_argument("--take")
    ls = lsub.add_parser("show"); ls.add_argument("log")
    ab = sub.add_parser("ab"); asub = ab.add_subparsers(dest="act")
    am = asub.add_parser("make"); am.add_argument("prompt"); am.add_argument("outdir"); am.add_argument("--arms", required=True)
    am.add_argument("--takes", type=int, default=4); am.add_argument("--credits-per-take", type=float)
    ash = asub.add_parser("sheet"); ash.add_argument("log"); ash.add_argument("sheet")
    asc = asub.add_parser("score"); asc.add_argument("sheet")
    dr = sub.add_parser("drift"); dsub = dr.add_subparsers(dest="act")
    dc = dsub.add_parser("check"); dc.add_argument("pairs")
    drr = dsub.add_parser("run"); drr.add_argument("pairs"); drr.add_argument("--metric", default="look_qa:first_frame_match")
    drr.add_argument("--at", default="first", choices=AT_FRAMES, help="which frame of the take the metric sees")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "log" and a.act == "add":
        print(json.dumps(log_add(a.log, a.arm, a.model, a.prompt, a.seed, json.loads(a.settings), a.credits, a.take)))
    elif a.cmd == "log" and a.act == "show":
        for r in log_rows(a.log):
            print(json.dumps(r, ensure_ascii=False))
    elif a.cmd == "ab" and a.act == "make":
        print(json.dumps(ab_make(a.prompt, a.outdir, [x.strip() for x in a.arms.split(",")], a.takes, a.credits_per_take), indent=1))
    elif a.cmd == "ab" and a.act == "sheet":
        print(json.dumps(ab_sheet(a.log, a.sheet)))
    elif a.cmd == "ab" and a.act == "score":
        print(json.dumps(ab_score(a.sheet), indent=1))
    elif a.cmd == "drift" and a.act == "check":
        P = drift_check(a.pairs)
        print("\n".join(P) or "pairs file OK")
        return 1 if P else 0
    elif a.cmd == "drift" and a.act == "run":
        print(json.dumps(drift_run(a.pairs, a.metric, a.at), indent=1))
    else:
        ap.print_help(); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
