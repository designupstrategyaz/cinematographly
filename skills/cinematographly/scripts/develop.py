#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""develop.py — the DEVELOPMENT gate. No script is approved until the job has done real
pre-production: sourced research, N genuinely different concepts, adversarial rounds that killed
something, a human choosing between them, a hook bank, and drafts with a critique between each.

Why (2026-09-06, second pass). The 2026-09-06 gate made the PROCESS un-skippable — a job, a
checkpoint, an approved script, linted prompts, an approved frame. It did nothing about the
CREATIVE process, and the operator's report was precise: *"there is no design thinking, no deep
pre-production. Just one quick script the AI thinks is best, which misses info in the skill or
online most of the time. It doesn't try multiple attempts and adversarial ones in series (5+) to
get to a better hook, script, story, let me choose and analyse them."*

One draft is the cheapest thing an agent can produce, and every gate downstream of the script
happily validates a mediocre script perfectly executed. `ideation.md` §3 ("diverge before you
converge"), §4 (the angle grid), §6 (kill tests) and §8 (the ideation gate) already said all of
this — as prose nothing enforced. This is the enforcement.

  develop.py init <job>       write 00-brief/DEVELOPMENT.md from the template
  develop.py check <job> [--phase concept|full]
                              validate it; exit 1 with every specific failure. `--phase concept` is
                              what must exist before the human picks (gate.py approve concept);
                              `full` adds hooks + drafts (gate.py approve script). gate.py runs both.
  develop.py status <job>     what is done, what is owed, in order
  develop.py --selftest

Exit codes: 0 pass · 1 findings · 2 usage/IO error.

What it demands, and why each one is there
------------------------------------------
  RESEARCH   ≥6 lines carrying a [TIER · source · date] tag (`preproduction-research.md` — the six
             sourced fields a brief needs). A concept invented from the model's priors is the
             "misses info in the skill or online" failure, exactly.
  LOOK       ≥4 real reference images that EXIST on disk with a provenance sidecar each, before a
             concept is written — and before any concept is SHOWN to the human. A live eval run on
             2026-09-06 produced the exact rationalisation this wording now forecloses: the agent
             wrote five concepts with no board and said the gap "doesn't block picking a concept
             now". It does. The board is what the choice is made against. A concept whose "one image" was imagined has never been checked
             against a photograph; this is the moodboard, and `refsource.py` / `pixabay_search.py`
             are how it gets filled. Descriptions of pictures do not count — the check is the file.
  CONCEPTS   ≥5, each with premise / question / image / structure / proof / risk filled, and
             **provably different from each other**: distinct dramatic questions, distinct opening
             images, ≥3 distinct structures, and pairwise word-overlap under a threshold. Five
             rewordings of one idea is the failure this check exists to catch — it is the cheap
             thing an agent does when told to "give five options".
  ADVERSARY  ≥2 rounds, each naming the hat it was argued from and each KILLING or WEAKENING at
             least one concept; ≥2 concepts killed across all rounds. A round that killed nothing
             did not happen (`ideation.md` §6 kill tests; the same evidence rule as `qa_log.py`).
  HOOKS      ≥5 against the chosen concept, each with an awareness level, a hook type and a
             written GAP, and not all the same type — the hook is routed from what the viewer
             already knows (`persuasion-psychology.md` §2), so five curiosity-gaps is one hook
             five times. The gap cell names what they don't know AND why they already care;
             importance is the leg that fails and the one rewriting cannot fix
             (`references/hook-craft.md` §2). Warns when the whole bank is indirect.
  CHOICE     the human picks: a surviving concept id, a name, and their verbatim quote. The agent
             recommends; it does not decide. This is the "let me choose and analyse them" line.
  DRAFTS     ≥3 script versions, and between consecutive versions a CRITIQUE of ≥15 words that
             names a specific line, beat or scene. A version bump with no recorded critique is a
             rewrite, not an iteration.

What it cannot do
-----------------
- It cannot tell you a concept is GOOD, only that five of them are genuinely different and that
  something was argued against them. Taste is the human's, which is why CHOICE is a human's quote.
- Its distinctness test is lexical. Two concepts with different words and the same idea pass it;
  the adversarial rounds are the backstop, and a human reading five concepts is the real one.
- (v2.69.0) It cannot catch a writer who lies on both sides: invented ids listed as deleted AND cited by a concept
  pass the research floor. The person naming what mattered, on a board that shows each concept's lines, is the
  check a file cannot make (build review 3, Sonnet; accepted as a known limit).
- It cannot verify the research is true — `research-quality.md` owns source tiers, and
  `claims_lint.py` owns the claims. This checks that sourced lines EXIST before anyone writes.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(SKILL_ROOT, "assets")

MIN_RESEARCH = 6
MIN_LOOK = 4
MIN_CONCEPTS = 5
MIN_ROUNDS = 2
MIN_KILLED = 2
MIN_HOOKS = 5
MIN_DRAFTS = 3
MIN_CRITIQUE_WORDS = 15
MAX_PAIR_OVERLAP = 0.55          # Jaccard on content words across question+image+structure

SOURCE_RE = re.compile(r"\[(PRIMARY|SECONDARY|TERTIARY|S|P|T)\s*[·|]", re.I)
DATED_RE = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b|\bread \d{4}-\d{2}-\d{2}\b", re.I)
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{1,80}>|NEEDS INPUT|TBD\b|\?\?\?|\.\.\.$", re.I)
CONCEPT_RE = re.compile(r"^###\s*(C\d+)\s*[·:.\-]\s*(.+?)\s*$", re.M)
# `- [environment] 00-brief/_look/pixabay-123-large.jpg — the tiled kitchen we can actually build`
LOOK_RE = re.compile(r"^[-*]\s*\[(?P<attr>[A-Za-z /-]{3,20})\]\s*(?P<path>[^\s—|]+)")
ROUND_RE = re.compile(r"^##\s*Adversarial round\s*(\d+)\s*[·:.\-]\s*(.+?)\s*$", re.M | re.I)
FIELD_RE = re.compile(r"^\s*(premise|question|image|structure|proof|risk|from)\s*:\s*(.*)$", re.I | re.M)
VERDICT_RE = re.compile(r"^\s*(killed|weakened|survived)\s*:\s*(.*)$", re.I | re.M)
DRAFT_RE = re.compile(r"^###\s*v(\d+)\b(.*)$", re.M)
CRITIQUE_RE = re.compile(r"^\s*critique\s*:\s*(.*(?:\n(?!\s*(?:###|##|critique\s*:)).*)*)", re.I | re.M)
# `[^|\n]` not `[^|]`: a dot-all cell swallows the next row when the trailing cell is absent,
# which silently turned a five-row bank into four. Caught by the selftest.
HOOK_ROW_RE = re.compile(r"^\|\s*(H\d+)\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|(?:([^|\n]*)\|)?", re.M)
# The direct half of the taxonomy (modes/ugc-volume.md §5). A bank drawn only from the
# indirect half has tested one side of a relationship that turns over (hook-craft.md §1).
DIRECT_TYPES = ("offer", "urgent", "cta", "comparison", "three things", "3 things",
                "testimonial", "serious", "trust", "unboxing", "first impression")
GAP_SPLIT_RE = re.compile(r"\s*(?:·|\|\||;|\bbecause\b|—)\s*", re.I)
MAX_GAP_ECHO = 0.60   # the "why they care" half restating the line is the commonest dodge
# ⛔ The other dodge, and the one that looks like a right answer: writing the SALIENCE leg twice.
# "because nobody has told them" describes the viewer's IGNORANCE, which is the gap restated, not a
# reason to care about closing it. A stake is something they already own, pay for, chose or worry
# about (hook-craft.md §2). Found by running the eval — the agent wrote this form every time, and
# so did this file's own first set of examples.
IGNORANCE_RE = re.compile(
    r"\b(?:nobody|no one|no-one)\s+(?:has\s+)?(?:ever\s+)?(?:told|explained|showed|shown|said)\b"
    r"|\bthey\s+(?:do\s+not|don't|never|have\s+never|haven't|had\s+never)\s+"
    r"(?:know|knew|hear|heard|see|seen|realise|realize|realised|realized)\b"
    r"|\b(?:not|never)\s+(?:been\s+)?(?:aware|told|explained)\b"
    r"|\bit\s+is\s?n[o']t\s+common\s+knowledge\b"
    r"|\bno\s+one\s+(?:knows|explains)\b", re.I)
CHOSEN_RE = re.compile(r"^\s*chosen\s*:\s*(C\d+)\b", re.I | re.M)
CHOSEN_LINE_RE = re.compile(r"^\s*chosen\s*:\s*(.+?)\s*$", re.I | re.M)

# ---- YOUR VOICE FIRST (v2.65.0, 2026-11-14: "Yes, quick fixes + Wave 1") --------------------------------
# A shipment review by two models found the same weakness first: the person meets the work as a late approver of
# options the agent invented. Research behind the change (references/ideation.md §0): AI-assisted writing comes out
# more alike across people (Doshi & Hauser, Science Advances 2024); AI examples fix people on the first idea
# (Wadinambiarachchi et al., CHI 2024); an AI that asks and reflects keeps ideas varied and keeps ownership, one
# that rewrites loses both (Maier et al., reported for CHI 2026). These checks apply to a DEVELOPMENT.md made from
# the 2.65 template (it carries VOICE_MARK); an older file is warned, never blocked, so jobs in flight are safe.
VOICE_MARK = "develop-template: 2.65"
# (v2.67.0) the mark is read as a NUMBER: a 2.67 template keeps every 2.65 check and adds the script checks. A
# string match would have switched Wave 1 off for every newer template (found by both plan reviewers, 2026-11-14).
MARK_RE = re.compile(r"develop-template:\s*(\d+)\.(\d+)")
TEMPLATE_VERSION = (2, 70)


def template_version(txt: str):
    """(major, minor) of the `develop-template:` mark, or None for a file made before the marks existed."""
    m = MARK_RE.search(txt or "")
    return (int(m.group(1)), int(m.group(2))) if m else None
QUOTED_RE = re.compile(r'["\u201c]([^"\u201c\u201d\n]{3,})["\u201d]')
TASTE_KEY_RE = re.compile(r"^\s*(asked|proud|cringe|loved|hated|never|for|skipped)\s*:\s*(.*)$", re.I | re.M)
MATERIAL_RE = re.compile(r"^[-*]\s*\[(seed|story|phrase|moment)\]\s*(.+)$", re.I | re.M)
SHOWN_RE = re.compile(r"^\s*shown\s*:\s*(.+?)\s*$", re.I | re.M)
RECOMMENDED_RE = re.compile(r"^\s*recommended\s*:\s*(C\d+)\b", re.I | re.M)
REFUSED_RE = re.compile(r"^\s*refused\s*:\s*(.+?)\s*$", re.I | re.M)
OPTION_RE = re.compile(r"^###\s*([A-Z])\b\s*[·:.\-]?\s*(.*?)\s*$", re.M)
THEIR_WORDS_RE = re.compile(r"^\s*their words\s*:\s*(.+?)\s*$", re.I | re.M)
PICKED_RE = re.compile(r"^\s*picked\s*:\s*([A-Z])\b", re.I | re.M)
WAIVER_RE = re.compile(r"^\s*waiver\s*:\s*(.+?)\s*$", re.I | re.M)


def _quotes(s: str, min_words: int = 3) -> list:
    return [q.strip() for q in QUOTED_RE.findall(s or "") if len(q.split()) >= min_words]


def _norm(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", (s or "").lower()))


def voice_checks(txt: str, cs: list, fields: dict, killed_all: set, phase: str) -> tuple:
    """(fails, warns, stats) for the taste session, their material, their picture, the pick, and (full) the two
    script options that carry one of their sentences."""
    fails, warns, st = [], [], {}
    taste = section(txt, "Taste")
    kv = [(k.lower(), v.strip()) for k, v in TASTE_KEY_RE.findall(taste)]
    skipped = [v for k, v in kv if k == "skipped"]
    st["taste"] = "skipped" if skipped else "asked"
    if skipped:
        if not _quotes(skipped[0]):
            fails.append('TASTE: `skipped:` needs their words, quoted ("I trust you, just make it"), not the agent\'s '
                         'summary — a skipped session is still their decision')
    else:
        one = {k: v for k, v in kv if k in ("asked", "proud", "cringe", "never", "for")}
        if not one.get("asked") or PLACEHOLDER_RE.search(one.get("asked", "")):
            fails.append("TASTE: no `asked: <who> · <YYYY-MM-DD>` — the taste session comes before any concept "
                         "(ideation.md §0). Ask three questions at a time; they may skip any")
        for k in ("proud", "cringe", "never", "for"):
            if not _quotes(one.get(k, "")):
                fails.append(f"TASTE: `{k}:` has no answer in their words, quoted (three words or more). Write what "
                             f"they said, not a tidy version of it (ideation.md §0: reflect, never rewrite)")
        loved = [v for k, v in kv if k == "loved" and _quotes(v)]
        hated = [v for k, v in kv if k == "hated" and _quotes(v)]
        if len(loved) < 2:
            fails.append(f"TASTE: {len(loved)} loved reference(s) with their reaction quoted, need 2 — "
                         f"`loved: <file, link or title> — \"<what they said about it>\"`")
        if len(hated) < 1:
            fails.append('TASTE: no hated reference with their reaction quoted — `hated: <title> — "<why>"`. What '
                         'they refuse is the strongest steer there is')
    mat = section(txt, "Their material")
    entries = [(k.lower(), v) for k, v in MATERIAL_RE.findall(mat) if _quotes(v)]
    none_line = re.search(r"^\s*none\s*:\s*(.+)$", mat, re.I | re.M)
    st["their_material"] = len(entries)
    if not entries and not (none_line and _quotes(none_line.group(1))):
        fails.append('THEIR MATERIAL: nothing of theirs is on file — `- [seed|story|phrase|moment] "<their words>"`, '
                     'or `none: "<their words declining>"`. Their seeds enter the concept bank as peers of the '
                     'agent\'s (ideation.md §0)')
    seeds = [v for k, v in entries if k == "seed"]
    from_theirs = [cid for cid, f in fields.items() if re.search(r"\btheir\b", f.get("from", ""), re.I)]
    st["concepts_from_them"] = len(from_theirs)
    if seeds and not from_theirs:
        fails.append(f"CONCEPTS: they gave {len(seeds)} seed(s) and no concept says `from: their seed` — their idea "
                     f"goes into the bank and is argued like the agent's, never left in the notes")
    # the board: one picture of theirs, unless they skipped the session
    if not skipped:
        mine = [l for l in section(txt, "Look").splitlines()
                if (m := LOOK_RE.match(l.strip())) and m.group("attr").strip().lower().startswith("their")]
        st["their_pictures"] = len(mine)
        if not mine:
            fails.append("LOOK: no picture of theirs on the board — at least one line `- [their <attribute>] "
                         "<path> — <what it settles>` (their photo, sketch or screenshot, with a provenance "
                         "sidecar). The stock pictures map the category's clichés; theirs sets the direction")
    # the pick is theirs: shown in a recorded order with the recommendation last, refusals recorded, combine allowed
    choice = section(txt, "Choice")
    ids = [c[0] for c in cs]
    shown = SHOWN_RE.search(choice)
    rec = RECOMMENDED_RE.search(choice)
    if not shown:
        fails.append("CHOICE: no `shown: C<n>, C<n>, …` — record the order the survivors were shown in. Shuffle "
                     "them and show the agent's recommendation LAST, so the first thing read is not the agent's "
                     "favourite (ideation.md §0)")
    else:
        order = re.findall(r"C\d+", shown.group(1))
        if rec and order and order[-1] != rec.group(1):
            fails.append(f"CHOICE: the recommendation {rec.group(1)} was shown in position "
                         f"{order.index(rec.group(1)) + 1 if rec.group(1) in order else '?'} of {len(order)}, "
                         f"not last")
    line = CHOSEN_LINE_RE.search(choice)
    if line and re.match(r"^\s*none\b", line.group(1), re.I):
        fails.append("CHOICE: they chose none — back to concepts with what they refused in hand; a pick of none "
                     "is a finding, not a pass")
    picked_ids = re.findall(r"C\d+", line.group(1)) if line else []
    for cid in picked_ids[1:]:
        if cid not in ids:
            fails.append(f"CHOICE: {cid} is not one of the concepts")
        elif cid in killed_all:
            fails.append(f"CHOICE: {cid} was KILLED in an adversarial round")
    refusals = [r for r in REFUSED_RE.findall(choice) if _quotes(r)]
    st["refusals"] = len(refusals)
    if not refusals:
        fails.append('CHOICE: no refusal recorded — `refused: C<n> — "<why, in their words>"` (or `refused: none — '
                     '"<their words>"`). What they turned down steers every later stage')
    if phase == "full":
        opts = blocks(section(txt, "Script options"), OPTION_RE)
        st["script_options"] = len(opts)
        # their words = the taste answers and their material, never the skip or the "none" line itself
        theirs = {_norm(q) for k, v in kv if k != "skipped" for q in _quotes(v)} | \
                 {_norm(q) for _k, v in entries for q in _quotes(v)}
        waiver = WAIVER_RE.search(section(txt, "Script options"))
        if not theirs:
            warns.append("SCRIPT OPTIONS: they gave no words of their own (skipped, and no material), so the options "
                         "carry none; offer again at the script stage")
        if len(opts) < 2:
            fails.append(f"SCRIPT OPTIONS: {len(opts)} shown, need 2 — after the drafts, two short alternatives on "
                         f"the concept they picked, side by side (script-craft.md §7b)")
        elif theirs and not (waiver and _quotes(waiver.group(1))):
            for oid, _t, body in opts:
                tw = THEIR_WORDS_RE.search(body)
                q = _quotes(tw.group(1) if tw else "", 3)
                if not q:
                    fails.append(f'SCRIPT OPTIONS: option {oid} has no `their words: "<a sentence of theirs>"` — each '
                                 f'option keeps one of their sentences, or `waiver: "<their words>"` says why not')
                elif not any(_norm(q[0]) in t_ or (len(t_.split()) >= 4 and t_ in _norm(q[0])) for t_ in theirs):
                    fails.append(f"SCRIPT OPTIONS: option {oid}'s `their words` are not in Taste or Their material — "
                                 f"quote what they said, not a polished version")
        pk = PICKED_RE.search(section(txt, "Script options"))
        pq = QUOTE_RE.search(section(txt, "Script options"))
        if not pk or (opts and pk.group(1) not in [o[0] for o in opts]):
            fails.append("SCRIPT OPTIONS: no `picked: <A|B>` naming one of the options shown")
        if not pq or len(pq.group(1).split()) < 3:
            fails.append("SCRIPT OPTIONS: `quote:` must be their reply verbatim (three words or more)")
    return fails, warns, st
# ---- RESEARCH THAT CHANGES DECISIONS (v2.69.0, 2026-11-14: "Also work on all other improvements you listed") ----
# Wave 4, planned with three review rounds each by Grok 4.7 and Sonnet 5.5. The six-line floor counted lines; nothing
# asked whether a line changed the film. Here the tier is picked from the decision (preproduction-research.md §2.1),
# each line names the alternative it decides, the PERSON names the lines that mattered and the rest are deleted (§7),
# the objective is theirs, and at T2+ one real audience phrase reaches the hook. Applies from `develop-template: 2.69`.
RESEARCH_CHECKS_FROM = (2, 69)
SAVED_SOURCE_FROM = (2, 70)          # (v2.70.0) each audience phrase names where it was saved
TIER_RE = re.compile(r"^\s*tier\s*:\s*(T[0-3])\b(.*)$", re.I | re.M)
T0_RE = re.compile(r"^[-*]\s*T0\b(.+)$", re.M)
R_LINE_RE = re.compile(r"^[-*]\s*(R\d+)\b\s*(.+)$", re.M)
BARE_TAG_RE = re.compile(r"^[-*]\s*\[(?:PRIMARY|SECONDARY|TERTIARY)\b", re.I | re.M)
DECIDES_RE = re.compile(r"\bdecides\s*:\s*(.+)$", re.I)
ALTERNATIVE_RE = re.compile(r"\bC\d+\b|\binstead of\b|\brules? (?:in|out)\b|\brather than\b|\bvs\.?\b|\bversus\b",
                            re.I)    # "not" and "over" let "tone not shape" pass (build review 1, Sonnet)
CITE_RE = lambda key: re.compile(r"^\s*" + key + r"\s*:\s*(.+?)\s*$", re.I | re.M)   # noqa: E731
CATEGORY_RE = re.compile(r"^\s*category\s*:\s*(.+?)\s*·\s*ours\s*:\s*(keep|break)\b\s*(?:—|-|:)?\s*(.*)$", re.I | re.M)
OBJECTIVE_RE = re.compile(r"^\s*objective\s*:\s*(\w+)\b(.*)$", re.I | re.M)
OBJECTIVES = ("sharing", "attribution", "conversion")            # the words script_score.py --objective accepts
MATTERED_RE = re.compile(r"^\s*research that mattered\s*:\s*(.+?)\s*$", re.I | re.M)
DELETED_RE = re.compile(r"^\s*deleted\s*:\s*(.+?)\s*$", re.I | re.M)
VOICE_LINE_RE = re.compile(r'^[-*]\s*\[(problem|objection|result|other)\]\s*["“]([^"“”\n]+)["”][ \t]*(.*)$',
                           re.I | re.M)
PHRASE_WORDS = (3, 15)


def _ids(s: str) -> list:
    return re.findall(r"\bR\d+\b", s or "")


def _cites(body: str, key: str) -> list:
    """R ids a concept's `research:` / `confirms:` line cites; a template placeholder left in cites nothing (build
    review 3, Sonnet: a fresh T0 template was refused for `<R1, R3 — …>` it never wrote)."""
    return _ids(" ".join(v for v in CITE_RE(key).findall(body) if not PLACEHOLDER_RE.search(v)))


def research_checks(job: str, txt: str, cs: list, fields: dict, rounds: list, phase: str) -> tuple:
    """(fails, warns, stats) for a 2.69+ DEVELOPMENT.md: the tier, the decision lines, citations, the person's
    `research that mattered`, the objective, keep-or-break per concept, and (T2+) the audience phrase in the hook."""
    fails, warns, st = [], [], {}
    tv_ = template_version(txt)
    res = section(txt, "Research")
    tm = TIER_RE.search(res)
    tier = int(tm.group(1)[1]) if tm else None
    st["tier"] = f"T{tier}" if tier is not None else None
    if tier is None:
        fails.append("RESEARCH: no `tier: T0|T1|T2|T3` — pick the tier from the decision, not the topic: how many "
                     "videos being wrong touches, and whether it can be reversed after delivery "
                     "(preproduction-research.md §2.1). T0 is a legitimate answer")
        return fails, warns, st
    rl = {rid: body for rid, body in R_LINE_RE.findall(res)}
    st["research_lines"] = len(rl)
    if len(rl) != len(R_LINE_RE.findall(res)):
        fails.append("RESEARCH: an R id is used twice — one id per line")
    if BARE_TAG_RE.search(res):
        fails.append("RESEARCH: a sourced line has no id — write it `- R<n> [PRIMARY · source · date] <fact> · "
                     "decides: <the alternative>`, so a concept can cite it and the person can name it")
    choice = section(txt, "Choice")
    deleted = set(_ids(" ".join(DELETED_RE.findall(choice))))
    for key, rx in (("research that mattered", MATTERED_RE), ("deleted", DELETED_RE)):
        for v in rx.findall(choice):
            if PLACEHOLDER_RE.search(v):     # an unfilled template line is not the person's answer (review 1, Sonnet)
                fails.append(f"CHOICE: `{key}:` is still the template's placeholder — write their answer or remove it")
    if tier == 0:
        cites_ = {r for _c, _t, b in cs for k in ("research", "confirms") for r in _cites(b, k)}
        if cites_:     # T0 means no research: nothing may rest on an id, deleted or not (build review 2, Grok)
            fails.append(f"RESEARCH: tier T0 but a concept cites {', '.join(sorted(cites_))} — T0 means the call was "
                         f"made without research; drop the citation or raise the tier")
        if rl:
            fails.append(f"RESEARCH: tier T0 but {len(rl)} research line(s) ({', '.join(rl)}) — T0 means the call was "
                         f"made without research: delete them, or raise the tier")
        t0 = T0_RE.search(res)
        if not t0 or not re.search(r"\bbasis\s*:\s*\S", t0.group(1), re.I) \
                or not re.search(r"\braise to T1 if\s*:\s*\S", t0.group(1), re.I) or PLACEHOLDER_RE.search(t0.group(1)):
            fails.append("RESEARCH: T0 needs its one line — `- T0 · <the call> · basis: <what it rests on> · raise to "
                         "T1 if: <what would change it>` (§2.1: the call was made without research, and on what)")
    else:
        for rid, body in rl.items():
            if not (SOURCE_RE.search(body) and DATED_RE.search(body)):
                fails.append(f"RESEARCH {rid}: no `[PRIMARY|SECONDARY|TERTIARY · source · YYYY-MM-DD]` tag "
                             f"(research-quality.md for the tiers)")
            dm = DECIDES_RE.search(body)
            lone_id = bool(dm and re.fullmatch(r"\s*(C\d+)\s*", dm.group(1)) and
                           dm.group(1).strip() in {c[0] for c in cs})        # `decides: C2` (build review 1, Grok)
            if not dm or PLACEHOLDER_RE.search(dm.group(1)) or (len(dm.group(1).split()) < 2 and not lone_id):
                fails.append(f"RESEARCH {rid}: no `decides:` on its line — say which choice this fact changes, on the "
                             f"same line as the fact (one line per R). A fact that decides nothing is deleted (§7)")
            elif not ALTERNATIVE_RE.search(dm.group(1)):
                warns.append(f"RESEARCH {rid}: `decides:` names no alternative — write the option it rules in or "
                             f"out (a concept id, or 'instead of', 'rules out', 'rather than')")
        # the floor counts what was researched, before the person's deletions: otherwise naming two of three lines
        # would deadlock (delete the third, then fail the floor) — build review 1, Sonnet
        # a deleted id counts only if a concept or a kill cites it — evidence the line existed (build review 2, Sonnet:
        # `deleted: R1, R2, R3` with nothing ever written passed the floor)
        cited_anywhere = {r for _c, _t, b in cs for k in ("research", "confirms") for r in _cites(b, k)} | \
            set(_ids(" ".join(b for _r, _h, b in rounds)))
        researched = set(rl) | (deleted & cited_anywhere)
        if len(researched) < 3:
            fails.append(f"RESEARCH: T{tier} with {len(researched)} line(s) researched, need 3 — at T1 orientation is 3–8 lines, each "
                         f"tied to a decision (§2.1). If nothing needs looking up, the tier is T0: say so")
        if tier == 1 and len(rl) > 8:
            warns.append(f"RESEARCH: {len(rl)} lines at T1 — the ladder says 3–8; past that it is T2 work or "
                         f"research for its own sake (§4)")
        if tier >= 2 and len(" ".join(CITE_RE("synthesis").findall(res)).split()) < 15:
            fails.append(f"RESEARCH: T{tier} needs `synthesis:` (15 words or more): the themes, the contradictions "
                         f"kept, the named sources (§2.1; product-management:synthesize-research)")
        if tier == 3 and len(" ".join(CITE_RE("counter-case").findall(res)).split()) < 10:
            fails.append("RESEARCH: T3 needs `counter-case:` — the refutation pass on the load-bearing claim, its "
                         "strongest case against and where it comes from (research-quality.md §4)")
    known = set(rl) | deleted
    # citations: concepts (research:, confirms:) and kills; unknown ids fail
    cited = set()
    for cid, _t, body in cs:
        for key in ("research", "confirms"):
            for ref in _cites(body, key):
                cited.add(ref)
                if ref not in known:
                    fails.append(f"CONCEPT {cid}: cites {ref}, which is not a research line")
        if tier >= 1:
            cm = CATEGORY_RE.search(body)
            if not cm or len(cm.group(3).split()) < 4 or PLACEHOLDER_RE.search(cm.group(0)):
                fails.append(f"CONCEPT {cid}: no keep-or-break line — `category: <the usual ad here> · ours: keep|"
                             f"break — <how our first three seconds differ>` (ideation.md §2b)")
    by_kill = set()
    for rid_, _h, body in rounds:
        by_kill |= set(_ids(body))
    cited |= by_kill
    st["research_cited"] = len(cited & set(rl))
    cm_ = CHOSEN_LINE_RE.search(choice)
    chosen_ = set(re.findall(r"C\d+", cm_.group(1))) if cm_ else set()
    by_chosen = set()
    for cid, _t, body in cs:
        if cid in chosen_:
            for key in ("research", "confirms"):
                by_chosen |= set(_cites(body, key))
    # the objective is the person's, in their words
    om = OBJECTIVE_RE.search(choice)
    if not om or om.group(1).lower() not in OBJECTIVES or not _quotes(om.group(2)):
        fails.append(f"CHOICE: no `objective: {'|'.join(OBJECTIVES)} — \"<their why, verbatim>\"` — the person "
                     f"says what the film is for; stage 2 passes it to script_score.py --objective (it switches the "
                     f"brand-in-hook note only, never the emotional register: performance-metrics.md §0c)")
    else:
        st["objective"] = om.group(1).lower()
    # the person names the research that mattered; every other line is deleted (§7)
    if tier >= 1:
        mm = MATTERED_RE.search(choice)
        if not mm:
            fails.append("CHOICE: no `research that mattered: R<n>, …` — show the concept board with each concept's "
                         "cited lines and ask the person which facts changed the film. Their answer, not the agent's "
                         "(`none — \"<their words>\"` is an answer)")
        else:
            named = set(_ids(mm.group(1)))
            none_ = bool(re.match(r"^\s*none\b", mm.group(1), re.I) and _quotes(mm.group(1)))
            if not named and not none_ and not PLACEHOLDER_RE.search(mm.group(1)):
                fails.append('CHOICE: `research that mattered:` names no R id — or write `none — "<their words>"`')
            if none_ and not rl:
                warns.append("RESEARCH: they said none of it mattered and every line is deleted — the call ran as T0; "
                             "say so in the brief")
            for ref in sorted(named - set(rl)):
                fails.append(f"CHOICE: {ref} is named as mattering but is not a research line")
            for ref in sorted(set(rl) - named):
                fails.append(f"RESEARCH {ref}: the person did not name it as mattering — delete the line and list "
                             f"it under `deleted:` in Choice (§7: research that lands nowhere is deleted; "
                             f"`confirms:` does not keep it)")
            for ref in sorted(named & set(rl) - by_chosen - by_kill):
                # a line that mattered landed in the film that ships or in a kill; a citation on a concept that was
                # killed for other reasons is not where it landed (build review 1, Grok)
                fails.append(f"RESEARCH {ref}: named as mattering but neither the chosen concept cites it nor a kill "
                             f"names it — say where it landed in the film, or it did not matter")
    # the audience's own words (T2+): a separate list, never the taste allow-list
    if tier >= 2:
        av = section(txt, "Audience voice")
        good, kinds = [], set()
        for kind, phrase, rest in VOICE_LINE_RE.findall(av):
            n = len(phrase.split())
            if not (PHRASE_WORDS[0] <= n <= PHRASE_WORDS[1]) or not DATED_RE.search(rest) or \
                    len(re.sub(r"[·\-\s\d]", "", DATED_RE.sub("", rest))) < 3:
                fails.append(f'AUDIENCE VOICE: "{phrase[:40]}" — a phrase is {PHRASE_WORDS[0]}–{PHRASE_WORDS[1]} '
                             f"words, then `· <source type> · YYYY-MM-DD`, and never a customer's name")
                continue
            # (v2.70.0) where the phrase was saved: a file in the job or a link — the defence against an invented
            # customer voice (Wave 4 build review, Sonnet). Required from template 2.70, a warning before it
            sv = re.search(r"\bsaved\s*:\s*(\S+)", rest)
            sv_link = bool(sv and re.match(r"https?://", sv.group(1)))
            sv_ok = bool(sv and (sv_link or os.path.isfile(_jobfile(job, sv.group(1)))))
            if sv_link:      # nothing here opens a link: it passes, with a warning (build review 1, Grok)
                warns.append(f'AUDIENCE VOICE: "{phrase[:40]}" is saved only as a link, which nothing here can check — '
                             f'save a copy (a screenshot or export) in the job')
            if not sv_ok:
                msg = (f'AUDIENCE VOICE: "{phrase[:40]}" has no `saved: <file in the job or link>` — keep the screenshot, '
                       f'export or link it came from, so a phrase can be checked, never invented')
                if tv_ and tv_ >= SAVED_SOURCE_FROM:
                    fails.append(msg)
                else:
                    warns.append(msg)
            good.append((kind.lower(), _norm(phrase))); kinds.add(kind.lower())
        st["audience_phrases"] = len(good)
        if not good:
            fails.append('AUDIENCE VOICE: none — at T2+, `## Audience voice` holds the phrases people actually use, '
                         '`- [problem|objection|result|other] "<3–15 words>" · <review|support|search query|comment> · '
                         'YYYY-MM-DD`. No client text? A search query is a source (discovery-and-search.md §5)')
        elif not kinds & {"problem", "objection"}:
            fails.append("AUDIENCE VOICE: no problem or objection phrase — the hook speaks one of them")
        if phase == "full" and good:
            so = section(txt, "Script options")
            pk = PICKED_RE.search(so)
            body = next((b for o, _t, b in blocks(so, OPTION_RE) if pk and o == pk.group(1)), "")
            fm = re.search(r"^\s*file\s*:\s*(.+?)\s*$", body, re.M)
            fp_ = _jobfile(job, fm.group(1)) if fm else ""
            lines = spoken_lines(fp_) if fm else []
            onscreen, hook_cards, nblock = [], [], 0
            try:
                import script_score as _ss
            except ImportError:
                _ss = None
            for l_ in (script_body(fp_) if fm else []):
                if _ss and _ss.BLOCK_RE.match(l_):
                    nblock += 1
                for t_ in re.findall(r'^\s*TEXT\s*:\s*(.+?)\s*$', l_, re.I):
                    onscreen.append(_norm(t_))
                    if nblock <= 1:
                        hook_cards.append(_norm(t_))     # the hook block's own cards only (build review 2, Grok)
            if lines:
                hook, where = " " + " ".join(lines[:2]) + " ", "its first two spoken lines"
            else:     # a silent film: the phrase may sit in its on-screen `TEXT:` cards (build reviews 1–2, Sonnet)
                hook = " " + " ".join(hook_cards) + " " if fm else ""
                where = "its on-screen TEXT cards (it has no spoken line)"
            if not fm or not os.path.isfile(fp_):
                fails.append("AUDIENCE VOICE: the picked option has no readable `file:` — the phrase check needs it")
            elif not any(k in ("problem", "objection") and f" {p} " in hook for k, p in good):
                fails.append(f"AUDIENCE VOICE: the picked option's hook ({where}) carries none of the problem or "
                             f"objection phrases — one real phrase of theirs reaches the film")
            for k, p in good:
                if k == "result" and any(f" {p} " in f" {l} " for l in lines + onscreen):
                    fails.append(f'AUDIENCE VOICE: the result phrase "{p}" is spoken or shown in the script — a '
                                 f"generated character never reports a customer's result as its own (compliance.md §2)")
    return fails, warns, st


BY_RE = re.compile(r"^\s*by\s*:\s*(.+?)\s*$", re.I | re.M)
QUOTE_RE = re.compile(r"^\s*quote\s*:\s*(.+?)\s*$", re.I | re.M)
STOP = set("a an the and or but of to in on at for with from by as is are was were be been it its "
           "this that these those he she they we you i not no yes into over under about after "
           "before while when then than so if what who whose which how why one two three".split())


def words(s: str) -> set:
    return {w for w in re.findall(r"[a-z']{3,}", (s or "").lower()) if w not in STOP}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def section(text: str, title: str) -> str:
    m = re.search(rf"^##\s*{re.escape(title)}\b.*$", text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^##\s", rest, re.M)
    return rest[: n.start()] if n else rest


def blocks(text: str, pattern: re.Pattern) -> list:
    """[(id, label, body)] for each ### heading matching pattern, body to the next ## or ###."""
    out, ms = [], list(pattern.finditer(text))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        nxt = re.search(r"^##\s", text[m.end():end], re.M)
        body = text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():end]
        out.append((m.group(1), m.group(2) if m.lastindex and m.lastindex >= 2 else "", body))
    return out


def _sidecar_of(asset: str) -> str:
    """The ONE sidecar resolver (provenance.find_sidecar), with a local fallback."""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import provenance
        return provenance.find_sidecar(asset)
    except Exception:
        for c in (asset + ".json", os.path.splitext(asset)[0] + ".json"):
            if os.path.isfile(c):
                return c
        return ""


def dev_path(job: str) -> str:
    return os.path.join(os.path.abspath(job), "00-brief", "DEVELOPMENT.md")


# ----------------------------------------------------------------------------------------------
def check(job: str, min_concepts: int = MIN_CONCEPTS, phase: str = "full") -> dict:
    """phase 'concept' checks research → concepts → adversarial → choice (what must exist BEFORE the
    human picks and before a word of script). phase 'full' adds hooks and drafts."""
    p = dev_path(job)
    if not os.path.isfile(p):
        return {"ok": False, "path": p, "fails": [
            f"no {os.path.relpath(p, job)} — `develop.py init {job}` writes the template. "
            f"A script with no development behind it is one guess wearing a version number "
            f"(ideation.md §3)"], "warns": [], "stats": {}}
    txt = open(p, encoding="utf-8").read()
    fails, warns, stats = [], [], {}
    tv = template_version(txt)
    laddered = bool(tv and tv >= RESEARCH_CHECKS_FROM)     # (v2.69.0) the ladder replaces the six-line floor

    # --- RESEARCH -------------------------------------------------------------------------------
    research = section(txt, "Research")
    sourced = [l.strip() for l in research.splitlines()
               if SOURCE_RE.search(l) and DATED_RE.search(l) and len(l.split()) >= 6]
    stats["research_sourced"] = len(sourced)
    if len(sourced) < MIN_RESEARCH and not laddered:
        fails.append(f"RESEARCH: {len(sourced)} sourced line(s), need {MIN_RESEARCH}. Each is one "
                     f"line with a `[PRIMARY|SECONDARY · source · YYYY-MM-DD]` tag "
                     f"(preproduction-research.md; research-quality.md for the tiers). Concepts "
                     f"built on the model's priors are the 'missed the information' failure")

    # --- LOOK: the moodboard is files, not adjectives -------------------------------------------
    # Real pictures before invented ones. A concept's `image:` line is a claim about a photograph
    # that may not exist; four references that DO exist, with provenance, are what stop the whole
    # film being designed out of the model's priors (preproduction-research.md; stock-sourcing.md §9).
    look_sec = section(txt, "Look")
    look_hits, look_missing, look_unprovenanced = [], [], []
    for line in look_sec.splitlines():
        m = LOOK_RE.match(line.strip())
        if not m:
            continue
        rel = m.group("path").strip()
        full = rel if os.path.isabs(rel) else os.path.join(os.path.abspath(job), rel)
        if not os.path.isfile(full):
            look_missing.append(rel)
            continue
        side = _sidecar_of(full)
        if not side:
            look_unprovenanced.append(rel)
            continue
        look_hits.append(rel)
    stats["look"] = len(look_hits)
    if len(look_hits) < MIN_LOOK:
        fails.append(f"LOOK: {len(look_hits)} sourced reference(s), need {MIN_LOOK}. Each line is "
                     f"`- [attribute] <path under the job> — <what it settles>`, and the file has "
                     f"to be THERE with a provenance sidecar. `refsource.py brief` turns the shots "
                     f"into searches; `pixabay_search.py -q '<terms>' --download 00-brief/_look/` "
                     f"fills the board directly. A concept designed against imagined pictures is "
                     f"the 'random generations that made no sense' failure, one stage earlier. "
                     f"⛔ DO NOT PRESENT THE CONCEPTS while this is outstanding — not as a "
                     f"shortlist, not 'to pick from now and source later'. The board is what the "
                     f"human's choice is made against; showing five concepts first makes the "
                     f"board a formality they have already decided around")
    for rel in look_missing:
        fails.append(f"LOOK: {rel} is listed but not on disk — a moodboard entry is a file, not a "
                     f"caption")
    for rel in look_unprovenanced:
        fails.append(f"LOOK: {rel} has no provenance sidecar — every reference asset carries one "
                     f"(source, licence, clearance) from the moment it lands "
                     f"(`provenance.py record`; stock-sourcing.md §9)")

    # --- CONCEPTS -------------------------------------------------------------------------------
    cs = blocks(section(txt, "Concepts"), CONCEPT_RE)
    stats["concepts"] = len(cs)
    fields = {}
    for cid, title, body in cs:
        f = {k.lower(): v.strip() for k, v in FIELD_RE.findall(body)}
        fields[cid] = f
        missing = [k for k in ("premise", "question", "image", "structure", "proof", "risk")
                   if not f.get(k)]
        if missing:
            fails.append(f"CONCEPT {cid}: missing {', '.join(missing)} — a concept is not an idea "
                         f"until it names its dramatic question, its one image and why it is true "
                         f"for THIS brand (ideation.md §5)")
        for k, v in f.items():
            if PLACEHOLDER_RE.search(v):
                fails.append(f"CONCEPT {cid}.{k} is a placeholder: {v[:50]!r}")
        if f.get("question") and not f["question"].rstrip().endswith("?"):
            fails.append(f"CONCEPT {cid}.question is not a question — the dramatic question is the "
                         f"thing the film opens and closes (ideation.md §5)")
    if len(cs) < min_concepts:
        fails.append(f"CONCEPTS: {len(cs)}, need {min_concepts}. Diverge before you converge — the "
                     f"angle grid in ideation.md §4 generates them; the first idea is a starting "
                     f"point, not a shortlist")
    # distinctness — five rewordings of one idea is the cheap failure
    if len(cs) >= 2:
        qs = {cid: (f.get("question") or "").strip().lower().rstrip("?") for cid, f in fields.items()}
        ims = {cid: (f.get("image") or "").strip().lower() for cid, f in fields.items()}
        for label, d in (("dramatic question", qs), ("opening image", ims)):
            seen = {}
            for cid, v in d.items():
                if v and v in seen:
                    fails.append(f"CONCEPTS {seen[v]} and {cid} share the same {label} — that is one "
                                 f"concept written twice")
                seen[v] = cid
        structures = {(f.get("structure") or "").strip().lower() for f in fields.values() if f.get("structure")}
        stats["distinct_structures"] = len(structures)
        if len(cs) >= min_concepts and len(structures) < 3:
            fails.append(f"CONCEPTS: only {len(structures)} distinct structure(s) across {len(cs)} "
                         f"concepts — vary the SHAPE (ideation.md §4's grid axes), not just the words")
        pairs = []
        ids = [c[0] for c in cs]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = fields[ids[i]], fields[ids[j]]
                wa = words(" ".join(a.get(k, "") for k in ("question", "image", "structure")))
                wb = words(" ".join(b.get(k, "") for k in ("question", "image", "structure")))
                ov = jaccard(wa, wb)
                if ov > MAX_PAIR_OVERLAP:
                    pairs.append((ids[i], ids[j], ov))
        stats["overlapping_pairs"] = len(pairs)
        for a, b, ov in pairs[:4]:
            fails.append(f"CONCEPTS {a} and {b} overlap {ov:.0%} on question+image+structure "
                         f"(cap {MAX_PAIR_OVERLAP:.0%}) — same concept, different words")

    # --- ADVERSARIAL ----------------------------------------------------------------------------
    rounds = blocks(txt, ROUND_RE)
    stats["rounds"] = len(rounds)
    killed_all, weak_all = set(), set()
    for rid, hat, body in rounds:
        if not hat.strip() or PLACEHOLDER_RE.search(hat):
            fails.append(f"ROUND {rid}: no hat named — say what it was argued FROM (the skeptical "
                         f"buyer, the compliance officer, the competitor, the bored scroller). An "
                         f"unnamed adversary is the same voice agreeing with itself")
        v = {k.lower(): vv for k, vv in VERDICT_RE.findall(body)}
        k = {x.strip() for x in re.split(r"[,\s]+", v.get("killed", "")) if re.match(r"^C\d+$", x.strip())}
        w = {x.strip() for x in re.split(r"[,\s]+", v.get("weakened", "")) if re.match(r"^C\d+$", x.strip())}
        reasons = len(re.findall(r"—|--|:\s*\S", v.get("killed", "") + v.get("weakened", "")))
        if not (k or w):
            fails.append(f"ROUND {rid}: killed nothing and weakened nothing — a round with no "
                         f"casualties did not happen (ideation.md §6; same evidence rule as qa_log.py)")
        if (k or w) and not reasons:
            fails.append(f"ROUND {rid}: names concepts but no reason — `killed: C3 — the claim needs "
                         f"a document nobody has`")
        killed_all |= k
        weak_all |= w
    if len(rounds) < MIN_ROUNDS:
        fails.append(f"ADVERSARIAL: {len(rounds)} round(s), need {MIN_ROUNDS} — in series, each from "
                     f"a different hat, each seeing the previous round's survivors")
    if len(killed_all) < MIN_KILLED and len(cs) >= min_concepts:
        fails.append(f"ADVERSARIAL: {len(killed_all)} concept(s) killed across all rounds, need "
                     f"{MIN_KILLED}. If everything survived, the tests were not tests")
    stats["killed"] = len(killed_all)

    # --- CHOICE ---------------------------------------------------------------------------------
    choice = section(txt, "Choice")
    chosen = CHOSEN_RE.search(choice)
    by = BY_RE.search(choice)
    quote = QUOTE_RE.search(choice)
    stats["chosen"] = chosen.group(1) if chosen else None
    if not chosen:
        fails.append("CHOICE: no `chosen: C<n>` — the agent shortlists and argues; the HUMAN picks. "
                     "Put the options in front of them (AskUserQuestion) and record the answer")
    else:
        if cs and chosen.group(1) not in [c[0] for c in cs]:
            fails.append(f"CHOICE: {chosen.group(1)} is not one of the concepts")
        if chosen.group(1) in killed_all:
            fails.append(f"CHOICE: {chosen.group(1)} was KILLED in an adversarial round — either the "
                         f"kill was wrong (revise the round and say why) or the choice is")
    if not by or PLACEHOLDER_RE.search(by.group(1)):
        fails.append("CHOICE: no `by:` — name the human who chose")
    if not quote or len(quote.group(1).split()) < 3:
        fails.append("CHOICE: `quote:` must be the chooser's reply verbatim (three words or more). "
                     "gate.py approve concept records the same quote against the transcript")

    voiced = bool(tv and tv >= (2, 65))
    stats["voice"] = voiced
    if voiced:
        vf, vw, vs = voice_checks(txt, cs, fields, killed_all, "concept")
        fails += vf; warns += vw; stats.update(vs)
    if laddered:
        rf, rw, rs = research_checks(job, txt, cs, fields, rounds, phase)
        fails += rf; warns += rw; stats.update(rs)
    elif voiced:
        warns.append("RESEARCH: this DEVELOPMENT.md predates the research ladder (v2.69.0), so it keeps the six-line "
                     "floor and nothing asks whether a line changed the film. For a new job, start from `develop.py init`")
    if not voiced:
        warns.append("TASTE: this DEVELOPMENT.md predates the taste session (v2.65.0), so nothing checks that the "
                     "person's own taste, material or picture shaped the concepts. For a new job, start from "
                     "`develop.py init` (ideation.md §0)")

    if phase == "concept":
        return {"ok": not fails, "path": p, "fails": fails, "warns": warns, "stats": stats,
                "phase": phase}

    # --- HOOKS ----------------------------------------------------------------------------------
    hooks = HOOK_ROW_RE.findall(section(txt, "Hooks"))
    stats["hooks"] = len(hooks)
    if len(hooks) < MIN_HOOKS:
        fails.append(f"HOOKS: {len(hooks)}, need {MIN_HOOKS} against the chosen concept — table rows "
                     f"`| H1 | awareness | type | the line/beat | the gap |` "
                     f"(assets/hook-bank-template.md)")
    else:
        types = {h[2].strip().lower() for h in hooks if h[2].strip()}
        aware = {h[1].strip().lower() for h in hooks if h[1].strip()}
        lines = [h[3].strip() for h in hooks]
        if len(types) < 3:
            fails.append(f"HOOKS: {len(types)} distinct type(s) — five of one type is one hook five "
                         f"times (modes/ugc-volume.md §5 lists the types)")
        if len(aware) < 2:
            warns.append("HOOKS: every hook targets the same awareness level — the level picks the "
                         "hook (persuasion-psychology.md §2); testing one level is testing one guess")
        if any(not l or PLACEHOLDER_RE.search(l) for l in lines):
            fails.append("HOOKS: a row has no line/beat written")

        # --- the gap column: what they don't know, AND why they already care ------------------
        # hook-craft.md §2 — a gap has three legs and IMPORTANCE is the one that fails most often,
        # because it is the one rewriting cannot supply. The check cannot judge the answer; it can
        # insist the writer wrote one, and catch the dodge of restating the line back.
        missing, thin, echo, ignorance = [], [], [], []
        for h in hooks:
            hid, line, gap = h[0], h[3].strip(), (h[4] or "").strip()
            if not gap or PLACEHOLDER_RE.search(gap):
                missing.append(hid); continue
            halves = [x for x in GAP_SPLIT_RE.split(gap) if x.strip()]
            if len(halves) < 2 or min(len(x.split()) for x in halves[:2]) < 3:
                thin.append(hid); continue
            if jaccard(words(halves[1]), words(line)) > MAX_GAP_ECHO:
                echo.append(hid); continue
            if IGNORANCE_RE.search(halves[1]):
                ignorance.append(hid)
        if missing:
            fails.append(f"HOOKS: no gap written for {', '.join(missing)} — a fifth cell saying "
                         f"what they don't know AND why they already care. A hook whose second half "
                         f"is hard to write is hollow, and no rewrite of the line fixes it "
                         f"(hook-craft.md §2)")
        if thin:
            fails.append(f"HOOKS: the gap for {', '.join(thin)} has only one half — the house form "
                         f"is `they don't know <X> · because <Y>`, both halves written out. "
                         f"Importance is the leg that fails (hook-craft.md §2)")
        if echo:
            fails.append(f"HOOKS: the 'why they care' for {', '.join(echo)} restates the line "
                         f"instead of naming what the viewer already wants — the commonest way to "
                         f"fill this cell without answering it (hook-craft.md §2)")
        if ignorance:
            fails.append(f"HOOKS: the 'why they care' for {', '.join(ignorance)} describes what the "
                         f"viewer DOESN'T KNOW — that is the gap written twice, not a reason to "
                         f"close it. Name a stake they already hold: something they own, pay for, "
                         f"chose, or worry about. The test: could they have said it about "
                         f"themselves yesterday? (hook-craft.md §2)")

        # --- both halves of the curve ---------------------------------------------------------
        if types and not any(any(d in ty for d in DIRECT_TYPES) for ty in types):
            warns.append("HOOKS: every hook is from the indirect half of the taxonomy — the "
                         "concreteness/click relationship turns over, so a bank of five indirect "
                         "hooks has tested one side of it (hook-craft.md §1). Add a direct one "
                         "(offer, comparison, three things, testimonial, serious) even if you "
                         "expect it to lose; that is what makes the bank evidence")

    # --- DRAFTS ---------------------------------------------------------------------------------
    drafts_sec = section(txt, "Drafts")
    ds = DRAFT_RE.findall(drafts_sec)
    crits = [c.strip() for c in CRITIQUE_RE.findall(drafts_sec)]
    stats["drafts"], stats["critiques"] = len(ds), len(crits)
    if len(ds) < MIN_DRAFTS:
        fails.append(f"DRAFTS: {len(ds)} version(s), need {MIN_DRAFTS} — `### v1` … with a "
                     f"`critique:` between consecutive versions. One draft is one guess")
    thin = [c for c in crits if len(c.split()) < MIN_CRITIQUE_WORDS]
    if thin:
        fails.append(f"DRAFTS: {len(thin)} critique(s) under {MIN_CRITIQUE_WORDS} words — a critique "
                     f"names the line, beat or scene that failed and why; 'tightened it' is not one")
    generic = [c for c in crits if not re.search(r"\b(line|beat|scene|S\d|hook|CTA|open|close|word|"
                                                 r"turn|image|shot)\b", c, re.I)]
    if generic:
        fails.append(f"DRAFTS: {len(generic)} critique(s) name nothing specific — quote the line or "
                     f"number the beat that changed")
    if len(ds) >= 2 and len(crits) < len(ds) - 1:
        fails.append(f"DRAFTS: {len(ds)} versions but {len(crits)} critique(s) — every bump needs the "
                     f"reason it happened, or it is a rewrite pretending to be an iteration")

    if voiced:
        vf, _vw, vs = voice_checks(txt, cs, fields, killed_all, "full")
        fails += [f for f in vf if f.startswith("SCRIPT OPTIONS")]
        stats.update(vs)
    if tv and tv >= SCRIPT_CHECKS_FROM:
        sf, sw, ss = script_checks(job, txt)
        fails += sf; warns += sw; stats.update(ss)
    elif voiced:
        warns.append("SCRIPT: this DEVELOPMENT.md predates the 2.67 script checks (the cold read, the quoted tests, "
                     "their words in the signed file, the comedy answer). For a new job, start from `develop.py init`")

    return {"ok": not fails, "path": p, "fails": fails, "warns": warns, "stats": stats,
            "phase": phase}

# ---- FAR BETTER SCRIPTS (v2.67.0, 2026-11-14: "Start Wave 3") ---------------------------------------------
# Planned with three review rounds each by Grok 4.7 and Sonnet 5.5.
# Both cut a 1–10 scorecard gate as a diary the agent writes. What is checked instead is what a person can read beside
# each option, and what ties the signed file to the pick. Jobs whose DEVELOPMENT.md carries `develop-template: 2.67`
# or later; older files keep their checks and get one warning.
SCRIPT_CHECKS_FROM = (2, 67)
MIN_DRAFTS_267, MAX_DRAFTS_267 = 4, 6        # four writing passes, then at most two fix passes (script-craft.md §7)
KV_RE = lambda key: re.compile(r"^\s*" + key + r"\s*:\s*(.+?)\s*$", re.I | re.M)   # noqa: E731
FILE_RE, COLD_RE = KV_RE("file"), KV_RE("cold read")
HOOK_ASKS_RE, ENDING_RE, SWAP_RE, COMEDY_RE = KV_RE("hook asks"), KV_RE("ending answers"), KV_RE("cannot swap"), \
    KV_RE("comedy")
STAMP_RE = re.compile(r"^script-sha256:\s*([0-9a-f]{64})\s*$", re.M)
FUNNY_RE = re.compile(r"^\**Funny:?\**\s*:?\s*(.+)$", re.I | re.M)
# The comedy question is asked with two fixed answers (AskUserQuestion), and only the first one passes. The outcome
# is decided by the person's verified words, never by a tag the agent types (Grok, plan round 3).
COMEDY_CLEAR = "Nothing in it makes me cringe, or irritates, disgusts or embarrasses me"


def _script_rows(path: str) -> list:
    try:
        import script_score as _ss                       # stdlib-only; imported here so develop.py stays light
        return _ss.speakers_and_lines(open(path, encoding="utf-8").read())
    except (OSError, ImportError):
        return []


def spoken_lines(path: str) -> list:
    """The spoken lines of a script file in the house block format, speaker labels and directions stripped,
    normalised — read by the same parser as script_score.py."""
    return [_norm(r[2]) for r in _script_rows(path) if _norm(r[2])]


def script_body(path: str) -> list:
    """Every non-blank line INSIDE the script's blocks — headers, `carried by:`, action and speech — and nothing
    outside them (no brief, control idea or dramatic question). What a cold reader is given, and what its stamp
    hashes, so a wordless script reads and stamps like any other (Sonnet, build review 1)."""
    try:
        import script_score as _ss
        text = open(path, encoding="utf-8").read()
    except (OSError, ImportError):
        return []
    out, inb = [], False
    for raw in text.splitlines():
        if _ss.BLOCK_RE.match(raw):
            inb = True
        elif _ss.HEADER_RE.match(raw):
            inb = False
            continue
        if inb and raw.strip():
            out.append(raw.rstrip())
    return out


def script_sha(path: str) -> str:
    return hashlib.sha256("\n".join(re.sub(r"\s+", " ", l).strip() for l in script_body(path)).encode("utf-8")
                          ).hexdigest()


def _jobfile(job: str, rel: str) -> str:
    rel = (rel or "").strip().strip("`").split()[0] if (rel or "").strip() else ""
    return rel if os.path.isabs(rel) else os.path.join(job, rel)


def _funny_answer(cold_path: str):
    """The cold read's `Funny:` answer: None when there is no such line; '' when it says nothing tries to be funny
    (the whole answer is `none`, `no` or `no line tries to be funny`); otherwise the line it named."""
    try:
        fz = FUNNY_RE.search(open(cold_path, encoding="utf-8").read())
    except OSError:
        return None
    if not fz:
        return None
    ans = fz.group(1).strip().strip("*").strip()
    # a negation made only of these words ("No line is meant to be funny", "none", "Nothing here tries to be funny");
    # anything else, such as "none of the setup; the grass line is the joke", names a joke
    # ONE sentence: only spaces between the words, one closing mark, so "No. This joke is funny." is a joke (review 3)
    return "" if re.fullmatch(r"(none|no|nothing)(\s+(line|lines|one|joke|jokes|here|in|it|this|script|is|are|was|"
                              r"tries|try|trying|meant|to|be|funny|of|them|at|all))*\s*[.!]?\s*", ans, re.I) else ans


def _cold_read_problem(job: str, where: str, cold_rel: str, script_path: str) -> str:
    cp = _jobfile(job, cold_rel)
    if not cold_rel or not os.path.isfile(cp):
        return (f"{where}: no `cold read: <file>` — `develop.py cold-input <job> <script file>`, dispatch "
                f"`cine-cold-reader` on the .cold-input.md it writes, then `develop.py stamp <job> <cold-read file> "
                f"<script file>`")
    st = STAMP_RE.search(open(cp, encoding="utf-8").read())
    if not st:
        return f"{where}: {cold_rel} is not stamped — `develop.py stamp <job> {cold_rel} <script file>`"
    if script_path and st.group(1) != script_sha(script_path):
        return (f"{where}: {cold_rel} read a different version of {os.path.relpath(script_path, job)} — the "
                f"script changed since; cold-read it again")
    if _funny_answer(cp) is None:
        return (f"{where}: {cold_rel} has no `Funny:` line — the cold reader's contract is `Funny: none` or the "
                f"line it found funny")
    return ""


def _comedy_clear(answer: str) -> bool:
    return _norm(answer) == _norm(COMEDY_CLEAR)


def script_checks(job: str, txt: str) -> tuple:
    """(fails, warns, stats) for a 2.67+ DEVELOPMENT.md, full phase."""
    fails, warns, st = [], [], {}
    # --- the drafts: four writing passes, then at most two fixes; identical drafts are a copy, not a pass
    dsec = section(txt, "Drafts")
    ds = blocks(dsec, re.compile(r"^###\s*v(\d+)\b(.*)$", re.M))
    st["drafts"] = len(ds)
    if len(ds) < MIN_DRAFTS_267:
        fails.append(f"DRAFTS: {len(ds)} version(s); this template asks for the four writing passes in order "
                     f"(logic, coverage, continuity, timing: script-craft.md §7), a critique between each")
    dwaiver = WAIVER_RE.search(dsec)
    if len(ds) > MAX_DRAFTS_267 and not (dwaiver and _quotes(dwaiver.group(1), 2)):
        fails.append(f"DRAFTS: {len(ds)} versions; the four writing passes plus two fixes is six. Ship or escalate "
                     f"(script-craft.md §7), or record why more are needed in their words: "
                     f"`waiver: \"<their words>\"` under Drafts")
    bodies, files = [], {}
    for vid, _l, b in ds:
        fm = FILE_RE.search(b)
        if fm:
            fp = _jobfile(job, fm.group(1))
            if not os.path.isfile(fp):
                fails.append(f"DRAFTS: v{vid}'s file {fm.group(1)} is not on disk")
                bodies.append("")
                continue
            files[vid] = fp
            # the film: the script's blocks plus the B-roll and wardrobe sections, because a coverage or continuity
            # pass may change no spoken word (build review 1, both models), while a save-as, a rewritten brief or a
            # director's note is not a pass (reviews 2 and 3). A file with no blocks is compared whole.
            ftxt = open(fp, encoding="utf-8").read()
            film = script_body(fp) + [section(ftxt, "B-roll"), section(ftxt, "Wardrobe")]
            if not script_body(fp):
                film = [ln for ln in ftxt.splitlines() if not re.match(r"^\s*(#\s|Script v\d|_?Saved:)", ln)]
            bodies.append(re.sub(r"\s+", " ", "\n".join(film)).strip())
        else:
            bodies.append(_norm(re.sub(r"^\s*(critique|cold read|file)\s*:.*$", "", b, flags=re.I | re.M)))
    same = [f"v{ds[i][0]}→v{ds[i + 1][0]}" for i in range(len(ds) - 1) if bodies[i] and bodies[i] == bodies[i + 1]]
    if same:
        fails.append(f"DRAFTS: {', '.join(same)} are the same text — a version is a pass, not a copy")
    early = [(vid, b) for vid, _l, b in ds if vid in ("1", "2") and COLD_RE.search(b)]
    if ds and not early:
        fails.append("DRAFTS: no cold read on v1 or v2 — a wrong premise is cheapest to find there. "
                     "`develop.py cold-input`, `cine-cold-reader`, `develop.py stamp`, then `cold read: <file>` in "
                     "that draft's block")
    elif early:
        vid, b = early[0]
        prob = _cold_read_problem(job, f"DRAFTS: v{vid}", COLD_RE.search(b).group(1), files.get(vid, ""))
        if prob:
            fails.append(prob)
    # --- the options: their file, a stamped cold read, the quoted tests, the comedy answer
    opts = blocks(section(txt, "Script options"), OPTION_RE)
    pk = PICKED_RE.search(section(txt, "Script options"))
    for oid, _t, b in opts:
        where = f"SCRIPT OPTIONS: option {oid}"
        fm = FILE_RE.search(b)
        sp = _jobfile(job, fm.group(1)) if fm else ""
        if not fm or not os.path.isfile(sp):
            fails.append(f"{where} has no `file: 01-script/options/{oid}.md` holding only its script — the cold "
                         f"reader reads that file and nothing else")
            continue
        if not script_body(sp):
            fails.append(f"{where}: {fm.group(1)} has no blocks in the house format "
                         f"([HOOK …] / [SCENE n — …] / [CTA …], references/script-format.md)")
            continue
        lines = spoken_lines(sp)
        cr = COLD_RE.search(b)
        prob = _cold_read_problem(job, where, cr.group(1) if cr else "", sp)
        if prob:
            fails.append(prob)
        for rx, name in ((HOOK_ASKS_RE, "hook asks"), (ENDING_RE, "ending answers")):
            m = rx.search(b)
            if not m or PLACEHOLDER_RE.search(m.group(1)) or len(m.group(1).split()) < 3:
                fails.append(f"{where} has no `{name}:` (the spine test, scorecard dimension 11: the person reads "
                             f"the hook's question beside the ending's answer)")
        sw = SWAP_RE.search(b)
        if len(lines) < 2:
            # a wordless or one-line option: the swap test has nothing to swap; say so in a few words
            if not sw or not re.match(r"\s*n/?a\b", sw.group(1), re.I) or len(sw.group(1).split()) < 4:
                fails.append(f"{where} has fewer than two spoken lines: write `cannot swap: n/a — <why, in a few "
                             f"words>` (a wordless option is welcome: emotional-journey.md §5.2)")
        else:
            pair = [_norm(q) for q in QUOTED_RE.findall(sw.group(1))] if sw else []
            idx = [next((i for i, l in enumerate(lines) if q and (q == l or q in l)), None) for q in pair]
            if len(pair) < 2 or None in idx or abs(idx[0] - idx[1]) != 1:
                fails.append(f'{where}: `cannot swap: "<line>" / "<next line>"` must quote two ADJACENT spoken '
                             f'lines of {fm.group(1)} that break when swapped, and say why (the shuffle test, '
                             f'dimension 5)')
        cm = COMEDY_RE.search(b)
        funny = _funny_answer(_jobfile(job, cr.group(1))) if cr else None
        if not cm:
            fails.append(f'{where} has no `comedy:` line — `comedy: none`, or `comedy: asked — "<their answer>"` '
                         f'(comedy-craft.md §9, asked of the person, never "is it funny?")')
        elif cm.group(1).strip().lower().startswith("none"):
            if funny:
                fails.append(f"{where} says `comedy: none` but its cold read found a line meant to be funny "
                             f"({funny[:80]}) — ask the person the §9 question about that line and record their "
                             f"answer")
        else:
            cq = _quotes(cm.group(1), 2)
            if not cq:
                fails.append(f'{where}: `comedy: asked — "<their answer>"` needs their answer in quotation marks')
            elif not _comedy_clear(cq[0]) and pk and pk.group(1) == oid:
                fails.append(f'{where} is the picked option and their comedy answer was not "{COMEDY_CLEAR}" — '
                             f"cut or rewrite the joke and ask again (comedy-craft.md §9: a negative reaction, not "
                             f"funniness, is what hurts the brand)")
    st["options_checked"] = len(opts)
    return fails, warns, st


def signed_script_problems(job: str, artifact: str) -> tuple:
    """(problems, comedy_quotes) for `gate.py approve script` on a 2.67+ job. The signed file keeps the picked option's
    sentence of theirs among its spoken lines; with a quoted `waiver:` it need only open with the option's first
    spoken line (a change after the pick stays possible). The comedy answer is returned for the transcript check."""
    p = dev_path(job)
    try:
        txt = open(p, encoding="utf-8").read()
    except OSError:
        return [], []
    tv = template_version(txt)
    if not tv or tv < SCRIPT_CHECKS_FROM:
        return [], []
    sec = section(txt, "Script options")
    pk = PICKED_RE.search(sec)
    opts = {o[0]: o[2] for o in blocks(sec, OPTION_RE)}
    if not pk or pk.group(1) not in opts:
        return ["no `picked:` option to compare the signed script with"], []
    b = opts[pk.group(1)]
    signed = spoken_lines(artifact)
    probs = []
    waiver = WAIVER_RE.search(sec)
    tw = THEIR_WORDS_RE.search(b)
    q = _quotes(tw.group(1), 3) if tw else []
    if waiver and _quotes(waiver.group(1), 2):
        fm = FILE_RE.search(b)
        of = _jobfile(job, fm.group(1)) if fm else ""
        opt_lines = spoken_lines(of) if of and os.path.isfile(of) else []
        if not of or not os.path.isfile(of):
            probs.append(f"option {pk.group(1)}'s `file:` is missing, so the signed script cannot be tied to the pick")
        elif opt_lines and (not signed or signed[0] != opt_lines[0]):
            probs.append(f"the signed script does not open with option {pk.group(1)}'s first spoken line — sign the "
                         f"option they picked, or show them the change and record the new pick")
        elif not opt_lines and [re.sub(r"\s+", " ", l).strip() for l in script_body(artifact)] != \
                [re.sub(r"\s+", " ", l).strip() for l in script_body(of)]:
            # a wordless option has no first line to tie by: the signed blocks must be the option's (Grok, review 2)
            probs.append(f"option {pk.group(1)} has no spoken line, and the signed script's blocks are not its blocks")
    elif q and _norm(q[0]) not in " ".join(signed):
        probs.append(f'their sentence "{q[0]}" (option {pk.group(1)}) is not spoken in '
                     f'{os.path.relpath(artifact, job)}. Keep it word for word, or record why not in their words: '
                     f'`waiver: "<their words>"` under Script options')
    cm = COMEDY_RE.search(b)
    comedy = _quotes(cm.group(1), 2) if cm and not cm.group(1).strip().lower().startswith("none") else []
    return probs, comedy


def approve_script_refusals(job: str, artifact: str, quote_typed) -> list:
    """Everything `gate.py approve script` refuses on a 2.67+ job, as messages. `quote_typed(q)` says whether the
    person typed q in this session (the gate passes its transcript check). One function, so the self-test covers
    what the gate does with it."""
    probs, comedy = signed_script_problems(job, artifact)
    out = [f"the signed file is not the option they picked: {x}" for x in probs]
    for q in comedy:
        if not quote_typed(q):
            out.append(f'the comedy answer "{q}" appears in no human turn of this session. Ask them the question '
                       f"(comedy-craft.md §9) and record what they wrote")
    return out


def cmd_cold_input(a) -> int:
    """Write <script>.cold-input.md: the script's blocks only, no brief or notes — the one file a cold reader gets."""
    sp = _jobfile(a.job, a.script)
    body = script_body(sp)
    if not body:
        print(f"error: {sp} has no blocks in the house format", file=sys.stderr); return 1
    out = os.path.splitext(sp)[0] + ".cold-input.md"
    open(out, "w", encoding="utf-8").write("\n".join(body) + "\n")
    print(f"wrote {os.path.relpath(out, a.job)} ({len(body)} lines) — dispatch cine-cold-reader on this file only")
    return 0


def cmd_stamp(a) -> int:
    """Record which version of a script a cold read read: the hash of its blocks, written into the cold read."""
    cp, sp = _jobfile(a.job, a.coldread), _jobfile(a.job, a.script)
    for f in (cp, sp):
        if not os.path.isfile(f):
            print(f"error: {f} not found", file=sys.stderr); return 2
    if not script_body(sp):
        print(f"error: {sp} has no blocks in the house format", file=sys.stderr); return 1
    # the stamp says what the cold reader READ: its input file must still be this script (Sonnet, build review 2)
    ci = os.path.splitext(sp)[0] + ".cold-input.md"
    if not os.path.isfile(ci) or open(ci, encoding="utf-8").read() != "\n".join(script_body(sp)) + "\n":
        print(f"REFUSED: {os.path.relpath(ci, a.job)} is missing or is not the script as it is now — the cold reader "
              f"read something else. `develop.py cold-input {a.job} {a.script}`, cold-read it again, then stamp",
              file=sys.stderr)
        return 1
    txt = open(cp, encoding="utf-8").read()
    txt = re.sub(r"\n*^script: [^\n]*$", "", txt, flags=re.M)
    txt = STAMP_RE.sub("", txt).rstrip() + \
        f"\n\nscript: {os.path.relpath(sp, a.job)}\nscript-sha256: {script_sha(sp)}\n"
    open(cp, "w", encoding="utf-8").write(txt)
    print(f"stamped {os.path.relpath(cp, a.job)} ← {os.path.relpath(sp, a.job)} ({len(script_body(sp))} lines)")
    return 0


def cmd_options(a) -> int:
    """The option card: for each option, side by side in one print, what the person reads before picking."""
    txt = open(dev_path(a.job), encoding="utf-8").read()
    opts = blocks(section(txt, "Script options"), OPTION_RE)
    if not opts:
        print("no `## Script options` yet"); return 1
    for oid, title, b in opts:
        print(f"\n=== Option {oid} · {title}")
        for rx, name in ((FILE_RE, "file"), (THEIR_WORDS_RE, "their words"), (HOOK_ASKS_RE, "hook asks"),
                         (ENDING_RE, "ending answers"), (SWAP_RE, "cannot swap"), (COMEDY_RE, "comedy")):
            m = rx.search(b)
            print(f"  {name + ':':<16} {m.group(1) if m else '— missing'}")
        cr = COLD_RE.search(b)
        cp = _jobfile(a.job, cr.group(1)) if cr else ""
        if cp and os.path.isfile(cp):
            print("  cold read (a stranger, who saw only the script):")
            for ln in open(cp, encoding="utf-8").read().splitlines():
                if re.match(r"^\*\*(For|Who speaks|The hook asks|The ending answers|Funny)", ln):
                    print("    " + ln.replace("**", ""))
        else:
            print("  cold read:       — missing")
    pk = PICKED_RE.search(section(txt, "Script options"))
    print(f"\npicked: {pk.group(1) if pk else '— not yet'}")
    return 0



TEMPLATE = """# DEVELOPMENT — <job slug>

<!-- develop-template: 2.70 — the taste session, their material, their picture, the two script options and their checks (cold read, the quoted tests, their words, comedy), and the research ladder (tier, decision lines, what mattered, objective, keep-or-break, audience voice) are checked -->

> `scripts/develop.py check <job>` validates this file, and `gate.py approve script` refuses until
> it passes. It exists because one draft is the cheapest thing an agent produces, and every gate
> after the script validates a mediocre script perfectly executed. The craft behind each section:
> `references/preproduction-research.md` (how deep, when to stop) · `references/ideation.md` §3–§6
> (diverge, the angle grid, concept-not-idea, the kill tests) · `references/persuasion-psychology.md`
> §2 (awareness picks the hook) · `references/script-craft.md` §6 (the scorecard the drafts face).

## Taste

Before any concept, and before any research is shown: ask them, three questions at a time (they may skip any).
Write their answers in THEIR words, in quotes. Reflect back what you heard ("so: dry, not cosy?"), never rewrite
it into tidier copy (`ideation.md` §0). If they would rather not, write only `skipped: "<their words>"`.

asked: <who> · <YYYY-MM-DD>
proud: "<what would make them proud of this film, their words>"
cringe: "<what would make them cringe>"
loved: <a file, link or title> — "<what they said about it>"
loved: <another> — "<what they said>"
hated: <a file, link or title> — "<why, their words>"
never: "<what must never appear>"
for: "<who it is for, in their words>"

## Their material

Their own ideas, stories, phrases and moments, verbatim. A `[seed]` enters the concept bank as a concept of its
own (`from: their seed`), argued like the agent's. If they have none, `none: "<their words>"`.

- [seed] "<an idea of theirs>"
- [story] "<a story they told>"
- [phrase] "<a phrase they actually use>"
- [moment] <a film moment they wish they had made> — "<why>"

## Research

Pick the tier from the DECISION, not the topic (`preproduction-research.md` §2.1): how many videos does being
wrong touch, and can it be reversed after delivery? T0 is a legitimate answer and should be used often.

tier: <T0|T1|T2|T3> — <the two answers>

T0: one line, and nothing else is owed.

- T0 · <the call> · basis: <what it rests on> · raise to T1 if: <what would change it>

T1 and up: 3–8 lines (T1), each a fact that changes a decision, each with an id, a source tag and the alternative
it decides. The buyer's own words, the category's conventions, the competitor's last three films, the platform's
behaviour, the product's real constraint, the thing the client said that nobody wrote down.

- R1 [PRIMARY · <source> · <YYYY-MM-DD>] <the fact> · decides: <C2 instead of C4 / rules out …>

(One line per R: the fact and its `decides:` on the same line.)

T2+: `synthesis: <themes, contradictions kept, named sources>`. T3 adds `counter-case: <the refutation pass>`.

## Audience voice

T2 and up only. The phrases people actually use, word for word, 3–15 words each: from reviews, support or sales
text the client gave, comments, or a search query (`discovery-and-search.md` §5). Kind and source type and date;
never a customer's name. The picked hook speaks one problem or objection phrase; a result phrase is never spoken by
a presenter as their own (`compliance.md` §2).

- [problem] "<their phrase>" · <review|support|search query|comment> · <YYYY-MM-DD> · saved: <file in the job or link>
- [objection] "<their phrase>" · <source type> · <YYYY-MM-DD> · saved: <file in the job or link>

## Look

Four or more real reference pictures, ON DISK, each with a provenance sidecar — the moodboard the
concepts are designed against. Not descriptions of pictures: files. One line each, naming the
attribute it settles.

    refsource.py brief 01-script/prompts/          # once shots exist, the shopping list writes itself
    pixabay_search.py -q "<terms>" --image-type photo --download 00-brief/_look/

- [environment] 00-brief/_look/pixabay-<id>-large.jpg — <what this picture settles that words did not>
- [their environment] 00-brief/_look/<their photo or sketch> — <what they want this to settle>

At least one picture is theirs (their photo, sketch or screenshot, with a provenance sidecar). The stock pictures
map the category's clichés; theirs sets the direction.

## Concepts

Five or more, genuinely different — different dramatic question, different opening image, at least
three different structures. Vary the axes in `ideation.md` §4, not the adjectives.

### C1 · <title>
premise: <one sentence a stranger would repeat>
question: <the dramatic question the film opens — ends in a ?>
image: <the ONE opening image>
structure: <the shape: two-hander / demo / testimonial-shaped / list / single-take monologue / …>
proof: <why this is true for THIS brand and no competitor>
risk: <what kills it — cost, compliance, an asset nobody has>
from: <their seed S1 | agent>
research: <R1, R3 — the lines it rests on (T1+)>
confirms: <R2 — evidence that agreed and changed nothing, if any>
category: <the usual ad in this category> · ours: <keep|break> — <how our first three seconds differ>

### C2 · <title>
premise:
question:
image:
structure:
proof:
risk:

## Adversarial round 1 · <the hat: the skeptical buyer / the compliance officer / the competitor / the bored scroller>

killed: C<n> — <the reason it cannot survive>
weakened: C<n> — <what it now has to fix>
survived: C<n>, C<n>

## Adversarial round 2 · <a different hat, seeing round 1's survivors>

killed:
weakened:
survived:

## Choice

The agent argues; the human picks. Put the survivors in front of them side by side, in a shuffled order
with the agent's recommendation LAST, each with its trade-off named. They may pick one, combine two
("C2 + C4, with my twist"), bring their own (write it as a concept first), or pick none (back to concepts).

shown: C<n>, C<n>, C<n>
recommended: C<n>
chosen: C<n>
by: <name>
quote: "<their reply, verbatim>"
twist: "<their change, if any>"
refused: C<n> — "<why, in their words>"
why: <one line — the trade-off they accepted>
objective: <sharing|attribution|conversion> — "<what the film is for, their words>"
research that mattered: <R1, R3 — the lines THEY name, from the board showing each concept's cited lines>
deleted: <R2 — the lines nobody named, removed from Research (§7)>

## Hooks

Five or more against the CHOSEN concept. Awareness level from `persuasion-psychology.md` §2; type
from `modes/ugc-volume.md` §5. Not five of one type, and not five from the indirect half —
`hook-craft.md` §1.

The line carries **one concrete anchor and one withheld term**. The gap cell names both halves:
what they don't know, and why they already care. If the second half is hard to write, the hook is
hollow (`hook-craft.md` §2).

| ID | awareness | type | the line / beat (0:00–0:06) | the gap: they don't know X · because Y |
|----|-----------|------|------------------------------|------------------------------------------|
| H1 | <level> | <type> | <the line> | <what they don't know> · because <why they already care> |

## Drafts

Each version, then the critique that forced the next one. A critique names the line, beat or scene.

Four writing passes in order, then at most two fixes (script-craft.md §7): v1 logic, v2 coverage, v3
continuity, v4 timing, v5 lines, v6 polish. A cold read on v1 or v2 (`cine-cold-reader`, the draft's file only).

### v1 · logic
file: 01-script/SCRIPT-<slug>-v1.md
cold read: 01-script/SCRIPT-<slug>-v1.coldread.md
critique: <what failed, naming the line or beat — 15+ words>

### v2 · coverage
file: 01-script/SCRIPT-<slug>-v2.md
critique:

### v3 · continuity
file: 01-script/SCRIPT-<slug>-v3.md
critique:

### v4 · timing
file: 01-script/SCRIPT-<slug>-v4.md

## Script options

After the drafts, show them two short alternatives on the concept they picked, side by side. Each keeps
one sentence of theirs (from Taste or Their material) word for word; if they do not want that, write
`waiver: "<their words>"`.

Each option is its own file holding only its script, so the cold reader reads that and nothing else. Beside each
option the person sees: the hook's question and the ending's answer, two lines that cannot swap, the cold read,
and their answer to the comedy question if the option tries to be funny (script-craft.md §7).

### A · <one-line difference>
file: 01-script/options/A.md
their words: "<a sentence of theirs, verbatim>"
hook asks: <the question the first seconds raise>
ending answers: <what the last line or image settles>
cannot swap: "<a spoken line>" / "<the next spoken line>" — <why swapping breaks it>
cold read: 01-script/options/A.coldread.md
comedy: <none | asked — "<their answer>">  (ask with two answers: "Nothing in it makes me cringe, or irritates, disgusts or embarrasses me" / "Something does: …"; only the first passes)

### B · <one-line difference>
file: 01-script/options/B.md
their words: "<a sentence of theirs, verbatim>"
hook asks:
ending answers:
cannot swap:
cold read: 01-script/options/B.coldread.md
comedy:

picked: <A|B>
quote: "<their reply, verbatim>"
"""


def cmd_init(a) -> int:
    p = dev_path(a.job)
    if os.path.isfile(p) and not a.force:
        print(f"{os.path.relpath(p)} exists — use --force to overwrite", file=sys.stderr); return 2
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE)
    print(f"wrote {os.path.relpath(p)} — fill it, then `develop.py check {a.job}`")
    return 0


def _report(r: dict, a) -> int:
    if getattr(a, "json", False):
        print(json.dumps(r, indent=2, ensure_ascii=False)); return 0 if r["ok"] else 1
    s = r["stats"]
    print(f"DEVELOPMENT {'PASS' if r['ok'] else 'INCOMPLETE'} — {os.path.relpath(r['path'])}")
    if s.get("voice"):
        print(f"  their voice: taste {s.get('taste', '—')} · their material {s.get('their_material', 0)} · "
              f"concepts from them {s.get('concepts_from_them', 0)} · their pictures {s.get('their_pictures', '—')} · "
              f"refusals {s.get('refusals', 0)}"
              + (f" · script options {s.get('script_options', 0)}" if "script_options" in s else ""))
    print((f"  research {s['tier']} · {s.get('research_lines', 0)} line(s) · " if s.get("tier") else
           f"  research {s.get('research_sourced', 0)}/{MIN_RESEARCH} sourced · ") +
          f"look {s.get('look', 0)}/{MIN_LOOK} on disk · "
          f"concepts {s.get('concepts', 0)}/{MIN_CONCEPTS} "
          f"({s.get('distinct_structures', 0)} structures) · "
          f"rounds {s.get('rounds', 0)}/{MIN_ROUNDS} (killed {s.get('killed', 0)}/{MIN_KILLED}) · "
          f"chosen {s.get('chosen') or '—'} · hooks {s.get('hooks', 0)}/{MIN_HOOKS} · "
          f"drafts {s.get('drafts', 0)}/{MIN_DRAFTS_267 if s.get('options_checked') is not None else MIN_DRAFTS} "
          f"with {s.get('critiques', 0)} critique(s)")
    for f in r["fails"]:
        print(f"  ✗ {f}")
    for w in r["warns"]:
        print(f"  ~ {w}")
    return 0 if r["ok"] else 1


def cmd_check(a) -> int:
    return _report(check(a.job, a.min_concepts, a.phase), a)


def cmd_status(a) -> int:
    r = check(a.job, a.min_concepts, a.phase)
    order = ["TASTE", "THEIR MATERIAL", "RESEARCH", "LOOK", "CONCEPT", "ADVERSARIAL", "ROUND", "CHOICE", "HOOKS",
             "DRAFTS", "SCRIPT OPTIONS"]
    nxt = next((f for k in order for f in r["fails"] if f.startswith(k)), None)
    _report(r, a)
    print(f"  next: {nxt.split('—')[0].strip() if nxt else 'development complete — script_score.py, then gate.py approve script'}")
    return 0 if r["ok"] else 1


def selftest() -> int:
    import tempfile
    good = TEMPLATE
    # build a passing document programmatically — if the template cannot be filled to pass, the
    # thresholds are wrong, not the writer
    R = "\n".join(f"- [PRIMARY · source{i} · 2026-09-0{i%9+1}] a fact that decides something real "
                  f"about the film number {i}" for i in range(1, 8))
    Cs = []
    seeds = [("a grove at dawn", "two-hander", "Can origin be proven?"),
             ("a bottle on a steel bench", "demo", "What does grade actually mean?"),
             ("a buyer's spreadsheet", "list", "Which supplier survives an audit?"),
             ("hands sorting olives", "single-take monologue", "Who picks these?"),
             ("an empty shelf", "testimonial-shaped", "Why did the last shipment fail?")]
    for i, (img, st, q) in enumerate(seeds, 1):
        Cs.append(f"### C{i} · concept {i}\npremise: sentence {i} distinct wording here\n"
                  f"question: {q}\nimage: {img}\nstructure: {st}\n"
                  f"proof: reason {i} unique to this brand\nrisk: risk {i}\n")
    L = "\n".join(f"- [environment] 00-brief/_look/ref{i}.jpg — what picture {i} settles"
                  for i in range(1, 5))
    doc = (f"# DEVELOPMENT — fixture\n\n## Research\n{R}\n\n## Look\n{L}\n\n## Concepts\n\n" + "\n".join(Cs) +
           "\n## Adversarial round 1 · the skeptical buyer\n\nkilled: C3 — the claim needs a document nobody has\n"
           "weakened: C1 — the proof is thin\nsurvived: C1, C2, C4, C5\n\n"
           "## Adversarial round 2 · the bored scroller\n\nkilled: C5 — nothing happens in the first two seconds\n"
           "weakened: C4 — the open is a talking head\nsurvived: C1, C2, C4\n\n"
           "## Choice\n\nchosen: C2\nby: Dana\nquote: \"C2, the bench one, it is the only one we can shoot\"\n"
           "why: the only concept the assets support\n\n"
           "## Hooks\n\n| ID | awareness | type | the line / beat | the gap |\n|---|---|---|---|---|\n"
           "| H1 | problem-aware | curiosity gap | I paid £400 for the wrong grade |"
           " which grade they were sold · because they have a bottle of it at home |\n"
           "| H2 | solution-aware | skeptic | I assumed the certificate was theatre |"
           " whether the certificate means anything · because they already pay a premium for it |\n"
           "| H3 | problem-aware | demonstration | this is what nine months in steel does |"
           " what storage does to the oil · because their own bottle has been open since spring |\n"
           "| H4 | unaware | story cold open | the buyer put it back on the shelf |"
           " why a professional rejected it · because they buy this brand every fortnight |\n"
           "| H5 | most-aware | direct offer | £12 a bottle, no subscription |"
           " what the price actually is · because they have been comparing for a fortnight |\n\n"
           "## Drafts\n\n### v1\ndraft\ncritique: the hook line about origin announces the topic instead of opening a gap in the first beat\n\n"
           "### v2\ndraft\ncritique: scene two has no value turn, the buyer line lands flat and the CTA arrives before any proof\n\n"
           "### v3\nfinal\n")
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job"); os.makedirs(os.path.join(job, "00-brief"))
        look = os.path.join(job, "00-brief", "_look"); os.makedirs(look)
        for i in range(1, 5):
            open(os.path.join(look, f"ref{i}.jpg"), "wb").write(b"\xff\xd8\xff\x00")
            json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                       "clearance": "NOT CLEARED — outstanding"},
                      open(os.path.join(look, f"ref{i}.json"), "w"))
        open(dev_path(job), "w").write(doc)
        r = check(job)
        assert r["ok"], r["fails"]
        assert r["stats"]["look"] == 4, r["stats"]
        # the moodboard is FILES: a listed picture that is not on disk must FAIL
        open(dev_path(job), "w").write(doc.replace("_look/ref4.jpg", "_look/imagined.jpg"))
        rl = check(job, phase="concept")
        assert not rl["ok"] and any("not on disk" in f for f in rl["fails"]), rl["fails"]
        # a picture with no provenance sidecar must FAIL
        open(os.path.join(look, "bare.jpg"), "wb").write(b"\xff\xd8\xff\x00")
        open(dev_path(job), "w").write(doc.replace("_look/ref4.jpg", "_look/bare.jpg"))
        rp = check(job, phase="concept")
        assert not rp["ok"] and any("no provenance sidecar" in f for f in rp["fails"]), rp["fails"]
        # too few is too few, and it blocks the CONCEPT phase — before anything is written
        thinlook = doc.replace(f"## Look\n{L}", "## Look\n- [environment] 00-brief/_look/ref1.jpg — one")
        open(dev_path(job), "w").write(thinlook)
        rt = check(job, phase="concept")
        assert not rt["ok"] and any(f.startswith("LOOK: 1 sourced") for f in rt["fails"]), rt["fails"]
        open(dev_path(job), "w").write(doc)
        head = doc.split("## Hooks")[0]
        open(dev_path(job), "w").write(head)
        rc_ = check(job, phase="concept")
        assert rc_["ok"], rc_["fails"]
        assert not check(job, phase="full")["ok"]
        open(dev_path(job), "w").write(doc)
        # five rewordings of one concept must FAIL
        same = doc
        for i in (2, 3, 4, 5):
            same = same.replace(f"question: {seeds[i-1][2]}", "question: Can origin be proven?")
            same = same.replace(f"image: {seeds[i-1][0]}", "image: a grove at dawn")
        open(dev_path(job), "w").write(same)
        r2 = check(job)
        assert not r2["ok"] and any("share the same" in f for f in r2["fails"]), r2["fails"]
        # a round that kills nothing must FAIL
        nokill = doc.replace("killed: C3 — the claim needs a document nobody has\n", "").replace(
            "weakened: C1 — the proof is thin\n", "")
        open(dev_path(job), "w").write(nokill)
        r3 = check(job)
        assert any("killed nothing" in f for f in r3["fails"]), r3["fails"]
        # no human quote must FAIL
        noq = doc.replace('quote: "C2, the bench one, it is the only one we can shoot"', "quote: ok")
        open(dev_path(job), "w").write(noq)
        r4 = check(job)
        assert any("verbatim" in f for f in r4["fails"]), r4["fails"]
        # a thin critique must FAIL
        thin = doc.replace("critique: the hook line about origin announces the topic instead of opening a gap in the first beat",
                           "critique: tightened it")
        open(dev_path(job), "w").write(thin)
        r5 = check(job)
        assert any("under 15 words" in f or "name nothing specific" in f for f in r5["fails"]), r5["fails"]
        # choosing a killed concept must FAIL
        badpick = doc.replace("chosen: C2", "chosen: C3")
        open(dev_path(job), "w").write(badpick)
        r6 = check(job)
        assert any("was KILLED" in f for f in r6["fails"]), r6["fails"]

        # --- the gap column -------------------------------------------------------------------
        # a row with no gap cell at all (the old four-column bank) must FAIL, not silently pass
        old_form = doc.replace(" | which grade they were sold · because they have a bottle of it at home |", " |")
        open(dev_path(job), "w").write(old_form)
        r7 = check(job)
        assert any(f.startswith("HOOKS: no gap written for H1") for f in r7["fails"]), r7["fails"]
        # one half only — "they don't know X" with no reason to care — must FAIL
        onehalf = doc.replace("which grade they were sold · because they have a bottle of it at home",
                              "which grade they were sold")
        open(dev_path(job), "w").write(onehalf)
        r8 = check(job)
        assert any(f.startswith("HOOKS: the gap for H1") and "one half" in f for f in r8["fails"]), r8["fails"]
        # the dodge: restating the line back as the reason they care must FAIL
        echoed = doc.replace("which grade they were sold · because they have a bottle of it at home",
                             "which grade they were sold · because I paid £400 for the wrong grade")
        open(dev_path(job), "w").write(echoed)
        r9 = check(job)
        assert any("restates the line" in f for f in r9["fails"]), r9["fails"]
        # ...but a genuinely different reason with a couple of shared words must NOT fail
        open(dev_path(job), "w").write(doc)
        assert check(job)["ok"], check(job)["fails"]
        # ⛔ the "why they care" that is really the gap written twice must FAIL
        ign = doc.replace("because they have a bottle of it at home",
                          "because nobody has told them what to look for")
        open(dev_path(job), "w").write(ign)
        r9b = check(job)
        assert any("DOESN'T KNOW" in f for f in r9b["fails"]), r9b["fails"]
        for phrase in ("because they do not know what to look for",
                       "because they have never heard of it",
                       "because it is not common knowledge in the trade"):
            open(dev_path(job), "w").write(
                doc.replace("because they have a bottle of it at home", phrase))
            assert any("DOESN'T KNOW" in f for f in check(job)["fails"]), phrase
        # ...and a real stake that happens to contain the word "know" must NOT fail
        open(dev_path(job), "w").write(doc.replace(
            "because they have a bottle of it at home",
            "because they know the shop and buy there every week"))
        assert check(job)["ok"], check(job)["fails"]
        open(dev_path(job), "w").write(doc)

        # a bank drawn only from the indirect half WARNS, and does not fail
        indirect = doc.replace("| H5 | most-aware | direct offer |", "| H5 | most-aware | POV |")
        open(dev_path(job), "w").write(indirect)
        r10 = check(job)
        assert r10["ok"], r10["fails"]
        assert any("indirect half" in w for w in r10["warns"]), r10["warns"]
        # and the passing fixture, which has a direct offer, does NOT warn
        open(dev_path(job), "w").write(doc)
        assert not any("indirect half" in w for w in check(job)["warns"])

        # --- YOUR VOICE FIRST (v2.65.0) ---------------------------------------------------------------
        # an older file (no template mark) passes as before, with a warning, so jobs in flight are not blocked
        rold = check(job)
        assert rold["ok"] and any("predates the taste session" in w for w in rold["warns"]), rold
        open(os.path.join(look, "theirs.jpg"), "wb").write(b"\xff\xd8\xff\x00")
        json.dump({"source": "owner supplied", "licence": {"name": "owner"}, "clearance": "CLEARED"},
                  open(os.path.join(look, "theirs.json"), "w"))
        taste = ('## Taste\n\nasked: Dana · 2026-11-14\nproud: "people stop and say that is exactly my morning"\n'
                 'cringe: "anything cosy with a founder smiling at the camera"\n'
                 'loved: a quiet kitchen short — "nobody speaks and you still get it"\n'
                 'loved: a bench demo — "it shows the thing, it does not tell me"\n'
                 'hated: the usual grove at sunset — "every oil ad looks like a holiday"\n'
                 'never: "no slow motion pouring, ever"\nfor: "people who already buy good oil and feel fooled"\n\n'
                 '## Their material\n\n- [seed] "a buyer reads the date on the neck out loud"\n'
                 '- [phrase] "the first cup tastes like the tank"\n\n')
        voiced = doc.replace("# DEVELOPMENT — fixture\n\n", "# DEVELOPMENT — fixture\n\n<!-- develop-template: 2.65 -->\n\n" + taste)
        voiced = voiced.replace("## Look\n", "## Look\n- [their kitchen] 00-brief/_look/theirs.jpg — the light they want\n")
        voiced = voiced.replace("risk: risk 2\n", "risk: risk 2\nfrom: their seed S1\n")
        voiced = voiced.replace("chosen: C2\n", "shown: C4, C2, C1\nrecommended: C1\nchosen: C2\n")
        voiced = voiced.replace("why: the only concept the assets support\n",
                                'refused: C4 — "it is a talking head and we hate those"\nwhy: the only concept the assets support\n')
        voiced += ('\n## Script options\n\n### A · the date first\ntheir words: "the first cup tastes like the tank"\nscript A\n\n'
                   '### B · the buyer first\ntheir words: "a buyer reads the date on the neck out loud"\nscript B\n\n'
                   'picked: B\nquote: "B, because it starts with a person"\n')
        def vcheck(text, phase="full"):
            open(dev_path(job), "w").write(text)
            return check(job, phase=phase)
        rv = vcheck(voiced)
        assert rv["ok"], rv["fails"]
        assert rv["stats"]["concepts_from_them"] == 1 and rv["stats"]["refusals"] == 1, rv["stats"]
        # every rule must FAIL when its part is missing
        def fails_with(text, needle, phase="full"):
            r = vcheck(text, phase)
            assert not r["ok"] and any(needle in f for f in r["fails"]), (needle, r["fails"])
        fails_with(voiced.replace('proud: "people stop and say that is exactly my morning"', "proud: exactly my morning"),
                   "TASTE: `proud:`", "concept")
        fails_with(voiced.replace('hated: the usual grove at sunset — "every oil ad looks like a holiday"\n', ""),
                   "no hated reference", "concept")
        fails_with(voiced.replace("from: their seed S1\n", ""), "no concept says `from: their seed`", "concept")
        fails_with(voiced.replace("- [their kitchen] 00-brief/_look/theirs.jpg — the light they want\n", ""),
                   "no picture of theirs", "concept")
        fails_with(voiced.replace("shown: C4, C2, C1", "shown: C1, C4, C2"), "not last", "concept")
        fails_with(voiced.replace('refused: C4 — "it is a talking head and we hate those"\n', ""), "no refusal recorded", "concept")
        fails_with(voiced.replace("chosen: C2\n", "chosen: C2 + C3\n"), "C3 was KILLED", "concept")
        assert vcheck(voiced.replace("chosen: C2\n", "chosen: C2 + C4\n"))["ok"]          # a combination is theirs to make
        fails_with(voiced.replace('their words: "the first cup tastes like the tank"', 'their words: "the first cup is great"'),
                   "are not in Taste or Their material")
        fails_with(voiced.replace("### B · the buyer first", "B"), "SCRIPT OPTIONS: 1 shown")
        assert vcheck(voiced.replace('their words: "the first cup tastes like the tank"', 'their words: "the first cup is great"')
                      .replace("picked: B", 'waiver: "use your own words, I do not mind"\npicked: B'))["ok"]
        # a skipped session is their decision: it passes without the answers or their picture, but only in their words
        skip = voiced.split("## Taste")[0] + '## Taste\n\nskipped: "I trust you, just make it good"\n\n## Their material\n\nnone: "nothing comes to mind right now"\n\n## Research' + voiced.split("## Research", 1)[1]
        skip = skip.replace("- [their kitchen] 00-brief/_look/theirs.jpg — the light they want\n", "").replace("from: their seed S1\n", "")
        assert vcheck(skip)["ok"], vcheck(skip)["fails"]
        fails_with(skip.replace('skipped: "I trust you, just make it good"', "skipped: owner said go ahead"), "`skipped:` needs their words", "concept")
        # (v2.67.0) the script checks: four passes, an early cold read, each option's file, a stamped cold read,
        # the quoted tests, the comedy answer; and the signed file keeps their sentence
        os.makedirs(os.path.join(job, "01-script", "options"), exist_ok=True)

        def wr(rel, text):
            open(os.path.join(job, rel), "w").write(text)

        def stamp(cold, script, expect=0):
            class _A: pass
            a_ = _A(); a_.job, a_.coldread, a_.script = job, cold, script
            if expect == 0:
                assert cmd_cold_input(a_) == 0                   # what the cold reader is given, as it is now
            assert cmd_stamp(a_) == expect
        brief = "# SCRIPT\n\n## Brief\nan oil brand, the buyer is the hero\n\n## SCRIPT\n\n"
        base_s = (brief + '[HOOK 0:00–0:04]\nANA: "a buyer reads the date on the neck out loud"\n\n'
                  '[SCENE 1 — 0:04–0:12]  the press\ncarried by: object — the date on the bottle\n'
                  'ANA: "We press it the morning we pick it."\nBEN: "Then why does it taste of grass?"\n\n'
                  '[CTA 0:12–0:15]\nANA: "Read the date before you buy."\n')
        for i in range(1, 5):
            wr(f"01-script/SCRIPT-v{i}.md", base_s.replace("grass", f"grass {'and ' * i}hay"))
        cold_ok = ("**For:** oil.\n**Who speaks:** two.\n**The hook asks:** why read a date.\n"
                   "**The ending answers:** read it.\n**Funny:** no line tries to be funny\n")
        wr("01-script/SCRIPT-v1.coldread.md", cold_ok)
        stamp("01-script/SCRIPT-v1.coldread.md", "01-script/SCRIPT-v1.md")
        wr("01-script/options/A.md", base_s.replace("a buyer reads the date on the neck out loud",
                                                    "the first cup tastes like the tank"))
        wr("01-script/options/B.md", base_s)
        for o in ("A", "B"):
            wr(f"01-script/options/{o}.coldread.md", cold_ok)
            stamp(f"01-script/options/{o}.coldread.md", f"01-script/options/{o}.md")
        drafts = ("## Drafts\n\n" + "".join(
            f"### v{i}\nfile: 01-script/SCRIPT-v{i}.md\n" + ("cold read: 01-script/SCRIPT-v1.coldread.md\n" if i == 1 else "")
            + (f"critique: the scene one line about grass is flat and the buyer beat {i} has no cause yet at all\n"
               if i < 4 else "") + "\n" for i in range(1, 5)))
        def opt(o, tw):
            return (f"### {o} · option {o}\nfile: 01-script/options/{o}.md\ntheir words: \"{tw}\"\n"
                    f"hook asks: why would anyone read a date aloud\nending answers: the date is the proof of freshness\n"
                    f'cannot swap: "We press it the morning we pick it." / "Then why does it taste of grass?" — the '
                    f"question answers the claim\ncold read: 01-script/options/{o}.coldread.md\ncomedy: none\n\n")
        options = ("## Script options\n\n" + opt("A", "the first cup tastes like the tank")
                   + opt("B", "a buyer reads the date on the neck out loud") + 'picked: B\nquote: "B, because it starts with a person"\n')
        v267 = voiced.replace("<!-- develop-template: 2.65 -->", "<!-- develop-template: 2.67 -->")
        v267 = v267.split("## Drafts")[0] + drafts + options
        r67 = vcheck(v267)
        assert r67["ok"], r67["fails"]
        # the cold reader's input carries the script's blocks and nothing of the brief
        class _C: pass
        wr("01-script/options/B-notes.md", base_s + "\n## Director's note\nthe client finds the grass line hilarious\n")
        c_ = _C(); c_.job, c_.script = job, "01-script/options/B-notes.md"
        assert cmd_cold_input(c_) == 0
        ci = open(os.path.join(job, "01-script/options/B-notes.cold-input.md")).read()
        assert "[HOOK" in ci and "carried by:" in ci and "Brief" not in ci and "oil brand" not in ci, ci
        assert "hilarious" not in ci and "Director" not in ci, ci       # nothing after the blocks either
        # re-stamping replaces the stamp instead of piling them up
        stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
        # a script edited after its cold input was made cannot be stamped as read
        wr("01-script/options/B.md", base_s.replace("Read the date", "Read the neck"))
        stamp("01-script/options/B.coldread.md", "01-script/options/B.md", expect=1)
        wr("01-script/options/B.md", base_s)
        stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
        _cr = open(os.path.join(job, "01-script/options/B.coldread.md")).read()
        assert _cr.count("script-sha256:") == 1 and _cr.count("\nscript: ") == 1, _cr
        # drafts: the count, a seventh with and without their words, copies, missing files, the early cold read
        fails_with(v267.replace("### v4\nfile: 01-script/SCRIPT-v4.md\n", ""), "four writing passes")
        more = v267.replace("## Script options", "".join(f"### v{i}\nfile: 01-script/SCRIPT-v{i - 4}.md\ncritique: the "
                                                         f"scene one line about grass is still flat in beat {i} and needs a cause\n\n"
                                                         for i in (5, 6, 7)) + "## Script options")
        fails_with(more, "the four writing passes plus two fixes is six")
        rw = vcheck(more.replace("### v5", 'waiver: "keep going, we need the second scene right"\n\n### v5'))
        assert rw["ok"], rw["fails"]                               # a seventh draft, with their words for why
        wr("01-script/SCRIPT-v4.md", open(os.path.join(job, "01-script/SCRIPT-v3.md")).read())
        fails_with(v267, "v3→v4 are the same text")
        wr("01-script/SCRIPT-v4.md", open(os.path.join(job, "01-script/SCRIPT-v3.md")).read()
           .replace("carried by: object — the date on the bottle", "carried by: face — her doubt"))
        assert vcheck(v267)["ok"]                                  # a pass that changes no spoken word is a pass
        wr("01-script/SCRIPT-v4.md", "# SCRIPT v4\nScript v0.4 · 30 s\n" + open(os.path.join(job, "01-script/SCRIPT-v3.md")).read()
           + "\n_Saved: 01-script/SCRIPT-v4.md_\n")
        wr("01-script/SCRIPT-v3.md", "# SCRIPT v3\nScript v0.3 · 30 s\n" + open(os.path.join(job, "01-script/SCRIPT-v3.md")).read()
           + "\n_Saved: 01-script/SCRIPT-v3.md_\n")
        fails_with(v267, "v3→v4 are the same text")                # a save-as is not a pass
        wr("01-script/SCRIPT-v4.md", open(os.path.join(job, "01-script/SCRIPT-v3.md")).read()
           .replace("an oil brand, the buyer is the hero", "an oil brand; the buyer is the hero, the date is proof")
           + "\n## Director's note\nslower on the pour\n")
        fails_with(v267, "v3→v4 are the same text")                # a new brief or note is the same film
        wr("01-script/SCRIPT-v3.md", base_s.replace("grass", "grass and and and hay"))
        wr("01-script/SCRIPT-v4.md", base_s.replace("grass", "grass and and and and hay"))
        fails_with(v267.replace("file: 01-script/SCRIPT-v3.md", "file: 01-script/NOPE.md"), "is not on disk")
        fails_with(v267.replace("cold read: 01-script/SCRIPT-v1.coldread.md\n", ""), "no cold read on v1 or v2")
        fails_with(v267.replace("cold read: 01-script/SCRIPT-v1.coldread.md\n", "").replace(
            "### v4\nfile: 01-script/SCRIPT-v4.md\n", "### v4\nfile: 01-script/SCRIPT-v4.md\ncold read: 01-script/SCRIPT-v1.coldread.md\n"),
            "no cold read on v1 or v2")                            # a cold read on v4 is not an early one
        wr("01-script/SCRIPT-v1.md", base_s.replace("grass", "grass and hay and straw"))
        fails_with(v267, "DRAFTS: v1: 01-script/SCRIPT-v1.coldread.md read a different version")
        wr("01-script/SCRIPT-v1.md", base_s.replace("grass", "grass and hay"))
        # options
        fails_with(v267.replace("file: 01-script/options/A.md\n", ""), "option A has no `file:")
        fails_with(v267.replace("hook asks: why would anyone read a date aloud\n", "", 1), "no `hook asks:`")
        fails_with(v267.replace('"We press it the morning we pick it." / "Then why does it taste of grass?"',
                                '"the first cup tastes like the tank" / "Then why does it taste of grass?"', 1),
                   "two ADJACENT spoken lines")                     # both are A's lines, two apart
        fails_with(v267.replace('"We press it the morning we pick it." / "Then why does it taste of grass?"',
                                '"a buyer reads the date on the neck out loud" / "We press it the morning we pick it."', 1),
                   "two ADJACENT spoken lines")                     # adjacent, but B's line, not A's
        fails_with(v267.replace("comedy: none\n", "", 1), "no `comedy:` line")
        wr("01-script/options/B.md", base_s.replace("Read the date", "Read the label"))
        fails_with(v267, "read a different version")                      # the option changed after its cold read
        wr("01-script/options/B.md", base_s)
        # a wordless option is welcome: no spoken line to swap, said in a few words
        wordless = (brief + "[HOOK 0:00–0:04]  a bottle on a bench\ncarried by: object — the date on the neck\n\n"
                    "[CTA 0:04–0:08]  the logo on the cork\ncarried by: object\n")
        wr("01-script/options/A.md", wordless)
        stamp("01-script/options/A.coldread.md", "01-script/options/A.md")
        wl = v267.replace('cannot swap: "We press it the morning we pick it." / "Then why does it taste of grass?" — the '
                          'question answers the claim\ncold read: 01-script/options/A',
                          "cannot swap: n/a — no one speaks, the bottle carries it\ncold read: 01-script/options/A", 1)
        assert vcheck(wl)["ok"], vcheck(wl)["fails"]
        fails_with(v267, "fewer than two spoken lines")            # a wordless option still needs its n/a said
        wr("01-script/options/A.md", base_s.replace("a buyer reads the date on the neck out loud",
                                                    "the first cup tastes like the tank"))
        stamp("01-script/options/A.coldread.md", "01-script/options/A.md")
        # the cold read's Funny line: required, and only a whole negation means nothing tries to be funny
        for funny, needle in (("", "has no `Funny:` line"),
                              ("**Funny:** none of the setup; the grass line is the joke", "found a line meant to be funny"),
                              ("**Funny:** the grass line is the joke", "found a line meant to be funny")):
            wr("01-script/options/B.coldread.md", cold_ok.replace("**Funny:** no line tries to be funny\n", funny + "\n"))
            stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
            fails_with(v267, needle)
        wr("01-script/options/B.coldread.md", cold_ok.replace("**Funny:** no line tries to be funny", "**Funny:** No."))
        stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
        assert vcheck(v267)["ok"]                                  # "No." is a whole negation
        wr("01-script/options/B.coldread.md", cold_ok.replace("no line tries to be funny", "No. This joke is funny."))
        stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
        fails_with(v267, "found a line meant to be funny")          # a second sentence after "No." names a joke
        for neg in ("No line is meant to be funny.", "Nothing here tries to be funny", "none", "No."):
            wr("01-script/options/B.coldread.md", cold_ok.replace("no line tries to be funny", neg))
            stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
            assert vcheck(v267)["ok"], (neg, vcheck(v267)["fails"])
        wr("01-script/options/B.coldread.md", cold_ok.replace("**Funny:** no line tries to be funny",
                                                              "**Funny:** the grass line is the joke"))
        stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
        flagged = v267.replace('comedy: none\n\npicked', 'comedy: asked — "Something does: the grass line"\n\npicked')
        fails_with(flagged, "their comedy answer was not")
        fails_with(v267.replace('comedy: none\n\npicked', f'comedy: asked — "{COMEDY_CLEAR}, but the grass line irritates me"\n\npicked'),
                   "their comedy answer was not")                  # the clear sentence, then a complaint, is not clear
        cleared = v267.replace('comedy: none\n\npicked', f'comedy: asked — "{COMEDY_CLEAR}"\n\npicked')
        assert vcheck(cleared)["ok"], vcheck(cleared)["fails"]
        # the signed file: their sentence must be SPOKEN in it; the comedy answer goes to the gate
        open(dev_path(job), "w").write(cleared)
        wr("01-script/SIGNED.md", base_s)
        pr, cq = signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))
        assert pr == [] and cq == [COMEDY_CLEAR], (pr, cq)
        typed = {COMEDY_CLEAR}
        assert approve_script_refusals(job, os.path.join(job, "01-script/SIGNED.md"), lambda q: q in typed) == []
        r_ = approve_script_refusals(job, os.path.join(job, "01-script/SIGNED.md"), lambda q: False)
        assert len(r_) == 1 and "appears in no human turn" in r_[0], r_
        wr("01-script/SIGNED.md", "# notes\nthey said: a buyer reads the date on the neck out loud\n\n"
           + base_s.replace("ANA: \"a buyer reads the date on the neck out loud\"", "ANA: \"the date is on the neck\""))
        pr, _ = signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))
        assert pr and "is not spoken in" in pr[0], pr                     # in the notes is not in the script
        r_ = approve_script_refusals(job, os.path.join(job, "01-script/SIGNED.md"), lambda q: True)
        assert r_ and "not the option they picked" in r_[0], r_
        wr("01-script/SIGNED.md", base_s.replace('"a buyer reads the date on the neck out loud"',
                                                 '"a buyer reads the date\nANA: on the neck out loud"'))
        assert signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))[0] == []   # split over two breaths
        # with a quoted waiver, the signed file opens with the option's first spoken line; later lines may change,
        # and the waiver counts even while their words are still listed (Grok, build review 1)
        waived = cleared.replace("picked: B", 'waiver: "change that sentence, I do not mind"\npicked: B')
        open(dev_path(job), "w").write(waived)
        wr("01-script/SIGNED.md", base_s.replace("Read the date", "Smell it").replace(
            '"We press it the morning we pick it."', '"We press it at dawn."'))
        assert signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))[0] == []
        wr("01-script/SIGNED.md", base_s.replace("a buyer reads the date on the neck out loud", "the tank tastes first"))
        pr, _ = signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))
        assert pr and "does not open with option B's first spoken line" in pr[0], pr
        # a waiver on a wordless option: the signed blocks must be its blocks; a missing option file refuses
        keep_b = open(os.path.join(job, "01-script/options/B.md")).read()
        wr("01-script/options/B.md", wordless)
        wr("01-script/SIGNED.md", wordless)
        assert signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))[0] == []
        wr("01-script/SIGNED.md", base_s.replace("a buyer reads the date on the neck out loud", "the tank tastes first"))
        pr, _ = signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))
        assert pr and "has no spoken line" in pr[0], pr
        os.remove(os.path.join(job, "01-script/options/B.md"))
        pr, _ = signed_script_problems(job, os.path.join(job, "01-script/SIGNED.md"))
        assert pr and "`file:` is missing" in pr[0], pr
        wr("01-script/options/B.md", keep_b)
        # the comedy sentence is spelled once, here; the template and the docs must carry it exactly
        assert COMEDY_CLEAR in TEMPLATE
        for ref in ("script-craft.md", "comedy-craft.md"):
            assert COMEDY_CLEAR in open(os.path.join(os.path.dirname(HERE), "references", ref), encoding="utf-8").read(), ref
        # older templates: a 2.66 mark keeps every 2.65 check and only warns about the script checks
        r66 = vcheck(voiced.replace("<!-- develop-template: 2.65 -->", "<!-- develop-template: 2.66 -->"))
        assert r66["ok"] and r66["stats"].get("voice") and any("predates the 2.67" in w for w in r66["warns"]), r66
        fails_with(voiced.replace("<!-- develop-template: 2.65 -->", "<!-- develop-template: 2.66 -->")
                   .replace("### B · the buyer first", "B"), "SCRIPT OPTIONS: 1 shown")
        # (v2.69.0) research that changes decisions: the tier, decision lines, citations, what the PERSON named,
        # the objective, keep-or-break per concept, and at T2+ one real audience phrase in the picked hook
        wr("01-script/options/B.md", keep_b)                     # back to the plain option and its fresh cold read
        wr("01-script/options/B.coldread.md", cold_ok)
        stamp("01-script/options/B.coldread.md", "01-script/options/B.md")
        r269 = ("tier: T2 — a series of six touches this; reversible but costly\n\n"
                "- R1 [PRIMARY · the client's returns log · 2026-11-10] buyers return bottles for a grassy taste · "
                "decides: C2 instead of C1, the taste is the fear\n"
                "- R2 [SECONDARY · a category review · 2026-11-09] every rival opens on a grove · decides: rules out "
                "C1's grove opening\n"
                "- R3 [PRIMARY · search queries · 2026-11-12] people search the harvest date · decides: the date "
                "rather than the region\n"
                "- R4 [TERTIARY · a blog · 2026-11-01] oil is healthy · decides: nothing new, confirms the brief\n\n"
                "synthesis: buyers fear a stale or grassy bottle and look for a date; rivals sell the grove, so the "
                "date on the bench is unclaimed ground (R1, R2, R3)\n")
        voice_ = ('## Audience voice\n\n- [objection] "press it the morning we pick it" · review · 2026-11-10\n'
                  '- [result] "my salad finally tastes of something" · review · 2026-11-10\n\n')
        v269 = v267.replace("<!-- develop-template: 2.67 -->", "<!-- develop-template: 2.69 -->").replace(R, r269)
        v269 = v269.replace("## Look\n", voice_ + "## Look\n", 1)
        for i in range(1, 6):
            v269 = v269.replace(f"risk: risk {i}\n", f"risk: risk {i}\nresearch: {'R1, R2' if i == 2 else 'R1'}\n"
                                f"{'confirms: R4' + chr(10) if i == 3 else ''}"
                                f"category: the grove at sunset ad · ours: break — we open on a bench, never a grove\n")
        v269 = v269.replace("killed: C5 — nothing happens in the first two seconds",
                            "killed: C5 — nothing happens in the first two seconds, and people look for the date (R3)")
        v269 = v269.replace("why: the only concept the assets support\n",
                            'why: the only concept the assets support\nobjective: conversion — "we need the bottle '
                            'bought this month"\nresearch that mattered: R1, R2, R3\ndeleted: R4\n')
        v269 = v269.replace("- R4 [TERTIARY · a blog · 2026-11-01] oil is healthy · decides: nothing new, confirms the brief\n", "")
        r69 = vcheck(v269)
        assert r69["ok"], r69["fails"]
        assert r69["stats"]["tier"] == "T2" and r69["stats"]["objective"] == "conversion" \
            and r69["stats"]["audience_phrases"] == 2, r69["stats"]
        assert vcheck(v269, "concept")["ok"], vcheck(v269, "concept")["fails"]
        # (v2.70.0) each audience phrase names where it was saved: a warning on a 2.69 file, required from 2.70
        assert any("has no `saved:" in w for w in vcheck(v269, "concept")["warns"])
        v270 = v269.replace("<!-- develop-template: 2.69 -->", "<!-- develop-template: 2.70 -->")
        fails_with(v270, "has no `saved:", "concept")
        wr("00-brief/review-12.png", "x")
        v270s = v270.replace("· review · 2026-11-10\n- [result]", "· review · 2026-11-10 · saved: 00-brief/review-12.png\n- [result]") \
                    .replace('tastes of something" · review · 2026-11-10', 'tastes of something" · review · 2026-11-10 · saved: https://example.org/r/9')
        assert vcheck(v270s, "concept")["ok"], vcheck(v270s, "concept")["fails"]
        assert any("saved only as a link" in w for w in vcheck(v270s, "concept")["warns"])    # a link warns
        fails_with(v270s.replace("saved: 00-brief/review-12.png", "saved: 00-brief/nope.png"), "has no `saved:", "concept")
        cp = "concept"
        fails_with(v269.replace("tier: T2", "level: T2"), "no `tier:", cp)
        fails_with(v269.replace(" · decides: rules out C1's grove opening", ""), "RESEARCH R2: no `decides:`", cp)
        assert any("names no alternative" in w for w in vcheck(v269.replace(
            "decides: rules out C1's grove opening", "decides: the opening shot"), cp)["warns"])
        fails_with(v269.replace("- R3 [PRIMARY", "- [PRIMARY"), "has no id", cp)
        fails_with(v269.replace("[PRIMARY · search queries · 2026-11-12]", "[search queries]"), "R3: no `[PRIMARY", cp)
        fails_with(v269.replace("research that mattered: R1, R2, R3", "research that mattered: R1, R2"),
                   "RESEARCH R3: the person did not name it", cp)
        fails_with(v269.replace("research that mattered: R1, R2, R3\n", ""), "no `research that mattered:", cp)
        fails_with(v269.replace("research that mattered: R1, R2, R3", "research that mattered: R1, R2, R3, R7"),
                   "R7 is named as mattering", cp)
        fails_with(v269.replace("deleted: R4\n", ""), "cites R4, which is not a research line", cp)
        fails_with(v269.replace("category: the grove at sunset ad · ours: break — we open on a bench, never a grove\n",
                                "", 1), "CONCEPT C1: no keep-or-break line", cp)
        fails_with(v269.replace("ours: break — we open", "ours: maybe — we open", 1), "CONCEPT C1: no keep-or-break", cp)
        fails_with(v269.replace("ours: break — we open on a bench, never a grove", "ours: break — a bench", 1),
                   "CONCEPT C1: no keep-or-break", cp)                    # how the first seconds differ, said
        fails_with(v269.replace("objective: conversion", "objective: recall"), "no `objective:", cp)
        fails_with(v269.replace('objective: conversion — "we need the bottle bought this month"',
                                "objective: conversion"), "no `objective:", cp)
        fails_with(v269.replace("synthesis: buyers fear", "notes: buyers fear"), "needs `synthesis:`", cp)
        fails_with(v269.replace("tier: T2", "tier: T3"), "needs `counter-case:`", cp)
        assert vcheck(v269.replace("tier: T2", "tier: T3").replace(
            "synthesis: buyers", "counter-case: the region may sell better than the date, per the 2025 panel\n"
            "synthesis: buyers"))["ok"]
        fails_with(v269.replace(voice_, "## Audience voice\n\n"), "AUDIENCE VOICE: none", cp)
        fails_with(v269.replace("[objection]", "[other]"), "no problem or objection phrase", cp)
        fails_with(v269.replace('"press it the morning we pick it"', '"the morning"'), "3–15 words", cp)
        fails_with(v269.replace('" · review · 2026-11-10\n- [result]', '"\n- [result]'), "3–15 words", cp)
        fails_with(v269.replace('" · review · 2026-11-10\n- [result]', '" · review\n- [result]'), "3–15 words", cp)
        fails_with(v269.replace('"press it the morning we pick it"', '"why does it taste of grass"'),
                   "carries none of the problem or objection phrases")    # the third spoken line is not the hook
        fails_with(v269.replace('"press it the morning we pick it"', '"the label hides the harvest date"'),
                   "carries none of the problem or objection phrases")
        wr("01-script/options/B.md", keep_b.replace('Read the date before you buy.', 'My salad finally tastes of something.'))
        fails_with(v269, "is spoken or shown in the script")
        wr("01-script/options/B.md", keep_b)
        # T0: one line, and the rest is not owed; T0 without its basis fails; at T1 two lines are too few
        kept_ = r269.replace("- R4 [TERTIARY · a blog · 2026-11-01] oil is healthy · decides: nothing new, confirms the brief\n", "")
        assert kept_ in v269
        t0 = v269.replace(kept_, "tier: T0 — one video, a two-way door\n\n- T0 · open on the bench · basis: the client's "
                          "returns log says enough · raise to T1 if: the series is commissioned\n")
        t0 = t0.replace(voice_, "").replace("research that mattered: R1, R2, R3\n", "").replace("deleted: R4\n", "")
        for c_ in ("research: R1, R2\n", "research: R1\n", "confirms: R4\n", " (R3)"):
            t0 = t0.replace(c_, "")
        assert vcheck(t0)["ok"], vcheck(t0)["fails"]
        fails_with(t0.replace(" · basis: the client's returns log says enough", ""), "T0 needs its one line", cp)
        r3_ = ("- R3 [PRIMARY · search queries · 2026-11-12] people search the harvest date · decides: the date rather "
               "than the region\n")
        fails_with(v269.replace("tier: T2", "tier: T1").replace(r3_, "").replace("research that mattered: R1, R2, R3",
                   "research that mattered: R1, R2").replace(" (R3)", "").replace("deleted: R4\n", "")
                   .replace("confirms: R4\n", ""), "T1 with 2 line(s) researched, need 3", cp)
        # (build review 1, Sonnet) naming two of three lines and deleting the third is the honest path, not a deadlock
        t1ok = v269.replace("tier: T2", "tier: T1").replace(r3_, "").replace(
            "research that mattered: R1, R2, R3", "research that mattered: R1, R2").replace("deleted: R4", "deleted: R3, R4")
        assert vcheck(t1ok, cp)["ok"], vcheck(t1ok, cp)["fails"]
        # ...and "none of it mattered", every line deleted, passes with a note that the call ran as T0
        nn_ = v269
        for line_ in [l_ for l_ in kept_.splitlines() if l_.startswith("- R")]:
            nn_ = nn_.replace(line_ + "\n", "")
        nn_ = nn_.replace("research that mattered: R1, R2, R3", 'research that mattered: none — "we knew all of it already"'
                          ).replace("deleted: R4", "deleted: R1, R2, R3, R4")
        rn_ = vcheck(nn_, cp)
        assert rn_["ok"] and any("ran as T0" in w for w in rn_["warns"]), rn_
        fails_with(v269.replace("research that mattered: R1, R2, R3", "research that mattered: <R1, R3 — the lines THEY name>"),
                   "still the template's placeholder", cp)
        fails_with(v269.replace("deleted: R4", "deleted: <R2 — the lines nobody named>"), "still the template's placeholder", cp)
        fails_with(t0.replace("raise to T1 if: the series is commissioned\n", "raise to T1 if: the series is commissioned\n"
                              "- R1 [PRIMARY · <source> · <YYYY-MM-DD>] <the fact> · decides: <C2 instead of C4>\n"),
                   "tier T0 but 1 research line", cp)
        fails_with(v269.replace("- R2 [SECONDARY", "- R1 [SECONDARY"), "used twice", cp)
        fails_with(v269.replace("research: R1, R2\n", "research: R1\n"), "RESEARCH R2: named as mattering but neither", cp)
        # (build review 1, Grok) a citation on a concept that was killed for other reasons is not where it landed
        gam_ = v269.replace("research: R1, R2\n", "").replace("risk: risk 5\nresearch: R1\n", "risk: risk 5\nresearch: R1, R2, R3\n")
        gam_ = gam_.replace(", and people look for the date (R3)", "")
        fails_with(gam_, "named as mattering but neither the chosen concept cites it", cp)
        assert not any("R3" in w for w in vcheck(v269, cp)["warns"])          # "rather than" names an alternative
        r_lone = vcheck(v269.replace("decides: rules out C1's grove opening", "decides: C1"), cp)
        assert r_lone["ok"] and not any("R2" in w for w in r_lone["warns"]), r_lone   # a lone concept id is one
        fails_with(v269.replace("decides: rules out C1's grove opening", "decides: grove"), "RESEARCH R2: no `decides:`", cp)
        r4_ = "- R4 [TERTIARY · a blog · 2026-11-01] oil is healthy · decides: nothing new instead of C1\n"
        fails_with(v269.replace(kept_, kept_.replace("\nsynthesis:", "\n" + r4_.rstrip("\n") + "\nsynthesis:", 1))
                   .replace("deleted: R4\n", ""), "RESEARCH R4: the person did not name it", cp)   # confirms keeps nothing
        fails_with(v269.replace("synthesis: buyers fear a stale or grassy bottle and look for a date; rivals sell the "
                                "grove, so the date on the bench is unclaimed ground (R1, R2, R3)", "synthesis: dates matter"),
                   "needs `synthesis:`", cp)
        fails_with(v269.replace("tier: T2", "tier: T3").replace("synthesis: buyers", "counter-case: region sells\nsynthesis: buyers"),
                   "needs `counter-case:`", cp)
        assert any("names no alternative" in w for w in vcheck(v269.replace(
            "decides: rules out C1's grove opening", "decides: tone not shape"), cp)["warns"])     # "not" is no alternative
        fails_with(v269.replace("file: 01-script/options/B.md", "file: 01-script/options/NOPE.md"), "no readable `file:`")
        wr("01-script/options/B.md", wordless)
        fails_with(v269, "on-screen TEXT cards (it has no spoken line)")   # a silent film: the phrase may sit on screen
        fails_with(v269.replace('"press it the morning we pick it"', '"the date on the neck"'), "carries none")  # a direction is not on screen
        wr("01-script/options/B.md", wordless.replace("carried by: object — the date on the neck\n",
                                                      'carried by: object — the date on the neck\nTEXT: "Read the date on the neck"\n'))
        rs_ = vcheck(v269.replace('"press it the morning we pick it"', '"the date on the neck"'))
        assert not any("AUDIENCE VOICE" in f for f in rs_["fails"]), rs_["fails"]    # ...a TEXT card counts
        wr("01-script/options/B.md", wordless.replace("carried by: object — the date on the neck\n",
                                                      'carried by: object\nTEXT: "My salad finally tastes of something"\n'))
        fails_with(v269, "is spoken or shown in the script")                 # a result phrase on screen is still a claim
        wr("01-script/options/B.md", wordless.replace("carried by: object\n", 'carried by: object\nTEXT: "Read the date on the neck"\n'))
        fails_with(v269.replace('"press it the morning we pick it"', '"the date on the neck"'), "carries none")  # a CTA card is not the hook
        wr("01-script/options/B.md", keep_b)
        fails_with(t0.replace("risk: risk 1\n", "risk: risk 1\nresearch: R1\n").replace(
            "why: the only concept the assets support\n", "why: the only concept the assets support\ndeleted: R1\n"),
            "tier T0 but a concept cites R1", cp)                              # T0: nothing rests on an id, deleted or not
        # (build review 3, Sonnet) a fresh template's placeholder citations, left in an honest T0 file, cite nothing
        assert vcheck(t0.replace("risk: risk 1\n", "risk: risk 1\nresearch: <R1, R3 — the lines it rests on (T1+)>\n"
                                 "confirms: <R2 — evidence that agreed and changed nothing, if any>\n"), cp)["ok"]
        # (build review 2, Sonnet) deleted ids nobody ever cited do not count toward the floor
        fails_with(t0.replace("tier: T0 — one video, a two-way door", "tier: T1 — one video").replace(
            '- T0 · open on the bench · basis: the client\'s returns log says enough · raise to T1 if: the series is '
            'commissioned\n', "").replace("why: the only concept the assets support\n", 'why: the only concept the assets '
            'support\nresearch that mattered: none — "we knew it"\ndeleted: R1, R2, R3\n'), "researched, need 3", cp)
        wr("01-script/options/B.md", keep_b)
        # a 2.67 file keeps the six-line floor and warns about the ladder
        r67b = vcheck(v267)
        assert r67b["ok"] and any("predates the research ladder" in w for w in r67b["warns"]), r67b
        fails_with(v267.replace(R, "\n".join(R.splitlines()[:5])), "RESEARCH: 5 sourced line(s), need 6", cp)
        open(dev_path(job), "w").write(doc)
        # the template itself carries the mark, so every new job gets these checks
        assert template_version(TEMPLATE) == TEMPLATE_VERSION and "## Taste" in TEMPLATE and "## Script options" in TEMPLATE
    print("selftest OK — phase concept passes before hooks/drafts exist; a filled doc passes full; "
          "a moodboard entry that is not on disk, one with no provenance and a thin board all fail; "
          "rewordings, a kill-free round, a bare 'ok', a thin critique and picking a killed concept "
          "all fail; a hook with no gap, a gap with one half, and a 'why they care' that restates "
          "the line all fail, as does a 'why they care' that is really the viewer's "
          "ignorance restated; an all-indirect bank warns without failing; (v2.65.0) the taste session, their "
          "material, their picture, the shown order, a refusal, combined picks and two script options carrying "
          "their words are each enforced on the new template, a skip in their words passes, and an older file warns; "
          "(v2.67.0) four passes, an early cold read, each option's file with a stamped cold read, the hook's "
          "question and the ending's answer, two adjacent lines that cannot swap and the comedy answer are each "
          "enforced, the signed file must speak their sentence, and a 2.66 file keeps its 2.65 checks; (v2.69.0) the research tier, "
          "lines that name what they decide, the lines the person named (the rest deleted), the objective in their "
          "words, keep-or-break per concept and, at T2+, an audience phrase in the picked hook (never a result "
          "phrase spoken) are each enforced, T0 passes on one line, and a 2.67 file keeps the six-line floor")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    st_ = sub.add_parser("stamp", help="(v2.67.0) record which version of a script a cold read read")
    st_.add_argument("job"); st_.add_argument("coldread"); st_.add_argument("script")
    ci_ = sub.add_parser("cold-input", help="(v2.67.0) the script's blocks only, the one file a cold reader gets")
    ci_.add_argument("job"); ci_.add_argument("script")
    op_ = sub.add_parser("options", help="(v2.67.0) the option card the person reads before picking")
    op_.add_argument("job")
    for name in ("init", "check", "status"):
        s = sub.add_parser(name); s.add_argument("job")
        s.add_argument("--min-concepts", type=int, default=MIN_CONCEPTS)
        if name == "init":
            s.add_argument("--force", action="store_true")
        else:
            s.add_argument("--json", action="store_true")
            s.add_argument("--phase", choices=["concept", "full"], default="full",
                           help="concept = research→concepts→adversarial→choice (before the pick); "
                                "full adds hooks and drafts (before the script is approved)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    return {"init": cmd_init, "check": cmd_check, "status": cmd_status, "stamp": cmd_stamp, "cold-input": cmd_cold_input,
            "options": cmd_options}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
