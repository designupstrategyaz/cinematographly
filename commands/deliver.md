---
description: Build the upload-by-hand delivery folders, one per platform, once the export is approved
argument-hint: <platform> [<platform> …]
allowed-tools: Bash(python3:*)
---
The open job is in `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/gate.py" status`. For each platform in
$ARGUMENTS, run
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/deliver.py" <job> --platform <name> …`
(add `--title` and `--description` if the person gave them; `--master` if `10-export/` holds more than one master).

It is refused until `export` is approved. Each folder in `10-export/DELIVERY/<platform>/` holds the master (same bytes),
the newest captions, a cover frame and `delivery.json` with the AI-disclosure line. Nothing is posted: uploading is the
person's action. If `delivery.json` says the disclosure is not set, say so before they upload.

At job close, `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/gate.py" close` writes the scorecard
(`99-costs/SCORECARD.md`: yield, retakes, cost per kept take and second).
