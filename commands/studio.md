---
description: Answer the studio's questions — approvers, review policy, platforms, music and likeness, disclosure, and the production settings (monthly ceiling, regens, retake factor, second opinion)
allowed-tools: Bash(python3:*), Write
---
1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/studio.py" questions` to see what is asked and what is already answered.
2. Ask the person the unanswered questions in plain words, three or four at a time.
3. Write their answers as JSON to a temporary file and run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/studio.py" set --answers <that file>`.

Ask the four production settings as their own group, last: "Production settings: the defaults every job starts
from" (`monthly_credit_ceiling`, `default_regens`, `retake_factor`, `second_opinion`). Say that each one can only make
jobs stricter or pre-fill a number. If they don't want a ceiling, leave it out.

The answers pre-fill new clients and new jobs. They never set a job's budget, never approve anything and never clear a
check. Three answers add a stop: a studio "no" on music licence or likeness blocks an export, and the monthly ceiling
makes a person confirm each Higgsfield call past it. Setting or lowering the ceiling applies at once. Raising or
removing it needs the person's own words: add `--by "<their name>" --quote "<what they wrote>"` to `studio.py set`.
Never raise it on your own reading of a deadline.
