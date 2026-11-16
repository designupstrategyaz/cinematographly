# The sound-off story test — does the video tell its story with no sound and no voiceover?

Clients accept a video this way: they mute it and watch whether the story still comes across. The owner,
2026-10-27: *"One of the main ways for clients to check is if the video tells a story without sound and
voiceover."* Until v2.41 the skill had this check only as prose checklists in two lanes. This file is now the
one definition every lane links to. `scripts/soundoff.py` runs the check, `qa_log.py --gate soundoff` records it,
and `gate.py approve export` will not pass without it. The research and the council are in
lab record lab-00019 (not shipped); the decisions are in the sound-off story proposal of 2026-10-27 [studio history].

## 1. Two tests, not one

| | **T1 — the muted feed** | **T2 — the picture alone** |
|---|---|---|
| What is on screen | Everything as shipped: captions, titles, the end card, the disclosure | The picture and the titles the title card permits, nothing else. **No caption of the voiceover**: a caption of the VO *is* the VO, read instead of heard |
| Sound | Off | Off |
| Source | Each delivery file in `10-export/` | Resolve's picture-only render (`render-mp4.py PICTURE_ONLY = True` — captions made in Resolve, routes 1–2, the default), or the captionless master (`<slug>-v<N>-master.mp4`) where a reason sent the burn outside (route 3) |
| The question | Can a scroller with the phone on silent follow it, read every claim and price, and find the offer? | Do the faces, the action and the objects tell the story — who, what happens, why it matters, what to do next? |
| Who watches | The producer may pass it | Someone who has **not read the script or the brief**, open question first (§3) |
| Weight | Follows the placement (§4) | The client's acceptance test: it runs whatever the media plan says |

**T3, the mirror test — eyes closed, does the sound alone carry it?** That is the accessibility test (audio
description, WCAG 2.x SC 1.2.5). It is out of scope here, named so nobody confuses it with T2.

⛔ **The limit, from Hullfish's editors** (`editing-storytelling.md` §6): a silent pass judges a different film
from the one shipping, because sound hides and sells cuts. So T1 and T2 judge **whether the story reads**, never
whether the cut is good. The master gate (`qa_log.py --gate master`: sound on, one thing heard and one thing
seen) is unchanged and still required. A sound-off PASS never stands in for it.

## 2. Why the check is worth enforcing

- **Clients run it.** It is the cheapest check a client can make, and they make it.
- **Muted viewing is common in feed placements, rare in others.** 79 % of LinkedIn feed video is watched with
  the sound off [PRIMARY · LinkedIn Video Ads Playbook, NAMER 2022]. Facebook found 41 % of feed video ads
  meaningless without sound and captions raising view time 12 % [PRIMARY as reported · Social Media Today
  2016-02-13]. Meta reports 80 % of Reels watched with sound on [PRIMARY · Meta, Aug 2022]; 88 % of TikTok users
  call sound essential [VENDOR · TikTok × Kantar 2021]. Both "69 % in public" and "85 % of Facebook video" were
  looked for and **not** confirmed in a primary (2026-10-27).
- **Captions take the eyes off the picture.** Viewers spend about 40–60 % of a subtitle's time on screen reading
  it [PEER-REVIEWED · Szarkowska & Gerber-Morón 2018, *PLoS ONE*, eye tracking, n = 74]. A story that reads only
  in the captions is the voiceover in another channel. That is why T2 removes them.

## 3. The order of the read — producer, cold viewer, client

The order comes from copy testing: **the open question before the closed ones**, so the closed questions cannot
leak the answer [PEER-REVIEWED review · Pechmann & Andrews 2010, FTC copy-test methods].

1. **Make the proofs** — `soundoff.py proofs <job>`. Before lock, a T2 proof of the cut: `--cut <file>`. The
   audio is stripped by stream copy, so the proof's picture is the render's picture. Each proof records its own
   hash and the hash of its source, so a re-render makes the proof stale, and every verdict logged on it too.
2. **The producer reads the story map** — `soundoff.py map init <job>`, then `map set` each beat from the muted
   proof: what the **picture** shows in that window, and Y / partial / N. A cell that only restates the voiceover
   is refused. An N needs a fix (a shot, an insert, a title the card permits, a re-cut) or the owner's waiver.
3. **The cold viewer watches T2 once and retells it** — in their own words, before seeing anything else:
   `qa_log.py --gate soundoff --test T2 --viewer cold --who "<name>" --proof <T2 proof> --retell "<their words>"`.
   At least 15 words [assumed]. A retell that is mostly the script word for word is refused.
4. **Then the closed questions** — show the viewer strip (numbers only, `soundoff.py strip`), ask beat by beat,
   and log the PASS or RETAKE with the beats the picture carried:
   `--verdict PASS --beats "HOOK@0:02,S2@0:11,CTA@0:24" --obs "<what they got, and from what>"`.
5. **T1 on every delivery file** — the producer watches each muted proof as shipped and logs it the same way
   (`--test T1`).
6. **The client** gets the pack (§6) and runs the test themselves, unprimed.

**Who is a cold viewer.** Anyone who has not read the script, the brief or the shot list, and has not seen the
cut with sound. A partner who read the script is not cold. The same person may re-check a later render: their
first look was cold, and that retell stands. With nobody available, the fallback is the owner's call:
`soundoff.py waive <job> --what cold-viewer --reason "…" --quote "<their words>"`, printed at every export.

**What a PASS must cite** (house rule K5): at least three different beats [assumed], each with an m:ss inside
that beat's window on this cut, **the offer beat among them** (CTA, or OFFER in the narrow map). A film with
fewer beats cites every beat and two distinct timecodes. A row about a file that is not a proof, a T1 proof
logged as T2, or a proof whose source changed is refused.

## 4. The rules at each gate

- **`approve lock` — advisory** (ruling K1): notes for anything unread, because a story fix is cheapest now.
  **One exception:** a beat the map marks N, unfixed and unwaived, refuses the lock.
- **`approve export` — blocking:**
  - T2 has a current proof, a PASS by a cold viewer (or the owner's cold-viewer waiver), and a story map that is
    current with the cut, every beat read, no N left;
  - T1 has a current proof and a logged verdict on **every** delivery file. A PASS is required unless the job
    records a sound-on-only media plan in the owner's words (`soundoff.py placement <job> --sound-on-only
    --platforms "TikTok, Reels" --quote "…"`); then a RETAKE is a note. An unknown placement counts as muted
    (ruling K2);
  - the captions are measured (§5);
  - every number and price the voiceover says is on screen for T1 (in a caption or a title); a number carried
    only by the captions is a note for T2.

## 5. What the machines check, and what they cannot

| Check | Tool | Refuses | Notes only |
|---|---|---|---|
| Caption timing | `srt_qa.py check 08-captions/<slug>.srt` | a file that does not parse, a cue that ends before it starts, overlapping cues, an empty cue, a pop chunk (1–3 words) under 0.5 s (§3b, §9 of `typography-and-captions.md`) | over 20 characters a second, over 2 lines, a line over 42 characters (Netflix English, adult); a line caption under 0.3 s a word (BBC). Long-form norms, **[assumed] for social**: each must be signed off, `srt_qa.py accept <srt> --by <who> --reason "…"` (ruling K8) |
| Numbers on screen | `soundoff.py claims <job>` | with T1 strict: a number or price only heard | a number only in the captions (a T2 gap); the offer with no end card; an end card under 2 s [assumed]; numbers written as words are not checked |
| Titles | `title_qa.py` (unchanged) | safe box, dwell, contrast, the phone proof | — |
| Brand early | nobody | — | in-world branding cannot be seen without vision; it stays a human check (§7) |

None of them judges the story. They make the read happen on the right bytes, in the right order, and keep the
record.

## 6. The hand-over (ruling K7)

`soundoff.py pack <job>` writes `09-qa/soundoff/PACK/`: **the proofs first** — `1-picture-only` (T2), then each
`muted-` file (T1) — a README that says *play these at volume 0, before you read anything*, and an appendix
(`09-qa/soundoff/PACK/APPENDIX.md`) to read after watching: the story map, the cold viewer's words, what was
changed. A manifest (`09-qa/soundoff/PACK/MANIFEST.json`) carries every file's hash. Upload it beside the final in the review platform's version stack
(`review-and-approval.md` §4–§4b). The client runs their own test unprimed and can still see the evidence.

## 7. Lane rules (ruling K4)

| Lane | T2 | Watch for |
|---|---|---|
| **DR advertorial** (`dr-advertorial.md` §8) | full | The mute test there is T1; every claim, number and price as text; the offer on screen 2–3 s |
| **UGC, talking head** (`modes/ugc-volume.md`) | **narrow** when the story *is* the speech: `map init --narrow --why "…"` — the picture alone must show WHO, the PRODUCT, the PROOF and the OFFER | Captions carry the speech in T1; the four rows carry T2 |
| **Narrative promo, brand** (`modes/narrative-promo.md`) | full — the core craft test | Faces, gesture and objects carry the turn (Campbell & Pearson below); a cold retell of the emotional arc |
| **Editorial explainer** (`modes/editorial-explainer.md`) | full | The designed text carries the numbers; faceless B-roll must show each beat |
| **Micro-drama** (`micro-drama.md` §9) | full, per episode | The cliffhanger reads from the picture; dialogue captions are off in T2 |
| **Golf and property flyovers** (`aerial-and-fpv.md`) | full, usually easy | The place, the sequence, the contact or offer card |
| **Repurpose** (`modes/repurpose.md`) | the master's T2 holds; **T1 per derivative**, since a re-crop moves the captions and the safe zones | |
| **Sound-led** (a music video, an ASMR piece) | may be waived: `soundoff.py waive <job> --what T2 --sound-led --reason "…" --quote "…"` | A sound-on media plan never waives T2; it only makes T1 advisory |

**What makes the picture carry it** [PEER-REVIEWED · Campbell & Pearson 2019, *Journal of Advertising Research*
59(1) 85–98; method: published ads, an agency dataset, practitioner interviews; no effect sizes]:

1. tell it by gesture, face and object, which favours simpler plots;
2. lean on shared shorthand that loads a story at once;
3. raise the visual energy: shorter, more varied shots and more motion, because silence flattens;
4. if text carries it, keep it brief, styled and placed to steer the eye.

Practitioners agree: Murch cuts each scene with the sound off before he turns it on [PRACTITIONER · No Film
School 2016]; Soderbergh's silent, black-and-white *Raiders* is a study of staging [PRACTITIONER · 2014]. The
selects pass already watches each scene as a silent sequence (`direction.md`); this test is the same question
asked of the locked film.

## 8. In Resolve

- **The picture-only render:** `render-mp4.py` with `PICTURE_ONLY = True` duplicates the timeline ("<timeline> —
  PICTURE ONLY") and disables every subtitle track and every video track whose name starts with one of
  `CAPTION_TRACKS`. It renders with no audio and leaves the editor on the cut. Point `OUTPUT_FOLDER` at
  `09-qa/soundoff`. Check Deliver ▸ Subtitles is off; the script cannot read that setting.
- **The map on the timeline:** `soundoff.py console <job>` writes `07-edit/resolve-production-console.soundoff.py`,
  one duration marker per beat (Green Y · Yellow partial · Red N · Cream waived · Blue unread), the note carrying
  what the picture shows and the fix. Nothing else changes.

## 9. What this file does not know

- **Whether three beats is the right minimum, and 15 words the right retell.** Both are [assumed]; calibrate on
  the first real jobs.
- **How often a solo producer can find a cold viewer**, and how long the read takes in a 4–5 hour day. The jury
  guessed about 15 minutes [assumed]; nobody has measured it.
- **Whether the client's own sound-off result should be recorded.** The pack leaves room; no field exists yet.
- **Burnt-in caption contrast and safe box.** Only titles are measured; captions are still checked on the output
  frame by eye (`typography-and-captions.md` §9).
- **A model as the cold viewer — not built, by decision.** Models trail people by 15–20 points on ad
  understanding, weakest on what happened in what order [PEER-REVIEWED · AdsQA, ICCV 2025: humans 51.3 vs best
  model 35.9 strict; preprint · VideoAds 2025: 94.3 % vs 73.4 %]. If it is ever built: opt-in, a paid call the
  owner approves, advisory only, and never a PASS.
