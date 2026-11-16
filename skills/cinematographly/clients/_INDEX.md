# Client routing index

Which client profile to load, by trigger. Keeping the routing here (not hardcoded in `SKILL.md`)
means adding a client is a table row + two files, never a core-skill edit.

**This folder holds no real client.** Your clients live in your own client folder: the folder
`CINE_CLIENTS` names, or a `_cine-clients/` folder above your jobs. Keep a routing table like this
one there (`_INDEX.md`) and read it first; `gate.py`, the claims lint and the planning tools look
in that folder before this one (`scripts/client_files.py` has the order). A plugin update
replaces this folder.

| If the task mentions… | Load profile | Costs file | Status |
|---|---|---|---|
| Acme · Acme Cycle Works · trying the pipeline on a fresh install · "show me a filled-in profile" | `clients/acme.md` | `clients/costs.acme.json` | **sample** — an invented bicycle repair shop, NOT a client. Section 0 is complete, so the gate opens a job under it; its cost and script numbers are not measured. Copy the shape, never the answers |

| Calibrating the skill itself — a prompt test, a model bake-off, "does the model actually obey X" | `clients/_lab.md` | none (each job prices its own envelope with `rate_card.py`) | **live** — ⚡ the internal test bench. NOT a client: nothing generated under it ships, so §0's answers are questions that do not arise rather than questions skipped. A calibration test runs through the gate like any other job (`prompting-craft.md` §13). |

**No match?** Ask the user which brand, then copy `clients/_TEMPLATE.md` to `<brand>.md` in your own
client folder (plus `costs.<brand>.json` and `script.<brand>.json`) and add a row to that folder's
index. The general skill (`SKILL.md` + `modes/` + `references/`) is brand-agnostic; only the profiles
carry brand specifics.
An empty match means *ask*, never *assume* — and since 2026-09-06 it also means **nothing generates**:
`scripts/gate.py open` refuses a job whose `Client:` line points at no profile.

**Every profile must declare, up front (section 0):** its default **mode** (`modes/_INDEX.md`), its
**⛔ hard locks**, its **verification policy** on the exact line `**Verification policy:** \`value\``
(parsed by `gate.py`), its **approved-language / compliance posture**, and its **distribution
platforms**. A profile missing them will produce confidently wrong work — which is why the gate reads
section 0 before it opens anything.
