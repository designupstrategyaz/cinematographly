# Proposals

`consolidate.py` writes a dated folder per pass into `proposals/` in your own history folder (see
`memory/README.md`), never into the plugin: `MANIFEST.json` (the episode list plus a content
hash of every skill file at read time), `EVIDENCE.md` (the grouped observations with witness counts),
and `PROMPT.md` (the consolidation brief). You or a model then draft `PROPOSAL.md` and
`proposal.diff` alongside them.

**Nothing here has been applied.** `evaluate_promotion.py <folder>` runs the mechanical gates —
freshness, cross-references, surface budget, client hard locks, evidence, eval-set isolation — and a
human reads the diff before anything lands. See `references/self-evolution.md` §4.

A proposal whose freshness gate fails is stale: the skill moved after the pass read it. Re-run
`consolidate.py` rather than forcing it through.
