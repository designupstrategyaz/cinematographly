# Client Profile — <BRAND>

Copy this file to `<brand>.md` in your own client folder (the folder `CINE_CLIENTS` names, or a
`_cine-clients/` folder above your jobs) and fill it in. **Load the matching profile whenever the task
is a video for that brand.** The general skill (`SKILL.md` + `modes/` + `references/`) is the *how*;
this profile is the *who/what*, and **when a profile value conflicts with a general default, the
profile wins.**

Add a row to that folder's `_INDEX.md` and create `costs.<brand>.json` beside the profile in the same pass.

(For a filled-in example, read `clients/acme.md`: an invented sample, not a client.)

---

## 0. ⛔ Hard locks (read before any change)

> ⛔ `scripts/gate.py open` reads this section. Any `<placeholder>`, `NEEDS INPUT` or `TBD` left
> here refuses the job: an unanswered hard lock is a question for the client, not a default.

**Default mode:** <A narrative-promo / B ugc-volume / C editorial / D repurpose> — and why.

List anything that is **fixed** and overrides improvement advice. Common ones:

1. **Format lock?** <is the script/prompt structure frozen, or open>
2. **Audio-text lock?** <can spoken lines be reworded, or are they approved as-is>
3. **Overlay policy?** <captions only is the skill default — does this client render anything else>
4. **Retired tools/models?** <anything explicitly out of the stack, and why>

If there are none, say so explicitly — "no hard locks; copy is open" is useful information.

**Verification policy — answer this one for every brand, it is never a default:**

**Verification policy:** `<per-stage-human | gated | standing>`

⛔ That line is parsed by `scripts/gate.py` — keep the exact shape `**Verification policy:** \`value\``.
The gate refuses to open a job while it still reads as a placeholder, and the PreToolUse hook denies
every generate_* call for a job whose profile does not carry it. The three values:

- `per-stage-human` — a person checks the script, the reference images, the audio and the clips,
  each before the next stage starts. ⛔ Overrides the review tiering, and a shared frame gate is not
  a substitute.
- `gated` — the general convention: machine triage first, human eyes concentrated at the frame gate
  and on flagged/landing/hero shots (`production-runbook.md` §5).
- `standing` — a pure variant ships on standing approval (`review-and-approval.md` §10).

⛔ An unanswered verification policy is **not** "gated by default" — ask. Getting this wrong in the
permissive direction ships unreviewed work to a client who expected to see it.

## 1. Brand(s)
- <company / product / sub-brands and how they relate>
- **Positioning line:** <the one sentence the videos are always arguing>
- **Logo & in-frame branding rules:** <what appears on screen and how>

## 2. Characters, personas & voices
- **Recurring characters** (Mode A): <role / personality / look> · voice **<voice id>**
- **Buyer personas** (Mode B): list them; full sheets from `assets/persona-brief-template.md`
- **Tonal locks:** <the non-negotiable character/tone rules>
- **Dialogue dynamic:** <initiator vs skeptic; peers?>
- **Identity lock method:** <platform Element id / hero reference frame + seed>
- **Written-voice profile:** <path to the client's voice profile, if your studio keeps one, or "none — house register"> · **load it BEFORE drafting**
  (`references/script-craft.md` §4); an anti-pattern list alone leaves the model in its default voice

## 3. Offer / subject matter (claims that must be accurate)
- <what's being sold; the value props>
- <programs, eligibility, deadlines, prices — and where each is verified>
- **Substantiation file:** <where the evidence for each claim lives, and who owns it>

**Claims-category:** `<sleep | beauty | supplements | finance | none>` — read by `gate.py approve script`, which runs `claims_lint.py` on the artifact with these patterns and REFUSES on any BLOCK. ⛔ `none` is a decision, not a blank: say it explicitly.

## 4. Non-negotiables (compliance) — what the ✅ Branding Check protects
1. <…>  2. <…>  3. <…>
- **Claims-sensitive category?** <sleep / wellness / beauty / supplements / health / finance / none>
  → if yes, `references/compliance.md` runs on every script and every export.
- **Approved-language sheet:** <link/path> · **Signer:** <name>
- **Restricted words for this brand:** <the client's own banned list, as items below — or `none`>
  - `<word or phrase>` → `<the replacement the client agreed>`
  - `<word or phrase with no agreed replacement>`
- **Required disclaimers:** <exact text, and where it must appear>

> ⛔ **The restricted-words list is read by `scripts/claims_lint.py`**, which `gate.py approve
> script` runs, so a listed word BLOCKs the script approval. Keep this shape:
> - one indented `- ` item per word or phrase, the word in backticks: `` - `cheap` ``;
> - when the client agreed a replacement, `→` (or `->`) and the replacement in backticks:
>   `` - `cheap` → `affordable` ``. More than one agreed replacement: each in its own backticks;
> - anything after the last backtick is a note and is not read (who agreed it, and when);
> - `none` on the field line when the client has no list.
>
> Matching is case-insensitive on word boundaries: `cheap` catches "Cheap!" but not "cheapest", so list
> each form the client bans. A listed word inside its agreed replacement passes (`free` → `free trial`
> lets "free trial" through and still blocks "free"). The lint reads spoken lines, captions, on-screen
> text and quoted reviews; in production notes the word is reported as a mention. An empty field or a
> placeholder skips the check, and the report says so; a field written as prose with no items is
> reported as NOT READ. `--allow "<phrase>"` overrides a listed word only with the client's written
> approval, as for any other claim.

## 5. Language, distribution & delivery format
- **Language / captions:** <target language + diacritics; captions burned in?>
- **Platforms:** <the actual channels — confirm, never assume> · **Accounts:** <handles>
- **AI-disclosure mechanism per platform:** <which toggle, plus the on-screen treatment>

### Delivery format — `<preset name>`
There is **no house format** (`references/delivery-format.md`). Name a preset from
`assets/delivery-formats.json`, or add one there.

| | |
|---|---|
| Preset | `<vertical-1080 / feed-4x5 / landscape-1080 / broadcast-eu-1080 / …>` |
| Aspect / resolution | <…> |
| Frame rate | <timeline fps> |
| Duration window | <…> |
| Loudness | <LUFS, true peak> |
| Safe zones | <from the preset; confirm per channel> |
| Filename token | `_<token>` |

- **Master format vs derived:** <if more than one, which is authored and which are re-crops>
- **Generation resolution:** <equal to delivery (stack requires it), or below-and-upscale> — and why

## 6. Visual Bible (the brand's tokens)
Written once, held across every video. Method: `references/production-design.md` §7; the token model,
shot components and drift audit are in `references/brand-system.md`.
- **Palette:** brand hexes · the held grade · saturation/value register · the one warm accent
- **Colour relationship:** <complementary / analogous / monochromatic / …> and why
- **Cultural check:** <any colour whose association inverts for this audience>
- **Per character/persona:** the verbatim wardrobe block · reference image paths · the identifying detail
- **Approved settings:** <3–5 environments, each with its named light source + Kelvin + prop list + the imperfection>
- **Product on camera:** the real asset files and how they are composited onto the start frame
- **Caption type block** (`references/typography-and-captions.md` §8): face + weight + fallback ·
  size / leading / tracking / case / alignment at the delivery resolution · contrast treatment
  (plate / shadow / reserved band) with values · fill and plate hex, tonal contrast checked ·
  disclosure treatment · **character-set check for the target language's diacritics**
- **Shot components** (`references/brand-system.md` §3): the named reusable shot types for this
  brand — dialogue MCU, establishing insert, product macro, reaction cutaway, the button — each with
  its framing, prompt skeleton, known failure and QA note
- **The "right kind of wrongness":** the deliberate break from the category's visual template that
  makes this brand recognisable — write it down, or it erodes toward the category mean
- **Edit assets & transition palette:** installed packs on the edit machine · the brand's allowed
  transition palette (tightening the mode palette in `references/editing-and-audio.md` § Transitions)
  · the *specific* pack asset names in use · title templates **only if this profile permits on-screen
  titles** (the skill default is captions-only)
- **Negative list:** what never appears in frame for this brand
- **On-screen system and standard voice (opt-in):** when the client wants supers, an opening or end
  card, a UI-footage treatment or one standard ElevenLabs voice, fill `clients/_STYLE-GUIDE-TEMPLATE.md`
  as `clients/style.<brand>.md` and point here. Only the sections filled there switch anything on

## 7. Assets & archive (Mode B especially)

> **Reference set:** per-project inputs live in `_reference/` (`character/ wardrobe/ props/
> environment/ light/ motion/`), one attribute per file, provenance sidecar per asset. A reference
> that produced an approved frame is **promoted into §6's Visual Bible** and reused across the
> account instead of re-sourced per video. Faces marked reference-only stay reference-only
> (`stock-sourcing.md` §5).
- **Existing UGC / B-roll archive:** <where it lives, how much, what it covers>
- **Licensing status:** <organic only? paid cleared? per-clip or blanket? expiry?>
- **Brand assets:** <logo files, product renders, palette hexes, fonts, music library>

## 7b. Script numbers — `clients/script.<brand>.json`

⛔ **Required before a script is written.** Copy `clients/script._TEMPLATE.json` and fill in
`runtime_target_s`, `hook_seconds_min`, `cta_seconds`, `beat_seconds`, `max_words_per_line`,
`speakers`. `scripts/beat_plan.py` derives the scene count from them and `scripts/script_score.py`
scores against them; **both refuse to run rather than assume a default.**

⛔ **Do not copy another brand's file.** That is exactly how one account's four-scene format became
this skill's template — see `references/script-format.md` § The scene count is DERIVED.

## 8. Generation stack & budget
- **Generation MCP / tools:** <which MCP>
- **Keys this account needs, and where they live** (⛔ the PATH, never the value —
  `references/environments.md` §2): <e.g. Pixabay → `~/.config/pixabay.key`; Higgsfield → MCP config>
- **Models:** start frames = <id>; **dialogue (mouth visible) = <id> with audio as reference**;
  B-roll = <id>; retired = <ids, and why>
- **Model roster** — one capability card per model (`references/ai-generation.md` § The model
  roster): strengths (earned in bake-offs) · failure modes (guardrail-table rows) · quirks (fps,
  resolution behaviour, audio, preset intercept) · **last verified <date>**. A row older than a
  quarter is a hypothesis; re-verify before a big batch.
- **Voices:** <character/persona → voice mapping>
- **Plan & envelope:** <monthly credits; per-video or per-batch budget; volume target>
- **Real per-generation costs:** in `clients/costs.<brand>.json` — **not restated in prose here**
- **Economy defaults:** <the cheap levers for this stack>

## 9. Script house format
- <structure, length, scene count, hook & CTA conventions, language>
- <1–3 worked examples, or links to the best shipped scripts>
- **⚠ Mark worked examples as illustrative** — re-verify every date, code, and program fact against
  the current brief before reusing one.

## 10. Production files & PM
- **Production root + naming:** <path + convention> (`00-brief … 10-export / 99-costs`)
- **PM tool & IDs:** <workspace / space / list ids; template task; onboarding doc>
- **Publish target:** <channel/account>
- **Reporting cadence the client expects:** <daily note? weekly? none>

## 10b. Review & approval

Per `references/review-and-approval.md` §7. Unanswered = NEEDS INPUT, never a guess.

| Question | This client |
|---|---|
| Platform, and whose account | <Frame.io / Dropbox Replay / ClickUp proofing / theirs — who pays> |
| If Replay: approver has a Dropbox login? | <yes / no — without one they can comment but not press Approved> |
| Named approver(s) | <one person whose `APPROVED` counts; a committee with no decider is the expensive failure> |
| Rounds included / price beyond | <n rounds; round n+1 = change order at …> |
| Turnaround SLA (both ways) | <yours to fix; theirs to respond before the silence rule applies> |
| Version visibility | <latest only / full history> |
| Share controls | <passphrase · expiry · downloads on-off · watermark (Pro+)> |
| Record location | `09-qa/review/comments-r<N>.csv` + decision record in `00-brief/DECISIONS-<SLUG>.md` |

## 11. Improvement scope
Which of this skill's advice applies here, and which is out because of §0. Be explicit — this is the
section that stops a future session "improving" something that is locked.
