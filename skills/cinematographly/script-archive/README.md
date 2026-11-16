# script-archive/

Every script that has been produced with this skill, kept as flat markdown.

## Why it exists

**Reproducibility.** "Make it like the one from March" needs the March script, not a memory of it.
The project folder is the file-of-record while a video is in production; this archive is what
survives after the project folder is tidied, a laptop is replaced, or a client folder is handed over.

It is also the corpus the writing craft is calibrated against: `script_score.py`'s dimensions are
only meaningful next to scripts that actually shipped, and `references/script-craft.md` §6 assumes
you can look at a past one.

## What goes here

- The **final approved** script for every shipped video — the version the VO was recorded from.
- Nothing else. Not drafts, not variants, not the shotlist, not the prompt file.
  ⛔ A folder of near-identical drafts is not an archive; it is a place nobody looks twice.

## Naming

Same grammar as everything else (`references/pm-workflow.md` § Naming convention):

```
<showid>-<slug>.md          acme-01007-city-intro.md
```

One file per episode. ⛔ **Never rename one after it lands** — a shipped script is a record, and its
name is how the shot manifest, the cost ledger and the episode registry point at it.

## How it relates to the rest

| | Holds | Lifetime |
|---|---|---|
| `<project>/01-script/` | the working drafts, `SCRIPT-<SLUG>-v<N>.md` | until the project is archived |
| `script-archive/` | the one approved final, per episode | permanent |
| `_series/<BRAND>/EPISODES.md` | the row that names it | permanent |

`references/self-evolution.md` reads this folder when a production lesson needs a real example
rather than a remembered one.
