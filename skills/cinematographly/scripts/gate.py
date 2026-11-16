#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""gate.py — the production gate. A job is a folder with a VALIDATED checkpoint, an APPROVALS ledger
and LINTED prompts, and nothing generates outside one.

Why this exists (2026-09-06). The skill's checkpoint was a paragraph the agent typed, its "required
reads" were a menu, and its approval policy lived in a client profile that did not exist. By the
skill's own test — "ask what it would take to pass a check fraudulently; if the answer is nothing, it
is not a check" — none of them were checks, and a run produced random generations, burned credits
and had no process. This script is the check. It is deterministic (no LLM in the audit body), it
reads files the agent cannot satisfy by narration, and the PreToolUse hook calls it before every
Higgsfield tool call and every DaVinci Resolve MCP call (`decide_resolve`).

  open <job-dir>                   validate 00-brief/CHECKPOINT.md + the client profile; register
                                   the job as ACTIVE. Refuses (exit 1) with the exact lines to fix.
                                   (v2.48.0) Prints the project switches: the house rules the optional
                                   `Switches:` line lifts for this job, each with its reason.
  status [--json] [--full]         the active job: policy, approvals, linted prompts, what the next
                                   generate call still needs. Fast by default (hashes, a size/mtime
                                   cache); --full re-lints every prompt. Preflight always re-lints.
  pre-lock [--write] [--host-job P] the cut, titles-off and picture-only renders as filled
                                   render-mp4.py copies (07-edit/_queue/), and what lock still needs
  where                            this install's scripts, skill, clients and state folders
  approve <stage> --by NAME --quote "<verbatim reply>" [--artifact PATH] [--media-id ID]
                                   record a human approval. The chain, in order: concept · script ·
                                   storyboard (v2.66.0) · cast (one cross-shot sign-off; each
                                   character:<NAME> is its own) · frame:<SHOT> · startframes (v2.66.0) ·
                                   audio · clips · music ·
                                   lock (picture lock) · export — `approve` refuses out of order.
                                   `concept` and `script` additionally run develop.py: no script is
                                   signed without sourced research, five genuinely different
                                   concepts, adversarial rounds that killed something, the human's
                                   pick, a hook bank and drafts with critiques between them.
                                   script needs --artifact (the locked script file);
                                   storyboard and startframes (jobs from the 2.65 development template
                                   on) take no --artifact: the gate records the shot list, or the frame
                                   sheet, and refuses while storyboard.py says either is not ready —
                                   the page and the animatic built from THIS shot list, a sketch of the
                                   person's or their quoted skip; every approved frame on the sheet.
                                   A clip waits for a startframes sign-off newer than its frame
                                   (references/storyboarding.md §6).
                                   frame:<SHOT> needs --artifact (the approved still, under the job)
                                   and --media-id (the Higgsfield media/job id the clip will bind).
                                   blocking:<SHOT> needs --artifact (the build's
                                   .blocking.manifest.json, every file still matching its hash) and,
                                   before the clip runs, --media-id (the uploaded MP4) — a clip that
                                   declares a `what: blocking` reference is refused without it
                                   (references/blocking.md §7).
                                   target:<SHOT> (v2.45) is the per-shot opt-in
                                   that lets an AI edit of our own footage (`kind: edit`, `use: target`)
                                   become a model reference; --artifact names the source picture it edits.
                                   When a session transcript is known (the hook records it), the
                                   quote must appear in a HUMAN turn of that transcript.
                                   STILLS (Mode S, Format `stills`): the chain is brief · frame:<ID> ·
                                   export. `brief` needs --artifact (sha recorded, no develop.py) and
                                   replaces concept → script; generate_image needs it plus a linted
                                   <ID>.frame.prompt.md whose ID the brief names; video/audio DENIED.
  preflight <SHOT> --kind frame|clip|edit [--json]
                                   print the ready-to-paste generate_* params for a linted prompt —
                                   the gated path is meant to be LESS work than a hand-written call
  hook                             PreToolUse entrypoint: tool-call JSON on stdin → decision JSON
  posthook                         PostToolUse entrypoint: logs a generate request the vendor accepted, by its
                                   hash and returned job id — what the duplicate-spend guard reads (v2.45)
  session                          SessionStart entrypoint: records the transcript path, prints
                                   additionalContext with the job state
  reconcile TRANSACTIONS.json      post-hoc: every generation that had no linted prompt behind it —
                                   the credit-waste report (input: Higgsfield `transactions` output)
  close                            clear the active job

Exit codes: 0 pass/done · 1 refused/findings · 2 usage/IO error.

What it checks before a Higgsfield call (all environments; the hook only makes it automatic)
-------------------------------------------------------------------------------------------
  - a job is ACTIVE (opened < 24 h ago) and its CHECKPOINT.md still validates (client profile
    present, its section 0 complete, verification policy one of per-stage-human/gated/standing,
    format preset real, inputs tagged PRESENT/MISSING, skips reasoned, budget provenance-labelled,
    approver named)
  - `script` is approved (all policies — the review that saves the most money), which in turn
    required `concept` and a complete 00-brief/DEVELOPMENT.md (scripts/develop.py)
  - generate_image / generate_video: the prompt text is identical (after whitespace / curly-quote /
    dash normalisation) to a prompt file that prompt_lint.py passes RIGHT NOW — the lint is re-run
    at hook time and the .ok sidecar is only a cache, so a hand-written sidecar buys nothing —
    and the model, duration, aspect, count and resolution match that file; no undeclared params
  - generate_video: the shot's start frame is approved (`frame:<SHOT>`), the call binds that
    frame's media id in an image-class role, and the still on disk is the still that was approved
  - generate_audio: the text EQUALS one spoken line of the approved script (speaker tags stripped),
    the model is a speech model, a voice_id is set
  - under per-stage-human: `audio` approved before a dialogue clip, and every spend is "ask" — unless
    an allowance covers it (`gate.py allow image|video --shots … --by … --quote …`: one approval in chat
    for a batch of shots plus 2 regens each by default; a covered call is still linted, and goes
    through pre-approved, under any policy)
  - other credit-spending Higgsfield tools (upscale, dubbing, voice cloning, apps…):
    denied without a job, "ask" inside one; publishing needs the `export` approval
  - (v2.45) NO UNLINTED ROUTE: Kling's own connector (text_to_image, image_to_image, text_to_video,
    image_to_video, omni_ref_video, motion_control) must carry a prompt identical to a linted prompt of the
    right kind for a Kling model — denied otherwise, "ask" when it matches; Higgsfield's motion_control takes
    no prompt and is denied. Uploads and identity elements (Kling file_upload/element_create, Higgsfield
    media_upload/manage_reference_elements create) are denied without a job and "ask" inside one. Any
    Scenario MCP run or upload is DENIED always: Scenario is not a provider this plugin uses
  - (v2.45) an image edit (`kind: edit`) binds its source picture; `use: target` needs `target:<SHOT>`
  - (v2.45) a request identical to one this job already submitted in the last 30 minutes asks first,
    naming the job to poll instead (the PostToolUse hook records submissions)
  - `get_cost: true` probes are allowed once a job is open (they spend nothing)
  - on PASS the hook does NOT pre-approve the call: it adds context and leaves the normal permission
    flow in place, so whatever prompt the operator's settings would show is still shown

The trust boundary — read this before relying on the gate
-----------------------------------------------------------
The gate holds against an agent that follows the rules and against honest mistakes. It does not
hold against an agent that edits gate.py, hooks.json or the ledger — same-user write access makes
that a one-line command, and no secret can be hidden from a process running as the same user. The
checks on THAT are outside this script: the Bash permission prompt in non-auto sessions, `git diff`
on the skill folder, `skill_audit.py` (which fails when a hook path does not resolve), and
`reconcile` against the platform's own transaction log, which the agent cannot edit.

What it cannot do
-----------------
- It cannot prove --quote is what the human said. Where the hook has recorded the session
  transcript it refuses a quote that appears in no human turn; elsewhere it records the quote as
  UNVERIFIED and the ledger keeps the timestamp and the file hash so a later reader can check.
- It cannot judge whether a prompt is GOOD — prompt_lint.py checks shape and the vendor-documented
  errors; craft is the reference files' job.
- It cannot fire without the hook. Where hooks do not run (some Cowork sessions), SKILL.md makes
  `gate.py preflight` the only sanctioned way to build a call, and `reconcile` catches what slipped
  past afterwards.
- It fails CLOSED. A spend gate that fails open is no gate; an internal error, an unreadable stdin
  or a call with no tool name denies with the reason. This is a deliberate deviation from the
  hook-authoring rule "never block unexpectedly". CINE_GATE=off in the shell that LAUNCHED the
  session bypasses it, and every bypass is written to $CINE_HOME/bypass.log.
- (v2.52.4) That promise only covers errors this file can catch. A failure BEFORE `cmd_hook` runs — a
  module imported at the top missing, this file cut off half way, no python3 on the hook's PATH — exits
  1 or 127, and Claude Code lets the call proceed on any exit other than 0 or 2. hooks/hooks.json closes
  that from outside: `onFailure: "block"` on the four gate entries, and a `|| { …; exit 2; }` tail on the
  command. test_gate.py's fail-closed section runs those exact command strings against a broken copy.
- One active job per CINE_HOME. Two sessions on one machine share it; `close` in one denies the
  other. Set CINE_HOME per session if that bites.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, subprocess, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import job_tier  # noqa: E402  the evaluation tier — one module answers it for every tool
import switches  # noqa: E402  (v2.48.0, project switches) the `Switches:` line — one parser for the gate and every script
SKILL_ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(SKILL_ROOT, "assets")
# The plugin's clients/ holds only templates and the sample. A studio's profiles live outside the plugin,
# because an update replaces that folder: CINE_CLIENTS=<your studio folder>/_cine-clients
import cine_home as _cine_home  # noqa: E402  (3.0.0) one home for every script: ~/.cinematographly, merged once
CINE_HOME = _cine_home.home(merge=False)   # the merge from ~/.cinematographly runs in main(), never on import or in tests
# (3.0.0) client profiles: CINE_CLIENTS, else `clients_dir` in ~/.cinematographly/config.json (setup.py), else the plugin's
CLIENTS = (os.environ.get("CINE_CLIENTS") or _cine_home.config_dir("clients_dir", CINE_HOME)
           or os.path.join(SKILL_ROOT, "clients"))
_P = _cine_home.paths(CINE_HOME)              # (3.0.0) the three paths from one function
ACTIVE_FILE, TRANSCRIPT_FILE = _P["active"], _P["transcript"]
ACTIVE_MAX_AGE_S = 24 * 3600
POLICIES = ("per-stage-human", "gated", "standing")
# The stage chain, in production order. frame:<SHOT> and character:<NAME> sit between script and
# clips. Each stage names what must be approved before it — `approve` refuses out of order, because
# a pipeline whose stages can be signed in any order is a list of words, not a pipeline.
# `titles` (2026-10-26: the title card is the permission list, C3): after picture lock, every title the
# card permits is rendered and passes title_qa.py on the composite before export.
# `storyboard` and `startframes` (v2.66.0, author: "Start Wave 2", 2026-11-14): the film signed as pictures in time
# before any paid picture, and the approved start frames signed side by side before their clips. Both are part of
# the chain only for jobs made from the 2.65 development template or later (storyboard.required); an older job in
# production keeps its chain and sees them as optional.
STAGES = ("concept", "script", "storyboard", "cast", "startframes", "audio", "clips", "music", "lock", "titles",
          "export")
PICTURE_SIGNOFFS = ("storyboard", "startframes")
REQUIRES = {"script": ["concept"], "storyboard": ["script"], "startframes": ["storyboard"],
            "audio": ["script"], "clips": ["script"],
            "music": ["script"], "lock": ["clips"], "titles": ["lock"], "export": ["lock", "music", "titles"]}
# ⚡ THE STILLS LANE — Mode S (2026-10-06, approved by the owner). Website and marketing stills have no
# concept round, no script, no voice and no cut, so the video chain above cannot be satisfied for
# them honestly — and a gate that can only be passed by writing a fake script is a gate that
# teaches people to write fake scripts. Mode S replaces concept → script with ONE human approval,
# `brief` (an artifact under the job, sha recorded, quote checked against the transcript like any
# other), and allows exactly three stages: brief · frame:<ID> · export. Everything that makes a
# generate_image call safe is UNCHANGED: a validated checkpoint, a prompt identical to a
# <ID>.frame.prompt.md that prompt_lint.py passes right now, model / count / resolution / negative /
# aspect read from that file. What Mode S adds is stricter, not looser: the ID must be named in the
# approved brief, the brief must be the bytes that were approved, and every media on the call must
# be a reference the linted file declares. Video and audio are DENIED in a stills job.
STILLS_STAGES = ("brief", "export")          # plus frame:<ID>
STILLS_FORMAT = "stills"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".avif")
# ⛔ THE SERVER SEGMENT IS NOT ALWAYS THE SERVER (2026-09-17). Every one of these patterns was
# written against the tool name as it appears when the MCP server is connected DIRECTLY
# (`mcp__Higgsfield__generate_image`). A server reached through a proxy carries the proxy's name
# first — in Cowork the user's locally-installed servers arrive as
# `mcp__remote-devices__<server>__<tool>` — and `[A-Za-z0-9_]+` cannot even cross the hyphen in
# `remote-devices`. So the gate went blind exactly where a human is least able to check it:
# the same tool, same spend, routed one layer differently. `SERVER` accepts an optional proxy
# segment and hyphens. Widening a gate's matcher can only gate MORE calls, never fewer.
SERVER = r"(?:[A-Za-z0-9_-]+__)?"
# A claude.ai connector, as the Claude desktop app serves it: `mcp__<connector uuid>__<tool>`. The uuid is the
# account's, not the vendor's, so it cannot be written into the plugin (v2.59.0). hooks/hooks.json fires on ANY such
# connector for the tools this gate decides on (CONNECTOR_MATCHER below); which uuid is the studio's Higgsfield
# account is a SETTING: `gate.py connectors` (stored in $CINE_HOME/connectors.json), or the comma-separated env
# vars CINE_HIGGSFIELD_CONNECTORS / CINE_OTHER_CONNECTORS. A connector named in neither ASKS: the gate cannot tell
# a paid Higgsfield call from another service's tool of the same name (Figma's connector serves a generate_image).
UUID_SRC = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"   # (v2.61.0) either case
CONNECTOR_UUID_RE = re.compile(r"^mcp__(" + UUID_SRC + r")__")
CONNECTORS_FILE = "connectors.json"
# Made-up uuids for the selftests: a connector the settings name as Higgsfield, and one they name as another service.
SAMPLE_CONNECTOR = "0a0a0a0a-0000-4000-8000-000000000001"
SAMPLE_OTHER = "0b0b0b0b-0000-4000-8000-000000000002"
TOOL_RE = re.compile(r"^mcp__" + SERVER + r"[A-Za-z0-9_-]+__generate_(image|video|audio)(_batch)?$")
# Credit-spending tools that carry no prompt the lint can hash: allowed only inside an open job, and
# always "ask" — the human confirms a spend the gate cannot read.
SPEND_RE = re.compile(r"^mcp__" + SERVER + r"[A-Za-z0-9_-]+__(animation_actions|apps_invoke|create_voice|"
                      r"create_voice_from_confirmed_audio|dubbing|generate_3d|motion_control|"
                      r"outpaint_image|remove_background|reframe|shorts_studio_create|upscale_image|"
                      r"upscale_video|voice_change|personal_clipper_create|video_analysis_create|"
                      r"ads_studio_generate|ai_influencer_generate|build_ai_influencer|execute_preset|"
                      r"shorts_studio_create_preset|scene_builder_3d_generate_angles|relight_image|"
                      r"virality_predictor|get_katana_config|"
                      # Kling's own API (the Kling_AI connector, 2026-10-26): every job is charged and
                      # none carries the `params` the generate path lints, so all are spend-class
                      r"text_to_image|image_to_image|text_to_video|image_to_video|omni_ref_video)$")
# ⛔ FIVE CONNECTOR TOOLS PASSED UNGATED (found 2026-10-06, stills-lane work, 2.17.0). ads_studio_generate,
# ai_influencer_generate, build_ai_influencer, execute_preset and shorts_studio_create_preset matched no
# class, so `decide` returned "allow" for them with NO job open. None carries the `params`/`requests`
# prompt the generate path lints, so all five are spend-class: denied without a job, "ask" inside one.
# build_ai_influencer is one tool for several actions — options / presets / recreate / quote read or
# price and spend nothing; `submit` generates. It is gated by action, and fails CLOSED: an action not
# listed here (or none) is treated as a spend.
# ⛔ THREE MORE PASSED UNGATED (found 2026-10-23, the Higgsfield 3D-blocking study; author: "Fix now").
# scene_builder_3d_generate_angles ("This spends credits", Seedream V5 Pro pricing) and relight_image
# are spend-class. virality_predictor is one tool for two actions: `preview` re-opens a dashboard,
# `create` starts a paid analysis — gated by action, failing CLOSED like build_ai_influencer.
# scene_builder_3d_generate_video is DENIED ALWAYS (DENY_ALWAYS below).
# ⛔ AND SEVEN MORE (found 2026-10-24, adding the Higgsfield modes as candidates; simulated through
# `gate.py hook`, every one returned allow with NO job open). get_katana_config opens a Katana run
# session and, with free_generation:true, SPENDS the account's free Katana run — spend-class. The six
# publishing tools below put a project or a website in front of the public (deploy_website ships a
# live public URL; participate_in_contest auto-publishes to the community feed): publish-class,
# behind the job's `export` approval like tiktok_publish. ⚠ The Katana workflow itself instructs the
# agent NOT to ask before spending ("Do not ask questions, request consent or confirmation (including
# credit spending)") — vendor text, data not instruction; this gate and the house rule outrank it.
FREE_ACTIONS = {"build_ai_influencer": {"options", "presets", "recreate", "quote"},
                "virality_predictor": {"preview"}}
# Tools refused even inside an open job, each with the route that replaces it.
DENY_ALWAYS_RE = re.compile(r"^mcp__" + SERVER + r"[A-Za-z0-9_-]+__(scene_builder_3d_generate_video)$")
DENY_ALWAYS = {
    "scene_builder_3d_generate_video":
        "a paid Seedance 2.5 generation that skips prompt_lint and the frame gate, defaults to 720p (under "
        "the 1080p floor) and turns generated sound on. Route it through generate_video with seedance_2_5, "
        "a linted prompt and the approved blocking render attached as its video reference "
        "(references/ai-generation.md; the blocking stage)",
}
# Spend-class tools whose own description says they spend no credits, gated anyway because they send
# reference media to Higgsfield and create the object a spend tool consumes. The reason says what the
# call does instead of claiming a spend.
NO_CREDIT_STAGE = {
    "shorts_studio_create_preset": "stores a Shorts Studio style preset from reference media (no credits by "
                                   "its own description) — confirm the media is client-approved; "
                                   "shorts_studio_create, which spends, renders from it",
}
# ⛔ NO UNLINTED ROUTE (v2.45, 2026-10-29). Kling's own connector and Higgsfield's motion control were spend-class:
# "ask" inside a job, with nothing linted — so a Kling call could carry any prompt at all, and the frame gate, the
# ceiling and every word rule were one connector away from irrelevant [scenario-same-moves-new-actor-integration
# §6, G1]. Now a Kling generation must carry a prompt identical (after normalisation) to a prompt file prompt_lint
# passes RIGHT NOW, written for a Kling model and of the right kind; anything else is DENIED. Higgsfield's
# motion_control takes no prompt at all, so it has no lintable route and is denied (house decision M3 open).
KLING_RE = re.compile(r"^mcp__" + SERVER + r"[Kk]ling(?:[-_][A-Za-z0-9]+)*__(.+)$")
KLING_IMAGE_TOOLS = {"text_to_image", "image_to_image"}
KLING_VIDEO_TOOLS = {"text_to_video", "image_to_video", "omni_ref_video", "motion_control"}
KLING_ROUTE = KLING_IMAGE_TOOLS | KLING_VIDEO_TOOLS
KLING_VOLATILE = ("rationale", "taskTraceId")          # free text and a fresh UUID per call: not the request
# ⛔ MEDIA LEAVES THE MACHINE ONLY INSIDE A JOB (v2.45). Kling's file_upload and element_create and Higgsfield's
# media_upload and manage_reference_elements(create) passed with NO job open — and an identity element is exactly
# where a face goes to a vendor as a reusable subject [same note, G2/R5]. Denied without a job, "ask" inside one.
UPLOAD_TOOLS = {"file_upload", "media_upload", "media_upload_widget", "media_import_url"}
IDENTITY_TOOLS = {"element_create", "element_update"}
UPLOAD_RE = re.compile(r"^mcp__" + SERVER + r"[A-Za-z0-9_-]+__(" + "|".join(sorted(UPLOAD_TOOLS | IDENTITY_TOOLS)) +
                       r"|manage_reference_elements)$")
REF_ELEMENT_READS = {"list", "get"}
# ⛔ SCENARIO IS NOT A PROVIDER (2026-10-28). Its MCP spends through `model_run` and sends media through
# `upload_asset`, and no hook matched it, so both ran ungated [scenario-alter-integration §5.6]. Any server whose
# name contains "scenario", in any case, behind any proxy segment and with any suffix: a run, a generation, a
# training or an upload is DENIED, inside a job or out. Reading (search, schemas, listings) passes.
SCENARIO_RE = re.compile(r"^mcp__(?:[A-Za-z0-9_-]+__)?[A-Za-z0-9_-]*?scenario[A-Za-z0-9_-]*?__(.+)$", re.I)
SCENARIO_DENY_RE = re.compile(r"^(?:model_run|upload_asset\w*)$|generat|train|run$|upload", re.I)
SCENARIO_WHY = "Scenario is not a provider this plugin uses"
# ⛔ A RESUBMIT IS PAID TWICE (v2.45; Scenario error E11: "a timeout resubmitted = paid twice"). Every generate
# request that reaches the vendor is logged by its hash (the PostToolUse hook, `gate.py posthook`); an identical
# request in the same job within this window asks first, naming the job to poll instead.
DUP_WINDOW_S = 30 * 60
# Publishing is shipping: it needs the job's `export` approval, then the human confirms.
PUBLISH_RE = re.compile(r"^mcp__" + SERVER + r"[A-Za-z0-9_-]+__(tiktok_publish|tiktok_prepare_publish|"
                        r"publish_project|publish_website|deploy_website|participate_in_contest|"
                        r"confirm_project_publication_review|update_project_publication)$")


def _alternatives(rx: "re.Pattern") -> list:
    """The tool names in the last `(a|b|c)` group of one of the class patterns above."""
    m = re.search(r"__\(([^()]*)\)(?:\(_batch\)\?)?\$$", rx.pattern)
    return m.group(1).split("|") if m else []


def class_names() -> set:
    """Every tool name the gate's spend, publish, deny and upload classes name."""
    return set(_alternatives(SPEND_RE) + _alternatives(PUBLISH_RE) + _alternatives(DENY_ALWAYS_RE) +
               _alternatives(UPLOAD_RE))


def connector_matcher() -> str:
    """The hooks.json matcher for claude.ai connectors served by uuid. (v2.61.0) EVERY tool on such a connector: the
    old matcher named only the tools the gate already knew, so a paid tool the vendor added later never reached the
    gate on the account the desktop app serves by uuid. The gate answers `{}` at once for a connector the settings
    do not name as Higgsfield. The selftest holds hooks.json to this exact string."""
    return "mcp__" + UUID_SRC + "__.*"


# (v2.61.0) Tool names only Higgsfield serves. A connector the settings name as "other" is let through, but never
# for one of these: one mistaken `connectors --other <uuid>` used to ungate the whole account.
SHARED_NAMES = {"generate_image", "generate_video", "generate_audio",
                "generate_image_batch", "generate_video_batch", "generate_audio_batch"}
HF_ONLY_PREFIXES = ("ads_studio_", "ai_influencer_", "scene_builder_3d_", "shorts_studio_")


def higgsfield_only(name: str) -> bool:
    return (name in class_names() and name not in SHARED_NAMES) or name.startswith(HF_ONLY_PREFIXES)


# (v2.61.0) A vendor tool the gate has not classified used to pass silently: three times a review found paid tools
# the vendor had added (the notes above). On a Higgsfield or Kling server a tool must now be in a class, or read-shaped,
# or the human is asked.
HF_NAMED_RE = re.compile(r"^mcp__" + SERVER + r"[Hh]iggsfield(?:[-_][A-Za-z0-9]+)*__(.+)$")
READ_RE = re.compile(r"(?:^|_)(?:get|list|show|search|query|describe|explore)(?:_|$)|"
                     r"_(?:status|quote|jobs|presets|accounts|trending|logs)$")
READ_EXACT = {"balance", "transactions", "jobs_wait", "job_display", "gpu_my", "whoami", "who_am_i",
              "ai_influencer_prepare"}     # prepares a form, spends nothing (the selftest below)


def is_read_name(name: str) -> bool:
    return name in READ_EXACT or bool(READ_RE.search(name))


def vendor_tool_name(tool: str, ck) -> str | None:
    """The bare tool name when the tool is on a Higgsfield or Kling server (by name, or a uuid connector the settings
    name as Higgsfield); None for anything else."""
    if ck == "higgsfield":
        return (tool or "").split("__")[-1]
    m = HF_NAMED_RE.match(tool or "") or KLING_RE.match(tool or "")
    return m.group(1) if m else None


def connector_settings() -> dict:
    """{"higgsfield": set, "other": set} from $CINE_HOME/connectors.json and the two env vars. A file that cannot be
    read counts as empty: an unnamed connector then ASKS, it is never allowed silently."""
    out = {"higgsfield": set(), "other": set()}
    try:
        data = json.load(open(os.path.join(CINE_HOME, CONNECTORS_FILE), encoding="utf-8"))
        for k in out:
            out[k] |= {str(x).strip().lower() for x in (data.get(k) or []) if str(x).strip()}
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    for k, env in (("higgsfield", "CINE_HIGGSFIELD_CONNECTORS"), ("other", "CINE_OTHER_CONNECTORS")):
        out[k] |= {x.strip().lower() for x in re.split(r"[,\s]+", os.environ.get(env, "")) if x.strip()}
    return out


def connector_kind(tool: str):
    """None for a tool not served by a uuid connector; else 'higgsfield', 'other' or 'unknown'. Named as both
    counts as Higgsfield: the gate never lets a listed spend through on a contradiction."""
    m = CONNECTOR_UUID_RE.match(tool or "")
    if not m:
        return None
    s, u = connector_settings(), m.group(1).lower()
    return "higgsfield" if u in s["higgsfield"] else "other" if u in s["other"] else "unknown"
# ⛔ DaVinci Resolve (2026-09-14). The MCP server that ships inside Resolve Studio 21.1 exposes the
# scripting API as `run_script` — sandboxed from the filesystem, but free to delete projects, start a
# render and call Resolve's AI Speech Generator — and `run_script_unsafe`, the same plus the whole OS.
# None of it spends credits, so none of it was gated, and two of Resolve's own features route around
# gates this skill already has (the voice gate; captions from the locked script). The scan reads the
# script's CODE (comments and strings removed) and is advisory by construction: a call hidden behind
# getattr/exec cannot be read, and the gate asks rather than pretending it can.
# ⚡ The name this session actually serves is `mcp__remote-devices__DaVinci_Resolve_Studio__…`:
# a proxy segment in front AND a `_Studio` suffix behind, neither of which the first version
# of this pattern admitted. Both are now optional parts, and the selftest asserts the REAL
# name rather than the two hand-written spellings it used to assert.
RESOLVE_RE = re.compile(r"^mcp__(?:[A-Za-z0-9_-]+?__)??[Dd]a_?[Vv]inci[_\- ]?[Rr]esolve(?:[_\- ]?[Ss]tudio)?__(.+)$")
RESOLVE_READONLY = {"get_resolve_status", "get_whats_new", "get_scripting_api", "search_scripting_api",
                    "get_scripting_docs", "list_luts", "list_dctls", "launch_resolve"}
RESOLVE_SCRIPT_TOOLS = {"run_script", "run_script_unsafe"}
RESOLVE_DENY = [
    (re.compile(r"\b(StartRendering|RenderWithQuickExport)\s*\("),
     "it STARTS a render — this skill queues (AddRenderJob) and a person presses Render on the Deliver "
     "page after looking at the job (editing-and-audio.md § Export)"),
    (re.compile(r"\bGenerateSpeech\s*\("),
     "Resolve's AI Speech Generator — voice goes through stage 6: an approved script line, a chosen "
     "voice, rights held (SKILL.md §2 row 6). A speech call inside the NLE skips all three"),
    (re.compile(r"\bCreateSubtitlesFromAudio\s*\("),
     "auto-captions from a transcription — captions are built from the LOCKED script (build_srt.py), "
     "never re-transcribed (editing-and-audio.md § Captions, locked-script clients)"),
]
RESOLVE_ASK = [
    (re.compile(r"\b(DeleteProject|DeleteTimelines|DeleteFolders|DeleteClips|DeleteAllRenderJobs|Quit)\s*\("),
     "destructive"),
    (re.compile(r"\b(SetRenderSettings|LoadRenderPreset|SetCurrentRenderFormatAndCodec|SetCurrentRenderMode|"
                r"AddRenderJob)\s*\("), "render-settings"),
    (re.compile(r"\b(LoadProject|CreateProject|CloseProject|ImportProject|RestoreProject)\s*\("),
     "project-switch"),
]
# ⛔ v2.49 HOUSE RULE 8 (2026-11-05: "for Fusion, Fairlight and making/adding/editing native titles, Claude should
# ALWAYS use computer control and not API. It fails all the time"). A script that WRITES to Fusion (a comp, a tool, an
# input, a title's words, a font), inserts a title, or does Fairlight work is DENIED — a deny, not an ask: no allowance
# covers it. READS stay open (a title's words read back, the comp list, the Loaders checked after an import). The check
# reads the script's live code: a console toggle set False and a helper nothing live calls are not counted, so the one
# console file can still be sent with PLACE_TITLES off. editing-and-audio.md § What runs through the API.
RULE8_DIRECT = {
    # Resolve-side calls that make or change Fusion work
    "AddFusionComp": "Fusion", "ImportFusionComp": "Fusion", "LoadFusionCompByName": "Fusion",
    "DeleteFusionCompByName": "Fusion", "RenameFusionCompByName": "Fusion", "CreateFusionClip": "Fusion",
    "InsertFusionGeneratorIntoTimeline": "Fusion", "InsertFusionCompositionIntoTimeline": "Fusion",
    # native titles
    "InsertFusionTitleIntoTimeline": "a native title", "InsertTitleIntoTimeline": "a native title",
    "InstallFile": "a title template install",
    # Fairlight
    "ApplyFairlightPresetToCurrentTimeline": "Fairlight", "InsertAudioToCurrentTrackAtPlayhead": "Fairlight",
    "SetVoiceIsolationState": "Fairlight",
}
RULE8_SOURCES = {"Fusion", "GetFusionCompByIndex", "GetFusionCompByName", "GetFusionComp", "GetCurrentComp",
                 "FontManager"}                  # calls whose result is a Fusion object
RULE8_FREE = {"fusion", "comp", "fu"}            # names Fusion's own console injects
RULE8_READ_PREFIX = ("Get", "Find", "Is", "Has", "Print", "Query")
RULE8_READ_NAMES = {"MapPath", "MapPathSegments", "ReverseMapPath", "ReverseMapPathSegments", "Export"} | RULE8_SOURCES
RULE8_RAW_RE = re.compile(r"\b(" + "|".join(RULE8_DIRECT) + r"|" + "|".join(sorted(RULE8_SOURCES)) + r")\s*\(")


def _rule8_problems(script: str) -> list:
    """What a Resolve script does to Fusion, Fairlight or a native title, as reasons. [] when it only reads."""
    import ast
    try:
        tree = ast.parse(script)
    except SyntaxError:
        hits = sorted(set(m.group(1) for m in RULE8_RAW_RE.finditer(_resolve_code(script))))
        return [f"the script does not parse, and it names {', '.join(hits)} — the gate cannot tell a read from a "
                f"write"] if hits else []
    # 1. the toggles: a module-level name assigned once, to a literal
    count, lit = {}, {}
    for n in ast.walk(tree):
        tg = []
        if isinstance(n, ast.Assign):
            tg = n.targets
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign, ast.For, ast.comprehension, ast.NamedExpr)):
            tg = [n.target]
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            tg = [n.optional_vars]
        for t in tg:
            for nm in ast.walk(t):
                if isinstance(nm, ast.Name):
                    count[nm.id] = count.get(nm.id, 0) + 1
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            try:
                lit[st.targets[0].id] = ast.literal_eval(st.value)
            except (ValueError, SyntaxError, TypeError):
                pass
    known = {k: v for k, v in lit.items() if count.get(k) == 1}

    def truth(e):
        if isinstance(e, ast.Constant):
            return bool(e.value)
        if isinstance(e, ast.Name) and e.id in known:
            return bool(known[e.id])
        if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
            v = truth(e.operand)
            return None if v is None else not v
        if isinstance(e, ast.BoolOp):
            vs = [truth(x) for x in e.values]
            if isinstance(e.op, ast.And):
                return False if False in vs else (True if all(v is True for v in vs) else None)
            return True if True in vs else (False if all(v is False for v in vs) else None)
        if isinstance(e, ast.Compare) and len(e.ops) == 1 and isinstance(e.left, ast.Name) and e.left.id in known:
            try:
                r = ast.literal_eval(e.comparators[0])
            except (ValueError, SyntaxError, TypeError):
                return None
            a = known[e.left.id]
            op = type(e.ops[0])
            if op is ast.Eq:
                return a == r
            if op is ast.NotEq:
                return a != r
            if op is ast.In:
                return a in r if isinstance(r, (list, tuple, set, str, dict)) else None
        return None

    def empty(e):                                   # a loop over a toggle's empty literal never runs
        if isinstance(e, ast.Name) and e.id in known:
            return not known[e.id]
        if isinstance(e, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return not (e.elts if hasattr(e, "elts") else e.keys)
        if isinstance(e, ast.Constant):
            return not e.value
        if isinstance(e, ast.BoolOp) and isinstance(e.op, ast.Or):
            return all(empty(x) for x in e.values)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr in ("items", "values", "keys"):
            return empty(e.func.value)
        return False

    class Prune(ast.NodeTransformer):
        def visit_If(self, node):
            self.generic_visit(node)
            v = truth(node.test)
            if v is True:
                return node.body
            if v is False:
                return node.orelse or None
            return node

        def visit_For(self, node):
            self.generic_visit(node)
            return (node.orelse or None) if empty(node.iter) else node
    tree = ast.fix_missing_locations(Prune().visit(tree))
    # 2. the helpers something live calls (classes are kept whole: their methods are reached by attribute)
    defs = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(n.name, []).append(n)

    def loads(nodes):
        out = set()
        for st in nodes:
            stack = [st]
            while stack:
                x = stack.pop()
                if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.update(loads(x.decorator_list))
                    continue
                if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load):
                    out.add(x.id)
                stack.extend(ast.iter_child_nodes(x))
        return out
    live, todo = set(), loads(tree.body)
    while todo:
        nm = todo.pop()
        if nm in defs and nm not in live:
            live.add(nm)
            for d in defs[nm]:
                todo |= loads(d.body) - live
    in_class = {id(f) for c in ast.walk(tree) if isinstance(c, ast.ClassDef) for f in c.body}

    class Dead(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            if node.name not in live and id(node) not in in_class:
                return None
            self.generic_visit(node)
            return node
        visit_AsyncFunctionDef = visit_FunctionDef
    tree = Dead().visit(tree)
    # 3. which names hold a Fusion object, per scope (a function's own names, then the module's), iterated to a fixed
    #    point; a helper's parameter holds one when a live call passes it one
    scopes = {0: []}                                 # scope key -> the nodes that belong to it (not nested defs)
    parent = {0: None}                               # a function's or a comprehension's enclosing scope
    COMPS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

    def collect(node, key):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scopes[id(ch)], parent[id(ch)] = [], key
                for d in ch.decorator_list + ch.args.defaults:
                    scopes[key].append(d)
                    collect(d, key)
                collect(ch, id(ch))
            elif isinstance(ch, COMPS):              # Python 3: a comprehension's loop names are its own
                scopes[key].append(ch)
                scopes[id(ch)], parent[id(ch)] = [], key
                collect(ch, id(ch))
            else:
                scopes[key].append(ch)
                collect(ch, key)
    collect(tree, 0)
    tainted = {k: set() for k in scopes}
    tainted[0] = set(RULE8_FREE)

    def is_src(c):
        f = c.func
        name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        if name == "scriptapp":
            return bool(c.args) and isinstance(c.args[0], ast.Constant) and c.args[0].value == "Fusion"
        return name in RULE8_SOURCES

    WRAP = {"list", "tuple", "sorted", "reversed", "iter", "next", "enumerate", "zip", "filter", "set"}

    def target_names(t):                             # the names a target binds — not the ones it indexes into
        if isinstance(t, ast.Name):
            return {t.id}
        if isinstance(t, ast.Starred):
            return target_names(t.value)
        if isinstance(t, (ast.Tuple, ast.List)):
            return set().union(*[target_names(x) for x in t.elts]) if t.elts else set()
        return set()
    binds = {k: set() for k in scopes}
    for k, nodes in scopes.items():
        for n in nodes:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    binds[k] |= target_names(t)
            elif isinstance(n, (ast.AugAssign, ast.AnnAssign, ast.For, ast.comprehension, ast.NamedExpr)):
                binds[k] |= target_names(n.target)
            elif isinstance(n, ast.withitem) and n.optional_vars is not None:
                binds[k] |= target_names(n.optional_vars)
            elif isinstance(n, ast.arg):
                binds[k].add(n.arg)

    def held(nm, sc):
        while sc is not None:
            if nm in tainted[sc]:
                return True
            if nm in binds[sc]:
                return False                         # bound here and not to a Fusion object: shadows the outer name
            sc = parent[sc]
        return False

    def tnt(e, sc):
        """Does this expression evaluate to a Fusion object (or a container of them)? A dict literal that carries one
        is a record, not the object; a call's arguments do not make its result one, except the iterable wrappers."""
        if e is None:
            return False
        if isinstance(e, ast.Name):
            return held(e.id, sc)
        if isinstance(e, ast.Call):
            if is_src(e):
                return True
            if isinstance(e.func, ast.Name) and e.func.id in WRAP:
                return any(tnt(x, sc) for x in e.args)
            return isinstance(e.func, ast.Attribute) and tnt(e.func.value, sc)
        if isinstance(e, (ast.Attribute, ast.Subscript, ast.Starred, ast.NamedExpr)):
            return tnt(e.value, sc)
        if isinstance(e, ast.IfExp):
            return tnt(e.body, sc) or tnt(e.orelse, sc)
        if isinstance(e, ast.BoolOp):
            return any(tnt(x, sc) for x in e.values)
        if isinstance(e, (ast.List, ast.Tuple, ast.Set)):
            return any(tnt(x, sc) for x in e.elts)
        if isinstance(e, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            return tnt(e.elt, id(e) if id(e) in scopes else sc)
        return False

    for _ in range(16):
        before = sum(len(v) for v in tainted.values())
        for sc, nodes in scopes.items():
            for n in nodes:
                if isinstance(n, ast.Assign) and tnt(n.value, sc):
                    for t in n.targets:
                        tainted[sc] |= target_names(t)
                elif isinstance(n, ast.NamedExpr) and tnt(n.value, sc):
                    tainted[sc] |= target_names(n.target)
                elif isinstance(n, (ast.For, ast.comprehension)) and tnt(n.iter, sc):
                    tainted[sc] |= target_names(n.target)
                elif isinstance(n, ast.withitem) and n.optional_vars is not None and tnt(n.context_expr, sc):
                    tainted[sc] |= target_names(n.optional_vars)
                elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in defs:
                    for d in defs[n.func.id]:
                        if id(d) not in tainted:
                            continue
                        ps = [x.arg for x in d.args.posonlyargs + d.args.args]
                        for i, x in enumerate(n.args):
                            if i < len(ps) and tnt(x, sc):
                                tainted[id(d)].add(ps[i])
                        for kw in n.keywords:
                            if kw.arg in ps and tnt(kw.value, sc):
                                tainted[id(d)].add(kw.arg)
        if sum(len(v) for v in tainted.values()) == before:
            break
    # 4. the writes
    found = []

    def root(e):
        while isinstance(e, (ast.Attribute, ast.Subscript, ast.Call)):
            e = e.func if isinstance(e, ast.Call) else e.value
        return e
    docs = {id(b_.body[0].value) for b_ in ast.walk(tree)
            if isinstance(b_, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and b_.body
            and isinstance(b_.body[0], ast.Expr) and isinstance(getattr(b_.body[0], "value", None), ast.Constant)}

    def _strs(v):
        if isinstance(v, str):
            yield v
        elif isinstance(v, dict):
            for k, x in v.items():
                yield from _strs(k)
                yield from _strs(x)
        elif isinstance(v, (list, tuple, set)):
            for x in v:
                yield from _strs(x)
    # a Fusion effect or transition: named in the plan data (a module-level literal) or as the literal "fusion"
    fusion_lit = any(re.search(r"\bfusion\b", x, re.I) for v in known.values() if isinstance(v, (list, tuple, dict))
                     for x in _strs(v)) or \
        any(isinstance(x, ast.Constant) and isinstance(x.value, str) and x.value.strip().lower() == "fusion"
            and id(x) not in docs for x in ast.walk(tree))
    for sc, nodes in scopes.items():
        for n in nodes:
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                a = n.func.attr
                if a in RULE8_DIRECT:
                    found.append(f"{a}() — {RULE8_DIRECT[a]} work (line {n.lineno})")
                elif a[:1].isupper() and not a.startswith(RULE8_READ_PREFIX) and a not in RULE8_READ_NAMES \
                        and tnt(n.func.value, sc):
                    found.append(f".{a}() on a Fusion object — a Fusion write (line {n.lineno})")
                elif a in ("AddEffect", "AddTransition") and fusion_lit:
                    found.append(f"{a}() in a script that names a Fusion item — a Fusion effect or transition is "
                                 f"Fusion work (line {n.lineno})")
            elif isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    if isinstance(t, (ast.Attribute, ast.Subscript)):
                        r = root(t)
                        if isinstance(r, ast.Name) and held(r.id, sc):
                            found.append(f"assigns {ast.unparse(t)[:60]} on a Fusion object — a Fusion write "
                                         f"(line {n.lineno})")
    found.sort(key=lambda f: int(re.search(r"line (\d+)", f).group(1)))
    seen, out = set(), []
    for f in found:
        k = f.split(" (line")[0]
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


RESOLVE_OPAQUE_RE = re.compile(r"\b(getattr|exec|eval|__import__|compile)\s*\(")
RESOLVE_MUTATE_RE = re.compile(r"\.\s*(Set[A-Z]\w*|Add[A-Z]\w*|Append\w*|Insert\w*|Create\w*|Import\w*|"
                               r"Delete\w*|Replace\w*|Link\w*|Relink\w*|Move\w*|Save\w*|Load\w*|Apply\w*|"
                               r"Export\w*|Transcribe\w*|Analyze\w*|OpenPage)\s*\(")
SPEECH_MODELS = {"seed_audio", "text2speech_v2"}
# ⛔ text2speech_v2 IS FIVE ENGINES BEHIND ONE MODEL ID, AND THE ENGINE IS A REQUIRED PARAM
# (2026-09-30). The vendor rejects the call without `variant`; this gate rejected any call WITH it
# (not on ALLOWED_PARAMS) — so the VO path PIPELINE.md prescribes (`variant=elevenlabs`) could not
# be sent at all. `variant`, `voice_type` and `voice_id` are all `required` for this model.
# [PRIMARY · Higgsfield MCP models_explore get text2speech_v2 · 2026-09-30]
TTS_VARIANTS = {"elevenlabs", "minimax", "seed_speech", "vibe_voice", "cozy_voice"}
# ⛔ THE WHITELIST WAS A YEAR BEHIND THE MODELS (2026-09-17). The gate refuses a param it cannot
# reason about — right, and the reason the list is short. But the vendor's own current contracts
# require params that were never on it: Seedance 2.5 takes `mode` (t2v / omni_reference /
# video_edit / video_extension), the Ad Multiplier workflow locks `mode:"video_edit"` +
# `generate_audio:false` + `duration_policy:"strict"`, and Soul 2.0 takes `quality`. Every one of
# those calls was DENIED by this gate as an undeclared param, which is a gate blocking the work
# rather than the mistake. Each addition below is a param a documented model REQUIRES — and two of
# them now carry a check of their own, because a param worth allowing is a param worth reading.
# [SECONDARY · Higgsfield skills repo + live MCP workflow catalog · 2026-09-17]
ALLOWED_PARAMS = {"model", "prompt", "duration", "aspect_ratio", "medias", "count", "get_cost",
                  "use_unlim", "negative_prompt", "resolution", "seed", "declined_preset_id",
                  "voice_id", "voice_type", "voice",
                  "mode", "generate_audio", "duration_policy", "quality", "bitrate_mode",
                  # Seedance video_extension direction — vendor-required for that mode, checked
                  # against the linted file in check_request (2026-09-26)
                  "extension_mode",
                  # Kling's audio switch. Without it the ONLY way to silence kling3_0 was refused as an
                  # undeclared param — while its default is sound ON (found 2026-09-19)
                  "sound",
                  # text2speech_v2's engine — vendor-REQUIRED, and read in check_request: legal only
                  # on that model, only from TTS_VARIANTS, never on an image or video call (2026-09-30)
                  "variant",
                  # GPT Image 2.6 (v2.49.0, the primary image model): format and GIF/SVG controls, each compared
                  # with the linted file in _check_match — never sent unread
                  "output_format", "background", "batch_size", "size", "frame_count", "frame_duration_ms",
                  # the connector's free-generation switch (v2.46.1) — read only on a Genjutsu call, and only
                  # when its linted spec says `free_gens: prefer`; refused on every other call
                  "use_free_gens"}
# ⚡ GENJUTSU (v2.46.1; 2026-11-03, "Include Genjutsu"). models_explore lists `resolution` as its ONLY
# parameter: the output follows the source video. These are the keys a Genjutsu call may carry at all.
GENJUTSU_CALL_PARAMS = {"model", "medias", "resolution", "prompt", "count", "get_cost", "use_free_gens"}
# The mode names the vendor documents. An unknown mode is a typo or a guess, and both cost money.
# ⛔ Only the FALLBACK for a model with no call_contract row. A roster model's modes are its own
# (assets/higgsfield-rates.json → call_contract): Kling's `mode` is a quality tier (std/pro/4k),
# Seedance's and Gemini's are generation modes — one shared list refused Kling's and all of Gemini's.
GEN_MODES = {"t2v", "i2v", "omni_reference", "video_edit", "video_extension"}
# A mode that EDITS or EXTENDS consumes an existing video: it must arrive with one.
MODES_NEED_VIDEO = {"video_edit", "video_extension", "edit"}
NON_IMAGE_ROLES = {"video", "audio", "driving_video", "audio_reference", "audio_references",
                   "video_references", "motion", "voice"}   # the API names too (2026-09-19)
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z ]{1,20}):\s*(.*)$")
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{1,80}>|NEEDS INPUT|TBD\b|\?\?\?", re.I)
POLICY_LINE_RE = re.compile(r"verification policy\**\s*[:—–-]\s*\**\s*`?(per-stage-human|gated|standing)`?",
                            re.I)
BUDGET_RE = re.compile(r"(\d[\d,.]*)\s*(?:cr|credits)\b", re.I)
# ⛔ The tag may carry its own evidence: `rate_card.py image` PRINTS `[measured 2026-09-17]`,
# and the first version of this pattern demanded a bare `[measured]` — so the skill's own
# pricing tool recommended a checkpoint line the skill's own gate then refused. A date after
# the word is strictly more informative; allow anything after it but not instead of it.
PROVENANCE_RE = re.compile(r"\[(estimated|measured|assumed|unpriced)\b[^\]]*\]", re.I)
# The two figures inside `Budget:` — the ceiling, and what we think it will actually cost.
ENVELOPE_RE = re.compile(r"envelope\s+([0-9]+(?:\.[0-9]+)?)\s*cr", re.I)
ESTIMATE_RE = re.compile(r"estimate\s+([0-9]+(?:\.[0-9]+)?)\s*cr", re.I)
SHOT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,30}$")
SCRIPT_LINE_RE = re.compile(r"^\s*(?:S\d+[A-Za-z]?\s+)?(?:[A-Z][A-Z0-9 _'’-]{0,30}:\s*)?(.+?)\s*$")


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def now() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class HashCache:
    """A job's file hashes keyed on (size, mtime_ns), the way git's index is — for REPORTS only.

    ⚡ a supplement ad job (2026-10-28): `status` took over two minutes on a 4.2 GB job, because it hashed every media file
    and re-linted every prompt on every call. A report may trust size and mtime; a gate that decides a spend or an
    export never does — preflight, approve and export hash fresh. The cache is written in place (no rename: a
    connected folder may refuse to replace a file) and a torn or foreign cache is simply rebuilt."""

    def __init__(self, job_path: str, gate_dir: str):
        self.root = job_path
        self.path = os.path.join(gate_dir, "hash-cache.json")
        self.hits = self.misses = 0
        self.dirty = False
        try:
            d = json.load(open(self.path, encoding="utf-8"))
            self.d = d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            self.d = {}

    def sha(self, fp: str) -> str:
        st = os.stat(fp)
        key = os.path.relpath(os.path.abspath(fp), self.root)
        e = self.d.get(key)
        if isinstance(e, list) and len(e) == 3 and e[0] == st.st_size and e[1] == st.st_mtime_ns:
            self.hits += 1
            return e[2]
        self.misses += 1
        h = sha256_file(fp)
        self.d[key] = [st.st_size, st.st_mtime_ns, h]
        self.dirty = True
        return h

    def save(self) -> None:
        if not self.dirty:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.d, fh)
            self.dirty = False
        except OSError:
            pass


def _develop_module():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import develop
    return develop


def _storyboard():
    """(v2.66.0) the storyboard reader: which jobs carry the picture sign-offs and what each still needs."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import storyboard
    return storyboard


def _ledger_module():
    """The production ledger. Imported lazily and NEVER allowed to break a gate: a tracking failure
    must not stop a legitimate approval, so every call site swallows its errors and says so."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("cine_ledger", os.path.join(HERE, "ledger.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ledger_sync(job_path: str) -> str:
    try:
        led = _ledger_module()
        rec = led.derive(job_path, led.load(job_path))
        led.save(job_path, rec)
        return rec.get("state", "")
    except Exception as e:                                    # noqa: BLE001
        print(f"  note: the ledger did not update ({e}) — the approval stands; run "
              f"`ledger.py sync {os.path.relpath(job_path)}` when it is fixed", file=sys.stderr)
        return ""


def _lint_module():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import prompt_lint  # the one deliberate import: the normaliser and the lint must be the same code
    return prompt_lint


def _prompt_dirs(job_path: str) -> list:
    """Every folder under the job that holds *.prompt.md. The reference plan lives in the prompts,
    so this is where the gate looks — not at a path convention that a job can quietly rename."""
    out = []
    for root, dirs, files in os.walk(job_path):
        dirs[:] = [d for d in dirs if not d.startswith(("_to_delete", ".", "_candidates"))]
        if any(f.endswith(".prompt.md") for f in files):
            out.append(root)
    return sorted(out)


def refplan_state(job_path: str) -> dict:
    """gap = declared, nothing behind it · blocked = a file that cannot be used as it stands.
    Either one means a generation would be spending credits on an unsourced or uncleared plan."""
    PL = _lint_module()
    gaps, blocked = [], []
    for d in _prompt_dirs(job_path):
        for r in PL.plan_rows(d, job_path):
            if r["state"] == "gap":
                gaps.append(r)
            elif r["state"] == "blocked":
                blocked.append(r)
    return {"gaps": gaps, "blocked": blocked, "dirs": _prompt_dirs(job_path),
            "ok": not (gaps or blocked)}


def coverage_state(job_path: str) -> dict:
    """⛔ The coverage floor, enforced instead of merely written down.

    `direction.md` §3 — "Coverage — generate choices, not just 'the shot'" — is genuinely generated
    and genuinely consumed: the retake tree's step 2 asks whether coverage already solves a fault,
    at a cost of about zero. But until 2026-09-07 `gate.py` contained no occurrence of the words
    "reaction" or "coverage", so a job that generated only its speaker clips passed every gate in
    this skill and arrived at the edit with nothing to cut away to.

    Only scenes that HAVE dialogue owe a reaction. A b-roll-only scene owes nothing, and
    `direction.md` §3 is equally clear that the floor is a floor: "don't over-cover"."""
    PL = _lint_module()
    scenes = {}
    for d in _prompt_dirs(job_path):
        for f in sorted(glob.glob(os.path.join(d, "*.clip.prompt.md"))):
            fm, _ = PL.split_front(read(f))
            shot = str(fm.get("shot") or "")
            m = re.match(r"^(S\d+)", shot, re.I)
            if not m:
                continue
            sc = scenes.setdefault(m.group(1).upper(), {"dialogue": [], "reaction": [], "other": []})
            kind = str(fm.get("type") or "").lower()
            sc["dialogue" if kind == "dialogue" else
               "reaction" if kind == "reaction" else "other"].append(shot)
    missing = [sc for sc, v in sorted(scenes.items()) if v["dialogue"] and not v["reaction"]]
    return {"scenes": scenes, "missing_reaction": missing, "ok": not missing}


def normalize_prompt(s: str) -> str:
    return _lint_module().normalize_prompt(s)


def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def load_json(p: str) -> dict:
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def find_profile(name: str, job_path: str) -> str | None:
    """Where a client profile named in a CHECKPOINT is on THIS machine, when the written path is not.

    ⚡ a supplement ad job (2026-10-28): the checkpoint named `/home/claude/acme/_cine-clients/acme.md` — a path in a cloud
    session's container — so on the Mac every `status` reported "no such profile" though the profile sat beside the
    jobs. Looked for, in order: CINE_CLIENTS, a `_cine-clients/` folder in the job's ancestors (the private
    profiles folder, kept out of the plugin), then the plugin's clients/. Validation still runs on what is found."""
    base = name if name.endswith(".md") else f"{name}.md"
    dirs = [CLIENTS]
    d = os.path.abspath(job_path)
    for _ in range(12):
        dirs.append(os.path.join(d, "_cine-clients"))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    dirs.append(os.path.join(SKILL_ROOT, "clients"))
    for dd in dirs:
        p = os.path.join(dd, base)
        if os.path.isfile(p):
            return p
    return None


def formats() -> dict:
    try:
        return load_json(os.path.join(ASSETS, "delivery-formats.json")).get("formats", {})
    except (OSError, json.JSONDecodeError):
        return {}


def cell(s) -> str:
    return str(s if s is not None else "").replace("|", "¦").replace("\n", " ").strip()


def parse_kv(text: str) -> dict:
    """`Key: value` lines, first occurrence wins, keys lower-cased. Multi-line values are joined
    when continuation lines are indented."""
    out, cur = {}, None
    for line in text.splitlines():
        if line.startswith("```") or line.startswith("#") or line.startswith(">"):
            cur = None; continue
        m = KEY_RE.match(line)
        if m:
            cur = m.group(1).strip().lower()
            if cur not in out:
                out[cur] = m.group(2).strip()
            else:
                cur = None
        elif cur and line.startswith((" ", "\t")) and line.strip():
            out[cur] = (out[cur] + " " + line.strip()).strip()
        else:
            cur = None
    return out


def section(text: str, num: str) -> str:
    """The body of `## <num>.` up to the next `## `."""
    m = re.search(rf"^##\s+{re.escape(num)}[.\s].*?$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^##\s", rest, re.M)
    return rest[: n.start()] if n else rest


def script_lines(text: str) -> list[str]:
    """The spoken lines of a script, normalised: scene ids and SPEAKER: tags stripped, headings,
    fences and directions dropped. A VO prompt must EQUAL one of these."""
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(("#", "```", "|", "-", "*", ">", "[", "(", "<!--")):
            continue
        m = SCRIPT_LINE_RE.match(s)
        if m:
            spoken = normalize_prompt(m.group(1)).strip('"').strip()
            if len(spoken.split()) >= 2:
                out.append(spoken)
    return out


# ----------------------------------------------------------------------------------------------
# job state
# ----------------------------------------------------------------------------------------------
class Job:
    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self.brief = os.path.join(self.path, "00-brief")
        self.checkpoint = os.path.join(self.brief, "CHECKPOINT.md")
        self.approvals_path = os.path.join(self.brief, "APPROVALS.md")
        self.prompts = os.path.join(self.path, "01-script", "prompts")
        self.gate_dir = os.path.join(self.path, ".gate")
        self.fields: dict = {}
        self.profile_path: str | None = None
        self.profile_moved: tuple | None = None      # (what the CHECKPOINT says, where it was found)
        self.policy: str | None = None
        self.switches: dict = {}                      # (v2.48.0, project switches) id → reason, the valid ones

    # -- checkpoint -----------------------------------------------------------------------------
    def validate(self) -> list[str]:
        problems: list[str] = []
        if not os.path.isfile(self.checkpoint):
            return [f"missing {os.path.relpath(self.checkpoint)} — copy assets/checkpoint-template.md "
                    f"there and fill every line"]
        txt = read(self.checkpoint)
        f = self.fields = parse_kv(txt)
        required = ["job", "mode", "client", "policy", "format", "voice", "inputs", "gates", "skips",
                    "budget", "approver", "next"]
        for k in required:
            if not f.get(k):
                problems.append(f"CHECKPOINT `{k.capitalize()}:` is empty")
        for k, v in f.items():
            if k in required and PLACEHOLDER_RE.search(v or ""):
                problems.append(f"CHECKPOINT `{k.capitalize()}:` still carries a placeholder: "
                                f"{PLACEHOLDER_RE.search(v).group(0)!r}")
        if f.get("mode") and not re.match(r"^[ABCDS]\b", f["mode"].strip()):
            problems.append("CHECKPOINT `Mode:` must start with A, B, C, D or S (modes/_INDEX.md)")
        client = (f.get("client") or "").strip()
        if client:
            if os.path.isabs(client):
                cand = client
            elif client.startswith("clients/") or "/" not in client:
                base = os.path.basename(client)
                cand = os.path.join(CLIENTS, base if base.endswith(".md") else f"{base}.md")
            else:
                cand = os.path.join(SKILL_ROOT, client)
            if not os.path.isfile(cand):
                moved = find_profile(os.path.basename(client), self.path)
                if moved:
                    if "/" in client:                 # a path that does not hold here; a bare name just resolved
                        self.profile_moved = (client, moved)
                    cand = moved
            if not os.path.isfile(cand):
                problems.append(f"CHECKPOINT `Client:` {client!r} — no such profile (looked in {CLIENTS}, in any "
                                f"`_cine-clients/` above the job, and in the plugin's clients/). "
                                f"Copy clients/_TEMPLATE.md to clients/<brand>.md, fill it, add the "
                                f"_INDEX.md row. An empty clients/ table means ASK, never assume")
            else:
                self.profile_path = cand
                problems += self._validate_profile(cand)
        pol = (f.get("policy") or "").strip().lower()
        if pol and pol not in POLICIES:
            problems.append(f"CHECKPOINT `Policy:` {pol!r} is not one of {'/'.join(POLICIES)}")
        if pol and self.policy and pol != self.policy:
            problems.append(f"CHECKPOINT `Policy:` {pol} disagrees with the profile's "
                            f"{self.policy} — the profile wins; fix the checkpoint")
        if not self.policy and pol in POLICIES:
            self.policy = pol
        fmt = (f.get("format") or "").strip()
        if fmt:
            preset = fmt.split()[0].strip("`*")
            if preset not in formats():
                problems.append(f"CHECKPOINT `Format:` {preset!r} is not a preset in "
                                f"assets/delivery-formats.json ({', '.join(formats())})")
            else:
                self.fields["_preset"] = preset
        # The stills lane is a pair: Mode S and Format `stills` imply each other. A video mode on
        # the stills preset would lose its fixed aspect; a stills job on a video preset would read
        # as a video job everywhere the format is consulted.
        if f.get("mode") and self.fields.get("_preset"):
            s_mode = self.is_stills()
            s_fmt = self.fields["_preset"] == STILLS_FORMAT
            if s_mode and not s_fmt:
                problems.append(f"CHECKPOINT `Mode:` S is the stills lane and needs `Format: "
                                f"{STILLS_FORMAT}` (each prompt file declares its own aspect) — got "
                                f"{self.fields['_preset']!r}")
            elif s_fmt and not s_mode:
                problems.append(f"CHECKPOINT `Format: {STILLS_FORMAT}` is the stills lane and needs "
                                f"`Mode: S` — a video job takes a video preset with a fixed aspect")
        inputs = f.get("inputs") or ""
        if inputs and not re.search(r"\b(PRESENT|MISSING)\b", inputs):
            problems.append("CHECKPOINT `Inputs:` must tag each input PRESENT or MISSING")
        for m in re.finditer(r"([A-Za-z][A-Za-z /+-]+?)\s+MISSING(?!\s*\()", inputs):
            problems.append(f"CHECKPOINT `Inputs:` {m.group(1).strip()!r} is MISSING with no "
                            f"parenthesis — (asked ...) or (accepted risk: ...)")
        skips = (f.get("skips") or "").strip()
        if skips and skips.lower() != "none" and not re.search(r"\s[—–-]\s", skips):
            problems.append("CHECKPOINT `Skips:` each skip needs ` — <reason>`; or write `none`")
        budget = f.get("budget") or ""
        if budget and not BUDGET_RE.search(budget):
            problems.append("CHECKPOINT `Budget:` needs a number in credits (e.g. `envelope 900 cr`)")
        if budget and not PROVENANCE_RE.search(budget):
            problems.append("CHECKPOINT `Budget:` needs a provenance tag: [estimated] / [measured] "
                            "/ [assumed] (pm-workflow.md, the verification readout)")
        # ⛔ A ZERO ESTIMATE IS NOT AN ESTIMATE (2026-09-17). lab-00001-fov was opened with
        # "envelope 60 cr · estimate 0 cr [estimated]" and the gate accepted it, because 0 is a
        # number and [estimated] is a tag. The truth was that `rate_card.py` had no rate for the
        # model — image models were not in the rate table at all — so the estimate was "I could not
        # price this" wearing the costume of a figure. The envelope check then compared spend
        # against nothing. THE SILENTLY WRONG NUMBER, in the one file whose job is to carry numbers.
        # A job that will generate has a non-zero estimate or says out loud that it has none.
        est = ESTIMATE_RE.search(budget or "")
        env = ENVELOPE_RE.search(budget or "")
        if est and env and _num(est.group(1)) == 0 and (_num(env.group(1)) or 0) > 0:
            problems.append(
                "CHECKPOINT `Budget:` says `estimate 0 cr` against a non-zero envelope — an "
                "envelope compared against nothing. Price it (`rate_card.py lookup --model <m> --res "
                "<r> --seconds <n>` for video, `rate_card.py image --model <m> --count <n>` for "
                "stills) and write the figure, or "
                "probe once with \"get_cost\": true and write what it returned. If the model has "
                "no rate in assets/higgsfield-rates.json, write `estimate UNPRICED [unpriced]` and "
                "say so — a stated unknown is usable, a false zero is not")
        # ⚡ THE EVALUATION TIER (house decision 2026-10-25). Optional; a job without the line is
        # production. An evaluation job states the question it answers BEFORE it runs — the arms and
        # the rule that decides between them — because an evaluation with no question is a cheap
        # first pass, which is exactly what the floor exists to stop.
        t = (f.get("tier") or "").strip().strip("`").split()[0].lower() if (f.get("tier") or "").strip() else ""
        if t and t not in job_tier.TIERS:
            problems.append(f"CHECKPOINT `Tier:` {t!r} is not one of {'/'.join(job_tier.TIERS)} — "
                            f"leave the line out for a production job")
        # (v2.72.0) THE EVALUATION LANE is opt-in: `Lane: eval` beside `Tier: evaluation` (job_tier.lane)
        ln_ = (f.get("lane") or "").strip().strip("`").split()[0].lower() if (f.get("lane") or "").strip() else ""
        if ln_ and ln_ != "eval":
            problems.append(f"CHECKPOINT `Lane:` {ln_!r} — the only lane is `eval` (the evaluation lane); leave the "
                            f"line out otherwise")
        elif ln_ == "eval" and t != "evaluation":
            problems.append("CHECKPOINT `Lane: eval` needs `Tier: evaluation` and a `Question:` — the lane exists "
                            "only to answer a question, and nothing it makes ships")
        elif ln_ == "eval" and re.match(r"^S\b", (f.get("mode") or "").strip()):
            problems.append("CHECKPOINT `Lane: eval` in a stills job (Mode S) — Mode S already has its own lane "
                            "(`brief`); the evaluation lane is for video and image questions in modes A–D")
        if t == "evaluation" and not (f.get("question") or "").strip():
            problems.append("CHECKPOINT `Tier: evaluation` needs `Question:` — the question, the arms "
                            "and the decision rule, written before the run (references/ai-generation.md, "
                            "the evaluation tier). Its outputs never ship")
        # ⚡ PROJECT SWITCHES (v2.48.0, project switches; 2026-11-03: "I think such choices are project
        # based?" — "yes"). OPTIONAL, and never in `required`: every CHECKPOINT opened before 2.48 has no line, and
        # no line (or `none`) means every house rule holds. When present, switches.py reads it — an id in
        # assets/project-switches.json, a reason of three words or more, never a locked rule — and each problem
        # refuses like any other line. No generate or spend decision reads `self.switches` (spending without approval
        # is on the locked list); only `approve export` does, for `music-led` (via music_fit) and `upload-master`.
        self.switches = {}
        sw = (f.get("switches") or "").strip()
        if sw and sw.lower() != "none":
            if PLACEHOLDER_RE.search(sw):
                problems.append(f"CHECKPOINT `Switches:` still carries a placeholder: "
                                f"{PLACEHOLDER_RE.search(sw).group(0)!r} — write `none`, or `<id> — <reason>` "
                                f"with an id from `switches.py list`")
            else:
                try:
                    self.switches, sw_problems = switches.parse(sw)
                except (OSError, json.JSONDecodeError) as e:
                    sw_problems = [f"`Switches:` cannot be checked — assets/project-switches.json is unreadable ({e})"]
                problems += [f"CHECKPOINT {p}" for p in sw_problems]
        return problems

    def tier(self) -> str:
        """'evaluation' or 'production' (job_tier.py). Absent or unknown is production."""
        return job_tier.tier(self.path)

    def is_eval_lane(self) -> bool:
        """(v2.72.0) `Lane: eval` with `Tier: evaluation` — one approved plan stands where concept and script stood."""
        return job_tier.lane(self.path) == "eval"

    def ever_evaluated(self) -> bool:
        """(v2.72.0) the job has an `eval` approval row: it stays evaluation material whatever its checkpoint says."""
        return job_tier.ever_evaluated(self.path)

    def is_stills(self) -> bool:
        """Mode S — the stills lane. Read from the checkpoint, never inferred."""
        if not self.fields:
            self.validate()
        return bool(re.match(r"^S\b", (self.fields.get("mode") or "").strip()))

    def _validate_profile(self, path: str) -> list[str]:
        p: list[str] = []
        txt = read(path)
        s0 = section(txt, "0")
        rel = os.path.relpath(path, SKILL_ROOT) if path.startswith(SKILL_ROOT) else path
        if not s0:
            p.append(f"profile {rel} has no `## 0.` hard-locks section")
            return p
        m = POLICY_LINE_RE.search(s0)
        if not m:
            p.append(f"profile {rel} section 0 does not declare `**Verification policy:** "
                     f"\\`per-stage-human|gated|standing\\`` — it is never a default; ask the client")
        else:
            self.policy = m.group(1).lower()
        holes = sorted(set(PLACEHOLDER_RE.findall(s0)))
        if holes:
            p.append(f"profile {rel} section 0 still has {len(holes)} unanswered item(s): "
                     f"{', '.join(holes[:6])}")
        return p

    # -- approvals -------------------------------------------------------------------------------
    def approvals(self) -> list[dict]:
        if not os.path.isfile(self.approvals_path):
            return []
        rows = []
        for line in read(self.approvals_path).splitlines():
            if not line.startswith("|") or re.match(r"^\|\s*(ts|-+)\s*\|", line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4 or not cells[0]:
                continue
            rows.append({"ts": cells[0], "stage": cells[1], "by": cells[2], "quote": cells[3],
                         "artifact": cells[4] if len(cells) > 4 else "",
                         "sha": cells[5] if len(cells) > 5 else "",
                         "media_id": cells[6] if len(cells) > 6 else "",
                         "verified": cells[7] if len(cells) > 7 else "",
                         "stamp": cells[8] if len(cells) > 8 else ""})     # (v2.72.0) appended, never inserted
        return rows

    def approved(self, stage: str) -> dict | None:
        for r in reversed(self.approvals()):
            if r["stage"].lower() == stage.lower():
                return r
        return None

    # -- prompts ---------------------------------------------------------------------------------
    def sidecars(self, relint: bool = False) -> list[dict]:
        """The linted prompts. With relint=True the lint is RE-RUN on each source file and a
        sidecar whose hash the fresh lint does not reproduce is marked forged/stale."""
        out = []
        if not os.path.isdir(self.prompts):
            return out
        pl = _lint_module() if relint else None
        for f in sorted(os.listdir(self.prompts)):
            if not f.endswith(".prompt.ok"):
                continue
            try:
                sc = load_json(os.path.join(self.prompts, f))
            except (OSError, json.JSONDecodeError):
                continue
            src = os.path.join(self.prompts, f[:-3] + ".md")
            sc["_file"] = f[:-3] + ".md"
            sc["_stale"] = (not os.path.isfile(src)) or sha256_file(src) != sc.get("file_sha256")
            sc["_forged"] = False
            if relint and os.path.isfile(src):
                try:
                    r = pl.lint(src, self.path)
                except Exception:
                    r = {"ok": False, "sidecar": None, "fails": ["lint crashed on the file"]}
                fresh = (r.get("sidecar") or {})
                if not r.get("ok") or fresh.get("prompt_sha256") != sc.get("prompt_sha256") \
                        or fresh.get("model") != sc.get("model") \
                        or fresh.get("duration") != sc.get("duration") \
                        or fresh.get("variants", 1) != sc.get("variants", 1) \
                        or fresh.get("resolution") != sc.get("resolution"):
                    sc["_forged"] = True
                    sc["_fails"] = r.get("fails") or ["sidecar does not match a fresh lint"]
            out.append(sc)
        return out

    def log(self, kind: str, payload: dict) -> None:
        try:
            os.makedirs(self.gate_dir, exist_ok=True)
            with open(os.path.join(self.gate_dir, "decisions.log"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": now(), "kind": kind, **payload}, ensure_ascii=False) + "\n")
        except OSError:
            pass


# ⛔ (3.1, PLAN-FINAL items 6–8) SESSIONS. One open-job pointer and one transcript pointer per machine meant a second
# Claude session could take over the first one's job, and an approval could be checked against the other session's
# transcript. Every hook call records its session (sessions/<id>.json: the transcript path FROM THE HOOK PAYLOAD, last
# seen, the job it opened). A shell call (open/approve/allow/status) resolves its session: --session / CINE_SESSION, else
# the single session a hook saw within the window, else — with two or more live — it refuses and names them. With no
# live session (hooks not seen recently, or never) it keeps the single shared pointers it always had.
SESSION_WINDOW_S = int(os.environ.get("CINE_SESSION_WINDOW") or 1800)   # long renders: 30 min by default
SESSION_STALE_S = 24 * 3600
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
HOOK_SESSION: str | None = None                # set by hook / session / posthook from their payload
CLI_SESSION: str | None = None                 # set by main() from --session, else CINE_SESSION
LAST_SESSION_WHY = ""


def sessions_dir() -> str:
    return os.path.join(CINE_HOME, "sessions")


def load_session(sid: str) -> dict | None:
    if not sid or not SESSION_ID_RE.match(sid):
        return None
    try:
        d = json.load(open(os.path.join(sessions_dir(), sid + ".json"), encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def save_session(sid: str, **upd) -> None:
    if not sid or not SESSION_ID_RE.match(sid):
        return
    try:
        os.makedirs(sessions_dir(), exist_ok=True)
        rec = load_session(sid) or {}
        rec.update({k: v for k, v in upd.items()})
        tmp = os.path.join(sessions_dir(), sid + ".json.part")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        os.replace(tmp, os.path.join(sessions_dir(), sid + ".json"))
    except OSError:
        pass


def live_sessions() -> list:
    out = []
    try:
        names = os.listdir(sessions_dir())
    except OSError:
        return out
    for f in names:
        if f.endswith(".json"):
            rec = load_session(f[:-5])
            if rec and time.time() - float(rec.get("last") or 0) <= SESSION_WINDOW_S:
                out.append(f[:-5])
    return sorted(out)


def resolve_session() -> tuple[str | None, str]:
    """(session id, why-not). (None, '') means: no live session — use the shared pointers."""
    sid = HOOK_SESSION or CLI_SESSION or os.environ.get("CINE_SESSION")
    if sid:
        rec = load_session(sid)
        if rec is None:
            return None, f"session {sid!r} is not one a hook has recorded on this machine"
        if time.time() - float(rec.get("last") or 0) > SESSION_STALE_S:
            return None, f"session {sid!r} has not been seen by a hook for over 24 h (stale)"
        return sid, ""
    live = live_sessions()
    if len(live) == 1:
        return live[0], ""
    if len(live) > 1:
        return None, (f"{len(live)} Claude sessions are live ({', '.join(live)}); say which one: "
                      f"`gate.py --session <id> …` or CINE_SESSION=<id> (SessionStart printed this session's id)")
    return None, ""


def hooks_seen(home: str | None = None) -> bool:
    """(3.1, build review 1) True once a real hook has recorded a session transcript in this home: hooks run here."""
    d = os.path.join(home or CINE_HOME, "sessions")
    for fp in glob.glob(os.path.join(d, "*.json")):
        try:
            if (json.load(open(fp, encoding="utf-8")) or {}).get("transcript"):
                return True
        except (OSError, ValueError, AttributeError):
            continue
    return False


def hookless() -> bool:
    """(3.1) True only when the studio set it (`studio_setup.py --hookless`, for Cowork / evals where hooks never run)
    AND no hook has ever recorded a transcript in this home. Never inferred: without it, an approval whose transcript
    cannot be resolved is refused, not recorded UNVERIFIED. (Build review 1: the agent can run `--hookless` itself, so
    on a home where hooks demonstrably run the setting is ignored; quotes there are always checked.)"""
    return _cine_home.config(CINE_HOME).get("hookless") is True and not hooks_seen()


def transcript_roots() -> list:
    env = os.environ.get("CINE_TRANSCRIPT_ROOT")
    roots = [os.path.join(os.path.expanduser("~"), ".claude", "projects")]
    return ([os.path.realpath(env)] if env else []) + [os.path.realpath(r) for r in roots]


VERIFIED_HOMES = "verified-homes.json"


def note_verified_home(job) -> None:
    """(build review 2) Remember which home recorded this job's transcript-checked approvals."""
    try:
        p = os.path.join(job.gate_dir, VERIFIED_HOMES)
        homes = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else []
        here = os.path.realpath(CINE_HOME)
        if here not in homes:
            os.makedirs(job.gate_dir, exist_ok=True)
            json.dump(sorted(set(homes) | {here}), open(p, "w", encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        pass


def _unchecked_from_another_home(job) -> bool:
    """True when this job has transcript-checked approvals and THIS home is not one that recorded them (a fresh or
    different CINE_HOME switched to hookless): an unchecked quote must not land on it."""
    if job is None or not any(str(r.get("verified") or "").strip().lower() == "transcript" for r in job.approvals()):
        return False
    try:
        homes = json.load(open(os.path.join(job.gate_dir, VERIFIED_HOMES), encoding="utf-8"))
    except (OSError, ValueError):
        homes = []
    return os.path.realpath(CINE_HOME) not in (homes if isinstance(homes, list) else [])


def quote_refusal(quote: str, job=None) -> str | None:
    """None when the quote may be recorded; else why not. Verified, or (hookless only) no transcript at all.
    (build review 2, Sonnet) A job that already carries a transcript-checked approval was worked where hooks run: an
    UNVERIFIED approval on it is refused even from a hookless home (a fresh CINE_HOME cannot launder a quote onto it)."""
    v = quote_in_transcript(quote)
    if v == "verified":
        return None
    if v == "no-transcript" and hookless():
        if _unchecked_from_another_home(job):
            return ("this job already has approvals checked against a session transcript, so an unchecked quote is "
                    "not recorded on it; approve it in the Claude Code session where the person said it")
        return None
    if v == "no-transcript":
        return ("the session transcript cannot be resolved" + (f": {LAST_SESSION_WHY}" if LAST_SESSION_WHY else "")
                + " — the quote cannot be checked, so nothing is recorded (a hookless studio sets it once: "
                  "`studio_setup.py --hookless`)")
    return "that quote appears in no human turn of the current session transcript"


def by_refusal(job, by: str) -> str | None:
    """(3.1) `--by` must name the checkpoint's Approver: one of its names (comma, semicolon or "and" list), at the
    start of --by as a whole word, any case ("Dana | CEO" is Dana). It proves the name matches the checkpoint, not
    who typed it — the quote check is what proves a human said the words."""
    appr = str((getattr(job, "fields", {}) or {}).get("approver") or "").strip()
    if not appr:
        return None
    names = [n.strip().lower() for n in re.split(r",|;|\band\b", appr) if n.strip()]
    b = (by or "").strip().lower()
    if any(b == n or (b.startswith(n) and not b[len(n):len(n) + 1].isalnum()) for n in names):
        return None
    return f"--by {by!r} is not the checkpoint's Approver ({appr}) — the approval is recorded under the approver's name"


def active_job() -> tuple[Job | None, str]:
    """(job, reason-if-none)."""
    p = os.environ.get("CINE_JOB")
    if p and HOOK_SESSION is None:                   # (3.1) CINE_JOB is the CLI process's own; a hook never follows it
        _named = CLI_SESSION or os.environ.get("CINE_SESSION")
        if not _named:                               # (build review 2, Grok HIGH) the one live session counts too
            _named = resolve_session()[0]
        _nrec = load_session(_named) if _named else None
        if _nrec and _nrec.get("job") and os.path.abspath(_nrec["job"]) != os.path.abspath(p):
            # (3.1 build review 1, Grok) a quote from session B must not land on job A
            return None, (f"CINE_JOB names {os.path.basename(p)}, but session {_named} has "
                          f"{os.path.basename(_nrec['job'])} open; use one or the other")
        return (Job(p), "") if os.path.isdir(p) else (None, f"CINE_JOB={p} is not a directory")
    sid, why = resolve_session()
    if why:
        return None, why
    if sid:
        rec = load_session(sid) or {}
        if rec.get("job"):
            if not os.path.isdir(rec["job"]):
                save_session(sid, job=None)
                return None, f"active job {rec['job']} no longer exists (this session's pointer has been cleared)"
            if time.time() - float(rec.get("opened") or 0) > ACTIVE_MAX_AGE_S:
                return None, (f"the active job {os.path.basename(rec['job'])} was opened more than 24 h ago — "
                              f"re-run `gate.py open` so a stale job cannot gate today's work")
            return Job(rec["job"]), ""
        if len(live_sessions()) > 1:
            return None, f"no job open in session {sid} (another session's job is not this one's)"
    if not os.path.isfile(ACTIVE_FILE):
        return None, "no job open"
    try:
        rec = json.loads(read(ACTIVE_FILE))
        if not isinstance(rec, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        rec = {"job": read(ACTIVE_FILE).strip(), "ts": 0}
    if not os.path.isdir(rec.get("job") or ""):
        # ⛔ SELF-HEAL. Detecting a vanished job and then leaving the pointer in place is how the
        # gate carried `/tmp/eval-.../jobs/bk-01001-morning` for a whole day on 2026-09-07 — a
        # temp dir an eval run deleted hours earlier. Every refusal named it, `status` reported it,
        # and nothing removed it. A pointer to a directory that does not exist is not state, it is
        # litter: clear it so the next message says "no job open", which is the truth.
        gone = rec.get("job")
        try:
            os.remove(ACTIVE_FILE)
            healed = " (the stale pointer has been cleared)"
        except OSError:
            healed = ""
        return None, f"active job {gone} no longer exists{healed}"
    if time.time() - float(rec.get("ts") or 0) > ACTIVE_MAX_AGE_S:
        return None, (f"the active job {os.path.basename(rec.get('job'))} was opened more than 24 h "
                      f"ago — re-run `gate.py open` so a stale job cannot gate today's work")
    if sid and rec.get("session") and rec["session"] != sid:
        # (3.1 build review 1, Grok HIGH) the shared pointer was opened by ANOTHER session: a second window, or the
        # same project after the first window went quiet, never spends or approves on it. Open the job here.
        return None, (f"no job open in session {sid}; the shared job {os.path.basename(rec['job'])} was opened by "
                      f"session {rec['session']}. Run `gate.py open <job-dir>` in this session to work on it here")
    return Job(rec["job"]), ""


def set_active(path: str | None, cwd: str = "") -> str | None:
    """Open (or close) the job for THIS session. Returns a refusal, or None. (3.1) The job goes on the resolved
    session's record; with no live session it goes on the shared pointer, as before."""
    os.makedirs(CINE_HOME, exist_ok=True)
    sid, why = resolve_session()
    if why:
        return why
    if sid:
        save_session(sid, job=os.path.abspath(path) if path else None, opened=time.time() if path else None, cwd=cwd)
        if len(live_sessions()) > 1:
            if path is None and os.path.isfile(ACTIVE_FILE):     # (build review 2) closing clears this session's pointer
                try:
                    if json.loads(read(ACTIVE_FILE)).get("session") == sid:
                        os.remove(ACTIVE_FILE)
                except (ValueError, AttributeError, OSError):
                    pass
            return None                         # several sessions: never touch another session's shared pointer
    if path is None:
        if os.path.isfile(ACTIVE_FILE):
            os.remove(ACTIVE_FILE)
        return None
    with open(ACTIVE_FILE, "w", encoding="utf-8") as fh:
        json.dump({"job": os.path.abspath(path), "ts": time.time(), "opened": now(), "cwd": cwd,
                   **({"session": sid} if sid else {})}, fh)
    return None


def bypass_log(msg: str) -> None:
    try:
        os.makedirs(CINE_HOME, exist_ok=True)
        with open(os.path.join(CINE_HOME, "bypass.log"), "a", encoding="utf-8") as fh:
            fh.write(f"{now()} {msg}\n")
    except OSError:
        pass


# ----------------------------------------------------------------------------------------------
# transcript check for approvals — the quote must be something a human typed
# ----------------------------------------------------------------------------------------------
def _strings_in(obj, out: list[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _strings_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _strings_in(v, out)


# (v2.61.0) What counts as the human's words. Until 2.61.0 the quote only had to appear as a SUBSTRING of any string in
# any user-role entry, tool results included: "do not ship the batch yet" verified "ship the batch", and a Bash
# result that echoed the words verified them too. Now the quote must be the WHOLE of something the human typed: the
# message, one of its sentences, or one of its comma clauses; or the whole of an answer they picked in
# AskUserQuestion (a tool_result linked to that tool's call). Text the harness adds (system reminders, pasted
# blocks, meta entries such as agent hand-backs, the summary written at a context reset) is not the human's.
SYSREM_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PASTE_RE = re.compile(r"<pasted_content[^>]*>.*?</pasted_content>", re.S)
ASK_ANSWER_RE = re.compile(r'"(?:[^"\\]|\\.)*"="((?:[^"\\]|\\.)*)"')
_QUOTE_TRIM = " \t.!?,;:\"'()[]"


def _norm_quote(s: str) -> str:
    return normalize_prompt(s or "").lower().strip(_QUOTE_TRIM)


def _human_units(text: str) -> set:
    """The whole message, each sentence and each comma clause, normalised — what a quote may equal."""
    text = PASTE_RE.sub(" ", SYSREM_RE.sub(" ", text or ""))
    units = {_norm_quote(text)}
    for piece in re.split(r"[.!?;\n\u2014\u2013]+| - ", text):      # sentences, and a dash: "yes — ship v4"
        units.add(_norm_quote(piece))
        for clause in piece.split(","):
            units.add(_norm_quote(clause))
    units.discard("")
    return units


def quote_in_transcript(quote: str) -> str:
    """'verified' | 'not-found' | 'no-transcript'. See the note above for what counts as the human's words.
    (3.1) The transcript is this session's (from the hook payload); with no live session, the shared pointer. A path
    outside Claude Code's projects folder is not a transcript (CINE_TRANSCRIPT_ROOT adds a root: tests, odd installs)."""
    global LAST_SESSION_WHY
    LAST_SESSION_WHY = ""
    sid, why = resolve_session()
    if why:
        LAST_SESSION_WHY = why
        return "no-transcript"
    tp = (load_session(sid) or {}).get("transcript") if sid else None
    if not tp:
        if not os.path.isfile(TRANSCRIPT_FILE):
            return "no-transcript"
        tp = read(TRANSCRIPT_FILE).strip()
    if not tp or not os.path.isfile(tp):
        return "no-transcript"
    real = os.path.realpath(tp)
    if not any(real.startswith(r.rstrip(os.sep) + os.sep) for r in transcript_roots()):
        LAST_SESSION_WHY = f"{tp} is not under Claude Code's projects folder, so it is not taken as a transcript"
        return "no-transcript"
    q = _norm_quote(quote)
    if not q:
        return "not-found"
    ask_ids: set = set()
    try:
        with open(tp, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(e, dict) or e.get("isMeta") or e.get("isCompactSummary") or e.get("isSidechain"):
                    continue
                msg = e.get("message") if isinstance(e.get("message"), dict) else {}
                role = e.get("type") or msg.get("role")
                content = msg.get("content")
                if role == "assistant":
                    for b in content if isinstance(content, list) else []:
                        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "AskUserQuestion":
                            ask_ids.add(b.get("id"))
                    continue
                if role != "user":
                    continue
                texts, answers = [], []
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    for b in content:
                        if not isinstance(b, dict):
                            continue
                        if b.get("type") == "text":
                            texts.append(str(b.get("text") or ""))
                        elif b.get("type") == "tool_result" and b.get("tool_use_id") in ask_ids:
                            c = b.get("content")
                            s = c if isinstance(c, str) else " ".join(
                                str(x.get("text") or "") for x in (c or []) if isinstance(x, dict))
                            answers += ASK_ANSWER_RE.findall(s)
                if any(q in _human_units(t) for t in texts) or any(_norm_quote(a) == q for a in answers):
                    return "verified"
    except OSError:
        return "no-transcript"
    return "not-found"


# ----------------------------------------------------------------------------------------------
# the decision — one function, used by hook, preflight and status
# ----------------------------------------------------------------------------------------------
def _num(v):
    try:
        return float(str(v).rstrip("s")) if v not in (None, "") else None
    except (ValueError, TypeError):
        return None


# --- the previz lane -----------------------------------------------------------------------------
# Concept art is the one generation that SAVES money, and the gate was refusing it. A director
# choosing between five sentences picks blind, the shot gets made, and the credits are spent
# discovering something the plan already contained. Real productions buy concept art for exactly
# this reason: it is a fraction of a shoot day and it prevents the shoot day being wrong.
#
# So the lane exists — and it is capped, justified, ordered and closed:
#   · a HARD cap (PREVIZ_MAX) no argument can exceed, and a per-lane budget under it
#   · `--why` in the operator's own words: which decision does seeing this unblock?
#   · the LOOK BOARD must already be filled — you do not generate a picture of a thing before you
#     have looked at photographs of the real thing; that ordering is the entire point
#   · it CLOSES the moment `concept` is approved. Previz informs the choice; after the choice it is
#     just untracked spend wearing a development label.
# ⛔ The quality floor is NOT relaxed here. A cheaper generation is a different picture, so cheap
# previz would mislead the director about the thing it exists to show. The cap is on COUNT.
PREVIZ_MAX = 12
PREVIZ_FILE = "previz.json"


def previz_path(job) -> str:
    return os.path.join(job.gate_dir, PREVIZ_FILE)


def previz_state(job) -> dict:
    try:
        with open(previz_path(job), encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return d if isinstance(d, dict) else {}


def previz_write(job, d: dict) -> None:
    os.makedirs(job.gate_dir, exist_ok=True)
    with open(previz_path(job), "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2, ensure_ascii=False)


def previz_available(job) -> tuple:
    """(ok, reason). The lane is open, under budget, and the concept is not yet signed."""
    st = previz_state(job)
    if not st or not st.get("budget"):
        return False, ("no previz lane is open — `gate.py previz <job> --budget N --why \"<the "
                       "decision this unblocks>\"`. Concept art is allowed here BECAUSE it is "
                       "cheaper than discovering the same thing in a finished shot; it is capped "
                       "and it closes when the concept is signed")
    if job.approved("concept"):
        return False, ("the concept is approved, so the previz lane is closed — previz informs the "
                       "CHOICE; after the choice it is untracked spend wearing a development "
                       "label. From here a picture is a start frame: write the prompt, lint it, "
                       "and go through the frame gate")
    used, budget = int(st.get("used") or 0), int(st.get("budget") or 0)
    if used >= budget:
        return False, (f"the previz lane is spent: {used}/{budget} used for "
                       f"{st.get('why', 'an unrecorded reason')!r}. Look at what came back before "
                       f"buying more — if it did not answer the question, another image of the same "
                       f"question will not either. `gate.py previz <job> --budget N --why ...` "
                       f"raises it, up to {PREVIZ_MAX}, and records why")
    return True, f"previz {used + 1}/{budget}"


def previz_spend(job, n: int = 1) -> None:
    st = previz_state(job)
    if not st:
        return
    st["used"] = int(st.get("used") or 0) + n
    st.setdefault("history", []).append(
        {"ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), "n": n})
    previz_write(job, st)


def brief_problems(job) -> list[str]:
    """Mode S: the approved brief, and that the file on disk is still the file that was approved.
    ⛔ A brief edited after its approval is a brief nobody approved — the same rule the frame gate
    applies to a still that changed after `approve frame:`."""
    br = job.approved("brief")
    if not br:
        return ["`brief` is not approved — a stills job's one human sign-off before any spend: "
                "`gate.py approve brief --by <name> --quote \"<their words>\" --artifact "
                "00-brief/BRIEF-<slug>.md` (the brief names every still ID it covers)"]
    p = os.path.join(job.path, br.get("artifact") or "")
    if not br.get("artifact") or not os.path.isfile(p):
        return ["the approved brief file is missing from the job — re-approve the brief"]
    if br.get("sha") and not sha256_file(p).startswith(br["sha"]):
        return [f"{br['artifact']} changed after it was approved — the approval is about different "
                f"bytes. Re-approve the brief (`gate.py approve brief ...`) with the human"]
    return []


# ---------------------------------------------------------------------------------------------- the evaluation lane
# (v2.72.0; 2026-11-15, "Build an eval route"; planned with three review rounds each by Grok 4.7 and Sonnet 5.5).
# Copied from Mode S: one approval, `eval` (00-brief/EVAL-PLAN.md), stands where concept and script stood, and the
# numbers the person approved — the shots, the takes per shot, the budget — are enforced at EVERY call, under every
# policy, before any allowance, counting this call and a reservation for every call already let through (two calls
# in one turn both reach PreToolUse before either is recorded). Speech, Genjutsu, Kling, previz, log-external and the
# unlintable spend tools are denied in the lane. A job with an `eval` row stays evaluation material for good.
def _eval_ledger_path(job) -> str:
    return os.path.join(job.gate_dir, "eval-ledger.jsonl")


def _eval_plan_text(job) -> str:
    p = os.path.join(job.path, job_tier.PLAN_FILE)
    return read(p) if os.path.isfile(p) else ""


def _stamp_ck(stamp: str) -> str:
    m = re.search(r"\bck=([0-9a-f]{8,64})", stamp or "")
    return m.group(1) if m else ""


def eval_lane_problems(job) -> list[str]:
    """May the lane spend at all: the plan approved, still the approved bytes, and the checkpoint's key lines unchanged."""
    r = job.approved("eval")
    if not r:
        return ["`eval` is not approved — the evaluation lane's one human sign-off before any spend: write "
                "00-brief/EVAL-PLAN.md from assets/eval-plan-template.md, show it, then `gate.py approve eval --by "
                "<name> --quote \"<their words>\" --artifact 00-brief/EVAL-PLAN.md`"]
    pth = os.path.join(job.path, job_tier.PLAN_FILE)
    if not os.path.isfile(pth):
        return ["the approved 00-brief/EVAL-PLAN.md is missing from the job"]
    if r.get("sha") and not sha256_file(pth).startswith(r["sha"]):
        return ["00-brief/EVAL-PLAN.md changed after it was approved — the approval is about different bytes. Put it "
                "back, or (only before the first generation) re-approve it with the person"]
    ck = _stamp_ck(r.get("stamp", ""))
    if not ck or ck != job_tier.checkpoint_key_sha(parse_kv(read(job.checkpoint))):
        return ["the checkpoint's key lines (Tier, Lane, Question, Budget, Policy, Mode, Format, Client) changed after "
                "the plan was approved — put them back, or (only before the first generation) re-approve the plan"]
    return []


def _eval_assign(job) -> tuple:
    """(reservations, released ids, {id: submissions it absorbed}, unexplained submission rows). One submission row
    fills one request slot of one reservation: rows in time order, each to the LATEST reservation at or before it
    with an open slot for that hash (build review 3, Grok: a later submission must not confirm an older sibling)."""
    rows = _jsonl(_eval_ledger_path(job))
    res = [r for r in rows if r.get("id") and not r.get("release")]
    released = {r.get("release") for r in rows if r.get("release")}
    slots = {r["id"]: list(r.get("hashes") or []) for r in res}
    filled = {r["id"]: 0 for r in res}
    unexplained = []
    for sub_ in sorted(_jsonl(_submitted_path(job)), key=lambda x: float(x.get("epoch") or 0)):
        h, e = sub_.get("hash"), float(sub_.get("epoch") or 0)
        cands = [r for r in res if float(r.get("epoch") or 0) <= e and h in slots[r["id"]]]
        if cands:
            r = max(cands, key=lambda x: float(x.get("epoch") or 0))
            slots[r["id"]].remove(h)
            filled[r["id"]] += 1
        else:
            unexplained.append(sub_)
    return res, released, filled, unexplained


def eval_usage(job) -> tuple:
    """(generations per shot, credits used, submissions no reservation explains). Counted: every unreleased
    reservation, every RELEASED one that billed anyway (a submission filled it: build review 3, Grok), every
    unexplained submission (against every shot) and external.jsonl."""
    per: dict = {}
    used = 0.0
    res, released, filled, unex = _eval_assign(job)
    for r in res:
        if r["id"] in released and not filled.get(r["id"]):
            continue
        for sh, g in (r.get("units") or {}).items():
            per[str(sh)] = per.get(str(sh), 0) + int(g or 0)
        used += float(r.get("credits") or 0)
    unexplained = len(unex)
    for r in unex:
        if isinstance(r.get("credits"), (int, float)):
            used += float(r["credits"])
    for r in _jsonl(os.path.join(job.gate_dir, "external.jsonl")):
        if isinstance(r.get("credits"), (int, float)):
            used += float(r["credits"])
    return per, used, unexplained


def eval_generated(job) -> bool:
    """Whether anything has been generated or is reserved and unreleased in this job (the plan is fixed from then on)."""
    res, released, _f, _u = _eval_assign(job)
    return bool([r for r in res if r["id"] not in released] or _jsonl(_submitted_path(job))
                or _jsonl(os.path.join(job.gate_dir, "external.jsonl")))


def eval_shot_problems(job, units, prices: list) -> list[str]:
    """Is this call inside the plan: every shot on the `Shots:` line, the takes and the budget not exceeded."""
    txt = _eval_plan_text(job)
    shots, n = job_tier.plan_shots(txt), job_tier.plan_numbers(txt)
    if not units:
        return ["every call in the evaluation lane must match the linted prompt of a shot the plan names"]
    probs = [f"{sh} is not on the plan's `Shots:` line ({', '.join(shots) or 'none'}) — the plan is what was approved"
             for sh in units if sh not in shots]
    if probs:
        return probs
    per, used, unexplained = eval_usage(job)
    takes = n["takes"] or 0
    for sh, g in units.items():
        have = per.get(sh, 0) + unexplained
        if have + g > takes:
            probs.append(f"{sh}: this would be take {have + g} of a plan that allows {takes} per shot — the plan is "
                         f"spent for this shot" + (f" ({unexplained} submission(s) with no reservation count against "
                                                   f"every shot)" if unexplained else ""))
    if any(c is None for c in prices) or not prices:
        probs.append("the gate cannot price this call, and the evaluation lane's budget must bind every call — use a "
                     "model and resolution with a row in assets/higgsfield-rates.json")
    else:
        this = sum(prices)
        if n["budget"] is None or used + this > n["budget"] + 1e-9:
            probs.append(f"this call ({this:g} cr) takes the plan past its budget ({used:g} of {n['budget']} cr used)")
    return probs


import contextlib  # noqa: E402


@contextlib.contextmanager
def eval_lock(job, wait_s: float | None = None):
    """An exclusive lock on the job's evaluation ledger, held from the usage read through the reservation."""
    if wait_s is None:
        try:
            wait_s = float(os.environ.get("CINE_EVAL_LOCK_WAIT") or 10.0)
        except ValueError:
            wait_s = 10.0
    fh = None
    try:
        import fcntl
        os.makedirs(job.gate_dir, exist_ok=True)
        fh = open(os.path.join(job.gate_dir, "eval.lock"), "a+")
        t0 = time.time()
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.time() - t0 > wait_s:
                    yield False
                    return
                time.sleep(0.05)
        yield True
    finally:
        if fh:
            try:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_UN)
            except OSError:
                pass
            fh.close()


# (v2.72.0, build review 2) NO CLOCK frees a take: an ask approved hours later runs without a new PreToolUse, so a
# reservation that expired would let it run outside the count (Grok). A reservation counts until it is RELEASED: by
# an instant vendor rejection (the failure hook, automatically) or by `gate.py release-take`, which refuses when a
# submission NEWER than the reservation carries its hash (a confirmed call is spent) or when the call may still be in
# flight. "Confirmed" uses only submissions newer than the reservation: every take of one prompt shares a request hash,
# so an earlier take must not confirm a later, declined ask (both reviewers).
EVAL_INFLIGHT_S = 1200      # release-take refuses a reservation younger than this: a long clip may still be running


def _eval_reservations(job) -> list:
    rows = _jsonl(_eval_ledger_path(job))
    released = {r.get("release") for r in rows if r.get("release")}
    return [r for r in rows if r.get("id") and r.get("id") not in released and not r.get("release")]


def _eval_confirmed(job, r: dict) -> bool:
    """A submission was assigned to this reservation (one submission confirms one request of one reservation)."""
    return bool(_eval_assign(job)[2].get(r.get("id")))


def _eval_rows_live(job) -> list:
    """The reservations that count: every one not released (legacy rows without an id count too)."""
    rows = _jsonl(_eval_ledger_path(job))
    released = {r.get("release") for r in rows if r.get("release")}
    return [r for r in rows if not r.get("release") and (not r.get("id") or r.get("id") not in released)]


def eval_release(job, rid: str, why: str, by: str = "gate") -> bool:
    try:
        with open(_eval_ledger_path(job), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": now(), "epoch": time.time(), "release": rid, "why": why[:200], "by": by},
                                ensure_ascii=False) + "\n")
    except OSError:
        return False
    return True


def eval_reserve(job, tool: str, units: dict, prices: list, hashes: list, pending: bool = False) -> bool:
    """Reserve the takes and credits of a lane call the gate let through. It counts until a release (see above).
    False when the ledger cannot be written: the caller denies, because an uncounted call is an unbounded one.
    `pending` only records that the call asked; it changes nothing about the count."""
    try:
        os.makedirs(job.gate_dir, exist_ok=True)
        rid = f"R{sum(1 for r_ in _jsonl(_eval_ledger_path(job)) if r_.get('id')) + 1}"
        with open(_eval_ledger_path(job), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": now(), "epoch": time.time(), "id": rid, "tool": tool, "units": units,
                                 "credits": sum(c for c in prices if c is not None), "hashes": hashes,
                                 **({"asked": True} if pending else {})}, ensure_ascii=False) + "\n")
    except OSError:
        return False
    return True


def brief_names(job, shot: str) -> bool:
    """Is the still ID named in the approved brief? Whole-token match, case-sensitive — `S1` does
    not match inside `S10`, and `hero` does not match inside `superhero`."""
    br = job.approved("brief") or {}
    p = os.path.join(job.path, br.get("artifact") or "")
    if not shot or not br.get("artifact") or not os.path.isfile(p):
        return False
    return re.search(r"(?<![A-Za-z0-9_-])" + re.escape(shot) + r"(?![A-Za-z0-9_-])", read(p)) is not None


def check_request(job: Job, kind: str, params: dict, policy: str, sidecars: list[dict] | None = None
                  ) -> tuple[list[str], dict]:
    """kind ∈ image/video/audio. Returns (problems, matched sidecar or {})."""
    problems: list[str] = []
    if not isinstance(params, dict):
        return ["params is not an object"], {}
    if params.get("get_cost") is True:
        return [], {"_probe": True}
    prompt = normalize_prompt(params.get("prompt") if isinstance(params.get("prompt"), str) else "")
    model = str(params.get("model") or "").strip()
    stills = job.is_stills()
    if stills and kind != "image":
        return [f"stills job (Mode S): generate_{kind} is not part of this lane — a stills job "
                f"makes images only. Open a video job (Mode A–D) for motion or voice"], {}
    if stills:
        problems += brief_problems(job)
    elif job.is_eval_lane():
        # (v2.72.0) the evaluation lane: the approved plan stands where script and storyboard stood
        if kind == "audio":
            return ["speech is not part of the evaluation lane — with no script there is no line to check a voice "
                    "against (v2.72.0). Evaluate speech in a production job, or leave it out of the question"], {}
        if kind == "video" and _lint_module().is_genjutsu(model):
            return ["Genjutsu is not part of the evaluation lane (v2.72.0) — it re-renders a source video at about 6× "
                    "a roster clip; evaluate it in its own production job"], {}
        problems += eval_lane_problems(job)
    elif not job.approved("script"):
        problems.append("`script` is not approved — `gate.py approve script --by <name> --quote "
                        "\"<their words>\" --artifact 01-script/SCRIPT-<slug>-v<N>.md`. The script "
                        "review is the one that saves the most money (review-and-approval.md §10)")
    elif kind in ("image", "video") and not job.approved("storyboard") and _storyboard().required(job.path):
        problems.append("`storyboard` is not approved — this job signs the film as pictures in time before any "
                        "paid picture: `board.py storyboard <job>`, `animatic.py <job>`, show both, then `gate.py "
                        "approve storyboard --by <name> --quote \"<their words>\"` (references/storyboarding.md). "
                        "`storyboard.py <job>` lists what is still missing")
    unknown = sorted(k for k in params if k not in ALLOWED_PARAMS)
    if unknown:
        problems.append(f"undeclared param(s) {unknown} — the gate compares what it can read; "
                        f"width/height/preset_id and the like are set through the prompt file's "
                        f"aspect/resolution, not at call time")
    mode = str(params.get("mode") or "").strip()
    _PL = _lint_module()
    if kind == "video" and _PL.is_genjutsu(model):
        gp, gsc = check_genjutsu(job, params, sidecars if sidecars is not None else job.sidecars(relint=True))
        return problems + gp, gsc
    if "use_free_gens" in params:
        problems.append(f"`use_free_gens` on {model or 'this call'!r} — the gate reads it on a Genjutsu call only, "
                        f"where the linted spec says `free_gens: prefer` (v2.46.1); anywhere else it is an unread switch "
                        f"on what bills")
    _c = _PL.call_contract(str(params.get("model") or ""))
    # ⛔ An EMPTY list is an answer ("this model takes no mode"), not a missing one. `or GEN_MODES`
    # read MiniMax's [] as "unknown" and let `mode: t2v` through on a model with no mode at all.
    _modes = set(_c.get("modes") or []) if _c else GEN_MODES
    if mode and mode not in _modes:
        problems.append(f"mode {mode!r} is not one {params.get('model') or 'the vendor'} documents "
                        f"({', '.join(sorted(_modes)) or 'it takes no mode'}) — an invented mode is a "
                        f"guess that bills")
    if mode in MODES_NEED_VIDEO:
        roles = [_PL.canonical_role(str((m or {}).get("role") or "")) for m in (params.get("medias") or [])
                 if isinstance(m, dict)]
        if "video_references" not in roles:
            problems.append(f"mode {mode!r} edits or extends an existing video but no media is a "
                            f"video (`video_references`) — the source is the thing being edited")
    # ⛔ A VIDEO MODEL THAT AUTHORS ITS OWN AUDIO IS THE VOICE GATE ROUTED AROUND. Stage 6 owns
    # voice: an approved line, a chosen voice, rights held. `generate_audio:true` skips all three
    # and returns a clip with speech nobody approved baked into the pixels' soundtrack. The vendor's
    # own ad workflow renders SILENT and restores the source's real audio in post — the same rule,
    # reached independently. Allowed only once `audio` is approved for this job.
    # (v2.49.0, 2026-11-05: "keep native sound … native audio can be replaced at any time after") A clip's
    # own DIEGETIC sound is production sound now — ambience, footsteps, the door — directed in the prompt's
    # [AUDIO] block and replaceable in the edit. What still needs `audio` approved is SPEECH: a model that speaks
    # a line nobody approved is the voice gate routed around. That check needs the linted clip, so it lives in
    # _check_match (speaks()). A job on the project switch `guide-audio` keeps the old rule: any sound needs
    # `audio` approved first.
    if params.get("generate_audio") and not job.approved("audio") and switches.on(job.path, "guide-audio"):
        problems.append("`generate_audio: true` without an approved `audio` stage, and this job turned on "
                        "`guide-audio` — native sound is a guide here: render silent and carry real audio "
                        "through the edit, or approve `audio` first")
    if "variant" in params and (kind != "audio" or model != "text2speech_v2"):
        problems.append(f"`variant` is text2speech_v2's engine switch — on "
                        f"{model or 'this call'!r} it means nothing the gate can check, and an "
                        f"unread param is how a call does something nobody reviewed")
    if kind == "audio":
        if model == "text2speech_v2":
            _v = str(params.get("variant") or "").strip()
            if not _v:
                problems.append("text2speech_v2 needs `variant` — the engine is a required param "
                                f"({', '.join(sorted(TTS_VARIANTS))}); the vendor rejects the call "
                                "without it. The client profile §2 names the engine its voices "
                                "were made on (elevenlabs for the house voices, PIPELINE.md)")
            elif _v not in TTS_VARIANTS:
                problems.append(f"variant {_v!r} is not an engine text2speech_v2 documents "
                                f"({', '.join(sorted(TTS_VARIANTS))}) — a guessed engine is a "
                                f"different voice, billed")
            if params.get("voice_type") not in ("preset", "element"):
                problems.append("text2speech_v2 needs `voice_type` — 'preset' or 'element' "
                                "(vendor-required)")
        if not prompt:
            problems.append("empty VO text")
        if model and model not in SPEECH_MODELS:
            problems.append(f"{model!r} is not a speech model ({', '.join(sorted(SPEECH_MODELS))}) — "
                            f"music and SFX models are not the VO path (ai-generation.md Step 4)")
        sc = job.approved("script")
        if sc and sc.get("artifact") and prompt:
            sp = os.path.join(job.path, sc["artifact"])
            if os.path.isfile(sp):
                lines = script_lines(read(sp))
                if prompt.strip('"') not in lines:
                    problems.append("VO text is not one spoken line of the approved script — the "
                                    "wording is locked, one line = one clip (revisions.md: a wording "
                                    "change cascades VO → clip → edit → captions). Use the line "
                                    "verbatim or re-approve the script")
            else:
                problems.append("the approved script file is missing from the job — re-approve it")
        if not params.get("voice_id") and not params.get("voice"):
            problems.append("no voice chosen — `voice_id` must come from the client profile §2 "
                            "(never a house default)")
        return problems, {}
    # ⛔ the word that is refused and still charged (Scenario E10, v2.45): the prompt is linted, so only a hand-added
    # param can carry it — a negative_prompt above all
    if _PL.WATERMARK_RE.search(json.dumps({k: v for k, v in params.items() if k != "prompt"}, ensure_ascii=False,
                                          default=str)):
        problems.append("the call carries the word 'watermark' (negative_prompt or another param) — a request carrying "
                        "it was refused as watermark removal and still charged (Scenario E10; prompting-craft.md §11g)")
    want_kind = "frame" if kind == "image" else "clip"
    want_kinds = ("frame", "edit") if kind == "image" else ("clip",)    # an image edit is an image call (v2.45)
    scs = sidecars if sidecars is not None else job.sidecars(relint=True)
    matches = [s for s in scs if s.get("kind") in want_kinds and s.get("prompt_sha256") == sha256_text(prompt)]
    if not matches:
        if not prompt:
            problems.append(f"empty prompt — a {want_kind} prompt is authored in "
                            f"01-script/prompts/<SHOT>.{want_kind}.prompt.md and linted first")
        else:
            problems.append(f"prompt text matches no linted {want_kind} prompt — write it in "
                            f"01-script/prompts/<SHOT>.{want_kind}.prompt.md, run "
                            f"`prompt_lint.py <file>`, then paste the PROMPT it prints verbatim "
                            f"(`gate.py preflight <SHOT> --kind {want_kind}` prints the whole call)")
        return problems, {}
    # several shots may share one motion prompt (normal in Mode B): pick the one this call binds
    best, best_probs = None, None
    for cand in matches:
        probs = _check_match(job, kind, params, policy, cand, model)
        if best_probs is None or len(probs) < len(best_probs):
            best, best_probs = cand, probs
        if not probs:
            break
    return problems + best_probs, best


def _check_match(job, kind, params, policy, match, model) -> list[str]:
    problems: list[str] = []
    if match.get("_forged"):
        problems.append(f"{match['_file']}'s sidecar does not match a fresh lint of the file — "
                        f"{'; '.join((match.get('_fails') or [])[:3])} — run prompt_lint.py; a "
                        f"hand-written .ok is not a lint")
    elif match.get("_stale"):
        problems.append(f"{match['_file']} was edited after its lint — run prompt_lint.py again")
    if model != match.get("model"):
        problems.append(f"model {model!r} ≠ linted {match.get('model')!r} for {match['_file']} — "
                        f"the model is cast in the prompt file, not at call time")
    cnt = _num(params.get("count"))
    if params.get("count") is not None and (cnt is None or cnt > float(match.get("variants") or 1)):
        problems.append(f"count {params.get('count')!r} exceeds the linted `variants: "
                        f"{match.get('variants') or 1}` for {match['_file']} — a variant multiplies "
                        f"the spend; declare it in the file")
    res = params.get("resolution")
    if res is not None and match.get("resolution") and str(res).lower() != str(match["resolution"]).lower():
        problems.append(f"resolution {res} ≠ linted {match['resolution']} — the floor is decided in "
                        f"the prompt file")
    # (v2.49.0) GPT Image 2.6 defaults to quality `low` and resolution `1k`: an omitted param is a cheap picture
    # nobody chose. The call sends exactly what the linted file states.
    if kind == "image" and model == "gpt_image_2_6":
        if res is None:
            problems.append(f"no `resolution` on gpt_image_2_6 — its default is 1k, under the floor; send the "
                            f"file's {match.get('resolution')!r}")
        q = params.get("quality")
        if q is None or str(q).lower() != str(match.get("quality") or "").lower():
            problems.append(f"quality {q!r} ≠ linted {match.get('quality')!r} — gpt_image_2_6 defaults to `low`; "
                            f"send the file's value")
        of = str(params.get("output_format") or "png").lower()
        if of != str(match.get("output_format") or "png").lower():
            problems.append(f"output_format {of!r} ≠ linted {match.get('output_format') or 'png'!r}")
        bs = _num(params.get("batch_size"))
        if params.get("batch_size") is not None and (bs is None or bs > float(match.get("variants") or 1)):
            problems.append(f"batch_size {params.get('batch_size')!r} exceeds the linted `variants: "
                            f"{match.get('variants') or 1}` — a batch multiplies the spend; declare it in the file")
    elif any(k in params for k in ("output_format", "background", "batch_size", "size", "frame_count",
                                   "frame_duration_ms")):
        problems.append(f"output_format/background/batch_size/size/frame_count/frame_duration_ms are GPT Image 2.6 "
                        f"params — on {model or 'this call'!r} nothing reads them")
    # (v2.49.0) the sound the call asks for is the sound the file decided — an omitted switch is the model's DEFAULT
    # (on, for Seedance and Kling), so a file that says `generate_audio: false` is held to it even when the call is silent
    if kind == "video" and match.get("generate_audio") is not None and str(match.get("generate_audio")).strip() != "":
        _lint_on = str(match.get("generate_audio")).strip().lower() in ("true", "1", "yes", "on")
        _aud = (_lint_module().call_shape(model or "", False, False) or {}).get("audio") or {}
        _p = _aud.get("param") or "generate_audio"
        _sent = params.get(_p)
        _eff = (bool(_aud.get("default_on")) if _sent is None else _sent != _aud.get("off", False)) if _aud.get("param") \
            else (None if _sent is None else bool(_sent))
        if _eff is not None and _eff != _lint_on:
            problems.append(f"{_p} {_sent!r}{' (omitted: the model defaults it ON)' if _sent is None else ''} ≠ linted "
                            f"generate_audio {match.get('generate_audio')!r} for {match['_file']} — the sound is decided in "
                            f"the prompt file; send what it says")
    neg = params.get("negative_prompt")
    if neg is not None and normalize_prompt(str(neg)) != normalize_prompt(match.get("negative") or ""):
        problems.append("negative_prompt differs from the linted [SUPPRESS] list")
    elif neg not in (None, "") and match.get("negative_channel") == "none":
        problems.append(f"negative_prompt sent for {match.get('model')}, which has NO negative field — the [SUPPRESS] list "
                        f"is dropped, never sent (assets/higgsfield-rates.json → negative: none; prompting-craft.md §5.1, "
                        f"§11g)")
    # ⚡ an image EDIT (v2.45): the call binds its source picture and only declared references, and an edit whose
    # result becomes a model reference needs the owner's per-shot opt-in
    if kind == "image" and match.get("kind") == "edit":
        src = str(match.get("edit_of_media") or "").strip()
        bound = [str((m_ or {}).get("value") or "").strip() for m_ in (params.get("medias") or [])
                 if isinstance(m_, dict)] if isinstance(params.get("medias"), list) else []
        if not src:
            problems.append(f"{match['_file']} names no `edit_of_media:` — the media id of the picture the call edits; "
                            f"add it and re-lint, so the gate can see the call edits THAT picture")
        elif src not in bound:
            problems.append(f"the call does not bind the edit's source picture (media {src}) — an edit made from another "
                            f"picture is a different edit")
        declared = {src} | {str(r.get("value")).strip() for r in (match.get("refs") or [])
                            if isinstance(r, dict) and r.get("value")}
        stray = [v for v in bound if v and v not in declared]
        if stray and not job.is_stills():            # the stills branch below names them for a stills job
            problems.append(f"the edit binds media {match['_file']} does not declare ({', '.join(stray)}) — every input is "
                            f"the source or a reference in `refs:`")
        problems += lane_problems(job, match)
    asp = params.get("aspect_ratio")
    want = formats().get(job.fields.get("_preset") or "", {}).get("aspect") or match.get("aspect")
    if asp and want and str(asp) != str(want):
        problems.append(f"aspect {asp} ≠ job format {want}")
    if kind == "image" and job.is_stills():
        # ⛔ Mode S has no frame gate BEFORE the spend — the brief is the only human sign-off — so
        # what the video modes leave to the preset or to later stages is checked here, at the call:
        shot = match.get("shot") or "?"
        # No preset aspect stands behind a stills job, so an omitted aspect_ratio is the model's
        # default — a square where the file said 16:9. The file's aspect must be SENT, not assumed.
        if not params.get("aspect_ratio"):
            problems.append(f"`aspect_ratio` is required on a still — {match['_file']} declares "
                            f"{match.get('aspect')!r} and a stills job has no preset aspect to fall "
                            f"back on; omitting it gets the model's default")
        if job.approved("brief") and not brief_names(job, shot):
            problems.append(f"still {shot!r} is not named in the approved brief — the brief is the "
                            f"list of stills the human signed. Add {shot} to the brief and "
                            f"re-approve it, or drop {match['_file']}")
        # ...and every input picture is one the linted file declares. A reference edit is a call
        # whose `medias` carry the picture being edited: an undeclared one is an unapproved input.
        declared = {str(r.get("value")).strip() for r in (match.get("refs") or [])
                    if isinstance(r, dict) and r.get("value")}
        if match.get("kind") == "edit" and match.get("edit_of_media"):
            declared.add(str(match["edit_of_media"]).strip())        # the picture being edited (v2.45)
        medias = params.get("medias")
        if medias is not None and not isinstance(medias, list):
            problems.append("`medias` is not a list")
        extra = []
        for m in (medias if isinstance(medias, list) else []):
            if not isinstance(m, dict):
                extra.append(f"?:{str(m)[:40]}")
            elif str(m.get("value") or "").strip() not in declared:
                extra.append(f"{m.get('role') or 'image'}:{str(m.get('value') or '').strip() or '?'}")
        if extra:
            problems.append(f"the call binds media {match['_file']} does not declare "
                            f"({', '.join(extra)}) — a reference image is declared in the prompt "
                            f"file's `refs:` with its `value:` (the media id the call binds), linted, "
                            f"then sent. `gate.py preflight {shot} --kind frame` emits exactly those")
    if kind == "video":
        shot = match.get("shot", "?")
        PL = _lint_module()
        medias = [m for m in params.get("medias") if isinstance(m, dict)] \
            if isinstance(params.get("medias"), list) else []
        raw = [(str(m.get("role") or "image").strip().lower(), str(m.get("value") or "").strip())
               for m in medias]
        # THE SHAPE — decided once, in prompt_lint.call_shape(), from the model's measured contract:
        # which slot the approved still goes in, whether an end frame can exist, which mode to send.
        linted_refs = [r for r in (match.get("refs") or []) if isinstance(r, dict) and r.get("value")]
        shape = PL.call_shape(model or "", bool(linted_refs), bool(match.get("end_frame")))
        start_role = shape["start_role"] or "start_image"
        # What each media IS. The legacy call shape sent the start frame as a lone `image`, which the
        # server coerces because nothing else is ambiguous. That reading is kept for exactly that case
        # and no other: with a second image in the call, `image` means nothing.
        imagey = [i for i, (r, _) in enumerate(raw)
                  if PL.canonical_role(r) in ("start_image", "end_image", "image_references")]
        role_of = [PL.canonical_role(r) for r, _ in raw]
        if len(imagey) == 1 and raw[imagey[0]][0] == "image":
            role_of[imagey[0]] = start_role
        ends = [raw[i][1] for i, r in enumerate(role_of) if r == "end_image"]
        starts = [raw[i][1] for i, r in enumerate(role_of) if r == "start_image"]
        if shape["reference_mode"] and starts:
            problems.append(f"{model} binds `start_image` here although {shape['why']} "
                            f"(assets/higgsfield-rates.json → call_contract) — the approved still goes "
                            f"in as `image_references`" + (" and the call needs mode "
                                                           f"{shape['mode']!r}" if shape["mode"] else ""))
        bound_as_start = [raw[i][1] for i, r in enumerate(role_of) if r == start_role]
        is_ext = match.get("gen_mode") == "video_extension"
        if is_ext:
            start_role = "video_references"
            bound_as_start = [raw[i][1] for i, r in enumerate(role_of) if r == "video_references"]
            if str(params.get("mode") or "") != "video_extension":
                problems.append(f"{match['_file']} is linted as mode video_extension — got "
                                f"{params.get('mode')!r}")
            if str(params.get("extension_mode") or "") != str(match.get("extension_mode") or ""):
                problems.append(f"extension_mode {params.get('extension_mode')!r} ≠ linted "
                                f"{match.get('extension_mode')!r}")
        elif params.get("extension_mode") is not None:
            problems.append("extension_mode sent on a call that is not a linted video_extension")
        if shape["mode"] and not is_ext and str(params.get("mode") or "") != shape["mode"]:
            problems.append(f"{model} needs mode {shape['mode']!r} for this call "
                            f"({'references only' if shape['reference_mode'] else 'frames'}) — got "
                            f"{params.get('mode')!r}" + (". Seedance only accepts a still at all in "
                            "omni_reference" if model == "seedance_2_5" else ""))
        elif shape["mode_required"] and not params.get("mode"):
            problems.append(f"{model} requires `mode` ({', '.join(shape['modes'])})")
        aud = shape["audio"]
        if params.get("generate_audio") and speaks(match) and not job.approved("audio"):
            problems.append(f"{match['_file']} carries spoken lines and `generate_audio: true`, and `audio` is not "
                            f"approved — native sound is kept since 2.49, but a model that SPEAKS a line nobody "
                            f"approved skips the voice gate (SKILL.md §2 row 6). Approve `audio` first and say "
                            f"whose voice it is")
        _guide = switches.on(job.path, "guide-audio")
        if aud.get("default_on") and not job.approved("audio") and (_guide or speaks(match)):
            if aud.get("param") and params.get(aud["param"]) != aud.get("off"):
                problems.append(f"{model} generates audio unless `{aud['param']}: {aud['off']!r}` is "
                                f"sent, and `audio` is not approved — omitting the switch is the voice "
                                f"gate routed around by a DEFAULT (found 2026-09-19). Send it, or approve "
                                f"`audio` first")
            elif not aud.get("param") and speaks(match):
                problems.append(f"{model} has native audio with no off switch — on a clip with lines it "
                                f"animates the mouth to speech nobody approved. Approve `audio` first, "
                                f"or use a roster model that can be silenced")
        takes = PL.media_roles(model or "")
        for i, r in enumerate(role_of):
            if takes and r not in takes:
                problems.append(f"media {raw[i][1] or '?'} has role {raw[i][0]!r} ({r}), which "
                                f"{model} does not take — it accepts {', '.join(sorted(takes))} "
                                f"(assets/higgsfield-rates.json → media_roles)")
        # ---- the START frame: approved, and bound AS the start frame ----------------------------
        # (v2.49.0) a `form: scene` clip with no start frame bound is built from APPROVED SHEETS instead: every
        # image it binds must be an approved character:/prop:/world:/frame: media id (scene_ref_problems)
        mid = ""
        fr = job.approved(f"frame:{shot}")
        _scene = str(match.get("form") or "").lower() == "scene" and not switches.on(job.path, "frame-led")
        if _scene and not starts:
            problems += scene_ref_problems(job, match, raw, role_of)
        elif not fr:
            problems.append(f"start frame for {shot} is not approved — the frame gate is the "
                            f"one-way door (~10× leverage, realism-qa.md §6). Approve it: "
                            f"`gate.py approve frame:{shot} --by <name> --quote \"...\" "
                            f"--artifact 02-startframes/<file> --media-id <job_or_media_id>`")
        else:
            mid = fr.get("media_id") or match.get("start_frame_media") or ""
            # (v2.66.0) the frames are signed side by side before their clips: a sheet newer than this frame
            if not job.is_eval_lane() and _storyboard().required(job.path) and \
                    not _storyboard().startframes_covers(job.path, shot):
                problems.append(f"the start frames are not signed side by side since frame:{shot} was approved — "
                                f"`board.py frames <job>`, show the page, then `gate.py approve startframes --by "
                                f"<name> --quote \"<their words>\"`. One frame at a time looks fine; a face, a light "
                                f"or a colour that drifts across them is plain only on one page "
                                f"(references/storyboarding.md §5)")
            if not mid:
                problems.append(f"frame:{shot} approval has no media id — re-approve with --media-id")
            elif mid not in bound_as_start:
                where = [raw[i][0] for i, (_, v) in enumerate(raw) if v == mid]
                problems.append(f"the call does not bind the approved start frame for {shot} "
                                f"(media id {mid}) as `{start_role}`"
                                + (f" — it is bound as {where[0]!r}. ⛔ An approved start frame in "
                                   f"another slot proves nothing about what the clip starts from"
                                   if where else " — every clip here is i2v from an approved frame "
                                                 "(prompting-craft.md §1)"))
            if len(starts) > 1:
                problems.append(f"{len(starts)} start frames bound — a clip starts from one picture")
            if shape["reference_mode"] and mid and mid in bound_as_start:
                pass  # the approved still, as a reference: measured close, not exact — the lint warned
            if match.get("start_frame_sha") and fr.get("sha") and \
                    not match["start_frame_sha"].startswith(fr["sha"]):
                problems.append(f"{match['_file']} points at a different still than the one "
                                f"approved for frame:{shot} — re-lint against the approved file")
        # ---- the END frame: approved like the start, because it fixes the picture as much -------
        emid = ""
        efr = job.approved(f"endframe:{shot}")
        if match.get("end_frame"):
            if not efr:
                problems.append(f"{match['_file']} declares an end frame and endframe:{shot} is not "
                                f"approved — an end frame fixes the picture exactly as much as a "
                                f"start frame. `gate.py approve endframe:{shot} --by <name> --quote "
                                f"\"...\" --artifact 02-startframes/<file> --media-id <id>`")
            else:
                emid = efr.get("media_id") or ""
                if not emid:
                    problems.append(f"endframe:{shot} approval has no media id — re-approve with "
                                    f"--media-id")
                elif emid not in ends:
                    problems.append(f"the linted plan for {shot} is first-and-last-frame and the call "
                                    f"does not bind the approved end frame (media id {emid}) as "
                                    f"`end_image` — without it this is a different shot from the "
                                    f"one that was linted")
                if match.get("end_frame_sha") and efr.get("sha") and \
                        not match["end_frame_sha"].startswith(efr["sha"]):
                    problems.append(f"{match['_file']} points at a different end still than the one "
                                    f"approved for endframe:{shot} — re-lint against the approved file")
        if ends and shape["end_role"] is None:
            problems.append(f"{model} cannot take an end frame in this call — {shape['why'] or 'it has no end_image'}")
        elif ends and not match.get("end_frame"):
            problems.append(f"the call binds an `end_image` that {match['_file']} does not declare — "
                            f"add `end_frame:` to the prompt file, lint it, and approve "
                            f"endframe:{shot}. An undeclared end frame is an unapproved picture")
        if len(ends) > 1:
            problems.append(f"{len(ends)} end frames bound — a clip arrives at one picture")
        # ---- every other media: a LINTED reference, or nothing ---------------------------------
        # ⛔ Until 2026-09-19 the gate checked that the approved start frame was PRESENT and never
        # looked at anything else in `medias`, so any unapproved picture could ride along on an
        # approved call — including an end frame, which steers the clip as hard as the start.
        allowed = {v for v in (mid, emid) if v} | {str(r.get("value")).strip() for r in
                                                   (match.get("refs") or [])
                                                   if isinstance(r, dict) and r.get("value")}
        extra = [f"{raw[i][0]}:{v}" for i, (_, v) in enumerate(raw) if v and v not in allowed]
        if extra:
            problems.append(f"the call binds media the linted prompt does not declare "
                            f"({', '.join(extra)}) — every input to a clip is an approved frame "
                            f"or a reference in the prompt file's `refs:`. Add it there and re-lint")
        # ---- a BLOCKING reference: approved, by media id, against an unchanged manifest ---------
        # (2026-10-23, references/blocking.md §7.) A grey render that sets the camera and the
        # positions is a picture that steers the clip; an unapproved one is the end-frame hole again.
        for r in (match.get("refs") or []):
            if not (isinstance(r, dict) and str(r.get("what") or "").strip().lower() == "blocking"):
                continue
            bap = job.approved(f"blocking:{shot}")
            if not bap:
                problems.append(f"{match['_file']} declares a blocking reference and blocking:{shot} is "
                                f"not approved — `gate.py approve blocking:{shot} --by <name> --quote "
                                f"\"...\" --artifact <the .blocking.manifest.json> --media-id <uploaded MP4>`")
                continue
            if not bap.get("media_id"):
                problems.append(f"blocking:{shot} approval has no media id — re-approve with --media-id "
                                f"(the uploaded MP4 the call binds)")
            elif str(r.get("value") or "").strip() != bap["media_id"]:
                problems.append(f"the blocking reference binds {r.get('value')!r}, and the approved "
                                f"blocking:{shot} is media {bap['media_id']} — a different render")
            mf = str(r.get("manifest") or "").strip()
            mp = mf if os.path.isabs(mf) else os.path.join(job.path, mf)
            if not mf or not os.path.isfile(mp):
                problems.append(f"the blocking reference names no readable `manifest:` ({mf or 'none'}) — "
                                f"the approval is bound to the manifest's hash")
            elif bap.get("sha") and not sha256_file(mp).startswith(bap["sha"]):
                problems.append(f"{mf} changed after blocking:{shot} was approved — the human approved a "
                                f"different build. Look at the new sheet and re-approve")
        # ---- an END STILL bound as a reference: the approved endframe:<SHOT>, by media id -------
        # (2026-10-25, references/multishot.md §3.) On a model with no true end frame the approved
        # end still rides in refs as `what: endframe`. It steers the arrival as hard as an end_image
        # does, so it is held to the same approval — an unapproved one is the end-frame hole again.
        for r in endframe_refs(match):
            if not efr:
                problems.append(f"{match['_file']} binds an end still as a reference and endframe:{shot} "
                                f"is not approved — `gate.py approve endframe:{shot} --by <name> --quote "
                                f"\"...\" --artifact 02-startframes/<file> --media-id <id>`")
                continue
            if not efr.get("media_id"):
                problems.append(f"endframe:{shot} approval has no media id — re-approve with --media-id")
            elif str(r.get("value") or "").strip() != efr["media_id"]:
                problems.append(f"the `what: endframe` reference binds {r.get('value')!r}, and the approved "
                                f"endframe:{shot} is media {efr['media_id']} — a different picture")
        if len(endframe_refs(match)) > 1:
            problems.append(f"{len(endframe_refs(match))} `what: endframe` references — a clip arrives at "
                            f"one picture")
        # ---- POSITIONAL TAGS: @Image N means the Nth image in `medias` -----------------------------
        # (2026-10-25, references/multishot.md §4.) A prompt that says "Mika corresponds to @Image 2"
        # is only true for the order prompt_lint mapped: the start still first when it is a
        # reference, then the refs in file order. The same pictures in another order put Mika's
        # face on the phone. Checked whenever the linted prompt uses a positional tag.
        if mid and not is_ext and PL.TAG_RE.search(str(match.get("prompt") or "")):
            for klass in ("image_references", "video_references", "audio_references"):
                want_seq = ([mid] if klass == "image_references" and start_role == klass else []) + \
                    [str(r["value"]).strip() for r in linted_refs
                     if PL.canonical_role(str(r.get("role") or "image").lower()) == klass
                     and str(r["value"]).strip() not in (mid, emid)]
                got_seq = [raw[i][1] for i, r in enumerate(role_of) if r == klass]
                if want_seq != got_seq:
                    tag = {"image_references": "@Image", "video_references": "@Video",
                           "audio_references": "@Audio"}[klass]
                    problems.append(f"the call binds {klass} as {got_seq} and the linted prompt's "
                                    f"{tag} N tags were mapped to {want_seq} — the tags are positional, "
                                    f"so a different order or a missing one re-points every tag after it. "
                                    f"Send `gate.py preflight {shot} --kind clip` verbatim")
        dur = _num(params.get("duration"))
        if dur is None:
            problems.append("`duration` is required on a clip call — the model default is not a "
                            "format decision; the linted file carries it")
        elif match.get("duration") is not None and dur != float(match["duration"]):
            problems.append(f"duration {params.get('duration')}s ≠ linted {match['duration']:g}s — "
                            f"the clip length is a format decision made in the prompt file")
        if policy == "per-stage-human" and speaks(match) and not job.approved("audio"):
            problems.append("per-stage-human: `audio` must be approved before a clip with lines "
                            "(a dialogue clip, or a multi-shot clip whose [SOUND] lists lines) is "
                            "generated (clients/_TEMPLATE.md §0)")
    return problems


def check_genjutsu(job, params: dict, scs: list) -> tuple:
    """A Genjutsu call (v2.46.1): generate_video on one of the four Genjutsu models, matched FIELD BY FIELD to a
    linted `<SHOT>.genjutsu.prompt.md` and to its `genjutsu:<SHOT>` approval. The call carries no start frame and
    no duration, so the spec is the whole contract: model, resolution, the ONE source video, the reference images,
    the prompt (or none), the free-generation switch. Returns (problems, matched sidecar or {})."""
    model = str(params.get("model") or "").strip()
    cands = [s_ for s_ in scs if s_.get("kind") == "genjutsu"]
    if not cands:
        return [f"{model} is Genjutsu and the job has no linted Genjutsu spec — write 01-script/prompts/<SHOT>.genjutsu"
                f".prompt.md (`prompt_lint.py --template genjutsu`), lint it, `gate.py approve genjutsu:<SHOT>`, then send "
                f"`gate.py preflight <SHOT> --kind genjutsu` verbatim"], {}
    same = [s_ for s_ in cands if s_.get("model") == model]
    if not same:
        return [f"model {model!r} matches no linted Genjutsu spec (linted: " +
                ", ".join(sorted({f"{s_.get('_file')} → {s_.get('model')}" for s_ in cands})) +
                ") — the model, full or Lite, is cast in the spec, not at call time"], {}
    best, best_p = None, None
    for c in same:
        p_ = _genjutsu_match(job, params, c)
        if best_p is None or len(p_) < len(best_p):
            best, best_p = c, p_
        if not p_:
            break
    return best_p, best


def _genjutsu_match(job, params: dict, sc: dict) -> list:
    PL = _lint_module()
    probs: list = []
    f_ = sc.get("_file") or "the spec"
    shot = sc.get("shot") or "?"
    if sc.get("_forged"):
        probs.append(f"{f_}'s sidecar does not match a fresh lint — {'; '.join((sc.get('_fails') or [])[:3])} — run "
                     f"prompt_lint.py; a hand-written .ok is not a lint")
    elif sc.get("_stale"):
        probs.append(f"{f_} was edited after its lint — run prompt_lint.py again")
    extra = sorted(k for k in params if k not in GENJUTSU_CALL_PARAMS)
    if extra:
        probs.append(f"{extra} on a Genjutsu call — models_explore lists `resolution` as its only parameter (the output "
                     f"follows the source video: no duration, aspect, mode or audio switch). An unread param is how a call "
                     f"does something nobody reviewed")
    res = params.get("resolution")
    if res is None:
        probs.append(f"no `resolution` — Genjutsu defaults to 720p, under the floor; send the spec's {sc.get('resolution')}")
    elif str(res).lower() != str(sc.get("resolution") or "").lower():
        probs.append(f"resolution {res} ≠ the spec's {sc.get('resolution')} ({f_})")
    medias = params.get("medias") if isinstance(params.get("medias"), list) else []
    if params.get("medias") is not None and not isinstance(params.get("medias"), list):
        probs.append("`medias` is not a list")
    vids, imgs, odd = [], [], []
    for m_ in medias:
        if not isinstance(m_, dict):
            odd.append(str(m_)[:40]); continue
        r_ = PL.canonical_role(str(m_.get("role") or "image"))
        v_ = str(m_.get("value") or "").strip()
        (vids if r_ == "video_references" else imgs if r_ == "image_references" else odd).append(
            v_ if r_ in ("video_references", "image_references") else f"{m_.get('role')}:{v_}")
    if odd:
        probs.append(f"media with roles Genjutsu does not take ({', '.join(odd)}) — image references and one video")
    src = str(sc.get("source_video") or "").strip()
    if len(vids) != 1:
        probs.append(f"{len(vids)} videos bound — a Genjutsu call takes exactly ONE source video ({src}, the spec's "
                     f"`source_video:`)")
    elif vids[0] != src:
        probs.append(f"the call's video is {vids[0]!r} and {f_} declares source_video {src!r} — a different "
                     f"{'driving' if sc.get('genjutsu_mode') == 'motion' else 'source'} video is a different shot")
    want = [str(r_.get("value")).strip() for r_ in (sc.get("refs") or []) if isinstance(r_, dict) and r_.get("value")]
    miss = [v for v in want if v not in imgs]
    stray = [v for v in imgs if v not in want]
    if stray:
        probs.append(f"the call binds image(s) {f_} does not declare ({', '.join(stray)}) — every reference is in the "
                     f"spec's `refs:`, linted and approved")
    if miss:
        probs.append(f"the call leaves out reference(s) {f_} declares ({', '.join(miss)}) — without them the motion "
                     f"lands on something nobody approved")
    sent = normalize_prompt(params.get("prompt") if isinstance(params.get("prompt"), str) else "")
    if sent != normalize_prompt(sc.get("prompt") or ""):
        probs.append(("the call sends a prompt and " + f_ + " has no [PROMPT] block — a Genjutsu spec sends no prompt "
                      "unless it declares one") if sent and not sc.get("prompt") else
                     f"the prompt differs from {f_}'s [PROMPT] block — send it verbatim (or none)")
    cnt = _num(params.get("count"))
    if params.get("count") is not None and (cnt is None or cnt > float(sc.get("variants") or 1)):
        probs.append(f"count {params.get('count')!r} exceeds the spec's `variants: {sc.get('variants') or 1}` — every "
                     f"Genjutsu take bills in full")
    if params.get("use_free_gens") not in (None, False) and params.get("use_free_gens") is not True:
        probs.append(f"use_free_gens {params.get('use_free_gens')!r} — true or nothing")
    elif params.get("use_free_gens") is True and sc.get("free_gens") != "prefer":
        probs.append(f"use_free_gens on a spec that says `free_gens: {sc.get('free_gens')}` — the spec decides")
    ap = job.approved(f"genjutsu:{shot}")
    if not ap:
        probs.append(f"genjutsu:{shot} is not approved — the human signs the spec (model, source video, references): "
                     f"`gate.py approve genjutsu:{shot} --by <name> --quote \"...\" --artifact {os.path.join('01-script', 'prompts', f_)}`")
    elif ap.get("sha") and not str(sc.get("file_sha256") or "").startswith(ap["sha"]):
        probs.append(f"{f_} changed after genjutsu:{shot} was approved — the human approved a different spec. "
                     f"Re-approve it")
    if not job.is_stills() and sc.get("rights") not in ("client-approved", "own"):
        probs.append(f"{f_} states rights {sc.get('rights')!r} — only client-approved material is uploaded")
    return probs


SHEET_STAGES = ("character:", "prop:", "world:", "frame:", "endframe:")


def approved_sheet_ids(job) -> dict:
    """{media_id: stage} for every approved identity sheet or still (v2.49.0, the reference route)."""
    out = {}
    for r in job.approvals():
        st = (r.get("stage") or "").lower()
        mid = (r.get("media_id") or "").strip()
        if mid and st.startswith(SHEET_STAGES):
            out[mid] = r["stage"]
    return out


def scene_ref_problems(job, match: dict, raw: list, role_of: list) -> list:
    """`form: scene` (v2.49.0): no start frame owns the picture, so the approval point is the reference sheets.
    Every image the call binds is an approved sheet; at least one is bound. Real photos used as LOOK references
    stay barred by the lint (character-and-props.md §8.7b); a generated sheet is an identity lock only."""
    probs = []
    ok_ids = approved_sheet_ids(job)
    imgs = [(raw[i][1], role_of[i]) for i in range(len(raw)) if role_of[i] == "image_references"]
    if not imgs:
        probs.append(f"{match.get('_file')} is a `form: scene` clip and binds no approved sheet — identity comes "
                     f"from `character:`/`prop:`/`world:` approvals (gate.py approve character:<NAME> --media-id …)")
    for v, _r in imgs:
        if v not in ok_ids:
            probs.append(f"image reference {v or '?'} is not an approved sheet — approve it first: "
                         f"`gate.py approve character:<NAME>|prop:<NAME>|world:<LOCATION> --by <name> --quote \"...\" "
                         f"--artifact <sheet file> --media-id {v or '<id>'}` (a scene clip's approval point is its sheets)")
    return probs


def speaks(match: dict) -> bool:
    """Does this linted clip carry scripted speech? A dialogue clip does; so does a multi-shot
    clip whose [SOUND] block lists lines (prompt_lint writes `has_speech`, references/multishot.md
    §6). Both get the voice gate: a model that speaks a line nobody approved is the same hole."""
    return (match or {}).get("type") == "dialogue" or bool((match or {}).get("has_speech"))


def endframe_refs(match: dict) -> list:
    """The `what: endframe` references of a linted clip — the approved end still bound as a
    reference on a model that has no true end frame (references/multishot.md §3)."""
    return [r for r in ((match or {}).get("refs") or [])
            if isinstance(r, dict) and str(r.get("what") or "").strip().lower() == "endframe"]


def requests_of(tool: str, tool_input) -> list[dict]:
    def as_dict(p):
        if isinstance(p, str):
            try:
                p = json.loads(p)
            except json.JSONDecodeError:
                return {"prompt": p}
        return p if isinstance(p, dict) else {}
    if not isinstance(tool_input, dict):
        return [{}]
    if tool.endswith("_batch"):
        reqs = tool_input.get("requests")
        if not isinstance(reqs, list) or not reqs:
            return []
        return [as_dict(r.get("params") if isinstance(r, dict) else {}) for r in reqs]
    return [as_dict(tool_input.get("params"))]


# ⛔ v2.45 (2026-10-29, the author: "It keeps making mp4s which it imports"; ruling C7). The scan below drops string
# literals, so the path in `ImportMedia(["…/07-edit/titles/S01.mov"])` was invisible and the import of an outside title
# movie passed silently. This pass reads the literals of a script that places media: a title, caption or disclosure
# movie named there is DENIED (a deny, not an ask: `gate.py allow resolve` does not cover it) unless its spec names an
# outside engine with a valid engine_reason or the file has a valid <file>.external.json; a literal that is only such a
# folder (a path built at run time) ASKS. The pattern is title_card.TITLE_MEDIA_RE — one definition.
PLACE_CALL_RE = re.compile(r"\b(ImportMedia|AppendToTimeline|InsertClip|ImportIntoTimeline|AddTake|"
                           r"AddItemListToMediaPool|AddItemsToMediaPool|ImportFolderFromFile)\s*\(")   # v2.50: + MediaStorage
TITLE_DIR_RE = re.compile(r"(?:^|[/\\])(?:07-edit[/\\](?:titles|disclosure)|08-captions)[/\\]?$", re.I)


def _literals(script: str) -> list:
    """Every string literal in a script, as its text (an f-string's literal parts)."""
    import ast, io, tokenize
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(script).readline):
            if t.type == tokenize.STRING:
                try:
                    out.append(str(ast.literal_eval(t.string)))
                except (ValueError, SyntaxError):
                    out.append(t.string)                       # an f-string before 3.12: its text, unresolved
            elif t.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
                out.append(t.string)
    except (tokenize.TokenError, SyntaxError):
        out = re.findall(r"[\"']([^\"'\n]+)[\"']", script)
    return out


PREVIEW_VIDEO_RE = re.compile(r"(?:^|/)PREVIEW-[^/]+\.(?:mov|mkv|mp4|mxf)$", re.I)
PREVIEW_DIR_RE = re.compile(r"(?:^|/)(?:06-music/(?:fit|bed|family)|06-sfx/conform)/?$", re.I)


def _preview_media(path: str) -> bool:
    """A file made outside Resolve as a preview: music_fit/composer/sfx_conform renders (music_fit.is_preview) and
    region_repair's PREVIEW-*.mov composite (v2.50). It is listened to or looked at, never placed in Resolve."""
    p = str(path or "").replace("\\", "/").strip()
    if not p or "\n" in p:
        return False
    if PREVIEW_DIR_RE.search(p):                            # a preview folder named as a folder (an import of all of it)
        return True
    try:
        import music_fit as _MF
        if _MF.is_preview(p):
            return True
    except Exception:                                       # noqa: BLE001
        if re.search(r"(?:^|/)(?:06-music/(?:fit|bed|family)|06-sfx/conform)/[^/]+\.\w+$", p, re.I):
            return True
    return bool(PREVIEW_VIDEO_RE.search(p))


def _title_media_ok(job, path: str) -> bool:
    """A title, caption or disclosure movie may go on the timeline only with its reason recorded."""
    import native
    import title_card as TC
    if not job:
        return False
    loc = path if os.path.isabs(path) and os.path.isfile(path) else os.path.join(job.path, TC.TITLES, os.path.basename(path))
    rec = native.jload(native.record_path(loc)) if os.path.isfile(loc) else None
    if rec and not native.check_reason(rec.get("reason")):
        return True
    stem = os.path.basename(path).split(".")[0]
    for sp in TC.specs(job.path):
        sid = os.path.basename(sp)[: -len(".title.json")]
        if stem == sid or stem.startswith(sid + "_"):
            sj = native.jload(sp) or {}
            return native.engine_of(sj) != "resolve" and not native.check_reason(sj.get("engine_reason"))
    return False


def _resolve_code(script: str) -> str:
    """The script with comments and string literals removed, so a docstring that says 'this never
    starts a render' is not a call — and a real call is not hidden by a comment on the same line."""
    import io, tokenize
    drop = {tokenize.COMMENT, tokenize.STRING, tokenize.NL, tokenize.NEWLINE}
    if hasattr(tokenize, "FSTRING_MIDDLE"):          # 3.12+: the literal text inside an f-string
        drop.add(tokenize.FSTRING_MIDDLE)
    try:
        return " ".join(t.string for t in tokenize.generate_tokens(io.StringIO(script).readline)
                        if t.type not in drop)
    except (tokenize.TokenError, SyntaxError):
        return script                 # unparseable: scan the raw text — stricter, never looser


def decide_resolve(sub: str, tool: str, tool_input) -> dict:
    """DaVinci Resolve MCP calls (RESOLVE_RE). No open job is NOT a deny here — a Resolve session is
    also research and maintenance — but it is named in the context, because an edit that belongs to no
    job is an edit nobody will find."""
    if sub in RESOLVE_READONLY:
        return {"decision": "allow", "reason": "", "context": ""}
    if os.environ.get("CINE_GATE", "").lower() == "off":
        bypass_log(f"CINE_GATE=off {tool} {json.dumps(tool_input, ensure_ascii=False, default=str)[:400]}")
        return {"decision": "pass", "reason": "",
                "context": "⚠️ CINE_GATE=off — Resolve gate bypassed by the launching shell; logged to "
                           "$CINE_HOME/bypass.log"}
    job, why_none = active_job()
    where = f"job {os.path.basename(job.path)}" if job else f"no production job open ({why_none})"
    if sub not in RESOLVE_SCRIPT_TOOLS:
        if sub in ("generate_lut", "update_dctl"):
            pre = _resolve_preapprove(job, tool, {"luts"}, [], [], where)
            if pre:
                return pre
        if job:
            job.log("ask", {"tool": tool})
        return {"decision": "ask",
                "reason": f"{tool} writes or deletes files outside the project (LUT/DCTL), or is a Resolve "
                          f"tool this gate cannot read — {where}. Confirm.", "context": ""}
    script = tool_input.get("script") if isinstance(tool_input, dict) else None
    if not isinstance(script, str) or not script.strip():
        return {"decision": "deny", "reason": f"{tool}: no script to check — refusing rather than guessing",
                "context": ""}
    code = _resolve_code(script)
    denied = [why for rx, why in RESOLVE_DENY if rx.search(code)]
    if denied:
        if job:
            job.log("deny", {"tool": tool, "problems": denied})
        return {"decision": "deny",
                "reason": f"GATE REFUSED {tool} ({where}) — the script calls what this skill routes through "
                          f"its own gate:\n  - " + "\n  - ".join(denied) +
                          "\n(The scan reads code, not comments or strings.)", "context": ""}
    r8 = _rule8_problems(script)                           # ⛔ v2.49 house rule 8: Fusion, Fairlight, titles by GUI
    if r8:
        if job:
            job.log("deny", {"tool": tool, "rule8": r8})
        return {"decision": "deny", "context": "", "reason":
                f"GATE REFUSED {tool} ({where}) — the computer-control rule: Fusion, Fairlight and native titles are "
                f"made in Resolve's own interface by computer control, never through the scripting API, which fails on "
                f"them:\n  - "
                + "\n  - ".join(r8[:8]) + (f"\n  - … and {len(r8) - 8} more" if len(r8) > 8 else "") +
                "\nDo it in Resolve's own interface with computer use (the Fusion page, the Inspector, the Effects "
                "library, the Fairlight page), then check a full-size still on screen, frame 0 and the last frame "
                "included. The API may still READ the result back (a title's words, the comp list, the Loaders). "
                "editing-and-audio.md § What runs through the API. No allowance covers this."}
    kinds = [k for rx, k in RESOLVE_ASK if rx.search(code)]
    notes = []
    if PLACE_CALL_RE.search(code):                         # ⛔ v2.45: a title movie put on the timeline (C7)
        import title_card as _TC
        lits = _literals(script)
        prev = sorted({x for x in lits if _preview_media(x)})   # ⛔ v2.50: a Python-made preview put into Resolve
        if prev:
            if job:
                job.log("deny", {"tool": tool, "preview_media": prev})
            return {"decision": "deny", "context": "", "reason":
                    f"GATE REFUSED {tool} ({where}) — it puts a PREVIEW made outside Resolve into Resolve:\n  - "
                    + "\n  - ".join(prev) + "\n(A preview is for listening and looking; a client deliverable is rebuilt in Resolve, "
                    "and the region-repair blend is a Fusion comp built by computer control.) Music: the console copy "
                    "from `music_fit.py rebuild` places the ORIGINAL track's segments, and the crossfades and fades are done "
                    "in Fairlight (07-edit/music/REBUILD.md). Region repair: build the comp from FUSION-<label>/RECIPE.md "
                    "(`region_repair.py fusion`) by computer control, then `region_repair.py qa --render`. No allowance "
                    "covers this."}
        hits = sorted({x for x in lits if _TC.TITLE_MEDIA_RE.search(x.replace("\\", "/"))})
        bad = [h for h in hits if not _title_media_ok(job, h)]
        if bad:
            if job:
                job.log("deny", {"tool": tool, "title_media": bad})
            return {"decision": "deny", "context": "", "reason":
                    f"GATE REFUSED {tool} ({where}) — it puts a title, caption or disclosure movie on the timeline:\n  - "
                    + "\n  - ".join(bad) + "\n(The house default is Resolve's or Fusion's own elements, never a movie file made outside and "
                    "imported.) The native route: "
                    "fusion_titles.py build → the .drfx installed and each title placed and its words typed BY COMPUTER "
                    "CONTROL (the computer-control rule), then read back by the API (the title is placed, never imported). "
                    "With the owner's words as the spec's engine_reason (or native.py record for a file with no spec), it passes."}
        if not hits and any(TITLE_DIR_RE.search(x.rstrip()) for x in lits):
            kinds.append("title-media")
            notes.append("it names a title, caption or disclosure folder and builds the file name at run time — the gate "
                         "cannot see which file; a title movie on the timeline needs its spec's engine and a "
                         "recorded reason (the native-elements rule)")
    if "render-settings" in kinds:
        notes.append("render settings — Resolve has aborted inside the Deliver page's render-settings widget "
                     "five times on the production Mac (crash_archive.txt: 2026-08-29 ×4 on 21.0.3, "
                     "2026-09-14 on 21.1). Save first with ProjectManager.SaveProject() in a NAMED project, "
                     "queue only, read the job back — scripts/render-mp4.py does all three")
        if job and not job.approved("lock"):
            notes.append("picture is not locked on this job — a render now is a WIP review render "
                         "(07-edit/), not a deliverable (10-export/)")
    if "destructive" in kinds:
        notes.append("deletes or quits — nothing in the scripting API undoes it")
    if "project-switch" in kinds:
        notes.append("switches projects — unsaved changes in the outgoing one can raise a dialog no script "
                     "can dismiss")
    if RESOLVE_OPAQUE_RE.search(code):
        kinds.append("opaque")
        notes.append("getattr/exec/eval/__import__ hide calls from this scan — the gate cannot vouch for "
                     "what runs")
    if sub == "run_script_unsafe":
        kinds.append("unsafe")
        notes.append("run_script_unsafe has the filesystem, network and subprocess, and a script that times "
                     "out keeps running inside the server — use run_script unless the OS is genuinely needed")
    mutates = bool(RESOLVE_MUTATE_RE.search(code))
    needs = ({"render"} if "render-settings" in kinds else set()) | ({"unsafe"} if "unsafe" in kinds else set()) \
        | ({"edit"} if mutates else set())
    if needs:
        pre = _resolve_preapprove(job, tool, needs, kinds, notes, where)
        if pre:
            return pre
    if kinds:
        if job:
            job.log("ask", {"tool": tool, "resolve": kinds})
        hint = "" if any(k in RESOLVE_NEVER_COVERED for k in kinds) else (
            "\n  (One approval can cover a session's scripts: ask the owner once, then `gate.py allow resolve "
            "--scope " + ",".join(sorted(needs or {"edit"})) + " --by <who> --quote \"<their words>\"`.)")
        return {"decision": "ask", "reason": f"{tool} ({where}):\n  - " + "\n  - ".join(notes) + hint,
                "context": "GATE: Resolve " + ", ".join(kinds) + f" · {where}"}
    if mutates:
        if job:
            job.log("pass", {"tool": tool, "resolve": "edit"})
        return {"decision": "pass", "reason": "",
                "context": f"GATE: Resolve edit · {where}" + (
                    "" if job else " — if this is production work, open the job first")}
    return {"decision": "allow", "reason": "", "context": ""}


# ⚡ THE ALLOWANCE (2026-10-26: "the gate asks me for 10 images and then again for each individual
# regen. It gets annoying to keep clicking approve" → "Batch plus regens (Recommended)", "2 per shot
# (Recommended)"). One approval, said in chat and recorded with `gate.py allow`, covers a batch of shots and
# a set number of regens of each. A covered call is still linted in full; only the click goes away. When
# a shot has used its generations, or a call names a shot the allowance does not, the gate asks again.
ALLOW_REGENS = 2


def default_regens() -> tuple:
    """(regens, source): the studio's pre-fill (0-2, wave 2c) or the house 2. A pre-fill, not a limit: an explicit
    `--regens N` (0-5) still records N, and the allowance line shows it."""
    st = _studio()
    v = st.default_regens() if st else None
    return (v, "studio.json") if v is not None else (ALLOW_REGENS, "house")
ALLOW_KINDS = {"image": ("frame", "edit"), "video": ("clip", "multishot")}   # an image edit is an image (v2.45)


def _allow_path(job) -> str:
    return os.path.join(job.gate_dir, "allowances.json")


def load_allowances(job) -> list:
    p = _allow_path(job)
    try:
        rows = json.loads(read(p)) if os.path.isfile(p) else []
        return rows if isinstance(rows, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_allowances(job, rows: list) -> None:
    os.makedirs(job.gate_dir, exist_ok=True)
    tmp = _allow_path(job) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, _allow_path(job))


def allowance_left(al: dict) -> int:
    return sum(max(0, al["per_shot"] - int((al.get("used") or {}).get(s, 0))) for s in al.get("shots", []))


def allowance_cover(job, kind: str, units: dict) -> dict | None:
    """The newest live allowance of this kind that covers every shot in the call with generations left."""
    for al in reversed(load_allowances(job)):
        # (v2.61.0) an allowance turns a call into a silent "allow"; one whose quote was never checked against the
        # session transcript covers nothing
        if al.get("revoked") or al.get("kind") != kind or al.get("verified") != "transcript":
            continue
        used = al.get("used") or {}
        if all(sh in al.get("shots", []) and int(used.get(sh, 0)) + n <= int(al["per_shot"])
               for sh, n in units.items()):
            return al
    return None


def allowance_spend(job, al_id: str, units: dict) -> dict:
    rows = load_allowances(job)
    for al in rows:
        if al.get("id") == al_id:
            used = al.setdefault("used", {})
            for sh, n in units.items():
                used[sh] = int(used.get(sh, 0)) + int(n)
            save_allowances(job, rows)
            return al
    return {}


# ⚡ THE RESOLVE ALLOWANCE (2026-10-28: "Also stop asking me to approve every script for Davinci, do it in a
# batch, like with AI gens"). One approval, said in chat and recorded with `gate.py allow resolve`, covers the
# session's Resolve scripts of the scopes it names, until it runs out of scripts or hours. A covered script is still
# scanned in full: what the gate DENIES stays denied (a started render, the AI speech generator, auto-captions), and
# what can't be undone — deletes, quits, project switches — and code the scan cannot read (getattr/exec) still ask
# every time. Kept with the job when one is open, and in CINE_HOME when none is (a Resolve session in the cloud
# often has no job on this machine).
RESOLVE_SCOPES = {"edit": "timeline edits: tracks, clips, titles, markers, grades, Fairlight presets (the mutating calls)",
                  "render": "render settings and queuing a job — never starting one",
                  "unsafe": "run_script_unsafe (the filesystem and OS) — for the inventory and file-writing toggles",
                  "luts": "writing a LUT or DCTL (generate_lut, update_dctl) — never deleting one"}
RESOLVE_ALLOW_DEFAULT = {"scope": ["edit", "render"], "scripts": 200, "hours": 12}
RESOLVE_NEVER_COVERED = ("destructive", "project-switch", "opaque", "title-media")   # v2.45: a title-folder path built at run time always asks


def _resolve_allow_path(job) -> str:
    return os.path.join(job.gate_dir if job else CINE_HOME, "resolve-allowances.json")


def load_resolve_allowances(job) -> list:
    p = _resolve_allow_path(job)
    try:
        rows = json.loads(read(p)) if os.path.isfile(p) else []
        return rows if isinstance(rows, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_resolve_allowances(job, rows: list) -> None:
    d = os.path.dirname(_resolve_allow_path(job))
    os.makedirs(d, exist_ok=True)
    tmp = _resolve_allow_path(job) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, _resolve_allow_path(job))


def _resolve_live(al: dict) -> bool:
    if al.get("revoked"):
        return False
    if int(al.get("used") or 0) >= int(al.get("scripts") or 0):
        return False
    try:
        t0 = dt.datetime.fromisoformat(str(al.get("ts")).replace("Z", "+00:00"))
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=dt.timezone.utc)
        return (dt.datetime.now(dt.timezone.utc) - t0).total_seconds() < float(al.get("hours") or 0) * 3600
    except (ValueError, TypeError):
        return False


def resolve_allowance_cover(job, needs: set) -> tuple:
    """(allowance, where) — the newest live Resolve allowance whose scopes include every need; the job's first."""
    for owner in ([job] if job else []) + [None]:
        for al in reversed(load_resolve_allowances(owner)):
            if _resolve_live(al) and al.get("verified") == "transcript" and needs <= set(al.get("scope") or []):
                return al, owner
    return None, None


def resolve_allowance_spend(owner, al_id: str) -> dict:
    rows = load_resolve_allowances(owner)
    for al in rows:
        if al.get("id") == al_id:
            al["used"] = int(al.get("used") or 0) + 1
            save_resolve_allowances(owner, rows)
            return al
    return {}


def resolve_allowance_line(al: dict) -> str:
    left = max(0, int(al.get("scripts") or 0) - int(al.get("used") or 0))
    state = "revoked" if al.get("revoked") else ("expired" if not _resolve_live(al) else f"{left} script(s) left")
    return (f"{al.get('id')} resolve [{', '.join(al.get('scope') or [])}] · {state} · {al.get('hours')} h from "
            f"{str(al.get('ts'))[:16]} · {al.get('by')}: \"{(al.get('quote') or '')[:60]}\" [{al.get('verified')}]")


def _resolve_preapprove(job, tool: str, needs: set, kinds: list, notes: list, where: str):
    """The decision for a covered Resolve call, or None."""
    if any(k in RESOLVE_NEVER_COVERED for k in kinds):
        return None
    al, owner = resolve_allowance_cover(job, needs)
    if not al:
        return None
    al = resolve_allowance_spend(owner, al["id"])
    if job:
        job.log("preapproved", {"tool": tool, "resolve_allowance": al.get("id"), "needs": sorted(needs)})
    return {"decision": "preapproved",
            "reason": f"Resolve allowance {al.get('id')} ({al.get('by')}: \"{(al.get('quote') or '')[:80]}\")",
            "context": f"GATE: Resolve {', '.join(sorted(needs))} pre-approved · {resolve_allowance_line(al)} · {where}"
                       + ("".join(f"\n  - {n}" for n in notes) if notes else "")}


def allowance_line(al: dict) -> str:
    shots = al.get("shots", [])
    names = ", ".join(shots) if len(shots) <= 6 else f"{shots[0]}…{shots[-1]} ({len(shots)} shots)"
    state = "revoked" if al.get("revoked") else f"{allowance_left(al)}/{al['per_shot'] * len(shots)} left"
    return (f"{al['id']} {al['kind']}: {names} · {al.get('regens')} regen(s) each · {state} · {al.get('by')}"
            f"{'' if al.get('verified') == 'transcript' else ' · UNVERIFIED quote'}")


def denied_preset(tool_input) -> str | None:
    """A preset the skill refuses to run (assets/aerial-moves.json `denied_presets`), wherever its id sits."""
    try:
        den = json.load(open(os.path.join(os.path.dirname(HERE), "assets", "aerial-moves.json"), encoding="utf-8")).get("denied_presets") or {}
    except (OSError, ValueError):
        return None
    blob = json.dumps(tool_input, default=str)
    return next((why for pid, why in den.items() if pid in blob), None)


def upload_class(tool: str, tool_input) -> str | None:
    """'media' | 'identity' when the call sends media to a vendor (v2.45), else None. manage_reference_elements reads
    with list/get; any other action — create, or one this gate does not know — is an identity upload (fails closed)."""
    mu = UPLOAD_RE.match(tool or "")
    if not mu:
        return None
    sub = mu.group(1)
    if sub == "manage_reference_elements":
        ti = tool_input if isinstance(tool_input, dict) else {}
        act = str(ti.get("action") or ("get" if ti.get("element_id") else "list")).strip().lower()
        if act in REF_ELEMENT_READS and not ti.get("medias"):
            return None
        return "identity"
    return "identity" if sub in IDENTITY_TOOLS else "media"


def model_family(model) -> str:
    """'kling' for kling3_0 and kling-video-v3_0 alike; the vendor word that leads a model id."""
    m = re.match(r"[a-z]+", str(model or "").strip().lower())
    return m.group(0) if m else ""


def lane_problems(job: "Job", sc: dict) -> list:
    """What a linted prompt still needs before ANY connector may spend it (v2.45): an edit whose result becomes a model
    reference needs the owner's per-shot opt-in; a clip needs its approved start frame."""
    out, shot = [], sc.get("shot") or "?"
    if sc.get("kind") == "edit" and sc.get("use") == "target":
        tap = job.approved(f"target:{shot}")
        if not tap:
            out.append(f"{sc.get('_file')} is `use: target` — its result becomes a MODEL REFERENCE, and an AI-edited target "
                       f"frame of our own footage is allowed only as a gated per-shot opt-in: "
                       f"`gate.py approve target:{shot} --by <name> --quote \"...\" [--artifact <the source frame>]`")
        elif tap.get("sha") and sc.get("edit_of_sha") and not str(sc["edit_of_sha"]).startswith(tap["sha"]):
            out.append(f"target:{shot} was approved for a different source picture than {sc.get('edit_of')} — the opt-in "
                       f"names the frame that may be edited; re-approve it for this one")
    if sc.get("kind") == "clip" and not job.approved(f"frame:{shot}") and \
            (str(sc.get("form") or "").lower() != "scene" or sc.get("start_frame")):
        out.append(f"start frame for {shot} is not approved — the frame gate holds on every connector "
                   f"(`gate.py approve frame:{shot} --by <name> --quote \"...\" --artifact <file> --media-id <id>`)")
    return out


def decide_kling(job: "Job", sub: str, tool: str, tool_input, jobname) -> dict:
    """Kling's own connector (v2.45): the call's `prompt` argument must BE a linted Kling prompt of the right kind."""
    PL = _lint_module()
    ti = tool_input if isinstance(tool_input, dict) else {}
    args = {}
    for a in ti.get("arguments") or []:
        if isinstance(a, dict) and a.get("name"):
            args[str(a["name"])] = a.get("value")
    prompt = args.get("prompt") if isinstance(args.get("prompt"), str) else \
        (ti.get("prompt") if isinstance(ti.get("prompt"), str) else "")
    kinds = ("frame", "edit") if sub in KLING_IMAGE_TOOLS else ("clip",)
    problems, sc = [], None
    if job.is_stills() and sub in KLING_VIDEO_TOOLS:
        problems.append(f"stills job (Mode S): {sub} is not part of this lane — a stills job makes images only")
    elif job.is_stills():
        problems += brief_problems(job)
    elif not job.approved("script"):
        problems.append("`script` is not approved — the script review is the one that saves the most money "
                        "(review-and-approval.md §10)")
    if PL.WATERMARK_RE.search(json.dumps(ti, ensure_ascii=False, default=str)):
        problems.append("the call carries the word 'watermark' — a request carrying it was refused as watermark removal "
                        "and still charged (Scenario E10; prompting-craft.md §11g)")
    if not prompt.strip():
        problems.append(f"{tool} carries no `prompt` argument — Kling's connector is gated like generate_*: its prompt is "
                        f"the text of a prompt file prompt_lint passes, verbatim, written for a Kling model" +
                        (". Motion control from a driving clip has no linted form yet"
                         if sub == "motion_control" else ""))
    else:
        h = sha256_text(normalize_prompt(prompt))
        cands = [s for s in job.sidecars(relint=True) if s.get("prompt_sha256") == h]
        fit = [s for s in cands if s.get("kind") in kinds]
        fam = model_family(ti.get("model") or "kling") or "kling"
        same = [s for s in fit if model_family(s.get("model")) == fam]
        if not cands:
            problems.append(f"the prompt matches no linted prompt — write it in 01-script/prompts/<SHOT>.{kinds[0]}.prompt.md "
                            f"for a Kling model (its ceiling, negatives and modes are Kling's), run prompt_lint.py, and send "
                            f"the PROMPT it prints verbatim")
        elif not fit:
            problems.append(f"the prompt is linted as a {cands[0].get('kind')} prompt ({cands[0].get('_file')}); {sub} needs "
                            f"a {' or '.join(kinds)} prompt")
        elif not same:
            problems.append(f"the prompt is linted for {fit[0].get('model')} ({fit[0].get('_file')}), not for a {fam} model — "
                            f"a prompt is written to its model's ceiling, negative channel and modes; lint a copy cast on "
                            f"the Kling model")
        else:
            sc = same[0]
            if sc.get("_forged"):
                problems.append(f"{sc['_file']}'s sidecar does not match a fresh lint — "
                                f"{'; '.join((sc.get('_fails') or [])[:3])}")
            elif sc.get("_stale"):
                problems.append(f"{sc['_file']} was edited after its lint — run prompt_lint.py again")
            problems += lane_problems(job, sc)
            neg = args.get("negative_prompt")
            if neg not in (None, ""):
                if sc.get("negative_channel") == "none":
                    problems.append(f"negative_prompt sent for {sc.get('model')}, which has no negative field — the "
                                    f"[SUPPRESS] list is dropped, never sent (prompting-craft.md §5.1, §11g)")
                elif normalize_prompt(str(neg)) != normalize_prompt(sc.get("negative") or ""):
                    problems.append("negative_prompt differs from the linted [SUPPRESS] list")
    if problems:
        job.log("deny", {"tool": tool, "problems": problems})
        return {"decision": "deny",
                "reason": f"GATE REFUSED {tool} on job {jobname} (no unlinted route, v2.45):\n  - " + "\n  - ".join(problems),
                "context": ""}
    dup = duplicate_of(job, request_hashes(tool, tool_input))
    if dup:
        job.log("ask", {"tool": tool, "note": "duplicate request", "first": dup.get("ts")})
        return {"decision": "ask", "reason": duplicate_reason(dup), "context": ""}
    job.log("ask", {"tool": tool, "matched": sc.get("_file")})
    return {"decision": "ask",
            "reason": f"{tool}: the prompt is {sc.get('_file')}'s, linted for {sc.get('model')} — Kling's connector also "
                      f"carries a model, inputs and a duration this gate cannot read; check them against the file "
                      f"({sc.get('resolution') or '?'}, {sc.get('duration') or '-'}s) and confirm the spend",
            "context": f"GATE: Kling route · {sc.get('shot')} {sc.get('kind')} · {sc.get('_file')}"}


def request_hashes(tool: str, tool_input) -> list:
    """One hash per generation the call asks for (probes excluded) — the identity the duplicate guard compares."""
    sub = (tool or "").split("__")[-1]
    km = KLING_RE.match(tool or "")
    if km and km.group(1) in KLING_ROUTE:
        ti = tool_input if isinstance(tool_input, dict) else {}
        core = {k: v for k, v in ti.items() if k not in KLING_VOLATILE}
        return [sha256_text(json.dumps({"t": km.group(1), "p": core}, sort_keys=True, ensure_ascii=False, default=str))]
    base = re.sub(r"_batch$", "", sub)
    return [sha256_text(json.dumps({"t": base, "p": p}, sort_keys=True, ensure_ascii=False, default=str))
            for p in requests_of(tool, tool_input) if isinstance(p, dict) and p and p.get("get_cost") is not True]


# ---- THE ENVELOPE AS A CAP (v2.62.0) ---------------------------------------------------------------------------
# The CHECKPOINT's `Budget: envelope N cr` was checked as TEXT only: a job with a 900-credit envelope could spend
# 2,000 and every linted call still passed under the gated or standing policy. Each submission now records what it
# cost by the rate table, and a call that would take the job past its envelope asks instead of passing.
def _price_request(base: str, p: dict):
    """Credits for one request by assets/higgsfield-rates.json, or None when it cannot be priced (an unknown or
    per-call model, no duration, an unknown resolution)."""
    try:
        import rate_card  # noqa: E402  (stdlib only)
        model = str(p.get("model") or "")
        res = str(p.get("resolution") or "").lower()
        n = _num(p.get("count")) or 1.0
        if base == "generate_video":
            e = rate_card.load_table().get(model) or {}
            if not res and len(e) == 1:
                res = next(iter(e))
            en, dur = e.get(res), _num(p.get("duration"))
            if not en or dur is None or rate_card.per_call(en):
                return None
            return float(en["cr_per_s"]) * dur * n
        if base == "generate_image":
            e = rate_card.load_image_table().get(model) or {}
            if not res and len(e) == 1:
                res = next(iter(e))
            en = e.get(res)
            n *= _num(p.get("batch_size")) or 1.0     # (v2.72.0) a batch of N pictures bills N (review, Grok)
            return float(en["cr_per_image"]) * n if en else None
    except (SystemExit, Exception):      # pricing is advisory; it never crashes the hook
        return None
    return None


def request_credits(tool: str, tool_input) -> list:
    """One price (or None) per generation the call asks for, aligned with request_hashes()."""
    if KLING_RE.match(tool or ""):
        return [None]                     # Kling bills its own account; the envelope is in Higgsfield credits
    base = re.sub(r"_batch$", "", (tool or "").split("__")[-1])
    return [_price_request(base, p) for p in requests_of(tool, tool_input)
            if isinstance(p, dict) and p and p.get("get_cost") is not True]


def job_spent(job: "Job") -> tuple[float, int]:
    """(credits recorded, submissions with no price) for the job."""
    total, unpriced = 0.0, 0
    for r in _jsonl(_submitted_path(job)):
        c = r.get("credits")
        if isinstance(c, (int, float)):
            total += float(c)
        else:
            unpriced += 1
    return total, unpriced


def billable(tool: str) -> bool:
    """(wave 2c) A Higgsfield generate call: what the envelope and the studio's monthly ceiling count. Kling bills its
    own account; another service's tool of the same name is not ours (the same connector test decide() uses)."""
    if not TOOL_RE.match(tool or "") or KLING_RE.match(tool or ""):
        return False
    return connector_kind(tool) != "other" or higgsfield_only((tool or "").split("__")[-1])


def _studio():
    try:
        import studio  # noqa: E402
        return studio
    except Exception:                                    # noqa: BLE001 — no studio module: 3.0 behaviour
        return None


def budget_asks(tool: str, tool_input) -> dict:
    """PURE (no writes): the job's envelope and the studio's monthly ceiling for this call.
    {"fires": bool, "lines": [str], "why": [str]}. Nothing for a call that is not billable; a spend-class tool (which
    always asks anyway, and has no price) gets the month line only, never `fires` (PLAN-SETTINGS-v3 §A, §B)."""
    out = {"fires": False, "lines": [], "why": [], "deny": None}
    spend_class = bool(SPEND_RE.match(tool or "")) and not KLING_RE.match(tool or "")
    if not (billable(tool) or spend_class):
        return out
    st = _studio()
    c, cprob = st.ceiling_state() if st else (None, None)
    mt = st.month_total() if st and (c is not None or cprob) else None
    if spend_class:
        if mt is not None:
            over = c is not None and mt["credits"] >= c
            out["lines"].append(st.month_line(mt, c) + (" · the month is ALREADY at or over the ceiling" if over else ""))
        return out
    prices = request_credits(tool, tool_input)
    if not prices:                                       # get_cost probes only: nothing is spent
        return out
    this = sum(p_ for p_ in prices if p_ is not None)
    unknown = any(p_ is None for p_ in prices)
    job, _ = active_job()
    if job:
        fields = job.fields or (parse_kv(read(job.checkpoint)) if os.path.isfile(job.checkpoint) else {})
        env = ENVELOPE_RE.search(fields.get("budget") or "")
        if env and float(env.group(1)) == 0:
            # (3.1 build review 1, Grok) envelope 0 = a concept-only job: the docs promise it cannot spend, so a paid
            # call is refused, not asked (a confirm would have spent)
            out["fires"] = True
            out["deny"] = (f"job {fields.get('job')} has a budget envelope of 0 cr (concept only), so nothing spends. "
                           f"Price the job and set the checkpoint's `Budget:` envelope with the client's OK first "
                           f"(START-HERE.md, From a concept to the first paid picture)")
        if env:
            envelope = float(env.group(1))
            spent, unpriced = job_spent(job)
            line = (f"envelope {envelope:g} cr · recorded {spent:g} cr" + (f" (+{unpriced} unpriced)" if unpriced else "")
                    + f" · this call {this:g} cr" + (" + unpriced" if unknown else ""))
            out["lines"].append(line)
            if spent + this > envelope or (unknown and spent >= envelope):     # the 3.0 predicate, unchanged
                out["fires"] = True
                out["why"].append(f"this call takes job {fields.get('job')} past its envelope ({line}); raise the "
                                  f"CHECKPOINT's `Budget:` envelope with the client's OK first, or confirm it")
    if cprob:
        out["fires"] = True
        out["why"].append(cprob + "; confirm this call, or fix studio.json with `studio.py set`")
    elif c is not None:
        voice = (tool or "").split("__")[-1].startswith("generate_audio")
        mline = (f"studio month {mt['month']} (UTC) {mt['credits']:g} / {c:g} cr · this call {this:g} cr"
                 + (" + unpriced" if unknown else ""))
        out["lines"].append(mline)
        if mt["credits"] + this > c or mt["unreadable"] or (unknown and (mt["credits"] >= c if voice else True)):
            out["fires"] = True
            reason = ("an unpriced call while a monthly ceiling is set" if unknown and mt["credits"] + this <= c
                      and not voice and not mt["unreadable"] else
                      f"{mt['unreadable']} spend record(s) cannot be read" if mt["unreadable"] else
                      "this call takes the studio's month past its ceiling")
            out["why"].append(f"{reason} ({mline}); confirm it, or raise the ceiling with the person's own words "
                              f"(`studio.py set --by … --quote …`)")
    return out


def budget_merge(d: dict, b: dict, tool: str = "") -> dict:
    """The merge rule (PLAN-SETTINGS-v3 §A): allow and deny are never touched; pass/preapproved become ASK when a budget
    stop fires; an existing ask keeps its own reason, with the budget appended; the lines ride along as context."""
    dec = d.get("decision")
    if dec in ("pass", "preapproved", "ask") and b.get("deny"):
        job, _ = active_job()
        if job:
            job.log("deny", {"tool": tool, "note": "budget", "why": b["deny"]})
        return {"decision": "deny", "reason": f"{tool}: {b['deny']}", "context": ""}
    if dec in ("allow", "deny") or not (b.get("lines") or b.get("why")):
        return d
    ctx = d.get("context") or ""
    ctx2 = (ctx + " · " if ctx else "") + " · ".join(b["lines"])
    if b.get("fires") and dec in ("pass", "preapproved"):
        job, _ = active_job()
        if job:
            job.log("ask", {"tool": tool, "note": "budget", "why": b["why"]})
        return {"decision": "ask", "reason": f"{tool}: budget stop — " + " | ".join(b["why"]), "context": ctx2}
    if dec == "ask" and b.get("fires"):
        return {**d, "reason": (d.get("reason") or "") + " · ALSO a budget stop: " + " | ".join(b["why"]),
                "context": ctx2}
    if dec == "ask" and b.get("lines"):
        # (build review 1, Grok) the person sees the month on the prompt itself, not only in the agent's context
        return {**d, "reason": (d.get("reason") or "") + " · " + " · ".join(b["lines"]), "context": ctx2}
    return {**d, "context": ctx2}


def envelope_check(tool: str, tool_input, d: dict) -> dict:
    """(v2.62.0) kept for callers: the budget stops (envelope and studio ceiling) merged into a decision."""
    return budget_merge(d, budget_asks(tool, tool_input), tool)


def _submitted_path(job: "Job") -> str:
    return os.path.join(job.gate_dir, "submitted.jsonl")


def duplicate_of(job: "Job", hashes: list) -> dict | None:
    """The most recent submission in this job of any of these hashes, within DUP_WINDOW_S, or None."""
    if not hashes:
        return None
    t = time.time()
    unconfirmed = None
    for r in reversed(_jsonl(_submitted_path(job))):
        try:
            age = t - float(r.get("epoch") or 0)
        except (TypeError, ValueError):
            continue
        if r.get("hash") in hashes and 0 <= age <= DUP_WINDOW_S:
            if not r.get("unconfirmed"):
                return {**r, "_age_min": age / 60.0}        # a real job id wins over a later failure (review 1, Sonnet)
            unconfirmed = unconfirmed or {**r, "_age_min": age / 60.0}
    return unconfirmed


def duplicate_reason(dup: dict) -> str:
    if dup.get("unconfirmed"):
        # (v2.70.0, Wave 5 A14) the call failed or timed out: the vendor may still have accepted and charged it
        return (f"an identical request failed or timed out at {dup.get('ts')} ({dup.get('_age_min', 0):.0f} min ago) with no "
                f"job id back — it may still have reached the vendor and been charged. Check first (Higgsfield: "
                f"show_generations / jobs_wait; Kling: query_tasks); a resubmitted timeout is paid twice. Confirm only "
                f"if nothing is running")
    ids = ", ".join(dup.get("ids") or []) or "its job id is in the tool result"
    return (f"already submitted at {dup.get('ts')} ({dup.get('_age_min', 0):.0f} min ago; job {ids}); poll that job instead "
            f"— Higgsfield: jobs_wait / show_generations; Kling: query_tasks. An identical request resubmitted after a "
            f"timeout is paid twice (Scenario E11). Confirm only if you want another take of the same request")


ID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
ID_KEY_RE = re.compile(r"\"(?:job_id|jobId|generation_id|generationId|task_id|taskId|id)\"\s*:\s*\"([A-Za-z0-9_-]{6,})\"")


def record_submission(job: "Job", tool: str, tool_input, tool_response) -> int:
    """PostToolUse: log what reached the vendor, keyed by request hash, with the job ids the vendor returned. A response
    that carries no id (an error, a refusal) records nothing — only a real submission makes a duplicate."""
    out: list = []

    def walk(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(tool_response)
    blob = "\n".join(out) + "\n" + json.dumps(tool_response, ensure_ascii=False, default=str)
    ids = []
    for rx in (ID_KEY_RE, ID_RE):
        for mm in rx.finditer(blob or ""):
            v = mm.group(1) if mm.groups() else mm.group(0)
            if v not in ids:
                ids.append(v)
    if not ids and not job.is_eval_lane():
        return 0
    # (v2.72.0, build review 3, Sonnet) in the evaluation lane a success with no recognisable id still records: a call
    # that returned anything confirms its reservation, so it can never be released and spent again
    hs = request_hashes(tool, tool_input)
    prices = request_credits(tool, tool_input)
    prices = prices if len(prices) == len(hs) else [None] * len(hs)
    try:
        os.makedirs(job.gate_dir, exist_ok=True)
        with open(_submitted_path(job), "a", encoding="utf-8") as fh:
            for h, c in zip(hs, prices):
                fh.write(json.dumps({"ts": now(), "epoch": time.time(), "tool": tool, "hash": h, "ids": ids[:6],
                                     "credits": c, **({} if ids else {"noid": True})}, ensure_ascii=False) + "\n")
    except OSError:
        return 0
    studio_events(job, tool, prices, "submitted")
    return len(hs)


def studio_events(job: "Job", tool: str, prices: list, kind: str) -> int:
    """(wave 2c) One studio spend event per request, for Higgsfield only (Kling bills its own account). A recorder:
    it never blocks; nothing is written without a studio folder."""
    if not billable(tool):
        return 0
    st = _studio()
    if not st:
        return 0
    jn = (job.fields or {}).get("job") or os.path.basename(job.path)
    return sum(1 for c in prices if st.record_spend(jn, tool, c, kind))


REJECTED_RE = re.compile(r"\b(?:HTTP|status|error|code)[\s:=]*4(?:00|01|03|04|09|22)\b|\bvalidation (?:error|failed)\b|"
                         r"\binvalid (?:param|argument|value|request)\w*|\bbad request\b|\bunprocessable\b|"
                         r"\binsufficient credits?\b", re.I)
TIMEOUT_RE = re.compile(r"\btim(?:ed|e)[ -]?out\b|\btimeout\b|\bdeadline\b|\bconnection (?:reset|closed|aborted)\b", re.I)
# (v2.72.0) only these release an evaluation reservation automatically; these others may have billed and never do
EVAL_RELEASE_RE = re.compile(r"\b(?:HTTP|status|error|code)[\s:=]*4(?:00|22)\b|\bvalidation (?:error|failed)\b|"
                             r"\binvalid (?:param|argument|value|request)\w*|\bbad request\b|\bunprocessable\b", re.I)
EVAL_MAYBE_BILLED_RE = re.compile(r"\b4(?:01|03|09)\b|\binsufficient credits?\b|\bcharged\b|\bbilled\b", re.I)


def record_unconfirmed(job: "Job", tool: str, tool_input, error) -> int:
    """PostToolUseFailure (v2.70.0, Wave 5 A14): a generate call that failed or timed out leaves no job id, so the
    success recorder logs nothing and an identical retry passed unguarded. Log it as UNCONFIRMED: the next identical
    request asks first. A PreToolUse alone still records nothing (a denied or abandoned call is no spend)."""
    hs = request_hashes(tool, tool_input)
    err_ = str(error or "")
    if not hs or (REJECTED_RE.search(err_) and not TIMEOUT_RE.search(err_)):
        # a timeout is never a rejection, whatever numbers its text carries: a false ask costs a click, a missed
        # record costs a second charge (build review 2, Sonnet)
        if hs and job.is_eval_lane() and EVAL_RELEASE_RE.search(err_) and not EVAL_MAYBE_BILLED_RE.search(err_):
            # (v2.72.0) a clear validation refusal billed nothing: release ONE unconfirmed reservation whose request
            # list is exactly this call's, under the lock (build review 3: never a sibling or a larger batch; never on a
            # 401/403/409 or "insufficient credits", which may have billed)
            with eval_lock(job) as _lk:
                if _lk:
                    for r_ in reversed(_eval_reservations(job)):
                        if list(r_.get("hashes") or []) == list(hs) and not _eval_confirmed(job, r_):
                            eval_release(job, r_["id"], f"instant vendor rejection: {err_[:120]}")
                            break
        return 0          # an instant validation refusal (a 4xx, bad params) charged nothing (build review 1, Sonnet)
    prices = request_credits(tool, tool_input)     # a timeout may have been billed: the envelope counts it (Grok)
    prices = prices if len(prices) == len(hs) else [None] * len(hs)
    try:
        os.makedirs(job.gate_dir, exist_ok=True)
        with open(_submitted_path(job), "a", encoding="utf-8") as fh:
            for h, c in zip(hs, prices):
                fh.write(json.dumps({"ts": now(), "epoch": time.time(), "tool": tool, "hash": h, "ids": [],
                                     "unconfirmed": True, "credits": c, "error": str(error or "")[:200]},
                                    ensure_ascii=False) + "\n")
    except OSError:
        return 0
    studio_events(job, tool, prices, "unconfirmed")      # a timeout may have billed: the month counts it too
    return len(hs)


def posthook_records(tool: str) -> bool:
    """Whether the PostToolUse recorder logs this call: a generate call on a named server or on a uuid connector the
    settings do not name as another service (v2.59.0: another service's generate_image is not a Higgsfield
    submission), or a Kling generation. (v2.59.2) An UNNAMED connector's call is recorded too: it reached here
    only because a person approved the ask, and if it was a Higgsfield spend the double-spend guard must know."""
    km = KLING_RE.match(tool or "")
    return bool((TOOL_RE.match(tool or "") and connector_kind(tool) != "other") or
                (km and km.group(1) in KLING_ROUTE))


def cmd_posthook(_a) -> int:
    """PostToolUse entrypoint: records a generate request the vendor accepted. Never blocks, never prints, fails open —
    it guards against a double spend, it is not the gate."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        tool = str((data or {}).get("tool_name") or "")
        if isinstance(data, dict):
            _record_transcript(data)                   # (3.1) the job is this session's
        failed = getattr(_a, "failed", False) or (data or {}).get("hook_event_name") == "PostToolUseFailure"
        if posthook_records(tool):
            job, _ = active_job()
            if job and failed:
                record_unconfirmed(job, tool, data.get("tool_input") or {}, data.get("error") or data.get("tool_response"))
            elif job:
                record_submission(job, tool, data.get("tool_input") or {}, data.get("tool_response"))
    except Exception:            # noqa: BLE001 — a recorder must never stop the session
        pass
    return 0


def decide(tool: str, tool_input, commit: bool = True, commit_previz: bool = True) -> dict:
    """Returns {"decision": allow|deny|ask|pass, "reason": str, "context": str}. `pass` = a
    generate/spend call that clears the gate: context is added and the NORMAL permission flow is
    left in place (no pre-approval). `allow` = a tool the gate has no opinion on (silent).
    (wave 2c) commit=False: a budget stop will turn a pass into an ask, so a covered call does not use up its allowance
    and an evaluation-lane call reserves as PENDING. It changes no decision. Previz always counts (a cap, review 3)."""
    rm = RESOLVE_RE.match(tool or "")
    if rm:
        return decide_resolve(rm.group(1), tool, tool_input)
    ck = connector_kind(tool)
    other_note = ""
    if ck == "other":                 # the settings say this uuid is another service (v2.59.0)
        if not higgsfield_only((tool or "").split("__")[-1]):
            return {"decision": "allow", "reason": "", "context": ""}
        ck, other_note = "higgsfield", (f"{tool}: the connector settings name this uuid as another service, but only "
                                        f"Higgsfield serves this tool, so it is gated as Higgsfield (v2.61.0). If the "
                                        f"settings are wrong: `python3 scripts/gate.py connectors --higgsfield <uuid>`.")
    always = DENY_ALWAYS_RE.match(tool or "")
    if always:
        return {"decision": "deny",
                "reason": f"{tool} is refused even inside an open job: {DENY_ALWAYS[always.group(1)]}.",
                "context": ""}
    scm = SCENARIO_RE.match(tool or "")
    if scm:
        if SCENARIO_DENY_RE.search(scm.group(1)):
            return {"decision": "deny",
                    "reason": f"{tool}: {SCENARIO_WHY} — no Scenario model run, generation or upload from this skill, "
                              f"inside a job or out. The gated route is a roster model through generate_* with a linted "
                              f"prompt (references/ai-generation.md); a plate edit is seedance_2_5 mode video_edit.",
                    "context": ""}
        return {"decision": "allow", "reason": "", "context": ""}
    m = TOOL_RE.match(tool or "")
    spend = SPEND_RE.match(tool or "")
    publish = PUBLISH_RE.match(tool or "")
    kl = KLING_RE.match(tool or "")
    kroute = kl.group(1) if kl and kl.group(1) in KLING_ROUTE else None
    up = upload_class(tool, tool_input)
    if spend and spend.group(1) in FREE_ACTIONS:
        act = tool_input.get("action") if isinstance(tool_input, dict) else None
        if isinstance(act, str) and act.strip().lower() in FREE_ACTIONS[spend.group(1)]:
            return {"decision": "allow", "reason": "", "context": ""}
    if not (m or spend or publish or kroute or up):
        vn = vendor_tool_name(tool, ck)
        # a known upload-class tool called in a read mode (manage_reference_elements list/get) is not unknown
        if vn is not None and not is_read_name(vn) and not UPLOAD_RE.match(tool or ""):
            return {"decision": "ask",
                    "reason": f"{tool}: the gate does not know this tool. It is not a read and not in any class it "
                              f"decides on (generate, spend, publish, upload), so it may spend, publish or delete. "
                              f"Confirm it yourself; then add it to the right class in scripts/gate.py (v2.61.0).",
                    "context": other_note}
        return {"decision": "allow", "reason": "", "context": ""}
    if spend and spend.group(1) == "execute_preset":
        why = denied_preset(tool_input)
        if why:
            return {"decision": "deny", "reason": f"{tool}: {why}.", "context": ""}
    if ck == "unknown":
        cu = CONNECTOR_UUID_RE.match(tool).group(1)
        note_seen_connector(cu.lower(), tool)
        return {"decision": "ask",
                "reason": f"{tool}: connector {cu} is not in the connector settings, so the gate cannot tell whether this "
                          f"call spends on your Higgsfield account or is another service's tool of the same name. "
                          f"If it is Higgsfield: `python3 scripts/gate.py connectors --higgsfield {cu}`. If not: "
                          f"`python3 scripts/gate.py connectors --other {cu}`. Until then every such call asks.",
                "context": ""}
    if os.environ.get("CINE_GATE", "").lower() == "off":
        bypass_log(f"CINE_GATE=off {tool} {json.dumps(tool_input, ensure_ascii=False, default=str)[:400]}")
        return {"decision": "pass", "reason": "",
                "context": "⚠️ CINE_GATE=off — generation gate bypassed by the launching shell; "
                           "logged to $CINE_HOME/bypass.log, and reconcile will report it"}
    job, why_none = active_job()
    if not job:
        return {"decision": "deny",
                "reason": f"No production job is open ({why_none}), so nothing spends" +
                          (" and no media leaves the machine" if up else "") + ". Open one: "
                          f"`python3 scripts/gate.py open <job-dir>` (it validates "
                          f"00-brief/CHECKPOINT.md and the client profile first). This is the "
                          f"'deny everything' setting chosen 2026-09-06 after a run wasted credits on "
                          f"ungated generations.", "context": ""}
    problems = job.validate()
    if problems:
        return {"decision": "deny",
                "reason": "The open job's checkpoint no longer validates:\n  - " +
                          "\n  - ".join(problems) + "\nFix and re-run `gate.py open`.",
                "context": ""}
    policy = job.policy or (job.fields.get("policy") or "").lower()
    jobname = job.fields.get("job")
    stills = job.is_stills()
    eval_lane = job.is_eval_lane()
    # (v2.72.0) once evaluated, always evaluated: a job with an `eval` row whose lane line is gone is not production
    if job.ever_evaluated() and not eval_lane and (spend or kroute or TOOL_RE.match(tool or "") or publish or up):
        job.log("deny", {"tool": tool, "problems": ["evaluated job outside the lane"]})
        return {"decision": "deny",
                "reason": f"{tool}: job {jobname} ran in the evaluation lane (an `eval` approval in its APPROVALS.md) "
                          f"and its checkpoint no longer says `Tier: evaluation` + `Lane: eval`. An evaluation never "
                          f"becomes production: open a new production job for the deliverable.", "context": ""}
    if publish:
        import flyover  # noqa: E402  (stdlib-only on this path)
        priv = flyover.private_block(job.path)
        if priv:
            job.log("deny", {"tool": tool, "problems": ["private flyover spec"]})
            return {"decision": "deny", "reason": f"{tool}: {priv}.", "context": ""}
        if not job.approved("export"):
            job.log("deny", {"tool": tool, "problems": ["export not approved"]})
            return {"decision": "deny",
                    "reason": f"{tool} publishes, and job {jobname} has no `export` approval — "
                              f"`gate.py approve export --by <name> --quote \"...\"` after export_qc.py "
                              f"passes and the client has signed off.", "context": ""}
        job.log("ask", {"tool": tool})
        return {"decision": "ask", "reason": f"publishing from job {jobname} — confirm",
                "context": f"GATE: export approved · {tool}"}
    if up:
        job.log("ask", {"tool": tool, "note": f"media out ({up})"})
        return {"decision": "ask",
                "reason": f"{tool} sends media to the vendor — job {jobname} is open; confirm it is this job's, "
                          f"cleared (provenance.py) and needed" +
                          (". ⚠ An identity element is a FACE or a character stored with the vendor as a reusable "
                           "subject: only for a character approved as character:<NAME> in this job" if up == "identity"
                           else ""),
                "context": f"GATE: media out ({up}) on job {jobname} — log what was sent in the shot manifest"}
    if kroute and eval_lane:
        job.log("deny", {"tool": tool, "problems": ["Kling in the evaluation lane"]})
        return {"decision": "deny",
                "reason": f"{tool}: Kling is not part of the evaluation lane (v2.72.0) — it bills its own account, so "
                          f"the plan's budget cannot bind it. Evaluate on a Higgsfield roster model with a price.",
                "context": ""}
    if kroute:
        return decide_kling(job, kroute, tool, tool_input, jobname)
    if spend and spend.group(1) == "motion_control":
        job.log("deny", {"tool": tool, "problems": ["no lintable prompt"]})
        return {"decision": "deny",
                "reason": f"{tool} takes no prompt, so nothing the lint passed can stand behind it — every generation "
                          f"here carries the text of a prompt file prompt_lint passes (v2.45, no unlinted route). Motion "
                          f"transfer goes through a roster model in reference-to-video with the real clip as a `what: "
                          f"motion` reference (seedance_2_5 omni_reference, kling4_0, wan3_0), or through Genjutsu on "
                          f"generate_video with a linted, approved <SHOT>.genjutsu.prompt.md (v2.46.1).", "context": ""}
    if spend and eval_lane and not NO_CREDIT_STAGE.get(spend.group(1)):
        job.log("deny", {"tool": tool, "problems": ["unlintable spend in the evaluation lane"]})
        return {"decision": "deny",
                "reason": f"{tool} spends credits the gate cannot lint or price against the plan — not part of the "
                          f"evaluation lane (v2.72.0). Only linted generate calls for the plan's shots spend here.",
                "context": ""}
    if spend:
        stage = NO_CREDIT_STAGE.get(spend.group(1))
        if stage:
            job.log("ask", {"tool": tool, "note": "no-credit stage"})
            return {"decision": "ask", "reason": f"{tool} {stage} — job {jobname} is open; confirm.",
                    "context": f"GATE: {tool} on job {jobname} — record the reference media in the shot manifest"}
        job.log("ask", {"tool": tool, "note": "unlintable spend"})
        return {"decision": "ask",
                "reason": f"{tool} spends credits and carries no prompt the gate can lint — job "
                          f"{jobname} is open; confirm this spend.",
                "context": f"GATE: unlintable spend tool {tool} on job {jobname} — record it in the "
                           f"shot manifest"}
    kind = m.group(1)
    if stills and kind != "image":
        job.log("deny", {"tool": tool, "problems": ["stills job"]})
        return {"decision": "deny",
                "reason": f"{tool}: job {jobname} is a stills job (Mode S) — it generates images "
                          f"only. Video and audio need a video job (Mode A–D) with its own "
                          f"checkpoint, concept and script.", "context": ""}
    reqs = requests_of(tool, tool_input)
    if not reqs:
        return {"decision": "deny", "reason": f"{tool}: empty or malformed `requests` — nothing to check",
                "context": ""}

    # --- the previz lane: concept art, before the concept is signed --------------------------------
    # Checked BEFORE the production path, because previz has no linted prompt by definition — the
    # shot it would belong to does not exist yet. That is the whole point: this is the picture you
    # look at in order to decide what the shots should be.
    # ⛔ Not in Mode S: a stills job has no concept to sign, so "before the concept" would be
    # forever — the lane would never close. Every still goes through its linted prompt.
    if kind == "image" and not stills and not eval_lane and not job.approved("concept"):
        okp, whyp = previz_available(job)
        probes = sum(1 for pp in reqs if isinstance(pp, dict) and pp.get("get_cost") is True)
        if probes == len(reqs):
            return {"decision": "pass", "reason": "",
                    "context": f"GATE: cost probe on job {jobname} (spends nothing)"}
        if okp:
            st = previz_state(job)
            used, budget = int(st.get("used") or 0), int(st.get("budget") or 0)
            if used + len(reqs) > budget:
                job.log("deny", {"tool": tool, "previz": f"{used}+{len(reqs)}>{budget}"})
                return {"decision": "deny",
                        "reason": f"previz lane: {len(reqs)} image(s) requested, "
                                  f"{budget - used} left of {budget}. Raise it deliberately "
                                  f"(`gate.py previz <job> --budget N --why ...`, max "
                                  f"{PREVIZ_MAX}) or send fewer.", "context": ""}
            floor = []
            for i, pp in enumerate(reqs):
                if not isinstance(pp, dict):
                    floor.append(f"request[{i}]: params is not an object")
                    continue
                mdl = str(pp.get("model") or "").strip().lower()
                # same authority the linter uses to catch a video model in a frame prompt
                hints = _lint_module().IMAGE_MODEL_HINT
                if not mdl:
                    floor.append(f"request[{i}]: no model — name the profile \u00a75 image model")
                elif not any(h in mdl for h in hints):
                    floor.append(f"request[{i}]: {mdl!r} does not look like an image model "
                                 f"(profile \u00a75 names the one this brand uses)")
                if not str(pp.get("prompt") or "").strip():
                    floor.append(f"request[{i}]: empty prompt")
            if floor:
                job.log("deny", {"tool": tool, "previz": floor})
                return {"decision": "deny",
                        "reason": "previz still holds the roster and the quality floor — a cheaper "
                                  "or off-roster generation is a DIFFERENT picture, and a previz "
                                  "that misleads you about the look is worse than none:\n  - " +
                                  "\n  - ".join(floor), "context": ""}
            if commit_previz:                 # (build review 2) a call that will be DENIED never burns a previz slot
                previz_spend(job, len(reqs))
            st = previz_state(job)
            job.log("previz", {"tool": tool, "n": len(reqs), "used": st.get("used"),
                               "budget": st.get("budget")})
            return {"decision": "pass", "reason": "",
                    "context": (f"GATE: PREVIZ {st.get('used')}/{st.get('budget')} on job "
                                f"{jobname} — {st.get('why', '')}. This is concept art for the "
                                f"development decision. ⛔ It is NOT a start frame: it cannot be "
                                f"approved as one, and nothing downstream may bind it. Save it "
                                f"under 00-brief/_previz/ (name it <CONCEPT-ID>-*.png so "
                                f"`board.py concepts` puts it on that concept's panel) and put it "
                                f"in front of the human.")}
        if not job.approved("script"):
            job.log("deny", {"tool": tool, "previz_closed": whyp})
            return {"decision": "deny",
                    "reason": f"No `script` approval, and no previz lane either — so this image is "
                              f"neither concept art nor a start frame.\n  {whyp}\n"
                              f"If you are trying to see a concept before choosing: that is what "
                              f"the previz lane is for, and `board.py concepts <job>` may already "
                              f"answer it for nothing.", "context": ""}
    scs = job.sidecars(relint=True) if kind != "audio" else []
    allp, summaries, all_probe = [], [], True
    gj: list = []                     # (params, spec) of every Genjutsu request in this call (v2.46.1)
    units: dict | None = {}           # shot → generations in this call, for the allowance
    for i, params in enumerate(reqs):
        probs, sc = check_request(job, kind, params, policy, scs)
        tag = f"request[{i}]" if tool.endswith("_batch") else "call"
        allp += [f"{tag}: {p}" for p in probs]
        if sc.get("_probe"):
            summaries.append(f"{tag}: cost probe (spends nothing)")
        else:
            all_probe = False
            if sc.get("kind") == "genjutsu":
                gj.append((params, sc))
                units = None                  # a clip allowance never covers a Genjutsu take (v2.46.1)
            elif units is not None and sc.get("shot") and kind in ALLOW_KINDS:
                try:
                    nvar = max(1, int(sc.get("variants") or 1))
                except (TypeError, ValueError):
                    nvar = 1
                if eval_lane:                 # (v2.72.0) a lane take is what the call bills: count × batch_size
                    nvar = max(1, int(_num(params.get("count")) or 1)) * max(1, int(_num(params.get("batch_size")) or 1))
                units[str(sc["shot"])] = units.get(str(sc["shot"]), 0) + nvar
            else:
                units = None
            if sc and kind == "video" and sc.get("shot") and sc.get("kind") != "genjutsu":
                # (3.1 build review 1, Grok + Sonnet) a scene whose continuity check FAILED gets no clip from the HOOK
                # either, not only from preflight (a call written by hand never ran preflight)
                try:
                    _scene, _crep = continuity_fail(job, sc)
                    _cv = "FAIL" if _scene else None
                except Exception as e:                       # noqa: BLE001 — a check that cannot run refuses
                    _scene, _cv, _crep = str(sc["shot"]), "FAIL", f"(the continuity reports could not be read: {type(e).__name__})"
                if _cv == "FAIL":
                    allp.append(f"{tag}: scene {_scene}'s continuity check FAILED ({_crep}); fix the scene and re-run "
                                f"the cine-scene-continuity check before any clip")
            if sc:
                summaries.append(f"{tag}: {sc.get('shot')} {sc.get('kind')} · {sc.get('model')} "
                                 f"{sc.get('resolution') or ''} {sc.get('duration') or ''}s")
            elif kind == "audio":
                summaries.append(f"{tag}: VO line ({len(str(params.get('prompt') or ''))} chars)")
    if allp:
        job.log("deny", {"tool": tool, "problems": allp})
        return {"decision": "deny",
                "reason": f"GATE REFUSED {tool} on job {jobname}:\n  - " + "\n  - ".join(allp) +
                          "\n`gate.py status` shows what is still open.", "context": ""}
    ctx = f"GATE OK · job {jobname} · policy {policy} · " + " · ".join(summaries)
    def _tail(ctx):
        # ⛔ the duplicate-spend guard (v2.45): an identical request this job already sent, within the window, asks first
        dup = None if all_probe else duplicate_of(job, request_hashes(tool, tool_input))
        if dup:
            job.log("ask", {"tool": tool, "note": "duplicate request", "first": dup.get("ts")})
            return {"decision": "ask", "reason": duplicate_reason(dup), "context": ctx}
        if gj and not all_probe:
            # ⚡ A GENJUTSU TAKE ALWAYS ASKS (v2.46.1), whatever the policy: it re-renders a whole source video at
            # about 6× Kling 4.0's price per 5 s [stated · 2026-11-03], and its free generations are counted
            lines = []
            for p_, sc_ in gj:
                free = p_.get("use_free_gens") is True
                lines.append(f"{sc_.get('shot')} · {sc_.get('genjutsu_name') or 'Genjutsu'} ({sc_.get('tier')}) {sc_.get('model')} "
                             f"{sc_.get('resolution')} · {'motion transfer' if sc_.get('genjutsu_mode') == 'motion' else 'object swap'}"
                             f" · {sc_.get('_file')} · " +
                             ("asks for a FREE generation (use_free_gens) — if the vendor refuses it, stop and ask the owner; "
                              "never resend it on credits" if free else
                              "spends credits — the owner stated about 100 cr per 5 s (2026-11-03); the get_cost probe of this "
                              "exact call is the figure to quote"))
            job.log("ask", {"tool": tool, "genjutsu": [sc_.get("_file") for _, sc_ in gj]})
            return {"decision": "ask",
                    "reason": "Genjutsu on job " + str(jobname) + " — " + " | ".join(lines) + ". Free generations stated by "
                              "the owner (2026-11-03): Lite 10, full 1 — not a live balance. Confirm this take.",
                    "context": ctx + " · GENJUTSU"}
        if not all_probe and units:
            al = allowance_cover(job, kind, units)
            if al and not commit:                        # (wave 2c) the budget stop asks; the regen is kept
                return {"decision": "preapproved",
                        "reason": f"allowance {al.get('id')} ({al.get('by')}: \"{(al.get('quote') or '')[:80]}\")",
                        "context": ctx + f" · ALLOWANCE {allowance_line(al)}"}
            if al:
                al = allowance_spend(job, al["id"], units)
                job.log("preapproved", {"tool": tool, "allowance": al.get("id"), "units": units,
                                        "left": allowance_left(al)})
                return {"decision": "preapproved",
                        "reason": f"allowance {al.get('id')} ({al.get('by')}: \"{(al.get('quote') or '')[:80]}\")",
                        "context": ctx + f" · ALLOWANCE {allowance_line(al)}"}
        if policy == "per-stage-human" and not all_probe:
            job.log("ask", {"tool": tool, "summary": summaries})
            hint = ""
            if units and kind in ALLOW_KINDS:
                spent = [al for al in load_allowances(job) if al.get("kind") == kind and not al.get("revoked")
                         and set(units) <= set(al.get("shots", []))]
                hint = (" — the allowance for these shots is used up" if spent else
                        f" — one approval can cover the regens too: ask once, then `gate.py allow {kind} --shots "
                        f"{','.join(sorted(units))} --by <name> --quote \"<their words>\"` "
                        f"({default_regens()[0]} regens per shot)")
            return {"decision": "ask",
                    "reason": f"per-stage-human policy — confirm this spend: {' · '.join(summaries)}{hint}",
                    "context": ctx}
        job.log("pass", {"tool": tool, "summary": summaries})
        return {"decision": "pass", "reason": "", "context": ctx}

    # (v2.72.0) THE EVALUATION LANE binds the plan HERE: after the match (the shots are known), under every policy,
    # before the duplicate ask, the allowance and the policy ask. The check and the reservation run under ONE lock, so
    # two hooks at once cannot both read the same usage (build review 1, Grok); an ask reserves as PENDING, which
    # counts for 30 minutes or until a submission confirms it, so a declined ask does not burn a take for good
    # (build review 1, Sonnet).
    if eval_lane and not all_probe:
        _prices = request_credits(tool, tool_input)
        _hashes = request_hashes(tool, tool_input)
        with eval_lock(job) as _locked:
            if not _locked:
                return {"decision": "deny", "reason": f"{tool}: the evaluation ledger is busy (another call is being "
                                                      f"checked); try again in a moment", "context": ""}
            ep = eval_lane_problems(job) or eval_shot_problems(job, units, _prices)   # the plan re-read under the lock
            if ep:
                job.log("deny", {"tool": tool, "problems": ep})
                return {"decision": "deny",
                        "reason": f"GATE REFUSED {tool} on job {jobname} (the evaluation plan):\n  - " + "\n  - ".join(ep),
                        "context": ""}
            out = _tail(ctx + f" · EVAL PLAN {', '.join(f'{k}+{v}' for k, v in units.items())}")
            if out.get("decision") in ("pass", "preapproved", "ask") and \
                    not eval_reserve(job, tool, units, _prices, _hashes,
                                     pending=out.get("decision") == "ask" or not commit):
                return {"decision": "deny", "reason": f"{tool}: the evaluation ledger ({_eval_ledger_path(job)}) cannot "
                                                      f"be written, so this call could not be counted against the plan",
                        "context": ""}
            return out
    return _tail(ctx)


# ----------------------------------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------------------------------
def cmd_open(a) -> int:
    job = Job(a.job_dir)
    if not os.path.isdir(job.path):
        print(f"error: {a.job_dir} is not a directory", file=sys.stderr); return 2
    if not os.path.isfile(job.checkpoint):
        os.makedirs(job.brief, exist_ok=True)
        tpl = os.path.join(ASSETS, "checkpoint-template.md")
        if os.path.isfile(tpl):
            with open(job.checkpoint, "w", encoding="utf-8") as fh:
                fh.write(read(tpl))
        print(f"REFUSED: no checkpoint. Wrote the template to "
              f"{os.path.relpath(job.checkpoint)} — fill every line, then run open again.")
        return 1
    problems = job.validate()
    if problems:
        print(f"REFUSED: {len(problems)} problem(s) in {os.path.relpath(job.checkpoint)}:")
        for p in problems:
            print(f"  - {p}")
        return 1
    if not os.path.isfile(job.approvals_path):
        tpl = os.path.join(ASSETS, "approvals-template.md")
        with open(job.approvals_path, "w", encoding="utf-8") as fh:
            fh.write(read(tpl) if os.path.isfile(tpl) else
                     "# Approvals\n\n| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n"
                     "|---|---|---|---|---|---|---|---|\n")
    os.makedirs(job.prompts, exist_ok=True)
    _why = set_active(job.path, os.getcwd())
    if _why:
        print(f"REFUSED: cannot open for this session — {_why}", file=sys.stderr)
        return 1
    # (v2.48.0, project switches) the switches go on the open record, so `status` can tell when they change after it
    job.log("open", {"policy": job.policy, "cwd": os.getcwd(), "switches": job.switches})
    ledger_sync(job.path)
    prof = os.path.relpath(job.profile_path, SKILL_ROOT) if job.profile_path.startswith(SKILL_ROOT) else job.profile_path
    print(f"OPEN: {job.fields.get('job')} · mode {job.fields.get('mode')[:1]} · policy {job.policy} · "
          f"format {job.fields.get('_preset')} · profile {prof}")
    _sid, _ = resolve_session()
    print(f"  active job → {'session ' + _sid if _sid else ACTIVE_FILE + ' (shared: no live session seen)'} "
          f"(expires in 24 h; re-open to refresh)")
    for line in switch_lines(job.switches):                  # (v2.48.0, project switches)
        print(f"  {line}")
    if job.is_stills():
        print("  stills lane: approve the brief (`gate.py approve brief --artifact 00-brief/BRIEF-<slug>.md "
              "...` — it names every still ID), write 01-script/prompts/<ID>.frame.prompt.md, lint it, "
              "then generate through `gate.py preflight <ID> --kind frame`. Video and audio are denied.")
    else:
        print("  next: approve the concept (`gate.py approve concept ...`), then the script, lint prompts, then generate "
              "through `gate.py preflight`.")
    return 0


# ⛔ A SCOPE THAT IS EASY TO SPOOF IS A HOLE (2026-09-17). The first version of this test was
# `"_lab" in job.fields["client"]` — a SUBSTRING — so a checkpoint whose client line read
# "acme (see _lab for the bench)" would have skipped the look board on a paying job. Two
# conditions now, both deliberate and both visible in the checkpoint: the profile FILE is `_lab`,
# and the job id is in the `lab-` series. A calibration job still pays every other price in the
# lane — a stated reason, a capped budget, a written denominator — and may not ship anything.
def calibration_job(job) -> bool:
    if not job.fields:
        job.validate()
    client = (job.fields.get("client") or "").strip().strip("`").strip()
    stem = os.path.splitext(os.path.basename(client))[0]
    return stem == "_lab" and os.path.basename(job.path).startswith("lab-")


def replica_source(job) -> dict | None:
    """00-brief/REPLICA-SOURCE.json, written by replicate.py: what this job replicates and how closely.
    House rule 2026-10-25, "Any reference, flagged": it is SHOWN at status and at export, never refused."""
    p = os.path.join(job.brief, "REPLICA-SOURCE.json")
    try:
        return load_json(p) if os.path.isfile(p) else None
    except (OSError, json.JSONDecodeError):
        return {"source": {"title": "?"}, "band": "unreadable", "closeness": None}


def replica_line(r: dict) -> str:
    src = r.get("source") or {}
    return (f"replicates **{src.get('title') or '?'}** ({src.get('owner') or '?'}, licence {src.get('licence') or '?'}) · "
            f"closeness {r.get('closeness')} ({r.get('band')}) — flagged by the house rule (2026-10-25): any "
            f"reference may be used; the call is the owner's, per job")


def switch_lines(sw: dict) -> list:
    """(v2.48.0, project switches) What `open` and `status` print: one line per house rule this job lifts — the
    id and the job's reason — or one line saying none is lifted. Shown every time, so a lift is never silent."""
    if not sw:
        return ["project switches: none — every house rule holds"]
    return ([f"project switches ({len(sw)}) — lifted for this job only, every other house rule holds:"] +
            [f"  {sid} — {why}" for sid, why in sw.items()])


ROLES = ("producer", "editor", "reviewer")


def role_line(job) -> str | None:
    """(3.1) The optional `Producer:`, `Editor:` and `Reviewer:` checkpoint lines, shown in status. Information only:
    none of them can approve (only the Approver's own words do), and a checkpoint without them reads as before."""
    f = getattr(job, "fields", {}) or {}
    got = {r: str(f.get(r) or "").strip() for r in ROLES}
    if not any(got.values()):
        return None
    shown = [f"{r.capitalize()} {v if v and not PLACEHOLDER_RE.search(v) else '(not set)'}" for r, v in got.items()]
    return "roles: " + " · ".join(shown) + " — information only; approvals come from the Approver"


def switch_status_lines(job, at_open: dict | None) -> list:
    """(v2.48.0, project switches) `status`: the switches as the CHECKPOINT has them now — what every script reads —
    and a warning when they differ from what `open` recorded."""
    out = switch_lines(job.switches)
    if at_open is not None and at_open != job.switches:
        out.append(f"⚠ switches changed since `open` (recorded then: {', '.join(at_open) or 'none'}) — every script "
                   f"reads the CHECKPOINT as it is now; re-run `gate.py open` so the record says so too")
    return out


def opened_switches(job) -> dict | None:
    """(v2.48.0, project switches) The switches `open` recorded in .gate/decisions.log, from the last open of this
    job; None when no open is on record. A job opened before 2.48 recorded none, which reads as {}."""
    try:
        lines = read(os.path.join(job.gate_dir, "decisions.log")).splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if '"open"' not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("kind") == "open":
            return rec.get("switches") or {}
    return None


def status_checked_line(full: bool, cache, secs: float) -> str:
    if full:
        return f"checked: full — every prompt re-linted, every media file hashed ({secs:.1f} s)"
    c = f"{cache.hits} cached, {cache.misses} hashed" if cache is not None else ""
    return (f"checked: fast — prompts against their sidecars by hash, media hashes by size and time ({c}; "
            f"{secs:.1f} s). `status --full` re-lints every prompt; preflight always does")


def cast_line(aps: list) -> str:
    """`cast` is its own sign-off, not the sum of the character approvals (a supplement ad job: "status says 'next: approve
    cast' although characters A and B are approved"). Say which characters are in, and what `cast` adds."""
    chars = sorted({r["stage"].split(":", 1)[1] for r in aps if r["stage"].lower().startswith("character:")})
    if not chars:
        return "approve cast"
    return (f"approve cast — character:{', character:'.join(chars)} approved; `cast` is the cross-shot sign-off on "
            f"top of them (breakdown.py: every character locked by a reference; the reference plan cleared), "
            f"one approval, not one per character")


def settings_info(job) -> dict:
    """(wave 2c) Every production setting this job runs on, each with where it came from (status, every path)."""
    s: dict = {}
    if job:
        fields = job.fields or {}
        env = ENVELOPE_RE.search(fields.get("budget") or "")
        s["envelope"] = {"value": float(env.group(1)) if env else None, "source": "checkpoint"}
        s["policy"] = {"value": job.policy, "source": "profile"}
        rf, rsrc = None, None
        if job.profile_path:
            cf = os.path.join(os.path.dirname(job.profile_path),
                              "costs." + os.path.splitext(os.path.basename(job.profile_path))[0] + ".json")
            try:
                rf = json.load(open(cf, encoding="utf-8"))["presets"]["quality"]["retry"]
                rsrc = os.path.basename(cf)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        s["retake_factor"] = {"value": rf, "source": rsrc or "no cost file"}
    r_, rsrc_ = default_regens()
    s["regens_per_approval"] = {"value": r_, "source": rsrc_}
    st = _studio()
    if st:
        c, cprob = st.ceiling_state()
        mt = st.month_total()
        s["studio_month"] = {"month": mt["month"], "credits": mt["credits"], "ceiling": c, "unpriced": mt["unpriced"],
                             "voice_unpriced": mt["voice_unpriced"], "unreadable": mt["unreadable"],
                             "problem": cprob, "source": "studio.json"}
        so = st.load().get("second_opinion", "none")
        s["second_opinion"] = {"value": so, "source": "studio.json" if so != "none" else "default"}
        s["studio_notes"] = st.disk_problems()
    return s


def settings_line(s: dict) -> str:
    parts = []
    if "envelope" in s:
        e = s["envelope"]["value"]
        parts.append(f"envelope {e:g} cr (checkpoint)" if e is not None else "envelope none (checkpoint)")
    sm = s.get("studio_month")
    if sm:
        parts.append(f"studio month {sm['month']} (UTC) {sm['credits']:g}"
                     + (f" / {sm['ceiling']:g} cr" if sm["ceiling"] is not None else " cr, no ceiling")
                     + (f", {sm['unpriced']} unpriced" if sm["unpriced"] else "")
                     + (f", {sm['voice_unpriced']} voice unpriced" if sm["voice_unpriced"] else "")
                     + (f", {sm['unreadable']} unreadable" if sm["unreadable"] else "")
                     + (f" ⛔ {sm['problem']}" if sm["problem"] else "")
                     + " (studio.json; Kling is a separate account; spend-class tools ask every time, not counted)")
    r = s["regens_per_approval"]
    parts.append(f"regens per approval {r['value']} ({r['source']}" + ("" if r["source"] == "house" else "; house 2") + ")")
    if "retake_factor" in s:
        rf = s["retake_factor"]
        parts.append(f"retake factor quality {rf['value']:g} ({rf['source']})" if rf["value"] is not None
                     else f"retake factor ({rf['source']})")
    if "policy" in s:
        parts.append(f"policy {s['policy']['value']} (profile)")
    so = s.get("second_opinion")
    if so:
        v = so["value"]
        parts.append("second opinion: none" if v == "none" else
                     f"second opinion: {v.get('tool')} (client material {v.get('client_material')})")
    notes = s.get("studio_notes") or []
    return "settings: " + " · ".join(parts) + "".join(f"\n  ⚠ {n_}" for n_ in notes)


def cmd_status(a) -> int:
    job, why = active_job()
    if not job:
        print(f"no active job ({why}) — `gate.py open <job-dir>`")
        print("  " + settings_line(settings_info(None)))
        return 1
    t0 = time.time()
    full = bool(getattr(a, "full", False))
    problems = job.validate()
    aps = job.approvals()
    # ⚡ a supplement ad job (2026-10-28): "`gate.py status` took more than 120 s … It should answer in under 5 s." The time
    # went on re-linting 142 prompts (each lint hashes its references) and hashing 4 GB of media, on every call. The
    # fast path checks each prompt against its sidecar by hash and reads media hashes from a size/mtime cache;
    # `--full` re-lints and re-hashes. Nothing that spends trusts the fast path: preflight always re-lints.
    scs = job.sidecars(relint=full)
    cache = None if full else HashCache(job.path, job.gate_dir)
    mt = media_trace(job, cache)
    if cache is not None:
        cache.save()
    st = {"job": job.fields.get("job"), "path": job.path, "policy": job.policy,
          "tier": job.tier(), "untraced_media": [r["path"] for r in mt["untraced"]],
          "checked": "full" if full else "fast",
          "profile": job.profile_path, "profile_moved": list(job.profile_moved) if job.profile_moved else None,
          "checkpoint_problems": problems,
          # (v2.48.0, project switches) the line as it reads now, and as `open` recorded it (None: no open on record)
          "switches": job.switches, "switches_at_open": opened_switches(job),
          "roles": {r: (job.fields or {}).get(r) for r in ROLES if (job.fields or {}).get(r)},
          "settings": settings_info(job),
          "approved": [f"{r['stage']} ({r['by']}, {r['ts'][:16]}{', ' + r['verified'] if r.get('verified') else ''})"
                       for r in aps],
          "prompts": [{"file": s["_file"], "shot": s.get("shot"), "kind": s.get("kind"),
                       "model": s.get("model"), "stale": s["_stale"], "forged": s["_forged"]} for s in scs]}
    needs = []
    stills = job.is_stills()
    if stills:
        # The stills lane reports its own three stages — never concept/script/DEVELOPMENT.md, which
        # a stills job does not have (the same lesson as the calibration lane below).
        needs += brief_problems(job)[:1]
        frames = [s for s in scs if s.get("kind") in ("frame", "edit")]   # an image edit is a still too (v2.45)
        for s in frames:
            if s["_forged"] or s["_stale"]:
                needs.append(f"re-lint {s['_file']}")
            elif job.approved("brief") and not brief_names(job, s.get("shot") or ""):
                needs.append(f"{s.get('shot')} is not in the approved brief — add it and re-approve, "
                             f"or drop {s['_file']}")
        if not frames:
            needs.append("write 01-script/prompts/<ID>.frame.prompt.md and lint it")
        elif not any(r["stage"].lower().startswith("frame:") for r in aps):
            needs.append("generate, then `approve frame:<ID>` for each still that is kept")
        elif not job.approved("export"):
            needs.append("put the delivered stills in 10-export/, then `approve export`")
        st["development"] = {"ok": None}
        st["next"] = needs or ["ready — `gate.py preflight <ID> --kind frame`"]
        if a.json:
            print(json.dumps(st, indent=2, ensure_ascii=False)); return 1 if problems else 0
        print(f"JOB {st['job']} · STILLS (Mode S) · policy {st['policy']} · {job.path}")
        print("  " + settings_line(st["settings"]))
        if role_line(job):
            print(f"  {role_line(job)}")
        for p in problems:
            print(f"  ⛔ checkpoint: {p}")
        for line in switch_status_lines(job, st["switches_at_open"]):      # (v2.48.0, project switches)
            print(f"  {line}")
        print(f"  approvals ({len(aps)}): " + (", ".join(st["approved"]) or "none"))
        for line in [allowance_line(al) for al in load_allowances(job)]:
            print(f"  allowance {line}")
        print(f"  linted prompts ({len(scs)}): " +
              (", ".join(f"{s['_file']}{' [FORGED]' if s['_forged'] else ' [STALE]' if s['_stale'] else ''}"
                         for s in scs) or "none"))
        print("  " + status_checked_line(full, cache, time.time() - t0))
        print("  next: " + "; ".join(st["next"]))
        return 1 if problems else 0
    if job.is_eval_lane():
        # (v2.72.0) the evaluation lane reports its plan, never concept/script/storyboard
        _txt = _eval_plan_text(job)
        _shots, _n = job_tier.plan_shots(_txt), job_tier.plan_numbers(_txt)
        _per, _used, _unexp = eval_usage(job)
        needs += eval_lane_problems(job)[:1]
        for sh in _shots:
            if not any(str(s_.get("shot")) == sh and not s_["_stale"] and not s_["_forged"] for s_ in scs):
                needs.append(f"write and lint the prompt for {sh}")
        st["eval"] = {"shots": _shots, "takes_per_shot": _n["takes"], "budget": _n["budget"], "used_credits": _used,
                      "takes_used": _per, "unexplained_submissions": _unexp}
        st["next"] = needs or ["ready — `gate.py preflight <SHOT> --kind frame|clip`, then generate inside the plan"]
        if a.json:
            print(json.dumps(st, indent=2, ensure_ascii=False)); return 1 if problems else 0
        print(f"JOB {st['job']} · EVALUATION LANE · policy {st['policy']} · {job.path}")
        print("  " + settings_line(st["settings"]))
        for p_ in problems:
            print(f"  ⛔ checkpoint: {p_}")
        print(f"  plan: shots {', '.join(_shots) or 'none'} · {_n['takes']} take(s) per shot · budget {_n['budget']} cr "
              f"· used {_used:g} cr · takes " + (", ".join(f"{k} {v}" for k, v in sorted(_per.items())) or "none")
              + (f" · {_unexp} submission(s) with no reservation" if _unexp else ""))
        print(f"  approvals ({len(aps)}): " + (", ".join(st["approved"]) or "none"))
        print("  next: " + "; ".join(st["next"]))
        return 1 if problems else 0
    if not job.approved("script"):
        needs.append("approve script")
    for s in scs:
        if s.get("kind") == "clip" and not job.approved(f"frame:{s.get('shot')}") and \
                (str(s.get("form") or "").lower() != "scene" or s.get("start_frame")):
            needs.append(f"approve frame:{s.get('shot')} (then bind its media id)")
        if s.get("kind") == "edit" and s.get("use") == "target" and not job.approved(f"target:{s.get('shot')}"):
            needs.append(f"approve target:{s.get('shot')} — the owner's per-shot opt-in before an AI edit of our own "
                         f"footage becomes a model reference")
        if s.get("kind") == "clip" and (s.get("end_frame") or endframe_refs(s)) and \
                not job.approved(f"endframe:{s.get('shot')}"):
            needs.append(f"approve endframe:{s.get('shot')} (the clip declares an end frame"
                         + (", bound as a reference)" if endframe_refs(s) and not s.get("end_frame") else ")"))
        if s["_forged"] or s["_stale"]:
            needs.append(f"re-lint {s['_file']}")
    if job.policy == "per-stage-human" and any(speaks(s) for s in scs) \
            and not job.approved("audio"):
        needs.append("approve audio (per-stage-human)")
    # ⛔ THE LANE WAS HALF-BUILT, AND ONLY THE HALF THAT BLOCKED ME GOT FIXED (2026-09-17).
    # `previz` was scoped to calibration the day the lane was created — because that is where it
    # refused. `status` was not, so it went on demanding a DEVELOPMENT.md and telling the operator
    # to "approve concept; approve script" for a job whose deliverable is a WRITTEN RESULT and
    # which has no concept and no script. A gate pointing at the wrong next action is a gate being
    # ignored. A calibration job reports its own lane: is the result written?
    if calibration_job(job):
        qa = os.path.join(job.path, "09-qa")
        results = sorted(f for f in (os.listdir(qa) if os.path.isdir(qa) else [])
                         if f.startswith("RESULT-") and f.endswith(".md"))
        st["calibration"] = {"results": results,
                             "varied": (job.fields.get("next") or "")[:160]}
        st["development"] = {"ok": None}
        needs = ([] if results else
                 ["write 09-qa/RESULT-<date>-<slug>.md — a calibration job's deliverable is the "
                  "WRITTEN RESULT, not the asset (clients/_lab.md)"])
        if results:
            needs = [f"result written ({', '.join(results)}) — land the finding in the craft files, "
                     f"then `gate.py close`"]
    else:
        try:
            dev = _develop_module().check(job.path, phase="full")
            st["development"] = {"ok": dev["ok"], "stats": dev["stats"], "fails": dev["fails"][:4]}
            if not job.approved("concept"):
                needs.insert(0, "development → `develop.py status <job>` → approve concept")
        except Exception:
            st["development"] = {"ok": None}
    if not st.get("calibration"):
        _sb_req = _storyboard().required(job.path)
        for stg in STAGES:
            if stg in PICTURE_SIGNOFFS and not _sb_req:
                continue                             # an older job: optional, not next (v2.66.0)
            if stg == "startframes" and not any(r["stage"].lower().startswith("frame:") for r in aps):
                continue                             # nothing to sign side by side yet
            if not job.approved(stg) and all(job.approved(n) for n in REQUIRES.get(stg, [])):
                needs.append(cast_line(aps) if stg == "cast" else f"approve {stg}")
                break
    st["next"] = needs or ["ready — `gate.py preflight <SHOT> --kind frame|clip|edit`"]
    st["allowances"] = [allowance_line(al) for al in load_allowances(job)]
    rep_ = replica_source(job)
    st["replica"] = rep_
    if a.json:
        print(json.dumps(st, indent=2, ensure_ascii=False)); return 1 if problems else 0
    print(f"JOB {st['job']} · policy {st['policy']} · {job.path}")
    print("  " + settings_line(st["settings"]))
    if role_line(job):
        print(f"  {role_line(job)}")
    if job.profile_moved:
        print(f"  ⚠ Client: the checkpoint names {job.profile_moved[0]}, which is not on this machine — using "
              f"{job.profile_moved[1]}. Write `Client: {os.path.basename(job.profile_moved[1])[:-3]}` — a name, not a "
              f"path: it is found from CINE_CLIENTS or a `_cine-clients/` folder above the job, on any machine")
    if rep_:
        print(f"  ⚠ {replica_line(rep_)}")
    if problems:
        print("  ⛔ checkpoint problems:")
        for p in problems:
            print(f"    - {p}")
    for line in switch_status_lines(job, st["switches_at_open"]):          # (v2.48.0, project switches)
        print(f"  {line}")
    print(f"  approvals ({len(aps)}): " + (", ".join(st["approved"]) or "none"))
    for line in st.get("allowances") or []:
        print(f"  allowance {line}")
    print(f"  linted prompts ({len(scs)}): " +
          (", ".join(f"{s['_file']}{' [FORGED]' if s['_forged'] else ' [STALE]' if s['_stale'] else ''}"
                     for s in scs) or "none"))
    if st["untraced_media"]:
        print(f"  media: {len(st['untraced_media'])} file(s) neither pulled nor logged — `gate.py reconcile --files`")
    print("  " + status_checked_line(full, cache, time.time() - t0))
    if st.get("calibration"):
        c = st["calibration"]
        print(f"  calibration bench · varying: {c['varied'] or '(not stated — previz will refuse)'}")
        print(f"  results: {', '.join(c['results']) or 'none written yet'}")
    d = st.get("development") or {}
    if d.get("ok") is not None:
        ds = d.get("stats") or {}
        print(f"  development: {'complete' if d['ok'] else 'INCOMPLETE'} — research "
              f"{ds.get('research_sourced', 0)} · concepts {ds.get('concepts', 0)} · rounds "
              f"{ds.get('rounds', 0)} (killed {ds.get('killed', 0)}) · chosen {ds.get('chosen') or '—'} "
              f"· hooks {ds.get('hooks', 0)} · drafts {ds.get('drafts', 0)}")
        for f in d.get("fails", []):
            print(f"    ✗ {f}")
    print("  next: " + "; ".join(st["next"]))
    return 1 if problems else 0


def board_stale(board: str, sources: list) -> str:
    """"" if the board is current, else why it is not.

    ⛔ Existence is a weak check — building a board is one command. FRESHNESS is not: a board built
    before the concepts were rewritten is a board of different concepts, and approving against it is
    approving something nobody looked at. So the gate compares mtimes, and says which source moved.
    """
    if not os.path.isfile(board):
        return "it has not been built"
    try:
        bt = os.path.getmtime(board)
    except OSError:
        return "it cannot be read"
    newer = []
    for sfile in sources:
        try:
            if os.path.isfile(sfile) and os.path.getmtime(sfile) > bt + 1:
                newer.append(os.path.relpath(sfile))
        except OSError:
            continue
    if newer:
        return ("it is older than " + ", ".join(newer[:4]) +
                (f" and {len(newer) - 4} more" if len(newer) > 4 else "") +
                " — you would be approving a board of something else")
    return ""


def cmd_previz(a) -> int:
    """Open, raise or read the development-stage concept-art lane."""
    job, why = active_job()
    if not job:
        print(f"no active job ({why}) — `gate.py open <job-dir>`", file=sys.stderr)
        return 1
    if job.is_eval_lane() and not a.status:
        print("REFUSED: no previz in the evaluation lane (v2.72.0) — previz is concept art for a concept that an "
              "evaluation does not have, and it would never close. Every picture here is a linted frame of a plan shot.",
              file=sys.stderr)
        return 1
    st = previz_state(job)
    if a.status or (a.budget is None and not a.why):
        if not st:
            print("previz: no lane open. `gate.py previz --budget N --why \"<the decision this "
                  "unblocks>\"`")
            return 1
        used, budget = int(st.get("used") or 0), int(st.get("budget") or 0)
        closed = " · CLOSED (concept approved)" if job.approved("concept") else ""
        print(f"previz {used}/{budget}{closed}\n  why: {st.get('why', '')}\n"
              f"  opened: {st.get('opened', '?')}")
        return 0 if used < budget and not closed else 1

    if job.is_stills():
        print("REFUSED: a stills job (Mode S) has no previz lane — there is no concept to inform. "
              "Every still is a linted <ID>.frame.prompt.md under the approved brief.", file=sys.stderr)
        return 1
    if job.approved("concept"):
        print("REFUSED: the concept is already approved — previz informs the CHOICE, and after the "
              "choice a picture is a start frame: write the prompt, lint it, go through the frame "
              "gate.", file=sys.stderr)
        return 1
    why_txt = (a.why or "").strip()
    if len(why_txt.split()) < 5:
        print("REFUSED: --why must say, in your own words, which decision seeing these images "
              "unblocks (five words or more). 'concept art' is a label, not a reason — and a "
              "spend nobody can state a reason for is the spend this whole gate exists to stop.",
              file=sys.stderr)
        return 1
    budget = int(a.budget or 0)
    if budget < 1 or budget > PREVIZ_MAX:
        print(f"REFUSED: --budget must be 1..{PREVIZ_MAX}. The cap is deliberate: past a dozen "
              f"images you are not deciding, you are browsing, and the answer to 'none of these "
              f"are right' is a better brief, not more of them.", file=sys.stderr)
        return 1
    # ⛔ THE LOOK BOARD IS A *CONCEPT* PRECONDITION, AND IT WAS APPLIED TO EVERYTHING (2026-09-17).
    # "You do not generate a picture of a thing before looking at photographs of the real thing" is
    # exactly right when previz is exploring WHAT SOMETHING LOOKS LIKE. It is meaningless for a
    # CALIBRATION run, where the subject is arbitrary on purpose - a chair in a bare room - and the
    # only thing under test is whether a prompt token moves the camera. Four photographs of chairs
    # would teach nothing, so satisfying the rule would be going through its motions, which is worse
    # than not having it.
    #
    # The fix is a SCOPE, not an exemption: a job whose profile is the internal bench
    # (clients/_lab.md) and whose checkpoint names the varied axis is running a measurement, not a
    # look. It still pays every other price in this lane - a stated reason, a capped budget, a
    # written denominator - and it may not ship anything. Everything else still needs its four
    # photographs.
    is_calibration = calibration_job(job)
    if is_calibration and not re.search(r"(?i)\bvary(?:ing)?\b|\bvaried\b|\bvariable\b",
                                        job.fields.get("next") or ""):
        print("REFUSED: a `_lab` job skips the look board, but only when its checkpoint says what is "
              "being VARIED. Put the varied axis in `Next:` - 'vary X, hold everything else'. "
              "\u26d4 A calibration run that cannot name its axis is not a calibration run, it is a "
              "spend.", file=sys.stderr)
        return 1
    look = os.path.join(job.path, "00-brief", "_look")
    n_look = len([f for f in os.listdir(look)
                  if not f.endswith(".json")]) if os.path.isdir(look) else 0
    if n_look < 4 and not is_calibration:
        print(f"REFUSED: the look board has {n_look} picture(s), needs 4. ⛔ You do not generate a "
              f"picture of a thing before looking at photographs of the real thing — that ordering "
              f"is the point. Real references cost nothing and routinely kill the concept the "
              f"previz would have flattered.\n"
              f"  pixabay_search.py -q \"<terms>\" --image-type photo --download "
              f"00-brief/_look/\n  board.py look {os.path.relpath(job.path)}", file=sys.stderr)
        return 1

    prev = int(st.get("budget") or 0)
    previz_write(job, {**st, "budget": budget, "why": why_txt,
                       "opened": st.get("opened") or dt.datetime.now(dt.timezone.utc)
                       .replace(microsecond=0).isoformat(),
                       "by": a.by or "", "used": int(st.get("used") or 0)})
    verb = "raised to" if prev else "open,"
    print(f"previz lane {verb} {budget} image(s) · used {int(st.get('used') or 0)}\n"
          f"  why: {why_txt}\n"
          f"  ⛔ These are NOT start frames. They cannot be approved as one, nothing downstream may "
          f"bind them, and the lane closes the moment `approve concept` is signed.\n"
          f"  Save them under 00-brief/_previz/ named <CONCEPT-ID>-*.png, then "
          f"`board.py concepts {os.path.relpath(job.path)}` puts each on its concept's panel.")
    return 0


def _shot_list(spec: str) -> list:
    out = []
    for tok in re.split(r"\s*,\s*", spec or ""):
        m = re.match(r"^([A-Za-z]+)(\d+)-\1?(\d+)$", tok)
        if m:
            out += [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)]
        elif tok:
            out.append(tok)
    return list(dict.fromkeys(out))


def cmd_allow_resolve(a) -> int:
    """One approval for a session's Resolve scripts (RESOLVE_SCOPES), with the job when one is open."""
    job, _why = active_job()
    if a.revoke:
        n = 0
        for owner in ([job] if job else []) + [None]:
            rows = load_resolve_allowances(owner)
            for al in rows:
                if a.revoke in (al.get("id"), "all") and not al.get("revoked"):
                    al["revoked"] = now(); n += 1
            save_resolve_allowances(owner, rows)
        print(f"revoked {n} Resolve allowance(s)")
        return 0
    scope = [x.strip() for x in (a.scope or ",".join(RESOLVE_ALLOW_DEFAULT["scope"])).split(",") if x.strip()]
    bad = [x for x in scope if x not in RESOLVE_SCOPES]
    if bad:
        print(f"REFUSED: unknown scope {', '.join(bad)} — one or more of: " +
              "; ".join(f"{k} ({v})" for k, v in RESOLVE_SCOPES.items()), file=sys.stderr)
        return 1
    if not (a.by or "").strip() or len((a.quote or "").split()) < 2:
        print("REFUSED: --by and --quote (the approver's words, verbatim, two words or more) are required",
              file=sys.stderr)
        return 1
    verified = quote_in_transcript(a.quote)
    _br = by_refusal(job, a.by)                         # (3.1) --by names the Approver
    if _br:
        print(f"REFUSED: {_br}", file=sys.stderr)
        return 1
    if verified == "no-transcript":                    # (v2.61.0) an allowance is never made from an unchecked quote
        print("REFUSED: no session transcript is recorded (the SessionStart hook writes its path), so the quote "
              "cannot be checked. An allowance pre-approves calls with no prompt, so it is never created from an "
              "unchecked quote. Run this inside the Claude Code session where the owner said it.", file=sys.stderr)
        return 1
    if verified == "not-found":
        print("REFUSED: that quote appears in no human turn of the current session transcript. Ask the owner once "
              "— which kinds of Resolve script, for how long — and record their words.", file=sys.stderr)
        return 1
    scripts = int(a.scripts or RESOLVE_ALLOW_DEFAULT["scripts"])
    hours = float(a.hours or RESOLVE_ALLOW_DEFAULT["hours"])
    if not (1 <= scripts <= 1000 and 0 < hours <= 24):
        print("REFUSED: --scripts 1..1000 and --hours up to 24 (a new day, a new approval)", file=sys.stderr)
        return 1
    rows = load_resolve_allowances(job)
    al = {"id": f"R{len(rows) + 1}" + ("" if job else "g"), "kind": "resolve", "scope": scope, "scripts": scripts,
          "hours": hours, "by": a.by.strip(), "quote": a.quote.strip(), "ts": now(), "used": 0,
          "verified": "transcript" if verified == "verified" else "UNVERIFIED",
          "job": os.path.basename(job.path) if job else None}
    rows.append(al)
    save_resolve_allowances(job, rows)
    if job:
        job.log("allow", {k: al[k] for k in ("id", "kind", "scope", "scripts", "hours", "by", "verified")})
    print(f"RESOLVE ALLOWANCE {resolve_allowance_line(al)} — Resolve scripts in these scopes now go through without a "
          f"prompt ({'this job' if job else 'no job open: every Resolve script in this session'}). Still denied: "
          f"starting a render, the AI speech generator, auto-captions. Still asked every time: deletes, quits, project "
          f"switches, code the scan cannot read.")
    return 0


def cmd_allow(a) -> int:
    """Record one approval that covers a batch of shots and their regens (see ALLOW_REGENS)."""
    if getattr(a, "kind", None) == "resolve":
        return cmd_allow_resolve(a)
    job, why = active_job()
    if not job:
        print(f"REFUSED: no active job ({why})", file=sys.stderr); return 1
    rows = load_allowances(job)
    if a.revoke:
        hit = [al for al in rows if a.revoke in (al.get("id"), "all") and not al.get("revoked")]
        for al in hit:
            al["revoked"] = now()
        save_allowances(job, rows)
        job.log("allow-revoke", {"ids": [al["id"] for al in hit]})
        print(f"revoked {', '.join(al['id'] for al in hit) or 'nothing'}")
        return 0
    if a.list or not a.kind:
        for al in rows:
            print("  " + allowance_line(al))
        rr = load_resolve_allowances(job) + load_resolve_allowances(None)
        for al in rr:
            print("  " + resolve_allowance_line(al))
        print(f"{len(rows) + len(rr)} allowance(s)" if rows or rr else "no allowances")
        return 0
    problems = job.validate()
    if problems:
        print("REFUSED: the open job's checkpoint does not validate:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 1
    if job.ever_evaluated() and not job.is_eval_lane():       # (v2.72.0) an evaluation never becomes production
        print("REFUSED: this job ran in the evaluation lane and its lane lines are gone — no allowance here; open a new "
              "production job", file=sys.stderr)
        return 1
    if a.kind not in ALLOW_KINDS:
        print(f"REFUSED: an allowance covers {' or '.join(ALLOW_KINDS)} generations; audio and the "
              f"unlintable spend tools still ask per call", file=sys.stderr)
        return 1
    if not (a.by or "").strip() or len((a.quote or "").split()) < 2:
        print("REFUSED: --by and --quote (the approver's words, verbatim, two words or more) are required",
              file=sys.stderr)
        return 1
    verified = quote_in_transcript(a.quote)
    _br = by_refusal(job, a.by)                         # (3.1) --by names the Approver
    if _br:
        print(f"REFUSED: {_br}", file=sys.stderr)
        return 1
    if verified == "no-transcript":                    # (v2.61.0) an allowance is never made from an unchecked quote
        print("REFUSED: no session transcript is recorded (the SessionStart hook writes its path), so the quote "
              "cannot be checked. An allowance pre-approves calls with no prompt, so it is never created from an "
              "unchecked quote. Run this inside the Claude Code session where the owner said it.", file=sys.stderr)
        return 1
    if verified == "not-found":
        print("REFUSED: that quote appears in no human turn of the current session transcript. Ask the "
              "approver once — the batch and the regens it covers — and record what they wrote.",
              file=sys.stderr)
        return 1
    eligible = sorted({str(sc.get("shot")) for sc in job.sidecars(relint=True)
                       if sc.get("kind") in ALLOW_KINDS[a.kind] and sc.get("shot")
                       and not sc["_stale"] and not sc["_forged"]})
    shots = eligible if (a.shots or "").strip().lower() == "all" else _shot_list(a.shots)
    if not shots:
        print(f"REFUSED: no shots — `--shots S1,S2` or `--shots S1-S10`, or `all` for every linted "
              f"{a.kind} prompt", file=sys.stderr)
        return 1
    missing = [sh for sh in shots if sh not in eligible]
    if missing:
        print(f"REFUSED: no current linted {a.kind} prompt for {', '.join(missing)} — lint them first; an "
              f"allowance covers prompts that exist, not ones written later", file=sys.stderr)
        return 1
    if job.is_eval_lane():
        # (v2.72.0) in the evaluation lane an allowance only skips the ask: the shots must be on the plan and the
        # generations per shot are capped by the plan's `Takes per shot` (the plan, not the allowance, is the counter)
        _lp = eval_lane_problems(job)
        if _lp:
            print(f"REFUSED: {_lp[0]}", file=sys.stderr); return 1
        _txt = _eval_plan_text(job)
        _off = [sh for sh in shots if sh not in job_tier.plan_shots(_txt)]
        if _off:
            print(f"REFUSED: {', '.join(_off)} not on the plan's `Shots:` line — an allowance covers the plan's shots only",
                  file=sys.stderr); return 1
        _takes = job_tier.plan_numbers(_txt)["takes"] or 1
        regens = (_takes - 1) if a.regens is None else int(a.regens)
        if not 0 <= regens <= _takes - 1:
            print(f"REFUSED: --regens {regens} — the plan allows {_takes} take(s) per shot, so at most {_takes - 1} "
                  f"regen(s)", file=sys.stderr); return 1
    else:
        regens = default_regens()[0] if a.regens is None else int(a.regens)
        if not 0 <= regens <= 5:
            print("REFUSED: --regens is 0..5 per shot", file=sys.stderr); return 1
    al = {"id": f"A{len(rows) + 1}", "kind": a.kind, "shots": shots, "regens": regens, "per_shot": 1 + regens,
          "by": a.by.strip(), "quote": a.quote.strip(), "ts": now(),
          "verified": "transcript" if verified == "verified" else "UNVERIFIED", "used": {}}
    rows.append(al)
    save_allowances(job, rows)
    job.log("allow", {k: al[k] for k in ("id", "kind", "shots", "regens", "by", "verified")})
    print(f"ALLOWANCE {allowance_line(al)} — linted {a.kind} calls for these shots now go through without "
          f"a prompt until each has had {al['per_shot']} generation(s)"
          + ("" if verified == "verified" else " · quote UNVERIFIED (no session transcript recorded)"))
    return 0


def cmd_approve(a) -> int:
    job, why = active_job()
    if not job:
        print(f"no active job ({why}) — `gate.py open <job-dir>`", file=sys.stderr); return 1
    # ⛔ Job.fields and Job.profile_path are populated by validate(), and cmd_approve never called
    # it — so `prof` below was ALWAYS None, the client profile was never read, and the category
    # rules never reached the lint. A mattress script with an unqualified "Made in USA" (16 CFR
    # §323.2 — a $753,000 FTC action against a direct competitor) was approved clean. The universal
    # rules still fired, which is why it looked like it worked.
    job.validate()
    stage = a.stage.strip()
    if ":" not in stage:                       # (3.1, build review 1) `Export` must run every export check
        stage = stage.lower()
    base = stage.split(":")[0].lower()
    if job.ever_evaluated() and not job.is_eval_lane():     # (v2.72.0, build review 1, Grok)
        print(f"REFUSED: `{stage}` — this job ran in the evaluation lane (an `eval` approval in its APPROVALS.md) and its "
              f"checkpoint no longer says `Tier: evaluation` + `Lane: eval`. An evaluation never becomes production: "
              f"nothing more is approved here. Open a new production job.", file=sys.stderr)
        return 1
    # endframe:<SHOT> is approved exactly like frame:<SHOT> — an artifact, a media id, script
    # first — because the picture a clip ARRIVES at is as fixed as the one it starts from.
    is_frame = stage.lower().startswith(("frame:", "endframe:"))
    # prop:<NAME> (v2.49.0): a hero prop's sheet, approved like a character sheet — the reference route binds it
    is_char = stage.lower().startswith(("character:", "prop:"))
    is_block = stage.lower().startswith("blocking:")
    is_family = stage.lower().startswith("family:")
    is_world = stage.lower().startswith("world:")
    # target:<SHOT> (v2.45; house decision 2026-10-28): the per-shot opt-in that lets an AI edit of our own footage
    # become a MODEL REFERENCE (`kind: edit`, `use: target`). --artifact names the source picture that may be edited
    is_target = stage.lower().startswith("target:")
    # genjutsu:<SHOT> (v2.46.1; 2026-11-03, "Include Genjutsu"): the human signs the Genjutsu SPEC — model (full
    # or Lite), the one source video, the reference images — because that file is the whole call
    is_gj = stage.lower().startswith("genjutsu:")
    is_brief = base == "brief" and ":" not in stage
    is_eval = base == "eval" and ":" not in stage          # (v2.72.0) the evaluation lane's one approval
    if base not in STAGES and not (is_frame or is_char or is_brief or is_block or is_family or is_world or is_target
                                   or is_gj or is_eval):
        print(f"error: stage must be one of {', '.join(STAGES)}, frame:<SHOT>, endframe:<SHOT>, "
              f"blocking:<SHOT>, family:<FAMILY>, world:<LOCATION>, target:<SHOT>, genjutsu:<SHOT>, character:<NAME> or "
              f"prop:<NAME> — "
              f"or, in a stills job (Mode S), brief", file=sys.stderr)
        return 2
    if (is_frame or is_char or is_block or is_family or is_world or is_target or is_gj) and \
            not SHOT_RE.match(stage.split(":", 1)[1] or ""):
        print(f"error: {base}:<id> needs an id of letters, digits, - _ (S3, S0B, hero)", file=sys.stderr)
        return 2
    # --- the lane: a stills job signs brief · frame:<ID> · export, and nothing else ---------------
    stills = job.is_stills()
    if is_brief and not stills:
        print(f"REFUSED: `brief` is the stills lane's approval (Mode S) and this job is Mode "
              f"{(job.fields.get('mode') or '?')[:1]} — a video job's chain is "
              f"{' → '.join(STAGES)}, and its script is the approval `brief` would be skipping.",
              file=sys.stderr)
        return 1
    if stills and is_family:
        print("REFUSED: `family:` — the insert lane belongs to the video modes; a stills job signs "
              "each still under its brief", file=sys.stderr)
        return 1
    if stills and is_gj:
        print("REFUSED: `genjutsu:` re-renders a video — a stills job (Mode S) makes images only", file=sys.stderr)
        return 1
    # --- (v2.72.0) the evaluation lane signs eval · frame: · endframe: · character: · prop: · world:, nothing else
    eval_lane = job.is_eval_lane()
    if is_eval and not eval_lane:
        print("REFUSED: `eval` is the evaluation lane's approval — this job's checkpoint does not say `Tier: evaluation` "
              "and `Lane: eval`. A production job's chain is " + " → ".join(STAGES) + ".", file=sys.stderr)
        return 1
    if eval_lane and not (is_eval or is_frame or is_char or is_world):
        print(f"REFUSED: `{stage}` — this is an evaluation job (the evaluation lane): it signs `eval`, `frame:` / "
              f"`endframe:`, `character:` / `prop:` and `world:`, nothing else. It answers a question; it has no "
              f"{base}.", file=sys.stderr)
        return 1
    if is_eval:
        _others = [r for r in job.approvals() if r["stage"].lower() != "eval"]
        if _others or eval_generated(job) or load_allowances(job):
            print("REFUSED: `eval` — the plan is fixed once anything else exists: " +
                  (f"approvals ({', '.join(r['stage'] for r in _others[:4])})" if _others else
                   "an allowance" if load_allowances(job) and not eval_generated(job) else
                   "a generation is recorded or reserved") +
                  ". A plan is approved first, and may be replaced only before the first generation. For a new "
                  "question, open a new evaluation job.", file=sys.stderr)
            return 1
        _ap = os.path.abspath(os.path.join(job.path, job_tier.PLAN_FILE))
        if not a.artifact or os.path.abspath(a.artifact if os.path.isabs(a.artifact)
                                             else os.path.join(job.path, a.artifact)) != _ap:
            print(f"REFUSED: `eval` needs --artifact {job_tier.PLAN_FILE} (the plan the person approved)", file=sys.stderr)
            return 1
        if not os.path.isfile(_ap):
            print(f"REFUSED: {job_tier.PLAN_FILE} is missing — copy assets/eval-plan-template.md there and fill it",
                  file=sys.stderr)
            return 1
        _env = ENVELOPE_RE.search(job.fields.get("budget") or "")
        _fails, _warns = job_tier.plan_problems(read(_ap), job.fields.get("question") or "",
                                                float(_env.group(1)) if _env else None)
        if _env is None:
            _fails.append("the checkpoint `Budget:` has no envelope figure, so the plan's budget has nothing to sit "
                          "under — write the envelope first")
        if _fails:
            print("REFUSED: `eval` — 00-brief/EVAL-PLAN.md:\n  - " + "\n  - ".join(_fails), file=sys.stderr)
            return 1
        for w_ in _warns:
            print(f"  ⚠ {w_}", file=sys.stderr)
    if stills and not (is_brief or base == "export" or stage.lower().startswith("frame:") or is_world):
        print(f"REFUSED: `{stage}` — this is a stills job (Mode S): only `brief`, `frame:<ID>` and "
              f"`export` are approved here. concept · script · cast · audio · clips · music · lock · "
              f"titles (and endframe:/character:) belong to the video modes A–D.", file=sys.stderr)
        return 1

    # ⛔ AN EVALUATION NEVER SHIPS (house decision 2026-10-25). The tier bends the 1080p floor, so
    # the two approvals that lead to delivery are refused outright in an evaluation job — the
    # refusal is what makes the bend safe. Its result goes in a lab README and the LEDGER instead.
    if job.tier() == "evaluation" and base in ("lock", "export"):
        print(f"REFUSED: `{stage}` in an evaluation job (`Tier: evaluation`) — nothing an evaluation "
              f"makes is locked or exported. Write its answer up (the lab README, memory/LEDGER.md) "
              f"and shoot the deliverable in a production job.", file=sys.stderr)
        return 1

    # A previz image is a category error at ANY stage, so this precedes the chain-order check.
    if a.artifact and os.sep + "_previz" + os.sep in os.path.abspath(a.artifact):
        print("REFUSED: that artifact lives under 00-brief/_previz/ — previz is concept art for a "
              "development decision, never a frame anything is conformed to. Generate the frame "
              "from its linted prompt and approve that.", file=sys.stderr)
        return 1

    # --- order: a stage cannot be signed before what it depends on --------------------------------
    need = list(REQUIRES.get(base, []))
    if is_frame or is_char or is_block or is_family or is_world or is_target or is_gj:
        need = ["script"]
    if stills:
        need = [] if is_brief else ["brief"]
    if eval_lane:                                          # (v2.72.0) the plan stands where the script stood
        need = [] if is_eval else ["eval"]
        _lp = [] if is_eval else eval_lane_problems(job)
        if _lp:
            print(f"REFUSED: `{stage}` — {_lp[0]}", file=sys.stderr)
            return 1
    # (v2.66.0) in a job made from the 2.65 template or later, nothing after the script is signed before the
    # storyboard: no cast, no sheet, no frame, no clips
    if not stills and not eval_lane and base not in ("concept", "script", "storyboard", "audio", "music") and \
            "storyboard" not in need and _storyboard().required(job.path):
        need.append("storyboard")
    missing = [n for n in need if not job.approved(n)]
    if missing:
        chain = ("brief → frame:<ID> → export (Mode S, the stills lane)" if stills else
                 f"{' → '.join(STAGES)} (SKILL.md §2)")
        print(f"REFUSED: `{stage}` needs {', '.join(missing)} approved first — the chain is "
              f"{chain}. Signing out of order is how a cut gets graded "
              f"before it is locked and captions get timed to a picture that then changes.",
              file=sys.stderr)
        return 1
    if is_family:
        try:                                       # (3.1 build review 1) a family shown in a review pack needs its code
            import review_pack as _rpf
            _prf = _rpf.approval_refusal(job.path, stage, getattr(a, "pack", None), a.quote or "")
        except Exception as e:                     # noqa: BLE001 — a check that cannot run refuses
            _prf = f"the review-pack check could not run ({type(e).__name__})"
        if _prf:
            print(f"REFUSED: {_prf}", file=sys.stderr)
            return 1
        return _approve_family(job, a, stage)
    # A stills job ships what the brief lists: a still is approved only under an intact brief that
    # names its ID — the same two conditions every generate_image call in the lane already meets.
    if stills and is_frame:
        sid = stage.split(":", 1)[1]
        bp = brief_problems(job)
        if bp or not brief_names(job, sid):
            print(f"REFUSED: `{stage}` — " + (bp[0] if bp else
                  f"{sid!r} is not named in the approved brief; add it to the brief and re-approve "
                  f"the brief first"), file=sys.stderr)
            return 1

    # --- development: the creative gate, before the concept and before the script -----------------
    if base in ("concept", "script"):
        try:
            dev = _develop_module()
            r = dev.check(job.path, phase="concept" if base == "concept" else "full")
        except Exception as e:                       # a broken checker must not silently pass work
            print(f"REFUSED: develop.py could not run ({e}) — fix it before approving {stage}",
                  file=sys.stderr)
            return 1
        if not r["ok"]:
            print(f"REFUSED: `{stage}` — 00-brief/DEVELOPMENT.md is not complete "
                  f"({'before the pick' if base == 'concept' else 'before a script is signed'}):",
                  file=sys.stderr)
            for f in r["fails"]:
                print(f"  - {f}", file=sys.stderr)
            print("  `develop.py status <job>` shows the order. One draft is one guess; the "
                  "development doc is what makes five real options and an argument against them "
                  "un-skippable.", file=sys.stderr)
            return 1

    # --- (v2.66.0) the picture sign-offs: the film in time, then the start frames side by side ------------
    if base in PICTURE_SIGNOFFS:
        SB = _storyboard()
        try:
            sp = SB.signoff_problems(job.path) if base == "storyboard" else SB.frames_signoff_problems(job.path)
        except Exception as e:                       # a broken checker must not silently pass work
            print(f"REFUSED: storyboard.py could not run ({e}) — fix it before approving {stage}", file=sys.stderr)
            return 1
        if sp:
            print(f"REFUSED: `{stage}` — " + ("the storyboard is not ready to sign:" if base == "storyboard" else
                                             "the start-frame sheet is not ready to sign:"), file=sys.stderr)
            for x in sp:
                print(f"  - {x}", file=sys.stderr)
            print("  " + ("Show the person the storyboard page and the animatic first: a panel changed now costs "
                          "nothing, the same change after the clips costs a regeneration (references/storyboarding.md)."
                          if base == "storyboard" else
                          "Show the person every approved start frame on one page, in cut order "
                          "(references/storyboarding.md §5)."), file=sys.stderr)
            return 1
        # the signed thing is fixed by the gate, not by an argument: the shot list, or the frame sheet
        a.artifact = (SB.shotlist_path(job.path) if base == "storyboard"
                      else os.path.join(job.path, SB.FRAMES_BOARD_REL))

    # The cross-shot view: the findings no single shot is wrong about. `cast` is where a film
    # commits to who and what it needs, so it is where "six shots need a hero nobody designed" and
    # "four shots each sourcing one apron" have to surface — after that they are just spend.
    if base == "cast":
        try:
            import importlib
            if HERE not in sys.path:
                sys.path.insert(0, HERE)
            BD = importlib.import_module("breakdown")
            bd = BD.breakdown(job.path)
        except Exception as e:
            print(f"REFUSED: the breakdown could not be read ({e}) — fix it before approving "
                  f"{stage}", file=sys.stderr)
            return 1
        blocking = [f for f in bd["findings"]
                    if f["kind"] in ("unlocked-character", "unnamed-character")]
        if blocking:
            print(f"REFUSED: `{stage}` — the cast is not locked:", file=sys.stderr)
            for f in blocking:
                print(f"  - {f['detail']}", file=sys.stderr)
            print("  `breakdown.py <job>` is the whole cross-shot view. ⛔ Identity is locked by a "
                  "reference, never by text: a description drifts between generations, and casting "
                  "is precisely the stage that is supposed to stop that.", file=sys.stderr)
            return 1

    # --- pre-production: references are sourced and cleared BEFORE a credit is spent --------------
    # `cast` unlocks character and start-frame generation; `clips` unlocks motion. Both spend. A
    # reference judged after the render has already cost the money it was meant to save
    # (stock-sourcing.md §5, §9; the reference plan in prompting-craft.md §6b).
    if base in ("cast", "clips"):
        try:
            rp = refplan_state(job.path)
        except Exception as e:                       # a broken checker must not silently pass work
            print(f"REFUSED: the reference plan could not be read ({e}) — fix it before approving "
                  f"{stage}", file=sys.stderr)
            return 1
        if not rp["dirs"]:
            print(f"REFUSED: `{stage}` — no *.prompt.md anywhere under the job. The shots are the "
                  f"plan; approving generation with no written prompts is approving whatever the "
                  f"model felt like (prompt_lint.py --template frame|clip).", file=sys.stderr)
            return 1
        if not rp["ok"]:
            print(f"REFUSED: `{stage}` — the reference plan is not sourced and cleared:",
                  file=sys.stderr)
            for r in rp["gaps"][:12]:
                print(f"  - {r['shot']} · {r['what']}: {r['detail']}", file=sys.stderr)
            for r in rp["blocked"][:12]:
                print(f"  - {r['shot']} · {r['what']}: {r['detail']}  ({r['source']})",
                      file=sys.stderr)
            extra = len(rp["gaps"]) + len(rp["blocked"]) - 24
            if extra > 0:
                print(f"  … and {extra} more", file=sys.stderr)
            print("  `refsource.py brief <prompts-dir>` turns each gap into a Pixabay search built "
                  "from the prompt's own words; `fill --execute` fetches candidates, you look at "
                  "them, `adopt` writes your pick back into the shot. `provenance.py record` "
                  "answers the §5 blockers on anything still NOT CLEARED.", file=sys.stderr)
            return 1

    # --- the boards: the human had something to LOOK at ------------------------------------------
    # The complaint this answers, verbatim: "wasted AI gens on something that should be obvious from
    # planning and the prompt". It is obvious — on a board. It is invisible in a `refs:` block and
    # in five sentences read one after another.
    if base == "concept":
        b = os.path.join(job.path, "00-brief", "BOARD-concepts.html")
        why_b = board_stale(b, [os.path.join(job.path, "00-brief", "DEVELOPMENT.md")])
        if why_b:
            print(f"REFUSED: `concept` — the concept board is not current: {why_b}.\n"
                  f"  `board.py concepts {os.path.relpath(job.path)}` — one page, every concept "
                  f"side by side with what killed the dead ones. Five concepts read in sequence "
                  f"get ratified; five concepts seen together get chosen between, and this is the "
                  f"choice the whole development phase exists to put in front of you.",
                  file=sys.stderr)
            return 1
    if base in ("cast", "clips"):
        b = os.path.join(job.path, "01-script", "BOARD-shots.html")
        srcs = []
        for root, dd, ff in os.walk(job.path):
            dd[:] = [d for d in dd if not d.startswith((".", "_to_delete"))]
            srcs += [os.path.join(root, f) for f in ff if f.endswith(".prompt.md")]
        why_b = board_stale(b, srcs)
        if why_b:
            print(f"REFUSED: `{stage}` — the shot board is not current: {why_b}.\n"
                  f"  `board.py shots {os.path.relpath(job.path)}` renders every reference slot as "
                  f"the picture it actually binds. An empty slot, an uncleared face or a reference "
                  f"that is simply not the thing the shot needs is obvious there and invisible in "
                  f"the prompt file. Look at it before you spend.", file=sys.stderr)
            return 1

    if base == "clips":
        # ⛔ every exterior clip read against its world card (2026-10-27, lab-00020 B12): the movers counted, nothing new
        import world as _WD  # noqa: E402  (stdlib-only)
        wr = _WD.check_reads(job.path)
        if wr:
            print("REFUSED: `clips` — the returned clips were not read against their world (world.py read; "
                  "references/world-design.md §7):\n  - " + "\n  - ".join(wr), file=sys.stderr)
            return 1
        cov = coverage_state(job.path)
        if not cov["ok"]:
            names = ", ".join(cov["missing_reaction"])
            print(f"REFUSED: `clips` — no listener reaction planned in {names}. A scene generated "
                  f"as exactly its dialogue clips gives the editor no choices: nothing to cut away "
                  f"to when a syllable floats, nothing to vary pacing with, nothing to react with "
                  f"(direction.md §3, the coverage floor).\n"
                  f"  A reaction is a `type: reaction` clip prompt — silent, the same character "
                  f"listening. It is the cheapest insurance in the pipeline: the retake tree's "
                  f"second question is whether coverage already solves the fault, at a cost of "
                  f"about zero.\n"
                  f"  If a scene deliberately has none, say so — but say it to a person, not to "
                  f"the gate.", file=sys.stderr)
            return 1

    # --- picture lock: the one-way door of post --------------------------------------------------
    if base == "lock":
        qa = os.path.join(job.path, "09-qa", "QA-LOG.md")
        if not os.path.isfile(qa) or len(read(qa).splitlines()) < 3:
            print("REFUSED: `lock` needs 09-qa/QA-LOG.md with real verdicts — picture lock is the "
                  "door everything downstream is cut to; locking un-QA'd picture means the grade, "
                  "the mix and the captions are all conformed to a cut that will change "
                  "(qa_log.py; realism-qa.md §6).", file=sys.stderr)
            return 1
        # ⛔ MOTION QA (house decision 2026-10-26: "Refuse picture lock without it"). Every shot in the
        # cut is measured — camera, framing, subject direction in and out, the action points — and set
        # against its prompt's plan; the cut's joins are measured and each planned hand-off checked.
        # A report about other bytes is stale. Findings are questions for the director; MISSING or
        # STALE reports are what refuse.
        # ⛔ …and the cut's transition and ramp budgets (house rule C4, C5) are in that same check.
        import motion_qa  # noqa: E402  (stdlib-only on this path; the measuring imports are lazy)
        mp = motion_qa.check_job(job.path)
        if mp:
            print("REFUSED: `lock` — the motion analysis is not complete for this cut "
                  "(motion_qa.py; shot-handoff.md §4b, realism-qa.md):\n  - " + "\n  - ".join(mp),
                  file=sys.stderr)
            return 1
        # ⛔ THE TITLE CARD (house rule C3, 2026-10-26: "Yes, the card is the permission"). Every project
        # has one, approved with the storyboard — the type, the scale, the motion tokens, which kinds of title
        # may appear at all, the transition and ramp budgets the lock check above reads. No card, no lock.
        import title_card  # noqa: E402  (stdlib-only)
        tc = title_card.check_card(job.path)
        if tc:
            print("REFUSED: `lock` — the project's title card is missing or does not lint "
                  "(title_card.py; typography-and-captions.md §6c):\n  - " + "\n  - ".join(tc), file=sys.stderr)
            return 1
        # ⛔ AERIALS (house rule 2026-10-26, C4: "Split: rules refuse, measures warn"). Every aerial, FPV,
        # insect or planet clip in the cut carries its declaration and passes its rules (a job, a subject, an
        # end, a real seed for a real place, a sound chain); the course or property cards, the overlays and the
        # rights manifest hold. The measures (scale, drift, seams, stars) and the cut notes only warn.
        import aerial_qa  # noqa: E402  (the measuring imports are lazy)
        import flyover  # noqa: E402
        ap_, aw_ = aerial_qa.check_job(job.path)
        fp_, fw_ = flyover.check_job(job.path)
        for w_ in aw_ + fw_:
            print(f"  NOTE (aerial) {w_}", file=sys.stderr)
        if ap_ or fp_:
            print("REFUSED: `lock` — the aerial rules do not hold (aerial_qa.py check; flyover.py check; "
                  "aerial-and-fpv.md):\n  - " + "\n  - ".join(ap_ + fp_), file=sys.stderr)
            return 1
        # ⛔ THE SOUND-OFF READ (owner request 2026-10-27, "Research … + model-council + implement"; jury K1). Before
        # lock the read is advisory — a story fix is cheapest now, so the notes say what has not been read — with one
        # exception: a beat the story map says the picture does not carry, unfixed and unwaived, refuses the lock.
        import soundoff  # noqa: E402  (stdlib-only)
        sp_, sw_ = soundoff.lock_check(job.path)
        for w_ in sw_:
            print(f"  NOTE (sound-off) {w_}", file=sys.stderr)
        if sp_:
            print("REFUSED: `lock` — the story does not read without sound (soundoff.py; references/sound-off-story.md):"
                  "\n  - " + "\n  - ".join(sp_), file=sys.stderr)
            return 1
    if base == "titles":
        # every title the card permits: its spec against the card (kind, words, dwell, anchor, the settle,
        # never across a transition or a ramp), rendered, and passing title_qa.py on the composite
        import title_card  # noqa: E402  (stdlib-only)
        tp = title_card.check_job(job.path)
        if tp:
            print("REFUSED: `titles` — not every title is cleared (title_card.py check; title_qa.py; "
                  "typography-and-captions.md §6c):\n  - " + "\n  - ".join(tp), file=sys.stderr)
            return 1
        import flyover  # noqa: E402  the hole cards and room labels against their cards
        ov, _ = flyover.overlays(job.path)
        if ov:
            print("REFUSED: `titles` — an overlay does not match its card (flyover.py overlays):\n  - "
                  + "\n  - ".join(ov), file=sys.stderr)
            return 1
    if stage == "export":
        # (3.1) the studio's own "no" blocks, for video AND stills (likeness only: a stills job has no music); an
        # unreadable or malformed answer blocks too. A "yes" or an unanswered question never clears anything.
        try:
            import studio as _studio
            _no = _studio.export_refusals(stills=bool(stills))
        except Exception as e:                       # noqa: BLE001 — a check that cannot run refuses
            _no = [f"the studio answers could not be read ({type(e).__name__})"]
        if _no:
            print("REFUSED: `export` —\n  - " + "\n  - ".join(_no) + "\n  Clear it for THIS delivery (licensed "
                  "music, signed releases), then update the studio's answer (`studio.py set`), or keep it and do "
                  "not export.", file=sys.stderr)
            return 1
    if stage == "export" and stills:
        # A stills job has no cut to watch and no .mp4 for export_qc.py to measure, so the two
        # video checks below cannot be met — and must not be faked. What it does have: at least one
        # still a human approved, and the deliverable files themselves in 10-export/.
        exp = os.path.join(job.path, "10-export")
        imgs = sorted(p for p in glob.glob(os.path.join(exp, "*")) if p.lower().endswith(IMAGE_EXT))
        sp = []
        if not any(r["stage"].lower().startswith("frame:") for r in job.approvals()):
            sp.append("no still is approved — `gate.py approve frame:<ID> --artifact <file> "
                      "--media-id <id>` for each one that ships")
        if not imgs:
            sp.append(f"10-export/ holds no image ({', '.join(IMAGE_EXT)}) — there is no export to "
                      f"approve")
        if sp:
            print("REFUSED: `export` (stills job):\n  - " + "\n  - ".join(sp), file=sys.stderr)
            return 1
    elif stage == "export":
        # ⛔ Every other gate here inspects a CLIP or probes a FILE. Nothing ever watched the FILM,
        # so a flash frame at a join, a black frame, a caption over a cut or a music seam was
        # invisible to every check in this skill — and it is what a client sees first. A master row
        # is one line in QA-LOG.md carrying two distinct timecodes, which cannot be written about a
        # cut nobody played (qa_log.py --gate master).
        qa = os.path.join(job.path, "09-qa", "QA-LOG.md")
        rows = [l for l in read(qa).splitlines() if l.startswith("| ")] if os.path.isfile(qa) else []
        if not any(re.search(r"\|\s*master\s*\|\s*PASS\s*\|", l, re.I) for l in rows):
            print("REFUSED: `export` needs a master-gate PASS in 09-qa/QA-LOG.md — somebody has to "
                  "have WATCHED the assembled cut, start to finish, before it goes out. Every other "
                  "gate in this skill inspects one clip or probes one file.\n"
                  "  python3 scripts/qa_log.py --project <job> --gate master --verdict PASS \\\n"
                  "      --obs \"room tone holds under the 0:12 cut, heard '<word>' clean over the "
                  "music; 1-frame flash on the incoming shot at 0:24\"\n"
                  "Two distinct timecodes, one heard and one seen. Run export_qc.py first — it "
                  "measures the file; the master gate is the part only a person can do.",
                  file=sys.stderr)
            return 1
        # ⛔ …and nothing ever read the FILE (2026-09-14). The refusal above says "run export_qc.py
        # first" and the gate never checked that anyone had: an export could be approved with no report,
        # with a FAIL report, or with a PASS about a render that was replaced afterwards. Every file in
        # 10-export/ is a deliverable, so every one needs a passing report about its exact bytes.
        exp = os.path.join(job.path, "10-export")
        renders = sorted(p for p in glob.glob(os.path.join(exp, "*"))
                         if p.lower().endswith((".mp4", ".mov", ".mxf")))
        qc_problems = [] if renders else ["10-export/ holds no .mp4/.mov/.mxf — there is no export to approve"]
        # (v2.48.0, project switch upload-master) a report export_qc.py wrote with --upload-master says so on its
        # `upload master:` line: that file is the job's one extra upload copy, the preset's shape at a larger size
        # (realism-qa V15 lifted for it alone). It passes here only where the job lifts `upload-master`, and never in
        # place of the delivery: another render must pass as the delivery itself, with a report carrying no such line.
        um_why = job.switches.get("upload-master")
        uploads, deliveries = [], []
        for v in renders:
            rel, rp = os.path.relpath(v, job.path), v + ".qc.txt"
            if not os.path.isfile(rp):
                qc_problems.append(f"{rel}: no QC report — python3 scripts/export_qc.py {rel} "
                                   f"--format <preset> --target-duration <s> --report")
                continue
            txt = read(rp)
            digest = re.search(r"^file_sha256:\s*([0-9a-f]{64})\s*$", txt, re.M)
            n_before = len(qc_problems)                       # (v2.48.0, project switch upload-master)
            if not re.search(r"^OVERALL: PASS\b", txt, re.M):
                qc_problems.append(f"{rel}: its QC report does not say OVERALL: PASS")
            elif "checks were skipped" in txt:
                qc_problems.append(f"{rel}: its QC report skipped duration/fps — re-run with --format and "
                                   f"--target-duration")
            elif not digest:
                qc_problems.append(f"{rel}: its QC report names no file_sha256 — re-run export_qc.py --report")
            elif digest.group(1) != sha256_file(v):
                qc_problems.append(f"{rel}: the file changed after it was measured — the report is about a "
                                   f"different render")
            if re.search(r"^upload master:", txt, re.M):     # (v2.48.0, project switch upload-master) (a)
                uploads.append(rel)
                if not um_why:
                    qc_problems.append(f"{rel}: its QC report is an upload master (export_qc.py --upload-master), and "
                                       f"this job does not lift `upload-master` — realism-qa V15: deliver at the "
                                       f"format's resolution and no higher. Add `upload-master — <why this job needs a "
                                       f"larger upload copy>` to the `Switches:` line in 00-brief/CHECKPOINT.md, or take "
                                       f"the copy out of 10-export/")
            elif len(qc_problems) == n_before:
                deliveries.append(rel)
        if uploads and not deliveries:                        # (v2.48.0, project switch upload-master) (b)
            qc_problems.append(f"an upload copy is not the delivery — {', '.join(uploads)} "
                               f"{'is an upload master' if len(uploads) == 1 else 'are upload masters'} "
                               f"(export_qc.py --upload-master), and no other render in 10-export/ passes as the "
                               f"delivery itself: export the delivery at its preset and QC it without --upload-master "
                               f"(python3 scripts/export_qc.py <file> --format <preset> --target-duration <s> --report)")
        if qc_problems:
            print("REFUSED: `export` needs every file in 10-export/ measured by export_qc.py, passing, "
                  "and unchanged since:\n  - " + "\n  - ".join(qc_problems), file=sys.stderr)
            return 1
        for u_ in uploads:                                    # (v2.48.0, project switch upload-master) named at the door
            print(f"  NOTE (upload master) {u_}: the job's extra upload copy, not the delivery (the delivery: "
                  f"{', '.join(deliveries)}) — realism-qa V15 {switches.lifted('upload-master', um_why)}",
                  file=sys.stderr)
        # ⛔ THE MIX (house decision 2026-10-26, the SFX jury: "Export audio gate", "Native audio as guide
        # only", "SFX licence manifest", "Room tone and ambience continuity"). export_qc.py measures the
        # file's level; nothing measured whether the line is heard over the bed, on a phone, folded to
        # mono, with room tone under it — or whether every sound in it may be used in a paid ad.
        import mix_qa  # noqa: E402  (stdlib-only on this path; the measuring imports are lazy)
        mx = mix_qa.check_job(job.path)
        if mx:
            print("REFUSED: `export` — the mix is not cleared (mix_qa.py; editing-and-audio.md, the mix "
                  "gate):\n  - " + "\n  - ".join(mx), file=sys.stderr)
            return 1
        # ⛔ THE LOOK (house decision 2026-10-26, the grading jury: "A: Export look check", and the rulings
        # C1–C4 "Apply all four"). export_qc.py measures size, fps and loudness; nothing measured whether the
        # file is tagged and levelled so a phone shows it as graded, whether a 45+ viewer can read it in
        # glare, or what a platform's re-encode does to it (banding, blocks, grain).
        import look_qa  # noqa: E402  (stdlib-only on this path; the measuring imports are lazy)
        lk = look_qa.check_job(job.path)
        if lk:
            print("REFUSED: `export` — the look is not cleared (look_qa.py; editing-and-audio.md, the grade "
                  "and the export look gate):\n  - " + "\n  - ".join(lk), file=sys.stderr)
            return 1
        # the titles again: a render replaced or a spec edited after `approve titles` is a different title
        import title_card  # noqa: E402  (stdlib-only)
        tp = title_card.check_job(job.path)
        if tp:
            print("REFUSED: `export` — the titles changed after they were cleared (title_card.py check):\n  - "
                  + "\n  - ".join(tp), file=sys.stderr)
            return 1
        import flyover  # noqa: E402
        ov, _ = flyover.overlays(job.path)
        if ov:
            print("REFUSED: `export` — an overlay does not match its card (flyover.py overlays):\n  - "
                  + "\n  - ".join(ov), file=sys.stderr)
            return 1
        # ⛔ ON-SCREEN TEXT IS MADE IN RESOLVE (2026-10-27: "Claude keeps insisting in creating mp4s of captions
        # etc outside resolve, it should defrult to Resolve or Fusion native elements. Not create outside for no
        # reason" — ruling C7). A delivery file ffmpeg made needs a recorded reason (one of four); a caption burn
        # Resolve made is checked in the pixels, because an accepted render setting is not a burned caption. Every
        # outside render is printed, so the owner reads each reason at the door.
        import native  # noqa: E402  (stdlib-only until there is a file to probe)
        np_, nw_ = native.check_job(job.path)
        if np_:
            print("REFUSED: `export` — text made outside Resolve without a reason, or captions not shown in the pixels "
                  "(native.py check; typography-and-captions.md §6c, editing-and-audio.md § Captions):\n  - "
                  + "\n  - ".join(np_), file=sys.stderr)
            return 1
        for w_ in nw_:
            print(f"  ▣ {w_}", file=sys.stderr)
        # ⛔ THE MUSIC TO PICTURE (house decision 2026-10-26, the music jury: "A: The fit", "B: Length and edits",
        # "C: The checks", "D: Arranging", "Music only; suggest cut nudges"). `approve music` comes before the
        # lock, so the fit can only be checked here, against the locked cut: a plan, a current REBUILD.json (v2.50: the edit rebuilt in Resolve from the original; the render is a preview),
        # no cut moved without an approved nudge, no click at a music edit, the stretch cap, no sung lyrics under
        # speech, the licence allowing the edits. Rules refuse; measures print as notes (C5).
        # (v2.48.0, project switch music-led) check_job reads the job's switch itself (switches.on), so `music_fit.py
        # check` and this gate cannot disagree: in a music-led job the song is the deliverable and the picture is cut to
        # it, so the fit, its render, a stale fit and a moved-cut nudge are lifted and printed below as a ♪ note; a
        # stretch of any size, an edit the licence does not allow and `music: none` still refuse.
        import music_fit  # noqa: E402  (stdlib-only until there is a render to measure)
        mp_, mw_ = music_fit.check_job(job.path)
        if mp_:
            # (v2.48.0, project switch music-led) the refusal names what failed: the song as delivered, not a fit
            what_ = ("the song does not hold as this music-led job's deliverable (music_fit.py check; project switch "
                     "`music-led`; editing-and-audio.md, music to picture)" if "music-led" in job.switches else
                     "the music is not fitted to the cut (music_fit.py check; editing-and-audio.md, music to picture)")
            print(f"REFUSED: `export` — {what_}:\n  - " + "\n  - ".join(mp_), file=sys.stderr)
            return 1
        for w_ in mw_:
            print(f"  ♪ {w_}", file=sys.stderr)
        # ⛔ THE LEAD COMPOSER (house decision 2026-10-27: all four packages; "Skill drafts, I edit"; the tiered
        # window; consent first with a whitelist; "AI vocals - needed sometimes"). Music composed here or generated
        # must carry its paperwork, its provenance, the owner's edit of the motif, the blind bake-off of its route,
        # the client's consent dated before generation, and an element sheet saying what each sound is.
        # (3.1) the studio's own "no" blocks: music not cleared for paid use, or no likeness releases. A "yes" or an
        # unanswered question never clears anything — the composer and sound-off checks below still run.
        # (moved above the stills split in build review 1: a stills export of real faces is blocked too)
        import composer  # noqa: E402  (stdlib-only until there is a render to measure)
        cp_, cw_ = composer.check_job(job.path)
        if cp_:
            print("REFUSED: `export` — the composed or generated music is not cleared (composer.py check; "
                  "editing-and-audio.md, the lead composer):\n  - " + "\n  - ".join(cp_), file=sys.stderr)
            return 1
        for w_ in cw_:
            print(f"  ♫ {w_}", file=sys.stderr)
        # ⛔ THE SOUND-OFF CHECK (owner request 2026-10-27: "One of the main ways for clients to check is if the video
        # tells a story without sound and voiceover"; lab-00019, the jury unanimous). T2 — the picture alone, read by
        # someone who has not read the script, the retell first — and T1, the muted feed, on every delivery file,
        # each on a proof of these exact bytes; the story map read beat by beat; the captions measured. The sound-on
        # master gate above is unchanged: a silent pass judges a different film (Hullfish), so it never replaces it.
        import soundoff  # noqa: E402  (stdlib-only)
        so_, sw_ = soundoff.check_job(job.path)
        if so_:
            print("REFUSED: `export` — the sound-off check is not done on these bytes (soundoff.py check; "
                  "references/sound-off-story.md):\n  - " + "\n  - ".join(so_), file=sys.stderr)
            return 1
        for w_ in sw_:
            print(f"  🔇 {w_}", file=sys.stderr)
        rep_ = replica_source(job)
        if rep_:
            print(f"  ⚠ EXPORT OF A REPLICA — {replica_line(rep_)}. This approval records that you exported it "
                  f"knowing that.", file=sys.stderr)
    quote = (a.quote or "").strip()
    if len(quote.split()) < 2:
        print("REFUSED: --quote must be the approver's reply verbatim (two words or more). "
              "A one-word 'ok' is recorded as what it is; the gate wants the sentence. "
              "⚡ If you asked with AskUserQuestion, the picked LABEL is the quote — so write the "
              "options as sentences (\"Approve the S3 start frame as it is\"), not \"Approved\" "
              "(2026-09-19: a one-word option cost the client a second round-trip).",
              file=sys.stderr)
        return 1
    verified = quote_in_transcript(quote)
    _br = by_refusal(job, a.by)                         # (3.1) --by names the Approver
    if _br:
        print(f"REFUSED: {_br}", file=sys.stderr)
        return 1
    if verified == "not-found":
        print("REFUSED: that quote appears in no human turn of the current session transcript. "
              "Ask the approver (AskUserQuestion / the review channel), then record what they "
              "actually wrote. A quote nobody typed is the lipsync incident again.", file=sys.stderr)
        return 1
    _qr = quote_refusal(quote, job) if verified != "verified" else None     # (3.1) no silent UNVERIFIED on a hooked home
    if _qr:
        print(f"REFUSED: {_qr}", file=sys.stderr)
        return 1
    try:                                           # (3.1) a stage shown in a review pack is approved WITH its code
        import review_pack as _rp
        _pr = _rp.approval_refusal(job.path, stage, getattr(a, "pack", None), quote)
    except Exception as e:                         # noqa: BLE001 — a check that cannot run refuses
        _pr = f"the review-pack check could not run ({type(e).__name__})"
    if _pr:
        print(f"REFUSED: {_pr}", file=sys.stderr)
        return 1
    artifact, sha = "", ""
    if base == "script" or is_frame or is_brief or is_block or is_world or is_gj or is_eval:
        if not a.artifact:
            print(f"REFUSED: `{stage}` needs --artifact (the exact file the human approved)",
                  file=sys.stderr)
            return 1
    # (v2.67.0) the signed script is the option they picked, and an answer to the comedy question is the person's
    # typed words, checked like an approval quote. The decision lives in develop.approve_script_refusals, which the
    # develop.py self-test covers; this is only the hand-over (test_gate.py checks the hand-over exists).
    if base == "script" and a.artifact:
        _ap = os.path.abspath(a.artifact if os.path.isabs(a.artifact) else os.path.join(job.path, a.artifact))
        try:
            _refusals = _develop_module().approve_script_refusals(
                job.path, _ap, lambda q: quote_refusal(q, job) is None)       # (3.1) verified (hookless: present)
        except Exception as e:                       # a broken checker must not silently pass work
            print(f"REFUSED: develop.py could not compare the signed script with the pick ({e})", file=sys.stderr)
            return 1
        if _refusals:
            print("REFUSED: `script` —\n  - " + "\n  - ".join(_refusals), file=sys.stderr)
            return 1
    if a.artifact:
        ap = a.artifact if os.path.isabs(a.artifact) else os.path.join(job.path, a.artifact)
        ap = os.path.abspath(ap)
        if not os.path.isfile(ap):
            print(f"REFUSED: artifact {a.artifact} not found", file=sys.stderr); return 1
        rel = os.path.relpath(ap, job.path)
        if rel.startswith(".."):
            print(f"REFUSED: artifact {a.artifact} is outside the job folder — the approved file "
                  f"lives under the job (pm-workflow.md layout)", file=sys.stderr)
            return 1
        # ⛔ RUN THE CLAIMS LINT. `script-craft.md` §6 makes claim safety a UNIVERSAL scorecard
        # dimension "because it is the one dimension whose failure is not a quality problem but a
        # legal one" — and until 2026-09-07 `gate.py` contained no occurrence of `claims_lint`, so
        # the bar was typed by hand and nothing ever ran the script. That is not a gate.
        # The category rules come from the client profile, so a sleep/mattress client gets its own
        # patterns automatically (clients/<brand>.md §4).
        if base == "script":
            lint = os.path.join(HERE, "claims_lint.py")
            # the category comes from the client profile's own filename, so a mattress client gets
            # the mattress patterns without anyone remembering to pass a flag
            # ⛔ and the regex had to match the profile's real markdown. The line is written
            # `**Claims-category:** `sleep`` — bold markers and a backtick between the colon and
            # the word — so `claims[- ]category:\s*sleep` matched nothing even once the blob was
            # read. Two independent defects on the same feature, and the visible symptom of both
            # was a clean pass.
            cat = ""
            prof = getattr(job, "profile_path", "")
            blob = read(prof) if (prof and os.path.isfile(str(prof))) else ""
            m = re.search(r"claims[-\s]category\s*:?\**\s*[`'\"*]*\s*([a-z]+)", blob, re.I)
            if m and m.group(1).lower() in ("sleep", "beauty", "supplements", "finance"):
                cat = m.group(1).lower()
            if not cat and blob:
                print(f"  note: {os.path.basename(str(prof))} declares no `Claims-category:` — only "
                      f"the universal claim rules ran. If this brand is in a claims-sensitive "
                      f"category (sleep/beauty/supplements/finance), declare it in §4.",
                      file=sys.stderr)
            # ⛔ --allow was named in this block's own refusal message ("re-run with --allow")
            # and there was no such flag on `gate.py approve`, so a phrase the client had approved
            # in writing could never actually pass. An instruction that cannot be followed is worse
            # than no instruction: it teaches people to reach for CINE_GATE=off.
            allow_args = []
            for phrase in (getattr(a, "allow", None) or []):
                allow_args += ["--allow", phrase]
            # the material-connection question is not inferable from a script's words, so the lint
            # reports NOT ASSERTED unless someone answers it. Answer it here, at the approval.
            dis_args = (["--paid"] if getattr(a, "paid", False) else
                        ["--no-material-connection"] if getattr(a, "no_material_connection", False)
                        else [])
            argv = ([sys.executable, lint, ap, "--json"] + (["--category", cat] if cat else [])
                    + allow_args + dis_args)
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
                found = json.loads(r.stdout or "{}") if r.stdout.strip().startswith(("{", "[")) else {}
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:   # noqa: BLE001
                print(f"REFUSED: could not run claims_lint.py on the artifact ({e}). The claim "
                      f"check is not optional — fix the tool or say why in the ledger.",
                      file=sys.stderr)
                return 1
            # ⛔ claims_lint --json returns {"<path>": [rows]}, keyed by FILE, and each row's
            # level field is named `severity`. The first version of this read `findings` and
            # `level` — both absent — so it found nothing and waved through a script with 13
            # findings in it, 6 of them BLOCK. Caught by checking the contract instead of assuming
            # it. A gate that silently passes is worse than no gate: it certifies.
            rows, inconclusive = [], []
            if isinstance(found, list):
                rows = found
            elif isinstance(found, dict):
                inconclusive = [x for x in (found.get("inconclusive") or []) if isinstance(x, str)]
                fnd = found.get("findings")
                buckets = list(fnd.values()) if isinstance(fnd, dict) else ([fnd] if fnd else
                                                                           list(found.values()))
                for v in buckets:
                    if isinstance(v, list):
                        rows += [x for x in v if isinstance(x, dict)]
            # ⛔ INCONCLUSIVE is not clean. The lint returns it when the script's language is one
            # its patterns cannot read — nothing matched because nothing COULD. Passing that as an
            # approval is the silent pass with a signature on it.
            if inconclusive:
                print(f"REFUSED: `script` — claims_lint could not READ {rel}: its patterns are "
                      f"English and this script is not. Nothing matched because nothing could "
                      f"match, so this is not a clean run.\n"
                      f"  Localise the risky-phrase table (compliance.md §4) into that language, or "
                      f"lint an English gloss of the script, then re-run. `--lang-ok` exists for "
                      f"when you have actually done the localisation.", file=sys.stderr)
                return 1
            blocks = [f for f in rows
                      if str(f.get("severity") or f.get("level") or "").upper() == "BLOCK"]
            if blocks:
                print(f"REFUSED: `script` — claims_lint found {len(blocks)} BLOCK-level claim(s) in "
                      f"{rel}. Claim safety is a universal scorecard dimension because its failure "
                      f"is legal, not aesthetic (script-craft.md §6):", file=sys.stderr)
                for f in blocks[:8]:
                    print(f"  - line {f.get('line', '?')}: {f.get('match', '')!r} — {f.get('why', '')}",
                          file=sys.stderr)
                print("  Fix them, or record the client's written approval and re-run with "
                      "`--allow \"<the exact phrase>\"` per phrase — the allowed phrase and your "
                      "name go onto the video's record, which is what makes it a paper trail rather "
                      "than a flag.", file=sys.stderr)
                return 1
            # ⛔ PERSIST. Until now this ran, printed, and was forgotten — so "which shipped videos
            # contain this claim" had no mechanism at all. The findings, the phrases anyone allowed
            # and who allowed them go onto the record, and the approved script is copied into
            # script-archive/ so the recall query has a corpus to search.
            try:
                led = _ledger_module()
                cli = os.path.basename((job.fields.get("client") or "").strip()).replace(".md", "")
                jn = re.sub(r"[^A-Za-z0-9._-]+", "-",
                            (job.fields.get("job") or os.path.basename(job.path)).strip()).strip("-.")
                dest = led.archive_script(job.path, ap, cli, jn or os.path.basename(job.path))
                rec = led.derive(job.path, led.load(job.path))
                led.record_claims(job.path, rec, {
                    "artifact": rel, "sha256": sha256_file(ap), "category": cat,
                    "disclosure": (found.get("disclosure") or {}).get(ap, "")
                                  if isinstance(found.get("disclosure"), dict) else "",
                    "findings": rows, "allowed": list(getattr(a, "allow", None) or []),
                    "by": a.by, "archived_to": dest or ""})
                led.save(job.path, rec)
                if dest:
                    rp = os.path.relpath(dest, SKILL_ROOT)
                    print(f"  archived → {dest if rp.startswith('..') else rp} "
                          f"(the corpus `ledger.py find --claim` searches)")
                else:
                    print("  ⛔ WARNING: nothing was archived (the artifact read as empty) — this "
                          "script will NOT be found by a recall query.")
            except Exception as e:                            # noqa: BLE001
                print(f"  ⛔ WARNING: the claims record was NOT persisted ({e}). The approval "
                      f"stands, but this script is invisible to `ledger.py find` — repair it with "
                      f"`ledger.py sync {os.path.relpath(job.path)}` and re-approve, or the recall "
                      f"query will report a clean result it has not earned.")
        # ⛔ A BLOCKING IS APPROVED AS ITS MANIFEST (2026-10-23). The grey render steers a clip's camera
        # and positions as hard as a start frame steers its picture, so it is signed like one — but
        # what is signed is the manifest, because the manifest is what names every file of the build
        # (MP4, sheet, map, spec, prompt blocks) with its hash. A file changed after the build means
        # the human looked at something else.
        if is_block:
            sid = stage.split(":", 1)[1]
            probs = []
            if not ap.endswith(".blocking.manifest.json"):
                probs.append(f"{rel} is not a blocking manifest — approve the "
                             f"<SHOT>.blocking.manifest.json that `blocking.py build` wrote")
            else:
                try:
                    man = json.load(open(ap, encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as e:
                    man = None
                    probs.append(f"the manifest is not readable JSON ({e})")
                if man is not None:
                    if str(man.get("shot") or "") != sid:
                        probs.append(f"the manifest is for shot {man.get('shot')!r}, not {sid!r}")
                    files = man.get("files") or {}
                    if "mp4" not in files:
                        probs.append("the manifest lists no mp4 — there is no reference video to approve")
                    base_dir = os.path.dirname(ap)
                    for k, v in files.items():
                        fp = os.path.normpath(os.path.join(base_dir, str(v.get("path", ""))))
                        if not os.path.isfile(fp):
                            probs.append(f"{k}: {v.get('path')} is missing")
                        elif sha256_file(fp) != v.get("sha256"):
                            probs.append(f"{k}: {v.get('path')} changed after the build")
            if probs:
                print(f"REFUSED: `{stage}` —\n  - " + "\n  - ".join(probs) +
                      "\n  Rebuild with `blocking.py build`, look at the sheet again, then approve the new "
                      "manifest (references/blocking.md §7).", file=sys.stderr)
                return 1
            if not a.media_id:
                print(f"  note: no --media-id — re-approve {stage} with the uploaded MP4's media id before "
                      f"the clip runs; the gate binds the reference to it.")
        # ⛔ THE WORLD IS APPROVED AS ITS CARD (2026-10-27, lab-00020; the author: "how the plugin approached the
        # scenario"). An exterior's sky, sun, wind, depth, land, water and background life are decided once, in the
        # card, before any frame — and every frame and clip that names it is linted against these exact bytes.
        if is_world:
            loc = stage.split(":", 1)[1]
            import world as _WD  # noqa: E402  (stdlib-only)
            want = os.path.abspath(_WD.card_path(job.path, loc))
            wp, ww = _WD.check_card(job.path, loc) if ap == want else (
                [f"{rel} is not the card for {loc} — approve {os.path.relpath(want, job.path)}"], [])
            for w_ in ww:
                print(f"  NOTE (world) {w_}", file=sys.stderr)
            if wp:
                print(f"REFUSED: `{stage}` — the world card does not hold (world.py check; references/world-design.md "
                      f"§3):\n  - " + "\n  - ".join(wp), file=sys.stderr)
                return 1
        # ⚡ GENJUTSU IS APPROVED AS ITS SPEC (v2.46.1): the file for THIS shot, passing a fresh lint now — its hash is
        # what the gate later compares, so a spec edited after the approval is refused at the call
        if is_gj:
            sid = stage.split(":", 1)[1]
            PLg = _lint_module()
            gprobs = []
            if os.path.basename(ap) != f"{sid}{PLg.GENJUTSU_SUFFIX}":
                gprobs.append(f"{rel} is not the Genjutsu spec for {sid} — approve 01-script/prompts/{sid}"
                              f"{PLg.GENJUTSU_SUFFIX}")
            else:
                try:
                    gr = PLg.lint(ap, job.path)
                except Exception as e:                    # a broken lint must not approve anything
                    gr = {"ok": False, "fails": [f"the lint crashed ({e})"], "sidecar": None}
                gsc = gr.get("sidecar") or {}
                if not gr.get("ok"):
                    gprobs += [f"lint: {x}" for x in (gr.get("fails") or [])[:6]]
                elif gsc.get("kind") != "genjutsu" or str(gsc.get("shot")) != sid:
                    gprobs.append(f"{rel} lints as {gsc.get('kind')} for shot {gsc.get('shot')!r}, not genjutsu:{sid}")
            if gprobs:
                print(f"REFUSED: `{stage}` —\n  - " + "\n  - ".join(gprobs) +
                      "\n  Fix the spec, run prompt_lint.py on it, and approve again.", file=sys.stderr)
                return 1
        artifact, sha = rel, sha256_file(ap)
    if is_frame and not a.media_id:
        print(f"REFUSED: {base}:<SHOT> needs --media-id — the Higgsfield job/media id that the clip "
              f"call will bind as its {'end' if base == 'endframe' else 'start'} frame. Approving a "
              f"still nobody can reference is theatre.",
              file=sys.stderr)
        return 1
    if not os.path.isfile(job.approvals_path):
        with open(job.approvals_path, "w", encoding="utf-8") as fh:
            fh.write("# Approvals\n\n| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n"
                     "|---|---|---|---|---|---|---|---|\n")
    # (v2.72.0) a row approved in the evaluation lane carries a stamp, APPENDED after the eight cells (an inserted
    # column would shift media_id for every production reader); the eval row's stamp freezes the checkpoint's key lines
    _stamp = ""
    if eval_lane:
        _stamp = "lane=eval" + (f" ck={job_tier.checkpoint_key_sha(parse_kv(read(job.checkpoint)))}" if is_eval else "")
    with open(job.approvals_path, "a", encoding="utf-8") as fh:
        fh.write(f"| {now()} | {cell(stage)} | {cell(a.by)} | {cell(quote)} | {cell(artifact)} | "
                 f"{sha[:16] if sha else ''} | {cell(a.media_id)} | "
                 f"{'transcript' if verified == 'verified' else 'UNVERIFIED hookless'} |" + (f" {_stamp} |" if _stamp else "") + "\n")
    job.log("approve", {"stage": stage, "by": a.by, "artifact": artifact, "verified": verified})
    if verified == "verified":
        note_verified_home(job)
    ledger_sync(job.path)
    print(f"APPROVED {stage} by {a.by}" + (f" · {artifact} sha {sha[:12]}" if artifact else "")
          + (f" · media {a.media_id}" if a.media_id else "")
          + (" · quote found in the session transcript" if verified == "verified" else
             " · quote UNVERIFIED (no session transcript recorded — the hook writes one at SessionStart)"))
    return 0


def _approve_family(job, a, stage: str) -> int:
    """`approve family:<FAMILY>` — the insert lane's frame gate (house decision 2026-10-25, the direct-response trial
    proposal's P7, "Family approval"). ONE contact sheet, looked at once, signs the start frames of a
    family's members — and writes an ordinary `frame:<SHOT>` row per member with that member's own
    still, sha and media id, so every clip is still bound to its own approved picture and every
    check downstream of the frame gate runs unchanged. What it saves is the human's time, never a
    check."""
    PL = _lint_module()
    fam = stage.split(":", 1)[1]
    fpath = os.path.join(job.prompts, f"{fam}{PL.FAMILY_SUFFIX}")
    probs = []
    if not os.path.isfile(fpath):
        print(f"REFUSED: `{stage}` — no {os.path.relpath(fpath, job.path)}. Write the family, lint it "
              f"(`prompt_lint.py <it>` writes and lints every member), then approve", file=sys.stderr)
        return 1
    chk = PL.lint_family(fpath, job.path, write=False)
    if not chk["ok"]:
        probs += chk["fails"]
    members = PL.family_members(fpath)
    if len(members) > PL.FAMILY_MAX:
        probs.append(f"{len(members)} members — one family approval covers at most {PL.FAMILY_MAX}")
    fam_sha = sha256_file(fpath)
    scs = {s_.get("shot"): s_ for s_ in job.sidecars(relint=True) if s_.get("family") == fam}
    for sh, _sf in members:
        sc = scs.get(sh)
        if not sc:
            probs.append(f"{sh}: no linted member prompt from this family — run prompt_lint.py on the family")
        elif sc.get("_forged") or sc.get("_stale"):
            probs.append(f"{sh}: its member prompt does not match a fresh lint — run prompt_lint.py on the family")
    # the ids: SHOT=media_id, every one a member, each start still on disk
    ids = {}
    for part in [x.strip() for x in (getattr(a, "media_ids", "") or "").split(",") if x.strip()]:
        if "=" not in part:
            probs.append(f"--media-ids item {part!r} is not SHOT=media_id")
            continue
        k, v = (x.strip() for x in part.split("=", 1))
        ids[k] = v
    if not ids:
        probs.append("--media-ids is required: `S12a=<id>,S12b=<id>` for each member the sheet approves "
                     "(members left out are not approved)")
    known = {sh for sh, _ in members}
    for k in ids:
        if k not in known:
            probs.append(f"{k} is not a member of family {fam} ({', '.join(sorted(known))})")
        elif not ids[k]:
            probs.append(f"{k}= has no media id")
    stills = {}
    for sh, sf in members:
        if sh not in ids:
            continue
        sp = os.path.join(job.path, sf) if sf and not os.path.isabs(sf) else sf
        if not sf or not os.path.isfile(sp):
            probs.append(f"{sh}: its start frame {sf or '(none)'} is not on disk")
        else:
            stills[sh] = (os.path.relpath(sp, job.path), sha256_file(sp))
    if not a.artifact:
        probs.append("--artifact is required: the contact sheet the human looked at")
        sheet_rel, sheet_sha = "", ""
    else:
        ap_ = os.path.abspath(a.artifact if os.path.isabs(a.artifact) else os.path.join(job.path, a.artifact))
        sheet_rel = os.path.relpath(ap_, job.path)
        sheet_sha = sha256_file(ap_) if os.path.isfile(ap_) else ""
        if not os.path.isfile(ap_):
            probs.append(f"the contact sheet {a.artifact} is not on disk")
        elif sheet_rel.startswith(".."):
            probs.append("the contact sheet is outside the job folder")
        elif not ap_.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".pdf")):
            probs.append(f"{a.artifact} is not an image — the family is approved on a contact sheet "
                         f"(contact_sheet.py over the members' start frames)")
    quote = (a.quote or "").strip()
    if len(quote.split()) < 2:
        probs.append("--quote must be the approver's reply verbatim (two words or more)")
    verified = quote_in_transcript(quote) if quote else "not-found"
    if by_refusal(job, a.by):                          # (3.1) --by names the Approver
        probs.append(by_refusal(job, a.by))
    if verified == "not-found":
        probs.append("that quote appears in no human turn of the current session transcript")
    elif verified != "verified" and quote_refusal(quote, job):         # (3.1) refused unless the studio is hookless
        probs.append(quote_refusal(quote, job))
    if probs:
        print(f"REFUSED: `{stage}` —\n  - " + "\n  - ".join(probs), file=sys.stderr)
        return 1
    if not os.path.isfile(job.approvals_path):
        with open(job.approvals_path, "w", encoding="utf-8") as fh:
            fh.write("# Approvals\n\n| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n"
                     "|---|---|---|---|---|---|---|---|\n")
    ver = "transcript" if verified == "verified" else "UNVERIFIED hookless"
    if verified == "verified":
        note_verified_home(job)
    ts = now()
    with open(job.approvals_path, "a", encoding="utf-8") as fh:
        fh.write(f"| {ts} | {cell(stage)} | {cell(a.by)} | {cell(quote)} | {cell(sheet_rel)} | "
                 f"{sheet_sha[:16]} | {cell(str(len(stills)) + ' frames · family ' + fam_sha[:12])} | {ver} |\n")
        for sh in sorted(stills):
            rel, sha = stills[sh]
            fh.write(f"| {ts} | frame:{cell(sh)} | {cell(a.by)} | {cell(quote + ' [family:' + fam + ']')} | "
                     f"{cell(rel)} | {sha[:16]} | {cell(ids[sh])} | {ver} |\n")
    job.log("approve", {"stage": stage, "by": a.by, "artifact": sheet_rel, "verified": verified,
                        "members": sorted(stills)})
    ledger_sync(job.path)
    print(f"APPROVED {stage} by {a.by} on {sheet_rel} — {len(stills)} start frame(s): "
          + ", ".join(f"{sh}={ids[sh]}" for sh in sorted(stills))
          + ("" if len(stills) == len(members) else
             f" · not approved: {', '.join(sorted(known - set(stills)))}"))
    return 0


def audio_preflight_stop(sc: dict, audio_approved: bool, guide_on: bool, aud: dict | None = None) -> str | None:
    """(v2.70.0, Wave 5 A7) The one case preflight must stop instead of writing the sound switch off: the prompt file asks
    for `generate_audio: true`, `audio` is not approved, and the clip speaks or the job is on `guide-audio`. Writing it
    off made the gate refuse the mismatch with the file, and sending it on is refused by the voice gate — a deadlock
    whose message named neither. Every other case keeps today's behaviour."""
    lin = sc.get("generate_audio")
    wants = lin is not None and str(lin).strip().lower() in ("true", "1", "yes", "on")
    if not wants or audio_approved or not (guide_on or speaks(sc)):
        return None
    if aud is not None and not (aud.get("param") and aud.get("default_on")):
        return None        # no off switch (MiniMax H3, Gemini, Kling 4.0): preflight never rewrote it, so no deadlock (Grok)
    return (f"{sc.get('_file')} asks for `generate_audio: true` and "
            f"{'the clip speaks' if speaks(sc) else 'the job is on `guide-audio`'}, but `audio` is not approved. Approve "
            f"`audio` first and say whose voice it is, or set `generate_audio: false` in the prompt file and re-lint it")


def continuity_units(job, sc: dict) -> list:
    """(build review 2, Grok) Every unit a continuity report for this clip may be filed under: the scene the prompt
    names (`scene:` in its front matter: a scene-form clip, whose shot id is not the scene's), the sidecar's own
    `scene`, the shot id, and its `S<n>` prefix."""
    out = []
    shot = str(sc.get("shot") or "")
    fm_scene = None
    try:
        src = os.path.join(job.prompts, sc.get("_file") or "")
        if sc.get("_file") and os.path.isfile(src):
            head = read(src).split("\n---", 2)[0] if read(src).startswith("---") else ""
            m = re.search(r"^scene:\s*['\"]?([A-Za-z0-9_.-]+)", head, re.M)
            fm_scene = m.group(1) if m else None
    except OSError:
        pass
    for u in (fm_scene, sc.get("scene"), shot, (re.match(r"^(S\d+)", shot) or [None, None])[1]):
        if u and str(u) not in out:
            out.append(str(u))
    return out


def continuity_fail(job, sc: dict) -> tuple[str | None, str | None]:
    """(unit, report) of the first FAILED continuity report among this clip's units, else (None, None)."""
    for u in continuity_units(job, sc):
        v, rep = continuity_verdict(job.path, u)
        if v == "FAIL":
            return u, rep
    return None, None


def continuity_verdict(job_path: str, scene: str) -> tuple[str | None, str | None]:
    """(3.1) The newest cine-scene-continuity report for a scene: (verdict, path), or (None, None) when there is none."""
    import fanout as _fo
    best = None
    for p in glob.glob(os.path.join(job_path, "09-qa", "fanout", "*", "*.md")):
        h, _prob = _fo.read_header(p)
        if h and h.get("agent") == "cine-scene-continuity" and str(h.get("unit")) == scene:
            m = os.path.getmtime(p)
            if best is None or m > best[0]:
                best = (m, str(h.get("verdict") or "").upper(), p)
    return (best[1], best[2]) if best else (None, None)


def cmd_preflight(a) -> int:
    job, why = active_job()
    if not job:
        print(f"no active job ({why}) — `gate.py open <job-dir>`", file=sys.stderr); return 1
    cp_problems = job.validate()
    want = a.kind
    _env0 = ENVELOPE_RE.search((job.fields or {}).get("budget") or "")
    if _env0 and float(_env0.group(1)) == 0:
        # (build review 2, Grok) the same stop as the hook: a concept-only job's preflight never says "would pass"
        print(f"REFUSED: job {job.fields.get('job')} has a budget envelope of 0 cr (concept only), so nothing spends. "
              f"Price the job and set the checkpoint's `Budget:` envelope with the client's OK first (START-HERE.md, "
              f"From a concept to the first paid picture)", file=sys.stderr)
        return 1
    scs = job.sidecars(relint=True)
    sc = next((s for s in scs if s.get("shot") == a.shot and s.get("kind") == want), None)
    if not sc:
        print(f"REFUSED: no linted {want} prompt for shot {a.shot} — "
              f"`prompt_lint.py 01-script/prompts/{a.shot}.{want}.prompt.md`", file=sys.stderr)
        return 1
    if want == "clip":                       # (3.1) a scene whose continuity check FAILED is fixed before any clip
        try:
            _fu, _frep = continuity_fail(job, sc)
            _units = continuity_units(job, sc)
            _scene = _fu or (_units[0] if _units else str(a.shot))
            _v, _rep = ("FAIL", _frep) if _fu else continuity_verdict(job.path, _scene)
        except Exception as e:               # noqa: BLE001 — a check that cannot run refuses
            print(f"REFUSED: the scene continuity check could not be read ({type(e).__name__})", file=sys.stderr)
            return 1
        if _v == "FAIL":
            print(f"REFUSED: scene {_scene}'s continuity check FAILED ({os.path.relpath(_rep, job.path)}) — fix the "
                  f"shots against the scene's sheets and run the check again before paying for a clip", file=sys.stderr)
            return 1
        if _v is None:
            print(f"  note: no continuity check for scene {_scene} yet (advisory: cine-scene-continuity via fanout.py)",
                  file=sys.stderr)
    prompt = sc.get("prompt") or ""          # the exact text the lint hashed — never rebuilt here
    preset = formats().get(job.fields.get("_preset") or "", {})
    params = {"model": sc["model"], "prompt": prompt}
    kind = "image" if want in ("frame", "edit") else "video"
    if want == "genjutsu":
        # the spec IS the call (v2.46.1): the one source video, the references, the resolution as the model spells it
        row = _lint_module().genjutsu_models().get(sc["model"]) or {}
        res = next((o for o in (row.get("resolutions") or []) if o.lower() == str(sc.get("resolution") or "").lower()),
                   sc.get("resolution"))
        params = {"model": sc["model"], "resolution": res,
                  "medias": [{"role": "video_references", "value": sc.get("source_video")}] +
                            [{"role": "image_references", "value": str(r["value"]).strip()}
                             for r in (sc.get("refs") or []) if isinstance(r, dict) and r.get("value")]}
        if prompt:
            params["prompt"] = prompt
        if sc.get("free_gens") == "prefer":
            params["use_free_gens"] = True
    elif want == "clip":
        d = sc.get("duration")
        params["duration"] = int(d) if d is not None and float(d).is_integer() else d
        params["aspect_ratio"] = preset.get("aspect") or sc.get("aspect")
        # The API's role names, never the skill's old ones (assets/higgsfield-rates.json →
        # media_roles). A lone `image` only ever worked because the server coerced it.
        PL = _lint_module()
        linted_refs = [r for r in (sc.get("refs") or []) if isinstance(r, dict) and r.get("value")]
        shape = PL.call_shape(sc["model"], bool(linted_refs), bool(sc.get("end_frame")))
        medias = []
        fr = job.approved(f"frame:{a.shot}")
        mid = (fr or {}).get("media_id") or sc.get("start_frame_media")
        if mid and shape["start_role"]:
            medias.append({"role": shape["start_role"], "value": mid})
        emid = ""
        if sc.get("end_frame") and shape["end_role"]:
            emid = (job.approved(f"endframe:{a.shot}") or {}).get("media_id") or ""
            if emid:
                medias.append({"role": shape["end_role"], "value": emid})
        for r in linted_refs:
            if r["value"] not in (mid, emid):
                medias.append({"role": PL.canonical_role(r.get("role", "image")), "value": r["value"]})
        # the params the call used to have to add by hand (episode 2026-09-19): the mode the shape
        # needs, the resolution as the MODEL spells it, and the audio switch when audio is unapproved
        if shape["mode"]:
            params["mode"] = shape["mode"]
        if sc.get("gen_mode") == "video_extension":
            # the source take is the start: only the linted video reference rides along
            params["mode"] = "video_extension"
            params["extension_mode"] = sc.get("extension_mode")
            medias = [{"role": "video_references", "value": r["value"]} for r in linted_refs
                      if PL.canonical_role(r.get("role", "")) == "video_references"]
        opts = shape.get("resolutions") or []
        want_res = str(sc.get("resolution") or "").lower()
        pick = next((o for o in opts if o.lower() == want_res), None)
        if pick:
            params["resolution"] = pick
        aud = shape["audio"]
        # (v2.49.0) the file decides the sound: kept native sound is the default, so the call sends the linted
        # `generate_audio`; it is silenced only when the job is on `guide-audio`, or the clip SPEAKS and `audio` is
        # not approved (the voice gate)
        _lin = sc.get("generate_audio")
        if aud.get("param") == "generate_audio" and _lin is not None and str(_lin).strip() != "":
            params["generate_audio"] = str(_lin).strip().lower() in ("true", "1", "yes", "on")
        _guide_on = switches.on(job.path, "guide-audio")
        _stop = audio_preflight_stop(sc, job.approved("audio"), _guide_on, aud)
        if _stop:
            print(f"REFUSED: {_stop}", file=sys.stderr)
            return 1
        if aud.get("default_on") and aud.get("param") and not job.approved("audio") and \
                (_guide_on or speaks(sc) or _lin is None):
            params[aud["param"]] = aud["off"]
        if medias:
            params["medias"] = medias
    else:
        params["aspect_ratio"] = preset.get("aspect") or sc.get("aspect")
        # ⛔ 2026-10-06: the file's `resolution:` was never sent for an image, so a 4k still came
        # back at the model's 2k default and the check below could not see it (it compares only a
        # resolution that IS sent). Image models carry no call contract here, so the declared
        # value goes out as written; a model that does not take it fails loudly at the server,
        # which beats a silent downgrade.
        if sc.get("resolution"):
            params["resolution"] = str(sc["resolution"]).lower()
        refs = [{"role": r.get("role", "image"), "value": r["value"]}
                for r in (sc.get("refs") or []) if r.get("value")]
        if want == "edit" and sc.get("edit_of_media"):
            # the picture being edited goes first — the prompt's "Image 1" (prompting-craft.md §11g)
            refs = [{"role": "image", "value": sc["edit_of_media"]}] + [r for r in refs if r["value"] != sc["edit_of_media"]]
        if refs:
            params["medias"] = refs
    if int(sc.get("variants") or 1) > 1:
        params["count"] = int(sc["variants"])
    probs, _ = check_request(job, kind, params, job.policy or "", scs)
    if cp_problems:
        probs.insert(0, "checkpoint no longer validates — `gate.py open` again")
    out = {"tool": f"mcp__Higgsfield__generate_{kind}", "params": params,
           "would_pass": not probs, "problems": probs,
           # a Genjutsu probe goes without the free switch, so it shows the credit price a refused free request would cost
           "cost_probe": {**{k: v for k, v in params.items() if not (want == "genjutsu" and k == "use_free_gens")},
                          "get_cost": True},
           "negative_prompt": "" if sc.get("negative_channel") == "none" else (sc.get("negative") or ""),
           "_negative_note": (f"{sc['model']} has no negative field: the [SUPPRESS] list is dropped, never sent "
                              f"(prompting-craft.md §11g)" if sc.get("negative_channel") == "none" else
                              "pass `negative_prompt` ONLY if models_explore lists it for this model; "
                              "it is kept out of `prompt` on purpose (prompting-craft.md §5.2)")}
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False)); return 0 if not probs else 1
    print(f"PREFLIGHT {a.shot} {want} · {sc['model']} {sc.get('resolution') or ''} "
          f"{str(sc.get('duration') or '') + 's' if want == 'clip' else ''}")
    if want == "genjutsu":
        print(f"  {sc.get('genjutsu_name')} ({sc.get('tier')}) · free generations stated by the owner (2026-11-03): Lite 10, "
              f"full 1 — " + ("this call asks for one; a refused free request goes back to the owner, never onto credits"
                              if params.get("use_free_gens") else "the spec says `free_gens: no`: this call spends credits"))
    print(f"  tool:   {out['tool']}")
    print("  params: " + json.dumps(params, ensure_ascii=False))
    if sc.get("negative") and sc.get("negative_channel") == "none":
        print(f"  negative_prompt: not sent — {sc['model']} has no negative field (the [SUPPRESS] list is dropped)")
    elif sc.get("negative"):
        print(f"  negative_prompt (only if the model exposes it): {sc['negative']}")
    if probs:
        print("  ⛔ would be REFUSED:")
        for p in probs:
            print(f"    - {p}")
        return 1
    print("  gate: would PASS" + (" — and ASK: a Genjutsu take always asks (v2.46.1)" if want == "genjutsu" else
                                  " (per-stage-human → the UI will ask)" if job.policy == "per-stage-human" else ""))
    print("  tip: run the same params with \"get_cost\": true first — a probe spends nothing.")
    return 0


def _record_transcript(data: dict) -> None:
    global HOOK_SESSION
    sid = data.get("session_id")
    if isinstance(sid, str) and SESSION_ID_RE.match(sid):
        HOOK_SESSION = sid
        upd = {"last": time.time()}
        if data.get("transcript_path"):
            upd["transcript"] = str(data["transcript_path"])
        save_session(sid, **upd)
    tp = data.get("transcript_path")
    if tp:
        try:
            os.makedirs(CINE_HOME, exist_ok=True)
            with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as fh:
                fh.write(str(tp))
        except OSError:
            pass


SEEN_FILE = "seen-connectors.json"       # (3.0.0) local only: uuids the gate asked about, with their tool names


def note_seen_connector(uuid: str, tool: str) -> None:
    """Remember an unnamed connector the gate asked about (uuid → tool names, last seen), so doctor and
    `gate.py connectors --seen` can show which one to name. Never blocks the hook: any error is ignored."""
    try:
        p = os.path.join(CINE_HOME, SEEN_FILE)
        try:
            data = json.load(open(p, encoding="utf-8"))
            data = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            data = {}
        rec = data.get(uuid) if isinstance(data.get(uuid), dict) else {}
        name = tool.split("__", 2)[-1]
        tools = sorted({*(t for t in rec.get("tools", []) if isinstance(t, str)), name})[:20]
        data[uuid] = {"tools": tools, "last": time.strftime("%Y-%m-%dT%H:%M:%S")}
        os.makedirs(CINE_HOME, exist_ok=True)
        tmp = p + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
        os.replace(tmp, p)
    except Exception:                       # noqa: BLE001 — a note must never change the gate's answer
        pass


def seen_connectors() -> dict:
    try:
        d = json.load(open(os.path.join(CINE_HOME, SEEN_FILE), encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def cmd_connectors(a) -> int:
    """Name which claude.ai connector uuid is your Higgsfield account and which are other services. Stored in
    $CINE_HOME/connectors.json; prints what is set. Never prints anything else about the account."""
    p = os.path.join(CINE_HOME, CONNECTORS_FILE)
    try:
        data = json.load(open(p, encoding="utf-8"))
        data = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        data = {}
    changed = False
    current_hf = {str(x).strip().lower() for x in (data.get("higgsfield") or [])}
    for kind, ids in (("higgsfield", a.higgsfield or []), ("other", a.other or [])):
        for u in ids:
            u = u.strip().lower()
            if not re.fullmatch(UUID_SRC, u):
                print(f"REFUSED: {u!r} is not a connector uuid (8-4-4-4-12 hex)", file=sys.stderr)
                return 2
            if kind == "other" and u in current_hf:
                # (v2.61.0) taking the gate off a Higgsfield connector is the owner's call, in their own words
                q = (getattr(a, "quote", None) or "").strip()
                if len(q.split()) < 2 or quote_in_transcript(q) != "verified":
                    print(f"REFUSED: {u} is named as your Higgsfield connector. Moving it to --other takes the gate "
                          f"off it, so it needs the owner's words: --quote \"<what they typed>\" (checked against "
                          f"this session's transcript).", file=sys.stderr)
                    return 1
            for k in ("higgsfield", "other"):
                data[k] = [x for x in (data.get(k) or []) if x != u]
            data.setdefault(kind, []).append(u)
            changed = True
    if changed:                       # (v2.59.2) written whole to a temp file, then renamed: never a torn file
        os.makedirs(CINE_HOME, exist_ok=True)
        tmp = p + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"higgsfield": sorted(data.get("higgsfield") or []), "other": sorted(data.get("other") or [])},
                      fh, indent=1)
        os.replace(tmp, p)
    s = connector_settings()
    print(f"connector settings ({p}{' + env' if os.environ.get('CINE_HIGGSFIELD_CONNECTORS') or os.environ.get('CINE_OTHER_CONNECTORS') else ''}):")
    print(f"  higgsfield: {', '.join(sorted(s['higgsfield'])) or 'none — every Higgsfield call through a claude.ai connector asks'}")
    print(f"  other:      {', '.join(sorted(s['other'])) or 'none'}")
    if getattr(a, "seen", False):
        named = s["higgsfield"] | s["other"]
        seen = {u: r for u, r in seen_connectors().items() if u not in named and isinstance(r, dict)}
        print(f"  seen, not named ({os.path.join(CINE_HOME, SEEN_FILE)}):" + ("" if seen else " none"))
        for u, r in sorted(seen.items()):
            print(f"    {u}  tools: {', '.join(r.get('tools', []))}  last: {r.get('last', '?')}")
    return 0


def cmd_hook(_a) -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            raise ValueError("hook input is not an object")
        _record_transcript(data)
        tool = data.get("tool_name")
        if not tool:
            d = {"decision": "deny", "reason": "gate.py hook received no tool_name — refusing rather "
                                                "than guessing (a spend gate fails closed)", "context": ""}
        else:
            _ti = data.get("tool_input") or {}
            _b = budget_asks(str(tool), _ti)                                  # (wave 2c) pure: envelope + ceiling
            # (build review 1) no session_id means the call will be denied below: commit nothing for it either
            _will_deny = bool(_b.get("deny")) or not data.get("session_id")
            d = decide(str(tool), _ti, commit=not _b["fires"] and not _will_deny, commit_previz=not _will_deny)
            d = budget_merge(d, _b, str(tool))                                # never touches allow or deny
            if not data.get("session_id") and d["decision"] != "allow":       # (3.1) reads pass; nothing else
                d = {"decision": "deny", "reason": f"{tool}: the hook payload carries no session_id, so the gate cannot "
                     f"tell which session's job and approvals apply — refusing (a spend gate fails closed)",
                     "context": ""}
    except Exception:  # fail CLOSED — see the docstring
        d = {"decision": "deny",
             "reason": "gate.py crashed while checking this call; a spend gate fails closed.\n" +
                       traceback.format_exc()[-3000:],
             "context": ""}
    if d["decision"] == "allow":
        # not a tool the gate has an opinion on: answer `{}` (no decision). (v2.59.2) Never SILENCE: the hook command
        # refuses an empty answer, because a gate.py cut off at a line boundary still parses, defines its functions,
        # never reaches main() and exits 0 having said nothing — which Claude Code reads as "no objection"
        print("{}")
        return 0
    hso = {"hookEventName": "PreToolUse"}
    if d["decision"] in ("deny", "ask", "preapproved"):
        # a call covered by a recorded allowance is pre-approved: the human said yes once, in chat
        hso["permissionDecision"] = "allow" if d["decision"] == "preapproved" else d["decision"]
        hso["permissionDecisionReason"] = d.get("reason") or ""
    # "pass": no permissionDecision — the operator's normal permission flow still runs
    if d.get("context"):
        hso["additionalContext"] = d["context"]
    out = {"hookSpecificOutput": hso}
    if d.get("context"):
        out["additionalContext"] = d["context"]
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_session(_a) -> int:
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
        if isinstance(data, dict):
            _record_transcript(data)
    except (json.JSONDecodeError, OSError):
        pass
    job, why = active_job()
    if not job:
        msg = (f"cinematographly gate: no production job is open ({why}). Higgsfield spend calls are "
               f"DENIED until `python3 scripts/gate.py open <job-dir>` validates a checkpoint.")
    # ⚡ a supplement ad job (2026-10-28): the plugin was reinstalled under the session (`cinematography` → `cinematography~g2`)
    # and every command written from memory pointed at a folder that was gone. The live path is said once, here, at the
    # start of every session: run the scripts from it, never from a path remembered from an earlier session.
    else:
        probs = job.validate()
        aps = ", ".join(r["stage"] for r in job.approvals()) or "none"
        msg = (f"cinematographly gate: job {job.fields.get('job')} is OPEN at {job.path} · policy "
               f"{job.policy} · approvals: {aps}" +
               # (v2.48.0, project switches) the house rules this job lifts, by id — `status` has the reasons
               (f" · project switches: {', '.join(job.switches)}" if job.switches else "") +
               (f" · ⛔ checkpoint problems: {len(probs)} (run gate.py status)" if probs else "") +
               ". Build every generate call with `gate.py preflight <SHOT> --kind frame|clip`.")
    msg += (f" Scripts this session: {HERE} (run them from here; a remembered path may be an old install — "
            f"`gate.py where`).")
    if HOOK_SESSION:                                   # (3.1) the id a shell call names when two sessions are live
        msg += f" This session's id: {HOOK_SESSION} (pass `--session {HOOK_SESSION}` if another session is open too)."
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg},
                      "additionalContext": msg}, ensure_ascii=False))
    return 0


# ---- MEDIA THAT NEVER PASSED THE GATE: a ledger row, and a reconcile by hash ---------------------
# (2026-10-25, house decision on the direct-response trial proposal's P8, "log-external + reconcile".) The free
# generations on higgsfield.ai exist only in the browser and only for a human (automation is
# prohibited there), so a clip made that way never crosses this gate and used to leave no trace in the
# job. Every generated file in a job is now either PULLED (pull_finals.py writes .gate/pulled.jsonl
# with its hash) or LOGGED here; `reconcile --files` lists whatever is neither.
MEDIA_LANES = ("02-startframes", "03-clips", "04-broll", "05-voice", job_tier.EVAL_DIR)
MEDIA_SKIP_DIRS = {"_review", "_blocking", "_previz", "_to_delete", ".gate"}
MEDIA_EXT = (".mp4", ".mov", ".mxf", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a",
             ".aac", ".flac")
EXTERNAL_SOURCES = ("website", "recording", "derived", "other")


def _jsonl(path: str) -> list:
    rows = []
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8", errors="ignore"):
            try:
                r = json.loads(line)
                if isinstance(r, dict):
                    rows.append(r)
            except json.JSONDecodeError:
                continue
    return rows


def media_trace(job, cache: "HashCache | None" = None) -> dict:
    """{traced, untraced, changed}: every media file in the generated lanes against the pull and
    external logs, by sha256. With a cache (status only), an unchanged file is not re-read."""
    sha256_file = cache.sha if cache is not None else globals()["sha256_file"]
    pulled = _jsonl(os.path.join(job.gate_dir, "pulled.jsonl"))
    ext = _jsonl(os.path.join(job.gate_dir, "external.jsonl"))
    known = {r.get("sha256"): r for r in pulled + ext if r.get("sha256")}
    traced, untraced = [], []
    for lane in MEDIA_LANES:
        top = os.path.join(job.path, lane)
        for dp, dns, fns in os.walk(top):
            dns[:] = sorted(d for d in dns if d not in MEDIA_SKIP_DIRS)
            for fn in sorted(fns):
                if not fn.lower().endswith(MEDIA_EXT):
                    continue
                fp = os.path.join(dp, fn)
                row = {"path": os.path.relpath(fp, job.path), "sha256": sha256_file(fp)}
                (traced if row["sha256"] in known else untraced).append(row)
    # a logged file whose bytes changed since: the row now describes a different picture
    changed = []
    for r in ext:
        fp = os.path.join(job.path, str(r.get("path") or ""))
        if r.get("path") and os.path.isfile(fp) and sha256_file(fp) != r.get("sha256"):
            changed.append(r.get("path"))
    return {"traced": traced, "untraced": untraced, "changed": changed}


def cmd_release_take(a) -> int:
    """(v2.72.0) Release a lane reservation whose call never ran: the person declined the ask or the permission prompt.
    Refused when a newer submission confirms it, or when it is younger than EVAL_INFLIGHT_S (it may still be running)."""
    job, why = active_job()
    if not job:
        print(f"no active job ({why})", file=sys.stderr); return 1
    job.validate()
    if not job.is_eval_lane():
        print("REFUSED: release-take is for the evaluation lane's reservations", file=sys.stderr); return 1
    if len((a.why or "").split()) < 3:
        print("REFUSED: --why needs a sentence: what happened to the call (\"declined at the permission prompt\")",
              file=sys.stderr); return 1
    # (v2.72.0, build review 3, Sonnet) a release frees a take, so it needs the person's words, checked like an allowance
    if not (a.by or "").strip() or len((a.quote or "").split()) < 2:
        print("REFUSED: --by and --quote (the person's words that they declined the call) are required", file=sys.stderr)
        return 1
    _v = quote_in_transcript(a.quote)
    if _v != "verified":
        print("REFUSED: the quote is not in a human turn of this session's transcript" +
              (" (no transcript is recorded)" if _v == "no-transcript" else "") +
              " — a release is never made from unchecked words", file=sys.stderr)
        return 1
    with eval_lock(job) as _lk:
        if not _lk:
            print("REFUSED: the evaluation ledger is busy; try again", file=sys.stderr); return 1
        return _release_take_locked(job, a)


def _release_take_locked(job, a) -> int:
    live = _eval_reservations(job)
    cand = [r for r in live if (not a.id or r.get("id") == a.id)]
    if not cand:
        print(f"REFUSED: no unreleased reservation{' ' + a.id if a.id else ''}", file=sys.stderr); return 1
    r = cand[-1]
    if _eval_confirmed(job, r):
        print(f"REFUSED: {r['id']} is confirmed — a submission after it carries its request hash, so the call ran and "
              f"its take is spent", file=sys.stderr); return 1
    age = time.time() - float(r.get("epoch") or 0)
    if age < EVAL_INFLIGHT_S:
        print(f"REFUSED: {r['id']} is {age:.0f} s old — its call may still be running; wait {EVAL_INFLIGHT_S} s and check "
              f"the platform (show_generations) first", file=sys.stderr); return 1
    if not eval_release(job, r["id"], f"{a.why} — {a.by}: \"{(a.quote or '')[:120]}\"", by=a.by):
        print("REFUSED: the evaluation ledger cannot be written", file=sys.stderr); return 1
    job.log("eval-release", {"id": r["id"], "why": a.why})
    print(f"RELEASED {r['id']} ({', '.join(f'{k}+{v}' for k, v in (r.get('units') or {}).items())}, "
          f"{float(r.get('credits') or 0):g} cr) — {a.why}")
    return 0


def cmd_log_external(a) -> int:
    job, why = active_job()
    if not job:
        print(f"no active job ({why}) — `gate.py open <job-dir>`", file=sys.stderr); return 1
    job.validate()
    if job.is_eval_lane() or job.ever_evaluated():
        print("REFUSED: log-external in the evaluation lane (v2.72.0) — every take of an evaluation is generated "
              "through the gate, so the plan can count it. Media made outside the gate answers a different question.",
              file=sys.stderr)
        return 1
    fp = a.file if os.path.isabs(a.file) else os.path.join(job.path, a.file)
    fp = os.path.abspath(fp)
    rel = os.path.relpath(fp, job.path)
    probs = []
    if not os.path.isfile(fp):
        probs.append(f"{a.file} not found")
    elif rel.startswith(".."):
        probs.append(f"{a.file} is outside the job folder — file it in its lane first")
    elif not fp.lower().endswith(MEDIA_EXT):
        probs.append(f"{a.file} is not a media file ({', '.join(MEDIA_EXT)})")
    evaluation = job.tier() == "evaluation"
    if evaluation and os.path.isfile(fp) and not job_tier.eval_marked(fp):
        probs.append(f"this is an evaluation job: file it under {job_tier.EVAL_DIR}/ with EVAL in the "
                     f"name ({job_tier.eval_name(os.path.basename(fp))}) before logging it")
    res = (a.res or "").lower()
    if a.source == "website":
        if not (a.model and a.res and a.seconds):
            probs.append("a website generation records --model, --res and --seconds")
        if not a.frame and not a.no_frame:
            probs.append("a website generation names the approved still it started from (--frame "
                         "<SHOT>), or says why it had none (--no-frame \"<reason>\")")
        try:
            px = _lint_module().res_px(res) if res else 0
        except Exception:                                     # noqa: BLE001
            px = 0
        # (v2.49.0) the video floor is 720p (one upscale on the final); stills keep 1080p; `floor-1080` restores it
        try:
            _is_video = (a.model or "") in (_lint_module().roster() or {})
        except Exception:                                     # noqa: BLE001
            _is_video = False
        _floor = 720 if (_is_video and not switches.on(job.path, "floor-1080")) else 1080
        if px and px < _floor and not evaluation:
            probs.append(f"{res} is under the {_floor}p floor and this is a production job — a free low-tier "
                         f"generation answers a question in an evaluation job (`Tier: evaluation`); it "
                         f"never becomes footage here")
    frame_row = None
    if a.frame:
        frame_row = job.approved(f"frame:{a.frame}")
        if not frame_row:
            probs.append(f"frame:{a.frame} is not approved — a generation from an unapproved still is "
                         f"an unapproved picture, wherever it was made")
    cr = _num(a.credits)
    if cr is None or cr < 0:
        probs.append(f"--credits {a.credits!r} is not a number of credits")
    if probs:
        print("REFUSED: log-external —\n  - " + "\n  - ".join(probs), file=sys.stderr)
        return 1
    sha = sha256_file(fp)
    if any(r.get("sha256") == sha for r in _jsonl(os.path.join(job.gate_dir, "external.jsonl"))):
        print(f"already logged: {rel} (sha {sha[:12]})"); return 0
    row = {"ts": now(), "path": rel, "sha256": sha, "source": a.source, "model": a.model or "",
           "resolution": res, "seconds": _num(a.seconds) if a.seconds else None, "credits": cr,
           "frame": a.frame or "", "frame_media_id": (frame_row or {}).get("media_id", ""),
           "no_frame": a.no_frame or "", "by": a.by, "note": a.note or "", "tier": job.tier()}
    os.makedirs(job.gate_dir, exist_ok=True)
    with open(os.path.join(job.gate_dir, "external.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    job.log("log-external", {k: row[k] for k in ("path", "sha256", "source", "credits", "by")})
    print(f"LOGGED {rel} · {a.source} · {a.model or '-'} {res or ''} {a.seconds or ''}s · {cr:g} cr · "
          f"by {a.by}" + (f" · from frame:{a.frame} ({row['frame_media_id']})" if a.frame else ""))
    print("  ⚠ a log records what a person says they did; it cannot prove it. The hash is what it CAN "
          "prove: the file described here is this file, unchanged.")
    return 0


def cmd_reconcile_files(a) -> int:
    job = Job(a.job_dir) if a.job_dir else active_job()[0]
    if not job:
        print("no job — `gate.py open <job-dir>` or pass --job-dir", file=sys.stderr); return 2
    t = media_trace(job)
    n = len(t["traced"]) + len(t["untraced"])
    print(f"RECONCILE FILES · {n} media file(s) in the generated lanes · {len(t['traced'])} traced "
          f"(pulled or logged) · {len(t['untraced'])} untraced"
          + (f" · {len(t['changed'])} logged file(s) changed since" if t["changed"] else ""))
    for r in t["untraced"][:60]:
        print(f"  - {r['path']}  sha {r['sha256'][:12]} — pull it with pull_finals.py, or "
              f"`gate.py log-external {r['path']} --source website|recording|derived|other --by <name>`")
    for pth in t["changed"][:20]:
        print(f"  ⛔ {pth} changed after it was logged — the row describes a different file; log the new one")
    return 1 if (t["untraced"] or t["changed"]) else 0


def cmd_reconcile(a) -> int:
    if getattr(a, "files", False):
        return cmd_reconcile_files(a)
    if not a.transactions:
        print("error: give a transactions dump (show_generations JSON), or --files to reconcile the "
              "job's media by hash", file=sys.stderr)
        return 2
    try:
        data = load_json(a.transactions)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr); return 2
    items = data if isinstance(data, list) else data.get("transactions") or data.get("items") or []
    job = Job(a.job_dir) if a.job_dir else active_job()[0]
    hashes = {s.get("prompt_sha256"): s for s in (job.sidecars() if job else [])}
    unlinted, linted, spent_un = [], [], 0.0
    # ⛔ THE SERVED MODEL IS THE ONLY MODEL THERE IS (2026-09-17). A calibration run requested
    # `nano_banana_pro` and every job came back `nano_banana_2` — reported in a response field
    # nobody reads, so six images were attributed to a model that never ran them. Same class as the
    # silent reroute by a model router (2026-09-08), and the vendor's own workflows state the rule from their
    # side: never silently replace a locked model, never silently downgrade to fit a free tier.
    # The sidecar already records the model the prompt was linted for; the dump records what ran.
    # Comparing two numbers we already have costs nothing, and is the only place this can be caught.
    served_mismatch: list[tuple] = []
    for t in items:
        if not isinstance(t, dict):
            continue
        prompt = normalize_prompt(str(t.get("prompt") or (t.get("params") or {}).get("prompt") or ""))
        cost = _num(t.get("cost") or t.get("credits") or t.get("amount") or 0) or 0.0
        h = sha256_text(prompt) if prompt else None
        (linted if h in hashes else unlinted).append(t)
        if h not in hashes:
            spent_un += cost
        else:
            want = str((hashes[h] or {}).get("model") or "").strip()
            got = str(t.get("model") or (t.get("params") or {}).get("model") or "").strip()
            if want and got and want != got:
                served_mismatch.append((str(t.get("id") or t.get("job_id") or "?")[:14], want, got, cost))
    # ⛔ RECONCILE DID NOT KNOW ABOUT THE LANE THE GATE ITSELF OPENS (2026-09-17). `previz` is
    # AUTHORISED spend: capped, reasoned, counted, and deliberately NOT behind a linted prompt —
    # concept art exists to be looked at before the prompts are written. Reconcile matched on
    # prompt hashes only, so every previz image came back as "spent outside a linted prompt". That
    # is a manufactured finding, the exact class this skill refuses elsewhere (reporting "I cannot
    # tell" as "ungated"), and a reconcile that cries wolf on its own lane is a reconcile nobody
    # reads. Rows inside a recorded previz window are now counted as ACCOUNTED, capped at the
    # lane's own `used` counter so a window cannot absorb more than it authorised.
    pv = previz_state(job) if job else {}
    windows = []
    for h in (pv.get("history") or []):
        try:
            windows.append(dt.datetime.fromisoformat(str(h.get("ts"))).timestamp())
        except (ValueError, TypeError):
            pass
    pv_cap = int(pv.get("used") or 0)
    previz_rows, still_unlinted = [], []
    for t in unlinted:
        ts = _num(t.get("created_at") or t.get("createdAt") or t.get("ts") or 0) or 0.0
        if not ts:
            iso = str(t.get("created_at") or t.get("createdAt") or "")
            try:
                ts = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
            except ValueError:
                ts = 0.0
        near = ts and any(abs(ts - w) <= 120 for w in windows)
        (previz_rows if (near and len(previz_rows) < pv_cap) else still_unlinted).append(t)
    if previz_rows:
        spent_un -= sum((_num(t.get("cost") or t.get("credits") or t.get("amount") or 0) or 0.0)
                        for t in previz_rows)
        unlinted = still_unlinted
    bl = os.path.join(CINE_HOME, "bypass.log")
    byp = sum(1 for _ in open(bl, encoding="utf-8")) if os.path.isfile(bl) else 0
    # ⛔ "Spent outside a linted prompt" and "I cannot tell" are different answers, and reporting
    # the second as the first is a manufactured finding — the exact failure this skill refuses
    # elsewhere. Run 2026-09-07 on a real `transactions` dump: 25 items, 0 matched, "194 credits
    # ungated" — but that endpoint carries display_name, credits and a timestamp and NO PROMPT, so
    # nothing could ever have matched. `show_generations` carries `params.prompt`; feed that.
    with_prompt = sum(1 for x in items if isinstance(x, dict)
                      and (x.get("prompt") or (x.get("params") or {}).get("prompt")))
    if items and not with_prompt:
        print(f"RECONCILE · INCONCLUSIVE — {len(items)} item(s), none carrying a prompt.\n"
              f"  This input cannot be reconciled: matching works by hashing the prompt against the "
              f"linted `.ok` sidecars, and nothing here has one. The Higgsfield `transactions` "
              f"endpoint returns display_name + credits + timestamp only.\n"
              f"  Use a `show_generations` dump instead — it carries `params.prompt` — or join the "
              f"two by timestamp first. Total spend in this file: "
              f"{sum((_num(x.get('cost') or x.get('credits') or x.get('amount') or 0) or 0) for x in items if isinstance(x, dict)):g} credits, "
              f"gated status UNKNOWN."
              + (f"\n  {byp} CINE_GATE=off bypass(es) logged." if byp else ""))
        return 1
    print(f"RECONCILE · {len(items)} generation(s) · {len(linted)} behind a linted prompt · "
          + (f"{len(previz_rows)} inside the previz lane (cap {pv.get('budget', '?')}, "
             f"used {pv_cap}) · " if previz_rows else "")
          + f"{len(unlinted)} without one · {spent_un:g} credits ungated"
          + (f" · {byp} CINE_GATE=off bypass(es) logged" if byp else ""))
    for t in unlinted[:40]:
        print(f"  - {str(t.get('id') or t.get('job_id') or '?')[:14]}  {str(t.get('model') or '?'):<14} "
              f"{(_num(t.get('cost') or t.get('credits') or t.get('amount') or 0) or 0):>7g} cr  "
              f"{normalize_prompt(str(t.get('prompt') or ''))[:70]!r}")
    if served_mismatch:
        print(f"  ⛔ SERVED MODEL ≠ REQUESTED MODEL on {len(served_mismatch)} generation(s) — the "
              f"prompt was linted and priced for one model and another one ran it. Fix the roster "
              f"or the id; re-read anything this job concluded from those frames:")
        for gid, want, got, cost in served_mismatch[:20]:
            print(f"  - {gid}  asked {want} · served {got}  {cost:>7g} cr")
    return 1 if (unlinted or served_mismatch) else 0


def cmd_close(_a) -> int:
    job, _ = active_job()
    if job:
        job.log("close", {})
        ledger_sync(job.path)
        try:                                       # (3.1) the job-close scorecard, derived; never blocks a close
            import shot_manifest as _sm
            if os.path.exists(_sm.manifest_path(job.path)):
                _rows = json.load(open(_sm.manifest_path(job.path), encoding="utf-8")).get("rows") or []
                print(f"  scorecard → {_sm.write_scorecard(job.path, _sm.scorecard(job.path, _rows))}")
            else:
                print("  scorecard: none — the job has no shot manifest (`shot_manifest.py init` starts one)")
        except Exception as e:                     # noqa: BLE001 — never blocks a close, but is never silent
            print(f"  scorecard: NOT written ({type(e).__name__}: {e})", file=sys.stderr)
    _why = set_active(None)
    if _why:      # (build review 3, Sonnet) a close that cannot tell which session it closes says so; never "closed"
        print(f"REFUSED: `close` — {_why}", file=sys.stderr)
        return 1
    print("closed — no active job; generation is denied until the next `gate.py open`")
    return 0


# ----------------------------------------------------------------------------------------------

def _selftest_budget() -> None:
    """(wave 2c) The budget stop's predicates and the merge rule, in-process with the price, the job and the studio
    stubbed (the hook path itself is exercised end to end in test_gate.py)."""
    g = globals()
    keep = {k: g[k] for k in ("request_credits", "active_job", "_studio")}

    class FakeStudio:
        def __init__(self, c, credits=0.0, unreadable=0, prob=None):
            self.c, self.cr, self.un, self.prob = c, credits, unreadable, prob

        def ceiling_state(self):
            return self.c, self.prob

        def month_total(self):
            return {"month": "2026-11", "credits": self.cr, "unpriced": 0, "voice_unpriced": 0,
                    "unreadable": self.un, "events": 0}

        def month_line(self, mt, c):
            return f"studio month {mt['month']} (UTC) {mt['credits']:g} / {c:g} cr"
    img, aud = "mcp__Higgsfield__generate_image", "mcp__Higgsfield__generate_audio"
    try:
        g["active_job"] = lambda *a_, **k_: (None, "test")

        def ba(tool, prices, studio_):
            g["request_credits"] = lambda *a_, **k_: list(prices)
            g["_studio"] = lambda: studio_
            return budget_asks(tool, {})
        assert not ba(img, [10.0], FakeStudio(100, 80))["fires"], "80 + 10 under 100 passes"
        assert not ba(img, [20.0], FakeStudio(100, 80))["fires"], "80 + 20 == 100 passes (past it, not at it)"
        assert ba(img, [21.0], FakeStudio(100, 80))["fires"], "80 + 21 over 100 fires"
        assert ba(img, [None], FakeStudio(100, 10))["fires"], "an unpriced image fires whenever a ceiling is set"
        assert ba(img, [10.0, None], FakeStudio(100, 10))["fires"], "a mixed batch with one unpriced row fires"
        assert not ba(aud, [None], FakeStudio(100, 10))["fires"], "voice under the ceiling passes (no voice rate exists)"
        assert ba(aud, [None], FakeStudio(100, 100))["fires"], "voice with the month at the ceiling fires"
        assert ba(img, [1.0], FakeStudio(100, 0, unreadable=1))["fires"], "an unreadable spend record fires"
        assert ba(img, [1.0], FakeStudio(None, 0, prob="studio.json cannot be read"))["fires"], "a bad studio file fires"
        assert ba(img, [1.0], FakeStudio(None))["lines"] == [], "no ceiling, no envelope: nothing (3.0 behaviour)"
        assert ba(img, [], FakeStudio(1, 50))["lines"] == [], "get_cost probes only: nothing is spent"
        assert ba("mcp__Kling_AI__text_to_image", [None], FakeStudio(1, 50)) == {"fires": False, "lines": [], "why": [],
                                                                               "deny": None}, \
            "Kling is a separate account: no line, no stop"
        import tempfile as _tf2
        with _tf2.TemporaryDirectory() as _gd:
            _fj0 = type("J0", (), {"fields": {"job": "c-01", "budget": "envelope 0 cr (concept only) · estimate "
                                               "UNPRICED [unpriced]"}, "checkpoint": "/nope", "gate_dir": _gd})()
            g["active_job"] = lambda *a_, **k_: (_fj0, "")
            z = ba(img, [2.0], FakeStudio(None))
            assert z["fires"] and z["deny"] and "envelope of 0 cr" in z["deny"], ("(review) envelope 0 denies", z)
            _fj0.fields = {"job": "c-01", "budget": "envelope 10 cr · estimate 8 cr [estimated]"}
            assert not ba(img, [2.0], FakeStudio(None))["deny"], "a real envelope never denies"
            g["active_job"] = lambda *a_, **k_: (None, "test")
        with _tf2.TemporaryDirectory() as _cj:                # (build review 2) a scene-form clip's scene is its own
            _pd = os.path.join(_cj, "01-script", "prompts"); os.makedirs(_pd)
            open(os.path.join(_pd, "S4.clip.prompt.md"), "w").write("---\nshot: S4\nscene: S2\nkind: clip\n---\nbody\n")
            _fd = os.path.join(_cj, "09-qa", "fanout", "c1"); os.makedirs(_fd)
            open(os.path.join(_fd, "S2.md"), "w").write('```fanout\n{"unit": "S2", "agent": "cine-scene-continuity", '
                                                       '"verdict": "FAIL"}\n```\nthe lamp moved\n')
            _cjob = type("CJ", (), {"path": _cj, "prompts": _pd})()
            _sc4 = {"shot": "S4", "_file": "S4.clip.prompt.md"}
            assert continuity_units(_cjob, _sc4)[0] == "S2", continuity_units(_cjob, _sc4)
            assert continuity_fail(_cjob, _sc4)[0] == "S2", "the scene a scene-form clip names is checked"
            assert continuity_fail(_cjob, {"shot": "S9", "_file": "nope.md"}) == (None, None)
        up = ba("mcp__Higgsfield__upscale_image", [None], FakeStudio(100, 100))
        assert not up["fires"] and "ALREADY" in up["lines"][0], "a spend-class tool gets the month line, never a stop"
        fire = {"fires": True, "lines": ["L"], "why": ["W"]}
        quiet = {"fires": False, "lines": ["L"], "why": []}
        for dd in ({"decision": "allow", "reason": "", "context": ""}, {"decision": "deny", "reason": "no", "context": ""}):
            assert budget_merge(dd, fire, img) == dd, f"{dd['decision']} is never touched by a budget stop"
        assert budget_merge({"decision": "pass", "reason": "", "context": "c"}, fire, img)["decision"] == "ask"
        assert budget_merge({"decision": "preapproved", "reason": "a", "context": ""}, fire, img)["decision"] == "ask"
        m_ = budget_merge({"decision": "ask", "reason": "already submitted", "context": ""}, fire, img)
        assert m_["reason"].startswith("already submitted") and "ALSO a budget stop: W" in m_["reason"], m_
        q_ = budget_merge({"decision": "pass", "reason": "", "context": "c"}, quiet, img)
        assert q_["decision"] == "pass" and q_["context"] == "c · L", q_
        a_ = budget_merge({"decision": "ask", "reason": "upscale spends", "context": ""}, quiet, img)
        assert a_["decision"] == "ask" and a_["reason"] == "upscale spends · L", "(review) the month is on the prompt"
        dn = {"fires": True, "lines": [], "why": [], "deny": "envelope 0"}
        for dd in ("pass", "preapproved", "ask"):
            assert budget_merge({"decision": dd, "reason": "", "context": ""}, dn, img)["decision"] == "deny", \
                f"(review) envelope 0 turns a {dd} into a deny"
        assert budget_merge({"decision": "allow", "reason": "", "context": ""}, dn, img)["decision"] == "allow"
        wrote: list = []

        class Rec:
            def record_spend(self, *a_, **k_):
                wrote.append(a_); return "x"
        g["_studio"] = lambda: Rec()
        fj = type("J", (), {"fields": {"job": "j"}, "path": "/x/j"})()
        assert studio_events(fj, "mcp__Kling_AI__text_to_video", [None], "submitted") == 0 and not wrote, \
            "Kling bills its own account: no studio event"
        assert studio_events(fj, img, [4.0, 4.0], "submitted") == 2 and len(wrote) == 2, "one event per request"
    finally:
        g.update(keep)


def _selftest_roles() -> None:
    class _J:
        fields: dict = {}
    j = _J()
    j.fields = {"approver": "Dana Ito"}
    assert role_line(j) is None, "no role lines: status reads as in 3.0"
    j.fields = {"approver": "Dana Ito", "producer": "Sam Reyes", "editor": "<name>"}
    ln = role_line(j)
    assert ln and "Producer Sam Reyes" in ln and "Editor (not set)" in ln and "Reviewer (not set)" in ln, ln
    assert "information only" in ln


def _selftest_sessions() -> None:
    """(3.1) PLAN-FINAL items 6–8: sessions, the approval guard, hookless only when set."""
    import tempfile, contextlib, io, shutil
    g = globals()
    keep = {k: g[k] for k in ("CINE_HOME", "ACTIVE_FILE", "TRANSCRIPT_FILE", "HOOK_SESSION", "CLI_SESSION")}
    old_env = {k: os.environ.pop(k, None) for k in ("CINE_SESSION", "CINE_JOB")}
    with tempfile.TemporaryDirectory() as td:
        try:
            g["CINE_HOME"] = td; g["ACTIVE_FILE"] = os.path.join(td, "active-job")
            g["TRANSCRIPT_FILE"] = os.path.join(td, "transcript-path"); g["HOOK_SESSION"] = None; g["CLI_SESSION"] = None
            # a hooked home (no hookless setting): no transcript at all → refused, never UNVERIFIED
            assert quote_in_transcript("yes ship it now") == "no-transcript"
            assert quote_refusal("yes ship it now"), "no transcript on a hooked home refuses"
            json.dump({"hookless": True}, open(os.path.join(td, "config.json"), "w"))
            assert quote_refusal("yes ship it now") is None, "hookless (set explicitly) records it"
            _gdt = os.path.join(td, "jt-gate"); os.makedirs(_gdt)
            class _JT:
                gate_dir = _gdt
                @staticmethod
                def approvals():
                    return [{"stage": "concept", "verified": "transcript"}]
            class _JU:
                gate_dir = _gdt
                @staticmethod
                def approvals():
                    return [{"stage": "concept", "verified": "UNVERIFIED hookless"}]
            assert quote_refusal("yes ship it now", _JT) and quote_refusal("yes ship it now", _JU) is None, \
                "(build review 2) a job checked in another home refuses an unchecked quote, even hookless"
            note_verified_home(_JT)
            assert quote_refusal("yes ship it now", _JT) is None, "the home that checked it may still record hookless"
            os.remove(os.path.join(td, "config.json"))
            # two sessions, each with its own transcript (under the temp root the tests declare)
            t1, t2 = os.path.join(td, "s1.jsonl"), os.path.join(td, "s2.jsonl")
            open(t1, "w").write(json.dumps({"type": "user", "message": {"role": "user", "content": "approve the one script"}}) + "\n")
            open(t2, "w").write(json.dumps({"type": "user", "message": {"role": "user", "content": "approve the two script"}}) + "\n")
            _record_transcript({"session_id": "s1", "transcript_path": t1}); g["HOOK_SESSION"] = None
            assert resolve_session() == ("s1", ""), "one live session is used"
            assert quote_in_transcript("approve the one script") == "verified"
            _record_transcript({"session_id": "s2", "transcript_path": t2}); g["HOOK_SESSION"] = None
            sid, why = resolve_session()
            assert sid is None and "s1" in why and "s2" in why, "two live sessions: refused, naming both"
            assert quote_refusal("approve the one script"), "ambiguous session: the quote is not checked"
            g["CLI_SESSION"] = "s1"
            assert quote_in_transcript("approve the one script") == "verified"
            assert quote_in_transcript("approve the two script") == "not-found", "session 2's words are not session 1's"
            g["CLI_SESSION"] = "nope"
            assert resolve_session()[0] is None and "not one a hook has recorded" in resolve_session()[1]
            # each session keeps its own job
            ja, jb = os.path.join(td, "ja"), os.path.join(td, "jb"); os.makedirs(ja); os.makedirs(jb)
            g["CLI_SESSION"] = "s1"; assert set_active(ja) is None
            g["CLI_SESSION"] = "s2"; assert set_active(jb) is None
            assert not os.path.exists(ACTIVE_FILE), "two live sessions: the shared pointer is never written"
            g["CLI_SESSION"] = "s1"; assert active_job()[0] and active_job()[0].path == os.path.abspath(ja)
            g["CLI_SESSION"] = None; g["HOOK_SESSION"] = "s2"
            assert active_job()[0] and active_job()[0].path == os.path.abspath(jb), "a hook sees its own session's job"
            os.environ["CINE_JOB"] = ja
            assert active_job()[0].path == os.path.abspath(jb), "a hook never follows CINE_JOB"
            os.environ.pop("CINE_JOB")
            g["HOOK_SESSION"] = None
            assert set_active(ja) and "say which one" in set_active(ja), "open with two live sessions and no id refuses"
            # a transcript outside the projects folder (and outside any declared root) is not a transcript
            saved_root = os.environ.pop("CINE_TRANSCRIPT_ROOT", None)
            try:
                g["CLI_SESSION"] = "s1"
                assert quote_in_transcript("approve the one script") == "no-transcript"
                assert "projects folder" in LAST_SESSION_WHY
            finally:
                if saved_root is not None:
                    os.environ["CINE_TRANSCRIPT_ROOT"] = saved_root
            # the sessions folder deleted after hooks ran: still refused without the hookless setting
            g["CLI_SESSION"] = None
            shutil.rmtree(sessions_dir())
            assert quote_in_transcript("approve the two script") == "verified", "the shared pointer is the last hook's"
            os.remove(TRANSCRIPT_FILE)
            assert quote_refusal("approve the two script"), "no sessions and no pointer: refused, not UNVERIFIED"
            # (3.1 build review 1, Grok HIGH) a later window never spends or approves on the job another one opened
            if os.path.isdir(sessions_dir()):
                shutil.rmtree(sessions_dir())
            _record_transcript({"session_id": "s5", "transcript_path": t1}); g["HOOK_SESSION"] = None
            assert set_active(ja) is None and json.load(open(ACTIVE_FILE)).get("session") == "s5"
            save_session("s5", job=None, last=time.time() - 3600)          # s5 went quiet; its record lost the job
            _record_transcript({"session_id": "s6", "transcript_path": t2})     # a new window, no job opened in it
            _j6, _w6 = active_job()
            assert _j6 is None and "opened by session s5" in _w6, ("another session's shared job is refused", _w6)
            g["HOOK_SESSION"] = None
            save_session("s6", job=jb, opened=time.time())
            os.environ["CINE_JOB"] = ja; g["CLI_SESSION"] = "s6"
            _j7, _w7 = active_job()
            assert _j7 is None and "use one or the other" in _w7, "CINE_JOB naming another job than the session's"
            g["CLI_SESSION"] = None                                         # no id given: the one live session is s6
            _j8, _w8 = active_job()
            assert _j8 is None and "use one or the other" in _w8, ("(build review 2) CINE_JOB vs the live session", _w8)
            os.environ["CINE_JOB"] = jb
            assert active_job()[0] and active_job()[0].path == os.path.abspath(jb), "CINE_JOB = the session's job is fine"
            os.environ.pop("CINE_JOB"); g["CLI_SESSION"] = None
            # (build review 2) closing a job clears the shared pointer it owns, even with another session live
            shutil.rmtree(sessions_dir())
            _record_transcript({"session_id": "s7", "transcript_path": t1}); g["HOOK_SESSION"] = None
            assert set_active(ja) is None and json.load(open(ACTIVE_FILE)).get("session") == "s7"
            _record_transcript({"session_id": "s8", "transcript_path": t2}); g["HOOK_SESSION"] = None
            g["CLI_SESSION"] = None
            _buf = io.StringIO()
            with contextlib.redirect_stderr(_buf), contextlib.redirect_stdout(io.StringIO()):
                _rc = cmd_close(None)
            assert _rc == 1 and "say which one" in _buf.getvalue() and os.path.exists(ACTIVE_FILE), \
                "(build review 3) close with two live sessions and no id refuses; it never claims 'closed'"
            g["CLI_SESSION"] = "s7"; assert set_active(None) is None
            assert not os.path.exists(ACTIVE_FILE), "a closed job does not come back through the shared pointer"
            g["CLI_SESSION"] = None
            # --by names the checkpoint's Approver (whole name, any case, a title after it is fine)
            class _J:
                fields = {"approver": "Dana Ito, Sam Reyes"}
            assert by_refusal(_J, "dana ito") is None and by_refusal(_J, "Sam Reyes | CEO") is None
            assert by_refusal(_J, "Dan") and by_refusal(_J, "Danae Ito") and by_refusal(_J, "Claude"), "others refused"
            # a hook payload without a session id: reads pass, anything gated is denied
            buf = io.StringIO()
            for payload, want in (({"tool_name": "mcp__Higgsfield__show_generations", "tool_input": {}}, "{}"),
                                  ({"tool_name": "mcp__Higgsfield__generate_video", "tool_input": {"params": {}}}, "no session_id")):
                buf = io.StringIO()
                old_stdin = sys.stdin
                sys.stdin = io.StringIO(json.dumps(payload))
                try:
                    with contextlib.redirect_stdout(buf):
                        cmd_hook(None)
                finally:
                    sys.stdin = old_stdin; g["HOOK_SESSION"] = None
                assert want in buf.getvalue(), (payload["tool_name"], buf.getvalue()[:200])
        finally:
            g.update(keep)
            for k, v in old_env.items():
                if v is not None:
                    os.environ[k] = v

def selftest() -> int:
    import tempfile as _tfr
    os.environ.setdefault("CINE_TRANSCRIPT_ROOT", _tfr.gettempdir())   # (3.1) the tests' transcripts live in temp
    import tempfile
    # the selftests' connector settings: the sample uuid is the Higgsfield account, nothing is "other" unless a test says so
    os.environ["CINE_HIGGSFIELD_CONNECTORS"] = SAMPLE_CONNECTOR
    os.environ.pop("CINE_OTHER_CONNECTORS", None)
    assert normalize_prompt("  a\n\n b\t“c”  ") == 'a b "c"'
    assert TOOL_RE.match("mcp__Higgsfield__generate_video_batch").group(1) == "video"
    assert not TOOL_RE.match("mcp__Higgsfield__models_explore")
    assert parse_kv("Job: a\nMode: B — why\n  more\nNext:")["mode"] == "B — why more"
    assert parse_kv("> Rules the validator applies: x\nJob: a")["job"] == "a"
    assert POLICY_LINE_RE.search("**Verification policy:** `gated`").group(1) == "gated"
    assert script_lines("# T\n\nS1  HOST: Every bottle starts here.\n- direction\nS3 HOST: \"Quoted line here.\"") == \
        ["Every bottle starts here.", "Quoted line here."]
    assert requests_of("x_batch", {"requests": [{"params": '{"model": "m"}'}, "junk"]}) == [{"model": "m"}, {}]
    # a clip with lines is under the voice gate whatever its type; an end still bound as a reference
    assert speaks({"type": "dialogue"}) and speaks({"type": "sequence", "has_speech": True})
    assert not speaks({"type": "broll"}) and not speaks({}) and not speaks(None)
    assert [r["value"] for r in endframe_refs({"refs": [{"what": "character", "value": "a"},
                                                        {"what": " EndFrame ", "value": "e"}, "junk"]})] == ["e"]
    with tempfile.TemporaryDirectory() as td:
        globals()["CINE_HOME"] = td
        globals()["ACTIVE_FILE"] = os.path.join(td, "active-job")
        globals()["TRANSCRIPT_FILE"] = os.path.join(td, "transcript-path")
        os.environ.pop("CINE_JOB", None); os.environ.pop("CINE_GATE", None)
        d = decide("mcp__Higgsfield__generate_video", {"params": {"model": "kling3_0", "prompt": "x"}})
        assert d["decision"] == "deny" and "No production job" in d["reason"], d
        assert decide("mcp__Higgsfield__show_generations", {})["decision"] == "allow"
        assert decide("mcp__Higgsfield__upscale_video", {"params": {}})["decision"] == "deny"
        # ⛔ 2026-10-26: a second Higgsfield connector (`Higgsfield-Second`) and Kling's own API connector
        # arrived and the hooks matched neither. Both are gated now: hooks.json fires, decide() denies.
        for _t in ("mcp__Higgsfield-Second__generate_video", "mcp__Kling_AI__image_to_video",
                   "mcp__Kling_AI__text_to_video", "mcp__Kling_AI__text_to_image", "mcp__Kling_AI__image_to_image",
                   "mcp__Kling_AI__omni_ref_video", "mcp__Kling_AI__motion_control",
                   "mcp__remote-devices__Kling_AI__image_to_video"):
            assert decide(_t, {"params": {}})["decision"] == "deny", _t
        for _t in ("mcp__Kling_AI__who_am_i", "mcp__Kling_AI__query_tasks",
                   "mcp__Kling_AI__query_membership_and_credits", "mcp__Higgsfield-Second__show_generations"):
            assert decide(_t, {})["decision"] == "allow", _t
        _hk = load_json(os.path.join(SKILL_ROOT, os.pardir, os.pardir, "hooks", "hooks.json"))
        _mk = [e.get("matcher") or "" for e in _hk["hooks"]["PreToolUse"]]
        for _t in ("mcp__Higgsfield-Second__generate_video", "mcp__Kling_AI__image_to_video",
                   "mcp__remote-devices__Kling_AI__text_to_video", "mcp__Higgsfield__generate_image"):
            assert any(re.fullmatch(mt, _t) for mt in _mk), (_t, _mk)
        assert not any(re.fullmatch(mt, "mcp__Figma__generate_image") for mt in _mk), _mk
        # the five connector tools that used to pass ungated: denied with no job, under BOTH names
        for _t in ("ads_studio_generate", "ai_influencer_generate", "build_ai_influencer", "execute_preset",
                   "shorts_studio_create_preset"):
            for _srv in ("Higgsfield", "remote-devices__Higgsfield", SAMPLE_CONNECTOR):
                assert SPEND_RE.match(f"mcp__{_srv}__{_t}").group(1) == _t, (_srv, _t)
                _d = decide(f"mcp__{_srv}__{_t}", {"action": "submit", "params": {}, "max_credits": 1})
                assert _d["decision"] == "deny" and "No production job" in _d["reason"], (_srv, _t, _d)
        # Higgsfield's Earth Zoom preset is reference only — refused before any job is consulted
        _ez = decide("mcp__Higgsfield-Second__execute_preset", {"preset_id": "1ac7759b-7df1-4c96-a97a-baf611f7d38e", "inputs": {}})
        assert _ez["decision"] == "deny" and "reference only" in _ez["reason"] and "ruling" not in _ez["reason"], _ez
        assert "reference only" not in decide("mcp__Higgsfield-Second__execute_preset", {"preset_id": "another"})["reason"]
        # the three found 2026-10-23: spend-class with no job, under every server name; the 3D-Jutsu
        # video tool refused always; virality_predictor free only for `preview`; its neighbours stay free
        for _t in ("scene_builder_3d_generate_angles", "relight_image", "virality_predictor"):
            for _srv in ("Higgsfield", "remote-devices__Higgsfield", SAMPLE_CONNECTOR):
                assert SPEND_RE.match(f"mcp__{_srv}__{_t}").group(1) == _t, (_srv, _t)
                _d = decide(f"mcp__{_srv}__{_t}", {"action": "create", "params": {}})
                assert _d["decision"] == "deny" and "No production job" in _d["reason"], (_srv, _t, _d)
        for _srv in ("Higgsfield", "remote-devices__Higgsfield", SAMPLE_CONNECTOR):
            _d = decide(f"mcp__{_srv}__scene_builder_3d_generate_video", {"prompt": "x"})
            assert _d["decision"] == "deny" and "refused even inside" in _d["reason"], (_srv, _d)
        _v = "mcp__" + SAMPLE_CONNECTOR + "__virality_predictor"
        assert decide(_v, {"action": "preview", "params": {}})["decision"] == "allow"
        for _ti in ({"action": "create"}, {}, {"action": "Create "}, None):
            assert decide(_v, _ti)["decision"] == "deny", _ti
        for _t in ("scene_builder_3d_get_project", "scene_builder_3d_query_python", "scene_builder_3d_list_projects",
                   "scene_builder_3d_get_generation"):
            assert decide("mcp__" + SAMPLE_CONNECTOR + "__" + _t, {})["decision"] == "allow", _t
        # build_ai_influencer's read/price actions spend nothing and stay free; submit, an unknown
        # action and a missing action are spends (fail closed)
        _b = "mcp__" + SAMPLE_CONNECTOR + "__build_ai_influencer"
        for _a in ("options", "presets", "recreate", "quote", " Quote "):
            assert decide(_b, {"action": _a})["decision"] == "allow", _a
        for _ti in ({"action": "submit"}, {"action": "generate"}, {}, {"action": 1}, None):
            assert decide(_b, _ti)["decision"] == "deny", _ti
        # neighbours that only read or price stay ungated
        for _t in ("ads_studio_quote", "ai_influencer_prepare", "get_presets", "shorts_studio_list_presets"):
            assert SPEND_RE.match("mcp__" + SAMPLE_CONNECTOR + "__" + _t) is None, _t
            assert decide("mcp__" + SAMPLE_CONNECTOR + "__" + _t, {})["decision"] == "allow", _t
        assert decide("mcp__Higgsfield__tiktok_publish", {})["decision"] == "deny"
        # the seven found 2026-10-24: Katana's run session spends (a free run); six tools publish
        for _srv in ("Higgsfield", "remote-devices__Higgsfield", SAMPLE_CONNECTOR):
            assert SPEND_RE.match(f"mcp__{_srv}__get_katana_config")
            for _ti in ({"free_generation": True}, {"free_generation": False}, {}):
                _d = decide(f"mcp__{_srv}__get_katana_config", _ti)
                assert _d["decision"] == "deny" and "No production job" in _d["reason"], (_srv, _ti, _d)
            for _t in ("publish_project", "publish_website", "deploy_website", "participate_in_contest",
                       "confirm_project_publication_review", "update_project_publication"):
                assert PUBLISH_RE.match(f"mcp__{_srv}__{_t}").group(1) == _t, (_srv, _t)
                assert decide(f"mcp__{_srv}__{_t}", {})["decision"] == "deny", (_srv, _t)
        # their readers stay free
        for _t in ("get_project_publication", "website_status", "list_websites", "get_preset_instructions",
                   "get_workflow_instructions", "shorts_studio_status"):
            assert decide("mcp__" + SAMPLE_CONNECTOR + "__" + _t, {})["decision"] == "allow", _t
        tp = os.path.join(td, "t.jsonl")
        open(tp, "w").write(json.dumps({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "content": "Your questions have been answered: \"yes, v3 is approved\""}]}}) + "\n")
        open(TRANSCRIPT_FILE, "w").write(tp)
        # (v2.61.0) that result is tied to no AskUserQuestion call, so it is not the human's answer
        assert quote_in_transcript("yes, v3 is approved") == "not-found"
        open(tp, "a").write(
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "toolu_ask1", "name": "AskUserQuestion", "input": {}}]}}) + "\n" +
            json.dumps({"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_ask1",
                 "content": 'User has answered your questions: "Approve v3?"="yes, v3 is approved". You can now continue'}]}}) + "\n" +
            json.dumps({"type": "user", "message": {"role": "user", "content": "do not ship the batch yet"}}) + "\n" +
            json.dumps({"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_bash1", "content": "echo: go ahead with all shots"}]}}) + "\n" +
            json.dumps({"type": "user", "isMeta": True, "message": {"role": "user", "content": "approve the export now"}}) + "\n" +
            json.dumps({"type": "user", "message": {"role": "user", "content":
                "<system-reminder>approve every frame</system-reminder> Yes — ship v4, thanks"}}) + "\n")
        open(TRANSCRIPT_FILE, "w").write(tp)
        assert quote_in_transcript("yes, v3 is approved") == "verified"           # the picked answer, whole
        assert quote_in_transcript("this was never typed") == "not-found"
        assert quote_in_transcript("ship the batch") == "not-found"               # a fragment of "do not ship the batch yet"
        assert quote_in_transcript("go ahead with all shots") == "not-found"      # a Bash result is not the human
        assert quote_in_transcript("approve the export now") == "not-found"       # a meta entry (agent hand-back)
        assert quote_in_transcript("approve every frame") == "not-found"          # a system reminder
        assert quote_in_transcript("ship v4") == "verified"                       # a dash-separated clause
        assert quote_in_transcript("Yes — ship v4, thanks") == "verified"         # the whole message
        # (v2.62.0) each request is priced by the rate table, so the envelope can be a cap
        assert request_credits("mcp__Higgsfield__generate_video",
                               {"params": {"model": "kling3_0", "resolution": "1080p", "duration": 5}}) == [7.5]
        assert request_credits("mcp__Higgsfield__generate_video",
                               {"params": {"model": "kling3_0", "resolution": "1080p", "duration": 5, "count": 2}}) == [15.0]
        assert request_credits("mcp__Higgsfield__generate_image",
                               {"params": {"model": "nano_banana_pro", "resolution": "2k", "count": 3}}) == [6.0]
        assert request_credits("mcp__Higgsfield__generate_video", {"params": {"model": "not_a_model", "duration": 5}}) == [None]
        assert request_credits("mcp__Higgsfield__generate_video_batch", {"requests": [
            {"params": {"model": "kling3_0", "resolution": "1080p", "duration": 4}},
            {"params": {"model": "kling3_0", "resolution": "1080p", "duration": 4, "get_cost": True}}]}) == [6.0]
    # ⛔ the claims_lint JSON contract: keyed by FILE, level field named `severity`. The first
    # version of the approve-script check read "findings"/"level" — both absent — and so waved
    # through a script with 6 BLOCK findings. Assert the real shape.
    _cl = {"01-script/SCRIPT-x-v3.md": [
        {"line": 2, "match": "Made in the USA", "severity": "BLOCK", "why": "…"},
        {"line": 6, "match": "Limited offer", "severity": "WARN", "why": "…"}]}
    _rows = []
    for _v in _cl.values():
        if isinstance(_v, list):
            _rows += [x for x in _v if isinstance(x, dict)]
    _blocks = [f for f in _rows if str(f.get("severity") or f.get("level") or "").upper() == "BLOCK"]
    assert len(_rows) == 2 and len(_blocks) == 1, (_rows, _blocks)
    # ...and the older/bare shapes still parse, so neither tool can break the other by changing
    assert [f for f in [{"level": "BLOCK"}] if str(f.get("severity") or f.get("level") or "").upper() == "BLOCK"]
    # ⛔ and the CURRENT shape, which nests findings and carries an `inconclusive` list of PATHS —
    # iterating every top-level value would pull those strings in as if they were findings
    _cur = {"findings": {"a.md": [{"severity": "BLOCK", "match": "x"}]},
            "coverage": {"a.md": {"tokens": 12}}, "inconclusive": ["a.md"]}
    _inc = [x for x in (_cur.get("inconclusive") or []) if isinstance(x, str)]
    _fnd = _cur.get("findings")
    _buckets = list(_fnd.values()) if isinstance(_fnd, dict) else [_fnd]
    _r2 = []
    for _v in _buckets:
        if isinstance(_v, list):
            _r2 += [x for x in _v if isinstance(x, dict)]
    assert _inc == ["a.md"] and len(_r2) == 1 and _r2[0]["severity"] == "BLOCK", (_inc, _r2)

    # ⛔ a vanished active job clears its own pointer rather than being carried
    with tempfile.TemporaryDirectory() as _td:
        _gone = os.path.join(_td, "jobs", "vanished")
        _home = os.path.join(_td, "home")
        os.makedirs(_home)
        _old_home, _old_active = CINE_HOME, ACTIVE_FILE
        globals()["CINE_HOME"] = _home
        globals()["ACTIVE_FILE"] = os.path.join(_home, "active.json")
        _env = os.environ.pop("CINE_JOB", None)
        try:
            json.dump({"job": _gone, "ts": time.time()}, open(ACTIVE_FILE, "w"))
            job_, why_ = active_job()
            assert job_ is None, job_
            assert "no longer exists" in why_ and "cleared" in why_, why_
            assert not os.path.isfile(ACTIVE_FILE), "the stale pointer was not cleared"
            assert active_job()[1] == "no job open", active_job()
        finally:
            globals()["CINE_HOME"], globals()["ACTIVE_FILE"] = _old_home, _old_active
            if _env is not None:
                os.environ["CINE_JOB"] = _env

    # ⛔ the calibration scope, which is a HOLE if a substring can open it. The first version of
    # this test was `"_lab" in client`, so a checkpoint reading "acme (see _lab bench)" would
    # have skipped the look board on a paying job. Both directions pinned.
    class _J:
        def __init__(self, client, name):
            self.fields = {"client": client}; self.path = "/x/" + name
        def validate(self): return []
    assert calibration_job(_J("clients/_lab.md", "lab-00001-fov"))
    assert calibration_job(_J("`clients/_lab.md`", "lab-00002"))
    assert not calibration_job(_J("acme (see _lab bench)", "lab-00003"))   # the spoof
    assert not calibration_job(_J("clients/_lab.md", "acme-07"))           # production id
    assert not calibration_job(_J("clients/acme.md", "lab-00004"))
    assert not calibration_job(_J("clients/_lab-acme.md", "lab-00005"))

    # ⛔ the Resolve MCP (2026-09-14): the CODE decides, not a comment or a string; reads stay silent
    with tempfile.TemporaryDirectory() as _td:
        _old_home, _old_active = CINE_HOME, ACTIVE_FILE
        globals()["CINE_HOME"] = _td
        globals()["ACTIVE_FILE"] = os.path.join(_td, "active-job")
        try:
            # ⛔ THE TEST ASSERTED A NAME NOBODY SERVES (2026-09-17). Both spellings below were
            # invented at the desk. The name this session actually receives is the THIRD one — the
            # server proxied through Cowork's device bridge, with a `_Studio` suffix. Under the old
            # pattern every Resolve call in this session, `run_script_unsafe` included, matched
            # nothing and passed ungated. Assert the real one FIRST and keep the invented ones only
            # as the "still tolerated" cases.
            _real = "mcp__remote-devices__DaVinci_Resolve_Studio__"
            assert RESOLVE_RE.match(_real + "run_script_unsafe").group(1) == "run_script_unsafe"
            assert decide(_real + "get_resolve_status", {})["decision"] == "allow"
            assert decide(_real + "run_script", {"script": "project.StartRendering([])"})["decision"] == "deny"
            assert decide(_real + "run_script_unsafe", {"script": "result = 1"})["decision"] == "ask"
            # the same hole on the credit-spending side: Higgsfield proxied the same way
            assert TOOL_RE.match("mcp__remote-devices__Higgsfield__generate_video").group(1) == "video"
            assert TOOL_RE.match("mcp__Higgsfield__generate_image_batch").group(1) == "image"
            assert SPEND_RE.match("mcp__remote-devices__Higgsfield__upscale_video")
            assert PUBLISH_RE.match("mcp__remote-devices__Higgsfield__tiktok_publish")
            assert TOOL_RE.match("mcp__remote-devices__Higgsfield__show_generations") is None
            # ⛔ THE CONNECTOR HAS NO "higgsfield" IN ITS NAME (2026-10-06), AND ITS UUID IS THE ACCOUNT'S (v2.59.0).
            # hooks.json fires on any uuid connector, for the gate's tool names only; the settings say which uuid is
            # Higgsfield. Figma's connector also serves a generate_image: named as "other" it passes; unnamed, it asks.
            _hf = "mcp__" + SAMPLE_CONNECTOR + "__generate_image"
            _figma = "mcp__" + SAMPLE_OTHER + "__generate_image"
            _new = "mcp__5c5c5c5c-1111-4222-8333-944444444444__generate_image"
            assert TOOL_RE.match(_hf).group(1) == "image"
            _hooks = load_json(os.path.join(SKILL_ROOT, os.pardir, os.pardir, "hooks", "hooks.json"))
            _matchers = [e.get("matcher") or "" for e in _hooks["hooks"]["PreToolUse"]]
            assert connector_matcher() in _matchers, "hooks.json's uuid matcher is not gate.connector_matcher()"
            _um = [mt for mt in _matchers if UUID_SRC in mt]
            _names = (_alternatives(SPEND_RE) + _alternatives(PUBLISH_RE) + _alternatives(DENY_ALWAYS_RE) +
                      _alternatives(UPLOAD_RE) + ["generate_image", "generate_video_batch", "generate_audio"])
            assert len(_names) > 45, len(_names)
            for _t in _names:                 # every tool the gate decides on starts it, on ANY uuid connector
                assert any(re.fullmatch(mt, "mcp__" + SAMPLE_OTHER + "__" + _t) for mt in _matchers), _t
            for _t in ("balance", "models_explore", "show_generations", "clickup_create_task", "get_figma_skill",
                       "send_message", "generate_diagram", "generate_image_x", "a_paid_tool_added_tomorrow"):
                # (v2.61.0) every tool of a uuid connector reaches the gate...
                assert any(re.fullmatch(mt, "mcp__" + SAMPLE_OTHER + "__" + _t) for mt in _um), _t
                assert any(re.fullmatch(mt, "mcp__" + SAMPLE_OTHER.upper() + "__" + _t) for mt in _um), _t
            for _t in ("clickup_create_task", "get_figma_skill", "send_message", "generate_diagram"):
                # ...and an unnamed connector's ordinary tool passes at once
                assert decide("mcp__" + SAMPLE_OTHER + "__" + _t, {})["decision"] == "allow", _t
            _post = [e.get("matcher") or "" for e in _hooks["hooks"]["PostToolUse"]]
            assert any(re.fullmatch(mt, _new) for mt in _post), _post
            # the decisions: named Higgsfield → gated (no job: deny); named other → silent; unnamed → ask, naming the fix
            assert decide(_hf, {"params": {}})["decision"] == "deny"
            assert connector_kind(_figma) == "unknown" and decide(_figma, {"params": {}})["decision"] == "ask"
            _ask = decide(_new, {"params": {}})
            assert _ask["decision"] == "ask" and "gate.py connectors --higgsfield" in _ask["reason"], _ask
            # (3.0.0) the ask is remembered locally with the tool's name, for doctor and `connectors --seen`
            assert "generate_image" in seen_connectors().get(_new.split("__")[1], {}).get("tools", []), seen_connectors()
            assert decide("mcp__" + SAMPLE_OTHER + "__clickup_create_task", {})["decision"] == "allow"
            os.environ["CINE_OTHER_CONNECTORS"] = SAMPLE_OTHER
            assert connector_kind(_figma) == "other" and decide(_figma, {"params": {}})["decision"] == "allow"
            # (v2.61.0) a tool only Higgsfield serves stays gated on a connector named "other": one mistaken setting
            # used to ungate the whole account
            for _t in ("scene_builder_3d_generate_video", "generate_3d", "ads_studio_generate", "upscale_video"):
                assert decide("mcp__" + SAMPLE_OTHER + "__" + _t, {"params": {}})["decision"] == "deny", _t
            assert decide("mcp__" + SAMPLE_OTHER + "__generate_image", {"params": {}})["decision"] == "allow"   # Figma's own
            # (v2.61.0) a vendor tool the gate does not know asks; a read passes; either-case uuids are one connector
            for _t in ("mcp__Higgsfield__brand_new_paid_generate", "mcp__Kling_AI__new_text_to_avatar",
                       "mcp__" + SAMPLE_CONNECTOR + "__a_paid_tool_added_tomorrow", "mcp__Higgsfield__delete_project",
                       "mcp__Higgsfield__sandbox_exec", "mcp__Higgsfield__website_secrets"):
                _d = decide(_t, {})
                assert _d["decision"] == "ask" and "does not know this tool" in _d["reason"], (_t, _d)
            for _t in ("mcp__Higgsfield__balance", "mcp__Higgsfield__list_projects", "mcp__Kling_AI__query_tasks",
                       "mcp__" + SAMPLE_CONNECTOR + "__show_generations", "mcp__Higgsfield__website_status"):
                assert decide(_t, {})["decision"] == "allow", _t
            assert connector_kind("mcp__" + SAMPLE_CONNECTOR.upper() + "__generate_video") == "higgsfield"
            assert decide("mcp__" + SAMPLE_CONNECTOR.upper() + "__generate_video", {"params": {}})["decision"] == "deny"
            os.environ["CINE_OTHER_CONNECTORS"] = SAMPLE_OTHER + "," + SAMPLE_CONNECTOR    # named as both
            assert connector_kind(_hf) == "higgsfield" and decide(_hf, {"params": {}})["decision"] == "deny"
            os.environ.pop("CINE_OTHER_CONNECTORS")
            # the settings file works on its own, and a broken file names nothing (unnamed → ask, never allow)
            _hold = os.environ.pop("CINE_HIGGSFIELD_CONNECTORS")
            assert decide(_hf, {"params": {}})["decision"] == "ask"
            json.dump({"higgsfield": [SAMPLE_CONNECTOR.upper()], "other": [SAMPLE_OTHER]},
                      open(os.path.join(CINE_HOME, CONNECTORS_FILE), "w"))
            assert decide(_hf, {"params": {}})["decision"] == "deny" and decide(_figma, {})["decision"] == "allow"
            open(os.path.join(CINE_HOME, CONNECTORS_FILE), "w").write("{not json")
            assert decide(_hf, {"params": {}})["decision"] == "ask" and decide(_figma, {"params": {}})["decision"] == "ask"
            os.remove(os.path.join(CINE_HOME, CONNECTORS_FILE))
            os.environ["CINE_HIGGSFIELD_CONNECTORS"] = _hold
            assert connector_kind("mcp__Higgsfield__generate_image") is None      # a named server is not a uuid connector
            # the recorder: a named server, the named Higgsfield connector and an unnamed one (its call was approved at
            # the ask, v2.59.2) record; a connector named as another service does not
            os.environ["CINE_OTHER_CONNECTORS"] = SAMPLE_OTHER
            assert posthook_records("mcp__Higgsfield__generate_image") and posthook_records(_hf)
            assert not posthook_records(_figma) and posthook_records(_new)
            assert not posthook_records("mcp__" + SAMPLE_CONNECTOR + "__balance")
            os.environ.pop("CINE_OTHER_CONNECTORS")
            _r = "mcp__DaVinci_Resolve__"
            assert decide(_r + "get_resolve_status", {})["decision"] == "allow"
            assert decide(_r + "run_script", {"script": "project.StartRendering([])"})["decision"] == "deny"
            assert decide(_r + "run_script", {"script": "p.GenerateSpeech({})"})["decision"] == "deny"
            assert decide(_r + "run_script",
                          {"script": "# StartRendering()\nx = 'GenerateSpeech('\nresult = 1"})["decision"] == "allow"
            assert decide(_r + "run_script", {"script": "project.AddRenderJob()"})["decision"] == "ask"
            assert decide(_r + "run_script",
                          {"script": "tl.AddMarker(1, 'Blue', 'b', '', 1, '')"})["decision"] == "pass"
            assert decide(_r + "run_script", {"script": "getattr(p, 'x')()"})["decision"] == "ask"
            assert decide(_r + "run_script_unsafe", {"script": "result = 1"})["decision"] == "ask"
            assert decide(_r + "run_script", {"script": "   "})["decision"] == "deny"
            assert decide("mcp__davinci-resolve__render", {})["decision"] == "ask"
            assert RESOLVE_RE.match("mcp__Higgsfield__generate_video") is None
            assert RESOLVE_RE.match("mcp__remote-devices__Higgsfield__generate_video") is None
        finally:
            globals()["CINE_HOME"], globals()["ACTIVE_FILE"] = _old_home, _old_active

    _selftest_v245()
    _selftest_v249()
    _selftest_sessions()
    _selftest_roles()
    _selftest_budget()
    print("selftest OK — normaliser, tool classes (generate/spend/publish), kv parser, script lines, "
          "batch coercion, policy line, deny-without-job, transcript quote check, a vanished "
          "active job that clears its own pointer, the calibration scope (and its substring spoof), "
          "the Resolve MCP classes (read/deny/ask/pass), the claude.ai Higgsfield connector matcher "
          "(its UUID gated, Figma's generate_image not), a suffixed Higgsfield connector and Kling's own API gated, and the five connector spend tools that used to "
          "pass ungated (build_ai_influencer gated by action, failing closed)")
    return 0


def _selftest_v249() -> None:
    """v2.49.0: the reference route (a `form: scene` clip binds approved sheets, no start frame), kept native sound
    (speech still needs `audio`), the sound the file decided, GPT Image 2.6's trap defaults, prop: approvals."""
    import tempfile

    class _FJ:
        def __init__(s, path, rows): s.path, s._rows, s.fields = path, rows, {}
        def approvals(s): return s._rows
        def approved(s, st):
            for r in reversed(s._rows):
                if r["stage"].lower() == st.lower():
                    return r
            return None
        def is_stills(s): return False
        def tier(s): return "production"
        def is_eval_lane(s): return False
        def ever_evaluated(s): return False

    td = tempfile.mkdtemp()
    rows = [{"stage": "script", "media_id": ""}, {"stage": "character:courier", "media_id": "m_char"},
            {"stage": "prop:satchel", "media_id": "m_prop"}, {"stage": "world:roof", "media_id": "m_roof"}]
    J = _FJ(td, rows)
    refs = [{"role": "image_references", "value": v} for v in ("m_char", "m_prop", "m_roof")]
    match = {"_file": "S4.clip.prompt.md", "shot": "S4", "kind": "clip", "form": "scene", "model": "seedance_2_5",
             "resolution": "1080p", "refs": refs, "generate_audio": "true", "variants": 1, "aspect": "16:9", "duration": 10}
    params = {"model": "seedance_2_5", "prompt": "x", "resolution": "1080p", "generate_audio": True, "duration": 10,
              "mode": "omni_reference", "medias": [dict(r) for r in refs]}
    assert _check_match(J, "video", params, "", match, "seedance_2_5") == [], "approved sheets, kept sound: clean"
    bad = dict(params, medias=[{"role": "image_references", "value": "m_char"},
                               {"role": "image_references", "value": "m_x"}])
    assert any("is not an approved sheet" in p_ for p_ in _check_match(J, "video", bad, "", match, "seedance_2_5"))
    none_ = dict(params, medias=[])
    assert any("binds no approved sheet" in p_ for p_ in _check_match(J, "video", none_, "", match, "seedance_2_5"))
    assert any("carries spoken lines" in p_ for p_ in
               _check_match(J, "video", params, "", dict(match, has_speech=True), "seedance_2_5"))
    assert any("≠ linted" in p_ for p_ in
               _check_match(J, "video", dict(params, generate_audio=False), "", match, "seedance_2_5"))
    # an i2v clip (no form) still needs its approved start frame
    assert any("start frame for S4 is not approved" in p_ for p_ in
               _check_match(J, "video", params, "", dict(match, form=None), "seedance_2_5"))
    im = {"_file": "S4.frame.prompt.md", "shot": "S4", "kind": "frame", "model": "gpt_image_2_6", "resolution": "2k",
          "quality": "high", "variants": 1, "aspect": "16:9"}
    pr = _check_match(J, "image", {"model": "gpt_image_2_6", "prompt": "x"}, "", im, "gpt_image_2_6")
    assert any("no `resolution` on gpt_image_2_6" in p_ for p_ in pr) and any("defaults to `low`" in p_ for p_ in pr), pr
    assert _check_match(J, "image", {"model": "gpt_image_2_6", "prompt": "x", "resolution": "2k", "quality": "high"},
                        "", im, "gpt_image_2_6") == []
    assert approved_sheet_ids(J) == {"m_char": "character:courier", "m_prop": "prop:satchel", "m_roof": "world:roof"}
    # an omitted switch is the model's default (ON): a file that says false is held to it
    off_ = dict(match, generate_audio="false")
    nog_ = {k: v for k, v in params.items() if k != "generate_audio"}
    assert any("omitted: the model defaults it ON" in p_ for p_ in _check_match(J, "video", nog_, "", off_, "seedance_2_5"))
    assert _check_match(J, "video", dict(params, generate_audio=False), "", off_, "seedance_2_5") == []
    # (v2.70.0, Wave 5 A7) the preflight audio stop, the plan's six cases
    _sp = {"_file": "S1.clip.prompt.md", "type": "dialogue"}
    _br = {"_file": "S2.clip.prompt.md", "type": "broll"}
    assert audio_preflight_stop({**_sp, "generate_audio": "true"}, False, False), "(1) speaks + true + unapproved → stop"
    assert audio_preflight_stop({**_br, "generate_audio": "true"}, False, True), "(2) guide-audio + true + unapproved → stop"
    assert audio_preflight_stop({**_br, "generate_audio": "false"}, False, True) is None, "(3) guide-audio + false → passes"
    assert audio_preflight_stop({**_br, "generate_audio": "true"}, False, False) is None, "(4) silent clip + true → as today"
    assert audio_preflight_stop({**_br, "generate_audio": "true"}, True, True) is None, "(5) audio approved → untouched"
    assert audio_preflight_stop(dict(_sp), False, True) is None, "(6) file silent on the switch → unchanged"
    _sw = {"param": "generate_audio", "default_on": True, "off": False}
    assert audio_preflight_stop({**_sp, "generate_audio": "true"}, False, False, _sw), "(1) on a model with the switch"
    assert audio_preflight_stop({**_sp, "generate_audio": "true"}, False, False, {}) is None, \
        "(7) a model with no audio switch (MiniMax H3, Gemini, Kling 4.0): never a deadlock, never a stop"
    assert "approve `audio` first" in audio_preflight_stop({**_sp, "generate_audio": "true"}, False, False).lower() \
        or "Approve `audio` first" in audio_preflight_stop({**_sp, "generate_audio": "true"}, False, False)
    assert _check_match(J, "video", nog_, "", match, "seedance_2_5") == [], "omitted = ON = the file's true"
    # the `guide-audio` switch puts the old rule back for one job: kept sound needs `audio` again
    os.makedirs(os.path.join(td, "00-brief"), exist_ok=True)
    open(os.path.join(td, "00-brief", "CHECKPOINT.md"), "w").write(
        "Job:        g-1\nSwitches:   guide-audio — the client mixes every sound themselves\n")
    assert any("routed around by a DEFAULT" in p_ for p_ in _check_match(J, "video", params, "", match, "seedance_2_5"))
    _cr = check_request(J, "video", params, "", sidecars=[])[0]
    assert any("guide-audio" in p_ for p_ in _cr), _cr
    os.remove(os.path.join(td, "00-brief", "CHECKPOINT.md"))
    # ⛔ house rule 8: Fusion, Fairlight and native titles are computer control — a script that writes them is denied
    R8 = {
        "item.GetFusionCompByIndex(1).FindTool('Template').SetInput('StyledText', 'Hi')": True,
        "c = resolve.Fusion().GetCurrentComp()\nfor t in c.GetToolList().values():\n    t.StyledText = 'x'": True,
        "timeline.InsertFusionTitleIntoTimeline('Text+')": True,
        "item.ImportFusionComp('/a.comp')": True,
        "project.ApplyFairlightPresetToCurrentTimeline('Duck')": True,
        "def w(tool):\n    tool.SetInput('Size', 2)\nw(item.GetFusionCompByIndex(1).FindTool('T'))": True,
        # reads stay open: a title's words read back, the Loaders checked after an import, a record dict filled
        "c = item.GetFusionCompByIndex(1)\nrow = {}\n(row['w'], row['f']) = (c.FindTool('T').GetInput('StyledText'), 1)\n"
        "result = {k: t.GetAttrs()['TOOLST_Clip_Name'] for k, t in c.GetToolList(False, 'Loader').items()}": False,
        "timeline.AddMarker(10, 'Blue', 'x', '', 1)\nitem.SetFades({'FadeIn': 12})": False,
        # a toggle set False and a helper nothing live calls are not counted
        "PLACE = False\ndef _p(tl):\n    tl.InsertFusionTitleIntoTimeline('Text+')\nif PLACE:\n    _p(timeline)": False,
        "PLACE = True\ndef _p(tl):\n    tl.InsertFusionTitleIntoTimeline('Text+')\nif PLACE:\n    _p(timeline)": True,
        "PLAN = []\nfor p in PLAN:\n    item.GetFusionCompByIndex(1).AddTool('Background')": False,
    }
    for src_, bad_ in R8.items():
        assert bool(_rule8_problems(src_)) is bad_, (src_, _rule8_problems(src_))
    _con = open(os.path.join(HERE, "resolve-production-console.py"), encoding="utf-8").read()
    assert _rule8_problems(_con) == [], _rule8_problems(_con)[:3]           # the shipped console, toggles as shipped
    assert _rule8_problems(_con.replace("\nPLACE_TITLES = False", "\nPLACE_TITLES = True", 1))
    assert _rule8_problems(_con.replace('\nFAIRLIGHT_PRESET = ""', '\nFAIRLIGHT_PRESET = "Duck"', 1))
    _old_env = os.environ.pop("CINE_GATE", None)
    try:
        d_ = decide_resolve("run_script", "mcp__remote-devices__DaVinci_Resolve_Studio__run_script",
                            {"script": "timeline.InsertFusionTitleIntoTimeline('Text+')"})
        assert d_["decision"] == "deny" and "computer-control rule" in d_["reason"] and "owner " + "rule" not in d_["reason"], d_
        # (v2.70.1, UX study) no message gate.py shows names an internal rule or ruling, gives the owner a gendered pronoun, or
        # tells the agent how to switch the gate off; comments and the module docs may (they are not shown)
        # (build reviews 1-2, Sonnet + Grok) also "(owner, <date>)" asides, "house decision" labels and "rule 8", in the
        # scripts whose refusals and written files a studio reads first. Docstrings and comments are not shown: skipped.
        import ast as _ast
        _core = ("(?:owner " + "rule|owner " + "ruling|owner " + "decision|\\(owner[ ,]|\\bowner,? 20\\d\\d-|\\brule "
                 + "8\\b|(?-i:\\bC" + "7\\b|\\(C\\d{1,2}\\)|, C\\d{1,2}\\)|ruling C\\d)|def" + "rult|fails all " + "the time|CINE_GATE=off "
                 + "in the launching")    # (build review 3, Grok) any ruling code in its aside shape: "(C2)", ", C3)"
        # (build review 2, Sonnet) a shown "he/his/him/himself": the reader may be anyone. The phrases above are split so
        # the guard's own lines cannot match; the pronoun pattern is built from pieces for the same reason.
        _he_core = "\\b(?:" + "h" + "e|h" + "is|h" + "im|h" + "imself)\\b"
        # casefolded; inside the module docstring every line is shown, elsewhere only text after an opening quote
        _in_doc = re.compile(_core + ")|" + _he_core, re.I)
        _in_str = re.compile("[\"'][^\"'\n]*(?:" + _core + ")|" + _he_core + ")", re.I)
        _leak, _here = [], os.path.dirname(os.path.abspath(__file__))
        for _f in ("gate.py", "native.py", "music_fit.py", "build_captions.py", "composer.py", "region_repair.py"):
            _src = open(os.path.join(_here, _f), encoding="utf-8").read()
            _doc, _tree = set(), _ast.parse(_src)
            _mod = _tree.body[0] if _tree.body and isinstance(_tree.body[0], _ast.Expr) else None
            _mod = set(range(_mod.lineno, _mod.end_lineno + 1)) if _mod is not None else set()
            for _nd in _ast.walk(_tree):
                # the MODULE docstring is the --help text (argparse description=__doc__): scanned (build review 2, Grok)
                if isinstance(_nd, (_ast.ClassDef, _ast.FunctionDef, _ast.AsyncFunctionDef)) and _nd.body \
                        and isinstance(_nd.body[0], _ast.Expr) and isinstance(getattr(_nd.body[0], "value", None), _ast.Constant) \
                        and isinstance(_nd.body[0].value.value, str):
                    _doc.update(range(_nd.body[0].lineno, _nd.body[0].end_lineno + 1))
            for _n, _ln in enumerate(_src.splitlines(), 1):
                if _n in _doc or _ln.lstrip().startswith("#"):
                    continue
                if (_in_doc if _n in _mod else _in_str).search(_ln.split("  # ")[0]):
                    _leak.append((_f, _n, _ln.strip()[:90]))
        # the agent's own procedure and the entry pages (build review 2, Grok); a bare "rule 8" is allowed here, since
        # SKILL.md §4 numbers real rules
        # (build review 3, Grok) "owner, <date>" without a parenthesis, one broken over two lines, "owner: *quote*",
        # and the two script guides START-HERE and SKILL.md send the agent to
        _md = re.compile("owner " + "rule|owner " + "ruling|owner " + "decision|def" + "rult|fails all " + "the time|"
                         "\\bown" + "er,?\\s+20\\d\\d|\\(own" + "er,\\s*$|\\bown" + "er: \\*|ruling C\\d", re.I)
        for _f in ("SKILL.md", "PIPELINE.md", "START-HERE.md", "GLOSSARY.md", "README.md", "scripts/README.md",
                   "scripts/INDEX.md"):
            _p = os.path.join(_here, "..", _f)
            for _n, _ln in enumerate(open(_p, encoding="utf-8") if os.path.isfile(_p) else [], 1):
                if _md.search(_ln):
                    _leak.append((_f, _n, _ln.strip()[:90]))
        assert not _leak, _leak
    finally:
        if _old_env is not None:
            os.environ["CINE_GATE"] = _old_env
    # ⛔ v2.50: a preview made outside Resolve never goes into Resolve (the music fit, the region-repair composite)
    _old_env2 = os.environ.pop("CINE_GATE", None)
    try:
        _R = "mcp__remote-devices__DaVinci_Resolve_Studio__run_script"
        for src_, bad_ in (("mp.ImportMedia(['/j/06-music/fit/song.fit.wav'])", True),
                           ("mp.ImportMedia(['/j/06-music/bed/song.bed.wav'])", True),
                           ("mp.ImportMedia(['/j/07-edit/repair/PREVIEW-S2.mov'])", True),
                           ("mp.ImportMedia(['/j/06-music/song.wav'])", False),
                           ("mp.ImportMedia(['/j/06-music/compose/j.layer.wav'])", False),
                           ("ms.AddItemListToMediaPool(['/j/06-music/fit/'])", True),
                           ("mp.ImportMedia(['/lib/Epic.Full.wav'])", False)):
            d_ = decide_resolve("run_script", _R, {"script": src_})
            assert (d_["decision"] == "deny" and "PREVIEW" in d_["reason"]) is bad_, (src_, d_)
    finally:
        if _old_env2 is not None:
            os.environ["CINE_GATE"] = _old_env2
    print("  v2.50 OK — a Python-made preview (music fit, bed, region-repair composite) is refused at import into "
          "Resolve; the original track and the composed layer are not")
    print("  v2.49 OK — a scene clip binds approved sheets (character:/prop:/world:) instead of a start frame; an unapproved "
          "or missing sheet refused; kept native sound passes while speech still needs `audio`; the sound and GPT Image "
          "2.6's quality/resolution are the file's, never a default; the computer-control rule: a Resolve script that writes Fusion, "
          "Fairlight or a native title is denied (reads, markers, fades and dead toggles pass)")


def _selftest_v245() -> None:
    """v2.45 (2026-10-29): no unlinted route, media out only inside a job, Scenario denied, the image edit and its
    target opt-in, the negative channel, the duplicate-spend guard. A real job fixture, linted for real."""
    import tempfile
    PL = _lint_module()
    hk = load_json(os.path.join(SKILL_ROOT, os.pardir, os.pardir, "hooks", "hooks.json"))
    pre = [e.get("matcher") or "" for e in hk["hooks"]["PreToolUse"]]
    post = [e.get("matcher") or "" for e in hk["hooks"].get("PostToolUse") or []]
    for t in ("mcp__scenario__model_run", "mcp__Scenario-Second__upload_asset", "mcp__remote-devices__SCENARIO_mcp__model_run",
              "mcp__Kling_AI__file_upload", "mcp__Higgsfield-Second__media_upload"):
        assert any(re.fullmatch(m_, t) for m_ in pre), (t, pre)
    for t in ("mcp__Higgsfield__generate_video", "mcp__Higgsfield-Second__generate_image_batch",
              "mcp__" + SAMPLE_CONNECTOR + "__generate_image", "mcp__Kling_AI__image_to_video",
              "mcp__remote-devices__Kling_AI__text_to_image"):
        assert any(re.fullmatch(m_, t) for m_ in post), (t, post)
    assert not any(re.fullmatch(m_, "mcp__Kling_AI__query_tasks") for m_ in post), "a read is not a submission"
    assert all("gate.py\" posthook" in h["command"] for e in hk["hooks"]["PostToolUse"] for h in e["hooks"])
    # (v2.70.0) a failed or timed-out call is recorded too, on exactly the same matchers
    assert [e.get("matcher") for e in hk["hooks"].get("PostToolUseFailure") or []] == post, "PostToolUseFailure matchers"
    assert all("gate.py\" posthook --failed" in h["command"] for e in hk["hooks"]["PostToolUseFailure"] for h in e["hooks"])
    with tempfile.TemporaryDirectory() as td:
        old = (CINE_HOME, ACTIVE_FILE, TRANSCRIPT_FILE, os.environ.pop("CINE_JOB", None))
        globals()["CINE_HOME"] = td
        globals()["ACTIVE_FILE"] = os.path.join(td, "active-job")
        globals()["TRANSCRIPT_FILE"] = os.path.join(td, "transcript-path")
        try:
            # --- no job: Scenario always denied, uploads denied, reads free -------------------------------
            for t in ("mcp__scenario__model_run", "mcp__Scenario-Second__upload_asset",
                      "mcp__remote-devices__SCENARIO_mcp__upload_asset_complete", "mcp__scenario__generate_image"):
                d_ = decide(t, {"dry_run": True})
                assert d_["decision"] == "deny" and SCENARIO_WHY in d_["reason"], (t, d_)
            assert decide("mcp__scenario__teams_list", {})["decision"] == "allow"
            for t, ti in (("mcp__Kling_AI__file_upload", {"filename": "a.png"}), ("mcp__Kling_AI__element_create", {}),
                          ("mcp__Higgsfield-Second__media_upload", {"filename": "a.png"}),
                          ("mcp__Higgsfield-Second__manage_reference_elements", {"action": "create", "medias": [{"id": "x"}]}),
                          ("mcp__Higgsfield-Second__manage_reference_elements", {"action": "rename"})):
                d_ = decide(t, ti)
                assert d_["decision"] == "deny" and "no media leaves the machine" in d_["reason"], (t, d_)
            for ti in ({"action": "list"}, {}, {"element_id": "0c0c0c0c-0000-4000-8000-000000000005"}):
                assert decide("mcp__Higgsfield-Second__manage_reference_elements", ti)["decision"] == "allow", ti
            assert decide("mcp__Kling_AI__element_list", {})["decision"] == "allow"
            # --- a job ------------------------------------------------------------------------------------
            job = os.path.join(td, "fx-02451-v245")
            for d_ in ("00-brief", "01-script/prompts", "02-startframes", "_reference"):
                os.makedirs(os.path.join(job, d_))
            prof = os.path.join(td, "fixture.md")
            open(prof, "w").write("# Client Profile — Fixture\n\n## 0. Hard locks\n\n**Default mode:** A\n\n"
                                  "**Verification policy:** `gated`\n\n**Named approver:** Dana\n\n## 1. Brand\n- Fixture.\n")
            open(os.path.join(job, "00-brief", "CHECKPOINT.md"), "w").write(
                f"# PRODUCTION CHECKPOINT\n\nJob:        fx-02451-v245\nMode:       A — one hero film\nClient:     {prof}\n"
                "Policy:     gated\nFormat:     vertical-1080 (master)\nVoice:      none — no lines\n"
                "Inputs:     brand assets PRESENT · reference images PRESENT\nGates:      frame gate → prompt lint → QA\n"
                "Skips:      none\nBudget:     envelope 900 cr · estimate 300 cr [estimated]\nApprover:   Dana\n"
                "Next:       frames\n")
            for f_, b_ in (("S3_hero_v2.png", b"\x89PNG hero"), ("S4_kitchen_v2.png", b"\x89PNG kitchen")):
                open(os.path.join(job, "02-startframes", f_), "wb").write(b_)
            rows = ["| t | concept | Dana | C2 it is | | | | UNVERIFIED |",
                    "| t | script | Dana | the script is signed | 01-script/S.md | | | UNVERIFIED |",
                    "| t | frame:S3 | Dana | the S3 still is right | 02-startframes/S3_hero_v2.png | | job_s3 | UNVERIFIED |"]
            apv = os.path.join(job, "00-brief", "APPROVALS.md")
            open(apv, "w").write("# Approvals\n\n| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n"
                                 "|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
            pdir = os.path.join(job, "01-script", "prompts")
            # (v2.71.0) the frame template ends in [CONSTRAINTS] now; this fixture keeps a legacy [SUPPRESS] list so the
            # gate's refusal of a negative_prompt on a model with no negative field is still exercised
            frame = PL.TEMPLATES["frame"].replace("[CONSTRAINTS]\ntext, logo, second panel, frame border",
                                                  "[SUPPRESS]\ntext, logo, second panel, frame border")
            assert "[SUPPRESS]" in frame, "the frame fixture lost its legacy [SUPPRESS] list"
            for a_, b_ in (("<who/what, pose, action as a mid-action verb, wardrobe stated verbatim>",
                            "a baker sliding a tray of loaves onto a steel bench, mid-push"),
                           ("<the fixed character block, pasted byte-for-byte across every frame>", "flour on her forearms"),
                           ("<location, props, season, time of day — concrete and authentic>",
                            "a bakery at 6am, stacked proving baskets soft and out of focus behind"),
                           ("<lens mm, height, angle: \"50mm, eye level, slight low angle\">", "50mm, eye level"),
                           ("<phone-real or cinema-real, film stock or sensor — physical language, no names>",
                            "phone-real, slight rolling shutter")):
                frame = frame.replace(a_, b_)
            frame = re.sub(r"(?ms)^\[LIGHTING\]\n.*?(?=^\[CAMERA\])",
                           "[LIGHTING]\nhard window sun from camera-left, warm, long shadows across the steel\n\n", frame)
            frame = re.sub(r"(?ms)^refs:.*?(?=^---$)", "", frame).replace("type: character", "type: environment") \
                .replace("character: hero ", "character_unused: hero ")
            edit = PL.TEMPLATES["edit"].replace("<the media id the call binds as the picture being edited>", "job_s4src") \
                .replace("<media id of the real product photo>", "media_oil")
            clip = ("---\nshot: S3\nkind: clip\ntype: broll\nmodel: kling3_0\nresolution: 4k\ncut: 3\nduration: 5\n"
                    "aspect: 9:16\nstart_frame: 02-startframes/S3_hero_v2.png\nfunction: the bake goes in\n"
                    "payload: the tray is on the bench and the bake has started\n---\n[MOTION]\n"
                    "INTENT: the morning rush: quick and sure\nSTART: her hands on the tray at hip height\n"
                    "MID: she pushes the tray onto the bench in one quick shove\nEND: the tray settles flat, the loaves still\n\n"
                    "[CAMERA]\nlocked-off, chest height\n\n[SUPPRESS]\nextra hands, text\n")
            files = {"S3.frame.prompt.md": frame, "S4.edit.prompt.md": edit, "S3.clip.prompt.md": clip,
                     "S5.frame.prompt.md": frame.replace("shot: S3", "shot: S5").replace("model: nano_banana_pro",
                                                                                          "model: kling_omni_image")
                                               .replace("a tray of loaves", "a tray of rye loaves")}
            lint_ = {}
            for n_, t_ in files.items():
                fp = os.path.join(pdir, n_)
                open(fp, "w", encoding="utf-8").write(t_)
                r_ = PL.lint(fp, job)
                assert r_["ok"], (n_, r_["fails"])
                PL.write_sidecar(fp, r_["sidecar"])
                lint_[n_] = r_["sidecar"]
            os.environ["CINE_JOB"] = job
            J = Job(job)
            assert not J.validate(), J.validate()
            img = {"model": "nano_banana_pro", "prompt": lint_["S3.frame.prompt.md"]["prompt"], "aspect_ratio": "9:16",
                   "resolution": "2k", "count": 2}
            # --- (v2.48.0, project switches): no line validates (above); a valid one is stored and changes no decision;
            # a locked rule refuses, naming it ---------------------------------------------------------------------
            cpp_ = os.path.join(job, "00-brief", "CHECKPOINT.md")
            cp0_ = read(cpp_)
            d0_ = decide("mcp__Higgsfield__generate_image", {"params": img})
            open(cpp_, "w").write(cp0_.replace("Skips:      none\n", "Skips:      none\nSwitches:   music-led — the "
                                               "song is the deliverable;\n            light-leak — one hit on the launch cut\n"))
            J_ = Job(job)
            assert not J_.validate() and set(J_.switches) == {"music-led", "light-leak"}, (J_.validate(), J_.switches)
            d1_ = decide("mcp__Higgsfield__generate_image", {"params": img})
            assert (d1_["decision"], d1_["reason"]) == (d0_["decision"], d0_["reason"]), (d0_, d1_)
            open(cpp_, "w").write(cp0_.replace("Skips:      none\n", "Skips:      none\nSwitches:   mask-wipe — the dancer "
                                               "reveals the next shot\n"))
            assert any("`Switches:`" in p and "never a switch" in p and "roto" in p for p in Job(job).validate())
            open(cpp_, "w").write(cp0_)
            # --- the duplicate-spend guard -------------------------------------------------------------------
            d_ = decide("mcp__Higgsfield__generate_image", {"params": img})
            assert d_["decision"] == "pass", d_
            assert decide("mcp__Higgsfield__generate_image", {"params": img})["decision"] == "pass", \
                "nothing submitted yet: a PreToolUse alone records nothing (a denied or abandoned call is no spend)"
            assert record_submission(J, "mcp__Higgsfield__generate_image", {"params": img}, [{"type": "text", "text":
                                     "error: 422 invalid aspect"}]) == 0, "a response with no job id records nothing"
            assert record_submission(J, "mcp__Higgsfield__generate_image", {"params": img}, [{"type": "text", "text":
                                     '{"jobs": [{"job_id": "0c0c0c0c-0000-4000-8000-000000000006"}]}'}]) == 1
            d_ = decide("mcp__Higgsfield-Second__generate_image", {"params": img})
            assert d_["decision"] == "ask" and "already submitted at" in d_["reason"] and "poll that job instead" in d_["reason"] \
                and "0c0c0c0c-0000-4000-8000-000000000006" in d_["reason"], d_
            assert decide("mcp__Higgsfield__generate_image_batch", {"requests": [{"params": img}]})["decision"] == "ask"
            assert decide("mcp__Higgsfield__generate_image", {"params": {**img, "count": 1}})["decision"] == "pass", \
                "a different request is not a duplicate"
            assert decide("mcp__Higgsfield__generate_image", {"params": {**img, "get_cost": True}})["decision"] == "pass"
            sp_ = _submitted_path(J)
            rows_ = [json.loads(x) for x in open(sp_)]
            for x in rows_:
                x["epoch"] -= DUP_WINDOW_S + 60
            open(sp_, "w").write("".join(json.dumps(x) + "\n" for x in rows_))
            assert decide("mcp__Higgsfield__generate_image", {"params": img})["decision"] == "pass", "past 30 minutes"
            # (v2.70.0, A14) a call that failed or timed out: no job id, but an identical retry still asks first
            assert record_unconfirmed(J, "mcp__Higgsfield__generate_image", {"params": img}, "timed out") == 1
            _last = json.loads(open(_submitted_path(J)).read().strip().splitlines()[-1])
            assert _last.get("unconfirmed") and _last.get("credits") == 4.0, _last    # the envelope counts it (Grok r1)
            d_ = decide("mcp__Higgsfield__generate_image", {"params": img})
            assert d_["decision"] == "ask" and "failed or timed out" in d_["reason"] and "show_generations" in d_["reason"], d_
            assert decide("mcp__Higgsfield__generate_image", {"params": {**img, "count": 1}})["decision"] == "pass", \
                "a different request after a failure is not a duplicate"
            # (build review 1, Sonnet) an instant validation refusal charged nothing: no record, no ask
            assert record_unconfirmed(J, "mcp__Higgsfield__generate_image", {"params": {**img, "count": 1}},
                                      "error: 422 Unprocessable Entity: invalid aspect") == 0
            for _msg in ("timed out after 400 seconds", "MCP error: request timed out (id 404)"):
                assert REJECTED_RE.search(_msg) is None or TIMEOUT_RE.search(_msg), _msg
            assert record_unconfirmed(J, "mcp__Higgsfield__generate_image", {"params": {**img, "count": 1}},
                                      "timed out after 400 seconds") == 1, "a timeout is recorded, whatever numbers it carries"
            assert record_unconfirmed(J, "mcp__Higgsfield__generate_image", {"params": {**img, "count": 1}},
                                      "error 400 after the upstream request timed out") == 1, "a timeout beats a status code"
            assert record_unconfirmed(J, "mcp__Higgsfield__generate_image", {"params": {**img, "count": 1}},
                                      "upstream gateway failure (request id 409)") == 1, "a bare number is not a status"
            # posthook through stdin, the way the hook runs it
            import io
            _stdin = sys.stdin
            try:
                sys.stdin = io.StringIO(json.dumps({"tool_name": "mcp__Higgsfield__generate_image", "tool_input": {"params": img},
                                                    "tool_response": {"job_id": "job_9f8e7d6c5b"}}))
                assert cmd_posthook(None) == 0
                sys.stdin = io.StringIO("not json")
                assert cmd_posthook(None) == 0, "the recorder fails open"
                # the PostToolUseFailure payload, as the failure hook delivers it (v2.70.0)
                sys.stdin = io.StringIO(json.dumps({"hook_event_name": "PostToolUseFailure", "tool_name":
                                                    "mcp__Higgsfield__generate_image", "tool_input": {"params": {**img, "count": 1}},
                                                    "error": "MCP tool call timed out"}))
                assert cmd_posthook(None) == 0
            finally:
                sys.stdin = _stdin
            _r9 = decide("mcp__Higgsfield__generate_image", {"params": img}); assert "job_9f8e7d6c5b" in _r9["reason"], (_r9, open(_submitted_path(J)).read()[-900:])
            assert "failed or timed out" in decide("mcp__Higgsfield__generate_image", {"params": {**img, "count": 1}})["reason"]
            # a confirmed job id in the window is named first, even when a later identical call failed
            record_unconfirmed(J, "mcp__Higgsfield__generate_image", {"params": img}, "MCP tool call timed out")
            _rj = decide("mcp__Higgsfield__generate_image", {"params": img})
            assert "job_9f8e7d6c5b" in _rj["reason"] and "failed or timed out" not in _rj["reason"], _rj
            # --- the negative channel and the word -----------------------------------------------------------
            d_ = decide("mcp__Higgsfield__generate_image", {"params": {**img, "count": 1, "negative_prompt": "extra fingers"}})
            assert d_["decision"] == "deny" and "differs from the linted" in d_["reason"], d_
            d_ = decide("mcp__Higgsfield__generate_image", {"params": {**img, "count": 1,
                                                                       "negative_prompt": lint_["S3.frame.prompt.md"]["negative"]}})
            assert d_["decision"] == "deny" and "NO negative field" in d_["reason"], d_
            d_ = decide("mcp__Higgsfield__generate_image", {"params": {**img, "count": 1, "negative_prompt": "watermark"}})
            assert d_["decision"] == "deny" and "'watermark'" in d_["reason"], d_
            # --- the image edit: its source bound, its declared refs, the target opt-in --------------------
            ed = {"model": "nano_banana_pro", "prompt": lint_["S4.edit.prompt.md"]["prompt"], "aspect_ratio": "9:16",
                  "resolution": "2k", "count": 2, "medias": [{"role": "image", "value": "job_s4src"},
                                                             {"role": "image", "value": "media_oil"}]}
            assert decide("mcp__Higgsfield__generate_image", {"params": ed})["decision"] == "pass"
            d_ = decide("mcp__Higgsfield__generate_image", {"params": {**ed, "medias": ed["medias"][1:]}})
            assert d_["decision"] == "deny" and "does not bind the edit's source" in d_["reason"], d_
            d_ = decide("mcp__Higgsfield__generate_image", {"params": {**ed, "medias": ed["medias"] + [{"role": "image",
                                                                                                      "value": "media_x"}]}})
            assert d_["decision"] == "deny" and "does not declare (media_x)" in d_["reason"], d_
            fp = os.path.join(pdir, "S4.edit.prompt.md")
            open(fp, "w", encoding="utf-8").write(edit.replace("use: frame ", "use: target "))
            r_ = PL.lint(fp, job)
            assert r_["ok"], r_["fails"]
            PL.write_sidecar(fp, r_["sidecar"])
            d_ = decide("mcp__Higgsfield__generate_image", {"params": ed})
            assert d_["decision"] == "deny" and "approve target:S4" in d_["reason"] and "2026-10-28" not in d_["reason"], d_
            open(apv, "a").write("| t | target:S4 | Dana | yes, edit our S4 frame into a target | "
                                 "02-startframes/S0_other.png | 0000aaaa | | UNVERIFIED |\n")
            d_ = decide("mcp__Higgsfield__generate_image", {"params": ed})
            assert d_["decision"] == "deny" and "different source picture" in d_["reason"], d_
            src_sha = sha256_file(os.path.join(job, "02-startframes", "S4_kitchen_v2.png"))[:16]
            open(apv, "a").write(f"| t | target:S4 | Dana | yes, edit our S4 frame into a target | "
                                 f"02-startframes/S4_kitchen_v2.png | {src_sha} | | UNVERIFIED |\n")
            assert decide("mcp__Higgsfield__generate_image", {"params": ed})["decision"] == "pass"
            # cmd_approve takes target:<SHOT> (script first) and records the source's hash
            open(os.path.join(CINE_HOME, "config.json"), "w").write('{"hookless": true}')   # (3.1) no transcript here
            rc_ = cmd_approve(argparse.Namespace(stage="target:S6", by="Dana", quote="yes edit the S6 plate frame",
                                                 artifact="02-startframes/S3_hero_v2.png", media_id=None, media_ids=None,
                                                 allow=[], paid=False, no_material_connection=False))
            assert rc_ == 0 and J.approved("target:S6") and J.approved("target:S6")["sha"], J.approved("target:S6")
            os.remove(os.path.join(CINE_HOME, "config.json"))                     # hookless off again
            # --- Kling's connector: a linted Kling prompt or nothing ----------------------------------------
            ka = lambda p_, **kw: {"model": kw.get("model", "kling-image-o1"), "arguments": [{"name": "prompt", "value": p_}]
                                   + kw.get("extra", []), "inputs": kw.get("inputs", []), "rationale": kw.get("why", "x"),
                                   "taskTraceId": kw.get("trace", "0190-a")}
            d_ = decide("mcp__Kling_AI__text_to_image", ka(lint_["S3.frame.prompt.md"]["prompt"]))
            assert d_["decision"] == "deny" and "not for a kling model" in d_["reason"], d_
            d_ = decide("mcp__Kling_AI__text_to_image", ka("a cat on a sofa"))
            assert d_["decision"] == "deny" and "matches no linted prompt" in d_["reason"], d_
            d_ = decide("mcp__Kling_AI__text_to_image", ka(lint_["S5.frame.prompt.md"]["prompt"]))
            assert d_["decision"] == "ask" and "S5.frame.prompt.md" in d_["reason"], d_
            d_ = decide("mcp__Kling_AI__text_to_video", ka(lint_["S5.frame.prompt.md"]["prompt"], model="kling-video-v3_0"))
            assert d_["decision"] == "deny" and "needs a clip prompt" in d_["reason"], d_
            kv = ka(lint_["S3.clip.prompt.md"]["prompt"], model="kling-video-v3_0",
                    inputs=[{"name": "image", "inputType": "URL", "url": "https://x/s3.png"}])
            d_ = decide("mcp__remote-devices__Kling_AI__image_to_video", kv)
            assert d_["decision"] == "ask" and "kling3_0" in d_["reason"], d_
            d_ = decide("mcp__Kling_AI__image_to_video", {**kv, "arguments": kv["arguments"] +
                                                          [{"name": "negative_prompt", "value": "watermark"}]})
            assert d_["decision"] == "deny" and "'watermark'" in d_["reason"], d_
            assert record_submission(J, "mcp__Kling_AI__image_to_video", kv, {"generation_id": "kgen_778899aa"}) == 1
            d_ = decide("mcp__Kling_AI__image_to_video", {**kv, "rationale": "another wording", "taskTraceId": "0190-b"})
            assert d_["decision"] == "ask" and "already submitted at" in d_["reason"] and "kgen_778899aa" in d_["reason"], d_
            d_ = decide("mcp__Kling_AI__motion_control", {"model": "kling-video-v3_0", "arguments": [],
                                                          "inputs": [{"name": "video", "inputType": "URL", "url": "u"}]})
            assert d_["decision"] == "deny" and "carries no `prompt`" in d_["reason"] and "no linted form yet" in d_["reason"] and "M3" not in d_["reason"], d_
            d_ = decide("mcp__Higgsfield-Second__motion_control", {"params": {"image_id": "a", "motion_video_id": "b"}})
            assert d_["decision"] == "deny" and "takes no prompt" in d_["reason"], d_
            # ⚡ GENJUTSU (v2.46.1): on the roster through its own lane — a linted spec, an approval, matched field by field.
            # Without a spec a Genjutsu call is still refused, clip prompt or not:
            d_ = decide("mcp__Higgsfield__generate_video", {"params": {"model": "hf_mult_motion_control",
                        "prompt": lint_["S3.clip.prompt.md"]["prompt"], "duration": 5,
                        "medias": [{"role": "start_image", "value": "job_s3"}]}})
            assert d_["decision"] == "deny" and "no linted Genjutsu spec" in d_["reason"], d_
            _selftest_genjutsu(job, pdir, apv, PL, lint_)
            # the clip's start frame holds on every connector
            open(apv, "w").write(open(apv).read().replace("| t | frame:S3 |", "| t | frame:S3x |"))
            d_ = decide("mcp__Kling_AI__image_to_video", {**kv, "taskTraceId": "0190-c", "inputs": []})
            assert d_["decision"] == "deny" and "start frame for S3 is not approved" in d_["reason"], d_
            # --- media out inside a job: ask, and an identity element says so ------------------------------
            d_ = decide("mcp__Kling_AI__file_upload", {"filename": "s3.png"})
            assert d_["decision"] == "ask" and "sends media" in d_["reason"] and "identity" not in d_["reason"], d_
            d_ = decide("mcp__Higgsfield-Second__manage_reference_elements", {"action": "create", "medias": [{"id": "i", "url": "u"}]})
            assert d_["decision"] == "ask" and "identity element" in d_["reason"], d_
            assert decide("mcp__Kling_AI__element_create", {"name": "x"})["decision"] == "ask"
            assert decide("mcp__scenario__model_run", {})["decision"] == "deny", "inside a job too"
            # preflight emits the edit's source first
            pf_ = io.StringIO()
            import contextlib
            with contextlib.redirect_stdout(pf_):
                cmd_preflight(argparse.Namespace(shot="S4", kind="edit", json=True))
            out_ = json.loads(pf_.getvalue())
            assert out_["params"]["medias"][0] == {"role": "image", "value": "job_s4src"}, out_
            assert out_["negative_prompt"] == "" and "no negative field" in out_["_negative_note"], out_
            st_ = io.StringIO()
            with contextlib.redirect_stdout(st_):
                cmd_status(argparse.Namespace(json=True, full=False))
            assert "S4.edit.prompt.md" in st_.getvalue(), st_.getvalue()[:400]
        finally:
            globals()["CINE_HOME"], globals()["ACTIVE_FILE"], globals()["TRANSCRIPT_FILE"] = old[:3]
            os.environ.pop("CINE_JOB", None)
            if old[3] is not None:
                os.environ["CINE_JOB"] = old[3]
    print("  v2.45 OK — Scenario denied always (four names), uploads and identity elements denied with no job and "
          "asked inside one, Kling's connector held to a linted Kling prompt of the right kind (and its frame "
          "gate), Higgsfield motion control denied, Genjutsu without a spec denied, the image edit's source and target opt-in, the "
          "negative channel and the word, the duplicate-spend guard (posthook, window, batch, Kling volatile args)")


def _selftest_genjutsu(job: str, pdir: str, apv: str, PL, lint_: dict) -> None:
    """v2.46.1 — Genjutsu full and Lite, motion and swap, both server names: no spec → deny, no approval → deny, the
    matching call → ask (free or paid said so), every field that differs → deny, a spec edited after approval → deny, the
    duplicate guard, the free switch refused off Genjutsu, a cost probe free. Runs inside _selftest_v245's job."""
    os.makedirs(os.path.join(job, "04-plates"), exist_ok=True)
    open(os.path.join(job, "04-plates", "B1_real_setdown.mov"), "wb").write(b"a real clip")
    open(os.path.join(job, "02-startframes", "B1_subject_v1.png"), "wb").write(b"\x89PNG subject")
    gsp = os.path.join(pdir, "B1.genjutsu.prompt.md")

    def _gl(t_, fp_=gsp):
        open(fp_, "w", encoding="utf-8").write(t_)
        r_ = PL.lint(fp_, job)
        assert r_["ok"], r_["fails"]
        PL.write_sidecar(fp_, r_["sidecar"])
        return r_
    gtx = PL.GENJUTSU_TEMPLATE.replace("source_video: <media id>", "source_video: job_src01") \
        .replace("value: <media id>", "value: job_ref01") \
        .replace("source_hash: <sha256 of source_file>",
                 "source_hash: " + sha256_file(os.path.join(job, "04-plates", "B1_real_setdown.mov")))
    gsc = _gl(gtx)["sidecar"]
    assert gsc["kind"] == "genjutsu" and gsc["tier"] == "lite" and gsc["source_video"] == "job_src01" \
        and gsc["prompt"] == "" and gsc["free_gens"] == "prefer", gsc
    gcall = {"model": "hf_mult_motion_control_flash", "resolution": "1080p", "use_free_gens": True,
             "medias": [{"role": "video_references", "value": "job_src01"}, {"role": "image_references", "value": "job_ref01"}]}
    d_ = decide("mcp__Higgsfield__generate_video", {"params": gcall})
    assert d_["decision"] == "deny" and "genjutsu:B1 is not approved" in d_["reason"], d_
    with open(apv, "a") as fh:
        fh.write(f"| t | genjutsu:B1 | Dana | Include Genjutsu | 01-script/prompts/B1.genjutsu.prompt.md | "
                 f"{sha256_file(gsp)[:16]} | | UNVERIFIED |\n")
    for srv in ("mcp__Higgsfield__generate_video", "mcp__Higgsfield-Second__generate_video"):
        d_ = decide(srv, {"params": gcall})
        assert d_["decision"] == "ask" and "Genjutsu Lite (lite)" in d_["reason"] and "FREE generation" in d_["reason"] \
            and "Lite 10, full 1" in d_["reason"], (srv, d_)
    # the connector's own role words (`image`, `video`) read as the same call
    d_ = decide("mcp__Higgsfield-Second__generate_video", {"params": {**gcall, "medias": [
        {"role": "video", "value": "job_src01"}, {"role": "image", "value": "job_ref01"}]}})
    assert d_["decision"] == "ask", d_
    # a cost probe spends nothing and passes
    assert decide("mcp__Higgsfield__generate_video", {"params": {**gcall, "get_cost": True}})["decision"] == "pass"
    nores = {k: v for k, v in gcall.items() if k != "resolution"}
    for bad_, why_ in (({**gcall, "resolution": "720p"}, "resolution 720p ≠"),
                       (nores, "no `resolution`"),
                       ({**gcall, "duration": 5}, "only parameter"),
                       ({**gcall, "aspect_ratio": "9:16"}, "only parameter"),
                       ({**gcall, "medias": gcall["medias"][:1]}, "leaves out reference"),
                       ({**gcall, "medias": gcall["medias"] + [{"role": "image_references", "value": "job_x"}]},
                        "does not declare"),
                       ({**gcall, "medias": [{"role": "video_references", "value": "job_other"}, gcall["medias"][1]]},
                        "declares source_video"),
                       ({**gcall, "medias": gcall["medias"] + [{"role": "video_references", "value": "job_v2"}]},
                        "exactly ONE source video"),
                       ({**gcall, "medias": gcall["medias"] + [{"role": "start_image", "value": "job_s3"}]},
                        "roles Genjutsu does not take"),
                       ({**gcall, "prompt": "she sets the cup down"}, "has no [PROMPT] block"),
                       ({**gcall, "model": "hf_mult_motion_control"}, "matches no linted Genjutsu spec"),
                       ({**gcall, "count": 2}, "exceeds the spec")):
        d_ = decide("mcp__Higgsfield__generate_video", {"params": bad_})
        assert d_["decision"] == "deny" and why_ in d_["reason"], (why_, d_)
    # the free switch is read on Genjutsu only
    d_ = decide("mcp__Higgsfield__generate_video", {"params": {"model": "kling3_0", "use_free_gens": True,
                "prompt": lint_["S3.clip.prompt.md"]["prompt"], "duration": 5,
                "medias": [{"role": "start_image", "value": "job_s3"}]}})
    assert d_["decision"] == "deny" and "`use_free_gens` on 'kling3_0'" in d_["reason"], d_
    # a spec edited after its approval is a different spec
    _gl(gtx.replace("before choosing.", "before choosing, side by side."))
    d_ = decide("mcp__Higgsfield__generate_video", {"params": gcall})
    assert d_["decision"] == "deny" and "changed after genjutsu:B1 was approved" in d_["reason"], d_
    _gl(gtx)
    assert decide("mcp__Higgsfield__generate_video", {"params": gcall})["decision"] == "ask"
    # ⛔ the approved spec binds the exact driving video: a different file under the same name is refused
    _vid = os.path.join(job, "04-plates", "B1_real_setdown.mov")
    open(_vid, "wb").write(b"another clip, same name")
    d_ = decide("mcp__Higgsfield__generate_video", {"params": gcall})
    assert d_["decision"] == "deny" and "is not the one this spec was written" in d_["reason"], d_
    open(_vid, "wb").write(b"a real clip")
    assert decide("mcp__Higgsfield__generate_video", {"params": gcall})["decision"] == "ask"
    # the duplicate guard holds on Genjutsu too
    J_ = Job(job)
    assert record_submission(J_, "mcp__Higgsfield__generate_video", {"params": gcall}, {"job_id": "gj_00112233"}) == 1
    d_ = decide("mcp__Higgsfield__generate_video", {"params": gcall})
    assert d_["decision"] == "ask" and "already submitted at" in d_["reason"] and "gj_00112233" in d_["reason"], d_
    # FULL object swap, paid: the lint points at Lite, the gate says it spends
    open(os.path.join(job, "04-plates", "B2_product.mov"), "wb").write(b"a product clip")
    g2 = gtx.replace("shot: B1", "shot: B2").replace("mode: motion", "mode: swap") \
        .replace("model: hf_mult_motion_control_flash", "model: hf_mult_replace_object") \
        .replace("source_video: job_src01", "source_video: job_src02") \
        .replace("source_file: 04-plates/B1_real_setdown.mov", "source_file: 04-plates/B2_product.mov") \
        .replace(sha256_file(os.path.join(job, "04-plates", "B1_real_setdown.mov")),
                 sha256_file(os.path.join(job, "04-plates", "B2_product.mov"))) \
        .replace("free_gens: prefer", "free_gens: no").replace("what: subject, value: job_ref01", "what: product, value: job_prod1")
    g2 = re.sub(r"(?ms)^\[QA\]\n.*\Z", "[QA]\nLabel and logo fidelity on every frame (look_qa.py); the hand and the table "
                "untouched.\n", g2)
    gp2 = os.path.join(pdir, "B2.genjutsu.prompt.md")
    r2 = _gl(g2, gp2)
    assert any("plan Lite first" in w and "hf_mult_replace_object_flash" in w for w in r2["warns"]), r2["warns"]
    with open(apv, "a") as fh:
        fh.write(f"| t | genjutsu:B2 | Dana | Include Genjutsu | 01-script/prompts/B2.genjutsu.prompt.md | "
                 f"{sha256_file(gp2)[:16]} | | UNVERIFIED |\n")
    c2 = {"model": "hf_mult_replace_object", "resolution": "1080p",
          "medias": [{"role": "video_references", "value": "job_src02"}, {"role": "image_references", "value": "job_prod1"}]}
    d_ = decide("mcp__Higgsfield-Second__generate_video", {"params": c2})
    assert d_["decision"] == "ask" and "Genjutsu (full)" in d_["reason"] and "spends credits" in d_["reason"] \
        and "object swap" in d_["reason"], d_
    d_ = decide("mcp__Higgsfield-Second__generate_video", {"params": {**c2, "use_free_gens": True}})
    assert d_["decision"] == "deny" and "free_gens: no" in d_["reason"], d_
    # Genjutsu LITE object swap (Kling 4.0) offers 720p/1080p only: a 480p call against its 1080p spec is refused
    g3 = g2.replace("shot: B2", "shot: B3").replace("model: hf_mult_replace_object", "model: hf_mult_replace_object_flash") \
        .replace("free_gens: no", "free_gens: prefer")
    gp3 = os.path.join(pdir, "B3.genjutsu.prompt.md")
    _gl(g3, gp3)
    with open(apv, "a") as fh:
        fh.write(f"| t | genjutsu:B3 | Dana | Include Genjutsu | 01-script/prompts/B3.genjutsu.prompt.md | "
                 f"{sha256_file(gp3)[:16]} | | UNVERIFIED |\n")
    c3 = {**c2, "model": "hf_mult_replace_object_flash", "use_free_gens": True}
    assert decide("mcp__Higgsfield-Second__generate_video", {"params": c3})["decision"] == "ask"
    d_ = decide("mcp__Higgsfield-Second__generate_video", {"params": {**c3, "resolution": "480p"}})
    assert d_["decision"] == "deny" and "resolution 480p ≠" in d_["reason"], d_
    open(gp3, "w", encoding="utf-8").write(g3.replace("resolution: 1080p", "resolution: 480p"))
    r3 = PL.lint(gp3, job)
    assert not r3["ok"] and any("is not one hf_mult_replace_object_flash offers" in f for f in r3["fails"]), r3["fails"]
    # a batch with one bad Genjutsu request refuses the batch
    d_ = decide("mcp__Higgsfield-Second__generate_video_batch", {"requests": [{"params": c2}, {"params": {**c2, "resolution": "480p"}}]})
    assert d_["decision"] == "deny" and "request[1]" in d_["reason"], d_
    # Higgsfield's legacy motion_control stays denied, and now names the Genjutsu lane
    d_ = decide("mcp__Higgsfield-Second__motion_control", {"params": {"image_id": "a", "motion_video_id": "b"}})
    assert d_["decision"] == "deny" and "genjutsu.prompt.md" in d_["reason"], d_
    for f_ in ("B1.genjutsu.prompt.md", "B1.genjutsu.prompt.ok", "B2.genjutsu.prompt.md", "B2.genjutsu.prompt.ok",
               "B3.genjutsu.prompt.md", "B3.genjutsu.prompt.ok"):
        if os.path.exists(os.path.join(pdir, f_)):
            os.remove(os.path.join(pdir, f_))
    print("  v2.46.1 OK — Genjutsu full and Lite, motion and swap, both server names: no spec / no approval / every "
          "differing field (resolution, params, video, references, prompt, model, count) / an edited spec / the free switch "
          "off Genjutsu / a different driving video under the same name / a Lite swap at 480p refused; the matching call asks and "
          "says free or paid; the duplicate guard; a probe passes")


def cmd_where(_a) -> int:
    """Where this install is — the one to run (a supplement ad job: the plugin moved under the session)."""
    print(f"scripts  {HERE}\nskill    {SKILL_ROOT}\nclients  {CLIENTS}\nstate    {CINE_HOME}")
    job, why = active_job()
    print(f"job      {job.path if job else '(none: ' + why + ')'}")
    return 0


# ---- PRE-LOCK: the three renders the lock checks read, queued at once, and what is left ------------------------------
# ⚡ a supplement ad job (2026-10-28): "Lock needs a cut render, and the steps aren't laid out. Before lock, the gate wants a
# joins report, title QA (titles on/off renders) and a muted read. Add one `pre-lock` command that queues the three
# renders and lists what's left." Each render is a filled copy of render-mp4.py (it QUEUES; a person presses Render),
# so one `gate.py allow resolve --scope render --scripts 3` covers the three scripts with one approval.
PRELOCK_RENDERS = (
    ("cut", "07-edit", "cut", {},
     "the cut: motion_qa.py measures its joins; it is also the titles-on half of title_qa.py native"),
    ("titles-off", os.path.join("09-qa", "titles"), "titles-off", {"TITLES_OFF": True},
     "the titles-off half of title_qa.py native (after lock, for `approve titles`)"),
    ("picture-only", os.path.join("09-qa", "soundoff"), "picture-only", {"PICTURE_ONLY": True},
     "the T2 proof: the picture alone, no audio, no captions — soundoff.py proofs, then a cold read"),
)


def _fill_config(src: str, values: dict) -> str:
    """render-mp4.py with its CONFIG lines set. Every key must exist exactly once: a renamed setting fails loudly."""
    for k, v in values.items():
        rx = re.compile(rf"^({re.escape(k)}\s*=\s*)([^#\n]*?)(\s*#.*)?$", re.M)
        if len(rx.findall(src)) != 1:
            raise ValueError(f"render-mp4.py has no single `{k} =` line to set")
        src = rx.sub(lambda m: f"{k} = {v!r}" + (("   " + m.group(3).strip()) if m.group(3) else ""), src, count=1)
    return src


def _prelock_version(job, slug: str) -> int:
    seen = [0]
    for _k, folder, _s, _t, _w in PRELOCK_RENDERS:
        d = os.path.join(job.path, folder)
        for f in (os.listdir(d) if os.path.isdir(d) else []):
            m = re.match(rf"{re.escape(slug)}-v(\d+)-", f)
            if m:
                seen.append(int(m.group(1)))
    return max(seen) + 1


def prelock_left(job) -> list:
    """[(check, ok, [lines])] — what `approve lock` will read, in its order, without approving anything."""
    out = []
    qa = os.path.join(job.path, "09-qa", "QA-LOG.md")
    ok = os.path.isfile(qa) and len(read(qa).splitlines()) >= 3
    out.append(("QA log", ok, [] if ok else ["09-qa/QA-LOG.md with real verdicts (qa_log.py)"]))
    for name, fn in (("motion and joins", lambda: __import__("motion_qa").check_job(job.path)),
                     ("title card", lambda: __import__("title_card").check_card(job.path)),
                     ("aerials", lambda: __import__("aerial_qa").check_job(job.path)[0]
                      + __import__("flyover").check_job(job.path)[0])):
        try:
            p = fn()
        except Exception as e:                        # noqa: BLE001  a broken checker is reported, never passed
            p = [f"the check could not run ({e})"]
        out.append((name, not p, list(p)))
    try:
        sp, sw = __import__("soundoff").lock_check(job.path)
    except Exception as e:                            # noqa: BLE001
        sp, sw = [f"the check could not run ({e})"], []
    out.append(("sound-off read", not sp, list(sp) + [f"(note) {w}" for w in sw]))
    try:
        tp = __import__("title_card").check_job(job.path)
    except Exception as e:                            # noqa: BLE001
        tp = [f"the check could not run ({e})"]
    out.append(("titles (after lock)", not tp, list(tp)))
    return out


def cmd_prelock(a) -> int:
    job, why = active_job()
    if not job:
        print(f"no active job ({why}) — `gate.py open <job-dir>`", file=sys.stderr); return 1
    job.validate()
    if job.is_stills():
        print("a stills job has no cut to lock", file=sys.stderr); return 1
    slug = (job.fields.get("job") or os.path.basename(job.path)).strip()
    preset = job.fields.get("_preset")
    fmt = formats().get(preset or "", {})
    if not fmt or not fmt.get("width"):
        print(f"REFUSED: the CHECKPOINT `Format:` names no video preset ({preset!r}) — the renders take their size "
              f"from it, never from a guess", file=sys.stderr)
        return 1
    m = re.search(r"(\d{2}(?:\.\d+)?)\s*fps", job.fields.get("format") or "", re.I)
    fps = float(m.group(1)) if m else fmt.get("fps_default")
    fps = int(fps) if fps and float(fps).is_integer() else fps
    host = (a.host_job or job.path).rstrip("/\\")
    n = a.version or _prelock_version(job, slug)
    src = read(os.path.join(HERE, "render-mp4.py"))
    qdir = os.path.join(job.path, "07-edit", "_queue")
    written = []
    print(f"PRE-LOCK {slug} · v{n} · {preset} {fmt['width']}x{fmt['height']} @ {fps} fps")
    if host.startswith("/sessions/") and not a.host_job:
        print("  ⚠ this path is a VM mount — Resolve on the Mac cannot see it. Pass --host-job <the job's path on the "
              "Mac> (get_device_info lists the connected folders)")
    for key, folder, suffix, toggles, purpose in PRELOCK_RENDERS:
        vals = {"OUTPUT_FOLDER": f"{host}/{folder.replace(os.sep, '/')}",
                "OUTPUT_FILENAME": f"{slug}-v{n}-{suffix}",
                "TIMELINE_NAME": a.timeline, "WIDTH": fmt["width"], "HEIGHT": fmt["height"], "FPS": fps,
                **toggles}
        try:
            body = _fill_config(src, vals)
        except ValueError as e:
            print(f"REFUSED: {e}", file=sys.stderr); return 1
        fp = os.path.join(qdir, f"render-{key}.py")
        if a.write:
            os.makedirs(qdir, exist_ok=True)
            os.makedirs(os.path.join(job.path, folder), exist_ok=True)
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(f"# pre-lock render {key} for {slug} v{n}, written by gate.py pre-lock {now()}\n" + body)
            written.append(fp)
        print(f"  {'queued' if a.write else 'would write'} {os.path.relpath(fp, job.path)} → "
              f"{folder.replace(os.sep, '/')}/{slug}-v{n}-{suffix}.mp4 — {purpose}")
    if a.write:
        print(f"  run the three as `run_script` scripts (one approval for all: `gate.py allow resolve --scope render "
              f"--scripts 3`), then press Render on the Deliver page; check each file exists and has a size")
    else:
        print("  (dry run — `gate.py pre-lock --write` writes them)")
    print("  then: motion_qa.py cut <the cut> … · soundoff.py proofs <job> · title_qa.py native --with <cut> "
          "--without <titles-off> (after lock)")
    left = prelock_left(job)
    print("LEFT BEFORE `approve lock`:")
    for name, ok, lines in left:
        print(f"  {'✓' if ok else '✗'} {name}" + ("" if ok else f" ({len([l for l in lines if not l.startswith('(note)')])})"))
        for ln in lines[:a.max]:
            print(f"      - {ln}")
        if len(lines) > a.max:
            print(f"      … {len(lines) - a.max} more")
    blocking = [n_ for n_, ok, _l in left if not ok and not n_.startswith("titles")]
    if a.json:
        print(json.dumps({"version": n, "written": written, "left": [{"check": n_, "ok": ok, "lines": l}
                                                                     for n_, ok, l in left]}, ensure_ascii=False))
    return 1 if blocking else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--session", help="(3.1) this Claude session's id (SessionStart prints it); needed when two are live")
    sub = ap.add_subparsers(dest="cmd")
    o = sub.add_parser("open"); o.add_argument("job_dir")
    s = sub.add_parser("status"); s.add_argument("--json", action="store_true")
    s.add_argument("--full", action="store_true", help="re-lint every prompt and re-hash every media file (slow on a "
                   "big job); the default checks by hash and a size/mtime cache")
    sub.add_parser("where", help="the scripts, skill, clients and state folders of THIS install")
    pl_ = sub.add_parser("pre-lock", help="queue the cut, titles-off and picture-only renders (render-mp4.py copies) "
                         "and list what `approve lock` still needs")
    pl_.add_argument("--write", action="store_true", help="write the three filled render-mp4.py copies to 07-edit/_queue/")
    pl_.add_argument("--host-job", help="the job's path on the machine Resolve runs on, when this runs in a VM")
    pl_.add_argument("--timeline", help="the timeline to render (default: the one open in Resolve)")
    pl_.add_argument("--version", type=int, help="the version number in the file names (default: the next free one)")
    pl_.add_argument("--max", type=int, default=6, help="lines shown per check")
    pl_.add_argument("--json", action="store_true")
    apv = sub.add_parser("approve"); apv.add_argument("stage"); apv.add_argument("--by", required=True)
    apv.add_argument("--pack", help="(3.1) the review pack's code, when a pack was made for this stage")
    apv.add_argument("--quote", required=True); apv.add_argument("--artifact"); apv.add_argument("--media-id")
    apv.add_argument("--media-ids", help="approve family:<FAMILY>: SHOT=media_id,SHOT=media_id — the "
                     "members the contact sheet approves")
    apv.add_argument("--allow", action="append", default=[],
                     help="a phrase the client has approved IN WRITING (repeatable). It is recorded "
                          "on the video's ledger record with your name — an --allow with no paper "
                          "trail is how an unapproved claim ships.")
    apv.add_argument("--paid", action="store_true",
                     help="approve script: someone on this script is paid, gifted, commissioned or "
                          "employed by the brand (the normal case for UGC). Turns the "
                          "material-connection disclosure check on.")
    apv.add_argument("--no-material-connection", action="store_true",
                     help="approve script: record that nobody is. One of these two is true, and a "
                          "run that answers neither reports NOT ASSERTED.")
    pf = sub.add_parser("preflight"); pf.add_argument("shot")
    pf.add_argument("--kind", choices=["frame", "clip", "edit", "genjutsu"], required=True); pf.add_argument("--json", action="store_true")
    pv = sub.add_parser("previz", help="the capped development-stage concept-art lane")
    pv.add_argument("--budget", type=int, help=f"images allowed, 1..{PREVIZ_MAX}")
    pv.add_argument("--why", help="which decision seeing them unblocks, in your own words")
    pv.add_argument("--by", help="who asked for it")
    pv.add_argument("--status", action="store_true")
    al_ = sub.add_parser("allow", help="one approval that covers a batch of shots and their regens, or a session's "
                                       "Resolve scripts (`allow resolve`)")
    al_.add_argument("kind", nargs="?", choices=sorted(ALLOW_KINDS) + ["resolve"])
    al_.add_argument("--scope", help="resolve: " + ", ".join(RESOLVE_SCOPES) + " (default edit,render)")
    al_.add_argument("--scripts", type=int, help=f"resolve: how many scripts (default {RESOLVE_ALLOW_DEFAULT['scripts']})")
    al_.add_argument("--hours", type=float, help=f"resolve: for how long (default {RESOLVE_ALLOW_DEFAULT['hours']} h)")
    al_.add_argument("--shots", help="S1,S2 or S1-S10, or `all` (every linted prompt of that kind now)")
    al_.add_argument("--regens", type=int, help=f"regens per shot on top of the first (default: the studio's default_regens, else {ALLOW_REGENS})")
    al_.add_argument("--by"); al_.add_argument("--quote")
    al_.add_argument("--revoke", help="an allowance id (A1), or `all`")
    al_.add_argument("--list", action="store_true")
    sub.add_parser("hook"); sub.add_parser("session"); sub.add_parser("close")
    cn_ = sub.add_parser("connectors", help="name your Higgsfield connector's uuid (and other services' uuids); list them")
    cn_.add_argument("--higgsfield", nargs="*", help="uuid(s) of your claude.ai Higgsfield connector")
    cn_.add_argument("--other", nargs="*", help="uuid(s) of other claude.ai connectors (e.g. Figma) the gate should let through")
    cn_.add_argument("--quote", help="the owner's words, needed to move a uuid out of --higgsfield (v2.61.0)")
    cn_.add_argument("--seen", action="store_true", help="(3.0.0) also list unnamed connectors the gate asked about")
    ph_ = sub.add_parser("posthook", help="PostToolUse: record a generate request the vendor accepted (the duplicate-spend guard)")
    ph_.add_argument("--failed", action="store_true", help="PostToolUseFailure: the call failed or timed out; record it as "
                                                           "unconfirmed so an identical retry asks first (v2.70.0)")
    rc = sub.add_parser("reconcile"); rc.add_argument("transactions", nargs="?"); rc.add_argument("--job-dir")
    rc.add_argument("--files", action="store_true",
                    help="match every media file in the generated lanes to a pull or log-external row by hash")
    rt = sub.add_parser("release-take", help="(v2.72.0) release an evaluation reservation whose call never ran")
    rt.add_argument("--id", help="the reservation (R1, R2 …); default the newest unreleased one")
    rt.add_argument("--why", required=True, help="what happened to the call")
    rt.add_argument("--by", required=True, help="who declined it"); rt.add_argument("--quote", required=True,
                                                                              help="their words, verbatim")
    le = sub.add_parser("log-external", help="record media made outside the gate (a website free "
                        "generation, a recording, a derived file) — a row with its hash")
    le.add_argument("file"); le.add_argument("--by", required=True)
    le.add_argument("--source", choices=EXTERNAL_SOURCES, required=True)
    le.add_argument("--model"); le.add_argument("--res"); le.add_argument("--seconds")
    le.add_argument("--credits", default="0", help="credits it cost (0 for a free generation)")
    le.add_argument("--frame", help="the approved frame:<SHOT> it started from")
    le.add_argument("--no-frame", help="why it had no start frame")
    le.add_argument("--note")
    a = ap.parse_args()
    global CLI_SESSION
    CLI_SESSION = a.session or os.environ.get("CINE_SESSION") or None
    if not a.selftest:
        _cine_home.merge_now()          # (3.0.0) once: an open job survives the rename (never when CINE_HOME is set)
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    return {"open": cmd_open, "status": cmd_status, "approve": cmd_approve, "preflight": cmd_preflight,
            "hook": cmd_hook, "posthook": cmd_posthook, "session": cmd_session, "reconcile": cmd_reconcile, "close": cmd_close, "log-external": cmd_log_external, "release-take": cmd_release_take,
            "previz": cmd_previz, "allow": cmd_allow, "where": cmd_where, "pre-lock": cmd_prelock,
            "connectors": cmd_connectors}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
