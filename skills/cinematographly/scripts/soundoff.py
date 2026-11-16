#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""soundoff.py — the client's sound-off check, run, recorded and handed over before the client runs it.

Author, 2026-10-27: *"One of the main ways for clients to check is if the video tells a story without sound and
voiceover."* Research and a three-judge council (lab record lab-00019 (not shipped), unanimous top six). The one
definition of the tests is `references/sound-off-story.md`; this script makes them hard to skip and hard to fake.

  T1  the muted feed — volume 0, everything as shipped: captions, titles, the end card. One per delivery file.
  T2  the picture alone — no sound, no voiceover and no caption of the voiceover: the captionless master, or
      Resolve's picture-only render (render-mp4.py PICTURE_ONLY), with only the titles the card permits.

Commands
  proofs <job> [--cut <file>] [--t2-source <file>] [--phone]
        09-qa/soundoff/<name>.T2.<ext> from the captionless source and <name>.T1.<ext> from every delivery file in
        10-export/, the audio stripped by stream copy (the picture is those bytes' picture). PROOFS.json keeps each
        proof's hash and the hash of the file it came from, so a re-render makes the proof — and every verdict
        logged on it — stale. --cut <file>: a T2 proof of the locked cut, for the read before lock.
        --phone: also a 390-px-wide copy of each T1 proof, the size a phone shows.
  map init <job> [--windows "HOOK=0:00-0:06,S1=0:06-0:15,..."] [--narrow --why "..."]
        the story map: one row per beat of the approved script ([HOOK] [SCENE n] [CTA]), its window on the cut from
        07-edit/timeline-dump.json (clip names carry the beat: HOOK_, S1-C1_, S2B_, CTA_). Re-running keeps your
        notes and says which windows moved. --narrow: the talking-head UGC map, whose story is the speech — four
        rows (WHO, PRODUCT, PROOF, OFFER) the picture alone must show (house rule K4/C5).
  map set <job> --beat <ID> --shows "<what the PICTURE shows>" --carries Y|partial|N [--fix "..."]
  map waive <job> --beat <ID> --reason "..." --quote "<the owner's words>"
  map show <job>                      writes STORY-MAP.md and prints it
  strip <job> [--proof <file>]        one frame per beat: STRIP-viewer.png (numbers only, so it cannot tell a
                                      cold viewer the story — K6) and STRIP-producer.png (ids, windows, notes)
  placement <job> --sound-on-only --platforms "..." --quote "<the owner's words>"   T1 becomes advisory (K2)
  placement <job> --muted                                                           undo it
  waive <job> --what T2 --sound-led --reason "..." --quote "<the owner's words>"   a music video, an ASMR piece (K4)
  waive <job> --what cold-viewer --reason "..." --quote "<the owner's words>"      a producer-only T2 (K3)
  claims <job>      every number and price the voiceover says, against the captions (T1) and the titles (T2)
  console <job>     07-edit/resolve-production-console.soundoff.py — one duration marker per beat, coloured by
                    whether the picture carries it (Green Y · Yellow partial · Red N · Cream waived · Blue unread)
  pack <job> [--draft]   09-qa/soundoff/PACK/: the proofs first (T2, then T1), README (play at volume 0), and an
                    APPENDIX to read after watching (the map, the cold viewer's words, what was fixed) — K7
  check <job>       what `gate.py approve export` reads. `lock-check <job>` is what `approve lock` reads.
  --selftest

The verdicts are logged with qa_log.py --gate soundoff (the evidence rules live there and in validate_row below):
  python3 scripts/qa_log.py --project <job> --gate soundoff --test T2 --viewer cold --who "Ana" \\
      --proof 09-qa/soundoff/<name>.T2.mp4 --retell "<her own words, written before she sees the beat list>"
  python3 scripts/qa_log.py --project <job> --gate soundoff --test T2 --viewer cold --who "Ana" \\
      --proof 09-qa/soundoff/<name>.T2.mp4 --verdict PASS --beats "HOOK@0:02,S2@0:11,CTA@0:24" \\
      --obs "she named the bakery and the 6 a.m. bake from the hands at 0:02; got the offer from the end card"

What it cannot do: judge the story. It makes the read happen on the right bytes, in the right order, by someone who
has not read the script, and it keeps the record. Thresholds marked [assumed] wait for real jobs to calibrate them.
Exit codes: 0 ok · 1 refused / problems · 2 usage, IO or ffmpeg error.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SO = os.path.join("09-qa", "soundoff")
PROOFS = os.path.join(SO, "PROOFS.json")
MAP = os.path.join(SO, "STORY-MAP.json")
MAP_MD = os.path.join(SO, "STORY-MAP.md")
LOG = os.path.join(SO, "SOUNDOFF-LOG.jsonl")
PLACEMENT = os.path.join(SO, "PLACEMENT.json")
WAIVERS = os.path.join(SO, "WAIVERS.json")
PACK = os.path.join(SO, "PACK")
CONSOLE = os.path.join(HERE, "resolve-production-console.py")
CONSOLE_COPY = "resolve-production-console.soundoff.py"
RENDER_EXT = (".mp4", ".mov", ".mxf")
REFERENCE = "references/sound-off-story.md"

MIN_BEATS = 3            # beat ids a PASS cites, each inside its window [assumed] (jury K5)
RETELL_MIN_WORDS = 15    # a retell shorter than this is a nod, not a retelling [assumed] (O)
SCRIPT_ECHO = 0.5        # share of a retell's 5-word runs found verbatim in the script: it was read, not watched [assumed]
RESTATE = 0.6            # share of a `shows` cell's words that are the beat's own VO words: a restatement [assumed]
ENDCARD_MIN_S = 2.0      # the end card's dwell [assumed] (B11; the DR mute test's 2–3 s)
CARRIES = ("Y", "partial", "N")
NARROW_ROWS = (("WHO", "who is talking — the person, seen"),
               ("PRODUCT", "the product, seen in use or in hand"),
               ("PROOF", "the proof, seen — a result, a demo, a card"),
               ("OFFER", "the offer and what to do next, as designed text or the end card"))
COLORS = {"Y": "Green", "partial": "Yellow", "N": "Red", "waived": "Cream", "": "Blue"}
# a beat named in a clip's file name: HOOK_v1.mp4 · S1-C1_host_kling_v2.mp4 · S2B_insert.mp4 · CTA_card.mp4
BEAT_IN_NAME = re.compile(r"(?<![A-Za-z0-9])(HOOK|CTA|S\d+)(?!\d)", re.I)
TC = re.compile(r"^(\d{1,2}):([0-5]\d)(?:\.(\d{1,3}))?$")
NUM = re.compile(r"[$€£¥]?\s?\d[\d.,]*\s?%?")
ENDCARD_KINDS = ("endcard", "end-card", "end_card")

from qa_log import INTENTION  # noqa: E402  (one definition of "an intention, not an observation")


# ── small things ───────────────────────────────────────────────────────────────────────────────────────────
def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


_SHA: dict = {}


def sha256_file(p: str) -> str:
    """Hashed once per (path, size, mtime) in a process: the export check reads the same 4K masters several times."""
    st = os.stat(p)
    k = (os.path.abspath(p), st.st_size, st.st_mtime_ns)
    if k not in _SHA:
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        _SHA[k] = h.hexdigest()
    return _SHA[k]


def jload(p: str):
    try:
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None
    except ValueError:
        return None


def jsave(p: str, d) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def J(job: str, *parts: str) -> str:
    return os.path.join(job, *parts)


def rel(job: str, p: str) -> str:
    return os.path.relpath(os.path.abspath(p), os.path.abspath(job))


def tc_of(s: float) -> str:
    s = max(0.0, float(s))
    return f"{int(s // 60)}:{int(s % 60):02d}"


def parse_tc(t: str) -> float | None:
    m = TC.match(t.strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2)) + (float("0." + m.group(3)) if m.group(3) else 0.0)


def words(t: str) -> list:
    return re.findall(r"[a-zà-ÿăâîșțşţ0-9']+", (t or "").lower())


def run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def probe(p: str) -> dict:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", p], 120)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return {}
    st = d.get("streams") or []
    v = next((s for s in st if s.get("codec_type") == "video"), {})
    fr = v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"
    try:
        n, dn = fr.split("/")
        fps = float(n) / float(dn) if float(dn) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    try:
        dur = float((d.get("format") or {}).get("duration") or v.get("duration") or 0)
    except ValueError:
        dur = 0.0
    return {"duration": dur, "fps": fps, "width": v.get("width"), "height": v.get("height"),
            "audio": any(s.get("codec_type") == "audio" for s in st), "video": bool(v)}


def verify_quote(quote: str) -> str | None:
    """The owner's words, checked the way gate.py checks an approval: a quote nobody typed is refused."""
    q = (quote or "").strip()
    if len(q.split()) < 2:
        return "--quote must be the owner's reply verbatim (two words or more)"
    try:
        import gate as G
        why = G.quote_refusal(q, G.active_job()[0])   # (3.1) verified, or present on a hookless studio (build review 3:
        #                                             never on a job another home checked) — never assumed
    except Exception as e:                # noqa: BLE001 — (3.1) a check that cannot run refuses
        return f"the quote cannot be checked ({type(e).__name__}) — nothing is recorded"
    return (why + " — ask the approver, then record their words") if why else None


# ── the job's files ────────────────────────────────────────────────────────────────────────────────────────
def renders(job: str) -> list:
    exp = J(job, "10-export")
    return sorted(p for p in glob.glob(os.path.join(exp, "*")) if p.lower().endswith(RENDER_EXT) and os.path.isfile(p))


def t2_candidates(job: str) -> list:
    """The captionless sources, newest first: Resolve's picture-only render, then the master."""
    own = [p for p in glob.glob(J(job, SO, "*picture-only*")) if p.lower().endswith(RENDER_EXT)
           and not re.search(r"\.T[12](-cut)?\.(mp4|mov)$|\.phone\.mp4$", p)]
    masters = [p for p in renders(job) if re.search(r"master", os.path.basename(p), re.I)]
    return sorted(own, key=os.path.getmtime, reverse=True) + sorted(masters, key=os.path.getmtime, reverse=True)


def script_beats(job: str) -> tuple:
    import shotlist as SL
    p = SL.find_script(job)
    if not p or not os.path.isfile(p):
        return None, []
    return p, SL.parse_script(SL.read(p))


def timeline(job: str) -> dict | None:
    p = J(job, "07-edit", "timeline-dump.json")
    d = jload(p)
    if not d:
        return None
    fps = float(d.get("fps") or 24.0)
    clips, end = [], 0.0
    for tn, items in (d.get("tracks") or {}).items():
        for it in items or []:
            s = it.get("start_s") if it.get("start_s") is not None else (it.get("start") or 0) / fps
            du = it.get("duration_s") if it.get("duration_s") is not None else (it.get("duration") or 0) / fps
            end = max(end, float(s) + float(du))
            if tn == "video1" and "transition" not in str(it.get("type") or "").lower():
                clips.append({"name": str(it.get("name") or ""), "t0": float(s), "t1": float(s) + float(du)})
    return {"fps": fps, "clips": sorted(clips, key=lambda c: c["t0"]), "end": end, "sha256": sha256_file(p)}


def windows_from(ids: list, clips: list) -> dict:
    """Each beat's window = the span of the V1 clips that carry its id; an unnamed clip (stock, a card) belongs
    to the beat before it — the first beat, if it opens the cut."""
    want = {i.upper() for i in ids}
    owner, cur = [], None
    for c in clips:
        m = BEAT_IN_NAME.search(c["name"])
        b = m.group(1).upper() if m and m.group(1).upper() in want else None
        cur = b or cur
        owner.append(b or cur)
    first = next((o for o in owner if o), None)
    W = {}
    for c, o in zip(clips, owner):
        o = o or first
        if not o:
            continue
        w = W.setdefault(o, {"t0": c["t0"], "t1": c["t1"], "shots": []})
        w["t0"], w["t1"] = min(w["t0"], c["t0"]), max(w["t1"], c["t1"])
        w["shots"].append(c["name"])
    return W


def parse_windows(spec: str) -> dict:
    W = {}
    for part in [p.strip() for p in (spec or "").split(",") if p.strip()]:
        m = re.match(r"^([A-Za-z0-9_-]+)\s*=\s*([\d:.]+)\s*-\s*([\d:.]+)$", part)
        a = parse_tc(m.group(2)) if m else None
        b = parse_tc(m.group(3)) if m else None
        if not m or a is None or b is None or b <= a:
            raise SystemExit(f"error: --windows item {part!r} is not ID=m:ss-m:ss")
        W[m.group(1).upper()] = {"t0": a, "t1": b, "shots": []}
    return W


# ── the story map ──────────────────────────────────────────────────────────────────────────────────────────
def load_map(job: str) -> dict | None:
    return jload(J(job, MAP))


def map_init(job: str, narrow: bool = False, why: str = "", windows: str = "", duration: float | None = None) -> tuple:
    T = timeline(job)
    sp, beats = script_beats(job)
    if narrow:
        if len((why or "").split()) < 3:
            raise SystemExit("error: --narrow needs --why \"<why this film's story is the speech>\" — the narrow T2 is "
                             "the talking-head UGC exception (house rule K4/C5), not a shortcut")
        end = duration if duration else (T["end"] if T else None)
        if not end:
            raise SystemExit("error: --narrow needs the film's length — dump the cut (07-edit/timeline-dump.json) or "
                             "pass --duration <s>")
        rows = [{"id": k, "n": i + 1, "kind": "narrow", "note": d, "vo": [], "t0": 0.0, "t1": round(end, 3),
                 "shots": []} for i, (k, d) in enumerate(NARROW_ROWS)]
        source = "whole film"
    else:
        if not beats:
            raise SystemExit("error: no approved script with [HOOK] / [SCENE n] / [CTA] beats (01-script/SCRIPT-*.md, "
                             "script-format.md) — the map is the script's beats laid on the cut")
        ids = [b["label"] for b in beats]
        if windows:
            W, source = parse_windows(windows), "manual"
        elif T:
            W, source = windows_from(ids, T["clips"]), "timeline"
        else:
            raise SystemExit("error: no 07-edit/timeline-dump.json — dump the cut (resolve-production-console.py "
                             "DUMP_TIMELINE_JSON) or give --windows \"HOOK=0:00-0:06,S1=0:06-0:15,...\"")
        rows = []
        for i, b in enumerate(beats):
            w = W.get(b["label"].upper()) or {}
            rows.append({"id": b["label"].upper(), "n": i + 1, "kind": b["kind"], "note": b.get("note") or "",
                         "vo": [f"{s}: {l}" for s, l in b.get("lines") or []],
                         "t0": round(w["t0"], 3) if w else None, "t1": round(w["t1"], 3) if w else None,
                         "shots": w.get("shots", [])})
    old = {b["id"]: b for b in ((load_map(job) or {}).get("beats") or [])}
    moved = []
    for r in rows:
        o = old.get(r["id"])
        for k in ("shows", "carries", "fix", "waiver"):
            r[k] = (o or {}).get(k) if o else ("" if k != "waiver" else None)
        if o and (o.get("t0"), o.get("t1")) != (r["t0"], r["t1"]):
            moved.append(f"{r['id']}: {fmt_win(o)} → {fmt_win(r)}")
    d = {"version": 1, "generated": now_iso(), "mode": "narrow" if narrow else "full", "why": why or "",
         "script": rel(job, sp) if sp else None, "windows": source,
         "timeline_sha256": T["sha256"] if (T and source == "timeline") else None,
         "fps": T["fps"] if T else None,
         "end_s": round(T["end"], 3) if T else (duration or None), "beats": rows}
    jsave(J(job, MAP), d)
    write_map_md(job, d)
    return d, moved


def fmt_win(b: dict) -> str:
    return "—" if b.get("t0") is None else f"{tc_of(b['t0'])}–{tc_of(b['t1'])}"


def map_set(job: str, beat: str, shows: str, carries: str, fix: str = "") -> dict:
    d = load_map(job)
    if not d:
        raise SystemExit("error: no story map — soundoff.py map init <job>")
    b = next((x for x in d["beats"] if x["id"] == beat.upper()), None)
    if not b:
        raise SystemExit(f"error: no beat {beat!r} in the map ({', '.join(x['id'] for x in d['beats'])})")
    s = (shows or "").strip()
    if len(s.split()) < 4 or INTENTION.match(s):
        raise SystemExit("REFUSED: --shows is what the PICTURE shows in that window, watched with the sound off — "
                         "\"her hands fold the dough, flour on the bench, the clock at 5:40\", not \"good\"")
    vo = set(w for line in b.get("vo") or [] for w in words(line.split(":", 1)[-1]))
    sw = words(s)
    if vo and len(sw) >= 5 and sum(1 for w in sw if w in vo) / len(sw) >= RESTATE:
        raise SystemExit("REFUSED: that is the beat's voiceover, not what the picture shows. Watch the window muted "
                         "and write what is IN the frames — the test is whether the picture says it without the words")
    c = {"y": "Y", "yes": "Y", "partial": "partial", "p": "partial", "n": "N", "no": "N"}.get((carries or "").lower())
    if not c:
        raise SystemExit("error: --carries Y | partial | N")
    if c in ("N", "partial") and not (fix or "").strip():
        print(f"  note: {b['id']} is {c} — say the fix (--fix: a shot, an insert, a title the card permits, a re-cut); "
              f"an unfixed N blocks the lock (house rule K1)", file=sys.stderr)
    b.update({"shows": s, "carries": c, "fix": (fix or "").strip() or b.get("fix") or "", "set": now_iso()})
    if c == "Y":
        b["waiver"] = None
    jsave(J(job, MAP), d)
    write_map_md(job, d)
    return b


def map_waive(job: str, beat: str, reason: str, quote: str) -> dict:
    d = load_map(job)
    if not d:
        raise SystemExit("error: no story map — soundoff.py map init <job>")
    b = next((x for x in d["beats"] if x["id"] == beat.upper()), None)
    if not b:
        raise SystemExit(f"error: no beat {beat!r} in the map")
    if len((reason or "").split()) < 3:
        raise SystemExit("error: --reason says why this beat may stay unread without sound")
    e = verify_quote(quote)
    if e:
        raise SystemExit("REFUSED: " + e)
    b["waiver"] = {"reason": reason.strip(), "quote": quote.strip(), "at": now_iso()}
    jsave(J(job, MAP), d)
    write_map_md(job, d)
    return b


def write_map_md(job: str, d: dict) -> str:
    L = [f"# Story map — {os.path.basename(os.path.abspath(job))} ({d.get('mode')})", "",
         f"Generated by soundoff.py map ({d.get('generated')}); windows from {d.get('windows')}. "
         f"What the PICTURE shows in each window, watched with the sound off ({REFERENCE}).", ""]
    if d.get("mode") == "narrow":
        L += [f"Narrow T2 (talking-head UGC): {d.get('why')}", ""]
    L += ["| # | beat | window | the picture shows | carries | fix / waiver |", "|---|---|---|---|---|---|"]
    for b in d["beats"]:
        fw = b.get("fix") or ""
        if b.get("waiver"):
            fw = f"WAIVED — {b['waiver']['reason']}"
        L.append(f"| {b['n']} | {b['id']} | {fmt_win(b)} | {b.get('shows') or '—'} | {b.get('carries') or '—'} | {fw} |")
    out = J(job, MAP_MD)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return out


def map_problems(job: str, stage: str) -> tuple:
    """(problems, notes) for the map. stage = lock | export."""
    P, W = [], []
    d = load_map(job)
    if not d:
        (W if stage == "lock" else P).append(
            "no story map — soundoff.py map init <job>, then map set each beat from the muted proof "
            "(what the picture shows; Y / partial / N)")
        return P, W
    T = timeline(job)
    if d.get("timeline_sha256") and T and T["sha256"] != d["timeline_sha256"]:
        (W if stage == "lock" else P).append("the cut changed after the story map was made — soundoff.py map init "
                                             "again (it keeps your notes and lists the windows that moved)")
    if d.get("windows") == "manual":
        W.append("the story map's windows were typed (--windows), not read from the cut")
    if d.get("mode") == "narrow":
        W.append(f"narrow T2 (talking-head UGC): {d.get('why')}")
    for b in d["beats"]:
        if b.get("waiver"):
            W.append(f"beat {b['id']} waived: {b['waiver']['reason']}")
            continue
        if b.get("t0") is None:
            (W if stage == "lock" else P).append(f"beat {b['id']}: no shot on the cut carries this beat's name — "
                                                 f"map init --windows, or waive it if it was cut")
        if not b.get("carries"):
            (W if stage == "lock" else P).append(f"beat {b['id']}: not read yet (map set --shows … --carries …)")
        elif b["carries"] == "N":
            P.append(f"beat {b['id']}: the picture does not carry it — fix it ({b.get('fix') or 'no fix named'}) and "
                     f"re-read, or waive it with the owner's words (map waive)")
        elif b["carries"] == "partial":
            W.append(f"beat {b['id']}: carried only partly — {b.get('fix') or 'no fix named'}")
    return P, W


# ── proofs ─────────────────────────────────────────────────────────────────────────────────────────────────
def load_proofs(job: str) -> dict:
    return jload(J(job, PROOFS)) or {"version": 1, "proofs": [], "t2_source": None}


def make_proof(job: str, src: str, test: str, stage: str, phone: bool = False) -> dict:
    stem, ext = os.path.splitext(os.path.basename(src))
    oext = ".mp4" if ext.lower() == ".mp4" else ".mov"
    tag = "T2-cut" if stage == "lock" else test
    dst = J(job, SO, f"{stem}.{tag}{oext}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-map", "0:v:0", "-c:v", "copy", "-an",
             "-map_metadata", "-1", dst])
    if r.returncode != 0:
        raise SystemExit(f"error: ffmpeg could not strip the audio from {rel(job, src)}: {r.stderr.strip()[:200]}")
    a, b = probe(src), probe(dst)
    if not b.get("video") or b.get("audio"):
        raise SystemExit(f"error: {rel(job, dst)} is not a silent picture (video={b.get('video')}, audio={b.get('audio')})")
    fr = 1.0 / (a.get("fps") or 24.0)
    if a.get("duration") and abs(b["duration"] - a["duration"]) > fr + 0.05:
        raise SystemExit(f"error: the proof runs {b['duration']:.3f} s and its source {a['duration']:.3f} s — more than "
                         f"a frame apart")
    rec = {"test": test, "stage": stage, "file": rel(job, dst), "sha256": sha256_file(dst),
           "source": rel(job, src), "source_sha256": sha256_file(src), "duration_s": round(b["duration"], 3),
           "made": now_iso(), "phone": None}
    if phone and test == "T1":
        ph = J(job, SO, f"{stem}.T1.phone.mp4")
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-map", "0:v:0", "-an", "-vf", "scale=390:-2",
                 "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", ph])
        if r.returncode == 0:
            rec["phone"] = rel(job, ph)
        else:
            print(f"  note: the 390-px phone copy failed: {r.stderr.strip()[:120]}", file=sys.stderr)
    return rec


def upsert(P: dict, rec: dict) -> None:
    P["proofs"] = [p for p in P["proofs"] if p["file"] != rec["file"]] + [rec]


def cmd_proofs(job: str, cut: str = "", t2_source: str = "", phone: bool = False) -> int:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("error: ffmpeg/ffprobe not on PATH", file=sys.stderr)
        return 2
    P = load_proofs(job)
    made = []
    if cut:
        if not os.path.isfile(cut):
            print(f"error: no such file: {cut}", file=sys.stderr)
            return 2
        rec = make_proof(job, cut, "T2", "lock")
        upsert(P, rec)
        made.append(rec)
    else:
        src = t2_source or next(iter(t2_candidates(job)), "")
        if src and not os.path.isfile(src):
            print(f"error: no such file: {src}", file=sys.stderr)
            return 2
        if src:
            rec = make_proof(job, src, "T2", "export")
            upsert(P, rec)
            P["t2_source"] = rel(job, src)
            made.append(rec)
        else:
            print("  ⚠ no captionless source for T2 — render the picture alone from Resolve (render-mp4.py "
                  "PICTURE_ONLY = True, into 09-qa/soundoff/) or keep the captionless master in 10-export/ "
                  "(<slug>-v<N>-master.mp4), then run proofs again", file=sys.stderr)
        for r_ in renders(job):
            if src and os.path.abspath(r_) == os.path.abspath(src):
                continue
            rec = make_proof(job, r_, "T1", "export", phone)
            upsert(P, rec)
            made.append(rec)
    P["updated"] = now_iso()
    jsave(J(job, PROOFS), P)
    for m in made:
        print(f"  {m['test']} ({m['stage']}) {m['file']}  ← {m['source']}" + (f"  + {m['phone']}" if m.get("phone") else ""))
    print(f"wrote {PROOFS}: {len(made)} proof(s). Watch them muted, read the story map against them, and log the "
          f"verdicts (qa_log.py --gate soundoff). A re-render makes these stale.")
    return 0 if made else 1


def proof_entry(job: str, path: str) -> dict | None:
    """The proof by its path — absolute, relative to the job, or relative to where the command runs."""
    cands = [path] if os.path.isabs(path) else [J(job, path), os.path.abspath(path)]
    wants = {rel(job, c) for c in cands}
    return next((p for p in load_proofs(job)["proofs"] if p["file"] in wants), None)


def proof_state(job: str, e: dict) -> str | None:
    """None when the proof and its source are both the bytes they were; else why not."""
    pf, sf = J(job, e["file"]), J(job, e["source"])
    if not os.path.isfile(pf):
        return f"{e['file']} is gone"
    if sha256_file(pf) != e["sha256"]:
        return f"{e['file']} changed after it was made"
    if not os.path.isfile(sf):
        return f"its source {e['source']} is gone"
    if sha256_file(sf) != e["source_sha256"]:
        return f"its source {e['source']} was re-rendered after the proof was made"
    return None


# ── the log ────────────────────────────────────────────────────────────────────────────────────────────────
def load_log(job: str) -> list:
    p = J(job, LOG)
    out = []
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def script_echo(job: str, text: str) -> float:
    """Share of the text's 5-word runs found verbatim in the script — in its spoken lines read in order, or in the
    file as written."""
    w = words(text)
    grams = [" ".join(w[i:i + 5]) for i in range(len(w) - 4)]
    if not grams:
        return 0.0
    sp, beats = script_beats(job)
    spoken = " ".join(words(" ".join(l for b in beats for _, l in b.get("lines") or [])))
    whole = " ".join(words(open(sp, encoding="utf-8").read())) if sp else ""
    return sum(1 for g in grams if g in spoken or g in whole) / len(grams)


def parse_beats(spec: str) -> tuple:
    out, bad = [], []
    for part in [p.strip() for p in (spec or "").split(",") if p.strip()]:
        m = re.match(r"^([A-Za-z0-9_-]+)\s*@\s*([\d:.]+)$", part)
        t = parse_tc(m.group(2)) if m else None
        if not m or t is None:
            bad.append(part)
        else:
            out.append({"id": m.group(1).upper(), "t": t, "tc": m.group(2)})
    return out, bad


def inside(t: float, b: dict) -> bool:
    """m:ss is a whole second, so the cited second [t, t+1) must overlap the beat's window."""
    if b.get("t0") is None:
        return False
    return t <= float(b["t1"]) and t + 1.0 > float(b["t0"])


def validate_row(job: str, test: str, viewer: str, who: str, proof: str, retell: str | None, beats: str,
                 obs: str, verdict: str | None) -> tuple:
    """(error | None, record). The evidence rules for a sound-off row (qa_log.py --gate soundoff)."""
    test, viewer = (test or "").upper(), (viewer or "").lower()
    if test not in ("T1", "T2"):
        return "--test T1 (the muted feed, captions on) or T2 (the picture alone)", None
    if viewer not in ("producer", "cold", "client"):
        return "--viewer producer | cold (someone who has not read the script or the brief) | client", None
    if not proof:
        return "--proof <the proof file you watched> (soundoff.py proofs)", None
    e = proof_entry(job, proof)
    if not e:
        return f"{proof} is not a proof made by soundoff.py proofs — log against the proof, not the render", None
    if e["test"] != test:
        return f"{e['file']} is a {e['test']} proof, not {test}", None
    st = proof_state(job, e)
    if st:
        return f"stale proof: {st} — soundoff.py proofs again; a verdict about other bytes is not a verdict", None
    who = (who or "").strip()
    if viewer == "cold" and not who:
        return "--who: the cold viewer's name or initials (the retell and the PASS must be the same person)", None
    rec = {"at": now_iso(), "test": test, "viewer": viewer, "who": who, "proof": e["file"], "proof_sha256": e["sha256"],
           "stage": e["stage"], "source": e["source"], "source_sha256": e["source_sha256"]}
    rows = load_log(job)
    if retell is not None and (verdict or "RETELL").upper() == "RETELL":
        if viewer == "producer":
            return "a retell is the cold viewer's (or the client's) — the producer has read the script", None
        if not who:
            return "--who: whose words these are", None
        r = retell.strip()
        if len(r.split()) < RETELL_MIN_WORDS or INTENTION.match(r):
            return (f"the retell is the viewer's own account — what happened, why, and what to do next — in at least "
                    f"{RETELL_MIN_WORDS} words [assumed], written down before they see the beat list"), None
        echo = script_echo(job, r)
        if echo >= SCRIPT_ECHO:
            return (f"{echo:.0%} of that retell is the script word for word — it was read, not watched. Write down "
                    f"what the viewer said"), None
        rec.update({"verdict": "RETELL", "retell": r})
        return None, rec
    v = (verdict or "").upper()
    if v not in ("PASS", "RETAKE"):
        return "--verdict PASS | RETAKE (or --retell for the cold viewer's first, open answer)", None
    rec.update({"verdict": v, "obs": (obs or "").strip(), "beats": []})
    if v == "RETAKE":
        cited, bad = parse_beats(beats)
        rec["beats"] = [f"{c['id']}@{c['tc']}" for c in cited]
        return None, rec
    M = load_map(job)
    if not M:
        return "no story map — soundoff.py map init <job> and read each beat before a PASS", None
    cited, bad = parse_beats(beats)
    if bad or not cited:
        return ("--beats \"HOOK@0:02,S2@0:11,CTA@0:24\": the beats the picture got across, each with the m:ss where "
                f"it did (unreadable: {', '.join(bad) or 'none given'})"), None
    ids = {b["id"]: b for b in M["beats"]}
    unknown = [c["id"] for c in cited if c["id"] not in ids]
    if unknown:
        return f"no beat {', '.join(unknown)} in the story map ({', '.join(ids)})", None
    out = [f"{c['id']}@{c['tc']} (its window {fmt_win(ids[c['id']])})" for c in cited if not inside(c["t"], ids[c["id"]])]
    if out:
        return "a timecode outside its beat's window on this cut: " + "; ".join(out), None
    distinct = {c["id"] for c in cited}
    need = min(MIN_BEATS, len(ids))
    if len(distinct) < need:
        return (f"a PASS cites at least {need} different beats [assumed] (house rule K5) — "
                f"{len(distinct)} given"), None
    if len(ids) < MIN_BEATS and len({round(c['t']) for c in cited}) < 2:
        return "a film with fewer than three beats cites two distinct timecodes", None
    offer = "OFFER" if M.get("mode") == "narrow" else "CTA"
    if offer in ids and offer not in distinct and not ids[offer].get("waiver"):
        return f"the {offer} beat is not cited — the offer is the beat a muted viewer most often loses", None
    if test == "T2" and viewer == "cold":
        prior = [r for r in rows if r.get("verdict") == "RETELL" and r.get("test") == "T2"
                 and (r.get("who") or "").lower() == who.lower()]
        if not prior:
            return (f"{who}'s PASS needs {who}'s retell logged FIRST — the open question before the beat list "
                    f"(qa_log.py --gate soundoff --test T2 --viewer cold --who \"{who}\" --proof … --retell \"…\")"), None
    rec["beats"] = [f"{c['id']}@{c['tc']}" for c in cited]
    return None, rec


def append_log(job: str, rec: dict) -> None:
    p = J(job, LOG)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ── placement and waivers ──────────────────────────────────────────────────────────────────────────────────
def t1_strict(job: str) -> bool:
    d = jload(J(job, PLACEMENT)) or {}
    return not d.get("sound_on_only")


def waivers(job: str) -> list:
    return (jload(J(job, WAIVERS)) or {}).get("waivers") or []


def has_waiver(job: str, what: str) -> dict | None:
    return next((w for w in reversed(waivers(job)) if w.get("what") == what), None)


def cmd_placement(job: str, sound_on_only: bool, muted: bool, platforms: str, quote: str) -> int:
    if muted:
        jsave(J(job, PLACEMENT), {"sound_on_only": False, "at": now_iso()})
        print("placement: muted or unknown — T1 must PASS on every delivery file")
        return 0
    if not sound_on_only:
        print("error: --sound-on-only (with --platforms and --quote) or --muted", file=sys.stderr)
        return 2
    if not (platforms or "").strip():
        print("error: --platforms names the sound-on-only buy (e.g. \"TikTok, Reels\")", file=sys.stderr)
        return 2
    e = verify_quote(quote)
    if e:
        print("REFUSED: " + e, file=sys.stderr)
        return 1
    jsave(J(job, PLACEMENT), {"sound_on_only": True, "platforms": platforms.strip(), "quote": quote.strip(),
                              "at": now_iso()})
    print(f"placement: sound-on only ({platforms.strip()}) — T1 still runs and is logged on every file; a RETAKE "
          f"there is a note, not a refusal. T2 is unchanged: the client runs it whatever the plan (house rule K2)")
    return 0


def cmd_waive(job: str, what: str, sound_led: bool, reason: str, quote: str) -> int:
    if what not in ("T2", "cold-viewer"):
        print("error: --what T2 | cold-viewer", file=sys.stderr)
        return 2
    if what == "T2" and not sound_led:
        print("REFUSED: only a sound-led piece waives T2 — a music video, an ASMR piece, a film whose story IS the "
              "sound (--sound-led). A sound-on media plan does not: the client runs T2 whatever the plan "
              "(house rule K4)", file=sys.stderr)
        return 1
    if len((reason or "").split()) < 3:
        print("error: --reason in a sentence", file=sys.stderr)
        return 2
    e = verify_quote(quote)
    if e:
        print("REFUSED: " + e, file=sys.stderr)
        return 1
    d = jload(J(job, WAIVERS)) or {"waivers": []}
    d["waivers"].append({"what": what, "reason": reason.strip(), "quote": quote.strip(), "at": now_iso()})
    jsave(J(job, WAIVERS), d)
    print(f"waived: {what} — {reason.strip()} (printed at every export as a note)")
    return 0


# ── the on-screen numbers (B11) ────────────────────────────────────────────────────────────────────────────
def _cores(text: str) -> set:
    return {re.sub(r"\D", "", m.group(0)) for m in NUM.finditer(text or "") if re.sub(r"\D", "", m.group(0))}


def title_specs(job: str) -> list:
    out = []
    for p in sorted(glob.glob(J(job, "07-edit", "titles", "*.title.json"))):
        if re.search(r"\.opt\d+\.title\.json$", p):
            continue
        s = jload(p)
        if isinstance(s, dict):
            C = s.get("content") or {}
            txt = " ".join(str(x) for x in (C.get("lines") or []) + [C.get(k) for k in (
                "line", "title", "subtitle", "kicker", "label", "place", "time", "price", "was", "note", "url") if C.get(k)])
            out.append({"id": s.get("id"), "kind": str(s.get("kind") or ""), "at_s": s.get("at_s"),
                        "duration_s": s.get("duration_s"), "text": txt})
    return out


def srt_text(job: str) -> str:
    out = []
    for p in sorted(glob.glob(J(job, "08-captions", "*.srt"))):
        for line in open(p, encoding="utf-8", errors="replace"):
            if "-->" in line or re.match(r"^\s*\d+\s*$", line):
                continue
            out.append(line.strip())
    return " ".join(out)


def claims(job: str) -> tuple:
    """(t1_holes, t2_holes, notes). A number or price the voiceover says must be on screen for a muted viewer
    (T1: in the captions or a title); for the picture alone (T2) only a title or the end card carries it."""
    _, beats = script_beats(job)
    if not beats:
        return [], [], ["no approved script — the on-screen numbers were not checked"]
    caps, T = _cores(srt_text(job)), title_specs(job)
    tit = set().union(*[_cores(t["text"]) for t in T]) if T else set()
    t1, t2, notes = [], [], []
    for b in beats:
        for spk, line in b.get("lines") or []:
            for m in NUM.finditer(line):
                core = re.sub(r"\D", "", m.group(0))
                if not core:
                    continue
                tok = m.group(0).strip()
                if core not in caps and core not in tit:
                    t1.append(f"{b['label']}: \"{tok}\" is only heard — no caption or title shows it")
                elif core not in tit:
                    t2.append(f"{b['label']}: \"{tok}\" lives in the voiceover and its captions — no title shows it")
            if re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|hundred|"
                         r"percent|half)\b", line, re.I):
                notes.append(f"{b['label']}: a number written in words is not checked (\"{line[:50]}\")")
    ends = [t for t in T if t["kind"].lower() in ENDCARD_KINDS]
    if any(b["kind"] == "cta" for b in beats) and not ends:
        t2.append("the offer has no end card — without sound, what does the viewer do next?")
    for t in ends:
        if t.get("duration_s") is not None and float(t["duration_s"]) < ENDCARD_MIN_S:
            notes.append(f"end card {t['id']} holds {float(t['duration_s']):.1f} s — under {ENDCARD_MIN_S:g} s [assumed]")
    return t1, t2, notes


# ── the strip (B3) ─────────────────────────────────────────────────────────────────────────────────────────
def cmd_strip(job: str, proof: str = "", width: int = 320) -> int:
    if not shutil.which("ffmpeg"):
        print("error: ffmpeg not on PATH", file=sys.stderr)
        return 2
    d = load_map(job)
    if not d:
        print("error: no story map — soundoff.py map init <job>", file=sys.stderr)
        return 1
    P = load_proofs(job)["proofs"]
    if proof:
        src = proof if os.path.isabs(proof) else J(job, proof)
    else:
        cands = [p for p in P if p["test"] == "T2" and p["stage"] == "export"] or [p for p in P if p["test"] == "T2"]
        if not cands:
            print("error: no T2 proof — soundoff.py proofs <job> (or --cut <file> before lock)", file=sys.stderr)
            return 1
        src = J(job, cands[-1]["file"])
    dur = probe(src).get("duration") or 0.0
    if d.get("mode") == "narrow":
        n = 8
        pts = [(i + 1, "", dur * (i + 0.5) / n, "") for i in range(n)]
    else:
        pts = [(b["n"], b["id"], (b["t0"] + b["t1"]) / 2.0, b.get("shows") or "") for b in d["beats"] if b.get("t0") is not None]
    if not pts:
        print("error: no beat has a window on the cut", file=sys.stderr)
        return 1
    outs = {}
    for kind in ("viewer", "producer"):
        tmp = tempfile.mkdtemp(prefix="soundoff_")
        for i, (n, bid, t, shows) in enumerate(pts):
            out = os.path.join(tmp, f"{i:04d}.png")
            lab = f"{n}" if kind == "viewer" else f"{n} {bid} {tc_of(t)}".strip()
            lab = re.sub(r"[^A-Za-z0-9 .:_-]", "", lab)
            ss = f"{min(t, max(0.0, dur - 0.1)):.2f}"
            r = run(["ffmpeg", "-y", "-loglevel", "error", "-ss", ss, "-i", src, "-frames:v", "1", "-vf",
                     f"scale={width}:-2,drawtext=text='{lab}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6",
                     out])
            if r.returncode != 0 or not os.path.exists(out):
                r = run(["ffmpeg", "-y", "-loglevel", "error", "-ss", ss, "-i", src, "-frames:v", "1", "-vf",
                         f"scale={width}:-2", out])
                if r.returncode != 0:
                    print(f"error: frame extract failed at {t:.2f} s: {r.stderr.strip()[:120]}", file=sys.stderr)
                    return 2
        cols = min(6, len(pts))
        rows = -(-len(pts) // cols)
        dest = J(job, SO, f"STRIP-{kind}.png")
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", os.path.join(tmp, "%04d.png"),
                 "-filter_complex", f"tile={cols}x{rows}:padding=4:color=0x202020", "-frames:v", "1", dest])
        shutil.rmtree(tmp, ignore_errors=True)
        if r.returncode != 0:
            print(f"error: tiling failed: {r.stderr.strip()[:200]}", file=sys.stderr)
            return 2
        outs[kind] = dest
    print(f"wrote {rel(job, outs['viewer'])} (numbers only — the one a cold viewer may see after the retell) and "
          f"{rel(job, outs['producer'])}\n  {len(pts)} frame(s) from {rel(job, src)}. Read it before any draft is shown. "
          f"A still cannot carry a beat that lives in motion, so the strip is an aid, never the verdict.")
    return 0


# ── Resolve: the map as markers ────────────────────────────────────────────────────────────────────────────
def console_copy(job: str) -> str:
    d = load_map(job)
    if not d:
        raise SystemExit("error: no story map — soundoff.py map init <job>")
    T = timeline(job)
    fps = (T["fps"] if T else None) or d.get("fps") or 24.0
    mk, seen = [], set()
    for b in d["beats"]:
        if b.get("t0") is None:
            continue
        fr = int(round(float(b["t0"]) * fps))
        while fr in seen:
            fr += 1
        seen.add(fr)
        state = "waived" if b.get("waiver") else (b.get("carries") or "")
        note = (b.get("shows") or "not read yet") + (f" · fix: {b['fix']}" if b.get("fix") else "")
        mk.append((fr, COLORS[state], f"Sound-off {b['n']} {b['id']} — {state or '?'}", note[:240],
                   max(1, int(round((float(b["t1"]) - float(b["t0"])) * fps))),
                   json.dumps({"soundoff_beat": b["id"], "carries": state})))
    src = open(CONSOLE, encoding="utf-8").read()
    for old, new in (("MARKERS = []  # __DETECT_BEATS_MARKERS__", "MARKERS = " + repr(mk) + "  # __DETECT_BEATS_MARKERS__"),
                     ("\nADD_BEAT_MARKERS = True", "\nADD_BEAT_MARKERS = True"),
                     ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False"),
                     ("\nENSURE_AUDIO_LANES = True", "\nENSURE_AUDIO_LANES = False")):
        if old not in src:
            raise RuntimeError(f"resolve-production-console.py no longer contains {old!r} — update soundoff.console_copy()")
        src = src.replace(old, new, 1)
    src = src.replace('"""\nDaVinci Resolve — the ONE production/editing-setup console script',
                      f'"""\nFilled in by soundoff.py console ({now_iso()}): the story map as one duration marker per beat '
                      f'(Green Y, Yellow partial, Red N, Cream waived, Blue unread). Nothing else is changed.\n\n'
                      f'DaVinci Resolve — the ONE production/editing-setup console script', 1)
    out = J(job, "07-edit", CONSOLE_COPY)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(src)
    return out


# ── the checks ─────────────────────────────────────────────────────────────────────────────────────────────
def lock_check(job: str) -> tuple:
    """`approve lock`: advisory (house rule K1) — except a beat the picture does not carry, unfixed and unwaived."""
    P, W = map_problems(job, "lock")
    if not any(r.get("test") == "T2" for r in load_log(job)):
        W.append("no T2 read of the cut yet — soundoff.py proofs <job> --cut <the locked cut>, watch it muted, map set "
                 "each beat (a story fix is cheapest now)")
    return P, W


def latest(rows: list, **match) -> dict | None:
    hit = [r for r in rows if all(r.get(k) == v for k, v in match.items()) and r.get("verdict") in ("PASS", "RETAKE")]
    return hit[-1] if hit else None


def check_job(job: str) -> tuple:
    """(problems, notes) for `approve export`. Rules refuse; the rest prints."""
    P, W = [], []
    if not renders(job):
        return P, W                        # nothing to export yet: the export gate's own check says so
    PR = load_proofs(job)
    rows = load_log(job)
    strict = t1_strict(job)
    t2w = has_waiver(job, "T2")
    # T2 — the picture alone
    if t2w:
        W.append(f"T2 waived (sound-led): {t2w['reason']}")
    else:
        t2 = [p for p in PR["proofs"] if p["test"] == "T2" and p["stage"] == "export"]
        e = t2[-1] if t2 else None
        st = proof_state(job, e) if e else "there is none"
        if st:
            P.append(f"T2: no current proof of the picture alone ({st}) — soundoff.py proofs <job>")
        else:
            r = latest(rows, test="T2", proof_sha256=e["sha256"], source_sha256=e["source_sha256"])
            cw = has_waiver(job, "cold-viewer")
            if not r:
                P.append(f"T2: no verdict on {e['file']} — a cold viewer watches it muted, the retell first, then the "
                         f"beats (qa_log.py --gate soundoff --test T2)")
            elif r["verdict"] != "PASS":
                P.append(f"T2: the last verdict on {e['file']} is RETAKE — {r.get('obs')}")
            elif r.get("viewer") != "cold" and not cw:
                P.append(f"T2: the PASS on {e['file']} is the {r.get('viewer')}'s — T2 needs someone who has not read the "
                         f"script (house rule K3). With nobody available, the fallback is the owner's: soundoff.py "
                         f"waive <job> --what cold-viewer --reason … --quote \"<their words>\"")
            elif r.get("viewer") != "cold":
                W.append(f"T2 passed by the {r.get('viewer')} alone — the cold viewer was waived: {cw['reason']}")
        mp, mw = map_problems(job, "export")
        P += ["story map: " + x for x in mp]
        W += ["story map: " + x for x in mw]
    # T1 — the muted feed, one per delivery file
    src = PR.get("t2_source")
    for r_ in renders(job):
        rr = rel(job, r_)
        if rr == src:
            continue
        ps = [p for p in PR["proofs"] if p["test"] == "T1" and p["source"] == rr]
        e = ps[-1] if ps else None
        st = proof_state(job, e) if e else "there is none"
        if st:
            P.append(f"T1: {rr} has no current muted proof ({st}) — soundoff.py proofs <job>")
            continue
        r = latest(rows, test="T1", proof_sha256=e["sha256"], source_sha256=e["source_sha256"])
        if not r:
            P.append(f"T1: no verdict on {e['file']} — watch it at volume 0, as shipped (qa_log.py --gate soundoff "
                     f"--test T1)")
        elif r["verdict"] != "PASS":
            (P if strict else W).append(f"T1: {e['file']} RETAKE — {r.get('obs')}"
                                        + ("" if strict else " (sound-on-only plan: advisory)"))
    if not strict:
        W.append("T1 is advisory: the job records a sound-on-only media plan")
    # captions measured (B10)
    import srt_qa
    sp_, sw_ = srt_qa.check_job(job)
    P += sp_
    W += sw_
    # the on-screen numbers (B11)
    t1h, t2h, notes = claims(job)
    P += [f"T1: {x}" for x in t1h] if strict else []
    W += [f"T1: {x}" for x in t1h] if not strict else []
    W += [f"T2: {x}" for x in t2h] + notes
    if not P:
        W.append("next: soundoff.py pack <job> — the proofs, the volume-0 instruction and the appendix, for the client")
    return P, W


# ── the hand-over (B12) ────────────────────────────────────────────────────────────────────────────────────
def _place(src: str, dst: str) -> None:
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def cmd_pack(job: str, draft: bool = False) -> int:
    P, W = check_job(job)
    if P and not draft:
        print("REFUSED: the sound-off evidence is not complete (soundoff.py check):\n  - " + "\n  - ".join(P) +
              "\n  (--draft packs what exists, marked DRAFT)", file=sys.stderr)
        return 1
    out = J(job, PACK)
    os.makedirs(out, exist_ok=True)
    PR = load_proofs(job)["proofs"]
    files, n = [], 1
    t2 = [p for p in PR if p["test"] == "T2" and p["stage"] == "export"]
    for p in t2[-1:]:
        dst = os.path.join(out, f"{n}-picture-only{os.path.splitext(p['file'])[1]}")
        _place(J(job, p["file"]), dst)
        files.append(dst)
        n += 1
    for p in [p for p in PR if p["test"] == "T1"]:
        stem = os.path.splitext(os.path.basename(p["source"]))[0]
        dst = os.path.join(out, f"{n}-muted-{stem}{os.path.splitext(p['file'])[1]}")
        _place(J(job, p["file"]), dst)
        files.append(dst)
        n += 1
    name = os.path.basename(os.path.abspath(job))
    readme = os.path.join(out, "README.md")
    open(readme, "w", encoding="utf-8").write(
        f"# {name} — the sound-off check{' (DRAFT)' if P else ''}\n\n"
        "Watch these before you read anything else, with the sound at zero.\n\n"
        "1. **The picture alone** (`1-picture-only`): no sound, no voiceover and no captions — only the picture and "
        "the designed titles. Does it tell the story? Who is it for, what happens, what do you do next?\n"
        "2. **The muted feed** (the `muted-` files): each delivery file as it ships, captions on, sound off — the "
        "way a scroller with the phone on silent sees it.\n\n"
        "Then open `APPENDIX.md`: how we checked it, what a viewer who had not read the script told us, and what "
        "we changed.\n")
    rows = load_log(job)
    d = load_map(job) or {"beats": []}
    A = [f"# Appendix — read after watching", "", "## The story map", "",
         "| # | beat | window | the picture shows | carries |", "|---|---|---|---|---|"]
    for b in d["beats"]:
        A.append(f"| {b['n']} | {b['id']} | {fmt_win(b)} | {b.get('shows') or '—'} | "
                 f"{'waived' if b.get('waiver') else (b.get('carries') or '—')} |")
    rt = [r for r in rows if r.get("verdict") == "RETELL"]
    A += ["", "## What a cold viewer said (before seeing the beat list)", ""]
    A += [f"> {r['retell']}\n>\n> — {r.get('who')}, {r['at'][:10]}" for r in rt] or ["(no cold viewer recorded)"]
    fixed = [b for b in d["beats"] if b.get("fix")]
    A += ["", "## What we changed", ""] + ([f"- {b['id']}: {b['fix']}" for b in fixed] or ["- nothing needed changing"])
    A += ["", "## The verdicts", ""] + [f"- {r['test']} · {r['verdict']} · {r.get('viewer')} · {r['at'][:16]} · "
                                       f"{', '.join(r.get('beats') or [])}" for r in rows if r.get("verdict") in ("PASS", "RETAKE")]
    for w in waivers(job):
        A.append(f"- waived {w['what']}: {w['reason']}")
    app = os.path.join(out, "APPENDIX.md")
    open(app, "w", encoding="utf-8").write("\n".join(A) + "\n")
    strip = J(job, SO, "STRIP-producer.png")
    if os.path.isfile(strip):
        _place(strip, os.path.join(out, "APPENDIX-strip.png"))
        files.append(os.path.join(out, "APPENDIX-strip.png"))
    files += [readme, app]
    man = {"made": now_iso(), "draft": bool(P), "files": [{"file": os.path.basename(f), "sha256": sha256_file(f)}
                                                         for f in files]}
    jsave(os.path.join(out, "MANIFEST.json"), man)
    print(f"wrote {rel(job, out)}/: {len(files)} file(s) and MANIFEST.json. Upload it beside the final (Frame.io or "
          f"Replay version stack, references/review-and-approval.md) with the proofs FIRST — the appendix is read after.")
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["proofs", "map", "strip", "placement", "waive", "claims", "console",
                                               "pack", "check", "lock-check"])
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--cut", default="")
    ap.add_argument("--t2-source", default="")
    ap.add_argument("--phone", action="store_true")
    ap.add_argument("--windows", default="")
    ap.add_argument("--narrow", action="store_true")
    ap.add_argument("--why", default="")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--beat", default="")
    ap.add_argument("--shows", default="")
    ap.add_argument("--carries", default="")
    ap.add_argument("--fix", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--quote", default="")
    ap.add_argument("--proof", default="")
    ap.add_argument("--sound-on-only", action="store_true")
    ap.add_argument("--muted", action="store_true")
    ap.add_argument("--platforms", default="")
    ap.add_argument("--what", default="")
    ap.add_argument("--sound-led", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help()
        return 2
    if a.cmd == "map":
        if len(a.rest) < 2:
            print("usage: soundoff.py map init|set|waive|show <job> …", file=sys.stderr)
            return 2
        sub, job = a.rest[0], a.rest[1]
        if sub == "init":
            d, moved = map_init(job, a.narrow, a.why, a.windows, a.duration)
            print(f"wrote {MAP} and {MAP_MD}: {len(d['beats'])} beat(s), windows from {d['windows']}")
            for m in moved:
                print(f"  moved: {m}")
            print("  next: watch the muted proof and `map set` each beat — what the PICTURE shows, Y / partial / N")
            return 0
        if sub == "set":
            b = map_set(job, a.beat, a.shows, a.carries, a.fix)
            print(f"  {b['id']}: {b['carries']} — {b['shows']}")
            return 0
        if sub == "waive":
            b = map_waive(job, a.beat, a.reason, a.quote)
            print(f"  {b['id']}: waived — {b['waiver']['reason']}")
            return 0
        if sub == "show":
            d = load_map(job)
            if not d:
                print("no story map — soundoff.py map init <job>", file=sys.stderr)
                return 1
            print(open(write_map_md(job, d), encoding="utf-8").read())
            return 0
        print("usage: soundoff.py map init|set|waive|show <job>", file=sys.stderr)
        return 2
    if not a.rest:
        print(f"usage: soundoff.py {a.cmd} <job>", file=sys.stderr)
        return 2
    job = a.rest[0]
    if a.cmd == "proofs":
        return cmd_proofs(job, a.cut, a.t2_source, a.phone)
    if a.cmd == "strip":
        return cmd_strip(job, a.proof)
    if a.cmd == "placement":
        return cmd_placement(job, a.sound_on_only, a.muted, a.platforms, a.quote)
    if a.cmd == "waive":
        return cmd_waive(job, a.what, a.sound_led, a.reason, a.quote)
    if a.cmd == "claims":
        t1, t2, notes = claims(job)
        for x in t1:
            print(f"  T1 ✗ {x}")
        for x in t2:
            print(f"  T2 · {x}")
        for x in notes:
            print(f"  note: {x}")
        print(f"{len(t1)} number(s) only heard · {len(t2)} carried by the captions alone")
        return 1 if t1 else 0
    if a.cmd == "console":
        print(f"wrote {console_copy(job)} — run it through the Resolve MCP or paste it into the console")
        return 0
    if a.cmd == "pack":
        return cmd_pack(job, a.draft)
    if a.cmd in ("check", "lock-check"):
        P, W = (check_job if a.cmd == "check" else lock_check)(job)
        for w in W:
            print(f"  note: {w}")
        for p in P:
            print(f"  ✗ {p}")
        print("sound-off: " + ("cleared" if not P else f"{len(P)} problem(s)"))
        return 1 if P else 0
    return 2


# ── selftest ───────────────────────────────────────────────────────────────────────────────────────────────
SCRIPT_FIXTURE = """# SCRIPT v2 — fixture

[HOOK 0:00–0:03]  the bench before dawn
HOST: „Every loaf here is shaped before six."

[SCENE 1 — the bench]  ESTABLISH — the bakery at 5 a.m.
HOST: „Thirty years of the same starter."

[SCENE 2 — the counter]  TURN — the door opens
HOST: „30% off your first box, $49 a month."

[CTA 0:09–0:12]  the box on the doorstep
HOST: „Order before Friday."
"""


def _selftest_quote_job() -> None:
    """(3.1.1) verify_quote passes the open job to gate.quote_refusal: on a hookless home, an unchecked quote is refused
    on a job whose transcript-checked approvals another home recorded, and accepted on a job with none."""
    import tempfile as _tq
    import gate as G
    keep = {k: getattr(G, k) for k in ("active_job", "hookless", "quote_in_transcript")}
    with _tq.TemporaryDirectory() as gd:
        class _J:
            gate_dir = gd
            rows: list = []

            def approvals(self):
                return self.rows
        j = _J()
        try:
            G.active_job = lambda *a_, **k_: (j, "")
            G.hookless = lambda: True
            G.quote_in_transcript = lambda q: "no-transcript"
            j.rows = [{"stage": "concept", "verified": "transcript"}]
            why = verify_quote("these words were never checked")
            assert why and "already has approvals checked" in why, ("another home's checked job refuses", why)
            j.rows = [{"stage": "concept", "verified": "UNVERIFIED hookless"}]
            assert verify_quote("these words were never checked") is None, "a hookless-only job still records"
        finally:
            for k, v in keep.items():
                setattr(G, k, v)


def selftest() -> int:
    _selftest_quote_job()
    import tempfile as _tfr
    os.environ.setdefault("CINE_TRANSCRIPT_ROOT", _tfr.gettempdir())   # (3.1) the tests' transcripts live in temp
    ok = True
    # the owner's-words check reads this session's transcript through gate.py; a selftest must not
    home = tempfile.mkdtemp(prefix="soundoff-home-")
    os.environ["CINE_HOME"] = home
    # (3.1) no transcript in this test, so its home is explicitly hookless (an unresolvable transcript refuses otherwise)
    open(os.path.join(home, "config.json"), "w").write('{"hookless": true}')
    if "gate" in sys.modules:
        sys.modules["gate"].TRANSCRIPT_FILE = os.path.join(home, "transcript-path")
        sys.modules["gate"].CINE_HOME = home

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  → {detail}"))

    # the lane files link the one definition (B1)
    lanes = ["modes/narrative-promo.md", "modes/ugc-volume.md", "modes/editorial-explainer.md", "modes/repurpose.md",
             "references/dr-advertorial.md", "references/micro-drama.md", "references/aerial-and-fpv.md"]
    missing = [f for f in lanes if REFERENCE.split("/")[-1] not in open(os.path.join(SKILL, f), encoding="utf-8").read()]
    check("every lane file links references/sound-off-story.md (one definition, B1)", not missing, missing)
    check("the shared definition exists", os.path.isfile(os.path.join(SKILL, REFERENCE)))
    # pure parts
    check("m:ss and m:ss.s parse; bare seconds do not", parse_tc("0:12") == 12 and parse_tc("1:02.5") == 62.5
          and parse_tc("12") is None)
    W_ = windows_from(["HOOK", "S1", "S2", "CTA"], [
        {"name": "HOOK_v1.mp4", "t0": 0, "t1": 3}, {"name": "S1-C1_host_v2.mp4", "t0": 3, "t1": 5},
        {"name": "stock-flour.mp4", "t0": 5, "t1": 6}, {"name": "S2B_insert.mp4", "t0": 6, "t1": 9},
        {"name": "CTA_card.mp4", "t0": 9, "t1": 12}])
    check("clip names carry the beat; an unnamed clip belongs to the beat before it",
          W_["S1"]["t0"] == 3 and W_["S1"]["t1"] == 6 and W_["S2"]["t0"] == 6 and W_["CTA"]["t1"] == 12, W_)
    check("a cited second overlaps the window (m:ss truncates)", inside(5.0, {"t0": 5.4, "t1": 7}) and
          not inside(8.0, {"t0": 5.4, "t1": 7}))
    if not shutil.which("ffmpeg"):
        print("selftest OK (pure parts only — ffmpeg not on PATH)" if ok else "selftest FAILED")
        return 0 if ok else 1
    import srt_qa
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("01-script", "07-edit/titles", "08-captions", "10-export", "09-qa"):
            os.makedirs(os.path.join(job, d))
        open(os.path.join(job, "01-script", "SCRIPT-bake-v2.md"), "w").write(SCRIPT_FIXTURE)
        json.dump({"fps": 24, "tracks": {"video1": [
            {"name": "HOOK_v1.mp4", "type": "Video", "start": 0, "duration": 72},
            {"name": "S1-C1_host_v1.mp4", "type": "Video", "start": 72, "duration": 72},
            {"name": "S2_host_v1.mp4", "type": "Video", "start": 144, "duration": 72},
            {"name": "CTA_card.mp4", "type": "Video", "start": 216, "duration": 72}]}},
            open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        for name in ("bake-v2-master.mp4", "bake-v2-final_9x16.mp4"):
            r = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=12:size=160x284:rate=24",
                     "-f", "lavfi", "-i", "sine=frequency=440:duration=12", "-shortest", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", os.path.join(job, "10-export", name)], 120)
            if r.returncode != 0:
                print("selftest FAILED — ffmpeg could not make the fixture: " + r.stderr[:200])
                return 1
        open(os.path.join(job, "08-captions", "bake.srt"), "w").write(
            "1\n00:00:00,000 --> 00:00:02,900\nEvery loaf here is shaped before six.\n\n"
            "2\n00:00:03,000 --> 00:00:05,900\nThirty years of the same starter.\n\n"
            "3\n00:00:06,000 --> 00:00:08,900\n30% off your first box,\n$49 a month.\n\n"
            "4\n00:00:09,000 --> 00:00:11,900\nOrder before Friday.\n")
        json.dump({"id": "END", "kind": "end-card", "at_s": 9.0, "duration_s": 3.0,
                   "content": {"lines": ["Bread at the door"], "price": "$49 / month"}},
                  open(os.path.join(job, "07-edit", "titles", "END.title.json"), "w"))

        # the map
        d, _ = map_init(job)
        check("map init: four beats from the script, windows from the cut",
              [b["id"] for b in d["beats"]] == ["HOOK", "S1", "S2", "CTA"] and d["beats"][1]["t0"] == 3.0, d["beats"])
        try:
            map_set(job, "HOOK", "Every loaf here is shaped before six", "Y")
            check("map set: the beat's own voiceover is refused as what the picture shows", False)
        except SystemExit as e:
            check("map set: the beat's own voiceover is refused as what the picture shows", "voiceover" in str(e), e)
        for bid, shows in (("HOOK", "hands fold dough on a floured bench, the wall clock reads 5:40"),
                           ("S1", "an old jar of starter, a grey-haired baker tips it into the bowl"),
                           ("CTA", "a box on a doorstep, the end card with the price and the brand")):
            map_set(job, bid, shows, "Y")
        map_set(job, "S2", "the shop door opens onto the street, people queue at the counter", "N",
                fix="add the price card over the queue")
        P, W = lock_check(job)
        check("lock: an unfixed N blocks; nothing else does (K1)", len(P) == 1 and "S2" in P[0], (P, W))
        map_set(job, "S2", "the shop door opens, a price card reads 30% off over the queue", "partial",
                fix="price card added; the box itself is not seen")
        P, W = lock_check(job)
        check("lock: a partial beat is a note, not a refusal", not P and any("partly" in w for w in W), (P, W))
        d, moved = map_init(job)
        check("map init again keeps the notes", d["beats"][0]["carries"] == "Y" and not moved, d["beats"][0])

        # the proofs
        rc = cmd_proofs(job)
        PR = load_proofs(job)
        t2 = [p for p in PR["proofs"] if p["test"] == "T2"]
        t1 = [p for p in PR["proofs"] if p["test"] == "T1"]
        check("proofs: T2 from the captionless master, T1 from the final, none carrying audio",
              rc == 0 and len(t2) == 1 and t2[0]["source"].endswith("master.mp4") and len(t1) == 1
              and not probe(os.path.join(job, t2[0]["file"]))["audio"], PR)
        t2f, t1f = t2[0]["file"], t1[0]["file"]

        # the evidence rules
        e, _ = validate_row(job, "T2", "cold", "Ana", t2f, None, "HOOK@0:01,S1@0:04,CTA@0:10", "she got it all", "PASS")
        check("a cold PASS without the retell first is refused (funnel order)", e and "retell logged FIRST" in e, e)
        e, _ = validate_row(job, "T2", "cold", "Ana", t2f, "a bakery, bread", "", "", None)
        check("a retell under 15 words is refused", e and "15 words" in e, e)
        e, _ = validate_row(job, "T2", "cold", "Ana", t2f,
                            "Every loaf here is shaped before six. Thirty years of the same starter. 30% off your first "
                            "box, $49 a month.", "", "", None)
        check("a retell that is the script word for word is refused", e and "script word for word" in e, e)
        e, rec = validate_row(job, "T2", "cold", "Ana", t2f,
                              "It's a small bakery very early in the morning, an old man makes bread with a starter "
                              "and then there's a deal on a bread box delivered to your door", "", "", None)
        check("a real retell is accepted as RETELL", e is None and rec["verdict"] == "RETELL", e)
        r = run([sys.executable, os.path.join(HERE, "qa_log.py"), "--project", job, "--gate", "soundoff", "--test", "T2",
                 "--viewer", "cold", "--who", "Ana", "--proof", t2f, "--retell", rec["retell"]], 60)
        qlog = open(os.path.join(job, "09-qa", "QA-LOG.md"), encoding="utf-8").read() if r.returncode == 0 else ""
        check("qa_log.py --gate soundoff logs it: a QA-LOG row for people, a JSON line for the gate",
              r.returncode == 0 and "| soundoff | RETELL |" in qlog and len(load_log(job)) == 1, r.stderr)
        e, _ = validate_row(job, "T2", "cold", "Ana", t2f, None, "HOOK@0:01,S1@0:08,CTA@0:10", "she got it", "PASS")
        check("a timecode outside its beat's window is refused", e and "outside its beat's window" in e, e)
        e, _ = validate_row(job, "T2", "cold", "Ana", t2f, None, "HOOK@0:01,S1@0:04", "she got it", "PASS")
        check("two beats are not three (K5)", e and "at least 3" in e, e)
        e, _ = validate_row(job, "T2", "cold", "Ana", t2f, None, "HOOK@0:01,S1@0:04,S2@0:07", "she got it", "PASS")
        check("a PASS that leaves out the offer beat is refused", e and "CTA" in e, e)
        e, _ = validate_row(job, "T2", "cold", "Ana", t1f, None, "HOOK@0:01,S1@0:04,CTA@0:10", "she got it", "PASS")
        check("a T1 proof cannot carry a T2 verdict", e and "is a T1 proof" in e, e)
        e, rec = validate_row(job, "T2", "cold", "Ana", t2f, None, "HOOK@0:01,S1@0:04,CTA@0:10",
                              "named the 5:40 clock and the starter; read the price on the end card", "PASS")
        check("a cold PASS after the retell, three beats in their windows → logged", e is None and rec["verdict"] == "PASS", e)
        append_log(job, rec)

        P, W = check_job(job)
        check("export: T1 unread and the captions unmeasured → refused, naming both",
              any(x.startswith("T1: no verdict") for x in P) and any("srt_qa" in x for x in P), P)
        e, rec = validate_row(job, "T1", "producer", "", t1f, None, "HOOK@0:01,S1@0:04,CTA@0:10",
                              "captions readable over the bench; the price is in the caption at 0:07", "PASS")
        check("a producer T1 PASS → logged", e is None, e)
        append_log(job, rec)
        srt = os.path.join(job, "08-captions", "bake.srt")
        srt_qa.write_report(srt)
        P, W = check_job(job)
        check("export: everything read, the caption report clean → cleared, the T2-only numbers as notes",
              not P and any("T2:" in w and "30" in w for w in W), (P, W))

        # stale bytes
        with open(os.path.join(job, "10-export", "bake-v2-master.mp4"), "ab") as fh:
            fh.write(b"\x00re-rendered")
        P, W = check_job(job)
        check("export: a re-rendered master makes T2's proof — and its PASS — stale", any("re-rendered" in x for x in P), P)
        cmd_proofs(job)
        P, W = check_job(job)
        check("export: a new proof needs a new verdict (the old PASS is about other bytes)",
              any(x.startswith("T2: no verdict") for x in P), P)
        t2f = [p for p in load_proofs(job)["proofs"] if p["test"] == "T2"][-1]["file"]
        e, rec = validate_row(job, "T2", "cold", "Ana", t2f, None, "HOOK@0:01,S1@0:04,CTA@0:10",
                              "re-checked on the new render: clock, starter, end card", "PASS")
        check("the same cold viewer re-checks new bytes without a second retell (her first look was cold)", e is None, e)
        append_log(job, rec)
        P, _ = check_job(job)
        check("export: cleared again", not P, P)

        # T1 strictness by placement (K2)
        e, rec = validate_row(job, "T1", "producer", "", t1f, None, "", "the caption covers the price card at 0:07", "RETAKE")
        append_log(job, rec)
        P, W = check_job(job)
        check("T1 RETAKE with an unknown placement → refused", any("T1:" in x and "RETAKE" in x for x in P), P)
        cmd_placement(job, True, False, "TikTok, Reels", "the buy is TikTok and Reels only")
        P, W = check_job(job)
        check("…with a sound-on-only plan recorded → a note, not a refusal", not P and any("advisory" in w for w in W), (P, W))

        # waivers (K3, K4)
        rc = cmd_waive(job, "T2", False, "the media plan is sound on", "the buy is TikTok and Reels only")
        check("a sound-on plan cannot waive T2", rc == 1)
        rc = cmd_waive(job, "cold-viewer", False, "nobody outside the job is free today", "go ahead without a cold viewer")
        check("the cold-viewer waiver needs a reason and the owner's words → recorded", rc == 0 and has_waiver(job, "cold-viewer"))

        # the numbers
        t1h, t2h, notes = claims(job)
        check("claims: $49 is in a title, 30 only in the captions; nothing only heard",
              not t1h and any("30" in x for x in t2h) and not any("49" in x for x in t2h), (t1h, t2h))
        os.remove(srt)
        t1h, _, _ = claims(job)
        check("claims: with no captions, a spoken number is only heard (a T1 hole)", any("30" in x for x in t1h), t1h)

        # Resolve, the strip, the pack, the narrow map
        out = console_copy(job)
        src = open(out, encoding="utf-8").read()
        check("console copy: one marker per beat, coloured by what the picture carries",
              "Sound-off 3 S2 — partial" in src and "'Yellow'" in src and "ENSURE_AUDIO_LANES = False" in src)
        check("strip: a viewer copy with numbers only and a producer copy",
              cmd_strip(job) == 0 and os.path.isfile(os.path.join(job, SO, "STRIP-viewer.png")))
        rc = cmd_pack(job, draft=True)
        man = jload(os.path.join(job, PACK, "MANIFEST.json")) or {}
        names = [f["file"] for f in man.get("files", [])]
        check("pack: the picture-only proof first, the muted files, README and APPENDIX, hashed",
              rc == 0 and names and names[0].startswith("1-picture-only") and "APPENDIX.md" in names, names)
        app = open(os.path.join(job, PACK, "APPENDIX.md"), encoding="utf-8").read()
        check("pack: the appendix carries the cold viewer's own words", "old man makes bread" in app)
        try:
            map_init(job, narrow=True)
            check("narrow map without --why is refused", False)
        except SystemExit as e:
            check("narrow map without --why is refused", "--why" in str(e), e)
        d, _ = map_init(job, narrow=True, why="a talking-head testimonial whose story is the speech")
        check("narrow map: WHO, PRODUCT, PROOF, OFFER over the whole film",
              [b["id"] for b in d["beats"]] == ["WHO", "PRODUCT", "PROOF", "OFFER"] and d["beats"][3]["t1"] == 12.0, d)
    print("-" * 60)
    print("selftest OK — one definition linked from every lane; proofs from the real bytes, stale on a re-render; "
          "the retell before the beats, three beats in their windows and the offer; T1 by placement; waivers in the "
          "owner's words; the numbers on screen; markers, strip and pack" if ok else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
