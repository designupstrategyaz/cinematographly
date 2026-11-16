#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""test_gate.py — the gate's own evidence. Walks a job from an empty folder to an allowed clip
generation and asserts every refusal on the way. Doubles as the executable half of evals/ (the
README there asks for exactly these cases: routing refuses without a profile, hard locks refuse,
the quality floor holds, evidence gates refuse a bare verdict).

Run: python3 scripts/test_gate.py          (run_tests.py runs it as a suite)
Exit: 0 all green · 1 a case failed.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, tempfile, time

os.environ.setdefault("CINE_TRANSCRIPT_ROOT", __import__("tempfile").gettempdir())   # (3.1) temp transcripts

def read_(p):
    return open(p, encoding="utf-8").read()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "gate.py")
LINT = os.path.join(HERE, "prompt_lint.py")
DEVELOP = os.path.join(HERE, "develop.py")
BOARD = os.path.join(HERE, "board.py")
LEDGER = os.path.join(HERE, "ledger.py")
PY = sys.executable
# Made-up connector uuids (v2.59.0): the one the settings name as the Higgsfield account, and another service's.
SAMPLE = "0a0a0a0a-0000-4000-8000-000000000001"
SAMPLE_OTHER = "0b0b0b0b-0000-4000-8000-000000000002"
os.environ["CINE_HIGGSFIELD_CONNECTORS"] = SAMPLE      # every env below is built from os.environ
os.environ.pop("CINE_OTHER_CONNECTORS", None)

PROFILE = """# Client Profile — Fixture

## 0. ⛔ Hard locks (read before any change)

**Default mode:** A — one hero film.

1. **Format lock?** open
2. **Audio-text lock?** lines are approved as-is once the script is signed
3. **Overlay policy?** captions only
4. **Retired tools/models?** none

**Verification policy:** `{policy}`

**Named approver:** Dana

**Claims-category:** `sleep` — written in the profile's real markdown shape (bold label, backticked
value), because the gate's category regex used to be `claims[- ]category:\\s*sleep` and matched
nothing against it.

## 1. Brand(s)
- Fixture brand.
"""

CHECKPOINT = """# PRODUCTION CHECKPOINT

Job:        fx-01001-test
Mode:       A — one hero film carrying the message
Client:     {profile}
Policy:     {policy}
Format:     vertical-1080 (master) · derived: none
            generation: 1080p minimum, minimax_h3 2k dialogue, kling3_0 4k b-roll
Voice:      none — house register, flagged
Inputs:     approved-language PRESENT · archive+licensing MISSING (accepted risk: no archive on a first job) ·
            personas PRESENT · brand assets PRESENT · music library MISSING (asked 2026-09-06) ·
            spend context PRESENT · reference images PRESENT
Gates:      ideation → script scorecard + claims lint → blocking → frame gate → prompt lint → QA → compliance → export QC
Skips:      none
Budget:     envelope 900 cr (client) · estimate 610 cr [estimated] · preflight 99-costs/PREFLIGHT-2026-09-06.md
Approver:   Dana
Next:       approve the script
"""

def dev_doc(chosen="C2", full=True):
    R = "\n".join(f"- [PRIMARY · source{i} · 2026-09-0{i%9+1}] a fact that decides something real "
                   f"about the film number {i}" for i in range(1, 8))
    seeds = [("a grove at dawn", "two-hander", "Can origin be proven?"),
             ("a bottle on a steel bench", "demo", "What does grade actually mean?"),
             ("a buyer's spreadsheet", "list", "Which supplier survives an audit?"),
             ("hands sorting olives", "single-take monologue", "Who picks these?"),
             ("an empty shelf", "testimonial-shaped", "Why did the last shipment fail?")]
    cs = "\n".join(f"### C{i} · concept {i}\npremise: sentence {i} distinct wording here\n"
                    f"question: {q}\nimage: {img}\nstructure: {st}\n"
                    f"proof: reason {i} unique to this brand\nrisk: risk {i}\n"
                    for i, (img, st, q) in enumerate(seeds, 1))
    L = "\n".join(f"- [environment] 00-brief/_look/ref{i}.jpg — what picture {i} settles"
                  for i in range(1, 5))
    head = (f"# DEVELOPMENT — fixture\n\n## Research\n{R}\n\n## Look\n{L}\n\n## Concepts\n\n{cs}\n"
            "## Adversarial round 1 · the skeptical buyer\n\nkilled: C3 — the claim needs a document nobody has\n"
            "weakened: C1 — the proof is thin\nsurvived: C1, C2, C4, C5\n\n"
            "## Adversarial round 2 · the bored scroller\n\nkilled: C5 — nothing happens in the first two seconds\n"
            "weakened: C4 — the open is a talking head\nsurvived: C1, C2, C4\n\n"
            f"## Choice\n\nchosen: {chosen}\nby: Dana\n"
            "quote: \"C2, the bench one, it is the only one we can shoot\"\nwhy: the assets support it\n")
    if not full:
        return head
    return head + ("\n## Hooks\n\n| ID | awareness | type | the line / beat | the gap |\n|---|---|---|---|---|\n"
                   "| H1 | problem-aware | curiosity gap | I paid 400 for the wrong grade | which grade they were sold · because they have a bottle of it at home |\n"
                   "| H2 | solution-aware | skeptic | I assumed the certificate was theatre | whether the certificate means anything · because they already pay a premium for it |\n"
                   "| H3 | problem-aware | demonstration | this is what nine months in steel does | what storage does to the oil · because their own bottle has been open since spring |\n"
                   "| H4 | unaware | story cold open | the buyer put it back on the shelf | why a professional rejected it · because they buy this brand every fortnight |\n"
                   "| H5 | most-aware | direct offer | twelve a bottle, no subscription | what the price actually is · because they have been comparing for a fortnight |\n"
                   "\n"
                   "## Drafts\n\n### v1\ndraft\ncritique: the hook line about origin announces the topic "
                   "instead of opening a gap in the first beat\n\n### v2\ndraft\ncritique: scene two has no "
                   "value turn, the buyer line lands flat and the CTA arrives before any proof\n\n### v3\nfinal\n")


SCRIPT = """# SCRIPT v3

S1  HOST: Every bottle starts in the same grove.
S3  HOST: We taste it before you ever see it.
"""

CLIP = """---
shot: S3
kind: clip
type: dialogue
model: minimax_h3
resolution: 2k
duration: 6
aspect: 9:16
start_frame: 02-startframes/S3_host_v2.png
line: "We taste it before you ever see it."
vo: 05-voice/S3.wav
payload: the glass stops being a prop and becomes the thing she is asking you to believe her about
---
[MOTION]
START: seated at the tasting table, both hands around the glass
MID:   lifting the glass to nose height, a slow inhale
END:   glass held still at chest height, eyes settling on the lens

[CAMERA]
locked-off, eye level

[PERFORMANCE]
STATE: guarded → warm   BEAT: the inhale
FACE:  eyes narrow slightly on the inhale, then open
GAZE:  on the lens from END onward

[SUPPRESS]
head bobbing, extra hands, text, watermark
"""

FRAME = """---
shot: S3
kind: frame
type: character
model: nano_banana_pro
aspect: 9:16
refs:
  - role: image, what: character, value: media_host_01
  - role: image, what: wardrobe, file: _reference/wardrobe/apron.jpg
---
[SUBJECT]
the host seated at a stone tasting bench, both hands around a tasting vessel, mid-breath

[CHARACTER]
green apron, silver hair, tortoiseshell glasses, no jewellery

[ENVIRONMENT]
late morning, olive branches in a jar, stacked crates out of focus

[LIGHTING]
5200K window sun from camera left, soft fill from a cream wall

[CAMERA]
50mm, eye level, slight low angle

[STYLE]
phone-real, slight rolling shutter, natural skin

[SAFE ZONE]
top 35% clear for the title; face clear of the right action rail

[SUPPRESS]
text, logo, watermark, extra fingers, second panel
"""

# --- Mode S, the stills lane (2026-10-06) -------------------------------------------------------
CHECKPOINT_S = (CHECKPOINT.replace("fx-01001-test", "fx-02001-stills")
                .replace("A — one hero film carrying the message", "S — four website stills for the home page")
                .replace("vertical-1080 (master) · derived: none", "stills · each prompt file declares its aspect")
                .replace("Voice:      none — house register, flagged", "Voice:      none — stills, no audio")
                .replace("Next:       approve the script", "Next:       approve the brief"))

BRIEF = """# BRIEF — home page stills

| ID | where it runs | what it shows |
|---|---|---|
| home-hero | home page hero, 16:9 | a finished rooftop install at golden hour |
| card-inverter | product card, 1:1 | the client's inverter, edited into a garage wall |
"""

FRAME_S = """---
shot: home-hero
kind: frame
type: environment
model: nano_banana_pro
resolution: 2k
aspect: 16:9
variants: 2
---
[SUBJECT]
a south-facing pitched roof carrying twelve dark monocrystalline panels in two even rows, a narrow aluminium rail along the ridge

[ENVIRONMENT]
a detached two-storey brick house at the edge of a village, an orchard behind it, a gravel drive with one parked bicycle

[LIGHTING]
low late-afternoon sun from camera right, warm and raking across the panels, long soft shadows on the lawn

[CAMERA]
35mm, standing eye height across the lawn, slight upward angle to the roofline

[STYLE]
natural daylight photograph, true colour, fine sensor grain

[SUPPRESS]
text, logo, watermark, lens flare, people
"""

# a reference EDIT: the picture being edited is a declared reference, bound by its media id
FRAME_S_EDIT = """---
shot: card-inverter
kind: frame
type: product
model: nano_banana_pro
resolution: 2k
aspect: 1:1
variants: 1
refs:
  - role: image, what: prop, value: media_inverter_01, not: studio background, packshot lighting
---
[SUBJECT]
the referenced inverter mounted on a clean garage wall at chest height, its cable conduit running straight down to the floor

[ENVIRONMENT]
a tidy garage with pale grey painted brick, a workbench out of focus to the left, a coiled garden hose on a hook

[LIGHTING]
overcast daylight through an open garage door behind camera, soft and even, a faint shadow under the unit

[CAMERA]
50mm, eye level, square to the wall

[STYLE]
natural daylight photograph, true colour, fine sensor grain

[SUPPRESS]
text, logo, watermark, people
"""

fails = []


# Higgsfield connector tools that passed the gate ungated until 2026-10-06 (gate.py SPEND_RE note).
# ...and three more found 2026-10-23 (gate.py FREE_ACTIONS note). virality_predictor is action-gated.
UNGATED_THREE = ("scene_builder_3d_generate_angles", "relight_image", "virality_predictor")
UNGATED_FIVE = ("ads_studio_generate", "ai_influencer_generate", "build_ai_influencer", "execute_preset",
                "shorts_studio_create_preset")

def check(name: str, cond: bool, detail: str = ""):
    print(f"  [{'ok' if cond else 'FAIL'}] {name}" + ("" if cond else f"\n        {detail[:4000]}"))
    if not cond:
        fails.append(name)


def run(args, env, stdin=None):
    # (3.1) these scenarios approve without a session transcript, so their homes are explicitly hookless (on a hooked
    # home an unresolvable transcript is refused); a test of the hooked path sets CINE_TEST_HOOKED=1
    h = env.get("CINE_HOME")
    if h and not env.get("CINE_TEST_HOOKED"):
        os.makedirs(h, exist_ok=True)
        if not os.path.exists(os.path.join(h, "config.json")):
            open(os.path.join(h, "config.json"), "w").write('{"hookless": true}')
    r = subprocess.run([PY] + args, input=stdin, capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, r.stdout, r.stderr


def hook(env, tool, params_or_requests, batch=False, raw=False):
    """raw=True sends params_or_requests as the whole tool_input (tools whose fields sit at the top
    level, e.g. build_ai_influencer's `action`)."""
    ti = params_or_requests if raw else ({"requests": params_or_requests} if batch else {"params": params_or_requests})
    payload = {"session_id": "t", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti}
    rc, out, err = run([GATE, "hook"], env, stdin=json.dumps(payload))
    if not out.strip():
        return "allow", "", err
    d = json.loads(out)
    h = d.get("hookSpecificOutput", {})
    ctx = h.get("additionalContext") or d.get("additionalContext", "")
    # no permissionDecision + context = the gate PASSED and left the normal permission flow alone
    return h.get("permissionDecision") or ("pass" if ctx else "allow"), h.get("permissionDecisionReason", ""), ctx


def fail_closed_suite(td: str) -> None:
    """(v2.52.4) What happens to a paid call when the gate ITSELF is broken. The rest of this file asks the
    gate a question and reads its answer; this section breaks the gate on a copy and runs the exact command
    strings hooks.json registers, through a shell, the way Claude Code does. Exit 2 is the only exit code
    Claude Code always treats as "block" — 1 and 127 are non-blocking hook errors and the call proceeds."""
    print("gate.py — a broken gate still blocks (hooks.json, fail closed)")
    plugin = os.path.normpath(os.path.join(ROOT, os.pardir, os.pardir))
    hooks = json.load(open(os.path.join(plugin, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]
    pre = [(e.get("matcher") or "", h) for e in hooks["PreToolUse"] for h in e["hooks"]]
    is_gate = lambda h: '/gate.py" hook' in h["command"]        # the slash keeps shell_gate.py out
    gate_h = [(m, h) for m, h in pre if is_gate(h)]
    other_h = [(m, h) for m, h in pre if not is_gate(h)]
    post_h = [h for ev in ("PostToolUse", "SessionStart") for e in hooks.get(ev) or [] for h in e["hooks"]]
    _cc = open(os.path.join(plugin, "commands", "connectors.md"), encoding="utf-8").read().split("\n---", 1)[0]
    check("(3.1.1) /cinematographly:connectors runs only when the person types it, with no pre-approved tools",
          "\ndisable-model-invocation: true" in _cc and "allowed-tools" not in _cc, _cc)
    check("hooks.json registers four gate.py PreToolUse entries", len(gate_h) == 4, str(len(gate_h)))
    check('every gate entry sets onFailure to "block" (a hook that cannot start, or times out, blocks)',
          all(h.get("onFailure") == "block" for _, h in gate_h), str([h.get("onFailure") for _, h in gate_h]))
    check("every gate entry's command ends by turning any failure into exit 2",
          all(h["command"].rstrip().endswith("exit 2; }") and "|| {" in h["command"] for _, h in gate_h),
          str([h["command"][-60:] for _, h in gate_h]))
    check("the shell gate, the recorder and SessionStart stay fail-open (they do not guard a spend)",
          all("onFailure" not in h and "exit 2" not in h["command"] for _, h in other_h) and
          all("onFailure" not in h and "exit 2" not in h["command"] for h in post_h))
    cmd = gate_h[0][1]["command"]
    check("the four gate entries run the same command", all(h["command"] == cmd for _, h in gate_h))
    call = json.dumps({"session_id": "t", "hook_event_name": "PreToolUse",
                       "tool_name": "mcp__Higgsfield__generate_image",
                       "tool_input": {"params": {"model": "gpt_image_2_6", "prompt": "a roof"}}})
    pydir = os.path.dirname(os.path.realpath(PY))

    def fire(root, path=None, payload=None):
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": root, "CINE_HOME": os.path.join(td, "home-fc")}
        env.pop("CINE_JOB", None); env.pop("CINE_GATE", None)
        env["PATH"] = path if path is not None else pydir + os.pathsep + env.get("PATH", "")
        r = subprocess.run(["/bin/sh", "-c", cmd], input=payload or call, capture_output=True, text=True, env=env,
                           timeout=60)
        dec = ""
        try:
            dec = json.loads(r.stdout)["hookSpecificOutput"].get("permissionDecision", "")
        except (ValueError, KeyError):
            pass
        return r.returncode, dec, r.stderr

    def broken(name, breaker):
        root = os.path.join(td, name)
        dst = os.path.join(root, "skills", "cinematographly", "scripts")
        shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("__pycache__"))
        breaker(dst)
        return root

    rc, dec, err = fire(plugin)
    check("healthy gate, no job open: the command answers deny and exits 0 (the tail does not fire)",
          rc == 0 and dec == "deny", f"rc={rc} dec={dec!r} {err[-300:]}")
    rc, dec, err = fire(broken("fc-missing-module", lambda d: os.remove(os.path.join(d, "job_tier.py"))))
    check("a module the gate imports is missing → exit 2, with the reason on stderr",
          rc == 2 and "fails closed" in err, f"rc={rc} {err[-300:]}")

    read_only = json.dumps({"session_id": "t", "hook_event_name": "PreToolUse",
                            "tool_name": "mcp__Higgsfield__models_explore", "tool_input": {}})
    rc, dec, err = fire(plugin, payload=read_only)
    check("healthy gate, a tool it has no opinion on: the command answers (no decision) and exits 0",
          rc == 0 and dec == "", f"rc={rc} dec={dec!r} {err[-300:]}")

    # (v2.59.2) A cut that lands at a line boundary still PARSES: the cut file defines its functions, never reaches
    # main() and exits 0 having printed nothing. Until 2.59.2 that silence was read as "no objection". So: cuts at
    # nine fractions of the file, and one placed on purpose where the cut file is valid Python.
    src = read_(os.path.join(HERE, "gate.py"))
    mid = src.rfind("\ndef ", 0, len(src) // 2) + 1
    import ast as _ast
    _ast.parse(src[:mid])                                # the deliberate cut really is valid Python
    cuts = [("at a function boundary (the cut file parses)", mid)] + \
           [(f"at {k}0 % of its length", len(src) * k // 10) for k in range(1, 10)]
    for i, (where, at) in enumerate(cuts):
        def cut(d, at=at):
            open(os.path.join(d, "gate.py"), "w", encoding="utf-8").write(src[:at])
        rc, dec, err = fire(broken(f"fc-truncated-{i}", cut))
        check(f"gate.py cut off {where} → exit 2", rc == 2 and "fails closed" in err, f"rc={rc} {err[-300:]}")
    rc, dec, err = fire(os.path.join(td, "fc-no-such-plugin"))
    check("gate.py is not there at all → exit 2", rc == 2, f"rc={rc} {err[-300:]}")
    rc, dec, err = fire(plugin, path=os.path.join(td, "fc-empty-path"))
    check("no python3 on the hook's PATH → exit 2 (it was 127, which Claude Code does not block on)",
          rc == 2 and "fails closed" in err, f"rc={rc} {err[-300:]}")


def stills_suite(td: str, profile: str) -> None:
    """Mode S — a stills job, in its own CINE_HOME so it cannot lean on the video job's state."""
    print("gate.py — Mode S, the stills lane")
    env = {**os.environ, "CINE_HOME": os.path.join(td, "home-s"),
           "CINE_ARCHIVE": os.path.join(td, "archive-s")}
    env.pop("CINE_JOB", None); env.pop("CINE_GATE", None)
    open(profile, "w").write(PROFILE.format(policy="gated"))
    job = os.path.join(td, "fx-02001-stills")
    for d in ("00-brief", "01-script/prompts", "02-startframes"):
        os.makedirs(os.path.join(job, d))
    cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
    IMG, VID, AUD = ("mcp__Higgsfield__generate_image", "mcp__Higgsfield__generate_video",
                     "mcp__Higgsfield__generate_audio")

    # opening: Mode S and Format `stills` imply each other
    open(cp, "w").write(CHECKPOINT_S.replace("stills · each prompt file", "vertical-1080 · each prompt file")
                        .format(profile=profile, policy="gated"))
    rc, out, err = run([GATE, "open", job], env)
    check("S job with a Format that is not `stills` → open REFUSED",
          rc == 1 and "needs `Format: stills`" in out, out + err)
    open(cp, "w").write(CHECKPOINT_S.replace("S — four website stills", "A — four website stills")
                        .format(profile=profile, policy="gated"))
    rc, out, err = run([GATE, "open", job], env)
    check("Format `stills` on a Mode A job → open REFUSED", rc == 1 and "needs `Mode: S`" in out, out + err)
    open(cp, "w").write(CHECKPOINT_S.replace("S — four", "Q — four").format(profile=profile, policy="gated"))
    rc, out, err = run([GATE, "open", job], env)
    check("an unknown mode letter is still refused", rc == 1 and "A, B, C, D or S" in out, out + err)
    open(cp, "w").write(CHECKPOINT_S.format(profile=profile, policy="gated"))
    rc, out, err = run([GATE, "open", job], env)
    check("S job (Mode S + Format stills) opens", rc == 0 and "OPEN:" in out and "stills lane" in out, out + err)

    # nothing generates before the brief — and there is no previz lane to fall into
    fp = os.path.join(job, "01-script", "prompts", "home-hero.frame.prompt.md")
    open(fp, "w").write(FRAME_S)
    rc, out, err = run([LINT, fp], env)
    check("an S-mode frame prompt lints with no script and no shot list", rc == 0 and "LINT PASS" in out, out + err)
    prompt = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip()
    good = {"model": "nano_banana_pro", "prompt": prompt, "aspect_ratio": "16:9", "count": 2, "resolution": "2k"}
    dec, why, _ = hook(env, IMG, good)
    check("generate_image in S without `brief` → deny, naming the brief (not the script, not previz)",
          dec == "deny" and "`brief` is not approved" in why and "script" not in why.split("`brief`")[0]
          and "previz" not in why, why)
    rc, out, err = run([GATE, "previz", "--budget", "2", "--why", "which roof angle reads best at hero size"], env)
    check("`gate.py previz` in S → refused (no concept to inform)", rc == 1 and "no previz lane" in err, err)

    # the lane's approvals
    rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "the script is approved",
                        "--artifact", "00-brief/CHECKPOINT.md"], env)
    check("`approve script` on an S job → REFUSED (stills: brief, frame, export only)",
          rc == 1 and "stills job" in err and "`brief`, `frame:<ID>` and `export`" in err, err)
    for stg in ("concept", "clips", "audio", "lock", "endframe:home-hero", "character:host"):
        rc, out, err = run([GATE, "approve", stg, "--by", "Dana", "--quote", "go ahead with it"], env)
        check(f"`approve {stg}` on an S job → REFUSED", rc == 1 and "stills job" in err, err)
    open(os.path.join(job, "02-startframes", "home-hero_v1.png"), "wb").write(b"\x89PNG\r\n stills fixture")
    rc, out, err = run([GATE, "approve", "frame:home-hero", "--by", "Dana", "--quote", "that roof is the one",
                        "--artifact", "02-startframes/home-hero_v1.png", "--media-id", "img_hero1"], env)
    check("frame:<ID> in S before the brief → REFUSED (it needs brief, not script)",
          rc == 1 and "needs brief approved first" in err and "script" not in err.split("the chain is")[0], err)
    bp = os.path.join(job, "00-brief", "BRIEF-home.md")
    open(bp, "w").write(BRIEF)
    rc, out, err = run([GATE, "approve", "brief", "--by", "Dana", "--quote", "brief is right, make these"], env)
    check("`approve brief` without --artifact → REFUSED", rc == 1 and "--artifact" in err, err)
    rc, out, err = run([GATE, "approve", "brief", "--by", "Dana", "--quote", "brief is right, make these",
                        "--artifact", "00-brief/BRIEF-home.md"], env)
    check("`approve brief` with the artifact → APPROVED, sha recorded, no develop.py",
          rc == 0 and "APPROVED brief" in out and " sha " in out, out + err)
    rec = json.load(open(os.path.join(job, "00-brief", "RECORD.json"), encoding="utf-8"))
    check("...and the ledger reads the stills job's state as `brief`", rec.get("state") == "brief", str(rec.get("state")))

    # generate_image: the linted prompt + the brief
    dec, why, ctx = hook(env, IMG, good)
    check("generate_image in S with `brief` + a linted prompt → pass", dec == "pass" and "home-hero frame" in ctx, why)
    dec, why, _ = hook(env, IMG, {**good, "prompt": prompt + " and a dog"})
    check("generate_image in S with an unlinted prompt → deny", dec == "deny" and "matches no linted" in why, why)
    dec, why, _ = hook(env, IMG, {**good, "aspect_ratio": "9:16"})
    check("S: the aspect is the PROMPT FILE's (no preset aspect to fall back on) → 9:16 vs 16:9 denied",
          dec == "deny" and "aspect 9:16" in why, why)
    dec, why, _ = hook(env, IMG, {**good, "count": 4})
    check("S: count above the linted variants → deny", dec == "deny" and "exceeds the linted" in why, why)
    dec, why, _ = hook(env, IMG, {**good, "model": "soul_2"})
    check("S: a different model than the file casts → deny", dec == "deny" and "≠ linted" in why, why)
    dec, why, _ = hook(env, IMG, {**good, "medias": [{"role": "image", "value": "img_unknown"}]})
    check("S: an undeclared media on a still → deny", dec == "deny" and "does not declare" in why, why)
    dec, _, ctx = hook(env, IMG, {"model": "nano_banana_pro", "prompt": "x", "get_cost": True})
    check("S: a cost probe passes (spends nothing)", dec == "pass" and "probe" in ctx, ctx)
    rc, out, err = run([GATE, "preflight", "home-hero", "--kind", "frame", "--json"], env)
    pf = json.loads(out) if out.strip().startswith("{") else {}
    check("S: preflight takes the aspect from the prompt file and would pass",
          rc == 0 and pf.get("would_pass") and pf["params"].get("aspect_ratio") == "16:9"
          and pf["params"].get("count") == 2, out + err)
    check("S: preflight sends the file's resolution (a 4k still silently came back 2k, 2026-10-06)",
          pf.get("params", {}).get("resolution") == "2k", out)
    dec, _, _ = hook(env, pf.get("tool", IMG), pf.get("params", {}))
    check("S: preflight params pass the hook verbatim", dec == "pass")

    # a reference EDIT: the edited picture is a declared ref, and only it may ride along
    fe = os.path.join(job, "01-script", "prompts", "card-inverter.frame.prompt.md")
    open(fe, "w").write(FRAME_S_EDIT)
    rc, out, err = run([LINT, fe], env)
    eprompt = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip() \
        if rc == 0 else ""
    check("an S-mode reference-edit prompt lints (ref declared with what:/value:/not:)", rc == 0, out + err)
    edit = {"model": "nano_banana_pro", "prompt": eprompt, "aspect_ratio": "1:1",
            "medias": [{"role": "image", "value": "media_inverter_01"}]}
    dec, why, ctx = hook(env, IMG, edit)
    check("S: reference edit binding the declared media → pass", dec == "pass" and "card-inverter frame" in ctx, why)
    dec, why, _ = hook(env, IMG, {**edit, "medias": edit["medias"] + [{"role": "image", "value": "img_rider"}]})
    check("S: an extra, undeclared reference riding on the edit → deny", dec == "deny" and "img_rider" in why, why)
    rc, out, err = run([GATE, "preflight", "card-inverter", "--kind", "frame", "--json"], env)
    pfe = json.loads(out) if out.strip().startswith("{") else {}
    check("S: preflight emits the declared reference as medias and would pass",
          rc == 0 and pfe.get("would_pass")
          and pfe["params"].get("medias") == [{"role": "image", "value": "media_inverter_01"}], out + err)

    # the brief binds the IDs, and the bytes
    fo = os.path.join(job, "01-script", "prompts", "about-team.frame.prompt.md")
    open(fo, "w").write(FRAME_S.replace("shot: home-hero", "shot: about-team")
                        .replace("one parked bicycle", "two parked bicycles"))
    rc, out, err = run([LINT, fo], env)
    oprompt = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip()
    dec, why, _ = hook(env, IMG, {"model": "nano_banana_pro", "prompt": oprompt, "aspect_ratio": "16:9"})
    check("S: a linted still whose ID the approved brief does not name → deny",
          dec == "deny" and "not named in the approved brief" in why, why)
    os.remove(fo); os.path.exists(fo[:-3] + ".ok") and os.remove(fo[:-3] + ".ok")
    # whole-token: an ID that occurs only INSIDE a longer word of the brief is not named by it —
    # `roof` and `top` both sit inside "rooftop" (lookahead and lookbehind respectively)
    for sid, noun in (("roof", "a parked wheelbarrow"), ("top", "a stacked ladder")):
        fh = os.path.join(job, "01-script", "prompts", f"{sid}.frame.prompt.md")
        open(fh, "w").write(FRAME_S.replace("shot: home-hero", f"shot: {sid}").replace("one parked bicycle", noun))
        rc, out, err = run([LINT, fh], env)
        hprompt = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip()
        dec, why, _ = hook(env, IMG, {"model": "nano_banana_pro", "prompt": hprompt, "aspect_ratio": "16:9"})
        check(f"S: `{sid}` is NOT named by a brief that only says `rooftop` (whole-token match)",
              dec == "deny" and "not named in the approved brief" in why, why)
        os.remove(fh); os.path.exists(fh[:-3] + ".ok") and os.remove(fh[:-3] + ".ok")
    dec, why, _ = hook(env, IMG, {k: v for k, v in good.items() if k != "aspect_ratio"})
    check("S: a still sent WITHOUT aspect_ratio → deny (no preset aspect to fall back on)",
          dec == "deny" and "`aspect_ratio` is required" in why, why)
    dec, why, _ = hook(env, IMG, {**edit, "medias": {"role": "image", "value": "media_inverter_01"}})
    check("S: `medias` that is not a list → deny", dec == "deny" and "not a list" in why, why)
    dec, why, ctx = hook(env, "mcp__Higgsfield__generate_image_batch",
                         [{"params": good}, {"params": {**good, "model": "soul_2"}}], batch=True)
    check("S: generate_image_batch — one good, one wrong model → deny naming request[1] only",
          dec == "deny" and "request[1]" in why and "request[0]" not in why, why)
    dec, why, ctx = hook(env, "mcp__Higgsfield__generate_image_batch", [{"params": good}, {"params": edit}],
                         batch=True)
    check("S: generate_image_batch of two linted stills → pass", dec == "pass" and "GATE OK" in ctx, why)
    open(bp, "a").write("| about-team | about page | the crew on a roof |\n")
    dec, why, _ = hook(env, IMG, good)
    check("S: the brief edited after its approval → deny until it is re-approved",
          dec == "deny" and "changed after it was approved" in why, why)
    rc, out, err = run([GATE, "status", "--json"], env)
    st = json.loads(out) if out.strip().startswith("{") else {}
    check("(wave 2c) the stills status carries the settings with a source each",
          (st.get("settings") or {}).get("regens_per_approval", {}).get("source") == "house", out)
    rc_, out_, _ = run([GATE, "status"], env)
    check("(wave 2c) the stills status prints the settings line", "settings: " in out_ and "(house)" in out_, out_)
    check("S: status names the brief problem, never concept/script/DEVELOPMENT",
          any("changed after it was approved" in n for n in st.get("next", []))
          and not any(("concept" in n or "approve script" in n or "DEVELOPMENT" in n) for n in st.get("next", [])),
          out + err)
    run([GATE, "approve", "brief", "--by", "Dana", "--quote", "the new row is fine too"], env)  # no artifact: refused
    rc, out, err = run([GATE, "approve", "brief", "--by", "Dana", "--quote", "the new row is fine too",
                        "--artifact", "00-brief/BRIEF-home.md"], env)
    dec, why, _ = hook(env, IMG, good)
    check("S: re-approving the edited brief clears it", rc == 0 and dec == "pass", why + err)

    # video, audio and the other tools
    dec, why, _ = hook(env, VID, {"model": "kling3_0", "prompt": prompt, "duration": 5})
    check("generate_video in S → deny (stills job)", dec == "deny" and "stills job" in why, why)
    dec, why, _ = hook(env, "mcp__Higgsfield__generate_video_batch",
                       [{"params": {"model": "kling3_0", "prompt": prompt}}], batch=True)
    check("generate_video_batch in S → deny (stills job)", dec == "deny" and "stills job" in why, why)
    dec, why, _ = hook(env, AUD, {"model": "seed_audio", "prompt": "hello there friend", "voice_id": "v1"})
    check("generate_audio in S → deny (stills job)", dec == "deny" and "stills job" in why, why)
    dec, why, _ = hook(env, f"mcp__{SAMPLE}__generate_video",
                       {"model": "kling3_0", "prompt": prompt, "duration": 5})
    check("generate_video through the claude.ai connector in S → deny", dec == "deny" and "stills job" in why, why)
    dec, why, ctx = hook(env, f"mcp__{SAMPLE}__generate_image", good)
    check("generate_image through the claude.ai connector in S → pass", dec == "pass", why)
    dec, why, _ = hook(env, "mcp__Higgsfield__upscale_image", {"params": {}})
    check("S: upscale_image (a spend tool) → ask, unchanged", dec == "ask" and "carries no prompt" in why, why)
    dec, why, _ = hook(env, "mcp__Higgsfield__tiktok_publish", {})
    check("S: publish without export → deny, unchanged", dec == "deny" and "`export`" in why, why)

    # frame and export
    rc, out, err = run([GATE, "approve", "frame:press-kit", "--by", "Dana", "--quote", "use this one too",
                        "--artifact", "02-startframes/home-hero_v1.png", "--media-id", "img_x"], env)
    check("S: approve frame:<ID> for an ID the brief does not name → REFUSED",
          rc == 1 and "not named in the approved brief" in err, err)
    rc, out, err = run([GATE, "approve", "frame:home-hero", "--by", "Dana", "--quote", "that roof is the one",
                        "--artifact", "02-startframes/home-hero_v1.png", "--media-id", "img_hero1"], env)
    check("frame:<ID> in S once the brief is approved → APPROVED", rc == 0 and "APPROVED frame:home-hero" in out, out + err)
    rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "ship the home page stills"], env)
    check("S: export with nothing in 10-export → REFUSED", rc == 1 and "10-export/ holds no image" in err, err)
    os.makedirs(os.path.join(job, "10-export"))
    open(os.path.join(job, "10-export", "home-hero_16x9.png"), "wb").write(b"\x89PNG\r\n delivered")
    _sts = os.path.join(td, "studio-stills-no"); os.makedirs(_sts, exist_ok=True)
    open(os.path.join(_sts, "studio.json"), "w").write('{"likeness_release": "no", "music_licence": "no"}')
    rc, out, err = run([GATE, "approve", "Export", "--by", "Dana", "--quote", "ship the home page stills"],
                       dict(env, CINE_STUDIO=_sts))
    check("(3.1 review) a stills export (typed `Export`) is blocked by the studio's likeness \"no\"; music is not asked",
          rc == 1 and "likeness releases" in err and "music" not in err.split("REFUSED")[-1].split("Clear it")[0], err)
    rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "ship the home page stills"], env)
    check("S: export with an approved still + the delivered image → APPROVED", rc == 0, out + err)
    dec, why, _ = hook(env, "mcp__Higgsfield__tiktok_publish", {})
    check("S: publish with export approval → ask, unchanged", dec == "ask", why)
    run([GATE, "close"], env)


# --- (v2.72.0) the evaluation lane ---------------------------------------------------------------------------------
CHECKPOINT_EV = (CHECKPOINT.replace("fx-01001-test", "fx-03001-eval")
                 .replace("Next:       approve the script",
                          "Tier:       evaluation\nQuestion:   Does the noun tail help?\nLane:       eval\n"
                          "Next:       approve the evaluation plan"))
EVAL_PLAN = """# Evaluation plan
Question: Does the noun tail help?
Shots: lane-a, lane-b
Takes per shot: 4
Budget: 10 cr
Arms: A with the tail, B without
Variable: the tail
Held fixed: model, resolution, aspect
Decision rule: more usable takes wins, twice
Judging: blind
"""


def eval_lane_suite(td: str, profile: str) -> None:
    """The evaluation lane (v2.72.0): one approved plan stands where concept and script stood; the plan's shots, takes
    and budget bind every call under every policy; an evaluated job never becomes production."""
    print("gate.py — the evaluation lane")
    env = {**os.environ, "CINE_HOME": os.path.join(td, "home-ev"), "CINE_ARCHIVE": os.path.join(td, "archive-ev")}
    env.pop("CINE_JOB", None); env.pop("CINE_GATE", None)
    open(profile, "w").write(PROFILE.format(policy="gated"))
    job = os.path.join(td, "fx-03001-eval")
    for d in ("00-brief", "01-script/prompts", "02-startframes"):
        os.makedirs(os.path.join(job, d))
    cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
    IMG, AUD = "mcp__Higgsfield__generate_image", "mcp__Higgsfield__generate_audio"
    base_cp = CHECKPOINT_EV.format(profile=profile, policy="gated")
    open(cp, "w").write(base_cp.replace("Tier:       evaluation\n", ""))
    rc, out, err = run([GATE, "open", job], env)
    check("`Lane: eval` without `Tier: evaluation` → open refused", rc == 1 and "needs `Tier: evaluation`" in out, out + err)
    open(cp, "w").write(base_cp.replace("Lane:       eval", "Lane:       fast"))
    rc, out, err = run([GATE, "open", job], env)
    check("an unknown `Lane:` → open refused", rc == 1 and "the only lane is `eval`" in out, out + err)
    open(cp, "w").write(base_cp)
    rc, out, err = run([GATE, "open", job], env)
    check("an evaluation-lane job opens", rc == 0 and "OPEN:" in out, out + err)

    def lint_frame(sid, noun):
        f = os.path.join(job, "01-script", "prompts", f"{sid}.frame.prompt.md")
        open(f, "w").write(FRAME_S.replace("shot: home-hero", f"shot: {sid}").replace("one parked bicycle", noun).replace("aspect: 16:9", "aspect: 9:16")
                           .replace("[SUPPRESS]", "[SAFE ZONE]\nevery load-bearing element inside y=15-65%, x=11-72% of frame (the MEASURED ad safe box: top 15% profile row, bottom 35% captions + CTA, right 28% action rail)\n\n[SUPPRESS]")
                           .replace("text, logo, watermark, lens flare, people", "text, logo, lens flare, people"))
        rc_, out_, err_ = run([LINT, f], env)
        pr = out_.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip() \
            if "PROMPT (paste" in out_ else ""
        return rc_, pr, out_ + err_
    rc, pa, o = lint_frame("lane-a", "one parked bicycle")
    check("a frame prompt lints in the lane with no script", rc == 0 and pa, o)
    _, pb, _ = lint_frame("lane-b", "two parked bicycles")
    _, px, _ = lint_frame("off-plan", "a parked wheelbarrow")
    A = {"model": "nano_banana_pro", "prompt": pa, "aspect_ratio": "9:16", "count": 2, "resolution": "2k"}
    B = {**A, "prompt": pb}
    dec, why, _ = hook(env, IMG, A)
    check("before the plan: deny naming `eval` (not the script, not previz)",
          dec == "deny" and "`eval` is not approved" in why and "previz" not in why and "`script`" not in why, why)
    rc, out, err = run([GATE, "previz", "--budget", "2", "--why", "which roof angle reads best"], env)
    check("`gate.py previz` in the lane → refused", rc == 1 and "no previz in the evaluation lane" in err, err)
    rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "go with this script",
                        "--artifact", "00-brief/CHECKPOINT.md"], env)
    check("`approve script` in the lane → refused (it has no script)", rc == 1 and "evaluation job" in err, err)
    pp = os.path.join(job, "00-brief", "EVAL-PLAN.md")
    open(pp, "w").write(EVAL_PLAN.replace("Shots: lane-a, lane-b\n", ""))
    rc, out, err = run([GATE, "approve", "eval", "--by", "Dana", "--quote", "run the tail test",
                        "--artifact", "00-brief/EVAL-PLAN.md"], env)
    check("a plan with no `Shots:` → approve eval refused", rc == 1 and "Shots" in err, err)
    open(pp, "w").write(EVAL_PLAN.replace("Judging: blind\n", ""))
    rc, out, err = run([GATE, "approve", "eval", "--by", "Dana", "--quote", "run the tail test",
                        "--artifact", "00-brief/EVAL-PLAN.md"], env)
    check("a complete plan (Judging missing only warns) → approve eval passes", rc == 0 and "Judging" in err, out + err)
    open(pp, "w").write(EVAL_PLAN)
    rc, out, err = run([GATE, "approve", "eval", "--by", "Dana", "--quote", "run the tail test now",
                        "--artifact", "00-brief/EVAL-PLAN.md"], env)
    check("before any generation a new eval row replaces the old one", rc == 0, out + err)
    rows = read_(os.path.join(job, "00-brief", "APPROVALS.md"))
    check("the eval row carries the stamp after the eight cells", "| lane=eval ck=" in rows, rows)
    _t = read_(cp); open(cp, "w").write(_t.replace("Next:       approve the evaluation plan", "Next:       run the takes"))
    # (wave 2c) a lane call that hits the studio ceiling asks, and reserves as PENDING (asked) like any lane ask
    _ste = os.path.join(td, "studio-ceiling-ev"); os.makedirs(_ste, exist_ok=True)
    json.dump({"monthly_credit_ceiling": 0.5}, open(os.path.join(_ste, "studio.json"), "w"))
    _ledg = os.path.join(job, ".gate", "eval-ledger.jsonl")
    _led0 = open(_ledg, encoding="utf-8").read() if os.path.isfile(_ledg) else ""
    dec, why, _ = hook(dict(env, CINE_STUDIO=_ste), IMG, A)
    _rows = [json.loads(l_) for l_ in open(_ledg, encoding="utf-8") if l_.strip()] if os.path.isfile(_ledg) else []
    check("(wave 2c) a gated lane call over the studio ceiling asks and reserves as asked (a declined ask is released)",
          dec == "ask" and "budget stop" in why and _rows and _rows[-1].get("asked") is True, f"{dec} {why} {_rows[-1:]}")
    open(_ledg, "w", encoding="utf-8").write(_led0)                  # back to before, so the take counts below hold
    dec, why, ctx = hook(env, IMG, A)
    check("an unrelated checkpoint edit does not stop the lane; lane-a × 2 → pass (gated)",
          dec == "pass" and "EVAL PLAN lane-a+2" in ctx, why + ctx)
    dec, why, _ = hook(env, IMG, {**A, "prompt": px})
    check("a shot not on the plan's `Shots:` line → deny", dec == "deny" and "not on the plan" in why, why)
    dec, why, _ = hook(env, IMG, A)
    check("lane-a take 4 of 4 → pass (the reservation counted the first call)", dec == "pass", why)
    dec, why, _ = hook(env, IMG, A)
    check("lane-a take 6 of 4 → deny, under the gated policy (nothing asks there)",
          dec == "deny" and "take 6 of a plan that allows 4" in why, why)
    dec, why, _ = hook(dict(env, CINE_STUDIO=_ste), IMG, A)
    check("(wave 2c) over the plan AND over the studio ceiling → still deny (a budget stop never softens a deny)",
          dec == "deny" and "allows 4" in why, why)
    dec, why, _ = hook(env, IMG, B)
    check("lane-b: 4 cr more passes 8 of 10? no — 8 used + 4 = 12 > 10 → deny on the budget",
          dec == "deny" and "past its budget" in why, why)
    dec, why, _ = hook(env, "mcp__Higgsfield__generate_image_batch", [{"params": B}, {"params": B}, {"params": B}],
                       batch=True)
    check("a batch counts its own requests: lane-b × 3 requests × 2 = take 6 of 4 → deny",
          dec == "deny" and "lane-b: this would be take 6" in why, why)
    rc, out, err = run([GATE, "approve", "eval", "--by", "Dana", "--quote", "change the test please",
                        "--artifact", "00-brief/EVAL-PLAN.md"], env)
    check("after a generation the plan is fixed: approve eval refused", rc == 1 and "plan is fixed" in err, err)
    _tp = os.path.join(td, "transcript-ev.jsonl")          # an allowance needs the quote on record
    open(_tp, "w").write(json.dumps({"type": "user", "message": {"role": "user", "content": "go ahead with these"}}) + "\n")
    open(os.path.join(env["CINE_HOME"], "transcript-path"), "w").write(_tp)
    rc, out, err = run([GATE, "allow", "image", "--shots", "off-plan", "--by", "Dana", "--quote", "go ahead with these"], env)
    check("allow for a shot not on the plan → refused", rc == 1 and "not on the plan" in err, out + err)
    rc, out, err = run([GATE, "allow", "image", "--shots", "lane-b", "--regens", "5", "--by", "Dana",
                        "--quote", "go ahead with these"], env)
    check("allow with more regens than the plan's takes → refused", rc == 1 and "at most 3" in err, out + err)
    os.remove(os.path.join(env["CINE_HOME"], "transcript-path"))
    dec, why, _ = hook(env, AUD, {"model": "text2speech_v2", "prompt": "hello there", "voice_id": "v1",
                                  "variant": "elevenlabs", "voice_type": "preset"})
    check("speech in the lane → deny", dec == "deny" and "speech is not part of the evaluation lane" in why, why)
    dec, why, _ = hook(env, "mcp__Kling_AI__text_to_image", {"prompt": pa}, raw=True)
    check("Kling in the lane → deny", dec == "deny" and "Kling is not part of the evaluation lane" in why, why)
    dec, why, _ = hook(env, "mcp__Higgsfield__upscale_image", {"params": {"media_id": "x"}}, raw=True)
    check("an unlintable spend tool in the lane → deny", dec == "deny" and "evaluation lane" in why, why)
    open(os.path.join(job, "02-startframes", "lane-a_v1.png"), "wb").write(b"\x89PNG lane a")
    rc, out, err = run([GATE, "log-external", "02-startframes/lane-a_v1.png", "--by", "Dana", "--source", "website"], env)
    check("log-external in the lane → refused", rc == 1 and "evaluation lane" in err, out + err)
    rc, out, err = run([GATE, "approve", "frame:lane-a", "--by", "Dana", "--quote", "keep the lane a still",
                        "--artifact", "02-startframes/lane-a_v1.png", "--media-id", "m_lane_a"], env)
    check("approve frame: in the lane needs only `eval` (no script, no storyboard)", rc == 0, out + err)
    rc, out, err = run([GATE, "approve", "clips", "--by", "Dana", "--quote", "the clips are fine"], env)
    check("approve clips in the lane → refused", rc == 1 and "evaluation job" in err, err)
    post = {"session_id": "t", "hook_event_name": "PostToolUse", "tool_name": IMG, "tool_input": {"params": A},
            "tool_response": {"job_id": "job_3f2e1d0c9b"}}
    run([GATE, "posthook"], env, stdin=json.dumps(post))
    rc, out, err = run([GATE, "status"], env)
    check("a recorded submission of a reserved call is not counted twice; status shows the plan and what is used",
          "EVALUATION LANE" in out and "used 8 cr" in out and "with no reservation" not in out, out + err)
    check("(wave 2c) the evaluation-lane status prints the settings line", "settings: envelope" in out, out)
    open(pp, "a").write("Note: edited later\n")
    dec, why, _ = hook(env, IMG, B)
    check("the plan edited after approval → deny", dec == "deny" and "changed after it was approved" in why, why)
    open(pp, "w").write(EVAL_PLAN)
    _t = read_(cp); open(cp, "w").write(_t.replace("envelope 900 cr", "envelope 9000 cr"))
    dec, why, _ = hook(env, IMG, B)
    check("the envelope raised after approval → deny (the key lines changed)", dec == "deny" and "key lines" in why, why)
    open(cp, "w").write(base_cp.replace("Tier:       evaluation\n", "").replace("Lane:       eval\n", ""))
    dec, why, _ = hook(env, IMG, A)
    check("the tier and lane lines removed → every spend denied (once evaluated, always evaluated)",
          dec == "deny" and "ran in the evaluation lane" in why, why)
    rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "ship the lane stills"], env)
    check("…and no approval is made there any more (export refused)", rc == 1 and "ran in the evaluation lane" in err, err)
    rc, out, err = run([GATE, "allow", "image", "--shots", "lane-a", "--by", "Dana", "--quote", "go ahead with these"], env)
    check("…and no allowance either", rc == 1 and "evaluation lane" in err, err)
    rc, out, err = run([os.path.join(HERE, "job_tier.py"), "check", os.path.join(job, "02-startframes", "lane-a_v1.png")], env)
    check("…and its media is still evaluation material (ship refusal)", rc == 1 and "evaluation lane" in out, out + err)
    # an evaluation job WITHOUT the lane line keeps the old behaviour: the script chain
    job2 = os.path.join(td, "fx-03002-eval-old")
    for d in ("00-brief", "01-script/prompts"):
        os.makedirs(os.path.join(job2, d))
    open(os.path.join(job2, "00-brief", "CHECKPOINT.md"), "w").write(
        base_cp.replace("fx-03001-eval", "fx-03002-eval-old").replace("Lane:       eval\n", ""))
    rc, out, err = run([GATE, "open", job2], env)
    f2 = os.path.join(job2, "01-script", "prompts", "lane-a.frame.prompt.md")
    open(f2, "w").write(FRAME_S.replace("shot: home-hero", "shot: lane-a").replace("aspect: 16:9", "aspect: 9:16")
                        .replace("[SUPPRESS]", "[SAFE ZONE]\nevery load-bearing element inside y=15-65%, x=11-72% of frame (the MEASURED ad safe box: top 15% profile row, bottom 35% captions + CTA, right 28% action rail)\n\n[SUPPRESS]")
                        .replace("text, logo, watermark, lens flare, people", "text, logo, lens flare, people"))
    run([LINT, f2], env)
    dec, why, _ = hook(env, IMG, A)
    check("`Tier: evaluation` without `Lane: eval` keeps the old chain (asks for the script or previz, not a plan)",
          dec in ("deny", "ask") and "`eval` is not approved" not in why, why)

    # per-stage-human: an ask reserves as PENDING; a declined ask stops counting after 30 minutes; two calls at once
    open(profile, "w").write(PROFILE.format(policy="per-stage-human"))
    job3 = os.path.join(td, "fx-03003-eval-ask")
    for d in ("00-brief", "01-script/prompts", "02-startframes"):
        os.makedirs(os.path.join(job3, d))
    cp3 = os.path.join(job3, "00-brief", "CHECKPOINT.md")
    open(cp3, "w").write(CHECKPOINT_EV.format(profile=profile, policy="per-stage-human").replace("fx-03001-eval", "fx-03003-eval-ask"))
    rc, out, err = run([GATE, "open", job3], env)
    check("a per-stage-human lane job opens", rc == 0, out + err)
    f3 = os.path.join(job3, "01-script", "prompts", "lane-a.frame.prompt.md")
    open(f3, "w").write(read_(os.path.join(job, "01-script", "prompts", "lane-a.frame.prompt.md")))
    run([LINT, f3], env)
    open(os.path.join(job3, "00-brief", "EVAL-PLAN.md"), "w").write(EVAL_PLAN.replace("Takes per shot: 4", "Takes per shot: 2"))
    rc, out, err = run([GATE, "approve", "eval", "--by", "Dana", "--quote", "run the ask test",
                        "--artifact", "00-brief/EVAL-PLAN.md"], env)
    dec, why, _ = hook(env, IMG, A)
    check("per-stage-human: the lane call asks", dec == "ask", why)
    rc, out, err = run([GATE, "approve", "eval", "--by", "Dana", "--quote", "run the ask test again",
                        "--artifact", "00-brief/EVAL-PLAN.md"], env)
    check("…an unreleased ask holds the plan fixed (no clock frees it)", rc == 1 and "plan is fixed" in err, err)
    led = os.path.join(job3, ".gate", "eval-ledger.jsonl")
    rows_ = [json.loads(l) for l in open(led) if l.strip()]
    check("…its reservation has an id and records that it asked", rows_ and rows_[-1].get("id") == "R1"
          and rows_[-1].get("asked") is True, str(rows_))
    rc, out, err = run([GATE, "release-take", "--why", "declined at the permission prompt", "--by", "Dana",
                        "--quote", "I declined that one"], env)
    check("release-take refuses without the person's words in the transcript", rc == 1 and "transcript" in err, err)
    _tp3 = os.path.join(td, "transcript-ev3.jsonl")
    open(_tp3, "w").write("".join(json.dumps({"type": "user", "message": {"role": "user", "content": q_}}) + "\n"
                                  for q_ in ("I declined that one", "I declined the repeat", "run the ask test again")))
    open(os.path.join(env["CINE_HOME"], "transcript-path"), "w").write(_tp3)
    REL = ["--by", "Dana", "--quote", "I declined that one"]
    rc, out, err = run([GATE, "release-take", "--why", "declined at the permission prompt"] + REL, env)
    check("release-take refuses a reservation young enough to be in flight", rc == 1 and "may still be running" in err, err)
    for r_ in rows_:
        r_["epoch"] = float(r_["epoch"]) - 4000
    open(led, "w").write("".join(json.dumps(r_) + "\n" for r_ in rows_))
    rc, out, err = run([GATE, "release-take", "--why", "declined at the permission prompt"] + REL, env)
    check("release-take releases a declined ask", rc == 0 and "RELEASED R1" in out, out + err)
    rc, out, err = run([GATE, "approve", "eval", "--by", "Dana", "--quote", "run the ask test again",
                        "--artifact", "00-brief/EVAL-PLAN.md"], env)
    check("a released ask no longer fixes the plan", rc == 0, out + err)
    import fcntl
    os.makedirs(os.path.join(job3, ".gate"), exist_ok=True)
    with open(os.path.join(job3, ".gate", "eval.lock"), "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        dec, why, _ = hook({**env, "CINE_EVAL_LOCK_WAIT": "0.5"}, IMG, A)
        fcntl.flock(lk, fcntl.LOCK_UN)
    check("while another call holds the ledger lock, a lane call is refused as busy (the check and the reservation "
          "are one locked step)", dec == "deny" and "ledger is busy" in why, why)
    payload = json.dumps({"session_id": "t", "hook_event_name": "PreToolUse", "tool_name": IMG,
                          "tool_input": {"params": A}})
    procs = [subprocess.Popen([PY, GATE, "hook"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=env) for _ in range(2)]
    outs = [p_.communicate(payload, timeout=60)[0] for p_ in procs]
    decs = sorted((json.loads(o_).get("hookSpecificOutput", {}).get("permissionDecision") or "pass") if o_.strip() else "allow"
                  for o_ in outs)
    check("two hooks at once with one call's takes left: one gets through, one is refused (the lock)",
          decs == ["ask", "deny"], str(decs) + " " + " | ".join(o_[:200] for o_ in outs))
    post3 = {"session_id": "t", "hook_event_name": "PostToolUse", "tool_name": IMG, "tool_input": {"params": A},
             "tool_response": {"job_id": "job_9a8b7c6d5e"}}
    run([GATE, "posthook"], env, stdin=json.dumps(post3))
    rows_ = [json.loads(l) for l in open(led) if l.strip()]
    for r_ in rows_:
        if r_.get("id"):
            r_["epoch"] = float(r_["epoch"]) - 4000      # old enough; the submission above is newer
    open(led, "w").write("".join(json.dumps(r_) + "\n" for r_ in rows_))
    _live = [r_ for r_ in rows_ if r_.get("id") and r_["id"] not in {x.get("release") for x in rows_}]
    rc, out, err = run([GATE, "release-take", "--id", _live[-1]["id"], "--why", "declined at the permission prompt"] + REL, env)
    check("release-take refuses a reservation a newer submission confirms (the call ran)", rc == 1 and "confirmed" in err, err)
    # a later ask of the SAME prompt is not confirmed by that earlier submission
    open(os.path.join(job3, "00-brief", "EVAL-PLAN.md"), "w").write(read_(os.path.join(job3, "00-brief", "EVAL-PLAN.md")))
    _l3 = os.path.join(job3, ".gate", "eval-ledger.jsonl")
    open(_l3, "a").write(json.dumps({"ts": "later", "epoch": time.time() + 10, "id": "R9", "tool": IMG,
                                    "units": {"lane-a": 2}, "credits": 4, "hashes": _live[-1]["hashes"]}) + "\n")
    _rows9 = [json.loads(l) for l in open(_l3) if l.strip()]
    for r_ in _rows9:
        if r_.get("id") == "R9":
            r_["epoch"] = time.time() - 1500
    open(_l3, "w").write("".join(json.dumps(r_) + "\n" for r_ in _rows9))
    _sp = os.path.join(job3, ".gate", "submitted.jsonl")                 # the earlier take, submitted before R9
    _srows = [json.loads(l) for l in open(_sp) if l.strip()]
    for r_ in _srows:
        r_["epoch"] = float(r_["epoch"]) - 3000
    open(_sp, "w").write("".join(json.dumps(r_) + "\n" for r_ in _srows))
    rc, out, err = run([GATE, "release-take", "--id", "R9", "--why", "declined the repeat take"] + REL, env)
    check("an earlier submission of the same prompt does not confirm a later, declined ask", rc == 0 and "RELEASED R9" in out,
          out + err)
    fail = {"session_id": "t", "hook_event_name": "PostToolUseFailure", "tool_name": IMG, "tool_input": {"params": A},
            "error": "HTTP 422 validation error: aspect_ratio"}
    open(_l3, "a").write(json.dumps({"ts": "now", "epoch": time.time() - 5000, "id": "R10", "tool": IMG,
                                    "units": {"lane-a": 2}, "credits": 4, "hashes": _live[-1]["hashes"]}) + "\n")
    run([GATE, "posthook", "--failed"], env, stdin=json.dumps(fail))
    _rel = {json.loads(l).get("release") for l in open(_l3) if l.strip()}
    check("an instant vendor rejection releases the call's reservation automatically", "R10" in _rel, str(_rel))
    open(_l3, "a").write(json.dumps({"ts": "now", "epoch": time.time() - 1300, "id": "R11", "tool": IMG,
                                    "units": {"lane-a": 2}, "credits": 4, "hashes": _live[-1]["hashes"]}) + "\n")
    run([GATE, "posthook", "--failed"], env, stdin=json.dumps({**fail, "error": "HTTP 402 insufficient credits"}))
    _rel = {json.loads(l).get("release") for l in open(_l3) if l.strip()}
    check("an 'insufficient credits' failure (it may have billed) releases nothing", "R11" not in _rel, str(_rel))
    run([GATE, "posthook"], env, stdin=json.dumps({**post3, "tool_response": {"status": "ok"}}))   # success, no id
    rc, out, err = run([GATE, "release-take", "--id", "R11", "--why", "declined the repeat take"] + REL, env)
    check("a success with no recognisable job id still confirms its reservation (no release)",
          rc == 1 and "confirmed" in err, out + err)
    rc, out, err = run([GATE, "status"], env)
    _u0 = out
    open(_l3, "a").write(json.dumps({"ts": "now", "epoch": time.time() - 3000, "id": "R12", "tool": IMG,
                                    "units": {"lane-b": 2}, "credits": 4, "hashes": ["hash-r12"]}) + "\n")
    rc, out, err = run([GATE, "release-take", "--id", "R12", "--why", "declined the repeat take"] + REL, env)
    rc2, out2, _ = run([GATE, "status"], env)
    open(os.path.join(job3, ".gate", "submitted.jsonl"), "a").write(
        json.dumps({"ts": "late", "epoch": time.time(), "tool": IMG, "hash": "hash-r12", "ids": ["j"], "credits": 4}) + "\n")
    rc3, out3, _ = run([GATE, "status"], env)
    check("a released call that bills anyway is counted again (its takes and credits come back)",
          rc == 0 and "lane-b" not in out2.split("takes")[-1].split("·")[0] and "lane-b 2" in out3, out2 + " || " + out3)
    os.remove(os.path.join(env["CINE_HOME"], "transcript-path"))
    open(profile, "w").write(PROFILE.format(policy="gated"))


def switches_suite(td: str, profile: str) -> None:
    """(v2.48.0, project switches) The optional `Switches:` line — a job lifts a named house rule, with a reason.
    Its own CINE_HOME, so it cannot lean on the video or stills job's state."""
    print("gate.py — project switches (v2.48.0)")
    env = {**os.environ, "CINE_HOME": os.path.join(td, "home-w"),
           "CINE_ARCHIVE": os.path.join(td, "archive-w")}
    env.pop("CINE_JOB", None); env.pop("CINE_GATE", None)
    open(profile, "w").write(PROFILE.format(policy="gated"))
    job = os.path.join(td, "fx-03001-switches")
    os.makedirs(os.path.join(job, "00-brief"))
    cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
    base = CHECKPOINT.format(profile=profile, policy="gated").replace("fx-01001-test", "fx-03001-switches")

    def write(sw=None):
        open(cp, "w").write(base if sw is None else base.replace("Skips:      none\n",
                                                                  f"Skips:      none\nSwitches:   {sw}\n"))

    def calls():
        return [hook(env, "mcp__Higgsfield__generate_video", {"model": "kling3_0", "prompt": "she turns"})[:2],
                hook(env, "mcp__Higgsfield__upscale_video", {"params": {}})[:2]]

    tpl = read_(os.path.join(ROOT, "assets", "checkpoint-template.md"))
    sys.path.insert(0, HERE)
    import gate as _g
    check("the template carries `Switches:   none` after `Skips:`, and its notes point at switches.py list",
          "Skips:      none\nSwitches:   none\n" in tpl and _g.parse_kv(tpl).get("switches") == "none"
          and "switches.py list" in tpl, tpl[-900:])
    write()
    rc, out, err = run([GATE, "open", job], env)
    check("a CHECKPOINT with no `Switches:` line (every job opened before 2.48) still opens — every house rule holds",
          rc == 0 and "OPEN:" in out and "project switches: none — every house rule holds" in out, out + err)
    check("(2.70.1) after open, the next step named is the concept, as START-HERE and `status` say",
          "next: approve the concept" in out and "next: approve the script" not in out, out)
    write("none")
    rc, out, err = run([GATE, "open", job], env)
    check("`Switches:   none` opens and says no house rule is lifted",
          rc == 0 and "OPEN:" in out and "project switches: none" in out, out + err)
    before = calls()
    write("music-led — the song is the deliverable;\n            speed-conform — lip-sync shot at 30 fps, conformed")
    rc, out, err = run([GATE, "open", job], env)
    check("two valid switches (one on a continuation line) open, and `open` prints each with its reason",
          rc == 0 and "project switches (2)" in out and "  music-led — the song is the deliverable" in out
          and "  speed-conform — lip-sync shot at 30 fps, conformed" in out, out + err)
    log = [json.loads(l) for l in read_(os.path.join(job, ".gate", "decisions.log")).splitlines() if l.strip()]
    rec = [r for r in log if r.get("kind") == "open"][-1]
    check("`open` records the switches in .gate/decisions.log",
          rec.get("switches") == {"music-led": "the song is the deliverable",
                                  "speed-conform": "lip-sync shot at 30 fps, conformed"}, str(rec))
    rc, out, err = run([GATE, "status"], env)
    check("`status` shows the switches, id and reason",
          rc == 0 and "project switches (2)" in out and "music-led — the song is the deliverable" in out
          and "changed since" not in out, out + err)
    rc, out, err = run([GATE, "status", "--json"], env)
    st = json.loads(out) if out.strip().startswith("{") else {}
    check("`status --json` carries the switches, as read now and as recorded at open",
          set(st.get("switches") or {}) == {"music-led", "speed-conform"}
          and st.get("switches_at_open") == st.get("switches"), out + err)
    rc, out, err = run([GATE, "session"], env, stdin="{}")
    check("the SessionStart summary names the switches by id",
          "project switches: music-led, speed-conform" in out, out + err)
    check("a valid switch changes no generate or spend decision (same verdict, same reason)",
          calls() == before and before[0][0] == "deny" and before[1][0] == "ask", str((before, calls())))
    write("music-led — the song is the deliverable")
    rc, out, err = run([GATE, "status"], env)
    check("a switch edited after `open` → status shows it as read now and warns it differs from the open record",
          "project switches (1)" in out and "switches changed since `open`" in out
          and "recorded then: music-led, speed-conform" in out, out + err)
    write("music-led — because")
    dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {"model": "kling3_0", "prompt": "she turns"})
    check("an invalid switch written after `open` → the hook denies like any broken line",
          dec == "deny" and "no longer validates" in why and "`Switches:`" in why, why)
    for sw, name, want in (
            ("grain-everywhere — the client loves film grain", "an unknown id → open REFUSED, naming the registry",
             ["not a switch in assets/project-switches.json", "known:"]),
            ("mask-wipe — the dancer reveals the next shot", "a locked id (mask-wipe) → open REFUSED, naming the rule",
             ["never a switch", "roto"]),
            ("motion-control — copy the dance for the launch", "motion-control (M3) → open REFUSED, naming the rule",
             ["never a switch", "M3"]),
            ("music-led", "a switch with no reason → open REFUSED", ["needs the form `<id> — <reason>`"]),
            ("music-led — because", "a one-word reason → open REFUSED", ["at least three words"]),
            ("<id> — <reason>", "the placeholder copied from the notes → open REFUSED", ["still carries a placeholder"])):
        write(sw)
        rc, out, err = run([GATE, "open", job], env)
        check(name, rc == 1 and "REFUSED" in out and "CHECKPOINT `Switches:`" in out
              and all(w in out for w in want), out + err)
    write()
    rc, out, err = run([GATE, "open", job], env)
    check("taking the line out again opens the job with every house rule holding",
          rc == 0 and "project switches: none" in out, out + err)


def export_switch_cases(job: str, env: dict) -> None:
    """(v2.48.0, project switches music-led and upload-master) What `approve export` reads from the two switches. Runs on
    the main job straight after its export is approved, so every other export check is already met and each case moves
    one thing; everything it adds is taken out again and the CHECKPOINT put back, so the cases after it see the job as
    it was."""
    print("gate.py — project switches at export (v2.48.0)")
    import hashlib
    sha = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
    cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
    base = read_(cp)
    hits_p, fit_p = (os.path.join(job, "07-edit", "music", n) for n in ("HITS.json", "FIT.json"))
    mf = os.path.join(job, "09-qa", "mix", "AUDIO-MANIFEST.md")
    sodir = os.path.join(job, "09-qa", "soundoff")
    proofs_p, log_p = os.path.join(sodir, "PROOFS.json"), os.path.join(sodir, "SOUNDOFF-LOG.jsonl")
    keep = {p: read_(p) for p in (hits_p, mf, proofs_p, log_p)}
    Q = [GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"]

    def switch(sw=None):
        open(cp, "w").write(base if sw is None else
                            base.replace("Skips:      none\n", f"Skips:      none\nSwitches:   {sw}\n"))

    # --- music-led: the song is fixed and is the deliverable; the picture is cut to it
    song = os.path.join(job, "06-music", "song.wav")
    os.makedirs(os.path.dirname(song), exist_ok=True)
    open(song, "wb").write(b"RIFF fixture: the client's song")
    open(mf, "a").write("| 06-music/song.wav | music | library:client | the client's own song, paid ads included | yes "
                        "| | | | | |\n")
    hits = {"music": "fit", "fps": 24, "duration": 15.0,
            "track": {"file": "06-music/song.wav", "vocals": "none", "edits_allowed": "no", "stems": "none"},
            "hits": [{"id": "BUTTON", "t": 11.0, "type": "button", "priority": "must", "want": "button"}],
            "speech": [], "approved_nudges": []}
    json.dump(hits, open(hits_p, "w"))
    switch()
    rc, out, err = run(Q, env)
    check("no switch: a declared track with no fit → export REFUSED as in 2.47.0, nothing lifted",
          rc == 1 and "the music is not fitted to the cut (music_fit.py check" in err
          and "no fit — `music_fit.py fit <job>`" in err and "lifted by project switch" not in err, err)
    # (2026-11-05, the author: the Python render is a preview; the deliverable is rebuilt in Resolve from the original)
    rb_p = os.path.join(job, "07-edit", "music", "REBUILD.json")
    made_ = [fit_p, rb_p, rb_p[:-5] + ".md", os.path.join(job, "07-edit", "resolve-production-console.music.py"),
             os.path.join(job, "07-edit", "timeline-dump.json")]
    json.dump({"fps": 24, "cuts_at_fit": [], "picked": 0, "plans": [{"plan": {
        "label": "the track", "track": "06-music/song.wav", "segments": [[0.0, 15.0]], "start": 0.0, "ratio": 1.0,
        "edits": []}, "hits": [], "map": ""}]}, open(fit_p, "w"))
    rc, out, err = run(Q, env)
    check("no switch: a fit with no REBUILD.json → export REFUSED, naming `rebuild` — never for want of a render",
          rc == 1 and "the music is not prepared for the Resolve rebuild — `music_fit.py rebuild <job>`" in err
          and "not rendered" not in err and "render <job>" not in err, err)
    rrc, rout, rerr = run([os.path.join(HERE, "music_fit.py"), "rebuild", job], env)
    rc, out, err = run(Q, env)
    check("no switch: `music_fit.py rebuild` and no render at all → export APPROVED, the measures waiting for the stem "
          "Resolve makes (a ♪ note)", rrc == 0 and os.path.isfile(rb_p) and rc == 0 and "APPROVED export" in out
          and "♪ the music is not measured" in err
          and not os.path.isfile(os.path.join(job, "06-music", "fit", "song.fit.wav")), rout + rerr + out + err)
    json.dump({"fps": 24, "tracks": {"audio5": [{"name": "song.fit.wav", "file": "/Volumes/jobs/fx/06-music/fit/song.fit.wav",
                                                 "start_s": 0.0, "duration_s": 15.0}]}},
              open(made_[-1], "w"))
    rc, out, err = run(Q, env)
    check("no switch: the timeline dump has the .fit.wav preview on A5 → export REFUSED, rebuild it in Resolve from the "
          "original", rc == 1 and "a preview render is on the timeline — rebuild it in Resolve from the original" in err,
          err)
    for f_ in made_:
        if os.path.isfile(f_):
            os.remove(f_)
    why = "the client's song is the deliverable"
    switch(f"music-led — {why}")
    rc, out, err = run(Q, env)
    check("music-led: the same job with no fit plan → export APPROVED, the lift printed with its reason",
          rc == 0 and "APPROVED export" in out and "♪ the music is not fitted to the cut — the song is fixed" in err
          and f"lifted by project switch `music-led` ({why})" in err, out + err)
    json.dump({"fps": 24, "cuts_at_fit": [], "picked": 0, "plans": [{"plan": {
        "label": "the track", "track": "06-music/song.wav", "segments": [[0.0, 15.15]], "start": 0.0, "ratio": 1.01,
        "edits": []}, "hits": [], "map": ""}]}, open(fit_p, "w"))
    json.dump(dict(hits, track=dict(hits["track"], edits_allowed="yes")), open(hits_p, "w"))
    rc, out, err = run(Q, env)
    check("music-led: the song stretched 1 % (inside the house cap, the licence allowing edits) → export REFUSED, the "
          "song plays at its own speed", rc == 1 and "music-led job's deliverable" in err
          and "the song is stretched" in err and "+1.00 %" in err, err)
    os.remove(fit_p)
    json.dump({"music": "none"}, open(hits_p, "w"))
    rc, out, err = run(Q, env)
    check("music-led with HITS.json music: none → export REFUSED as a contradiction",
          rc == 1 and "music: none" in err and "contradiction" in err, err)
    switch()
    open(hits_p, "w").write(keep[hits_p])
    open(mf, "w").write(keep[mf])
    os.remove(song)

    # --- upload-master: one extra upload copy beside the delivery, never in place of it
    exp = os.path.join(job, "10-export")
    master = os.path.join(exp, "fx-v4-final_9x16.mp4")
    up = os.path.join(exp, "fx-v4-final_9x16_2160.mp4")
    open(up, "wb").write(b"\x00\x00\x00\x18ftypmp42 fixture bytes, the 2160 upload copy")
    us = sha(up)
    uwhy = "the platform re-encodes 1080 uploads badly"
    open(up + ".qc.txt", "w").write(
        f"export_qc.py — fx-v4-final_9x16_2160.mp4\n{'=' * 60}\nfile_sha256: {us}\n"
        f"format: vertical-1080 · target duration: 15 s\n"
        f"upload master: the job's extra upload copy, not the delivery — realism-qa V15 lifted by project switch "
        f"`upload-master` ({uwhy}); the delivered file is QC'd against its preset without --upload-master\n"
        f"  [PASS] resolution: 2160x3840, an upload master\n{'-' * 60}\nOVERALL: PASS (1/1 checks passed)\n")
    for ext in (".mix.json", ".look.json"):                  # the checks after QC, met for the copy as for the delivery
        json.dump({"export_sha256": us, "verdict": "PASS", "checks": []}, open(up + ext, "w"))
    q = json.load(open(master + ".captions.qa.json"))
    json.dump(dict(q, render="10-export/fx-v4-final_9x16_2160.mp4", render_sha256=us), open(up + ".captions.qa.json", "w"))
    t1u = os.path.join(sodir, "fx-v4-final_9x16_2160.T1.mp4")
    open(t1u, "wb").write(b"\x00\x00\x00\x18ftypmp42 T1 proof of the upload copy")
    e = {"test": "T1", "stage": "export", "file": os.path.relpath(t1u, job), "sha256": sha(t1u),
         "source": "10-export/fx-v4-final_9x16_2160.mp4", "source_sha256": us}
    pr = json.loads(keep[proofs_p])
    pr["proofs"].append(e)
    json.dump(pr, open(proofs_p, "w"))
    open(log_p, "a").write(json.dumps({"test": "T1", "proof": e["file"], "proof_sha256": e["sha256"], "stage": "export",
                                       "source": e["source"], "source_sha256": us, "viewer": "producer",
                                       "verdict": "PASS", "beats": ["S1@0:01", "S3@0:07", "CTA@0:13"]}) + "\n")
    rc, out, err = run(Q, env)
    check("an upload-master report with no `upload-master` switch → export REFUSED, naming the switch and V15",
          rc == 1 and "is an upload master" in err and "does not lift `upload-master`" in err and "V15" in err
          and "is not the delivery" not in err, err)
    switch(f"upload-master — {uwhy}")
    parked = os.path.join(job, "fx-v4-final_9x16.parked")
    os.rename(master, parked)
    rc, out, err = run(Q, env)
    check("upload-master on, the upload copy alone in 10-export/ → export REFUSED: an upload copy is not the delivery",
          rc == 1 and "an upload copy is not the delivery" in err and "does not lift" not in err, err)
    os.rename(parked, master)
    rc, out, err = run(Q, env)
    check("upload-master on, the delivery alongside → export APPROVED, the upload copy printed as lifted",
          rc == 0 and "APPROVED export" in out and "NOTE (upload master) 10-export/fx-v4-final_9x16_2160.mp4" in err
          and "(the delivery: 10-export/fx-v4-final_9x16.mp4)" in err
          and f"lifted by project switch `upload-master` ({uwhy})" in err, out + err)
    for f in (up, up + ".qc.txt", up + ".mix.json", up + ".look.json", up + ".captions.qa.json", t1u):
        os.remove(f)
    for p in (proofs_p, log_p):
        open(p, "w").write(keep[p])
    switch()


def main() -> int:
    td = tempfile.mkdtemp(prefix="gate-test-")
    try:
        # ⛔ CINE_ARCHIVE too, or approving a fixture script files it into the SHIPPED recall
        # corpus — three of them were sitting in script-archive/ after one run, and a real
        # `ledger.py find` then reported ⛔ hits on videos that do not exist. In a query whose
        # whole value is that ⛔ means "go pull an ad", a fixture is not a harmless artefact.
        env = {**os.environ, "CINE_HOME": os.path.join(td, "home"),
               "CINE_ARCHIVE": os.path.join(td, "archive")}
        env.pop("CINE_JOB", None); env.pop("CINE_GATE", None)
        job = os.path.join(td, "fx-01001-test")
        for d in ("00-brief", "00-brief/_look", "01-script/prompts", "02-startframes", "05-voice"):
            os.makedirs(os.path.join(job, d))
        for i in range(1, 5):                      # the moodboard develop.py demands: real files
            open(os.path.join(job, "00-brief", "_look", f"ref{i}.jpg"), "wb").write(b"\xff\xd8\xff\x00")
            json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                       "clearance": "NOT CLEARED — outstanding"},
                      open(os.path.join(job, "00-brief", "_look", f"ref{i}.json"), "w"))
        profile = os.path.join(td, "fixture.md")
        open(profile, "w").write(PROFILE.format(policy="gated"))

        print("gate.py — end-to-end")
        # 0. the two normalisers are copies by charter; a drift between them fails every clip case
        sys.path.insert(0, HERE)
        import gate as _g, prompt_lint as _l
        tricky = "  a\n\n b\t\u201cc\u201d \u2014 d \u2019e\r\n"
        _src = read_(os.path.join(HERE, "gate.py"))
        _call = ('_refusals = _develop_module().approve_script_refusals(\n'
                 '                job.path, _ap, lambda q: quote_refusal(q, job) is None)')   # (3.1) verified (hookless: present)
        _i = _src.find(_call)
        _after = _src[_i + len(_call):].split("\n")[:8] if _i >= 0 else []
        _j = next((k for k, ln in enumerate(_after) if ln.strip() == "if _refusals:"), None)
        _hand = _i >= 0 and _j is not None and any(ln.strip() == "return 1" for ln in _after[_j + 1:_j + 4])
        # A TEXT check, not a run: a full 2.67 job through `approve script` is not built here. The decision itself is
        # tested in develop.py's self-test (approve_script_refusals); this pins the exact hand-over and its refusal.
        check("(2.67) approve script hands the signed file to develop.approve_script_refusals and refuses on any",
              bool(_hand) and _src.index("approve_script_refusals(") < _src.index("# ⛔ RUN THE CLAIMS LINT"),
              "the hand-over block in cmd_approve changed shape")
        check("gate.normalize_prompt == prompt_lint.normalize_prompt",
              _g.normalize_prompt(tricky) == _l.normalize_prompt(tricky) == 'a b "c" - d \'e')
        # 1. no job → deny everything, probes included
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {"model": "kling3_0", "prompt": "a fox"})
        check("no open job denies generate_video", dec == "deny" and "No production job" in why, why)
        dec, _, _ = hook(env, "mcp__Higgsfield__models_explore", {})
        check("non-generate tools pass silently", dec == "allow")
        dec, why, _ = hook(env, "mcp__Higgsfield__motion_control", {"params": {}})
        check("no open job denies a credit-spending non-generate tool too", dec == "deny", why)
        # 1b. ⛔ the claude.ai Higgsfield connector is served under its UUID, with no "higgsfield"
        # in the name — so the hook must be registered for THAT name, and for no other connector
        # (Figma's also serves a generate_image).
        HF = f"mcp__{SAMPLE}__generate_image"
        FIGMA = f"mcp__{SAMPLE_OTHER}__generate_image"
        check("gate.TOOL_RE reads the connector's generate_image as an image generate call",
              (_g.TOOL_RE.match(HF) or [None, None])[1] == "image")
        _hooks = json.load(open(os.path.join(ROOT, os.pardir, os.pardir, "hooks", "hooks.json"), encoding="utf-8"))
        _mt = [e.get("matcher") or "" for e in _hooks["hooks"]["PreToolUse"]]
        import re as _re
        check("a hooks.json PreToolUse matcher fullmatches the connector's tool name",
              any(_re.fullmatch(m, HF) for m in _mt), str(_mt))
        check("hooks.json's uuid matcher is exactly gate.connector_matcher() (built from the gate's own classes)",
              _g.connector_matcher() in _mt, str(_mt))
        check("(v2.61.0) it fires on every tool of a uuid connector, so a paid tool added later reaches the gate",
              all(any(_re.fullmatch(m, f"mcp__{SAMPLE_OTHER}__{x}") for m in _mt)
                  for x in ("clickup_create_task", "get_figma_skill", "a_paid_tool_added_tomorrow")))
        check("...and the gate lets another connector's ordinary tool through at once",
              all(_g.decide(f"mcp__{SAMPLE_OTHER}__{x}", {})["decision"] == "allow"
                  for x in ("clickup_create_task", "get_figma_skill")))
        # (v2.59.0) another service's generate_image now fires the hook: unnamed it asks, named as "other" it passes
        dec, why, _ = hook(env, FIGMA, {"prompt": "a diagram"})
        check("an unnamed uuid connector's generate_image → ask, naming the command that settles it",
              dec == "ask" and "gate.py connectors --other" in why, why)
        env_o = {**env, "CINE_OTHER_CONNECTORS": SAMPLE_OTHER}
        dec, why, _ = hook(env_o, FIGMA, {"prompt": "a diagram"})
        check("...named as another service (Figma), it passes silently, as before v2.59.0", dec == "allow", why)
        env_n = {k: v for k, v in env.items() if k != "CINE_HIGGSFIELD_CONNECTORS"}
        dec, why, _ = hook(env_n, HF, {"model": "nano_banana_pro", "prompt": "a roof"})
        check("with no connector settings at all, your Higgsfield connector's generate_image asks (never passes silently)",
              dec == "ask", why)
        rc, out, err = run([GATE, "connectors", "--other", SAMPLE_OTHER], env_n)
        check("(3.1.1) `--other` for a fresh uuid without the person's words is refused", rc == 1 and "owner's words" in err,
              out + err)
        _tpc = os.path.join(env_n["CINE_HOME"], "transcript-connectors.jsonl")
        open(_tpc, "w").write(json.dumps({"type": "user", "message": {"role": "user",
                                                                       "content": "that one is Figma, let it through"}}) + "\n"
                                                                       + json.dumps({"type": "user", "message": {"role": "user", "content": f"{SAMPLE_OTHER[:8]} is Figma, let it through"}}) + "\n")
        open(os.path.join(env_n["CINE_HOME"], "transcript-path"), "w").write(_tpc)
        rc, out, err = run([GATE, "connectors", "--other", SAMPLE_OTHER, "--quote", "not what they said"], env_n)
        check("(3.1.1) ...and with a quote that is not in the transcript", rc == 1 and "owner's words" in err, out + err)
        rc, out, err = run([GATE, "connectors", "--other", SAMPLE_OTHER, "--quote", "that one is Figma, let it through"], env_n)
        check("(3.1.1 build review) words in the transcript that do not name the connector are refused",
              rc == 1 and "naming it" in err, out + err)
        _seen = os.path.join(env_n["CINE_HOME"], "seen-connectors.json")
        _seen0 = open(_seen).read() if os.path.isfile(_seen) else None
        json.dump({SAMPLE_OTHER: {"tools": [f"mcp__{SAMPLE_OTHER}__shorts_studio_create"], "last": "x"}}, open(_seen, "w"))
        rc, out, err = run([GATE, "connectors", "--other", SAMPLE_OTHER, "--quote", f"{SAMPLE_OTHER[:8]} is Figma, let it through"], env_n)
        check("(3.1.1) a uuid seen serving a Higgsfield-only tool is refused as --other, even with the words",
              rc == 1 and "only Higgsfield serves" in err, out + err)
        if _seen0 is None:
            os.remove(_seen)
        else:
            open(_seen, "w").write(_seen0)
        rc, out, err = run([GATE, "connectors", "--higgsfield", SAMPLE, "--other", SAMPLE_OTHER, "--quote",
                            f"{SAMPLE_OTHER[:8]} is Figma, let it through"], env_n)
        dec, why, _ = hook(env_n, HF, {"model": "nano_banana_pro", "prompt": "a roof"})
        check("`gate.py connectors --higgsfield` writes the setting, and the call is gated again (no job → deny)",
              rc == 0 and dec == "deny" and "No production job" in why, out + err + why)
        dec, why, _ = hook(env_n, FIGMA, {"prompt": "a diagram"})
        check("...and `--other` lets that connector's generate_image through", dec == "allow", why)
        rc, out, err = run([GATE, "connectors", "--other", SAMPLE], env_n)
        dec, why, _ = hook(env_n, HF, {"model": "nano_banana_pro", "prompt": "a roof"})
        check("(v2.61.0) moving your Higgsfield connector to --other without the owner's words is refused, and it stays gated",
              rc == 1 and "needs the owner's words" in err and dec == "deny", out + err + why)
        os.remove(os.path.join(env_n["CINE_HOME"], "transcript-path")); os.remove(_tpc)   # later steps run without it
        rc, out, err = run([GATE, "connectors", "--higgsfield", "not-a-uuid"], env_n)
        check("`gate.py connectors` refuses something that is not a connector uuid", rc == 2 and "REFUSED" in err, out + err)
        os.remove(os.path.join(env_n["CINE_HOME"], "connectors.json"))
        dec, why, _ = hook(env, HF, {"model": "nano_banana_pro", "prompt": "a roof"})
        check("the connector's generate_image with no open job → deny", dec == "deny" and "No production job" in why, why)
        dec, why, _ = hook(env, f"mcp__{SAMPLE}__balance", {})
        check("the connector's read-only tools pass silently", dec == "allow", why)
        # 1c. ⛔ five connector tools that spend (or stage reference media) matched no gate class and
        # passed with no job open (found 2026-10-06). Through the hook, under both server names.
        for t in UNGATED_FIVE:
            for srv in ("Higgsfield", SAMPLE):
                dec, why, _ = hook(env, f"mcp__{srv}__{t}", {"action": "submit", "params": {}, "max_credits": 5}, raw=True)
                check(f"no open job denies {srv[:10]}…__{t}", dec == "deny" and "No production job" in why, why)
        for t in UNGATED_THREE:
            for srv in ("Higgsfield", SAMPLE):
                dec, why, _ = hook(env, f"mcp__{srv}__{t}", {"action": "create", "params": {}}, raw=True)
                check(f"no open job denies {srv[:10]}…__{t}", dec == "deny" and "No production job" in why, why)
        dec, why, _ = hook(env, f"mcp__{SAMPLE}__virality_predictor",
                           {"action": "preview", "params": {"model": "virality_predictor"}}, raw=True)
        check("virality_predictor preview (re-opens a dashboard) passes with no job", dec == "allow", why)
        dec, why, _ = hook(env, "mcp__Higgsfield__scene_builder_3d_generate_video", {"prompt": "x"}, raw=True)
        check("scene_builder_3d_generate_video with no job → deny (refused always)",
              dec == "deny" and "refused even inside" in why, why)
        BAI = f"mcp__{SAMPLE}__build_ai_influencer"
        dec, why, _ = hook(env, BAI, {"action": "quote", "tier": "normal"}, raw=True)
        check("build_ai_influencer quote (prices, spends nothing) passes with no job", dec == "allow", why)
        dec, why, _ = hook(env, BAI, {"action": "options"}, raw=True)
        check("build_ai_influencer options passes with no job", dec == "allow", why)
        dec, why, _ = hook(env, BAI, {"tier": "normal"}, raw=True)
        check("build_ai_influencer with no action fails closed → deny", dec == "deny", why)
        dec, why, _ = hook(env, f"mcp__{SAMPLE}__ads_studio_quote", {}, raw=True)
        check("ads_studio_quote (a price, no spend) still passes silently", dec == "allow", why)

        # 2. open without a checkpoint writes the template and refuses
        rc, out, err = run([GATE, "open", job], env)
        check("open with no checkpoint refuses and writes the template",
              rc == 1 and os.path.isfile(os.path.join(job, "00-brief", "CHECKPOINT.md")), out + err)
        rc, out, err = run([GATE, "open", job], env)
        check("open with the unfilled template refuses on placeholders", rc == 1 and "placeholder" in out, out)

        # 3. a skeleton profile must refuse: the policy is declared, one hard lock still reads NEEDS INPUT.
        #    (Until v2.53.0 this borrowed a real client's skeleton from the plugin's clients/. The plugin
        #    ships no real client now, so the fixture is written here.)
        cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
        skeleton = os.path.join(td, "skeleton.md")
        sk_txt = PROFILE.format(policy="per-stage-human").replace(
            "4. **Retired tools/models?** none", "4. **Retired tools/models?** NEEDS INPUT")
        assert "NEEDS INPUT" in sk_txt
        open(skeleton, "w").write(sk_txt)
        open(cp, "w").write(CHECKPOINT.format(profile=skeleton, policy="per-stage-human"))
        rc, out, err = run([GATE, "open", job], env)
        check("a skeleton profile refuses (NEEDS INPUT in section 0)",
              rc == 1 and "unanswered" in out, out)

        # 3b. what the plugin's own clients/ folder ships (v2.53.0): templates, `_lab`, one invented
        #     sample, and no real client. The sample is the filled-in example, so it must stay complete:
        #     a `Client:` written as `clients/acme.md` resolves to it and opens.
        shipped = sorted(f for f in os.listdir(os.path.join(os.path.dirname(HERE), "clients")))
        allowed = {"_INDEX.md", "_STYLE-GUIDE-TEMPLATE.md", "_TEMPLATE.md", "_lab.md", "acme.md",
                   "costs._TEMPLATE.json", "costs.acme.json", "script._TEMPLATE.json", "script.acme.json"}
        check("the plugin's clients/ holds the templates, _lab and the invented sample, and nothing else",
              set(shipped) == allowed, f"unexpected: {sorted(set(shipped) - allowed)} missing: {sorted(allowed - set(shipped))}")
        #     Its own copy of the job and its own CINE_HOME, so the steps below see no state from it.
        job_s = os.path.join(td, "sample", os.path.basename(job))
        shutil.copytree(job, job_s)
        env_s = {k: v for k, v in env.items() if k != "CINE_CLIENTS"}
        env_s["CINE_HOME"] = os.path.join(td, "home-sample")
        open(os.path.join(job_s, "00-brief", "CHECKPOINT.md"), "w").write(
            CHECKPOINT.format(profile="clients/acme.md", policy="per-stage-human"))
        rc, out, err = run([GATE, "open", job_s], env_s)
        check("the shipped sample client resolves from the plugin's clients/ and opens (section 0 complete)",
              rc == 0 and "OPEN:" in out, out + err)

        # 4. missing profile refuses with the ask-never-assume line
        open(cp, "w").write(CHECKPOINT.format(profile="clients/nobody.md", policy="gated"))
        rc, out, err = run([GATE, "open", job], env)
        check("missing profile refuses", rc == 1 and "no such profile" in out, out)

        # 5. policy disagreement refuses
        open(cp, "w").write(CHECKPOINT.format(profile=profile, policy="standing"))
        rc, out, err = run([GATE, "open", job], env)
        check("checkpoint policy ≠ profile policy refuses", rc == 1 and "disagrees" in out, out)

        # 6. a complete checkpoint opens
        open(cp, "w").write(CHECKPOINT.format(profile=profile, policy="gated"))
        rc, out, err = run([GATE, "open", job], env)
        check("complete checkpoint opens the job", rc == 0 and "OPEN:" in out, out + err)
        check("APPROVALS.md was created", os.path.isfile(os.path.join(job, "00-brief", "APPROVALS.md")))

        # 7. job open, nothing approved / linted, and no previz lane → deny, naming BOTH the
        #    production path and the development one, because an image at this moment is neither
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image", {"model": "nano_banana_pro", "prompt": "a host"})
        check("open job, no script approval, no previz lane → deny, and says which two things it is not",
              dec == "deny" and "neither concept art nor a start frame" in why
              and "previz lane" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {"model": "kling3_0", "prompt": "she turns"})
        check("a VIDEO with no script approval and no linted prompt still denies the old way",
              dec == "deny" and "`script` is not approved" in why and "matches no linted" in why, why)
        # 7b. the PREVIZ lane — concept art before the concept is signed
        rc, out, err = run([GATE, "previz", "--budget", "3", "--why", "concept art"], env)
        check("previz with a label instead of a reason → refused",
              rc == 1 and "five words or more" in err, err)
        rc, out, err = run([GATE, "previz", "--budget", "99",
                            "--why", "which of C1 and C2 survives being looked at"], env)
        check("previz above the hard cap → refused", rc == 1 and "1..12" in err, err)
        _look = os.path.join(job, "00-brief", "_look")
        _stash = os.path.join(td, "_look-stashed")
        shutil.move(_look, _stash)                 # the board is filled by the develop fixture
        os.makedirs(_look)
        rc, out, err = run([GATE, "previz", "--budget", "2",
                            "--why", "which of C1 and C2 survives being looked at"], env)
        check("previz before the look board is filled → refused, and says why that order matters",
              rc == 1 and "look board has 0" in err
              and "before looking at photographs of the real thing" in err, err)
        shutil.rmtree(_look); shutil.move(_stash, _look)
        rc, out, err = run([GATE, "previz", "--budget", "2",
                            "--why", "which of C1 and C2 survives being looked at"], env)
        check("previz opens once the real photographs are on disk", rc == 0 and "previz lane" in out, out + err)
        check("and it says plainly that these are not start frames", "NOT start frames" in out, out)
        rc, out, _ = run([GATE, "hook"], env, stdin=json.dumps({"hook_event_name": "PreToolUse",
                          "tool_name": "mcp__Higgsfield__generate_image",
                          "tool_input": {"params": {"model": "nano_banana_pro", "prompt": "a dark bakery before opening"}}}))
        check("(build review 2) a previz call with no session_id is denied", '"deny"' in out, out)
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_image",
                             {"model": "nano_banana_pro", "prompt": "a dark bakery before opening"})
        check("an image with no linted prompt now PASSES as previz, and is labelled previz",
              dec == "pass" and "PREVIZ 1/2" in ctx and "NOT a start frame" in ctx, f"{dec} {why} {ctx}")
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_image",
                             {"model": "kling3_0", "prompt": "a dark bakery"})
        check("previz still holds the roster — a video model is refused",
              dec == "deny" and "does not look like an image model" in why, why)
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_image",
                             {"model": "nano_banana_pro", "prompt": "one loaf on a steel bench"})
        check("the second previz image spends the lane", dec == "pass" and "PREVIZ 2/2" in ctx, ctx)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image",
                           {"model": "nano_banana_pro", "prompt": "a third look"})
        check("past the budget → refused, and says to look at what came back first",
              dec == "deny" and "spent" in why and "Look at what came back" in why, why)
        rc, out, err = run([GATE, "previz", "--status"], env)
        check("previz --status reports the lane", "previz 2/2" in out, out + err)
        # a previz image can never become an approved frame
        pv = os.path.join(job, "00-brief", "_previz"); os.makedirs(pv, exist_ok=True)
        open(os.path.join(pv, "C2-open.png"), "wb").write(b"\x89PNG\r\n\x1a\n")
        rc, out, err = run([GATE, "approve", "frame:S3", "--by", "Dana", "--quote",
                            "that frame is right, go", "--artifact", os.path.join(pv, "C2-open.png"),
                            "--media-id", "media_x"], env)
        check("a previz image offered as an approved frame → REFUSED",
              rc == 1 and "_previz" in err and "never a frame anything is conformed to" in err, err)

        dec, _, ctx = hook(env, "mcp__Higgsfield__generate_image", {"model": "nano_banana_pro", "prompt": "x", "get_cost": True})
        check("cost probe passes once a job is open (no pre-approval, context only)", dec == "pass" and "probe" in ctx, ctx)

        # 8. DEVELOPMENT — the creative gate, before the concept and before the script
        DEV = os.path.join(job, "00-brief", "DEVELOPMENT.md")
        sp = os.path.join(job, "01-script", "SCRIPT-test-v3.md"); open(sp, "w").write(SCRIPT)
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "yes, v3 is approved",
                            "--artifact", "01-script/SCRIPT-test-v3.md"], env)
        check("script before concept → refused (chain order)", rc == 1 and "needs concept approved" in err, err)
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana", "--quote", "go with C2"], env)
        check("concept with no DEVELOPMENT.md → refused", rc == 1 and "DEVELOPMENT.md" in err, err)
        rc, out, err = run([DEVELOP, "init", job], env)
        check("develop.py init writes the template", rc == 0 and os.path.isfile(DEV), out + err)
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana", "--quote", "go with C2"], env)
        check("concept with the unfilled template → refused", rc == 1 and "CONCEPTS" in err, err)
        # one idea written five times must not pass
        one = dev_doc(full=False)
        for img, st, q in [("a bottle on a steel bench", "demo", "What does grade actually mean?"),
                           ("a buyer's spreadsheet", "list", "Which supplier survives an audit?"),
                           ("hands sorting olives", "single-take monologue", "Who picks these?"),
                           ("an empty shelf", "testimonial-shaped", "Why did the last shipment fail?")]:
            one = one.replace(f"question: {q}", "question: Can origin be proven?").replace(
                f"image: {img}", "image: a grove at dawn")
        open(DEV, "w").write(one)
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana", "--quote", "go with C2"], env)
        check("five rewordings of one concept → refused", rc == 1 and "share the same" in err, err)
        # a round that killed nothing must not pass
        nokill = dev_doc(full=False).replace("killed: C3 — the claim needs a document nobody has\n", "") \
            .replace("weakened: C1 — the proof is thin\n", "")
        open(DEV, "w").write(nokill)
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana", "--quote", "go with C2"], env)
        check("an adversarial round that killed nothing → refused", rc == 1 and "killed nothing" in err, err)
        # the real thing, concept phase
        open(DEV, "w").write(dev_doc(full=False))
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana", "--quote", "go with C2, the bench one"], env)
        check("a complete development doc with NO concept board → still refused",
              rc == 1 and "concept board is not current" in err and "has not been built" in err, err)
        run([BOARD, "concepts", job], env)
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana", "--quote", "go with C2, the bench one"], env)
        check("concept approved once the doc is complete AND the board was built",
              rc == 0 and "APPROVED concept" in out, out + err)
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "yes, v3 is approved",
                            "--artifact", "01-script/SCRIPT-test-v3.md"], env)
        check("script with no hooks and one draft → refused", rc == 1 and ("HOOKS" in err or "DRAFTS" in err), err)
        open(DEV, "w").write(dev_doc())
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "ok"], env)
        check("one-word quote refused", rc == 1 and "verbatim" in err, err)
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "yes, v3 is approved"], env)
        check("script approval without --artifact refused", rc == 1 and "--artifact" in err, err)
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "yes, v3 is approved",
                            "--artifact", "01-script/SCRIPT-test-v3.md"], env)
        check("script approved with 5 hooks, 3 drafts and 2 critiques behind it",
              rc == 0 and "APPROVED script" in out, out + err)
        rc, out, err = run([GATE, "approve", "brief", "--by", "Dana", "--quote", "the brief is fine, go",
                            "--artifact", "01-script/SCRIPT-test-v3.md"], env)
        check("`approve brief` on a Mode A job → REFUSED (it is the stills lane's approval)",
              rc == 1 and "stills lane" in err and "Mode A" in err, err)

        # 8a. ⛔ THE CLIENT'S CLAIMS CATEGORY MUST REACH THE LINT. Two independent defects meant it
        # never did: cmd_approve never called job.validate(), so job.fields/profile_path were empty
        # and the profile was never read; and the regex did not match the profile's real markdown.
        # The visible symptom of both was a clean pass — a mattress script with an unqualified
        # "Made in USA" (16 CFR §323.2, a $753,000 FTC action against a direct competitor) was
        # APPROVED. Only the universal rules were firing, which is why it looked like it worked.
        catf = os.path.join(job, "01-script", "SCRIPT-test-cat.md")
        open(catf, "w").write("# SCRIPT cat\n\nS1  HOST: Proudly made in America.\n"
                              "S3  HOST: We taste it before you ever see it.\n")
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "yes, cat is approved",
                            "--artifact", "01-script/SCRIPT-test-cat.md"], env)
        check("a CATEGORY-specific BLOCK is caught, so the client profile actually reached the lint",
              rc == 1 and "claims_lint found" in err and "323.2" in err, err[:300])

        # 8b. THE LEDGER — the approval must leave a queryable record, and the recall corpus must
        # populate itself. Before 2026-09-08 claims_lint ran here, printed, and was forgotten, so
        # "which shipped videos contain this claim" had no mechanism at all.
        REC = os.path.join(job, "00-brief", "RECORD.json")
        check("approving writes the ledger record without a second command", os.path.isfile(REC), REC)
        rec = json.loads(open(REC, encoding="utf-8").read()) if os.path.isfile(REC) else {}
        check("...and its state is derived from the approvals, not typed",
              rec.get("state") == "script" and rec.get("approved") == ["concept", "script"], str(rec.get("state")))
        cl = rec.get("claims") or {}
        check("...and the claims check is persisted with the artifact it ran on",
              cl.get("artifact") == "01-script/SCRIPT-test-v3.md" and cl.get("disclosure") == "NOT ASSERTED",
              str(cl)[:200])
        arch = cl.get("archived_to") or ""
        check("...and the approved script archives itself into the recall corpus",
              arch and os.path.isfile(arch) and "same grove" in open(arch, encoding="utf-8").read(), arch)
        rc, out, err = run([LEDGER, "find", os.path.dirname(job), "--claim", "same grove", "--json"], env)
        found = json.loads(out) if out.strip().startswith("{") else {}
        check("RECALL: a phrase in a shipped script finds its video",
              rc == 0 and len(found.get("videos") or []) == 1
              and found["videos"][0]["job"] == "fx-01001-test", out[:200] + err[:200])
        check("...and the recall reports what it searched, so a miss is not mistaken for absence",
              (found.get("searched") or {}).get("archived_scripts", 0) >= 1, str(found.get("searched")))
        rc, out, err = run([LEDGER, "find", os.path.dirname(job), "--claim", "zqx-not-present", "--json"], env)
        check("...and a phrase that is not there exits 1 rather than 0", rc == 1, out[:120])
        rc, out, err = run([LEDGER, "index", os.path.dirname(job), "--json"], env)
        check("the index finds the job by walking the root",
              rc == 0 and any(r.get("job") == "fx-01001-test" for r in json.loads(out or "[]")),
              out[:200] + err[:200])
        rc, out, err = run([LEDGER, "index", os.path.dirname(job), "--persona", "P9", "--json"], env)
        check("...and filtering on an absent persona returns nothing, exit 1", rc == 1, out[:120])

        # ⛔ --allow was named in gate.py's own refusal text and did not exist as a flag, so a
        # client-approved phrase could never pass. It must work AND leave the approver's name.
        bad = os.path.join(job, "01-script", "SCRIPT-test-v4.md")
        open(bad, "w").write("# SCRIPT v4\n\nS1  HOST: this permanently fixes your sleep.\n"
                             "S3  HOST: We taste it before you ever see it.\n")
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana", "--quote", "yes, v4 is approved",
                            "--artifact", "01-script/SCRIPT-test-v4.md"], env)
        # ⛔ this assertion must not be satisfiable by the fixture failing to trip a BLOCK — the
        # first version used a WARN-only phrase, so both checks short-circuited to True and the
        # suite printed a green line having tested nothing.
        check("a BLOCK-level claim is refused (the precondition --allow is for)",
              rc == 1 and "claims_lint found" in err, err[:200])
        rc2, out2, err2 = run([GATE, "approve", "script", "--by", "Dana", "--quote", "yes, v4 is approved",
                               "--artifact", "01-script/SCRIPT-test-v4.md",
                               "--allow", "permanently", "--allow", "fixes your"], env)
        check("--allow lets client-approved phrases through (the flag the refusal text promised)",
              rc2 == 0 and "APPROVED script" in out2, err2[:220])
        rec = json.loads(open(REC, encoding="utf-8").read())
        check("...and the allowed phrases are on the record with who allowed them",
              (rec.get("claims") or {}).get("allowed") == ["permanently", "fixes your"]
              and (rec.get("claims") or {}).get("allowed_by") == "Dana",
              str(rec.get("claims"))[:220])
        check("...and the earlier check is kept in claims_history, not overwritten",
              len(rec.get("claims_history") or []) >= 1, str(rec.get("claims_history"))[:160])

        # a killed script must stop vanishing
        rc, out, err = run([LEDGER, "kill", job, "--by", "Dana"], env)
        check("kill without a reason is refused", rc == 2 and "--why" in err, err[:120])
        rc, out, err = run([LEDGER, "kill", job, "--by", "Dana", "--why", "client killed the angle"], env)
        check("kill is recorded and beats the approvals", rc == 0 and
              json.loads(open(REC, encoding="utf-8").read())["state"] == "killed", out + err)
        # ...and it must not be a one-way door for the fixture's remaining checks
        rec = json.loads(open(REC, encoding="utf-8").read())
        rec["events"] = [e for e in rec["events"] if e.get("kind") != "kill"]
        open(REC, "w", encoding="utf-8").write(json.dumps(rec))

        # 9. audio: line must be in the approved script, voice must be chosen
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio",
                           {"model": "seed_audio", "prompt": "Buy now, limited offer!", "voice_id": "v1", "voice_type": "preset"})
        check("VO text outside the approved script → deny", dec == "deny" and "not one spoken line of the approved script" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio",
                           {"model": "seed_audio", "prompt": "We taste it before you ever see it."})
        check("VO with no voice_id → deny", dec == "deny" and "no voice chosen" in why, why)
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_audio",
                             {"model": "seed_audio", "prompt": "We taste it before you ever see it.", "voice_id": "v1", "voice_type": "preset"})
        check("VO of a script line with a voice → pass", dec == "pass" and "GATE OK" in ctx, why)
        # 9b. text2speech_v2: the engine is vendor-REQUIRED (models_explore, 2026-09-30) — the gate
        # used to refuse the only call the vendor accepts
        LINE = "We taste it before you ever see it."
        t2s = {"model": "text2speech_v2", "prompt": LINE, "variant": "elevenlabs",
               "voice_type": "preset", "voice_id": "v1"}
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_audio", t2s)
        check("text2speech_v2 + variant elevenlabs + voice → pass", dec == "pass" and "GATE OK" in ctx, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio", {k: v for k, v in t2s.items() if k != "variant"})
        check("text2speech_v2 without variant → deny, naming the engines",
              dec == "deny" and "needs `variant`" in why and "elevenlabs" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio", {**t2s, "variant": "eleven_labs"})
        check("text2speech_v2 with an invented engine → deny", dec == "deny" and "not an engine" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio", {k: v for k, v in t2s.items() if k != "voice_type"})
        check("text2speech_v2 without voice_type → deny", dec == "deny" and "needs `voice_type`" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio",
                           {"model": "seed_audio", "prompt": LINE, "voice_id": "v1", "voice_type": "preset",
                            "variant": "elevenlabs"})
        check("variant on seed_audio → deny (it is text2speech_v2's switch)",
              dec == "deny" and "engine switch" in why, why)

        # 10. frame prompt: lint, then the hook matches the hash
        fp = os.path.join(job, "01-script", "prompts", "S3.frame.prompt.md"); open(fp, "w").write(FRAME)
        rc, out, err = run([LINT, fp], env)
        check("a frame whose reference was never sourced → lint FAILS before a credit is spent",
              rc == 1 and "not found" in out, out)
        os.makedirs(os.path.join(job, "_reference", "wardrobe"), exist_ok=True)
        ref = os.path.join(job, "_reference", "wardrobe", "apron.jpg")
        open(ref, "wb").write(b"\xff\xd8 fixture")
        rc, out, err = run([LINT, fp], env)
        check("sourced but with no provenance sidecar → lint FAILS",
              rc == 1 and "no provenance sidecar" in out, out)
        PROV = os.path.join(HERE, "provenance.py")
        rc, out, err = run([PROV, "record", ref, "--source", "client-supplied"], env)
        check("a client-supplied asset with no --holder → provenance REFUSED",
              rc == 1 and "--holder" in err, err)
        rc, out, err = run([PROV, "record", ref, "--source", "client-supplied",
                            "--holder", "Fixture Brand"], env)
        check("provenance written, but unanswered blockers → NOT CLEARED",
              rc == 0 and "NOT CLEARED" in out and "unanswered" in out, out + err)
        rc, out, err = run([LINT, fp], env)
        check("an UNCLEARED asset → lint FAILS (stock-sourcing §5)", rc == 1 and "NOT CLEARED" in out, out)
        rc, out, err = run([PROV, "record", ref, "--source", "client-supplied", "--holder", "Fixture Brand",
                            "--face", "none", "--trademark", "none", "--property", "none",
                            "--transformation", "none", "--cleared-by", "Dana", "--force"], env)
        check("`--transformation none` is refused as an answer",
              "transformation" in out and "NOT CLEARED" in out, out + err)
        rc, out, err = run([PROV, "record", ref, "--source", "client-supplied", "--holder", "Fixture Brand",
                            "--face", "none", "--trademark", "owned:Fixture Brand's own mark",
                            "--property", "none",
                            "--transformation", "composited onto a generated bench and regraded",
                            "--cleared-by", "Dana", "--force"], env)
        check("all four blockers answered + signed → CLEARED", rc == 0 and "CLEARED by Dana" in out, out + err)
        rc, out, err = run([PROV, "audit", os.path.join(job, "_reference")], env)
        check("provenance audit reports the set as cleared", rc == 0 and "0 not cleared" in out, out)
        with open(ref, "ab") as fh:
            fh.write(b" edited after the record was written")
        rc, out, err = run([PROV, "audit", os.path.join(job, "_reference")], env)
        check("an asset changed after its record → audit flags FILE CHANGED",
              "FILE CHANGED" in out, out)
        rc, out, err = run([PROV, "record", ref, "--source", "client-supplied", "--holder", "Fixture Brand",
                            "--face", "none", "--trademark", "owned:Fixture Brand's own mark",
                            "--property", "none",
                            "--transformation", "composited onto a generated bench and regraded",
                            "--cleared-by", "Dana", "--force"], env)
        rc, out, err = run([LINT, fp], env)
        check("a CLEARED asset → lint PASSES without reference-only", rc == 0, out)
        rc, out, err = run([LINT, fp], env)
        check("frame prompt lints", rc == 0 and "LINT PASS" in out, out + err)
        sc = json.load(open(fp[:-3] + ".ok"))
        prompt = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip()
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_image", {"model": "nano_banana_pro", "prompt": prompt, "aspect_ratio": "9:16"})
        check("linted frame prompt, right model → pass", dec == "pass" and "S3 frame" in ctx, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image", {"model": "soul_2", "prompt": prompt})
        check("linted prompt with a different model → deny", dec == "deny" and "≠ linted" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image", {"model": "nano_banana_pro", "prompt": prompt + " extra word"})
        check("edited prompt text → deny", dec == "deny" and "matches no linted" in why, why)
        open(fp, "a").write("\n")  # touch the file after lint
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image", {"model": "nano_banana_pro", "prompt": prompt})
        check("prompt file edited after lint → deny as stale", dec == "deny" and "edited after its lint" in why, why)
        run([LINT, fp], env)

        # 11. clip prompt: needs the start frame on disk, then approval, then the media bound
        cl = os.path.join(job, "01-script", "prompts", "S3.clip.prompt.md"); open(cl, "w").write(CLIP)
        # the coverage floor: S3 speaks, so S3 owes a listener reaction (direction.md §3). Without
        # it `approve clips` refuses — which is the point of the check, and is asserted below.
        REACT = (CLIP.replace("shot: S3", "shot: S3-R").replace("type: dialogue", "type: reaction")
                 .replace('line: "We taste it before you ever see it."\n', "")
                 .replace("vo: 05-voice/S3.wav\n", ""))
        rc, out, err = run([LINT, cl], env)
        check("clip prompt without the still on disk fails lint", rc == 1 and "not found under the job" in out, out)
        open(os.path.join(job, "02-startframes", "S3_host_v2.png"), "wb").write(b"\x89PNG\r\n fixture")
        open(os.path.join(job, "05-voice", "S3.wav"), "wb").write(b"RIFF fixture")
        rc, out, err = run([LINT, cl], env)
        check("clip prompt lints once the still exists", rc == 0, out + err)
        cprompt = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip()
        check("[SUPPRESS] stays out of the prompt text", "head bobbing" not in cprompt and "[SUPPRESS]" not in cprompt)
        vparams = {"model": "minimax_h3", "prompt": cprompt, "duration": 6, "aspect_ratio": "9:16"}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vparams)
        check("clip before the frame gate → deny", dec == "deny" and "start frame for S3 is not approved" in why, why)
        rc, out, err = run([GATE, "approve", "frame:S3", "--by", "Dana", "--quote", "S3 v2, the left one",
                            "--artifact", "02-startframes/S3_host_v2.png"], env)
        check("frame approval without --media-id refused", rc == 1 and "--media-id" in err, err)
        rc, out, err = run([GATE, "approve", "frame:S3", "--by", "Dana", "--quote", "S3 v2, the left one",
                            "--artifact", "02-startframes/S3_host_v2.png", "--media-id", "job_abc123"], env)
        check("frame approved with artifact + media id", rc == 0, out + err)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vparams)
        check("clip that does not bind the approved frame → deny", dec == "deny" and "does not bind the approved start frame" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**vparams, "duration": 8, "medias": [{"role": "image", "value": "job_abc123"}]})
        check("clip with a different duration → deny", dec == "deny" and "duration 8s" in why, why)
        good = {**vparams, "medias": [{"role": "image", "value": "job_abc123"}]}
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_video", good)
        check("clip with linted prompt + approved frame bound → pass (gated)", dec == "pass" and "S3 clip" in ctx, why)
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_video_batch", [{"index": 3, "params": good}, {"index": 4, "params": {**good, "model": "kling3_0"}}], batch=True)
        check("batch: one good, one wrong model → deny names request[1]", dec == "deny" and "request[1]" in why and "request[0]" not in why, why)

        # 11a. (v2.66.0) the picture sign-offs, in a job made from the 2.65 development template. This job's
        # DEVELOPMENT.md predates the mark, so the mark is written in here and taken out at the end: everything
        # above ran under the old chain, which is exactly what a job in production keeps.
        import storyboard as _sb
        dev_p = os.path.join(job, "00-brief", "DEVELOPMENT.md")
        dev_before = read_(dev_p)
        rc, out, err = run([GATE, "status"], env)
        check("an older job's status does not name the storyboard as next", "approve storyboard" not in out, out)
        open(dev_p, "w").write("<!-- develop-template: 2.65 -->\n" + dev_before)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image", {"model": "nano_banana_pro", "prompt": prompt})
        check("(2.66) a 2.65-template job: a linted, approved-script frame is denied until the storyboard is signed",
              dec == "deny" and "`storyboard` is not approved" in why and "animatic.py" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", good)
        check("(2.66) ...and so is the clip", dec == "deny" and "`storyboard` is not approved" in why, why)
        rc, out, err = run([GATE, "status"], env)
        check("(2.66) status names the storyboard as the next sign-off", "approve storyboard" in out, out)
        rc, out, err = run([GATE, "approve", "cast", "--by", "Dana", "--quote", "the cast is right"], env)
        check("(2.66) `cast` before the storyboard is refused on order", rc == 1 and "needs storyboard" in err, err)
        rc, out, err = run([GATE, "approve", "frame:S3", "--by", "Dana", "--quote", "S3 v2, the left one",
                            "--artifact", "02-startframes/S3_host_v2.png", "--media-id", "job_abc123"], env)
        check("(2.66) so is a start frame", rc == 1 and "needs storyboard" in err, err)
        rc, out, err = run([GATE, "approve", "storyboard", "--by", "Dana", "--quote", "the storyboard works for me"], env)
        check("(2.66) `storyboard` with no shot list is refused, naming shotlist.py",
              rc == 1 and "not ready to sign" in err and "shotlist.py" in err, err)
        sl_txt = _sb.FIXTURE.replace("- 2: 01-script/storyboard/their/hands.png: \"like my gran's hands\"",
                                     "skipped: \"go with your drawings this time\"")
        open(_sb.shotlist_path(job), "w").write(sl_txt)
        rc, out, err = run([GATE, "approve", "storyboard", "--by", "Dana", "--quote", "the storyboard works for me"], env)
        check("(2.66) a shot list with no page and no animatic is refused, naming both builders",
              rc == 1 and "board.py storyboard" in err and "animatic.py" in err, err)
        rc, out, err = run([BOARD, "storyboard", job], env)
        check("(2.66) board.py storyboard builds the page", rc == 0 and "storyboard" in out, out + err)
        rc, out, err = run([os.path.join(HERE, "animatic.py"), job], env)
        if rc != 0 and "ffmpeg is not on PATH" in err:          # a machine with no ffmpeg: write what it would write
            mp4 = os.path.join(job, _sb.ANIMATIC_REL); open(mp4, "wb").write(b"no ffmpeg here")
            json.dump({"film_digest": _sb.digest(sl_txt), "mp4": _sb.ANIMATIC_REL, "mp4_sha256": _sb.sha256_file(mp4)},
                      open(os.path.join(job, _sb.ANIMATIC_JSON_REL), "w"))
        else:
            check("(2.66) animatic.py builds the reel", rc == 0 and "7.5 s" in out, out + err)
        rc, out, err = run([GATE, "approve", "storyboard", "--by", "Dana", "--quote", "the storyboard works for me"], env)
        apv_rows = _sb._approval_rows(job)
        check("(2.66) page + animatic from this shot list → storyboard approved, the shot list recorded as the artifact",
              rc == 0 and apv_rows[-1]["stage"] == "storyboard"
              and apv_rows[-1]["artifact"].endswith(os.path.basename(_sb.shotlist_path(job))), out + err)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image", {"model": "nano_banana_pro", "prompt": prompt})
        check("(2.66) the frame passes once the storyboard is signed", dec == "pass", why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", good)
        check("(2.66) the clip is still denied: frame:S3 was approved and the frames were never signed side by side",
              dec == "deny" and "not signed side by side since frame:S3" in why, why)
        rc, out, err = run([GATE, "approve", "startframes", "--by", "Dana", "--quote", "the frames hold together"], env)
        check("(2.66) `startframes` with no frame sheet is refused, naming board.py frames",
              rc == 1 and "board.py frames" in err, err)
        rc, out, err = run([BOARD, "frames", job], env)
        rc, out, err = run([GATE, "approve", "startframes", "--by", "Dana", "--quote", "the frames hold together"], env)
        check("(2.66) the sheet of the approved frames → startframes approved", rc == 0, out + err)
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_video", good)
        check("(2.66) ...and the clip passes", dec == "pass" and "S3 clip" in ctx, why)
        # a retake: the same shot, a new picture and media id, approved after the sheet was signed
        good_r = {**vparams, "medias": [{"role": "image", "value": "job_retake9"}]}
        rc, out, err = run([GATE, "approve", "frame:S3", "--by", "Dana", "--quote", "S3 v2, the left one",
                            "--artifact", "02-startframes/S3_host_v2.png", "--media-id", "job_retake9"], env)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", good_r)
        check("(2.66) a retake frame approved after the sheet → its clip is denied until the sheet is signed again",
              rc == 0 and dec == "deny" and "not signed side by side" in why, out + err + why)
        rc, out, err = run([GATE, "approve", "startframes", "--by", "Dana", "--quote", "the frames hold together"], env)
        check("(2.66) ...and the old sheet cannot be re-signed: it shows a different set", rc == 1 and "different set" in err, err)
        rc, out, err = run([BOARD, "frames", job], env)
        rc, out, err = run([GATE, "approve", "startframes", "--by", "Dana", "--quote", "the frames hold together"], env)
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_video", good_r)
        check("(2.66) rebuilt and re-signed → the retake's clip passes", rc == 0 and dec == "pass", out + err + why)
        open(_sb.shotlist_path(job), "w").write(sl_txt.replace("| 3.5 |", "| 2.0 |"))
        rc, out, err = run([GATE, "approve", "storyboard", "--by", "Dana", "--quote", "the storyboard works for me"], env)
        check("(2.66) re-signing after a duration changed is refused until the page and animatic are rebuilt",
              rc == 1 and "different shot list" in err, err)
        # back to the old chain, and the original S3 frame, for everything below
        open(dev_p, "w").write(dev_before)
        rc, out, err = run([GATE, "approve", "frame:S3", "--by", "Dana", "--quote", "S3 v2, the left one",
                            "--artifact", "02-startframes/S3_host_v2.png", "--media-id", "job_abc123"], env)
        check("(2.66) the old chain again: frame:S3 re-approved with no storyboard question asked", rc == 0, out + err)

        # 11b. variants, unlintable spend tools, publishing
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "count": 3})
        check("count above the linted variants → deny", dec == "deny" and "exceeds the linted" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__upscale_video", {"params": {"model": "x"}})
        check("unlintable spend tool inside a job → ask", dec == "ask" and "carries no prompt" in why, why)
        for t in UNGATED_FIVE:
            for srv in ("Higgsfield", SAMPLE):
                dec, why, _ = hook(env, f"mcp__{srv}__{t}", {"action": "submit", "params": {}, "max_credits": 5}, raw=True)
                if t == "shorts_studio_create_preset":
                    check(f"inside a job: {t} ({srv[:10]}…) → ask, named as a no-credit stage",
                          dec == "ask" and "client-approved" in why and "carries no prompt" not in why, why)
                else:
                    check(f"inside a job: {t} ({srv[:10]}…) → ask", dec == "ask" and "carries no prompt" in why, why)
        for t in UNGATED_THREE:
            dec, why, _ = hook(env, f"mcp__Higgsfield__{t}", {"action": "create", "params": {}}, raw=True)
            check(f"inside a job: {t} → ask", dec == "ask" and "carries no prompt" in why, why)
        for srv in ("Higgsfield", SAMPLE):
            dec, why, _ = hook(env, f"mcp__{srv}__scene_builder_3d_generate_video",
                               {"prompt": "x", "resolution": "1080p"}, raw=True)
            check(f"inside a job: scene_builder_3d_generate_video ({srv[:10]}…) → still deny, names the route",
                  dec == "deny" and "generate_video with seedance_2_5" in why, why)
        dec, why, _ = hook(env, f"mcp__{SAMPLE}__build_ai_influencer",
                           {"action": "recreate", "job_id": "0c0c0c0c-0000-4000-8000-000000000003"}, raw=True)
        check("inside a job: build_ai_influencer recreate (no generation) → allow, no prompt", dec == "allow", why)
        dec, why, _ = hook(env, "mcp__Higgsfield__tiktok_publish", {})
        check("publish without export approval → deny", dec == "deny" and "`export`" in why, why)
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export before lock, music and titles → refused", rc == 1 and "needs lock, music, titles approved first" in err, err)
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock before clips → refused", rc == 1 and "needs clips approved" in err, err)
        # --- the reference plan gate: `clips` unlocks motion spend, so nothing may be unsourced ---
        gapshot = os.path.join(job, "01-script", "prompts", "S9.frame.prompt.md")
        open(gapshot, "w").write(
            "---\nshot: S9\nkind: frame\nmodel: nano_banana\naspect: 9:16\nrefs:\n"
            "  - role: image, what: environment, need: rustic kitchen window light\n"
            "---\n[SUBJECT]\nA baker slides a tray forward\n\n[ENVIRONMENT]\n"
            "A small tiled kitchen, flour on the counter\n\n[LIGHTING]\n5200K window light\n\n"
            "[CAMERA]\n35mm eye level\n")
        run([BOARD, "shots", job], env)
        rc, out, err = run([GATE, "approve", "clips", "--by", "Dana", "--quote", "the selects are right, cut it"], env)
        check("clips with an unsourced reference → refused",
              rc == 1 and "reference plan is not sourced" in err and "S9" in err, err)
        adopted_dir = os.path.join(job, "_reference", "environment")
        os.makedirs(adopted_dir, exist_ok=True)
        open(os.path.join(adopted_dir, "kitchen.jpg"), "wb").write(b"\xff\xd8\xff\x00")
        json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                   "clearance": "NOT CLEARED — outstanding"},
                  open(os.path.join(adopted_dir, "kitchen.json"), "w"))
        _t = open(gapshot).read()                 # read THEN truncate — open(w) truncates first
        open(gapshot, "w").write(_t.replace("need: rustic kitchen window light",
                                            "file: _reference/environment/kitchen.jpg"))
        rc, out, err = run([GATE, "approve", "clips", "--by", "Dana", "--quote", "the selects are right, cut it"], env)
        check("an adopted-but-uncleared reference is still refused",
              rc == 1 and "NOT CLEARED" in err, err)
        _t = open(gapshot).read()
        open(gapshot, "w").write(_t.replace(
            "file: _reference/environment/kitchen.jpg",
            "file: _reference/environment/kitchen.jpg, use: reference-only"))
        rc, out, err = run([GATE, "approve", "clips", "--by", "Dana", "--quote", "the selects are right, cut it"], env)
        check("a scene that speaks and has no reaction → clips REFUSED",
              rc == 1 and "listener reaction" in err, err)
        rct = os.path.join(job, "01-script", "prompts", "S3-R.clip.prompt.md")
        open(rct, "w").write(REACT)
        # ⛔ the world (2026-10-27, lab-00020): an exterior is designed once and approved before its frames
        WORLD = os.path.join(HERE, "world.py")
        rc, out, err = run([WORLD, "init", job, "--location", "GROVE"], env)
        check("world.py init writes a card to fill", rc == 0 and os.path.isfile(os.path.join(job, "00-brief", "world",
                                                                                             "GROVE.world.json")), out + err)
        rc, out, err = run([GATE, "approve", "world:GROVE", "--artifact", "00-brief/world/GROVE.world.json", "--by", "Dana",
                            "--quote", "the grove world is right"], env)
        check("approve world: on an unfilled card → refused, naming world.py check", rc == 1 and "world card does not hold" in err, err)
        sys.path.insert(0, HERE)
        import world as _WDT
        json.dump(_WDT._good_card("GROVE"), open(os.path.join(job, "00-brief", "world", "GROVE.world.json"), "w"))
        rc, out, err = run([GATE, "approve", "world:GROVE", "--artifact", "00-brief/world/GROVE.world.json", "--by", "Dana",
                            "--quote", "the grove world is right"], env)
        check("approve world: on a card that holds → approved", rc == 0, out + err)
        rc, out, err = run([GATE, "approve", "clips", "--by", "Dana", "--quote", "the selects are right, cut it"], env)
        check("sourced + reference-only + the coverage floor → clips approved", rc == 0, err)
        os.remove(gapshot)
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock with no QA log → refused", rc == 1 and "QA-LOG" in err, err)
        os.makedirs(os.path.join(job, "09-qa"), exist_ok=True)
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write(
            "# QA\n| ts | shot | verdict | observation |\n| t | S3 | PASS | heard 'taste' on the third beat |\n")
        # ⛔ motion QA (2026-10-26, "Refuse picture lock without it"): the passed shot has no motion
        # report and the cut no joins report → refused, naming both; a report about other bytes is stale
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock with a QA log but no motion analysis → refused, naming the shot and the joins",
              rc == 1 and "motion analysis" in err and "S3: no motion report" in err and "no joins report" in err, err)
        import hashlib as _h
        mdir = os.path.join(job, "09-qa", "motion"); os.makedirs(mdir, exist_ok=True)
        os.makedirs(os.path.join(job, "03-clips"), exist_ok=True)
        s3 = os.path.join(job, "03-clips", "S3_v1.mp4"); open(s3, "wb").write(b"\x00\x00\x00\x18ftypmp42 S3 take")
        json.dump({"shot": "S3", "file": "03-clips/S3_v1.mp4", "sha256": "0" * 64},
                  open(os.path.join(mdir, "S3.motion.json"), "w"))
        open(os.path.join(mdir, "cut_v1.joins.json"), "w").write('{"cut_sha256": "x", "joins": []}')
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock with a motion report about other bytes → refused as stale",
              rc == 1 and "changed after it was measured" in err, err)
        json.dump({"shot": "S3", "file": "03-clips/S3_v1.mp4", "sha256": _h.sha256(open(s3, "rb").read()).hexdigest()},
                  open(os.path.join(mdir, "S3.motion.json"), "w"))
        # ⛔ the title card (house rule C3, 2026-10-26): every project has one — the permission list for titles
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock with no title card → refused, naming title_card.py propose",
              rc == 1 and "title card" in err and "propose" in err, err)
        TCARD = os.path.join(HERE, "title_card.py")
        rc, out, err = run([TCARD, "propose", job, "--lane", "captions-only"], env)
        check("title_card.py propose writes a captions-only card", rc == 0, out + err)
        # ⛔ aerials (house rule 2026-10-26, C4/C5): a course card with no numbers and no seeds refuses lock;
        # with it gone the lock goes through
        FLY = os.path.join(HERE, "flyover.py")
        rc, out, err = run([FLY, "course", "init", job, "--name", "A spec course", "--holes", "2"], env)
        check("flyover.py course init writes a private course card", rc == 0 and os.path.isfile(os.path.join(job, "00-brief", "COURSE.json")), out + err)
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock with an unfilled course card → refused, naming the aerial rules",
              rc == 1 and "aerial rules" in err and "hole 1: no par" in err and "RIGHTS.md" in err, err)
        os.rename(os.path.join(job, "00-brief", "COURSE.json"), os.path.join(job, "00-brief", "COURSE.json.parked"))
        # ⛔ the sound-off read (2026-10-27, jury K1): advisory before lock, except a beat the picture does not carry
        sodir = os.path.join(job, "09-qa", "soundoff"); os.makedirs(sodir, exist_ok=True)

        def story_map(carries):
            json.dump({"version": 1, "mode": "full", "windows": "manual", "timeline_sha256": None, "beats": [
                {"id": "S1", "n": 1, "kind": "scene", "t0": 0.0, "t1": 6.0, "shows": "a grove at dawn, hands on the bark",
                 "carries": "Y", "fix": "", "waiver": None},
                {"id": "S3", "n": 2, "kind": "scene", "t0": 6.0, "t1": 12.0, "shows": "she lifts the glass and inhales, eyes on us",
                 "carries": carries, "fix": "" if carries == "Y" else "an insert of the pour", "waiver": None},
                {"id": "CTA", "n": 3, "kind": "cta", "t0": 12.0, "t1": 15.0, "shows": "the bottle and the end card",
                 "carries": "Y", "fix": "", "waiver": None}]}, open(os.path.join(sodir, "STORY-MAP.json"), "w"))
        story_map("N")
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock with a beat the picture does not carry → refused, naming the beat (K1)",
              rc == 1 and "does not read without sound" in err and "beat S3" in err, err)
        story_map("Y")
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "picture is locked, go to mix"], env)
        check("picture lock with clips + a QA log + current motion and joins reports + a title card → approved, the "
              "sound-off read a note", rc == 0 and "NOTE (sound-off)" in err, out + err)
        run([GATE, "approve", "music", "--by", "Dana", "--quote", "track 4, the slow one"], env)
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export before titles → refused", rc == 1 and "needs titles approved first" in err, err)
        tdir = os.path.join(job, "07-edit", "titles"); os.makedirs(tdir, exist_ok=True)
        json.dump({"id": "T1", "kind": "hero", "duration_s": 3, "content": {"lines": ["Sleep well"]}},
                  open(os.path.join(tdir, "T1.title.json"), "w"))
        rc, out, err = run([GATE, "approve", "titles", "--by", "Dana", "--quote", "the titles read well on the phone"], env)
        check("approve titles with a title the card does not permit → refused",
              rc == 1 and "not on the title card" in err, err)
        os.remove(os.path.join(tdir, "T1.title.json"))
        rc, out, err = run([GATE, "approve", "titles", "--by", "Dana", "--quote", "the titles read well on the phone"], env)
        check("approve titles on a captions-only card with no titles → approved", rc == 0, out + err)
        # ⛔ nobody has watched the FILM yet — every row in that log is about one clip
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with no master-gate row → refused", rc == 1 and "master-gate PASS" in err, err)
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "a").write(
            "| t | FILM | master | PASS | room tone holds under the 0:12 cut, heard 'taste' clean; "
            "1-frame flash on the incoming shot at 0:24 |\n")
        # ⛔ …and nobody has measured the FILE. The refusal said "run export_qc.py first"; the gate never
        # checked. No export, no report, a FAIL, a skipped check, a replaced render → all refused.
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("a watched cut with nothing in 10-export → refused", rc == 1 and "10-export" in err, err)
        exp = os.path.join(job, "10-export")
        os.makedirs(exp, exist_ok=True)
        master = os.path.join(exp, "fx-v4-final_9x16.mp4")
        open(master, "wb").write(b"\x00\x00\x00\x18ftypmp42 fixture bytes")
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("an export with no QC report → refused", rc == 1 and "no QC report" in err, err)
        import hashlib
        sha = hashlib.sha256(open(master, "rb").read()).hexdigest()

        def qc_report(verdict, digest, skipped=False):
            open(master + ".qc.txt", "w").write(
                f"export_qc.py — fx-v4-final_9x16.mp4\n{'=' * 60}\nfile_sha256: {digest}\n"
                f"  [PASS] resolution\n{'-' * 60}\nOVERALL: {verdict} (1/1 checks passed)\n"
                + ("(Duration and/or fps checks were skipped — pass --target-duration/--fps to include them.)\n"
                   if skipped else ""))
        for verdict, digest, skipped, needle, name in (
                ("FAIL", sha, False, "OVERALL: PASS", "a FAIL report"),
                ("PASS", sha, True, "skipped", "a report that skipped duration/fps"),
                ("PASS", "0" * 64, False, "changed after it was measured", "a PASS about different bytes")):
            qc_report(verdict, digest, skipped)
            rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
            check(f"export with {name} → refused", rc == 1 and needle in err, err)
        qc_report("PASS", sha)
        # ⛔ the mix (2026-10-26): a passing export_qc report is the file's level, not whether the line is heard
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with no mix report and no audio manifest → refused, naming both",
              rc == 1 and "no mix report" in err and "no audio manifest" in err, err)
        json.dump({"export_sha256": sha, "verdict": "FAIL", "checks": [{"name": "VO over bed", "status": "FAIL"}]},
                  open(master + ".mix.json", "w"))
        mf = os.path.join(job, "09-qa", "mix", "AUDIO-MANIFEST.md"); os.makedirs(os.path.dirname(mf), exist_ok=True)
        open(mf, "w").write("| file | role | source | licence | paid ads | tool | version | plan | region | approved |\n"
                            "|---|---|---|---|---|---|---|---|---|---|\n"
                            "| 05-voice/S3.wav | vo | ai:elevenlabs | ElevenLabs terms | yes | ElevenLabs | eleven_v3 | "
                            "free | RO | |\n")
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with a failing mix and a free-plan AI voice → refused, naming both",
              rc == 1 and "the mix FAILS — VO over bed" in err and "BLOCKED" in err, err)
        json.dump({"export_sha256": sha, "verdict": "PASS", "checks": []}, open(master + ".mix.json", "w"))
        _m = read_(mf)
        open(mf, "w").write(_m.replace("| free |", "| creator |"))
        # ⛔ the look (2026-10-26): tags, legal levels, 45+ legibility and the platform round trip
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with a cleared mix but no look report → refused, naming look_qa.py",
              rc == 1 and "no look report" in err and "look_qa.py export" in err, err)
        json.dump({"export_sha256": sha, "verdict": "FAIL", "checks": [{"name": "range and tags", "status": "FAIL"},
                                                                     {"name": "banding", "status": "PASS"}]},
                  open(master + ".look.json", "w"))
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with a failing look → refused, naming the failing check only",
              rc == 1 and "the look FAILS — range and tags" in err and "banding" not in err, err)
        json.dump({"export_sha256": "0" * 64, "verdict": "PASS", "checks": []}, open(master + ".look.json", "w"))
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with a passing look report about other bytes → refused as stale",
              rc == 1 and "changed after its look was measured" in err, err)
        json.dump({"export_sha256": sha, "verdict": "PASS", "checks": []}, open(master + ".look.json", "w"))
        # ⛔ the music to picture (2026-10-26): `approve music` comes before the lock, so nothing checked the bed
        # against the locked cut — no plan, a stale rebuild (2026-11-05: the render is a preview), a cut moved without
        # an approved nudge
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with no music plan → refused, naming music_fit.py and hits init",
              rc == 1 and "music is not fitted" in err and "hits init" in err, err)
        mdir = os.path.join(job, "07-edit", "music")
        os.makedirs(mdir, exist_ok=True)
        json.dump({"music": "none"}, open(os.path.join(mdir, "HITS.json"), "w"))
        # ⛔ the sound-off check (2026-10-27): T2 by a cold viewer, the retell first; T1 on every delivery file
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with every check but the sound-off one → refused, naming T2 and T1",
              rc == 1 and "sound-off check is not done" in err and "T2:" in err and "T1:" in err, err)
        srcf = os.path.join(sodir, "fx-v4-picture-only.mp4"); open(srcf, "wb").write(b"\x00\x00\x00\x18ftypmp42 picture only")
        t2p = os.path.join(sodir, "fx-v4-picture-only.T2.mp4"); open(t2p, "wb").write(b"\x00\x00\x00\x18ftypmp42 T2 proof")
        t1p = os.path.join(sodir, "fx-v4-final_9x16.T1.mp4"); open(t1p, "wb").write(b"\x00\x00\x00\x18ftypmp42 T1 proof")
        H = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
        T2E = {"test": "T2", "stage": "export", "file": os.path.relpath(t2p, job), "sha256": H(t2p),
               "source": os.path.relpath(srcf, job), "source_sha256": H(srcf)}
        T1E = {"test": "T1", "stage": "export", "file": os.path.relpath(t1p, job), "sha256": H(t1p),
               "source": "10-export/fx-v4-final_9x16.mp4", "source_sha256": sha}
        json.dump({"version": 1, "proofs": [T2E, T1E], "t2_source": T2E["source"]}, open(os.path.join(sodir, "PROOFS.json"), "w"))
        row = lambda e, **k: json.dumps(dict({"test": e["test"], "proof": e["file"], "proof_sha256": e["sha256"],
                                              "stage": "export", "source": e["source"], "source_sha256": e["source_sha256"]}, **k))
        open(os.path.join(sodir, "SOUNDOFF-LOG.jsonl"), "w").write("\n".join([
            row(T2E, viewer="producer", verdict="PASS", beats=["S1@0:01", "S3@0:07", "CTA@0:13"])]) + "\n")
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with a producer-only T2 PASS → refused: T2 needs someone who has not read the script (K3)",
              rc == 1 and "has not read the" in err and "cold-viewer" in err, err)
        open(os.path.join(sodir, "SOUNDOFF-LOG.jsonl"), "a").write("\n".join([
            row(T2E, viewer="cold", who="Ana", verdict="RETELL", retell="an olive grove, a woman tastes the oil, then the bottle"),
            row(T2E, viewer="cold", who="Ana", verdict="PASS", beats=["S1@0:01", "S3@0:07", "CTA@0:13"]),
            row(T1E, viewer="producer", verdict="PASS", beats=["S1@0:01", "S3@0:07", "CTA@0:13"])]) + "\n")
        # ⛔ captions made in Resolve (house rule C7, 2026-10-27): shown in the pixels of the delivery file, not assumed
        os.makedirs(os.path.join(job, "08-captions"), exist_ok=True)
        srt_ = os.path.join(job, "08-captions", "fx-v4.srt")
        open(srt_, "w").write("1\n00:00:00,500 --> 00:00:03,000\nEvery loaf here is shaped\nbefore six.\n")
        run([os.path.join(HERE, "srt_qa.py"), "check", srt_], env)
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export with captions burned in Resolve and no pixel check → refused, naming srt_qa.py burned (C7)",
              rc == 1 and "srt_qa.py burned" in err and "native.py check" in err, err)
        json.dump({"render": "10-export/fx-v4-final_9x16.mp4", "render_sha256": sha, "plate": os.path.relpath(srcf, job),
                   "plate_sha256": H(srcf), "srt": "08-captions/fx-v4.srt", "srt_sha256": H(srt_), "verdict": "FAIL",
                   "cues": [{"n": 1, "t": 1.45, "status": "FAIL", "note": "no caption in the pixels"}]},
                  open(master + ".captions.qa.json", "w"))
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("…a pixel check that found no caption → refused, naming the cue", rc == 1 and "cue 1 at 1.45 s" in err, err)
        json.dump({"render": "10-export/fx-v4-final_9x16.mp4", "render_sha256": sha, "plate": os.path.relpath(srcf, job),
                   "plate_sha256": H(srcf), "srt": "08-captions/fx-v4.srt", "srt_sha256": H(srt_), "verdict": "PASS",
                   "cues": [{"n": 1, "t": 1.45, "status": "PASS", "note": ""}]}, open(master + ".captions.qa.json", "w"))
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "final v4 is signed off, publish it"], env)
        check("export after lock + music + a watched cut + passing QC, mix and look reports on these bytes + a "
              "clean audio manifest + a declared music plan (none) + the sound-off check on these bytes → approved, "
              "noting no bed and the next step (the pack)",
              rc == 0 and "no music bed" in err and "no composer's brief" in err and "soundoff.py pack" in err, out + err)
        export_switch_cases(job, env)        # (v2.48.0, project switches music-led and upload-master)
        dec, why, _ = hook(env, "mcp__Higgsfield__tiktok_publish", {})
        check("publish with export approval → ask", dec == "ask", why)
        os.rename(os.path.join(job, "00-brief", "COURSE.json.parked"), os.path.join(job, "00-brief", "COURSE.json"))
        dec, why, _ = hook(env, "mcp__Higgsfield__tiktok_publish", {})
        check("publish of a private course spec → deny, even with export approved (C5)", dec == "deny" and "C5" in why, why)
        os.remove(os.path.join(job, "00-brief", "COURSE.json"))
        dec, why, _ = hook(env, "mcp__Higgsfield-Second__execute_preset",
                           {"preset_id": "1ac7759b-7df1-4c96-a97a-baf611f7d38e", "inputs": {}}, raw=True)
        check("inside a job: the Earth Zoom preset → deny, reference only", dec == "deny" and "reference only" in why and "ruling" not in why, why)
        dec, _, _ = hook(env, "mcp__Higgsfield__show_generations", {})
        check("read-only Higgsfield tool passes silently", dec == "allow")

        # 11a2. the DaVinci Resolve MCP (2026-09-14) — the server inside Resolve Studio 21.1. Nothing it
        # does spends credits, and two of Resolve's own features route around gates this skill has.
        def rhook(tool, script=None):
            payload = {"session_id": "t", "hook_event_name": "PreToolUse", "tool_name": tool,
                       "tool_input": {"script": script, "timeout": 10} if script is not None else {}}
            _rc, _out, _err = run([GATE, "hook"], env, stdin=json.dumps(payload))
            if not _out.strip():
                return "allow", _err
            h = json.loads(_out).get("hookSpecificOutput", {})
            return (h.get("permissionDecision") or ("pass" if h.get("additionalContext") else "allow"),
                    (h.get("permissionDecisionReason") or "") + (h.get("additionalContext") or ""))
        dec, why = rhook("mcp__DaVinci_Resolve__get_resolve_status")
        check("Resolve read-only tool passes silently", dec == "allow", why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "p = resolve.GetProjectManager().GetCurrentProject()\np.StartRendering([])\n")
        check("run_script that STARTS a render → deny", dec == "deny" and "STARTS a render" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script", "project.GenerateSpeech({'TextInput': 'hi'})\n")
        check("run_script calling Resolve's AI Speech Generator → deny (the voice gate)",
              dec == "deny" and "stage 6" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script", "tl = project.GetCurrentTimeline()\n"
                                                              "tl.CreateSubtitlesFromAudio()\n")
        check("run_script auto-captioning from audio → deny (locked script)", dec == "deny" and "LOCKED" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "# this never calls StartRendering() — a person does\nx = 'GenerateSpeech('\n"
                         "result = project.GetName()\n")
        check("a call named only in a comment or a string is not a call → allow", dec == "allow", why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "project.SetRenderSettings({'TargetDir': '/tmp'})\nproject.AddRenderJob()\n")
        check("render settings → ask, naming the crash history", dec == "ask" and "crash_archive" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "tl = project.GetCurrentTimeline()\ntl.AddMarker(10, 'Blue', 'b', '', 1, '')\n")
        check("an ordinary timeline edit → pass with context", dec == "pass" and "Resolve edit" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script", "getattr(project, 'Start' + 'Rendering')([])\n")
        check("a call hidden behind getattr → ask, and the gate says it cannot read it",
              dec == "ask" and "getattr" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script_unsafe", "result = project.GetName()\n")
        check("run_script_unsafe → ask even when it only reads", dec == "ask" and "run_script_unsafe" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__delete_lut")
        check("LUT/DCTL writes and deletes → ask", dec == "ask", why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script", "")
        check("run_script with no script → deny (fails closed)", dec == "deny", why)
        # ⚡ the Resolve allowance (2026-10-28: "stop asking me to approve every script for Davinci, do it in a
        # batch, like with AI gens")
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "project.SetRenderSettings({'TargetDir': '/tmp'})\nproject.AddRenderJob()\n")
        check("before an allowance, render settings ask and name `gate.py allow resolve`",
              dec == "ask" and "allow resolve" in why, why)
        _tp = os.path.join(td, "transcript-allow.jsonl")       # (v2.61.0) an allowance needs the owner's words on record
        open(_tp, "w").write("".join(json.dumps({"type": "user", "message": {"role": "user", "content": s}}) + "\n" for s in (
            "do it in a batch", "do it in a batch, like with AI gens", "go ahead with S9 and two regens",
            "go ahead, S3 and two regens")))
        open(os.path.join(env["CINE_HOME"], "transcript-path"), "w").write(_tp)
        rc, out, err = run([GATE, "allow", "resolve", "--scope", "edit,teleport", "--by", "Dana", "--quote",
                            "do it in a batch"], env)
        check("allow resolve: an unknown scope is refused, listing the four", rc == 1 and "unknown scope" in err
              and "luts" in err, err)
        rc, out, err = run([GATE, "allow", "resolve", "--scripts", "2", "--by", "Dana", "--quote",
                            "do it in a batch, like with AI gens"], env)
        check("allow resolve records one approval for the session's edits and render queuing",
              rc == 0 and "RESOLVE ALLOWANCE R1" in out and "edit, render" in out, out + err)
        os.remove(os.path.join(env["CINE_HOME"], "transcript-path"))   # later approvals here run with no transcript
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "tl = project.GetCurrentTimeline()\ntl.AddMarker(10, 'Blue', 'b', '', 1, '')\n")
        check("…an edit now goes through pre-approved, naming the allowance", dec == "allow" and "pre-approved" in why
              and "R1" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "project.SetRenderSettings({'TargetDir': '/tmp'})\nproject.AddRenderJob()\n")
        check("…render settings too, the crash note still carried", dec == "allow" and "crash_archive" in why, why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script", "project.DeleteTimelines([tl])\n")
        check("…a delete still asks every time", dec == "ask", why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script", "p = resolve.GetProjectManager().GetCurrentProject()\n"
                                                              "p.StartRendering([])\n")
        check("…starting a render is still denied", dec == "deny", why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script_unsafe", "result = project.GetName()\n")
        check("…run_script_unsafe is outside the default scopes: it asks", dec == "ask", why)
        dec, why = rhook("mcp__DaVinci_Resolve__run_script",
                         "tl = project.GetCurrentTimeline()\ntl.AddMarker(20, 'Blue', 'b', '', 1, '')\n")
        check("…two scripts used, the allowance is spent: the next edit is back to the normal prompt",
              dec == "pass", why)
        rc, out, err = run([GATE, "allow", "--list"], env)
        check("allow --list shows the Resolve allowance and what is left", "R1 resolve" in out and "0 script(s) left" not in out
              and ("expired" in out or "left" in out), out + err)
        rc, out, err = run([GATE, "allow", "resolve", "--revoke", "all"], env)
        check("allow resolve --revoke all", rc == 0 and "revoked" in out, out + err)

        # 11b2. the reference plan across the job — the planning view, before any spend
        rc, out, err = run([LINT, os.path.join(job, "01-script", "prompts"), "--plan"], env)
        check("--plan lists every reference, its attribute and whether it is cleared",
              "REFERENCE PLAN" in out and "character" in out and "wardrobe" in out
              and "cleared" in out and "0 not cleared" in out, out + err)

        # 11c. the review's bypasses, closed
        forged_src = os.path.join(job, "01-script", "prompts", "S9.clip.prompt.md")
        open(forged_src, "w").write("garbage, never linted\n")
        fp9 = "a fox running through a field, 8k, cinematic, masterpiece"
        json.dump({"shot": "S9", "kind": "clip", "model": "kling3_0", "resolution": "1080p", "duration": 5,
                   "aspect": "9:16", "variants": 4, "prompt": fp9,
                   "prompt_sha256": __import__("hashlib").sha256(fp9.encode()).hexdigest(),
                   "file_sha256": __import__("hashlib").sha256(open(forged_src, "rb").read()).hexdigest()},
                  open(forged_src[:-3] + ".ok", "w"))
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {"model": "kling3_0", "prompt": fp9, "duration": 5, "aspect_ratio": "9:16"})
        check("hand-written .ok sidecar → deny (lint is re-run at hook time)", dec == "deny" and "hand-written .ok" in why, why)
        os.remove(forged_src); os.remove(forged_src[:-3] + ".ok")
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**vparams, "medias": [{"role": "video", "value": "job_abc123"}]})
        check("approved id bound under a video role → deny, naming the slot it was found in",
              dec == "deny" and "as `start_image`" in why and "bound as 'video'" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "width": 1920, "height": 1080})
        check("undeclared width/height params → deny", dec == "deny" and "undeclared param" in why, why)

        # 11c2. the params the vendor's CURRENT contracts require — allowed, and then READ.
        # Before 2026-09-17 every one of these was denied as "undeclared", which is a gate that
        # blocks the work instead of the mistake. Each is now on the whitelist with a check.
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**good, "mode": "t2v", "duration_policy": "strict"})
        check("Seedance-style mode + duration_policy → no longer an undeclared-param deny",
              "undeclared param" not in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "mode": "t2b"})
        check("an invented mode → deny", dec == "deny" and "not one minimax_h3 documents" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "mode": "t2v"})
        check("a REAL mode on a model that takes none (minimax_h3 + t2v) → deny — an empty mode list "
              "is an answer, not a missing one", dec == "deny" and "it takes no mode" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "mode": "video_edit"})
        check("video_edit with no source video in medias → deny",
              dec == "deny" and "video_references" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "generate_audio": True})
        check("generate_audio:true on a clip that carries spoken lines, `audio` not approved → deny (the voice gate "
              "still holds for speech; v2.49 keeps native sound only for clips with no lines)",
              dec == "deny" and "carries spoken lines" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "variant": "elevenlabs"})
        check("variant on a video call → deny", dec == "deny" and "engine switch" in why, why)
        nodur = {k: v for k, v in good.items() if k != "duration"}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", nodur)
        check("clip call without duration → deny", dec == "deny" and "`duration` is required" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio", {"model": "seed_audio", "prompt": "Every bottle", "voice_id": "v1", "voice_type": "preset"})
        check("VO that is a substring, not a line → deny", dec == "deny" and "not one spoken line" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_audio", {"model": "sonilo_music", "prompt": "We taste it before you ever see it.", "voice_id": "v1", "duration": 30})
        check("music model on the VO path → deny", dec == "deny" and "not a speech model" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video_batch", [], batch=True)
        check("empty batch → deny", dec == "deny" and "empty or malformed" in why, why)
        rc, out, err = run([GATE, "hook"], env, stdin="{not json")
        check("malformed stdin → deny (fails closed)", '"deny"' in out and "fails closed" in out, out + err)
        rc, out, err = run([GATE, "hook"], env, stdin=json.dumps({"tool_input": {}}))
        check("missing tool_name → deny (fails closed)", '"deny"' in out and "no tool_name" in out, out + err)
        rc, out, err = run([GATE, "hook"], env, stdin=json.dumps({"session_id": "t", "tool_name": "mcp__Higgsfield__generate_video_batch",
                                                                  "tool_input": {"requests": [{"index": 0, "params": json.dumps(good)}]}}))
        check("batch params passed as a JSON string → decoded, passes", '"permissionDecision"' not in out and "GATE OK" in out, out + err)
        # two shots sharing one motion prompt (Mode B): the bound frame picks the shot
        cl4 = os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md")
        open(cl4, "w").write(CLIP.replace("shot: S3", "shot: S4").replace("S3_host_v2.png", "S4_host_v1.png"))
        open(os.path.join(job, "02-startframes", "S4_host_v1.png"), "wb").write(b"\x89PNG\r\n fixture 4")
        run([LINT, cl4], env)
        run([GATE, "approve", "frame:S4", "--by", "Dana", "--quote", "S4 v1 works, go",
             "--artifact", "02-startframes/S4_host_v1.png", "--media-id", "job_def456"], env)
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_video", {**good, "medias": [{"role": "image", "value": "job_def456"}]})
        check("identical motion prompt on two shots → the bound frame selects S4", dec == "pass" and "S4 clip" in ctx, why)
        # S4 speaks too, so S4 owes its own listener reaction before `clips` will approve again
        open(os.path.join(job, "01-script", "prompts", "S4-R.clip.prompt.md"), "w").write(
            REACT.replace("shot: S3-R", "shot: S4-R")
                 .replace("start_frame: 02-startframes/S3_host_v2.png",
                          "start_frame: 02-startframes/S4_host_v1.png"))
        run([BOARD, "shots", job], env)          # prompts changed since the last board
        rc, out, err = run([GATE, "approve", "clips", "--by", "Dana | CEO", "--quote", "the selects are fine by me"], env)
        rc2, out2, _ = run([GATE, "status", "--json"], env)
        check("a pipe in --by cannot shift the ledger columns", any("clips" in x and "Dana ¦ CEO" in x for x in json.loads(out2)["approved"]), out2)
        rc, out, err = run([GATE, "approve", "clips", "--by", "Dana", "--quote", "fine by me", "--artifact", os.path.abspath(__file__)], env)
        check("artifact outside the job → refused", rc == 1 and "outside the job" in err, err)
        # transcript-verified approvals: the quote must be in a human turn
        tp = os.path.join(td, "transcript.jsonl")
        open(tp, "w").write(json.dumps({"type": "user", "message": {"role": "user", "content": "yes — the export is approved, ship v4"}}) + "\n")
        open(os.path.join(env["CINE_HOME"], "transcript-path"), "w").write(tp)
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "looks great, ship it"], env)
        check("quote absent from the transcript → refused", rc == 1 and "no human turn" in err, err)
        # (3.1) a stage shown in a review pack is approved only with its code, in the approver's words
        _rp = os.path.join(HERE, "review_pack.py")
        rc, out, err = run([_rp, "make", job, "export", "--file", "00-brief/CHECKPOINT.md"], env)
        _code = out.split()[1].rstrip(":") if rc == 0 else ""
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "the export is approved, ship v4"], env)
        check("(3.1) a review pack exists → approve without --pack refused", rc == 1 and "pass --pack" in err, out + err)
        shutil.rmtree(os.path.join(job, "07-review"))
        _st = os.path.join(td, "studio-no"); os.makedirs(_st, exist_ok=True)
        open(os.path.join(_st, "studio.json"), "w").write('{"music_licence": "no"}')
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "the export is approved, ship v4"],
                           dict(env, CINE_STUDIO=_st))
        check("(3.1) a studio \"no\" on music licence blocks export", rc == 1 and "NOT cleared for paid use" in err, out + err)
        rc, out, err = run([GATE, "approve", "Export", "--by", "Dana", "--quote", "the export is approved, ship v4"],
                           dict(env, CINE_STUDIO=_st))
        check("(3.1 review) `approve Export` (capitalised) runs the same export checks", rc == 1 and "NOT cleared" in err, out + err)
        open(os.path.join(_st, "studio.json"), "w").write('{"music_licence": "No"}')
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "the export is approved, ship v4"],
                           dict(env, CINE_STUDIO=_st))
        check("(3.1 review) a malformed studio answer (\"No\") blocks rather than passing", rc == 1 and "'No'" in err, out + err)
        open(os.path.join(_st, "studio.json"), "w").write('{"music_licence": "n')
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "the export is approved, ship v4"],
                           dict(env, CINE_STUDIO=_st))
        check("(3.1 review) a half-written studio.json blocks the export", rc == 1 and "cannot be read" in err, out + err)
        open(os.path.join(_st, "studio.json"), "w").write('{"music_licence": "no"}')
        _cfgp = os.path.join(env["CINE_HOME"], "config.json")
        _cfg0 = open(_cfgp).read() if os.path.isfile(_cfgp) else None
        _cfg = json.loads(_cfg0) if _cfg0 else {}
        json.dump({**_cfg, "studio": _st}, open(_cfgp, "w"))
        _empty = os.path.join(td, "studio-empty"); os.makedirs(_empty, exist_ok=True)
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "the export is approved, ship v4"],
                           dict(env, CINE_STUDIO=_empty))
        check("(3.1 build review, Grok) CINE_STUDIO pointed at an empty folder cannot hide the configured studio's \"no\"",
              rc == 1 and "NOT cleared for paid use" in err, out + err)
        if _cfg0 is None:
            os.remove(_cfgp)
        else:
            open(_cfgp, "w").write(_cfg0)
        open(os.path.join(_st, "studio.json"), "w").write('{"music_licence": "yes", "likeness_release": "unknown"}')
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "the export is approved, ship v4"],
                           dict(env, CINE_STUDIO=_st))
        check("quote present in a human turn → approved as transcript-verified (a studio yes/unknown blocks nothing)",
              rc == 0 and "found in the session transcript" in out, out + err)
        os.remove(os.path.join(env["CINE_HOME"], "transcript-path"))
        # (3.1) a hooked home (no hookless setting) with no transcript: refused, never recorded UNVERIFIED
        _cfg = os.path.join(env["CINE_HOME"], "config.json"); os.remove(_cfg)
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "ship the cut as it is"],
                           dict(env, CINE_TEST_HOOKED="1"))
        check("(3.1) hooked home, no transcript → refused, nothing recorded", rc == 1 and "cannot be resolved" in err, out + err)
        open(_cfg, "w").write('{"hookless": true}')

        # (3.1) a scene whose continuity check FAILED refuses a clip's preflight; a newer PASS clears it
        _fd = os.path.join(job, "09-qa", "fanout", "cont-1"); os.makedirs(_fd, exist_ok=True)
        open(os.path.join(_fd, "S3.md"), "w").write('```fanout\n{"unit": "S3", "agent": "cine-scene-continuity", '
                                                   '"verdict": "FAIL"}\n```\nlens differs between S3 shots\n')
        rc, out, err = run([GATE, "preflight", "S3", "--kind", "clip", "--json"], env)
        check("(3.1) scene continuity FAIL → clip preflight refused", rc == 1 and "continuity check FAILED" in err, out + err)
        time.sleep(0.05)
        _fd2 = os.path.join(job, "09-qa", "fanout", "cont-2"); os.makedirs(_fd2, exist_ok=True)
        open(os.path.join(_fd2, "S3.md"), "w").write('```fanout\n{"unit": "S3", "agent": "cine-scene-continuity", '
                                                    '"verdict": "PASS"}\n```\nall eight things agree\n')
        # 12. preflight emits params the gate would pass
        rc, out, err = run([GATE, "preflight", "S3", "--kind", "clip", "--json"], env)
        pf = json.loads(out)
        check("preflight would pass and binds the approved media", rc == 0 and pf["would_pass"] and
              any(m["value"] == "job_abc123" for m in pf["params"]["medias"]), out + err)
        dec, _, _ = hook(env, pf["tool"], pf["params"])
        check("preflight params pass the hook verbatim", dec == "pass")
        time.sleep(0.05)
        _fd3 = os.path.join(job, "09-qa", "fanout", "cont-3"); os.makedirs(_fd3, exist_ok=True)
        open(os.path.join(_fd3, "S3.md"), "w").write('```fanout\n{"unit": "S3", "agent": "cine-scene-continuity", '
                                                    '"verdict": "FAIL"}\n```\nthe lamp moved\n')
        dec, why, _ = hook(env, pf["tool"], pf["params"])
        check("(3.1 build review) a newer continuity FAIL denies the clip at the HOOK, not only at preflight",
              dec == "deny" and "continuity check FAILED" in why, why)
        shutil.rmtree(_fd3)
        # (v2.62.0) the envelope is a cap: once the job's recorded spend would pass it, the same call asks
        _sub = os.path.join(job, ".gate", "submitted.jsonl")
        _before = open(_sub, encoding="utf-8").read() if os.path.isfile(_sub) else None
        os.makedirs(os.path.dirname(_sub), exist_ok=True)
        with open(_sub, "a", encoding="utf-8") as _fh:
            _fh.write(json.dumps({"ts": "x", "epoch": 0, "tool": "t", "hash": "h-old", "ids": ["x"], "credits": 100000}) + "\n")
        dec, why, _ = hook(env, pf["tool"], pf["params"])
        check("(v2.62.0) a call that takes the job past its CHECKPOINT envelope asks instead of passing",
              dec == "ask" and "past its envelope" in why, why)
        if _before is None:
            os.remove(_sub)
        else:
            open(_sub, "w", encoding="utf-8").write(_before)
        dec, _, _ = hook(env, pf["tool"], pf["params"])
        check("...and passes again under the envelope", dec == "pass")
        # (wave 2c) THE STUDIO'S MONTHLY CEILING: its own stop, beside the envelope (PLAN-SETTINGS-v2/v3)
        _stc = os.path.join(td, "studio-ceiling"); os.makedirs(_stc, exist_ok=True)
        _envc = dict(env, CINE_STUDIO=_stc)
        _stj = os.path.join(_stc, "studio.json")
        json.dump({"monthly_credit_ceiling": 1000000}, open(_stj, "w"))
        dec, why, ctx = hook(_envc, pf["tool"], pf["params"])
        _pm = re.search(r"studio month \S+ \(UTC\) 0 / 1e\+06 cr · this call ([0-9.]+) cr(?! \+ unpriced)", ctx)
        check("(wave 2c) under the ceiling the call passes and carries the studio month line", dec == "pass" and _pm, ctx)
        _P = float(_pm.group(1)) if _pm else 1.0
        json.dump({"monthly_credit_ceiling": _P}, open(_stj, "w"))
        dec, why, _ = hook(_envc, pf["tool"], pf["params"])
        check("(wave 2c) month + this call == ceiling → passes (the stop is past it, not at it)", dec == "pass", why)
        json.dump({"monthly_credit_ceiling": _P - 0.5}, open(_stj, "w"))
        dec, why, _ = hook(_envc, pf["tool"], pf["params"])
        check("(wave 2c) one credit short → asks, with the studio month in the reason",
              dec == "ask" and "budget stop" in why and "past its ceiling" in why, why)
        _pl = {"tool_name": pf["tool"], "tool_input": {"params": pf["params"]}, "hook_event_name": "PreToolUse"}
        rc, out, _ = run([GATE, "hook"], _envc, stdin=json.dumps(_pl))
        check("(wave 2c) no session_id with the ceiling hit → still deny (the fail-closed deny stays last)",
              '"deny"' in out, out)
        open(_stj, "w").write('{"monthly_credit_ceiling": "3000"}')
        dec, why, _ = hook(_envc, pf["tool"], pf["params"])
        check("(wave 2c) a ceiling written as a string → asks (the stop is never dropped silently)",
              dec == "ask" and "not a number of credits" in why, why)
        open(_stj, "w").write('{"monthly_credit_ceiling": 30')
        dec, why, _ = hook(_envc, pf["tool"], pf["params"])
        check("(wave 2c) a half-written studio.json → asks", dec == "ask" and "cannot be read" in why, why)
        json.dump({"monthly_credit_ceiling": 1000000}, open(_stj, "w"))
        _post = {"session_id": "t", "hook_event_name": "PostToolUse", "tool_name": pf["tool"],
                 "tool_input": {"params": pf["params"]}, "tool_response": {"job_id": "job_ceiling_ok_01"}}
        run([GATE, "posthook"], _envc, stdin=json.dumps(_post))
        rc, out, _ = run([os.path.join(ROOT, "scripts", "studio.py"), "month", "--json"], _envc)
        _mt = json.loads(out) if rc == 0 else {}
        check("(wave 2c) an accepted submission writes one studio spend event at its price",
              _mt.get("events") == 1 and abs(_mt.get("credits", -1) - _P) < 1e-9, out)
        rc, out, _ = run([GATE, "status"], _envc)
        check("(wave 2c) status shows the settings line with the month, the envelope and the regens source",
              f"studio month {_mt.get('month')} (UTC) {_P:g} / 1e+06 cr" in out and "envelope 900 cr (checkpoint)" in out
              and "regens per approval 2 (house)" in out, out)
        _fail = {**_post, "hook_event_name": "PostToolUseFailure", "error": "request timed out after 120 s"}
        _fail.pop("tool_response", None)
        run([GATE, "posthook", "--failed"], _envc, stdin=json.dumps(_fail))
        rc, out, _ = run([os.path.join(ROOT, "scripts", "studio.py"), "month", "--json"], _envc)
        _mt2 = json.loads(out) if rc == 0 else {}
        check("(wave 2c) a timeout (may have billed) writes a studio event at its quoted price too",
              _mt2.get("events") == 2 and abs(_mt2.get("credits", -1) - 2 * _P) < 1e-9, out)
        _sp0 = os.path.join(job, ".gate", "submitted.jsonl")
        open(_sp0, "w").write("".join(l for l in open(_sp0, encoding="utf-8") if "timed out" not in l))
        rc, out, _ = run([GATE, "status"], dict(_envc, CINE_HOME=os.path.join(td, "home-nojob")))
        check("(wave 2c) with no job open, status still prints the studio month against the ceiling",
              rc == 1 and "no active job" in out and "studio month" in out and "/ 1e+06 cr" in out, out)
        shutil.rmtree(os.path.join(_stc, "spend"), ignore_errors=True)
        # an existing ask keeps its own reason; the budget stop is appended, never a replacement
        _dup = {**_post, "tool_response": {"job_id": "job_ceiling_dup_02"}}
        run([GATE, "posthook"], env, stdin=json.dumps(_dup))                 # a submission in the JOB → duplicate
        json.dump({"monthly_credit_ceiling": 0.5}, open(_stj, "w"))
        dec, why, _ = hook(_envc, pf["tool"], pf["params"])
        check("(wave 2c) a duplicate-submit ask over the ceiling keeps the duplicate reason and appends the budget stop",
              dec == "ask" and "already submitted" in why and "ALSO a budget stop" in why, why)
        _sp = os.path.join(job, ".gate", "submitted.jsonl")
        open(_sp, "w").write("".join(l for l in open(_sp, encoding="utf-8") if "job_ceiling_dup_02" not in l))
        check("preflight emits the API's role name, not the coerced legacy `image`",
              any(m["role"] == "start_image" and m["value"] == "job_abc123" for m in pf["params"]["medias"]),
              out)

        # 12b. END FRAMES (2026-09-19). The guidance recommended first-and-last-frame and the checks
        # refused it: the role vocabulary predated the API's names, preflight had nowhere to put a
        # second frame, and the approvals ledger knew only start frames.
        S5 = (CLIP.replace("shot: S3", "shot: S5").replace("type: dialogue", "type: broll")
              .replace('line: "We taste it before you ever see it."\n', "")
              .replace("vo: 05-voice/S3.wav\n",
                       "function: the boom down into the grove that the next line pays off\n")
              .replace("seated at the tasting table, both hands around the glass",
                       "standing at the grove's edge, both hands around the glass")
              .replace("start_frame: 02-startframes/S3_host_v2.png",
                       "start_frame: 02-startframes/S5_a.png\nend_frame: 02-startframes/S5_b.png"))
        c5 = os.path.join(job, "01-script", "prompts", "S5.clip.prompt.md"); open(c5, "w").write(S5)
        open(os.path.join(job, "02-startframes", "S5_a.png"), "wb").write(b"\x89PNG\r\n S5 start")
        rc, out, err = run([LINT, c5], env)
        check("end_frame declared but not on disk → lint FAILS", rc == 1 and "end_frame" in out and
              "not found under the job" in out, out)
        open(os.path.join(job, "02-startframes", "S5_b.png"), "wb").write(b"\x89PNG\r\n S5 end, boomed down")
        rc, out, err = run([LINT, c5], env)
        check("end_frame on disk → lint passes", rc == 0, out + err)
        s5prompt = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip()
        same = os.path.join(job, "01-script", "prompts", "S5x.clip.prompt.md")
        open(same, "w").write(S5.replace("shot: S5", "shot: S5x").replace("S5_b.png", "S5_a.png"))
        rc, out, err = run([LINT, same], env)
        check("end frame identical to the start frame → lint FAILS (encodes a still)",
              rc == 1 and "DIFFERENCE between the frames" in out, out)
        os.remove(same); os.path.exists(same[:-3] + ".ok") and os.remove(same[:-3] + ".ok")
        asref = os.path.join(job, "01-script", "prompts", "S5y.clip.prompt.md")
        open(asref, "w").write(S5.replace("shot: S5", "shot: S5y").replace(
            "payload:", "refs:\n  - role: end_image · what: environment · value: job_sneaky\npayload:"))
        rc, out, err = run([LINT, asref], env)
        check("an end frame smuggled in as a REFERENCE → lint FAILS (it would reach the model unapproved)",
              rc == 1 and "pins a FRAME" in out, out)
        os.remove(asref); os.path.exists(asref[:-3] + ".ok") and os.remove(asref[:-3] + ".ok")
        kl = os.path.join(job, "01-script", "prompts", "S5z.clip.prompt.md")
        open(kl, "w").write(S5.replace("shot: S5", "shot: S5z").replace("model: minimax_h3", "model: kling3_0")
                            .replace("resolution: 2k", "resolution: 1080p").replace(
            "payload:", "refs:\n  - role: image · what: prop · value: job_prop1\npayload:"))
        rc, out, err = run([LINT, kl], env)
        check("kling3_0 given an image reference → lint FAILS (it takes start and end frames only)",
              rc == 1 and "kling3_0 does not take 'image_references'" in out, out)
        os.remove(kl); os.path.exists(kl[:-3] + ".ok") and os.remove(kl[:-3] + ".ok")
        run([LINT, c5], env)

        v5 = {"model": "minimax_h3", "prompt": s5prompt, "duration": 6, "aspect_ratio": "9:16"}
        run([GATE, "approve", "frame:S5", "--by", "Dana", "--quote", "S5 start, the wide on the grove",
             "--artifact", "02-startframes/S5_a.png", "--media-id", "job_s5a"], env)
        rc, out, err = run([GATE, "status", "--json"], env)
        check("status owes `approve endframe:S5` while it is unapproved",
              any("endframe:S5" in n for n in json.loads(out).get("next", [])), out)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v5, "medias": [{"role": "start_image", "value": "job_s5a"},
                                             {"role": "end_image", "value": "job_s5b"}]})
        check("end frame declared but not approved → deny", dec == "deny" and
              "endframe:S5 is not approved" in why, why)
        rc, out, err = run([GATE, "approve", "endframe:S5", "--by", "Dana", "--quote", "S5 end, boomed in",
                            "--artifact", "02-startframes/S5_b.png"], env)
        check("endframe approval without --media-id → refused", rc == 1 and "--media-id" in err and
              "end frame" in err, err)
        rc, out, err = run([GATE, "approve", "endframe:S5", "--by", "Dana", "--quote", "S5 end, boomed in",
                            "--artifact", "02-startframes/S5_b.png", "--media-id", "job_s5b"], env)
        check("endframe approved with artifact + media id", rc == 0, out + err)
        ok5 = {**v5, "medias": [{"role": "start_image", "value": "job_s5a"},
                                {"role": "end_image", "value": "job_s5b"}]}
        dec, why, ctx = hook(env, "mcp__Higgsfield__generate_video", ok5)
        check("start_image + end_image, both approved → pass", dec == "pass" and "S5 clip" in ctx, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v5, "medias": [{"role": "start_image", "value": "job_s5a"}]})
        check("FLF plan sent without its end frame → deny (a different shot from the linted one)",
              dec == "deny" and "does not bind the approved end frame" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v5, "medias": [{"role": "start_image", "value": "job_s5b"},
                                             {"role": "end_image", "value": "job_s5a"}]})
        check("start and end SWAPPED → deny (an approved still in the wrong slot proves nothing)",
              dec == "deny" and "as `start_image`" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v5, "medias": [{"role": "start_image", "value": "job_s5a"},
                                             {"role": "end_image", "value": "job_unapproved"}]})
        check("an UNAPPROVED end frame → deny", dec == "deny" and "does not bind the approved end frame" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v5, "medias": [{"role": "image", "value": "job_s5a"},
                                             {"role": "end_image", "value": "job_s5b"}]})
        check("legacy `image` beside an end frame is NOT read as the start (coercion is ambiguous) → deny",
              dec == "deny" and "as `start_image`" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**ok5, "medias": ok5["medias"] + [{"role": "image_references", "value": "job_rider"}]})
        check("an undeclared extra media riding on an approved call → deny",
              dec == "deny" and "does not declare" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**good, "medias": [{"role": "start_image", "value": "job_abc123"},
                                               {"role": "end_image", "value": "job_s5b"}]})
        check("an end_image on a clip whose prompt declares none → deny",
              dec == "deny" and "does not declare" in why, why)
        rc, out, err = run([GATE, "preflight", "S5", "--kind", "clip", "--json"], env)
        pf5 = json.loads(out)
        roles5 = {m["role"]: m["value"] for m in pf5["params"].get("medias", [])}
        check("preflight S5 binds start_image AND end_image and would pass",
              rc == 0 and pf5["would_pass"] and roles5 == {"start_image": "job_s5a", "end_image": "job_s5b"},
              out + err)
        dec, _, _ = hook(env, pf5["tool"], pf5["params"])
        check("preflight S5 params pass the hook verbatim", dec == "pass")
        # the section is self-contained: later sections count the job's prompts
        os.remove(c5); os.path.exists(c5[:-3] + ".ok") and os.remove(c5[:-3] + ".ok")

        # 12c. PER-MODEL CALL SHAPES (2026-09-19, measured on a production job) and the model the
        # owner added the same day. One broll clip body, re-cast per model.
        B = (S5.replace("end_frame: 02-startframes/S5_b.png\n", "")
               .replace("standing at the grove's edge", "walking the grove's first row"))
        def cast(shot, model, res, extra=""):
            f = os.path.join(job, "01-script", "prompts", f"{shot}.clip.prompt.md")
            open(f, "w").write(B.replace("shot: S5", f"shot: {shot}").replace("model: minimax_h3", f"model: {model}")
                                .replace("resolution: 2k", f"resolution: {res}").replace("payload:", extra + "payload:")
                                .replace("walking the grove's first row", f"walking the grove's first row ({shot})"))
            rc, out, _ = run([LINT, f], env)
            pr = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip() \
                if "PROMPT (paste verbatim" in out else ""
            return f, rc, out, pr
        def drop(f):
            os.remove(f); os.path.exists(f[:-3] + ".ok") and os.remove(f[:-3] + ".ok")
        f6, rc, out, _ = cast("S6e", "seedance_2_5", "1080p", "end_frame: 02-startframes/S5_b.png\n")
        check("seedance_2_5 + end_frame → lint FAILS (its start_image is a reference, so no first or last frame)",
              rc == 1 and "no first frame and no last one" in out, out)
        drop(f6)
        f6, rc, out, p6 = cast("S6", "seedance_2_5", "1080p")
        check("seedance_2_5 clip lints, WARNING that the first frame will be close, not exact",
              rc == 0 and "CLOSE, not exact" in out, out)
        run([GATE, "approve", "frame:S6", "--by", "Dana", "--quote", "S6 start, the grove row",
             "--artifact", "02-startframes/S5_a.png", "--media-id", "job_s6a"], env)
        v6 = {"model": "seedance_2_5", "prompt": p6, "duration": 6, "aspect_ratio": "9:16"}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v6, "mode": "omni_reference", "generate_audio": False,
                            "medias": [{"role": "start_image", "value": "job_s6a"}]})
        check("seedance with `start_image` → deny (measured: it is a reference there, corr 0.53-0.96)",
              dec == "deny" and "image_references" in why, why)
        ok6 = {**v6, "mode": "omni_reference", "generate_audio": False,
               "medias": [{"role": "image_references", "value": "job_s6a"}]}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", ok6)
        check("seedance: approved still as image_references + omni_reference + audio off → pass", dec == "pass", why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {k: v for k, v in ok6.items() if k != "mode"})
        check("seedance without mode omni_reference → deny", dec == "deny" and "omni_reference" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {k: v for k, v in ok6.items() if k != "generate_audio"})
        check("seedance with generate_audio OMITTED (defaults ON), no lines, no sound decided in the file → pass "
              "(v2.49: native sound is kept)", dec == "pass", why)
        f6s, rc, out, p6s = cast("S6s", "seedance_2_5", "1080p", "generate_audio: false\n")
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v6, "prompt": p6s, "mode": "omni_reference",
                            "medias": [{"role": "image_references", "value": "job_s6a"}]})
        check("…but a file that says `generate_audio: false` holds the call to it: the switch omitted (ON) → deny",
              dec == "deny" and "omitted: the model defaults it ON" in why, why)
        drop(f6s)
        rc, out, _ = run([GATE, "preflight", "S6", "--kind", "clip", "--json"], env)
        pf6 = json.loads(out)
        check("preflight S6 emits image_references, omni_reference, generate_audio false, resolution 1080p — and passes",
              pf6["would_pass"] and pf6["params"].get("mode") == "omni_reference"
              and pf6["params"].get("generate_audio") is False and pf6["params"].get("resolution") == "1080p"
              and pf6["params"]["medias"] == [{"role": "image_references", "value": "job_s6a"}], out)
        # (v2.70.0, Wave 5 A7) a clip with no lines whose file asks for sound keeps it: preflight sends true, never stops
        f6t, rc, out, _ = cast("S6t", "seedance_2_5", "1080p", "generate_audio: true\n")
        run([GATE, "approve", "frame:S6t", "--by", "Dana", "--quote", "S6t start, the grove row",
             "--artifact", "02-startframes/S5_a.png", "--media-id", "job_s6t"], env)
        rc, out, err = run([GATE, "preflight", "S6t", "--kind", "clip", "--json"], env)
        check("(2.70) preflight: a silent clip whose file says generate_audio true sends it on, with no stop",
              rc == 0 and json.loads(out)["params"].get("generate_audio") is True and "REFUSED" not in err, out + err)
        drop(f6t)
        # ...a clip that SPEAKS whose file asks for sound, `audio` not approved, on a model WITH an off switch that
        # defaults on (Seedance): preflight stops and names the approval
        f3a = os.path.join(job, "01-script", "prompts", "S3a.clip.prompt.md")
        open(f3a, "w").write(CLIP.replace("shot: S3", "shot: S3a").replace("model: minimax_h3", "model: seedance_2_5")
                             .replace("resolution: 2k", "resolution: 1080p").replace("payload:", "generate_audio: true\npayload:"))
        rc_l, out_l, _ = run([LINT, f3a], env)
        rc, out, err = run([GATE, "preflight", "S3a", "--kind", "clip", "--json"], env)
        check("(2.70) preflight: a speaking Seedance clip whose file says generate_audio true, audio unapproved → "
              "REFUSED, naming the approval (no silent off-switch the gate then refuses)",
              rc_l == 0 and rc == 1 and "Approve `audio` first" in err, out_l[-600:] + out + err)
        drop(f3a)
        # ...but MiniMax H3 has no audio switch: preflight never rewrote it, so it is never stopped for this (Grok r1)
        f3m = os.path.join(job, "01-script", "prompts", "S3m.clip.prompt.md")
        open(f3m, "w").write(CLIP.replace("shot: S3", "shot: S3m").replace("payload:", "generate_audio: true\npayload:"))
        run([LINT, f3m], env)
        rc, out, err = run([GATE, "preflight", "S3m", "--kind", "clip", "--json"], env)
        check("(2.70) preflight: the same speaking clip on MiniMax H3 (no audio switch) is not stopped for audio",
              "Approve `audio` first" not in err, out + err)
        drop(f3m)
        drop(f6)

        # 12c-bis. BLOCKING (2026-10-23, references/blocking.md §7). A grey 3D render passed as a video
        # reference steers the camera and the positions as hard as a frame steers the picture: it is
        # approved as its build MANIFEST (every file hashed), bound by media id, and refused otherwise.
        import hashlib
        bdir = os.path.join(job, "02-startframes", "_blocking", "S6b"); os.makedirs(bdir, exist_ok=True)
        bmp4 = os.path.join(bdir, "S6b.blocking.mp4"); open(bmp4, "wb").write(b"\x00\x00\x00 ftyp blocking S6b")
        bman = os.path.join(bdir, "S6b.blocking.manifest.json")
        def write_man(dur):
            json.dump({"shot": "S6b", "duration": dur, "legend": {"red": "the host", "yellow": "the glass"},
                       "files": {"mp4": {"path": "S6b.blocking.mp4",
                                         "sha256": hashlib.sha256(open(bmp4, "rb").read()).hexdigest()}}},
                      open(bman, "w"))
        write_man(5)
        blk = ("refs:\n  - role: video_references · what: blocking · value: job_blk · "
               "manifest: 02-startframes/_blocking/S6b/S6b.blocking.manifest.json\n")
        fb, rc, out, pb = cast("S6b", "seedance_2_5", "1080p", blk)
        check("blocked clip lints (WARN-first): no [LEGEND], no [PRECEDENCE], no `not:`, duration ≠ blocking",
              rc == 0 and "[LEGEND] missing on a blocked clip" in out and "[PRECEDENCE] missing" in out
              and "declares no `not:`" in out and "the blocking's 5 s" in out, out)
        fx, rc, out, _ = cast("S6x", "seedance_2_5", "1080p", blk.replace("video_references", "image"))
        check("a blocking passed as an IMAGE reference → lint FAILS", rc == 1 and "goes in as `video_references`" in out, out)
        drop(fx)
        write_man(6)
        fb, rc, out, pb = cast("S6b", "seedance_2_5", "1080p", blk)
        check("manifest duration = clip duration → the duration WARN clears", rc == 0 and "the blocking's" not in out, out)
        run([GATE, "approve", "frame:S6b", "--by", "Dana", "--quote", "S6b start, the grove row",
             "--artifact", "02-startframes/S5_a.png", "--media-id", "job_s6b"], env)
        vb = {"model": "seedance_2_5", "prompt": pb, "duration": 6, "aspect_ratio": "9:16", "mode": "omni_reference",
              "generate_audio": False, "medias": [{"role": "image_references", "value": "job_s6b"},
                                                  {"role": "video_references", "value": "job_blk"}]}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vb)
        check("blocking reference declared, blocking:S6b not approved → deny",
              dec == "deny" and "blocking:S6b is not approved" in why, why)
        rc, out, err = run([GATE, "approve", "blocking:S6b", "--by", "Dana", "--quote", "S6b blocking, as built",
                            "--artifact", "02-startframes/_blocking/S6b/S6b.blocking.mp4", "--media-id", "job_blk"], env)
        check("approve blocking with the MP4 instead of the manifest → refused", rc == 1 and "not a blocking manifest" in err, err)
        open(bmp4, "ab").write(b" edited after the build")
        rc, out, err = run([GATE, "approve", "blocking:S6b", "--by", "Dana", "--quote", "S6b blocking, as built",
                            "--artifact", "02-startframes/_blocking/S6b/S6b.blocking.manifest.json", "--media-id", "job_blk"], env)
        check("a build file changed after its manifest → approval refused", rc == 1 and "changed after the build" in err, err)
        write_man(6)
        rc, out, err = run([GATE, "approve", "blocking:S6b", "--by", "Dana", "--quote", "S6b blocking, as built",
                            "--artifact", "02-startframes/_blocking/S6b/S6b.blocking.manifest.json", "--media-id", "job_blk"], env)
        check("blocking approved as its manifest, with the MP4's media id", rc == 0, out + err)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vb)
        check("approved blocking bound by media id, manifest unchanged → pass", dec == "pass", why)
        rc, out, err = run([GATE, "approve", "blocking:S6b", "--by", "Dana", "--quote", "S6b blocking, the other upload",
                            "--artifact", "02-startframes/_blocking/S6b/S6b.blocking.manifest.json", "--media-id", "job_blk2"], env)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vb)
        check("the prompt binds job_blk, the approval says job_blk2 → deny", dec == "deny" and "a different render" in why, why)
        run([GATE, "approve", "blocking:S6b", "--by", "Dana", "--quote", "S6b blocking, as built",
             "--artifact", "02-startframes/_blocking/S6b/S6b.blocking.manifest.json", "--media-id", "job_blk"], env)
        man = json.load(open(bman)); man["note"] = "rebuilt"; json.dump(man, open(bman, "w"))
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vb)
        check("the manifest changed after approval → deny", dec == "deny" and "changed after blocking:S6b was approved" in why, why)
        drop(fb)

        # 12c-ter. MULTISHOT (2026-10-25, references/multishot.md). A planned multi-shot clip on seedance
        # binds the approved END still as a reference (`what: endframe`) — held to endframe:<SHOT> by
        # media id — and its @Image N tags are positional, so the call must bind in the linted order.
        MS = """---
shot: S4m
kind: clip
form: multishot
type: sequence
model: seedance_2_5
resolution: 1080p
duration: 24
aspect: 9:16
start_frame: 02-startframes/S5_a.png
payload: the viewer learns that the app moved Mika's dinner to Venice, and that she chose it
refs:
  - role: image_references, what: character, value: job_ms_mika, not: sheet background, panel layout
  - role: image_references, what: prop, value: job_ms_phone, owner: Mika, not: studio background
  - role: image_references, what: environment, value: job_ms_terrace, not: people in the plate
  - role: image_references, what: endframe, value: job_ms_end
---
[GOAL]
A 24-second sequence on a sofa and then a Venice terrace: Mika taps her phone and the world changes around her.

[REFERENCES]
[Characters] Mika corresponds to @Image 2. Use only the appearance, hairstyle, and clothing.
[Props] The phone corresponds to @Image 3 and belongs only to Mika. Use only the shape, material, and colour.
[Scenes] The terrace corresponds to @Image 4. Use only the space, materials, and lighting, never the people in it.
[Frames] @Image 1 is the first frame of Stage 1; match its composition. @Image 5 is the final frame of Stage 3.

[STAGES]
Stage 1 | 0–8 s | MS, 35 mm, eye level, slow push-in
Use: Mika, @Image 2, @Image 3
Event: Mika reads the screen and taps it once with her index finger.
End state: phone in Mika's right hand, screen toward her, her eyes on it.
Cut: match cut on the tap

Stage 2 | 8–16 s | MS, 35 mm, eye level, locked-off
Use: Mika, @Image 2, @Image 4
Event: Mika lowers the phone and looks at the plate of spaghetti in front of her.
End state: phone face down on the table, fork in her right hand.
Cut: hard

Stage 3 | 16–24 s | WS, 24 mm, eye level, slow pull-back
Use: Mika, @Image 4, @Image 5
Event: Mika lifts the first forkful, the terrace opening out around her.
End state: Mika small in frame at the terrace table, hard midday sun on the plaster wall.

[SOUND]
Lines, each spoken exactly once and nothing else:
6.0–7.0 s Mika: "Ooh."
9.0–9.6 s Mika: "Pasta!"
Ambience changes on the cut frames.

[CONSISTENCY]
One woman throughout, the same clothes in every stage; the phone stays Mika's; screen direction left to right.
"""
        def ms_cast():
            f = os.path.join(job, "01-script", "prompts", "S4m.clip.prompt.md")
            open(f, "w").write(MS)
            rc, out, _ = run([LINT, f], env)
            pr = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip() \
                if "PROMPT (paste verbatim" in out else ""
            return f, rc, out, pr
        fm_, rc, out, pm = ms_cast()
        check("a planned multishot clip (seedance, end still as a reference) lints", rc == 0 and pm, out)
        run([GATE, "approve", "frame:S4m", "--by", "Dana", "--quote", "S4m open, the sofa",
             "--artifact", "02-startframes/S5_a.png", "--media-id", "job_s4m"], env)
        vm = {"model": "seedance_2_5", "prompt": pm, "duration": 24, "aspect_ratio": "9:16", "mode": "omni_reference",
              "generate_audio": False,
              "medias": [{"role": "image_references", "value": v} for v in
                         ("job_s4m", "job_ms_mika", "job_ms_phone", "job_ms_terrace", "job_ms_end")]}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vm)
        check("multishot: end still as a reference, endframe:S4m not approved → deny",
              dec == "deny" and "binds an end still as a reference and endframe:S4m is not approved" in why, why)
        rc, out, _ = run([GATE, "status", "--json"], env)
        check("status asks for endframe:S4m (bound as a reference)",
              "approve endframe:S4m (the clip declares an end frame, bound as a reference)" in out, out)
        run([GATE, "approve", "endframe:S4m", "--by", "Dana", "--quote", "S4m close, the terrace",
             "--artifact", "02-startframes/S5_b.png", "--media-id", "job_ms_end_other"], env)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vm)
        check("multishot: the endframe ref binds job_ms_end, the approval says job_ms_end_other → deny",
              dec == "deny" and "a different picture" in why, why)
        run([GATE, "approve", "endframe:S4m", "--by", "Dana", "--quote", "S4m close, the terrace",
             "--artifact", "02-startframes/S5_b.png", "--media-id", "job_ms_end"], env)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", vm)
        check("multishot: approved start + approved end still as references, linted order → pass", dec == "pass", why)
        swapped = {**vm, "medias": [vm["medias"][0], vm["medias"][2], vm["medias"][1]] + vm["medias"][3:]}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", swapped)
        check("multishot: the same pictures in another order (Mika's face on the phone) → deny",
              dec == "deny" and "tags are positional" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**vm, "medias": vm["medias"][:4]})
        check("multishot: the end still left out → deny (it re-points nothing, but @Image 5 is gone)",
              dec == "deny" and "tags are positional" in why, why)
        rc, out, _ = run([GATE, "preflight", "S4m", "--kind", "clip", "--json"], env)
        pfm = json.loads(out)
        check("preflight S4m emits the medias in the linted tag order and would pass",
              pfm["would_pass"] and pfm["params"]["medias"] == vm["medias"], out)
        drop(fm_)

        # 12c-quater. THE INSERT LANE (2026-10-25, house decision on the direct-response trial proposal's P7, "Family
        # approval"). One family file, linted once, writes one ordinary linted prompt per member; one
        # contact sheet signs every member's start frame, and each clip still binds its OWN still.
        def extract(out_):
            return out_.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip() \
                if "PROMPT (paste verbatim" in out_ else ""
        PD = os.path.join(job, "01-script", "prompts")
        FAM = (B.replace("shot: S5\n", "family: grove\n")
                .replace("model: minimax_h3", "model: kling3_0").replace("resolution: 2k", "resolution: 1080p")
                .replace("start_frame: 02-startframes/S5_a.png\n", "")
                .replace("payload:", "cut_max: 2.5\nslots: row\nmembers:\n"
                         "  - shot: S9a · start_frame: 02-startframes/S9a.png · row: first row\n"
                         "  - shot: S9b · start_frame: 02-startframes/S9b.png · row: last row\npayload:")
                .replace("walking the grove's first row", "walking the grove's {{row}}"))
        fam_p = os.path.join(PD, "grove.family.md"); open(fam_p, "w").write(FAM)
        for sh in ("S9a", "S9b"):
            open(os.path.join(job, "02-startframes", f"{sh}.png"), "wb").write(b"\x89PNG\r\n " + sh.encode())
        rc, out, _ = run([LINT, fam_p], env)
        check("a family lints once and writes one linted prompt per member",
              rc == 0 and "FAMILY PASS" in out and all(os.path.isfile(os.path.join(PD, f"{x}.clip.prompt.ok"))
                                                       for x in ("S9a", "S9b")), out)
        rc, out, _ = run([LINT, os.path.join(PD, "S9a.clip.prompt.md")], env)
        p9a = extract(out)
        check("a member is an ordinary prompt with its slot filled", rc == 0 and "walking the grove's first row" in p9a, out)
        v9 = {"model": "kling3_0", "prompt": p9a, "duration": 6, "aspect_ratio": "9:16", "sound": "off",
              "medias": [{"role": "start_image", "value": "job_s9a"}]}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", v9)
        check("a family member before its frame is approved → deny", dec == "deny" and "frame:S9a" in why, why)
        os.makedirs(os.path.join(job, "02-startframes", "_review"), exist_ok=True)
        open(os.path.join(job, "02-startframes", "_review", "grove_sheet.jpg"), "wb").write(b"\xff\xd8 sheet")
        fa = [GATE, "approve", "family:grove", "--by", "Dana", "--quote", "grove inserts, both good",
              "--artifact", "02-startframes/_review/grove_sheet.jpg"]
        rc, out, err = run(fa, env)
        check("approve family without --media-ids → refused", rc == 1 and "--media-ids is required" in err, err)
        rc, out, err = run(fa + ["--media-ids", "S9a=job_s9a,S9z=job_x"], env)
        check("a media id for a shot that is not a member → refused", rc == 1 and "S9z is not a member" in err, err)
        rc, out, err = run([os.path.join(HERE, "review_pack.py"), "make", job, "family:grove", "--file",
                            "02-startframes/_review/grove_sheet.jpg"], env)
        rc2, out2, err2 = run(fa + ["--media-ids", "S9a=job_s9a,S9b=job_s9b"], env)
        check("(3.1 build review) a family shown in a review pack is refused without its code",
              rc == 0 and rc2 == 1 and "has a review pack" in err2, out + err + out2 + err2)
        shutil.rmtree(os.path.join(job, "07-review"), ignore_errors=True)
        rc, out, err = run(fa + ["--media-ids", "S9a=job_s9a,S9b=job_s9b"], env)
        check("one contact sheet signs both members' start frames", rc == 0 and "2 start frame(s)" in out, out + err)
        aps = open(os.path.join(job, "00-brief", "APPROVALS.md"), encoding="utf-8").read()
        check("each member gets its own frame:<SHOT> row, its own still and media id",
              "| frame:S9a |" in aps and "| frame:S9b |" in aps and "| job_s9b |" in aps
              and "02-startframes/S9a.png" in aps, aps[-600:])
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", v9)
        check("the member, its own approved still bound as start → pass", dec == "pass", why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {**v9, "medias": [{"role": "start_image", "value": "job_s9b"}]})
        check("the member bound to its SIBLING's still → deny (each clip binds its own picture)", dec == "deny", why)
        open(fam_p, "a").write("\n")
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", v9)
        check("the family edited after its members were written → deny until it is linted again",
              dec == "deny" and "fresh lint" in why, why)
        rc, out, _ = run([LINT, fam_p], env)
        check("re-linting the family rewrites its members", rc == 0, out)

        def fam_fails(old, new, name="bad"):
            fp_ = os.path.join(PD, f"{name}.family.md")
            open(fp_, "w").write(FAM.replace("family: grove", f"family: {name}").replace(old, new))
            rc_, out_, _ = run([LINT, fp_], env)
            os.remove(fp_)
            return rc_, out_
        rc, out = fam_fails("type: broll", "type: dialogue")
        check("a dialogue family → lint FAILS (the lane is inserts and b-roll only)", rc == 1 and "insert / broll only" in out, out)
        rc, out = fam_fails("function: the boom down into the grove that the next line pays off",
                            "function: proof of the results")
        check("a family that carries proof of a claim → lint FAILS", rc == 1 and "PROOF of a claim" in out, out)
        rc, out = fam_fails("cut_max: 2.5", "cut_max: 4")
        check("cut_max over 2.5 s → lint FAILS (a longer shot is a hero shot)", rc == 1 and "cut_max: 4" in out, out)
        rc, out = fam_fails("payload:", "refs:\n  - role: image_references · what: character · value: job_face\npayload:")
        check("a family binding a character reference → lint FAILS (identity is shot by shot)",
              rc == 1 and "binds no character reference" in out, out)
        many = "".join(f"  - shot: S8m{i} · start_frame: 02-startframes/S9a.png · row: row {i}\n" for i in range(13))
        rc, out = fam_fails("  - shot: S9a · start_frame: 02-startframes/S9a.png · row: first row\n"
                            "  - shot: S9b · start_frame: 02-startframes/S9b.png · row: last row\n", many)
        check("13 members → lint FAILS (one approval covers at most 12)", rc == 1 and "at most 12" in out, out)
        rc, out = fam_fails("row: last row", "row: last row · light: dusk")
        check("a member setting an undeclared key → lint FAILS", rc == 1 and "sets light" in out, out)
        hand = os.path.join(PD, "S9c.clip.prompt.md"); open(hand, "w").write(B.replace("shot: S5", "shot: S9c"))
        rc, out = fam_fails("  - shot: S9b · start_frame: 02-startframes/S9b.png · row: last row\n",
                            "  - shot: S9c · start_frame: 02-startframes/S9b.png · row: last row\n")
        check("a family never overwrites a hand-written prompt", rc == 1 and "was not generated from this family" in out, out)
        os.remove(hand)
        for x in ("S9a", "S9b"):
            drop(os.path.join(PD, f"{x}.clip.prompt.md"))
        os.remove(fam_p)

        # 12c-quinquies. MEDIA THAT NEVER PASSED THE GATE (P8, "log-external + reconcile") and THE
        # EVALUATION TIER (P9, "Adopt, ship-refusal enforced") — both house decisions 2026-10-25.
        rc, out, _ = run([GATE, "reconcile", "--files"], env)
        check("reconcile --files lists the media no pull and no log accounts for", rc == 1 and "untraced" in out, out)
        os.makedirs(os.path.join(job, "04-broll"), exist_ok=True)
        web = os.path.join(job, "04-broll", "S5_grove_kling_v1.mp4"); open(web, "wb").write(b"\x00 website free gen")
        le = [GATE, "log-external", "04-broll/S5_grove_kling_v1.mp4", "--by", "Dana", "--source", "website",
              "--model", "kling3_0", "--seconds", "5"]
        rc, out, err = run(le + ["--res", "480p", "--frame", "S5"], env)
        check("a free 480p website generation in a PRODUCTION job → refused (the 720p video floor holds, v2.49)",
              rc == 1 and "under the 720p floor" in err, err)
        rc, out, err = run(le + ["--res", "1080p", "--frame", "S99"], env)
        check("a website generation from an unapproved still → refused", rc == 1 and "frame:S99 is not approved" in err, err)
        rc, out, err = run(le + ["--res", "1080p"], env)
        check("a website generation that names no start frame and no reason → refused", rc == 1 and "--no-frame" in err, err)
        rc, out, err = run(le + ["--res", "1080p", "--frame", "S5"], env)
        check("a 1080p website generation from an approved still → logged with its hash", rc == 0 and "LOGGED" in out, out + err)
        rc, out, _ = run([GATE, "reconcile", "--files"], env)
        check("...and reconcile counts it as traced", "04-broll/S5_grove_kling_v1.mp4" not in out, out)
        open(web, "ab").write(b" regraded")
        rc, out, _ = run([GATE, "reconcile", "--files"], env)
        check("a logged file edited afterwards → flagged as changed", rc == 1 and "changed after it was logged" in out, out)
        os.remove(web)
        cp_orig = open(cp, encoding="utf-8").read()
        open(cp, "w").write(cp_orig.replace("Next:", "Tier:       evaluation\nNext:"))
        rc, out, _ = run([GATE, "status", "--json"], env)
        check("Tier: evaluation with no Question: → the checkpoint does not validate", "needs `Question:`" in out, out)
        open(cp, "w").write(cp_orig.replace("Next:", "Tier:       evaluation\nQuestion:   does kling3_0 at 720p hold "
                                            "the grove texture at feed size? arms 720p vs 1080p; rule: 3 of 3 read the same\nNext:"))
        rc, out, _ = run([GATE, "status", "--json"], env)
        check("with its Question: the evaluation job validates and status reports the tier",
              '"tier": "evaluation"' in out and "needs `Question:`" not in out, out)
        fe, rc, out, pe = cast("S8ev", "kling3_0", "720p")
        check("in an evaluation job a 720p roster clip lints with a WARN, not a FAIL",
              rc == 0 and "EVALUATION TIER" in out, out)
        rc, out, err = run([GATE, "approve", "export", "--by", "Dana", "--quote", "ship the evaluation cut"], env)
        check("approve export in an evaluation job → refused", rc == 1 and "evaluation job" in err, err)
        rc, out, err = run([GATE, "approve", "lock", "--by", "Dana", "--quote", "lock the evaluation cut"], env)
        check("approve lock in an evaluation job → refused", rc == 1 and "evaluation job" in err, err)
        ev1 = os.path.join(job, "04-broll", "S5_grove_kling_v2.mp4"); open(ev1, "wb").write(b"\x00 eval take")
        rc, out, err = run([GATE, "log-external", "04-broll/S5_grove_kling_v2.mp4", "--by", "Dana", "--source",
                            "website", "--model", "kling3_0", "--res", "720p", "--seconds", "5", "--frame", "S5"], env)
        check("an evaluation file outside _eval/ → refused", rc == 1 and "_eval/" in err, err)
        os.makedirs(os.path.join(job, "_eval", "04-broll"), exist_ok=True)
        ev2 = os.path.join(job, "_eval", "04-broll", "S5_grove_kling_EVAL_v1.mp4"); open(ev2, "wb").write(b"\x00 eval take")
        rc, out, err = run([GATE, "log-external", "_eval/04-broll/S5_grove_kling_EVAL_v1.mp4", "--by", "Dana",
                            "--source", "website", "--model", "kling3_0", "--res", "720p", "--seconds", "5",
                            "--frame", "S5"], env)
        check("in _eval/ with EVAL in the name → logged at 720p", rc == 0 and "LOGGED" in out, out + err)
        rc, out, err = run([os.path.join(HERE, "export_qc.py"), ev2, "--format", "vertical-1080"], env)
        check("export_qc refuses an evaluation file before measuring it", rc == 1 and "REFUSED" in err, out + err)
        os.remove(ev1); os.remove(ev2); drop(fe)
        open(cp, "w").write(cp_orig)

        # 12c-sexies. A REPLICA IS FLAGGED, NEVER REFUSED (house decision 2026-10-25, "Any reference, flagged"):
        # replicate.py writes 00-brief/REPLICA-SOURCE.json and the gate shows it at status (and again at export)
        rs = os.path.join(job, "00-brief", "REPLICA-SOURCE.json")
        json.dump({"source": {"title": "ref spot", "owner": "Some Agency", "licence": "third-party"},
                   "closeness": 92.0, "band": "shot-for-shot", "flagged": True}, open(rs, "w"))
        rc, out, _ = run([GATE, "status"], env)
        check("status shows what the job replicates, its licence and its closeness",
              "replicates **ref spot**" in out and "third-party" in out and "closeness 92.0 (shot-for-shot)" in out, out)
        rc, out, _ = run([GATE, "status", "--json"], env)
        check("…and carries it in the JSON", '"band": "shot-for-shot"' in out, out[-400:])
        os.remove(rs)

        f7, rc, out, p7 = cast("S7", "kling3_0", "1080p")
        run([GATE, "approve", "frame:S7", "--by", "Dana", "--quote", "S7 start, the grove row",
             "--artifact", "02-startframes/S5_a.png", "--media-id", "job_s7a"], env)
        v7 = {"model": "kling3_0", "prompt": p7, "duration": 6, "aspect_ratio": "9:16",
              "medias": [{"role": "start_image", "value": "job_s7a"}]}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", v7)
        check("kling3_0 with `sound` omitted (defaults ON) on a clip with no lines → pass (v2.49: native sound kept)",
              dec == "pass", why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**v7, "sound": "off"})
        check("kling3_0 with sound:'off' → pass (the switch used to be refused as an undeclared param)",
              dec == "pass", why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**v7, "sound": "off", "mode": "pro"})
        check("kling3_0 mode 'pro' (its QUALITY tier) → pass — one shared mode list refused it", dec == "pass", why)
        drop(f7)

        # gemini_omni_flash_1_1 — added by the author, 2026-09-19: "Google Omni 1.1 is not allowed. Should be."
        f8, rc, out, _ = cast("S8lo", "gemini_omni_flash_1_1", "720p")
        check("gemini at 720p (its DEFAULT) → lint FAILS the 1080p floor", rc == 1 and "1080p" in out, out)
        drop(f8)
        f8, rc, out, p8 = cast("S8", "gemini_omni_flash_1_1", "1080p")
        check("gemini_omni_flash_1_1 at 1080p lints — on the roster, priced, first frame flagged unmeasured",
              rc == 0 and "not been measured" in out, out)
        run([GATE, "approve", "frame:S8", "--by", "Dana", "--quote", "S8 start, the grove row",
             "--artifact", "02-startframes/S5_a.png", "--media-id", "job_s8a"], env)
        v8 = {"model": "gemini_omni_flash_1_1", "prompt": p8, "duration": 6, "aspect_ratio": "9:16",
              "resolution": "1080p", "medias": [{"role": "start_image", "value": "job_s8a"}]}
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", v8)
        check("gemini without mode → deny (it is REQUIRED; image-to-video for a frame call)",
              dec == "deny" and "image-to-video" in why, why)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**v8, "mode": "image-to-video"})
        check("gemini, approved start_image, mode image-to-video → pass", dec == "pass", why)
        rc, out, _ = run([GATE, "preflight", "S8", "--kind", "clip", "--json"], env)
        pf8 = json.loads(out)
        check("preflight S8 emits mode image-to-video and resolution 1080p, and passes",
              pf8["would_pass"] and pf8["params"].get("mode") == "image-to-video"
              and pf8["params"].get("resolution") == "1080p", out)
        drop(f8)
        f8d = os.path.join(job, "01-script", "prompts", "S8d.clip.prompt.md")
        open(f8d, "w").write(CLIP.replace("shot: S3", "shot: S8d").replace("model: minimax_h3", "model: gemini_omni_flash_1_1")
                             .replace("resolution: 2k", "resolution: 1080p")
                             .replace("seated at the tasting table", "seated at the gemini tasting table"))
        rc, out, _ = run([LINT, f8d], env)
        p8d = out.split("PROMPT (paste verbatim — the gate hashes it):", 1)[1].split("\nNEGATIVE", 1)[0].strip() \
            if "PROMPT (paste verbatim" in out else ""
        run([GATE, "approve", "frame:S8d", "--by", "Dana", "--quote", "S8d start, the host",
             "--artifact", "02-startframes/S3_host_v2.png", "--media-id", "job_s8d"], env)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video",
                           {"model": "gemini_omni_flash_1_1", "prompt": p8d, "duration": 6, "aspect_ratio": "9:16",
                            "mode": "image-to-video", "resolution": "1080p",
                            "medias": [{"role": "start_image", "value": "job_s8d"}]})
        check("gemini DIALOGUE clip before `audio` is approved → deny (native audio, no off switch)",
              dec == "deny" and "no off switch" in why, why)
        drop(f8d)

        # 13. per-stage-human → audio must be approved, then the decision is ask
        open(profile, "w").write(PROFILE.format(policy="per-stage-human"))
        open(cp, "w").write(CHECKPOINT.format(profile=profile, policy="per-stage-human"))
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", good)
        check("per-stage-human: dialogue clip before audio approval → deny", dec == "deny" and "`audio` must be approved" in why, why)
        # a multishot is `type: sequence`, not dialogue — its [SOUND] lines put it under the same gate
        fm_, rc, out, pm = ms_cast()
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**vm, "prompt": pm})
        check("per-stage-human: a multishot clip WITH LINES before audio approval → deny",
              dec == "deny" and "`audio` must be approved" in why and "multi-shot" in why, why)
        drop(fm_)
        run([GATE, "approve", "audio", "--by", "Dana", "--quote", "the VO take two is good"], env)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", good)
        check("per-stage-human: all gates passed → ask (the UI prompts the human)", dec == "ask" and "confirm this spend" in why, why)
        # ⚡ the allowance (2026-10-26: "the gate asks me for 10 images and then again for each
        # individual regen") — one approval covers the shot and 2 regens; the lint still runs on every call
        check("per-stage-human: the ask says one approval can cover the regens", "gate.py allow video --shots S3" in why, why)
        _tpv = os.path.join(env["CINE_HOME"], "transcript-allow-video.jsonl")   # (v2.61.0) the owner's words on record
        open(_tpv, "w").write("".join(json.dumps({"type": "user", "message": {"role": "user", "content": s}}) + "\n"
                                      for s in ("go ahead with S9 and two regens", "go ahead, S3 and two regens")))
        open(os.path.join(env["CINE_HOME"], "transcript-path"), "w").write(_tpv)
        rc, out, err = run([GATE, "allow", "video", "--shots", "S9", "--by", "Dana", "--quote", "go ahead with S9 and two regens"], env)
        check("allow: a shot with no linted prompt is refused", rc == 1 and "no current linted video prompt for S9" in err, err)
        rc, out, err = run([GATE, "allow", "video", "--shots", "S3", "--by", "Dana", "--quote", "go ahead, S3 and two regens"], env)
        check("allow: recorded as the first generation plus 2 regens", rc == 0 and "ALLOWANCE A1 video: S3" in out
              and "3/3 left" in out, out + err)
        # (v2.61.0) an allowance whose quote was never checked covers nothing: mark A1 unverified, the call asks again
        _alp = [x for x in (os.path.join(job, ".gate", "allowances.json"),) if os.path.isfile(x)]
        if _alp:
            _rows = json.load(open(_alp[0], encoding="utf-8"))
            _keep = json.dumps(_rows)
            for _r in _rows if isinstance(_rows, list) else []:
                _r["verified"] = "UNVERIFIED"
            json.dump(_rows, open(_alp[0], "w", encoding="utf-8"))
            _d, _w, _ = hook(env, "mcp__Higgsfield__generate_video", good)
            check("(v2.61.0) an allowance with an unchecked quote pre-approves nothing", _d == "ask", _w)
            open(_alp[0], "w", encoding="utf-8").write(_keep)
        else:
            check("(v2.61.0) the allowances file is where the test expects it", False, "no .gate/allowances.json")
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", {**good, "prompt": good["prompt"] + " Extra words."})
        check("allow: a prompt that is not the linted one is still refused", dec == "deny", why)
        # (3.1 build review) a covered call with no session_id is denied AND keeps its regen
        rc, out, _ = run([GATE, "hook"], env, stdin=json.dumps({"hook_event_name": "PreToolUse", "tool_input": {"params": good},
                                                                "tool_name": "mcp__Higgsfield__generate_video"}))
        rc2, out2, _ = run([GATE, "status"], env)
        check("(3.1 build review) no session_id: denied, and the allowance stays at 3/3", '"deny"' in out and "3/3 left" in out2,
              out + out2[-300:])
        # (wave 2c) a covered call that hits the studio ceiling asks AND keeps its regen (the allowance is not spent)
        _stv = os.path.join(td, "studio-ceiling-v"); os.makedirs(_stv, exist_ok=True)
        json.dump({"monthly_credit_ceiling": 0.5}, open(os.path.join(_stv, "studio.json"), "w"))
        _d, _w, _ = hook(dict(env, CINE_STUDIO=_stv), "mcp__Higgsfield__generate_video", good)
        rc, out, err = run([GATE, "status"], env)
        check("(wave 2c) an allowance-covered call over the ceiling asks and leaves the allowance at 3/3",
              _d == "ask" and "budget stop" in _w and "3/3 left" in out, f"{_d} {_w} {out[-400:]}")
        decs = [hook(env, "mcp__Higgsfield__generate_video", good)[0] for _ in range(3)]
        dec4, why4, _ = hook(env, "mcp__Higgsfield__generate_video", good)
        check("allow: the generation and two regens go through without a prompt; the third regen asks again",
              decs == ["allow"] * 3 and dec4 == "ask" and "used up" in why4, f"{decs} {dec4} {why4}")
        rc, out, err = run([GATE, "status"], env)
        check("status shows the allowance and what is left", "allowance A1 video: S3" in out and "0/3 left" in out, out)
        rc, out, err = run([GATE, "allow", "--revoke", "all"], env)
        check("allow --revoke", rc == 0 and "revoked A1" in out, out + err)
        # (wave 2c) the studio's default_regens pre-fills an allowance; an explicit --regens still wins, up to 5
        _str = os.path.join(td, "studio-regens"); os.makedirs(_str, exist_ok=True)
        json.dump({"default_regens": 1}, open(os.path.join(_str, "studio.json"), "w"))
        _envr = dict(env, CINE_STUDIO=_str)
        rc, out, err = run([GATE, "allow", "video", "--shots", "S3", "--by", "Dana", "--quote", "go ahead, S3 and two regens"], _envr)
        check("(wave 2c) no --regens + studio default_regens 1 → the allowance covers 2 generations", rc == 0 and "2/2 left" in out, out + err)
        rc, out, err = run([GATE, "allow", "video", "--shots", "S3", "--regens", "4", "--by", "Dana", "--quote",
                            "go ahead, S3 and two regens"], _envr)
        check("(wave 2c) an explicit --regens 4 still records 4 (a pre-fill, not a limit)", rc == 0 and "5/5 left" in out, out + err)
        rc, out, err = run([GATE, "allow", "video", "--shots", "S3", "--regens", "6", "--by", "Dana", "--quote",
                            "go ahead, S3 and two regens"], _envr)
        check("(wave 2c) --regens 6 is still refused", rc == 1 and "0..5" in err, out + err)
        json.dump({"default_regens": 7}, open(os.path.join(_str, "studio.json"), "w"))
        rc, out, err = run([GATE, "status"], _envr)
        check("(wave 2c) a hand-edited default_regens 7 is ignored: the house 2, with a note in status",
              "regens per approval 2 (house)" in out and "default_regens: 0, 1 or 2" in out, out)
        run([GATE, "allow", "--revoke", "all"], env)

        # 14. status and reconcile
        rc, out, err = run([GATE, "status", "--json"], env)
        st = json.load(open(os.devnull)) if False else json.loads(out)
        check("status lists approvals and prompts", rc == 0 and len(st["approved"]) >= 6 and len(st["prompts"]) == 3, out)
        # 14b. ⚡ a supplement ad job (2026-10-28): status took over 120 s — fast by default, --full re-lints; cast; where; a
        # profile path from another machine; pre-lock
        check("status is fast by default and says how it checked", st.get("checked") == "fast", out)
        rc, out, err = run([GATE, "status"], env)
        check("status prints the fast-check line with the way to the full one", "checked: fast" in out and "status --full" in out, out)
        rc, out, err = run([GATE, "status", "--full", "--json"], env)
        check("status --full re-lints (checked: full)", rc == 0 and json.loads(out).get("checked") == "full", out + err)
        check("status keeps its hash cache under .gate/", os.path.isfile(os.path.join(job, ".gate", "hash-cache.json")))
        rc, out, err = run([GATE, "where"], env)
        check("where names this install's scripts folder", rc == 0 and HERE in out and job in out, out + err)
        cast_ = _g.cast_line([{"stage": "character:B"}, {"stage": "character:A"}, {"stage": "script"}])
        check("the cast line names the approved characters and says cast is one sign-off on top",
              "character:A, character:B approved" in cast_ and "one approval" in cast_ and _g.cast_line([]) == "approve cast", cast_)
        os.makedirs(os.path.join(td, "_cine-clients"), exist_ok=True)
        shutil.copy(profile, os.path.join(td, "_cine-clients", os.path.basename(profile)))
        cp_txt = open(cp, encoding="utf-8").read()
        open(cp, "w", encoding="utf-8").write(cp_txt.replace(profile, "/home/claude/elsewhere/_cine-clients/"
                                                             + os.path.basename(profile)))
        rc, out, err = run([GATE, "status"], env)
        check("a profile path from another machine resolves from a _cine-clients/ above the job, and says so",
              "no such profile" not in out and "not on this machine" in out, out)
        open(cp, "w", encoding="utf-8").write(cp_txt)
        rc, out, err = run([GATE, "pre-lock"], env)
        check("pre-lock (dry) names the three renders, writes nothing, and lists what lock still needs",
              rc == 0 and out.count("would write") == 3 and "LEFT BEFORE `approve lock`" in out and "✓ QA log" in out
              and "✓ motion and joins" in out and "sound-off read" in out
              and not os.path.isdir(os.path.join(job, "07-edit", "_queue")), out + err)
        bare = os.path.join(td, "bare-job"); os.makedirs(os.path.join(bare, "00-brief"), exist_ok=True)
        left = {n_: ok_ for n_, ok_, _l in _g.prelock_left(_g.Job(bare))}
        check("pre-lock on a job with no QA log and no joins lists both as left", left.get("QA log") is False
              and left.get("motion and joins") is False, str(left))
        rc, out, err = run([GATE, "pre-lock", "--write", "--host-job", "/Users/someone/jobs/fx"], env)
        q = os.path.join(job, "07-edit", "_queue")
        files = sorted(os.listdir(q)) if os.path.isdir(q) else []
        cut = open(os.path.join(q, "render-cut.py"), encoding="utf-8").read() if "render-cut.py" in files else ""
        toff = open(os.path.join(q, "render-titles-off.py"), encoding="utf-8").read() if files else ""
        ponly = open(os.path.join(q, "render-picture-only.py"), encoding="utf-8").read() if files else ""
        check("pre-lock --write: three filled render-mp4.py copies, sized from the CHECKPOINT format, on the host path",
              files == ["render-cut.py", "render-picture-only.py", "render-titles-off.py"]
              and "OUTPUT_FOLDER = '/Users/someone/jobs/fx/07-edit'" in cut and "OUTPUT_FILENAME = 'fx-01001-test-v1-cut'" in cut
              and "WIDTH = 1080" in cut and "HEIGHT = 1920" in cut and "\nTITLES_OFF = False" in cut
              and "\nTITLES_OFF = True" in toff and "/09-qa/titles'" in toff and "\nPICTURE_ONLY = True" in ponly
              and all(compile(t, "q", "exec") for t in (cut, toff, ponly)), out + err + str(files))
        tx = os.path.join(td, "tx.json")
        json.dump([{"id": "g1", "model": "minimax_h3", "cost": 12, "prompt": cprompt},
                   {"id": "g2", "model": "kling3_0", "cost": 40, "prompt": "a fox running through a field, 8k, cinematic"}],
                  open(tx, "w"))
        rc, out, err = run([GATE, "reconcile", tx], env)
        check("reconcile reports the ungated spend", rc == 1 and "1 without one" in out and "40 credits ungated" in out, out)
        # the served model is the only model there is — a linted prompt run by a different model
        tx2 = os.path.join(td, "tx2.json")
        json.dump([{"id": "g3", "model": "seedance_2_5", "cost": 9, "prompt": cprompt}], open(tx2, "w"))
        rc, out, err = run([GATE, "reconcile", tx2], env)
        check("reconcile catches a served model that is not the requested one",
              rc == 1 and "SERVED MODEL" in out and "asked minimax_h3" in out and "served seedance_2_5" in out, out)

        # 15. checkpoint breakage after open is caught at the hook
        open(cp, "w").write(CHECKPOINT.format(profile=profile, policy="per-stage-human").replace("Approver:   Dana", "Approver:   <who>"))
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", good)
        check("checkpoint edited to a placeholder after open → deny", dec == "deny" and "no longer validates" in why, why)

        # 16. escape hatch is logged, close denies again
        env2 = {**env, "CINE_GATE": "off"}
        dec, _, ctx = hook(env2, "mcp__Higgsfield__generate_video", {"model": "kling3_0", "prompt": "anything"})
        check("CINE_GATE=off passes with a warning in context and a bypass.log line", dec == "pass" and "bypassed" in ctx
              and os.path.isfile(os.path.join(env["CINE_HOME"], "bypass.log")), ctx)
        import shot_manifest as _sm                 # (3.1) close writes the scorecard, derived from the manifest
        _mp = _sm.manifest_path(job); os.makedirs(os.path.dirname(_mp), exist_ok=True)
        json.dump({"rows": [{"id": "S1#1", "shot": "S1", "kind": "broll", "file": "x.mp4", "cost_credits": 8,
                             "qa_status": "select"}]}, open(_mp, "w"))
        _sc = os.path.join(job, "99-costs", "SCORECARD.md")
        if os.path.exists(_sc):
            os.remove(_sc)
        rc, out, err = run([GATE, "close"], env)
        check("(3.1) close writes 99-costs/SCORECARD.md from the manifest", rc == 0 and os.path.isfile(_sc)
              and "| Takes kept | 1 |" in open(_sc).read(), out + err)
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_video", good)
        check("after close → deny", dec == "deny" and "No production job" in why, why)

        # 17. prompt_lint refusals that protect credits
        bad = CLIP.replace("model: minimax_h3", "model: wan2_7")
        open(cl, "w").write(bad); rc, out, _ = run([LINT, cl], env)
        check("off-roster model fails lint", rc == 1 and "roster" in out, out)
        bad = CLIP.replace("resolution: 2k", "resolution: 720p")
        open(cl, "w").write(bad); rc, out, _ = run([LINT, cl], env)
        check("unknown resolution row fails lint", rc == 1 and "has no '720p' row" in out, out)
        bad = CLIP.replace("model: minimax_h3", "model: minimax_h3_max").replace("resolution: 2k", "resolution: 768p")
        open(cl, "w").write(bad); rc, out, _ = run([LINT, cl], env)
        check("768p clears the 720p video floor (v2.49; `floor-1080` restores 1080p)",
              "video floor" not in out and "1080p floor" not in out, out)
        bad = CLIP.replace("duration: 6", "duration: 40")
        open(cl, "w").write(bad); rc, out, _ = run([LINT, cl], env)
        check("duration outside the model range fails", rc == 1 and "outside" in out, out)
        bad = CLIP.replace("[MOTION]", "[ENVIRONMENT]\nsunny tasting room\n\n[MOTION]")
        open(cl, "w").write(bad); rc, out, _ = run([LINT, cl], env)
        check("picture block in an i2v clip fails (the §11 fork)", rc == 1 and "i2v clip prompt" in out, out)
        bad = CLIP.replace("locked-off, eye level", "handheld, slow dolly in, then a whip pan")
        open(cl, "w").write(bad); rc, out, _ = run([LINT, cl], env)
        check("several camera moves fail (one behaviour per clip)", rc == 1 and "camera" in out.lower(), out)
        bad = CLIP.replace('line: "We taste it before you ever see it."',
                           'line: "We taste every single bottle in the tasting room before any buyer anywhere in the world ever sees it, and that is the whole point of the grove."')
        open(cl, "w").write(bad); rc, out, _ = run([LINT, cl], env)
        check("a line longer than the clip fails", rc == 1 and "needs ~" in out, out)
        check("a failed lint removes the stale .ok", not os.path.isfile(cl[:-3] + ".ok"))

        stills_suite(td, profile)
        eval_lane_suite(td, profile)         # (v2.72.0) the evaluation lane
        switches_suite(td, profile)          # (v2.48.0, project switches)
        fail_closed_suite(td)                # (v2.52.4) a broken gate still blocks
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print("-" * 60)
    if fails:
        print(f"FAIL ({len(fails)}): " + "; ".join(fails)); return 1
    print("gate suite OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
