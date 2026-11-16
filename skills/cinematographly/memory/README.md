# `memory/` in the plugin: templates only

A studio's history is its own. It names clients, jobs and people, so it never ships with the plugin,
and a plugin update replaces this folder.

**Your history lives in a folder of yours:** the folder `CINE_MEMORY` names, or a `_cine-memory/`
folder above your jobs. `python3 scripts/memory_home.py init` creates one with the templates below
and an empty ledger; `python3 scripts/memory_home.py where` prints the one in use.

| In your history folder | What it is |
|---|---|
| `episodes/<date>-<slug>.md` | The close-out note for a job: what broke, what fixed it. Template: `episodes/_TEMPLATE.md` here |
| `episodes/_promoted/` | Notes whose lesson has landed |
| `proposals/<date>/` | Proposed rule changes, written by `scripts/consolidate.py` and gated by `scripts/evaluate_promotion.py` |
| `LEDGER.md` | Your ledger: one line per change that landed, with its evidence |

Where the rules say `memory/...`, read it as a path in that folder. `scripts/skill_audit.py` checks
those pointers against your folder when it finds one, and says how many it could not check when it
does not.

What changed in the plugin itself, version by version, is in `CHANGELOG.md` at the skill's root.
`references/self-evolution.md` describes the loop.
