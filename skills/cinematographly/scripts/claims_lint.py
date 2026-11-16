#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""claims_lint.py — lint a script for risky advertising claims before it goes to generation.

The rule set is the table in ../references/compliance.md section 4, which carries the reasoning and
the sources. This script is the mechanical pass; it is a first line of defence, NOT a compliance
sign-off and NOT legal advice. A clean run means "nothing on the known list" — it does not mean the
net impression is safe, and net impression is what actually governs. A human still reads the script
WITH the shot descriptions before it ships.

Usage
-----
  python3 claims_lint.py SCRIPT.md
  python3 claims_lint.py SCRIPT.md --category sleep      # add category-specific terms
  python3 claims_lint.py 01-script/*.md --quiet          # batch, findings only
  python3 claims_lint.py SCRIPT.md --allow "clinically proven"   # client-approved, recorded
       (--allow suppresses ONLY findings inside that exact phrase — other risky wording on the
        same line still reports. Record the written approval; an --allow with no paper trail is
        how an unapproved claim ships.)
  python3 claims_lint.py SCRIPT.md --paid                # a creator is paid/gifted/employed
  python3 claims_lint.py SCRIPT.md --json                # machine-readable
  python3 claims_lint.py SCRIPT.md --profile clients/<brand>.md   # name the client profile
  python3 claims_lint.py 01-script/SCRIPT.md 08-captions/x.srt    # captions and review sheets too

THE CLIENT'S RESTRICTED WORDS
---------------------------------------
The client profile's §4 "Restricted words for this brand" list is read, and every listed word or
phrase found in what this lints (the script, captions, on-screen text and quoted reviews in it, and
any captions or review file passed beside it) is a BLOCK. Matching is case-insensitive on word
boundaries, so `cheap` catches "Cheap!" and not "cheapest". A word inside the replacement the client
agreed (`free` inside `free trial`) passes. The mention/use tiering applies as for every other rule,
and --allow suppresses a restricted word exactly as it suppresses any other finding.
  The profile is the one --profile names; without it, the one the job's 00-brief/CHECKPOINT.md
`Client:` line names, looked for where gate.py looks (CINE_CLIENTS, a `_cine-clients/` folder above
the job, then the plugin's clients/). `gate.py approve script` passes no profile, and the artifact it
lints sits inside the job, so this lookup is how the list reaches the approval. No profile, no field,
`none` or a placeholder: the check is skipped and the report says so. A field written as prose with
no list items is reported as NOT READ (a NOTE), never as clean. --no-profile skips the lookup.

DISCLOSURE — the check whose failure is an ABSENCE
--------------------------------------------------
Per-line patterns cannot see a missing disclosure, and a missing disclosure is what every FTC video
enforcement action in compliance.md section 2b actually turns on. So there is a document-level pass:
if the script shows a material connection (or --paid says there is one) and carries no adequate
disclosure anywhere, that is a BLOCK. When neither is true the pass reports NOT ASSERTED rather than
clean, because nothing was examined. ⛔ Pass --paid whenever a creator is paid, gifted, commissioned
or employed — it is the normal case for UGC and it is not inferable from the script's words.

LANGUAGE LIMIT — read this before trusting a clean run
------------------------------------------------------
The patterns are ENGLISH. A Romanian, Spanish or German script will come back clean because nothing
matched, not because nothing is wrong. For a non-English client, either translate the risky-phrase
table in ../references/compliance.md section 4 into that language and add the patterns to
CATEGORY_RULES, or run the lint on an English gloss of the script. A clean run on a
non-English script with no localised rules is not evidence of anything — say so rather than
reporting it as a pass.

Exit codes: 0 clean · 1 findings · 2 usage/IO error.

Severity
--------
  BLOCK  a disease/cure/absolute claim, or a fabricated-endorsement shape. Do not ship.
  WARN   needs substantiation on file, or a qualifier, before it ships.
  NOTE   fine in most contexts; check it against the imagery it sits on.
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)

# ⛔ THE SILENT PASS. A clean run on a script the rules cannot READ is not a finding, it is a
# failure to look — and it reports as the good outcome, which is the worst property a check can
# have. Measured three times on 2026-09-07: this lint on a non-English script; a JSON contract read
# by the wrong key, finding 0 of 13 real findings; and `gate.py reconcile` on a payload carrying no
# prompts, announcing "194 credits ungated" when nothing could ever have matched.
# The rule: a checker must distinguish "I looked and found nothing" from "I could not look", and the
# mechanical way to do it is to report a DENOMINATOR. Deliberately conservative — English function
# words are common enough that any real English script clears the floor easily.
EN_MARKERS = set("the and you your it is are for with this that of to a in on we our but not have "
                 "was were be been they them what when how why can will just from at as so if".split())
EN_FLOOR = 0.06          # [ASSUMED 2026-09-07] fraction of tokens that are English function words


def language_coverage(text: str) -> dict:
    """Does the ENGLISH rule set stand a chance of reading this script?"""
    toks = re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE)
    if not toks:
        return {"tokens": 0, "en_markers": 0, "en_ratio": 0.0, "readable": False}
    hits = sum(1 for w in toks if w in EN_MARKERS)
    return {"tokens": len(toks), "en_markers": hits,
            "en_ratio": round(hits / len(toks), 3), "readable": hits / len(toks) >= EN_FLOOR}

# (pattern, severity, why, reframe)
RULES: list[tuple[str, str, str, str]] = [
    # --- absolutes / disease claims ---
    (r"\bcures?\b(?!\s+(?:for\s+)?nothing)", "BLOCK", "Cure claim — drugs only",
     "Describe what people report, not what it cures"),
    (r"\btreats?\b", "BLOCK", "Treatment claim — drugs only",
     "'supports' / 'designed to help with' + the normal function"),
    (r"\bheals?\b", "BLOCK", "Healing claim", "'supports recovery' with substantiation, or drop"),
    (r"\bprevents?\b", "BLOCK", "Disease-prevention claim", "'supports normal <function>'"),
    (r"\breverses?\b", "BLOCK", "Condition-reversal claim", "'supports the natural process of …'"),
    (r"\beliminat(?:es?|ing)\b", "BLOCK", "Absolute elimination claim", "'helps reduce'"),
    (r"\berases?\b", "BLOCK", "Absolute cosmetic claim", "'visibly softens the look of'"),
    (r"\bfix(?:es)?\s+your\b", "BLOCK", "Implied cure + permanence", "'part of a routine that helps'"),
    (r"\bfor\s+good\b", "BLOCK", "Permanence claim", "'results vary; continued use helps maintain'"),
    (r"\bpermanent(?:ly)?\b", "BLOCK", "Permanence claim", "'results vary; continued use helps maintain'"),
    (r"\bguarantee(?:d|s)?\s+(?:results?|weight|sleep|relief|returns?)\b", "BLOCK",
     "Efficacy guarantee", "'backed by a 30-day money-back guarantee' (satisfaction, not efficacy)"),
    (r"\bno\s+side\s+effects?\b", "BLOCK", "Absolute safety claim", "Omit unless adverse-event data supports it"),
    (r"\brisk[- ]free\b", "BLOCK", "Absolute risk claim", "Describe the actual refund/return terms"),
    (r"\bmiracle\b", "BLOCK", "Miracle claim", "Drop"),
    (r"\bdetox(?:es|ify|ifies|ifying)?\b", "BLOCK", "Unsubstantiable red-flag term",
     "Name the actual studied ingredient function"),
    (r"\bworks?\s+for\s+everyone\b", "BLOCK", "Universalises a variable outcome", "'a lot of people find it helps'"),
    (r"\bFDA[- ]approved\b", "BLOCK", "False for supplements/cosmetics",
     "'made in an FDA-registered facility' — only if true"),

    # --- named conditions (disease claim by naming) ---
    (r"\binsomnia\b", "BLOCK", "Names a diagnosable disorder", "'trouble falling asleep' / 'restless nights'"),
    (r"\banxiety\b", "BLOCK", "Names a diagnosable condition", "'everyday stress' / 'feeling wound up'"),
    (r"\bdepress(?:ion|ed)\b", "BLOCK", "Names a diagnosable condition", "Do not make this claim; refer to a professional"),
    (r"\bADHD\b", "BLOCK", "Names a diagnosable condition", "Do not make this claim"),
    (r"\b(?:diabet(?:es|ic)|arthritis|hypertension|menopause\s+symptoms?)\b", "BLOCK",
     "Names a disease/medical condition", "Reframe to normal-function language, or drop"),

    # --- personal attributes (Meta Advertising Standards, "Privacy Violations and Personal Attributes",
    # checked 2026-10-21): an ad may not assert or imply the viewer's health condition, and a QUESTION
    # counts — "Do you have diabetes?" is Meta's own rejected example. Age is on the same list ("Meet other
    # seniors" is rejected). compliance.md §5c.
    (r"\b(?:do|are|have)\s+you\s+(?:have|got|suffer(?:ing)?\s+from|struggl(?:e|ing)\s+with|been\s+diagnosed|"
     r"living\s+with|dealing\s+with)\b", "WARN",
     "Personal attributes (Meta): a question about the viewer's health or condition is the policy's own "
     "rejected example",
     "Describe the product and what it is formulated to do ('New diabetes treatment available', not 'Do you "
     "have diabetes?')"),
    (r"\byour\s+(?:\w+\s+)?(?:disease|condition|disorder|diagnosis)\b", "WARN",
     "Personal attributes (Meta): asserts the viewer has a condition",
     "Talk about the product, or a named storyteller's experience, never the viewer's condition"),
    (r"\byou(?:'re|\s+are)\s+(?:over|in\s+your)\s+\d0s?\b|\bother\s+(?:seniors|women\s+over\s+\d+)\b", "WARN",
     "Personal attributes (Meta): an age call-out ('Meet other seniors' is a rejected example)",
     "Target the age in the ad set, not in the copy"),

    # --- evidence & authority ---
    (r"\bclinically\s+(?:proven|tested|validated)\b", "WARN", "Implies rigor not shown in the ad",
     "Name the study: 'in a 60-person double-blind trial, 72% reported …'"),
    (r"\bscientifically\s+(?:proven|backed)\b", "WARN", "Vague science claim", "Cite the study, or drop"),
    (r"\bproven\b", "WARN", "Proof claim needs substantiation on file", "'shown in <named study>' or 'many people report'"),
    (r"\bdoctors?\s+(?:recommend|approved|trust)\w*\b", "WARN", "Expert-endorsement claim",
     "Name the credentialed person and disclose the connection — only if real"),
    (r"#1\s+(?:doctor|dermatologist|pharmacist)", "BLOCK", "Unverifiable superlative", "Drop unless a disclosed survey backs it"),
    (r"\b(?:scientists?|doctors?|experts?)\s+agree\b", "WARN", "Overstates consensus", "'supported by emerging research' — if true"),
    (r"\b(?:harvard|oxford|cambridge|stanford|ivy[- ]league|mit)\b", "WARN", "Implied institutional endorsement",
     "Cite the actual named study, or drop"),
    (r"\b(?:lowers?|reduces?|balances?|raises?|boosts?)\s+(?:your\s+)?(?:cortisol|serotonin|dopamine|gaba|hormones?|blood\s+sugar)\b",
     "BLOCK", "Specific biochemical mechanism claim without a human RCT", "Drop the mechanism; keep subjective language"),
    (r"\bboosts?\s+(?:your\s+)?immun\w+\b", "WARN", "Implied disease-prevention, especially with illness imagery",
     "'supports normal immune function' — and strip seasonal-illness imagery"),

    # --- outcomes & speed ---
    (r"\blose\s+\d+\s*(?:lbs?|pounds?|kg|kilos?)\b", "BLOCK", "Specific outcome presented as expectation",
     "State the real average result, prominently, next to the claim"),
    (r"\b(?:melts?|burns?)\s+fat\b", "BLOCK", "Weight-loss mechanism claim", "'supports a healthy metabolism'"),
    (r"\b(?:instant|overnight|immediate)\s+(?:results?|relief)\b", "WARN", "Implausible speed",
     "'many people notice a difference in the first week' — if substantiated"),
    (r"\bin\s+(?:just\s+)?\d+\s*(?:days?|hours?|nights?|weeks?)\b", "WARN", "Time-bound outcome claim",
     "Only with substantiation; state what's typical"),
    (r"\b100%\s+(?:natural|safe|effective)\b", "WARN", "Natural is not safe; 100% is absolute",
     "'made with natural ingredients' + the consult-your-doctor line"),

    # --- endorsement & review integrity ---
    (r"\bas\s+seen\s+(?:on|in)\b", "WARN", "Media-endorsement claim", "Only real, verifiable placements"),
    (r"\bresults?\s+not\s+typical\b", "WARN", "Does not by itself cure the deception",
     "State what IS typical, with data, at equal prominence"),
    (r"\b(?:thousands?|millions?)\s+of\s+(?:happy\s+)?(?:customers?|people|reviews?)\b", "WARN",
     "Quantified social proof needs to be real and current", "Use the real, sourced number or drop it"),
    (r"\b\d(?:\.\d)?\s*(?:stars?|/5)\b", "WARN", "On-screen rating must be real and current",
     "Show only real aggregate data, with the source"),
    (r"\bbest\b|\bnumber\s+one\b|\bworld'?s\s+(?:best|leading)\b", "NOTE", "Superlative — needs substantiation",
     "Make it specific and provable, or drop"),

    # --- finance ---
    (r"\bguaranteed\s+returns?\b|\bcan'?t\s+lose\b|\bpassive\s+income\s+guaranteed\b", "BLOCK",
     "Financial guarantee", "Describe the mechanism and the risk; never guarantee a return"),
    (r"\b\d+%\s+(?:returns?|roi|apy)\b", "WARN", "Specific return figure", "Only with the real disclosed basis and period"),

    # --- ⛔ forecast language: a promise to the CLIENT is a claim like any other, and this one is
    # unsubstantiable by construction. A manager with PERFECT premarket knowledge of a work's
    # intrinsic appeal cuts prediction error by 16%, leaving 84% unexplained [PRIMARY · Salganik &
    # Watts, Topics in Cognitive Science 2009]; the best linguistic model picks the winning headline
    # 54.42% of the time; experts pick the better ad 55% of the time. There is no version of this
    # sentence that is true. performance-metrics.md §0.
    (r"\bwill\s+(?:go\s+viral|blow\s+up|perform|convert|win|crush\s+it)\b", "BLOCK",
     "Outcome forecast — unsubstantiable by construction (performance-metrics.md §0)",
     "Say what it TESTS and name the kill/scale threshold: 'H3 against the bank, promote at two "
     "runs above floor'"),
    (r"\b(?:guaranteed|guarantee[sd]?)\s+(?:to\s+)?(?:go\s+viral|virality|views?|reach|engagement)\b",
     "BLOCK", "Guaranteed reach or engagement", "Never guarantee an outcome you do not control"),
    (r"\bvirality\s+scores?\b|\bvirality\s+(?:rating|index|prediction)\b", "WARN",
     "A virality score in a deliverable (performance-metrics.md §0)",
     "No published instrument validates one. Use it as a same-day comparator between two versions "
     "and report the DIRECTION, never the number"),
    (r"\bproven\s+to\s+(?:go\s+viral|convert|perform)\b", "BLOCK",
     "\"Proven to perform\" — the copy-test literature says the opposite",
     "389 split-cable experiments found copy-test measures do not predict sales (Lodish et al. 1995)"),
]

# Add a language key here (e.g. "ro") with translated patterns to lint a non-English script.
CATEGORY_RULES = {
    # ⛔ Researched 2026-09-07 against the regulator's own text for a mattress client. Every rule
    # below traces to a rule or an actual enforcement action IN THIS CATEGORY, which is why they are
    # BLOCK rather than NOTE. `references/compliance.md` and the client's own profile (§4) carry the
    # reasoning; this is the mechanical pass.
    "sleep": [(r"\bknocks?\s+you\s+out\b", "WARN", "Sedation claim", "'helps you wind down'"),
              (r"\bsleep(?:ing)?\s+pills?\b", "NOTE", "Drug comparison — check the implied claim", "Avoid the comparison"),
              # 16 CFR §323.2 — "all or virtually all" components must be US. FTC charged a mattress
              # company $753,000 on this exact pattern (Resident Home / DreamCloud, 2021).
              # $53,088 per violation.
              (r"\bmade\s+in\s+(?:the\s+)?USA\b(?!\s*(?:of|\*|\u2020))|\b100%\s+(?:USA|American)[- ]made\b|"
               r"\bproudly\s+made\s+in\s+America\b", "BLOCK",
               "Unqualified US-origin claim (16 CFR §323.2) — the client's own PDP says 'of U.S. and imported components'",
               "Say the full qualifier on screen, or drop origin: 'family-owned in Arizona since 2010'"),
              # FTC Health Products Compliance Guidance (Dec 2022): a named condition pulls in the
              # RCT expectation. Enforced on a non-drug product in FTC v. Gravity Defyer (2022).
              (r"\b(?:best|top)\s+(?:mattress|bed)\s+for\s+\w+\s*pain\b|\brelieves?\s+\w*\s*pain\b|"
               r"\bcombats?\s+\w*\s*pain\b|\b(?:cures?|fixes|ends)\s+(?:back|neck|joint)\s+pain\b",
               "BLOCK", "Pain-relief claim — needs competent and reliable scientific evidence, RCT-grade",
               "Mechanism, not outcome: 'medium-firm support designed to keep your spine neutral'"),
              (r"\bimproves?\s+(?:your\s+)?sleep\s+quality\b|\bspeeds?\s+(?:up\s+)?(?:muscle\s+)?recovery\b|"
               r"\bsleep\s+deeper\b|\bhelps?\s+you\s+sleep\s+better\b", "BLOCK",
               "Sleep/recovery outcome claim — a health benefit claim with no clinical evidence on file",
               "Describe the construction and let the viewer draw the conclusion"),
              # Green Guides §260.16 — percentage required; §260.4 — no unqualified general benefit.
              # FTC v. Moonlight Slumber (2017): organic/natural/PLANT-BASED mattress claims.
              (r"\bplant[- ]based\b(?![^.]{0,60}\d+\s?%)", "BLOCK",
               "'Plant-based' with no percentage (Green Guides §260.16 requires the percentage stated)",
               "Name the substitution and its scope, with the figure the client supplies in writing"),
              (r"\beco[- ]friendly\b|\bgreen\s+(?:mattress|foam|sleep)\b|\ball[- ]natural\b|"
               r"\bchemical[- ]free\b|\bnon[- ]toxic\b", "BLOCK",
               "Unqualified general environmental/safety claim (Green Guides §260.4)",
               "Name the specific benefit and its basis, or drop it"),
              (r"\bfree\s+of\s+harmful\s+substances\b|\bno\s+(?:VOCs?|off[- ]?gassing)\b", "BLOCK",
               "Broader than CertiPUR-US actually tests (foam only, <0.5ppm VOC) — the exact claim in the Moonlight Slumber order",
               "State what the certification covers, not what it implies"),
              # 16 CFR §255.4 Example 1 is literally a mattress endorsed by a chiropractic association.
              (r"\b(?:doctor|chiropractor|physician)[- ]?(?:recommended|approved|endorsed)\b|"
               r"\bmedical\s+expert\s+approved\b", "WARN",
               "Expert/organisational endorsement (16 CFR §255.4) — needs the evaluation basis, and §255.5 disclosure if paid",
               "On-screen seal only; no voiceover implying doctors chose this over others"),
              # 16 CFR §465.2 — a synthetic presenter claiming personal experience. No disclosure cures it.
              (r"\bI\s+(?:sleep|slept|wake up|woke up)\b|\bmy\s+back\s+pain\b|"
               r"\bsince\s+I\s+(?:got|started\s+using)\s+(?:this|it)\b", "WARN",
               "First-person experience — ⛔ a HARD STOP if the presenter is synthetic (16 CFR §465.2, fake testimonial)",
               "Third person, product facts only: 'Bio-Pur is designed to sleep cooler than traditional memory foam'"),
              # NAD, Tuft & Needle v. Nectar (2019) — a "LIMITED OFFER" that was always available.
              (r"\blimited\s+(?:time\s+)?offer\b|\bends?\s+(?:tonight|today|soon)\b|\bwhile\s+supplies\s+last\b",
               "WARN", "Urgency claim — false urgency is what competitors actually file on in this category",
               "Only with a real end date the client will honour, and record it"),],
    "beauty": [(r"\bbotox\b|\bfiller\b", "WARN", "Comparison to a medical procedure", "Avoid; describe the cosmetic effect"),
               (r"\banti[- ]ag(?:e|ing)\b", "NOTE", "Category term — check imagery", "'supports skin's natural renewal'")],
    "supplements": [(r"\bdosage?\b|\bmg\b", "NOTE", "Dosing language invites a drug reading", "Keep to label language"),
                    # ⛔ Researched 2026-10-21 (lab-00009 R1) against the regulator's own text. Fatty liver
                    # (NAFLD/MASLD, NASH/MASH) is a disease: naming it, or what the product does to it, is a
                    # disease claim — an unapproved drug (21 CFR §101.93(g)). compliance.md §3.
                    (r"\bfatty\s+liver\b|(?-i:\bN?AFLD\b|\bMASLD\b|\bN?ASH\b|\bMASH\b)|"
                     r"\bliver\s+(?:disease|damage|failure)\b|\bcirrhosis\b|\bhepatitis\b", "BLOCK",
                     "Names a liver disease: a disease claim (21 CFR §101.93(g))",
                     "'supports normal liver function', with substantiation and the DSHEA disclaimer"),
                    # FTC v. BASF / DIEM Labs (Hepaxa), 2021: "clinically proven to reduce liver fat".
                    (r"\b(?:reduces?|melts?|clears?|flush(?:es)?|burns?|removes?|dissolves?)\s+(?:the\s+)?"
                     r"(?:liver\s+fat|fat\s+(?:in|from|around)\s+(?:your\s+|the\s+)?liver)\b", "BLOCK",
                     "Liver-fat reduction: the claim the FTC settled in BASF / DIEM Labs (2021)",
                     "Drop the outcome; describe the ingredients' normal-function role, with substantiation"),
                    (r"\bliver\s+inflammation\b|\bscar\s+tissue\b|\bfibrosis\b", "BLOCK",
                     "Organ inflammation or scarring is disease language (FDA: damage to an organ)",
                     "Drop it; no supplement claim covers it"),
                    (r"\binflammation\b", "WARN", "Inflammation claims read as disease mitigation for a supplement",
                     "Name the normal function instead, with substantiation"),
                    # FDA counts claims about a disease's characteristic signs ("reduces cholesterol"); NIDDK names
                    # raised ALT/AST as the sign of NAFLD. Inference — no FDA text names ALT/AST.
                    (r"\b(?:lowers?|reduces?|normali[sz]es?|brings?\s+down)\s+(?:your\s+)?"
                     r"(?:liver\s+enzymes?|(?-i:ALT|AST))\b|(?-i:\b(?:ALT|AST)\b)\s+levels?\b", "BLOCK",
                     "Lowering raised ALT/AST treats a sign of liver disease: an implied disease claim "
                     "(applied from 21 CFR §101.93(g)(2)(ii))",
                     "'helps maintain liver enzyme levels already within the normal range', with substantiation"),
                    # TikTok Ads Policy, Weight Management (August 2026): not allowed.
                    (r"\bwithout\s+(?:any\s+)?(?:diet(?:ing)?|exercise|working\s+out)\b|"
                     r"\bno\s+(?:diet|exercise)\s+(?:needed|required)\b", "BLOCK",
                     "TikTok Weight Management: 'the product alone, without diet or exercise' is not allowed",
                     "'alongside a balanced diet and regular activity'"),
                    # TikTok "Misleading and false content" (April 2026) bans before-and-after comparisons.
                    (r"\bbefore[- ]and[- ]after\b|\bbefore\s*/\s*after\b", "WARN",
                     "TikTok bans before-and-after product-effect comparisons; Meta allows the impact of use "
                     "with the time it took",
                     "Show use and a substantiated timeframe, not a transformation")],
    "finance": [(r"\bsecret\b|\bloophole\b|\bthe\s+banks?\s+don'?t\s+want\b", "BLOCK",
                 "Deceptive-inducement framing", "Drop entirely")],
}

DISCLOSURE_HINTS = [
    (r"\b(?:i|we)\s+(?:tried|used|took|started)\b", "First-person experience — if the presenter is synthetic, "
     "this is a testimonial shape: needs a dramatization disclosure AND the underlying claim substantiated"),
    (r"\b(?:my|our)\s+results?\b", "Personal-result claim — state what's typical at equal prominence"),
    # 16 CFR 465.2(b): the business is liable if it knew or should have known the testimonialist
    # misrepresented that they USED the product or misrepresented THEIR EXPERIENCE of it. The FTC's
    # own red flag: "a business shouldn't provide the text for a testimonial without a reasonable
    # basis to conclude that the text is truthful about the testimonialist's experience."
    (r"\b(?:i|we)(?:'|\u2019)?ve\s+(?:been\s+)?(?:using|sleeping\s+on|had|owned)\b|"
     r"\b(?:for|over)\s+(?:the\s+)?(?:past\s+)?(?:\d+|two|three|four|five|six|nine|ten|twelve|a\s+few|"
     r"several)\s+(?:days?|weeks?|months?|years?)\b",
     "Duration-of-use claim — 16 CFR 465.2(b). Write it to what THIS speaker can actually attest; "
     "a creator who received the product last week cannot say three months"),
]

# Disclosure wording the FTC has specifically called inadequate or ambiguous. Verbatim sources in
# references/compliance.md section 2b.4; verified against the FTC's own FAQ and Disclosures 101
# on 2026-09-07. WARN, not BLOCK: each is wrong AS THE DISCLOSURE and harmless as ordinary copy,
# and only a human can tell which one this line is.
INADEQUATE_DISCLOSURE = [
    (r"#\s?(?:sp|spon|collab|ambassador|partner|client|advisor|consultant|comped|hosted|"
     r"freeproduct|endorsement)\b", "WARN",
     "Ambiguous disclosure tag — the FTC names each of these as insufficient",
     "'#ad' at the START, or 'Paid partnership with <brand>' on screen and spoken"),
    (r"\bgifted\b(?!\s+by\b)", "WARN",
     "'Gifted' alone is ambiguous without a brand reference (FTC FAQ)",
     "'Gifted by <brand>', or 'Thanks <brand> for the free product'"),
    (r"\b(?:sponsored|presented|brought\s+to\s+you)\s+by\b|\bpromoted\b", "WARN",
     "May read as 'underwrote but did not create' — the wrong impression for a brand-produced ad; "
     "'Promoted' is named as one to avoid",
     "'Ad' / 'Advertisement' / 'Paid Advertisement' / 'Paid partnership with <brand>'"),
]

# --- document-level: a material connection with NO adequate disclosure anywhere ---------------
# Per-line regexes cannot see this, because the failure is an ABSENCE. Every FTC video enforcement
# action in compliance.md section 2b is one: Teami, Warner Bros., Lord & Taylor and Machinima all
# reduce to "the disclosure was somewhere the viewer never went" -- which, at script stage, looks
# exactly like "the disclosure was never written".
CONNECTION_SHAPE = re.compile(
    # paid / gifted / commissioned
    r"\bthey\s+sent\s+me\b|\bsent\s+me\s+(?:this|these|those|a|the|their|it)\b|"
    r"\bpartnered\s+with\b|\bteamed\s+up\s+with\b|\bcollab(?:oration)?\s+with\b|"
    r"\bsponsored\s+th(?:is|e)\b|\bpaid\s+me\b|\bcompensated\b|\baffiliate\b|"
    r"\bgifted\s+(?:me|this|to\s+me)\b|\bcommissioned\s+(?:this|me)\b|"
    r"\b(?:brand\s+)?ambassador\b|\bmy\s+(?:discount\s+)?code\b|"
    r"\blink\s+in\s+(?:my\s+)?bio\b|"
    # insider -- 16 CFR 465.5, the branch that carries CIVIL PENALTIES
    r"\bmy\s+(?:company|employer)\b|\bi\s+work\s+(?:for|at|here)\b|"
    r"\b(?:i'm|i’m|i\s+am)\s+(?:the\s+|a\s+|one\s+of\s+the\s+)?"
    r"(?:founder|co-?founder|owner|ceo|cmo|coo|president|"
    r"head\s+of|on\s+the\s+[\w-]+\s+team)\b",
    re.IGNORECASE)

# case-SENSITIVE: a promo code is an all-caps token. Folding case turns "the dress code matters"
# into a material connection.
CODE_SHAPE = re.compile(r"\bcode\s+[A-Z][A-Z0-9]{2,11}\b")

# What counts as the disclosure. ⛔ This one is asymmetric: a false NEGATIVE costs a nuisance
# finding, a false POSITIVE certifies an undisclosed ad. So the bare word "ad" is NOT enough --
# it appears in "ad concept 3", "ad-lib", "ad hoc", "Ad name:", and in the ad-name join key
# batch_plan.py generates. A hashtag is unambiguous; a bare label counts only when it IS the
# whole overlay line; everything else has to be one of the FTC's own multiword forms
# (compliance.md 2b.4). "dramatization" is deliberately absent: it satisfies a DIFFERENT
# obligation (compliance.md section 0, row 2) and accepting it here would implement the exact
# error that section exists to prevent.
_LABEL = (r"(?:ads?|advert|advertisement|paid\s+ad|paid\s+advertisement|paid\s+partnership|"
          r"sponsored|sponsored\s+advertising\s+content)")
ADEQUATE_DISCLOSURE = re.compile(
    r"#ad\b|#advertisement\b|#paidpartnership\b|"
    r"^[\s>|*\-]*(?:\*\*)?(?:OVERLAY|SUPER|TEXT|CAPTION|ON-?SCREEN|TITLE|VO|LOWER\s*THIRD)?"
    r"\s*:?\s*(?:\*\*)?" + _LABEL + r"(?:\*\*)?\s*[.:!]?\s*$|"
    r"\bpaid\s+partnership\b|\bthis\s+(?:video\s+)?is\s+an\s+ad\b|"
    r"\bpaid\s+advertisement\b|\bsponsored\s+advertising\s+content\b|"
    r"\bpaid\s+for\s+by\s+(?!the\s+(?:client|brand|agency|company|studio)\b)\w|"
    r"\bpaid\s+me\s+to\b|\bthanks?\b[^.\n]{0,40}\bfor\s+the\s+free\b|"
    r"\bmy\s+(?:company|employer)(?:'|’)?s\b",
    re.IGNORECASE | re.MULTILINE)


def disclosure_check(text: str, declared_paid: bool, asserted_none: bool = False) -> tuple[list[dict], str]:
    """Is a material connection disclosed ANYWHERE in this script? Returns (findings, state).

    Four states, and only one of them is a pass:
      DISCLOSED    a connection exists and the script carries an adequate disclosure
      UNDISCLOSED  a connection exists and it does not                        -> BLOCK
      NOT ASSERTED nobody said whether there is one and the words gave nothing away -> finding
      NONE         a human asserted there is no material connection (--no-material-connection)

    NOT ASSERTED is deliberately not silent. The language check next door already treats "I could
    not look" as a result rather than a pass (self-evolution.md 6b, the SILENT PASS rule), and this
    is the same shape: --paid is not inferable from a script's words, so a run that never asked is
    evidence of nothing. Answer it either way and the finding goes away.
    """
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith(("<!--", "_Saved")))
    hits = [m.group(0) for m in CONNECTION_SHAPE.finditer(body)] + \
           [m.group(0) for m in CODE_SHAPE.finditer(body)]
    if not declared_paid and not hits:
        if asserted_none:
            return [], "NONE"
        return ([{"line": 0, "match": "(document)", "severity": "NOTE",
                  "why": "Material connection NOT ASSERTED — no connection was declared and none was "
                         "detected in the words, so this question was never answered",
                  "reframe": "Pass --paid if any creator here is paid, gifted, commissioned or "
                             "employed (the normal case for UGC), or --no-material-connection to "
                             "record that there is none. compliance.md section 2b",
                  "text": "(whole script)"}], "NOT ASSERTED")
    m = ADEQUATE_DISCLOSURE.search(body)
    if not m:
        why = ("Material connection with no adequate disclosure anywhere in the script"
               + (f" (triggered by {hits[0]!r})" if hits else " (--paid was declared)"))
        return ([{"line": 0, "match": "(document)", "severity": "BLOCK", "why": why,
                  "reframe": "Write the disclosure INTO the script: burned-in caption-layer text "
                             "from frame one AND the first spoken line. 'Paid partnership with "
                             "<brand>' or '<brand> paid me to make this'. compliance.md section 2b",
                  "text": "(whole script)"}], "UNDISCLOSED")
    # placement: the FTC grades the same words differently at the top and at the bottom
    lines = [l for l in body.splitlines() if l.strip()]
    upto = body[:m.start()].count("\n")
    seen_before = len([l for l in body.splitlines()[:upto] if l.strip()])
    out: list[dict] = []
    if lines and seen_before > max(1, len(lines) // 4):
        out.append({"line": upto + 1, "match": m.group(0).strip()[:40], "severity": "WARN",
                    "why": "Disclosure present but LATE — the FTC grades the same words weaker "
                           "further down: 'easier to miss and thus less likely to be effective'",
                    "reframe": "Move it to frame one, on screen and in the first spoken line "
                               "(compliance.md section 2b.3)",
                    "text": (lines[min(seen_before, len(lines) - 1)] or "")[:110]})
    return out, "DISCLOSED"


SPOKEN = re.compile(r"^\s*(?:[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț '\-]{1,30}:|>|-)\s*")

# ------------------------------------------------------------------ mention vs use
# ⛔ THE DEFECT THIS FIXES (2026-09-08). The lint scanned every line of the file, so a script's own
# COMPLIANCE NOTES tripped it: a note reading `never say "Made in the USA" unqualified` reported a
# BLOCK for 'Made in the USA'; `no disclosure cures it` reported a cure claim; `a body-shaped
# depression` reported a diagnosable condition. Four BLOCKs, all of them the writer doing the right
# thing. That is worse than noise — it teaches a writer that the way to a clean lint is to DELETE
# the reasoning that says why the phrase is forbidden, which is exactly backwards.
#
# The distinction the old version could not draw is MENTION vs USE. A phrase is a claim when it
# reaches the audience; discussing it in production prose is not a claim. So each line is placed in
# one of three tiers and severity follows the tier:
#
#   VOICED   a spoken line, a TEXT/CAPTION/OVERLAY record — what the audience hears or reads.
#            Severity stands. This is the tier that ships.
#   IMAGERY  a scene slug, a shot or B-roll description, wardrobe, end frames — what the audience
#            SEES. Severity also stands, and deliberately: Green Guides section 260.4's own example
#            holds that imagery alone can carry an environmental claim with no words at all
#            (compliance.md; the client's own profile, section 4). A picture is a claim.
#   NOTE     production prose: briefs, director's notes, compliance notes, headings. Downgraded to
#            NOTE and labelled as a mention, never silently dropped — a human still sees it.
#
# ⛔ AND THE SAFE DEFAULT, which is the part that makes this safe to ship. The tiering is only
# applied when the file actually PARSES as a script — at least one voiced line found. A file with no
# recognisable spoken lines has no structure to read, so nothing is downgraded and the report says
# the tiering did not run. That is this file's own rule from the top: a checker must distinguish
# "I looked and found nothing" from "I could not look."
VOICED_RE = re.compile(
    r"^\s*(?:<?[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț '\-]{0,30}>?\s*:\s*[„\"“'])"      # NARRATOR: „line"
    r"|<\s*TEXT\b"                                                              # <TEXT record: "...">
    r"|^\s*(?:TEXT|CAPTION|OVERLAY|SUPER|VO|V\.O\.)\b\s*[:\-]",                 # TEXT: / CAPTION:
    re.I)
IMAGERY_LINE_RE = re.compile(r"^\s*(?:\[(?:HOOK|SCENE|SCEN[ĂA]|SZENE|SCÈNE|ESCENA|CTA)\b|S\d+[A-Z]?\s*[—–-])", re.I)
IMAGERY_HEAD_RE = re.compile(r"b-?roll|insert|end frame|wardrobe|shot ?list|storyboard|"
                             r"art direction|production design|set|prop", re.I)
SCRIPT_HEAD_RE = re.compile(r"^##+\s*(?:script|scene|hook|cta)\b", re.I)
HEAD_RE_CL = re.compile(r"^(#+)\s*(.*)$")


def tier_lines(text: str) -> tuple[list[str], bool]:
    """One tier per line: 'voiced' | 'imagery' | 'note'. Second value: did the file parse as a script?

    Parsing means at least one VOICED line was found. When it did not parse, every line comes back
    'voiced' so that nothing is downgraded — see the note above.
    """
    lines = text.splitlines()
    tiers, section = [], "note"
    for line in lines:
        h = HEAD_RE_CL.match(line)
        if h:
            title = h.group(2)
            if SCRIPT_HEAD_RE.match(line):
                section = "imagery"          # inside the SCRIPT block, slugs are imagery
            elif IMAGERY_HEAD_RE.search(title):
                section = "imagery"
            else:
                section = "note"
            tiers.append("note")
            continue
        if VOICED_RE.search(line):
            tiers.append("voiced")
        elif IMAGERY_LINE_RE.match(line):
            tiers.append("imagery")
        else:
            tiers.append(section if section == "imagery" else "note")
    parsed = "voiced" in tiers
    if not parsed:
        return ["voiced"] * len(lines), False
    return tiers, True


# ------------------------------------------------------------------ the client's restricted words
# ⛔ clients/_TEMPLATE.md §4 carried "Restricted words for this brand" and no script read it, so a word
# the client had banned reached `gate.py approve script` as clean. The field now has a list form, which
# the template documents and this reads:
#   - **Restricted words for this brand:** <free text — ignored once items follow>
#     - `cheap` → `affordable`
#     - `guarantee`
# One indented item per word or phrase, the word in backticks; `→` (or `->`) and the agreed
# replacement(s) in backticks; anything after the last backtick is a note and is not read. The label
# must be exactly "Restricted words" or "Restricted words for this brand": a differently scoped field
# ("Restricted words in alt text") is not this list and is left alone.
RESTRICTED_FIELD_RE = re.compile(
    r"^(\s*)[-*]\s+\*\*\s*Restricted\s+words(?:\s+for\s+this\s+brand)?\s*:?\s*\*\*\s*:?\s*(.*)$", re.I)
RESTRICTED_ITEM_RE = re.compile(r"^\s*[-*]\s+`([^`]+)`(.*)$")
RESTRICTED_ARROW_RE = re.compile(r"^\s*(?:→|->|=>)\s*(.*)$")
# gate.py's PLACEHOLDER_RE: an unfilled template line is an unanswered field, never a word to ban
PLACEHOLDER_CL = re.compile(r"<[^<>\n]{1,80}>|NEEDS INPUT|\bTBD\b|\?\?\?", re.I)


def parse_restricted(text: str) -> dict:
    """The profile's restricted-words list.

    state: LIST (words found) · NONE (the field says `none`) · UNANSWERED (empty or a placeholder) ·
    UNREAD (written, but not in the list form — reported, never passed as clean) · ABSENT (no field).
    words: [(word, [agreed replacements])]. unread: item lines that are not in the list form."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = RESTRICTED_FIELD_RE.match(line)
        if not m:
            continue
        indent = len(m.group(1).expandtabs())
        inline = m.group(2).strip()
        words, unread = [], []
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            if len(nxt.expandtabs()) - len(nxt.expandtabs().lstrip()) <= indent:
                break
            s = nxt.strip()
            if not s.startswith(("-", "*")):
                continue                                   # the field's own text, wrapped
            it = RESTRICTED_ITEM_RE.match(nxt)
            if not it:
                unread.append(s)
                continue
            word = " ".join(it.group(1).split())
            if not word or PLACEHOLDER_CL.search(word):
                continue                                   # the template's own example items
            reps = []
            arrow = RESTRICTED_ARROW_RE.match(it.group(2))
            if arrow:
                reps = [" ".join(r.split()) for r in re.findall(r"`([^`]+)`", arrow.group(1))
                        if r.strip() and not PLACEHOLDER_CL.search(r)]
            words.append((word, reps))
        if words:
            state = "LIST"
        elif unread:
            state = "UNREAD"
        elif re.match(r"^[`'\"*]*none\b", inline, re.I):
            state = "NONE"
        elif not inline or PLACEHOLDER_CL.search(inline):
            state = "UNANSWERED"
        else:
            state = "UNREAD"                               # prose on the field line, no list items
            unread = [inline[:110]]
        return {"state": state, "words": words, "unread": unread, "field_line": i + 1}
    return {"state": "ABSENT", "words": [], "unread": [], "field_line": 0}


def _job_of(path: str) -> str | None:
    """The job folder a linted file sits in: the nearest ancestor with 00-brief/CHECKPOINT.md."""
    d = os.path.dirname(os.path.abspath(path))
    for _ in range(12):
        if os.path.isfile(os.path.join(d, "00-brief", "CHECKPOINT.md")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


def _checkpoint_client(job: str) -> str:
    """The CHECKPOINT's `Client:` value, read as gate.py's parse_kv reads it (first occurrence wins;
    fence, heading and quote lines skipped)."""
    try:
        with open(os.path.join(job, "00-brief", "CHECKPOINT.md"), encoding="utf-8") as fh:
            txt = fh.read()
    except OSError:
        return ""
    for line in txt.splitlines():
        if line.startswith(("```", "#", ">")):
            continue
        m = re.match(r"^client\s*:\s*(.*)$", line, re.I)
        if m:
            return m.group(1).strip().strip("`'\"").strip()
    return ""


def resolve_profile(client: str, job: str) -> str | None:
    """Where the profile a CHECKPOINT names is, in gate.py's order (Job.validate, then find_profile):
    the written path; CINE_CLIENTS (else the plugin's clients/); a `_cine-clients/` above the job; the
    plugin's clients/. A copy of that order, because gate.py is not imported here: it is the approval's
    own module, and the lint must run standalone."""
    if not client:
        return None
    try:
        import cine_home as _ch                       # stdlib-only, beside this file
        cfg = _ch.config_dir("clients_dir")
    except ImportError:
        cfg = None
    clients = os.environ.get("CINE_CLIENTS") or cfg or os.path.join(SKILL_ROOT, "clients")
    base = os.path.basename(client)
    base = base if base.endswith(".md") else f"{base}.md"
    if os.path.isabs(client):
        cand = client
    elif client.startswith("clients/") or "/" not in client:
        cand = os.path.join(clients, base)
    else:
        cand = os.path.join(SKILL_ROOT, client)
    if os.path.isfile(cand):
        return cand
    dirs, d = [clients], os.path.abspath(job)
    for _ in range(12):
        dirs.append(os.path.join(d, "_cine-clients"))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    dirs.append(os.path.join(SKILL_ROOT, "clients"))
    for dd in dirs:
        p = os.path.join(dd, base)
        if os.path.isfile(p):
            return p
    return None


def restricted_for(path: str, profile: str | None, no_profile: bool = False) -> dict:
    """The restricted-words list that applies to one linted file, and where it came from."""
    if no_profile:
        return {"state": "SKIPPED", "why": "--no-profile", "profile": None, "words": [], "unread": []}
    src = "--profile"
    if not profile:
        job = _job_of(path)
        client = _checkpoint_client(job) if job else ""
        profile = resolve_profile(client, job) if client else None
        src = "CHECKPOINT"
        if not profile:
            why = ("no client profile found — pass --profile, or lint a file inside a job whose "
                   "00-brief/CHECKPOINT.md names one") if not client else \
                  f"the CHECKPOINT names {client!r} and no such profile was found"
            return {"state": "SKIPPED", "why": why, "profile": None, "words": [], "unread": []}
    try:
        with open(profile, encoding="utf-8") as fh:
            got = parse_restricted(fh.read())
    except OSError as e:
        return {"state": "SKIPPED", "why": f"the profile could not be read ({e})", "profile": profile,
                "words": [], "unread": []}
    got.update(profile=profile, source=src)
    return got


def _phrase_re(phrase: str):
    """Case-insensitive, on word boundaries, any run of whitespace between the words. The lookarounds
    are `\\w`-based rather than `\\b`, so a phrase that starts or ends on punctuation (`#1`, `24/7`)
    still has a boundary."""
    body = r"\s+".join(re.escape(p) for p in phrase.split())
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE)


def _profile_label(p: str | None) -> str:
    if not p:
        return "the client profile"
    rel = os.path.relpath(p, SKILL_ROOT)
    return rel if not rel.startswith("..") else os.path.basename(p)



def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def lint(text: str, category: str | None, allow: list[str],
         strict: bool = False, restricted: list | None = None,
         restricted_src: str | None = None) -> list[dict]:
    rules = list(RULES) + CATEGORY_RULES.get((category or "").lower(), []) + INADEQUATE_DISCLOSURE
    allowed = [a.lower() for a in allow]
    # the client's own restricted words, each with the replacement(s) the client agreed
    banned = [(w, _phrase_re(w), [_phrase_re(r) for r in reps], reps) for w, reps in (restricted or [])]
    out: list[dict] = []
    tiers, parsed = tier_lines(text)
    if strict:
        tiers, parsed = ["voiced"] * len(tiers), parsed
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "<!--", "|--", "_Saved")):
            continue
        low = line.lower()
        # spans of client-approved phrases on this line; a finding is suppressed ONLY if it falls
        # inside one of them — approving "clinically proven" must not whitelist "cures insomnia"
        # sitting on the same line.
        allowed_spans = []
        for a in allowed:
            start = low.find(a)
            while start != -1:
                allowed_spans.append((start, start + len(a)))
                start = low.find(a, start + 1)
        for pat, sev, why, fix in rules:
            for m in re.finditer(pat, line, re.IGNORECASE):
                hit = m.group(0)
                if any(s0 <= m.start() and m.end() <= e0 for s0, e0 in allowed_spans):
                    continue
                tier = tiers[lineno - 1]
                sev2, why2 = sev, why
                if tier == "note" and sev != "NOTE":
                    # A MENTION, not a use: the phrase is in production prose, which does not ship.
                    # Downgraded and relabelled, never dropped — a human still reads it.
                    sev2 = "NOTE"
                    why2 = (f"MENTION (production prose, not spoken or on screen) — {why}. "
                            f"Not a claim as written; check the phrase never reaches a voiced line "
                            f"or an image. --strict scores every line as voiced.")
                out.append({"line": lineno, "match": hit, "severity": sev2, "tier": tier,
                            "why": why2, "reframe": fix, "text": stripped[:110]})
        # a restricted word is a BLOCK wherever it is voiced or seen; inside the replacement
        # the client agreed it passes, and inside an --allow span it is suppressed like any finding.
        for word, pat, rep_pats, reps in banned:
            rep_spans = [(m.start(), m.end()) for rp in rep_pats for m in rp.finditer(line)]
            for m in pat.finditer(line):
                if any(s0 <= m.start() and m.end() <= e0 for s0, e0 in allowed_spans + rep_spans):
                    continue
                tier = tiers[lineno - 1]
                why = (f"Restricted word for this brand — {_profile_label(restricted_src)} §4 lists "
                       f"{word!r}")
                sev2 = "BLOCK"
                if tier == "note":
                    sev2 = "NOTE"
                    why = (f"MENTION (production prose, not spoken or on screen) — {why}. Not a use as "
                           f"written; check it never reaches a voiced line or an image. --strict "
                           f"scores every line as voiced.")
                fix = (("Use the replacement the client agreed: " + " / ".join(repr(r) for r in reps))
                       if reps else "No replacement agreed — rewrite without it, or ask the client for "
                                    "one and add it to the profile (`word` → `replacement`)")
                out.append({"line": lineno, "match": m.group(0), "severity": sev2, "tier": tier,
                            "why": why, "reframe": fix, "text": stripped[:110]})
        for pat, why in DISCLOSURE_HINTS:
            if re.search(pat, line, re.IGNORECASE):
                out.append({"line": lineno, "match": "(shape)", "severity": "NOTE",
                            "tier": tiers[lineno - 1],
                            "why": why, "reframe": "See compliance.md section 2", "text": stripped[:110]})
    if not parsed:
        out.append({"line": 0, "match": "(document)", "severity": "NOTE", "tier": "voiced",
                    "why": "MENTION/USE TIERING DID NOT RUN — no spoken line was found, so this "
                           "file does not parse as a script and EVERY line was scored as voiced. "
                           "That is the conservative direction, but it means a production note "
                           "reads here as a claim. Expect false BLOCKs on a prose document.",
                    "reframe": "Run it on the SCRIPT artifact, in the house format "
                               "(references/script-format.md), or accept the over-reporting",
                    "text": "(whole document)"})
    return out


def _restricted_line(r: dict) -> str:
    """The per-file status of the client's restricted-words check, in the disclosure line's
    shape: it says whether the check ran, never only what it found."""
    st, lab = r.get("state"), _profile_label(r.get("profile"))
    if st == "LIST":
        n = len(r.get("words") or [])
        agreed = sum(1 for _, reps in r.get("words") or [] if reps)
        return (f"restricted words: CHECKED — {n} from {lab} §4 ({agreed} with an agreed replacement)"
                + (f"; {len(r['unread'])} item(s) NOT READ, see the NOTE" if r.get("unread") else ""))
    if st == "NONE":
        return f"restricted words: NONE — {lab} §4 records that the client has no list"
    if st == "UNANSWERED":
        return f"restricted words: SKIPPED — {lab} §4 leaves the field unanswered (a placeholder or empty)"
    if st == "UNREAD":
        return f"restricted words: NOT READ — {lab} §4 is not in the list form (see the NOTE)"
    if st == "ABSENT":
        return f"restricted words: SKIPPED — {lab} has no \"Restricted words for this brand\" field"
    return f"restricted words: SKIPPED — {r.get('why', 'not checked')}"


def _restricted_note(r: dict) -> list[dict]:
    """A list the lint could not read is reported, not passed (the SILENT PASS rule at the top)."""
    if not r.get("unread"):
        return []
    return [{"line": 0, "match": "(profile)", "severity": "NOTE", "tier": "voiced",
             "why": f"Restricted words NOT READ — {_profile_label(r.get('profile'))} §4 has "
                    f"{len(r['unread'])} entr(y/ies) not in the list form, so those words were not "
                    f"checked: " + " · ".join(x[:60] for x in r["unread"][:3]),
             "reframe": "One indented item per word: - `word` → `the agreed replacement` "
                        "(clients/_TEMPLATE.md §4)",
             "text": "(client profile)"}]


def _disclosure_line(state: str) -> str:
    return {
        "NONE": "disclosure: NONE — recorded by a human as having no material connection",
        "NOT ASSERTED": "disclosure: NOT ASSERTED — nobody said whether a creator here is paid, "
                        "gifted, commissioned or employed, and the words gave nothing away. This "
                        "is not a pass. Pass --paid or --no-material-connection.",
        "DISCLOSED": "disclosure: DISCLOSED — a material-connection disclosure is written into "
                     "the script (verify it survives the edit and the reframe: compliance.md 2b.6)",
        "UNDISCLOSED": "disclosure: UNDISCLOSED — see the BLOCK above",
    }.get(state, f"disclosure: {state}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts", nargs="*", help="script .md file(s)")
    ap.add_argument("--category", help="sleep | beauty | supplements | finance")
    ap.add_argument("--allow", action="append", default=[],
                    help="a phrase the client has approved in writing (repeatable). Record the approval.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="findings only")
    ap.add_argument("--paid", action="store_true",
                    help="a creator on this script is paid, gifted, commissioned or employed — the "
                         "normal case for UGC, and NOT inferable from the words. Turns the "
                         "document-level disclosure check on unconditionally.")
    ap.add_argument("--no-material-connection", action="store_true",
                    help="record that NOBODY on this script is paid, gifted, commissioned or "
                         "employed by the brand. The honest alternative to --paid; one of the two "
                         "has to be true, and neither leaves the question unanswered.")
    ap.add_argument("--strict", action="store_true",
                    help="score EVERY line as voiced — disables the mention/use tiering, so a "
                         "phrase discussed in a production note reports at full severity. Use it "
                         "on a document that is not a script in the house format.")
    ap.add_argument("--lang-ok", action="store_true",
                    help="the rules DO cover this script's language — suppress the INCONCLUSIVE "
                         "result. Pass it only after localising the patterns; a clean run on a "
                         "language the rules cannot read is not evidence of anything")
    # the client profile whose §4 restricted words are checked
    ap.add_argument("--profile", metavar="PROFILE.md",
                    help="the client profile to read §4 \"Restricted words for this brand\" from. "
                         "Default: the profile the job's 00-brief/CHECKPOINT.md `Client:` names, "
                         "found as gate.py finds it")
    ap.add_argument("--no-profile", action="store_true",
                    help="do not look for a client profile: the restricted-words check is skipped "
                         "and the report says so")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.profile and not os.path.isfile(a.profile):
        print(f"error: --profile {a.profile} not found", file=sys.stderr)
        return 2

    paths: list[str] = []
    for pattern in a.scripts:
        paths.extend(sorted(glob.glob(pattern)) or [pattern])

    all_findings, worst = {}, 0
    coverage, inconclusive, disclosure, restricted = {}, [], {}, {}
    for p in paths:
        try:
            text = read(p)
            rs = restricted_for(p, a.profile, a.no_profile)            #
            findings = lint(text, a.category, a.allow, strict=a.strict,
                            restricted=rs.get("words"), restricted_src=rs.get("profile"))
            findings += _restricted_note(rs)
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        restricted[p] = {"state": rs.get("state"), "profile": rs.get("profile"),
                         "words": len(rs.get("words") or []), "unread": len(rs.get("unread") or []),
                         "status": _restricted_line(rs)}
        dis_findings, dis_state = disclosure_check(text, a.paid, a.no_material_connection)
        findings += dis_findings
        disclosure[p] = dis_state
        cov = language_coverage(text)
        coverage[p] = cov
        if not cov["readable"] and not a.lang_ok:
            inconclusive.append(p)
            worst = max(worst, 1)
        all_findings[p] = findings
        if any(f["severity"] == "BLOCK" for f in findings):
            worst = max(worst, 2)
        elif findings:
            worst = max(worst, 1)

    if a.json:
        print(json.dumps({"findings": all_findings, "coverage": coverage,
                          "inconclusive": inconclusive, "disclosure": disclosure,
                          "restricted": restricted},                      #
                         indent=2, ensure_ascii=False))
    else:
        for p, findings in all_findings.items():
            if not findings and a.quiet:
                if disclosure.get(p) not in ("DISCLOSED", "NONE"):
                    print(f"\n=== {p} ===\n  " + _disclosure_line(disclosure.get(p, "?")))
                continue
            print(f"\n=== {p} ===")
            cov = coverage.get(p, {})
            if p in inconclusive:
                print(f"  ⛔ INCONCLUSIVE — the rules are ENGLISH and this script does not read as "
                      f"English ({cov.get('en_markers', 0)} function words in "
                      f"{cov.get('tokens', 0)} tokens, {cov.get('en_ratio', 0):.1%}).")
                print(f"  Nothing matched because nothing COULD match. This is not a clean run and "
                      f"it is not evidence of anything.")
                print(f"  Localise the patterns in references/compliance.md §4 into this language, "
                      f"or lint an English gloss, or pass --lang-ok if you have done so already.")
                if findings:
                    print(f"  ({len(findings)} finding(s) below came from language-independent "
                          f"patterns and are still real.)")
                if not findings:
                    continue
            elif not findings:
                print(f"  clean — nothing on the known list "
                      f"({cov.get('tokens', 0)} tokens scanned).")
                print("  " + _disclosure_line(disclosure.get(p, "?")))
                print("  " + restricted[p]["status"])                     #
                continue
            print("  " + _disclosure_line(disclosure.get(p, "?")))
            print("  " + restricted[p]["status"])                         #
            for f in sorted(findings, key=lambda x: ({"BLOCK": 0, "WARN": 1, "NOTE": 2}[x["severity"]], x["line"])):
                print(f"  [{f['severity']:5}] line {f['line']:>3}  {f['match']!r}")
                print(f"          why:     {f['why']}")
                print(f"          reframe: {f['reframe']}")
                print(f"          in:      {f['text']}")
        print("\n" + "-" * 72)
        print("A clean run means 'nothing on the known list'. It does not clear the NET IMPRESSION —")
        print("read the script WITH the shot descriptions before shipping. See references/compliance.md.")
    return 1 if worst else 0


def selftest() -> int:
    """⛔ Both directions. A coverage check that never fires is decoration; one that fires on the
    language it DOES cover is worse than nothing, because it trains people to pass --lang-ok."""
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    en = ('ANA: "The zoned cutouts are shaped in a hexagonal grid."\n'
          'ANA: "You get a hundred nights to try it, and a twenty-year warranty."')
    ro = ('ANA: "Salteaua noastră vindecă durerile de spate în trei nopți."\n'
          'ANA: "Fabricată integral în România, din materiale complet naturale."')
    check("plain English reads as readable", language_coverage(en)["readable"])
    check("Romanian does NOT", not language_coverage(ro)["readable"])
    check("empty text is not readable, and says so", not language_coverage("")["readable"])
    check("a denominator is always reported", language_coverage(en)["tokens"] > 0)
    # ⛔ the dangerous false positive: terse English that is still English
    terse = 'ANA: "Twenty years."\nANA: "A hundred nights."\nANA: "That is the offer."'
    check("terse but real English still reads as readable", language_coverage(terse)["readable"])
    # ...and the rules themselves still fire on English
    # ---------------------------------------------------------------- MENTION vs USE
    # ⛔ Four real BLOCKs on 2026-09-08 were all the writer doing the right thing: a compliance note
    # saying never to say a phrase reported the phrase. Downgrading a mention is safe ONLY while a
    # use is still caught and the parse is still honest — all three are pinned here.
    SCRIPT_FIXTURE_CL = (
        "# Script v3\n\n"
        "## SCRIPT\n\n"
        "[HOOK 0:00-0:06]  a bare mattress in low side light\n"
        'NARRATOR: "Sag past an inch and a half and they replace it."\n\n'
        "## Compliance notes\n"
        '1. Never say "Made in the USA" unqualified, and no disclosure cures it.\n')
    tiers, parsed = tier_lines(SCRIPT_FIXTURE_CL)
    check("a script in the house format parses", parsed)
    lines = SCRIPT_FIXTURE_CL.splitlines()
    check("the spoken line is scored as VOICED", tiers[lines.index(
        'NARRATOR: "Sag past an inch and a half and they replace it."')] == "voiced")
    check("a scene slug is scored as IMAGERY — a picture is a claim",
          tiers[lines.index("[HOOK 0:00-0:06]  a bare mattress in low side light")] == "imagery")
    note_i = lines.index('1. Never say "Made in the USA" unqualified, and no disclosure cures it.')
    check("a compliance note is scored as NOTE", tiers[note_i] == "note")
    f = lint(SCRIPT_FIXTURE_CL, "sleep", [])
    blocks = [h for h in f if h["severity"] == "BLOCK"]
    check("⛔ the compliance note no longer BLOCKS its own forbidden phrase", not blocks)
    check("...but the phrase is still REPORTED, as a mention",
          any(h["match"].lower() == "made in the usa" and "MENTION" in h["why"] for h in f))
    used = lint(SCRIPT_FIXTURE_CL.replace(
        '"Sag past an inch and a half and they replace it."',
        '"Made in the USA. It cures back pain."'), "sleep", [])
    check("⛔ and the same phrase in a SPOKEN line is still a BLOCK — the downgrade is not a hole",
          any(h["severity"] == "BLOCK" and h["match"].lower() == "made in the usa" for h in used))
    check("--strict scores the note at full severity again",
          any(h["severity"] == "BLOCK" for h in lint(SCRIPT_FIXTURE_CL, "sleep", [], strict=True)))
    prose = "This document explains that a product must never be called Made in the USA unqualified."
    pf = lint(prose, "sleep", [])
    check("⛔ a file with NO spoken line does not get tiered — it scores everything as voiced",
          any(h["severity"] == "BLOCK" for h in pf))
    check("...and it SAYS the tiering did not run, rather than passing silently",
          any("TIERING DID NOT RUN" in h["why"] for h in pf))

    hits = lint('ANA: "Made in the USA. It cures back pain."', "sleep", [])
    # --- disclosure, the check whose failure mode is an ABSENCE (compliance.md 2b) ------------
    # ⛔ Asymmetric: a false negative is a nuisance finding, a false POSITIVE certifies an
    # undisclosed ad. Every row below is a real string an adversarial reader produced against an
    # earlier version of this check that matched the bare word "ad" and passed all of them.
    paid = "HOST: They sent me this mattress. Use my code SLEEP20."
    for txt, flag, want in [
        (paid, False, "UNDISCLOSED"),
        ("# Ad concept 3 — the 3am ceiling\n" + paid, True, "UNDISCLOSED"),
        ("HOST: let her ad-lib the last line. " + paid, False, "UNDISCLOSED"),
        ("Ad name: ACME-B1-H01-P1-a\n" + paid, False, "UNDISCLOSED"),
        ("HOST: the lighting was ad hoc. " + paid, False, "UNDISCLOSED"),
        ("TODO: we still need an ad disclosure burned in\n" + paid, False, "UNDISCLOSED"),
        ("OVERLAY: Dramatization\n" + paid, False, "UNDISCLOSED"),
        ("OVERLAY: Paid partnership with Acme\n" + paid, False, "DISCLOSED"),
        ("OVERLAY: #ad\n" + paid, False, "DISCLOSED"),
        ("HOST: Acme paid me to make this. " + paid, False, "DISCLOSED"),
        ("HOST: I'm the founder of Acme and I sleep on it nightly.", False, "UNDISCLOSED"),
        ("HOST: I work for Acme, and this is my company's mattress.", False, "DISCLOSED"),
        ("HOST: mornings are hard.", False, "NOT ASSERTED"),
        ("HOST: the dress code matters.", False, "NOT ASSERTED"),
        ("HOST: talent paid by the client.", False, "NOT ASSERTED"),
        ("HOST: mornings are hard.", True, "UNDISCLOSED"),
    ]:
        got = disclosure_check(txt, flag)[1]
        check(f"disclosure {want:<12} {txt.splitlines()[0][:44]!r}", got == want)
    check("...and UNDISCLOSED is a BLOCK",
          any(x["severity"] == "BLOCK" for x in disclosure_check(paid, False)[0]))
    check("...and NOT ASSERTED is a finding, never silence",
          any(x["severity"] for x in disclosure_check("HOST: hi.", False)[0])
          and "not a pass" in _disclosure_line("NOT ASSERTED").lower())
    check("...and asserting there is none clears it",
          disclosure_check("HOST: hi.", False, True) == ([], "NONE"))
    check("a disclosure buried at the bottom still WARNs on placement",
          any(x["severity"] == "WARN"
              for x in disclosure_check("HOST: they sent me this.\n" * 8 + "OVERLAY: #ad", False)[0]))
    tags = lint("HOST: gifted, honestly. #spon. Sponsored by Acme.", None, [])
    check("the FTC's named-inadequate tags fire",
          {h["match"].lower() for h in tags} >= {"#spon", "gifted"})
    check("...and 'gifted by <brand>' does not",
          not any(h["match"].lower() == "gifted" for h in lint("HOST: gifted by Acme.", None, [])))
    check("duration-of-use is flagged as an experience claim",
          any("Duration-of-use" in h["why"] for h in
              lint("HOST: I've been sleeping on it for three months.", None, [])))

    # ---------------------------------------------------------------- personal attributes and liver claims
    # (lab-00009 R1, 2026-10-21): Meta's own rejected example, the FDA disease line, and no false fire on
    # the everyday words the case-sensitive acronyms would otherwise catch.
    pa = lint('HOST: "Do you have fatty liver?"', "supplements", [])
    check("a health question WARNs as a Meta personal attribute",
          any("Personal attributes" in h["why"] for h in pa))
    check("...and fatty liver BLOCKs as a disease claim under supplements",
          any(h["severity"] == "BLOCK" and "liver disease" in h["why"] for h in pa))
    check("lowering ALT levels BLOCKs as an implied disease claim",
          any(h["severity"] == "BLOCK" for h in lint('HOST: "It lowers your ALT levels."', "supplements", [])))
    check("...while 'mash', 'ash' and 'last' do not fire",
          not lint('HOST: "Mash the potatoes, sweep the ash, and last of all rest."', "supplements", []))
    check("'without diet or exercise' BLOCKs (TikTok Weight Management)",
          any(h["severity"] == "BLOCK" for h in lint('HOST: "Works without diet or exercise."', "supplements", [])))
    check("an age call-out WARNs", any("age call-out" in h["why"]
                                       for h in lint('HOST: "If you\'re over 40, watch this."', None, [])))
    check("the English rules still fire", any(f["severity"] == "BLOCK" for f in hits))
    check("...and name the line", all(f.get("line") for f in hits))

    # ---------------------------------------------------------------- the client's restricted words
    # ⛔ The field existed and nothing read it. Pinned here: the list form parses, every other form says
    # what it is (never a silent clean), a word is caught where it ships and passes inside its agreed
    # replacement, and the list reaches a run that names no profile — the shape gate.py calls.
    PROF = ("## 4. Non-negotiables (compliance)\n"
            "- **Restricted words for this brand:** the client's own list, beyond the general lint\n"
            "  - `cheap` → `affordable`\n"
            "  - `free` → `free trial` — agreed by email, 2026-10-01\n"
            "  - `solar panels` → `solar modules` / `PV modules`\n"
            "  - `guarantee`\n"
            "- **Required disclaimers:** none\n")
    pr = parse_restricted(PROF)
    check("HR-01 the list form parses: four words, the agreed replacements, the note ignored",
          pr["state"] == "LIST" and [w for w, _ in pr["words"]] == ["cheap", "free", "solar panels", "guarantee"]
          and pr["words"][1][1] == ["free trial"] and pr["words"][2][1] == ["solar modules", "PV modules"]
          and pr["words"][3][1] == [])
    check("HR-01 `none` is recorded as NONE",
          parse_restricted("- **Restricted words for this brand:** `none` — confirmed\n")["state"] == "NONE")
    check("HR-01 the template's own placeholders are UNANSWERED, never banned words",
          parse_restricted("- **Restricted words for this brand:** <the list, or `none`>\n"
                           "  - `<word or phrase>` → `<the agreed replacement>`\n")["state"] == "UNANSWERED")
    check("HR-01 a field written as prose is UNREAD, not clean",
          parse_restricted('- **Restricted words:** "official", "authorised" must not appear.\n')["state"]
          == "UNREAD")
    check("HR-01 a differently scoped field (alt text) is not this list",
          parse_restricted("- **Restricted words in alt text:** \"our project\"\n")["state"] == "ABSENT")
    check("HR-01 a profile with no field is ABSENT", parse_restricted("## 4. Non-negotiables\n")["state"] == "ABSENT")
    W_ = pr["words"]
    S_ = ("# SCRIPT v1\n\n## SCRIPT\n\n[HOOK 0:00-0:04]  the bill on the table\n"
          'HOST: "Cheap power, finally."\n'
          'HOST: "The cheapest month we have had."\n'
          'HOST: "Start your free trial today."\n'
          'HOST: "And the survey is free."\n'
          'CAPTION: "Our SOLAR   PANELS, installed in a day."\n'
          'REVIEW: "Affordable, and the crew was quick." — a verified buyer\n\n'
          "## Notes\nThe client bans the word guarantee.\n")
    rf = [h for h in lint(S_, None, [], restricted=W_, restricted_src="clients/x.md")
          if "Restricted word" in h["why"]]
    blocks_ = [h["match"].lower() for h in rf if h["severity"] == "BLOCK"]
    check("HR-01 a restricted word in a spoken line BLOCKs, case-insensitive",
          "cheap" in blocks_)
    check("HR-01 ...on word boundaries: 'cheapest' is not 'cheap'",
          not any("cheapest" in h["text"].lower() and h["match"].lower() == "cheap" for h in rf))
    check("HR-01 the agreed replacement passes ('free trial'); the bare word does not",
          sum(1 for h in rf if h["match"].lower() == "free" and h["severity"] == "BLOCK") == 1
          and not any("free trial" in h["text"] for h in rf))
    check("HR-01 a caption BLOCKs too, across any run of spaces",
          any(h["severity"] == "BLOCK" and "solar" in h["match"].lower() for h in rf))
    check("HR-01 a review quote with only the agreed word is clean",
          not any("Affordable" in h["text"] for h in rf))
    check("HR-01 the word in production notes is a MENTION (NOTE), never dropped",
          any(h["match"].lower() == "guarantee" and h["severity"] == "NOTE" and "MENTION" in h["why"]
              for h in rf))
    check("HR-01 ...and --strict scores it at full severity",
          any(h["match"].lower() == "guarantee" and h["severity"] == "BLOCK"
              for h in lint(S_, None, [], strict=True, restricted=W_)))
    check("HR-01 --allow suppresses it exactly as it suppresses any other finding",
          not any(h["match"].lower() == "cheap" for h in lint(S_, None, ["cheap power"], restricted=W_)))
    check("HR-01 a captions file with no speaker lines is scored whole: the word BLOCKs",
          any(h["severity"] == "BLOCK" and "Restricted" in h["why"]
              for h in lint("1\n00:00:01,000 --> 00:00:02,000\nCheap power, finally.\n", None, [], restricted=W_)))
    check("HR-01 no list, no restricted finding (the existing rules alone)",
          not any("Restricted" in h["why"] for h in lint(S_, None, [])))
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        clients_dir = os.path.join(td, "_cine-clients")
        job = os.path.join(td, "jobs", "zzst-01001-test")
        os.makedirs(clients_dir); os.makedirs(os.path.join(job, "00-brief")); os.makedirs(os.path.join(job, "01-script"))
        open(os.path.join(clients_dir, "zz-selftest-brand.md"), "w", encoding="utf-8").write(PROF)
        open(os.path.join(job, "00-brief", "CHECKPOINT.md"), "w", encoding="utf-8").write(
            "# PRODUCTION CHECKPOINT\n\nJob: zzst-01001-test\nClient:     zz-selftest-brand\n")
        sp = os.path.join(job, "01-script", "SCRIPT-test-v1.md")
        open(sp, "w", encoding="utf-8").write(S_)
        rsel = restricted_for(sp, None)
        check("HR-01 the profile is found from the job's CHECKPOINT, in a `_cine-clients/` above it",
              rsel["state"] == "LIST" and rsel["source"] == "CHECKPOINT"
              and rsel["profile"].endswith("zz-selftest-brand.md"))
        # the call gate.py makes: the artifact path, --json, no profile flag
        r_ = subprocess.run([sys.executable, os.path.abspath(__file__), sp, "--json", "--no-material-connection"],
                            capture_output=True, text=True, timeout=60)
        got = json.loads(r_.stdout or "{}")
        rows_ = [x for v in (got.get("findings") or {}).values() for x in v]
        check("HR-01 gate.py's call shape (--json, no profile) gets a restricted-word BLOCK",
              any(x["severity"] == "BLOCK" and "Restricted word" in x["why"] for x in rows_)
              and (got.get("restricted") or {}).get(sp, {}).get("state") == "LIST")
        loose = os.path.join(td, "loose.md")
        open(loose, "w", encoding="utf-8").write(S_)
        rs0 = restricted_for(loose, None)
        check("HR-01 no CHECKPOINT and no --profile: SKIPPED, and the status line says why",
              rs0["state"] == "SKIPPED" and "no client profile" in _restricted_line(rs0))
        check("HR-01 ...with no finding added", _restricted_note(rs0) == [])
        check("HR-01 --no-profile skips the lookup and says so",
              restricted_for(sp, None, no_profile=True)["state"] == "SKIPPED")
        un = os.path.join(td, "legacy.md")
        open(un, "w", encoding="utf-8").write('- **Restricted words:** "official" must not appear.\n')
        rsu = restricted_for(sp, un)
        check("HR-01 a prose field read through --profile is a NOTE finding, not a pass",
              rsu["state"] == "UNREAD" and _restricted_note(rsu)[0]["severity"] == "NOTE")

    print("-" * 60)
    print("selftest OK — the coverage check fires on a language the rules cannot read, does NOT "
          "fire on terse English, always reports a denominator, the rules still work, and the "
          "document-level disclosure pass BLOCKS an undisclosed material connection while reading "
          "NOT ASSERTED — never clean — when nothing was examined; and the client's restricted words "
          " BLOCK where they ship, pass inside the agreed replacement, and reach a run that "
          "names no profile"
          if ok else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
