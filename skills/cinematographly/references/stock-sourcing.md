# Stock sourcing — the licence decides, not the shot

> **Stock is one source of real footage; this file is about its licence.** How real footage and
> generated footage are actually *joined* — the seam taxonomy, matching a generation to a plate, what
> to shoot vs generate, and the disclosure exposure a mixed timeline creates — is `real-and-ai.md`.
> ⛔ The hard block on recognisable faces in stock applies with more force in hybrid work, not less:
> a real identifiable person cut next to synthetic material is the one seam this skill treats as a
> legal question before a craft one.

**When to read this:** you are about to pull a photo, a clip or a music bed off a stock library for
an ad — as visual reference, as a start-frame input, or as a bed under the mix. The deciding
question is never "is this the right shot", it is **"can this shot ship"** — a licence question with
a *per-asset* answer, not a site-level one.

Facts below are tiered per `research-quality.md`, checked **2026-08-28**, and are Pixabay's own
words unless marked otherwise [PRIMARY · pixabay.com/service/terms/ · /service/license-summary/ ·
/service/faq/ · /api/docs/]. The terms version in force at this check is **2024-11-18**; licence
pages change without announcement, so re-read before a new client engagement and record the version
date you actually downloaded under (§9).

---

## 0. What stock is FOR here — and what it is not

Not cut-in b-roll. At 30–50 vertical ads a month the footage in the cut is generated
(`ai-generation.md`); stock plays two much narrower roles: **visual reference** — the look handed to
a prompt: light quality, palette, room type, wardrobe, the texture of a real surface
(`production-design.md`) — and **start-frame input**, a still fed to an i2v model as frame one
(`prompting-craft.md`). Plus music beds (§8).

**This is why the 9:16 shortage matters far less than it first looks.** A landscape reference is a
perfectly good style input to a vertical generation: you are borrowing the light, the palette and
the surface behaviour, not the framing. Reserve the hunt for portrait assets for the case where the
sourced pixels themselves ship — rare here, and fortunate, because portrait is exactly what the
video API cannot filter for (§6).

## 1. The grant — genuinely permissive, and not where the risk lives

The Pixabay Content Licence grants an "irrevocable, worldwide, perpetual… non-exclusive and
royalty-free right to download, use, copy, modify or adapt the Content for commercial or
non-commercial purposes." **Attribution is not required in the finished ad** (§7 carries the
separate obligation that *is* real). Paid social for a paying client sits squarely inside
"commercial"; "modify or adapt" covers cutting, retouching and compositing; "perpetual" means the
downloaded file is yours to keep. **The licence does not differ by media type** — Audio is Content
exactly like an image is.

**The exposure is not the grant. It is everything the grant does not cover** — §2 and §3 — and all
of it is decided by what is inside the frame, one asset at a time.

## 2. What the licence forbids

- **Standalone redistribution.** No selling or distributing Content "on a Standalone basis" — no
  creative effort applied, substantially unchanged. An ad is a new work; a clip exported with a logo
  bumper stuck on the end is uncomfortably close to the line (§5).
- ⛔ **The trademark rule is a flat prohibition, not a caution.** "If Content depicts any trademarks,
  logos or brands… you cannot use that Content for commercial purposes in relation to goods and
  services." No cure exists inside the licence — no disclaimer, no de-emphasis, no "it's only in the
  background". A visible mark removes that asset from commercial use.
- **Misleading or deceptive use**, expressly including **suggesting endorsement or affiliation** —
  easy to trip in wellness: a stock clinician, a stock lab bench.
- **Immoral or illegal use**, "especially Content which features a recognisable person"; and **use
  as part of a trade mark or business name** — no stock element inside a logo lockup.

## 3. What the licence does NOT give you — the part that costs money

The rights reservation is explicit. Content "may be subject to additional intellectual property
rights… includes but is not limited to identifiable people, logos, brands…, buildings and
architecture, audio or video samples and organisations", and — the sentence to memorise —
**"Responsibility for determining whether permissions are needed always rests solely and exclusively
with you."** On model releases the position is narrower than most people assume: Pixabay **requires
uploaders to hold** releases where needed but does **not provide, warrant or furnish** them, and its
own guidance is that "It is best to contact the artist and inquire about a model release if a person
is recognisable". Everything is supplied **"AS IS"** with all warranties disclaimed, and ⛔ **you
indemnify Pixabay** against third-party claims arising from your use — the inverse of a
rights-managed library: no fallback, no legal defence, nobody to call.

Read together, a permissive licence over an **unwarranted** chain of title: a fine trade for
reference material, a bad one for a face in a paid ad (§5).

## 4. Using stock as AI input — what is actually documented

⛔ **For images and video, the licence is silent.** There is no prohibition on using Pixabay content
as reference or start-frame input to a generative model anywhere in the terms, the licence summary
or the FAQ. It is permitted **by implication**, through "modify or adapt" — a reasonable reading,
not a written permission. Record it in the client file as exactly that.

The one explicit statement concerns **music**: adapting Pixabay music with AI tools is allowed "as
long as the final result is a new, original creative work and the music is not redistributed on a
standalone basis" — no AI rule, just the standalone test that already governs everything else.

**The miscitation to stop repeating:** ToS §7A, in which *uploaders* grant Pixabay the right to
train on uploaded content, runs in the **opposite direction** — it is Pixabay's permission from its
contributors, not yours as a downloader. It circulates as if it settled the downloader question; it
does not touch it.

**And the rule that outranks all of the above:** §5's per-asset check applies to the *output* too.
The generator launders pixels, not rights.

## 5. ⛔ What blocks a shot from shipping — checked per asset, every time

This is the section that matters. The licence is permissive; the exposure is entirely in what is
inside the frame. Run this on every asset you pull, and **again on every frame a model generates
from it**. Not a once-per-library judgement, and not delegable to a tool.

| Blocker | Why it blocks | Verdict |
|---|---|---|
| **A recognisable face** | No release, none obtainable in practice, none warranted, and you have indemnified the platform (§3) | ⛔ **Hard block for final footage.** Reference-only is defensible *provided the output does not reproduce the likeness* |
| **A visible trademark, logo or brand** | Flat licence prohibition for commercial use (§2) | ⛔ Block. Not cured by cropping to "mostly gone" — remove it cleanly or drop the asset |
| **A distinctive building or private property** | Named in the reserved-rights list; property releases exist for a reason | Block for final footage; reference only, with the structure not reproduced |
| **Insufficient transformation** | A near-raw clip with a bumper on it is close to standalone distribution (§2) | Block until it is genuinely a new work |
| **AI output that inherited a protected element** | The model kept the face, the mark, the façade | ⛔ Block — same check, same verdict, no discount for being generated |

**Why the face rule bites harder in this account's categories.** In sleep, wellness and home a
person in frame is not scenery: the ad implies a **health state** or **product use** by the person
shown — closer to an endorsement shape than to decoration, which drags in `compliance.md` §2. An
unreleased stranger appearing to endorse a wellness product is a claims problem *and* a rights one,
so a stock face is two exposures for the price of one.

**The reference-only carve-out, precisely** so it is not over-read: a style, light or palette
reference is defensible when the delivered frames do not reproduce the identifiable person, the mark
or the building. The moment the output *does* — i2v held the start frame faithfully, the face
survived the pass — it is a shipping asset again and the hard block applies. **Check the output, not
the intent**; `realism-qa.md` runs the frame-level pass where this gets caught.

## 6. The API — what it can and cannot do

Two documented endpoints, both `GET`, both JSON: images `https://pixabay.com/api/` · videos
`https://pixabay.com/api/videos/`. **Shared parameters:** `key`, `q` (≤100 characters, URL-encoded),
`lang`, `id`, `category`, `min_width`, `min_height`, `editors_choice`, `safesearch`, `order`
(`popular`|`latest`), `page`, `per_page` (3–200, default 20), `callback`, `pretty`. **Images only:**
`image_type` (`all`|`photo`|`illustration`|`vector`), `orientation` (`all`|`horizontal`|`vertical`),
`colors`. **Videos only:** `video_type` (`all`|`film`|`animation`).

⛔ **The video endpoint has no `orientation` parameter.** Vertical cannot be filtered server-side at
all. The only route is **over-fetch and filter client-side** on each rendition's `width`/`height` —
what `scripts/pixabay_search.py --vertical` does, and why that flag exists rather than being passed
through. `min_width`/`min_height` do not help: they constrain **absolute pixels, not aspect**, so
`min_height=1920` happily returns 4K landscape.

**Video response:** a `videos` object with `large`/`medium`/`small`/`tiny`, each carrying `url`,
`width`, `height`, `size`, `thumbnail`; plus `duration` (seconds), `pageURL`, `tags`, `user` — the
rendition, not the hit, is the unit of the aspect check.

**Image response — you choose the size, and a default key is not thumbnail-grade.** A default key
returns `previewURL` (≤150px), `webformatURL` (≤640px, **valid 24 hours**) and **`largeImageURL`
(≤1280px)**, plus `imageWidth` / `imageHeight` / `imageSize` describing the original. The
`webformatURL` is also resizable in place: **replace `_640` with `_180`, `_340` or `_960`**
[PRIMARY · pixabay.com/api/docs/ · checked 2026-08-28]. Only three fields need approved **full API
access**: `fullHDURL` (≤1920px), `imageURL` (the original) and `vectorURL`.

So the practical ceiling on a free key is **1280px**, which is enough for reference and for most
start-frame work at 1080×1920 — the shortfall is a top-up, not a blocker. Request full access when
you need the original or true 1920px; do not treat it as a precondition for using the API at all.
Note that a `webformatURL` expiring after 24 hours is a second, independent reason the pipeline
downloads rather than links.

⛔ **No API field indicates AI-generated content.** Uploaders must label AI work, but the label is
exposed neither as a filter nor as a response field — it **cannot be detected or excluded
programmatically**, and the library holds AI material by design. "Photographic reference, not AI" is
a human eye on every asset, not a query parameter — and it is how stock quietly re-introduces the
generated look you are designing out (`photorealism-physics.md`).

## 7. Rate limits, the caching rule, hotlinking, and the two attributions

- **Rate limit:** 100 requests per 60 seconds by default. Every response carries
  `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` — read them rather than guessing
  at a sleep. **"Systematic mass downloads are not allowed."** Default access also caps results at
  **500 per query**.
- ⛔ **"Requests must be cached for 24 hours."** The wording is genuinely ambiguous between a floor
  (do not re-request the same query inside 24h) and a ceiling (do not hold a response longer than
  24h) — say so rather than picking a reading silently. The house implementation satisfies **both**:
  serve from cache while an entry is under 24 hours old, discard it after. Caching is not an
  optimisation here, it is a term of use — which is why `pixabay_search.py` refuses `--no-cache`.
- ⛔ **"Permanent hotlinking of images… is not allowed… please download them to your server first."**
  Nothing in an ad, a picker UI or a deck may point at a Pixabay URL.
- **Permanent storage of the downloaded media is fine** — it follows from the perpetual grant (§1).
  **The 24-hour rule governs API responses; the perpetual licence governs media files. Different
  objects, different rules** — conflating them produces either an out-of-terms cache or a pointless
  re-download of assets you may keep forever.

**The two attribution obligations are not the same obligation:**

| Obligation | Where it applies | What satisfies it |
|---|---|---|
| The **licence** | The finished ad | Nothing — attribution is not required |
| The **API terms** | Your own tooling | "Show your users where the images and videos are from, whenever search results are displayed" — render `pageURL` and `user` on every result |

Which is why every line and every JSON record out of `scripts/pixabay_search.py` carries `pageURL`
and `user`: structural, not a display preference someone can switch off.

## 8. Music — a manual lane, on purpose

**There is no documented audio endpoint** — the API covers images and video only. An undocumented
`/api/audio/` path resolves at the router, but it is [UNVERIFIED], undocumented and unsupported:
**do not build on it**, and treat any tool that does as a liability rather than a shortcut.

So music is a **manual website fetch into a local library**: pull the track by hand, file it in the
project's `06-music/` with the BPM in the name (`pm-workflow.md`), and write the same provenance
record as any other asset (§9). Licence-wise music is unremarkable — Audio is Content, the grant is
identical, a bed under a commercial video is fine, and **delivering the track itself is standalone
redistribution** and prohibited. [UNVERIFIED] whether Pixabay music trips Content-ID-style matching
on Meta or TikTok: a **delivery** risk, not a licence one — a false match can mute or pull an ad
that is perfectly licensed. Test a bed once per platform before standardising on it
(`editing-and-audio.md` prefers a small vetted bed library to a fresh track per video).

**Every sound in the mix also gets a row in the job's audio manifest** (`09-qa/mix/AUDIO-MANIFEST.md`,
`editing-and-audio.md` §7c): the bed, every effect, every voice, and an AI-made sound's tool, version,
plan and region. `approve export` refuses while a row is missing, names no licence that covers paid
advertising, or hits a known block (`assets/ai-audio-licences.json`).

**Editing a track is a use the licence has to allow.** Whole-bar edits, a stretch, stems and an arrangement
(`music_fit.py`, `editing-and-audio.md` § Music to picture) change the track. Record `edits_allowed: yes` in
the job's hit list only once the licence says so. The fitted bed's `.conform.json` names the track it came
from, so the bed inherits the track's row in the audio manifest.

**Generated music** follows the compose policy in `editing-and-audio.md` § Music bed:

- library music arranged by default;
- a generator for a temp track only, logged;
- shipped only case by case: consent before generation, a whitelisted vendor, a terms snapshot, a passing
  blind bake-off;
- Sonilo excluded.

**Instruments for music composed here** (route 1) carry their own licences in
`assets/music-instruments.json`; an instrument with no row there does not render client music.

## 8b. Sound effects — the libraries on the machine first

Author, 2026-10-26: *"I have the Fairlight SFX pack too installed … You can find many effects there too"*.
Search what is already licensed and on the machine before downloading anything:
`sfx_conform.py library search "<the read's words>" --paid-ads-only`, then `library pull` into the job,
which carries the licence into the audio manifest (`editing-and-audio.md` §7f). Each library's terms
travel with its catalogue:

| Library | Paid ads | Terms, and where they come from |
|---|---|---|
| **Fairlight Sound Library** (Blackmagic, about 500 foley files) | yes, **in a Resolve project** | Royalty-free, for personal or commercial projects, but **only in projects made with DaVinci Resolve**. Films made from them may be distributed; the sounds themselves may not be leased, sold, distributed or sub-licensed [PRIMARY · Blackmagic's download terms, cl. 1.2 and 1.4, checked 2026-10-26]. This skill finishes in Resolve, so the condition holds; a mix finished anywhere else does not |
| **Final Cut Pro Sound Effects** and **impulse responses** (Apple, extracted from `FCPContent.pkg`) | yes | Royalty-free in your own soundtracks for film, video and audio, which you may broadcast and distribute. The files may not be distributed on their own, or repackaged as sound files or samples [PRIMARY · Apple support, HT204260, checked 2026-10-26]. The right comes with the Final Cut Pro licence |
| **Pixabay sound effects** | yes | The Pixabay Content License, as for images and video (§1–§3); per file, recorded in the library's CSV |
| **Ocular Sounds** (18 packs, 3,644 sounds, bought 2026; `Fairlight Sound Library/Ocular Sounds/`) | yes | The product pages list "films, games, trailers, ads, music, social content". Conditions: the sounds stay part of a larger production, never shared or resold on their own; never "the main element of a music track"; the licence is **per person**, so an outside editor needs their own seat [PRIMARY · ocularsounds.com product pages and licence summary, checked 2026-10-27]. Every file was checked against its pack's metadata sheet on arrival |
| **Ghosthack** (SFX packs and Coriolis construction kits) | **unverified** | The FAQ names music, movies, games and YouTube, not ads, and bars releasing rendered kit songs as your own; no licence text came in the zips [PRIMARY · Ghosthack FAQ, checked 2026-10-27]. Not used in client ads until the licence is read |
| **BBC Sound Effects** (sound-effects.bbcrewind.co.uk) | ⛔ **no** | The free downloads are under the RemArc licence: personal, educational or research use only [SECONDARY · MusicRadar; the BBC's own licensing page was not reachable from this session]. **Never in client work.** A paid commercial licence may exist; it is the owner's call, per project |

⛔ **Never upload or share a library's raw files**, to a client folder, a cloud drive or an AI tool's
inputs. Every licence above forbids distributing the sounds themselves. Only the finished mix leaves the
machine.

**Downloading a Pixabay sound effect — through the person's own browser, one file at a time** (a supplement ad job, 2026-10-27:
Pixabay is blocked from the cloud session and from the Mac shell, and repeated clicks left 11 copies of one WAV in
Downloads):

1. One click per file. Before clicking again, look in `~/Downloads` for the file (and its `name (1).wav` copies) — a
   download that seems not to have started usually has.
2. Move each file straight into `Fairlight Sound Library/SFX Downloads (Pixabay)/library/<category>/`, named
   `<author>-<slug>-<pixabay id>.<ext>`. Delete the extra copies (the owner grants `device_bash` delete permission once,
   for Downloads only).
3. Add its row to that library's `library.csv` (path, author, title, id, page URL, licence, duration, category) and write
   its provenance JSON beside it (§9: source page, author, licence, the date, the sha256).
4. Relink Resolve to the library copy, never to the one in Downloads.
5. Then `sfx_conform.py library search` finds it like every other library sound, licence and all.

**Placing and levelling the sounds** is measured, not guessed: `sfx_conform.py levels <job>` sets each event's gain from
the voice's momentary loudness at that moment, by category, under a −6 dBFS peak ceiling, and moves each in-point to the
file's own transient (`editing-and-audio.md` §7f). The density to aim for is the client's (`clients/audio.<brand>.json`,
measured from the client's own reference ads: one client's was up to 13 events a minute).

## 9. The provenance record — per asset, written at download time

> ⛔ **Enforced since 2026-09-06.** `scripts/prompt_lint.py` refuses a reference with no sidecar, so
> no asset reaches a prompt without one. `scripts/pixabay_search.py` writes it on download;
> **`scripts/provenance.py record`** writes it for everything else — the client's own files, your
> own shoot, licensed stock, an AI generation (which needs `--derived-from`, because a generation
> inherits every block its inputs carried). In both, **clearance is DERIVED from the four §5
> blockers below, never asserted**: each must be answered, `released:<who>` or `owned:<who>` clears
> one, a note does not, and a human name has to sign it. `provenance.py audit _reference/` prints
> the whole set and re-hashes each file, so an asset swapped after its record was written is caught.
> ⛔ **And since 2026-09-07 `prompt_lint.py` re-hashes on the ENFORCED path too** — until then
> this sentence was true of a command no gate ran, so a re-download, a hand-edit or a "better
> version" dropped over the file inherited the old clearance silently. A sidecar with no
> `sha256` now warns, because nothing can tell whether that file is still the cleared one.

Same discipline as the shot manifest (`pm-workflow.md`): written **when the file lands**, never
reconstructed at review. Per asset — `id` · `pageURL` · `user` · download date · **the licence terms
version date in force** (2024-11-18 at this check) · the rendition URL actually fetched · dimensions
(and duration, for video) · tags.

It lives **with the asset in `_reference/`** — the project's input folder, outside the numbered
stages — as a `.json` sidecar per asset,
indexed from the shot manifest, so a generated clip traces back through its start frame to the
source asset and the terms it came under. `scripts/pixabay_search.py --download` writes it
automatically, including the outstanding §5 checks as an explicit list so the sidecar never reads as
a clearance. A hand-pulled music track gets the same record, typed by hand, in `06-music/`. **Why
the terms version date and not just the URL:** if the licence changes, the question a client's
counsel asks is what you downloaded *under*, not what the page says today.

⛔ **The sidecar's NAME is part of the contract:** `<asset filename>.json`, appended — never
`<stem>.json`. Appending cannot collide (a JPEG's and a PNG's records stay two files, where a
shared stem would collapse them into one), and every reader in the skill resolves it through one function
(`provenance.find_sidecar`, which still reads the legacy stem form for assets downloaded before
2026-09-06). This is not pedantry: two writers using different names and two readers preferring
different ones is how, on 2026-09-06, an asset cleared seconds earlier read back as **NOT CLEARED**
and adoption refused it.

## 9b. Sourcing is a pre-production step, driven by the shot list

Everything above describes what a *good* stock decision looks like. This section is about *when* it
gets made — because the failure this skill kept producing was not a bad asset, it was an asset
chosen at the moment it was needed, from a query invented on the spot, and examined after the render.

The order that fixes it:

| | | |
|---|---|---|
| **1. Declare** | in the shot's own prompt | `- role: image, what: environment, need: rustic kitchen window light` — the slot is designed where the shot is designed. `prompt_lint.py` FAILS a prompt with an unsourced slot, so the declaration cannot rot into a habit. |
| **2. Brief** | `refsource.py brief 01-script/prompts/` | Every unsourced slot becomes a search. Terms come from `need:`, or — when the slot has none — from the shot's own `[ENVIRONMENT]` / `[LIGHTING]` / `[SUBJECT]` blocks, with camera and lighting jargon stripped (`50mm`, `5200K` describe how *you* will shoot it). Aspect drives orientation. The §5 risk for that attribute is printed **before** the search, not after. |
| **3. Fill** | `refsource.py fill … --execute` | Runs those searches through `pixabay_search.py` — same key resolution, same 24h cache, same rate-limit refusal — and downloads N candidates per gap into `_reference/_candidates/<shot>-<attr>/`, each with the §9 provenance sidecar written at download time. |
| **4. Look** | `refsource.py candidates …` | The lookbook. A human reads tags, dimensions, the page URL and the author, and **chooses**. The script does not choose; auto-picking the first hit is how a photograph nobody looked at ends up in a delivered frame. |
| **5. Adopt** | `refsource.py adopt … --shot S3 --what wardrobe --pick <file>` | The pick moves into `_reference/<attr>/` with its sidecar and the shot's ref line is rewritten to point at it. Adoption **refuses** an asset with no provenance, and refuses one still `NOT CLEARED` unless it is explicitly `--use reference-only`. That is where §5 stops being a good intention. |
| **6. Gate** | `gate.py approve cast` / `approve clips` | Refuse while any reference is unsourced or uncleared. Both stages unlock spend; a plan with a hole in it does not reach them. |

⛔ **Step 3 filters what comes back, and this is not optional politeness — it is a correctness
check.** Verified live 2026-09-06: `q="linen apron white plain"` with `orientation=vertical` and
`order=popular` returned **a zebra** among its top hits, and `q="kitchen window small tiled"`
returned **tomatoes** and a stained-glass church window. Each arrived as a normal 200 with a
provenance sidecar written, so nothing downstream would have flagged them — the operator would
simply have been choosing between three irrelevant photographs. So: **a candidate whose own Pixabay
tags share no word with the query is dropped**, the count is printed, and a thin surviving set is
reported as a finding *about the query* rather than a reason to take what is there. The lesson
generalises past this API — **relevance is a claim the vendor makes, and an unchecked claim is not
evidence** — and it is why `need:` keeps the word order a human wrote it in: reordering the phrase
is what produced the tomatoes.

Two things the brief deliberately will not do. It will not search for a `what: voice` slot — the API
serves images and video, and quietly skipping the slot would read as "sourced". And it will not
invent terms when the shot is vague: fewer than two usable words is reported as a finding against
*the prompt*, because a slot you cannot shop for is a slot nobody has actually designed.

The moodboard is the same rule one stage earlier. `develop.py` requires **four real reference
pictures on disk, with provenance, before a concept is written** — files, not adjectives. A concept
whose "one image" was imagined has never been checked against a photograph.

---

## 10. Alternatives — one line each, and one warning

| Library | Covers | How its terms differ from Pixabay's |
|---|---|---|
| **Pexels API** | photos + video | No attribution in the licence, but the API guidelines require a **prominent link back**; 200 requests/hour, 20,000/month |
| **Unsplash API** | photos only | ⛔ **Hotlinking is mandatory** — the exact inverse of Pixabay's rule — plus a required download-tracking ping; 50 requests/hour until production approval |
| **Openverse** | CC aggregator, and it indexes **audio** — its one real advantage here | The **licence varies per item**, so obligations are per-asset (some attribution, some no-derivatives). [SECONDARY — its API returned 403 at this check and was not verified] |

⛔ **Do not build one pipeline across two of these.** Pixabay forbids hotlinking and Unsplash
requires it; mixing them makes correct behaviour depend on which library an asset came from, and the
failure is silent. One library per pipeline, its rules implemented once, the rest reached by hand.

## 11. The honest open question — measure it, don't inherit a verdict

**Nobody has measured what actually matters here.** The portrait share of Pixabay's video library
and the depth of its sleep / wellness / home material are both unmeasured — by this account, and by
any source worth citing. Every confident verdict online about the library being thin (or rich) for a
category is somebody's impression of a different set of queries than yours.

So the recommendation is a measurement, not an opinion. Take the **ten standing queries** this
account actually searches in the client's categories, run them through `scripts/pixabay_search.py`,
and record per query: total hits · how many survive `--vertical` · **how many survive §5's per-asset
check**. That last column is the only one that predicts anything, and it is always the smallest.
Until that table exists the library's fitness is **NEEDS INPUT** (`research-quality.md` §6) — not a
guess in either direction.

---

**Cross-refs:** `compliance.md` (claims, endorsement shapes, disclosure — §5's face rule feeds
straight into it) · `production-design.md` (what a reference is actually *for*) ·
`character-and-props.md` (why a stock face is not a character) · `photorealism-physics.md` (why a
real photo is a strong reference and a weak deliverable) · `ai-generation.md` (start frames and the
i2v pass) · `pm-workflow.md` (`_reference/`, the shot manifest, naming) · `research-quality.md`
(the tiers, the refutation pass, and the decay dates used above).
