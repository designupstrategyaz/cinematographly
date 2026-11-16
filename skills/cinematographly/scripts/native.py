#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""native.py — on-screen text is made in Resolve. Anything rendered outside it says why.

The native-elements rule: captions, titles and supers default to Resolve's or Fusion's own elements, never a movie
made outside and imported without a reason. It replaced an earlier plan that made HyperFrames the title engine.

The default, for every job:
  captions   the locked .srt on a Resolve Subtitle track, styled there, burned by Resolve's own render
             (render-mp4.py BURN_SUBTITLES); or each cue as a Fusion Text+ clip on the "captions" track
  titles     Fusion titles on the "titles" track: the brand's styled template, placed at the spec's anchor with
             its words set and read back (`resolve-production-console.py` PLACE_TITLES), measured on Resolve's
             own renders with the titles on and off (`title_qa.py native`)
  supers     Fusion (typography-and-captions.md §6b rule 10)

An outside render (ffmpeg/libass, HyperFrames, supers-gsap) needs one of four reasons:
  batch       a machine-assembled Mode B batch: no edit timeline exists in Resolve for these videos
  derivative  a Mode D re-crop or re-format of a master already rendered, with no timeline to open
  remux       a stream copy of a Resolve render (tags, faststart, container) — no new pixels, checked packet for
              packet against --source
  owner       the owner asked for it, in their own words (--quote)
"Resolve is not reachable from here" and "the look needs HyperFrames" are not reasons on their own: they are
questions for the owner, and their answer is the `owner` reason.

  reasons                               the four reasons
  console <job> [--srt FILE] [--captions-as track|textplus] [--no-titles] [--host-job PATH] [--options ID]
                [--install] [--no-build] [--no-add-fonts] [--expect SNAPSHOT]
        writes 07-edit/resolve-production-console.native.py with every title spec whose engine is resolve, and
        PLACE_SUBTITLES with the locked .srt onto a Subtitle track, read back.
        ⛔ v2.49, the computer-control rule: the copy PLACES NO TITLE (PLACE_TITLES, PLACE_TITLE_OPTIONS, INSTALL_TITLE_TEMPLATES,
        ADD_FONTS and Text+ captions stay off) — titles go in by computer control, and DUMP_TIMELINE_JSON +
        sync-specs read them back. --owner-paste writes the old placing copy below for the OWNER to paste into
        Workspace ▸ Console themselves; gate.py refuses it through run_script.
        ⚡ v2.45 (a title is never a movie made outside and imported): the card's Fusion titles are
        GENERATED first (fusion_titles.py build — the card's font and Style, sizes, ink, plate and motion tokens) and
        spliced in as TITLE_TEMPLATES; a stale template refuses. PLACE_TITLES inserts each by its installed name
        (--install: fusion.InstallFile of the .drfx) or as a stock Text+ with the generated comp imported
        (TITLE_ROUTE auto), on a scratch top track, moves it onto its named track (Titles · Supers · Disclosure) at
        the spec's frame (21.1.2 SetPosition), writes the words and reads back the words, the font as installed,
        the card hash, the position and the fold; any failure is a row that STOPS — never rendered around.
        --options ID: PLACE_TITLE_OPTIONS — <ID>.opt1..3 on a duplicate timeline, one track each, reviewed as
        Resolve's own stills (Timeline.ExportFrame) for `title_qa.py strip-native`.
        --host-job: the job's path as Resolve's machine sees it, when this runs in a VM with another mount path.
  templates <job> [--format F] [--fps N]      fusion_titles.py build (the same as the console does first)
  options <job> <id>                          the console copy with PLACE_TITLE_OPTIONS for that title
  record <job> <file> --tool T --reason CODE --why "…" [--quote "…"] [--source FILE]
        <file>.external.json for a file made outside Resolve (build_captions.py writes its own)
  sync-specs <job> [--dump 07-edit/timeline-dump.json] [--write]
        the timeline is the truth once titles live in Resolve: each title on a Titles, Supers or Disclosure track is
        matched to its spec (its words, then the nearest start within 1 s) and the spec's time, length and words are
        rewritten from it, the engine set to resolve; a title with no spec gets one (N<k>), a spec with no title is
        reported. The dump comes from the console's DUMP_TIMELINE_JSON, which carries each title's words.
  status <job>      every title's engine, every delivery file's maker, every external record
  check <job>       what `approve export` refuses (exit 1 if anything)
  --selftest

What export refuses:
  · a delivery file whose container says ffmpeg muxed it (the encoder tag is Lavf…) and that has no record;
  · a record whose reason is not one of the four, an owner reason without their words, a record about other bytes;
  · a remux whose video stream is not its source's, packet for packet;
  · a delivery file whose captions Resolve burned, without a `srt_qa.py burned` PASS on its bytes — an accepted
    render setting is not a burned caption.
What it cannot do: see who pressed Render. A container's encoder tag can be stripped, and a file with no tag reads
as unknown. The check reads what the file says, and every record is printed at export for the owner to read.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
CONSOLE = os.path.join(HERE, "resolve-production-console.py")
CONSOLE_COPY = "resolve-production-console.native.py"
PLACEMENT = os.path.join("07-edit", "titles", "native-placement.json")
RENDER_EXT = (".mp4", ".mov", ".mxf")
RULING = "the native-elements rule"     # deliverables are made in Resolve (was internal ruling C7)
REASONS = {
    "batch": "a machine-assembled Mode B batch: no edit timeline exists in Resolve for these videos (modes/ugc-volume.md)",
    "derivative": "a Mode D re-crop or re-format of a master already rendered, with no timeline to open (modes/repurpose.md)",
    "remux": "a stream copy of a Resolve render (tags, faststart, container): no new pixels, checked packet for packet "
             "against --source",
    "owner": "the owner asked for it, in their own words (--quote)",
}
ENGINES = ("resolve", "hyperframes", "gsap")
# a delivery file named like this is declared captionless (the build_captions master, a textless version, the
# sound-off T2 source) and is not held to the burned-captions check
TEXTLESS_RE = re.compile(r"(master|textless|clean|picture[-_ ]?only|no[-_ ]?caps?)", re.I)
DIFF_THR = 0.15        # a pixel is the text's when the two renders differ by more than this (0–1). Two first-
                       # generation H.264 encodes of one source at CRF 23 left 0.006 % of the frame above it, at
                       # CRF 14 none (testsrc2, 2026-10-27); a second-generation encode is far noisier [assumed]
MIN_BLOB = 6           # smaller specks of difference are encoder noise, at the analysis width [assumed]
CLUSTER_MIN = 0.05     # a cluster of difference holding less of the frame's ink than this is noise, not text [assumed]


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jload(p: str):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def rel(job: str, p: str) -> str:
    return os.path.relpath(p, job) if os.path.abspath(p).startswith(os.path.abspath(job) + os.sep) else p


# ── reasons ──────────────────────────────────────────────────────────────────────────────────────────────
def check_reason(r, where: str = "") -> list:
    """Problems with an external-render reason: {code, why, quote?, source?}. Empty list = a valid reason."""
    pre = f"{where}: " if where else ""
    if not isinstance(r, dict) or not r.get("code"):
        return [f"{pre}no reason — made outside Resolve, it needs one of {', '.join(REASONS)} ({RULING}: "
                f"Resolve or Fusion native by default, \"not create outside for no reason\")"]
    P = []
    code = str(r.get("code"))
    if code not in REASONS:
        P.append(f"{pre}reason {code!r} is not one of {', '.join(REASONS)} — anything else is a question for the "
                 f"owner, and their answer is the `owner` reason")
    if len(str(r.get("why") or "").split()) < 4:
        P.append(f"{pre}the reason needs a sentence (--why), not a word")
    if code == "owner" and len(str(r.get("quote") or "").split()) < 3:
        P.append(f"{pre}an owner reason needs their own words (--quote \"…\")")
    if code == "remux" and not r.get("source"):
        P.append(f"{pre}a remux names the Resolve render it copies (--source)")
    return P


def reason_args(ap) -> None:
    ap.add_argument("--reason", choices=sorted(REASONS), help="why this is made outside Resolve (native.py reasons)")
    ap.add_argument("--why", default="", help="the reason, in a sentence")
    ap.add_argument("--quote", default="", help="the owner's own words (the `owner` reason)")


def reason_of(a) -> dict:
    return {k: v for k, v in (("code", a.reason), ("why", (a.why or "").strip()), ("quote", (a.quote or "").strip()),
                              ("source", getattr(a, "source", None))) if v}


def record_path(f: str) -> str:
    return f + ".external.json"


def record(out: str, tool: str, reason: dict, inputs: list | None = None) -> dict:
    P = check_reason(reason, os.path.basename(out))
    if P:
        raise SystemExit("REFUSED: " + "; ".join(P))
    r = {"file": os.path.basename(out), "sha256": sha256_file(out), "tool": tool, "reason": reason,
         "inputs": inputs or [], "ruling": RULING, "at": dt.datetime.now().isoformat(timespec="seconds")}
    json.dump(r, open(record_path(out), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return r


# ── what made a file ─────────────────────────────────────────────────────────────────────────────────────
def made_by(p: str) -> tuple:
    """("ffmpeg" | "resolve" | "unknown", the tag that said so). Reads the container's own tags."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", p],
                           capture_output=True, text=True, timeout=30)
        j = json.loads(r.stdout or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return "unknown", ""
    tags = dict((j.get("format") or {}).get("tags") or {})
    for s in j.get("streams") or []:
        for k, v in (s.get("tags") or {}).items():
            tags.setdefault(f"stream.{k}", v)
    enc = str(tags.get("encoder") or tags.get("ENCODER") or "")
    if enc.lower().startswith("lavf"):
        return "ffmpeg", f"encoder={enc}"
    blob = json.dumps(tags).lower()
    if "davinci" in blob or "blackmagic" in blob:
        return "resolve", next((f"{k}={v}" for k, v in tags.items() if re.search("davinci|blackmagic", str(v), re.I)), "")
    return "unknown", enc and f"encoder={enc}"


def render_maker(p: str) -> str:
    """Who made a movie, in words, from its own tags: "HyperFrames 0.8.204, muxed by ffmpeg (Lavf60.16.100)", "made by
    DaVinci Resolve", or "" when the file says nothing (a supplement ad job's title movies carried hyperframes_renderer)."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", p],
                           capture_output=True, text=True, timeout=30)
        j = json.loads(r.stdout or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return ""
    tags = {str(k).lower(): str(v) for k, v in ((j.get("format") or {}).get("tags") or {}).items()}
    for st in j.get("streams") or []:
        for k, v in (st.get("tags") or {}).items():
            tags.setdefault(str(k).lower(), str(v))
    parts = []
    if tags.get("hyperframes_renderer") or tags.get("hyperframes_version"):
        parts.append(f"HyperFrames {tags.get('hyperframes_version') or ''}".strip())
    enc = tags.get("encoder") or ""
    if enc.lower().startswith("lavf"):
        parts.append(f"muxed by ffmpeg ({enc})")
    elif re.search("davinci|blackmagic", json.dumps(tags), re.I):
        parts.append("made by DaVinci Resolve")
    return ", ".join(parts)


def stream_hash(p: str) -> str | None:
    """sha256 of the first video stream's packets — equal for a stream copy, different after a re-encode."""
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-map", "0:v:0", "-c", "copy", "-f", "hash", "-hash",
                            "sha256", "-"], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"SHA256=([0-9a-f]{64})", r.stdout or "")
    return m.group(1) if m else None


# ── the difference between two Resolve renders: the text alone ───────────────────────────────────────────
def diff_frames(with_p: str, without_p: str, at: float, n: int, fps: float, w: int, h: int, thr: float = DIFF_THR):
    """(with, without, masks): n frames from `at` of each render at w×h, and per frame where they differ — the
    text and only the text, when the two renders are the same timeline with the text tracks on and off."""
    import numpy as np
    import title_qa as TQ
    Fw = TQ.plate_frames(with_p, at, n, fps, w, h)
    Fo = TQ.plate_frames(without_p, at, n, fps, w, h)
    if Fw is None or Fo is None:
        return None, None, None
    m = min(len(Fw), len(Fo))
    Fw, Fo = Fw[:m], Fo[:m]
    return Fw, Fo, clean_masks(np.abs(Fw - Fo).max(axis=-1) > thr)


def clean_masks(raw):
    """Per frame, the difference that is text: specks under MIN_BLOB go, and so does a cluster holding under CLUSTER_MIN
    of the frame's ink (encoder noise from a change elsewhere). Shared by two renders and by Resolve's still pairs."""
    import numpy as np
    try:
        import cv2
    except ImportError:
        return raw
    m = len(raw)
    masks = np.zeros_like(raw)
    k9 = np.ones((9, 9), np.uint8)
    for i in range(m):
        k, lab, st, _ = cv2.connectedComponentsWithStats(raw[i].astype(np.uint8), connectivity=8)
        keep = [j for j in range(1, k) if st[j, cv2.CC_STAT_AREA] >= MIN_BLOB]
        if not keep:
            continue
        mi = np.isin(lab, keep)
        # Text is letters close together: grown by ~8 px it is one cluster (or one per line). Encoder noise left by
        # a change elsewhere in the frame is a scatter of specks: a cluster holding under CLUSTER_MIN of the ink goes.
        kc, lc = cv2.connectedComponents(cv2.dilate(mi.astype(np.uint8), k9, iterations=1), connectivity=8)
        if kc > 2:
            ink = np.bincount(lc[mi], minlength=kc)
            tot = float(ink.sum()) or 1.0
            mi &= np.isin(lc, [j for j in range(1, kc) if ink[j] / tot >= CLUSTER_MIN])
        masks[i] = mi
    return masks


def same_shape(a: str, b: str) -> list:
    import title_qa as TQ
    x, y = TQ.probe(a), TQ.probe(b)
    P = []
    if (x["w"], x["h"]) != (y["w"], y["h"]):
        P.append(f"the two renders differ in size ({x['w']}×{x['h']} vs {y['w']}×{y['h']}) — render both from the same "
                 f"timeline at the same format")
    if abs(x["fps"] - y["fps"]) > 0.01:
        P.append(f"the two renders differ in frame rate ({x['fps']:g} vs {y['fps']:g})")
    if x["duration"] and y["duration"] and abs(x["duration"] - y["duration"]) > 0.5:
        P.append(f"the two renders differ in length ({x['duration']:.2f} s vs {y['duration']:.2f} s) — the same range")
    return P


# ── the job ──────────────────────────────────────────────────────────────────────────────────────────────
def renders(job: str) -> list:
    return sorted(p for p in glob.glob(os.path.join(job, "10-export", "*"))
                  if p.lower().endswith(RENDER_EXT) and os.path.isfile(p))


def srts(job: str) -> list:
    return sorted(glob.glob(os.path.join(job, "08-captions", "*.srt")))


NOT_WORDS = ("lines", "emphasis", "logo", "plate", "mark", "face", "label_pos", "decimals", "from", "rule")


def spec_text(spec: dict) -> tuple:
    """(one text block, {field: text}) from a title spec's content. ⚡ v2.45: a bool is never a word (`plate: true`
    became the field "True", since a bool is an int), nor are the kit's switches (mark, face, label_pos …)."""
    C = spec.get("content") or {}
    lines = [str(x) for x in (C.get("lines") or []) if str(x).strip()]
    fields = {k: str(v) for k, v in C.items() if k not in NOT_WORDS and not isinstance(v, bool)
              and isinstance(v, (str, int, float)) and str(v).strip()}
    text = "\n".join(lines) if lines else "\n".join(fields.values())
    return text, fields


def engine_of(spec: dict) -> str:
    return str(spec.get("engine") or "resolve").strip().lower()


def check_external(job: str, f: str) -> tuple:
    P, W = [], []
    rp = record_path(f)
    r = jload(rp)
    rl = rel(job, f)
    if r is None:
        return P, W, None
    P += check_reason(r.get("reason"), rl)
    if r.get("sha256") != sha256_file(f):
        P.append(f"{rl}: changed after its external record was written — the record is about other bytes")
    rs = r.get("reason") or {}
    if rs.get("code") == "remux" and not P:
        src = rs.get("source")
        sp = src if os.path.isabs(str(src)) else os.path.join(job, str(src))
        if not os.path.isfile(sp):
            P.append(f"{rl}: a remux of {src}, which is gone — the stream copy cannot be checked")
        else:
            a, b = stream_hash(sp), stream_hash(f)
            if not a or not b:
                P.append(f"{rl}: the video streams could not be hashed (ffmpeg) — the remux is unchecked")
            elif a != b:
                P.append(f"{rl}: not a stream copy of {src} — its video packets differ, so the pixels were re-made outside "
                         f"Resolve; a remux reason does not cover that")
    W.append(f"made outside Resolve: {rl} by {r.get('tool')} — {rs.get('code')}: {rs.get('why')}"
             + (f" (owner: \"{rs.get('quote')}\")" if rs.get("quote") else ""))
    return P, W, r


def captions_report(render: str) -> str:
    return render + ".captions.qa.json"


def dump_problems(job: str) -> list:
    """⚡ v2.45: export reads the TIMELINE, not only the delivery file — a Resolve render with imported title movies on it
    reads as made in Resolve. So a job with titles needs a timeline dump (DUMP_TIMELINE_JSON, which carries each item's
    media file) made after its newest delivery render; `title_card.check_job` reads it for title-folder movies. Not asked
    of a machine-assembled batch or a derivative with no timeline (their records say so)."""
    import title_card as TC
    R = renders(job)
    if not R or not TC.specs(job):
        return []
    recs = [jload(record_path(f)) or {} for f in R]
    if all((r.get("reason") or {}).get("code") in ("batch", "derivative") for r in recs):
        return []
    dp = os.path.join(job, "07-edit", "timeline-dump.json")
    how = ("run the console with DUMP_TIMELINE_JSON = True after the render (run_script: write result['timeline_dump'] "
           "to 07-edit/timeline-dump.json) — export reads what is ON the timeline, so an imported title movie is seen")
    if not os.path.isfile(dp):
        return [f"no 07-edit/timeline-dump.json — {how}"]
    newest = max(os.path.getmtime(f) for f in R)
    if os.path.getmtime(dp) + 1 < newest:
        return [f"07-edit/timeline-dump.json is older than the newest delivery render — {how}"]
    d = jload(dp) or {}
    rows = [r for k, v in (d.get("tracks") or {}).items() if str(k).startswith("video") for r in v or []
            if r.get("type") != "transition"]
    if rows and not any("file" in r for r in rows):
        return [f"07-edit/timeline-dump.json carries no media files (a dump from before v2.45) — {how}"]
    return []


def check_job(job: str) -> tuple:
    """(problems, notes) for `approve export`."""
    P, W = [], []
    P += dump_problems(job)
    S = srts(job)
    cur = {rel(job, s): sha256_file(s) for s in S}
    for f in renders(job):
        rl = rel(job, f)
        p_, w_, r = check_external(job, f)
        P += p_
        W += w_
        if r is None:
            who, tag = made_by(f)
            if who == "ffmpeg":
                P.append(f"{rl}: the container says ffmpeg made it ({tag}) and no reason is recorded — on-screen text "
                         f"and the delivery render are made in Resolve ({RULING}). If there is a reason: native.py "
                         f"record <job> {rl} --tool … --reason {'|'.join(REASONS)} --why \"…\"")
        if not S:
            continue
        if TEXTLESS_RE.search(os.path.basename(f)):
            W.append(f"{rl}: declared captionless by its name — not held to the burned-captions check")
            continue
        if r is not None and r.get("tool") == "build_captions":
            continue
        q = jload(captions_report(f))
        if q is None:
            P.append(f"{rl}: its captions were burned in Resolve — show they are in the pixels: srt_qa.py burned <job> "
                     f"--render {rl} --plate <the same timeline rendered with the captions off: render-mp4.py "
                     f"PICTURE_ONLY>")
        elif q.get("render_sha256") != sha256_file(f):
            P.append(f"{rl}: re-rendered after its captions were checked in the pixels — srt_qa.py burned again")
        elif q.get("srt") not in cur or cur[q.get("srt")] != q.get("srt_sha256"):
            P.append(f"{rl}: its burned-captions check was made against {q.get('srt')}, which changed or is gone — "
                     f"srt_qa.py burned again")
        elif q.get("verdict") != "PASS":
            bad = [c for c in q.get("cues") or [] if c.get("status") == "FAIL"]
            P.append(f"{rl}: the captions are not all in the pixels — " + "; ".join(
                f"cue {c['n']} at {c['t']:.2f} s: {c['note']}" for c in bad[:4]) + (" …" if len(bad) > 4 else ""))
    return P, W


# ── the console copy ─────────────────────────────────────────────────────────────────────────────────────
def console_copy(job: str, srt: str | None = None, captions_as: str = "track", titles: bool = True,
                 host_job: str | None = None, expect: str | None = None, options: str | None = None,
                 install: bool = False, build: bool = True, add_fonts: bool = True, fmt_name: str = "vertical-1080",
                 owner_paste: bool = False) -> tuple:
    """(path, titles, cues, skipped, notes). ⚡ v2.45: the card's Fusion titles are generated first (fusion_titles.py
    build) and spliced in as TITLE_TEMPLATES; a stale template never reaches Resolve.
    ⛔ v2.49 house rule 8 ("for Fusion, Fairlight and making/adding/editing native titles, Claude should ALWAYS use
    computer control and not API. It fails all the time"): by default the copy carries the specs, the templates, the
    fonts check and the Subtitle-track captions, but places NO title — PLACE_TITLES, PLACE_TITLE_OPTIONS,
    INSTALL_TITLE_TEMPLATES, ADD_FONTS and Text+ captions stay off, and the titles are placed by computer control.
    owner_paste=True writes the old placing copy for the OWNER to paste into Workspace ▸ Console himself; gate.py
    refuses it through run_script."""
    import title_card as TC
    card = TC.load_card(os.path.join(job, TC.CARD)) if os.path.isfile(os.path.join(job, TC.CARD)) else {}
    nat = card.get("native") or {}
    font = ((card.get("fonts") or {}).get("anchor") or {}).get("family")
    host = (host_job or os.path.abspath(job)).rstrip("/\\")
    notes = []

    def on_host(p: str) -> str:
        a = os.path.abspath(p)
        j = os.path.abspath(job)
        return host + a[len(j):] if a.startswith(j) else a
    man = None
    if titles and card and card.get("kinds"):
        import fusion_titles as FT
        if build:
            try:
                man = FT.build(job, fmt_name)
                notes.append(f"generated {len(man['kinds'])} Fusion title(s) from the card ({FT.OUT}/templates.json, card "
                             f"{man['card_sha256'][:8]})")
            except SystemExit as e:
                notes.append(f"no generated titles: {e} — PLACE_TITLES falls back to a stock {nat.get('template') or 'Text+'} "
                             f"with the style frame's inputs, and says so")
        if man is None and os.path.isfile(os.path.join(job, FT.OUT, "templates.json")):
            bad = FT.check(job)
            if bad:
                raise SystemExit("REFUSED: the generated Fusion titles are stale — " + "; ".join(bad)
                                 + " (fusion_titles.py build <job>, after the card lints clean)")
            man = jload(os.path.join(job, FT.OUT, "templates.json"))
    tpl = {}
    if man:
        out_dir = os.path.join(job, FT.OUT)
        for kind, k in (man.get("kinds") or {}).items():
            tpl[kind] = {"name": k["name"], "comp": on_host(os.path.join(out_dir, k["comp"])), "sha256": k["sha256"],
                         "card_sha256": man["card_sha256"], "main": k.get("main") or "TT_Main", "fields": k.get("fields") or [],
                         "motion": {x: (k.get("motion") or {}).get(x) for x in ("e", "x", "X", "h", "x0")},
                         "fps": man.get("fps"), "format": man.get("format"), "font": k.get("font"), "style": k.get("style"),
                         "kit": k.get("kit")}
    fonts = []
    for role in ("anchor", "companion"):
        fp = TC._font_path(card, (card.get("fonts") or {}).get(role) or {}) if card else None
        if fp:
            fonts.append(on_host(fp))

    def row(p_: str, s: dict, tid: str) -> dict:
        text, fields = spec_text(s)
        r = {"id": tid, "kind": s.get("kind"), "at_s": float(s.get("at_s") or 0),
             "duration_s": float(s.get("duration_s") or 0), "text": text, "fields": fields,
             **({"font": font} if font else {}),
             **({"emphasis": True} if (s.get("content") or {}).get("emphasis") else {})}
        if s.get("kind") in tpl:
            import fusion_titles as FT
            r["words"] = FT.words_for(s, tpl[s["kind"]].get("kit"), tpl[s["kind"]].get("fields"))
            r["kit"] = tpl[s["kind"]].get("kit")
            if (s.get("content") or {}).get("plate") is True and not ((card.get("kinds") or {}).get(s["kind"]) or {}).get("plate"):
                pr, pg, pb, pa = TC.rgba01((card.get("colors") or {}).get("plate"))   # this title's own plate (kits.js C.plate)
                r["inputs"] = {"TT_Main": {"Enabled3": 1, "ElementShape3": 2, "Offset3": [0, 0], "Level3": 1,
                                           "Red3": pr, "Green3": pg, "Blue3": pb, "Alpha3": pa}}
            if tpl[s["kind"]].get("fields"):          # the fields beside THIS title's main block (its own line count)
                n_main = len([x for x in str(r["words"].get("TT_Main") or "").split("\n") if x.strip()]) or 1
                r["place"] = FT.field_centres(card, s["kind"], FT.fmt_of(fmt_name), n_main)
        return r
    items, skipped = [], []
    if titles:
        for p in TC.specs(job):
            s = jload(p) or {}
            tid = os.path.basename(p)[: -len(".title.json")]
            if engine_of(s) != "resolve":
                skipped.append(f"{tid} ({engine_of(s)})")
                continue
            if card and s.get("kind") not in (card.get("kinds") or {}):
                skipped.append(f"{tid} (kind {s.get('kind')!r} is not on the title card)")
                continue
            items.append(row(p, s, tid))
    opts = {}
    if options:
        base = os.path.join(job, TC.TITLES, options)
        ps = sorted(glob.glob(glob.escape(base) + ".opt*.title.json"),
                    key=lambda x: int(re.search(r"\.opt(\d+)\.title\.json$", x).group(1)))
        if not ps:
            raise SystemExit(f"error: no {os.path.relpath(base, job)}.opt*.title.json — write the options as specs first")
        rows_ = []
        for p in ps[:3]:
            s = jload(p) or {}
            if engine_of(s) != "resolve":
                raise SystemExit(f"error: {os.path.relpath(p, job)} names engine {engine_of(s)} — PLACE_TITLE_OPTIONS reviews "
                                 f"titles made in Resolve")
            n = re.search(r"\.opt(\d+)\.title\.json$", p).group(1)
            rows_.append(dict(row(p, s, f"{options}.opt{n}"), option=int(n)))
        opts[options] = rows_
        os.makedirs(os.path.join(job, "09-qa", "titles", options), exist_ok=True)
    cues = []
    if srt:
        import srt_qa
        cues, errs = srt_qa.parse(open(srt, encoding="utf-8-sig").read())
        if errs:
            raise SystemExit(f"error: {srt} does not parse: {errs[0]}")
        cues = [{"n": c["n"], "t0": round(c["t0"], 3), "t1": round(c["t1"], 3), "text": "\n".join(c["lines"])} for c in cues]
    if items or opts:
        os.makedirs(os.path.join(job, "09-qa", "stills"), exist_ok=True)     # Resolve writes the stills; the folder must exist
    src = open(CONSOLE, encoding="utf-8").read()
    reps = [("MARKERS = []  # __DETECT_BEATS_MARKERS__", "MARKERS = []  # __DETECT_BEATS_MARKERS__"),
            ("\nADD_BEAT_MARKERS = True", "\nADD_BEAT_MARKERS = False"),
            ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False"),
            ("\nENSURE_AUDIO_LANES = True", "\nENSURE_AUDIO_LANES = False"),
            ("TITLES = []  # __NATIVE_TITLES__", "TITLES = " + repr(items) + "  # __NATIVE_TITLES__"),
            ('TITLE_TEMPLATE = "Text+"', f"TITLE_TEMPLATE = {json.dumps(nat.get('template') or 'Text+', ensure_ascii=False)}"),
            ('TITLE_TRACK = "Titles"', f"TITLE_TRACK = {json.dumps(nat.get('track') or 'Titles')}"),
            ("TITLE_LAYOUT = {}  # __NATIVE_LAYOUT__", "TITLE_LAYOUT = " + repr(TC.layout_for(card) if card else {}) + "  # __NATIVE_LAYOUT__"),
            ("TITLE_TEMPLATES = {}  # __NATIVE_TEMPLATES__", "TITLE_TEMPLATES = " + repr(tpl) + "  # __NATIVE_TEMPLATES__"),
            ("FONT_FILES = []  # __NATIVE_FONTS__", "FONT_FILES = " + repr(fonts) + "  # __NATIVE_FONTS__"),
            ('STILLS_DIR = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/09-qa/stills"', f'STILLS_DIR = r"{host}/09-qa/stills"'),
            ('OPTIONS_DIR = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/09-qa/titles"', f'OPTIONS_DIR = r"{host}/09-qa/titles"'),
            ("SRT_CUES = []  # __NATIVE_SRT_CUES__", "SRT_CUES = " + repr(cues) + "  # __NATIVE_SRT_CUES__"),
            ('CAPTION_TEMPLATE = "Text+"', f"CAPTION_TEMPLATE = {json.dumps(nat.get('caption_template') or 'Text+', ensure_ascii=False)}"),
            ('SUBTITLES_AS = "track"', f"SUBTITLES_AS = {json.dumps(captions_as)}"),
            ('NATIVE_REPORT_PATH = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/07-edit/titles/native-placement.json"',
             f"NATIVE_REPORT_PATH = r\"{host}/{PLACEMENT}\"")]
    if nat.get("route") in ("auto", "template", "import"):
        reps.append(('TITLE_ROUTE = "auto"', f"TITLE_ROUTE = {json.dumps(nat['route'])}"))
    if items and owner_paste:
        reps.append(("\nPLACE_TITLES = False", "\nPLACE_TITLES = True"))
    if tpl:
        reps.append(("\nCHECK_FONTS = False", "\nCHECK_FONTS = True"))
        if add_fonts and fonts and owner_paste:
            reps.append(("\nADD_FONTS = False", "\nADD_FONTS = True"))
        drfx = os.path.join(job, FT.OUT, (man.get("drfx") or {}).get("file") or "")
        if os.path.isfile(drfx):
            reps.append(('DRFX_PATH = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/07-edit/titles/fusion/cine-titles.drfx"',
                         f'DRFX_PATH = r"{on_host(drfx)}"'))
            if install and owner_paste:
                reps.append(("\nINSTALL_TITLE_TEMPLATES = False", "\nINSTALL_TITLE_TEMPLATES = True"))
    if opts:
        reps.append(("TITLE_OPTIONS = {}  # __NATIVE_OPTIONS__", "TITLE_OPTIONS = " + repr(opts) + "  # __NATIVE_OPTIONS__"))
        if owner_paste:
            reps.append(("\nPLACE_TITLE_OPTIONS = False", "\nPLACE_TITLE_OPTIONS = True"))
    if srt:
        reps.append(('SRT_PATH = r"REPLACE-WITH-YOUR-PROJECT-FOLDER/08-captions/SLUG.srt"', f'SRT_PATH = r"{on_host(srt)}"'))
        if captions_as == "track" or owner_paste:
            reps.append(("\nPLACE_SUBTITLES = False", "\nPLACE_SUBTITLES = True"))
    if expect:
        snap = jload(expect)
        if not isinstance(snap, dict) or "tracks" not in snap:
            raise SystemExit(f"error: {expect} is not a timeline snapshot (SNAPSHOT_TIMELINE's result['native']['snapshot'])")
        reps.append(("EXPECT_SNAPSHOT = {}  # __EXPECT_SNAPSHOT__", "EXPECT_SNAPSHOT = " + repr(snap) + "  # __EXPECT_SNAPSHOT__"))
    for old, new in reps:
        if old not in src:
            raise RuntimeError(f"resolve-production-console.py no longer contains {old!r} — update native.console_copy()")
        src = src.replace(old, new, 1)
    compile(src, CONSOLE_COPY, "exec")
    out = os.path.join(job, "07-edit", CONSOLE_COPY)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(src)
    if not owner_paste and (items or opts or (srt and captions_as == "textplus") or (install and tpl)):
        notes.append("⛔ the computer-control rule: this copy places no title — "
                     + ", ".join(x for x in (f"{len(items)} title(s)" if items else "", "the title options" if opts else "",
                                             "the Text+ captions" if srt and captions_as == "textplus" else "",
                                             "the .drfx install" if install and tpl else "") if x)
                     + " go in BY COMPUTER CONTROL (install the .drfx, drag each template onto its named track at the "
                       "spec's frame, type its words, read a full-size still, frame 0 and the last frame included). Then "
                       "run this copy with DUMP_TIMELINE_JSON = True and `native.py sync-specs <job>` to read the words and "
                       "positions back (editing-and-audio.md § What runs through the API)")
    if owner_paste:
        notes.append("--owner-paste: this copy PLACES titles through the API — it is for the owner to paste into Workspace "
                     "▸ Console themselves; gate.py refuses it through run_script (the computer-control rule)")
    if items and not tpl and owner_paste:
        notes.append("PLACE_TITLES uses the stock template with the style frame's static inputs: no motion, no plate "
                     "(the card does not generate titles yet — fusion_titles.py build after it lints clean)")
    return out, len(items), len(cues), skipped, notes


# ── status ───────────────────────────────────────────────────────────────────────────────────────────────
# ⚡ a supplement ad job (2026-10-28): "When titles go native, regenerate their title.json. title_card.py check_job still judged S01
# by the old animated .mov ("needs 2.56 s")." The timeline is the truth once titles live in Resolve: sync-specs reads the
# dump (`resolve-production-console.py` DUMP_TIMELINE_JSON, which carries each title's words) and rewrites each spec's
# time, length and words from it, the engine set to resolve.
SYNC_TRACKS = {"titles": "main", "supers": "super", "disclosure": "disclosure"}   # track name prefix → kind for a new spec
SYNC_TOL_S = 1.0                                                                    # a moved title is matched this far


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip().lower()


def sync_specs(job: str, dump_p: str | None = None, write: bool = False) -> dict:
    """{updated, created, unplaced, words_changed, problems}: every title on the timeline's text tracks against its
    spec — matched by its words, then by the nearest start within SYNC_TOL_S — and, with write, each spec rewritten."""
    import title_card as TC
    dump_p = dump_p or os.path.join(job, "07-edit", "timeline-dump.json")
    out = {"dump": rel(job, dump_p), "updated": [], "created": [], "unplaced": [], "words_changed": [], "problems": []}
    d = jload(dump_p)
    if not d:
        out["problems"].append(f"no timeline dump at {rel(job, dump_p)} — run the console with DUMP_TIMELINE_JSON = True "
                               f"(run_script: write result['timeline_dump'] there)")
        return out
    names = d.get("track_names") or {}
    items = []
    for k, rows in (d.get("tracks") or {}).items():
        nm = (names.get(k) or "").strip().lower()
        kind = next((v for t, v in SYNC_TRACKS.items() if nm.startswith(t)), None)
        if not k.startswith("video") or not kind:
            continue
        for r in rows:
            if r.get("type") == "transition" or not r.get("text") or r.get("start_s") is None:
                continue
            items.append({"track": names.get(k), "kind": kind, **r})
    if not items:
        out["problems"].append("the dump has no titles with words on a Titles, Supers or Disclosure track — an older dump "
                               "(before 2026-10-28) carries no words; dump again")
        return out
    specs = []
    for sp in TC.specs(job):
        s = jload(sp) or {}
        specs.append((sp, s, _norm(spec_text(s)[0])))
    used, pairs = set(), []
    for sp, s, txt in specs:                                    # 0. ⚡ v2.45: the item PLACE_TITLES named cine:<id>
        tid_ = os.path.basename(sp)[: -len(".title.json")]
        hit = [i for i, it in enumerate(items) if i not in used and str(it.get("name") or "") == f"cine:{tid_}"]
        if hit:
            it_ = items[hit[0]]
            if it_.get("words"):                                # a generated title: its words per tool
                import fusion_titles as FT
                want = {k: v for k, v in FT.words_for(s, None if not s.get("kind") else _kit_of(job, s), None).items()
                        if not k.startswith("_")}
                rew = {k: _norm(v) for k, v in want.items()} != {k: _norm(v) for k, v in it_["words"].items() if k in want or v}
            else:
                rew = _norm(it_["text"]) != txt
            used.add(hit[0]); pairs.append((sp, s, it_, rew))
    for sp, s, txt in specs:                                    # 1. the same words, nearest in time
        if sp in {p_[0] for p_ in pairs}:
            continue
        hit = [i for i, it in enumerate(items) if i not in used and _norm(it["text"]) == txt]
        if hit:
            i = min(hit, key=lambda i: abs(float(items[i]["start_s"]) - float(s.get("at_s") or 0)))
            used.add(i); pairs.append((sp, s, items[i], False))
    done = {p_[0] for p_ in pairs}
    for sp, s, txt in specs:                                    # 2. moved and re-worded: the nearest start
        if sp in done:
            continue
        near = [i for i, it in enumerate(items) if i not in used
                and abs(float(it["start_s"]) - float(s.get("at_s") or 0)) <= SYNC_TOL_S]
        if near:
            i = min(near, key=lambda i: abs(float(items[i]["start_s"]) - float(s.get("at_s") or 0)))
            used.add(i); pairs.append((sp, s, items[i], True))
        else:
            out["unplaced"].append(os.path.basename(sp).split(".")[0])
    stamp = {"dump_sha256": sha256_file(dump_p), "at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat()}
    for sp, s, it, reworded in pairs:
        tid = s.get("id") or os.path.basename(sp).split(".")[0]
        new = dict(s, at_s=float(it["start_s"]), duration_s=float(it["duration_s"]))
        if reworded and it.get("words"):
            import fusion_titles as FT
            new["content"] = FT.content_from_words(s, _kit_of(job, s), it["words"])
            out["words_changed"].append(f"{tid}: {json.dumps({k: v for k, v in it['words'].items()}, ensure_ascii=False)} "
                                        f"(claims_lint.py on the new words)")
        elif reworded:
            new["content"] = {**{k: v for k, v in (s.get("content") or {}).items() if k in ("emphasis", "mark", "logo")},
                              "lines": [x for x in str(it["text"]).split("\n") if x.strip()]}
            out["words_changed"].append(f"{tid}: “{spec_text(s)[0]}” → “{it['text']}” (claims_lint.py on the new words)")
        if engine_of(s) != "resolve":
            new["engine"] = "resolve"
            new.pop("engine_reason", None)
        new["synced_from_timeline"] = {**stamp, "track": it["track"], "frames": [it.get("start"), it.get("duration")]}
        a_ = (s.get("anchor") or {}).get("at_s")
        if a_ is not None and abs(float(a_) - new["at_s"]) > 2 / float(d.get("fps") or 24):
            out["problems"].append(f"{tid}: it now starts at {new['at_s']:.3f} s, its anchor is at {float(a_):.3f} s — "
                                   f"re-anchor it to the picture event it lands on")
        changed = {k for k in ("at_s", "duration_s", "content", "engine") if new.get(k) != s.get(k)}
        if changed:
            out["updated"].append(f"{tid}: " + ", ".join(sorted(changed)))
            if write:
                json.dump(new, open(sp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    n = len(TC.specs(job))
    for i, it in enumerate(items):
        if i in used:
            continue
        n += 1
        tid = f"N{n}"
        out["created"].append(f"{tid}: “{it['text']}” at {float(it['start_s']):.2f} s on {it['track']} (kind {it['kind']} — "
                              f"check it against the card)")
        if write:
            os.makedirs(os.path.join(job, TC.TITLES), exist_ok=True)
            json.dump({"id": tid, "kind": it["kind"], "at_s": float(it["start_s"]), "duration_s": float(it["duration_s"]),
                       "anchor": {"type": "cut", "at_s": float(it["start_s"])},
                       "content": {"lines": [x for x in str(it["text"]).split("\n") if x.strip()]},
                       "synced_from_timeline": {**stamp, "track": it["track"], "frames": [it.get("start"), it.get("duration")],
                                                "created": True}},
                      open(os.path.join(job, TC.TITLES, f"{tid}.title.json"), "w", encoding="utf-8"), indent=1,
                      ensure_ascii=False)
    return out


def _kit_of(job: str, spec: dict) -> str | None:
    import title_card as TC
    try:
        card = json.load(open(os.path.join(job, TC.CARD), encoding="utf-8"))
    except (OSError, ValueError):
        return spec.get("kit")
    return spec.get("kit") or ((card.get("kinds") or {}).get(spec.get("kind")) or {}).get("kit")


def cmd_status(job: str) -> int:
    import title_card as TC
    print("titles:")
    for p in TC.specs(job):
        s = jload(p) or {}
        e = engine_of(s)
        tid = os.path.basename(p)[: -len(".title.json")]
        why = "" if e == "resolve" else " — " + ((s.get("engine_reason") or {}).get("code") or "NO REASON")
        print(f"  {tid}: {e}{why}")
    print("delivery files:")
    for f in renders(job):
        r = jload(record_path(f))
        who, tag = made_by(f)
        q = jload(captions_report(f))
        print(f"  {rel(job, f)}: {who}{' (' + tag + ')' if tag else ''}"
              + (f" · external: {r.get('tool')} — {(r.get('reason') or {}).get('code')}" if r else "")
              + (f" · captions in the pixels: {q.get('verdict')}" if q else ""))
    P, W = check_job(job)
    for w in W:
        print(f"  note: {w}")
    for x in P:
        print(f"  ✗ {x}")
    return 1 if P else 0


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────
def _ff(*args) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _gate_rule8(src: str) -> list:
    """gate.py's rule-8 reading of a console copy ([] = only reads and setup)."""
    import gate
    return gate._rule8_problems(src)


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and bool(cond)
    check("no reason is refused", check_reason(None) and "no reason" in check_reason(None)[0])
    check("an unknown reason is refused, pointing to the owner", any("question for the" in x for x in
                                                                     check_reason({"code": "faster", "why": "it is quicker to do here"})))
    check("an owner reason without their words is refused", any("own words" in x for x in
                                                              check_reason({"code": "owner", "why": "the client wants the kit look"})))
    check("a remux without its source is refused", any("--source" in x for x in
                                                       check_reason({"code": "remux", "why": "faststart and colour tags"})))
    check("a batch reason with a sentence is valid", not check_reason({"code": "batch", "why": "forty UGC variants assembled by script"}))
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("10-export", "08-captions", "00-brief", os.path.join("07-edit", "titles"), os.path.join("09-qa", "soundoff")):
            os.makedirs(os.path.join(job, d))
        W_, H_, fps = 540, 960, 12
        plate = os.path.join(job, "09-qa", "soundoff", "fx-v1-picture-only.mp4")
        _ff("-f", "lavfi", "-i", f"testsrc2=s={W_}x{H_}:r={fps}:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", plate)
        final = os.path.join(td, "fx-v1-final_9x16.mp4")       # first generation, like two Resolve renders of one timeline
        _ff("-f", "lavfi", "-i", f"testsrc2=s={W_}x{H_}:r={fps}:d=4", "-vf", "drawbox=x=100:y=540:w=250:h=60:color=white:t=fill:enable='between(t,1,2)',"
            "drawbox=x=120:y=540:w=200:h=60:color=white:t=fill:enable='between(t,2.5,3.5)'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", final)
        textless = os.path.join(job, "10-export", "fx-v1-textless_9x16.mp4")
        _ff("-i", plate, "-c", "copy", textless)
        record(textless, "ffmpeg", {"code": "derivative", "why": "the textless version the client asked for, copied"})
        who, tag = made_by(final)
        check("a file ffmpeg muxed reads as ffmpeg (the Lavf encoder tag)", who == "ffmpeg" and tag.startswith("encoder=Lavf"), (who, tag))
        # the burned-captions check, on the pair
        import srt_qa
        srt = os.path.join(job, "08-captions", "fx.srt")
        open(srt, "w").write("1\n00:00:01,000 --> 00:00:02,000\nFresh bread\n\n2\n00:00:02,500 --> 00:00:03,500\nbefore six\n")
        q = srt_qa.measure_burned(job, final, plate, srt, "vertical-1080")
        check("captions that are in the pixels, inside the box, pass", q["verdict"] == "PASS", json.dumps(q["cues"]))
        open(srt, "a").write("\n3\n00:00:03,600 --> 00:00:03,900\nlast word\n")
        q = srt_qa.measure_burned(job, final, plate, srt, "vertical-1080")
        check("a cue with nothing in the pixels fails (the burn did not happen there)",
              q["verdict"] == "FAIL" and any(c["status"] == "FAIL" and "no caption" in c["note"] for c in q["cues"]), json.dumps(q["cues"]))
        same = srt_qa.measure_burned(job, plate, plate, srt, "vertical-1080")
        check("a render with no captions at all fails every cue, naming the burn setting",
              same["verdict"] == "FAIL" and "BURN_SUBTITLES" in same.get("note", ""), same.get("note"))
        # the export check
        dst = os.path.join(job, "10-export", "fx-v1-final_9x16.mp4")
        os.replace(final, dst)
        open(srt, "w").write("1\n00:00:01,000 --> 00:00:02,000\nFresh bread\n\n2\n00:00:02,500 --> 00:00:03,500\nbefore six\n")
        P, W = check_job(job)
        check("an ffmpeg-made delivery file with no record is refused, naming native.py record",
              any("ffmpeg made it" in x and "native.py" in x for x in P), P)
        check("…and its captions with no pixel check are refused, naming srt_qa.py burned",
              any("srt_qa.py burned" in x for x in P), P)
        check("a textless version is declared captionless by its name", any("declared captionless" in w for w in W), W)
        record(dst, "ffmpeg", {"code": "batch", "why": "a machine-assembled batch with no Resolve timeline"})
        q = srt_qa.measure_burned(job, dst, plate, srt, "vertical-1080")
        json.dump(q, open(captions_report(dst), "w"))
        P, W = check_job(job)
        check("with a valid batch record and the captions in the pixels: clear, and the reason is printed",
              not P and any("made outside Resolve" in w and "batch" in w for w in W), (P, W))
        open(srt, "a").write("\n")
        P, _ = check_job(job)
        check("a changed .srt makes the pixel check stale", any("changed or is gone" in x for x in P), P)
        q = srt_qa.measure_burned(job, dst, plate, srt, "vertical-1080")
        json.dump(q, open(captions_report(dst), "w"))
        # a remux: a stream copy passes, a re-encode does not
        rmx = os.path.join(job, "10-export", "fx-v1-final_9x16.mov")
        _ff("-i", dst, "-c", "copy", rmx)
        record(rmx, "ffmpeg", {"code": "remux", "why": "a mov container for the client's player", "source": os.path.relpath(dst, job)})
        json.dump(dict(q, render_sha256=sha256_file(rmx)), open(captions_report(rmx), "w"))
        P, _ = check_job(job)
        check("a remux that is a stream copy of its source is clear", not P, P)
        _ff("-i", dst, "-c:v", "libx264", "-crf", "30", rmx)
        record(rmx, "ffmpeg", {"code": "remux", "why": "a mov container for the client's player", "source": os.path.relpath(dst, job)})
        json.dump(dict(q, render_sha256=sha256_file(rmx)), open(captions_report(rmx), "w"))
        P, _ = check_job(job)
        check("a 'remux' that re-encoded is refused (its packets differ)", any("not a stream copy" in x for x in P), P)
        os.remove(rmx)
        # the console copy compiles and carries the specs and the cues
        import title_card as TC
        TC.propose(job, "ads", accent="#E8432E", page_bg="#111111")
        json.dump({"id": "T1", "kind": "hero", "duration_s": 2.5, "at_s": 1.0, "anchor": {"type": "settle", "at_s": 1.0},
                   "content": {"lines": ["Sleep through", "the night"]}}, open(os.path.join(job, "07-edit", "titles", "T1.title.json"), "w"))
        json.dump({"id": "T2", "kind": "hero", "engine": "hyperframes", "duration_s": 2.0, "at_s": 4.0,
                   "content": {"lines": ["x"]}}, open(os.path.join(job, "07-edit", "titles", "T2.title.json"), "w"))
        json.dump({"id": "T3", "kind": "lower-third", "duration_s": 2.0, "at_s": 6.0, "content": {"lines": ["x"]}},
                  open(os.path.join(job, "07-edit", "titles", "T3.title.json"), "w"))
        out0, *_x0 = console_copy(job, srt, "textplus", host_job="/Users/someone/jobs/job")
        src0 = open(out0, encoding="utf-8").read()
        check("v2.49 computer-control rule: the default copy places no title and no Text+ caption, says why, and the gate reads it as clean",
              "\nPLACE_TITLES = False" in src0 and "\nPLACE_SUBTITLES = False" in src0
              and any("computer-control rule" in n_ for n_ in _x0[-1]) and _gate_rule8(src0) == [], (_x0[-1], _gate_rule8(src0)))
        out, nt, nc, sk, _notes = console_copy(job, srt, "textplus", host_job="/Users/someone/jobs/job", owner_paste=True)
        src = open(out, encoding="utf-8").read()
        check("…--owner-paste writes the placing copy, and the gate refuses it through run_script",
              "\nPLACE_TITLES = True" in src and bool(_gate_rule8(src)), _gate_rule8(src)[:2])
        check("the console copy turns PLACE_TITLES and PLACE_SUBTITLES on, with the resolve-engine titles and the cues",
              nt == 1 and nc == 2 and "\nPLACE_TITLES = True" in src and "\nPLACE_SUBTITLES = True" in src
              and "'Sleep through\\nthe night'" in src and 'SUBTITLES_AS = "textplus"' in src, (nt, nc))
        check("…skips the titles another engine renders and a kind not on the card, and maps paths to Resolve's machine",
              sk == ["T2 (hyperframes)", "T3 (kind 'lower-third' is not on the title card)"] and 'SRT_PATH = r"/Users/someone/jobs/job/08-captions/fx.srt"' in src, (sk,))
        check("…a card that does not lint generates no titles: the stock template, and the copy says so",
              "TITLE_TEMPLATES = {}  # __NATIVE_TEMPLATES__" in src and any("no generated titles" in n_ for n_ in _notes)
              and any("stock template" in n_ for n_ in _notes), _notes)
        # ⚡ v2.45 (2026-10-29: "It keeps making mp4s which it imports")
        check("spec_text: a bool is never a word (sclp's `plate: true` became the field \"True\")",
              spec_text({"content": {"lines": ["Clinically studied"], "plate": True, "mark": "bar"}}) == ("Clinically studied", {})
              and spec_text({"content": {"price": "$39", "plate": True, "label_pos": "below"}}) == ("$39", {"price": "$39"}))
        hf = os.path.join(td, "S01.mov")
        _ff("-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.2", "-metadata", "hyperframes_renderer=hyperframes",
            "-metadata", "hyperframes_version=0.8.204", "-movflags", "use_metadata_tags", "-c:v", "prores_ks", hf)
        mk = render_maker(hf)
        check("render_maker names what made a title movie from its own tags: HyperFrames 0.8.204, muxed by ffmpeg",
              mk.startswith("HyperFrames 0.8.204") and "muxed by ffmpeg (Lavf" in mk, mk)
        check("a job whose every delivery file is a batch or a derivative has no timeline to dump: not asked",
              not dump_problems(job), dump_problems(job))
        cut_ = os.path.join(job, "10-export", "fx-v1-final_4x5.mp4")
        open(cut_, "wb").write(b"\x00\x00\x00\x18ftypmp42 a Resolve render")
        P_ = dump_problems(job)
        check("export with titles and a Resolve delivery render but no timeline dump refuses: export reads what is ON the "
              "timeline", any("no 07-edit/timeline-dump.json" in x for x in P_), P_)
        dp_ = os.path.join(job, "07-edit", "timeline-dump.json")
        json.dump({"fps": 12, "tracks": {"video1": [{"name": "a.mp4", "type": "video", "start": 0, "duration": 48}]}}, open(dp_, "w"))
        check("…a dump from before v2.45 (no media files) refuses", any("carries no media files" in x for x in dump_problems(job)))
        json.dump({"fps": 12, "tracks": {"video1": [{"name": "a.mp4", "type": "video", "start": 0, "duration": 48,
                                                     "file": "/Users/x/03-clips/a.mp4"}]}}, open(dp_, "w"))
        os.utime(dp_, (os.path.getmtime(cut_) - 60, os.path.getmtime(cut_) - 60))
        check("…a dump older than the newest delivery render refuses", any("older than the newest" in x for x in dump_problems(job)))
        os.utime(dp_, None)
        check("…a current dump with media files is clear", not dump_problems(job), dump_problems(job))
        os.remove(cut_)
        # the generated titles: a card that lints → TITLE_TEMPLATES, the fonts, the words per tool
        heavy = TC._sysfont("InterDisplay-ExtraBold.otf", "Inter-Bold.otf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf")
        regular = TC._sysfont("Inter-Regular.otf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf")
        if heavy and regular:
            cp_ = os.path.join(job, TC.CARD)
            cj = json.load(open(cp_, encoding="utf-8"))
            fh, fr = TC.read_font(heavy), TC.read_font(regular)
            cj["fonts"] = {"anchor": {"family": fh["family"], "file": heavy, "weight": int(fh["weight_class"])},
                           "companion": {"family": fr["family"], "file": regular, "weight": int(fr["weight_class"])}}
            json.dump(cj, open(cp_, "w"), indent=1)
            json.dump({"id": "P1", "kind": "price", "duration_s": 2.0, "at_s": 4.0, "anchor": {"type": "cut", "at_s": 4.0},
                       "content": {"price": "$39", "was": "$59", "plate": True}},
                      open(os.path.join(job, "07-edit", "titles", "P1.title.json"), "w"))
            out, nt, nc, sk, notes = console_copy(job, None, "track", host_job="/Users/someone/jobs/job", install=True,
                                                  owner_paste=True)
            src = open(out, encoding="utf-8").read()
            g_ = {}
            exec(compile(src.split("\nresolve = app.GetResolve()")[0], "cfg", "exec"), g_)     # the CONFIG block only
            T_ = g_["TITLE_TEMPLATES"]
            check("a card that lints: the console copy carries the generated templates (names with the card hash, the comp "
                  "on Resolve's machine), the fonts, CHECK_FONTS, the install switch and the .drfx",
                  set(T_) == set(cj["kinds"]) and all(v["name"].endswith(TC._sha(cp_)[:8]) for v in T_.values())
                  and T_["hero"]["comp"].startswith("/Users/someone/jobs/job/07-edit/titles/fusion/")
                  and g_["FONT_FILES"] == [os.path.abspath(heavy), os.path.abspath(regular)] and g_["CHECK_FONTS"] and g_["ADD_FONTS"]
                  and g_["INSTALL_TITLE_TEMPLATES"] and g_["DRFX_PATH"].endswith(".drfx") and any("generated" in n_ for n_ in notes),
                  (list(T_), notes))
            rows_ = {r["id"]: r for r in g_["TITLES"]}
            check("…each row carries its words per tool: the price on TT_Main and the was on its own tool; the bool is gone",
                  rows_["P1"]["words"] == {"TT_Main": "$39", "was": "$59"} and rows_["P1"]["kit"] == "price-card"
                  and rows_["T1"]["words"]["TT_Main"] == "Sleep through\nthe night", rows_)
            json.dump(dict(cj, tracking_em=-0.02), open(cp_, "w"), indent=1)
            try:
                console_copy(job, None, "track", build=False)
                refused_ = False
            except SystemExit as e_:
                refused_ = "stale" in str(e_)
            check("a card edited after the titles were generated, with --no-build: refused (no stale template reaches Resolve)",
                  refused_)
            json.dump(cj, open(cp_, "w"), indent=1)
            for n_ in (1, 2):
                json.dump({"id": f"T1.opt{n_}", "kind": "hero", "duration_s": 2.5, "at_s": 1.0, "anchor": {"type": "settle", "at_s": 1.0},
                           "content": {"lines": ["Sleep through", "the night"] if n_ == 1 else ["Wake up", "rested"]}},
                          open(os.path.join(job, "07-edit", "titles", f"T1.opt{n_}.title.json"), "w"))
            out, nt, *_r = console_copy(job, None, "track", titles=False, host_job="/Users/someone/jobs/job", options="T1",
                                        owner_paste=True)
            g_ = {}
            exec(compile(open(out, encoding="utf-8").read().split("\nresolve = app.GetResolve()")[0], "cfg", "exec"), g_)
            check("--options T1: PLACE_TITLE_OPTIONS on, both options as rows (option 1 and 2), the stills folder made and "
                  "mapped to Resolve's machine; PLACE_TITLES off",
                  g_["PLACE_TITLE_OPTIONS"] and [r["option"] for r in g_["TITLE_OPTIONS"]["T1"]] == [1, 2]
                  and g_["OPTIONS_DIR"] == "/Users/someone/jobs/job/09-qa/titles" and not g_["PLACE_TITLES"]
                  and os.path.isdir(os.path.join(job, "09-qa", "titles", "T1")), g_.get("TITLE_OPTIONS"))
        else:
            print("  [SKIP] no system fonts: the generated-titles copy is not exercised")
    print("-" * 60)
    print("selftest OK — reasons are refused unless one of four with a sentence (and the owner's words); an ffmpeg-made "
          "file with no record is refused; captions are checked in the pixels against a captions-off render; a remux "
          "must be a stream copy; the console copy carries the titles and the cues; v2.45: the generated Fusion titles, "
          "their fonts and per-tool words go into the copy (a stale one refuses), options as rows for Resolve stills, a "
          "bool is never a word, a title movie's maker is named, and export needs a current timeline dump" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("reasons")
    c = sub.add_parser("console"); c.add_argument("job"); c.add_argument("--srt")
    c.add_argument("--captions-as", choices=["track", "textplus"], default="track")
    c.add_argument("--no-titles", action="store_true"); c.add_argument("--host-job")
    c.add_argument("--expect", help="a timeline snapshot from before the edit: the copy checks the invariant after it")
    c.add_argument("--options", help="a title id: PLACE_TITLE_OPTIONS for its <id>.opt1..3 specs (Resolve stills)")
    c.add_argument("--install", action="store_true", help="INSTALL_TITLE_TEMPLATES: fusion.InstallFile the .drfx first")
    c.add_argument("--no-build", action="store_true", help="use the generated titles as they are (fusion_titles.py check)")
    c.add_argument("--no-add-fonts", action="store_true", help="CHECK_FONTS only: never AddFont")
    c.add_argument("--format", default="vertical-1080")
    c.add_argument("--owner-paste", action="store_true", help="the old copy that PLACES titles through the API, for the owner "
                   "to paste into Workspace ▸ Console themselves — gate.py refuses it through run_script (the computer-control rule)")
    tp = sub.add_parser("templates", help="fusion_titles.py build: the card's Fusion titles"); tp.add_argument("job")
    tp.add_argument("--format", default="vertical-1080"); tp.add_argument("--fps", type=float)
    op = sub.add_parser("options", help="the console copy with PLACE_TITLE_OPTIONS for one title"); op.add_argument("job")
    op.add_argument("id"); op.add_argument("--host-job"); op.add_argument("--format", default="vertical-1080")
    op.add_argument("--owner-paste", action="store_true")
    r = sub.add_parser("record"); r.add_argument("job"); r.add_argument("file"); r.add_argument("--tool", required=True)
    reason_args(r); r.add_argument("--source")
    for name in ("status", "check"):
        s = sub.add_parser(name); s.add_argument("job")
    sy = sub.add_parser("sync-specs", help="rewrite each title spec's time, length and words from the timeline dump")
    sy.add_argument("job"); sy.add_argument("--dump"); sy.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "reasons":
        for k, v in REASONS.items():
            print(f"  {k:<11} {v}")
        return 0
    if a.cmd in ("console", "options"):
        if a.cmd == "options":
            out, nt, nc, sk, notes = console_copy(a.job, None, "track", False, a.host_job, None, options=a.id, fmt_name=a.format,
                                                  owner_paste=a.owner_paste)
        else:
            out, nt, nc, sk, notes = console_copy(a.job, a.srt, a.captions_as, not a.no_titles, a.host_job, a.expect,
                                                  options=a.options, install=a.install, build=not a.no_build,
                                                  add_fonts=not a.no_add_fonts, fmt_name=a.format,
                                                  owner_paste=a.owner_paste)
        print(f"wrote {out}: {nt} title(s), {nc} caption cue(s)" + (f"; not placed, another engine: {', '.join(sk)}" if sk else ""))
        for n_ in notes:
            print(f"  note: {n_}")
        if a.owner_paste:
            print("OWNER ONLY: paste it into Workspace ▸ Console yourself — gate.py refuses it through run_script (the computer-control rule). "
                  "A row PLACE_TITLES could not place is a STOP: report it — never render the title elsewhere to get past it.")
        else:
            print("Run it in Resolve (the MCP's run_script, or Workspace ▸ Console) for the setup and the read-backs; in "
                  f"run_script mode write result['native'] to {PLACEMENT}. Titles are placed by computer control "
                  "— never rendered elsewhere to get past a title that will not place.")
        return 0
    if a.cmd == "templates":
        import fusion_titles as FT
        man = FT.build(a.job, a.format, a.fps)
        for k, v in man["kinds"].items():
            print(f"  {k}: {v['name']}  ({v['setting']}, {v['comp']})")
        print(f"wrote {FT.OUT}/templates.json — card {man['card_sha256'][:8]}, {man['fps']:g} fps, {man['format']}")
        return 0
    if a.cmd == "record":
        if not a.reason:
            print("error: --reason " + "|".join(REASONS), file=sys.stderr)
            return 2
        rr = record(a.file, a.tool, reason_of(a))
        print(f"wrote {record_path(a.file)} — {rr['reason']['code']}: {rr['reason'].get('why')}")
        return 0
    if a.cmd == "status":
        return cmd_status(a.job)
    if a.cmd == "sync-specs":
        r = sync_specs(a.job, a.dump, a.write)
        verb = "" if a.write else "would be "
        for k, lab in (("updated", f"{verb}updated"), ("created", f"{verb}created"), ("words_changed", "words changed"),
                       ("unplaced", "not on the timeline (left as they are)"), ("problems", "⚠")):
            for x in r[k]:
                print(f"  {lab}: {x}")
        if not a.write and (r["updated"] or r["created"]):
            print("  (dry run — --write rewrites the specs; then title_card.py check and title_qa.py native again)")
        return 1 if r["problems"] and not (r["updated"] or r["created"]) else 0
    if a.cmd == "check":
        P, W = check_job(a.job)
        import title_card as TC
        P += TC.timeline_title_media(a.job)          # approve export runs it through title_card.check_job
        for w in W:
            print(f"  note: {w}")
        for x in P:
            print(f"  ✗ {x}")
        print("clear" if not P else f"{len(P)} problem(s)")
        return 1 if P else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
