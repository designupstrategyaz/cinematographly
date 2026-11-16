# Evaluation plan

One question, answered before anyone argues about it. Nothing this job makes ships. The gate binds the four lines
marked ⛔ at every call: a shot not listed, a take past the count or a credit past the budget is refused.

⛔ Question: <the same sentence as the checkpoint's Question: line>
⛔ Shots: <the prompt files' shot IDs, comma-separated, e.g. B2cA, B2cB>
⛔ Takes per shot: <1–8>
⛔ Budget: <credits, from rate_card.py or a get_cost probe; at most the checkpoint envelope>

Arms: <A: what it is · B: what it is (one arm is fine for a single-prompt question)>
Variable: <the one thing that differs between the arms>
Held fixed: <model, resolution, duration, the start frame, seeds>
Decision rule: <what result picks which arm, and what result decides nothing (four takes show only a large gap)>
Judging: <blind (genlab.py ab sheet), usable or not, by whom>

The approval: `gate.py approve eval --by <name> --quote "<their words>" --artifact 00-brief/EVAL-PLAN.md`, before any
generation. Until the first generation a new approval replaces the old one; after it the plan is fixed.
