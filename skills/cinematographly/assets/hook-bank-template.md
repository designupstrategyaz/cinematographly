# Hook bank — <BRAND>
Updated <date> · Mode B · The compounding asset: proven hooks get reapplied to new bodies.

> **Every hook is a new claim shape.** A hook inherits nothing from the body's compliance clearance —
> lint each one (`scripts/claims_lint.py`) even when the body is unchanged. This is the most common
> failure of the modular system.

> **The ad name is the join key.** Every shipped variant is named
> `<BRAND>-<bodyID>-<hookID>-<personaID>-<variant>` on the platform — IDs matching this bank
> exactly — so metrics join back without hand-typing. Rules, waterfall and promotion floors:
> `references/performance-metrics.md`.

## Standing bank (promoted — beat the bank average, reuse freely)

| ID | Type | The line / beat (0:00–0:06) | The gap: don't know X · because Y | Persona fit | Hook rate (best) | Hold rate | Impressions | Runs ≥ floor | Lint |
|----|------|------------------------------|-----------------------------------|-------------|------------------|-----------|-------------|--------------|------|
| H01 | curiosity gap | <…> | <…> · because <…> | P1, P3 | <%> | <%> | <n> | 2 | clean |
| H02 | skeptic | <…> | <…> · because <…> | P2 | <%> | <%> | <n> | 2 | clean |

Hook rate = 3s views ÷ impressions (2s on TikTok — don't mix the two in one column). Hold rate =
ThruPlay ÷ 3s views. Promotion needs two runs above the impressions floor
(`performance-metrics.md` §3); one great week is one witness.

## In test (this batch)

| ID | Type | The line / beat | The gap: don't know X · because Y | Body | Persona | Ad name (join key) | Shipped | Hook rate / impr |
|----|------|-----------------|-----------------------------------|------|---------|--------------------|---------|------------------|
| H07 | POV | <…> | <…> · because <…> | B1 | P1 | <BRAND>-B1-H07-P1-a | <date> | pending |

## Retired (kept so nobody re-tests them)

| ID | Type | The line | Why retired |
|----|------|----------|-------------|
| H03 | PAS | <…> | underperformed twice · or: agitation drifted into a disease claim |

## Type coverage check (per `modes/ugc-volume.md` §5)

At least **4 distinct types** live in any month's batch. Current spread:

- [ ] curiosity gap · [ ] POV · [ ] mistake/correction · [ ] skeptic · [ ] problem–agitate–solution
- [ ] comparison · [ ] day-in-the-life · [ ] three things · [ ] unboxing · [ ] testimonial
- [ ] humour / pattern interrupt · [ ] serious / trust-building

**Tone pairing:** for any body being tested at two registers, note the paired hook IDs here —
one light, one serious, same body. That is the cheapest tone test available.

## Writing rules

*(Sourced in `references/hook-craft.md`; the first three are the ones the evidence moved.)*

- ⛔ **One concrete anchor, one withheld term.** Name something real enough to care about — a
  number, an object, a moment, a person — and withhold exactly one thing. Zero anchors is a mood;
  zero withheld is a summary. **"Make it more mysterious" is a direction, not a rule**: the
  concreteness/click relationship is curvilinear and turns over, so both ends are worse than the
  middle (§1).
- ⛔ **Fill the gap column before writing the line.** *They don't know `<X>` · because `<Y>`.* If
  `<Y>` is hard to write, the hook is hollow and no rewriting of the line fixes it — the missing leg
  is **importance**, and importance comes from the audience, not from the copy (§2).
  ⛔ **`<Y>` is a stake they already hold** — something they own, pay for, chose, or worry about —
  **never something they lack.** "Because nobody has told them" is the gap written twice; the test
  is whether they could have said `<Y>` about themselves yesterday, before your video existed.
  `scripts/develop.py` fails a bank whose rows have no gap, one half of a gap, or a "because" that
  just restates the line.
- **Brand late.** Early, long, persistent brand placement measurably hurt sharing of video ads
  (Tellis et al. 2019, §5). Keep the name and the logo out of 0:00–0:06 unless the client's own
  tested data says otherwise. `script_score.py --brand <name>` warns.
- **Test both halves of the curve.** A month of five indirect hooks tested one side of it. Ship at
  least one direct hook (offer, comparison, three things, testimonial, serious) even when you expect
  it to lose — that is what makes the bank evidence instead of a preference.
- Six seconds — the platform's number, not a measurement (§3). ⛔ Never cite the "3-second rule":
  it is Facebook's billing threshold and has no study behind it.
- Conflict, not demographic. "Are you a X?" is a filter that gives everyone else permission to leave.
- One idea. A hook with a clause is two hooks.
- Hedged language outperforms and is safer: "I don't know if it's placebo but—" beats "this changed my life".
- If it could open any brand's video, it isn't a hook yet.
- **Keep the promise modest.** The largest test of headline copy predicted the winner 54% of the
  time, and follower count beats every linguistic feature measured (§4). A hook bank is a way to
  lose less often; it is not a growth lever, and it should not be sold as one.
