# Mode B — UGC Volume

**Use when:** the brief is *many* short videos rather than one good one. Signals: a monthly
target (20–50+), multiple brands or product lines, buyer personas supplied, an existing UGC/B-roll
archive to draw on, paid-social distribution, hook testing, "native", "not obvious AI".

**Do not use for:** a single hero film, a brand launch piece, anything where one video carries the
whole campaign. That is Mode A (`narrative-promo.md`).

**The one-line difference from Mode A:** Mode A optimizes the *video*. Mode B optimizes the
*system that makes videos* — and then defends quality with gates, because at volume quality dies by
drift, not by decision.

## Files this mode requires — read before the artifact, not instead of it

A model that opens this file and works will legitimately skip what it does not name, so it names
everything (the 2026-08-28 pre-mortem's open item 2). Beyond SKILL.md §2's ladder:
`assets/batch-plan-template.md` §0 (the required inputs, PRESENT/MISSING into the checkpoint) ·
`references/delivery-format.md` · `references/persuasion-psychology.md` §2 (awareness → hook type) ·
`references/script-craft.md` · `references/direction.md` §1 · `references/typography-and-captions.md` ·
`references/refinement-loop.md` · `references/stock-sourcing.md` (the archive's licence) ·
`references/realism-qa.md` §5–§6b (the batch-variance rule and the tiered card) ·
`references/series-parallel.md` (N ≥ 2 is the normal case here) ·
`references/discovery-and-search.md` (the caption is the index; the watermark and originality gates,
which are checked on the export) · `references/comedy-craft.md` **whenever any row is a light tone**
(§1 the review question, §3 relatedness, §9 the gate) · `references/compliance.md` §2b (the
material-connection disclosure, which the creator-posts-on-their-own-account model makes mandatory).
A long-body DR job (§2b) also loads `references/dr-advertorial.md` and `compliance.md` §5c.
**The frame gate is not skipped at volume** — every clip still binds an approved still; `gate.py` refuses otherwise (the pre-mortem's
open item 3). Artifacts: the checkpoint (`Mode: B`), the batch plan from `batch_plan.py`, one linted
frame + clip prompt per shot per episode, the join gate's report.

---

## 1. The economics that decide every choice here

Read this before designing anything; it explains why the rest of the file looks the way it does.

- **Only a small fraction of ads carry the spend.** Roughly 6% of creatives drive the majority of
  delivery. Volume is not a vanity metric — it is how you find the winner.
- **Creative demand scales with spend.** A rough industry anchor is about **one new ad per $3,000/month
  of Meta spend**: $5–15K/mo → 12–20 creatives/month; $15–50K/mo → 30–60; $50K+ → 80–120+.
  A 30–50/month brief therefore implies roughly $15–50K/month of spend behind it. **Ask.** It tells you
  what the videos are for and how hard the winner-finding has to work.
- **Fatigue is measurable.** Conversion rate declines first (leading indicator), then CTR drops
  20–30% off peak, then frequency climbs past 3–4. Refresh **weekly for TikTok, every 2–4 weeks for
  Meta**.
- **Hook testing beats ad testing.** Testing 3–5 hooks against one locked body resolves in 2–3 days
  instead of 5–7 and costs materially less per learning, because only the first 2–3 seconds change.
- **Retention benchmarks to aim at** (practitioner-aggregated, directional — not platform-published):
  Meta 3-second hold rate ~25–35% competitive, 35%+ elite; TikTok measures at 2 seconds, ~30–40%
  competitive, 40%+ elite.
- **The hook window is about six seconds, not three.** Platform guidance puts ~90% of ad-recall
  impact inside the first six seconds. The 3-second number is a *retention measurement point*, not
  the length of your hook.

**The consequence for production:** you do **not** write 40 scripts a month. You write a small number
of **compliance-cleared bodies** per brand and recombine them against a **hook bank** and a **CTA
bank**. That is where the volume comes from, and it is the only way the compliance review stays
tractable.

**There is a second reason the modular system works, and it is not about cost.** Viewers cannot see
the production; they infer a maker's control from **consistency**, and limits you impose on yourself
read as design where the identical limits imposed from outside would read as poverty [PRIMARY ·
Mahaffy, *Micro-Budget Methods of Cinematic Storytelling* — via a local extraction, read
2026-08-29]. So the reuse that makes 40 videos deliverable — one room, one persona register, one
grade, one type block — is also what makes a batch look *intentional* rather than cheap, provided
the limits are actually held. Ad-hoc, inconsistent variation is the thing that reads as accident.

⚠ **This is in tension with the batch-variance rule (`realism-qa.md` §5), and the tension is real.**
That rule exists because template-shaped output reads as slop; this one says that holding a template
consistently is exactly what reads as authorship. They resolve on **which layer varies**: vary the
*content* — hook, persona, objection, opening beat, framing choice. Hold the *system* — register,
palette, grade, type, blocking vocabulary, mix. A batch that varies the system and repeats the
content has it precisely backwards, and that is the failure both rules are pointing at from opposite
sides.

---

## 2. The modular asset system

```
       personas          hook bank            body            CTA bank
    ┌──────────────┐   ┌────────────┐   ┌──────────────┐   ┌───────────┐
    │ P1 · P2 · P3 │ × │ H1 … H10   │ + │ B1 (locked,  │ + │ C1 · C2   │
    │ (who speaks) │   │ (0:00-0:06)│   │  cleared)    │   │ (last 4s) │
    └──────────────┘   └────────────┘   └──────────────┘   └───────────┘
```

**Body** — the substantiated core: the demo, the proof, the mechanism, the cleared claim. Expensive
to make, expensive to clear, **changes rarely**. One to three per brand per month.

**Hook** — the first 6 seconds. Cheap, disposable, tested aggressively. **Every hook is a new claim
shape and needs its own compliance lint even when the body is unchanged** — this is the single most
common failure of the modular system.

**CTA** — the last 3–5 seconds. Offer, urgency, price, where to buy. Cheapest to vary, lowest
compliance risk (unless it makes a guarantee — see `compliance.md`).

**Persona** — who is speaking. Drives wardrobe, room, vocabulary, objection, and voice. A persona is
not a demographic; it is a person with a specific problem and a specific reason to distrust the
category.

**Variant math:** 3 personas × 5 hooks × 2 bodies × 2 CTAs = 60 permutations. **Do not ship all of
them.** Ship a designed subset that satisfies the batch-variance rule (`realism-qa.md` §5) and covers
the test you actually want to run. Combinatorics is a menu, not a plan — a batch that ships every
permutation is exactly the template-shaped output that reads as slop.

## 2b. Long-body DR: one locked body, several hooks

**Use when** the brief asks for several hooks on one shared body of a minute or more, built with direct-
response devices (offer banner, numbered labels, proof cards, an end card with a button). §2 still holds.
What changes is the length, the join, and what must stay identical across the hooks. The devices, sound
map, voice and AI routing are in `references/dr-advertorial.md`.

**The measured shape** [measured · lab-00009 · 2026-10-21]:
- One DR agency's portfolio, 10 ads: 38–60 s, median shot 1.46 s, and in the median ad 75.5 % of shots
  last 2 s or less. Its three brief examples run 51–140 s.
- The same agency's own brand, its 26 live Meta ads with the most impressions: median runtime 215.5 s,
  17 of 26 at 180 s or more, and one body family cut to 44, 72, 172, 215, 221 and 222 s.
- The hook beat ends at 2.2–6.0 s (median 3.2 s) across the 13 ads read.

So SKILL.md §3's 35–55 s window is the short-form window. A long-body job takes its length from the
brief: a body of 60–240 s, and hooks of about 4–8 s whose **picture** differs in the first 3–5 s, not only
the text [PRIMARY (opinion) · Savannah Sanchez, quoted by Motion · checked 2026-10-21].

**Lock the body once.** Claims cleared, VO final, captions built from the final VO's word timings. Every
hook is still linted on its own (§2), and every hook ends on the same one-line hinge that the body's first
sentence answers. The body's first 2–3 s must work after every hook: no callback to any one of them.

**The join is where a hook swap shows.** Hold these identical across the hooks [SECONDARY · practitioner
consensus, lab-00009 R2 §4 · checked 2026-10-21; the loudness figure is derived]:
- the same voice, model, settings and processing chain, with hook and body within ±1 LU;
- room tone running continuously across the join (one loop for every hook), and a J-cut that brings the
  body's first syllable in 3–6 frames before its picture;
- the same grade and the same caption style tokens;
- the offer banner either in every hook or in none of them.

**Export one complete file per hook** (hook + body), never one file carrying all the hooks. Name each with
§8's join key, the body ID fixed and only the hook ID changing; a client's own naming convention goes in its
profile and wins. Plan the cut-downs at chapter boundaries, so a 60 s version is a cut, not a rewrite.

**Pace and devices for the body** come from the DR card, not the award card: run
`sequence_lint.py --regime dr --baseline` (`references/sequence-grammar.md` §2c item 14).

---

## 3. The pipeline — four stages, not eight

Mode A's eight gated stages are right for one film and wrong for forty. Mode B runs **four stages at
the batch level**, with per-video work inside them.

| # | Stage | Unit | You produce | Gate |
|---|-------|------|-------------|------|
| 1 | 🧭 **Batch Plan** | per month, per brand | Persona sheet, body briefs, hook bank, CTA bank, the shipped matrix, cost estimate | Every body has a cleared claim; matrix satisfies the variance rule; cost inside envelope |
| 2 | ✍️ **Script Batch** | per matrix row | All scripts for the batch, in one pass | **`claims_lint.py` clean on every script**; `script_score.py` PASS; hooks distinct in *type*, not just wording; durations inside the brief's window |
| 3 | 🏭 **Produce** | per video | Voice → clips → archive blend → assemble → captions | Per-clip QA card passes (`realism-qa.md` §6); archive footage licensed; lipsync verified by listening |
| 4 | 📦 **Deliver & Learn** | per batch | Exports + disclosure notes + the debrief | `slop_check.py` passes on the folder; compliance gate signed; **performance written back to the hook bank** |

Stage 4's second half is what makes the next month cheaper. A batch that ships without recording
what won is a batch you have to redo blind. See §8.

---

## 4. Stage 1 — the batch plan

Produce `00-batch/BATCH-<BRAND>-<YYYY-MM>.md` from `assets/batch-plan-template.md`:

0. **Angles.** If the bank is thin, run `references/ideation.md` §4 — the persona × objection ×
   proof × register grid — before anything else. Forty videos need forty things worth saying, and
   generating them cold each month is what makes batches converge on three angles by week three.
1. **Personas** (from the client, or drafted and confirmed). One block each: who they are, the
   problem in their words, the objection that stops them buying, vocabulary they'd actually use,
   room/setting, wardrobe, voice. Use `assets/persona-brief-template.md`.
2. **Bodies.** For each: the offer, the single cleared claim, the proof shown, the archive footage
   it needs, the substantiation reference. **A body without a cleared claim is not a body yet.**
   One idea per body (the Rule of One) — a body arguing two things persuades of neither.
3. **Hook bank.** Draw from the taxonomy in §5; aim for at least 4 distinct *types* per brand.
4. **CTA bank.** 2–3 variants.
5. **The matrix.** The actual rows you will ship, with duration targets spread across the window.
   ⛔ **The variance rule is now a distribution control, not a taste control.** YouTube's
   inauthentic-content policy names "AI-generated content made with generic or unoriginal templates
   giving the impression of mass production" and "characters put in the same situation over and over
   again with the same outcome" — original AI content at volume, which is precisely this mode. Meta
   separately deprioritises "duplicative" posting. Both carry reach consequences
   (`discovery-and-search.md` §4c), and the advertising literature independently says cosmetic
   variation does nothing at this involvement level (`comedy-craft.md` §6). Vary the **argument**;
   the wrapper varies on top, not instead.
   `scripts/batch_plan.py` expands personas × hooks × bodies × CTAs, applies the variance rule, and
   prints the matrix plus a credit/cost estimate.
6. **The compliance sheet.** The client's approved language, the required disclaimers, the
   disclosure treatment, and who signs off.
7. **The Visual Bible.** Palette, per-persona wardrobe blocks and reference images, the approved
   settings with their light sources and prop lists, the real product assets, and the negative list.
   Written once per brand into the client profile — see `references/production-design.md` §7. Without
   it, forty videos drift into forty looks.

---

## 5. Hook taxonomy

Six seconds — the platform's number, not a measurement of attention (`references/hook-craft.md` §3,
which also says why the "3-second rule" is not citable). The hook's job is to make the next six
seconds inevitable — not to explain the product.

**Two rules sit above the table**, both sourced in `hook-craft.md`:
**one concrete anchor and one withheld term** (§1 — the concreteness/click curve turns over, so
vaguer is not reliably better), and **the gap needs all three legs** — salient, important, fillable
(§2). Every type below can be written hollow; these are what stop that.

**Pick the type from the viewer's awareness level, not from taste.** Most aware wants the deal;
product aware wants reassurance; solution aware wants education; problem aware wants empathy;
completely unaware needs arresting. Firing a hard offer at an unaware audience chases them off, and
opening a long story to a most-aware buyer loses them. The five levels and the routing rule are in
`references/persuasion-psychology.md` §2 — a hook that underperforms is very often the right hook
aimed at the wrong level, which is a different fix from writing a new hook.

| Type | Shape | Best for | Compliance load |
|---|---|---|---|
| **Curiosity gap** | State a consequence, withhold the cause: "I wasted £400 before someone told me this" | Everything; the most-reached-for. Note the £400 — the consequence is the anchor, the cause is the gap | Low |
| **POV** | "POV: it's 3am and you've been staring at the ceiling again" | Identification, sleep/wellness especially | Low — but avoid naming a disorder |
| **Mistake / correction** | "I was doing this completely wrong for two years" | Categories with a learning curve | Low |
| **Skeptic** | "I genuinely thought this was a scam" | High-distrust categories | Low — and it *helps*, because hedged language is safer |
| **Problem–agitate–solution** | Name the pain, twist it, resolve | Direct response, the workhorse | **Medium** — agitation drifts into disease claims fast |
| **Comparison** | "£12 vs £180 — honest difference" | Competitive categories | Medium — comparative claims need substantiation too |
| **Day in the life** | Product woven into a routine | Lifestyle, home, low hard-sell | Low |
| **Three things** | "Three things I wish I'd known about…" | Editorial, explainer, social search | Low |
| **Unboxing / first impression** | Sensory discovery | Ecommerce, gadgets, home | Low |
| **Testimonial** | A person reporting their result | Highest converting | **Highest** — see `compliance.md` §2. With a synthetic presenter this needs the dramatization disclosure and the underlying claim still needs substantiation |
| **Humour / pattern interrupt** | An absurd cold open | Cutting through in a crowded feed | Low, but check the joke doesn't imply a claim |
| **Serious / trust-building** | Straight to camera, low energy, no music | Claims-sensitive categories, older audiences | Low — and often the right register when the claim is careful |
| **Reverse psychology** | A mock warning against buying: "Don't order this if you like your old routine" | DR and impulse categories; 3 of the 13 DR ads in lab-00009 open this way | Medium — the "warning" must not imply a health risk or name the viewer's condition (`compliance.md` §5c) |
| **Authority or number anchor** | A credential, a number or the product in hand in the first line | Supplements, where long-running ads lean on a reason to believe [VENDOR · two supplement ad datasets, lab-00009 R4 · 2026] | Medium — the credential must be real; an AI "doctor" is not one (`compliance.md` §2) |

⛔ **Test both halves of the curve, not five shades of indirect.** The bottom six rows are the
*indirect* half (they withhold to earn the next beat); offer/comparison/three-things/testimonial/
serious are the *direct* half (they lead with the thing). A bank of five indirect hooks is a bank
that tested one side of a relationship that turns over (`hook-craft.md` §1), and
`scripts/develop.py` warns on it. The direct half also wins outright at the aware end of the ladder,
which is the routing rule above.

**Tonal range is a deliverable, not a style.** A brief asking for "both serious and humorous" is
asking whether you can run the same body at two registers. You can: the body stays, the hook type
and the delivery change. Plan them as **paired rows in the matrix**, not as separate campaigns —
that is also the cheapest possible tone test.

---

## 6. Stage 3 — producing at volume

### 6.1 Presenter strategy — pick per row, not per brand

| Approach | When it's right | Cost | Watch out for |
|---|---|---|---|
| **Archive-led** — real UGC/B-roll the client owns, generated scenes only for gaps | The client has an archive; highest authenticity per credit | Lowest | Licensing for paid use; matching grade between real and generated |
| **AI presenter** — generated person, audio-driven lipsync | No archive, or a persona the archive doesn't cover | Medium | Every tell in `realism-qa.md` §1–2; disclosure obligations |
| **Recurring mascot / character** | Brand wants a franchise face; works across many videos | Medium, amortized | Identity lock discipline; keeps the disclosure burden **lower** than photoreal humans |
| **Faceless** — VO + product macro + hands + screen-record + text kinetics | Highest volume ceiling, cheapest, no presenter risk | Lowest | Gets monotonous fast; needs the strongest hooks |

**Default recommendation for a claims-sensitive multi-brand account:** archive-led where the archive
reaches, faceless for the long tail, AI presenter for personas the archive can't cover, and a
recurring mascot where the brand wants a franchise. **A photoreal synthetic human presenting as a
customer is the highest-risk option in the set** — use it deliberately, disclosed, and never for a
testimonial claim.

### 6.2 Blending archive footage with generated scenes

The seam is what gives it away. Four fixes, in order of impact:

1. **Grade to the archive, not to the render.** The real footage is the reference. Pull the
   generated clips toward the archive's white balance, contrast, and noise floor — never the reverse.
2. **Match the noise.** Real phone footage has compression noise and low-light grain. Add matching
   grain to the generated material (`realism-qa.md` §4) or the cut reads as two cameras.
3. **Cut on motion, never on a static hold.** A cut between real and generated during a movement is
   nearly invisible; a cut between two static frames invites comparison.
4. **Let the archive carry the faces, the generated material carry the world.** Real footage of a
   person plus generated product/environment/B-roll is far more robust than the reverse, because
   faces are where every tell lives.

**Licensing is a gate, not a footnote.** Archive UGC filmed for organic use is often not licensed
for paid. Confirm usage rights **per clip** before it enters a batch, and record the confirmation in
the batch plan.

### 6.3 Batch generation

Same three model roles as Mode A (`ai-generation.md`), with volume adjustments:

- **Dialogue = route the lipsync path per `ai-generation.md` Step 4.** For English one-off UGC,
  native-audio generation (Path B) is often the cheaper, simpler default *after its bake-off* — one
  step, no padding or conform, face-matched prosody; add the verbatim word check to the QA card and
  watch per-clip voice drift. Voice-first (Path A) stays mandatory for mispronounced languages,
  recurring voices, and locked or claims-sensitive wording. Never a silent generation with VO laid
  over in the edit.
- **Shorter clips.** 3–5s per generation. Drift compounds with duration and short clips also cut
  better for UGC pacing.
- **Preflight the cost once per batch shape**, not per job — one representative `get_cost` call with
  the exact params outside the batch, then submit.
- **Check every batch result for the preset-intercept failure shape**, not just success/fail counts,
  and resubmit with the declined-preset id. Failed submissions aren't charged; silent preset output is
  worse than an error.
- **One variable per regeneration.** At volume the temptation is to fix three things at once and
  lose the ability to attribute the fix.
- **Lane the work:** frames queue, dialogue queue, B-roll queue, VO queue — run in parallel, review
  in one pass. Serial per-video production is what makes 40 videos take a month of hands.

### 6.4 Captions and text

Burnt-in captions are standard and non-optional for UGC: Feed placements, accessibility, and the share
that watches muted all need them. Build the sound for sound-on viewing and keep the mute test
(`references/dr-advertorial.md` §8), which is T1 of `references/sound-off-story.md`. A talking head whose story
*is* the speech runs the **narrow T2** there: the picture alone shows who, the product, the proof and the offer
(`soundoff.py map init <job> --narrow --why "…"`).

⚠️ **SUPERSEDES IN PLACE** (2026-10-21) — previously: "Burnt-in captions are standard and non-optional for
UGC — most of the audience is muted." The premise is wrong for Reels: Meta reports 80 % of Reels viewed
with sound on [PRIMARY* · Meta "How to Reels" deck, Instagram internal data, Aug 2022 · checked
2026-10-21]. "Most feed video ads are viewed without sound" is Meta's statement of February 2016, and no
newer Feed figure was found [PRIMARY · Meta for Business, Feb 2016 · checked 2026-10-21]. The rule stands;
its reason changed.

**Route by
who owns the timing** (`editing-and-audio.md` § Captions): rows a human editor cuts and finishes get
captions in Resolve (the default since house rule C7, 2026-10-27: the Subtitle track, or the brand's Text+
where the profile permits); **machine-assembled rows with no Resolve timeline, and derivative re-crops, may use
route 3** — `build_captions.py --reason batch|derivative --why "…"` burns each format's captions from the locked
`.srt`, fully scripted including the `--disclosure` line from frame one, and records why. A row that has a Resolve
timeline gets its captions there. A hand-edited cut only meets route 3 through the conform bridge (real timings
dumped from the edit first). Build the `.srt` from the **locked script**, never
a fresh transcription; QA the *output* frames, not the intent.

⛔ **The disclosure is caption-layer text, not a title card.** Where any row carries a material
connection, `--disclosure` runs from frame one **and** the first spoken line says it too — a
talking-head UGC ad uses both channels, so 16 CFR §255.0(f) needs both
(`compliance.md` §2b.3). It is deliberately not a card: Meta's branded-content rules forbid title
cards in a video's first three seconds and cap interstitials at three consecutive seconds, and
running the disclosure as caption text over the opening action satisfies both regimes at once.

**Two format rules bound the overlay treatment, and both are documented**
(`discovery-and-search.md` §4): Instagram will not recommend a reel "where text does not cover the
majority of the screen" is breached, and TikTok's own guidance is **5–10 words per second** of text
inside the UI safe zone. A keyword-heavy or disclosure-heavy overlay can breach both at once. The
*presence* of text is documented as good on both platforms; the *density* is where they bite. The 5–10
words per second is for text overlays; speech-synced captions run at the speech rate
(`typography-and-captions.md` §3b).

**The post-copy is part of the deliverable, not an afterthought.** The caption is the only lever all
three platforms document as a search signal, and Google's Search Console now measures it for TikTok
and Instagram posts. Draft it from the locked script — lead with the plain-language problem phrase,
≤5 hashtags for Instagram, never the disclosure alone (`discovery-and-search.md` §2, §5).

---

## 7. Stage 4 — deliver and QC the batch

- `scripts/slop_check.py <delivery-folder>` — the mechanical batch pass: duration window and spread,
  distinct durations, resolution and frame-rate consistency. Fails the batch if it collapsed into a
  template. Add `--loudness` to also check per-file LUFS and the spread across the batch (slow, so
  opt-in). Framing, setting, presenter mix and hook-type variety stay a human read.
- `scripts/export_qc.py` per file — spec compliance.
- The compliance checklist from `compliance.md` §6, signed per batch.
- **Disclosure note per file** in the handoff: which platform toggle to set, and confirmation that
  the on-screen disclosure is burnt in.
- **Daily progress note** if the client asked for one (trials usually do): what shipped, what's in
  review, what's blocked. One paragraph, same time each day, opening with an honest status colour —
  **Green** (on plan) / **Yellow** (at risk, here's the mitigation) / **Red** (off plan, here's the
  ask). A Yellow that was flagged early is professionalism; a Red that appears from nowhere after
  five Greens is how trust dies.
- **Numbers in the note carry provenance** (measured / estimated / assumed — `pm-workflow.md` § Board
  operating conventions), and any capacity or cost claim ships behind the verification readout.

---

## 7a. ⛔ Do not make it cinematic

The platform's own performance guidance tells advertisers to **"maintain DIY or not overly polished
aesthetic"** [PRIMARY · TikTok for Business · checked 2026-08-29], and the reason is structural: every
parameter that reads as *expensive* reads as *advertisement*, and an ad is what a scrolling viewer is
deciding whether to skip. Shallow depth of field, low-key exposure, slow reveals, long takes and
palette desaturation are Mode A vocabulary. In this lane they are tells.

What does cross over from the craft files is the frame-local half — light direction, a single
dominant source, palette coherence, close proximity, centred framing — the things that make an image
*good* rather than *expensive*. `references/style-transfer.md` §5 is the full crossing table, and
`photorealism-physics.md` §8 makes the same argument about grain and halation: the reference is a
phone, not an ARRI.

## 7b. Review at volume — one link per drop, not one per file

Per-file review links do not survive 30–50 videos a month. Share the **folder**: a folder share
carries everything inside it and updates as you add files, so one link per client per drop shows
Thursday's new variants without a re-send, in a grid the client can scan side by side. That grid IS
the hook-variant comparison — the strongest argument for reviewing a batch on a real review platform
rather than in a chat thread. Set the share to latest-version-only unless a note specifically needs
the client to compare against an earlier cut.

The mechanics, the platform decision (Frame.io is not automatically the answer — for a Resolve-cut
batch the comment round-trip may be worth more than the branded page), and the sign-off convention
are in `references/review-and-approval.md`. Two rules that bite hardest at volume: **approval is a
top-level `APPROVED` comment from a named reviewer**, and **the file name is the ad-name join key**
(`performance-metrics.md` §2) so an approval, a manifest row, a hook-bank row and a metrics row all
name the same variant.

---

## 8. The learning loop — what makes month two cheaper

The batch is not done when the files ship. Write back:

1. **Hook performance → the hook bank.** Not hand-typed: every shipped ad carries the join key in
   its platform ad name (`<BRAND>-<bodyID>-<hookID>-<personaID>-<variant>`, assigned in the batch
   plan), so the platform's own rows — daily pull or Ads Manager Scheduled Export — join back to
   hook IDs mechanically. Read them through the diagnosis waterfall (hook rate → hold rate →
   quartiles → CTR → CVR) and the impressions floor in `references/performance-metrics.md`.
   Promotion to the standing bank takes the two-witness bar: beats the bank average on two runs,
   each above the floor. Proven hooks reapplied to new bodies are the compounding asset in this
   whole system; sub-floor numbers stay "in test" no matter how good they look.
2. **Every new failure → the guardrail tables.** A new artifact goes in `ai-generation.md`'s guardrail
   table; a new tell goes in `realism-qa.md` §1; a new risky phrase goes in `compliance.md` §4.
3. **Real cost → the ledger.** Reconcile against what actually settled, not the preflight.
4. **Write the episode note.** `memory/episodes/<date>-<brand>.md` — what changed, what broke, what
   you'd do differently. This is the input to the consolidation pass that promotes observations into
   permanent skill rules; see `self-evolution.md`.

**The debrief a client asks for at the end of a trial is this file's §8 output, written up.** If the
loop was run, the debrief writes itself.

---

## 9. Capacity — answer this honestly

When a client asks weekly capacity, the honest answer has a shape:

- **Ramp matters.** Month one is slower: personas, hook bank, compliance sheet, identity locks, and
  the archive audit are one-time costs. Steady state is 2–3× the first week's rate.
- **The bottleneck is rarely generation.** It is compliance review, client feedback loops, and
  archive licensing. Quote against the slowest of those, not the fastest.
- **Plan the month at 70–80% of the ceiling, with stretch rows marked** (`pm-workflow.md` § Calendar) —
  the quoted number is the 70–80% number, not the ceiling.
- **State a rate you can hold with the gates on.** Capacity claimed without the QA card and the
  claims lint is not capacity; it is a backlog of rework. The client's own brief says "volume without
  quality dropping" — the gates *are* the answer to that.
- **Quote a range with the assumption attached**, e.g. "N/week steady-state assuming the archive is
  licensed and claims are pre-cleared; M/week during ramp."
- **A long-body DR batch (§2b) is not a 40-second video times four.** The timed fast path
  (`references/production-runbook.md`) budgets one 20–40 s video at 4 h 45 m. A brief asking for two or
  three batches a day of three hooks plus a 1–3 minute body is outside that path. Time the first batch with
  `scripts/stage_timer.py` and quote from the measured stages, never from the brief's number.
- ⛔ **A humorous lane is not a free tone toggle on a serious workflow.** The joke explains 7–17% of
  whether anyone is amused; the joke × viewer match explains ~35% (`comedy-craft.md` §4). That is an
  argument for volume and segmentation, and the documented professional practice is a **10:1
  write-to-ship ratio** — 300–500 concepts written to ship 30–50. Quote the comedic lane with that
  number attached or do not quote it separately at all.

---

## 10. Definition of Done — Mode B

Per video: reads as native (QA card passed) · hook is one of the taxonomy's types, not a restated
body · claims lint clean or client-approved · disclosure burnt in where required · captions correct
and legible · the sound-off check logged on each export's own bytes (T1, and the narrow or full T2 —
`references/sound-off-story.md`) · spec-compliant export.

Per batch: variance rule satisfied · every archive clip licensed for its use · compliance checklist
signed · cost reconciled · **hook performance and failures written back**.

If any is shaky, say so plainly rather than shipping and hoping.

**Cross-refs:** `persuasion-psychology.md` (awareness routing for the hook bank, and the ethics
gate) · `production-design.md` (the room, which in UGC is the authenticity signal) ·
`realism-qa.md` (the QA card and the variance rule) · `compliance.md` (the lint and
disclosure) · `ai-generation.md` (prompts, identity lock, economy) · `editing-and-audio.md` (mix,
captions, export) · `pm-workflow.md` (folders and naming) · `self-evolution.md` (how this month's
lessons become next month's defaults) · `clients/<brand>.md` (personas, archive, approved language).
