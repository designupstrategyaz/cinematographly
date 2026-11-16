# Hook Craft — what the evidence actually supports about the first six seconds

**Why this file exists.** The hook is the most-discussed and least-evidenced object in short-form.
This skill had hook doctrine in three places (`persuasion-psychology.md` §2, `modes/ugc-volume.md`
§5, `script-craft.md` §6 dimension 5) built almost entirely from copywriting books, and one of its
load-bearing rules — *"open a gap rather than announce a topic"* — is **contradicted as an
unqualified instruction by the best field evidence available.** This file is the sourced version:
what is measured, what is a vendor's house style, what is folklore, and what the measurements
change about how we write.

Every claim carries a tier (`research-quality.md` §2). Researched 2026-09-07; the retrieval dates
are on each row. **Durable literature does not need re-checking** (§1 of that file) — the
platform-prescription rows do.

---

## 1. The single most important thing on this page

⛔ **Curiosity is not free, and more gap is not more better.** The relationship between how much a
headline withholds and how many people click it is **curvilinear** — it turns over.

> **[PRIMARY · Aubin Le Quéré & Matias, "When curiosity gaps backfire: effects of headline
> concreteness on information selection decisions", *Scientific Reports* 2025 (s41598-024-81575-9)
> · 8,977 pre-registered A/B tests, Upworthy Research Archive · fetched 2026-09-07]**
> Concreteness × baseline-concreteness interaction **−0.058, p < 0.001**. Where a test's headlines
> were already concrete (>3.06), **50.9% lost clicks when made more concrete**, and a one-unit
> increase in standardised concreteness cost **−9.9%** click-through. Where they were vague
> (<2.58), the same increase *gained* **+5.5%**. In the authors' words: click-through "vary[s]
> positively with headline concreteness when average test concreteness is lower, vary[s] negatively
> when higher."

Read that in both directions, because the second direction is the one this skill was missing:

- Making a **vague** opener more specific helps. That is the version everyone already believes, and
  it is the version "specificity is instant credibility" (`persuasion-psychology.md` §2) encodes.
- Making an **already-specific** opener more specific hurts. There is nothing left to find out.
- And therefore **there is an optimum in the middle, not at an end** — so "make it more mysterious"
  and "make it more concrete" are both *directions*, not *rules*, and a writer who applies either
  one twice in a row has walked past the peak.

### The house rule that comes out of it

> **One concrete anchor, one withheld term.**
>
> The hook names something real enough to care about — a number, an object, a moment, a named
> person — and withholds exactly one thing: the cause, the method, the outcome, or the identity.
> Zero anchors is a mood, not a hook: nothing to want. Zero withheld is a summary: nothing to stay
> for. **The failure mode this replaces is iterating in one direction until the hook falls off the
> other side of the curve.**

This is the rule `script_score.py --hook-anchors` half-checks (§6) and the rule the hook bank's
`gap` column exists to make writable.

**A local media plan hands you the anchor.** When the ad runs in a small radius around one address
— [PRACTITIONER · course notes] 5–10 miles — the place is the concrete anchor, and the opening names it. A
national spot or a generated one does not inherit the place: the media plan decides, not an earlier
cut. The place is an anchor, not the brand, so §5 (brand out of the first beat) still holds.

---

## 2. What a gap actually requires — the three legs

The gap-theory citation in `persuasion-psychology.md` §3 was doing one job (curiosity = a felt gap)
and leaving out the part that makes it operational.

**[PRIMARY · Golman & Loewenstein, "Curiosity, Information Gaps, and the Utility of Knowledge"
(Carnegie Mellon) · read 2026-09-07]** — *"curiosity occurs when an individual becomes aware of a
gap in his or her knowledge that could potentially be filled."* Curiosity scales with the gap's
**importance**, its **salience**, and its **potential for epiphany**. A *latent* question — one the
viewer holds but has not been made aware of — produces no curiosity at all. And an unanswerable
question does not intrigue; Golman & Loewenstein note it can *"torment a person."*

So a gap is only a gap when **all three** hold, and each one is a separate writing failure:

| Leg | The viewer must… | The failure when it's missing | The fix |
|---|---|---|---|
| **Salience** | *know* they don't know it | The hook references a question they were never asked. Reads as a non-sequitur | Ask the question out loud, or show the anomaly, in the first line |
| **Importance** | *care* about the answer | The classic hollow hook: a perfectly-formed gap about something nobody wanted | Name a **stake they already hold** — see the test below |
| **Epiphany** | *believe watching will fill it* | The tease. "You won't believe what happened" promises nothing checkable | Name the shape of the answer — a number, a method, a verdict — without giving it |

⛔ **All three, or it is decoration.** This is the skill's own fraud test applied to a hook: *ask
what it would take to pass the check fraudulently.* "It has a question mark" passes nothing.

### ⛔ The importance test — and the one wrong answer everyone writes

> **A stake is something the viewer already owns, pays for, chose, uses, or worries about.**
> Not something they lack.

The failure is subtle and it is the most common one there is, including in this skill's own first
draft of its examples: writing the *salience* leg twice. "Because nobody has told them what to look
at", "because they've never heard this", "because they don't know how it's made" all describe the
viewer's **ignorance** — which is the gap itself restated, not a reason to care about closing it.
Ignorance is not an appetite; people live comfortably with almost all of theirs.

| Not importance (ignorance, reworded) | Importance (a stake they hold) |
|---|---|
| because nobody has told them what to look at | because there is a bottle of it open in their kitchen |
| because they've never seen the process | because they pay double for it every week |
| because it isn't common knowledge | because they chose this brand over the cheap one and have been defending it |

The test to run on the second half: **could the viewer have said it about themselves yesterday,
before they ever saw your video?** A stake passes. Ignorance does not — you had to tell them it was
there, which is the gap, not the reason.

`develop.py` refuses the ignorance form by name in the gap column, because it is the one dodge that
looks exactly like a right answer.

**The most common real-world failure is importance**, not salience — because importance is the one
the writer cannot supply by writing harder. It comes from the audience, which is why the awareness
routing in `persuasion-psychology.md` §2 sits upstream of every hook decision and is not
negotiable.

---

## 3. Six seconds — where the number actually comes from

The house has used "six seconds" for a long time with no provenance. Here it is, honestly:

**[PRIMARY · TikTok Creative Best Practices, creative centre · fetched 2026-09-07]** — *"Prioritize
your hook in the first 6 seconds to boost engagement and increase watch time."* **This is a
platform's prescription to its advertisers, not a published measurement.** No study, no method, no
figure is disclosed with it. It is PRIMARY for *what the platform recommends* — which is genuinely
useful, because the platform is also the distributor — and it is **not evidence about human
attention.**

The mechanism argument in `persuasion-psychology.md` §1 (one perceptual event, one semantic event,
and time to settle — from Styles on perceptual load and the attentional blink) is the *reason* a
number in that neighbourhood is plausible. Keep the two separate: the mechanism is durable
literature, the six is a vendor's round number that agrees with it.

**[MEASURED · script corpus 2026-11-05, `script-craft.md` §2d]** What real spots do in that window, without
proving any rule:
- **Verbatim TV and social ads:** the first spoken sentence runs 10 words (3–16), about 4–5 s at the measured
  2.2 words a second.
- **The 24 beat records of longer films:** the hook ends at about 16 % of the spoken words (5–24 %).

Both sit comfortably inside a six-second hook. Neither says six is right; they say the spots that won awards or ran
nationally did not spend longer.

### ⛔ The 3-second rule is not a finding. Do not cite it.

**[PRIMARY · Matt Pakes (Facebook product manager, video), Medium · fetched 2026-09-07]** — asked to
justify the 3-second video-view threshold: *"While there is no broad industry standard for view
measurement, **three seconds is one common choice**, and gives us a consistent metric for all video
on Facebook."*

**Three seconds is a billing and counting standard, chosen for consistency, defended without a
single citation.** Every "you have 3 seconds to hook them" deck traces back to a platform's
measurement convention that got retold as a fact about brains. Naming it is the point: it is the
most confidently repeated number in this industry and it has no research behind it at all.

---

## 4. The ceiling on all of this — read before promising anything

Two findings that should govern the *tone* of every hook conversation with a client.

**[PRIMARY · Gligorić, Lifchits, West & Anderson, "Linguistic effects on news headline success",
*PLOS ONE* 2023, 18(3):e0281682 — Registered Report · 24,333 randomised headline pairs from
real field experiments · fetched 2026-09-07]**
- The best linguistic model predicted which headline won **54.42%** of the time (53.17% recall,
  54.53% precision). Coin-flip is 50. It reached **58.3%** only on the pairs with the largest
  click-through gaps.
- **Longer headlines did better** (β = 0.07, p = 7.6×10⁻⁸) — the opposite of the "shorter is
  punchier" reflex.
- ⛔ **Second-person "you" was not supported** (β = 0.05, p = 0.044; the authors report no
  significant positive association). "Speak to *one* person, use 'you'" is one of the most repeated
  rules in copywriting and this is the largest test of it. It is not refuted — it is *unsupported*,
  which means stop asserting it as a reason.

**[PRIMARY · Ling, Blackburn, De Cristofaro & Stringhini, "Slapping Cats, Bopping Heads, and Oreo
Shakes: Understanding Indicators of Virality in TikTok Short Videos", ACM Web Science 2022 · 400
videos · fetched 2026-09-07]** — **the creator's follower count is the most powerful predictor of
virality.** (Small sample; treat the ranking as directional, not the effect size.)

> **What this means for how we talk about hooks.** Copy-craft's whole measurable effect on which of
> two headlines wins is worth about four points over a coin flip, and it is swamped by who is
> posting. So: **a hook bank is a way to lose less often, not a growth lever**, and any promise
> shaped like "the right hook will make this take off" is not supportable. What the bank *is* good
> for is the thing Gligorić's number also implies — since no one can predict the winner from the
> line, **you test, and the bank is the memory of what testing found.** That is exactly what
> `performance-metrics.md` §3's promotion floor is for.

---

## 5. Brand in the hook — the one placement finding we have

**[PRIMARY · Tellis, MacInnis, Tirunillai & Zhang, "What Drives Virality (Sharing) of Online
Digital Content? The Critical Role of Information, Emotion, and Brand Prominence", *Journal of
Marketing* 2019 · YouTube video ads, field studies + independent replication · fetched
2026-09-07]**
- *"Prominent (early vs. late, long vs. short duration, persistent vs. pulsing) placement of brand
  names hurts sharing."*
- What drove sharing was **positive arousal**: amusement, excitement, inspiration, warmth — and
  only ~7% of YouTube video ads evoked strong positive emotion at all.

**Scope it honestly before you use it:** this measures **sharing** of **YouTube ads**. It is not a
retention finding and it is not TikTok. The defensible read is narrow and still useful: *putting the
logo and the brand name in the first beat has a measured downside on one real outcome and no
measured upside on any.* So the house position is **brand late unless the client's own tested data
says otherwise** — and when a client mandates a 0:00 logo, that is a legitimate brand decision, but
it now has a citation attached to the cost, which is a better conversation than taste.

[PRACTITIONER · course notes] The course's spots agree in practice: most open on people, a place or the
product and close on the brand line or wordmark; one exception carries a line on the opening
product shot. A practitioner's habit, not a measurement — and their taglines are third-party copy
that stays in the local notes (`research-quality.md` §6).

### 5b. ⚡ What the outcome literature says back — and why it does not overturn the above

Researched 2026-09-18; every source and its trail lives in `assets/creative-benchmarks.json`.
Two large-scale sources push the other way, and the honest reading is that **they scope this finding
rather than refute it**:

| Source | Says | Outcome MEASURED | Tier |
|---|---|---|---|
| Tellis et al. 2019 (above) | brand prominence **hurts** | **sharing** | **PRIMARY**, peer-reviewed, independent |
| Google/Kantar, *The Short & the Long of ABCDs*, Apr 2021 | *"Brand early, often, and richly"* — up to **+30%** short-term sales likelihood, **+17%** long-term brand contribution | **sales likelihood · brand contribution** | SECONDARY — platform-commissioned, **no sample size published**, the Kantar study not read, five years old |
| Nelson-Field × VCCP Media, 2025 | an ad is recallable after **~1.5s** *if distinctive assets are present*; well-branded = **3.5×** attention-adjusted ROI | **recall / attribution** | SECONDARY — **agency-commissioned**, 72 ads / 20k views, **measurement method not disclosed** |

**They measure three different outcomes.** Sharing is not recall is not sales likelihood. Nothing in
that table is evidence against anything else in it.

⚡ **And the sharper point: brand PRESENCE is not brand ANNOUNCEMENT.** "<Brand> presents" in the
first beat is an *announcement* — that is the thing Tellis measured hurting sharing. A product in
frame, the house colour, a recurring character, a sonic mark: that is *presence*, which is what the
attribution literature is actually asking for. **A hook can carry every distinctive asset and never
announce anything**, and that resolves most of the apparent clash.

⛔ **Weigh the sources, do not count them.** Tellis is peer-reviewed and independent; the other two
are commissioned by parties who sell branded creative and disclose less method. Two-against-one is
not evidence, it is two interested parties agreeing.

**House position, revised:** the brand is **not announced** in the first beat. Distinctive assets
**may be present** in it and usually should be. Past that the dial is set by the video's
**objective**, which the client profile already declares — optimise for reach and sharing → later
and lighter; optimise for attribution, recall or conversion → present from frame one, still not
announced. Either way the decision records which finding it leaned on.

**[MEASURED · script corpus 2026-11-05]** Where the brand is first spoken:
- **Award-annual spots:** about a third of the way into the spoken words (median 36 %, range 8–90 %).
- **Public-service spots:** at the end, with the CTA.
- **Long brand films:** mostly on the end card, not in the voice.

This is description, not an outcome measure. It does not settle Tellis against the attribution literature, but it
shows the craft habit: announced late and lightly, present in the picture throughout.

`script_score.py --brand <name>` flags it mechanically (§6). ⚠️ **The flag is objective-blind and
presence-blind** — it sees a brand TOKEN in the hook window, which is the announcement half only. It
cannot see a logo on a product in frame, and it does not know whether this video is optimising for
sharing or for attribution. Read its finding against the objective before acting on it.

---

## 6. What the tools can and cannot check

Three of the findings above are mechanically checkable and the rest are not. The tools implement
exactly the three and say so, because a checker that pretends to score judgement is the failure mode
in `script_score.py`'s own header.

| Rule | Tool | What it actually measures | Why it is honest about its limits |
|---|---|---|---|
| One concrete anchor | `script_score.py --hook-anchors` | Numbers, proper nouns, quantities and units inside the hook window | **One-sided by construction.** It can catch *zero* anchors (the vague end of the curve). It cannot detect "nothing withheld", so a summary-shaped hook still passes and only a human catches it |
| Brand late | `script_score.py --brand <name>` | Whether the brand string appears inside the hook window | Warns, never fails — the evidence is about sharing on another platform (§5) |
| A gap has three legs | `develop.py --phase full` | Every hook-bank row carries a written `gap` — what they don't know **and** why they already care | It checks that the writer *answered*, not that the answer is good. That is the honest ceiling of a text check, and it is still most of the value: the hollow hook is usually hollow because nobody ever wrote the sentence |
| Test both halves of the curve | `develop.py --phase full` | Warns when every hook in the bank is from the indirect half | Five indirect hooks is testing one side of a curve that turns over (§1) |

---

## 7. ⛔ Blacklist — sources that look like evidence and are not

Recorded by name, because each of these will come back the next time anyone researches hooks.

| Source | Why it is out |
|---|---|
| **"The 3-second rule"** (any deck, any agency) | Traces to Facebook's *billing* threshold; the PM defending it cited nothing (§3). There is no study |
| **Balamurugan & Rajani 2026, "Hook Analytics", JAAFR** | **13 synthetic videos**, pay-to-publish venue. It is the top hit that *looks* like a study on this topic, which is precisely why it is listed here rather than merely ignored |
| **Berger & Milkman 2012, "What Makes Online Content Viral", JMR** | Real and good — and about the **wrong outcome.** 6,956 NYT articles, measuring **being emailed** (anger +34%, awe +30% odds of most-emailed). Using an emailing-a-newspaper-article result to choose the emotional register of a six-second video hook is a category error. Sharing ≠ retention, and Tellis (§5) found a *different* emotional profile for video |
| **Munger et al. 2020, POQ** | Cited both ways in clickbait arguments; its finding is **null effects** of clickbait exposure on trust, learning and polarisation. It supports no hook rule in either direction |
| **Any "hook rate" benchmark quoted without its platform and window** | 3s views ÷ impressions on Meta and 2s on TikTok are different numbers (`assets/hook-bank-template.md`). A benchmark without its definition is not a benchmark |

**Where the feed is honest about itself:** most of a short-video feed is abandoned, whatever you
write. **[PRIMARY · Zannettou et al., CHI 2024 · 9.2M TikTok recommendations donated by 347
users · fetched 2026-09-07]** is the largest real-consumption dataset we found. Treat any hook
promise that ignores baseline abandonment as innumerate.

---

## 8. Writing a hook, in order

1. **Route from awareness** (`persuasion-psychology.md` §2). More aware → more direct. This decides
   more than the line does.
2. **Name the gap in one sentence before writing the line**: *they don't know `<X>`, and they care
   because `<Y>`.* If `<Y>` is hard to write, the hook is hollow and no rewriting fixes it — go back
   to step 1.
3. **Write one concrete anchor and withhold one term** (§1). Not two withheld terms; a hook with a
   clause is two hooks (`assets/hook-bank-template.md`). When the media plan is a small radius
   around one address, the anchor is the place (§1).
4. **Check the three legs** (§2): salient, important, fillable.
5. **Keep the brand out of the first beat** unless the client has tested otherwise (§5).
6. **Write five, across both halves of the curve and at least two awareness levels**, and let the
   test decide (§4). The bank is the memory; the promotion floor in `performance-metrics.md` §3 is
   what makes it a memory rather than an anecdote. ⛔ **When a client asks for five of one type,
   write theirs AND add the direct one** — labelled, with one line on why it is there. *Adding* the
   sixth is the only version of this that survives: mentioning that variety would be better, then
   shipping five of one type, tests one side of the curve exactly as if you had said nothing. The
   client keeps what they asked for and gets the comparison for free, which is the whole argument.
7. **Check the button against the hook's question** (`script-craft.md` §6 dimension 11). A hook that
   opens a gap the ending never closes is worse than no gap: it spends trust.

**On a real shoot, openings and asks are modules around one body.** Development still writes the
full bank (step 6); the shoot films two or three openings and two or three asks, each cutting onto
the same body. [PRACTITIONER · course notes] The reason given is that a pile of whole scripts means none of
them is made well. On that job: about 5 s of face time for the opening (the practitioner's number;
§3's six is a platform's prescription, and both stand), about 6 s for the ask, 10 s as the ceiling;
the body is b-roll with the speaker off camera; one opening may be seasonal, and the others still
have to work once the season is over. Later tests ran three or four of each. When a test sells
nothing, swap the film's modules first; when none of them sells either, the question moves to the
offer (`performance-metrics.md` §0).

---

**Cross-references:** `persuasion-psychology.md` §2 (awareness routing — upstream of everything
here) and §3 (stickiness) · `modes/ugc-volume.md` §5 (the twelve types and their compliance load) ·
`script-craft.md` §6 (the scorecard) · `performance-metrics.md` §3 (promotion floors — what turns a
bank into evidence) · `assets/hook-bank-template.md` (the artifact) · `research-quality.md` §2
(the tiers used throughout).
