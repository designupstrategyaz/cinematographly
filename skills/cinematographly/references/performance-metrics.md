# Performance metrics — closing the loop from ad platform back to the hook bank

**When to read this:** you are setting up (or running) the writeback in `modes/ugc-volume.md` §8, a
client asks "which videos worked?", or you are deciding whether a hook/body/persona earned promotion.
This file turns the learning loop from hand-typed impressions into an API-fed pipeline with a join
key. It is the measurement half of Mode B; the creative half is `script-craft.md` and the hook bank.

Source tiers follow `research-quality.md`: [PRIMARY] = platform docs, [SECONDARY] = named
practitioner sources, [UNVERIFIED] = folklore or unconfirmed field shapes. Everything here checked
2026-08-28; API fields decay fast — re-verify before building against any field older than a quarter.

---

## 0. ⛔ What can and cannot be predicted before it ships

**Read this before anyone asks for a virality score, and before anyone promises one.** Researched
2026-09-07; tiers per `research-quality.md` §2.

### The answer is no, and the reason is not a modelling limitation

> **[PRIMARY · Salganik, Dodds & Watts, "Experimental Study of Inequality and Unpredictability in an
> Artificial Cultural Market", *Science* 311(5762), 2006 · 14,341 participants, 48 unknown songs, one
> independent condition and eight parallel invisible worlds · verified 2026-09-07]**

Forty-eight unknown songs were run through eight mutually invisible worlds, twice. The same songs
came out in wildly different orders. *"Lockdown"* ranked **26th of 48 on intrinsic appeal** and
finished **1st in one world and 40th in another**. The song ranked top-5 on appeal had only a
**50% chance** of finishing top-5 on success. The authors' own summary is the honest ceiling on
craft: *"The 'best' songs never do very badly, and the 'worst' songs never did well, but any other
result was possible."*

⛔ **And the number that ends the argument** **[PRIMARY · Salganik & Watts, *Topics in Cognitive
Science* 1:439–468, 2009 · prediction-error analysis on the same experiment · verified 2026-09-07]**:
a manager with **perfect premarket knowledge** of every work's intrinsic appeal cuts expected
prediction error from 0.77 to 0.65 — **a 16% improvement, leaving 84% unexplained.**

That is not "our model is not good enough yet". Perfect information about the artefact is worth
16%. The rest is the network. Their conclusion, verbatim: *"Experts fail to predict success not
because they are incompetent judges or misinformed about the preferences of others, but because when
individual decisions are subject to social influence, markets do not simply aggregate pre-existing
individual preferences."*

### The ceilings, so nobody has to re-litigate this

| What was predicted | Best result | The catch |
|---|---|---|
| Which of two headlines wins **[PRIMARY · Gligorić et al., *PLOS ONE* 2023 · 24,333 pairs]** | **54.42%** | Coin flip is 50 |
| Song success from acoustics **[PRIMARY · Interiano et al., *R. Soc. Open Sci.* 2018 · 500k songs]** | **0.74** | One artist-reputation variable took it to **0.86** — the creator is worth more than the song |
| News popularity, pre-publication **[PRIMARY · Bandari, Asur & Huberman, 2012 · 10,000 test articles]** | "84%" | ⛔ Majority class is **76%** — an 8-point margin, and the top predictor was the **publication source**, not the writing |
| Hit songs from acoustics + human labels **[PRIMARY · Pachet & Roy, ISMIR 2008 · 32,978 titles]** | F ≈ 3–4% | Against a random baseline of 3%. *"No significant statistical patterns concerning popularity"* |
| An expert picking the better ad **[PRIMARY · Armstrong et al., *EJM* 2016 · 96 matched pairs]** | **55%** | Commercial copy-testing scored **59%**, and both against a recall proxy, not sales |
| TV copy-test scores → actual sales **[PRIMARY · Lodish et al., *JMR* 1995 · 389 split-cable experiments]** | — | ⛔ *"The data do not show a strong relationship between standard recall and persuasion copy test measures and sales effectiveness"* |
| Box office from the script **[PRIMARY · Eliashberg, Hui & Zhang, *IEEE TKDE* 2014 · 300 scripts]** | 42% MSE reduction | Its own authors: use it *"during the final stages of green-lighting"*, **explicitly not as an initial screening tool**. And its economic result is a **portfolio** one — median ROI 134% vs 84% across 5–20 scripts, not a picking result |

**[PRIMARY · De Vany & Walls, *J. Cultural Economics* 1999 · 2,000+ films]** puts the structural
version: box-office revenue is *"asymptotically Pareto-distributed and has infinite variance"*, so
*"there is no typical movie"* and *"revenue forecasts have zero precision."*

### What this means for a 40-second promo, concretely

**[PRIMARY · Guinaudeau, Munger & Votta, *Computational Communication Research* 4(2), 2022 · 11,546
TikTok accounts, 1,998,642 videos · verified 2026-09-07]** — inside **one account's own output**:
the top 20% of its videos take **75.76%** of its views, and the median **peak-to-median ratio is
64×**. The same creator's best video gets 64 times their typical one.

> ⛔ **One video is not evidence about the script that made it.** That is why §3's promotion floor
> needs two runs, and why a single week is one witness.

**[PRIMARY · Liu et al., "Hot streaks in artistic, cultural, and scientific careers", *Nature* 559,
2018 · ~30,000 individuals including film directors · verified 2026-09-07]** — the hot streak
*"emerges randomly within an individual's sequence of works"*. If the position of your best work in
your own sequence is random, **the number of works is the only lever you fully control.**

### ⛔ What pre-production may claim, and what it may not

**May not.** No virality score in a deliverable. No "this will perform". No percentage confidence on
an outcome. `claims_lint.py` flags forecast language, because a promise to a client is a claim like
any other and this one is unsubstantiable by construction.

**May.** Four things, all defensible:
1. **Raise the floor** with the handful of verified findings — brand out of the first beat
   (`hook-craft.md` §5), one concrete anchor and one withheld term (§1 there), the anchor/settle
   spec (`motion-craft.md` §6). Each is worth points, not multiples. ⛔ And **[PRIMARY · Hartnett,
   Kennedy, Sharp & Greenacre, *J. Advertising* 45(1), 2016 · 312 TV ads against in-market sales]**
   is the standing rebuttal to any checklist that promises more: *"no single creative device can do
   much alone to explain sales effectiveness. There is no one simple cookbook."*
2. ⛔ **Name the distributing account in the brief.** It is the largest legitimately knowable term
   and the skill did not ask for it: one artist-reputation variable moved 0.74 → 0.86; the top
   predictor of news popularity was the source; follower count dominates TikTok virality
   (`hook-craft.md` §4). A brief that does not say *which account, which audience, which format that
   account already wins with* has omitted the biggest variable in the model.
3. **Ship a variant set with a pre-committed decision rule**, not a forecast — the hook bank, and a
   kill/scale threshold written before anything is generated. **[PRIMARY · Kohavi, KDD 2015 keynote,
   Microsoft · verified 2026-09-07]**: *"1/3 of ideas were positive… 1/3 were flat… 1/3 were
   negative"*, with Bing lower still. That is the base rate to plan against. On a real shoot the
   variant set is the openings and asks filmed as modules around one body (`hook-craft.md` §8), and
   the decision rule reads them in order: a test that sells nothing points first at the film — swap
   the modules — and only when none of them sells at the offer [PRACTITIONER · course notes]. The join key
   (§2) has no ask ID, so an ask is read through the ad that carries it, not on its own.
4. **Budget and report at portfolio level**, because that is the only level at which the
   script-stage evidence is positive at all (Eliashberg's 134% vs 84%).

### The vendor instrument, read honestly

Higgsfield ships a **Virality Predictor** (`mcp__Higgsfield__virality_predictor`). What it actually
is, from its own product page and UI **[PRIMARY · higgsfield.ai/apps/virality-predictor and the
running app · read 2026-09-07]**:

- **Input is a finished video, up to 15 seconds.** *"A hook you're testing, an ad before launch, a
  reel sitting in drafts."* ⛔ **So it cannot answer the pre-production question at all** — by its
  own input spec, there must already be a clip. That is a scope fact, not a criticism.
- Method, verbatim: *"We simulate the cortical response of **720 modeled brains**, second by second."*
  **Modeled**, not measured — and no accuracy figure, validation set, correlation or method is
  published anywhere on the page. By this skill's own tiers that makes every number it returns
  **[UNVERIFIED]**, which *never terminates a claim* (`research-quality.md` §2).
- Outputs: an overall score /100, Hook Score, Hold Rate, and per-region bars (Visual Cortex,
  Auditory Cortex, Language Network, Attention Control, Focus Drift).

**How to use it, and how not to.**

⛔ **Never as a score.** Never in a client deliverable, never as a gate, never quoted as a number.
An observed run returned **Overall 46/100 with Hook Score 29 and Hold Rate 93%** on the same
14-second clip — a hook called weak on a clip that, by the same instrument, held 93% of its
audience. Those two cannot both be strong evidence about the same fourteen seconds, and no published
method exists to reconcile them. A number you cannot interrogate cannot carry a decision.

✅ **As a same-day comparator between two versions of one thing.** Two cuts of the same hook, same
instrument, same session, and you take the direction of the difference rather than either value.
That is the identical logic to the hook bank, and it is defensible for the same reason: you are not
predicting the outcome, you are ordering two candidates and then letting the market decide. It is
also the pipeline's only cheap way to express a preference between two finished clips — which is
exactly the selection pressure the clip stage otherwise lacks.

**One reading worth taking seriously even so.** The per-region bars are not validated, but they are
*diagnostic-shaped*, and a low **Auditory Cortex** band on a piece with a two-layer mix is the same
finding `export_qc.py`'s room-tone check makes mechanically. Where an unvalidated instrument and a
measurement agree, act on the measurement and treat the instrument as having pointed at it.

---

## 0c. ⚡ Outcome data — what exists, what survives its trail, and the one benchmark that counts

Researched 2026-09-18 after a standing ask for "as much outcome data as there is, by category and
industry." The findings, their samples and their commissioning parties are in
`assets/creative-benchmarks.json`; this section is what to DO about them.

⛔ **The headline is not the numbers. It is that most of them are not numbers.** The industry
publishes a great deal of "CTR by industry" content and almost none of it carries a method. One
widely-copied table gives Finance ~1.03%, Cosmetics ~0.32%, Fashion ~0.25% — and, **on the same
page**, In-Feed CTR of 1.5–3%. In-feed is the dominant format, so both cannot describe the same
population. No sample, no period, no source, no geography. It is recorded in the file's `blacklist`
rather than quietly dropped, so nobody re-imports it in three months. **Treat an unsourced benchmark
as a rumour with a decimal point**, and when a client cites one, that entry is the reply.

**What did survive, and what each is good for:**

| Finding | Good for | ⛔ Not good for |
|---|---|---|
| **ABCD** (Google/Kantar 2021) — brand early/often, humanise by featuring people, bright high-contrast visuals, audio + text supporting the story, CTA reinforced by voice-over | a **structural checklist** on a cut before it ships; it is the most operational thing found | a target number. Its +30% / +17% are a platform's own study with no published sample |
| **Attention + distinctive assets** (Nelson-Field × VCCP 2025) | the argument that **unattributed attention is wasted spend** — relevant to every "should the product be in this shot" call | quoting the "66p in every £1" figure to a client. That is a marketing number from their own model |
| **Brand placement and sharing** (Tellis et al. 2019, PRIMARY) | the one **peer-reviewed, independent** placement finding this skill owns | anything other than sharing. See `hook-craft.md` §5b for how the three reconcile |
| **TikTok Creative Center** | a real corpus of ads with outcome SIGNAL and usable metadata — duration, CTA, primary text, CTR *buckets* | a benchmark. It is a **library of winners**: no control group, bucketed CTR, ~6-month window, thin outside US/UK/WEU |
| **Emotional vs rational by horizon** (Binet & Field, IPA Databank, 1,000+ proven-ROI cases) | choosing the **register** for an objective: rational drives spikes that DECAY, emotional is associated with durable growth | quoting **60:40** as though it were measured on TikTok. It is largely TV-era, survivorship-biased, disproportionately UK — and its own critics note the ratio "became a meme, and memes lose their conditions" |
| **The abandonment curve** (UMass/Akamai, 65M users, 257M ad views, matched pairs) | the **shape**: ~1/3 gone by the quarter mark, ~2/3 by halfway — the loss is front-loaded. And a useful corrective: 15s vs 20s completion differed by **3%**, 20s vs 30s by **4%** | ⛔ almost everything else. It is **2013 desktop pre-roll** — interruptive, in a player, thirteen years old. Our medium is a 2026 vertical feed where the ad IS the content |

### ⚡ What all of it adds up to — the objective picks the register

Four independent sources, four different outcomes, and **they stop conflicting the moment you stop
reading them as one question**:

| If the objective is… | Register | Brand | Leaning on |
|---|---|---|---|
| **sharing / reach** | emotional — positive arousal: amusement, excitement, inspiration, warmth | **late and light**; an announcement in the first beat has a measured cost | Tellis 2019 (PRIMARY) · Binet & Field |
| **attribution / recall** | whatever the brief wants, but the distinctive assets are IN it | **present from frame one** — presence, not announcement | Nelson-Field × VCCP · ABCD |
| **conversion / activation** | rational, direct, specific — and **expect the effect to decay** | present and named; a CTA reinforced by voice-over | ABCD · Binet & Field |

Two things worth carrying out of that table. **Tellis found only ~7% of YouTube ads evoked strong
positive emotion at all** — the bar for the first row is low and almost nobody clears it. And Binet
& Field's warning applies to the third: an activation-only diet buys spikes that decay, and does not
build the thing that makes the next spike cheaper.

⛔ **The register half stays a human call.** `script_score.py --objective
sharing|attribution|conversion` applies the *brand* half mechanically — it knows which finding
applies to this video instead of stating the sharing one as if it were the only one. **No tool here
can score "emotionally-led"**, and one that claimed to would be the virality predictor again.

### ⛔ The only tier-1 benchmark is this client's own data

*"Is 0.8% good?"* has no external answer. It is answerable against **this client, this offer, this
audience, over time** — which is exactly what `ledger.py publish` and `pull_metrics.py` exist to
accumulate, and why the ad-name join key in `pm-workflow.md` matters more than any table above.
**Judge a video against the last ten of its own.** Use an external figure only as a sanity check on
the order of magnitude, and say which one you used.

⚠️ This is also the honest reason the skill has no virality predictor and will not grow one: §0
above settles what can be predicted before a thing ships, and none of the data found on 2026-09-18
changes that answer.

### 🔍 Specified, not run — `lab-00002`

The one design that makes the Creative Center's selection bias survivable: **compare the top bucket
against a lower bucket WITHIN one industry, objective and format** — that is a control group inside
the library. ~40 ads, coded on dimensions this skill already claims matter (where the brand is first
*present* vs first *announced*, whether the hook has a concrete anchor and a withheld term, cuts in
the first 6s, whether a turn carries a reaction). **Predictions committed before coding**, or it is
pattern-matching. Correlational, confounded by offer and audience, and roughly a day of manual
coding — that day is the real cost, and it would be the first time the creative half of this skill
argued from outcomes rather than from taste.

## 1. The diagnosis waterfall — read metrics in this order, never in isolation

Each metric isolates ONE stage of the video. A "bad video" verdict without locating the stage is
useless for the writeback — the whole point is knowing WHAT to change in the next batch.

| Stage | Metric | Formula (Meta fields) | Weak | Strong | If weak, change… |
|---|---|---|---|---|---|
| 1. Hook (0–3s) | **Hook rate** | 3s video views ÷ impressions | <25% | 35%+ | the hook ONLY — first frame, first line, pattern interrupt. Body is unindicted. |
| 2. Body | **Hold rate** | ThruPlay ÷ 3s views | <40% | 60%+ | pacing, proof, the reactivity of the middle — hook is doing its job. |
| 3. Depth | **Retention quartiles** | p25/p50/p75/p95/p100 watched | cliff at a quartile | smooth decay | the beat AT the cliff — pull the script, find what happens at that timestamp. |
| 4. Offer | **CTR (link)** | link clicks ÷ impressions | <0.5–1% | 1.5%+ | CTA framing, offer, end-card — they watched but didn't act. |
| 5. Landing | **CVR** | conversions ÷ link clicks | — | — | NOT the video. High CTR + low CVR indicts the landing page or audience, not creative. Say so in the debrief instead of re-cutting. The first check on the page is the message match: the first screen the ad lands on states the ad's offer in the ad's words. |

⛔ **These bands are META-SHAPED, and applying them to another platform is a category error.**
The hook-rate range was derived on Meta's *3-second video plays*. TikTok's nearest metric is
**2-second video views** — a different measurement — TikTok has **no ThruPlay** at all, and YouTube
Studio exposes **no sub-3-second metric**, so a hook rate simply cannot be computed there. Google
Ads' "TrueView view" is a 10s/30s threshold, not a hook read. `pull_metrics.py` therefore computes
each platform on its own fields and marks every non-Meta row **UNBENCHMARKED** rather than scoring
it against a band it was not built from.

⛔ **And do not total "views" across platforms.** TikTok counts a view when playback *starts*;
Instagram counts replays; Meta's paid ladder has no "views" column at all; and **YouTube redefined
the word twice in eighteen months** — Shorts on 2025-03-31, then *all formats* on 2026-08-24
[PRIMARY · support.google.com/youtube/answer/2991785 · 2026-09-08]. Any time series crossing those
dates has a discontinuity; `engagedViews` is the continuous one, so store both. A cross-platform
"total views" is a number with no referent.

⚠ **Meta's quartiles are not a retention funnel.** `Video plays at 25%` etc. "**including plays that
skipped to this point**" [PRIMARY · facebook.com/business/help/1792720544284355]. A cliff between
two quartiles is therefore not necessarily a drop-off, and TikTok's equivalents carry no such
caveat — so the two platforms' quartiles are not comparable either.

⚠ **`Results` is objective-dependent** — "based on the objective and settings you selected"
[PRIMARY · same]. Two ads in one export can have `Results` meaning different events. Never sum it.

⚠ **A client's "click-through rate" may be a cost.** Stage 4's CTR is a ratio; what a client reads
out under that name is sometimes a cost per link click, in currency. Ask which column they mean, and
store the platform's own column name and its value, never the spoken word — so a cost is never read
as a percentage in the debrief.

Benchmarks are [SECONDARY] practitioner ranges (vertical- and price-point-dependent); the field
formulas are [PRIMARY]. The waterfall logic itself is the durable part: **fix the earliest weak
stage first** — a better body under a dead hook is unmeasurable, so hook fixes always outrank body
fixes in the next batch.

Meta's own creative feedback: **ad relevance diagnostics** (quality / engagement-rate / conversion-rate
rankings vs ads competing for the same audience) [PRIMARY]. Use as a tiebreaker, not a target —
"below average" on quality ranking plus a weak hook rate is converging evidence.

---

## 2. The join key — ad naming IS the schema

The API returns rows keyed by ad ID and ad NAME. Nothing else connects a platform row to the hook
bank, the shot manifest, or the batch plan. So the name carries the join key:

```
<BRAND>-<bodyID>-<hookID>-<personaID>-<variant>   e.g.  ACME-B2-H07-P1-a
```

Rules — these are what make §8 automatable, treat them as lint:

- **Assigned at batch-plan time** (`scripts/batch_plan.py` output), not at upload time. The person
  uploading (you or the client) copies the name verbatim; it is in the delivery manifest.
- IDs match the hook bank and body register EXACTLY (H07 in the ad name is H07 in the bank).
- Never rename a live ad — the name is the primary key; renames orphan history. Duplicate-and-rename
  creates a NEW ad in the metrics (Meta treats it as one, but your join must too: new variant suffix).
- UTM parameters are the secondary key for CVR-side joins (same IDs in `utm_content`). Secondary
  because ad names survive in every report export; UTMs only survive where analytics is wired.
  [Own synthesis — the naming convention itself is standard practice, SECONDARY.]
- Parse defensively: split on `-`, validate against the hook bank, and quarantine rows that don't
  parse (client-made ads, boosted posts) into an "unattributed" bucket rather than dropping them.

If the client runs the ad account and won't adopt the convention: ask for a **Scheduled Export**
(§4) with ad name + the waterfall fields, and maintain a manual name→ID mapping table in
`09-qa/`. Degraded but workable; say so in the capacity plan.

---

## 3. Statistical floors — when a number is allowed to mean something

- **There is no official platform minimum-impressions floor for creative testing.** Anyone quoting
  one is quoting folklore. Meta's ~50 optimization events / 7 days figure is the **learning-phase
  exit** — a delivery-mechanics threshold, not test significance [PRIMARY for what it is; misused
  constantly].
- Practitioner floor for READING a hook rate: a few hundred to ~1,000 impressions per hook
  [SECONDARY, converging but not verified — convergence ≠ verification]. Below that, the number is
  noise; the hook stays "in test" in the bank regardless of how good or bad it looks.
- Promotion to the standing bank requires the two-witness bar the bank already uses: beat the bank
  average **on two separate runs** (different bodies or different weeks), each above the impressions
  floor. One great week is one witness.
- Retirement is cheaper than promotion: two reads below bank average above the floor → retire. Note
  WHY in the retired table (hook-stage failure vs body dragging it down — check hold rate before
  blaming the hook).
- Small accounts (client trials, 8-video batches) may never clear the floor per-hook. Then the
  honest debrief output is **directional reads + qualitative review**, labeled as such — never
  dress sub-floor numbers as findings. The verification readout rule applies: assumed/underpowered
  ⇒ NEEDS INPUT, not a conclusion.

---

## 4. Platform access reality — what it actually takes to pull the numbers

### Meta (Facebook/Instagram) — the main lane
- **Marketing API Insights**, ad level, fields: `impressions`, `actions` (filter
  `action_type=video_view` for 3s views), `video_thruplay_watched_actions`,
  `video_continuous_2_sec_watched_actions`, `video_p25/p50/p75/p95/p100_watched_actions`, link
  clicks, plus spend. All [PRIMARY]. `video_play_curve_actions` exists for a retention curve; its
  exact response shape is [UNVERIFIED] — test before building on it.
- Access tiers renamed **May 4 2026: Limited / Full** (was Development/Standard). Full requires
  ~500 successful calls + low error rate over rolling window [PRIMARY]. Limited is enough for a
  single ad account at daily-pull cadence.
- Auth for unattended pulls: **system user token** (Business Manager → system user → non-expiring
  token scoped `ads_read`). Never a personal user token in a cron job.
- **The no-code/no-review bridge: Ads Manager Scheduled Export** — emailed CSV, ad-name column
  included, needs zero API access. This is the default for a client trial; the API is for standing
  monthly clients. Build the parser against the CSV first — same join key, same waterfall — and the
  API pull becomes a drop-in swap later.
- June 15 2026 organic video metric deprecations do NOT touch ads Insights fields;
  `post_video_retention_graph` (organic) survives [PRIMARY].

### YouTube (organic + Ads)
- **YouTube Analytics API**: `audienceWatchRatio` by `elapsedVideoTimeRatio` gives the full
  retention curve — better resolution than Meta's quartiles [PRIMARY]. OAuth in **Testing mode**
  (<100 users) needs no app review for own/client channels.
- **Google Ads API** (for YouTube ad campaigns): Basic Access application required; developer token
  + OAuth. Heavier lift — only when a client actually runs YouTube ads at volume.

### TikTok
- Business API view definitions: 2s and 6s views [PRIMARY]. Exact JSON field names [UNVERIFIED] —
  confirm in the sandbox before writing the parser. Separate business-portal app review. TikTok's
  hook window is 2s, not 3s — the waterfall's stage-1 formula swaps accordingly; do not compare 2s
  hook rates against Meta 3s benchmarks.

---

## 5. Pull cadence and where the data lives

- **Daily pull** (or daily scheduled export), ad level, previous day.
- **Trailing 7-day re-pull** every run: attribution restates — yesterday's conversions grow for up
  to a week. Overwrite the trailing window, never append-only, or CVR trends lie.
- **Spreadsheet first.** One sheet per brand: raw rows (as pulled) + a computed tab (waterfall
  columns + parsed join-key columns). Move to a database only when a qualitative breakdown the
  sheet can't express is actually blocking — not before. The hook bank stays the human-readable
  ledger; the sheet feeds it, doesn't replace it.
- The writeback into the bank stays a **reviewed step**, not a blind sync: numbers auto-fill,
  promotion/retirement is decided by a person against §3's bars. (Same shape as self-evolution:
  the pipeline proposes, the human promotes.)
- Off-the-shelf comparable: **Motion** ($99–499/mo) does creative analytics with naming-convention
  joins. The buy-vs-build line: one brand, spreadsheet + scheduled export wins; several brands with
  standing ad accounts, Motion's price is under an hour of your month. Re-check pricing before
  quoting — [SECONDARY, checked 2026-08-28].

---

## 6. What this feeds — the writeback contract

`modes/ugc-volume.md` §8 step 1 consumes this file's output. The contract:

1. Every shipped ad carries the §2 join key in its platform ad name (batch-plan manifest column).
2. After the floor (§3) is cleared, waterfall metrics land in the hook bank's columns — hook rate
   and hold rate per hook ID, quartile-cliff notes per body ID.
3. Promotion/retirement decisions cite the numbers and the floor ("H07: 41% hook rate over 2.3k
   impressions, two runs — promoted").
4. Stage-3+ findings (retention cliffs, CTR) go to the BODY register and the debrief, not the hook
   bank — the bank only ever answers "which openings earn attention".
5. A client debrief with numbers ships behind the verification readout (`pm-workflow.md`):
   measured (API/export) vs estimated (sub-floor directional) vs assumed — labeled per figure.

**Built 2026-09-08: `scripts/pull_metrics.py`.** The CSV/export path, as §4 called for.

```
pull_metrics.py ingest <export.csv> --platform meta|tiktok|youtube|googleads --root <prod-root>
pull_metrics.py report <prod-root> --client <brand> --month 2026-09
pull_metrics.py hooks  <prod-root> --client <brand> [--write _series/<BRAND>/HOOKS-USED.md]
```

⛔ **The finding that shaped it: none of the four platforms has a fixed export schema.** The header
row is whatever columns the user ticked, no platform publishes a default set or a header list, and
the headers *are* the UI display strings — so they change with the account's language
[PRIMARY research pass · 2026-09-08]. A positional parser is guaranteed to be wrong eventually and
silently. The tool is column-NAME driven, **quarantines every unrecognised header and names it**,
and takes `--map "Header=field"` so a new column is closed without a code change. It also drops
Meta's summary/totals row (the quick export "includes summary totals", and the totals row carries no
ad name — counting it would add a phantom video carrying the whole month's spend), and parses
numbers locale-safely, because Google Ads documents that an account may render `2,000.50` or
`2.000,50` and **no platform documents an export-locale override**.

⛔ **The organic join is OURS to make.** No platform guarantees a field we control in its export —
YouTube's `Video title` is the only confirmed one of the four. So `ledger.py publish <job>
--platform <p> --post-id <id> --url <permalink>` records the join at upload time, and ingest uses
it. Without that record an organic row can never be attributed, and the tool reports it as
**UNATTRIBUTED** rather than dropping it.

⚠ **Three of §1's five stages are analysed; two are not.** Hook, body and offer are computed.
**Stage 3 (retention quartiles / the cliff) and stage 5 (CVR) are parsed and stored but not yet
read**, so `change_next` never points at them, and §6 item 2's "quartile-cliff notes per body ID"
has no writer. Say so in a debrief rather than implying the waterfall ran end to end.

**Still not built, and honestly so:**
- **No API leg.** YouTube Analytics API and Google Ads API are both reachable for our own
  properties (a Cloud project in Testing mode; a Basic-access developer token) and are the obvious
  next step. Meta's Marketing API needs no App Review for *your own* ad accounts but lands in
  **Limited** tier — "for development only, not for production apps running for live advertisers" —
  and reaching Full needs 500 calls in 15 days, which 30–50 videos/month may never generate.
  ⛔ **TikTok organic watch-time has no realistic API path for a small agency**: the Display API
  returns no watch time or retention at all, and the Organic API is partner-gated. TikTok is
  manual-export-only, which is why its CSV parser has to be the most robust.
- **XLSX is refused, not half-parsed.** It is actually the *safer* download from Meta and Google Ads
  because numbers arrive typed; the tool just carries no xlsx reader and says so.
- **No golden fixtures yet.** Every header name in the alias table came from a platform's own
  documentation, but **no platform publishes the export's actual header row** — so the alias table
  is what we have verified, never a schema. The cheapest thing that would close this: export one
  file per surface, commit them as fixtures, and add a test that fails when a header set drifts.
