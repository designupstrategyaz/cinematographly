# Product video — software, apps and SaaS: formats, screen footage, text over UI, sound and cards

Loaded when the subject is a product's own interface (a web app, a mobile app, a dashboard), in any mode. It
covers what the rest of the skill does not: how real UI footage is captured, framed, moved and labelled, and
the beat structures of the formats software companies buy.

The client's choices go in their style guide (`clients/_STYLE-GUIDE-TEMPLATE.md`, filled as
`clients/style.<brand>.md`). This file gives the defaults and the evidence behind them. The house default
still holds: captions are the only on-screen text unless the project's approved title card names more
(`typography-and-captions.md` §6c, house rule C3; the card is proposed from what the profile allows).

Evidence tags:

- **[PRIMARY]**: a platform, a standard or a data study.
- **[VENDOR]**: a tool maker on its own tool, or a vendor's data report.
- **[PRACTITIONER]**: a named studio's opinion.
- **[VENDOR-TASTE]**: one client's approvals and rejections across six code-built launch films (Higgsfield's
  higgsfield-motion-saas skill, its client-taste file, October 2026). One client's taste, not a market rule.
- **[COMMUNITY]**: the awesome-opus5-5-videos prompt collection, read through a fetch summary.

All sources were read 2026-10-23 unless the line says otherwise.

## 0. The one hard rule: the product's UI is never generated

A video or image model invents interface text, icons and numbers that the product does not have. Every frame
of the product's own UI is a **real capture** of the real product, or a code-built recreation the client has
approved. AI generation is for the people, the world and the b-roll around the product.

To put the UI on a phone in a generated shot, composite the real capture onto the screen
(`real-and-ai.md`). This is the same rule as the logo: in-world, real, never rendered by a model.

The same rule covers a product's mechanism, a cutaway or a diagram of how it works: never generated, built from
the real numbers, every label read from one spec (`modes/editorial-explainer.md`, the mechanism and diagram beat).

## 1. Formats and their beat structures

Length data first. Completion falls with length: under 1 min 66 %, 1–2 min 56 %, 2–10 min 50 % [VENDOR ·
Vidyard, 1.78 M business videos, 2022 data]. Under 1 min holds about half its audience [VENDOR · Wistia,
2025]. TikTok's model found 21–34 s ads converted best, with a text CTA, at 720p or above, in 9:16 [PRIMARY ·
TikTok, ML analysis, December 2021].

| Format | Length | Beats (one idea each) | Source |
|---|---|---|---|
| **Social clip** | 15–34 s | The proposition in the first 3 s and the hook by 6 s → 2–3 selling points shown in the product → CTA | [PRIMARY · TikTok Creative best practices, June 2025] |
| **Feature launch** | 20–45 s | Who it is for → before (the old way, 1 beat) → after (the feature doing it) → how to turn it on → CTA | [VENDOR · Clevera launch kit] |
| **Launch teaser** | 15–30 s | Hook → three fast product moments → "live now" → where to get it, in the last 3 s. Open on the screen mid-task; brand card in the last second | [VENDOR · Clevera; proMotion.studio] |
| **Product demo** | 60–120 s | One-line setup → the workflow in 3–4 beats, the last one being "it's live" → one proof moment → CTA. Word budget: 60 s = 125–150 words, 90 s = 150–200 | [PRACTITIONER · Simplifilm] |
| **Explainer** | about 60 s | Hook 0–8 s → problem 8–20 → solution 20–35 → how it works 35–50 (three steps at most) → CTA 50–60, at 130–150 spoken wpm as a ceiling | [PRACTITIONER · Educational Voice, 2026] |
| **Customer story** | about 2–2.5 min, plus 30–60 s cut-downs | The strongest line or result first (0–10 s) → who they are → the problem → the decision → the change → results → their advice and CTA. Every number on screen with its baseline and period. Do not script the customer | [VENDOR · Mindstamp; PRACTITIONER · Heavybit] |

Mode C's three-movement shape (`modes/editorial-explainer.md`) fits the explainer. A claim about a customer's
results is a testimonial (`compliance.md` §2), and the numbers need the client's evidence.

## 2. Product footage: capture, framing, cursor, zoom

### 2.1 Capture spec (the shoot)

| Item | Default | Why |
|---|---|---|
| Resolution | 3840 × 2160, or a Retina screen at 2× | Punch-ins stay sharp; record large, export smaller [PRACTITIONER · Dynatrace capture guide; VENDOR · TechSmith] |
| Browser | 125 % zoom; no bookmarks bar, extensions or OS toolbars | [PRACTITIONER · Dynatrace] |
| Data | A demo account with fictional names, numbers and avatars. Hide real customer data before recording; blurring afterwards misses frames | Apple requires fictional account data in App Store previews (Guideline 2.3.9) [PRIMARY]; Arcade and Loom both edit or blur before or during capture [VENDOR] |
| Cursor | Moved slowly and on purpose; no audio during capture (the VO is recorded separately) | [PRACTITIONER · Dynatrace; VENDOR · TechSmith] |
| Takes | One take per beat, with a second of stillness either side | Room to cut and to zoom |

The client's real product and data are client material (`stock-sourcing.md` §9). Record each capture's
provenance like any other asset.

### 2.2 Frame or no frame

- **No frame, full bleed**, when the detail is the point: a setting, a number, a result.
- **A browser or device frame** when context is the point: "it runs in your browser", "it's on your phone".
  Rotato and Screen Studio supply device frames [VENDOR].
- **On 9:16 a desktop UI is never shown at full width.** A 1920-wide screen scaled into 1080 is 0.56 of its
  size, so 14 px interface text becomes about 8 px, which nobody reads on a phone (arithmetic). Crop to the
  active region and punch in at 2× or more, or rebuild the moment on a mobile layout.
- App Store previews are a separate deliverable with their own rules: native resolution, no hands or
  devices, dissolves allowed [PRIMARY · Apple app-preview specifications].

### 2.3 Cursor and clicks

- An enlarged, smoothed cursor that hides when idle. Each move takes 0.6–0.9 s on a 5–15 % arc, and the
  cursor enters and leaves from outside the frame [VENDOR-TASTE].
- A click: squash to 0.92 over 0.12 s, release over 0.2 s, with an optional ripple and click sound on the
  same frame [VENDOR-TASTE; VENDOR · Screen Studio].
- Typing at 50–60 characters a second at most, in a human cadence, with a caret [VENDOR-TASTE].
- A held drag follows the cursor and springs back on release. The cursor drives every change: nothing in
  the UI changes without a visible cause [COMMUNITY].

### 2.4 Zoom and camera over the UI

- **Auto-zoom on the click, at the lowest scale that keeps the text readable.** Tella's defaults are 1.5×
  (slow and medium) and 2× (fast), its range 1–3.5×, each zoom at least 1 s [VENDOR · Tella docs]. Too
  close goes soft [VENDOR · Arcade, Tella].
- **One motivated move per scene.** Each camera move has a cause on screen: follow the caret, lean in on the
  click, pull back when results land, push in as a card grows [VENDOR-TASTE].
- A zoom is interpolated in log space. Never put two zoom-ins in a row [COMMUNITY]. The zoom direction never
  flips across a cut: a camera that flies into something lands in the next shot from further out and settles
  in [VENDOR-TASTE].
- **In-scene curves are soft** (entrances 0.45–0.7 s, overshoot 2–4 % at most). **Strong curves only hide a
  cut:** the cut sits at the peak of the move [VENDOR-TASTE].
- Large zooms, spins and long pans are vestibular triggers; opacity, colour and small scale changes are safe
  [PRIMARY · WebKit, WCAG 2.3.3; PRACTITIONER · Val Head]. Keep zoom factors moderate.
- A pan on a real camera runs no faster than one frame width per 7 s at 24 fps [VENDOR · RED]. A UI pan
  under motion blur can run faster; judge it on the contact sheet.

### 2.5 Transitions between screens

- **Ads and launches: carry, morph or cut — not a crossfade.** Keep one thing continuous across the cut (the
  object, its direction, the UI state or a colour) and hard-cut the rest. "Nothing appears or leaves by
  opacity alone" [VENDOR-TASTE]. The same lists ban shockwave rings, particles, RGB split, camera shake, lens
  flares, neon glows and bouncy easing [COMMUNITY]. A light leak stays out with them unless the job's CHECKPOINT
  carries the `light-leak` switch (`assets/project-switches.json`): one leak hit on one cut, screen-blended and
  peaking on the transition, inside the accent budget (`editing-and-audio.md` § Transitions, the budget, C5)
  (v2.48.0, switch `light-leak`) — when and where: `editing-and-audio.md` § Finishing looks.
- **App Store previews: dissolves and fades are the platform's own advice**, and a transition must not imply
  a feature the app lacks [PRIMARY · Apple]. The destination decides.

## 3. Text over UI

- **Size.** A line of text is 7–8 % of the frame height on 16:9 and 1:1, and 3.9–4.5 % on 9:16 (about 75–86
  px either way at 1080 wide) [PRIMARY · BBC Subtitle Guidelines 1.2.5, March 2026]. Supers follow the
  caption type block in the profile (`typography-and-captions.md` §8).
- **Contrast.** 4.5:1, or 3:1 for large text [PRIMARY · WCAG 1.4.3]. Check it over the moving background, not
  on a still. One client rejected a dark plate behind text, so dim the background's exposure first and add a
  soft shadow [VENDOR-TASTE]; the profile decides.
- **Placement.** Never over the UI element being demonstrated: put the text in the area the camera move
  leaves empty. Safe zones are in `typography-and-captions.md` §5b and `dr-advertorial.md` §3. Meta asks for
  the bottom 35 % of a Reel to stay clear [PRIMARY · Meta Reels Ads Guide, about mid-2024].
- **Hold.** At least 0.3 s a word, and never under the reading floor in `typography-and-captions.md` §5.
  Any must-read line holds 0.8 s or more, and a 15 s film carries 16 must-read words or fewer
  [VENDOR-TASTE]. TikTok's "5–10 words a second" is a ceiling, not a target [PRIMARY · TikTok].
- **Outgoing text clears before incoming text arrives**: two supers never share the frame [COMMUNITY].

## 4. Voiceover or on-screen text: both, with different jobs

- Sound is on more than the old folklore says. 80 % of Reels are viewed with sound (`typography-and-captions.md`,
  opening note), and 88 % of TikTok users call sound essential [PRIMARY · TikTok and Kantar, 2021].
- Captions still lift completion and recall: 80 % of viewers say they are more likely to finish with captions,
  and captions gave +8 % ad recall on mobile [PRIMARY · Verizon Media and Publicis survey, 2019].
- On Demand Gen in-stream ads, a human voice gave +12 % conversions and supers +3 % [PRIMARY · Google Ads,
  US, July 2026].

So every product video is built to work both ways:

| Channel | Carries |
|---|---|
| **VO** | The argument |
| **Captions** | The VO, word for word |
| **Supers** | Only the 3–5 things that must survive a muted scroll: the product name, the promise, the offer, the CTA |

A logo and captions on screen at the same moment cut ad memory by 12 % in the same survey [PRIMARY · Verizon
Media and Publicis, 2019], so give each one its own moment.

**The standard voice.** Record one ElevenLabs voice per client, with its settings, in the style guide (§5 of
the template) and in `clients/<brand>.md` §2. Lock it per series. Vendor guidance [VENDOR · ElevenLabs docs]:

| Setting | Guidance |
|---|---|
| Model | Multilingual v2 is the most stable for long-form and reads numbers and dates reliably; v3 and the newer v4 are more expressive |
| Stability | About 50 to start |
| Similarity | About 75 |
| Style exaggeration | 0 |
| Speaker boost | On only if it helps (it adds latency) |
| Speed | 1.0 (range 0.7–1.2) |
| Pronunciation | A pronunciation dictionary for the product's names |

v3 and v4 drop the similarity, boost and speed controls and the break tags. Keep a 10-second reference read
of the locked settings, so drift can be heard. Clone only a voice the client has rights to (`compliance.md` §5, the hard rules).

## 5. Sound

**UI sound effects.** Put a click on the click frame, quiet ticks under typing, a whoosh on a carried
transition, and one chime on the result. Place each transient at its peak on the frame of the event
(`dr-advertorial.md` §5 has the map and the levels). Material Design's rule for interfaces applies: earcons
for feedback, decorative sound sparingly, and nothing on a frequent action [PRIMARY · Material Design,
Applying sound to UI].

**Music under speech: at least 10 LU below the speech, measured, not set.**

- Torcoli et al. recommend speech at least **10 LU** above music and **15 LU** above ambience.
- Non-expert listeners preferred gaps **4 LU larger** than experts did [PRIMARY · JAES 2019, 22 listeners].
- So for a general audience aim at about 14 LU under the voice. The duck is whatever gain change reaches that.
  `editing-and-audio.md` (the audio finish) carries the rule, and the profile token is
  `music.duck` (`brand-system.md` §2).

**Loudness.** Loudness comes from the delivery preset (`delivery-format.md`). No social platform publishes
an upload target; Meta normalises at playback [PRIMARY · Meta engineering, 2023], and YouTube turns loud
uploads down but never quiet ones up [PRACTITIONER · Ian Shepherd].

**A clean mix for the client.** When the client mixes the final themselves, deliver the M&E and a no-sound
master (`editing-and-audio.md`, the M&E section).

## 6. Opening card and end card

The house default is neither (`editing-and-audio.md`, the captions section). Both are opt-in, through the style
guide.

**Opening.** Brand within the first 5 s, and two or more shots in the first 5 s [PRIMARY · YouTube ABCD;
Google and Kantar, 11,000 ads: +30 % short-term sales likelihood]. The proposition goes in the first 3 s
[PRIMARY · TikTok]. In a product video the brand arrives *in* the product (its UI and logo on screen, or a
person saying the name), not as a card [PRIMARY · ABCD: people saying the brand beat voiceover]. If the client
wants an opening card, it lasts 1 s at most, and the product is already mid-task behind or after it [VENDOR ·
proMotion.studio].

**End card**, when the profile asks for one, built once as a template:

| Element | Spec |
|---|---|
| Wordmark or logo | Centred, upper-middle of the safe box |
| Tagline | 1–2 lines, at the caption type block's size or larger |
| CTA | One action, written as the button the viewer will see. Above the platform's bottom rail (`dr-advertorial.md` §3: above y 1248 on 1920). Never "swipe up" on TikTok, which moves the viewer to the next video [PRIMARY · TikTok] |
| URL or store badge | Optional, if the placement has no link button |
| Voice | The VO says the CTA while the card shows it [PRIMARY · ABCD] |
| Required text | A purchase or offer disclaimer goes here when one is required (`compliance.md`; App Store previews allow it in the end frame [PRIMARY · Apple]) |
| Hold | About 4 s, never under its reading time (`sequence-grammar.md` §2c, item 11). No platform publishes an end-card hold for ads |
| Motion | Enters with the house motion for supers (`typography-and-captions.md` §6b), holds still, ends clean |

## 7. Which pipeline makes which piece

| Piece | Made with |
|---|---|
| UI moments | Real captures, cut and zoomed in Resolve (§2) |
| People using the product, the world, b-roll | This skill's generation pipeline, with the real UI composited onto screens (`real-and-ai.md`) |
| Supers, cards, motion graphics | The supers lane (`typography-and-captions.md` §6b) |
| A fully code-rendered launch film (needle zooms, morphs, synth sound) | A different genre. Use the higgsfield-motion-saas skill if it is installed |

## 8. What this file cannot tell you

- None of the beat structures in §1 comes from a controlled study. They are vendor and studio practice, and
  the TikTok length finding is a 2021 model.
- No documented defaults were found for cursor size, ripple length or zoom easing in the screen-recording
  tools. The numbers in §2.3 are one client's taste.
- No platform publishes a minimum super size in pixels or an end-card hold for ads.
- Current Meta figures for sound-off viewing were not found. The 2016 "85 % muted" figure came from
  publishers' data, not Meta.
