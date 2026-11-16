# Craft Cheatsheet — short-form film craft for promo video

Distilled from the author's notes on published film-craft books: McKee, Cooper
& Dancyger, Pope, Cowgill, Katz, Brown, Ward, StudioBinder, Pearlman, Bowen, Glebas, Rabiger,
plus the Midjourney/realism prompt extractions. Everything here is tuned for a ~60-second,
mobile-first promo. Author names in parentheses point you to the deeper source.

**This is the fast lookup. The reasoning under it is in `cinematography-craft.md`** (lighting as a
decision system, lens language, movement grammar, staging, composition, and the table of what
actually survives into an AI pipeline) **and `editing-storytelling.md`** (why a cut works, montage,
continuity and when to break it, rhythm, performance in the cut). Read those when the cheatsheet's
answer is not enough, or when you need to justify a decision to a client.

## 1 · Story & script (short form)

- **The gap is the engine (McKee).** Set an expectation, then deliver something different.
  Typically: the skeptic expects a catch (cost, risk); the guide reframes and closes the gap.
- **One dramatic question, binary answer (Cooper & Dancyger).** e.g. "Can they get X with zero
  risk?" — posed in the first ~15s, answered in the last ~10s. Not three questions.
- **Antagonism must be real (McKee, Pope).** The obstacle = the audience's genuine objection.
  Weak opposition makes a flat, unconvincing video.
- **Every scene turns a value (McKee, Pope).** Trust↔doubt, worry↔relief. If nothing flips,
  the scene doesn't exist — cut it. In 60s you have room for ~4 turns.
- **Image-first, dialogue-sparse (Cooper & Dancyger).** Lead each scene with an image that
  sets tone + premise; let dialogue do only what images can't.
- **Subtext over on-the-nose (McKee, Pope).** A hesitation or a glance sells doubt better than
  "I'm worried about the cost."
- **Control idea in one sentence (McKee).** "[Value] wins because [cause]." Every scene serves it.
- **End on a button (Cooper & Dancyger).** A decision made, an answer delivered, one CTA. No
  trailing summary.

## 2 · Shot design & composition

- **Establish → intimate (Katz, Ward).** Open wide for geography, move through medium to
  close-up for the emotional beat. Save the tightest shot for the payoff.
- **Shot sizes and what they're for (Katz, Glebas):**
  - *Wide / establishing* — place us in the world, show scale (commune, field, factory).
  - *Medium* — the workhorse of 60s video; expression + context, natural conversation.
  - *Medium close-up* — builds connection; default for a character's key line.
  - *Close-up* — a face full-frame; dialogue intimacy, the decisive beat.
  - *Extreme close-up* — reserve for the climactic reveal (the smile, the handshake, a panel detail).
- **The line / 180° rule (Katz, Bowen, Glebas).** Keep both characters on consistent sides
  across a conversation; cross the line and the space reverses and confuses.
- **Eyeline match (Katz, Ward).** When A looks at B, the next shot's direction must agree, or
  the viewer loses the spatial map.
- **Composition (Ward, Glebas).** Rule of thirds, not dead center. Leave headroom and
  *lookroom* in the direction of gaze/movement. The eye goes to the area of greatest local
  contrast — make the subject (or the brand accent) that peak; subordinate the background.
- **Lens = emotion (Brown, Ward).** Wide (18–35mm) = expansive, energetic, slight face
  distortion, great for environments/action. Normal (50mm) = neutral, trustworthy,
  documentary. Long (85mm+) = isolates, compresses, flatters — intimate testimonial intensity.
  For a credible solar brand, lean normal-to-long with natural light.

## 3 · Lighting & color

- **3-point logic (Brown).** Key (main modelling), fill (opens shadows), backlight/rim
  (separation, dimension). Every light should look *motivated* by a real source (sun, window,
  lamp) or it reads as "lit set."
- **Warm vs cool = feeling (Brown, Ward, StudioBinder).** Warm (gold/orange) = comfort, hope,
  success, life → use for the solved state, happy customer, sunrise. Cool (blue/cyan) =
  problem, distance, uncertainty → use for the "before," the high-bill worry.
- **Orange–teal complementary pair** is the reliable tension look: warm subject against cooler
  surround.
- **Color as a system (StudioBinder).** Saturation = energy (desaturated reads documentary/
  real; saturated reads stylised). Value = mood (high-key optimistic, low-key serious). Give
  the brand one repeated warm accent so the eye locks to the panel/logo at the key moment.
- **Consistency (Brown, Ward).** Match color temperature and skin value across intercut shots,
  or cuts feel discontinuous. Pick one grade and hold it across the whole video — this is also
  how the series stays recognisable.

**⚡ Fix the scenario before the shots — the four-cell matrix.** A 35–55s video lives in one or two
cells. Decide the cell at the plan and every shot inherits its light model, which is how a batch
intercuts without a grade rescue (`cinematography-craft.md` §6.2). A shot list that decides lighting
per shot has already lost the continuity.

| Cell | Default light model | The mixed-temperature pair | UGC-safe version | Name in `[ENVIRONMENT]` |
|---|---|---|---|---|
| **Day interior** | window as key, light coming *in*; practicals as accents | 5600K window vs 2700K lamp | exactly this, uncorrected — it *is* the native phone condition | the window (which wall), the lamp, the blown exterior |
| **Day exterior** | overcast · or golden hour · or sun-as-backlight-plus-bounce | none — one source | ⚡ **overcast**: one token, whole light model, and the only one that is *matchable* across a batch | the sky condition, the ground the bounce comes off |
| **Night interior** | warm practicals, cool window or screen | 2700K lamp vs 4000K window/TV | the strongest cell for UGC — motivated colour contrast with no fixture invented | every lamp that is on, by name |
| **Night exterior** | one large soft overhead as moonlight, plus practicals; needs a base ambient or the frame has holes | 4300K "moon" vs 2200K sodium/shopfront | 🟡 hardest to fake; prefer a lit doorway or a car interior to open street | the practical that explains the exposure |

⛔ Do **not** compose the cell from parts. Pick one and let it decide; mixing a day-interior window
with a night-exterior sodium in one video is the fault F12 catches on the contact sheet, and by then
the clips are paid for. [SECONDARY · StudioBinder, *Film Lighting: The Ultimate Guide*, 2023, for
the four-cell structure and the recipes; the batch argument is `cinematography-craft.md` §6.2]

⛔ The **3-point logic** above is feature-film default and is the fastest single route to "this is
an ad": no phone video has a hair light. It stands for narrative-promo and editorial modes. For UGC
read every fill decision as a **negative-fill** decision instead, and see the withhold list in
`photorealism-physics.md` §8.

## 4 · Editing rhythm

- **Cut on action (Bowen, Pearlman).** The invisible cut lands mid-motion (a turn, a reach).
  Too early feels abrupt; too late drags.
- **Pace on a curve (Pearlman, Bowen).** For 60s: open ~4–5s (establish), tighten to 2–3s
  (build), quicken to 1–2s at the turn, release 3–4s on the button. Identical shot lengths
  read robotic — vary them and rhythm emerges.
- **Three rhythms (Pearlman).** Physical (movement tempo), emotional (hold a face long enough
  for the feeling to register), event (info-dense beats need longer shots). Balance them.
- **Cut with the music, not always on it (Pearlman).** Cutting slightly before a beat builds;
  after it releases. Exact downbeat cuts feel stiff. A one-frame cut to silence = punctuation.
- **The button ending (McKee, Pearlman).** Hold ~3s on the resolved emotion (a smile / a
  handshake / the resolved state), then cut to black. No sentimental trailing shot, and no end
  card unless the project's title card names one — captions are the only on-screen text by default
  (`typography-and-captions.md` §6c, house rule C3).
- **The hard cut governs; ramps are planned (house rule C4–C5, 2026-10-26).** At most 2 accent
  transitions a film, a dip only at the end, nothing on a dialogue clip, whips as seasoning; a ramp is
  declared on the clip (`ramp:`), one per 20 s and 2 a video at most, and every slow-down passes
  `motion_qa.py warp` (`editing-and-audio.md`, the budget and § The ramp).
- **Leave a handle for the transition (production note).** A cross-dissolve needs footage on both
  sides of the cut to blend — generate B-roll 1–2s past what the montage plan needs. Dialogue clips are the exception:
  generate them to the length of the line and take the handle from the join (`shot-handoff.md` §2),
  because extra length on a speaking clip leaves the mouth moving after the line. See `ai-generation.md` / `editing-and-audio.md`.

## 5 · Directing the characters

- **Direct the arc, not the line (Glebas, Rabiger).** The skeptic's face is the story:
  weary/skeptical → curious → convinced → warm. Give the voice/generation that trajectory explicitly.
- **Guide the eye (Glebas).** Each shot has one thing to look at. Use contrast, motion, and
  framing to point at it — the reacting face, the product, the in-world brand mark.
- **Honest performance.** The guide is sincere and playful, never smug; the customer is
  sympathetic, never a buffoon. (The tonal locks live in the client profile.)

## 60-second checklist

**Script:** one question posed by 0:15 / answered by 0:55 · real antagonism · every scene turns
a value · image-first · subtext · one-CTA button.
**Shots:** wide→medium→close progression · count from runtime and pace (`sequence-grammar.md` §2c) · 180° + eyelines honored · one dominant
subject · thirds + lookroom.
**Light/color:** warm=solution / cool=problem · motivated sources · one held grade · brand warm accent.
**Edit:** cut on action · pacing curve · rhythm to music · 3s button then black.
