# Client Profile — `acme` (an invented sample, not a client)

**Status: SAMPLE.** Acme Cycle Works does not exist. It is a made-up neighbourhood bicycle repair
shop, written so that the template has one filled-in example and the tools have one client they can
load on a fresh install. Every fact below is invented: the shop, its offer, its numbers.

- **Copy the shape, never the answers.** Your own client's profile goes in your own client folder
  (the folder `CINE_CLIENTS` names, or a `_cine-clients/` folder above your jobs), not here. A plugin
  update replaces this folder.
- **Do not run client work under this profile.** Section 0 is complete, so `gate.py open` accepts a
  job that names it. That is for trying the pipeline end to end; a real brand needs its own answers.

## 0. ⛔ Hard locks (read before any change)

**Default mode:** B (ugc-volume). A local shop posts short, frequent, one-idea videos; a hero film
would be the wrong size for the budget.

1. **Format lock?** Open. The hook, body and call to action can change from video to video.
2. **Audio-text lock?** Spoken lines can be reworded until the script is approved. After approval
   they are fixed for that video.
3. **Overlay policy?** Captions only, plus the disclosure line in section 5.
4. **Retired tools/models?** None beyond the standing roster in `references/ai-generation.md`.

**Verification policy:** `per-stage-human`

The owner of the shop looks at the script, the reference images, the voice and the clips, each before
the next stage starts. A small shop with one decision-maker can afford that, and it is the safest
answer for a first client.

**Named approver:** Sam Reyes, the shop's owner (an invented person, like the shop). A real profile names one person, never a role.

## 1. Brand(s)
- **Acme Cycle Works:** a two-person bicycle repair shop with one location. No sub-brands.
- **Positioning line:** your bike, fixed properly, back the same week.
- **Logo and in-frame branding:** the shop sign may appear in a wide shot. No logo is added on top
  of the picture.

## 2. Characters, personas & voices
- **Recurring characters:** none. No mascot, no recurring presenter.
- **Buyer personas** (Mode B): the daily commuter whose bike is their transport; the parent with a
  child's bike that has sat in a shed; the weekend rider before a long ride. Full sheets come from
  `assets/persona-brief-template.md`.
- **Tonal locks:** plain and practical. Never mock a customer for a neglected bike.
- **Dialogue dynamic:** one speaker to camera.
- **Identity lock method:** a hero reference frame per persona, approved before any clip.
- **Written-voice profile:** none; house register.

## 3. Offer / subject matter (claims that must be accurate)
- A standard service, a full service, and puncture repair while you wait.
- Prices and turnaround times change. They are read from the shop's current price list for every
  script, never from an older script.
- **Substantiation file:** the shop's price list and booking calendar, owned by the shop's owner.

**Claims-category:** `none` — a repair shop makes no health, finance or sleep claims. `none` is a
decision: the general checks in `claims_lint.py` still run.

## 4. Non-negotiables (compliance) — what the ✅ Branding Check protects
1. No price or turnaround time that the current price list does not show.
2. No before-and-after of a bike the shop did not repair.
3. No claim about safety that goes beyond "checked and adjusted".
- **Claims-sensitive category?** None.
- **Approved-language sheet:** the price list. **Signer:** the shop's owner.
- **Restricted words for this brand:**
  - `cheap` → `affordable`
  - `guaranteed`
  - `good as new` → `running smoothly`
- **Required disclaimers:** none beyond the AI disclosure in section 5.

## 5. Language, distribution & delivery format
- **Language / captions:** English. Captions burned in.
- **Platforms:** Instagram Reels and TikTok, organic only. **Accounts:** the shop's own.
- **AI-disclosure mechanism per platform:** each platform's own AI-content label, and one caption
  line saying the people shown are AI-generated.

### Delivery format — `vertical-1080`

| | |
|---|---|
| Preset | `vertical-1080` |
| Aspect / resolution | 9:16, 1080 × 1920 |
| Frame rate | 24 |
| Duration window | 20 to 35 seconds |
| Loudness | from the preset |
| Safe zones | from the preset |
| Filename token | `_v1080` |

- **Master format vs derived:** one master, nothing derived.
- **Generation resolution:** equal to delivery.

## 6. Visual Bible (the brand's tokens)
- **Palette:** workshop greys and worn wood, daylight from the shop window, one warm accent: the
  orange of the shop's work aprons.
- **Colour relationship:** a muted, near-monochrome room with one complementary accent, so the eye
  goes to the hands and the bike.
- **Cultural check:** none found for this audience.
- **Per persona:** everyday clothes for the weather; a helmet carried, not worn indoors.
- **Approved settings:** the workshop bench under the window; the shop doorway; the street outside
  on an overcast day.
- **Product on camera:** real photos of the shop's own tools and stand. Customer bikes are generic.
- **Caption type block:** set per `references/typography-and-captions.md` §8 before the first batch.
- **The "right kind of wrongness":** the bench is never tidy. Every other shop's video is spotless.
- **Negative list:** no other shop's branding; no bike maker's logo in close-up; no child without
  an adult in frame.

## 7. Assets & archive
- **Existing archive:** about forty phone photos of the workshop, taken by the owner.
- **Licensing status:** the shop's own photos, cleared for organic and paid use.
- **Brand assets:** the shop sign artwork. No font, no music library.

## 7b. Script numbers — `clients/script.acme.json`
Invented numbers, so `beat_plan.py` and `script_score.py` have something to run on. Measure your own.

## 8. Generation stack & budget
- **Generation tools and models:** the standing roster in `references/ai-generation.md`.
- **Keys this account needs, and where they live:** none are recorded for a sample.
- **Voices:** one narrator voice per persona, chosen at the voice gate.
- **Plan and envelope:** in `clients/costs.acme.json`. Its numbers are the template's and were not
  measured on any account. Never quote a real client from that file.

## 9. Script house format
- One idea per video: hook, the problem shown, the fix shown, one ask.
- Worked scripts: none yet.

## 10. Production files & PM
- **Production root and naming:** `acme-<number>-<slug>`, with the standard `00-brief … 10-export`
  folders.
- **PM tool and ids:** none for a sample.
- **Reporting cadence:** none.

## 10b. Review & approval

| Question | This client |
|---|---|
| Platform, and whose account | the studio's review tool, on the studio's account |
| Named approver(s) | Sam Reyes (the shop's owner) |
| Rounds included / price beyond | two rounds; a third is a change order |
| Turnaround SLA (both ways) | two working days each way |
| Version visibility | latest only |
| Share controls | link expires after 14 days; downloads off |
| Record location | `09-qa/review/comments-r<N>.csv` and the decision record in `00-brief/` |

## 11. Improvement scope
Everything in the skill applies. Nothing is locked beyond section 0.
