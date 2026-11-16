# DR advertorial — the devices, the long-body pace, the sound, the voice and the AI routing

Loaded by the long-body DR sub-mode (`modes/ugc-volume.md` §2b): one locked body of a minute or more,
several hooks, and direct-response devices on screen. Two kinds of evidence sit under this file, and each
line says which:

- **[measured · lab-00009]** — 13 DR ads read shot by shot on 2026-10-21 with the lab-00006 pipeline: one
  agency's 10 portfolio ads (4:5, 38–60 s) and 3 of its brief examples (9:16, 51–140 s). One agency is one
  house style, so a count here says what that agency does, not what the market does.
- **Researched** — lab-00009 R2 (editing), R3 (AI generation) and R4 (hooks and samples), checked
  2026-10-21, each source tagged by tier. Practitioner advice is labelled opinion.

## 1. The overlay lock comes first

Captions are the only on-screen text by default (`editing-and-audio.md`, the captions section). Every
device in §2 renders **only when the project's approved title card names it** (house rule C3,
2026-10-26: *"Yes, the card is the permission"*; `typography-and-captions.md` §6c), and the card is
proposed from what the client profile allows. A DR brief usually allows a lot (banner, labels, cards, an end
card); the ads lane's card carries a hero line, a stat, a price card and an end card, and anything else in
§2 is added to the card by name before it is built. A required disclosure rides on top regardless
(`compliance.md` §2).

## 2. The devices — what the 13 ads used, and how to build each

| Device | Ads (of 13) | Where in 1080 × 1920 | When | Sound cue |
|---|---|---|---|---|
| Emoji as a graphic element | 6 | inside the card it marks | with the card | none |
| Logo card | 6 | centre | the close | none |
| Headline box (the hook line as text) | 5 | upper band, y 285–840 | the hook; in some ads the whole runtime | none |
| End card with a button | 5 | button above y 1248, clear of the rail | the last 2–7 s | riser into it |
| Split screen | 5 | full frame | a comparison | whoosh on entry |
| Offer banner | 4 (2 for the whole ad) | top strip, about y 290–390 | see below | tick on a pulse |
| Price card | 4 | upper band | the offer | tick |
| 3D anatomy | 4 | full frame | the mechanism | low hit or throb |
| Red "pain" glow on the anatomy | 4 | on the organ | the agitation | low hit or throb |
| Arrow or circle callout | 3 | on the object | a detail the VO names | tick |
| Numbered list label ("#2", "SIGN 2/5") | 3 | upper band | each chapter opens | tick |
| Phone-screen UI (a text, a notification) | 3 | full frame | a story beat | notification sound |
| Review card | 2 | upper band | the proof chapter | tick |
| Checkmark card | 1 | upper band | ingredient or benefit lists | one ding per check |
| Cartoon expert | 1 | full frame | the mechanism | none |

[measured · lab-00009 · 2026-10-21]. End cards ran 1.7–7.4 s (median 3.2 s) on the 10 ads that had one.

**The offer banner has two placements, and the evidence splits.** Two of the agency's own ads run it for
the whole ad. A practitioner source keeps it out of the hook and puts it in the last 15–20 s, because it
signals "ad" before the hook has earned attention [VENDOR (opinion) · lab-00009 R4 B3 · 2026-10-21].
Follow the client's brief; with several hooks, the banner is in every hook or in none (`modes/ugc-volume.md`
§2b).

**Real proof only.** A review card shows a real, current review; a star rating or review count shows the
real aggregate with its source; an expert is a real, credentialed person. `compliance.md` §4 has the rows.

**Build each device once, as a template.** In Resolve: one Text+ or Fusion title per device, saved in the
brand's bin with its safe-box position and its caption tokens (font, fill, stroke, accent colour) baked in,
so all the hooks of a batch share one graphics system. Their motion follows `typography-and-captions.md`
§6b (one curve family, one duration tier). `assets/supers-gsap/` can render the same motion outside Resolve, only
with a recorded reason (house rule C7, 2026-10-27).
These templates are not built yet: making and testing them needs a Resolve session.

## 3. Placement — one box that is safe everywhere

| Zone | x | y (of 1920) | Use |
|---|---|---|---|
| Upper band | 120–960 | 285–840 | the hook headline, the offer banner (about 290–390), list labels, checkmark and proof cards |
| Lower band (TikTok rail notch) | 120–780 | 840–1248 | pop captions, the end-card button |
| If a Meta Reels disclaimer may be added | 120–780 | bottom edge at most 1152 | everything that must be read |
| Faces | 120–960 | 285–1248, eyes around 500–800 | the presenter |

[derived · the evidenced 9:16 box in `delivery-format.md` §3 (top 15 % / bottom 35 % / left 11 % / right
28 % at the action rail, measured from TikTok's and Google's own template files) scaled to 1080 × 1920,
and the centred 4:5 crop, lab-00009 R2 §2 · 2026-10-21]. ⛔ Corrected 2026-10-25: this note first cited
"Meta's 14 / 35 / 6", a blog figure with no Meta source that `delivery-format.md` §3 refuses. The box
did not change: its bottom edge is still y = 1248. `typography-and-captions.md` §5b has the reasoning and the caption
position. Re-check the TikTok preview with the final ad caption: a longer caption shrinks the safe area.

## 4. Pacing a body of one to four minutes

- **One insert per VO line or clause, 1–2 s.** In the median portfolio ad, 75.5 % of shots last 2 s or
  less; in the three brief examples, 52–65 % [measured · lab-00009]. A brief may make 2 s a hard cap.
- **Literal or metaphor.** Literal when the line names something you can see (food, the product, an
  action, a visible symptom). A metaphor (a drain, a factory, 3D anatomy) only when the line names an
  invisible process, and the VO names what the metaphor stands for in the same sentence [SECONDARY · lab-00009
  R2 §5, from the audio-visual relatedness studies cited there · checked 2026-10-21].
- **Hold the shots that carry the claim longer.** Pain and mechanism visuals 1.5–2.0 s; low-information
  colour inserts about 1 s [opinion · lab-00009 R2 §5].
- **Come back to the presenter.** After every 2–3 inserts, 2–4 s of the talking head or the a-roll
  [opinion · lab-00009 R2 §5]. The agency's portfolio mostly ran VO over a montage (7 of 10 ads had no
  talking head); its longer brief examples kept a face on screen for 32–96 % of the runtime [measured ·
  lab-00009].
- **A macro interrupt every 20–40 s**: a list label, a checkmark card, a review card, or a banner pulse
  with a tick [opinion · lab-00009 R2 §5]. In chapter form, 5–6 chapters of 25–40 s for a 3-minute body,
  each opening on a label or a re-hook and closing on a question the next one answers [VENDOR (opinion) ·
  lab-00009 R4 B1].
- **Insert volume.** A 3-minute body at about 2.7 words a second is about 490 words, so 70–90 unique
  inserts [derived · lab-00009 R2 §5]. With no repeats allowed, cut at most two non-overlapping segments of
  clearly different framing from one generation; otherwise generate separately.
- **The insert lane** (house decision 2026-10-25, the direct-response trial proposal's P7). Seventy inserts are not
  seventy approvals. Group them into **families**, one prompt with `{{slot}}` holes per family
  ("hands with the bottle", "the kitchen at dawn"):
  - `01-script/prompts/<family>.family.md` declares the shared prompt, `slots:` (the only words that
    vary), `cut_max:` and a `members:` list, each with its `shot:`, its `start_frame:` and its slot
    values;
  - `prompt_lint.py <family>.family.md` lints it once and writes one ordinary linted
    `<SHOT>.clip.prompt.md` per member, so every call still matches its own prompt;
  - `gate.py approve family:<family> --artifact <contact sheet> --media-ids S12a=<id>,S12b=<id>`
    signs every member's start frame from one look at one sheet. It writes a `frame:<SHOT>` row per
    member with that member's own still and media id, so each clip still binds its own approved
    picture and every later check runs unchanged.

  The caps are mechanical:
  - at most **12 members** per family;
  - at most **2.5 s** of each member used in the cut;
  - `type:` insert or broll only;
  - never a line, a character reference or a shot that carries proof of a claim;
  - a family edited after its members were written fails every member until it is linted again.

  Spend still needs the open job and its preflight. One wrong template multiplies into twelve wrong
  shots, which is why the sheet is looked at before anything moves.
  An insert of hands at work is about the person, not the product or the material: its `[MOTION]`
  opens with `INTENT:` (why she does it, and the manner that forces) and the sugar, the capsules or the
  water are the consequence of her force (`motion-craft.md` §6b).
- **The product.** Name it after the mechanism, show the bottle at least three times and never for long,
  and keep brand and logo on screen well under a quarter of the runtime [VENDOR (opinion) · lab-00009 R4 B2].
- **The card for the plan:** `scripts/sequence_lint.py --regime dr --baseline` (`sequence-grammar.md` §2c).

## 5. Sound — a small palette, placed on the frame

| Sound | Where | How often |
|---|---|---|
| Room tone | under every VO line and across every cut, the hook-to-body join included | continuous |
| Tick or pop | each list label, each review or proof card | per device |
| Ding or soft chime | each checkmark, on the frame it lands | one per check |
| Whoosh | section changes and far-travelling moves (the anatomy camera) | at most about 1 cut in 3 |
| Riser, 0.5–1.5 s | ending exactly on the mechanism reveal, the offer reveal, the end card | 2–3 per ad |
| Record scratch or hard stop | the one pattern-interrupt pivot, never over a key word | at most once |
| Caption pops | — | silent |

[opinion · practitioner consensus, lab-00009 R2 §3 · checked 2026-10-21]. Put the transient on the frame of
the visual event, not at the start of the file. Practitioner levels, which disagree with each other: ticks
and dings about 12–18 dB under the VO, whooshes and risers about 8–12 dB under, room tone about 16–25 dB
under. Master to the delivery preset's loudness (`delivery-format.md`); no flashing frames on an interrupt.

**Music is the user's call.** The research splits: one source leaves music out under talking heads because
it reads more organic, another runs a lyric-free bed about 18 dB under the voice. Neither overrides
`editing-and-audio.md` (the music bed section): ask the user which track, or whether there is one, every
time. Designed SFX come from a licensed source, and each sound's source and licence go in the delivery note.

## 6. Voice — UGC, not a podcast read

- **Pace:** hooks 2.8–3.3 words a second, the body 2.5–2.9 for a 45+ audience (about 160 words a minute of
  body). Never time-compress TTS above about 3.3 [SECONDARY · lab-00009 R2 §6, from published speech-rate
  studies · checked 2026-10-21].
- **Delivery:** vary sentence length; one natural disfluency (a self-correction, a restart) every 20–30 s;
  real breaths at sentence starts, with about half of any evenly spaced generated breaths deleted and some
  line starts nudged 2–4 frames so the rhythm is uneven [opinion · lab-00009 R2 §6].
- **Engine settings:** on ElevenLabs v3/v4 there is no SSML; use ellipses, dashes and audio tags such as
  `[sighs]` or `[exhales]`, at a lower stability, and generate two or three sentences at a time, then comp
  the best takes. Pick a voice that already talks informally: the tags cannot fix the wrong voice [PRIMARY ·
  ElevenLabs documentation, via lab-00009 R2 §6 and R3 §7 · checked 2026-10-21].
- **A phone-mic chain:** high-pass at 80–120 Hz, a gentle roll-off above about 10–12 kHz, 2–4 dB of light
  compression with no hard gate, a short small-room reverb on a send, and the room tone underneath
  [opinion · lab-00009 R2 §6].
- **The words are claims-sensitive, so the voice comes first.** `ai-generation.md` Step 4 makes Path A
  (TTS of the locked text, then the clip with that audio as its reference) mandatory for locked or
  claims-sensitive wording. Captions come from the final VO's word timings (`typography-and-captions.md`
  §3b).

## 7. AI routing for this lane — the roster only

| Shot | Model | Why |
|---|---|---|
| Talking-head lines, cut into lines of about 6–12 s | `minimax_h3` at 2K | held one continuous take on a speaking face in a vendor's side-by-side, and led a realism benchmark [VENDOR · lab-00009 R3 §1 · 2026] |
| Silent handheld b-roll | `kling3_0` | the roster's b-roll model; add "one continuous shot, no cuts" |
| Skin and eye close-ups | `seedance_2_5` | where the budget allows [VENDOR · lab-00009 R3 §1] |
| 3D anatomy | a stylised, semi-scientific still (translucent torso, the organ highlighted, a dark ground), animated with first and last frame on `kling3_0` | not photoreal surgery: see the picture rule in `compliance.md` §3 |
| A cartoon expert | `seedance_2_5`, in a deliberately cartoon 3D style | never a photoreal white coat or a "Dr." byline (`compliance.md` §2) |

- **Whether H3's audio reference drives accurate lipsync to a supplied TTS track is unverified**
  (lab-00009 R3, "could not verify" item 7). Bake it off on one line before the first batch, per
  `ai-generation.md` Step 4; its fallbacks are listed there.
- **The resolution floor holds**: generate at 1080p or the model's best tier (`ai-generation.md`, the
  quality floor). A free lower-resolution route is not part of this lane.
- **Avatar generators and other models the research named are off the roster** and are not used here.
- **One prompt checklist per shot** [opinion · lab-00009 R3 §3]: a phone-geometry phrase; one named light
  source with its direction and colour; a cause for any camera motion; "one continuous shot, no cuts, no
  subtitles, no music"; two or three concrete age markers without listing flaws; a hand with one job; the
  clip generated to the length of its line. QA the motion first and the texture second, and keep the
  presenter's mouth off screen whenever the VO allows.
- **Present an AI person as a storyteller, not a customer.** A synthetic presenter reporting a personal
  result is the fabricated-testimonial risk in `compliance.md` §2; "my sister…" or "women I talk to…" is the
  shape that does not claim a result she never had [VENDOR (opinion) · lab-00009 R4 A4].

## 8. Two tests on every export

**The mute test** — phone volume at 0, the export full-screen on a real phone in the platform preview
[opinion · lab-00009 R2 §7]:
1. In the first 3 s, with no audio, can a stranger tell the topic and who it is for?
2. Read the captions only: do they tell the story (problem, cause, mechanism, solution, proof, offer)?
3. Pause at three random points: is every claim, number and price on screen as text?
4. Is the proof visible: the cards, the checkmarks, the mechanism?
5. Is the offer and the button on screen as text for at least 2–3 s, inside the box (§3)?
6. Does one person who has not seen the brief know what it is, why to care, and what to do next?

Since v2.41 this list is **T1** of the shared sound-off test (`sound-off-story.md`): run on a muted proof of each
delivery file, logged with `qa_log.py --gate soundoff`, and required by `approve export`. The DR lane also runs
**T2**: the picture alone, no captions, read first by someone who has not seen the brief (question 6, made a
procedure).

**The organic-feel test** [opinion · lab-00009 R2 §7]:
1. The first frame has no logo, no designed title card and no studio light.
2. Room tone is present, and there is no music bed (or a very low one) under the talking head.
3. The speech has some unscripted rhythm.
4. One native-looking caption style throughout.
5. No heavy grade on the a-roll.
6. No "I used this" line voiced by an AI person.

## 9. What this file does not know

- Whether pop captions sell better than line captions. No study compares them in ads; §3b of
  `typography-and-captions.md` rests on reading research.
- Whether any single device raises conversion. The counts in §2 are what one agency does.
- The practitioner levels and intervals in §4–§5. They are opinion, and they disagree.
- Whether a Higgsfield clip's invisible markers survive a Resolve re-encode, which decides whether a
  platform labels the ad as AI on its own (lab-00009 R3, "could not verify" item 11).
