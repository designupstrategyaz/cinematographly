#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""timeline_export.py — the cut plan as a timeline for DaVinci Resolve, Final Cut Pro and Premiere Pro. (3.0.0)

  timeline_export.py <job> [--fps 24000/1001] [--width W --height H | --format PRESET] [--out DIR]
  timeline_export.py --selftest

From `07-edit/CUTS.json` (cut_plan.py; refused while a shot is unresolved or the self-check fails) it writes two files:

  07-edit/<job>.fcpxml   FCPXML 1.10 — Final Cut Pro 10.6+/11 and DaVinci Resolve
  07-edit/<job>.xml      FCP 7 XML (xmeml v5) — Premiere Pro. EXPERIMENTAL: structurally tested, not imported here

What is in them: the picture on one track, hard cuts in shot order, each take's unused frames kept as handles (the
clip uses IN→OUT of the whole file), the shot's voice-over under it trimmed to the shot, and markers (the shot's name
and its cut-plan notes). What is not: music (Resolve rebuilds it in Fairlight from REBUILD.json; CUTS.md says where to
place the original by hand in Final Cut or Premiere), transitions, J/L audio edits, drop-frame timecode.

Every time is a whole number of frames at a rational rate (24000/1001, 24, 25, 30000/1001, 30, 60000/1001, 60),
written as frames × den/num seconds. Paths are absolute: relink when the project moves to another machine.
"""
from __future__ import annotations
import argparse, json, os, random, re, shutil, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from fractions import Fraction
from urllib.parse import quote, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cut_plan as CP  # noqa: E402

RATES = (Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001), Fraction(30),
         Fraction(60000, 1001), Fraction(60))


# ---------- time ----------

def ft(frames: int, R: Fraction) -> str:
    """FCPXML time for a whole number of frames: frames × den/num seconds, reduced."""
    if not isinstance(frames, int):
        raise ValueError(f"not a whole number of frames: {frames!r}")
    s = Fraction(frames) / R
    return f"{s.numerator}s" if s.denominator == 1 else f"{s.numerator}/{s.denominator}s"


def parse_ft(s: str) -> Fraction:
    m = re.fullmatch(r"(-?\d+)(?:/(\d+))?s", s or "")
    if not m:
        raise ValueError(f"not an FCPXML time: {s!r}")
    return Fraction(int(m.group(1)), int(m.group(2) or 1))


def to_frames_exact(seconds: Fraction, R: Fraction) -> int:
    """An edit point given in seconds → frames, refused (never rounded) when it is not a whole frame at the rate."""
    f = Fraction(seconds) * R
    if f.denominator != 1:
        raise ValueError(f"{seconds} s is not a whole frame at {CP.rate_str(R)} fps ({float(f):.4f} frames)")
    return int(f)


def audio_time(seconds: float) -> str:
    """An audio asset's own duration, by samples at 48 kHz: may be a fraction of a frame (only edit points must not)."""
    s = Fraction(round(seconds * 48000), 48000)
    return f"{s.numerator}s" if s.denominator == 1 else f"{s.numerator}/{s.denominator}s"


def xmeml_rate(R: Fraction) -> tuple[int, bool]:
    """(timebase, ntsc): TRUE only for the 1001 rates, on timebase 24/30/60; FALSE for the true rates."""
    if R.denominator == 1001:
        return R.numerator // 1000, True
    if R.denominator == 1:
        return R.numerator, False
    raise ValueError(f"no xmeml timebase for {R}")


def file_url(path: str, localhost: bool = False) -> str:
    return ("file://localhost" if localhost else "file://") + quote(os.path.abspath(path))


# ---------- the model ----------

def probe(path: str) -> dict:
    """{'seconds', 'video', 'audio_channels'} by ffprobe; empty dict when it cannot read the file."""
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path],
                           capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout or "{}")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}
    st = d.get("streams") or []
    aud = [s for s in st if s.get("codec_type") == "audio"]
    return {"seconds": float((d.get("format") or {}).get("duration") or 0),
            "video": any(s.get("codec_type") == "video" for s in st),
            "audio_channels": int(aud[0].get("channels") or 2) if aud else 0}


def build_model(job: str, cuts: dict, R: Fraction, width: int, height: int, prober=probe) -> dict:
    clips, pos = [], 0
    for r in cuts["shots"]:
        path = os.path.join(job, r["file"])
        info = prober(path)
        c = {"shot": r["shot"], "path": path, "asset_frames": r["asset_frames"], "in": r["in"], "out": r["out"],
             "offset": pos, "audio_channels": info.get("audio_channels", 0), "vo": None,
             "markers": [(0, r["shot"])] + [(0, f) for f in (r.get("findings") or [])]}
        vo = CP.voice_for(job, r["shot"])
        if vo:
            vi = prober(vo)
            if vi.get("seconds"):
                vf = CP.frames_floor(vi["seconds"], R)
                c["vo"] = {"path": vo, "seconds": vi["seconds"], "asset_frames": vf,
                           "frames": min(vf, r["out"] - r["in"]), "channels": vi.get("audio_channels") or 2}
        clips.append(c)
        pos += r["out"] - r["in"]
    return {"name": cuts.get("job") or os.path.basename(job), "rate": R, "width": width, "height": height,
            "clips": clips, "frames": pos}


# ---------- FCPXML 1.10 ----------

def x(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_fcpxml(m: dict) -> str:
    R = m["rate"]
    res = [f'    <format id="r1" frameDuration="{ft(1, R)}" width="{m["width"]}" height="{m["height"]}"/>']
    spine, n = [], 1
    for c in m["clips"]:
        n += 1
        aid = f"r{n}"
        ha = c["audio_channels"] > 0
        aattr = f' hasAudio="1" audioSources="1" audioChannels="{c["audio_channels"]}" audioRate="48000"' if ha else ' hasAudio="0"'
        res.append(f'    <asset id="{aid}" name="{x(c["shot"])}" start="0s" duration="{ft(c["asset_frames"], R)}" '
                   f'hasVideo="1" videoSources="1" format="r1"{aattr}>\n'
                   f'      <media-rep kind="original-media" src="{x(file_url(c["path"]))}"/>\n    </asset>')
        used = c["out"] - c["in"]
        body = []
        if c["vo"]:
            n += 1
            vid = f"r{n}"
            v = c["vo"]
            res.append(f'    <asset id="{vid}" name="{x(c["shot"])}-vo" start="0s" duration="{audio_time(v["seconds"])}" '
                       f'hasVideo="0" hasAudio="1" audioSources="1" audioChannels="{v["channels"]}" audioRate="48000">\n'
                       f'      <media-rep kind="original-media" src="{x(file_url(v["path"]))}"/>\n    </asset>')
            body.append(f'          <asset-clip ref="{vid}" lane="-1" offset="{ft(c["in"], R)}" name="{x(c["shot"])}-vo" '
                        f'start="0s" duration="{ft(v["frames"], R)}" audioRole="dialogue"/>')
        for rel, text in c["markers"]:
            body.append(f'          <marker start="{ft(c["in"] + rel, R)}" duration="{ft(1, R)}" value="{x(text[:200])}"/>')
        spine.append(f'        <asset-clip ref="{aid}" offset="{ft(c["offset"], R)}" name="{x(c["shot"])}" '
                     f'start="{ft(c["in"], R)}" duration="{ft(used, R)}" tcFormat="NDF">\n'
                     + "".join(b + "\n" for b in body) + '        </asset-clip>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10">\n  <resources>\n'
            + "\n".join(res) + '\n  </resources>\n  <library>\n'
            f'    <event name="{x(m["name"])}">\n      <project name="{x(m.get("project") or m["name"] + "-cut")}">\n'
            f'        <sequence format="r1" duration="{ft(m["frames"], R)}" tcStart="0s" tcFormat="NDF" '
            f'audioLayout="stereo" audioRate="48k">\n          <spine>\n'
            + "\n".join(spine) + '\n          </spine>\n        </sequence>\n      </project>\n    </event>\n'
            '  </library>\n</fcpxml>\n')


def check_fcpxml(text: str, R: Fraction) -> list:
    """Our own structural check: version, frameDuration, every edit point a whole frame, ranges inside assets, a gapless
    spine whose sum is the sequence. Shares our reading of the spec — Resolve's import and OTIO are the independent ones."""
    p = []
    root = ET.fromstring(text)
    if root.get("version") != "1.10":
        p.append(f"version {root.get('version')} (want 1.10)")
    fmt = root.find("resources/format")
    if fmt is None or parse_ft(fmt.get("frameDuration")) != 1 / R:
        p.append("frameDuration is not one frame at the rate")
    assets = {a.get("id"): a for a in root.iter("asset")}
    seq = root.find(".//sequence")
    pos = Fraction(0)
    whole = lambda t: (t * R).denominator == 1  # noqa: E731
    for c in seq.find("spine"):
        off, st, du = (parse_ft(c.get(k)) for k in ("offset", "start", "duration"))
        for k, t in (("offset", off), ("start", st), ("duration", du)):
            if not whole(t):
                p.append(f"{c.get('name')}: {k} {c.get(k)} is not a whole frame")
        if off != pos:
            p.append(f"{c.get('name')}: offset {c.get('offset')} leaves a gap or overlap")
        a = assets.get(c.get("ref"))
        if a is None or st + du > parse_ft(a.get("duration")):
            p.append(f"{c.get('name')}: start+duration runs past its asset")
        for v in c.findall("asset-clip"):
            vo, vd = parse_ft(v.get("offset")), parse_ft(v.get("duration"))
            if not (whole(vo) and whole(vd)) or vo < st or vo + vd > st + du:
                p.append(f"{c.get('name')}: the voice-over is not inside its shot")
        for mk in c.findall("marker"):
            if not whole(parse_ft(mk.get("start"))):
                p.append(f"{c.get('name')}: a marker is not on a whole frame")
        pos += du
    if parse_ft(seq.get("duration")) != pos:
        p.append(f"sequence duration {seq.get('duration')} ≠ the spine's sum")
    return p


# ---------- xmeml v5 (Premiere Pro; experimental) ----------

def write_xmeml(m: dict) -> str:
    R = m["rate"]
    tb, ntsc = xmeml_rate(R)
    rate = f"<rate><timebase>{tb}</timebase><ntsc>{'TRUE' if ntsc else 'FALSE'}</ntsc></rate>"
    vclips, a1, a2, files, n = [], [], [], {}, 0

    def file_el(path, frames, video, channels):
        if path in files:
            return f'<file id="{files[path]}"/>'
        files[path] = f"file-{len(files) + 1}"
        med = (f"<video><samplecharacteristics><width>{m['width']}</width><height>{m['height']}</height>"
               f"</samplecharacteristics></video>" if video else "")
        med += f"<audio><channelcount>{channels}</channelcount></audio>" if channels else ""
        return (f'<file id="{files[path]}"><name>{x(os.path.basename(path))}</name>'
                f'<pathurl>{x(file_url(path, localhost=True))}</pathurl>{rate}<duration>{frames}</duration>'
                f'<media>{med}</media></file>')
    for c in m["clips"]:
        n += 1
        used = c["out"] - c["in"]
        mk = "".join(f"<marker><comment></comment><name>{x(t[:200])}</name><in>{c['in'] + rel}</in><out>-1</out></marker>"
                     for rel, t in c["markers"])
        vclips.append(f'<clipitem id="clipitem-{n}"><name>{x(c["shot"])}</name><enabled>TRUE</enabled>'
                      f'<duration>{c["asset_frames"]}</duration>{rate}<start>{c["offset"]}</start>'
                      f'<end>{c["offset"] + used}</end><in>{c["in"]}</in><out>{c["out"]}</out>'
                      f'{file_el(c["path"], c["asset_frames"], True, c["audio_channels"])}{mk}</clipitem>')
        if c["vo"]:
            v = c["vo"]
            for k, track in ((1, a1), (2, a2)):
                if k > v["channels"]:
                    continue
                n += 1
                track.append(f'<clipitem id="clipitem-{n}"><name>{x(c["shot"])}-vo</name><enabled>TRUE</enabled>'
                             f'<duration>{v["asset_frames"]}</duration>{rate}<start>{c["offset"]}</start>'
                             f'<end>{c["offset"] + v["frames"]}</end><in>0</in><out>{v["frames"]}</out>'
                             f'{file_el(v["path"], v["asset_frames"], False, v["channels"])}'
                             f'<sourcetrack><mediatype>audio</mediatype><trackindex>{k}</trackindex></sourcetrack>'
                             f'</clipitem>')
    atracks = "".join(f"<track>{''.join(t)}</track>" for t in (a1, a2) if t)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="5">'
            f'<sequence id="sequence-1"><name>{x(m["name"])}-cut</name><duration>{m["frames"]}</duration>{rate}'
            f'<timecode>{rate}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>'
            f'<media><video><format><samplecharacteristics>{rate}<width>{m["width"]}</width><height>{m["height"]}'
            f'</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>'
            f'<track>{"".join(vclips)}</track></video><audio>{atracks}</audio></media></sequence></xmeml>\n')


def check_xmeml(text: str, R: Fraction) -> list:
    p = []
    root = ET.fromstring(text)
    tb, ntsc = xmeml_rate(R)
    if root.get("version") != "5":
        p.append("xmeml version is not 5")
    for rt in root.iter("rate"):
        if rt.findtext("timebase") != str(tb) or rt.findtext("ntsc") != ("TRUE" if ntsc else "FALSE"):
            p.append(f"a rate is not timebase {tb} / ntsc {'TRUE' if ntsc else 'FALSE'}"); break
    for f in root.iter("file"):
        u = f.findtext("pathurl")
        if u is not None and not u.startswith("file://localhost/"):
            p.append(f"pathurl {u!r} is not file://localhost/…")
    pos = 0
    vtrack = root.find("sequence/media/video/track")
    for c in vtrack.findall("clipitem"):
        s, e, i, o, d = (int(c.findtext(k)) for k in ("start", "end", "in", "out", "duration"))
        if s != pos:
            p.append(f"{c.findtext('name')}: start {s} leaves a gap or overlap")
        if not (0 <= i < o <= d) or e - s != o - i:       # <out> is exclusive: out − in = end − start
            p.append(f"{c.findtext('name')}: in/out/start/end disagree")
        pos = e
    if int(root.findtext("sequence/duration")) != pos:
        p.append("sequence duration ≠ the video track's end")
    return p


def xmllint(path: str) -> str | None:
    """None when well-formed (and DTD-valid when CINE_FCPXML_DTD names Apple's DTD), else the error. Skipped without xmllint."""
    if not shutil.which("xmllint"):
        return None
    args = ["xmllint", "--noout"]
    dtd = os.environ.get("CINE_FCPXML_DTD")
    if dtd and path.endswith(".fcpxml") and os.path.isfile(dtd):
        args += ["--dtdvalid", dtd]
    r = subprocess.run(args + [path], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stderr.strip() or "xmllint failed")[:300]


def export(job: str, R: Fraction, width: int, height: int, out_dir: str | None = None, prober=probe) -> tuple:
    try:
        cuts = json.load(open(os.path.join(job, "07-edit", "CUTS.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None, ["no 07-edit/CUTS.json — run `cut_plan.py plan <job>` first"]
    probs = CP.self_check(cuts)
    if probs:
        return None, probs
    if CP.parse_rate(cuts.get("rate")) != R:
        return None, [f"CUTS.json was planned at {cuts.get('rate')} fps, not {CP.rate_str(R)}: plan again at this rate"]
    if R not in RATES:
        return None, [f"{CP.rate_str(R)} is not a supported rate"]
    m = build_model(job, cuts, R, width, height, prober)
    out_dir = out_dir or os.path.join(job, "07-edit")
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, m["name"])
    written, problems = [], []
    for ext, w, chk in ((".fcpxml", write_fcpxml, check_fcpxml), (".xml", write_xmeml, check_xmeml)):
        text = w(m)
        problems += [f"{ext}: {q}" for q in chk(text, R)]
        open(stem + ext, "w", encoding="utf-8").write(text)
        lint = xmllint(stem + ext)
        if lint:
            problems.append(f"{ext}: {lint}")
        written.append(stem + ext)
    return written, problems


# ---------- tests ----------

def _model(R, clips, w=1080, h=1920):
    pos, out = 0, []
    for shot, asset, i, o, vo in clips:
        out.append({"shot": shot, "path": f"/tmp/My Jobs/Café/{shot} take.mp4", "asset_frames": asset, "in": i,
                    "out": o, "offset": pos, "audio_channels": 0, "markers": [(0, shot)],
                    "vo": ({"path": f"/tmp/My Jobs/Café/{shot}_vo.wav", "seconds": vo, "asset_frames": int(vo * R),
                            "frames": min(int(vo * R), o - i), "channels": 2} if vo else None)})
        pos += o - i
    return {"name": "acme-01001-x", "rate": R, "width": w, "height": h, "clips": out, "frames": pos}


def selftest() -> int:
    # golden vectors, by hand from N frames = N × den/num s
    assert ft(24, Fraction(24000, 1001)) == "1001/1000s" and ft(1, Fraction(24000, 1001)) == "1001/24000s"
    assert ft(1800, Fraction(30000, 1001)) == "3003/50s"          # 60.06 s
    assert ft(48, Fraction(24)) == "2s" and ft(1, Fraction(25)) == "1/25s" and ft(0, Fraction(25)) == "0s"
    assert ft(12, Fraction(24000, 1001)) == "1001/2000s"
    try:
        to_frames_exact(Fraction(1), Fraction(24000, 1001)); raise AssertionError("1 s is not whole at 23.976")
    except ValueError:
        pass
    assert to_frames_exact(Fraction(1001, 1000), Fraction(24000, 1001)) == 24
    try:
        ft(1.5, Fraction(24)); raise AssertionError("a fractional frame count is refused")
    except ValueError:
        pass
    assert audio_time(2.5) == "5/2s"                               # an asset may be a fraction of a frame
    assert xmeml_rate(Fraction(24000, 1001)) == (24, True) and xmeml_rate(Fraction(24)) == (24, False)
    assert xmeml_rate(Fraction(30000, 1001)) == (30, True) and xmeml_rate(Fraction(60000, 1001)) == (60, True)
    assert xmeml_rate(Fraction(25)) == (25, False)
    # a two-shot model at 23.976, the significant fields by hand
    R = Fraction(24000, 1001)
    m = _model(R, [("S1", 120, 12, 60, 3.0), ("S2", 100, 20, 68, None)])
    fx = write_fcpxml(m)
    assert not check_fcpxml(fx, R), check_fcpxml(fx, R)
    root = ET.fromstring(fx)
    sp = root.findall(".//spine/asset-clip")
    assert [(c.get("offset"), c.get("start"), c.get("duration")) for c in sp] == \
        [("0s", "1001/2000s", "1001/500s"), ("1001/500s", "1001/1200s", "1001/500s")], \
        [(c.get("offset"), c.get("start"), c.get("duration")) for c in sp]
    assert root.find(".//sequence").get("duration") == "1001/250s"          # 96 frames
    vo = sp[0].find("asset-clip")
    assert vo.get("offset") == "1001/2000s" and vo.get("duration") == "1001/500s", "VO trimmed to its 48-frame shot"
    assert "file:///tmp/My%20Jobs/Caf%C3%A9/S1%20take.mp4" in fx, "spaces and diacritics percent-encoded"
    xm = write_xmeml(m)
    assert not check_xmeml(xm, R), check_xmeml(xm, R)
    xr = ET.fromstring(xm)
    c1 = xr.find("sequence/media/video/track/clipitem")
    assert [c1.findtext(k) for k in ("start", "end", "in", "out")] == ["0", "48", "12", "60"]   # <out> exclusive
    assert xr.findtext("sequence/rate/ntsc") == "TRUE" and xr.findtext("sequence/rate/timebase") == "24"
    assert unquote(c1.find("file/pathurl").text) == "file://localhost/tmp/My Jobs/Café/S1 take.mp4"
    assert len(xr.findall("sequence/media/audio/track")) == 2, "stereo VO on two linked tracks"
    assert "TRUE" not in write_xmeml(_model(Fraction(24), [("S1", 120, 12, 60, None)])).split("<ntsc>")[1][:5], \
        "true 24 fps is ntsc FALSE"
    # the checkers catch what they are for (sabotage of the output)
    assert check_fcpxml(fx.replace('offset="1001/500s"', 'offset="1001/400s"', 1), R), "a gap"
    assert check_fcpxml(fx.replace('start="1001/2000s"', 'start="1/2s"', 1), R), "a non-whole frame"
    assert check_xmeml(xm.replace("<ntsc>TRUE</ntsc>", "<ntsc>FALSE</ntsc>", 1), R), "a wrong ntsc flag"
    assert check_xmeml(xm.replace("file://localhost/", "file:///", 1), R), "a pathurl without localhost"
    # properties: random timelines at every rate, both checkers clean, sums agree
    rnd = random.Random(7)
    try:
        import hypothesis  # noqa: F401  (optional; the seeded loop below runs either way)
    except ImportError:
        pass
    for _ in range(200):
        R = rnd.choice(RATES)
        clips = []
        for k in range(rnd.randint(1, 8)):
            asset = rnd.randint(10, 600)
            i = rnd.randint(0, asset - 2)
            o = rnd.randint(i + 1, asset)
            clips.append((f"S{k}", asset, i, o, rnd.choice([None, rnd.uniform(0.2, 9.0)])))
        mm = _model(R, clips)
        assert not check_fcpxml(write_fcpxml(mm), R), (R, clips)
        assert not check_xmeml(write_xmeml(mm), R), (R, clips)
        assert sum(o - i for _, _, i, o, _ in clips) == mm["frames"]
    # optional: OpenTimelineIO reads the files back (frame counts) — test-only, skipped when not installed
    try:
        import opentimelineio as otio  # noqa: F401
        otio_note = "OTIO present (read-back not wired for these adapters yet)"
    except ImportError:
        otio_note = "OTIO not installed (read-back skipped)"
    # the job: refused while unresolved; written and linted when resolved
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "acme-01001-x")
        md = os.path.join(job, "09-qa", "motion"); os.makedirs(md)
        os.makedirs(os.path.join(job, "03-clips"))
        for rep in (CP._rep("S1"), CP._rep("S2", dur=6.0, cut=1.0, onset=1.0, peak=3.0)):
            json.dump(rep, open(os.path.join(md, f"{rep['shot']}.motion.json"), "w"))
        R = Fraction(24)
        CP.write(job, CP.plan_job(job, R, ["S1", "S2"], tracker=lambda *a: None))
        os.makedirs(os.path.join(job, "05-voice")); open(os.path.join(job, "05-voice", "S1_vo.wav"), "w").close()
        fake = lambda p: ({"seconds": 9.0, "video": False, "audio_channels": 2} if p.endswith(".wav")  # noqa: E731
                          else {"seconds": 5.0, "video": True, "audio_channels": 0})
        w, p = export(job, R, 1080, 1920, prober=fake)
        assert w is None and any("unresolved" in q for q in p), p
        CP.write(job, CP.plan_job(job, R, ["S1"], tracker=lambda *a: None))
        w, p = export(job, R, 1080, 1920, prober=fake)
        assert w and not p and all(os.path.isfile(f) for f in w), p
        sp = ET.parse(w[0]).getroot().find(".//spine/asset-clip")
        assert sp.find("asset-clip").get("duration") == sp.get("duration"), "a 9 s VO is trimmed to its 2 s shot"
        w, p = export(job, Fraction(25), 1080, 1920, prober=fake)
        assert w is None and "planned at 24" in p[0], p
    print(f"selftest OK — frame-defined goldens at 23.976/29.97/24/25 (24 f = 1001/1000 s; 1800 f = 60.06 s); a "
          f"non-whole edit point refused, an audio asset may be fractional; ntsc TRUE only for the 1001 rates; FCPXML "
          f"1.10 and xmeml fields by hand (VO trimmed to its shot, <out> exclusive, paths with spaces and diacritics); "
          f"the checkers catch a gap, a non-whole frame, a wrong ntsc flag and a bad pathurl; 200 random timelines at "
          f"every rate check clean; the export refuses an unresolved plan and a rate it was not planned at; {otio_note}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="?"); ap.add_argument("--fps"); ap.add_argument("--format")
    ap.add_argument("--width", type=int); ap.add_argument("--height", type=int); ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.job:
        ap.print_help(); return 2
    job = os.path.abspath(a.job)
    preset = a.format
    if not preset:
        try:
            mm = re.search(r"^Format:\s*([A-Za-z0-9_-]+)", open(os.path.join(job, "00-brief", "CHECKPOINT.md"),
                                                                 encoding="utf-8").read(), re.M)
            preset = mm.group(1) if mm else None
        except OSError:
            preset = None
    w, h = a.width, a.height
    if preset and not (w and h):
        try:
            pr = json.load(open(os.path.join(os.path.dirname(HERE), "assets", "delivery-formats.json"),
                                encoding="utf-8"))["formats"][preset]
            w, h = w or pr["width"], h or pr["height"]
        except (OSError, ValueError, KeyError):
            pass
    R = CP.parse_rate(a.fps) if a.fps else (CP.format_rate(preset) if preset else None)
    if not (R and w and h):
        print("need a rate and a size: --fps and --width/--height, or --format PRESET (or the checkpoint's Format)",
              file=sys.stderr)
        return 2
    written, probs = export(job, R, w, h, a.out)
    if not written:
        print("REFUSED:\n  - " + "\n  - ".join(probs), file=sys.stderr); return 1
    for f in written:
        print(f"wrote {f}")
    if probs:
        print("CHECK FAILED:\n  - " + "\n  - ".join(probs), file=sys.stderr); return 1
    print("Final Cut Pro: File ▸ Import ▸ XML (the .fcpxml). DaVinci Resolve: File ▸ Import ▸ Timeline (the .fcpxml). "
          "Premiere Pro: File ▸ Import (the .xml; experimental). Relink if the media moved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
