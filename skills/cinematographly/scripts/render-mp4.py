# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
DaVinci Resolve — queue ONE render job for a timeline (MP4 · H.264) at the client's delivery format.
It does NOT start the render: a person presses Render on the Deliver page. Queuing lets you eyeball
the job before committing render time, and a re-run never starts a render nobody asked for.

TWO WAYS TO RUN — the same file, unchanged:
  A. The DaVinci Resolve MCP that ships inside Resolve Studio 21.1+ (Claude Code on the Mac): edit
     CONFIG, then send the whole file as the `run_script` script. `resolve` and `project` are
     injected; the sandbox has no `os` and no `open` (measured 2026-09-14), so in this mode the script
     never touches the filesystem — create OUTPUT_FOLDER first (`mkdir -p`). The queued job comes back
     in `result`. scripts/gate.py reads the script before it runs (hooks/hooks.json) and asks.
  B. Pasted into Workspace ▸ Console ▸ Py3 in Resolve Studio: edit CONFIG, paste, press Enter.
  Then: Deliver page ▸ check the queued job ▸ Render ▸
        export_qc.py <file> --format <preset> --target-duration <s> --report
  The job's readback is not a witness for the rendered file; the QC report is.

⛔ RESOLVE HAS CRASHED IN THIS STEP. Five aborts on the production Mac inside the Deliver page's
render-settings widget (crash_archive.txt: 2026-08-29 ×4 on 21.0.3, 2026-09-14 on 21.1). The last was
a scripted render-settings change; the same calls minutes later did not crash. Cause unproven. So
this script SAVES THE PROJECT before it touches a render setting, and refuses an "Untitled Project".
"""

# ── CONFIG — edit every line below ──────────────────────────────────────────
OUTPUT_FOLDER = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/10-export"
OUTPUT_FILENAME = "REPLACE-WITH-A-NAME"          # no extension — Resolve appends .mp4
TIMELINE_NAME = None                              # None = the timeline currently open
# ---- Delivery format ----------------------------------------------------------
# There is NO house format, so there is no default below. Take all three from the client's format
# block (clients/<brand>.md §5), which names a preset in assets/delivery-formats.json:
#   vertical-1080      1080 x 1920   24 fps   -14 LUFS   (TikTok / Reels / Shorts)
#   feed-4x5           1080 x 1350   30 fps   -14 LUFS   (IG / FB feed)
#   square-1080        1080 x 1080   30 fps   -14 LUFS
#   landscape-1080     1920 x 1080   25 fps   -14 LUFS   (YouTube / web)
#   landscape-4k       3840 x 2160   25 fps   -14 LUFS
#   broadcast-eu-1080  1920 x 1080   25 fps   -23 LUFS   (EBU R128 — NOT -14)
WIDTH = None                # e.g. 1080
HEIGHT = None               # e.g. 1920
FPS = None                  # e.g. 24 — must equal the TIMELINE's frame rate: checked, never forced
                            # (WIDTH x HEIGHT must have the timeline's shape too: checked, never forced)
AUDIO_SAMPLE_RATE = 48000   # every preset's sample_rate_hz
# ---- The sound-off proof (references/sound-off-story.md, T2: the picture alone) -------------------------------
PICTURE_ONLY = False        # queue a render of a DUPLICATE of the timeline with every caption video track
                            # (CAPTION_TRACKS) disabled, the subtitles kept out of the render (ExportSubtitle False:
                            # a subtitle track cannot be disabled by script) and NO audio — the picture and the
                            # designed titles only. The timeline you edit is never touched; the duplicate stays in
                            # the project, named "<timeline> — PICTURE ONLY". Point OUTPUT_FOLDER at
                            # <job>/09-qa/soundoff and name it <slug>-v<N>-picture-only, then
                            # `soundoff.py proofs <job>`. Use it when the captions were placed in Resolve (routes 1
                            # and 3), so no captionless master exists.
CAPTION_TRACKS = ["captions", "subtitles", "subs", "cc"]  # video track names (or name prefixes) that carry caption
                            # Text+ clips, matched case-insensitively
# ---- Titles and captions made in Resolve (house rule C7, 2026-10-27: "it should defrult to Resolve or Fusion native
# elements. Not create outside for no reason") ----------------------------------------------------------------------
TITLES_OFF = False          # queue a render of a DUPLICATE of the timeline with every title video track (TITLE_TRACKS)
                            # disabled and NO audio — everything else as the cut, burned captions included. It is the
                            # "without" half of `title_qa.py native`: render the cut as usual (the delivery render, or
                            # <job>/09-qa/titles/<slug>-v<N>-titles-on), then this into <slug>-v<N>-titles-off, with the
                            # same VIDEO_QUALITY and BURN_SUBTITLES. The duplicate stays, named "<timeline> — TITLES OFF".
TITLE_TRACKS = ["titles", "supers"]   # video track names (or prefixes) that carry the titles. The standard layout
                            # (a supplement ad job): V1 Picture, V2 Graphics, V3 Titles, V4 Disclosure, V5 Supers. Graphics and
                            # the disclosure stay ON: a titles-off render must differ from the cut by the titles alone
BURN_SUBTITLES = None       # True: Resolve burns the Subtitle track into the picture (ExportSubtitle + SubtitleFormat
                            # "BurnIn") — the native caption route. False: no subtitles in the render. None: the Deliver
                            # page's setting, untouched. ⚠ An accepted setting is not a burned caption (a community
                            # measurement on 19.1.3.7 found none in the output): `srt_qa.py burned` checks the pixels.
VIDEO_QUALITY = None        # None: Resolve's current setting; or 'Best', or a bit rate. A QA pair renders both alike.
# ─────────────────────────────────────────────────────────────────────────────

if PICTURE_ONLY and TITLES_OFF:
    raise RuntimeError("PICTURE_ONLY and TITLES_OFF are two different renders — set one, run, then the other.")

# Guard: refuse an unedited CONFIG. An earlier version of this script, pasted unedited, created a
# folder literally named "REPLACE-WITH-YOUR-PROJECT-FOLDER" on disk; a render at a guessed format is
# the same mistake one step later.
_unedited = [n for n, v in (("OUTPUT_FOLDER", OUTPUT_FOLDER), ("OUTPUT_FILENAME", OUTPUT_FILENAME))
             if "REPLACE-WITH" in v]
_unedited += [n for n, v in (("WIDTH", WIDTH), ("HEIGHT", HEIGHT), ("FPS", FPS)) if not v]
if _unedited:
    raise RuntimeError("CONFIG not edited — still unset: " + ", ".join(_unedited) +
                       ". A real project path, a real filename, and the client's delivery format.")

try:
    import os                    # console: available · MCP run_script sandbox: PermissionError
except Exception:                # noqa: BLE001
    os = None
import posixpath                 # available in both (measured 2026-09-14)

resolve = app.GetResolve() if "app" in dir() else resolve  # noqa: F821 (Resolve injects `resolve`)
pm = resolve.GetProjectManager()
project = pm.GetCurrentProject()
if not project:
    raise RuntimeError("No project is currently open in Resolve.")
if (project.GetName() or "").startswith("Untitled Project"):
    raise RuntimeError(
        f"Refusing: the open project is '{project.GetName()}'. Save it under the job's name first "
        "(File ▸ Save Project As). Resolve auto-names an unsaved project the moment a timeline is "
        "made, and a render set up there is one nobody finds again.")

# Pick the timeline
if TIMELINE_NAME:
    timeline = None
    for i in range(1, project.GetTimelineCount() + 1):
        tl = project.GetTimelineByIndex(i)
        if tl.GetName() == TIMELINE_NAME:
            timeline = tl
            break
    if not timeline:
        raise RuntimeError(f"Timeline '{TIMELINE_NAME}' not found in this project.")
    project.SetCurrentTimeline(timeline)
else:
    timeline = project.GetCurrentTimeline()
    if not timeline:
        raise RuntimeError("No timeline is currently open — open one or set TIMELINE_NAME.")

# A render frame rate that differs from the timeline retimes the whole film. Check, never force.
tl_fps = float(timeline.GetSetting("timelineFrameRate") or 0)
if abs(tl_fps - float(FPS)) > 0.001:
    raise RuntimeError(f"Timeline '{timeline.GetName()}' runs at {tl_fps:g} fps but CONFIG FPS is {FPS}. "
                       "Conform the timeline (or correct CONFIG) first.")
# HR-07: a timeline of another size than the delivery moves every graphic centred or scaled on it (the course's
# "1080" timeline was 1920x1012, its centre at Y 506). The same check, never forced: the size is the timeline's.
tl_w = int(float(timeline.GetSetting("timelineResolutionWidth") or project.GetSetting("timelineResolutionWidth") or 0))
tl_h = int(float(timeline.GetSetting("timelineResolutionHeight") or project.GetSetting("timelineResolutionHeight") or 0))
# Refused when the SHAPE differs (that moves the centre and the safe boxes); the same shape at another size is a
# plain scale at render (a 3840x2160 timeline to a 1920x1080 delivery), so it is named, not refused.
if not (tl_w and tl_h):
    print(f"! Timeline '{timeline.GetName()}': its resolution did not read back, so its size was not checked.")
elif abs(tl_w * int(HEIGHT) - tl_h * int(WIDTH)) > 0.005 * tl_h * int(WIDTH):
    raise RuntimeError(f"Timeline '{timeline.GetName()}' is {tl_w}x{tl_h} but CONFIG is {WIDTH}x{HEIGHT}: another "
                       "shape, so every centred or scaled graphic sits wrong. Set the timeline's resolution (or correct "
                       "CONFIG) first.")
elif (tl_w, tl_h) != (int(WIDTH), int(HEIGHT)):
    print(f"! Timeline '{timeline.GetName()}' is {tl_w}x{tl_h}; the render scales it to {WIDTH}x{HEIGHT} (same shape).")

print(f"Setting up render for timeline: {timeline.GetName()}  ({WIDTH}x{HEIGHT} @ {FPS} fps)")

# Save BEFORE any render setting — see the crash note at the top. ProjectManager.SaveProject, not
# Project.SaveProject: on the Project object that attribute is None (measured 2026-09-14).
if not pm.SaveProject():
    raise RuntimeError("ProjectManager.SaveProject() returned False — refusing to touch render settings "
                       "on a project that is not saved.")

original = timeline
picture_only = {}
titles_off = {}
QUIET = PICTURE_ONLY or TITLES_OFF          # a proof render: no audio
if TITLES_OFF:
    # the same reasoning as PICTURE_ONLY below: a duplicate, never the editor's cut
    taken = {project.GetTimelineByIndex(i).GetName() for i in range(1, (project.GetTimelineCount() or 0) + 1)}
    base = f"{timeline.GetName()} — TITLES OFF"
    name, k = base, 2
    while name in taken:
        name, k = f"{base} {k}", k + 1
    dup = timeline.DuplicateTimeline(name)
    if not dup:
        raise RuntimeError(f"DuplicateTimeline({name!r}) returned nothing — no titles-off render was queued.")
    if not project.SetCurrentTimeline(dup):
        raise RuntimeError(f"SetCurrentTimeline({name!r}) returned False.")
    timeline = dup
    off = [("video", i) for i in range(1, (timeline.GetTrackCount("video") or 0) + 1)
           if any((timeline.GetTrackName("video", i) or "").strip().lower().startswith(t.lower()) for t in TITLE_TRACKS)]
    if not off:
        project.SetCurrentTimeline(original)
        raise RuntimeError(f"No video track named like {TITLE_TRACKS} on {original.GetName()!r} — nothing to turn off. Put "
                           f"the titles on a track named 'titles' (resolve-production-console.py PLACE_TITLES does).")
    for kind, i in off:
        timeline.SetTrackEnable(kind, i, False)
    still_on = [f"{kind} {i}" for kind, i in off if timeline.GetIsTrackEnabled(kind, i)]
    if still_on:
        raise RuntimeError(f"These tracks would not switch off on {name!r}: {still_on} — nothing was queued.")
    titles_off = {"timeline": name, "disabled": [f"{k} {i}" for k, i in off]}
    print(f"  TITLES OFF: rendering the duplicate {name!r} — off: {', '.join(titles_off['disabled'])} — and no audio.")
if PICTURE_ONLY:
    # ⛔ A duplicate, not the cut: disabling the caption tracks on the editor's timeline and re-enabling them after
    # queuing would render WITH captions, because the job renders the timeline as it is when someone presses Render.
    taken = {project.GetTimelineByIndex(i).GetName() for i in range(1, (project.GetTimelineCount() or 0) + 1)}
    base = f"{timeline.GetName()} — PICTURE ONLY"
    name, k = base, 2
    while name in taken:
        name, k = f"{base} {k}", k + 1
    dup = timeline.DuplicateTimeline(name)
    if not dup:
        raise RuntimeError(f"DuplicateTimeline({name!r}) returned nothing — no picture-only render was queued.")
    if not project.SetCurrentTimeline(dup):
        raise RuntimeError(f"SetCurrentTimeline({name!r}) returned False.")
    timeline = dup
    # ⛔ A subtitle track cannot be switched off by script: SetTrackEnable("subtitle", …) is accepted and the track
    # stays on (measured 21.1.1, a supplement ad job), so this used to refuse every picture-only render of a job with a
    # subtitle track. The subtitles are kept out of the render by ExportSubtitle = False instead, below.
    off = []
    for i in range(1, (timeline.GetTrackCount("video") or 0) + 1):
        tn = (timeline.GetTrackName("video", i) or "").strip().lower()
        if any(tn.startswith(c.lower()) for c in CAPTION_TRACKS):
            off.append(("video", i))
    for kind, i in off:
        timeline.SetTrackEnable(kind, i, False)
    still_on = [f"{kind} {i}" for kind, i in off if timeline.GetIsTrackEnabled(kind, i)]
    if still_on:
        raise RuntimeError(f"These tracks would not switch off on {name!r}: {still_on} — nothing was queued.")
    picture_only = {"timeline": name, "disabled": [f"{k} {i}" for k, i in off]}
    print(f"  PICTURE ONLY: rendering the duplicate {name!r} — off: {', '.join(picture_only['disabled']) or 'no caption tracks found'}"
          f" — and no audio. If the captions sit on a video track with another name, add it to CAPTION_TRACKS.")

page_before = resolve.GetCurrentPage()   # render calls switch Resolve to the Deliver page (measured)
if os is not None:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Format + codec by ID. GetRenderFormats is {name: id}, GetRenderCodecs is {description: id}; the
# setter wants ids. On 21.1 {"MP4": "mp4"} and {"H.264": "H264"} (measured 2026-09-14).
formats = project.GetRenderFormats() or {}
fmt_id = formats.get("MP4")
codecs = (project.GetRenderCodecs(fmt_id) or {}) if fmt_id else {}
codec_id = codecs.get("H.264")
if not fmt_id or not codec_id:
    raise RuntimeError(f"MP4 / H.264 not available here. Formats: {sorted(formats)} · MP4 codecs: {codecs}")
if not project.SetCurrentRenderFormatAndCodec(fmt_id, codec_id):
    raise RuntimeError(f"SetCurrentRenderFormatAndCodec({fmt_id!r}, {codec_id!r}) returned False.")

settings = {
    "SelectAllFrames": True,
    "TargetDir": OUTPUT_FOLDER,
    "CustomName": OUTPUT_FILENAME,
    "FormatWidth": int(WIDTH),
    "FormatHeight": int(HEIGHT),
    "FrameRate": float(FPS),
    "ExportVideo": True,
    "ExportAudio": not QUIET,
    "AudioSampleRate": int(AUDIO_SAMPLE_RATE),
}
# ── Subtitle burn-in ─────────────────────────────────────────────────────────
# A Subtitle track does NOT composite into the render unless Deliver ▸ Advanced Settings ▸ Subtitles says so.
# RenderSettings documents ExportSubtitle and SubtitleFormat ('BurnIn' | 'EmbeddedCaptions' | 'SeparateFile') — the
# DaVinciResolveScript.pyi served by Resolve's MCP, read 2026-10-27. An accepted key is still not a burned caption (a
# community measurement on 19.1.3.7 found no subtitles in the output), so the pixels are checked after the render.
if PICTURE_ONLY or BURN_SUBTITLES is False:
    settings["ExportSubtitle"] = False
elif BURN_SUBTITLES is True:
    settings["ExportSubtitle"] = True
    settings["SubtitleFormat"] = "BurnIn"
if VIDEO_QUALITY is not None:
    settings["VideoQuality"] = VIDEO_QUALITY
if not project.SetRenderSettings(settings):
    raise RuntimeError(f"SetRenderSettings refused: {settings}")
if BURN_SUBTITLES is True and not PICTURE_ONLY:
    print("Subtitles: asked Resolve to BURN the Subtitle track in (ExportSubtitle + BurnIn). After the render: "
          "srt_qa.py burned <job> --render <this file> --plate <the PICTURE_ONLY render> — the pixels, not the setting.")
elif BURN_SUBTITLES is None and not PICTURE_ONLY:
    print("REMINDER: subtitle burn-in was left as the Deliver page has it (BURN_SUBTITLES = None). Check Advanced "
          "Settings ▸ Subtitles before you press Render, then srt_qa.py burned on the file.")

# Replace only THIS output's earlier job. ⛔ Until 2026-09-14 this loop deleted EVERY job in the
# queue — including jobs an editor had queued by hand for other timelines.
def _same_dir(a, b):
    return posixpath.normpath(str(a or "")) == posixpath.normpath(str(b or ""))


mine = [j for j in (project.GetRenderJobList() or [])
        if _same_dir(j.get("TargetDir"), OUTPUT_FOLDER)
        and posixpath.splitext(str(j.get("OutputFilename") or ""))[0] == OUTPUT_FILENAME]
for j in mine:
    project.DeleteRenderJob(j["JobId"])

job_id = project.AddRenderJob()
if not job_id:
    raise RuntimeError("AddRenderJob returned nothing — check the render settings above.")

# Read the queued job back: a True from a setter means the API accepted it, not that the job is right.
job = next((j for j in (project.GetRenderJobList() or []) if j.get("JobId") == job_id), {})
checks = {
    "FormatWidth": job.get("FormatWidth") == int(WIDTH),
    "FormatHeight": job.get("FormatHeight") == int(HEIGHT),
    "FrameRate": abs(float(job.get("FrameRate") or 0) - float(FPS)) < 0.001,
    "AudioSampleRate": job.get("AudioSampleRate") == int(AUDIO_SAMPLE_RATE),
    "IsExportVideo": job.get("IsExportVideo") is True,
    "IsExportAudio": job.get("IsExportAudio") is (not QUIET),
    "TargetDir": _same_dir(job.get("TargetDir"), OUTPUT_FOLDER),
    "OutputFilename": posixpath.splitext(str(job.get("OutputFilename") or ""))[0] == OUTPUT_FILENAME,
}
for k, ok in checks.items():
    print(f"  [{'PASS' if ok else 'MISMATCH'}] {k}: {job.get(k)!r}")
_subkeys = {k: v for k, v in job.items() if "ubtitle" in str(k)}
if _subkeys:
    print(f"  (the job reads back {_subkeys} — informative only; the pixels decide)")

if page_before and resolve.GetCurrentPage() != page_before:
    resolve.OpenPage(page_before)
if (PICTURE_ONLY or TITLES_OFF) and original is not timeline:
    project.SetCurrentTimeline(original)     # the editor is put back on the cut; the job keeps the duplicate

if not all(checks.values()):
    project.DeleteRenderJob(job_id)
    raise RuntimeError("The queued job did not read back as CONFIG — it was removed again. "
                       "Nothing is queued; fix the mismatch above first.")

expected = posixpath.join(OUTPUT_FOLDER, job.get("OutputFilename") or OUTPUT_FILENAME + ".mp4")
print(f"Queued render job {job_id} — NOT started. Replaced {len(mine)} earlier job(s) for this output.")
print(f"Expected output once rendered: {expected}")
print("Deliver page ▸ check the job ▸ Render. Then export_qc.py on the file.")
result = {"job_id": job_id, "replaced_jobs": len(mine), "expected_output": expected,
          "timeline": timeline.GetName(), "checks": checks, "job": job, "picture_only": picture_only,
          "titles_off": titles_off, "burn_subtitles": BURN_SUBTITLES}
