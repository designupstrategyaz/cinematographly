# Discovery and search — writing a video that can be FOUND, not just fed

**Why this file exists.** Every retention doctrine in this skill assumes one arrival path: the
video is pushed into a feed and has six seconds to earn the next six. That is not the only path any
more. All three platforms have built search surfaces and monetised them — TikTok Search Ads,
Instagram's keyword-matched Search, and since **July 2026** a Google Search Console property type
for **TikTok, Instagram, X and YouTube** posts. The skill had **zero** coverage of any of it: before
this file, "SEO" and "searchable" returned no hits in the whole tree and "social search" appeared
once, as a single cell in `modes/ugc-volume.md`.

This is a short file on purpose. Almost everything the SEO trade publishes about short-form is
unsourced, and the honest, documented surface is small — **caption text, hashtags, sound, and a
handful of eligibility gates**. What follows is the documented part, with the folklore named.

Researched 2026-09-07; retrieval dates on each row. ⚠ **Platform documentation is the fastest-decaying
tier in `research-quality.md`.** Everything in §2–§4 is a snapshot; re-check before it goes in a
client deliverable.

---

## 1. The thing to internalise first

⛔ **Speech and on-screen text are extracted by the platforms; neither is documented as a search
ranking signal.** This distinction is the whole file, and getting it backwards is how a team spends
a month writing "keyword-rich VO" for no measurable reason.

**What is proven about extraction.** TikTok's Research API exposes a per-video field:

> `voice_to_text` | string | "Voice to text and subtitles (for videos that have voice to text
> features on, show the texts already generated)"
> **[PRIMARY · developers.tiktok.com/doc/research-api-specs-query-videos, page dated "Last updated
> September 1, 2026" · fetched 2026-09-07]**

TikTok also translates **text stickers** and auto-generates captions
**[PRIMARY · newsroom.tiktok.com/en-us/auto-translations-and-captions, 2022-07-21 · 2026-09-07]**.
So the platform reads speech and reads some on-screen text. That is extraction.

**What breaks the inference.** The same API restricts what you may *query* on:

> `Condition.field_name` — one of `["create_date", "username", "region_code", "video_id",
> "hashtag_name", "keyword", "video_length", "view_count", "comment_count", "music_id", "effect_id"]`
> …where `keyword` is defined as **"The keyword in the video description."**
> **[PRIMARY · same page · 2026-09-07]**

Speech is exposed and **not searchable**, even in TikTok's own research tooling. And TikTok's public
Search model card names only three content-side factors:

> "**Content information:** How relevant the content is to your search, hashtags, and the sound
> used." … "For many users, how relevant the content is to the specific term entered is generally
> weighted more heavily than other factors."
> **[PRIMARY · tiktok.com/transparency/en-us/recommendation-system/ · 2026-09-07]**

No captions, no speech, no overlay text in that list. YouTube's Shorts page is the same shape:

> "**Search:** Content is ranked based on various factors. These factors include **how well the
> metadata matches the viewers' search** and whether or not the viewers click and watch the content."
> **[PRIMARY · support.google.com/youtube/answer/11914225 (Shorts variant) · 2026-09-07 — the page
> carries no visible last-updated date, so treat it as the most volatile row here]**

And Instagram's, from Mosseri, ranked in his stated order of importance:

> "1. **Your text in Search.** … We try to match what you type with relevant **usernames, bios,
> captions, hashtags and places**." … "**Use relevant keywords and hashtags in captions.** For a
> post to be found in Search, put keywords and hashtags in **the caption, not the comments**."
> **[PRIMARY · about.instagram.com/blog/announcements/break-down-how-instagram-search-works,
> Adam Mosseri, 2021-08-25 · 2026-09-07]**

Three platforms, three independently written lists, and **all three name text metadata and none
names the audio track or the burned-in text**. ⚠ These are three companies describing their own systems
in marketing prose, so the agreement is not a measurement (§8) — but it is what the record says and
there is nothing better. Write the caption like it is the index, because on the documented record it
is.

**The one place the mismatch is worth exploiting anyway.** Spoken words *do* earn credit on
Instagram — not for search, but for originality: content "narrated with a **new voiceover**" is
named as a material change that keeps a video out of the duplicate-suppression path (§4). And a
caption you have to write anyway costs nothing to write from the script's own words. So the rule
below is cheap either way.

---

## 2. What a writer and an editor actually control

Every row is either 🟢 documented by the platform, 🟡 extracted-but-not-documented-as-ranking, or
🔴 documented as ineffective / undocumented entirely.

| Lever | Status | The documentation |
|---|---|---|
| **Caption / description text** | 🟢 The strongest lever, on all three | IG: match runs against "captions" ✎ · YT: "Search terms are matched with the video and the text in the description" · TikTok: `keyword` = "the keyword in the video description" · Google: "tweaking your **TikTok caption**… to match the rising Google Search terms" |
| **Hashtags** | 🟢 Named by all three — but capped on IG | TikTok Search model card names hashtags · YT Shorts names "Sounds & hashtags" · IG: caption not comments; **now limited to five**, and Instagram's own line is "Using fewer (up to 5) more targeted hashtags… can improve both your content's performance and people's experience" [SECONDARY · Social Media Today · 2025-12-18] |
| **Sound / audio choice** | 🟢 Documented as a search signal | TikTok Search: "…hashtags, and **the sound used**" · YT Shorts: Audio Library sounds aid sounds-page discovery |
| **Title (YouTube)** | 🟢 | "Identify 1-2 main words… feature them prominently in both your description and title" |
| **Cover / thumbnail text** | 🟢 for YT and TikTok ads · 🟡 organic | YT: "title, thumbnail, and description are more important pieces of metadata for your video's discovery" |
| **Spoken words (VO / script)** | 🟡 Extracted, not documented as ranking | §1. Earns originality credit on IG; claimed to lift recall by TikTok's own vendor studies |
| **On-screen text / overlays** | 🟡 Organic inference · 🟢 for TikTok **search ads** | See the blacklist, item 4 — the famous quote is carousel-ad guidance |
| **Keywords in comments** | 🔴 Documented as ineffective | IG, verbatim: "put keywords and hashtags in the caption, **not the comments**" |
| **YouTube tags** | 🔴 Nearly useless by YouTube's own account | "tags play a **minimal role** in your video's discovery"; excessive tags in a description "is against our policies on spam" |
| **Alt text** | 🔴 No documented search use | Instagram documents alt text as a screen-reader accessibility feature only (2018-11-28) |
| **Uploaded filename** | 🔴 Zero documentation, any platform | Pure SEO-blog folklore |
| **Structured data / key moments** | ⛔ Not available to you | Requires editing the watch page, which the host platform owns. Real for a self-hosted video, impossible for a Reel |

✎ Instagram's matched fields also include **usernames, bios and profile names** — account-level, not
per-video, and therefore a client decision rather than an edit decision. Raise it once at onboarding
and never again.

**A cover image, one practitioner's recipe** [PRACTITIONER · course notes, from one lesson]: one face framed
chest-up and two words, the shorter word set much larger than the other. Set the words in Resolve, in
English (titles-and-motion C7), and check that the face still reads at 120 px wide
(`character-and-props.md` T10). The course's own cover words stay in the local notes and never pass into a
client's cover.

---

## 3. Google now measures it, which is the part to tell a client

Google shipped **platform properties** in Search Console in July 2026:

> "Earlier this month, we announced platform properties for Search Console, allowing you to track
> how your social and video posts on **Instagram, TikTok, X, and YouTube** perform on **Google
> Search, Discover, and Google News**. Today, platform properties are globally available to
> everyone." … "you can use Search Console annotations to track whether external updates, like
> **rewriting a YouTube title or TikTok caption**, affect your search performance over time."
> **[PRIMARY · developers.google.com/search/blog/2026/07/platform-properties-social-video-guide,
> 2026-07-29 · 2026-09-07]**

And the companion guide names the exact creative lever:

> "you can use insights to rework your content, such as **tweaking your TikTok caption, adjusting
> your hashtags to match the rising Google Search terms, or editing a new version of the video that
> focuses on the exact details people are searching for.**"
> **[PRIMARY · developers.google.com/search/docs/monitor-debug/analyze-social-video-content,
> "Last updated 2026-07-29 UTC" · 2026-09-07]**

Three Google surfaces carry this content: the **Short video carousel**, the **Latest posts
carousel**, and the **"What people are saying" carousel**.

**Why this matters more than any percentage.** It is a **measurement instrument the client can be
given**, and it closes a loop this skill otherwise cannot close: `performance-metrics.md` can read
in-platform performance but has no read on search demand. Search Console's query themes are demand
data for free — they say what the audience is *asking*, which is hook material (`hook-craft.md` §2,
the gap's three legs) before it is caption material. Instagram's `/p/` vs `/reels/` URL split even
lets you compare formats.

⚠ **Set it up before the batch, not after.** Annotations only compare forward.

---

## 4. Eligibility — the gates that make everything above moot

These are pass/fail, they are documented, and each one is cheap to satisfy at the edit and
impossible to satisfy after the upload.

⛔ **No visible watermark.** Instagram states it three ways:

> "every piece of eligible content (e.g., content that is original, does not violate our community
> guidelines, **has no visible watermarks** and satisfies our recommendation guidelines) is shown to
> a small audience…" **[PRIMARY · creators.instagram.com/blog/recommendations-and-originality,
> 2024-04-30 · 2026-09-07]** · "Don't post reels that contain watermarks, that are blurry or
> otherwise low quality" (2022-08-30, updated 2023-04-25) · "We're **less likely to recommend** …
> content with noticeable watermarks" (2023-05-31).

TikTok's For You feed eligibility standards match: ineligible is *"Reproduced or unoriginal content
that is imported or uploaded without any new or creative edits, such as content with **someone
else's visible watermark or superimposed logo**"*
**[PRIMARY · tiktok.com/community-guidelines/en/fyf-standards/ · 2026-09-07]**. Note the policies say
*watermarks*, generically — not "TikTok logos". A stock-library bug, a screen-recorded UI, an
editor's trial-version stamp all count. This is a `clip_qa` / `export_qc` concern and belongs on the
export checklist, not in someone's memory.

⛔ **Originality, with a counted threshold.** Instagram: "when we find two or more identical pieces
of content on Instagram, we will only recommend **the original one**" — matched "based on audio and
visual signals" — and accounts that repeatedly (**10 or more times in the last 30 days**) post others'
content "will not be shown in surfaces where we recommend content" **[PRIMARY · same, 2024-04-30]**.
The named escapes are material change: "materially edited to become a meme, a parody compilation,
**narrated with a new voiceover** or remixed to express a reaction."

**Read that against `modes/repurpose.md`.** Cross-posting one master to three platforms is normal and
fine; posting the *same file* twice inside Instagram is the failure. And the documented escape hatch
is exactly what a per-platform recut already does.

⛔ **Instagram's recommendation gates cover Search too** — "Explore, **Search**, Reels, and any other
places where we recommend content." So a claims problem is also a discovery problem: Instagram's
Recommendation Guidelines name "content containing **exaggerated health claims** or attempting to
sell products or services based on these claims, such as 'miracle cures'" as non-recommendable. For a
sleep or wellness brand that is `compliance.md` and this file failing together.

**The documented format floor** (and the one real conflict with search optimisation):

| Rule | Platform | Verbatim |
|---|---|---|
| ≤ 3 minutes | Instagram | "In order to be recommended, they must be 3 minutes or less" (2023-05-31 page; the 2022 page words it "your content has to be") |
| 9:16, no borders, high resolution | Instagram | "high-resolution, 9 x 16 vertical videos with no borders" |
| **Text must not cover most of the frame** | Instagram | "**where text does not cover the majority of the screen**" ⚠ found on the 2022-08-30 page, which did not re-fetch on review — re-check before quoting to a client |
| 5–10 words/second of text | TikTok | "We recommend displaying **5-10 words per second** when using text" |
| 9:16, ≥720p, UI safe zone | TikTok | "orienting vertically at 9:16, shooting at least 720P resolution, and keeping your content visible within the **UI safe zone**" |

**[PRIMARY · creators.instagram.com (2022-08-30/2023-04-25); ads.tiktok.com/help/article/creative-best-practices · 2026-09-07]**

⛔ **This is the only documented search-vs-reach conflict, and it is about coverage and pacing, not
about keywords.** A keyword-stuffed overlay treatment can breach Instagram's screen-coverage rule and
TikTok's text-pacing rule at the same time. The *presence* of text is documented as good on both
platforms; the *density* is where the rules bite. See `typography-and-captions.md` for the placement
craft this constrains.

---

## 4b. Facebook — the fourth platform, and the one with the least documentation

Facebook is in scope for any brand publishing across all four surfaces, and it is the least
documented of them. Three things a team that has only shipped TikTok/IG/YouTube will get wrong:

**1. Reels and in-feed video are being merged into one thing.** Meta, June 2025: *"In the coming
months, **all videos on Facebook will be shared as reels**, eliminating the need to choose between
uploading a video or reel"*, and *"Reels on Facebook will also not have any length or format
restrictions"* **[PRIMARY · about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/ ·
2026-09-08]**. For organic Page posting that means **one 9:16 file, not two**.
⚠ Meta contradicts itself: the Reels Publishing API still says *"3 to 90 seconds"*
**[PRIMARY · developers.facebook.com/docs/video-api/guides/reels-publishing · v25.0, undated]**.
Moot at 35–55 s — but never write "Facebook Reels max = 90s" as settled fact, and do not assume the
organic unification extends to **paid Feed placements**, which are governed by a separate placement
page that could not be retrieved **[UNVERIFIED]**.

**2. Facebook does NOT document keyword-in-caption ranking, and porting Instagram's rule there is a
mistake.** Instagram publishes an explicit search playbook (§1). Facebook publishes an AI system card
for search whose body is not retrievable **[UNVERIFIED · transparency.meta.com/features/explaining-ranking/fb-search/]**,
and its only *published* statement about caption text is negative: *"long, distracting captions,
often with an inordinate amount of hashtags"* and captions *"completely unrelated to the content"*
are named demotion triggers **[PRIMARY · about.fb.com/news/2025/04/cracking-down-spammy-content-facebook/
· 2025-04-24]**. So on Facebook, hashtag-stuffing is a documented *risk*, not a documented *lever*.

**3. Facebook's watermark rule is not documented — Instagram's is.** No reachable Meta page states a
Facebook watermark rule; the March 2026 originality announcement does not use the word
**[UNVERIFIED for Facebook]**. Keep "no third-party watermarks" as a house rule justified by
Instagram's and YouTube's own text, and do not attribute it to Facebook.

**What Facebook does document, and it lands squarely on a batch pipeline** — see §4c.

---

## 4c. ⛔ "Mass production" is now a named violation on two of the four platforms

This is the most consequential thing in this file for high-volume AI-UGC, and it is not a compliance
question or a taste question — it is a **distribution-eligibility** question, in the platforms' own
words.

> **Meta, March 2026:** *"Content that is **duplicative or involves minor edits to another creator's
> post** will be considered unoriginal and deprioritized."* Unoriginal includes *"Simply watching
> along, reacting with facial expressions, stitching multiple clips together, or narrating what's
> already on screen — without adding anything meaningful"*, and the named low-value edits are
> **"adding borders, inserting captions, and changing the reel's speed."** Consequence: deprioritised
> in Feed and Reels; repeat offenders *"may see their account deemed non-recommendable and
> demonetized."*
> **[PRIMARY · about.fb.com/news/2026/03/rewarding-original-creators-on-facebook/ · 2026-09-08]**

> **YouTube**, in the policy renamed from "repetitious content" to **inauthentic content** on
> **2025-07-15**, names *"AI-generated content made with generic or unoriginal templates giving the
> impression of mass production"* and *"videos where characters are put in the same situation over
> and over again with the same outcome."*
> **[PRIMARY · support.google.com/youtube/answer/1311392 · 2026-09-08]**

⚠ **Read the scope of each before using it.** These two are not the same rule and an earlier draft
of this file blurred them:

- **YouTube's applies to us directly.** "Generic or unoriginal templates giving the impression of
  mass production" and "characters put in the same situation over and over again with the same
  outcome" describe **original AI content made at volume** — which is exactly what Mode B is. There
  is no reuse element and no escape by making the footage ourselves.
- **Meta's is narrower than it first reads.** The enumerated low-value edits — borders, captions,
  speed — sit inside a sentence about *"minor edits to **another creator's post**"*: they are about
  what fails to launder someone else's content, not a list of edits that are worthless on your own
  footage. What reaches our case from Meta is the other word: **"duplicative."** Near-identical
  variants of our own master, posted into the same surface, are duplicative; a batch of genuinely
  different videos is not, however it was edited.

So the honest statement is: **YouTube's policy names a template batch; Meta's names near-identical
posting.** Both point the same way, and neither is a reason to stop varying captions or speed — the
reason to vary something *else as well* is that on YouTube the template itself is the exposure.

⛔ **This is what the batch-variance rule is actually for.** `realism-qa.md` §5 and the pairwise
lockstep check in `batch_plan.py` were built as a *slop* control — a batch that shares a template
reads as AI. They are now also the control that keeps the account recommendable. Two consequences:

- **Variety has to be substantive, not only cosmetic.** Cosmetic variation is not forbidden and is
  not useless — it is just not *sufficient*, on YouTube by policy and at high involvement by
  measurement. Different argument, different setting, different presenter is what carries the
  variance; different caption and different speed ride along on top. This is the same distinction
  `comedy-craft.md` §6 reaches from the advertising-variation literature — two independent routes to
  one rule.
- **Cross-*platform* posting is fine; the same file twice inside one platform is not.** Nothing in
  either policy penalises a brand for posting its own video natively to four platforms. Both
  penalise duplicative content *within* a surface. Post the clean master natively four times; never
  export from one app and upload that file to another (see the watermark gate in §4).

---

## 5. What this changes about how we write

1. **Write the caption from the script, not after it.** The caption is the index; the VO is not. One
   sentence that names the product problem in the audience's own words, at the front. Everything
   else — the joke, the CTA, the emoji — after it.
2. ⛔ **Get the search terms before the hooks, not after the batch.** Search Console platform
   properties (§3) and the platform search bars are demand data. `hook-craft.md` §8 step 6 asks for five
   hooks across the concreteness curve; one of them should be *the phrase people actually type*,
   which is usually more concrete than anything a copywriter would choose.
3. **The `keyword` sentence is a real constraint on hook craft, and they pull in opposite
   directions.** A searchable opening line names the thing plainly. A high-performing feed hook
   often withholds. This is not a contradiction to resolve in one video — it is a reason the hook
   bank should contain **at least one plain-named hook per batch**, and the ad-name join key
   (`performance-metrics.md` §2) is what tells you which arrival path paid.
4. **Never ship an overlay treatment without checking it against the two format rules in §4.** They
   are the cheapest ⛔ in this file to satisfy and the most expensive to discover after upload.
5. **Watermark and originality checks belong on the export gate**, not in a person's head — see the
   verification block below.

---

## 6. Verification — what closes this file out

- [ ] Caption drafted **from the script**, leading with the plain-language problem phrase, ≤5 hashtags for Instagram
- [ ] Search terms sourced (Search Console platform property, or platform search bar) **before** the hook bank was written; at least one hook uses the plain named phrase
- [ ] No visible watermark anywhere in frame — checked on the export, not the source
- [ ] The file posted to each platform is a **per-platform recut**, not the identical file twice inside one platform
- [ ] On-screen text: does not cover the majority of the frame · paced at ≤10 words/second · inside the UI safe zone
- [ ] ≤3 minutes, 9:16, no letterbox bars, ≥720p (this skill's floor is 1080p — `delivery-format.md`)
- [ ] Claims read once more against `compliance.md` **as a discovery risk**, not only a legal one (§4)

---

## 7. Blacklist — repeated everywhere, unsupported

1. **"40% of Gen Z use TikTok instead of Google for search."** A misquotation. What was said, at
   Fortune Brainstorm Tech on 2022-07-12 by Prabhakar Raghavan (then SVP, Google Knowledge &
   Information), was: *"In our studies, something like almost 40% of young people, when they're
   looking for **a place for lunch**, they don't go to Google Maps or Search. They go to TikTok **or**
   Instagram."* **[SECONDARY · TechCrunch, Sarah Perez, 2022-07-12 · 2026-09-07]** Google confirmed to
   TechCrunch it came from an internal survey of US users aged 18–24 and that "**the data has not yet
   been made public**." Four years later it still has not been. Five distortions ride on it: the hedge
   is dropped, *lunch* becomes *search*, *TikTok or Instagram* becomes *TikTok*, *US 18–24* becomes
   *Gen Z globally*, and an unpublished internal survey becomes a statistic. **Never use it, in the
   skill or in a client deck.**
2. **"TikTok's Research API proves TikTok OCRs your on-screen text."** It does not. The nearest
   field is `sticker_info_list`, documented as "returns the **interactive sticker** details" —
   polls and Q&A widgets, not burned-in type. There is no OCR field.
3. **"`voice_to_text` proves TikTok search ranks on your transcript."** The field exists, is
   conditional on the creator having enabled captions, is **not queryable**, and speech appears
   nowhere in TikTok's Search model card. Extraction ≠ ranking (§1).
4. **"TikTok tells you to put keywords in your on-screen text."** The real quote — *"Text hook:
   Keywords shown as on-screen text or in overlays"* — is genuine
   **[PRIMARY · ads.tiktok.com/help/article/search-ads-creative, "Last Updated: January 2026" ·
   2026-09-07]**, and sits under the heading **"Tips for Carousel Image Ads"**, introduced by "Ensure
   the carousel image content directly matches the account's search query or your bidding keyword."
   It is paid-carousel guidance. Quote it with its context or not at all.
5. **"Alt text boosts Instagram SEO."** No Instagram documentation says so; alt text is documented
   as an accessibility feature, and for photos.
6. **"Rename the file with your keyword before uploading."** Zero documentation on any platform.
7. **"YouTube tags matter."** YouTube: "tags play a minimal role in your video's discovery."
8. **"More hashtags, more reach"** (Instagram). Capped at five; Instagram's own framing is that
   fewer and more targeted performs better. Hashtags remain documented **for Search**, which is a
   different claim from reach — keep the two apart.
9. **"Optimising for search costs you watch time."** **No evidence either way** — I looked for it
   specifically and there is no published test. Do not assert the tradeoff. The real, documented
   constraint is screen coverage and text pacing (§4).
10. **TikTok's own creative statistics** — "+58% uplift in recall" from captions, "+2.1x awareness
    lift" at 5–10 words/second, "2 in 3 discoveries on TikTok were made via search" — are
    **unpublished proprietary vendor studies**, run for a party with a commercial interest in the
    number, and they measure **ads**. Directional advertiser guidance, never evidence. The pacing
    number is worth following anyway because it is also the platform's own stated preference.

---

## 8. What this file cannot tell you

- **Whether any of it ranks your video.** Every statement above is a platform describing its own
  system in marketing prose. None of it is a measurement, none is falsifiable from outside, and all
  of it can change without notice. `performance-metrics.md` §0 applies here in full: the ceiling on
  predicting a video's fate is low, and this file does not raise it.
- **How much traffic search actually sends.** There is **no public panel measurement of in-app search
  query volume** on TikTok or Instagram. Every circulating figure is an unpublished platform survey,
  a commercial panel (Adobe Express 2026: n=807 SurveyMonkey respondents, 53% millennial, run by a
  company selling video tools), or a platform's own marketing science. The defensible sentence for a
  client is: *all three platforms now build product and ad surfaces around in-app search, and Google
  now gives you a Search Console property for it — that product investment is better evidence than
  any of the percentages.*
- **Instagram's current Search system card.** `transparency.meta.com/features/explaining-ranking/ig-search/`
  is client-rendered and could not be retrieved. It is likely the freshest primary source on
  Instagram search and is a known gap — check it in a browser before a client conversation.
- **Anything about ranking on the audio track.** If a platform starts ranking on transcripts, §1
  inverts and the VO becomes the index. Watch for it; do not assume it.

---

**Cross-references:** `hook-craft.md` §2 and §8 (the plain-named hook this file adds to the bank) ·
`typography-and-captions.md` (the overlay craft §4 constrains) · `modes/repurpose.md` (per-platform
recuts, which are also the originality escape) · `delivery-format.md` (the format floor) ·
`compliance.md` §4 (health claims are a discovery gate too) · `performance-metrics.md` §0 and §2
(the prediction ceiling; the join key that says which arrival path paid) · `research-quality.md` §1
(platform docs are the fastest-decaying tier here).
