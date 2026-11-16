# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
DaVinci Resolve — the ONE production/editing-setup console script for this skill. Everything that
isn't the render/Deliver step (that's render-mp4.py — the only other Resolve script this skill ships)
belongs in here as a toggle, not as a new standalone file. Two scripts, total. Don't add a third.

TWO WAYS TO RUN — the same file, unchanged (Resolve Studio; see the 21.1 note below):
  A. The DaVinci Resolve MCP that ships inside Resolve Studio 21.1+ (Claude Code on the Mac): open the
     project + target timeline, edit CONFIG (or take the copy `detect_beats.py` writes into 07-edit/
     with MARKERS filled in), and send the whole file as the `run_script` script. `resolve` and
     `project` are injected; the sandbox has no `open`, so DUMP_TIMELINE_JSON hands the dump back in
     `result` for the agent to write — nothing here touches the filesystem in this mode.
     scripts/gate.py reads the script before it runs (hooks/hooks.json).
  B. Pasted into Workspace ▸ Console ▸ Py3: edit CONFIG, paste the whole script, press Enter.
"""

# ⚠ RESOLVE 21.1 (2026-09-08) — Python scripting is Studio. Blackmagic's 21.1 notes say "Advanced
# scripting now requires DaVinci Resolve Studio", and on Blackmagic's download list it is the Studio
# 21.1 entry that carries the scripting and console items, not the free one. On Studio 21.1.0.14 this
# file's calls run through the MCP's `run_script` (measured 2026-09-14). On the FREE edition console
# Python does not run (client, 2026-09-14) — this file needs Studio either way
# (references/editing-and-audio.md, the 21.1 note).

# ── CONFIG ───────────────────────────────────────────────────────────────────
ADD_BEAT_MARKERS = True
# Filled in by detect_beats.py from real beat analysis of the chosen track — see
# editing-and-audio.md "Beat markers in Resolve". Leave empty (and ADD_BEAT_MARKERS = False) to
# skip. Each tuple is (frame, color, name), optionally followed by (note, duration, customData) —
# composer.py's copy carries the spotting cues as duration markers and each hit's window as JSON custom
# data. frame counts from the timeline's FIRST frame.
MARKERS = []  # __DETECT_BEATS_MARKERS__

DUMP_TIMELINE_JSON = False  # every clip's name, track, start and duration IN TIMELINE FRAMES, relative
                            # to the timeline start. This is how the FINAL, human-edited cut's real
                            # timings get back out of Resolve (the subtitle track can't be read, but
                            # clip positions can) — feeds caption conforming (editing-and-audio.md §
                            # Captions, the conform bridge) and lets the selects/manifest record what
                            # actually shipped vs what was planned. Read-only; changes nothing.
                            # Console: written to DUMP_PATH. MCP run_script: returned in `result`.
DUMP_PATH = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/07-edit/timeline-dump.json"

ENSURE_BROLL_TRACK = True   # create the V2 b-roll track (editing-and-audio.md's standing rule:
                            # dialogue/A-roll on V1, all b-roll on a separate V2 track) if the
                            # timeline doesn't already have a second video track.
ENSURE_AUDIO_LANES = True   # ⛔ create the A1–A6 lanes editing-and-audio.md has specified all
                            # along: A1–A2 dialogue · A3 ambience · A4 foley/SFX · A5–A6 music.
                            # Until 2026-09-07 this script created ONE video track and no audio
                            # lanes at all, so the file that names the lanes and the file that
                            # builds the timeline disagreed, and the lane structure the room-tone
                            # rule depends on had to be built by hand every time — which is how a
                            # two-layer mix becomes the default.
AUDIO_LANES = ["A1 dialogue", "A2 dialogue", "A3 ambience", "A4 foley/SFX",
               "A5 music", "A6 music"]

PLACE_MUSIC_FIT = False     # the fitted music, REBUILT here from the ORIGINAL track (2026-11-05: a Python render
                            # is a preview, "never import like that in to Resolve"). `music_fit.py rebuild <job>` writes
                            # the copy, 07-edit/resolve-production-console.music.py, with this on and MUSIC_FIT spliced
                            # in: the original imported ONCE, each of its segments appended to A5 as a source range at
                            # its record frame, and every placed item read back (start and length), mismatches
                            # reported; with no segments (a speed change comes first) the original is placed whole at
                            # the first frame. It never places over clips already on that track and never deletes
                            # anything. Crossfades, fades and a speed change are NOT made here: they are Fairlight work,
                            # done by computer control (house rule 8; 07-edit/music/REBUILD.md). The copy fills MARKERS
                            # with SPARSE markers — phrase starts, the must-hits, the cut nudges (listed, never
                            # applied), each music seam with its crossfade length, the end fade — never every beat
                            # (editing-and-audio.md § Music to picture).
MUSIC_FIT = {}  # __MUSIC_FIT__   {file, sha256, track, record_offset_frames, segments: [{src_in_f, src_out_f, record_f}]}
                            # — frames at the timeline's rate; src_out_f is the first frame NOT played, so endFrame is
                            # passed as src_out_f − 1, the last frame in [assumed for audio ranges, not measured live:
                            # the read-back of each length catches a difference]; record_f counts from the timeline's
                            # first frame

PLACE_MUSIC_ELEMENTS = False  # composer.py console <job> (its copy, 07-edit/resolve-production-console.compose.py):
                            # the composed layer on A6, then every stem and alt mix on its own NAMED stereo track,
                            # DISABLED so the mix is not doubled — switch one on in Fairlight to rebalance. Clip
                            # colours by origin (library Blue, composed Purple, generated Orange, stems Navy, alt
                            # mixes Teal). Never places over a clip, never deletes; read back.
MUSIC_ELEMENTS = []  # __MUSIC_ELEMENTS__
MUSIC_FAMILY = []  # __MUSIC_FAMILY__   one new timeline per length of the music (60/30/15/6), skipped if it exists
FAIRLIGHT_PRESET = ""       # a Fairlight preset the owner saved (busses, a Ducker on the music keyed from dialogue,
                            # a limiter) applied to the current timeline when named here and present in
                            # Resolve.GetFairlightPresets(). Off by default: a preset can change the track layout.

APPLY_GRADE_PLAN = False    # the grade plan from `grade_luts.py plan <job> --console` (07-edit/grade-plan.json,
                            # spliced in below with this switched on). A colour group per model with its
                            # correction LUT on the group's pre-clip graph; per clip the group, the grade
                            # template (only on a clip with no grade yet), the shot-match CDL, the
                            # Deflicker, look and texture nodes switched by the plan, and the look LUT;
                            # the timeline's vignette and Film Look Creator nodes for drama. Every LUT and
                            # group is read back. The API CANNOT ADD NODES, so the template DRX carries them,
                            # labelled; a clip whose node labels do not match the map is left alone
                            # (editing-and-audio.md § The grade template).
GRADE_PLAN = {}  # __GRADE_PLAN__

INVENTORY_TEMPLATES = False # read-only: every Fusion title, transition, generator and effect template on this
                            # machine (the user's, the system's, the app's own, and each one inside a .drfx
                            # bundle) and the OFX plugin bundles — what `motion_qa.py inventory` tags for the
                            # transition budget (house rule C5) and the title spike (C7). The scripting API
                            # cannot list templates, so this reads folders: run it in Workspace ▸ Console, or
                            # through run_script_unsafe (the run_script sandbox has no os). The built-in
                            # Video Transitions are not files: they are in the Effects Library, and the
                            # timeline dump names any the cut uses.
INVENTORY_PATH = r"REPLACE-WITH-A-FOLDER/resolve-inventory.json"
INVENTORY_EXTRA_ROOTS = []  # template folders kept elsewhere (a marketplace's install folder), as paths
OFX_DIRS = ["/Library/OFX/Plugins", r"C:\Program Files\Common Files\OFX\Plugins", "/usr/OFX/Plugins"]

FUSION_TITLE_SPIKE = False  # one template, proved before a job leans on it: can its text be set by script and
                            # read back, and does its layout survive 9:16? (House rule C7, 2026-10-27, made Resolve
                            # the default for titles; C6 had kept templates to 16:9 openers.) It makes a SCRATCH timeline
                            # (1080×1920 with SPIKE_VERTICAL), inserts SPIKE_TITLE there, sets SPIKE_TEXT on
                            # every text input it finds and reads each back, then returns to your timeline.
                            # Your cut is never touched; the scratch timeline stays in the media pool for you
                            # to look at the layout on the Edit page and delete by hand.
SPIKE_TITLE = "Text+"       # the template's name exactly as the Effects Library shows it
SPIKE_TEXT = "SPIKE 0123"
SPIKE_VERTICAL = True

# ⚡ v2.45 (2026-10-29) — USE THE INSTALLED LIBRARY. The owner's packs (Fusion titles such as "Background Reveal" and
# "Background Reveal Lower Third", JTechWP, Video Editor Studio, Free Smooth Transitions, Krokodove; OFX MagicAnimate Free,
# CineDream, Higgsfield Color Match) are assets: inventoried, mapped to the skill's kinds, placed by script.
LIBRARY_SCAN = False        # read-only: Resolve.GetEffectsList("video"/"audio") — every Fusion, OFX and audio effect
                            # with its category and id (titles and transitions are not in it) — and, where this runs
                            # with a filesystem (Workspace ▸ Console, run_script_unsafe), every title, transition,
                            # generator and effect template in the template folders with each macro's PUBLISHED INPUTS
                            # → result['library'] (or LIBRARY_PATH) → `resolve_library.py scan --from-console <file>`
LIBRARY_PATH = r"REPLACE-WITH-A-FOLDER/resolve-library.raw.json"
APPLY_TRANSITIONS = False   # TRANSITION_PLAN (`resolve_library.py console <job> --plan …`): TimelineItem.AddTransition
                            # at each planned cut — the outgoing item, its end — then read back: the transition item,
                            # its length, and both neighbours' start and length (a transition with no handle eats frames:
                            # that shows as a neighbour that moved, and is reported, never left silently)
TRANSITION_PLAN = []  # __LIBRARY_TRANSITIONS__  [{id, track, at_s, type, category, position, alignment, duration}]
APPLY_EFFECTS = False       # EFFECT_PLAN: TimelineItem.AddEffect(category, id) on each named item (cine:<id>, or a clip
                            # name); a Fusion effect's inputs set through Effect.GetFusionComp() and read back; an OFX
                            # effect (MagicAnimate, CineDream, Higgsfield Color Match) applied with its defaults — OFX
                            # parameters are not scriptable — and flagged for a manual pick in the Inspector
EFFECT_PLAN = []  # __LIBRARY_EFFECTS__  [{id, item, category, effect_id, name, inputs, manual}]

# ⛔ ON-SCREEN TEXT IS MADE HERE, IN RESOLVE (house rule C7, 2026-10-27: "it should defrult to Resolve or Fusion
# native elements. Not create outside for no reason"). `native.py console <job>` writes a copy of this file with the
# toggles below filled in from the job (07-edit/resolve-production-console.native.py). Re-runs are idempotent: a title
# already at its frame on its track is not placed again — its words are written again and read back.
# MEASURED on Studio 21.1.1, a supplement ad job (2026-10-28):
#  · InsertFusionTitleIntoTimeline lands on the TOPMOST UNLOCKED video track, at the playhead, for the timeline's mark
#    in–out (without marks every title is 120 frames). With any other track unlocked it RIPPLES the cut (V1 was pushed
#    120 frames); onto V3 under a locked V4 it failed silently. So every other track is locked first, the marks are
#    set, the text track must be the TOP video track, and the locks are put back as they were.
#  · A Text+ added inside a CLIP's own Fusion comp never shows on the Edit page: text is always its own title clip.
#  · StyledText written with SetInput read back '' after a later edit: it is written inside comp.Lock()/Unlock()
#    as tool.StyledText = text, then checked on a still (Project.ExportCurrentFrameAsStill — the composite; a
#    screenshot goes stale when Resolve sits on another Space).
#  · Left-aligned: HorizontalLeftCenterRight = -1 and HorizontalJustificationNew = 0. A bar behind the text (the
#    highlighter): element 3, ElementShape3 = 2, Offset3 = {0, 0} (it defaults to a shadow offset), Level3 = 1 (one
#    bar per line).
#  · A clip's last Fusion comp cannot be deleted (DeleteFusionCompByName): delete its tools and wire MediaIn to MediaOut.
# ⚡ v2.45 (2026-10-29, the author: "It keeps making mp4s which it imports"). From the 21.1.2 stubs [stub until the live
# test]: TimelineItem.SetPosition({trackIndex, startFrame}) — so the insert goes onto a SCRATCH top track with everything
# else locked and is MOVED onto its named track (Titles · Supers · Disclosure) at the spec's frame: the text track no
# longer has to be on top; Timeline.ExportFrame(offset, {outputType: 'file', filePath}) — stills with no playhead move
# and no page dependence; TimelineItem.ImportFusionComp / LoadFusionCompByName — the generated comp on a stock Text+
# (the no-install route); fusion.InstallFile(.drfx) and FontManager().GetFontList()/AddFont(). A row that cannot be
# placed STOPS with its reason: nothing here renders around it, and neither may the agent.
PLACE_TITLES = False        # every title spec whose engine is resolve, as a TITLE_TEMPLATE title on the TITLE_TRACK
                            # video track, at the spec's at_s for its duration_s; the card's style frame applied
                            # (TITLE_LAYOUT, each input read back), the words written and read back, a still taken
TITLES = []  # __NATIVE_TITLES__
TITLE_TEMPLATE = "Text+"    # the Effects Library title by name — Text+, or the brand's saved title template
TITLE_TRACK = "Titles"
TITLE_LAYOUT = {}  # __NATIVE_LAYOUT__  {kind: {Text+ input: value}} from the title card's style frame
STILLS_DIR = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/09-qa/stills"   # a still of each title at its hold: the check
TITLE_TEMPLATES = {}  # __NATIVE_TEMPLATES__  {kind: {name, comp, sha256, card_sha256, main, fields, motion, fps, font, style,
                            # kit}} — the card's generated Fusion titles (fusion_titles.py build). Empty: the stock
                            # TITLE_TEMPLATE with TITLE_LAYOUT's static inputs (no motion, no plate), and the report says so
TITLE_ROUTE = "auto"        # "template": the installed template by name · "import": a stock Text+ with the generated .comp
                            # imported (ImportFusionComp) and made active · "auto": the template when Resolve has it, else import
TITLE_KIND_TRACK = {"super": "Supers", "disclosure": "Disclosure"}   # a kind (or its kit) → its named video track;
                            # every other kind goes on TITLE_TRACK (render-mp4.py TITLE_TRACKS counts all three)
INSTALL_TITLE_TEMPLATES = False   # fusion.InstallFile(DRFX_PATH, True) before placing [stub: live without a restart? L1-f]
DRFX_PATH = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/07-edit/titles/fusion/cine-titles.drfx"
CHECK_FONTS = False         # read-only: Fusion's FontManager lists the card's face (family + style)? Each row records it
ADD_FONTS = False           # …and when it does not: FontManager().AddFont(each FONT_FILES), then check again [stub: does it
                            # apply without a restart? L1-e — if not, the report names the one manual step]
FONT_FILES = []  # __NATIVE_FONTS__  the card's font files, at their paths on THIS machine
PLACE_TITLE_OPTIONS = False # TITLE_OPTIONS (`native.py console <job> --options <id>`): on a DUPLICATE timeline "<cut> —
                            # OPTIONS <id>" (made once, reused), each option on its own "Titles opt<N>" track by the same
                            # placement as PLACE_TITLES; then Resolve's own stills — Timeline.ExportFrame — with only that
                            # option's track on and with every title track off, at five moments (entrance · legible · mid
                            # · exit · gone) → OPTIONS_DIR/<id>/opt<N>_<moment>_{on,off}.png for `title_qa.py
                            # strip-native`. The cut is never touched (EXPECT_SNAPSHOT proves it); nothing renders
TITLE_OPTIONS = {}  # __NATIVE_OPTIONS__  {id: [title rows for opt1..3, each with "option": N]}
OPTION_FRAMES = "strip"     # "strip": the five moments · "all": also every frame of the window (title ± 0.25 s), on and
                            # off, → OPTIONS_DIR/<id>/opt<N>/{on,off}/f<offset>.png (`title_qa.py native --with-frames`)
OPTIONS_DIR = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/09-qa/titles"
PLACE_SUBTITLES = False     # the locked .srt (build_srt.py), never a transcription. SUBTITLES_AS "track": imported
                            # and appended with the playhead at the timeline's start (measured: it lands at frame 0;
                            # never pass mediaType 3 — it crashed Resolve), then read back cue by cue. Style the track
                            # once (Inspector ▸ Track Style) from the card's caption tokens; Resolve burns it at
                            # render (render-mp4.py BURN_SUBTITLES). A subtitle track cannot be disabled by script
                            # (SetTrackEnable does nothing): a captions-off render sets ExportSubtitle False.
                            # "textplus": each cue as a CAPTION_TEMPLATE title on the CAPTION_TRACK, like the titles.
SRT_PATH = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/08-captions/SLUG.srt"
SRT_CUES = []  # __NATIVE_SRT_CUES__
SUBTITLES_AS = "track"
CAPTION_TEMPLATE = "Text+"
CAPTION_TRACK = "Captions"
NATIVE_REPORT_PATH = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/07-edit/titles/native-placement.json"
TRACK_LAYOUT = ["Picture", "Graphics", "Titles", "Disclosure", "Supers"]   # the standard video track names
                            # (a supplement ad job): scripts find tracks by NAME (render-mp4.py TITLE_TRACKS, CAPTION_TRACKS)
NAME_TRACKS = False         # name V1..Vn from TRACK_LAYOUT where a track still has Resolve's default name; it never adds
                            # a track (an empty track above the text tracks would block every title insert)
SNAPSHOT_TIMELINE = False   # read-only: every track's name, enabled and locked state, and its items by name and frame
                            # → result['snapshot']. Run it before and after any structural edit (the invariant check)
EXPECT_SNAPSHOT = {}  # __EXPECT_SNAPSHOT__  a snapshot from before the edit: every track and title it had must still be
                            # there, named and enabled the same; differences come back in result['invariant']
# ─────────────────────────────────────────────────────────────────────────────

resolve = app.GetResolve() if "app" in dir() else resolve  # noqa: F821 (injected: console and run_script)
try:
    open                        # noqa: B018 — console: a builtin · MCP run_script sandbox: removed
    _CAN_WRITE = True
except NameError:
    _CAN_WRITE = False
result = {"mode": "console" if _CAN_WRITE else "mcp-run_script", "done": []}

pm = resolve.GetProjectManager()
project = pm.GetCurrentProject()
if not project:
    raise RuntimeError("No project is currently open in Resolve.")
timeline = project.GetCurrentTimeline()
if not timeline:
    raise RuntimeError("No timeline is currently open — open the target timeline first.")

print(f"Working on timeline: {timeline.GetName()}")
result["timeline"] = timeline.GetName()

if ENSURE_BROLL_TRACK:
    video_tracks = timeline.GetTrackCount("video")
    if video_tracks < 2:
        ok = timeline.AddTrack("video")
        print(f"  Added V2 (b-roll track). AddTrack accepted: {ok}. "
              f"Move b-roll clips up onto it — never intercut b-roll into V1.")
    else:
        print(f"  {video_tracks} video track(s) already exist — V2 is available, nothing added.")
    result["done"].append(f"video tracks: {timeline.GetTrackCount('video')}")

if ENSURE_AUDIO_LANES:
    have = timeline.GetTrackCount("audio")
    want = len(AUDIO_LANES)
    if have < want:
        for _ in range(want - have):
            timeline.AddTrack("audio")
        print(f"  Added {want - have} audio track(s) — now {timeline.GetTrackCount('audio')}.")
    else:
        print(f"  {have} audio track(s) already exist — nothing added.")
    # SetTrackName works and reads back on Studio 21.1.0.14 (measured 2026-09-14). The names are
    # still checked, not assumed; if one does not take, the lanes are there in the right ORDER, which
    # is what the doctrine depends on.
    unnamed = []
    for i, name in enumerate(AUDIO_LANES, start=1):
        try:
            timeline.SetTrackName("audio", i, name)
            if timeline.GetTrackName("audio", i) != name:
                unnamed.append(f"A{i}")
        except Exception as e:                                              # noqa: BLE001
            unnamed.append(f"A{i} ({e})")
    print("  Lanes: " + " · ".join(AUDIO_LANES)
          + (f"  — ⚠ not named, do it by hand: {', '.join(unnamed)}" if unnamed else ""))
    print("  ⛔ A3 is not optional. 'No clip plays over silence — every moment carries at least the")
    print("     room-tone bed under it' (editing-and-audio.md). export_qc.py FAILS a master with")
    print("     true digital silence in it, so an empty A3 is caught at the door rather than by a")
    print("     client. Lay the bed before the fine cut, not after.")
    result["done"].append(f"audio lanes: {timeline.GetTrackCount('audio')}"
                          + (f", unnamed {unnamed}" if unnamed else ""))

if PLACE_MUSIC_FIT:
    _mf = MUSIC_FIT or {}
    if not _mf.get("file"):
        print("  PLACE_MUSIC_FIT is True but MUSIC_FIT is empty — run `music_fit.py rebuild <job>` and use the copy it "
              "writes into 07-edit/.")
    else:
        _ti = int(_mf.get("track") or 5)
        _name = _mf["file"].replace("\\", "/").split("/")[-1]
        _segs = list(_mf.get("segments") or [])
        while timeline.GetTrackCount("audio") < _ti:
            timeline.AddTrack("audio")
        _have = timeline.GetItemListInTrack("audio", _ti) or []
        if [_it for _it in _have if (_it.GetName() or "") == _name]:
            print(f"  A{_ti} already carries {_name} — left as it is, nothing imported again.")
            result["done"].append(f"music: already on A{_ti}")
        elif _have:
            print(f"  ⚠ A{_ti} already has {len(_have)} clip(s) — the music is NOT placed over them. Clear A{_ti} "
                  f"by hand (nothing here deletes), then run this again.")
            result["done"].append(f"music: A{_ti} not empty, not placed")
        else:
            _mp = project.GetMediaPool()
            _imp = _mp.ImportMedia([_mf["file"]]) or []
            if not _imp:
                print(f"  ⚠ ImportMedia returned nothing for {_mf['file']} — is the path on this machine?")
                result["done"].append("music: import failed")
            elif _segs:
                # the ORIGINAL, cut by source range: one clipInfo per segment. recordFrame is ABSOLUTE (unlike
                # AddMarker's frame): the timeline's first frame + the segment's record_f. endFrame is the LAST frame in.
                _t0 = timeline.GetStartFrame() + int(_mf.get("record_offset_frames") or 0)
                _mp.AppendToTimeline([{"mediaPoolItem": _imp[0], "startFrame": int(_s["src_in_f"]),
                                       "endFrame": int(_s["src_out_f"]) - 1, "mediaType": 2, "trackIndex": _ti,
                                       "recordFrame": _t0 + int(_s["record_f"])} for _s in _segs])
                _now = timeline.GetItemListInTrack("audio", _ti) or []
                _back, _bad = [], []
                for _k, _s in enumerate(_segs, start=1):
                    _rec = _t0 + int(_s["record_f"])
                    _len = int(_s["src_out_f"]) - int(_s["src_in_f"])
                    _at = [_it for _it in _now if _it.GetStart() == _rec]
                    if not _at:
                        _bad.append(f"segment {_k}: nothing starts at frame {_s['record_f']}")
                    elif _at[0].GetDuration() != _len:
                        _bad.append(f"segment {_k}: {_at[0].GetDuration()} frames at frame {_s['record_f']}, planned {_len}")
                    else:
                        _back.append(_at[0])
                if _mf.get("color"):
                    for _it in _back:
                        _it.SetClipColor(_mf["color"])
                print(f"  Music: {len(_segs)} segment(s) of the ORIGINAL {_name} on A{_ti} — {len(_back)}/{len(_segs)} "
                      f"read back at their frames and lengths.")
                for _b in _bad:
                    print(f"  ⚠ {_b} — check A{_ti} by eye; nothing here moves or deletes it.")
                print("  Crossfades, the end fade and any speed change are Fairlight work, by computer control "
                      "(07-edit/music/REBUILD.md) — not this script.")
                result["done"].append(f"music: {len(_segs)} segment(s) of the original on A{_ti}, read back "
                                      f"{len(_back)}/{len(_segs)}" + (f", mismatches: {'; '.join(_bad)}" if _bad else ""))
            else:
                # AppendToTimeline's recordFrame is ABSOLUTE (unlike AddMarker's frame): the timeline's first frame
                _rec = timeline.GetStartFrame() + int(_mf.get("record_offset_frames") or 0)
                _mp.AppendToTimeline([{"mediaPoolItem": _imp[0], "mediaType": 2, "trackIndex": _ti, "recordFrame": _rec}])
                _back = [_it for _it in (timeline.GetItemListInTrack("audio", _ti) or []) if _it.GetStart() == _rec]
                if _mf.get("color"):
                    for _it in _back:
                        _it.SetClipColor(_mf["color"])
                print(f"  Music: {_name} placed whole on A{_ti} at the first frame — "
                      + ("read back." if _back else f"⚠ NOT read back: check A{_ti} by eye.")
                      + " Any speed change and the cuts are Fairlight work, by computer control (07-edit/music/REBUILD.md).")
                result["done"].append(f"music: placed on A{_ti}, read back {bool(_back)}")

def _place_audio(tl, el, mp):
    """One music element on its own audio track of `tl`: the track made (stereo) and named if it is new, nothing placed
    over another clip, imported, appended at the first frame, coloured, enabled or disabled, read back."""
    ti = int(el.get("track") or 6)
    name = el["file"].replace("\\", "/").split("/")[-1]
    while tl.GetTrackCount("audio") < ti:
        tl.AddTrack("audio", "stereo")
    if el.get("name") and ti > len(AUDIO_LANES):
        tl.SetTrackName("audio", ti, el["name"])
    have = tl.GetItemListInTrack("audio", ti) or []
    if [it for it in have if (it.GetName() or "") == name]:
        return f"A{ti} already carries {name}"
    if have:
        return f"⚠ A{ti} has {len(have)} clip(s) — {name} NOT placed over them"
    imp = mp.ImportMedia([el["file"]]) or []
    if not imp:
        return f"⚠ ImportMedia returned nothing for {el['file']}"
    rec = tl.GetStartFrame()
    mp.AppendToTimeline([{"mediaPoolItem": imp[0], "mediaType": 2, "trackIndex": ti, "recordFrame": rec}])
    back = [it for it in (tl.GetItemListInTrack("audio", ti) or []) if it.GetStart() == rec]
    for it in back:
        if el.get("color"):
            it.SetClipColor(el["color"])
    if el.get("enabled") is False:
        tl.SetTrackEnable("audio", ti, False)
    on = tl.GetIsTrackEnabled("audio", ti)
    return f"{name} on A{ti} ({tl.GetTrackName('audio', ti)}), {'on' if on else 'off'}, " + ("read back" if back else "⚠ NOT read back")


if PLACE_MUSIC_ELEMENTS:
    _mp = project.GetMediaPool()
    for _el in MUSIC_ELEMENTS or []:
        _r = _place_audio(timeline, _el, _mp)
        print(f"  Music {_el.get('role') or ''}: {_r}")
        result["done"].append(f"music element: {_r}")

if MUSIC_FAMILY:
    _mp = project.GetMediaPool()
    _names = [project.GetTimelineByIndex(_i).GetName() for _i in range(1, project.GetTimelineCount() + 1)]
    for _fm in MUSIC_FAMILY:
        if _fm["name"] in _names:
            print(f"  Timeline '{_fm['name']}' exists — left as it is.")
            result["done"].append(f"family: {_fm['name']} exists")
            continue
        _tl = _mp.CreateEmptyTimeline(_fm["name"])
        if not _tl:
            print(f"  ⚠ CreateEmptyTimeline('{_fm['name']}') failed")
            continue
        project.SetCurrentTimeline(_tl)
        _r = _place_audio(_tl, _fm, _mp)
        project.SetCurrentTimeline(timeline)
        print(f"  Timeline '{_fm['name']}': {_r}")
        result["done"].append(f"family: {_fm['name']}: {_r}")

if FAIRLIGHT_PRESET:
    _pres = resolve.GetFairlightPresets() or []
    if FAIRLIGHT_PRESET in _pres:
        _ok = project.ApplyFairlightPresetToCurrentTimeline(FAIRLIGHT_PRESET)
        print(f"  Fairlight preset '{FAIRLIGHT_PRESET}' applied: {_ok} (no getter: check the mixer by eye).")
        result["done"].append(f"fairlight preset: {FAIRLIGHT_PRESET} {_ok}")
    else:
        print(f"  ⚠ No Fairlight preset '{FAIRLIGHT_PRESET}' — saved presets: {', '.join(_pres) or 'none'}.")
        result["done"].append("fairlight preset: missing")

if ADD_BEAT_MARKERS:
    if not MARKERS:
        print("  ADD_BEAT_MARKERS is True but MARKERS is empty — run detect_beats.py on the "
              "chosen track first, or tap markers live (see editing-and-audio.md) if librosa "
              "isn't available.")
    else:
        # ⛔ AddMarker's frameId counts from the timeline's FIRST frame — measured 2026-09-14 on
        # Studio 21.1.0.14 through an OTIO export of the timeline: AddMarker(10) landed 10 frames in,
        # and AddMarker(GetStartFrame() + 20) landed AN HOUR past the end of a 5-second timeline and
        # still returned True. So never add GetStartFrame() here (AppendToTimeline's recordFrame is
        # the one that is absolute), and a True is not a placed marker: read GetMarkers() back.
        length = timeline.GetEndFrame() - timeline.GetStartFrame()
        past_end = [m[0] for m in MARKERS if length > 0 and m[0] >= length]
        for m in MARKERS:
            frame, color, name = m[0], m[1], m[2]
            note = m[3] if len(m) > 3 else ""
            dur = int(m[4]) if len(m) > 4 and m[4] else 1
            custom = m[5] if len(m) > 5 else ""
            timeline.AddMarker(frame, color, name, note, dur, custom)
        have = {int(float(k)) for k in (timeline.GetMarkers() or {})}
        landed = sum(1 for m in MARKERS if m[0] in have)
        print(f"  Beat markers: {landed}/{len(MARKERS)} read back on the timeline"
              + (f" ({len(MARKERS) - landed} missing — a marker may already exist on that frame)"
                 if landed < len(MARKERS) else "") + ".")
        if past_end:
            print(f"  ⚠ {len(past_end)} marker(s) sit at or past the timeline's current end (frame "
                  f"{length}). Expected only if the cut is not assembled yet — otherwise the music "
                  f"offset is wrong (detect_beats.py --offset-seconds).")
        result["done"].append(f"markers: {landed}/{len(MARKERS)} read back, {len(past_end)} past end")

if APPLY_GRADE_PLAN:
    _G = GRADE_PLAN or {}
    _rep = {"groups": {}, "clips": {}, "timeline": {}, "unplanned": [], "not_on_timeline": [], "problems": []}
    if not _G.get("clips"):
        print("  APPLY_GRADE_PLAN is True but GRADE_PLAN is empty — run `grade_luts.py plan <job> --console` "
              "and use the copy it writes into 07-edit/.")
    else:
        _NM = _G.get("node_map") or {}
        _CN, _TN = _NM.get("clip") or {}, _NM.get("timeline") or {}

        def _norm(_s):
            return "".join(ch for ch in str(_s or "").lower() if ch.isalnum())

        def _lut_is(_got, _want):
            # GetLUT returns the path relative to the LUT folder; compare the file name, case-blind
            return bool(_got) and _norm(str(_got).replace("\\", "/").split("/")[-1]) == \
                _norm(str(_want).replace("\\", "/").split("/")[-1])

        def _labels_match(_graph, _map):
            # ⛔ the map is only safe on the template's own layout: every mapped node labelled as the map says
            _bad = []
            for _k, _i in _map.items():
                try:
                    _lab = _graph.GetNodeLabel(_i)
                except Exception:                                           # noqa: BLE001
                    _lab = None
                if _norm(_lab) != _norm(_k):
                    _bad.append(f"node {_i} is {_lab!r}, the map wants {_k!r}")
            return _bad

        def _ungraded(_graph):
            # measured 2026-10-26 on Studio 21.1.1: a timeline with no timeline grade has 0 nodes; a graded
            # node lists its tools ("Primary Balance", "LUT: <name>", …); an unlabelled node's label is ''
            try:
                _n = _graph.GetNumNodes()
                return _n == 0 or (_n == 1 and not (_graph.GetToolsInNode(1) or []))
            except Exception:                                               # noqa: BLE001
                return False

        try:
            project.RefreshLUTList()
        except Exception:                                                   # noqa: BLE001
            pass
        _groups = {}
        for _g in (project.GetColorGroupsList() or []):
            _groups[_g.GetName()] = _g
        for _name, _spec in (_G.get("groups") or {}).items():
            _g = _groups.get(_name) or project.AddColorGroup(_name)
            if not _g:
                _rep["groups"][_name] = "could not be created"
                continue
            _groups[_name] = _g
            _pg = _g.GetPreClipNodeGraph()
            if not _pg or _pg.GetNumNodes() < 1:
                _rep["groups"][_name] = "the pre-clip graph has no node — add one by hand on the Color page " \
                                        "(the API cannot add nodes), then run again"
                continue
            _pg.SetLUT(1, _spec["pre_lut"])
            _got = _pg.GetLUT(1)
            _rep["groups"][_name] = "LUT read back" if _lut_is(_got, _spec["pre_lut"]) else (
                f"LUT did NOT read back (got {_got!r}) — is {_spec['pre_lut']} fitted (grade_luts.py fit) and "
                f"installed through the LUT tool?")

        _plan, _seen = _G["clips"], set()
        _need = max(_CN.values()) if _CN else 0
        for _ti in range(1, int(timeline.GetTrackCount("video")) + 1):
            for _it in (timeline.GetItemListInTrack("video", _ti) or []):
                try:
                    if _it.GetType() not in (None, "video"):
                        continue                                    # 21.1 lists transitions as items
                except Exception:                                           # noqa: BLE001
                    pass
                _key = _it.GetName()
                if _key not in _plan:
                    try:
                        _key = _it.GetMediaPoolItem().GetClipProperty("File Name") or _key
                    except Exception:                                       # noqa: BLE001
                        pass
                if _key not in _plan:
                    _rep["unplanned"].append(_it.GetName())
                    continue
                _seen.add(_key)
                _c, _st = _plan[_key], []
                _g = _groups.get(_c["group"])
                if _g:
                    _it.AssignToColorGroup(_g)
                    _cg = _it.GetColorGroup()
                    _st.append("group ok" if _cg and _cg.GetName() == _c["group"] else "group did NOT read back")
                _ng = _it.GetNodeGraph()
                if not _ng:
                    _rep["problems"].append(f"{_key}: no node graph came back")
                    _rep["clips"][_key] = _st + ["nodes left alone"]
                    continue
                if _G.get("template_drx") and _ng.GetNumNodes() < _need:
                    if _ungraded(_ng):
                        _ng.ApplyGradeFromDRX(_G["template_drx"], 0)
                        _st.append("template applied")
                    else:
                        _st.append("has a grade of its own — template NOT applied")
                if _ng.GetNumNodes() < _need:
                    _rep["problems"].append(f"{_key}: {_ng.GetNumNodes()} node(s), the map needs {_need} — "
                                            f"apply the grade template (DRX) first")
                    _rep["clips"][_key] = _st + ["nodes left alone"]
                    continue
                _bad = _labels_match(_ng, _CN)
                if _bad:
                    _rep["problems"].append(f"{_key}: not the template's layout — " + "; ".join(_bad))
                    _rep["clips"][_key] = _st + ["nodes left alone"]
                    continue
                for _k, _i in _CN.items():
                    _ng.SetNodeEnabled(_i, bool(_c["nodes"].get(_k)))
                _st.append("nodes " + ",".join(_k for _k in _CN if _c["nodes"].get(_k)) + " on (not readable)")
                if _c.get("look_lut"):
                    _ng.SetLUT(_CN["look"], _c["look_lut"])
                    _st.append("look LUT ok" if _lut_is(_ng.GetLUT(_CN["look"]), _c["look_lut"])
                               else "look LUT did NOT read back")
                _cdl = _c.get("cdl")
                if _cdl:
                    _ok = _it.SetCDL({"NodeIndex": str(_CN["shot_match"]),
                                      "Slope": " ".join(f"{v:.4f}" for v in _cdl["slope"]),
                                      "Offset": " ".join(f"{v:.4f}" for v in _cdl["offset"]),
                                      "Power": " ".join(f"{v:.4f}" for v in _cdl.get("power", [1, 1, 1])),
                                      "Saturation": f"{_cdl.get('sat', 1.0):.4f}"})
                    _st.append("CDL set" if _ok else "CDL refused")
                _rep["clips"][_key] = _st
        _rep["not_on_timeline"] = sorted(set(_plan) - _seen)

        _want = _G.get("timeline") or {}
        _tg = timeline.GetNodeGraph()
        _tn = _tg.GetNumNodes() if _tg else 0
        _tneed = max(_TN.values()) if _TN else 0
        if _G.get("timeline_drx") and _tn < _tneed and _tg and _ungraded(_tg):
            _tg.ApplyGradeFromDRX(_G["timeline_drx"], 0)
            _tn = _tg.GetNumNodes()
        if _tn >= _tneed and _TN and not _labels_match(_tg, _TN):
            for _k, _i in _TN.items():
                _tg.SetNodeEnabled(_i, bool(_want.get(_k)))
            _rep["timeline"] = {_k: bool(_want.get(_k)) for _k in _TN}
        elif any(_want.values()):
            _rep["problems"].append("the timeline graph lacks the template's labelled nodes ("
                                    + ", ".join(_TN) + ") — apply the timeline DRX; vignette and film look NOT set")
        _okc = sum(1 for v in _rep["clips"].values() if "nodes left alone" not in v)
        print(f"  Grade plan ({_G.get('lane')}): {len(_rep['groups'])} group(s) · {_okc}/{len(_plan)} clip(s) set · "
              f"{len(_rep['unplanned'])} on the timeline but not in the plan · "
              f"{len(_rep['not_on_timeline'])} planned but not found")
        for _name, _v in _rep["groups"].items():
            print(f"    {_name}: {_v}")
        for _p in _rep["problems"]:
            print(f"    ⚠ {_p}")
        print("  Then: grab a still per group and run `grade_luts.py lutcheck`; export, then `look_qa.py export`.")
        result["grade"] = _rep
        result["done"].append(f"grade: {_okc}/{len(_plan)} clips, {len(_rep['problems'])} problem(s)")

def _published(_txt):
    """The published inputs of a Fusion macro (.setting text): [{id, name, source_op, source}] — what a script can set on
    a pack's title or effect through its comp. A regex, not a parser: a pack's file may be large or unusual."""
    import re as _re
    _out = []
    for _m in _re.finditer(r"(Input\d+)\s*=\s*InstanceInput\s*\{(.*?)\}", _txt or "", _re.S):
        _b = _m.group(2)
        _row = {"id": _m.group(1)}
        for _k, _f in (("name", "Name"), ("source_op", "SourceOp"), ("source", "Source")):
            _hit = _re.search(_f + r'\s*=\s*"([^"]*)"', _b)
            _row[_k] = _hit.group(1) if _hit else None
        _out.append(_row)
    return _out


def _template_walk(_os, _zf, inputs=False):
    """(items, roots, unreadable, ofx): every Fusion title, transition, generator and effect template on this machine
    (the user's, the system's, the app's own, and each one inside a .drfx bundle) and the OFX bundles. With `inputs`,
    each macro's published inputs (LIBRARY_SCAN)."""
    _home = _os.path.expanduser("~")
    _roots = []
    try:
        _fu = resolve.Fusion()
        _mp = _fu.MapPath("Templates:") if _fu else ""
        if _mp:
            _roots.append(("fusion", str(_mp)))
    except Exception:                                                       # noqa: BLE001
        pass
    _roots += [("user", _os.path.join(_home, "Library", "Application Support", "Blackmagic Design",
                                      "DaVinci Resolve", "Fusion", "Templates")),
               ("system", "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates"),
               ("app", "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Resources/Fusion/Templates"),
               ("user", _os.path.join(_os.environ["APPDATA"], "Blackmagic Design", "DaVinci Resolve", "Support",
                                      "Fusion", "Templates") if _os.environ.get("APPDATA") else ""),
               ("system", r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Templates"),
               ("user", _os.path.join(_home, ".local", "share", "DaVinciResolve", "Fusion", "Templates"))]
    _roots += [("extra", str(_r)) for _r in INVENTORY_EXTRA_ROOTS]
    _KIND = {"titles": "title", "transitions": "transition", "generators": "generator", "effects": "effect"}

    def _kind_of(_parts):
        for _p in _parts:
            if _p.lower() in _KIND:
                return _KIND[_p.lower()]
        return "other"
    _items, _seen, _bad = [], set(), []
    for _src, _root in _roots:
        _real = _os.path.realpath(_root) if _root else ""
        if not _real or _real in _seen or not _os.path.isdir(_real):
            continue
        _seen.add(_real)
        for _dp, _dn, _fn in _os.walk(_real):
            for _f in sorted(_fn):
                _full = _os.path.join(_dp, _f)
                _rel = _os.path.relpath(_full, _real).replace("\\", "/")
                _low = _f.lower()
                if _low.endswith((".setting", ".comp")):
                    _it = {"kind": _kind_of(_rel.split("/")[:-1]), "name": _f.rsplit(".", 1)[0],
                           "source": _src, "path": _rel, "root": _real}
                    if inputs and _low.endswith(".setting"):
                        try:
                            with open(_full, encoding="utf-8", errors="replace") as _fh:
                                _it["published_inputs"] = _published(_fh.read(4 << 20))
                        except Exception:                                   # noqa: BLE001
                            _it["published_inputs"] = None
                    _items.append(_it)
                elif _low.endswith(".drfx"):
                    try:
                        with _zf.ZipFile(_full) as _z:
                            for _n in sorted(_z.namelist()):
                                if _n.lower().endswith(".setting"):
                                    _it = {"kind": _kind_of(_n.split("/")[:-1]),
                                           "name": _n.split("/")[-1].rsplit(".", 1)[0],
                                           "source": f"drfx:{_f}", "path": f"{_rel}::{_n}", "root": _real}
                                    if inputs:
                                        _it["published_inputs"] = _published(_z.read(_n).decode("utf-8", "replace"))
                                    _items.append(_it)
                    except Exception as _e:                                 # noqa: BLE001
                        _bad.append(f"{_rel}: {_e}")
    _ofx = []
    for _d in OFX_DIRS:
        if _os.path.isdir(_d):
            _ofx += sorted(_x[:-len(".ofx.bundle")] for _x in _os.listdir(_d) if _x.lower().endswith(".ofx.bundle"))
    return _items, sorted(_seen), _bad, _ofx


def _resolve_version():
    try:
        return resolve.GetVersionString()
    except Exception:                                                       # noqa: BLE001
        return None


if INVENTORY_TEMPLATES:
    try:
        import os as _os
        import zipfile as _zf
    except Exception:                                                       # noqa: BLE001 (the sandbox refuses)
        _os = None
        print("INVENTORY_TEMPLATES: needs the filesystem — run this in Workspace ▸ Console, or through "
              "run_script_unsafe (the run_script sandbox has no os). Nothing listed.")
        result["inventory"] = {"error": "no filesystem in this sandbox"}
    if _os is not None:
        _items, _roots_seen, _bad, _ofx = _template_walk(_os, _zf)
        _inv = {"resolve": _resolve_version(), "roots": _roots_seen, "templates": _items, "ofx": _ofx, "unreadable": _bad}
        _by = {}
        for _i in _items:
            _by[_i["kind"]] = _by.get(_i["kind"], 0) + 1
        print(f"  Inventory: {len(_items)} template(s) under {len(_roots_seen)} folder(s) — "
              + ", ".join(f"{_v} {_k}" for _k, _v in sorted(_by.items())) + f"; {len(_ofx)} OFX bundle(s)"
              + (f"; {len(_bad)} .drfx unreadable" if _bad else ""))
        if not _CAN_WRITE or "REPLACE-WITH-" in INVENTORY_PATH:
            result["inventory"] = _inv
            print("  INVENTORY_PATH not set (or no open here) — the inventory is in result['inventory'].")
        else:
            import json as _json
            with open(INVENTORY_PATH, "w", encoding="utf-8") as _fh:
                _json.dump(_inv, _fh, indent=1, ensure_ascii=False)
            print(f"  wrote {INVENTORY_PATH} — then `motion_qa.py inventory {INVENTORY_PATH}` tags it.")
        result["done"].append(f"inventory: {len(_items)} templates, {len(_ofx)} OFX")

if LIBRARY_SCAN:
    # ⚡ v2.45: what is installed, by the API where it can say (effects: category and id) and by the folders where it
    # cannot (titles, transitions, generators — and each macro's published inputs). Read-only.
    _lib = {"resolve": _resolve_version(), "effects": {}, "templates": None, "ofx_bundles": None, "notes": []}
    for _mt in ("video", "audio"):
        try:
            _lib["effects"][_mt] = [dict(_e) for _e in (resolve.GetEffectsList(_mt) or [])]
        except Exception as _e:                                             # noqa: BLE001
            _lib["notes"].append(f"GetEffectsList({_mt!r}) failed: {_e}")
    try:
        import os as _os
        import zipfile as _zf
    except Exception:                                                       # noqa: BLE001 (the run_script sandbox)
        _os = None
        _lib["notes"].append("no filesystem here (run_script): the effects are listed, the titles, transitions and "
                             "generators are not — run LIBRARY_SCAN in Workspace ▸ Console or run_script_unsafe, or pass "
                             "`resolve_library.py scan --folder <Templates>` / `--names <list>`")
    if _os is not None:
        _items, _roots_seen, _bad, _ofx = _template_walk(_os, _zf, inputs=True)
        _lib.update(templates=_items, roots=_roots_seen, unreadable=_bad, ofx_bundles=_ofx)
    _ne = sum(len(_v) for _v in _lib["effects"].values())
    print(f"  Library: {_ne} effect(s) from GetEffectsList" + (f", {len(_lib['templates'])} template(s) from the folders"
                                                                if _lib["templates"] is not None else "")
          + "".join(f"\n    ⚠ {_n}" for _n in _lib["notes"]))
    if _CAN_WRITE and "REPLACE-WITH-" not in LIBRARY_PATH:
        import json as _json
        with open(LIBRARY_PATH, "w", encoding="utf-8") as _fh:
            _json.dump(_lib, _fh, indent=1, ensure_ascii=False)
        print(f"  wrote {LIBRARY_PATH} — then `resolve_library.py scan --from-console {LIBRARY_PATH} --job <job>`.")
    else:
        result["library"] = _lib
        print("  The scan is in result['library'] — write it to a file for `resolve_library.py scan --from-console`.")
    result["done"].append(f"library: {_ne} effects" + (f", {len(_lib['templates'])} templates" if _lib["templates"] is not None else ""))

if FUSION_TITLE_SPIKE:
    _sp = {"title": SPIKE_TITLE, "text": SPIKE_TEXT, "problems": []}
    _orig = project.GetCurrentTimeline()
    _mp = project.GetMediaPool()
    _stl = _mp.CreateEmptyTimeline(f"SPIKE {SPIKE_TITLE} (delete me)") if _mp else None
    if not _stl:
        _sp["problems"].append("CreateEmptyTimeline returned nothing (a timeline of that name may exist — rename it)")
    else:
        project.SetCurrentTimeline(_stl)
        if SPIKE_VERTICAL:
            for _k, _v in (("useCustomSettings", "1"), ("timelineResolutionWidth", "1080"),
                           ("timelineResolutionHeight", "1920")):
                _stl.SetSetting(_k, _v)
            _sp["resolution"] = [_stl.GetSetting("timelineResolutionWidth"), _stl.GetSetting("timelineResolutionHeight")]
            if _sp["resolution"] != ["1080", "1920"]:
                _sp["problems"].append(f"the scratch timeline reads {_sp['resolution']}, not 1080×1920")
        _ti = _stl.InsertFusionTitleIntoTimeline(SPIKE_TITLE)
        _sp["inserted"] = bool(_ti)
        _sp["text_inputs"], _sp["tools"] = [], []
        if not _ti:
            _sp["problems"].append(f"InsertFusionTitleIntoTimeline({SPIKE_TITLE!r}) returned nothing — check the "
                                   f"name against the Effects Library")
        else:
            _comp = _ti.GetFusionCompByIndex(1) if (_ti.GetFusionCompCount() or 0) >= 1 else None
            _sp["comp"] = bool(_comp)
            if not _comp:
                _sp["problems"].append("the title has no Fusion composition the script can reach")
            else:
                for _t in (_comp.GetToolList(False) or {}).values():
                    try:
                        _tn = _t.Name
                    except Exception:                                       # noqa: BLE001
                        _tn = "?"
                    _sp["tools"].append(_tn)
                    try:
                        _was = _t.GetInput("StyledText")
                    except Exception:                                       # noqa: BLE001
                        _was = None
                    if _was is None:
                        continue
                    _t.SetInput("StyledText", SPIKE_TEXT)
                    _sp["text_inputs"].append({"tool": _tn, "was": _was,
                                               "reads_back": _t.GetInput("StyledText") == SPIKE_TEXT})
                if not _sp["text_inputs"]:
                    _sp["problems"].append(f"no tool takes StyledText — the tools are {_sp['tools']}: the text sits "
                                           f"behind a macro control this spike does not know yet")
                elif not all(_x["reads_back"] for _x in _sp["text_inputs"]):
                    _sp["problems"].append("a text input did not read back what was set")
        if _orig:
            project.SetCurrentTimeline(_orig)
            _sp["returned_to"] = _orig.GetName()
    _sp["verdict"] = "PROVEN" if not _sp["problems"] and _sp.get("text_inputs") else "NOT PROVEN"
    print(f"  Title spike {SPIKE_TITLE!r}: {_sp['verdict']}"
          + "".join(f"\n    ⚠ {_p}" for _p in _sp["problems"]))
    print("  Look at the scratch timeline's layout on the Edit page (title-safe, the 9:16 frame), grab a still, "
          "then delete the timeline by hand. A PROVEN spike is half the proof: the layout is the other half.")
    result["spike"] = _sp
    result["done"].append(f"title spike: {_sp['verdict']}")



def _find_clip(folder, name):
    for _c in (folder.GetClipList() or []):
        try:
            if _c.GetName() == name:
                return _c
        except Exception:                                                   # noqa: BLE001
            pass
    for _sub in (folder.GetSubFolderList() or []):
        _hit = _find_clip(_sub, name)
        if _hit:
            return _hit
    return None


def _video_track(tl, name, create=True):
    for _i in range(1, int(tl.GetTrackCount("video") or 0) + 1):
        if (tl.GetTrackName("video", _i) or "").strip().lower() == name.strip().lower():
            return _i, False
    if not create:
        return None, False
    tl.AddTrack("video")
    _i = int(tl.GetTrackCount("video"))
    tl.SetTrackName("video", _i, name)
    return _i, True


def _tc(frame, fps):
    _f = int(round(fps)) or 24
    _h, _r = divmod(int(frame), 3600 * _f)
    _m, _r = divmod(_r, 60 * _f)
    _s, _fr = divmod(_r, _f)
    return f"{_h:02d}:{_m:02d}:{_s:02d}:{_fr:02d}"


def _lock_all_but(tl, keep):
    """Lock every video, audio and subtitle track except video `keep`; return what to put back."""
    _prev = []
    for _kind in ("video", "audio", "subtitle"):
        for _i in range(1, int(tl.GetTrackCount(_kind) or 0) + 1):
            try:
                _was = bool(tl.GetIsTrackLocked(_kind, _i))
            except Exception:                                               # noqa: BLE001
                continue
            _want = not (_kind == "video" and _i == keep)
            if _was != _want:
                tl.SetTrackLock(_kind, _i, _want)
                _prev.append((_kind, _i, _was))
    return _prev


def _restore_locks(tl, prev):
    for _kind, _i, _was in prev:
        try:
            tl.SetTrackLock(_kind, _i, _was)
        except Exception:                                                   # noqa: BLE001
            pass


def _as_input(v):
    return {1: v[0], 2: v[1]} if isinstance(v, (list, tuple)) and len(v) == 2 else v


def _same(a, b):
    if isinstance(b, (list, tuple)) and isinstance(a, dict):
        return all(abs(float(a.get(k + 1, a.get(str(k + 1), 1e9))) - float(x)) < 1e-4 for k, x in enumerate(b))
    if isinstance(b, float) or isinstance(a, float):
        try:
            return abs(float(a) - float(b)) < 1e-4
        except (TypeError, ValueError):
            return False
    return a == b


def _write(comp, tool, inputs):
    """Inputs written inside comp.Lock()/Unlock() (measured: SetInput alone read back '' later); returns the misses."""
    try:
        comp.Lock()
    except Exception:                                                       # noqa: BLE001
        pass
    try:
        for _k, _v in inputs.items():
            if _k == "StyledText":
                tool.StyledText = _v
            else:
                tool.SetInput(_k, _as_input(_v))
    finally:
        try:
            comp.Unlock()
        except Exception:                                                   # noqa: BLE001
            pass
    return [_k for _k, _v in inputs.items() if not _same(tool.GetInput(_k), _v)]


def _fps_of(tl):
    return float(tl.GetSetting("timelineFrameRate") or 0) or 24.0


def _version_at_least(want):
    """Resolve's version (GetVersionString '21.1.2.5') against a tuple: False when it cannot be read."""
    _v = _resolve_version() or ""
    try:
        _got = tuple(int(_x) for _x in str(_v).split(".")[:3])
    except ValueError:
        return False
    return _got + (0,) * (3 - len(_got)) >= tuple(want)


def _is_transition(_it):
    try:
        return _it.GetType() == "transition"
    except Exception:                                                       # noqa: BLE001
        return False


def _overlaps(tl, vt, rec, n):
    return [_x for _x in (tl.GetItemListInTrack("video", vt) or []) if not _is_transition(_x)
            and _x.GetStart() < rec + n and rec < _x.GetStart() + _x.GetDuration()]


def _comp_count(_it):
    try:
        return int(_it.GetFusionCompCount() or 0)
    except Exception:                                                       # noqa: BLE001
        return 0


def _insert_at(tl, name, rec, n, target):
    """A Fusion title `name` at absolute frame `rec` for `n` frames on video track `target`, nothing else moved.
    Measured on 21.1.1 (a supplement ad job): the insert lands on the topmost UNLOCKED track at the playhead for the marks and
    ripples every other unlocked track; under a locked track it fails silently. So when the target is not the top track,
    a scratch top track takes the insert with everything else locked, and 21.1.2's TimelineItem.SetPosition moves it
    down [stub until L1-a]. Returns (item, row)."""
    _row = {}
    _top = int(tl.GetTrackCount("video") or 0)
    _tmp = None
    if target != _top:
        tl.AddTrack("video")
        _tmp = int(tl.GetTrackCount("video"))
        tl.SetTrackName("video", _tmp, "_cine-insert")
    _lane = _tmp or target
    _prev = _lock_all_but(tl, _lane)
    _it = None
    try:
        tl.SetCurrentTimecode(_tc(rec, _fps_of(tl)))
        tl.SetMarkInOut(rec, rec + n - 1)
        _it = tl.InsertFusionTitleIntoTimeline(name)
        try:
            tl.ClearMarkInOut()
        except Exception:                                                   # noqa: BLE001
            pass
    finally:
        _restore_locks(tl, _prev)
    _row["inserted"] = _it is not None
    _row["locks_restored"] = len(_prev)
    if _tmp is None:
        return _it, _row
    if _it is not None:
        _ok = False
        try:
            _ok = bool(_it.SetPosition({"trackIndex": int(target), "startFrame": int(rec)}))
        except Exception as _e:                                             # noqa: BLE001 — pre-21.1.2: no SetPosition
            _row["move_error"] = f"SetPosition: {_e}"
        try:
            _where = list(_it.GetTrackTypeAndIndex() or [])
        except Exception:                                                   # noqa: BLE001
            _where = []
        _row["moved"] = bool(_ok and _where == ["video", int(target)] and int(_it.GetStart()) == int(rec))
        if not _row["moved"] and not _row.get("move_error"):
            _row["move_error"] = (f"SetPosition returned {_ok}; the title reads back on {_where or '?'} at "
                                  f"{_it.GetStart() - tl.GetStartFrame()} (wanted video {target} at {rec - tl.GetStartFrame()})")
    if not [_x for _x in (tl.GetItemListInTrack("video", _tmp) or []) if not _is_transition(_x)]:
        tl.DeleteTrack("video", _tmp)
        _row["scratch_removed"] = True
    else:
        _row["scratch_left"] = (f"V{_tmp} _cine-insert still holds the title — it did not move onto V{target}: move it by "
                                f"hand, or delete it and the track")
    return _it, _row


def _cine(_comp, main="TT_Main"):
    """The generated template's identity, read back from Resolve: TT_Main's CustomData.cine."""
    try:
        _t = _comp.FindTool(main) if _comp else None
        return dict(_t.GetData("cine") or {}) if _t else {}
    except Exception:                                                       # noqa: BLE001
        return {}


def _active_comp(_it, tpl, route):
    """(comp, how): the card's generated title active on the item — the installed template's own comp, or the generated
    .comp imported onto a stock Text+ and loaded. Anything else is refused: a title from another card is not the card's."""
    _main = tpl.get("main") or "TT_Main"
    _n = _comp_count(_it)
    _c = _it.GetFusionCompByIndex(_n) if _n else None
    _id = _cine(_c, _main)
    if _id.get("card_sha256") == tpl.get("card_sha256"):
        return _c, ("template" if _n == 1 else "import")
    if route == "template":
        if _id.get("card_sha256"):
            return None, (f"the title on the timeline was generated from another card ({str(_id['card_sha256'])[:8]}; this "
                          f"card is {str(tpl.get('card_sha256'))[:8]}) — rebuild and reinstall (fusion_titles.py build)")
        return None, "the inserted title is not the card's template (a stock title came back) — TITLE_ROUTE auto imports it"
    # a stock Text+ (the import route), or this item from an earlier card on a re-run: the card's comp imported over it
    _c = _it.ImportFusionComp(tpl["comp"])
    if not _c:
        return None, f"ImportFusionComp({tpl['comp']!r}) returned nothing — is the path on this machine?"
    try:
        _names = list(_it.GetFusionCompNameList() or [])
    except Exception:                                                       # noqa: BLE001
        _names = []
    if _names:
        _it.LoadFusionCompByName(_names[-1])
        _c = _it.GetFusionCompByName(_names[-1]) or _c
    if _cine(_c, _main).get("card_sha256") != tpl.get("card_sha256"):
        return None, "the imported comp does not carry this card's hash — rebuild (fusion_titles.py build)"
    for _old in _names[:-1]:             # the stock Text+ (or an earlier card's comp): not the last, so it can go —
        try:                             # the item then carries the card's comp alone, whichever Resolve shows
            _it.DeleteFusionCompByName(_old)
        except Exception:                                                   # noqa: BLE001
            pass
    return _c, "import"


def _font_ok(fam, style):
    """True / False / None (unknown): is the face in Fusion's font list? The list's shape is [stub] (L1-e): a dict of
    family → styles, or of files → names; both are read, case- and space-blind."""
    if not fam:
        return None
    try:
        _fl = resolve.Fusion().FontManager().GetFontList()
    except Exception:                                                       # noqa: BLE001
        return None
    if _fl is None:
        return None
    _norm = lambda _s: "".join(str(_s).lower().split())                     # noqa: E731
    _f, _st = _norm(fam), _norm(style or "")

    def _has(_node, _in_family=False):
        if isinstance(_node, dict):
            for _k, _v in _node.items():
                _kn = _norm(_k)
                if _kn == _f and (not _st or _has_style(_v)):
                    return True
                if _has(_v):
                    return True
            return False
        if isinstance(_node, (list, tuple)):
            return any(_has(_x) for _x in _node)
        _n = _norm(_node)
        return _f in _n and (not _st or _st in _n)

    def _has_style(_v):
        if isinstance(_v, dict):
            return any(_norm(_k) == _st or _has_style(_x) for _k, _x in _v.items())
        if isinstance(_v, (list, tuple)):
            return any(_has_style(_x) for _x in _v)
        return _st in _norm(_v)
    return bool(_has(_fl))


def _still(tl, frame_abs, path):
    """A still of the timeline at an absolute frame: Timeline.ExportFrame (21.1.2 — no playhead move, no page needed),
    else the current frame as a still (the playhead moved there)."""
    _off = int(frame_abs - tl.GetStartFrame())
    try:
        _r = tl.ExportFrame(_off, {"outputType": "file", "filePath": path})
        if (_r or {}).get("success"):
            return path
    except Exception:                                                       # noqa: BLE001
        pass
    tl.SetCurrentTimecode(_tc(frame_abs, _fps_of(tl)))
    return path if project.ExportCurrentFrameAsStill(path) else None


def _track_for(t, default_track, kind_track):
    if kind_track is None:
        return default_track
    return kind_track.get(t.get("kind") or "") or kind_track.get(t.get("kit") or "") or default_track


def _place_title(tl, t, track_name, tpl=None, template="Text+", layout=None, route="auto", still_dir=None, colour="Orange"):
    """One title row: its slot on its named track, the insert (scratch track + move when the track is not on top), the
    card's comp (installed, or imported), the words written and read back, the read-back (font as installed, card hash,
    fps, position, the fold), its name cine:<id>, a still. A row with a `problem` was not placed: STOP and report it."""
    _fps = _fps_of(tl)
    _base = tl.GetStartFrame()
    _rec = _base + int(round(float(t["at_s"]) * _fps))
    _n = max(1, int(round(float(t["duration_s"]) * _fps)))
    _vt, _made = _video_track(tl, track_name)
    _row = {"id": t["id"], "kind": t.get("kind"), "track": track_name, "track_index": _vt, "track_added": _made,
            "record_frame": _rec - _base, "frames": _n, "set": t.get("text")}
    if tpl:
        _row["template"] = tpl.get("name")
    if (tl.GetTrackName("video", _vt) or "").strip().lower() != track_name.strip().lower():
        _row["problem"] = f"V{_vt} did not take the name {track_name!r} — name it by hand; the QA renders find it by name"
        return _row, None
    _over = _overlaps(tl, _vt, _rec, _n)
    _mine = [_x for _x in _over if (_x.GetName() or "") == f"cine:{t['id']}" and _x.GetStart() == _rec]
    _legacy = [] if (_mine or tpl) else [_x for _x in _over if _x.GetStart() == _rec and _comp_count(_x)]
    _others = [_x for _x in _over if _x not in _mine and _x not in _legacy]
    _it = (_mine or _legacy or [None])[0]
    if _it is not None:
        _row["already"] = True
    elif _others:
        _row["problem"] = (f"the slot on {track_name!r} at {float(t['at_s']):.2f} s is taken by {_others[0].GetName()!r} — "
                           f"move that item, or move the spec (nothing is placed over another item)")
        return _row, None
    else:
        _top = _vt == int(tl.GetTrackCount("video") or 0)
        if not _top and not _version_at_least((21, 1, 2)):
            _row["problem"] = (f"V{_vt} {track_name!r} is not the top video track: an insert lands only on the topmost "
                               f"unlocked track (measured, 21.1.1), and Resolve {_resolve_version()} has no "
                               f"TimelineItem.SetPosition to move it down (21.1.2 has). Place the text tracks bottom-up "
                               f"(Titles before Disclosure before Supers), or empty and remove the tracks above it")
            return _row, None
        _name = (tpl["name"] if route != "import" else "Text+") if tpl else template
        _it, _ins = _insert_at(tl, _name, _rec, _n, _vt)
        if _it is None and tpl and route == "auto" and _name != "Text+":
            _row["template_missing"] = f"{_name!r} is not installed in Resolve — the import route (a stock Text+)"
            _it, _ins = _insert_at(tl, "Text+", _rec, _n, _vt)
        _row.update(_ins)
        if _it is None:
            _row["problem"] = (f"not placed: InsertFusionTitleIntoTimeline({_name!r}) returned nothing (the name, or the "
                               f"slot) — nothing was rendered instead")
            return _row, None
        try:
            _it.SetName(f"cine:{t['id']}")          # named at once: a re-run finds it, whatever stops this row below
        except Exception:                                                   # noqa: BLE001
            pass
        if _row.get("moved") is False:
            _row["problem"] = _row.get("scratch_left") or _row.get("move_error") or "the title did not move onto its track"
            return _row, _it
    if not _comp_count(_it):
        _row["problem"] = "not placed: the returned item has no Fusion composition (the slot taken, or the track not on top)"
        return _row, _it
    if tpl:
        _comp, _how = _active_comp(_it, tpl, route)
        _row["route"] = _how if _comp is not None else None
        if _comp is None:
            _row["problem"] = _how
            return _row, _it
        _main_name = tpl.get("main") or "TT_Main"
        _main = _comp.FindTool(_main_name)
        if _main is None:
            _row["problem"] = f"the comp has no {_main_name} tool — rebuild the template"
            return _row, _it
        _words = dict(t.get("words") or {_main_name: t.get("text")})
        _extra = _words.pop("_extra", None)
        _set, _miss = [], []
        for _tn, _w in _words.items():
            _tool = _comp.FindTool(_tn)
            if _tool is None:
                _set.append({"tool": _tn, "reads_back": False})
                _miss.append(f"{_tn}: no such tool")
                continue
            _m = _write(_comp, _tool, {"StyledText": _w})
            _set.append({"tool": _tn, "reads_back": not _m})
        for _tn, _xy in (t.get("place") or {}).items():
            _tool = _comp.FindTool(_tn)
            if _tool is not None:
                _miss += [f"{_tn}:{_m}" for _m in _write(_comp, _tool, {"Center": _xy})]
        for _tn, _ins in (t.get("inputs") or {}).items():          # per-title inputs (a spec's own plate)
            _tool = _comp.FindTool(_tn)
            if _tool is not None:
                _miss += [f"{_tn}:{_m}" for _m in _write(_comp, _tool, _ins)]
        if t.get("emphasis") and (layout or {}).get("_emphasis") and not _main.GetInput("Enabled3"):
            _miss += [f"emphasis:{_m}" for _m in _write(_comp, _main, layout["_emphasis"])]
        _row["text"] = _set
        _row["reads_back"] = bool(_set) and all(_y["reads_back"] for _y in _set)
        if _miss:
            _row["layout_misses"] = sorted(set(_miss))
        if _extra:
            _row["problem"] = (f"words with no tool in the template: {', '.join(_extra)} — they would be lost; a field the "
                               f"kit does not have is a question for the card, not a smaller title")
        _id = _cine(_comp, _main_name)
        _row["card_sha256"] = _id.get("card_sha256")
        if _id.get("fps") and abs(float(_id["fps"]) - _fps) > 0.01:
            _row["problem"] = (f"the template was generated at {float(_id['fps']):g} fps and the timeline runs at {_fps:g} — "
                               f"its keys are in frames: fusion_titles.py build --fps {_fps:g}")
        try:
            _row["font"], _row["style"] = _main.GetInput("Font"), _main.GetInput("Style")
        except Exception:                                                   # noqa: BLE001
            _row["font"], _row["style"] = None, None
        _row["font_installed"] = _font_ok(_row["font"], _row["style"]) if CHECK_FONTS else None
        try:
            _fo = _comp.FindTool("TT_Fold")
            _row["fold"] = _fo.SourceTime.GetExpression() if _fo is not None else None
        except Exception:                                                   # noqa: BLE001
            _row["fold"] = None
        try:
            _row["render_end"] = (_comp.GetAttrs() or {}).get("COMPN_RenderEnd")
        except Exception:                                                   # noqa: BLE001
            _row["render_end"] = None
        _X = int(((tpl.get("motion") or {}).get("X")) or 0)
        if _X and not _row["fold"]:
            _row["problem"] = "the comp's TT_Fold carries no expression — the exit would not land on the clip's end"
        elif _X and _row["render_end"] is not None and abs(float(_row["render_end"]) - (_n - 1)) > 0.5:
            _row["problem"] = (f"the comp ends at frame {_row['render_end']}, the clip at {_n - 1}: the folded exit would "
                               f"land off the clip's end [L1-d] — re-time the title, or re-key its exit")
        if _row["font_installed"] is False and not _row.get("problem"):
            _row["font_missing"] = (f"Resolve's font list has no {_row['font']} {_row['style'] or ''} — ADD_FONTS with the "
                                    f"card's file, or install it to ~/Library/Fonts and restart Resolve")
    else:
        _comp = _it.GetFusionCompByIndex(1)
        _tools = list((_comp.GetToolList(False, "TextPlus") or {}).values()) if _comp else []
        _tools = [_x for _x in _tools if _x.GetInput("StyledText") is not None]
        _named = {}
        for _x in _tools:
            try:
                _named[(_x.Name or "").lower()] = _x
            except Exception:                                               # noqa: BLE001
                pass
        _lay = {_k: _v for _k, _v in dict((layout or {}).get(t.get("kind") or "", (layout or {}).get("*", {})) or {}).items()
                if not _k.startswith("_")}
        if t.get("emphasis") and not _lay.get("Enabled3"):
            _lay.update((layout or {}).get("_emphasis") or {})
        _set, _miss = [], []
        for _k, _v in (t.get("fields") or {}).items():
            _x = _named.get(_k.lower())
            if _x is not None:
                _m = _write(_comp, _x, {**_lay, "StyledText": _v})
                _set.append({"tool": _k, "reads_back": "StyledText" not in _m})
                _miss += [m for m in _m if m != "StyledText"]
        if not _set and _tools:
            _m = _write(_comp, _tools[0], {**_lay, "StyledText": t["text"]})
            _set.append({"tool": next((k for k, v in _named.items() if v is _tools[0]), "?"),
                         "reads_back": "StyledText" not in _m})
            _miss += [m for m in _m if m != "StyledText"]
        _row["text"] = _set
        _row["reads_back"] = bool(_set) and all(_y["reads_back"] for _y in _set)
        if _miss:
            _row["layout_misses"] = sorted(set(_miss))
        try:
            _row["font"] = _tools[0].GetInput("Font") if _tools else None
        except Exception:                                                   # noqa: BLE001
            _row["font"] = None
        if not _tools:
            _row["problem"] = "the template has no Text+ tool the script can reach (a macro hides it) — set the words by hand"
        if t.get("font") and _row.get("font") and _row["font"] != t["font"]:
            _row["font_mismatch"] = f"the template's font is {_row['font']!r}, the title card's anchor is {t['font']!r}"
    _row["start_ok"] = _it.GetStart() == _rec
    _row["duration_ok"] = _it.GetDuration() == _n
    if not _row.get("problem") and not (_row["start_ok"] and _row["duration_ok"]):
        _row["problem"] = (f"it sits at {(_it.GetStart() - _base) / _fps:.2f} s for {_it.GetDuration()} frames, not at "
                           f"{float(t['at_s']):.2f} s for {_n} — move and trim it by hand")
    try:
        _it.SetName(f"cine:{t['id']}")
    except Exception:                                                       # noqa: BLE001
        pass
    try:
        _it.SetClipColor(colour)
    except Exception:                                                       # noqa: BLE001
        pass
    if still_dir:
        _row["still"] = _still(tl, _rec + _n // 2, f"{still_dir}/{t['id']}.png")
    return _row, _it


def _place_text(items, template, track_name, kind, layout=None, templates=None, route="auto", kind_track=None, tl=None):
    """Each item {id, kind, at_s, duration_s, text, words?, fields?, font?} as a Fusion title on its named video track
    (TITLE_KIND_TRACK: Titles · Supers · Disclosure): the card's generated template when TITLE_TEMPLATES has its kind,
    else the stock `template` with `layout`'s static inputs. Returns the placement report; a row with a problem is a STOP."""
    tl = tl or timeline
    _rep = {"kind": kind, "template": template, "track": track_name, "placed": [], "problems": [],
            "templates": "generated" if templates else "stock (no motion, no plate: the card generates no titles yet)"}
    _still_dir = STILLS_DIR if (STILLS_DIR and "REPLACE-WITH-" not in STILLS_DIR) else None
    _tracks = {}
    for _t in items:
        _tn = _track_for(_t, track_name, kind_track)
        _tpl = (templates or {}).get(_t.get("kind") or "")
        _row, _it = _place_title(tl, _t, _tn, _tpl, template, layout, route, _still_dir,
                                 "Orange" if kind == "titles" else "Teal")
        _tracks[_tn] = _row.get("track_index")
        _rep["placed"].append(_row)
    _rep["tracks"] = _tracks
    _rep["locks_restored"] = sum(int(r.get("locks_restored") or 0) for r in _rep["placed"])
    _rep["track_index"] = _tracks.get(track_name) or (next(iter(_tracks.values()), None))
    if not items:
        _vt, _made = _video_track(tl, track_name, create=False)
        _rep["track_index"] = _vt
    _bad = [r["id"] for r in _rep["placed"] if r.get("problem") or not r.get("reads_back")
            or r.get("font_installed") is False]
    _rep["verdict"] = "PLACED" if items and not _bad and not _rep["problems"] else (
        "NOTHING TO PLACE" if not items else "NOT ALL PLACED")
    _rep["problems"] += [f"{r['id']}: {r['problem']}" for r in _rep["placed"] if r.get("problem")]
    print(f"  {kind}: {len(items) - len(_bad)}/{len(items)} placed and read back on "
          + ", ".join(f"V{_v} {_k!r}" for _k, _v in _tracks.items()) + f" ({_rep['templates']})"
          + "".join(f"\n    ⛔ {r['id']}: {r.get('problem') or r.get('font_missing') or 'the words did not read back'}"
                    for r in _rep["placed"] if r["id"] in _bad)
          + "".join(f"\n    ⚠ {r['id']}: {r['template_missing']}" for r in _rep["placed"] if r.get("template_missing"))
          + "".join(f"\n    ⚠ {r['id']}: {r['font_mismatch']}" for r in _rep["placed"] if r.get("font_mismatch"))
          + "".join(f"\n    ⚠ {r['id']}: layout not taken: {', '.join(r['layout_misses'])}" for r in _rep["placed"]
                    if r.get("layout_misses"))
          + ("\n  ⛔ STOP: report the rows above. Never render a title elsewhere to get past a row that did not place."
             if _bad else "")
          + ("\n  Look at the stills (a contact sheet), not a screenshot." if _still_dir else ""))
    return _rep


def _moments(row, tpl, tl):
    """The five review moments of a placed title, as absolute frames: entrance · legible · mid · exit · gone."""
    _m = (tpl or {}).get("motion") or {}
    _e, _X = float(_m.get("e") or 0), int(_m.get("X") or 0)
    _n = int(row["frames"])
    _rec = tl.GetStartFrame() + int(row["record_frame"])
    _leg = min(_n - 1, int(-(-_e // 1)) + 1)
    _ex = max(_leg, _n - _X - 1)
    return [("entrance", _rec + int(_e // 2)), ("legible", _rec + _leg), ("mid", _rec + (_leg + _ex) // 2),
            ("exit", _rec + _ex), ("gone", _rec + _n - 1)]


def _snapshot(tl):
    _base = tl.GetStartFrame()
    _snap = {"timeline": tl.GetName(), "tracks": {}}
    for _kind in ("video", "audio", "subtitle"):
        for _i in range(1, int(tl.GetTrackCount(_kind) or 0) + 1):
            try:
                _en = bool(tl.GetIsTrackEnabled(_kind, _i))
            except Exception:                                               # noqa: BLE001
                _en = None
            try:
                _lk = bool(tl.GetIsTrackLocked(_kind, _i))
            except Exception:                                               # noqa: BLE001
                _lk = None
            _items = tl.GetItemListInTrack(_kind, _i) or []
            _snap["tracks"][f"{_kind}{_i}"] = {"name": tl.GetTrackName(_kind, _i), "enabled": _en, "locked": _lk,
                                               "items": [[_x.GetName(), _x.GetStart() - _base, _x.GetDuration()]
                                                         for _x in _items]}
    return _snap


def _invariant(before, after):
    """What a structural edit lost: tracks gone or renamed, tracks disabled, items gone (by name), fewer items."""
    _d = []
    _by_name = {v.get("name"): (k, v) for k, v in (after.get("tracks") or {}).items()}
    for _k, _v in (before.get("tracks") or {}).items():
        _hit = _by_name.get(_v.get("name"))
        if not _hit:
            _d.append(f"{_k} {_v.get('name')!r} is gone (or renamed)")
            continue
        _k2, _w = _hit
        if _v.get("enabled") and _w.get("enabled") is False:
            _d.append(f"{_v.get('name')!r} ({_k2}) was enabled, now disabled")
        _names_b = sorted(x[0] for x in _v.get("items") or [])
        _names_a = sorted(x[0] for x in _w.get("items") or [])
        _lost = sorted(set(_names_b) - set(_names_a))
        if _lost:
            _d.append(f"{_v.get('name')!r} lost {len(_lost)} item(s): {', '.join(_lost[:6])}" + (" …" if len(_lost) > 6 else ""))
        elif len(_names_a) < len(_names_b):
            _d.append(f"{_v.get('name')!r} holds {len(_names_a)} item(s), had {len(_names_b)}")
    return _d


_native = {}
if NAME_TRACKS:
    _named_now = []
    for _i, _nm in enumerate(TRACK_LAYOUT, start=1):
        if _i > int(timeline.GetTrackCount("video") or 0):
            break
        _cur = (timeline.GetTrackName("video", _i) or "").strip()
        if not _cur or _cur.lower() in (f"video {_i}", f"v{_i}"):
            timeline.SetTrackName("video", _i, _nm)
            _named_now.append(f"V{_i} {_nm}" + ("" if timeline.GetTrackName("video", _i) == _nm else " (did not take)"))
    print("  Track names: " + (", ".join(_named_now) or "nothing to name — every track already has a name"))
    _native["track_names"] = _named_now

if SNAPSHOT_TIMELINE or EXPECT_SNAPSHOT:
    _snap_before = EXPECT_SNAPSHOT or None
    _native["snapshot"] = _snapshot(timeline)

if INSTALL_TITLE_TEMPLATES:
    # ⚡ v2.45 route T: the generated .drfx installed [stub: fusion.InstallFile — does the Effects Library list it without
    # a restart? L1-f]. Route auto falls back to importing the comp onto a stock Text+ either way.
    _ins = {"drfx": DRFX_PATH, "problems": []}
    if "REPLACE-WITH-" in DRFX_PATH:
        _ins["problems"].append("DRFX_PATH is a placeholder — native.py console <job> --install fills it")
    else:
        try:
            _ins["installed"] = bool(resolve.Fusion().InstallFile(DRFX_PATH, True))
        except Exception as _e:                                             # noqa: BLE001
            _ins["installed"] = False
            _ins["problems"].append(f"InstallFile: {_e}")
    print(f"  Title templates: {'installed' if _ins.get('installed') else 'NOT installed'} from {DRFX_PATH}"
          + "".join(f"\n    ⚠ {_p}" for _p in _ins["problems"])
          + ("\n  (TITLE_ROUTE auto: a template Resolve does not list is imported onto a stock Text+ instead)"
             if not _ins.get("installed") else ""))
    _native["install"] = _ins
    result["done"].append(f"title templates: {'installed' if _ins.get('installed') else 'not installed'}")

if CHECK_FONTS:
    _faces = sorted({(_v.get("font"), _v.get("style")) for _v in (TITLE_TEMPLATES or {}).values() if _v.get("font")})
    _fr = {"faces": [], "added": [], "problems": []}
    for _fam, _sty in _faces:
        _ok = _font_ok(_fam, _sty)
        if _ok is False and ADD_FONTS and FONT_FILES:
            for _ff in FONT_FILES:
                try:
                    _added = bool(resolve.Fusion().FontManager().AddFont(_ff))
                except Exception as _e:                                     # noqa: BLE001
                    _added = False
                    _fr["problems"].append(f"AddFont({_ff!r}): {_e}")
                _fr["added"].append({"file": _ff, "accepted": _added})
            _ok = _font_ok(_fam, _sty)
            if _ok is False:
                _fr["problems"].append(f"{_fam} {_sty}: AddFont did not make it appear — it may need a restart: install "
                                       f"the file to ~/Library/Fonts and restart Resolve (the one manual step, once per face)")
        elif _ok is False:
            _fr["problems"].append(f"{_fam} {_sty} is not in Resolve's font list — ADD_FONTS with the card's file, or "
                                   f"install it to ~/Library/Fonts and restart Resolve")
        _fr["faces"].append({"font": _fam, "style": _sty, "installed": _ok})
    print("  Fonts: " + (", ".join(f"{_x['font']} {_x['style']} {'✓' if _x['installed'] else ('✗' if _x['installed'] is False else '?')}"
                                   for _x in _fr["faces"]) or "no generated templates to check")
          + "".join(f"\n    ⚠ {_p}" for _p in _fr["problems"]))
    _native["fonts"] = _fr
    result["done"].append(f"fonts: {sum(1 for _x in _fr['faces'] if _x['installed'])}/{len(_fr['faces'])} installed")

if PLACE_TITLES:
    _native["titles"] = _place_text(TITLES, TITLE_TEMPLATE, TITLE_TRACK, "titles", TITLE_LAYOUT,
                                    templates=TITLE_TEMPLATES, route=TITLE_ROUTE, kind_track=TITLE_KIND_TRACK)
    result["done"].append(f"titles: {_native['titles']['verdict']}")

if PLACE_SUBTITLES and SUBTITLES_AS == "textplus":
    _native["captions"] = _place_text([{"id": f"C{_c['n']}", "kind": "caption", "at_s": _c["t0"],
                                        "duration_s": _c["t1"] - _c["t0"], "text": _c["text"]} for _c in SRT_CUES],
                                      CAPTION_TEMPLATE, CAPTION_TRACK, "captions", TITLE_LAYOUT, kind_track=None)
    result["done"].append(f"captions as Text+: {_native['captions']['verdict']}")
elif PLACE_SUBTITLES:
    _sp = {"srt": SRT_PATH, "cues": len(SRT_CUES), "problems": []}
    if "REPLACE-WITH-" in SRT_PATH:
        _sp["problems"].append("SRT_PATH is a placeholder — native.py console <job> --srt <file> fills it")
    else:
        _mp = project.GetMediaPool()
        _base = timeline.GetStartFrame()
        _fps = float(timeline.GetSetting("timelineFrameRate") or 0) or 24.0
        for _i in range(1, int(timeline.GetTrackCount("subtitle") or 0) + 1):     # already there: a re-run adds nothing
            _its = sorted(timeline.GetItemListInTrack("subtitle", _i) or [], key=lambda _x: _x.GetStart())
            if SRT_CUES and len(_its) == len(SRT_CUES) and all(
                    abs((_x.GetStart() - _base) - round(_c["t0"] * _fps)) <= 1 for _c, _x in zip(SRT_CUES, _its)):
                _sp.update(already=True, track=_i, items=len(_its))
                break
        _imp = [] if _sp.get("already") else (_mp.ImportMedia([SRT_PATH]) or [])
        _sp["imported"] = len(_imp)
        if _sp.get("already"):
            pass
        elif not _imp:
            _sp["problems"].append("ImportMedia did not take the .srt — import it by hand: File ▸ Import ▸ Subtitle")
        else:
            try:
                _sp["pool_type"] = _imp[0].GetClipProperty("Type")
            except Exception:                                               # noqa: BLE001
                _sp["pool_type"] = None
            _before = {_i: len(timeline.GetItemListInTrack("subtitle", _i) or [])
                       for _i in range(1, int(timeline.GetTrackCount("subtitle") or 0) + 1)}
            timeline.SetCurrentTimecode(_tc(_base, _fps))       # measured: at the start, the .srt lands at frame 0
            _mp.AppendToTimeline([_imp[0]])                      # never mediaType 3: it crashed Resolve (21.1.1)
            _st = next((_i for _i in range(1, int(timeline.GetTrackCount("subtitle") or 0) + 1)
                        if len(timeline.GetItemListInTrack("subtitle", _i) or []) > _before.get(_i, 0)), None)
            _items = sorted(timeline.GetItemListInTrack("subtitle", _st) or [], key=lambda _x: _x.GetStart()) if _st else []
            _sp["track"], _sp["items"] = _st, len(_items)
            if len(_items) != len(SRT_CUES):
                _sp["problems"].append(f"the subtitle track holds {len(_items)} subtitle(s), the .srt {len(SRT_CUES)} — check "
                                       f"it by eye, or import it by hand (File ▸ Import ▸ Subtitle)")
            _off = [f"cue {_c['n']}: {(_x.GetStart() - _base) / _fps:.2f} s, not {_c['t0']:.2f} s"
                    for _c, _x in zip(SRT_CUES, _items) if abs((_x.GetStart() - _base) - round(_c["t0"] * _fps)) > 1]
            if _off:
                _sp["problems"].append("the timing did not read back: " + "; ".join(_off[:4]))
    _sp["verdict"] = "PLACED" if not _sp["problems"] else "NOT PLACED"
    print(f"  Subtitles from {SRT_PATH}: {_sp['verdict']}" + "".join(f"\n    ⚠ {_p}" for _p in _sp["problems"])
          + ("\n  Next: style the track once (Inspector ▸ Track Style) from the card's caption tokens; render with "
             "BURN_SUBTITLES = True; then srt_qa.py burned on the render." if _sp["verdict"] == "PLACED" else ""))
    _native["subtitles"] = _sp
    result["done"].append(f"subtitles: {_sp['verdict']}")

if PLACE_TITLE_OPTIONS:
    # ⚡ v2.45: the review loop inside Resolve — options as Resolve's own stills, on a duplicate; nothing renders
    _opr = {"titles": {}, "problems": []}
    _odir = OPTIONS_DIR if "REPLACE-WITH-" not in OPTIONS_DIR else None
    if not _odir:
        _opr["problems"].append("OPTIONS_DIR is a placeholder — native.py console <job> --options <id> fills it")
    for _oid, _rows in ((TITLE_OPTIONS or {}).items() if _odir else []):
        _dname = f"{timeline.GetName()} — OPTIONS {_oid}"
        _dup = None
        for _i in range(1, int(project.GetTimelineCount() or 0) + 1):
            _x = project.GetTimelineByIndex(_i)
            if _x and _x.GetName() == _dname:
                _dup = _x
        _dup = _dup or timeline.DuplicateTimeline(_dname)
        if not _dup:
            _opr["problems"].append(f"{_oid}: DuplicateTimeline({_dname!r}) returned nothing")
            continue
        project.SetCurrentTimeline(_dup)
        _orep = {"timeline": _dname, "rows": [], "stills": []}
        try:
            for _t in _rows:
                _trk = f"Titles opt{int(_t.get('option') or 1)}"
                _tpl = (TITLE_TEMPLATES or {}).get(_t.get("kind") or "")
                _row, _it = _place_title(_dup, _t, _trk, _tpl, TITLE_TEMPLATE, TITLE_LAYOUT, TITLE_ROUTE, None, "Orange")
                _row["option"] = int(_t.get("option") or 1)
                _orep["rows"].append(_row)
            _nv = int(_dup.GetTrackCount("video") or 0)
            _textual = [_i for _i in range(1, _nv + 1) if (_dup.GetTrackName("video", _i) or "").strip().lower().startswith(
                ("titles", "supers", "disclosure", "captions"))]
            _was = {_i: _dup.GetIsTrackEnabled("video", _i) for _i in _textual}
            for _row in _orep["rows"]:
                if _row.get("problem"):
                    continue
                _tpl = (TITLE_TEMPLATES or {}).get(_row.get("kind") or "")
                _N = _row["option"]
                for _state in ("on", "off"):
                    for _i in _textual:
                        _dup.SetTrackEnable("video", _i, _state == "on" and _i == _row["track_index"])
                    for _mn, _f in _moments(_row, _tpl, _dup):
                        _pth = f"{_odir}/{_oid}/opt{_N}_{_mn}_{_state}.png"
                        _orep["stills"].append({"option": _N, "moment": _mn, "state": _state,
                                                "frame": _f - _dup.GetStartFrame(), "file": _still(_dup, _f, _pth)})
                    if OPTION_FRAMES == "all":
                        _pad = int(round(0.25 * _fps_of(_dup)))
                        _r0 = _dup.GetStartFrame() + int(_row["record_frame"])
                        for _f in range(max(_dup.GetStartFrame(), _r0 - _pad), _r0 + int(_row["frames"]) + _pad):
                            _off = _f - _dup.GetStartFrame()
                            _still(_dup, _f, f"{_odir}/{_oid}/opt{_N}/{_state}/f{_off:06d}.png")
            for _i, _on in _was.items():
                _dup.SetTrackEnable("video", _i, bool(_on))
        finally:
            project.SetCurrentTimeline(timeline)
        _orep["verdict"] = "STILLS" if _orep["rows"] and not [r for r in _orep["rows"] if r.get("problem")] else "NOT ALL PLACED"
        _opr["titles"][_oid] = _orep
        print(f"  Options {_oid}: {len(_orep['rows'])} on {_dname!r} — {len(_orep['stills'])} still(s) → {_odir}/{_oid}/"
              + "".join(f"\n    ⛔ opt{r['option']}: {r['problem']}" for r in _orep["rows"] if r.get("problem"))
              + "\n  Next: title_qa.py strip-native <job> --title " + _oid + " (the grid and the still checks), then the pick.")
    _native["options"] = _opr
    result["done"].append(f"options: {sum(len(v['rows']) for v in _opr['titles'].values())} placed on duplicates")


def _items_on(tl, track):
    """The video items (no transitions) on a track given by name or index: (index, items sorted by start)."""
    if isinstance(track, int):
        _vt = track
    else:
        _vt, _ = _video_track(tl, str(track or "Picture"), create=False)
        if _vt is None and str(track or "").lower() in ("picture", "v1", ""):
            _vt = 1
    if not _vt:
        return None, []
    return _vt, sorted([_x for _x in (tl.GetItemListInTrack("video", _vt) or []) if not _is_transition(_x)],
                       key=lambda _x: _x.GetStart())


if APPLY_TRANSITIONS:
    # ⚡ v2.45: the planned transitions (the card's grammar, resolve_library.py's installed names) at their cuts. 21.1's
    # AddTransition was measured on a simple Cross Dissolve between two solid clips; a pack transition through
    # category fusion/ofx and a cut with no handle are [stub] — so both neighbours are read back.
    _trr = {"rows": [], "problems": []}
    _fps = _fps_of(timeline)
    for _p in TRANSITION_PLAN or []:
        _r = {"id": _p.get("id"), "type": _p.get("type"), "category": _p.get("category"), "at_s": _p.get("at_s")}
        _vt, _its = _items_on(timeline, _p.get("track") or "Picture")
        _cut = timeline.GetStartFrame() + int(round(float(_p.get("at_s") or 0) * _fps))
        _out = next((_x for _x in _its if abs(_x.GetStart() + _x.GetDuration() - _cut) <= 1), None)
        _inn = next((_x for _x in _its if abs(_x.GetStart() - _cut) <= 1), None)
        _have = [_x for _x in (timeline.GetItemListInTrack("video", _vt) or []) if _is_transition(_x)
                 and _x.GetStart() <= _cut <= _x.GetStart() + _x.GetDuration()] if _vt else []
        if _have:
            _r["already"] = _have[0].GetName()
            _trr["rows"].append(_r)
            continue
        _host = _out if (_p.get("position") or "end") == "end" else _inn
        if _host is None:
            _r["problem"] = f"no item {'ends' if (_p.get('position') or 'end') == 'end' else 'starts'} at {float(_p.get('at_s') or 0):.2f} s on V{_vt}"
            _trr["rows"].append(_r)
            continue
        _before = [(_x.GetStart(), _x.GetDuration()) for _x in (_out, _inn) if _x is not None]
        _opts = {"type": _p.get("type") or "Cross Dissolve", "category": _p.get("category") or "simple",
                 "position": _p.get("position") or "end", "alignment": _p.get("alignment") or "center"}
        if _p.get("duration"):
            _opts["duration"] = int(_p["duration"])
        try:
            _tr = _host.AddTransition(_opts)
        except Exception as _e:                                             # noqa: BLE001
            _tr, _r["error"] = None, str(_e)
        _after = [(_x.GetStart(), _x.GetDuration()) for _x in (_out, _inn) if _x is not None]
        _r["placed"] = _tr is not None
        _r["neighbours_unchanged"] = _before == _after
        if _tr is not None:
            try:
                _r["read_back"] = {"name": _tr.GetName(), "frames": _tr.GetDuration(), "type": _tr.GetType()}
            except Exception:                                               # noqa: BLE001
                _r["read_back"] = None
        if _tr is None:
            _r["problem"] = (f"AddTransition({_opts['type']!r}, {_opts['category']}) returned nothing — the name, the category, "
                             f"or no handle on the clips" + (f": {_r['error']}" if _r.get("error") else ""))
        elif not _r["neighbours_unchanged"]:
            _r["problem"] = (f"the clips either side moved or shortened ({_before} → {_after}): the transition ate frames "
                             f"the cut needs — undo it (Edit ▸ Undo) and keep the hard cut, or generate the handles")
        _trr["rows"].append(_r)
    _bad = [_r for _r in _trr["rows"] if _r.get("problem")]
    print(f"  Transitions: {len(_trr['rows']) - len(_bad)}/{len(_trr['rows'])} placed and read back"
          + "".join(f"\n    ⛔ {_r.get('id') or _r.get('type')}: {_r['problem']}" for _r in _bad))
    _native["transitions"] = _trr
    result["done"].append(f"transitions: {len(_trr['rows']) - len(_bad)}/{len(_trr['rows'])}")


def _find_item(tl, name):
    for _i in range(1, int(tl.GetTrackCount("video") or 0) + 1):
        for _x in (tl.GetItemListInTrack("video", _i) or []):
            if not _is_transition(_x) and (_x.GetName() or "") == name:
                return _x
    return None


if APPLY_EFFECTS:
    # ⚡ v2.45: the installed effects on named items. A Fusion effect's inputs are reachable through its comp; an OFX
    # effect's are not (the 21.1.2 API sets no OFX parameter) — it goes on with its defaults and is flagged.
    _efr = {"rows": [], "manual": []}
    for _p in EFFECT_PLAN or []:
        _cat, _eid = _p.get("category") or "fusion", _p.get("effect_id") or ""
        _r = {"id": _p.get("id"), "item": _p.get("item"), "effect": _p.get("name") or _eid, "category": _cat}
        _it = _find_item(timeline, _p.get("item") or "")
        if _it is None:
            _r["problem"] = f"no video item named {_p.get('item')!r} (PLACE_TITLES names its titles cine:<id>)"
            _efr["rows"].append(_r)
            continue
        try:
            _have = [_e for _e in (_it.GetEffects(_cat) or []) if ((_e.GetInfo() or {}).get("id") == _eid)]
        except Exception:                                                   # noqa: BLE001
            _have = []
        _eff = _have[0] if _have else None
        _r["already"] = bool(_have)
        if _eff is None:
            try:
                _eff = _it.AddEffect(_cat, _eid)
            except Exception as _e:                                         # noqa: BLE001
                _eff, _r["error"] = None, str(_e)
        _r["applied"] = _eff is not None
        if _eff is None:
            _r["problem"] = f"AddEffect({_cat!r}, {_eid!r}) returned nothing" + (f": {_r['error']}" if _r.get("error") else "")
        elif _cat == "fusion" and _p.get("inputs"):
            _c = _eff.GetFusionComp()
            _set = {}
            for _k, _v in (_p.get("inputs") or {}).items():
                _hit = False
                for _tool in ((_c.GetToolList(False) or {}).values() if _c else []):
                    if _tool.GetInput(_k) is not None:
                        _m = _write(_c, _tool, {_k: _v})
                        _hit = not _m
                        break
                _set[_k] = _hit
            _r["inputs"] = _set
            if not all(_set.values()):
                _r["problem"] = "inputs that did not take: " + ", ".join(_k for _k, _v in _set.items() if not _v)
        if _cat == "ofx" and _eff is not None:
            _r["manual"] = _p.get("manual") or ("OFX parameters are not scriptable (21.1.2): applied with its defaults — "
                                                "pick its settings in the Inspector")
            _efr["manual"].append(f"{_p.get('item')}: {_r['effect']} — {_r['manual']}")
        _efr["rows"].append(_r)
    _bad = [_r for _r in _efr["rows"] if _r.get("problem")]
    print(f"  Effects: {len(_efr['rows']) - len(_bad)}/{len(_efr['rows'])} applied"
          + "".join(f"\n    ⛔ {_r.get('item')}: {_r['problem']}" for _r in _bad)
          + "".join(f"\n    ✋ manual: {_m}" for _m in _efr["manual"]))
    _native["effects"] = _efr
    result["done"].append(f"effects: {len(_efr['rows']) - len(_bad)}/{len(_efr['rows'])}, {len(_efr['manual'])} manual")

if EXPECT_SNAPSHOT:
    _after = _snapshot(timeline)
    _native["snapshot_after"] = _after
    _native["invariant"] = _invariant(EXPECT_SNAPSHOT, _after)
    print("  Timeline invariant: " + ("held — every track and item from before is still there, named and enabled"
                                      if not _native["invariant"] else
                                      "BROKEN:" + "".join(f"\n    ⚠ {_x}" for _x in _native["invariant"])))
    result["done"].append(f"invariant: {'held' if not _native['invariant'] else 'BROKEN'}")

if _native:
    result["native"] = _native
    if _CAN_WRITE and "REPLACE-WITH-" not in NATIVE_REPORT_PATH and any(k in _native for k in ("titles", "captions", "subtitles",
                                                                                         "options")):
        import json as _json
        with open(NATIVE_REPORT_PATH, "w", encoding="utf-8") as _fh:
            _json.dump(_native, _fh, indent=1, ensure_ascii=False)
        print(f"  wrote {NATIVE_REPORT_PATH}")
    elif any(k in _native for k in ("titles", "captions", "subtitles", "options")):
        print("  The placement report is in result['native'] — write it to 07-edit/titles/native-placement.json.")

print("Done.")

if DUMP_TIMELINE_JSON:
    _base = timeline.GetStartFrame()
    _fps = float(timeline.GetSetting("timelineFrameRate") or project.GetSetting("timelineFrameRate") or 0)
    _dump = {"timeline": timeline.GetName(), "fps": _fps, "start_frame": _base, "tracks": {}}

    def _item_type(_it):
        # ⛔ From 21.1 GetItemListInTrack returns TRANSITIONS as items too (measured 2026-09-14: a Cross
        # Dissolve came back between the two clips it joins). Anything that counts shots from this dump
        # must filter on type. GetType is 21.1+; on an older build the call fails and type stays None.
        try:
            return _it.GetType()
        except Exception:                                                   # noqa: BLE001
            return None
    def _item_text(_it):
        # ⚡ a supplement ad job (2026-10-28): titles made in Resolve need their specs rewritten from the timeline (`native.py
        # sync-specs`), so the dump carries each title's words — the Text+ StyledText inside the item's comp.
        # ⚡ v2.45: a generated title (TT_Main carries CustomData.cine) gives its main words and each tool's words
        try:
            _n = int(_it.GetFusionCompCount() or 0)
            if not _n:
                return None, None
            for _ci in range(_n, 0, -1):
                _c = _it.GetFusionCompByIndex(_ci)
                _m = _c.FindTool("TT_Main") if _c else None
                if _m is not None and (_m.GetData("cine") or {}):
                    _ws = {}
                    for _x in (_c.GetToolList(False, "TextPlus") or {}).values():
                        _v = _x.GetInput("StyledText")
                        if _v:
                            _ws[_x.Name] = str(_v)
                    return _ws.get("TT_Main"), _ws
            _c = _it.GetFusionCompByIndex(1)
            _w = [_x.GetInput("StyledText") for _x in (_c.GetToolList(False, "TextPlus") or {}).values()]
            _w = [str(_v) for _v in _w if _v]
            return ("\n".join(_w) if _w else None), None
        except Exception:                                                   # noqa: BLE001
            return None, None
    def _item_file(_it):
        # ⚡ v2.45: each item's media file, so export can see an imported title movie on the timeline (title_card.py
        # timeline_title_media) — a Resolve render that carries one reads as made in Resolve otherwise
        try:
            _m = _it.GetMediaPoolItem()
            return (_m.GetClipProperty("File Path") or None) if _m else None
        except Exception:                                                   # noqa: BLE001
            return None
    _dump["track_names"] = {}
    for _kind in ("video", "audio"):
        for _ti in range(1, int(timeline.GetTrackCount(_kind)) + 1):
            _items = timeline.GetItemListInTrack(_kind, _ti) or []
            try:
                _dump["track_names"][f"{_kind}{_ti}"] = timeline.GetTrackName(_kind, _ti)
            except Exception:                                               # noqa: BLE001
                pass
            _rows = []
            for _it in _items:
                _r = {"name": _it.GetName(), "type": _item_type(_it), "start": _it.GetStart() - _base,
                      "duration": _it.GetDuration(),
                      "start_s": round((_it.GetStart() - _base) / _fps, 3) if _fps else None,
                      "duration_s": round(_it.GetDuration() / _fps, 3) if _fps else None}
                _tx, _ws = _item_text(_it) if _kind == "video" else (None, None)
                if _tx:
                    _r["text"] = _tx
                if _ws:
                    _r["words"] = _ws
                _r["file"] = _item_file(_it) if _r["type"] != "transition" else None
                # HR-06 / HR-15 (v2.47.0): the fields motion_qa.py check reads — written only when Resolve
                # answers, so a missing one stays a skip-with-info there. [assumed] property names ("FPS",
                # "Sample Rate", "Opacity"): read them back once on a live Resolve before trusting a note.
                if _r["type"] != "transition":
                    try:
                        _mpi = _it.GetMediaPoolItem()
                    except Exception:                                       # noqa: BLE001
                        _mpi = None
                    try:
                        _v = _mpi.GetClipProperty("FPS" if _kind == "video" else "Sample Rate") if _mpi else None
                        if _v not in (None, ""):
                            _r["source_fps" if _kind == "video" else "sample_rate"] = _v
                    except Exception:                                       # noqa: BLE001
                        pass
                    if _kind == "video":
                        try:
                            _o = _it.GetProperty("Opacity")
                            if _o not in (None, ""):
                                _r["opacity"] = float(_o)
                        except Exception:                                   # noqa: BLE001
                            pass
                _rows.append(_r)
            _dump["tracks"][f"{_kind}{_ti}"] = _rows
    _n = sum(len(v) for v in _dump["tracks"].values())
    if not _fps:
        print("DUMP_TIMELINE_JSON: ⚠ the timeline reported no frame rate — seconds left empty rather "
              "than guessed; frames are still exact.")
    if not _CAN_WRITE:
        result["timeline_dump"] = _dump
        print(f"DUMP_TIMELINE_JSON: {_n} items returned in result['timeline_dump'] — write them to "
              f"07-edit/timeline-dump.json (the run_script sandbox cannot write files).")
    elif "REPLACE-WITH-" in DUMP_PATH:
        print("DUMP_TIMELINE_JSON: set DUMP_PATH first (refusing to write to a placeholder path).")
    else:
        import json as _json
        with open(DUMP_PATH, "w", encoding="utf-8") as _fh:
            _json.dump(_dump, _fh, indent=2, ensure_ascii=False)
        print(f"DUMP_TIMELINE_JSON: wrote {_n} items -> {DUMP_PATH}")
    # Read-back sanity per the house rule: report, don't assume.
    print("  Verify: the item count and the first video clip's start_s should match what you see on")
    print("  the timeline.")
