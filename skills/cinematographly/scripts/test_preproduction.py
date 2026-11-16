#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""test_preproduction.py — the pre-production stage as ONE STORY, through the real CLIs.

Run: python3 scripts/test_preproduction.py     (stdlib only · no network · no credits · no key)

WHY THIS EXISTS, SEPARATELY FROM THE SELFTESTS
Every script here already has a selftest, and every selftest passes on scripts that do not compose.
`develop.py` knows about a look board, `refsource.py` knows about gaps, `gate.py` knows about
approvals — and until this file, nothing ran them in the order a person actually runs them, on one
job folder, with each step's output being the next step's input. The bugs that survive unit tests
are exactly the ones that live in the seams: two sidecar naming conventions, a plan row that reads
"bound at call time" when it means "nothing here", a gate that reads a different folder than the
linter writes.

So this walks the stage in order and asserts the REFUSAL at each point, because the refusals are
the product. A pre-production gate that can be walked past is decoration.

  1  open the job                     · CHECKPOINT validated
  2  develop init                     · the template lands
  3  approve concept                  → REFUSED: no research
  4  research only                    → REFUSED: LOOK, named specifically
  5  pictures with no sidecars        → REFUSED: no provenance
  6  a listed picture not on disk     → REFUSED: the board is files, not captions
  7  four real pictures + sidecars    · LOOK satisfied, now refused on concepts
  8  five concepts, two kill rounds   → REFUSED until the HUMAN's quote is there
  9  the human picks                  · approve concept PASSES
 10  approve script                   → REFUSED: no hooks, one draft
 11  hooks + 3 drafts + critiques     · approve script PASSES with --artifact
 12  shots declaring `need:` slots    · the plan shows gaps, the lint FAILS the prompt
 13  refsource brief                  · a query per gap, from the shot's own words, NO network
 14  refsource fill (no --execute)    · dry run: prints commands, downloads nothing
 15  approve cast                     → REFUSED, naming the unsourced shots
 16  candidates land                  · the lookbook lists them
 17  adopt an uncleared asset         → REFUSED
 18  adopt a TYPED "CLEARED"          → REFUSED — clearance is re-derived, never read
 19  a real provenance record         · adopt PASSES, the ref line is rewritten
 20  the second slot reference-only   · adopt PASSES
 21  approve cast                     · PASSES — the plan is clean
 22  a generation before the lint     → the hook DENIES it

WHAT THIS FILE CANNOT TEST
- Whether an AGENT handed the skill actually does any of this. These are the gates; a person or an
  agent still has to walk into them. `evals/` is that half — `claude plugin eval` runs the skill in
  a fresh session and grades what the model did. Neither replaces the other.
- Whether the PreToolUse hook fires in a real client. Step 22 calls `gate.py hook` directly with a
  hook-shaped payload, which proves the DECISION; that the client delivers the payload at all was
  verified live on 2026-09-06 and is re-checked by running one real generation per release.
- Whether the pictures are any good. That is the point of the human in step 16.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
GATE = os.path.join(HERE, "gate.py")
DEV = os.path.join(HERE, "develop.py")
REFSRC = os.path.join(HERE, "refsource.py")
LINT = os.path.join(HERE, "prompt_lint.py")
PROV = os.path.join(HERE, "provenance.py")
BOARD = os.path.join(HERE, "board.py")
BREAK = os.path.join(HERE, "breakdown.py")
SHOTLIST = os.path.join(HERE, "shotlist.py")

FAILS: list = []


def check(name: str, cond, detail: str = "") -> None:
    print(f"  [{' ok ' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)
        for line in str(detail).strip().splitlines()[:6]:
            print(f"        {line}")


def run(argv: list, env: dict, cwd: str | None = None) -> tuple:
    # (3.1) these approvals have no session transcript, so the test home is explicitly hookless
    _h = env.get("CINE_HOME")
    if _h and not env.get("CINE_TEST_HOOKED"):
        os.makedirs(_h, exist_ok=True)
        if not os.path.exists(os.path.join(_h, "config.json")):
            open(os.path.join(_h, "config.json"), "w").write('{"hookless": true}')
    p = subprocess.run([sys.executable] + argv, capture_output=True, text=True, env=env, cwd=cwd,
                       timeout=120)
    return p.returncode, p.stdout, p.stderr


def hook(env: dict, tool: str, payload: dict) -> tuple:
    """One PreToolUse decision, through the same entry point the client calls."""
    body = json.dumps({"tool_name": tool, "tool_input": payload})
    p = subprocess.run([sys.executable, GATE, "hook"], input=body, capture_output=True, text=True,
                       env=env, timeout=60)
    try:
        out = json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        return "unparseable", p.stdout + p.stderr, {}
    h = out.get("hookSpecificOutput", out)
    return h.get("permissionDecision", "?"), h.get("permissionDecisionReason", ""), out


# ------------------------------------------------------------------------------------- fixtures
PROFILE = """# Client Profile — Fixture Bakery

## 0. ⛔ Hard locks (read before any change)

**Default mode:** A — one hero film.

1. **Format lock?** open
2. **Audio-text lock?** lines are approved as-is once the script is signed
3. **Overlay policy?** captions only
4. **Retired tools/models?** none

**Verification policy:** `gated`

**Named approver:** Dana

## 1. Brand(s)
- Fixture Bakery — bread.

## 5. Generation stack
- image model: nano_banana · video model: minimax_h3
"""

CHECKPOINT = """# PRODUCTION CHECKPOINT

Job:        fx-02001-preprod
Mode:       A — one hero film carrying the message
Client:     {profile}
Policy:     gated
Format:     vertical-1080 (master) · derived: none
            generation: 1080p minimum, minimax_h3 2k dialogue, kling3_0 4k b-roll
Voice:      none — house register, flagged
Inputs:     approved-language PRESENT · archive+licensing MISSING (accepted risk: fixture job) ·
            personas PRESENT · brand assets PRESENT · music library MISSING (asked 2026-09-06) ·
            spend context PRESENT · reference images MISSING (asked 2026-09-06)
Gates:      ideation → look board → script scorecard → blocking → reference plan → frame gate →
            prompt lint → QA → compliance → export QC
Skips:      none
Budget:     envelope 900 cr (client) · estimate 610 cr [estimated] · preflight 99-costs/PREFLIGHT-2026-09-06.md
Approver:   Dana
Next:       fill the look board
"""


def research_lines(n: int = 7) -> str:
    return "\n".join(
        f"- [PRIMARY · source{i} · 2026-09-0{i % 9 + 1}] a fact that decides something real "
        f"about the film number {i}" for i in range(1, n + 1))


def concepts() -> str:
    seeds = [("a grove at dawn", "two-hander", "Can origin be proven?"),
             ("a bottle on a steel bench", "demo", "What does grade actually mean?"),
             ("a buyer's spreadsheet", "list", "Which supplier survives an audit?"),
             ("hands sorting olives", "single-take monologue", "Who picks these?"),
             ("an empty shelf", "testimonial-shaped", "Why did the last shipment fail?")]
    return "\n".join(f"### C{i} · concept {i}\npremise: sentence {i} distinct wording here\n"
                     f"question: {q}\nimage: {img}\nstructure: {st}\n"
                     f"proof: reason {i} unique to this brand\nrisk: risk {i}\n"
                     for i, (img, st, q) in enumerate(seeds, 1))


ROUNDS = ("## Adversarial round 1 · the skeptical buyer\n\n"
          "killed: C3 — the claim needs a document nobody has\n"
          "weakened: C1 — the proof is thin\nsurvived: C1, C2, C4, C5\n\n"
          "## Adversarial round 2 · the bored scroller\n\n"
          "killed: C5 — nothing happens in the first two seconds\n"
          "weakened: C4 — the open is a talking head\nsurvived: C1, C2, C4\n")

CHOICE = ('## Choice\n\nchosen: C2\nby: Dana\n'
          'quote: "C2, the bench one, it is the only one we can shoot"\n'
          'why: the only concept the assets support\n')

TAIL = ("\n## Hooks\n\n| ID | awareness | type | the line / beat | the gap |\n|---|---|---|---|---|\n"
        "| H1 | problem-aware | curiosity gap | I paid 400 for the wrong grade | which grade they were sold · because they have a bottle of it at home |\n"
        "| H2 | solution-aware | skeptic | I assumed the certificate was theatre | whether the certificate means anything · because they already pay a premium for it |\n"
        "| H3 | problem-aware | demonstration | this is what nine months in steel does | what storage does to the oil · because their own bottle has been open since spring |\n"
        "| H4 | unaware | story cold open | the buyer put it back on the shelf | why a professional rejected it · because they buy this brand every fortnight |\n"
        "| H5 | most-aware | direct offer | twelve a bottle, no subscription | what the price actually is · because they have been comparing for a fortnight |\n"
        "\n"
        "## Drafts\n\n### v1\ndraft\ncritique: the hook line about origin announces the topic "
        "instead of opening a gap in the first beat\n\n### v2\ndraft\ncritique: scene two has no "
        "value turn, the buyer line lands flat and the CTA arrives before any proof\n\n### v3\nfinal\n")

# The house script shape (references/script-format.md): [HOOK] · [SCENE n — …] · [CTA], with the
# speaker label and the line. shotlist.py derives from exactly this, so the fixture has to BE it —
# a fixture in a shape the tool does not accept tests nothing.
SCRIPT = """# SCRIPT v3 — fixture

## Control idea (one sentence)
Bread proves itself.

## SCRIPT

[HOOK 0:00–0:06]  the room before anyone arrives

[SCENE 1 — the bench]  ESTABLISH — a working bakery an hour before it opens
HOST: „Every loaf starts in the same room."

[SCENE 2 — the counter]  TURN — the value changes
HOST: „You taste it first."

[CTA 0:16–0:20]  the resolved state, in-world branding
HOST: „Come before they go."
"""

FRAME = """---
shot: {shot}
kind: frame
type: environment
model: nano_banana
aspect: 9:16
variants: 2
refs:
{refs}
---
[SUBJECT]
A baker slides a tray forward, mid-action

[ENVIRONMENT]
A small tiled kitchen, flour dusting the counter, a shelf of tins, a window behind

[LIGHTING]
5200K daylight, soft from the left, long diagonal shadows

[CAMERA]
35mm, eye level

[STYLE]
phone-real, mild grain

[SUPPRESS]
extra hands, text, watermark
"""


def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def write(p: str, text: str) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def jpg(p: str, salt: bytes = b"") -> None:
    """A REAL image when Pillow is here, so board.py's embedding path is actually exercised —
    a fixture that only ever feeds a checker bytes it cannot read tests the error branch."""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        from PIL import Image
        c = (60 + (salt[0] if salt else 0) * 7) % 256
        Image.new("RGB", (120, 90), (c, 140, 200 - c % 100)).save(p, "JPEG")
    except Exception:
        with open(p, "wb") as fh:
            fh.write(b"\xff\xd8\xff\x00fixture" + salt)


def dev_doc(*, research=True, look="", concepts_in=True, choice=True, tail=True) -> str:
    parts = ["# DEVELOPMENT — fixture\n"]
    parts.append("\n## Research\n" + (research_lines() if research else "(none yet)\n"))
    if look:
        parts.append("\n## Look\n" + look + "\n")
    if concepts_in:
        parts.append("\n## Concepts\n\n" + concepts())
        parts.append(ROUNDS)
    if choice:
        parts.append(CHOICE)
    if tail:
        parts.append(TAIL)
    return "\n".join(parts)


def look_lines(names: list) -> str:
    return "\n".join(f"- [environment] 00-brief/_look/{n} — what picture {i} settles"
                     for i, n in enumerate(names, 1))


# ----------------------------------------------------------------------------------------- main
def main() -> int:
    td = tempfile.mkdtemp(prefix="preprod-test-")
    try:
        # CINE_ARCHIVE too — see the note in test_gate.py: a fixture script filed into the
        # shipped recall corpus becomes a false ⛔ hit in a real query.
        env = {**os.environ, "CINE_HOME": os.path.join(td, "home"),
               "CINE_ARCHIVE": os.path.join(td, "archive")}
        env.pop("CINE_JOB", None)
        env.pop("CINE_GATE", None)
        job = os.path.join(td, "fx-02001-preprod")
        prompts = os.path.join(job, "01-script", "prompts")
        look = os.path.join(job, "00-brief", "_look")
        for d in ("00-brief", "00-brief/_look", "01-script/prompts", "02-startframes"):
            os.makedirs(os.path.join(job, d))
        profile = os.path.join(td, "fixture-client.md")
        write(profile, PROFILE)
        write(os.path.join(job, "00-brief", "CHECKPOINT.md"), CHECKPOINT.format(profile=profile))
        DEVMD = os.path.join(job, "00-brief", "DEVELOPMENT.md")

        print("pre-production — the stage as one story\n")

        # -- 1 · the job opens -----------------------------------------------------------------
        rc, out, err = run([GATE, "open", job], env)
        check("1  the job opens against a validated checkpoint", rc == 0, out + err)

        # -- 2 · the development doc ------------------------------------------------------------
        rc, out, err = run([DEV, "init", job], env)
        check("2  develop init writes the template", rc == 0 and os.path.isfile(DEVMD), out + err)

        # -- 3 · nothing is written yet ---------------------------------------------------------
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana",
                            "--quote", "looks good to me"], env)
        check("3  approve concept on an unfilled doc → REFUSED", rc == 1, err)

        # -- 4 · research alone is not a look ---------------------------------------------------
        write(DEVMD, dev_doc(look="", concepts_in=True, choice=True, tail=True))
        rc, out, err = run([DEV, "check", job, "--phase", "concept"], env)
        check("4  research + concepts but no look board → REFUSED, and LOOK is named",
              rc == 1 and "LOOK:" in (out + err), out + err)

        # -- 5 · pictures with no provenance ----------------------------------------------------
        names = [f"ref{i}.jpg" for i in range(1, 5)]
        for i, n in enumerate(names):
            jpg(os.path.join(look, n), salt=bytes([i]))
        write(DEVMD, dev_doc(look=look_lines(names)))
        rc, out, err = run([DEV, "check", job, "--phase", "concept"], env)
        check("5  four pictures with no provenance sidecar → REFUSED",
              rc == 1 and "no provenance sidecar" in (out + err), out + err)

        # -- 6 · a caption is not a picture -----------------------------------------------------
        for n in names:
            write(os.path.join(look, n + ".json"),
                  json.dumps({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                              "clearance": "NOT CLEARED — outstanding"}))
        write(DEVMD, dev_doc(look=look_lines(names[:3] + ["imagined.jpg"])))
        rc, out, err = run([DEV, "check", job, "--phase", "concept"], env)
        check("6  a listed picture that is not on disk → REFUSED",
              rc == 1 and "not on disk" in (out + err), out + err)

        # -- 7 · a real board ------------------------------------------------------------------
        write(DEVMD, dev_doc(look=look_lines(names)))
        rc, out, err = run([DEV, "check", job, "--phase", "concept"], env)
        check("7  four real pictures with provenance → the concept phase passes", rc == 0, out + err)

        # -- 8 · the human has not picked -------------------------------------------------------
        nopick = dev_doc(look=look_lines(names)).replace(
            'quote: "C2, the bench one, it is the only one we can shoot"', "quote: ok")
        write(DEVMD, nopick)
        rc, out, err = run([DEV, "check", job, "--phase", "concept"], env)
        check("8  a one-word approval is not the human picking → REFUSED",
              rc == 1 and "verbatim" in (out + err).lower(), out + err)

        # -- 9 · the boards, then the pick, then the gate ----------------------------------------
        write(DEVMD, dev_doc(look=look_lines(names)))
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana",
                            "--quote", "C2, the bench one, it is the only one we can shoot"], env)
        check("9  a complete development doc with NO concept board → REFUSED",
              rc == 1 and "concept board is not current" in err, err)
        rc, out, err = run([BOARD, "look", job], env)
        check("9  the look board renders every sourced picture into one file",
              rc == 0 and os.path.isfile(os.path.join(job, "00-brief", "BOARD-look.html")), out + err)
        rc, out, err = run([BOARD, "concepts", job], env)
        check("9  the concept board puts the five side by side", rc == 0 and "5 item" in out, out + err)
        board = read(os.path.join(job, "00-brief", "BOARD-concepts.html"))
        check("9  the board carries the kill REASON, not just the verdict",
              "KILLED" in board and "a document nobody has" in board)
        check("9  the board is one self-contained file that opens anywhere",
              "data:image/" not in board or "<script" not in board)
        rc, out, err = run([GATE, "approve", "concept", "--by", "Dana",
                            "--quote", "C2, the bench one, it is the only one we can shoot"], env)
        check("9  approve concept PASSES once research, look, concepts, kills and the pick exist",
              rc == 0, out + err)

        # -- 10 · a script needs drafts ---------------------------------------------------------
        write(DEVMD, dev_doc(look=look_lines(names), tail=False))
        scriptp = os.path.join(job, "01-script", "SCRIPT-fixture-v3.md")
        write(scriptp, SCRIPT)
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana",
                            "--quote", "the script is right, go", "--artifact", scriptp], env)
        check("10 approve script with no hooks and no drafts → REFUSED", rc == 1, err)

        # -- 11 · the full development doc ------------------------------------------------------
        write(DEVMD, dev_doc(look=look_lines(names)))
        rc, out, err = run([GATE, "approve", "script", "--by", "Dana",
                            "--quote", "the script is right, go", "--artifact", scriptp], env)
        check("11 approve script PASSES with 5 hooks, 3 drafts and 2 critiques behind it",
              rc == 0, out + err)

        # -- 12 · shots that declare what they need ---------------------------------------------
        s1 = os.path.join(prompts, "S1.frame.prompt.md")
        s3 = os.path.join(prompts, "S3.frame.prompt.md")
        write(s1, FRAME.format(shot="S1", refs=(
            "  - role: image, what: environment, need: small tiled bakery kitchen daylight\n"
            "  - role: image, what: wardrobe, need: white linen apron plain")))
        write(s3, FRAME.format(shot="S3", refs=(
            "  - role: image, what: prop, need: plain metal baking tray")))
        rc, out, err = run([LINT, prompts, "--plan"], env)
        check("12 the plan reports three gaps and refuses",
              rc == 1 and "3 reference(s) not sourced" in out, out + err)
        rc, out, err = run([LINT, s1], env)
        check("12 the lint FAILS a prompt whose slot is declared but unsourced",
              rc == 1 and "refsource.py" in (out + err), out + err)

        # -- 13 · the brief, with no network ----------------------------------------------------
        rc, out, err = run([REFSRC, "brief", prompts, "--json"], env)
        check("13 brief exits non-zero while gaps remain", rc == 1, err)
        briefs = json.loads(out)["briefs"]
        by = {b["what"]: b for b in briefs}
        check("13 one brief per gap", len(briefs) == 3 and set(by) == {"environment", "wardrobe", "prop"},
              json.dumps(sorted(by)))
        check("13 the query comes from the shot's own `need:`, in the order it was written",
              by["wardrobe"]["query"].startswith("white linen apron")
              and by["wardrobe"]["query_from"] == "need:", by["wardrobe"]["query"])
        check("13 aspect 9:16 becomes a vertical search",
              all(b["shape"] == "vertical" for b in briefs))
        check("13 the §5 risk for the attribute is stated BEFORE the search",
              "property release" in by["environment"]["risk"]
              and "trademark" in by["prop"]["risk"], by["prop"]["risk"])
        check("13 the brief names the shot that needs it, not just the attribute",
              by["prop"]["shot"] == "S3" and by["wardrobe"]["shot"] == "S1")

        # -- 14 · a dry run downloads nothing ---------------------------------------------------
        before = sorted(os.listdir(job))
        rc, out, err = run([REFSRC, "fill", prompts], env)
        check("14 fill without --execute is a dry run: prints the commands, exits 1",
              rc == 1 and "DRY RUN" in out and "pixabay_search.py" in out, out[:400])
        check("14 the dry run created nothing",
              sorted(os.listdir(job)) == before and not os.path.isdir(
                  os.path.join(job, "_reference")), sorted(os.listdir(job)))

        # -- 15 · the gate on spend -------------------------------------------------------------
        rc, out, err = run([GATE, "approve", "cast", "--by", "Dana",
                            "--quote", "the boards are right, cast it"], env)
        check("15 approve cast with unsourced references → REFUSED, naming the shots",
              rc == 1 and "reference plan is not sourced" in err and "S1" in err and "S3" in err, err)

        # -- 16 · candidates land (what `fill --execute` would have written) ---------------------
        cand = os.path.join(job, "_reference", "_candidates")
        picks = {}
        for shot, attr, n in (("s1", "environment", 2), ("s1", "wardrobe", 2), ("s3", "prop", 2)):
            d = os.path.join(cand, f"{shot}-{attr}")
            for k in range(n):
                a = os.path.join(d, f"pixabay-{attr[:3]}{k}-large.jpg")
                jpg(a, salt=f"{attr}{k}".encode())
                write(a + ".json", json.dumps({
                    "source": "pixabay", "id": k, "pageURL": f"https://pixabay.com/photos/{attr}-{k}/",
                    "user": "someone", "tags": f"{attr}, kitchen, plain",
                    "licence": {"name": "Pixabay Content License"},
                    "clearance": "NOT CLEARED — per-asset checks below are outstanding"}))
                picks.setdefault(attr, a)
        rc, out, err = run([REFSRC, "candidates", prompts], env)
        check("16 the lookbook lists every gap with its candidates and their page URLs",
              rc == 0 and out.count("pixabay.com/photos/") == 6
              and all(g in out for g in ("s1-environment", "s1-wardrobe", "s3-prop")), out[:400])

        # -- 17 · an uncleared asset ------------------------------------------------------------
        rc, out, err = run([REFSRC, "adopt", prompts, "--shot", "S1", "--what", "wardrobe",
                            "--pick", picks["wardrobe"]], env)
        check("17 adopting an asset that is still NOT CLEARED → REFUSED",
              rc == 1 and "NOT CLEARED" in err, err)

        # -- 18 · the fraud test: what would it take to pass this dishonestly? -------------------
        faked = picks["wardrobe"] + ".json"
        write(faked, json.dumps({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                                 "clearance": "CLEARED by me on 2026-09-06"}))
        rc, out, err = run([REFSRC, "adopt", prompts, "--shot", "S1", "--what", "wardrobe",
                            "--pick", picks["wardrobe"]], env)
        check("18 a TYPED 'CLEARED' with no blockers object → REFUSED as an assertion",
              rc == 1 and "assertion, not a record" in err, err)
        rc, out, err = run([PROV, "record", picks["wardrobe"], "--source", "pixabay",
                            "--face", "a recognisable face, no release",
                            "--trademark", "none — unbranded",
                            "--property", "none — plain background",
                            "--transformation", "reference only, conditions a generated frame",
                            "--cleared-by", "Dana", "--force"], env)
        rc, out, err = run([REFSRC, "adopt", prompts, "--shot", "S1", "--what", "wardrobe",
                            "--pick", picks["wardrobe"]], env)
        check("18 a real record whose face blocker still blocks → REFUSED",
              rc == 1 and "NOT CLEARED" in err, err)

        # -- 19 · a real, re-derivable, signed record -------------------------------------------
        rc, out, err = run([PROV, "record", picks["wardrobe"], "--source", "pixabay",
                            "--face", "none — a mannequin form, no person in frame",
                            "--trademark", "none — a generic motif, no mark",
                            "--property", "none — plain white background",
                            "--transformation", "reference only, conditions a generated frame, "
                                                "never composited or redistributed",
                            "--cleared-by", "Dana", "--force"], env)
        check("19 provenance.py record derives CLEARED once every blocker is answered",
              rc == 0 and "CLEARED by Dana" in out, out + err)
        rc, out, err = run([REFSRC, "adopt", prompts, "--shot", "S1", "--what", "wardrobe",
                            "--pick", picks["wardrobe"]], env)
        check("19 adopt PASSES on a real record", rc == 0, err)
        body = open(s1, encoding="utf-8").read()
        check("19 the shot's ref line now points at the adopted file, not a wish",
              "what: wardrobe, file: _reference/wardrobe/" in body and "need: white linen" not in body,
              body.split("---")[1])
        check("19 the adopted file and its sidecar landed on the one convention",
              os.path.isfile(os.path.join(job, "_reference", "wardrobe",
                                          os.path.basename(picks["wardrobe"])))
              and os.path.isfile(os.path.join(job, "_reference", "wardrobe",
                                              os.path.basename(picks["wardrobe"]) + ".json")))
        check("19 the decision is logged with who picked what",
              os.path.isfile(os.path.join(job, "_reference", "_refsource.json")))

        # -- 20 · reference-only is the other honest answer --------------------------------------
        for shot, attr in (("S1", "environment"), ("S3", "prop")):
            rc, out, err = run([REFSRC, "adopt", prompts, "--shot", shot, "--what", attr,
                                "--pick", picks[attr], "--use", "reference-only"], env)
            check(f"20 {shot}/{attr} adopts as reference-only", rc == 0, err)

        # -- 20b · the CROSS-SHOT view: the findings no single shot is wrong about ---------------
        rc, out, err = run([BREAK, job], env)
        check("20b the breakdown aggregates the requirements across every shot",
              "BREAKDOWN" in out and "environment" in out and "prop" in out, out + err)
        # two shots, each declaring the same unsourced attribute → ONE finding, not two
        write(os.path.join(prompts, "S5.frame.prompt.md"), FRAME.format(shot="S5", refs=(
            "  - role: image, what: light, need: hard raking window light")))
        write(os.path.join(prompts, "S6.frame.prompt.md"), FRAME.format(shot="S6", refs=(
            "  - role: image, what: light, need: hard raking window light")))
        rc, out, err = run([BREAK, job], env)
        check("20b two shots needing the same thing is one SOURCE-ONCE finding",
              out.count("source it ONCE") == 1, out)
        check("20b and it names both shots", "S5" in out and "S6" in out)
        # a character named in a shot with no locked reference blocks `cast`
        write(os.path.join(prompts, "S7.frame.prompt.md"),
              FRAME.format(shot="S7", refs="  - role: image, what: character, value: media_1")
              .replace("type: environment", "type: character\ncharacter: hero"))
        rc, out, err = run([BREAK, job], env)
        check("20b an unlocked character is a cross-shot finding",
              "not locked" in out or "CHARACTER-hero" in out, out)
        rc, out, err = run([GATE, "approve", "cast", "--by", "Dana",
                            "--quote", "the boards are right, cast it"], env)
        check("20b approve cast is REFUSED while the cast is not locked by a reference",
              rc == 1 and "the cast is not locked" in err, err)
        os.makedirs(os.path.join(job, "_reference"), exist_ok=True)
        write(os.path.join(job, "_reference", "CHARACTER-hero.md"), "# hero\n")
        for f in ("S5", "S6", "S7"):
            os.remove(os.path.join(prompts, f"{f}.frame.prompt.md"))

        # -- 20c · the shot list, DERIVED rather than blank --------------------------------------
        rc, out, err = run([SHOTLIST, job, "--check"], env)
        check("20c --check says plainly there is no shot list yet", rc == 1 and "no shot list" in err, err)
        rc, out, err = run([SHOTLIST, job], env)
        check("20c the shot list derives from the approved script",
              rc == 0 and "derived" in out and "SCRIPT-fixture-v3.md" in out, out + err)
        sl = read(os.path.join(job, "01-script", f"SHOTLIST-{os.path.basename(job)}.md"))
        check("20c the script's own lines are carried in, not re-typed",
              "Every loaf starts in the same room" in sl or "You taste it first" in sl, sl[:300])
        check("20c ⛔ no shot size or camera move was invented", "<NEEDS DIRECTION>" in sl)
        rc, out, err = run([SHOTLIST, job], env)
        check("20c re-deriving over a director's work is REFUSED without --force",
              rc == 1 and "already exists" in err, err)

        # -- 21 · the plan is clean, the board is current, the gate opens ------------------------
        rc, out, err = run([GATE, "approve", "cast", "--by", "Dana",
                            "--quote", "the boards are right, cast it"], env)
        check("21 a clean plan with NO shot board → still REFUSED",
              rc == 1 and "shot board is not current" in err, err)
        rc, out, err = run([BOARD, "shots", job], env)
        check("21 the shot board renders every reference slot as a picture",
              rc == 0 and os.path.isfile(os.path.join(job, "01-script", "BOARD-shots.html")), out + err)
        sb = read(os.path.join(job, "01-script", "BOARD-shots.html"))
        try:
            import PIL  # noqa: F401
            check("21 the adopted references appear as embedded images, not filenames",
                  sb.count("data:image/") >= 2, str(sb.count("data:image/")))
        except ImportError:
            print("  [skip] embedded-image check — Pillow not installed")
        check("21 the board says every reference is sourced and cleared",
              "every reference sourced and cleared" in sb)
        rc, out, err = run([LINT, prompts, "--plan"], env)
        check("21 the plan is clean: nothing unsourced, nothing uncleared",
              rc == 0 and "0 reference(s) not sourced · 0 not cleared" in out, out)
        rc, out, err = run([GATE, "approve", "cast", "--by", "Dana",
                            "--quote", "the boards are right, cast it"], env)
        check("21 approve cast PASSES once every reference is sourced and cleared", rc == 0, err)

        # -- 21b · a STALE board is not a board -------------------------------------------------
        import time as _t
        _t.sleep(1.1)
        write(s3, read(s3) + "\n[SAFE ZONE]\ntop 35% clear for the title\n")
        rc, out, err = run([GATE, "approve", "clips", "--by", "Dana",
                            "--quote", "the selects are right, cut it"], env)
        check("21b editing a prompt after the board was built → REFUSED as stale",
              rc == 1 and "older than" in err and "S3" in err, err)
        run([BOARD, "shots", job], env)

        # -- 22 · and spend is STILL gated on the prompt itself ----------------------------------
        dec, why, _ = hook(env, "mcp__Higgsfield__generate_image",
                           {"params": {"model": "nano_banana", "prompt": "a baker in a kitchen"}})
        check("22 a generation whose prompt was never linted → DENIED",
              dec == "deny", f"{dec}: {why}")
        rc, out, err = run([LINT, s1], env)
        check("22 adopting an environment reference makes the prompt's own scenery ILLEGAL — "
              "reference the nouns, prompt the verbs",
              rc == 1 and "re-describes it" in (out + err), out + err)
        body = open(s1, encoding="utf-8").read()
        body = body.replace(
            "A small tiled kitchen, flour dusting the counter, a shelf of tins, a window behind",
            "as supplied by the reference").replace(
            "[STYLE]\nphone-real, mild grain",
            "[SAFE ZONE]\ntop 35% clear for the title, face clear of the platform UI\n\n"
            "[STYLE]\nphone-real, mild grain")
        write(s1, body)
        rc, out, err = run([LINT, s1], env)
        check("22 with the scenery left to the reference, the prompt lints clean and writes its .ok",
              rc == 0 and os.path.isfile(s1.replace(".prompt.md", ".prompt.ok")), out + err)

        # -- a last seam: the gate and the linter read the SAME plan ----------------------------
        sys.path.insert(0, HERE)
        import gate as G  # noqa: E402
        st = G.refplan_state(job)
        check("seam: gate.refplan_state agrees with prompt_lint --plan",
              st["ok"] and not st["gaps"] and not st["blocked"], json.dumps(
                  [r["detail"] for r in st["gaps"] + st["blocked"]]))
        check("seam: the gate found the prompts folder by walking, not by convention",
              any(p.endswith(os.path.join("01-script", "prompts")) for p in st["dirs"]),
              json.dumps(st["dirs"]))
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print("-" * 60)
    if FAILS:
        print(f"FAIL ({len(FAILS)}): " + "; ".join(FAILS))
        return 1
    print("pre-production suite OK — the stage refuses at every point it is supposed to, and "
          "opens only when the work is actually there")
    return 0


if __name__ == "__main__":
    sys.exit(main())
