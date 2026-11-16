---
description: Check this machine for Cinematographly — what a first concept needs, then what later steps need
allowed-tools: Bash(python3:*)
---
Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/doctor.py"` and show its report as it is.

Explain each RED line and its fix in one sentence. AMBER lines can wait until the step that needs them; say which
step. Doctor only reads: do not install, uninstall, enable or edit anything on the person's behalf unless they ask.
