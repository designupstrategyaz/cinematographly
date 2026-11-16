# Approvals — the human sign-off ledger

Written only by `scripts/gate.py approve <stage> --by <name> --quote "<their words>" [--artifact
<file>] [--media-id <id>]`. The gate reads it before every generate_* call.

What a row must be: **the approver's reply, verbatim, after they saw the thing.** The agent asks
(AskUserQuestion / the client's review channel), the human answers, the answer is quoted here with
the exact file it approved and that file's hash. A row that paraphrases, or that quotes a reply
given before the artifact existed, is the lipsync incident in a new coat — the gate cannot detect
it, so the ledger keeps the timestamp and the hash so a later reader can.

Stages: `script` (needs --artifact, the locked script file) · `audio` (per-stage-human: the VO
before dialogue clips) · `frame:<SHOT>` (needs --artifact, the approved still, and --media-id, the
Higgsfield id the clip will bind) · `clips` (the selects pass) · `export`.

| ts | stage | by | quote | artifact | sha256 | media_id |
|---|---|---|---|---|---|---|
