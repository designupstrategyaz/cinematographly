# Refreshing a client's cost profile

`clients/costs.<client>.json` is the **only** source of generation prices for that account.
`estimate_duration.py` refuses to quote without it and never borrows another client's numbers — a
wrong quote that looks authoritative is worse than no quote.

## Where the number actually comes from

**The Generate button in the app, for the exact configuration you will run.** That is what your
account will be charged, on your plan, at that resolution and duration. Everything else is worse:

| Source | Good for | Why it is not the answer |
|---|---|---|
| **Generate button (UI preflight)** | **the number you quote** | — |
| Transaction ledger | history; models missing from the card; the retake multiplier | tells you the past, not the config you are about to run |
| Published pricing page | rough comparison across models | **measured wrong twice**: Kling 3.0 1080p listed 7, charged 10; 720p listed 6, charged 8.75. **some roster models are not on it at all** |

⛔ **Never quote from the pricing page.** It is list pricing, it omits models this pipeline depends
on, and on 2026-08-29 it understated the two it did list by ~45%.

Also check, per model, before pricing a month: **free generations** and **unlimited mode**. They are
plan features that change the cost model rather than discounting it — and the platform states they
work only on the website, **not via MCP/CLI**, so a scripted batch pays for what a hand-run batch
gets free.

## Why these are measured, not looked up

**The generation platform publishes no per-model rate card through its API.** `models_explore`
returns capabilities (durations, resolutions, reference roles) and no price; the pricing surface is
a purchase widget for plans and credit packs, not a per-second table. So the honest source is what
your account was **actually billed**, which is also the number that matters for margin.

This makes the cost profile a *measurement with a date on it*, exactly like everything else the
skill treats as evidence (`research-quality.md`).

## The refresh

Run this in an environment with the generation MCP attached (Claude Code on the Mac, or a Cowork
session with it connected):

1. **Pull the ledger.** `transactions` for the period since the last refresh. If the account is
   shared across clients, filter to this client's generations by folder/project or by date range —
   and if you cannot separate them, say so in `_provenance` rather than pretending.
2. **Group by model and by shot type**, not just by model: a 5s dialogue clip at 1080p and a 5s
   B-roll clip at 720p are different line items even on the same model.
3. **Divide by seconds generated, including failures.** Retakes and rejected generations are real
   cost. A credits-per-second figure that excludes them understates every quote by the retake rate
   (`ai-generation.md`'s retake economics table has the multiplier).
4. **Cross-check against `shot_manifest.py report`** for the same period — the manifest's per-shot
   actuals and the platform's ledger should agree within a few percent. If they do not, the manifest
   has gaps and the discrepancy is worth more than the refresh.
5. **Write the file** with `last_verified` (ISO date) and `_provenance` (what you measured, over what
   period, and what you could not separate).

## Staleness

`estimate_duration.py` warns past **45 days** and warns loudly when `last_verified` is absent —
because an undated cost profile produces an ASSUMED number wearing a measured number's clothes, and
the verification readout (`pm-workflow.md`) exists to stop exactly that reaching a client.

Re-measure early when: the model roster changes, the plan or credit-pack tier changes, or a batch's
reconciliation misses the estimate by more than ~15%. That last one is the useful trigger — it comes
free from the reconciliation you already do at the end of a batch.

## Starting a new client

There is no bootstrap price. Run one real video, measure it, and quote the second one from that.
Until then every number in a proposal is **estimated**, labelled as such per the verification
readout, with the range stated rather than a single figure.

## ⛔ Where a rate lives once you have read it

`assets/higgsfield-rates.json` → **`rate_table`**, and nowhere else. `scripts/rate_card.py` reads
it; no reference, profile or script restates a rate. Rule 5 of the scripts charter: a number
hardcoded somewhere else is a bug with a delay on it.

Each entry carries `cr_per_s`, `list_cr_per_s` (the struck-through price beside the discounted one),
`min_s`/`max_s` from the model picker, the `measured` date, and the raw `readings` it was derived
from — so a later reader can check the arithmetic instead of trusting the rate.

**Two readings per model, at different durations.** One point cannot show linearity; two can. Every
model measured so far has been exactly linear, which is why the table stores cr/s and never a
per-clip price.

⛔ **The Generate button shows a promotional price.** Read the struck-through number too, and quote
a client at list unless the discount is contractually yours.

## Your own readings: `<studio>/rates-override.json` (3.1)

The rate card in `assets/higgsfield-rates.json` ships with the plugin and is replaced on every update. Put your own
readings in the studio folder instead. They survive updates, and each field you give replaces only that field:

```json
{
  "rate_table": {
    "kling3_0": { "1080p": { "cr_per_s": 1.75, "measured": "2026-11-16", "readings": "5s = 8.75 on the Generate button" } }
  },
  "image_rate_table": {
    "<image model>": { "2K": { "cr_per_image": 2, "measured": "2026-11-16", "readings": "1 image = 2" } }
  }
}
```

Give `measured` (the date you read it) every time: an undated or month-old rate is flagged by `doctor` and by every
quote. A malformed entry is ignored with a warning, never used. `rate_card.py lookup --model <m> --res <r> --seconds
<n>` shows the price it will quote.
