---
description: Make your studio folder (clients, history, jobs) and tell every Cinematographly tool where it is
argument-hint: "[studio folder] [--install-deps] [--hookless | --hooked]"
allowed-tools: Bash(python3:*)
---
Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/studio_setup.py" $ARGUMENTS` and show the person what it made and what it kept.

It never overwrites a file. With no folder given it uses the configured studio, else `~/Cinematographly`.
`--install-deps` installs the picture and sound check packages (numpy, OpenCV, Pillow): run it only when the person
asked for it. A concept and a script need none of them.

Then offer `/cinematographly:studio` (the studio's questions) and suggest `/cinematographly:doctor`.
