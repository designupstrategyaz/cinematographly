#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""skill_audit.py — the skill's own routing gate: do the cross-references resolve, is anything orphaned,
and what does each file cost to load.

The scripts have run_tests.py. The PROSE had nothing. This skill routes by a table citing dozens
of reference files (this audit prints the count; it is never written here), and those files cite each
other's section numbers constantly — a link rot surface
with no check on it. A skill that grows faster than its routing gets slower to use; this measures both
halves of that.

  audit  — run every check below (default command)

Checks
------
  1. PATHS. Every `references/x.md`, `scripts/x.py`, `modes/x.md`, `clients/x.md`, `assets/x` cited
     anywhere in the skill's markdown resolves on disk.
  2. ORPHANS. Every file in references/ is listed in references/_INDEX.md, and every file _INDEX.md
     lists exists. An unrouted reference is a file nobody will ever open.
  3. CLASSIFICATION. Every reference carries a core / extended / never-loaded class in _INDEX.md.
  4. ROUTER. Every reference reachable from SKILL.md's router table or from _INDEX.md.
  5. SECTIONS. A citation of the form `file.md` section N is checked against that file's section
     ids — markdown headings, the `**N.M —**` bold inline sub-heads this skill uses heavily, and
     lettered blocks (`section 6A` = block A under section 6). Informational by default;
     --strict-sections makes them findings.
  6. PACKAGING LIMITS. The two length caps the plugin installer enforces, which nothing else here
     was checking (and which failed a real install on 2026-08-30): SKILL.md frontmatter
     `description` <= 1024 chars, `.claude-plugin/plugin.json` `description` <= 500, and NO XML
     TAGS in either description (`clients/<brand>.md` reads as a tag and is rejected). Also that
     the manifest is valid JSON with a kebab-case `name`. Each of these three rules was learned the
     same way: an install was refused. Anything the installer refuses belongs here, not in a habit.
     The description is read in BOTH forms it is written in: folded (`description: >-`, the source
     repo) and one line, quoted or plain (what the build writes into an installed copy).
  7. RATE RESTATEMENT. A generation rate written anywhere except assets/higgsfield-rates.json is a
     copy that goes stale silently — charter rule 5. Any "cr/s" outside the rate asset, rate_card.py
     and refresh_costs.md is reported.
  8. BUDGET. Per-file size and an approximate token cost, with the core total against a ceiling.
     The estimate is chars/4 — stdlib only, no tiktoken. It is an ESTIMATE, not a measurement.
  9. HOOKS (2026-09-06). `hooks/hooks.json` at the plugin root parses, every hook entry has a
     matcher (PreToolUse) and a command, and every `${CLAUDE_PLUGIN_ROOT}/...` path in a command
     resolves to a file on disk. A hook that points at nothing is a gate that silently allows.
 10. GATE WIRING (2026-09-06). SKILL.md cites `scripts/gate.py` and `scripts/prompt_lint.py`, and
     the checkpoint and approvals templates exist in assets/. The skill's whole enforcement story
     rests on these being routed; an unrouted gate is the old paragraph-checkpoint again.
 11. HARD-RULE DENSITY (2026-09-06). ⛔ per file is reported, and SKILL.md is capped: at the
     2026-08-30 count (18 in the router, 542 across the corpus) the mark had stopped carrying
     information. Reserve ⛔ for a rule a script checks; prose says the rest.

What it cannot do
-----------------
- **It cannot tell you the hook FIRES.** It checks the registration parses and the paths resolve;
  whether the runtime honours plugin hooks (Cowork does not, per anthropics/claude-code#63360 at
  the time of writing) is a runtime property. `scripts/test_gate.py` proves the gate's logic; a live
  `generate_*` call with `get_cost: true` and no job open proves the wiring — it must be denied.
- **It cannot tell you a citation points at the RIGHT section, only that the section exists.**
- **A path inside a sentence that declares the thing unbuilt is reported separately, not as a
  break** — an honestly named gap is documentation, not rot. Saying so is what buys the pass.
- **It cannot tell you a reference is correct, current, or worth loading.** It checks that the
  pointer resolves, not that the thing pointed at is true. Contradictions between two references
  pass every check here (item 1 of prompting-craft.md section 11 sat contradicted for weeks and
  would have passed).
- The token figures are an approximation with no tokenizer behind them; use them for RELATIVE
  comparison between files and for spotting growth, never as a budget you can bank on.
- It has no opinion on whether a file should be core. That judgement is in _INDEX.md's prose.

Usage
-----
  python3 skill_audit.py                       # from anywhere inside the skill
  python3 skill_audit.py --root /path/to/skill --json
  python3 skill_audit.py --ceiling-core 60000  # fail if the always-loaded surface exceeds N tokens
  python3 skill_audit.py --strict-sections

Exit codes: 0 clean · 1 findings · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_home  # noqa: E402  (a `memory/...` path is a pointer into the studio's own history)

SKILL_DIRS = ["references", "scripts", "modes", "clients", "assets", "memory", "evals"]
PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+/[A-Za-z0-9_.-]+\.(?:md|py|json))`")
BARE_RE = re.compile(r"`([A-Za-z0-9_-]+\.(?:md|py|json))`")
# "`file.md` §6b"  /  "`file.md` section 6.1"
# ⛔ THE LETTER GOES AFTER THE DECIMAL. `\d+[a-z]?(?:\.\d+)?` reads "8.3b" as "8.3" and
# "**8.3b ...**" as nothing at all - so every citation to §8.3b in this skill was being validated
# against §8.3, and would have passed even if §8.3b did not exist. Found live 2026-09-17 while
# building the supersession parser, which needed the same shape and would not match.
SECT_RE = re.compile(r"`([A-Za-z0-9_-]+\.md)`\s*(?:§|section\s+)(\d+(?:\.\d+)?[a-z]?)", re.I)
# The § is optional: SKILL.md numbers its own sections "## §0 · The gate".
# ⛔ AND IT MISSED A FOURTH ONE (2026-09-17, same day, same class). `ai-generation.md` numbers its
# pipeline as `## Step 1 — START FRAME`, `## Step 3b — The pass architecture`. The number is not
# adjacent to the `##`, so none of those headings were indexed and a file citing §3b was reported as
# citing a section that does not exist. `Step`/`Stage`/`Phase` are heading forms this skill actually
# uses, so the index has to know them — the citation was right and the checker was wrong.
HEAD_RE = re.compile(r"^#{2,4}\s+\u00a7?\s*(?:Step|Stage|Phase)?\s*(\d+(?:\.\d+)?[a-z]?)[.\s\u2014\u2013-]", re.M)
# This skill numbers most sub-sections as bold inline heads (`**6.3 — Seeds are ...**`) rather than
# markdown headings. Both are section ids; a checker that only knows one of them cries wolf.
# A bold-lead subsection, in either house style: "**6.3 — Seeds are weaker**" or
# "**1.4 Direction.**". The second branch requires a capital to follow, so "**5 minutes**"
# is not a heading; the 1-2 digit cap keeps "**2026-08-28**" out.
# ⛔ AND IT STILL MISSED ONE (2026-09-17). The widened version demanded an UPPERCASE letter after
# the number, so `**3.8 ⚡ Motion that is not boring**` — the house style for a finding that carries a
# marker — resolved to nothing, and two files citing §3.8 were reported as citing a section that does
# not exist. The rule is now "a number, then a dash, or whitespace not followed by a lowercase
# letter", which admits the marker forms and still rejects `**5 minutes**`.
BOLD_RE = re.compile(r"^\*\*(?:Step|Stage|Phase)?\s*(\d{1,2}(?:\.\d+)?[a-z]?)(?:\s*[—–-]|[.\s](?![a-z]))", re.M)
# `### A · Specifiable in the prompt` — a lettered block under a numbered section, cited as "6A".
LETTER_RE = re.compile(r"^#{2,4}\s+([A-Z])\s*[·.\s]", re.M)
# A path cited inside a sentence that says the thing does not exist yet is a declared gap, not rot.
# SUPERSESSION (research-quality.md §5b). Two markers, one graph.
#   at the new claim   : ** SUPERSEDES `file.md` §N (YYYY-MM-DD) - <reason> **
#   at the old claim   : ** SUPERSEDED BY `file.md` §N (YYYY-MM-DD) **
#   in-place correction: ** SUPERSEDES IN PLACE (YYYY-MM-DD) - previously: "<old wording>" ... **
# The em dash is the house separator; a plain hyphen and an en dash are accepted so the marker is
# not lost to a keyboard.
_SEP = r"[\u2014\u2013-]"
SUPERSEDES_RE = re.compile(
    r"\*\*SUPERSEDES\*\*\s*`([A-Za-z0-9_-]+\.md)`\s*\u00a7?\s*([0-9]+(?:\.[0-9]+)?[a-z]?)"
    r"\s*\((\d{4}-\d{2}-\d{2})\)\s*" + _SEP + r"?\s*(.*)")
SUPERSEDED_BY_RE = re.compile(
    r"\*\*SUPERSEDED BY\*\*\s*`([A-Za-z0-9_-]+\.md)`\s*\u00a7?\s*([0-9]+(?:\.[0-9]+)?[a-z]?)"
    r"\s*\((\d{4}-\d{2}-\d{2})\)")
# ⛔ The reason runs to the end of the PARAGRAPH, not the end of the line. `(.*)` without DOTALL
# truncated a wrapped quote mid-string, so a correctly written in-place correction was reported as
# unquoted. Found live 2026-09-17, on the first real one.
IN_PLACE_RE = re.compile(
    r"(?s)\*\*SUPERSEDES IN PLACE\*\*\s*\((\d{4}-\d{2}-\d{2})\)\s*" + _SEP + r"?\s*(.*?)(?=\n\s*\n|\Z)")
# A bare marker that matched none of the three shapes above — a typo that would otherwise make the
# whole declaration invisible to this check, which is the one failure mode a checker must not have.
SUPERSEDE_ANY_RE = re.compile(r"\*\*SUPERSEDE(?:S|D BY)[^*]*\*\*")
MIN_REASON = 20

# A verbatim fragment: a quoted run of >=12 chars, in straight or curly quotes, optionally wrapped
# in markdown emphasis. `"x"` alone is a word, not a fragment; the length floor is what makes this
# check mean "somebody pasted the real text".
# A quote may WRAP across lines (markdown blockquotes do it constantly) but not across a blank
# line — found live 2026-09-17, the first version forbade \n and reported 9 quoted entries as unquoted.
QUOTED_FRAGMENT_RE = re.compile(r"[\u201c\"](?:(?!\n\s*\n)[^\u201c\u201d\"]){12,600}[\u201d\"]")
# A specifics entry can rest on a QUOTE (somebody wrote it) or on a MEASUREMENT (a tool counted it).
# Both are evidence; neither is an opinion. A measured entry must name the date and the tool, so the
# number can be re-run — which is the measured equivalent of quoting the source (added 2026-09-30,
# when five films were measured and not one of the findings was quotable).
SOURCE_TAG_RE = re.compile(r"\[(?:PRIMARY|SECONDARY|TERTIARY|PRACTITIONER)\b[^\]\n]*\]|\*Provenance:", re.I)
MEASURED_RE = re.compile(r"\[measured\s+\d{4}-\d{2}-\d{2}[^\]]*\b[a-z_]+\.py\b[^\]]*\]", re.I)
UNBUILT_RE = re.compile(r"not\s+(?:yet\s+)?(?:built|scripted|written|exist|implemented)|unbuilt|"
                        r"roadmap|does\s+not\s+exist|designed,\s*not\s+built|when\s+it\s+is,\s*it\s+lands",
                        re.I)
# Produced per PROJECT by the pipeline, never shipped in the skill folder. Citing one is correct.
PROJECT_ARTIFACTS = {"MASTER-image-prompts-all-scenes.md"}
# A file may declare that its paths point outside this skill (further-reading.md cites other repos).
EXTERNAL_MARKER = "<!-- skill_audit: external-paths -->"
DESC_RE_FM = re.compile(r"^description:\s*>-?\n((?:[ \t]+\S.*\n)+)", re.M)
# The same key on ONE line (quoted or plain), with any indented continuation lines. `(?![>|])` keeps
# a block-scalar header out of it, so an empty folded block is "unparseable", never the text ">-".
DESC_RE_LINE = re.compile(r"^description:[ \t]*(?![>|])(\S.*)\n((?:[ \t]+\S.*\n)*)", re.M)
MAX_SKILL_DESC = 1024      # installer limit, SKILL.md frontmatter
MAX_PLUGIN_DESC = 500      # installer limit, .claude-plugin/plugin.json
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# A description is scanned for XML tags. `clients/<brand>.md` is a placeholder to a human and a tag
# to a parser; the installer rejects it. Any angle bracket is reported, since a lone one is either a
# broken tag or a comparison nobody needs in a trigger string.
TAGLIKE_RE = re.compile(r"<[^<>]*>")
CLASS_RE = re.compile(r"^\|\s*`?([A-Za-z0-9_-]+\.md)`?\s*\|\s*\*{0,2}(core|extended|never)\b",
                      re.I | re.M)
MAX_SKILL_HARD_RULES = 8   # ⛔ marks allowed in SKILL.md; 18 was the count when they stopped meaning anything
HARD_RULE = "⛔"
IGNORE_BARE = PROJECT_ARTIFACTS | {"README.md", "SKILL.md", "PIPELINE.md", "CLAUDE.md", "MEMORY.md", "LEDGER.md",
               "_INDEX.md", "_TEMPLATE.md", "BIBLE.md", "INVARIANTS.md", "EPISODES.md",
               "DECISIONS.md", "HOOKS-USED.md", "BATCH.json", "JOIN.md", "QA-LOG.md",
               "CHECKPOINT.md", "APPROVALS.md", "hooks.json", "transactions.json",
               # job artefacts the scripts write (v2.50): the music rebuild, the region-repair comp, the fan-out round
               "REBUILD.json", "REBUILD.md", "BED.json", "FIT.json", "HITS.json", "STEMS.json", "FAMILY.json",
               "fusion.json", "track.json", "RECIPE.md", "PLAN.json", "RESULT.json"}
# Tool names that have ACTUALLY been served, with where each was seen. Add a name here when a new
# routing appears — never a name invented at the desk, which is how the hole below was missed.
GATED_TOOL_CORPUS = [
    ("mcp__Higgsfield__generate_video", True, "direct connection, Claude Code CLI"),
    ("mcp__Higgsfield__generate_image_batch", True, "direct connection, Claude Code CLI"),
    ("mcp__remote-devices__Higgsfield__generate_video", True,
     "the same server proxied through Cowork's device bridge"),
    ("mcp__DaVinci_Resolve__run_script", True, "Resolve Studio 21.1, direct"),
    ("mcp__remote-devices__DaVinci_Resolve_Studio__run_script_unsafe", True,
     "served in this Cowork session, 2026-09-17"),
    ("mcp__Gmail__send_message", False, "an unrelated server — must NOT be gated by this plugin"),
    ("mcp__0a0a0a0a-0000-4000-8000-000000000001__generate_image", True,
     "a claude.ai connector served by uuid (2026-10-06); since v2.59.0 any uuid, and the connector settings say which is Higgsfield"),
    ("mcp__0b0b0b0b-0000-4000-8000-000000000002__clickup_create_task", True,
     "another claude.ai connector's ordinary tool — reaches the gate since v2.61.0, which lets it through at once"),
    ("mcp__Higgsfield-Second__generate_video", True,
     "a second Higgsfield connector, served in a Cowork cloud session, 2026-10-26"),
    ("mcp__Kling_AI__image_to_video", True,
     "Kling's own API connector, served in a Cowork cloud session, 2026-10-26 — every job charged"),
    ("Bash", True, "the shell: shell_gate.py stops text drawn outside Resolve (house rule C7, 2026-10-27)"),
    ("mcp__remote-devices__device_bash", True, "the linked computer's shell in a Cowork session — the same shell gate"),
]


def frontmatter_description(fm: str) -> str | None:
    """The `description:` of a SKILL.md frontmatter as one line of text, or None when there is none.

    It is written two ways and both are read. The SOURCE repo folds it (`description: >-` and
    indented lines). The BUILD flattens it to one quoted line, so an installed copy carries
    `description: '...'`. Reading only the folded form meant that this audit, run on an installed
    copy, reported "no parseable description" and skipped the length and tag checks: the one place
    the installer's limit had already been applied was the one place it went unchecked
    (found 2026-11-10).

    What it cannot do: it is not a YAML parser. A quoted value is unquoted by the two rules that
    cover what the build writes ('' inside single quotes; JSON-style escapes inside double quotes).
    A literal block (`description: |`) is not read and is reported as unparseable."""
    m = DESC_RE_FM.search(fm)
    if m:
        return " ".join(l.strip() for l in m.group(1).splitlines())
    m = DESC_RE_LINE.search(fm)
    if not m:
        return None
    v = " ".join([m.group(1).strip()] + [l.strip() for l in m.group(2).splitlines()])
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    if len(v) >= 2 and v[0] == v[-1] == '"':
        try:
            return json.loads(v)
        except ValueError:
            return v[1:-1]
    return v


def _bracket_findings(where: str, desc: str) -> list[str]:
    """XML tags are refused outright; a lone angle bracket is reported as the near-miss it is."""
    out = []
    tags = TAGLIKE_RE.findall(desc)
    if tags:
        out.append(f"PACKAGING    {where} description contains XML tag(s) {tags} — the installer "
                   f"refuses them. A placeholder like `clients/<brand>.md` is a tag to a parser; "
                   f"write it in words instead")
    elif any(c in desc for c in "<>"):
        out.append(f"PACKAGING    {where} description contains a stray angle bracket — either a "
                   f"broken tag or a comparison that has no business in a trigger string")
    return out


def find_root(start: str) -> str | None:
    p = os.path.abspath(start)
    for _ in range(6):
        if os.path.isfile(os.path.join(p, "SKILL.md")) and os.path.isdir(os.path.join(p, "references")):
            return p
        p = os.path.dirname(p)
    return None


def md_files(root: str) -> list[str]:
    out = [os.path.join(root, f) for f in ("SKILL.md", "PIPELINE.md")
           if os.path.isfile(os.path.join(root, f))]
    for d in ("references", "modes", "clients", "assets"):
        dp = os.path.join(root, d)
        if os.path.isdir(dp):
            out += [os.path.join(dp, f) for f in sorted(os.listdir(dp)) if f.endswith(".md")]
    return out


def approx_tokens(path: str) -> int:
    return max(1, round(os.path.getsize(path) / 4))


def audit(root: str, ceiling_core: int | None, strict_sections: bool) -> dict:
    findings: list[str] = []
    notes: list[str] = []
    files = md_files(root)
    ref_dir = os.path.join(root, "references")
    on_disk = sorted(f for f in os.listdir(ref_dir) if f.endswith(".md") and not f.startswith("_"))

    # 1. paths — scanned line by line so a declared gap can be told from a broken link
    heads: dict[str, set[str]] = {}
    letters: dict[str, set[str]] = {}
    unbuilt: list[str] = []
    history_unchecked: list[str] = []
    for f in files:
        txt = open(f, encoding="utf-8").read()
        base = os.path.basename(f)
        heads[base] = set(HEAD_RE.findall(txt)) | set(BOLD_RE.findall(txt))
        letters[base] = set(LETTER_RE.findall(txt))
        rel = os.path.relpath(f, root)
        external = EXTERNAL_MARKER in txt
        lines = txt.splitlines()
        for i, line in enumerate(lines):
            window = "\n".join(lines[max(0, i - 2):i + 3])
            declared = bool(UNBUILT_RE.search(window))
            for m in PATH_RE.findall(line):
                if m.split("/")[0] not in SKILL_DIRS or os.path.exists(os.path.join(root, m)):
                    continue
                msg = f"{rel}:{i + 1} cites `{m}`"
                where = "not on disk"
                if m.startswith("memory/"):
                    # (v2.54.0) the history is the studio's and lives outside the plugin. With a history
                    # folder on this machine the pointer is checked there; with none it is COUNTED as
                    # unchecked and said so, never passed as found.
                    state, _ = memory_home.resolve(m, root)
                    if state in ("studio", "template"):
                        continue
                    if state == "unchecked":
                        history_unchecked.append(msg)
                        continue
                    where = "not in the studio's history folder"
                (unbuilt if declared else findings).append(
                    f"DECLARED GAP {msg} — named as not built" if declared
                    else f"BROKEN PATH  {msg} — {where}")
            if external:
                continue
            for m in BARE_RE.findall(line):
                if m in IGNORE_BARE or m.startswith("test_"):
                    continue
                if any(os.path.exists(os.path.join(root, d, m)) for d in SKILL_DIRS) \
                        or os.path.exists(os.path.join(root, m)):
                    continue
                msg = f"{rel}:{i + 1} cites `{m}`"
                (unbuilt if declared else findings).append(
                    f"DECLARED GAP {msg} — named as not built" if declared
                    else f"BROKEN PATH  {msg} — not on disk in any skill folder")

    # 2/3/4. index, orphans, classification
    idx_p = os.path.join(ref_dir, "_INDEX.md")
    classes: dict[str, str] = {}
    if not os.path.isfile(idx_p):
        findings.append("MISSING      references/_INDEX.md — the references have no registry, so "
                        "nothing can say which are always loaded")
    else:
        itxt = open(idx_p, encoding="utf-8").read()
        classes = {k: v.lower() for k, v in CLASS_RE.findall(itxt)}
        for f in on_disk:
            if f not in classes:
                findings.append(f"ORPHAN       references/{f} is not classified in _INDEX.md — an "
                                f"unrouted reference is a file nobody will open")
        for f in classes:
            if not os.path.isfile(os.path.join(ref_dir, f)):
                findings.append(f"GHOST        _INDEX.md lists references/{f} — not on disk")

    skill_txt = open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
    for f in on_disk:
        if f not in skill_txt and f not in classes:
            findings.append(f"UNROUTED     references/{f} is reachable from neither SKILL.md nor "
                            f"_INDEX.md")

    # 5. section citations
    for f in files:
        txt = open(f, encoding="utf-8").read()
        rel = os.path.relpath(f, root)
        for target, sec in SECT_RE.findall(txt):
            if target not in heads or sec in heads[target]:
                continue
            m = re.fullmatch(r"(\d+)([A-Za-z])", sec)   # "6A" = block A under section 6
            if m and m.group(1) in heads[target] and m.group(2).upper() in letters[target]:
                continue
            msg = f"SECTION      {rel} cites `{target}` §{sec} — no such section in {target}"
            (findings if strict_sections else notes).append(msg)

    # 6. budget
    # 7. rate restatement — the single-source rule, enforced
    RATE_OK = {"assets/higgsfield-rates.json", "scripts/rate_card.py", "scripts/refresh_costs.md",
               "memory/LEDGER.md"}
    for dirpath, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ("__pycache__", "_to_delete", ".git",
                                                "memory", "evals", "script-archive")]
        for n in names:
            if not n.endswith((".md", ".py", ".json")):
                continue
            rel = os.path.relpath(os.path.join(dirpath, n), root)
            if rel in RATE_OK:
                continue
            try:
                txt = open(os.path.join(dirpath, n), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in re.finditer(r"[\d.]+\s*cr/s", txt):
                findings.append(f"RATE         {rel} states a rate ({m.group(0)!r}) — rates live "
                                f"ONLY in assets/higgsfield-rates.json -> rate_table. Point at "
                                f"scripts/rate_card.py instead (charter rule 5)")
                break

    # 6. packaging limits — the caps the installer enforces
    fm = skill_txt.split("---", 2)[1] if skill_txt.startswith("---") else ""
    d = frontmatter_description(fm)
    if d is None:
        findings.append("PACKAGING    SKILL.md frontmatter has no parseable `description:` — neither "
                        "a folded block (`description: >-`) nor a one-line value")
    else:
        if len(d) > MAX_SKILL_DESC:
            findings.append(f"PACKAGING    SKILL.md description is {len(d)} chars — the installer "
                            f"rejects anything over {MAX_SKILL_DESC}. It is the TRIGGER surface, so "
                            f"cut architecture words, never the trigger nouns")
        findings.extend(_bracket_findings("SKILL.md", d))
    man = None
    probe = root
    for _ in range(3):
        cand = os.path.join(probe, ".claude-plugin", "plugin.json")
        if os.path.isfile(cand):
            man = cand; break
        probe = os.path.dirname(probe)
    if man:
        try:
            mf = json.load(open(man, encoding="utf-8"))
        except json.JSONDecodeError as e:
            findings.append(f"PACKAGING    {os.path.relpath(man, probe)} is not valid JSON: {e}")
            mf = {}
        pd = mf.get("description", "")
        if len(pd) > MAX_PLUGIN_DESC:
            findings.append(f"PACKAGING    plugin.json description is {len(pd)} chars — the "
                            f"installer rejects anything over {MAX_PLUGIN_DESC}")
        findings.extend(_bracket_findings("plugin.json", pd))
        if mf.get("name") and not NAME_RE.match(mf["name"]):
            findings.append(f"PACKAGING    plugin.json name {mf['name']!r} is not kebab-case")
    else:
        notes.append("PACKAGING    no .claude-plugin/plugin.json found above the skill root — the "
                     "install limits were not checked (fine if this skill does not ship as a plugin)")

    # 9. hooks — registration parses and every command path resolves
    _pre_matchers: list[tuple[int, str]] = []
    hooks_path = os.path.join(probe if man else root, "hooks", "hooks.json")
    if os.path.isfile(hooks_path):
        try:
            hk = json.load(open(hooks_path, encoding="utf-8"))
        except json.JSONDecodeError as e:
            hk = None
            findings.append(f"HOOKS        hooks/hooks.json is not valid JSON: {e}")
        if isinstance(hk, dict):
            events = hk.get("hooks") if isinstance(hk.get("hooks"), dict) else {}
            if not events:
                findings.append("HOOKS        hooks/hooks.json has no `hooks` object — nothing is registered")
            plugin_root = os.path.dirname(os.path.dirname(hooks_path))
            for ev, entries in events.items():
                for i, ent in enumerate(entries or []):
                    if ev == "PreToolUse" and not ent.get("matcher"):
                        findings.append(f"HOOKS        {ev}[{i}] has no matcher — it would fire on every tool")
                    if ev == "PreToolUse" and ent.get("matcher"):
                        _pre_matchers.append((i, ent["matcher"]))
                    for h in ent.get("hooks") or []:
                        cmd = h.get("command", "")
                        for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)", cmd):
                            if not os.path.isfile(os.path.join(plugin_root, m.group(1))):
                                findings.append(f"HOOKS        {ev}[{i}] command cites "
                                                f"${{CLAUDE_PLUGIN_ROOT}}/{m.group(1)} — not on disk; "
                                                f"a hook that points at nothing silently allows")
                        if not cmd:
                            findings.append(f"HOOKS        {ev}[{i}] has an entry with no command")
        # ⛔ A MATCHER THAT MATCHES NOTHING IS NOT A GATE (2026-09-17). Check 9 used to verify that a
        # matcher EXISTS and that its command is on disk — both true, all along, of a matcher that
        # matched zero real tool names. The Resolve matcher was written as `mcp__DaVinci_Resolve__…`
        # and the name actually served in a Cowork session is
        # `mcp__remote-devices__DaVinci_Resolve_Studio__…`: proxy segment in front, `_Studio` behind.
        # Every Resolve call in such a session, `run_script_unsafe` included, ran ungated and the
        # audit said the hooks were fine. So the audit now runs the matchers against names that have
        # actually been served, and against one that must NOT be caught.
        for _i, _m in _pre_matchers:
            try:
                re.compile(_m)
            except re.error as e:
                findings.append(f"HOOKS        PreToolUse[{_i}] matcher is not a valid regex ({e}) — "
                                f"it gates nothing")
                continue
            if not any(re.match(_m, n) for n, _g, _w in GATED_TOOL_CORPUS):
                findings.append(f"HOOKS        PreToolUse[{_i}] matcher `{_m}` matches NONE of the "
                                f"{len(GATED_TOOL_CORPUS)} known tool names — a dead matcher reads "
                                f"exactly like a live one")
        if _pre_matchers:
            for _n, _gated, _where in GATED_TOOL_CORPUS:
                _hit = any(re.match(_m, _n) for _, _m in _pre_matchers)
                if _gated and not _hit:
                    findings.append(f"HOOKS        `{_n}` ({_where}) is not matched by any PreToolUse "
                                    f"matcher — that call reaches the tool with no gate")
                if not _gated and _hit:
                    findings.append(f"HOOKS        `{_n}` ({_where}) IS matched by a PreToolUse matcher "
                                    f"— the gate is over-broad and will stall unrelated work")
    else:
        notes.append("HOOKS        no hooks/hooks.json at the plugin root — the gate runs only when "
                     "the agent runs gate.py itself")

    # 9b. EVERY SPECIFIC NAMES ITS SOURCE OR ITS MEASUREMENT.
    # references/specifics-catalogue.md exists because two supplied corpora were converted into rules while the
    # specifics that worked were thrown away. Until v2.63.0 the bar was "an entry you cannot QUOTE does not
    # belong", and the file shipped about 22 KB of third-party course and corpus text word for word. Since v2.63.0
    # an entry describes the specific in our own words and names where it came from: a source tag
    # ([PRIMARY|SECONDARY|PRACTITIONER · ...]) in the entry or in its section's opening, or a
    # [measured <date> <tool>.py] tag. A specific with neither is a rule wearing a specific's clothes.
    _spec = os.path.join(root, "references", "specifics-catalogue.md")
    if os.path.isfile(_spec):
        _txt = open(_spec, encoding="utf-8").read()
        for _m in re.finditer(r"^###\s+(.+?)\s*$", _txt, re.M):
            _start = _m.end()
            _nxt = re.search(r"^##", _txt[_start:], re.M)
            _body = _txt[_start:_start + (_nxt.start() if _nxt else len(_txt))]
            _sec = list(re.finditer(r"^## ", _txt[:_m.start()], re.M))
            _intro = _txt[_sec[-1].start():_m.start()] if _sec else ""
            _intro = _intro[:_intro.find("\n### ")] if "\n### " in _intro else _intro
            if not (SOURCE_TAG_RE.search(_body) or MEASURED_RE.search(_body) or SOURCE_TAG_RE.search(_intro)):
                findings.append(f"SPECIFICS    specifics-catalogue.md \u00a7 \u201c{_m.group(1)[:60]}\u201d "
                                f"names neither its source nor a [measured <date> <tool>.py] tag \u2014 "
                                f"that is a rule, not a specific (the file's \u00a78 rule 4)")

    # 11. SUPERSESSION — research-quality.md §5b. The danger is not a wrong claim, it is a wrong
    # claim left LIVE and UNLINKED. Reciprocity is the check that matters.
    sup_edges = []            # (src_file, src_sec, dst_file, dst_sec, date, reason)
    sup_back = set()          # (file_declaring, dst_file, dst_sec)
    in_place = []             # (file, date, body)
    def _section_at(txt: str, pos: int) -> str:
        """The nearest numbered heading or bold subsection above `pos` — which section a marker
        sits in. Uses the SAME parsers as the citation checker, so a form one accepts the other
        cannot silently reject."""
        best, name = -1, ""
        for rx in (HEAD_RE, BOLD_RE):
            for m in rx.finditer(txt[:pos]):
                if m.start() > best:
                    best, name = m.start(), m.group(1)
        return name
    def _code_spans(t: str) -> list:
        """Ranges covered by a fenced block or an inline-code span. A marker whose START falls in
        one is an EXAMPLE, not a declaration — which is how research-quality.md §5b can show all
        three markers. ⛔ It must NOT blank the whole text: a real marker's target filename is
        itself backticked, so stripping code spans outright makes every true declaration
        unparseable. Found live 2026-09-17, on the first run after adding the example rule."""
        sp = [m.span() for m in re.finditer(r"(?s)```.*?```", t)]
        sp += [m.span() for m in re.finditer(r"`[^`\n]*`", t)]
        return sp
    def _is_example(pos: int, spans: list) -> bool:
        return any(a <= pos < b for a, b in spans)
    for f in files:
        txt = open(f, encoding="utf-8").read()
        spans = _code_spans(txt)
        base, rel = os.path.basename(f), os.path.relpath(f, root)
        seen_spans = []
        for m in SUPERSEDES_RE.finditer(txt):
            if _is_example(m.start(), spans):
                continue
            seen_spans.append(m.span())
            dst_f, dst_s, date, reason = m.groups()
            src_s = _section_at(txt, m.start())
            sup_edges.append((base, src_s, dst_f, dst_s, date, reason.strip(), rel))
        for m in SUPERSEDED_BY_RE.finditer(txt):
            if _is_example(m.start(), spans):
                continue
            seen_spans.append(m.span())
            sup_back.add((base, _section_at(txt, m.start()), m.group(1), m.group(2)))
        for m in IN_PLACE_RE.finditer(txt):
            if _is_example(m.start(), spans):
                continue
            seen_spans.append(m.span())
            in_place.append((rel, m.group(1), m.group(2).strip()))
        # a marker that parsed as none of the three is a typo that would hide the declaration
        for m in SUPERSEDE_ANY_RE.finditer(txt):
            if _is_example(m.start(), spans):
                continue
            if not any(a <= m.start() < b for a, b in seen_spans):
                findings.append(f"SUPERSEDE    {rel} has a supersession marker this checker cannot "
                                f"parse: {m.group(0)[:70]!r} \u2014 it needs a backticked file, a "
                                f"\u00a7section and a (YYYY-MM-DD), or the words IN PLACE with a "
                                f"date (research-quality.md \u00a75b). An unparseable marker is an "
                                f"UNCHECKED one")
    for base, src_s, dst_f, dst_s, date, reason, rel in sup_edges:
        if dst_f == base and dst_s == src_s:
            findings.append(f"SUPERSEDE    {rel} \u00a7{src_s} supersedes itself")
            continue
        if dst_f not in heads:
            findings.append(f"SUPERSEDE    {rel} \u00a7{src_s} supersedes `{dst_f}` \u2014 no such "
                            f"reference file")
            continue
        if dst_s not in heads[dst_f]:
            findings.append(f"SUPERSEDE    {rel} \u00a7{src_s} supersedes `{dst_f}` \u00a7{dst_s} \u2014 "
                            f"that section does not exist. If the old text was DELETED, the marker "
                            f"is SUPERSEDES IN PLACE at the new claim, not a pointer at a section "
                            f"that is gone (research-quality.md \u00a75b)")
            continue
        if len(reason) < MIN_REASON:
            findings.append(f"SUPERSEDE    {rel} \u00a7{src_s} supersedes `{dst_f}` \u00a7{dst_s} with no "
                            f"reason \u2014 \u201csuperseded\u201d without one is a deletion with extra "
                            f"steps, and the reason is the only part a future reader can argue with")
        if (dst_f, dst_s, base, src_s) not in sup_back:
            findings.append(f"SUPERSEDE    \u26a1 `{dst_f}` \u00a7{dst_s} is SUPERSEDED BY {rel} \u00a7{src_s} "
                            f"and does not say so \u2014 the old claim is still live and unlinked, "
                            f"which is the exact failure \u00a75b exists to stop. Add "
                            f"\u201c\u26d4 **SUPERSEDED BY** `{base}` \u00a7{src_s} ({date})\u201d to it")
    for dec_f, dec_s, dst_f, dst_s in sorted(sup_back):
        if dst_f not in heads or dst_s not in heads.get(dst_f, ()):  # dangling back-pointer
            findings.append(f"SUPERSEDE    `{dec_f}` \u00a7{dec_s} says it is superseded by `{dst_f}` "
                            f"\u00a7{dst_s}, which does not exist")
            continue
        if not any(e[0] == dst_f and e[1] == dst_s and e[2] == dec_f and e[3] == dec_s
                   for e in sup_edges):
            findings.append(f"SUPERSEDE    `{dec_f}` \u00a7{dec_s} says it is superseded by `{dst_f}` "
                            f"\u00a7{dst_s}, but that section does not claim to supersede it \u2014 "
                            f"half a pair is worse than none, because it reads as settled")
    for rel, date, body in in_place:
        if not QUOTED_FRAGMENT_RE.search(body):
            findings.append(f"SUPERSEDE    {rel} corrects itself in place ({date}) without quoting "
                            f"what the text USED to say \u2014 the correction is then unreadable "
                            f"without a git blame (research-quality.md \u00a75b)")

    # 10. gate wiring — the enforcement story is routed
    for must in ("scripts/gate.py", "scripts/prompt_lint.py"):
        if f"`{must}`" not in skill_txt and os.path.basename(must) not in skill_txt:
            findings.append(f"GATE         SKILL.md does not cite {must} — an unrouted gate is the "
                            f"paragraph checkpoint again")
    for tpl in ("assets/checkpoint-template.md", "assets/approvals-template.md"):
        if not os.path.isfile(os.path.join(root, tpl)):
            findings.append(f"GATE         {tpl} missing — gate.py open cannot seed a job")

    # 11. hard-rule density
    density = {}
    for path in md_files(root):
        n = open(path, encoding="utf-8").read().count(HARD_RULE)
        if n:
            density[os.path.relpath(path, root)] = n
    skill_n = density.get("SKILL.md", 0)
    if skill_n > MAX_SKILL_HARD_RULES:
        findings.append(f"DENSITY      SKILL.md carries {skill_n} ⛔ marks (cap {MAX_SKILL_HARD_RULES}) — "
                        f"when everything is non-negotiable nothing is; keep ⛔ for script-checked rules")

    budget = []
    for f in on_disk:
        p = os.path.join(ref_dir, f)
        budget.append({"file": f, "bytes": os.path.getsize(p), "tokens": approx_tokens(p),
                       "class": classes.get(f, "?")})
    budget.sort(key=lambda d: -d["tokens"])
    core_files = [b for b in budget if b["class"] == "core"]
    core_tokens = sum(b["tokens"] for b in core_files) + approx_tokens(os.path.join(root, "SKILL.md"))
    total_tokens = sum(b["tokens"] for b in budget)
    if ceiling_core is not None and core_tokens > ceiling_core:
        findings.append(f"BUDGET       always-loaded surface ~{core_tokens} tokens exceeds the "
                        f"ceiling of {ceiling_core}")

    return {"root": root, "references": len(on_disk), "findings": findings, "notes": notes,
            "supersessions": [{"from_file": e[0], "from_section": e[1], "to_file": e[2],
                               "to_section": e[3], "date": e[4], "reason": e[5]} for e in sup_edges],
            "in_place_corrections": [{"file": a, "date": b, "note": c} for a, b, c in in_place],
            "declared_gaps": unbuilt, "history_pointers_unchecked": history_unchecked,
            "hard_rule_density": density,
            "core_files": [b["file"] for b in core_files], "core_tokens_est": core_tokens,
            "all_references_tokens_est": total_tokens, "budget": budget}


def selftest() -> int:
    assert PATH_RE.findall("see `references/a-b.md` and `scripts/x_y.py`") == \
        ["references/a-b.md", "scripts/x_y.py"]
    assert BARE_RE.findall("read `motion-design.md` now") == ["motion-design.md"]
    assert SECT_RE.findall("`prompting-craft.md` §6b and `series-continuity.md` section 6.1") == \
        [("prompting-craft.md", "6b"), ("series-continuity.md", "6.1")]
    # ⛔ the letter goes AFTER the decimal — §8.3b is not §8.3, and reading it as §8.3 made every
    # citation to §8.3b validate against a different section. Found live 2026-09-17.
    assert SECT_RE.findall("`character-and-props.md` §8.3b") == [("character-and-props.md", "8.3b")]
    assert BOLD_RE.findall("**8.3b \u26a1 The house sheet**\n") == ["8.3b"]
    assert HEAD_RE.findall("## 8.3b The thing\n") == ["8.3b"]
    assert HEAD_RE.findall("## 6b. Reference budget\n### 6.1 The registry\n## Not numbered\n"
                           "## \u00a70 \u00b7 The gate\n"
                           "## Step 3b \u2014 The pass architecture\n"   # the form ai-generation.md uses
                           "## Step 1 \u2014 START FRAME\n") == ["6b", "6.1", "0", "3b", "1"]
    # and the bold form of the same: `**Step 3c. A state change...**`
    assert BOLD_RE.findall("**Step 3c. A state change means switching the reference**\n"
                           "**Step 12 \u2014 something**\n") == ["3c", "12"]
    # the specifics-catalogue quote bar: a real pasted fragment counts, a bare word does not
    assert QUOTED_FRAGMENT_RE.search('he says \u201cGot any change on you?\u201d here')
    assert QUOTED_FRAGMENT_RE.search('*"pressed back, breathless, light shock"*')
    assert not QUOTED_FRAGMENT_RE.search('the word "annoyed" is short')
    assert not QUOTED_FRAGMENT_RE.search('no quotes at all in this line')
    # a blockquote that WRAPS is still one fragment; a quote broken by a blank line is not
    assert QUOTED_FRAGMENT_RE.search('> *"Black leather steering wheel with a stitched rim\n> and a '
                                     'silver four-pointed star emblem on the center hub."*')
    assert not QUOTED_FRAGMENT_RE.search('he said "well\n\nand then later" she replied')
    # a measured entry needs a date AND the tool that produced it, so the number can be re-run
    assert MEASURED_RE.search("[measured 2026-09-30 \u00b7 film_breakdown.py \u00b7 997 shots]")
    assert not MEASURED_RE.search("[measured 2026-09-30]")          # no tool named
    assert not MEASURED_RE.search("[measured with film_breakdown.py]")   # no date
    assert BOLD_RE.findall(
        "**6.3 — Seeds are weaker**\n**5.1 - split**\n**Bold, not a head**\n"
        "**1.4 Direction.**\n**7.0 The mechanism, first.**\n"      # the second house style
        "**3.8 \u26a1 Motion that is not boring**\n"                  # a marker, not a letter
        "**9.0 \u26d4 Blacklist**\n"
        "**5 minutes**\n**2026-08-28**\n"                          # neither is a heading
    ) == ["6.3", "5.1", "1.4", "7.0", "3.8", "9.0"]
    assert LETTER_RE.findall("### A \u00b7 Specifiable\n### D. Not obtainable\n### Also not\n") == ["A", "D"]
    assert UNBUILT_RE.search("the pull itself is not scripted yet")
    assert not UNBUILT_RE.search("run pull_finals.py after the batch")
    assert DESC_RE_FM.search("---\nname: x\ndescription: >-\n  one two\n  three\n---\n").group(1) \
        == "  one two\n  three\n"
    # the description is read in both forms: folded (the source) and one line (an installed copy)
    assert frontmatter_description("\nname: x\ndescription: >-\n  one two\n  three\n") == "one two three"
    assert frontmatter_description("\nname: x\ndescription: 'a video''s cost: one, two'\n") \
        == "a video's cost: one, two"
    assert frontmatter_description('\nname: x\ndescription: "say \\"hi\\" twice"\n') == 'say "hi" twice'
    assert frontmatter_description("\nname: x\ndescription: plain words\n  carried over\n") \
        == "plain words carried over"
    assert frontmatter_description("\nname: x\n") is None
    assert frontmatter_description("\nname: x\ndescription: >-\n") is None      # an empty block is not ">-"
    assert frontmatter_description("\nname: x\ndescription: |\n  literal\n") is None   # not read: say so
    assert len(frontmatter_description("\ndescription: '" + "x" * 1025 + "'\n")) == 1025  # the limit bites
    assert NAME_RE.match("cinematography") and not NAME_RE.match("Cinema_Graphy")
    assert TAGLIKE_RE.findall("loads clients/<brand>.md now") == ["<brand>"]
    assert _bracket_findings("t", "loads clients/<brand>.md") and \
        _bracket_findings("t", "a < b") and not _bracket_findings("t", "clean text")
    assert MAX_SKILL_DESC == 1024 and MAX_PLUGIN_DESC == 500
    assert CLASS_RE.findall("| `delivery-format.md` | **core** | x |\n| `ideation.md` | extended | y |") == \
        [("delivery-format.md", "core"), ("ideation.md", "extended")]
    # --- SUPERSESSION parsers (research-quality.md §5b) -------------------------------------
    _sup = SUPERSEDES_RE.search(
        "\u26a0\ufe0f **SUPERSEDES** `character-and-props.md` \u00a78.3b (2026-09-17) \u2014 the model "
        "cannot hold one face across three panels")
    assert _sup and _sup.groups()[:3] == ("character-and-props.md", "8.3b", "2026-09-17"), _sup
    assert len(_sup.group(4)) >= MIN_REASON
    _bk = SUPERSEDED_BY_RE.search("\u26d4 **SUPERSEDED BY** `specifics-catalogue.md` \u00a73.2 (2026-09-17)")
    assert _bk and _bk.groups() == ("specifics-catalogue.md", "3.2", "2026-09-17"), _bk
    _ip = IN_PLACE_RE.search('\u26a0\ufe0f **SUPERSEDES IN PLACE** (2026-09-17) \u2014 previously: '
                             '"one identical person across all three panels". The model cannot.')
    assert _ip and _ip.group(1) == "2026-09-17" and QUOTED_FRAGMENT_RE.search(_ip.group(2))
    # ...and the reason runs to the end of the PARAGRAPH, so a wrapped quote survives
    _ipw = IN_PLACE_RE.search('**SUPERSEDES IN PLACE** (2026-09-17) \u2014 previously: "The vehicle '
                              'sheet is FOUR\nattributes, not a paragraph." It generalised from one '
                              'scene type.\n\nNext paragraph.')
    assert _ipw and QUOTED_FRAGMENT_RE.search(_ipw.group(2)), _ipw and _ipw.group(2)
    assert "Next paragraph" not in _ipw.group(2)
    # the separator may be an em dash, an en dash or a hyphen - a marker must not be lost to a keyboard
    for _d in ("\u2014", "\u2013", "-"):
        assert SUPERSEDES_RE.search(f"**SUPERSEDES** `a.md` \u00a71 (2026-01-01) {_d} because reasons here")
    # a malformed marker must still be SEEN - an unparseable declaration is an unchecked one
    assert SUPERSEDE_ANY_RE.search("**SUPERSEDES the old thing**")
    assert not SUPERSEDES_RE.search("**SUPERSEDES the old thing**")
    assert not SUPERSEDE_ANY_RE.search("this section supersedes nothing at all")

    # --- SUPERSESSION end to end: every branch fires, and the clean pair is silent -----------
    import tempfile as _tf
    def _mini(fs: dict) -> list:
        d = _tf.mkdtemp()
        os.makedirs(os.path.join(d, "references")); os.makedirs(os.path.join(d, "assets"))
        os.makedirs(os.path.join(d, "scripts"))
        open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8").write(
            "# s\n`scripts/gate.py` `scripts/prompt_lint.py`\n")
        for k, v in fs.items():
            open(os.path.join(d, "references", k), "w", encoding="utf-8").write(v)
        return [x for x in audit(d, None, False)["findings"] if x.startswith("SUPERSEDE")]

    NEW = ("## 1. New\n\n\u26a0\ufe0f **SUPERSEDES** `old.md` \u00a72 (2026-09-17) \u2014 "
           "the earlier measurement was taken from a cached page\n")
    OLD_OK = "## 2. Old\n\n\u26d4 **SUPERSEDED BY** `new.md` \u00a71 (2026-09-17)\n"
    assert _mini({"new.md": NEW, "old.md": OLD_OK}) == [], _mini({"new.md": NEW, "old.md": OLD_OK})
    _bad = _mini({"new.md": NEW, "old.md": "## 2. Old\n\nstill says the old thing\n"})
    assert any("still live and unlinked" in x for x in _bad), _bad
    _gone = _mini({"new.md": NEW, "old.md": "## 9. Other\n\nnothing here\n"})
    assert any("that section does not exist" in x for x in _gone), _gone
    _nofile = _mini({"new.md": NEW})
    assert any("no such reference file" in x for x in _nofile), _nofile
    _thin = _mini({"new.md": "## 1. New\n\n**SUPERSEDES** `old.md` \u00a72 (2026-09-17) \u2014 no\n",
                   "old.md": OLD_OK})
    assert any("with no reason" in x for x in _thin), _thin
    _half = _mini({"old.md": OLD_OK, "new.md": "## 1. New\n\nnothing claims to supersede\n"})
    assert any("does not claim to supersede it" in x for x in _half), _half
    _me = _mini({"new.md": "## 1. New\n\n**SUPERSEDES** `new.md` \u00a71 (2026-09-17) \u2014 "
                           "a long enough reason to pass the floor\n"})
    assert any("supersedes itself" in x for x in _me), _me
    _nq = _mini({"new.md": "## 1. New\n\n**SUPERSEDES IN PLACE** (2026-09-17) \u2014 it was wrong\n"})
    assert any("without quoting what the text USED to say" in x for x in _nq), _nq
    _wq = _mini({"new.md": '## 1. New\n\n**SUPERSEDES IN PLACE** (2026-09-17) \u2014 previously: '
                           '"one identical person across all three panels". The model cannot.\n'})
    assert _wq == [], _wq
    _typo = _mini({"new.md": "## 1. New\n\n**SUPERSEDES the old guidance**\n"})
    assert any("cannot parse" in x for x in _typo), _typo
    _ex = _mini({"new.md": "## 1. New\n\nwrite `**SUPERSEDES** x` or:\n\n```\n"
                           "**SUPERSEDED BY** whatever\n```\n"})
    assert _ex == [], _ex

    # --- HISTORY POINTERS (v2.54.0): `memory/...` is the studio's folder, outside the plugin --------
    def _hist(env_dir, put=None):
        d = _tf.mkdtemp()
        for sub_ in ("references", "assets", "scripts"):
            os.makedirs(os.path.join(d, sub_))
        open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8").write("# s\n`scripts/gate.py` `scripts/prompt_lint.py`\n")
        open(os.path.join(d, "references", "a.md"), "w", encoding="utf-8").write(
            "## 1. A\n\nSee `memory/episodes/2026-01-01-note.md` and `memory/episodes/_TEMPLATE.md`.\n")
        _old, _cwd = os.environ.get("CINE_MEMORY"), os.getcwd()
        try:
            os.chdir(d)
            if env_dir:
                os.environ["CINE_MEMORY"] = env_dir
                if put:
                    os.makedirs(os.path.join(env_dir, "episodes"), exist_ok=True)
                    open(os.path.join(env_dir, "episodes", put), "w").write("x")
            else:
                os.environ.pop("CINE_MEMORY", None)
            r_ = audit(d, None, False)
        finally:
            os.chdir(_cwd)
            if _old is None:
                os.environ.pop("CINE_MEMORY", None)
            else:
                os.environ["CINE_MEMORY"] = _old
        return [x for x in r_["findings"] if "memory/" in x], r_["history_pointers_unchecked"]
    _f, _u = _hist(None)
    assert _f == [] and len(_u) == 1 and "2026-01-01-note" in _u[0], (_f, _u)      # counted, not found, not broken
    _f, _u = _hist(_tf.mkdtemp(), put="2026-01-01-note.md")
    assert _f == [] and _u == [], (_f, _u)                                         # checked and present
    _f, _u = _hist(_tf.mkdtemp())
    assert len(_f) == 1 and "not in the studio's history folder" in _f[0] and _u == [], (_f, _u)   # checked and absent

    print("selftest OK \u2014 path, bare-path, section-citation, heading and classification parsers; "
          "frontmatter-description parser, kebab-case name, install limits, XML-tag refusal, rate "
          "restatement; SUPERSESSION end to end \u2014 the matched pair, the stale claim left live "
          "and unlinked, a dangling section, a dangling file, a thin reason, half a pair, "
          "self-supersession, an unquoted in-place correction, an unparseable marker, and an "
          "example in code; HISTORY POINTERS \u2014 unchecked with no history folder, clean when the "
          "studio holds the note, broken when it does not")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="skill root (auto-detected by walking up)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ceiling-core", type=int)
    ap.add_argument("--strict-sections", action="store_true")
    ap.add_argument("--top", type=int, default=10, help="how many files to show in the budget table")
    ap.add_argument("--supersessions", action="store_true",
                    help="print what this skill has changed its mind about: every declared "
                         "supersession and in-place correction (research-quality.md \u00a75b)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    root = find_root(a.root) or find_root(os.path.dirname(os.path.abspath(__file__)))
    if not root:
        print("REFUSED: no SKILL.md + references/ found from here. Pass --root.", file=sys.stderr)
        return 2
    r = audit(root, a.ceiling_core, a.strict_sections)
    if a.supersessions:
        sup, ip = r["supersessions"], r["in_place_corrections"]
        print(f"\nwhat this skill has changed its mind about \u2014 {root}")
        print(f"\n  cross-file supersessions ({len(sup)}):"
              if sup else "\n  cross-file supersessions: none")
        for e in sup:
            print(f"    {e['from_file']} \u00a7{e['from_section']}  supersedes  "
                  f"{e['to_file']} \u00a7{e['to_section']}   ({e['date']})")
            print(f"        {e['reason'][:150]}")
        print(f"\n  in-place corrections ({len(ip)}):" if ip else "\n  in-place corrections: none")
        for e in ip:
            print(f"    {e['file']}   ({e['date']})")
            print(f"        {e['note'][:180]}")
        bad = [x for x in r["findings"] if x.startswith("SUPERSEDE")]
        print(f"\n  {len(bad)} supersession finding(s)" if bad else "\n  no supersession findings")
        for x in bad:
            print(f"  \u2717 {x}")
        return 1 if bad else 0
    if a.json:
        print(json.dumps(r, indent=2)); return 1 if r["findings"] else 0
    print(f"\nskill_audit — {root}\n  {r['references']} references · "
          f"~{r['core_tokens_est']} tokens always-loaded · ~{r['all_references_tokens_est']} tokens "
          f"if everything were loaded")
    print(f"  core: {', '.join(r['core_files']) if r['core_files'] else '(none classified)'}")
    print(f"\n  heaviest references (estimate, chars/4):")
    for b in r["budget"][:a.top]:
        print(f"    {b['tokens']:>6}  {b['class']:<9} {b['file']}")
    dens = r.get("hard_rule_density") or {}
    if dens:
        top = sorted(dens.items(), key=lambda kv: -kv[1])[:6]
        print(f"\n  ⛔ density — {sum(dens.values())} marks across {len(dens)} files; SKILL.md {dens.get('SKILL.md', 0)} "
              f"(cap {MAX_SKILL_HARD_RULES}); heaviest: " + ", ".join(f"{k} {v}" for k, v in top))
    if r["declared_gaps"]:
        print(f"\n  {len(r['declared_gaps'])} declared gap(s) — cited and honestly named as not built:")
        for g in r["declared_gaps"]:
            print(f"    · {g}")
    if r["notes"]:
        print(f"\n  {len(r['notes'])} section-citation note(s) (informational; --strict-sections to gate):")
        for n in r["notes"][:15]:
            print(f"    · {n}")
        if len(r["notes"]) > 15:
            print(f"    · … and {len(r['notes']) - 15} more")
    hp = r.get("history_pointers_unchecked") or []
    if hp:
        print(f"\n  {len(hp)} pointer(s) into the studio's history NOT CHECKED — no history folder on this machine "
              f"(set CINE_MEMORY, or run from under a `_cine-memory/` folder)")
    print()
    for f in r["findings"]:
        print(f"  ! {f}")
    if not r["findings"]:
        print("  routing clean — every cited path " + ("that could be checked " if hp else "") +
              "resolves, nothing orphaned, everything classified")
    print("  (pointers only — nothing here read a reference for correctness or currency)\n")
    return 1 if r["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
