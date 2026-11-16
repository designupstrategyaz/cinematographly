# Review and approval — getting a "yes" that means something

**When to read this:** a cut is going to a client, you are setting up the review platform for a new
account, or you are deciding whether feedback is a fix, a new round, or a change order. This is the
layer between "the file is done" and "the client has signed off" — the stage most likely to eat a
week of unbilled time.

Facts below are tiered per `research-quality.md`, checked **2026-08-28**. Platform behaviour and
pricing decay fast; re-verify anything older than a quarter before quoting it to a client.

---

## 1. The governing rule

**A review round is a production stage with a cost, not a courtesy.** It gets scoped in the batch
plan, bounded in the contract, and logged like any other milestone (`pm-workflow.md`). The two gates
are already defined there — the **script/storyboard gate** (cheap changes) and the **cut gate**
(expensive changes). This file is about how the cut gate actually runs.

Round discipline, unchanged from `pm-workflow.md` and restated because the platform makes it easy to
forget: notes come back **timecode-referenced, one round**. Round two is scoped to round one's items.
Round three is a change order. A comment that arrives after sign-off is a new job, priced.

---

## 2. Approval — a real status field on one platform, a convention on the other

> **The skill's own record of an approval is `00-brief/APPROVALS.md`, written by `gate.py approve
> <stage> --by <name> --quote "<their reply verbatim>" --artifact <file>`** (2026-09-06). Whatever
> the platform below gives you — a Replay status, a top-level `APPROVED` comment on Frame.io, a
> line in chat — the quote and the file hash land there, and the gate refuses the next stage
> without them. The platform is where the client approves; the ledger is what production reads.
> **The chain is ordered** — `concept → script → cast/frame → audio → clips → music → lock → titles →
> export` — and `approve` refuses out of order. ⛔ **`lock` is picture lock**: it needs the clips
> approved, a real `09-qa/QA-LOG.md`, the motion analysis and the project's title card, and mix, grade,
> captions and titles happen after it; `titles` is signed once every title the card permits passes
> `title_qa.py` on the composite (`typography-and-captions.md` §6c). The
> earliest and cheapest of these is `concept`: the client choosing between five real options costs
> one conversation and saves the whole pipeline.

**Dropbox Replay has a genuine approval status. Frame.io does not.** That asymmetry decides more than
it looks like it should, so both cases are written out.

**Replay: `Needs review` / `In progress` / `Approved`** — a machine-readable file attribute, not a
label written in a comment. The project download dialog filters to **"Only files with 'Approved'
status"** (so month-end delivery of a client's approved cuts is one action), and status changes are
their own email-notification category [PRIMARY · help.dropbox.com — Replay projects, Replay settings].
**The catch: only signed-in Dropbox users can set it.** Dropbox staff, answering a producer whose
client reviewed by link: *"only logged in users can change the status of a video"* [PRIMARY · Dropbox
Community 630337] — in that same thread the client could comment without an account perfectly well.
There is also one unresolved report of the status control disappearing for external viewers
altogether, with no confirmed fix [PRIMARY · Community 859194]. Whether a **free** Dropbox Basic
account is enough to press Approved is [UNVERIFIED]. So: get each client contact a login and you have
a real approval artifact; if they refuse, you are back to the convention below — with the extra
annoyance that they can see a button they cannot press.

**Frame.io has no approval action.** Confirmed from two independent primary sources:

- The V4 API has no approval status. `GET /v4/accounts/{id}/files/{id}/status` returns an enum of
  `created` / `transcoded` / `uploaded` — that is *transcode* state, not review state. No
  Needs-Review/Approved enum exists anywhere in the spec. [PRIMARY · api.frame.io/v4/openapi.json]
- The reviewer UI offers threaded comments, emoji reactions and a **Mark As Complete** button —
  no approve control on a share link. [PRIMARY · help.frame.io 9105278, 9105232]
  (An Approve / Needs Work decision exists only in the Frame.io viewer embedded in **Adobe
  Workfront** — enterprise stack, not a Pro/Team share link. [PRIMARY · help.frame.io 14543173])

So on Frame.io — and on Replay whenever the approver will not sign in — sign-off is whatever you
write into the contract. The house convention:

> **Approval is a top-level comment reading `APPROVED` on the latest version, from a named
> reviewer.** Not a reply. Not an emoji. Not a "looks great!" in WhatsApp.

"Not a reply" is not fussiness — **replies do not appear in Frame.io's filtering, sorting or search
results** [PRIMARY · help.frame.io 9105278], so an approval buried in a reply thread is invisible to
every mechanism you would use to find it later, including the comment export that becomes your
record. The same export is the evidence: filter to the asset, export, file it in `09-qa/review/`.
This is the same enforcement principle as the QA log — **a sign-off you cannot produce on demand did
not happen** (`realism-qa.md` §6).

Silence is not approval. The silence rule in `pm-workflow.md` (a stated deadline, then proceed on the
last approved version) governs, and it only works if "last approved version" is a thing you can point
at.

### 2a. Before a cut goes out: the event sheet and the draft loop (v2.46)

The owner's standing rule is that every video draft gets a contact sheet, read, before anyone sees the
clip. Until v2.46 nothing made that sheet for an assembled cut, so the read happened on whatever frames
were to hand. The adopted method (from two open-source animation skills' review loops, in our own
tools) makes the sheet from the cut's own events and keeps reading until a pass is clean.

1. **Make the sheet of the render.** `contact_sheet.py events --project <job> --cut <render>` puts one
   tile on the sheet for every event the job already records: POSTER (frame 0, the thumbnail), each cut
   (C1…, 0.4 s after it), each transition (X1…), each title (its id, just after its entrance lands),
   each must-hit and the button (from `07-edit/music/HITS.json`), each placed sound (FX1…) and END. A transition can be
   scrubbed with `--scrub A B --every 0.2`. The sheet is named for the render's hash.
2. **Read every tile against its question.** POSTER: does frame 0 show the subject? A cut: has the
   incoming head settled, with no flash frame and the eyeline held? A title: has it landed inside the
   safe box, off the face and the product, legible at phone size? A hit or a sound: is the thing it marks
   in the frame? END: does the end card hold?
3. **Log what you saw, tile by tile.** `qa_log.py --gate draft --render <render> --sheet <sheet>`:
   one RETAKE row per finding (it gets an id, D1, D2 …), naming the tiles. A row about another render's
   sheet is refused.
4. **Fix, re-render, make a new sheet.** A fix is logged FIXED `--fixes Dn` against the new render's
   sheet. The tool refuses a FIXED that cites the render the finding was made on: a fix nobody rendered
   is not a fix.
5. **Stop on a clean pass, or after three rounds.** A PASS cites at least two tiles and is refused while
   any finding is open. After the third render read since the last PASS, the loop stops and the cut goes
   to the director with its open findings named, rather than a fourth round alone.

`qa_log.py --gate draft --check --render <the file you are about to send>` says whether that exact file
has a draft PASS. **Open question Q4 (the owner's): should a missing draft PASS block a cut from going
to the client, or only warn?** Until it is answered the check warns and exits 0 (`--strict` exits 1),
and `gate.py` does not enforce it. Run the same sheet on the export in `10-export/` as well: it shows
what the encoder wrote, not what the timeline held. `mix_qa.py wave` is the sound side of the same read.

The event sheet reads a cut in time. The **scene board** (§11, v2.49) reads the shots of one scene across each
other — lens, height, size, distances, props, wardrobe, light — and it comes first: before any approval request.

---

## 3. Choosing the platform — a client × setup decision, not a house default

Do not hardcode one tool. The right choice depends on who reviews, how polished the client-facing
surface must be, and — decisively for this operation — **whether comments need to land back on a
Resolve timeline**.

| Platform | Price (checked 2026-08-28) | Wins when | Loses on |
|---|---|---|---|
| **Frame.io Free** | $0 · 2 members · **2 projects** · 2GB | Trying it; a single client | 2-project cap is reached the moment you have 3 live accounts; no passphrase/expiry/watermark |
| **Frame.io Pro** | **$15**/user/mo | Client-facing polish: branded shares, passphrase, expiry, download-off, 1 watermark template, unlimited projects, 2TB | **No Resolve integration in V4** (§5) |
| **Frame.io Team** | **$25**/user/mo | Internal comments, restricted folders, comparison viewer | Price, for a solo shop |
| **Dropbox Replay** | **$10**/user/mo annual ($12 monthly), needs Dropbox Plus+ | **The only bidirectional Resolve Studio comment round-trip** (delete in Resolve, it deletes in Replay) · **a real Approved status** · password, watermark with per-viewer IP/date tracking, due date, side-by-side compare (all Add-On; collaborators inherit compare from your seat) | **No API and no webhooks at all** — Dropbox staff, twice · approval needs the client signed in · Resolve-side comment import only from the *current* version · files **cannot be moved between projects** (re-upload loses every comment) · no mobile app · 1080p playback ceiling |
| **Blackmagic Cloud Presentations** | Blackmagic ID **free**; Presentations bought as a quantity in a Cloud Organization — ⛔ **price not published on any Blackmagic page**, it is behind the login. Cloud storage **$15/TB/mo** [PRIMARY · BMD release 2024-11-26]; project libraries "a nominal monthly fee" with no figure [PRIMARY · R21 manual p. 4253] | **The best round trip of the three, and near-free**: markers sync automatically both ways, no export step at all (§5b) | **Beta since Resolve 18.5 — three years and five months** · **max 10 reviewers, every one needs a Blackmagic ID** · no approval status · no version stacking · **no public link** at all |
| **ClickUp Proofing** | included in existing plan (Business $12/user/mo annual; Free/Unlimited capped at 100 proofing uses) | Review lives *in the task* with the brief, hook copy and deadline; guests can proof; timestamped comments with replies + resolve | No version stacking, no side-by-side compare, no branded share page, no watermark; reviewer must tolerate a PM UI |
| **Vimeo Starter** | **$12**/seat/mo | Cheapest real review page with comment export; doubles as hosting | Not a production review tool |

All prices [PRIMARY · each vendor's own pricing page].

**When Frame.io earns its $15** — when **two or more** of these are true at once:

1. More than **2 concurrent client projects** (the Free cap — at 30–50 ads/month across several
   clients you are already past it, so Free is not a landing spot).
2. Clients ask to see **v1 against v3** — version stacking plus the show-all-versions share toggle,
   which ClickUp proofing does not do.
3. A client's brand team circulates the link internally and you need **branded, passphrase-protected,
   expiring** shares.
4. You batch **one share link per weekly drop of 8–12 hook variants** rather than one link per file.

**The honest counter-case**, and it must be said before spending: for a shop that edits in Resolve
and already pays for ClickUp, the comment round-trip is worth more per month than a branded share
page. **Dropbox Replay ($10) returns comments to your timeline; Frame.io V4 does not.** If only
criterion 1 is true, Replay or ClickUp proofing is the better buy, and Frame.io is the right answer
mainly when a client asks for it by name — which is a perfectly good reason on its own.

**The trade, stated plainly, because the two products fail in opposite directions:**

> **Replay gives you the approval button and the Resolve round-trip, and no automation whatsoever.**
> **Frame.io gives you the API and webhooks, and no approval and no Resolve integration.**

Neither is a compromise position — pick by which half you actually need. If review has to talk to
ClickUp (a link created on a status change, comments pulled onto a task, approval read
programmatically), Replay cannot do any of it: **there is no Replay API and no webhooks**, confirmed
by Dropbox staff on two separate requests describing exactly this use case [PRIMARY · Dropbox
Community 690600, 755273], and the only Replay token in the Dropbox SDK is a read-only team
audit-log event. If instead the win is that the client presses Approved and your timeline fills with
their markers, Replay is the one, and the automation you give up is automation Frame.io may not even
sell you (§6). Both lanes are written out below; run one, not half of each.

---

## 4. Frame.io in practice — the shape that survives 30–50 assets a month

- **Hierarchy:** Account → Workspace → Project → Folder → File / Version Stack. Free, Pro and Team
  all get exactly **one workspace**; only Enterprise gets more [PRIMARY · frame.io/pricing]. So the
  organising cut is **one project per client**, folders per month or per batch.
- **One persistent share link per client per drop.** Sharing a folder shares everything inside and
  **updates dynamically as you add or remove files** [PRIMARY · help.frame.io 9105232] — so the link
  you sent Monday shows Thursday's new hook variants without re-sending. **Grid layout** presents the
  variants side by side; card aspect ratio is settable to vertical, which is what you want for 9:16.
- **Version stacks:** drop the new cut on the original; newest opens by default, older versions
  reachable from the version number. The **share setting decides whether the client sees history at
  all** ("show all versions or just the latest") [PRIMARY · 9101068, 9105232]. Default to latest-only
  for clients who spiral when they can compare; show all when the note was "go back to how v1 opened".
- **Collections** are saved live metadata queries that group assets across folders without moving
  them [PRIMARY · 9101042] — the natural home for a "winners" view feeding the hook bank.
- **Guest reviewers are free and need no account.** They are prompted for name and email on their
  first comment, can annotate and leave timecoded notes, and download only if you enabled it. The
  trap: **an unauthenticated reviewer who leaves the session cannot edit their earlier comments**
  [PRIMARY · 9105242]. Tell clients to finish a pass in one sitting.
- **Notification noise is structurally low for clients**: reviewers get a fixed 15-minute digest, and
  only for assets they have already commented on [PRIMARY · 13181549].
- **Share Activity** logs opens, views, comments and downloads — the evidence when a client says they
  never saw the cut [PRIMARY · 9105232].
- **File naming carries the join key.** The ad-name key from `performance-metrics.md` §2
  (`<BRAND>-<bodyID>-<hookID>-<personaID>-<variant>`) is the Frame.io file name too, so an approval,
  a shot manifest row, a hook-bank row and a platform metrics row all name the same object. Approval
  that cannot be tied to a variant ID is not usable at volume.

---

## 4b. Dropbox Replay in practice — the shape that survives 30–50 assets a month

- **Versions stack properly.** v2 replaces v1 inside one file; the newest opens; older ones sit in a
  Versions dropdown. 40 ads at 3 versions each is **40 objects, not 120** [PRIMARY · Dropbox staff,
  Community 769585]. With **Hide past versions** on the link, one durable link per ad and the client
  never sees the rejected cut. Unresolved comments carry forward across versions.
- **Side-by-side compare** (Add-On) locks playback across both versions and auto-swaps the audio to
  whichever side is unmuted — and **collaborators inherit compare from your seat**, so the client
  gets it without paying [PRIMARY · help.dropbox.com — compare video versions].
- **Reviewers need no account to comment**: timestamped notes, **range comments via Shift+drag**,
  freehand drawing on frames, replies, resolve, reactions [PRIMARY · help.dropbox.com — Replay
  feedback; corroborated by a field report in Community 630337]. One Dropbox staff answer elsewhere
  contradicts this — it appears to concern ordinary Dropbox file comments, not Replay — so
  **test it with a signed-out browser profile before you promise a client anything**. Whether an
  anonymous reviewer is prompted for a name (and therefore how their comments are attributed) is
  [UNVERIFIED], which matters when several stakeholders review at once.
- **Link controls:** password, due date and watermark are **Add-On**; disable downloads, require
  login and the link kill-switch are free. The watermark can be a **per-email link that records the
  IP, date and time of each view** — the strongest leak-tracing of any option here. **No link
  expiry is documented anywhere** [UNVERIFIED], which is a real gap against Frame.io Pro.
- ⛔ **Files cannot be moved between projects. At all.** Dropbox staff, accepted answer: once a file
  is in a project there is no way to move it out or across, and the only remedy is re-upload —
  *"loosing all the comments in the proces"* [PRIMARY · Community 599784], including any Approved
  status. At 30–50 assets a month across several clients, misfiling is a weekly certainty and here it
  is **unrecoverable**. Per-client structure must be right on the first upload, every time.
- ⛔ **The storage trap that fights the Resolve integration.** Files added to Replay **from your
  Dropbox** do not count against your plan storage. Files added **from third-party editing software**
  — which is exactly what the Resolve Deliver-page upload is — count against **both** your Replay
  allowance and your Dropbox plan quota [PRIMARY · help.dropbox.com — Replay FAQ]. The convenient path
  is the expensive one. Render into your Dropbox folder, then add to Replay *from Dropbox*.
- Without the Add-On you are capped at **4 files** (Plus); the Add-On removes the cap. Per-file
  ceilings (150GB / 12 hours) are irrelevant at this length.
- **"Share link views" notifications** tell you when the client actually opened the cut — it kills
  the "did you see it?" chase, and it is the evidence equivalent of Frame.io's Share Activity.
- **No mobile app** — review on a phone is mobile web only, and an open feature request for one sits
  unanswered [PRIMARY · Community 842847]. Playback tops out at **1080p with manual quality
  selection**; Dropbox staff confirm there is no auto mode [PRIMARY · Community 749034]. Clients
  review vertical ads on phones, so this is the weakest point of the product for this exact use case.
- **Nothing documents how Replay handles 9:16** — no page, thread or credible third party addresses
  portrait display or letterboxing [UNVERIFIED]. Upload one real ad and open it on a phone before
  committing. That single test also settles the no-account-commenting question above.

---

### 4c. The sound-off pack goes in the stack

The client's quickest check is to mute the cut. Put `soundoff.py pack`'s folder beside the final — the
picture-only proof first, the muted files, then the appendix — so they run it on our proofs, unprimed
(`sound-off-story.md` §6).

## 5. The Resolve bridge — what actually works today

**The native integration is dead for new accounts — and as of Resolve 21 it is gone from the
application entirely (§5b).** Resolve's Deliver-page Frame.io preset with
automatic comment→marker sync was real and good: comments, replies and annotations synced to the
timeline as a distinct Frame.io marker type [PRIMARY · DaVinci Resolve 18.6 manual]. But Frame.io
scopes it to **Resolve 16/17 Studio, V3 only**, files it under Legacy, and warns there have been no
recent updates from Blackmagic [PRIMARY · help.frame.io 2883263]. The V4 integration list names
Premiere Pro and Final Cut Pro X — **not Resolve** [PRIMARY · help.frame.io 9084073]. V3 accounts
were force-migrated [PRIMARY · Frame.io developer forum]. A 2026 signup is V4; assume browser upload
and no native sync. [The Blackmagic forum threads that would confirm Resolve 19/20 behaviour returned
403 and were not worked around — so "the preset errors vs silently fails on V4" is UNVERIFIED.]

**The V4 path that works** — comment export → EDL → timeline markers:

1. In the Frame.io comments panel, **filter to the asset** (only what is visible after filtering gets
   exported), then export from the three-dot menu — **CSV** [PRIMARY · 9105278, 9105309].
2. Convert CSV → EDL. Two options: `scripts/frameio_comments_to_edl.py` in this skill (offline, no
   third-party upload of client feedback), or the free web tool **editingtools.io Marker Converter**
   ("Frame.io > Comments (.csv)" → "DaVinci Resolve > Sequence (.edl)") [PRIMARY · editingtools.io].
3. In Resolve: right-click the timeline in the Media Pool → **Timelines > Import > Timeline Markers
   from EDL**.

Two gotchas, both from the vendors' own guidance and both real:

- **Markers must fall inside the timeline's timecode range.** Frame.io comment timecodes are
  file-relative (`00:00:xx:xx`); a Resolve timeline usually starts at `01:00:00:00`. Offset the
  comment timecodes (the script's `--offset`, default `01:00:00:00`) or set the timeline's Starting
  Timecode to match — otherwise the import silently lands nothing.
- **Special characters in marker text can choke the import.** The script strips them by default.

Note the asymmetry with the captions problem (`editing-and-audio.md`): comments come *in* to Resolve
fine, but nothing pushes a rendered cut *out* to Frame.io automatically any more. Upload is manual,
or scripted against the API (§6).

### 5b. Resolve 21 deleted Frame.io. Presentations is what replaced it.

⛔ **Asked directly in Resolve 21: there is no Frame.io preset on the Deliver page.** The evidence is
a manual diff, not an inference. Resolve 20's reference manual carried a dedicated **Chapter 13,
"Frame.io and Dropbox Replay Integration" (pp. 303–311)**, with the preset, the automatic
comment→marker sync, the Media Storage volume and *Link to Frame.io Media*. In the Resolve 21 manual
that chapter **does not exist** — the numbering runs Ch. 12 Data Burn-In → Ch. 13 Resolve Live, and
Dropbox Replay was moved out on its own to Ch. 201 "Workflow Integrations". The Deliver-page preset
list in Ch. 187 reads: YouTube · Vimeo · **TikTok** · **Presentations** · **Dropbox or Dropbox
Replay** · masters · exchange. No Frame.io.
**[PRIMARY · DaVinci Resolve 21 Reference Manual (built 2026-07-09) vs the 20 manual · 2026-09-08]**

⛔ **Blackmagic never announced the removal**, which is why V3-era walkthroughs are still everywhere.
Worse, the R21 manual still contains **residual Frame.io text it forgot to delete** — Preferences →
System → **Internet Accounts** still lists Frame.io (pp. 110–111, 4188), and p. 4328 still says
"FrameIO comment markers are supported by collaborative workflow." The giveaway that this is stale
copy rather than a surviving feature: the *same* Quick Export sentence appears twice in one manual —
p. 4176 says "YouTube, Vimeo, and **Frame.io**", p. 811 says "YouTube, Vimeo, and **Dropbox**".
**Do not design a workflow around a login button whose feature chapter was deleted.** ⚠ Whether that
button still renders and still accepts a V4 login in 21.1 is [UNVERIFIED] — nobody has tested it.

**The Presentations round trip, which is the honest answer to "or Blackmagic Cloud?"**

> "Any markers added by members in Presentations are updated to the timeline in DaVinci Resolve
> **automatically and vice versa**." … "once a timeline has been uploaded to a presentation, it's
> **automatically linked behind the scenes**."
> **[PRIMARY · R21 manual Ch. 193, pp. 4285–4286 · 2026-09-08]**

- **Zero export steps.** No CSV, no EDL, no script. Sync happens when the timeline is open and you
  are signed into Blackmagic Cloud — "markers can be added by members the previous night and will
  then sync when the editor opens the timeline in the morning."
- Presentations markers render **circular** (normal markers are triangular) and carry **the colour
  of the member who wrote them**. Push one out with `Mark > Add Marker > Presentations`.
- ⛔ Deleting a Presentations marker removes it **from both sides** and **is not undoable** — and any
  timeline user can delete any member's marker.
- The publish path: create the presentation **in the browser first** (blackmagicdesign.com →
  Presentations → Add Presentation), then Deliver page → preset **Presentations** → *Upload To* →
  pick it. There are no codec settings: "This setting simply adds the metadata necessary for
  Presentations to share your timeline."
- **21.1 (released 2026-09-08) added subtitle support, annotation sharing and comment replies** to
  Presentations — the only review work in the entire 21 cycle.

**And the four reasons not to make it the pipeline:**

1. ⛔ **"As of this writing, Presentations is still in beta"** — printed three times in the R21
   manual, and it has said that since **Resolve 18.5 in April 2023**. Three years and five months.
2. ⛔ **Ten reviewers, each needing their own Blackmagic ID.** There is **no public link and no
   password option** — only an admin *Presentation enabled* toggle. An ecommerce client's legal or
   brand reviewer will not create a Blackmagic account to leave one comment.
3. ⛔ **No approval status field** anywhere in the chapter — so §2's convention (a top-level
   `APPROVED` comment from a named reviewer) is the only sign-off available, and chat is
   presentation-wide rather than per-clip, and **messages cannot be deleted**.
4. **No version stacking.** Uploads land as separate clips, so `revisions.md`'s "version bump, never
   overwrite" has to live in the file name.

**The recommendation, for 30–50 videos a month:** **Dropbox Replay is still the pipeline** — it is
the only option with a native bidirectional round trip *and* a real Approved status *and* version
stacking, and **reviewers need no account**, which is the constraint that actually decides this at
volume. **Run Presentations as the second channel** for a fast internal or director look where the
ten-seat, account-required ceiling is not a problem, and revisit it as the primary the moment the
beta note leaves the manual. **Use Frame.io only when a client insists on it**, and budget the EDL
shuffle below — roughly a clerical hour a month at this volume.

⚠ **One step in §5 above needs verifying in your build.** `Timelines > Import > Timeline Markers
from EDL` is documented by **Frame.io**, not by Blackmagic: the R21 manual documents marker *export*
to EDL (pp. 4245/4249) and has **no marker-import section at all**. The command very likely still
exists — check it once before designing a round on it. [UNVERIFIED · BMD side · 2026-09-08]

---

### Replay's native path — and the rule that keeps notes from being stranded

Replay still has the integration Frame.io lost: **Resolve Studio only**, connected under
**Preferences → System → Internet Accounts**, uploaded from the **Deliver page's Replay icon**
(distinct from the plain Dropbox icon), with **bidirectional** comment sync — delete a comment in
Resolve and it disappears in Replay, and the reverse [PRIMARY · help.dropbox.com — Replay + DaVinci
Resolve]. That is a genuinely better round-trip than any file bridge.

Three rules make it survive a second round:

1. ⛔ **Import every comment into Resolve BEFORE you render the next version.** Resolve can only pull
   comments from the file's **current version** [PRIMARY · same page]. The moment v2 becomes current,
   any v1 note you never imported is web-UI-only forever — still visible to you and the client,
   permanently unreachable from your timeline. There is no documented workaround; the nearest escape
   is Replay's comment export (CSV / FCP XML / Avid text), and whether that re-imports cleanly as
   markers is [UNVERIFIED].
2. **"Import markers as comments" only sends NEW markers** when you push a new version — old ones do
   not re-sync [PRIMARY · same page].
3. **Do not plan on client drawings reaching your timeline.** Dropbox's blog claims annotations sync;
   the authoritative help article documents comments only and never mentions annotations or marker
   colours. Treat the drawings as web-only until your own test says otherwise [UNVERIFIED].

**The unknown to settle first: no Dropbox page names a supported Resolve version, minimum or
maximum.** The integration shipped alongside Resolve 17.4 in 2021 and there is no primary
confirmation it works on 19 or 20 — and a Blackmagic forum thread titled "Dropbox Replay not showing
markers on DaVinci Resolve 18" exists but returned 403 and was not worked around, so its content is
unknown. **Test the Deliver-page upload on your own Resolve build before this becomes the workflow.**

---

## 6. What is buildable against the API

Only relevant when review is automated — a standing client, not a one-off. Everything here
[PRIMARY · api.frame.io/v4/openapi.json + Adobe developer docs, checked 2026-08-28].

- **Auth is Adobe IMS.** For unattended jobs use **OAuth Server-to-Server (client credentials)**,
  scopes `openid AdobeID frame.s2s.all`. The *credential* is durable; **access tokens expire in ~1
  hour and there is no refresh token** — re-mint per run. (A legacy non-expiring developer token
  exists for not-yet-Admin-Console accounts, requires header
  `x-frameio-legacy-token-auth: true`, and is explicitly transitional — do not build on it.)
- ⛔ **Verify before building anything:** the docs require an account "administered via the Adobe
  Admin Console", and the published pricing table has **no row for API, webhooks or custom actions**
  at any tier. Whether a self-serve Pro/Team account can create a webhook at all is **UNVERIFIED**.
  Confirm with Adobe in writing before a single line of integration code — this is the assumption
  most likely to invalidate the rest of this section.
- **Ingest:** `POST /v4/accounts/{id}/folders/{id}/files/remote_upload` — Frame.io pulls from a URL
  you hand it. For an AI-generation pipeline whose outputs already live at a signed URL this is the
  right call; no chunking code. (`local_upload` returns S3 presigned chunk URLs if you must push.)
- **Versioning:** `POST /v4/accounts/{id}/folders/{id}/version_stacks` with an ordered
  `file_ids: [v1, v2]`. **There is no endpoint to append a third version to an existing stack** —
  an unresolved limitation, not an oversight in the reading. Design around it.
- **Shares:** `POST /v4/accounts/{id}/projects/{id}/shares` with `access` (`public`|`secure`),
  `passphrase`, `expiration`, `downloading_enabled`, `commenting_enabled`, `watermark_enabled`,
  `show_all_asset_versions`, `layout`, `card_aspect_ratio`, `asset_ids`. Every share control in §4 is
  API-settable (subject to the plan gates in §3).
- **Comments read back with annotations:** `GET /v4/accounts/{id}/files/{id}/comments` —
  `timestamp` is `HH:MM:SS:FF`, `annotation` is stringified JSON geometry in normalised 0–1
  coordinates. So a QA pass can read client markup programmatically.
- **Approval status = a custom metadata field.** Create a `select` field definition
  (`POST /v4/accounts/{id}/metadata/field_definitions`), write values in bulk
  (`PATCH /v4/accounts/{id}/projects/{id}/metadata/values`), and subscribe to
  **`metadata.value.updated`** — there is no `status.changed` event because there is no status.
  Custom metadata is available on every plan including Free [PRIMARY · frame.io/pricing].
- **Webhooks** are workspace-scoped, 30 event types (`file.ready`, `file.versioned`,
  `comment.created`, `comment.completed`, `share.viewed`, `metadata.value.updated`, …). Signature is
  HMAC-SHA256 over `v0:timestamp:body`, header `X-Frameio-Signature`, prefix `v0=`; reject timestamps
  older than 5 minutes. **The payload carries only the resource ID — always re-fetch.**
- **Custom actions** put your own menu item on selected assets and **can return a form**
  (`text`, `textarea`, `select`, `boolean`, `link`). Hard limit: **5–10 second timeout** — acknowledge
  immediately, do the work asynchronously.
- **Rate limits** are per endpoint per `account_user`: commonly 100/min reads, 60/min lists, 10/min
  heavier writes, 5/sec on file-create. Whether an S2S service account is one shared bucket is
  **UNVERIFIED** — it decides your throughput ceiling, so measure before promising a batch cadence.

---

## 7. Decide these per client (intake)

Goes in the client profile (`clients/_TEMPLATE.md` §10). Unanswered means NEEDS INPUT, not a guess:

1. **Platform and who pays** — theirs or yours; if theirs, you are a guest and the folder structure is
   not yours to design. On Replay, add: **does the approver have a Dropbox login?** Without one they
   can comment but cannot press Approved, and the main reason to choose Replay evaporates.
2. **Named approver(s)** — one person's `APPROVED` counts. A committee without a named decider is
   the most expensive failure mode in this whole file.
3. **Rounds included**, and the price of a round beyond them.
4. **Turnaround SLA** both ways: yours to deliver a fix, theirs to respond before the silence rule
   applies.
5. **Version visibility** — latest-only or full history.
6. **Share controls** — passphrase, expiry, downloads on/off, watermark (Pro+).
7. **Where the record lives** — comment export filed in `09-qa/review/`, decision record in
   `00-brief/DECISIONS-<SLUG>.md`.

---

## 8. Risks to state out loud before adopting

- ⛔ **What happens to assets when a plan lapses, is cancelled or downgraded is UNDOCUMENTED** —
  no retention window, no read-only-vs-delete answer, on any page reachable. **Never let a client
  master exist only in Frame.io.** The archive of record stays in your own folder structure
  (`10-export/`), Frame.io is a review surface. Get the lapse policy in writing before committing.
- **Storage overage can lock the account.** Frame.io warns and, if unresolved "within an allotted
  grace period", the account "may become locked"; the grace period length is not published
  [PRIMARY · help.frame.io 2673548].
- **Watermarking below Enterprise is one static template at a time**; session-based and forensic
  watermarking are Enterprise, and forensic download is not supported in V4 at all [PRIMARY · 9948588].
- **Comparison viewer tier is contradictory** across Frame.io's own pricing page (Team feature) and
  its feature article (no plan restriction) — UNVERIFIED; do not promise it on Pro.
**Replay, the same discipline applied:**

- **Cancellation is only half documented.** You keep access to your files and can edit or remove
  existing link passwords, but cannot add new ones [PRIMARY · Replay FAQ]. What happens to files
  **above the free 4-file cap**, to existing watermarked links, due dates and compare access, and
  what happens if the underlying **Dropbox plan** drops below Plus, is documented nowhere
  [UNVERIFIED]. Same conclusion as Frame.io: the master of record lives in `10-export/`, never only
  in the review tool.
- **The misfile is unrecoverable** (§4b) — no move between projects, re-upload loses all comments.
- **The storage double-count** on Resolve-side uploads (§4b) quietly bills the convenient path.
- **No API, no webhooks** — if the pipeline needs to talk to the board, this is a hard stop, not a
  roadmap item: Dropbox has twice declined to commit [PRIMARY · Community 690600, 755273].

- Reported but old or unconfirmed, listed so nobody re-discovers them as news: client confusion with
  the review UI (2019, pre-V4), a playback-reset bug (2022), slow support (2025) — all [SECONDARY ·
  Capterra reviewers]. **Vertical 9:16 proxy problems: no credible evidence found in either
  direction** — treat as a non-issue until yours says otherwise.

---

## 9. The self-hosted instance (added 2026-08-29)

A self-hosted Frame.io-style review app on the account's own VPS
(`studio.<the studio's domain>`). ⛔ **Fix this before designing anything around it: as of
2026-08-29 that hostname does not resolve — NXDOMAIN from two networks.** If clients are meant to
reach it, nobody currently can. DNS first, procedure second.

### 9.1 Five capabilities decide the procedure — confirm each, do not assume

A clone inherits the *look* of Frame.io, not necessarily its behaviour, and §2 of this file exists
because **Frame.io proper has no approval action while Replay does**. Which one yours resembles
changes the whole sign-off convention.

| # | Question | If yes | If no |
|---|---|---|---|
| 1 | Is there a real **approval status** field? | Use it; §2's status semantics apply | Fall back to §2's convention: a **top-level `APPROVED` comment from a named reviewer**, never a reply |
| 2 | Do **comments export**, and in what shape? | If it emits a Frame.io-shaped CSV, `scripts/frameio_comments_to_edl.py` already converts notes into Resolve markers | Notes get retyped by hand — budget for it, or write an exporter |
| 3 | Is there an **API or webhooks**? | ⛔ **This unblocks a roadmap item.** The API helper was blocked on *"can a self-serve plan use the API at all"* (§6, `scripts/README.md`). On your own server that question is answered by construction | Manual only |
| 4 | **Versioning** — version stacks, or bare uploads? | Keep the "version bump, never overwrite" rule (`revisions.md`) | Enforce it in filenames instead |
| 5 | **Per-client isolation** — can client A see only client A? | Standard project separation | ⛔ Do not put two clients on it until this is true |

### 9.2 What self-hosting buys, and what it costs

**Buys:** no plan-lapse risk — which retires the largest open risk in §8; API access; your own
approval semantics rather than a vendor's; no per-seat cost as a client adds reviewers.

**Costs, and this is the half to take seriously: you are now the sysadmin, the backup operator and
the custodian of client footage.** A vendor outage is their problem at 2am; a VPS outage is yours,
during an approval round, with a client waiting.

⛔ **So the governing rule in §1 gets stronger, not weaker: the master of record is `10-export/`,
never the review platform.** Self-hosting removes the *vendor* risk and replaces it with an
*operational* one you own. Add to the setup: automated backups with a restore you have actually
tested, TLS renewal, a named upgrade path, and a line in the client agreement saying where their
footage physically lives — which may matter for an EU client.

---

## 10. Review at volume — when the client cannot review every video

**The arithmetic decides this, not preference.** At 2–3 videos a day — 40–60 a month — a per-video
round costs the client hours of attention a month *plus* the latency of each round. **Per-video
approval at that cadence is not slow, it is structurally impossible**, and pretending otherwise
produces the worst available outcome: rounds that are nominally required, quietly skipped, and an
approval record that is fiction. An approval record that would not survive a dispute is worse than
an honest standing approval.

⛔ **And reviewing everything is not the quality-maximising choice anyway.** From a different
industry with the same structure — a long, uniform queue inspected by a human:

> *"100% visual inspection by even well-trained and experienced production inspectors has been shown
> to be only about 80–85% effective"*

with 100% inspection described as **"fragile"**, subject to *"many potential sources of error and
poorly controlled variables"*, and sampling performed *afterwards* as a *"sanity check to
demonstrate whether the 100% inspection has had a complete breakdown."*
[SECONDARY · *Pharmaceutical Technology*, "Statistical Solutions: Visual Inspection Goes Viral" ·
checked 2026-08-29 · ⛔ different domain — the transfer is structural, not evidential]

### 10.1 Approve the format, not the output

The tiering is already latent in `series-continuity.md` §3: **what needs approval is a change to an
INVARIANT. A VARIANT ships.** The invariants list *is* the standing approval.

| Tier | What qualifies | Who reviews | Evidence kept |
|---|---|---|---|
| **Standing** | A pure VARIANT under an approved invariants version | **Nobody — it ships** | The registry row + the ship gate (`realism-qa.md` §6b) |
| **Batch** | The day's or week's output as **one playlist**, reviewed as a set | Client, timeboxed, exception comments only | The playlist link + whatever came back |
| **Named** | Changes an INVARIANT · introduces or alters a claim · a new look, character or format · a hero or launch asset · **the first episode under a new invariants version** | Client, per asset | Full §2 sign-off evidence |

⛔ **Compliance overrides the tier.** Anything touching a claim, a disclosure or a regulated term is
**Named**, always, whatever the batch says (`compliance.md`, and `real-and-ai.md` §5 if the video is
hybrid).

### 10.2 ⛔ The review that saves money is the script, not the rough cut

On this pipeline the words are locked before generation, and a wording change *after* generation
cascades **VO → clip regeneration → re-edit → captions** (`revisions.md`). **A client note on a
rough cut is the most expensive note they can give you.** So spend their attention where it is
cheap: a **batched script review** — several scripts at once, on a fixed day — is worth more than
any number of picture rounds, and it is the one review a high-volume client should never skip.

**Rough cuts are therefore internal by default.** At this cadence the rough cut is the producer's
own checkpoint — the `selects`/`edit` gate in `production-runbook.md` — not a client deliverable.
Publish one to the client only for a **Named** asset. That is not corner-cutting: a client buying
2–3 videos a day is buying a *system*, and asking them to referee each assembly asks for a judgement
they cannot make well at that volume.

### 10.3 The deemed-approval clause — put it in the contract, not in the workflow

A timeboxed batch review only works if silence means something, and ⛔ **silence means nothing unless
it was agreed in writing.** Deemed approval is standard, common contract practice; observed windows
run from **5 business days to 90 days**, with **14–15 days** common, and the fair pattern includes:
proper notice to a specified address, complete information supplied with the request, and — the part
worth insisting on — **a two-request procedure: an initial request, then a second written request
carrying a prominent warning, before approval is deemed.** [SECONDARY · Law Insider clause database,
deemed-approval samples · checked 2026-08-29 · ⛔ a clause database is evidence that the clause type
is common, not legal advice — have it drafted]

⛔ **Never operate an unwritten silence-equals-yes rule.** It manufactures a record that will not
survive the one moment it is needed.

### 10.4 The cadence that follows

- **Daily:** finals ship under Standing. Registry rows written. Nothing sent.
- **Weekly:** one **batch playlist** posted; one **script batch** sent for the week ahead. Both
  timeboxed to the contractual window.
- **Per exception:** a **Named** asset goes out on its own, with real sign-off evidence.
- **Monthly:** the metrics read (`performance-metrics.md`) — which is the review that actually tells
  the client whether the work is working, and the one worth their hour.

⛔ **The client's attention is a budget like credits are.** Spent on rough cuts it buys the least;
spent on scripts, on the format, and on the monthly numbers it buys the most.

---

## 11. Before asking for approval: the scene board (v2.49)

House rule 10, 2026-11-05: consistency across the shots of a scene is checked **in depth before any approval
request**. They were asked to approve shots whose focal length and whose distances between objects had changed from
one shot to the next, which is easily detectable. On a real job two shots came back with beige trousers and were
"fixed" to jeans to match their neighbour while four other shots stayed beige, and a table moved between two shots
(production lessons, 2026-11-05). Each shot had been checked alone; the scene never was.

**The board.** Before an approval request for frames, sheets-in-use, clips or a cut, put **every shot of the scene
side by side** — the approved stills, or each take's first, middle and last frame — with the scene's sheets beside
them (the wardrobe and props sheet, the location sheet, the character sheets: `character-and-props.md` §8.3g).
Compare, shot by shot:

| What | What to look for |
|---|---|
| Lens and field of view | the same focal length where the plan says so; a change only where the shot list asks for one |
| Camera height | eye level stays eye level; a height change is a planned one |
| Subject size in frame | the same shot size reads the same size; a face does not grow between two mediums |
| Distances between objects | the table, the chair, the door at the same distances in every shot (the `[LOCATION MAP]` metres) |
| Positions of furniture and props | nothing moves between shots unless someone moved it in a shot |
| Wardrobe | every garment, colour and accessory as the scene's sheet shows it, per character state |
| Light direction | the key comes from the same side, the shadows fall the same way |
| Time of day | the sky, the colour of the light and the shadow length agree |

**Fix toward the scene's sheet, never toward the neighbouring shot.** The sheet says which shot is wrong; matching a
neighbour can spread the error, as the trousers did. Where no sheet settles it, the question goes to the owner
before anything is regenerated.

**The approval request says what was compared and what changed.** One short list: the shots on the board, the
eight things compared, each finding and the fix made toward the sheet, and anything left open. A request that does
not carry it is not ready to send. Verify on the real output — a render or the returned file at full size, never a
viewer or a thumbnail.

**When a fix touches story or brand, ask what it is for** (production lessons, 2026-11-05). A tablet screen got a
logo when it needed to sell the story (a home-financing form); a request read too narrowly cost a round. Before
fixing, write one line on what the fixed thing must do in the shot, and ask when it is not obvious.

**Status: manual until a script measures it.** `breakdown.py` already lists what drifts between shots as written
in the prompts; nothing yet measures lens, height, subject size or distances on the pictures. A script that does is
planned. Until then the board is built and read by eye, and the list in the approval request is the evidence.
