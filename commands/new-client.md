---
description: Add a client — a short interview that writes their profile, ready for a first job
argument-hint: "[client name]"
allowed-tools: Bash(python3:*), Write
---
1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/new_client.py" questions` to see the questions and the studio's defaults.
2. Ask the person those questions in plain words, three or four at a time. Use their own words for the answers.
   The approver must be one real person's name: never a role, and never yourself.
3. Write their answers as JSON (keys as listed) to a temporary file, then run
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/new_client.py" make --answers <that file>`.
4. If it refuses, ask only about what it names, and run it again. It never overwrites an existing client.

Then suggest `/cinematographly:new-job <client> <slug>`. Also say that the rest of the profile (brand look, voices,
claims evidence) can be filled in over time.
