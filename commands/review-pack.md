---
description: Make a review page for a client to see a stage outside the chat (it never approves anything)
argument-hint: <stage> <file> [<file> …]
allowed-tools: Bash(python3:*)
---
The open job is in `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/gate.py" status`. Run
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/cinematographly/scripts/review_pack.py" make <job> <stage> --file <file> …`
with the stage and files from: $ARGUMENTS

Tell the person:
1. where the page is (`07-review/<stage>/<code>/index.html`) and that they send it however they like;
2. the client's reply is evidence, never the approval;
3. the approval is still the Approver's own sentence in this chat, and it must contain the 16-character pack code;
4. if any file in the pack changes, make a new pack and show it again: the old code is refused.

Record the approval only after the Approver writes it, with
`gate.py approve <stage> --pack <code> --by "<Approver>" --quote "<their exact words>"`. Never write the quote yourself.
