---
description: Start a job — the folder layout and a checkpoint the spend gate accepts, then open it
argument-hint: "<client> <slug> [--mode A|B|C|D|S] [--approver \"Name\"] [--format PRESET]"
allowed-tools: Bash(python3:*)
---
Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/new_job.py" $ARGUMENTS`.

- `<client>` is a profile name (`acme` is the sample). `<slug>` is short, lower-case, with hyphens.
- If it says the approver must be a person's name, ask the person who approves the work and re-run with
  `--approver "Their Name"`. Never invent a name.
- The job opens for a concept only: no inputs yet, a budget of 0 credits, nothing priced. Every paid generation is refused until a budget is set; other paid tools ask first.

Then run `/cinematographly:next` and start the development step it names.
