#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""shell_gate.py — a shell command that draws on-screen text outside Resolve is stopped before it runs.

Author, 2026-10-27: *"There is one more issue, Claude keeps insisting in creating mp4s of captions etc outside
resolve, it should defrult to Resolve or Fusion native elements. Not create outside for no reason."* (house rule
C7). The docs said Resolve first and the shell still reached for ffmpeg, so this is the PreToolUse hook on `Bash` and
on the linked computer's `device_bash` (hooks/hooks.json). It stops:

  · ffmpeg drawing text into a VIDEO file (a `subtitles=`, `ass=` or `drawtext=` filter) anywhere but 09-qa/ —
    captions are made in Resolve; a burn with a reason goes through `build_captions.py --reason …`, which records it;
  · HyperFrames (`title.mjs`) or supers-gsap (`render.mjs`) on a spec whose `engine` is not theirs, or has no
    recorded `engine_reason` (native.py's four: batch, derivative, remux, owner).
A still or a contact sheet (an image output) passes, and so does a review copy in 09-qa/ (a timecode burn for notes).
A spec this machine cannot read (a command for the linked computer) is asked about, not guessed.

It FAILS OPEN: a crash here lets the command run, because it guards a default, not a spend (gate.py fails closed
for spend). What it cannot see: text drawn by a script it does not name, or ffmpeg called from inside Python —
`approve export` catches those by the file (native.py check: a container ffmpeg made, with no record).

  hook          read the PreToolUse JSON on stdin; print a decision only when it has one
  --selftest
"""
from __future__ import annotations
import json, os, re, shlex, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_EXT = (".mp4", ".mov", ".mxf", ".m4v", ".webm", ".mkv", ".avi")
TEXT_FILTER = re.compile(r"\b(subtitles|ass|drawtext)\s*=")
QUICK = re.compile(r"ffmpeg|title\.mjs|render\.mjs|hyperframes|python")
# ⛔ v2.45 (2026-10-29, the author: "It keeps making mp4s which it imports"): the two outside routes this gate missed —
# the HyperFrames CLI itself, and a Python script that draws text and writes a video (a supplement ad job's card labels, pop
# captions and badge: make_gfx_v4.py, build_pop.py, make_plates_close.py)
HF_CLI_RE = re.compile(r"(?:^|[\s/])(?:npx\s+(?:-y\s+)?)?hyperframes(?:@[\w.^~-]+)?\s+(render|snapshot)\b")
PY_RUN_RE = re.compile(r"(?:^|[\s;&|])python(?:3(?:\.\d+)?)?\s+(?:-[A-Za-z]+\s+)*([^\s;|&]+\.py)\b")
DRAWS_TEXT_RE = re.compile(r"ImageDraw\.Draw|\.text\s*\(|ImageFont\.truetype|cv2\.putText|drawtext=")
WRITES_VIDEO_RE = re.compile(r"-c:v|libx264|prores|qtrle|rawvideo|VideoWriter|\.mov[\"']|\.mp4[\"']|\.mxf[\"']")
SPLIT = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")
RULING = "house rule C7, 2026-10-27"
NATIVE = ("captions: native.py console <job> --srt 08-captions/<slug>.srt → resolve-production-console PLACE_SUBTITLES "
          "→ render-mp4.py BURN_SUBTITLES = True → srt_qa.py burned; titles: native.py console <job> → PLACE_TITLES → "
          "title_qa.py native")


def _tokens(seg: str) -> list:
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


def _ffmpeg(seg: str) -> str | None:
    """A reason to stop this ffmpeg segment, or None."""
    if not re.search(r"(^|[\s/])ffmpeg(\s|$)", seg) or not TEXT_FILTER.search(seg):
        return None
    t = _tokens(seg)
    outs = [x for i, x in enumerate(t) if x.lower().endswith(VIDEO_EXT) and (i == 0 or t[i - 1] != "-i")]
    bad = [o for o in outs if "09-qa/" not in o.replace("\\", "/")]
    if not bad:
        return None
    return (f"REFUSED ({RULING}: \"it should defrult to Resolve or Fusion native elements. Not create outside for no "
            f"reason\"): this ffmpeg command draws text (subtitles=/ass=/drawtext=) into {', '.join(bad)} outside Resolve. "
            f"The native route — {NATIVE}. With a reason (native.py reasons: batch, derivative, remux, owner), burn "
            f"captions through build_captions.py --reason … --why \"…\", which records it. A review copy goes in 09-qa/.")


def _spec_path(seg: str, cwd: str, cds: list) -> tuple:
    t = _tokens(seg)
    sp = next((t[i + 1] for i, x in enumerate(t[:-1]) if x == "--spec"), None)
    if not sp:
        return None, None
    tries = [sp] if os.path.isabs(sp) else [os.path.join(cwd, *cds, sp), os.path.join(cwd, sp)]
    return sp, next((p for p in tries if os.path.isfile(p)), None)


def _lane(seg: str, cwd: str, cds: list) -> tuple:
    """(decision, reason) for a HyperFrames or supers-gsap render, or (None, None)."""
    if re.search(r"(^|[\s/])title\.mjs(\s|$)", seg):
        lane, eng = "HyperFrames (assets/titles-hyperframes/title.mjs)", "hyperframes"
    elif re.search(r"(^|[\s/])render\.mjs(\s|$)", seg) and ("supers-gsap" in seg or any("supers-gsap" in c for c in cds)
                                                              or "supers-gsap" in cwd):
        lane, eng = "supers-gsap (assets/supers-gsap/render.mjs)", "gsap"
    else:
        return None, None
    sp, path = _spec_path(seg, cwd, cds)
    if not sp:
        return None, None                                  # no spec: --help, a test harness — nothing to check
    if not path:
        return "ask", (f"{lane} renders a title outside Resolve ({RULING}). The spec {sp} cannot be read from here to "
                       f"check its engine — it must say \"engine\": \"{eng}\" with an \"engine_reason\" (native.py "
                       f"reasons). Allow only if it does.")
    try:
        spec = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return "ask", f"{lane}: the spec {sp} does not parse — its engine cannot be checked"
    have = str(spec.get("engine") or "resolve").strip().lower()
    if have != eng:
        return "deny", (f"REFUSED ({RULING}: \"it should defrult to Resolve or Fusion native elements. Not create "
                        f"outside for no reason\"): {sp} is a {have} title, so it is made in Resolve, not rendered by "
                        f"{lane}. The native route — {NATIVE}. To render it here, the spec needs \"engine\": \"{eng}\" "
                        f"and an \"engine_reason\" (native.py reasons — the owner's words for a look Fusion can't do).")
    sys.path.insert(0, HERE)
    import native
    why = native.check_reason(spec.get("engine_reason"), sp)
    if why:
        return "deny", f"REFUSED ({RULING}): {lane} on {sp} — " + "; ".join(why)
    return None, None


def _hf_cli(seg: str, cwd: str, cds: list) -> tuple:
    """(decision, reason) for the HyperFrames CLI: a render or snapshot is an outside title unless it writes only into
    09-qa/ (a review still) or names a spec whose engine is hyperframes with a recorded reason (the title.mjs rule)."""
    m = HF_CLI_RE.search(seg)
    if not m:
        return None, None
    outs = [t for t in _tokens(seg) if t.lower().endswith(VIDEO_EXT + (".png", ".jpg"))]
    if outs and all("09-qa" in o for o in outs):
        return None, None                                  # a review still or copy in 09-qa/
    specs_ = [t for t in _tokens(seg) if t.endswith(".title.json")]
    if not specs_:
        return "deny", (f"REFUSED ({RULING}; v2.45: \"It keeps making mp4s which it imports\") — `hyperframes {m.group(1)}` "
                        f"renders a title outside Resolve and names no title spec. Titles are made in Resolve: {NATIVE}. "
                        f"A look Fusion cannot make is the owner's call: their words as the spec's engine_reason, then "
                        f"title.mjs --spec <it>.")
    sp = specs_[0]
    tries = [sp] if os.path.isabs(sp) else [os.path.join(cwd, *cds, sp), os.path.join(cwd, sp)]
    path = next((p for p in tries if os.path.isfile(p)), None)
    if not path:
        return "ask", f"hyperframes {m.group(1)} on {sp}, which cannot be read from here — it must name engine hyperframes and a reason"
    try:
        spec = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return "ask", f"hyperframes: the spec {sp} does not parse — its engine cannot be checked"
    if str(spec.get("engine") or "resolve").strip().lower() != "hyperframes":
        return "deny", f"REFUSED ({RULING}): {sp} is made in Resolve (no outside engine) — {NATIVE}"
    sys.path.insert(0, HERE)
    import native
    why = native.check_reason(spec.get("engine_reason"), sp)
    return ("deny", f"REFUSED ({RULING}): hyperframes on {sp} — " + "; ".join(why)) if why else (None, None)


def _py_text_video(seg: str, cwd: str, cds: list) -> tuple:
    """(decision, reason) for `python3 <file>.py` whose source draws text AND writes a video outside 09-qa/. The plugin's
    own scripts are exempt (contact sheets, strips and build_captions.py carry their own rules); it fails open on a file
    it cannot read."""
    for f in PY_RUN_RE.findall(seg):
        p = f if os.path.isabs(f) else os.path.join(cwd, *cds, f)
        if not os.path.isfile(p):
            p = f if os.path.isabs(f) else os.path.join(cwd, f)
        if os.path.realpath(p).startswith(os.path.realpath(HERE) + os.sep):
            continue
        try:
            src = open(p, encoding="utf-8", errors="replace").read(512 * 1024)
        except OSError:
            continue                                       # fail open
        if not (DRAWS_TEXT_RE.search(src) and WRITES_VIDEO_RE.search(src)):
            continue
        outs = re.findall(r"[\"']([^\"'\n]+\.(?:mov|mp4|mxf|webm|m4v))[\"']", src)
        if outs and all("09-qa" in o for o in outs):
            continue
        return "deny", (f"REFUSED ({RULING}: \"it should defrult to Resolve or Fusion native elements. Not create outside "
                        f"for no reason\"; v2.45) — {f} draws text and writes a video. Titles, card labels and captions are "
                        f"made in Resolve: {NATIVE}. A plate with no words is fine (draw the words in Resolve); with the "
                        f"owner's reason, `native.py record` the output.")
    return None, None


def decide(data: dict) -> tuple:
    """(decision, reason): decision None means say nothing."""
    ti = data.get("tool_input") or {}
    cmd = str(ti.get("command") or ti.get("cmd") or "")
    if not cmd or not QUICK.search(cmd):
        return None, None
    cwd = str(data.get("cwd") or os.getcwd())
    cds = []
    asks = []
    for seg in SPLIT.split(cmd):
        m = re.match(r"^\s*cd\s+(\S+)\s*$", seg)
        if m:
            cds.append(m.group(1).strip("'\""))
            continue
        r = _ffmpeg(seg)
        if r:
            return "deny", r
        d, r = _lane(seg, cwd, cds)
        if d == "deny":
            return d, r
        if d == "ask":
            asks.append(r)
        for fn in (_hf_cli, _py_text_video):
            d, r = fn(seg, cwd, cds)
            if d == "deny":
                return d, r
            if d == "ask":
                asks.append(r)
    return ("ask", " · ".join(asks)) if asks else (None, None)


def cmd_hook() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        d, r = decide(data if isinstance(data, dict) else {})
    except Exception:  # noqa: BLE001 — fail OPEN: this guards a default, not a spend
        return 0
    if d:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": d,
                                                 "permissionDecisionReason": r}}, ensure_ascii=False))
    return 0


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and bool(cond)
    with tempfile.TemporaryDirectory() as td:
        def D(cmd, tool="Bash"):
            return decide({"tool_name": tool, "tool_input": {"command": cmd}, "cwd": td})
        d, r = D('ffmpeg -y -i 10-export/fx-master.mp4 -vf "subtitles=08-captions/fx.srt" 10-export/fx-final_9x16.mp4')
        check("ffmpeg burning an .srt into a delivery file → deny, naming the native route and build_captions --reason",
              d == "deny" and "PLACE_SUBTITLES" in r and "build_captions.py --reason" in r, (d, r))
        d, _ = D("cd job && ffmpeg -i cut.mp4 -vf \"drawtext=text='SALE':fontsize=90\" -c:a copy out.mov",
                 "mcp__remote-devices__device_bash")
        check("…drawtext into a .mov through the linked computer's shell → deny", d == "deny", d)
        d, _ = D("ffmpeg -i cut.mp4 -vf \"drawtext=text='%{pts\\:hms}'\" 09-qa/review/fx-v3-tc.mp4")
        check("a timecode burn for a review copy in 09-qa/ passes", d is None, d)
        d, _ = D("ffmpeg -i cut.mp4 -vf \"fps=1,drawtext=text='%{n}',tile=4x3\" -frames:v 1 09-qa/sheet.png")
        check("a labelled contact sheet (an image) passes", d is None, d)
        d, _ = D("ffmpeg -i a.mp4 -c copy -movflags +faststart b.mp4 && ls -la")
        check("ffmpeg with no text filter passes", d is None, d)
        d, _ = D("python3 scripts/build_captions.py --srt a.srt --format vertical-1080 --burn m.mp4 -o f.mp4 --reason batch --why x")
        check("build_captions.py passes here (it refuses without a reason and records one with it)", d is None, d)
        d, _ = D("git status")
        check("an unrelated command says nothing", d is None, d)
        os.makedirs(os.path.join(td, "t"))
        sp = os.path.join(td, "t", "T1.title.json")
        json.dump({"id": "T1", "kind": "hero", "content": {"lines": ["x"]}}, open(sp, "w"))
        d, r = D(f"node assets/titles-hyperframes/title.mjs --card c.json --spec {sp} --format vertical-1080 --out T1.mov")
        check("HyperFrames on a spec with no engine (so resolve) → deny, naming the native route", d == "deny" and "PLACE_TITLES" in r, (d, r))
        json.dump({"id": "T1", "kind": "hero", "engine": "hyperframes", "content": {"lines": ["x"]}}, open(sp, "w"))
        d, r = D(f"cd assets/titles-hyperframes && node title.mjs --spec {sp} --out T1.mov")
        check("…engine hyperframes with no reason → deny", d == "deny" and "no reason" in r, (d, r))
        json.dump({"id": "T1", "kind": "hero", "engine": "hyperframes", "content": {"lines": ["x"]},
                   "engine_reason": {"code": "owner", "why": "the kinetic kit for the launch film", "quote": "use the HyperFrames kit"}},
                  open(sp, "w"))
        d, _ = D(f"node title.mjs --spec t/T1.title.json --out T1.mov")
        check("…with the owner's words it passes (the spec found relative to the working folder)", d is None, d)
        d, r = D("cd assets/supers-gsap && node render.mjs --spec /nowhere/super.json --out s")
        check("supers-gsap on a spec this machine cannot read → ask, saying what to check", d == "ask" and "engine_reason" in r, (d, r))
        import subprocess
        pr = subprocess.run([sys.executable, os.path.abspath(__file__), "hook"], input="{not json", capture_output=True, text=True)
        check("a hook input it cannot read fails open: exit 0, no decision", pr.returncode == 0 and not pr.stdout.strip(), pr)
        pr = subprocess.run([sys.executable, os.path.abspath(__file__), "hook"], capture_output=True, text=True,
                            input=json.dumps({"tool_name": "Bash", "cwd": td, "tool_input": {
                                "command": "ffmpeg -i m.mp4 -vf ass=a.ass out.mp4"}}))
        h = (json.loads(pr.stdout or "{}").get("hookSpecificOutput") or {})
        check("the hook prints a PreToolUse deny for a burn", h.get("permissionDecision") == "deny", pr.stdout)
    print("-" * 60)
    print("selftest OK — ffmpeg text into a video outside 09-qa/ is refused; images, review copies and plain remuxes pass; "
          "HyperFrames and supers-gsap run only on a spec that names their engine with a reason" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    a = sys.argv[1:]
    if a[:1] == ["--selftest"]:
        return selftest()
    if a[:1] == ["hook"]:
        return cmd_hook()
    print(__doc__)
    return 0 if a[:1] in (["--help"], ["-h"]) else 2


if __name__ == "__main__":
    sys.exit(main())
