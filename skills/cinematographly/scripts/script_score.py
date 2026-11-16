#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""script_score.py — mechanical self-test for a spoken video script.

The scorecard in ../references/script-craft.md section 6 has twelve dimensions, of which eight are
scored per script (four universal + four chosen). This script measures
the ones a machine can measure and refuses to pretend about the rest.

WHAT IT CANNOT DO — and this is the important half:
  * It cannot HEAR the script. The read-aloud test (script-craft section 1) stays human and is the
    highest-yield gate in the whole process.
  * It cannot judge whether a line REACTS to the one before it (the reactivity test). It flags a
    weak proxy — adjacent lines of near-identical shape — and that is all.
  * It cannot tell whether the idea is any good. That is ideation.md's job, upstream.
A clean run means "nothing mechanical is wrong." It does not mean the script is good.

WHAT IT MEASURES
  Speakability   line length in words, longest line, lines over the breath ceiling,
                 stumble candidates (sibilant runs, consonant clusters), held-open clauses
  Rhythm         line-length variance (a flat script reads as written, not spoken)
  Voice          contraction rate, question rate, first-person presence
  Structure      hook length, scene count, speaker alternation, CTA count, duration
  Polish         banned-phrase and hype-vocabulary hits, pronunciation ambiguities

WHAT IT WARNS ABOUT — advisory, never a failure, and the reasons are the point
  Two findings from ../references/hook-craft.md are mechanically visible in the [INTRO] block:
  whether the hook holds a concrete ANCHOR, and whether the BRAND is sitting in it. Neither can
  be a FAIL, because neither is decided by the text this tool can see:
    * the anchor may be in the PICTURE ("I thought this was a scam" over the product in hand is a
      well-formed hook with no textual anchor), and this skill's own doctrine is image-first;
    * the brand evidence (Tellis et al. 2019) measured SHARING of YouTube ads, not retention on a
      vertical feed, so it scopes to a caution and not a rule.
  Both are printed as questions addressed to the director. A checker that manufactures findings
  costs more attention than it saves.

Usage
-----
  python3 script_score.py SCRIPT.md
  python3 script_score.py SCRIPT.md --lang ro          # Romanian checks and hype list
  python3 script_score.py SCRIPT.md --ugc              # relax: disfluency and hedging expected
  python3 script_score.py SCRIPT.md --max-words 15 --hook-min 6
  python3 script_score.py SCRIPT.md --brand Sansone    # warn if the brand sits in the hook
  python3 script_score.py SCRIPT.md --json
  python3 script_score.py --selftest

Exit codes: 0 no failures - 1 one or more checks failed - 2 usage/IO error.
"""
from __future__ import annotations
import argparse, json, math, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from estimate_duration import parse as parse_script, count_spoken_words  # noqa: F401
except Exception as e:                                                       # noqa: BLE001
    print(f"error: could not import the shared script parser from estimate_duration.py: {e}",
          file=sys.stderr)
    raise SystemExit(2)

CHAR_RE = re.compile(r"^\s*(?:\*\*)?([A-Za-zĂÂÎȘȚăâîșț][A-Za-zĂÂÎȘȚăâîșț '’\-]{0,29})(?:\*\*)?\s*:\s+(.+)$")
# (v2.65.0) HOOK is the house template's name for the opening block (script-format.md); it is read as INTRO.
BLOCK_RE = re.compile(r"^\s*(?:\*\*)?\[\s*(INTRO|HOOK|SCEN[EĂA]\s*\d+|CTA)[^\]]*\]", re.IGNORECASE)
HEADER_RE = re.compile(r"^\s*(#{1,6}\s|-{3,}\s*$|_)")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*[–\-—]\s*(\d{1,2}):(\d{2})")
STOP = {"TEXT", "NOTE", "NOTA", "NOTĂ", "INTRO", "HOOK", "CARRIED BY", "CTA", "SCENE", "SCENA", "SCENĂ", "B-ROLL",
        "BROLL", "TITLE", "LOGO", "CUT", "VISUAL", "VIZUAL", "DECOR", "REGIE", "WARDROBE",
        "BRIEF", "SAVED", "STYLE", "MOTION", "CAMERA", "LIGHTING", "ENVIRONMENT", "LOC",
        "INSERT", "INSERTURI", "DIALOG", "SCENARIU", "CONTROL", "SPEECH", "FRAMING"}

# either apostrophe: text from Word or Google Docs carries the curly one (v2.51, SCR-01; in the 2026-11-05 script
# corpus 76 % of screenplay contractions were curly, so a straight-only count missed three in four)
CONTRACTIONS = re.compile(r"\b\w+['’](?:s|t|re|ve|ll|d|m)\b|\bn['’]t\b", re.IGNORECASE)
# Held-open clause markers: the listener has to hold the sentence open while you finish it.
SUBORD = {"en": r"\b(?:which|although|whereas|despite|whilst|inasmuch|notwithstanding)\b",
          "ro": r"\b(?:care|deși|întrucât|deoarece|astfel încât|în timp ce|cu toate că)\b"}
HYPE = {"en": ["revolutionary", "game-changing", "cutting-edge", "state of the art", "seamless",
               "unlock the potential", "take it to the next level", "complete solution",
               "in today's world", "in the digital age", "look no further", "elevate your",
               "delve into", "leverage", "robust", "holistic", "unparalleled", "transformative"],
        "ro": ["revoluționează", "revolutionar", "de ultimă generație", "soluție completă",
               "valorifică potențialul", "transformă complet", "soluția ideală", "în era digitală",
               "într-o lume tot mai competitivă", "nu este doar", "de neegalat", "inovator"]}
# Sequences that make a speaker stumble.
SIBILANT = re.compile(r"(?:\b\w*[sșzșcș]\w*\b[\s,]+){3,}", re.IGNORECASE)
CLUSTER = re.compile(r"[bcdfghjklmnpqrstvwxzșțBCDFGHJKLMNPQRSTVWXZȘȚ]{5,}")
AMBIGUOUS = re.compile(r"(?<![\w])(?:\d{4}|\d+[.,]\d+|[A-ZĂÂÎȘȚ]{2,}\s*\d+|[€$£]\s?\d|\d+\s?[%€$£]|\d+/\d+)")

# ---- measured reference bands (v2.51, assets/script-bands.json; script corpus 2026-11-05) -----------------------
# Printed beside the script's own numbers as advisory notes. Never a FAIL, and never a threshold unless --house is
# passed: a client's clients/script.<client>.json still decides. Source and limits: references/script-craft.md s2d.
BANDS_PATH = os.path.join(HERE, "..", "assets", "script-bands.json")
SENT_RE = re.compile(r"[^.!?…]+[.!?…]+|[^.!?…]+$")
FILLERS = {"en": r"\b(?:um+|uh+|erm|you know|i mean|kind of|sort of|basically|honestly|actually)\b|\blike,",
           "ro": r"\b(?:ăă+|îî+|adică|practic|gen|știi|cum să zic|de fapt)\b"}
CONNECTIVE = re.compile(r"^(?:But|Yet|So|Then|Now|Also|Plus|And|Meanwhile|However|Still|Dar|Și|Deci|Apoi|Acum|Totuși)\b")
CUT_OFF = re.compile(r"(?:—|--|–|-|\.\.\.|…)\s*$")


def load_bands():
    try:
        with open(BANDS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def sentences_of(line):
    return [x.strip() for x in SENT_RE.findall(line) if re.search(r"\w", x)]


def runtime_seconds(text):
    """Script runtime from the block timecodes: the first block's start to the last block's end."""
    starts, ends = [], []
    for raw in text.splitlines():
        if BLOCK_RE.match(raw):
            m = TIME_RE.search(raw)
            if m:
                starts.append(int(m.group(1)) * 60 + int(m.group(2)))
                ends.append(int(m.group(3)) * 60 + int(m.group(4)))
    return (max(ends) - min(starts)) if starts and max(ends) > min(starts) else None


def short_closers(lines, short=8):
    """(share of multi-sentence lines ending on a short statement, share of short sentences overall)."""
    multi = ended = n_sent = n_short = 0
    for l in lines:
        ss = sentences_of(l)
        n_sent += len(ss)
        n_short += sum(1 for x in ss if len(x.split()) <= short)
        if len(ss) >= 2:
            multi += 1
            if len(ss[-1].split()) <= short and not ss[-1].endswith("?"):
                ended += 1
    return (ended / multi if multi else None), (n_short / n_sent if n_sent else None), multi


def band_text(b, fmt="{:g}"):
    return f"{fmt.format(b['p10'])}–{fmt.format(b['p90'])} (median {fmt.format(b['median'])})"


def reference_bands(B, text, rows, counts, ugc, lang):
    """The script's numbers beside the measured bands. Returns (bands, warnings): bands are notes; a warning is
    raised only where a number sits far outside what real scripts do (pace above p90, a CTA in the first 60 % of a
    short spot,
    the short-closer pattern in a talking-head script)."""
    out, warns = [], []
    if not B:
        return out, warns
    lines = [r[2] for r in rows]
    words = sum(counts)
    T = runtime_seconds(text)
    A = B["ads"]
    if T and words:
        wps = words / T
        wb = A["words_per_second"]
        verdict = "above" if wps > wb["p90"] else "below" if wps < wb["p10"] else "within"
        out.append(("pace", f"{wps:.2f} words/s over {T}s", f"ads {band_text(wb)}; award-annual spots median "
                    f"{A['words_per_second_award_annual']['median']}", verdict))
        if verdict == "above":
            warns.append(("pace", f"{wps:.2f} spoken words a second over the {T}s runtime is above the p90 of 48 "
                          f"real TV/social spots ({wb['p90']}). Crowded: cut words, or give the picture the "
                          f"time (award-annual spots run about {A['words_per_second_award_annual']['median']}/s)"))
        for secs, key in ((15, "spoken_words_15s"), (30, "spoken_words_30s")):
            if abs(T - secs) <= max(2, secs * 0.1):
                out.append((f"words for a {secs}s spot", f"{words}", f"ads {band_text(A[key])}",
                            "above" if words > A[key]["p90"] else "below" if words < A[key]["p10"] else "within"))
    cta_idx = next((i for i, r in enumerate(rows) if r[0] == "CTA"), None)
    if cta_idx is not None and words:
        share = sum(counts[:cta_idx]) / words
        cb = A["cta_start_share_15_30s"]
        out.append(("CTA starts at", f"{share:.0%} of the spoken words", f"15-30s ads {band_text(cb, '{:.0%}')}; "
                    f"60-120s films mostly leave it to the end card",
                    "below" if share < cb["p10"] else "above" if share > cb["p90"] else "within"))
        if share < 0.6 and (T is None or T <= 45):
            warns.append(("CTA position", f"the CTA starts at {share:.0%} of the spoken words; in 15-30 s spots it "
                          f"starts at {cb['p10']:.0%}-{cb['p90']:.0%}. An early ask before the turn has landed — "
                          f"deliberate? (script-craft.md s2d)"))
    all_s = [x for l in lines for x in sentences_of(l)]
    if not ugc:
        D = B["dialogue"]
        if len({r[1] for r in rows}) >= 2 and all_s:
            qs = sum(1 for x in all_s if x.endswith("?")) / len(all_s)
            qb = D["question_share_of_sentences"]
            out.append(("questions", f"{qs:.0%} of sentences", f"dialogue {band_text(qb, '{:.0%}')}",
                        "above" if qs > qb["p90"] else "below" if qs < qb["p10"] else "within"))
        if lang == "en" and words:
            cr = 100 * sum(len(CONTRACTIONS.findall(l)) for l in lines) / words
            cb2 = D["contractions_per_100_words"]
            out.append(("contractions", f"{cr:.1f} per 100 words", f"dialogue {band_text(cb2)}",
                        "above" if cr > cb2["p90"] else "below" if cr < cb2["p10"] else "within"))
        cut = sum(1 for l in lines if CUT_OFF.search(l))
        n_scenes = max(1, len({r[0] for r in rows if r[0]}))
        if cut > n_scenes:
            out.append(("cut-off / trailing lines", f"{cut} in {n_scenes} block(s)",
                        "real dialogue: about 4 % of speeches each; one a scene at most (s3)", "above"))
    else:
        H = B["talking_head"]
        if all_s:
            sw = sum(len(x.split()) for x in all_s) / len(all_s)
            sb = H["sentence_words"]
            out.append(("sentence length", f"{sw:.1f} words", f"talking head {band_text(sb)}",
                        "above" if sw > sb["p90"] else "below" if sw < sb["p10"] else "within"))
            conn = sum(1 for x in all_s if CONNECTIVE.match(x)) / len(all_s)
            out.append(("connective openers", f"{conn:.0%} of sentences",
                        f"real answers about {H['connective_opener_share']:.0%}; scripted dialogue about 5 %", "note"))
        if words:
            fl = 100 * sum(len(re.findall(FILLERS[lang], l, re.I)) for l in lines) / words
            fb = H["fillers_per_100_words"]
            out.append(("fillers", f"{fl:.1f} per 100 words", f"edited interviews {band_text(fb)} (a floor); above "
                        f"{H['fillers_ceiling_per_100_words']} reads as a bit",
                        "above" if fl > H["fillers_ceiling_per_100_words"] else "below" if fl < fb["p10"] else "within"))
        ended, short_rate, multi = short_closers(lines)
        if ended is not None and multi >= 3:
            w = H["short_closer_warn"]
            out.append(("short closers", f"{ended:.0%} of {multi} multi-sentence lines end on 8 words or fewer "
                        f"(short sentences overall {short_rate:.0%})",
                        f"real answers {band_text(H['short_closer_share_of_multi_sentence_answers'], '{:.0%}')}, "
                        f"about the same as their short-sentence share", "note"))
            if ended >= w["share_at_least"] and short_rate and ended >= w["ratio_to_short_sentence_share_at_least"] * short_rate:
                warns.append(("short closers", f"{ended:.0%} of the multi-sentence lines end on a short statement "
                              f"while only {short_rate:.0%} of all sentences are short. Real speakers do not save the "
                              f"punch for the end of every turn; this reads as written copy performed "
                              f"(script-craft.md s2d)"))
    return out, warns


def speakers_and_lines(text):
    """Ordered (scene, speaker, line-text) inside script blocks only."""
    out, scene, inb = [], None, False
    for raw in text.splitlines():
        mb = BLOCK_RE.match(raw)
        if mb:
            scene, inb = mb.group(1).upper(), True
            continue
        if HEADER_RE.match(raw):
            scene, inb = None, False
            continue
        if not inb:
            continue
        m = CHAR_RE.match(raw)
        if m and m.group(1).strip().upper() not in STOP and 1 <= len(m.group(1).split()) <= 4:
            body = re.sub(r"\[[^\]]*\]", " ", re.sub(r"\([^)]*\)", " ", m.group(2)))
            body = body.replace("„", "").replace("”", "").replace('"', "").strip()
            if body:
                out.append((scene, m.group(1).strip(), body))
    return out


WPS_ASSUMED, PAUSE_ASSUMED = 2.4, 0.6        # the same speech model as estimate_duration.py; assumed, not a voice


def block_clocks(text):
    """(v2.67.0) The two clocks, per block: [(label, window_s or None, speech_s, n_lines)] in script order.
    The window is the block header's timecode (`[SCENE 1 — 0:06–0:19]`, as beat_plan.py prints it); speech is
    words at an ASSUMED 2.4 a second plus 0.6 s a line. A block whose speech is longer than its window cannot be
    said in the picture it was given."""
    out, cur = [], None
    for raw in text.splitlines():
        mb = BLOCK_RE.match(raw)
        if mb:
            m = TIME_RE.search(raw)
            win = None
            if m:
                a_ = int(m.group(1)) * 60 + int(m.group(2))
                b_ = int(m.group(3)) * 60 + int(m.group(4))
                win = b_ - a_ if b_ > a_ else None
            label = re.sub(r"\s+", " ", mb.group(1).upper())
            if label.startswith("SCEN"):
                label = "SCENE " + re.sub(r"\D", "", label)
            cur = [label, win, 0.0, 0]
            out.append(cur)
            continue
        if HEADER_RE.match(raw):
            cur = None
            continue
        if cur is None:
            continue
        m = CHAR_RE.match(raw)
        if m and m.group(1).strip().upper() not in STOP and 1 <= len(m.group(1).split()) <= 4:
            body = re.sub(r"\[[^\]]*\]", " ", re.sub(r"\([^)]*\)", " ", m.group(2)))
            body = body.replace("„", "").replace("”", "").replace('"', "").strip()
            if body:
                cur[2] += count_spoken_words(body) / WPS_ASSUMED + PAUSE_ASSUMED
                cur[3] += 1
    return [tuple(x) for x in out]


def clock_warnings(clocks):
    """A WARN for each block whose speech is longer than its picture time; never a FAIL (the speech rate is assumed)."""
    return [("two clocks", f"[{label}] needs about {sp:.1f}s of speech for {n} line(s) and its timecode gives it "
             f"{win}s of picture (at an assumed {WPS_ASSUMED} words a second plus {PAUSE_ASSUMED}s a line). Cut "
             f"about {math.ceil((sp - win) * WPS_ASSUMED)} words, or give the block more picture time")
            for label, win, sp, n in clocks if win and sp > win]


def hook_seconds(text):
    for raw in text.splitlines():
        mb = BLOCK_RE.match(raw)
        if mb and mb.group(1).upper() in ("INTRO", "HOOK"):
            m = TIME_RE.search(raw)
            if m:
                a = int(m.group(1)) * 60 + int(m.group(2))
                b = int(m.group(3)) * 60 + int(m.group(4))
                return b - a
    return None


# A concrete anchor: something the viewer can picture or price. Digits and currency carry most of
# it; a mid-line capitalised token catches named people, places and products. Deliberately narrow —
# a wide "concreteness" heuristic would fire on ordinary prose and the finding would stop being read.
ANCHOR_NUM = re.compile(r"[£$€]\s?\d|\d+\s?(?:%|p|k|kg|g|ml|l|cm|mm|m|h|hr|hrs|min|mins|sec|secs|"
                        r"days?|weeks?|months?|years?|times?|x)\b|\b\d+\b", re.I)
ANCHOR_NAME = re.compile(r"(?<=[a-z,;:\s\"'\u201e\u201c\u201d(\[])\b[A-Z][a-z]{2,}\b")


def hook_window(text):
    """Everything the viewer receives in the [INTRO] block — spoken lines, the on-screen TEXT card
    and the beat description — with the block header itself dropped.

    The header is dropped deliberately: `[INTRO 0:00-0:06]` contains digits, and counting a
    timecode as a concrete anchor would make the anchor check pass on every script ever written.
    Scanning the card as well as the dialogue is the point — Tellis measured brand PROMINENCE, and
    the house template's hook beat is often a text card with no spoken line at all."""
    out, inb = [], False
    for raw in text.splitlines():
        mb = BLOCK_RE.match(raw)
        if mb:
            inb = mb.group(1).upper() in ("INTRO", "HOOK")
            continue                      # never scan the header line: it carries the timecode
        if inb:
            if HEADER_RE.match(raw):
                inb = False
                continue
            out.append(re.sub(r"<[^<>\n]*>", " ", raw))   # placeholders are not anchors
    return " ".join(out).strip()


def anchors_in(text, brand=None):
    """Concrete anchors found in a stretch of hook text, as (kind, token) pairs.

    The brand is excluded when known. A brand name is a label, not the thing the viewer is
    weighing — counting it would let a hook satisfy the anchor rule by saying nothing but its own
    name, which is the exact placement the sharing evidence says costs you (hook-craft.md s5)."""
    found = [("number", m.group(0).strip()) for m in ANCHOR_NUM.finditer(text)]
    found += [("name", m.group(0)) for m in ANCHOR_NAME.finditer(text)]
    if brand:
        b = brand.strip().lower()
        found = [(k, v) for k, v in found if v.lower() != b]
    return found


def brand_in(text, brand):
    """Whether the brand string appears in the hook window. Word-boundary, case-insensitive."""
    if not brand:
        return False
    return re.search(r"\b" + re.escape(brand.strip()) + r"\b", text, re.I) is not None


SELFTEST_BASE = """# Fixture
## SCRIPT

[INTRO 0:00-0:06]  the hook beat.
TEXT: "{card}"
ANA: "{hook}"

[SCENE 1 - 0:06-0:19]  a steel bench.
ANA: "I had been buying the cheap one for years, and I never once checked."
BOGDAN: "You are not alone there."

[SCENE 2 - 0:19-0:34]  the bottle, held.
ANA: "Look at the date on the neck, not the front label."
BOGDAN: "That is the only number that matters?"

[CTA 0:34-0:40]
ANA: "Check yours tonight."
"""


def objective_from_job(script_path: str) -> str | None:
    """(v2.69.0) The person's `objective:` from the job's 00-brief/DEVELOPMENT.md (its Choice section), found from the
    script's own folders, so stage 2 never scores a script against the wrong objective by forgetting the flag."""
    d = os.path.dirname(os.path.abspath(script_path))
    for _ in range(6):
        dp = os.path.join(d, "00-brief", "DEVELOPMENT.md")
        if os.path.isfile(dp):
            txt_ = open(dp, encoding="utf-8").read()
            ch_ = re.search(r"^##\s*Choice\b.*?(?=^##\s|\Z)", txt_, re.M | re.S)    # the Choice section only (review 1)
            m = re.search(r"^\s*objective\s*:\s*(sharing|attribution|conversion)\b", ch_.group(0) if ch_ else "",
                          re.I | re.M)
            return m.group(1).lower() if m else None
        d = os.path.dirname(d)
    return None


def selftest() -> int:
    """The two advisory checks, and — as much as it matters — the findings they must NOT make."""
    # 0. (v2.69.0) the person's objective is read from the job's DEVELOPMENT.md, found from the script's folders
    import tempfile
    with tempfile.TemporaryDirectory() as td_:
        os.makedirs(os.path.join(td_, "00-brief")); os.makedirs(os.path.join(td_, "01-script", "options"))
        sp_ = os.path.join(td_, "01-script", "options", "B.md")
        assert objective_from_job(sp_) is None                         # no DEVELOPMENT.md: nothing assumed
        open(os.path.join(td_, "00-brief", "DEVELOPMENT.md"), "w").write(
            '## Choice\n\nchosen: C2\nobjective: Conversion — "we need it bought this month"\n')
        assert objective_from_job(sp_) == "conversion", objective_from_job(sp_)
        open(os.path.join(td_, "00-brief", "DEVELOPMENT.md"), "w").write("## Choice\n\nobjective: brand recall\n")
        assert objective_from_job(sp_) is None                         # not one of the three words: never guessed
        open(os.path.join(td_, "00-brief", "DEVELOPMENT.md"), "w").write(
            "## Research\n\nobjective: sharing (a rival's, quoted)\n\n## Choice\n\nobjective: attribution — \"they remember us\"\n")
        assert objective_from_job(sp_) == "attribution", objective_from_job(sp_)    # only the Choice section counts
    # 1. the window is the INTRO block, and the block's own timecode is never an anchor
    plain = SELFTEST_BASE.format(card="no numbers here at all", hook="I thought it was a scam")
    w = hook_window(plain)
    assert "0:00" not in w, w
    assert "scam" in w and "steel bench" not in w, w
    assert anchors_in(w) == [], anchors_in(w)

    # 2. a price in the spoken hook IS an anchor; so is a named thing; so is a card-only number
    # (v2.65.0) the house template labels the opening block [HOOK …]; it is the same window
    hooked = SELFTEST_BASE.format(card="no numbers here at all", hook="I thought it was a scam").replace("[INTRO 0:00-0:06]", "[HOOK 0:00–0:06]")
    assert hook_window(hooked) == w, (hook_window(hooked), w)
    # (v2.67.0) the two clocks: one HOOK fixture read by both parsers gives the same blocks and lines
    clocked = ("[HOOK 0:00–0:04]\nANA: \"I paid forty pounds for the wrong tin, and I still use it every single "
               "morning\"\n\n[SCENE 1 — 0:04–0:12]\nANA: \"Every loaf by hand.\"\n\n[CTA 0:12–0:15]\n"
               "ANA: \"Come before six.\"\n")
    ck = block_clocks(clocked)
    assert [c[0] for c in ck] == ["HOOK", "SCENE 1", "CTA"] and [c[1] for c in ck] == [4, 8, 3], ck
    assert ck[0][2] > 4 and ck[1][2] < 8, ck          # 16 words cannot be said in 4 s; 4 words fit in 8 s
    cw = clock_warnings(ck)
    assert len(cw) == 1 and "[HOOK]" in cw[0][1] and "assumed" in cw[0][1], cw   # the hook warns; the scene does not
    assert "Cut about 8 words" in cw[0][1], cw             # (7.27 - 4) s x 2.4 words a second = 7.8, rounded up
    eh = block_clocks("[HOOK 0:00–0:03]  a door opens\ncarried by: object\n\n[SCENE 1 — 0:03–0:09]\nANA: \"hello\"\n")
    assert eh[0][0] == "HOOK" and eh[0][3] == 0 and eh[0][2] == 0 and eh[1][3] == 1, eh   # a wordless hook is a block
    import estimate_duration as _ed
    ed_rows = _ed.parse(clocked)
    assert [(b["name"], len(b["lines"])) for b in ed_rows] == [(c[0], c[3]) for c in ck], \
        ("estimate_duration.py and script_score.py read different blocks", ed_rows, ck)
    assert ed_rows[0]["lines"][0][1] == 16, ed_rows        # the hook line is counted, all 16 words
    assert block_clocks("[SCENE 1]\nANA: \"hi there\"\n")[0][1] is None   # no timecode: speech only
    # (v2.67.0) the template's `carried by:` line is a direction, never a speaker
    cb = block_clocks("[SCENE 1 — 0:00–0:05]\ncarried by: object — the label on the box\nANA: \"hi there\"\n")
    assert cb[0][3] == 1, cb
    assert [r[1] for r in speakers_and_lines("[SCENE 1]\ncarried by: face\nANA: \"hi\"\n")] == ["ANA"]
    assert hook_seconds(hooked.replace("0:00–0:06", "0:00-0:06")) == 6
    priced = SELFTEST_BASE.format(card="no numbers here at all", hook="I paid 400 for the wrong one")
    assert any(k == "number" for k, _ in anchors_in(hook_window(priced)))
    named = SELFTEST_BASE.format(card="no numbers here at all", hook="the buyer at Sansone put it back")
    assert any(k == "name" and v == "Sansone" for k, v in anchors_in(hook_window(named)))
    carded = SELFTEST_BASE.format(card="9 months in steel", hook="I thought it was a scam")
    assert any(k == "number" for k, _ in anchors_in(hook_window(carded))), \
        "an on-screen card is part of the hook the viewer receives"

    # 3. anchors are NOT counted from later scenes — SCENE 1 is full of them
    assert anchors_in(hook_window(plain)) == [], "the window must stop at the next block"

    # 4. the brand check sees the card and the line, and is word-bounded
    assert brand_in(hook_window(SELFTEST_BASE.format(card="Sansone", hook="a scam")), "Sansone")
    assert brand_in(hook_window(SELFTEST_BASE.format(card="x", hook="Sansone is not cheap")), "Sansone")
    assert not brand_in(hook_window(plain), "Sansone")
    assert not brand_in("Sansonello is a different word", "Sansone"), "word boundary, not substring"

    # 4b. a proper noun opening a quoted card is still a name — the lookbehind must allow quotes
    quoted = SELFTEST_BASE.format(card="Sansone tastes better", hook="I thought it was a scam")
    assert any(k == "name" and v == "Sansone" for k, v in anchors_in(hook_window(quoted)))
    # ...and with --brand given, the brand alone does NOT satisfy the anchor rule
    assert anchors_in(hook_window(quoted), "Sansone") == [], anchors_in(hook_window(quoted), "Sansone")

    # 4c. contractions count with either apostrophe (SCR-01)
    assert len(CONTRACTIONS.findall("I’m sure it’s fine, isn't it? We'll see.")) == 4

    # 4d. the measured bands (v2.51): runtime from the timecodes, the CTA position, the short-closer pattern
    B = load_bands()
    assert B and B["dialogue"]["house_line_ceiling"] == 21 and B["ads"]["house_line_ceiling"] == 22, "bands asset"
    assert runtime_seconds(plain) == 40, runtime_seconds(plain)
    rows = speakers_and_lines(plain)
    counts = [count_spoken_words(r[2]) for r in rows]
    bands, warns = reference_bands(B, plain, rows, counts, False, "en")
    names = {b[0] for b in bands}
    assert "pace" in names and "CTA starts at" in names and "questions" in names, names
    cta = next(b for b in bands if b[0] == "CTA starts at")
    assert cta[1].startswith("9") and not any(w[0] == "CTA position" for w in warns), (cta, warns)
    early = plain.replace("[SCENE 2 - 0:19-0:34]", "[CTA 0:19-0:21]\nANA: \"Order now.\"\n\n[SCENE 2 - 0:21-0:34]")
    r2 = speakers_and_lines(early)
    _, w2 = reference_bands(B, early, r2, [count_spoken_words(r[2]) for r in r2], False, "en")
    assert any(w[0] == "CTA position" for w in w2), "a CTA in the first 60 % must be asked about"
    # fillers: "like," counts (a comma is not a word boundary), the bare verb does not
    assert len(re.findall(FILLERS["en"], "I like it. It was, like, fine, you know?", re.I)) == 2
    punchy = ["I tried every serum on the shelf for two whole years and nothing changed at all. It failed.",
              "My sister kept sending me links and I kept ignoring every single one of them. Big mistake.",
              "Then I read the label on hers and realised it was the one ingredient I had skipped. Game over."]
    ended, short_rate, multi = short_closers(punchy)
    assert multi == 3 and ended == 1.0 and short_rate == 0.5, (ended, short_rate, multi)
    ugc_rows = [("SCENE 1", "ANA", l) for l in punchy]
    _, w3 = reference_bands(B, "", ugc_rows, [count_spoken_words(l) for l in punchy], True, "en")
    assert any(w[0] == "short closers" for w in w3), w3
    natural = ["So I tried every serum on the shelf for two years, and honestly nothing changed.",
               "My sister kept sending me links. I ignored them, which, you know, was dumb of me.",
               "And then I read the label on hers and saw the one ingredient I'd skipped."]
    _, w4 = reference_bands(B, "", [("SCENE 1", "ANA", l) for l in natural],
                            [count_spoken_words(l) for l in natural], True, "en")
    assert not any(w[0] == "short closers" for w in w4), w4

    # 5. it must not fire on a script with no INTRO block at all — silence, not a manufactured finding
    assert hook_window("[SCENE 1 - 0:00-0:10]\nANA: \"hello\"\n") == ""

    print("selftest OK - the hook window is the INTRO block only and excludes its own timecode; "
          "a price, a named thing and an on-screen card all count as anchors; a later scene's "
          "numbers do not; the brand check is word-bounded and reads the card; a script with no "
          "INTRO block produces no finding; the brand alone never counts as the anchor; contractions "
          "count with a straight or a curly apostrophe; and the measured bands read the runtime, ask about a "
          "CTA in the first 60 % of a short spot and catch lines that all end on a punch")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", nargs="?")
    ap.add_argument("--lang", default="en", choices=["en", "ro"])
    ap.add_argument("--ugc", action="store_true",
                    help="UGC monologue: disfluency and hedging are features; relaxes the "
                         "alternation and question checks")
    ap.add_argument("--client", help="load thresholds from clients/script.<client>.json "
                                     "(hook_seconds_min, max_words_per_line)")
    ap.add_argument("--max-words", type=int, default=None,
                    help="breath ceiling per line. No house figure — 15 is one earlier client's "
                         "answer. Comes from --client, or pass it explicitly.")
    ap.add_argument("--hook-min", type=float, default=None,
                    help="minimum hook seconds. No house figure — 6s is one client's answer for a "
                         "60s two-hander, and is wrong for a 35s UGC monologue. From --client, or "
                         "pass it explicitly.")
    ap.add_argument("--house", action="store_true",
                    help="take --max-words from the measured house band (assets/script-bands.json): 21 for "
                         "dialogue, 22 for an ad's VO. Explicit and printed; --hook-min still comes from "
                         "the client or the flag. No band exists for --ugc lines.")
    ap.add_argument("--vo", action="store_true",
                    help="with --house: the script is an ad's VO / single voice, so the ads band (22) applies")
    ap.add_argument("--objective", choices=["sharing", "attribution", "conversion"],
                    help="what this video optimises for — it decides WHICH brand-placement finding "
                         "applies (hook-craft.md s5b). Omitted, the tool says so rather than "
                         "picking one.")
    ap.add_argument("--brand",
                    help="brand name. Warns if it appears inside the [INTRO] block — early, long "
                         "and persistent brand placement measurably HURTS sharing (Tellis et al., "
                         "Journal of Marketing 2019; references/hook-craft.md section 5). Scoped: "
                         "that study measured sharing of YouTube ads, so this warns and never fails.")
    ap.add_argument("--no-hook-anchors", action="store_true",
                    help="skip the concrete-anchor warning on the hook window")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.script:
        ap.error("a script path is required (or --selftest)")
    obj_note = None
    if not a.objective:
        a.objective = objective_from_job(a.script)
        if a.objective:
            obj_note = (f"objective {a.objective}, read from the job's DEVELOPMENT.md (the person's words); it switches "
                        f"the brand-in-hook note only, never the emotional register (performance-metrics.md §0c)")

    # Thresholds are per-client, never global: a hook floor that is right for a 60s narrative
    # two-hander fails every 35s UGC monologue, and used to do so silently.
    if a.client:
        import json as _json
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import client_files                    # CINE_CLIENTS, a `_cine-clients/` folder, then the plugin's
        p = client_files.find(f"script.{a.client}.json", a.script)
        try:
            if not p:
                raise FileNotFoundError(a.client)
            with open(p, encoding="utf-8") as fh:
                params = _json.load(fh)
        except FileNotFoundError:
            print(f"error: no script.{a.client}.json ({client_files.where_looked(a.script)}). Create it "
                  f"(hook_seconds_min, max_words_per_line, notes) or pass --hook-min and --max-words explicitly.",
                  file=sys.stderr)
            return 2
        if a.hook_min is None:
            a.hook_min = params.get("hook_seconds_min")
        if a.max_words is None:
            a.max_words = params.get("max_words_per_line")
    # `0` is not a threshold. clients/script._TEMPLATE.json ships zeros precisely so the tools
    # REFUSE until someone measures — but `is None` let a zero through, so a 2-second hook passed
    # (`want >= 0s`) while every correct line failed (`over 0 words`). One check that anything
    # passes and one that fires on everything, from the same line. beat_plan.py refused correctly.
    B = load_bands()
    house_note = None
    if a.house and not a.max_words:
        if a.ugc:
            print("error: --house has no measured line ceiling for --ugc (talking-head lines are judged by "
                  "sentence length, script-craft.md s2d). Pass --max-words.", file=sys.stderr)
            return 2
        if not B:
            print("error: assets/script-bands.json is missing or unreadable", file=sys.stderr)
            return 2
        a.max_words = B["ads" if a.vo else "dialogue"]["house_line_ceiling"]
        house_note = f"--max-words {a.max_words} from the measured house band ({'ads VO' if a.vo else 'dialogue'})"
    if not a.hook_min or not a.max_words:
        ref = ""
        if B:
            ref = (f" Measured reference (assets/script-bands.json): dialogue lines p90 about "
                   f"{B['dialogue']['house_line_ceiling']} words, ad VO max sentence p90 {B['ads']['max_sentence_words_p90']}; "
                   f"--house takes those for --max-words.")
        print("error: --hook-min and --max-words have no silent house default — they are client x format "
              "decisions. Pass --client NAME, or both flags explicitly." + ref +
              " (references/script-craft.md, references/persuasion-psychology.md §1)", file=sys.stderr)
        return 2

    try:
        text = open(a.script, encoding="utf-8").read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    rows = speakers_and_lines(text)
    if not rows:
        print("error: no dialogue found inside [INTRO]/[SCENE n]/[CTA] blocks — is this the house "
              "script format? See references/script-format.md.", file=sys.stderr)
        return 2

    lines = [r[2] for r in rows]
    speakers = [r[1] for r in rows]
    counts = [count_spoken_words(l) for l in lines]
    total_words = sum(counts)
    speech_s = total_words / 2.4 + 0.6 * len(lines)

    long_lines = [(i, c, lines[i]) for i, c in enumerate(counts) if c > a.max_words]
    stumbles = [(i, lines[i]) for i, l in enumerate(lines) if SIBILANT.search(l) or CLUSTER.search(l)]
    subord = [(i, lines[i]) for i, l in enumerate(lines) if re.search(SUBORD[a.lang], l, re.IGNORECASE)]
    hype = [(i, h, lines[i]) for i, l in enumerate(lines) for h in HYPE[a.lang] if h in l.lower()]
    ambig = [(i, m.group(0), lines[i]) for i, l in enumerate(lines) for m in AMBIGUOUS.finditer(l)]
    contr = sum(len(CONTRACTIONS.findall(l)) for l in lines)
    questions = sum(1 for l in lines if l.rstrip().endswith("?"))
    variance = statistics.pstdev(counts) if len(counts) > 1 else 0.0
    same_speaker_runs = sum(1 for i in range(1, len(speakers)) if speakers[i] == speakers[i - 1])
    # weak reactivity proxy: adjacent lines of near-identical length AND both statements
    flat_pairs = [i for i in range(1, len(lines))
                  if abs(counts[i] - counts[i - 1]) <= 1
                  and not lines[i].rstrip().endswith("?")
                  and not lines[i - 1].rstrip().endswith("?")]
    hook_s = hook_seconds(text)
    cta_lines = [r for r in rows if r[0] == "CTA"]
    scenes = sorted({r[0] for r in rows if r[0] and r[0].startswith("SCEN")})

    checks = [
        ("line length", not long_lines,
         f"{len(long_lines)} line(s) over {a.max_words} words"
         + ("" if not long_lines else " — longest " + str(max(c for _, c, _ in long_lines)))),
        ("rhythm variance", variance >= 2.0,
         f"stdev {variance:.1f} words (want >= 2.0 — a flat script reads as written, not spoken)"),
        ("stumble candidates", not stumbles,
         "none" if not stumbles else f"{len(stumbles)} line(s) with sibilant runs or consonant clusters"),
        ("held-open clauses", not subord,
         "none" if not subord else f"{len(subord)} line(s) with a subordinating clause the listener must hold open"),
        ("hype / banned vocabulary", not hype,
         "none" if not hype else f"{len(hype)} hit(s): " + ", ".join(sorted({h for _, h, _ in hype}))[:80]),
        ("pronunciation decided", not ambig,
         "none" if not ambig else f"{len(ambig)} number/acronym/currency token(s) whose spoken form is ambiguous"),
        ("hook length", hook_s is None or hook_s >= a.hook_min,
         "no [INTRO] timecode found — cannot check" if hook_s is None
         else f"{hook_s:.0f}s (want >= {a.hook_min:g}s)"),
        ("one CTA", len(cta_lines) <= 1,
         f"{len(cta_lines)} spoken line(s) in the CTA block (want at most 1)"),
    ]
    if not a.ugc:
        checks.append(("speaker alternation", same_speaker_runs == 0,
                       "alternates cleanly" if same_speaker_runs == 0 else
                       f"{same_speaker_runs} place(s) where the same speaker has consecutive lines "
                       f"— intended, or is this narration split in two?"))
        checks.append(("contractions present", contr > 0 or a.lang == "ro",
                       f"{contr} contraction(s) — an uncontracted script reads as written prose performed"))
    else:
        checks.append(("UGC voice signals", contr > 0 or a.lang == "ro",
                       f"{contr} contraction(s); UGC needs the disfluency and hedging that prose rules strip"))

    failed = [n for n, ok, _ in checks if not ok]

    # --- advisory tier: hook-craft.md findings that the text half-shows --------------------------
    # These are WARNINGS by construction, not softness. See the module docstring: the anchor may be
    # in the picture, and the brand evidence is about sharing on another platform. Each is phrased
    # as a question to the director, because a difference the tool cannot adjudicate is a question.
    hook_text = hook_window(text)
    warnings = []
    # Informational, never a fault: a finding that is real but does not apply to THIS video's
    # objective. Kept separate so a scoped note cannot be read as a warning and 'fixed'.
    notes: list = []
    if hook_text and not a.no_hook_anchors:
        anch = anchors_in(hook_text, a.brand)
        if not anch:
            warnings.append(("hook anchor",
                             "no number, price, quantity or named thing in the [INTRO] block "
                             "(spoken line or on-screen card) — is "
                             "the anchor in the PICTURE? If there is no anchor at all, the hook is "
                             "at the vague end of a curve that turns over (hook-craft.md s1): one "
                             "concrete anchor, one withheld term"))
    # ⛔ THE FLAG WAS OBJECTIVE-BLIND, AND THAT MADE IT HALF TRUE (2026-09-18). Tellis measured
    # SHARING. Two later sources — Google/Kantar's ABCDs and Nelson-Field's attention work — measure
    # sales likelihood and RECALL, and both want the brand present early. They do not contradict
    # Tellis; they measure different outcomes (hook-craft.md s5b, assets/creative-benchmarks.json).
    # So the finding depends on what this video is FOR, and the tool now says which reading applies
    # instead of stating the sharing one as if it were the only one.
    if a.brand and hook_text and brand_in(hook_text, a.brand):
        if a.objective == "sharing":
            warnings.append(("brand in hook",
                             f"{a.brand!r} is spoken inside the [INTRO] block, and this video is "
                             f"optimising for SHARING — the one outcome where early, long and "
                             f"persistent brand placement is measured to HURT (Tellis et al. 2019, "
                             f"PRIMARY, hook-craft.md s5). Deliberate, or inherited from a "
                             f"template? A client-mandated 0:00 brand is a legitimate decision "
                             f"with a cost attached"))
        elif a.objective in ("attribution", "conversion"):
            notes.append(("brand in hook (scoped)",
                          f"{a.brand!r} is spoken inside the [INTRO] block. For {a.objective}, that "
                          f"is NOT the Tellis finding — that one measured sharing. The attribution "
                          f"literature wants distinctive assets present early "
                          f"(hook-craft.md s5b). ⚠️ But note the distinction it turns on: this tool "
                          f"can only see the brand ANNOUNCED as a word. Presence — product in "
                          f"frame, house colour, a recurring character — is what that literature "
                          f"actually asks for, and no script check can see it"))
        else:
            warnings.append(("brand in hook",
                             f"{a.brand!r} is spoken inside the [INTRO] block, and no --objective "
                             f"was given. Early brand placement measurably hurt SHARING (Tellis et "
                             f"al. 2019); it is wanted for attribution and conversion (hook-craft.md "
                             f"s5b). Pass --objective sharing|attribution|conversion and the finding "
                             f"becomes the one that applies to this video"))

    bands, band_warns = reference_bands(B, text, rows, counts, a.ugc, a.lang)
    warnings += band_warns
    clocks = block_clocks(text)
    warnings += clock_warnings(clocks)
    if house_note:
        notes.append(("house band", house_note))
    if obj_note:
        notes.append(("objective", obj_note))

    if a.json:
        print(json.dumps({
            "lines": len(lines), "words": total_words, "speech_seconds": round(speech_s, 1),
            "scenes": len(scenes), "variance": round(variance, 2), "questions": questions,
            "hook_window_words": len(hook_text.split()),
            "blocks": [{"block": l, "window_s": w, "speech_s": round(sp, 1), "lines": n} for l, w, sp, n in clocks],
            "hook_anchors": [{"kind": k, "token": v} for k, v in anchors_in(hook_text, a.brand)],
            "checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in checks],
            "warnings": [{"name": n, "detail": d} for n, d in warnings],
            "notes": [{"name": n, "detail": d} for n, d in notes],
            "bands": [{"name": n, "value": v, "measured": m, "verdict": vd} for n, v, m, vd in bands],
            "result": "FAIL" if failed else "PASS"}, indent=2, ensure_ascii=False))
        return 1 if failed else 0

    print(f"\nscript_score — {os.path.basename(a.script)}"
          f"{'  [UGC mode]' if a.ugc else ''}  lang={a.lang}\n" + "=" * 74)
    print(f"  {len(lines)} spoken lines - {total_words} words - ~{speech_s:.0f}s of speech "
          f"- {len(scenes)} scene(s) - {len(set(speakers))} speaker(s)")
    print(f"  line words: min {min(counts)} / median {statistics.median(counts):.0f} / max {max(counts)}")
    print("-" * 74)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<26} {detail}")

    def show(title, items, fmt):
        if items:
            print(f"\n  {title}")
            for it in items[:6]:
                print("    " + fmt(it))
            if len(items) > 6:
                print(f"    … and {len(items)-6} more")

    if any(w for _l, w, _s, _n in clocks):
        print(f"\n  Two clocks, per block (speech at an assumed {WPS_ASSUMED} words/s + {PAUSE_ASSUMED}s a line):")
        for label, win, sp, n in clocks:
            print(f"    {label:<9} picture {str(win) + 's' if win else '—':>5}   speech {sp:5.1f}s"
                  + ("   ▲ longer than its picture" if win and sp > win else ""))
    show("Over the breath ceiling:", long_lines, lambda t: f"[{t[1]}w] {t[2][:80]}")
    show("Stumble candidates (say these aloud):", stumbles, lambda t: f"{t[1][:80]}")
    show("Held-open clauses (split into two lines):", subord, lambda t: f"{t[1][:80]}")
    show("Hype / banned vocabulary:", hype, lambda t: f"{t[1]!r} in: {t[2][:66]}")
    show("Write these the way they will be SAID:", ambig, lambda t: f"{t[1]!r} in: {t[2][:66]}")
    for name, detail in notes:
        print(f"  note  {name}: {detail}")
    if bands:
        print("\n  Measured reference (script corpus 2026-11-05, assets/script-bands.json — advisory, never a FAIL):")
        for name, value, measured, verdict in bands:
            mark = {"within": "  ", "above": "▲ ", "below": "▼ ", "note": "· "}[verdict]
            print(f"    {mark}{name:<24} {value:<34} | {measured}")
    for name, detail in warnings:
        print(f"\n  [WARN] {name}\n    " + detail)
    if flat_pairs and not a.ugc:
        print(f"\n  Reactivity proxy: {len(flat_pairs)} adjacent pair(s) of near-identical length, both "
              f"statements.\n    Weak signal only — run the real test by hand: could those two lines "
              f"swap speakers?\n    If yes, that is narration with two names on it (script-craft.md section 3).")

    print("\n" + "-" * 74)
    print("  NOT MEASURED, and they matter more than everything above:")
    print("    - Read it ALOUD, at pace. A stumble here is a stumble on camera.")
    print("    - Reactivity: does every line answer, resist, or deflect the one before it?")
    print("    - Is the idea any good? That was decided upstream, in ideation.md.")
    print("    - The gap's three legs (hook-craft.md s2): does the viewer KNOW they don't know it,")
    print("      CARE about the answer, and believe watching will FILL it? Importance is the leg")
    print("      that fails, and it is the one rewriting the line cannot supply.")
    print("    - Nothing here can see whether the hook withholds anything at all.")
    print("  Then score by hand (script-craft.md section 6): the 4 universal dimensions —\n"
          "  speakability, human voice, signal-to-noise, CLAIM SAFETY — plus 4 chosen from the\n"
          "  remaining 8, as the writer's note. This tool's result is mechanical only, never a\n"
          "  mark out of 10; what the gate checks on a script is in script-craft.md section 7.")
    print("=" * 74)
    if failed:
        print(f"  RESULT: FAIL — {', '.join(failed)}")
        return 1
    print("  RESULT: PASS (mechanical). The script is not yet approved — see above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
