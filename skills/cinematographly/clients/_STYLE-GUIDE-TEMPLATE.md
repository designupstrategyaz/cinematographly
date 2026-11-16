# Style guide — <BRAND>

**How to use this file.**

1. Copy it to `clients/style.<brand>.md` and point `clients/<brand>.md` §6 at it.
2. Fill it with the client, in their words, and record each decision's source: a quote, a brand book page,
   or "default, accepted on <date>".
3. Every **Default** below is a recommendation with its evidence pointer. The client may override it; nothing
   here overrides a hard lock in the profile's §0.

**What filling it changes.** The house default is captions-only: no supers, no cards, no logo
(`references/editing-and-audio.md`, the captions section). A section filled here is the profile "explicitly
asking" for that element, and nothing else is switched on.

**Values live once.** Hexes, faces and sizes go in the profile's tokens (`references/brand-system.md` §2).
This file names the token; it does not restate the value.

Status: `draft` / `approved by <name> on <date>: "<verbatim quote>"`

---

## 1. Formats and structure

| Decision | This client | Default and evidence |
|---|---|---|
| Formats bought (social clip · feature launch · teaser · demo · explainer · customer story · DR body) | | Beat maps per format: `references/product-video.md` §1; DR: `references/dr-advertorial.md` §4 |
| Length per format | | Social 15–34 s; feature 20–45 s; demo 60–120 s (`product-video.md` §1) |
| Aspect ratios and the master | | 9:16 master, re-laid out (not cropped) for 1:1 and 16:9 (`references/delivery-format.md`) |
| Hook window | | The proposition in the first 3 s (TikTok); brand within 5 s (ABCD) |
| Variants per concept (hooks, lengths) | | `modes/ugc-volume.md` §2b for long bodies with swappable hooks |

## 2. Opening card

| Decision | This client | Default and evidence |
|---|---|---|
| Opening card: none / logo sting / title card | | **None.** The brand arrives in the product or from a person saying it (ABCD: a person saying the brand beats voiceover) |
| If yes: duration, content, motion | | 1 s at most, with the product already mid-task (`product-video.md` §6) |
| Brand-early rule (logo or name inside 5 s, and how) | | Integrated: product UI or packaging in frame, or the name said aloud |
| Sound on the open | | No sting unless the brand owns one (a sonic logo is a token) |

## 3. On-screen text system

| Decision | This client | Default and evidence |
|---|---|---|
| Captions: regime (line or pop), face, size, placement | | `references/typography-and-captions.md` §3b, §5, §8. The caption type block lives in the profile §6 |
| Supers (product name, promise, offer, CTA): yes or no; maximum words per super | | 3–5 supers a video, 16 must-read words in a 15 s film at most (`product-video.md` §3) |
| Super face, weight, size, colour tokens | | A line is 3.9–4.5 % of frame height on 9:16, 7–8 % on 16:9 (BBC). 4.5:1 contrast over the moving picture (WCAG) |
| Contrast treatment: plate, shadow or dimmed background | | Dim the background first; a plate if the brand book requires one |
| Safe area per platform | | `dr-advertorial.md` §3 (the box safe everywhere) and `typography-and-captions.md` §5b |
| Holds | | At least 0.3 s a word and the reading floor; must-read lines 0.8 s or more |
| Numbers, prices and claims on screen | | Every number with its baseline and period; claims through `compliance.md` and `claims_lint.py` |
| Disclosures (AI, ad, dramatization) | | Always burnt in when required (`compliance.md` §2b, §5) |

## 4. Product footage treatment

| Decision | This client | Default and evidence |
|---|---|---|
| Source of UI footage | | **Real captures only**: the product's UI is never generated (`product-video.md` §0) |
| Capture spec: resolution, browser zoom, OS chrome | | 4K or 2× Retina, 125 % zoom, no bookmarks bar or OS toolbars (`product-video.md` §2.1) |
| Demo account and data | | Fictional names, numbers and avatars, staged before recording; real data never shown |
| Frame: none / browser / device (which device) | | Full bleed for detail, a frame for context; on 9:16 crop and punch in, never a full-width desktop |
| Cursor: size, style, smoothing, click effect, click sound | | Enlarged and smoothed; squash and ripple on the click frame (`product-video.md` §2.3) |
| Zoom: auto-zoom on clicks, scale range, minimum duration | | 1.5–2×, the lowest that reads; each zoom 1 s or more (`product-video.md` §2.4) |
| Screen-to-screen transitions | | Carry, morph or cut at peak speed, never a crossfade (ads); dissolves allowed only for App Store previews |
| Device or app mock-ups in generated shots | | Real captures composited onto the screen (`references/real-and-ai.md`) |

## 5. Voiceover or on-screen text

| Decision | This client | Default and evidence |
|---|---|---|
| VO: yes, no, or per format | | Yes. The VO carries the argument, captions carry the VO, supers carry the 3–5 must-reads (`product-video.md` §4) |
| Voice source: human talent / ElevenLabs stock voice / a cloned client voice (rights on file) | | Clone only with rights (`compliance.md` §5) |
| **The standard ElevenLabs voice** | | One voice per brand, locked per series |
| ├ voice name and voice ID | | |
| ├ model | | Multilingual v2 for stability and numbers; v3 or v4 for expression |
| ├ stability / similarity / style / speaker boost / speed | | About 50 / 75 / 0 / off unless it helps / 1.0 (ElevenLabs docs) |
| ├ pronunciation dictionary (product names, acronyms) | | Required whenever the product has a coined name |
| └ reference read (file) | | A 10-second read at the locked settings, for drift checks |
| Read style: pace (wpm), register, energy | | 130–150 wpm as a ceiling for explainers; UGC reads per `dr-advertorial.md` §6 |
| When text replaces VO entirely (silent formats) | | Teasers of 6–15 s that must work muted |

## 6. Sound

| Decision | This client | Default and evidence |
|---|---|---|
| Music: who chooses the track, licence source | | **The client chooses, every time**; never an autonomous pick (`editing-and-audio.md`, the music bed section) |
| Music under speech | | **At least 10 LU below the speech, aim about 14 LU**, measured on the mix (Torcoli et al., JAES 2019); token `music.duck` |
| Ambience and room tone | | At least 15 LU below the speech |
| UI sound effects: palette (click, typing, whoosh, success chime), licence | | One sound per kind of event, on the frame (`product-video.md` §5; `dr-advertorial.md` §5) |
| Sonic logo | | Only if the brand has one |
| Loudness target and true peak | | From the delivery preset, not a habit (`delivery-format.md`) |
| Deliverables: full mix, M&E, no-sound master, stems | | M&E whenever language versions or a client mix are possible (`editing-and-audio.md`, the audio delivery layer) |

## 7. Motion language

| Decision | This client | Default and evidence |
|---|---|---|
| Camera over UI: which moves, how many per scene | | One motivated move per scene; zooms in log space; no two zoom-ins in a row (`product-video.md` §2.4) |
| In-scene easing and durations | | Soft: entrances 0.45–0.7 s, overshoot 2–4 % at most |
| Cut transitions | | Strong curves only at a cut, with the cut on the peak of the move; zoom direction never flips across a cut |
| Text motion | | The supers system (`typography-and-captions.md` §6b) |
| Banned effects | | Shockwaves, particles, RGB split, camera shake, flares, neon glows, bouncy easing, opacity-only transitions (`product-video.md` §2.5) |
| Motion sensitivity | | Moderate zoom factors; no spins or flashing (`product-video.md` §2.4) |
| Live-action and generated shots: the camera plan | | `references/sequence-grammar.md` §2b; blocked shots per `references/blocking.md` |

## 8. End card

| Decision | This client | Default and evidence |
|---|---|---|
| End card: yes or no, per format | | No (house default); DR formats usually yes (`dr-advertorial.md` §2) |
| Layout: wordmark, tagline (1–2 lines), one CTA, URL or store badge | | `product-video.md` §6, built once as a template |
| CTA wording per platform | | One action, written like the real button; never "swipe up" on TikTok |
| VO on the card | | The VO says the CTA the card shows (ABCD) |
| Hold | | About 4 s, never under its reading time (`sequence-grammar.md` §2c, item 11) |
| Required text on the card (offer terms, disclaimers) | | `compliance.md` |
| Motion in and out | | The supers system; the card holds still and ends clean |

---

**Open questions for the client** (tick when answered, with the date and the quote):

- [ ] Which formats, lengths and ratios are in scope this quarter?
- [ ] Opening card: none, or which?
- [ ] Supers: yes or no; the brand faces and colours (tokens)
- [ ] The demo account: who stages it, and which data may appear?
- [ ] The standard voice: which ElevenLabs voice, or human talent? Rights on file?
- [ ] Music: who picks, from which library?
- [ ] End card: yes or no; the CTA per platform
- [ ] Who approves: the style guide, then each video (`references/review-and-approval.md`)
