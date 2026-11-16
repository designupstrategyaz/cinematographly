---
description: Show or name which claude.ai connector is your Higgsfield account (and which are other services)
argument-hint: "[--higgsfield <id>] [--other <id> --quote \"<the person's words>\"] [--seen]"
disable-model-invocation: true
---
Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/gate.py" connectors $ARGUMENTS` and show what it prints.

- With no arguments it shows the current settings. `--seen` adds connectors the gate asked about but nobody named.
- `--higgsfield <id>` names your Higgsfield connector: its paid calls are then gated like any Higgsfield call.
- `--other <id> --quote "<words>"` names another service (for example Figma). That lets its generate tools through
  with no gate and no budget count, so the gate refuses it unless the quote is the person's own words, typed earlier in
  this session, naming the connector (its first 8 characters). For example, the person first writes in the chat
  "1a2b3c4d is Figma", then types `/cinematographly:connectors --other <id> --quote "1a2b3c4d is Figma"`. Words that
  only appear inside the command itself do not count.
  A connector already seen serving a tool only Higgsfield serves is always refused as `--other`. A hookless (Cowork)
  home cannot name one: there is no transcript to check the words against.
- The settings live in `connectors.json` in the plugin's home folder; editing that file by hand, or the
  `CINE_OTHER_CONNECTORS` / `CINE_HIGGSFIELD_CONNECTORS` environment variables, skip these checks (README, "What the
  checks do not cover").
- The id is the part after `mcp__` in the connector's tool names (`mcp__<id>__generate_image`).

Only run this when the person typed the command. Never name a connector on your own reading of a tool list.
