# PRODUCTION CHECKPOINT

> This file is the checkpoint. It used to be a paragraph the agent typed into the chat, which by the
> skill's own test ("what would it take to pass this fraudulently?") was not a check. Now it is a file
> that `scripts/gate.py open <job-dir>` validates before the job is allowed to generate anything, and
> that the PreToolUse hook re-validates before every Higgsfield generate_* call.

> Rules the validator applies: every line below must be filled — any `<placeholder>`, `NEEDS INPUT`
> or `TBD` refuses. `Client:` must name a profile that exists and whose section 0 is complete.
> `Policy:` must be one of per-stage-human / gated / standing and must agree with the profile.
> `Format:` must be a preset name from assets/delivery-formats.json. Every `Inputs:` item is tagged
> PRESENT or MISSING, and a MISSING one carries `(asked …)` or `(accepted risk: …)`. `Skips:` is
> `none` or each skip carries ` — <reason>`. `Budget:` carries a number in credits and a provenance
> tag — **exactly one of `[estimated]` `[measured]` `[assumed]`, in square brackets, on the same
> line as the number it qualifies** (a bare "610 cr" refuses, and so does "estimated 610 cr"
> without the brackets). Keep the `Key:` at the start of the line; indent continuation lines.
>
> `Client:` is resolved against `$CINE_CLIENTS` when that is set, and `<skill>/clients/` otherwise —
> a profile that lives elsewhere is an env var, not a reason to edit this line.
>
> Optional, for an EVALUATION job only: add `Tier: evaluation` and `Question: <the question, the
> arms, the rule that decides>` as two more lines. The job may then generate below the 1080p floor on
> roster models, and nothing it makes can be locked, exported or filed outside `_eval/`
> (references/ai-generation.md, the evaluation tier). Leave both out for a production job.
> Add `Lane: eval` too (v2.72.0) when the question needs no concept or script: one approved plan,
> `00-brief/EVAL-PLAN.md` from assets/eval-plan-template.md (`gate.py approve eval`), stands in for them,
> and the gate holds every call to the plan's shots, takes and budget. Speech, previz and Kling stay out.
>
> Optional, for any job: `Switches:` lifts a named house rule for THIS job only (v2.48.0, project
> switches). `none`, or no line at all, means every house rule holds. Each item is `<id> — <reason>`,
> items separated by `;`, continuation lines indented. The id must be one in
> assets/project-switches.json (`python3 scripts/switches.py list` prints them, with what each lifts
> and what still holds); the reason says why, in at least three words. An unknown id refuses, and so
> does an id with no reason. The locked rules are never switches — no roto or advanced VFX, no AI
> images as references, no spend without approval, native Resolve titles, English, a contact sheet
> before any draft, never picking music, no Higgsfield motion_control — and writing one refuses with
> the rule it would break. A switch changes nothing at the spend gate.
>
> Optional, for a team (3.1): `Producer:`, `Editor:` and `Reviewer:` lines name who does what; `gate.py
> status` shows them. They are information only: none of them can approve. Only the `Approver:` does,
> in their own words. Leave them out and the job reads exactly as before.
Job:        <showid-slug, e.g. acme-01001-spring-service>
Mode:       <A/B/C/D/S> — <one line why; a trial batch is B even when the number is small; S = stills only, needs Format: stills>
Client:     <clients/brand.md>
Policy:     <per-stage-human | gated | standing — copied from the profile section 0>
Format:     <preset, e.g. vertical-1080> (master) · derived: <preset or none>
            generation: <the resolution regime — 1080p minimum, the tier per model>
Voice:      <voice profile loaded BEFORE drafting, or: none — house register, flagged>
Inputs:     approved-language <PRESENT|MISSING (…)> · archive+licensing <PRESENT|MISSING (…)> ·
            personas <PRESENT|MISSING (…)> · brand assets <PRESENT|MISSING (…)> ·
            music library <PRESENT|MISSING (…)> · spend context <PRESENT|MISSING (…)> ·
            reference images <PRESENT|MISSING (…)>
Gates:      ideation kill tests → script scorecard + claims lint → blocking cards → frame gate →
            prompt lint → QA card + selects → compliance → slop/export QC → verification readout
Skips:      none
Switches:   none
Budget:     envelope <N> cr (<who set it>) · estimate <N> cr [estimated] · preflight <99-costs/PREFLIGHT-YYYY-MM-DD.md>
Approver:   <the named human who approves each stage — never "the client">
Next:       <the specific first action>
