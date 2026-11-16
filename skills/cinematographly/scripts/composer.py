#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""composer.py — the skill as lead composer (v2.40.0): the composer's paperwork, the client's owned motif, composed
layers over a library bed, a rules-first note engine, the generated-bed trial, and the checks. Everything it makes
lands in DaVinci Resolve's Fairlight page: 48 kHz/24-bit WAVs on named, coloured tracks, with markers.

The house choices: the skill drafts the motif and a person edits it; a tiered hit window; the client's consent
first, with a named vendor whitelist; −14 LUFS as the house level; AI vocals only case by case; and everything it
builds works in Resolve's Fairlight page.

The paperwork (package A)
  brief init|lint <job>      06-music/COMPOSER-BRIEF.json: media plan, references and why each is liked, the music's
                             role, VO density, lengths, the mnemonic, the revision cap, the deliverables, consent
  spot init|lint <job>       07-edit/music/SPOTTING.json: per cue the function, the target feeling, the temp and why
                             it was liked, withhold or release, the end-card mood — against the timeline's fps
  consent <job> --by --quote --scope generated,composed,ai_vocals [--date]
                             the client's written consent, recorded BEFORE any generated material enters a cut
The owned identity layer (package B)
  motif draft <home> --brand B --key K [--syllables "AC-ME"] [--feeling warm|bright|tense] [--n 3]
                             three motif drafts (3–6 notes, simple ratios, the rhythm from the brand name's
                             syllables) → <home>/MOTIF-DRAFTS.json and a .mid per draft. The skill drafts; the owner edits
  motif adopt <home> --draft N --edited <file.json|.mid> --by <name> [--statement "..."]
                             the owner's edited motif → <home>/MOTIF.json, with the diff against the draft kept as
                             evidence of their authorship; refused when nothing substantive changed; a melody check
                             against the owner's kit MIDI and every other client's motif
  layer <job> --motif <home>/MOTIF.json [--backend numpy|fluidsynth|sfizz]
                             accents on the hard hits and the mnemonic as the button, in the bed's CONFIRMED key, on
                             its bar grid, muted under speech → 06-music/compose/<job>.layer.wav + a stem per part,
                             .compose.json (provenance) and .licence.json (the audio manifest)
  family <job> [--lengths 30,15,6]
                             the length family from one idea: each length ends inside its slot on the mnemonic
  key confirm <job> --key "C#m" --by <name>   the owner's ear confirms the bed's key before any layer locks
The note engine (package C)
  solve <job> [--bpm 70-140] [--play-through H3]
                             a tempo map that puts every hard hit on a downbeat, one inserted 2/4 or 3/4 bar allowed
  plan template|lint <job>   07-edit/music/PLAN.json: sections, a Roman-numeral chord per bar, parts, motif — the
                             plan is written by the agent; code realises it
  realise <job>              the notes, voiced and checked: key, range, bar length, parallels, copy-paste repeats
  render <job> [--backend ...]   SCORE → a 48 kHz mix and a stem per part, timed
  gate-a <wav> --refs <dir>  the automatic outlier check against reference tracks (loudness, true peak, mono loss,
                             high-band flux, verbatim repeats)
The generated-bed trial (package D)
  generated record <job> --file F --vendor V --plan P --prompt "..." --terms-url U --terms-file T --use temp|ship
  vocals record <job> --file F --lyrics-file L --lyrics-by "..." --voice "..." --disclosure "..."
  bakeoff init <job> --library A --candidate B [--vo V] [--picture P] [--trials 30] --subject vendor:elevenlabs
  bakeoff record <dir> --listener N --role other|composer --picks "1:X,2:Y,…"   bakeoff result <dir>
Resolve and the checks
  elements <job>             09-qa/mix/ELEMENTS.md: every audio element as library, human, sample-rendered (route 1) or
                             AI-generated (route 2), and what each needs disclosed
  console <job>              07-edit/resolve-production-console.compose.py: the ORIGINAL track's segments on A5 (music_fit.py
                             rebuild — a Python render is a preview, never imported), the layer on A6,
                             stems on named, disabled tracks (switch them on in Fairlight), clip colours by origin,
                             spotting, hit and seam markers, the Fairlight preset if one is named. The alt mix and the
                             length family are previews too: not placed, rebuilt in Resolve
  check <job>                what `approve export` runs: rules refuse, measures warn
  --selftest

What it cannot do: hear. Whether the music serves the scene is the director's ear and the blind bake-off's job;
language models reason about harmony near chance (MusicTheoryBench), so the plan is checked by code, never trusted.
Resolve has no MIDI instruments: the .mid files are for a DAW; Fairlight gets rendered stems.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, math, os, random, re, shutil, struct, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import music_fit as MF  # noqa: E402  (stdlib-only at import; numpy is lazy there too)

SR = 48000
BRIEF = os.path.join("06-music", "COMPOSER-BRIEF.json")
SPOT = os.path.join("07-edit", "music", "SPOTTING.json")
COMPOSE_DIR = os.path.join("06-music", "compose")
FAMILY_DIR = os.path.join("06-music", "family")
GEN_DIR = os.path.join("06-music", "generated")
LAYER = os.path.join("07-edit", "music", "LAYER.json")
TEMPO = os.path.join("07-edit", "music", "TEMPO-MAP.json")
PLAN = os.path.join("07-edit", "music", "PLAN.json")
SCORE = os.path.join("07-edit", "music", "SCORE.json")
ELEMENTS = os.path.join("09-qa", "mix", "ELEMENTS.md")
ELEMENTS_JSON = os.path.join("09-qa", "mix", "ELEMENTS.json")
COMPOSE_COPY = "resolve-production-console.compose.py"
INSTRUMENTS = os.path.join(SKILL, "assets", "music-instruments.json")
GENERATORS = os.path.join(SKILL, "assets", "music-generators.json")
BAKEOFF_DAYS = 92                       # K7: a blind bake-off per route or vendor, re-run each quarter
HEADROOM_DB = -3.0                      # stems and mixes peak at −3 dBFS, no limiter (the delivery spec)
ROLES = ("hero", "texture")
VO_DENSITY = ("none", "light", "dense")
FUNCTIONS = ("establish", "build", "underscore", "hit", "transition", "release", "button", "silence")
WITHHOLD = ("withhold", "release", "hold")
SCOPES = ("generated", "composed", "ai_vocals")
FEELINGS = {"warm": ("major", "falling"), "bright": ("major", "rising"), "tense": ("minor", "rising"),
            "sad": ("minor", "falling"), "calm": ("major", "arch"), "bold": ("major", "arch"), "dark": ("minor", "arch")}
COLORS = {"library": "Blue", "composed": "Purple", "generated": "Orange", "alt": "Teal", "stem": "Navy"}


def _np():
    return MF._np()


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def jload(p: str, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def jdump(obj, p: str) -> str:
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return p


def cine_home() -> str:
    import cine_home as _ch  # noqa: E402  (3.0.0) the one home resolver
    return _ch.home(merge=False)


def parse_date(s) -> dt.datetime | None:
    if not s:
        return None
    s = str(s).strip().replace("Z", "")
    for f in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s[:len(dt.datetime.now().strftime(f))], f)
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return None


# ── theory ──────────────────────────────────────────────────────────────────────────────────────────────
PCS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B", "Fb": "E", "E#": "F", "B#": "C"}
MODES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
         "mixolydian": [0, 2, 4, 5, 7, 9, 10], "harmonic_minor": [0, 2, 3, 5, 7, 8, 11], "lydian": [0, 2, 4, 6, 7, 9, 11]}
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}


def parse_key(k: str) -> tuple[int, str]:
    """'C#m', 'F# minor', 'Bb', 'D dorian' → (tonic pitch class, mode)."""
    k = (k or "").strip()
    m = re.match(r"^([A-Ga-g])([#b]?)\s*(m(?:in(?:or)?)?|maj(?:or)?|dorian|mixolydian|lydian|harmonic[_ ]minor)?$", k.replace("-", " "))
    if not m:
        raise ValueError(f"key {k!r}: write it like C, F#m, Bb major or D dorian")
    name = m.group(1).upper() + (m.group(2) or "")
    name = FLAT.get(name, name)
    q = (m.group(3) or "").lower().replace(" ", "_")
    mode = "minor" if q in ("m", "min", "minor") else ("major" if q in ("", "maj", "major") else q)
    return PCS.index(name), mode


def key_name(tonic: int, mode: str) -> str:
    return PCS[tonic % 12] + ("m" if mode == "minor" else ("" if mode == "major" else " " + mode))


def scale_pcs(tonic: int, mode: str) -> set:
    return {(tonic + i) % 12 for i in MODES[mode]}


def degree_pitch(tonic: int, mode: str, degree: int, octave: int = 4) -> int:
    """Scale degree (1-based, may run past 7 or below 1) → MIDI note; octave 4 puts the tonic near middle C."""
    steps = MODES[mode]
    d = degree - 1
    o, i = divmod(d, 7)
    return 12 * (octave + 1 + o) + tonic + steps[i]


def parse_roman(sym: str, tonic: int, mode: str) -> dict:
    """A Roman numeral → its chord: root pitch class, chord pitch classes, and which are outside the key.
    Accepts I ii iii IV V vi vii°, bVII bVI bIII, 7 / maj7 / sus2 / sus4 / add9, V/V, and N.C. (no chord)."""
    s = (sym or "").strip()
    if s.upper() in ("N.C.", "NC", "-", "REST"):
        return {"symbol": s, "root": None, "pcs": [], "outside": []}
    m = re.match(r"^([b#]?)(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)(°|o|dim|ø|\+|aug)?(maj7|7|sus2|sus4|add9|6)?(?:/(V|IV|ii|vi))?$", s)
    if not m:
        raise ValueError(f"chord {sym!r}: a Roman numeral like I, vi, IV, V7, bVII, iiø is expected")
    acc, num, qual, ext, sec = m.groups()
    steps = MODES["major" if mode in ("major", "lydian", "mixolydian") else "minor"]
    base_tonic = tonic
    if sec:                                                  # V/V: the chord built on the degree of the secondary key
        base_tonic = (tonic + MODES["major"][ROMAN[sec.upper()] - 1]) % 12
        steps = MODES["major"]
    deg = ROMAN[num.upper()]
    root = (base_tonic + MODES["major"][deg - 1] + (-1 if acc == "b" else (1 if acc == "#" else 0))) % 12 if acc else \
        (base_tonic + steps[deg - 1]) % 12
    minor = num.islower()
    third = 3 if minor else 4
    fifth = 7
    if qual in ("°", "o", "dim", "ø"):
        third, fifth = 3, 6
    elif qual in ("+", "aug"):
        third, fifth = 4, 8
    ivs = [0, third, fifth]
    if qual == "ø" and ext != "7":                           # half-diminished: the minor seventh is implied
        ivs.append(10)
    if ext == "7":                                           # "7" is a minor seventh (V7, ii7, viiø7); "maj7" says so
        ivs.append(10)
    elif ext == "maj7":
        ivs.append(11)
    elif ext == "sus2":
        ivs[1] = 2
    elif ext == "sus4":
        ivs[1] = 5
    elif ext == "add9":
        ivs.append(14)
    elif ext == "6":
        ivs.append(9)
    pcs = [(root + i) % 12 for i in ivs]
    sc = scale_pcs(tonic, mode)
    return {"symbol": s, "root": root, "pcs": pcs, "outside": [p for p in pcs if p not in sc]}


def nearest_voicing(pcs: list, prev: list | None, lo: int = 52, hi: int = 76, voices: int = 4) -> list:
    """Close voicing of the chord's pitch classes inside [lo, hi], moving as little as possible from `prev`."""
    pcs = list(dict.fromkeys(pcs)) or [0]
    cands = []
    for base in range(lo, hi - 6):
        for rot in range(len(pcs)):
            order = pcs[rot:] + pcs[:rot]
            v, cur = [], base
            for pc in order:
                n = cur + ((pc - cur) % 12)
                v.append(n)
                cur = n + 1
            while len(v) < voices:
                v.append(v[len(v) - len(pcs)] + 12)
            v = v[:voices]
            if v[-1] <= hi and v[0] >= lo:
                cands.append(tuple(v))
    cands = sorted(set(cands))
    if not cands:
        return sorted(lo + ((p - lo) % 12) for p in pcs)[:voices]
    if not prev:
        mid = (lo + hi) / 2
        return list(min(cands, key=lambda v: abs(sum(v) / len(v) - mid)))
    return list(min(cands, key=lambda v: sum(abs(a - b) for a, b in zip(v, prev)) + 0.1 * abs(v[-1] - prev[-1])))


# ── MIDI (a small SMF writer and reader; no dependency) ──────────────────────────────────────────────────
GM = {"piano": 0, "bell": 14, "pluck": 46, "pad": 89, "sub": 38, "lead": 81, "arp": 46, "strings": 48, "guitar": 24}
DRUM_NOTES = {"kick": 36, "snare": 38, "hat": 42, "impact": 49, "tom": 45}


def _vlq(n: int) -> bytes:
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def write_midi(path: str, parts: dict, tempo_events: list, meter_events: list | None = None, tpq: int = 480) -> str:
    """parts: {name: [{"beat": b, "dur": d, "pitch": p, "vel": v}, ...]} in BEATS; tempo_events: [(beat, bpm)];
    meter_events: [(beat, num, den)]. Type-1 file, one track per part, drums on channel 10."""
    def trk(events):
        events = sorted(events, key=lambda e: (e[0], e[1]))
        data, last = bytearray(), 0
        for tick, _, msg in events:
            data += _vlq(max(0, tick - last)) + msg
            last = tick
        data += _vlq(0) + b"\xff\x2f\x00"
        return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)
    tracks = []
    ev = []
    for b, bpm in tempo_events:
        us = int(round(60_000_000 / float(bpm)))
        ev.append((int(round(b * tpq)), 0, b"\xff\x51\x03" + us.to_bytes(3, "big")))
    for b, num, den in meter_events or [(0, 4, 4)]:
        ev.append((int(round(b * tpq)), 0, b"\xff\x58\x04" + bytes([num, int(math.log2(den)), 24, 8])))
    tracks.append(trk(ev))
    ch_next = 0
    for name, notes in parts.items():
        drum = name in DRUM_NOTES or name in ("perc", "drums")
        ch = 9 if drum else ch_next
        if not drum:
            ch_next = ch_next + 1 if ch_next + 1 != 9 else 10
        ev = [(0, 0, b"\xff\x03" + _vlq(len(name.encode())) + name.encode())]
        if not drum:
            ev.append((0, 1, bytes([0xC0 | ch, GM.get(name.split("_")[0], 0)])))
        for n in notes:
            t0 = int(round(float(n["beat"]) * tpq))
            t1 = max(t0 + 1, int(round((float(n["beat"]) + float(n["dur"])) * tpq)))
            p, v = int(n["pitch"]) & 0x7F, max(1, min(127, int(n.get("vel", 90))))
            ev.append((t0, 3, bytes([0x90 | ch, p, v])))
            ev.append((t1, 2, bytes([0x80 | ch, p, 0])))
        tracks.append(trk(ev))
    head = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), tpq)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "wb").write(head + b"".join(tracks))
    return path


def read_midi_notes(path: str) -> list:
    """Every note in a MIDI file as {"beat", "dur", "pitch", "vel"} (beats from the file's ticks per quarter)."""
    b = open(path, "rb").read()
    if b[:4] != b"MThd":
        raise ValueError(f"{path}: not a MIDI file")
    _, ntr, tpq = struct.unpack(">HHH", b[8:14])
    i, notes = 14, []
    for _ in range(ntr):
        if b[i:i + 4] != b"MTrk":
            break
        ln = struct.unpack(">I", b[i + 4:i + 8])[0]
        j, end, tick, run, on = i + 8, i + 8 + ln, 0, 0, {}
        while j < end:
            d = 0
            while True:
                c = b[j]; j += 1
                d = (d << 7) | (c & 0x7F)
                if not c & 0x80:
                    break
            tick += d
            st = b[j]
            if st == 0xFF:
                ln2 = 0; j += 2
                while True:
                    c = b[j]; j += 1
                    ln2 = (ln2 << 7) | (c & 0x7F)
                    if not c & 0x80:
                        break
                j += ln2
                continue
            if st in (0xF0, 0xF7):
                ln2 = 0; j += 1
                while True:
                    c = b[j]; j += 1
                    ln2 = (ln2 << 7) | (c & 0x7F)
                    if not c & 0x80:
                        break
                j += ln2
                continue
            if st & 0x80:
                run = st; j += 1
            kind = run & 0xF0
            if kind in (0xC0, 0xD0):
                j += 1
                continue
            d1, d2 = b[j], b[j + 1]; j += 2
            if kind == 0x90 and d2 > 0:
                on[(run & 0x0F, d1)] = (tick, d2)
            elif kind in (0x80, 0x90):
                k = (run & 0x0F, d1)
                if k in on:
                    t0, v = on.pop(k)
                    notes.append({"beat": round(t0 / tpq, 4), "dur": round((tick - t0) / tpq, 4), "pitch": d1, "vel": v})
        i = end
    return sorted(notes, key=lambda n: (n["beat"], n["pitch"]))


# ── instruments, the palette and their licences ──────────────────────────────────────────────────────────
def instruments() -> dict:
    return jload(INSTRUMENTS, {}) or {}


def part_family(part: str) -> str:
    fam = (instruments().get("parts") or {})
    base = part.split("_")[0]
    return fam.get(part) or fam.get(base) or "unknown"


def palette_problems(parts, override: dict | None = None) -> list:
    """Route 1's palette (the research's quality ceiling): synth, piano, bell, percussion and ambient sound right
    from samples; exposed solo strings, winds, guitars, vocals and orchestral realism sound cheap. A blocked family
    needs the owner's override with a reason."""
    P = []
    pal = instruments().get("palette") or {}
    allowed, blocked = set(pal.get("allowed") or []), pal.get("blocked") or {}
    ok = set((override or {}).get("families") or []) if (override or {}).get("reason") else set()
    for p in parts:
        fam = part_family(p)
        if fam in blocked and fam not in ok:
            P.append(f"part {p!r} ({fam}): {blocked[fam]} — outside the palette (an owner override needs a reason)")
        elif fam not in allowed and fam not in blocked:
            P.append(f"part {p!r}: no family in assets/music-instruments.json — name it there first")
    return P


def instrument_licence(path_or_id: str) -> dict:
    """The registry row for an instrument file (SF2/SFZ/plugin) or the built-in synths. Unknown → paid_ads unknown."""
    for row in instruments().get("instruments") or []:
        if path_or_id == row.get("id") or (row.get("match") and re.search(row["match"], path_or_id or "", re.I)):
            return dict(row, file=path_or_id)
    return {"id": "unknown", "file": path_or_id, "licence": "", "paid_ads": "unknown",
            "why": "not in assets/music-instruments.json — read its licence and add a row before it renders client music"}


# ── the built-in synths (numpy): sketches and identity layers with no third-party samples ─────────────────
def _env(n: int, sr: int, a: float, d: float, sustain: float = 0.0, r: float = 0.05, hold_s: float | None = None):
    np = _np()
    t = np.arange(n) / sr
    e = np.minimum(1.0, t / max(a, 1e-4))
    dec = np.exp(-np.maximum(0.0, t - a) / max(d, 1e-4))
    e = e * (sustain + (1 - sustain) * dec)
    if hold_s is not None:
        rel = np.clip(1.0 - (t - hold_s) / max(r, 1e-4), 0.0, 1.0)
        e = e * np.where(t > hold_s, rel, 1.0)
    return e


def _hz(p: float) -> float:
    return 440.0 * 2 ** ((p - 69) / 12.0)


def synth_note(kind: str, pitch: int, dur: float, vel: int, sr: int = SR, seed: int = 0):
    """One note of a built-in instrument as a mono float array. Attacks are fast enough that the measured
    transient peak sits within 3 ms of the note's start (the hit record's onset definition)."""
    np = _np()
    rng = np.random.default_rng(seed + int(pitch) * 7919)
    f = _hz(pitch)
    amp = (max(1, min(127, vel)) / 127.0) ** 1.3
    tail = {"piano": 1.6, "bell": 2.2, "pluck": 0.6, "pad": 0.9, "sub": 0.25, "lead": 0.2, "arp": 0.5,
            "kick": 0.45, "snare": 0.25, "hat": 0.08, "impact": 1.6, "texture": 1.2}.get(kind, 0.4)
    n = int((dur + tail) * sr)
    t = np.arange(n) / sr
    if kind in ("piano",):
        y = sum((1 / k ** 1.4) * np.sin(2 * np.pi * f * k * (1 + 0.0004 * k * k) * t) * np.exp(-t * (1.2 + 0.7 * k))
                for k in range(1, 9))
        y = y * _env(n, sr, 0.002, 9.0, 1.0, 0.18, dur)
    elif kind == "bell":
        mod = np.sin(2 * np.pi * f * 3.5 * t) * (2.2 * np.exp(-t * 2.5))
        y = np.sin(2 * np.pi * f * t + mod) * _env(n, sr, 0.002, 1.1, 0.0)
    elif kind in ("pluck", "arp"):
        y = sum((1 / k) * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (3.0 + 2.2 * k)) for k in range(1, 10))
        y = y * _env(n, sr, 0.002, 0.5, 0.0, 0.08, dur)
    elif kind == "pad":
        y = 0
        for det in (-0.07, 0.0, 0.07):
            fd = f * 2 ** (det / 12)
            y = y + sum(((-1) ** (k + 1)) / k * np.sin(2 * np.pi * fd * k * t) * (0.85 ** k) for k in range(1, 12))
        y = y / 3 * _env(n, sr, 0.35, 99.0, 1.0, 0.6, dur)
    elif kind == "sub":
        y = (np.sin(2 * np.pi * f * t) + 0.15 * np.sin(4 * np.pi * f * t)) * _env(n, sr, 0.004, 99.0, 1.0, 0.08, dur)
    elif kind == "lead":
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1.0, t / 0.4)
        y = sum((1 / k) * np.sin(2 * np.pi * f * k * vib * t) for k in (1, 3, 5, 7, 9)) * _env(n, sr, 0.006, 99.0, 1.0, 0.12, dur)
    elif kind == "kick":
        fr = 45 + 75 * np.exp(-t * 28)
        ph = 2 * np.pi * np.cumsum(fr) / sr
        y = np.sin(ph) * np.exp(-t * 7.5) + 0.25 * rng.standard_normal(n) * np.exp(-t * 300)
    elif kind == "snare":
        noise = rng.standard_normal(n)
        noise = np.convolve(noise, np.ones(3) / 3, mode="same") - np.convolve(noise, np.ones(15) / 15, mode="same")
        y = 0.8 * noise * np.exp(-t * 16) + 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t * 22)
    elif kind == "hat":
        noise = rng.standard_normal(n)
        y = (noise - np.convolve(noise, np.ones(5) / 5, mode="same")) * np.exp(-t * 60) * 0.6
    elif kind == "impact":
        fr = 38 + 80 * np.exp(-t * 9)
        ph = 2 * np.pi * np.cumsum(fr) / sr
        noise = rng.standard_normal(n)
        y = 1.0 * np.sin(ph) * np.exp(-t * 2.2) + 0.45 * noise * np.exp(-t * 18)
    elif kind == "texture":
        noise = rng.standard_normal(n)
        for _ in range(3):
            noise = np.convolve(noise, np.ones(9) / 9, mode="same")
        y = noise * 6.0 * _env(n, sr, 0.8, 99.0, 1.0, 1.0, dur)
    else:
        y = np.sin(2 * np.pi * f * t) * _env(n, sr, 0.005, 0.5, 0.3, 0.1, dur)
    y = np.asarray(y, dtype=np.float64)
    pk = float(np.max(np.abs(y))) or 1.0
    return (amp * y / pk).astype(np.float32)


PAN = {"pad": (0.85, 0.85), "sub": (1.0, 1.0), "piano": (0.95, 0.8), "bell": (0.75, 1.0), "pluck": (1.0, 0.7),
       "arp": (0.7, 1.0), "lead": (0.9, 0.9), "kick": (1.0, 1.0), "snare": (0.95, 1.0), "hat": (0.8, 1.0),
       "impact": (1.0, 1.0), "texture": (0.9, 0.9)}
LEVEL_DB = {"pad": -9, "sub": -6, "piano": -6, "bell": -8, "pluck": -9, "arp": -11, "lead": -8, "kick": -4,
            "snare": -8, "hat": -16, "impact": -3, "texture": -14}


def render_builtin(parts: dict, length_s: float, sr: int = SR, seed: int = 0) -> dict:
    """{part: [{"t", "dur", "pitch", "vel"}]} (seconds) → {part: stereo float32 array of length_s}."""
    np = _np()
    N = int(math.ceil(length_s * sr))
    out = {}
    for part, notes in parts.items():
        kind = part.split("_")[0]
        y = np.zeros((N, 2), dtype=np.float32)
        g = 10 ** (LEVEL_DB.get(kind, -10) / 20.0)
        pl, pr = PAN.get(kind, (0.9, 0.9))
        for i, n in enumerate(notes):
            i0 = int(round(float(n["t"]) * sr))
            if i0 >= N:
                continue
            x = synth_note(kind, int(n["pitch"]), float(n["dur"]), int(n.get("vel", 90)), sr, seed + i)
            i1 = min(N, i0 + len(x))
            y[i0:i1, 0] += g * pl * x[:i1 - i0]
            y[i0:i1, 1] += g * pr * x[:i1 - i0]
        out[part] = y
    return out


def render_external(backend: str, parts_beats: dict, tempo_events: list, meter_events: list, length_s: float,
                    instrument: str, part_instruments: dict | None = None, sr: int = SR) -> dict:
    """FluidSynth (SF2) or sfizz_render (SFZ), one part at a time so every part is its own stem."""
    np = _np()
    exe = {"fluidsynth": "fluidsynth", "sfizz": "sfizz_render"}[backend]
    if not shutil.which(exe):
        raise SystemExit(f"{exe} is not installed — the VM installs FluidSynth with apt; sfizz_render from its release "
                         f"page; or use --backend numpy")
    td = tempfile.mkdtemp(prefix="cmp-")
    out, N = {}, int(math.ceil(length_s * sr))
    try:
        for part, notes in parts_beats.items():
            inst = (part_instruments or {}).get(part) or instrument
            mid = write_midi(os.path.join(td, part + ".mid"), {part: notes}, tempo_events, meter_events)
            wav = os.path.join(td, part + ".wav")
            if backend == "fluidsynth":
                cmd = ["fluidsynth", "-ni", "-F", wav, "-r", str(sr), "-g", "0.5", inst, mid]
            else:
                cmd = ["sfizz_render", "--sfz", inst, "--midi", mid, "--wav", wav, "--samplerate", str(sr)]
            subprocess.run(cmd, check=True, capture_output=True, stdin=subprocess.DEVNULL)
            x = MF.decode(wav, sr, 2)
            y = np.zeros((N, 2), dtype=np.float32)
            y[:min(N, len(x))] = x[:N]
            out[part] = y
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return out


def write_stems(stems: dict, out_dir: str, name: str, headroom_db: float = HEADROOM_DB) -> dict:
    """The stems and their sum at one common gain, peaking at `headroom_db` (no limiter): stems sum to the mix."""
    np = _np()
    if not stems:
        raise SystemExit("nothing to render")
    mix = sum(stems.values())
    pk = float(np.max(np.abs(mix))) or 1.0
    g = (10 ** (headroom_db / 20.0)) / pk
    files = {}
    os.makedirs(out_dir, exist_ok=True)
    for part, y in stems.items():
        p = os.path.join(out_dir, f"{name}.stem-{part}.wav")
        MF.encode(y * g, SR, p)
        files[part] = p
    mp = os.path.join(out_dir, f"{name}.wav")
    MF.encode(mix * g, SR, mp)
    return {"mix": mp, "stems": files, "gain_db": round(20 * math.log10(g), 2)}


def notes_to_seconds(notes: list, tmap: "TempoMap") -> list:
    return [dict(n, t=round(tmap.time(n["beat"]), 5), dur=round(tmap.time(n["beat"] + n["dur"]) - tmap.time(n["beat"]), 5))
            for n in notes]


class TempoMap:
    """Beats ↔ seconds for a constant tempo with bars of varying length (meter changes), starting at `start` s."""

    def __init__(self, bpm: float, start: float = 0.0, bars: list | None = None):
        self.bpm, self.start = float(bpm), float(start)
        self.bars = list(bars or [])             # beats per bar, in order; extended with 4 when asked past the end

    @property
    def beat_s(self) -> float:
        return 60.0 / self.bpm

    def time(self, beat: float) -> float:
        return self.start + float(beat) * self.beat_s

    def beat(self, t: float) -> float:
        return (float(t) - self.start) / self.beat_s

    def bar_starts(self, n: int | None = None) -> list:
        out, b = [], 0.0
        k = 0
        while (n is None and k < len(self.bars)) or (n is not None and k < n):
            out.append(b)
            b += self.bars[k] if k < len(self.bars) else 4
            k += 1
        return out

    def downbeats_s(self, n: int) -> list:
        return [self.time(b) for b in self.bar_starts(n)]

    def as_dict(self) -> dict:
        return {"bpm": round(self.bpm, 4), "start": round(self.start, 4), "bars": self.bars}

    @staticmethod
    def from_dict(d: dict) -> "TempoMap":
        return TempoMap(d["bpm"], d.get("start", 0.0), d.get("bars"))

    def midi_meters(self) -> list:
        ev, b, last = [], 0.0, None
        for n in self.bars:
            if n != last:
                ev.append((b, int(n) if float(n).is_integer() else 4, 4))
                last = n
            b += n
        return ev or [(0, 4, 4)]


# ── package A: the composer's brief, the spotting note, consent and the key ──────────────────────────────
def brief_init(job: str, force: bool = False) -> str:
    p = os.path.join(job, BRIEF)
    if os.path.isfile(p) and not force:
        raise SystemExit(f"{BRIEF} exists — the director's answers are not overwritten (--force to start again)")
    d = {"status": "DRAFT — fill every field; `composer.py brief lint <job>` says what is missing",
         "media_plan": [{"platform": "", "placement": "", "territories": [], "sound_on_share": "unverified"}],
         "references": [{"ref": "", "why_liked": "", "not_to_copy": ""}],
         "role": "", "vo_density": "", "lengths": [], "end_card_s": 4.0,
         "mnemonic": {"needed": False, "brand_name": "", "syllables": "", "language": "", "motif": ""},
         "revision_cap": 2, "route": "library",
         "deliverables": {"alt_mixes": ["full", "underscore"], "stems": "on_request", "stingers": 0},
         "consent": [], "route1_platform_label": "ask", "made": now_iso()}
    return jdump(d, p)


def brief_problems(job: str) -> tuple[list, list]:
    B = jload(os.path.join(job, BRIEF))
    if B is None:
        return [f"no composer's brief — `composer.py brief init {job}` and fill it"], []
    P, W = [], []
    mp = [m for m in B.get("media_plan") or [] if (m.get("platform") or "").strip()]
    if not mp:
        P.append("media_plan: name each platform and placement (where the music will be heard)")
    for m in mp:
        if not m.get("territories"):
            P.append(f"media_plan {m.get('platform')}: territories (ISO codes) — disclosure rules differ by region")
    refs = [r for r in B.get("references") or [] if (r.get("ref") or "").strip()]
    if not refs:
        W.append("references: none — the temp and the reference tracks, each with why it is liked, guide the cue")
    for r in refs:
        if not (r.get("why_liked") or "").strip():
            P.append(f"reference {r.get('ref')!r}: why it is liked — ask why a temp was chosen (temp diagnosis)")
    if B.get("role") not in ROLES:
        P.append("role: hero (the music leads) or texture (the music supports)")
    if B.get("vo_density") not in VO_DENSITY:
        P.append("vo_density: none, light or dense — it decides how much melody the cue can carry")
    if not B.get("lengths") or not all(isinstance(x, (int, float)) and x > 0 for x in B.get("lengths") or []):
        P.append("lengths: the slot lengths in seconds, e.g. [30, 15, 6]")
    mn = B.get("mnemonic") or {}
    if mn.get("needed") and not (mn.get("brand_name") or "").strip():
        P.append("mnemonic.needed is true: name the brand (and its syllables) the mnemonic carries")
    if not isinstance(B.get("revision_cap"), int) or B.get("revision_cap") < 0:
        P.append("revision_cap: a whole number of rounds")
    if B.get("route") not in ("library", "route1", "route2", "hybrid"):
        P.append("route: library, route1 (composed here), route2 (a generator) or hybrid")
    if B.get("route1_platform_label") not in ("ask", "yes", "no"):
        P.append("route1_platform_label: ask, yes or no (the owner's call until counsel answers, K10)")
    for c in B.get("consent") or []:
        if not parse_date(c.get("date")) or not (c.get("quote") or "").strip() or not c.get("by"):
            P.append("consent: every entry needs a date, who gave it and their words")
    return P, W


def spot_init(job: str, force: bool = False) -> str:
    p = os.path.join(job, SPOT)
    if os.path.isfile(p) and not force:
        raise SystemExit(f"{SPOT} exists — not overwritten (--force)")
    fps, cuts, end, _ = MF.cuts_of(job)
    if fps is None:
        raise SystemExit("no 07-edit/timeline-dump.json — dump the cut first (resolve-production-console.py "
                         "DUMP_TIMELINE_JSON); spotting is done against the cut")
    cue = {"id": "M1", "in_s": 0.0, "out_s": round(end or 0, 3), "function": "", "target_feeling": "",
           "temp": "", "temp_why": "", "withhold_or_release": "", "end_card_mood": "", "notes": ""}
    return jdump({"status": "DRAFT — one row per cue; split M1 where the music's job changes", "fps": fps,
                  "cues": [cue], "picture": picture_for_spotting(job, fps), "made": now_iso()}, p)


def picture_for_spotting(job: str, fps: float | None = None) -> dict:
    """(v2.68.0) What the composer needs from the picture before writing a note, read from the job, not typed: where
    the voice speaks, the must-hits, where the placed effects land, and each shot's Energy from the Sequence chain
    as PICTURE INTENT (how much the shot moves), never as a loudness target (plan rounds 1–2, both models). The cue
    leaves the voice windows and the big effects room; `target_feeling` stays the person's words."""
    _f, _c, _e, speech = MF.cuts_of(job)
    out = {"voice": speech, "must_hits": [], "effects": [], "energy_by_shot": [],
           "note": "picture intent, not a loudness curve: keep the cue out from under the voice windows and leave room "
                   "where the effects land; build towards the must-hits"}
    H = jload(os.path.join(job, MF.HITS))
    if H:
        out["must_hits"] = [{"id": h.get("id"), "t": h.get("t"), "want": h.get("want")}
                            for h in H.get("hits") or [] if h.get("priority") == "must"]
    P = jload(os.path.join(job, "06-music", "SFX-PLACEMENT.json")) or {}
    for e in P.get("events") or []:
        t = e.get("in_s") if e.get("in_s") is not None else (e.get("frame") / float(fps or 24) if e.get("frame") is not None else None)
        if t is not None:
            out["effects"].append({"sfx": e.get("sfx"), "t": round(float(t), 3)})
    try:
        import storyboard as SB
        ps, errs = SB.panels(job)
        t = 0.0
        for p_ in ps if not errs else []:
            if p_.get("dur"):
                out["energy_by_shot"].append({"shot": p_["shot"], "in_s": round(t, 2), "out_s": round(t + p_["dur"], 2),
                                              "energy": p_.get("energy") or None})
                t += p_["dur"]
    except Exception:                       # noqa: BLE001  no shot list yet: the composer works from the cut alone
        pass
    return out


def spot_problems(job: str) -> tuple[list, list]:
    S = jload(os.path.join(job, SPOT))
    if S is None:
        return [f"no spotting note — `composer.py spot init {job}`"], []
    P, W = [], []
    fps_tl, _, end, _ = MF.cuts_of(job)
    if fps_tl and abs(float(S.get("fps") or 0) - fps_tl) > 0.01:
        P.append(f"the spotting note says {S.get('fps')} fps and the timeline is {fps_tl} fps — spot against the cut")
    cues = S.get("cues") or []
    if not cues:
        P.append("no cues")
    for c in cues:
        cid = c.get("id") or "?"
        if c.get("function") not in FUNCTIONS:
            P.append(f"cue {cid}: function — one of {', '.join(FUNCTIONS)}")
        if not (c.get("target_feeling") or "").strip():
            P.append(f"cue {cid}: target_feeling — the one feeling the cue serves")
        if (c.get("temp") or "").strip() and not (c.get("temp_why") or "").strip():
            P.append(f"cue {cid}: the temp is named without why it was liked")
        if c.get("withhold_or_release") not in WITHHOLD:
            P.append(f"cue {cid}: withhold_or_release — withhold, release or hold")
        if not (isinstance(c.get("in_s"), (int, float)) and isinstance(c.get("out_s"), (int, float)) and c["out_s"] > c["in_s"]):
            P.append(f"cue {cid}: in_s and out_s in seconds, out after in")
    if cues and not (cues[-1].get("end_card_mood") or "").strip():
        W.append("the last cue names no end_card_mood — the music under the product shot changes what is remembered "
                 "(Boltz 2001)")
    return P, W


def consent_add(job: str, by: str, quote: str, scope: list, date: str | None = None) -> dict:
    p = os.path.join(job, BRIEF)
    B = jload(p)
    if B is None:
        raise SystemExit(f"no {BRIEF} — `composer.py brief init {job}` first")
    bad = [s for s in scope if s not in SCOPES]
    if bad or not scope:
        raise SystemExit(f"--scope: one or more of {', '.join(SCOPES)}")
    if len((quote or "").split()) < 3:
        raise SystemExit("--quote: the client's own words (a sentence, not 'ok')")
    c = {"date": date or now_iso(), "by": by, "quote": quote, "scope": scope, "recorded": now_iso()}
    B.setdefault("consent", []).append(c)
    jdump(B, p)
    return c


def consent_before(job: str, scope: str, when: dt.datetime | None) -> dict | None:
    """The earliest consent covering `scope` dated at or before `when` (IPA/ISBA Principle 11: before inclusion)."""
    B = jload(os.path.join(job, BRIEF)) or {}
    ok = []
    for c in B.get("consent") or []:
        d = parse_date(c.get("date"))
        if d and scope in (c.get("scope") or []) and (when is None or d <= when):
            ok.append((d, c))
    return min(ok, key=lambda x: x[0])[1] if ok else None


def key_confirm(job: str, key: str, by: str) -> dict:
    """K9: the bed's key, detected by the map, confirmed by the owner's ear before any composed layer locks."""
    tonic, mode = parse_key(key)
    H = MF.load_hits(job)
    tr = H.setdefault("track", {})
    detected = None
    F = jload(os.path.join(job, MF.FIT))
    if F:
        M = jload(os.path.join(job, F["plans"][F.get("picked", 0)]["map"])) or {}
        detected = (M.get("key") or {}).get("name")
    tr["key_confirmed"] = {"key": key_name(tonic, mode), "by": by, "date": now_iso(), "detected": detected}
    jdump(H, os.path.join(job, MF.HITS))
    return tr["key_confirmed"]


# ── package B: the owned motif ───────────────────────────────────────────────────────────────────────────
def syllable_rhythm(syllables: str) -> list:
    """'ac-ME' → durations in beats: a stressed syllable (in CAPITALS, or marked with ') is long, the rest short —
    simple integer ratios only (1:1, 1:2; complex ratios sound un-rhythmic). Nothing marked: the last is long."""
    parts = [s for s in re.split(r"[-\s·.]+", syllables or "") if s]
    if not parts:
        return []
    marked = [x.endswith("'") or (x.isupper() and len(x) > 1) for x in parts]
    if not any(marked):
        marked[-1] = True
    return [1.0 if m else 0.5 for m in marked]


def motif_drafts(brand: str, key: str, syllables: str = "", feeling: str = "warm", n: int = 3, seed: int = 0) -> list:
    """Rule-based drafts, 3–6 notes: the contour by feeling (rising reads exciting, falling pleasant), ending on the
    tonic or the fifth, the rhythm from the brand name's syllables where given. The owner edits one."""
    tonic, mode = parse_key(key)
    want_mode, contour = FEELINGS.get(feeling, FEELINGS["warm"])
    rng = random.Random(f"{brand}|{key}|{syllables}|{feeling}|{seed}")
    base_r = syllable_rhythm(syllables)
    drafts = []
    shapes = {"rising": [[1, 3, 5], [5, 6, 8], [1, 2, 3, 5], [3, 5, 8], [5, 6, 7, 8]],
              "falling": [[8, 7, 5], [5, 3, 1], [5, 4, 3, 1], [8, 5, 3, 1], [6, 5, 3]],
              "arch": [[1, 3, 5, 3], [3, 5, 6, 5], [1, 5, 6, 5], [5, 8, 7, 5], [1, 2, 5, 4, 3]]}
    pool = list(shapes[contour])
    rng.shuffle(pool)
    for k in range(n):
        degs = list(pool[k % len(pool)])
        L = min(6, max(3, len(base_r))) if base_r else len(degs)
        while len(degs) < L:
            degs.insert(-1, degs[-2] + rng.choice([-1, 1]))
        degs = degs[:L]
        if degs[-1] not in (1, 5, 8, 3):
            degs[-1] = 1 if contour == "falling" else 5
        if base_r:                                           # the name's rhythm ends the motif; pickups before it
            rhythm = ([0.5] * max(0, L - len(base_r)) + base_r)[-L:]
        else:
            rhythm = [rng.choice([0.5, 0.5, 1.0]) for _ in range(L - 1)] + [1.5]
        rhythm[-1] = max(rhythm[-1], 1.0)
        notes, b = [], 0.0
        for d, r in zip(degs, rhythm):
            notes.append({"beat": round(b, 3), "dur": round(r * 0.95, 3), "pitch": degree_pitch(tonic, mode, d, 5),
                          "vel": 96 if b == 0 else 84})
            b += r
        drafts.append({"id": k + 1, "brand": brand, "key": key_name(tonic, mode), "feeling": feeling,
                       "contour": contour, "syllables": syllables, "notes": notes, "timbre": "bell",
                       "mode_suggested": want_mode})
    return drafts


def motif_draft(home: str, brand: str, key: str, syllables: str = "", feeling: str = "warm", n: int = 3) -> str:
    os.makedirs(home, exist_ok=True)
    D = motif_drafts(brand, key, syllables, feeling, n)
    for d in D:
        write_midi(os.path.join(home, f"MOTIF-DRAFT-{d['id']}.mid"), {d["timbre"]: d["notes"]}, [(0, 100)])
    return jdump({"brand": brand, "made": now_iso(), "drafted_by": "composer.py motif draft (rules, no model)",
                  "drafts": D, "next": "edit one (any MIDI editor, or the notes here), then `composer.py motif adopt`"},
                 os.path.join(home, "MOTIF-DRAFTS.json"))


def _intervals(notes: list) -> list:
    ps = [int(n["pitch"]) for n in sorted(notes, key=lambda n: n["beat"])]
    return [b - a for a, b in zip(ps, ps[1:])]


def _iois(notes: list) -> list:
    bs = [float(n["beat"]) for n in sorted(notes, key=lambda n: n["beat"])]
    return [round(b - a, 3) for a, b in zip(bs, bs[1:])]


def motif_diff(draft: list, edited: list) -> dict:
    """What the owner changed: notes added or removed, pitches moved, rhythm changed — the authorship evidence."""
    a = sorted(draft, key=lambda n: n["beat"])
    b = sorted(edited, key=lambda n: n["beat"])
    m = min(len(a), len(b))
    pitch = sum(1 for i in range(m) if int(a[i]["pitch"]) != int(b[i]["pitch"]))
    rhythm = sum(1 for i in range(m) if abs(float(a[i]["beat"]) - float(b[i]["beat"])) > 1e-3
                 or abs(float(a[i]["dur"]) - float(b[i]["dur"])) > 0.05)
    added = abs(len(a) - len(b))
    changed = sum(1 for i in range(m) if int(a[i]["pitch"]) != int(b[i]["pitch"])
                  or abs(float(a[i]["beat"]) - float(b[i]["beat"])) > 1e-3) + added
    frac = changed / max(len(a), len(b), 1)
    return {"notes_draft": len(a), "notes_adopted": len(b), "pitch_changes": pitch, "rhythm_changes": rhythm,
            "added_or_removed": added, "changed_fraction": round(frac, 3),
            "intervals_draft": _intervals(a), "intervals_adopted": _intervals(b)}


def melody_matches(notes: list, midi_dirs: list, motif_files: list) -> list:
    """The adopted motif's interval and rhythm sequence against the owner's kit MIDI and every other client's
    motif. An identical interval sequence (transposition-free) is a match; a match with the same rhythm is exact."""
    iv, io = _intervals(notes), _iois(notes)
    if len(iv) < 2:
        return []
    out = []
    for f in motif_files:
        M = jload(f) or {}
        other = M.get("notes") or []
        if _intervals(other) == iv:
            out.append({"file": f, "kind": "motif", "exact": _iois(other) == io})
    for d in midi_dirs:
        for f in glob.glob(os.path.join(d, "**", "*.mid"), recursive=True)[:5000]:
            try:
                ns = read_midi_notes(f)
            except Exception:                               # noqa: BLE001
                continue
            top = {}
            for n in ns:                                     # the top line per onset
                k = round(n["beat"], 3)
                if k not in top or n["pitch"] > top[k]["pitch"]:
                    top[k] = n
            seq = [top[k] for k in sorted(top)]
            siv = _intervals(seq)
            for i in range(0, max(0, len(siv) - len(iv) + 1)):
                if siv[i:i + len(iv)] == iv:
                    out.append({"file": f, "kind": "kit midi", "at_note": i,
                                "exact": _iois(seq[i:i + len(iv) + 1]) == io})
                    break
    return out


def motif_adopt(home: str, draft_id: int, edited: str, by: str, statement: str = "", written_by_owner: bool = False,
                midi_dirs: list | None = None, registry: str | None = None) -> dict:
    """K2 (house rule 2026-10-27: "Skill drafts, I edit"): the owner picks a draft and substantively edits it;
    the diff is kept. Refused when under a third of the notes changed, unless he wrote it himself."""
    D = jload(os.path.join(home, "MOTIF-DRAFTS.json"))
    if not D:
        raise SystemExit(f"no MOTIF-DRAFTS.json in {home} — `composer.py motif draft` first")
    dr = next((d for d in D["drafts"] if int(d["id"]) == int(draft_id)), None)
    if dr is None:
        raise SystemExit(f"no draft {draft_id}")
    if edited.lower().endswith(".mid"):
        notes = read_midi_notes(edited)
    else:
        E = jload(edited)
        notes = (E or {}).get("notes") if isinstance(E, dict) else E
    if not notes or not 3 <= len(notes) <= 8:
        raise SystemExit("the edited motif needs 3–8 notes")
    t0 = min(float(n["beat"]) for n in notes)
    notes = [{"beat": round(float(n["beat"]) - t0, 3), "dur": float(n["dur"]), "pitch": int(n["pitch"]),
              "vel": int(n.get("vel", 90))} for n in sorted(notes, key=lambda n: n["beat"])]
    diff = motif_diff(dr["notes"], notes)
    if diff["changed_fraction"] < 1 / 3 and not written_by_owner:
        raise SystemExit(f"refused: only {diff['changed_fraction']:.0%} of the draft changed — the motif is the owner's "
                         f"when they substantively edit it (a third of the notes or more), or say --written-by-owner")
    reg = registry or os.path.join(cine_home(), "motifs")
    others = [f for f in glob.glob(os.path.join(reg, "*.json")) if (jload(f) or {}).get("brand") != dr["brand"]]
    matches = melody_matches(notes, midi_dirs or [], others)
    exact = [m for m in matches if m["exact"]]
    if exact:
        raise SystemExit("refused: the motif repeats an existing melody exactly — " + "; ".join(m["file"] for m in exact))
    dur_beats = max(n["beat"] + n["dur"] for n in notes)
    M = {"brand": dr["brand"], "key": dr["key"], "timbre": dr.get("timbre", "bell"), "notes": notes,
         "drafted_from": {"draft": dr["id"], "notes": dr["notes"], "by": D.get("drafted_by")},
         "diff": diff, "adopted_by": by, "adopted_at": now_iso(), "written_by_owner": bool(written_by_owner),
         "statement": statement or f"{by} chose draft {dr['id']} and rewrote it ({diff['changed_fraction']:.0%} of the notes "
                                   f"changed); the skill drafted, {by} composed the adopted motif",
         "melody_check": {"checked": now_iso(), "midi_dirs": midi_dirs or [], "motifs_compared": len(others),
                          "matches": matches},
         "derived": {"mnemonic_beats": dur_beats, "stinger": notes[-3:], "statement_bars": 2},
         "blind_test": None}
    jdump(M, os.path.join(home, "MOTIF.json"))
    os.makedirs(reg, exist_ok=True)
    jdump(M, os.path.join(reg, re.sub(r"[^A-Za-z0-9_-]+", "_", dr["brand"]) + ".json"))
    write_midi(os.path.join(home, "MOTIF.mid"), {M["timbre"]: notes}, [(0, 100)])
    return M


def transpose_diatonic(notes: list, src_key: str, dst_key: str) -> list:
    """Each note keeps its scale degree: a motif written in C major sung over a C#m bed keeps its shape in C#m."""
    st, sm = parse_key(src_key)
    dt_, dm = parse_key(dst_key)
    s_steps = MODES[sm]
    out = []
    shift = ((dt_ - st + 6) % 12) - 6                         # the nearest tonic move (−6..+5 semitones)
    for n in notes:
        p = int(n["pitch"])
        rel_ = (p - st) % 12
        octv = (p - st) // 12
        deg = min(range(7), key=lambda i: abs(s_steps[i] - rel_))
        q = st + shift + 12 * octv + MODES[dm][deg]
        out.append(dict(n, pitch=int(q)))
    return out


def _speech(H: dict) -> list:
    return [(float(a), float(b)) for a, b in H.get("speech") or []]


def _in_speech(t: float, sp: list) -> bool:
    return any(a - 0.05 <= t <= b + 0.05 for a, b in sp)


def layer(job: str, motif_path: str, backend: str = "numpy", instrument: str = "builtin", stab: bool = False) -> dict:
    """Package B (B9): composed layers over the fitted library bed — an impact on every hard hit, the client's
    mnemonic as the button, in the bed's confirmed key on its bar grid, motif notes muted under speech."""
    H = MF.load_hits(job)
    F = jload(os.path.join(job, MF.FIT))
    if not F or not (F.get("render") or {}).get("file"):
        raise SystemExit("no fitted bed — `music_fit.py fit` and `render` first; the layer sits on the bed's grid")
    kc = (H.get("track") or {}).get("key_confirmed")
    if not kc or not kc.get("key"):
        raise SystemExit("the bed's key is not confirmed — listen, then `composer.py key confirm <job> --key <K> --by <you>` "
                         "(K9: detection errs on modal and sparse beds)")
    Mo = jload(motif_path)
    if not Mo or not Mo.get("notes"):
        raise SystemExit(f"{motif_path}: no adopted motif — `composer.py motif adopt` first")
    b = F["plans"][F.get("picked", 0)]
    plan = MF.Plan.from_dict(b["plan"])
    M = jload(os.path.join(job, b["map"]))
    beat_tl = (60.0 / float(M["tempo"])) / plan.ratio
    fps = float(H.get("fps") or 24)
    sp = _speech(H)
    dur = float(H.get("duration") or 0) or plan.start + plan.length()
    parts = {"impact": []}
    hard = [h for h in H.get("hits") or [] if MF.tier_of(h) == "hard" and h.get("strategy") != "play_through"
            and h.get("want") not in ("stop_down", "button", "entry") and isinstance(h.get("t"), (int, float))]
    OFF = 0.008                                               # the impact onset 8 ms after its frame: inside 0..+1 frame
    tonic, mode = parse_key(kc["key"])
    for h in hard:
        parts["impact"].append({"t": float(h["t"]) + OFF, "dur": 0.6, "pitch": 36, "vel": 112, "hit": h["id"]})
        if stab:
            parts.setdefault("bell", []).append({"t": float(h["t"]) + OFF, "dur": 0.5, "pitch": degree_pitch(tonic, mode, 1, 4), "vel": 96, "hit": h["id"]})
    btn = next((h for h in H.get("hits") or [] if h.get("want") == "button"), None)
    ec = H.get("end_card") or {}
    t_btn = float(btn["t"]) if btn else float(ec.get("t") or (dur - 4.0))
    mot = transpose_diatonic(Mo["notes"], Mo["key"], kc["key"])
    last = max(float(n["beat"]) for n in mot)
    timbre = Mo.get("timbre") or "bell"
    muted = 0
    for n in mot:
        t = t_btn + OFF - (last - float(n["beat"])) * beat_tl
        if t < 0:
            continue
        if _in_speech(t, sp):
            muted += 1
            continue
        parts.setdefault(timbre, []).append({"t": round(t, 5), "dur": float(n["dur"]) * beat_tl, "pitch": int(n["pitch"]),
                                             "vel": int(n.get("vel", 90)), "motif": True})
    if not parts["impact"]:
        parts.pop("impact")
    pp = palette_problems(list(parts))
    if pp:
        raise SystemExit("refused: " + "; ".join(pp))
    lic = instrument_licence(instrument if backend != "numpy" else "builtin")
    if str(lic.get("paid_ads")).lower() != "yes":
        raise SystemExit(f"refused: the instrument {lic.get('file')} is not cleared for paid ads — {lic.get('why') or lic.get('licence')}")
    t0 = time.time()
    if backend == "numpy":
        stems_ = render_builtin(parts, dur)
    else:
        pb = {k: [dict(n, beat=n["t"] / beat_tl, dur=n["dur"] / beat_tl) for n in v] for k, v in parts.items()}
        stems_ = render_external(backend, pb, [(0, 60.0 / beat_tl)], [(0, 4, 4)], dur, instrument)
    secs = round(time.time() - t0, 2)
    name = os.path.basename(os.path.abspath(job)) + ".layer"
    od = os.path.join(job, COMPOSE_DIR)
    out = write_stems(stems_, od, name)
    mid = write_midi(os.path.join(od, name + ".mid"),
                     {k: [{"beat": n["t"] / beat_tl, "dur": n["dur"] / beat_tl, "pitch": n["pitch"], "vel": n["vel"]} for n in v]
                      for k, v in parts.items()}, [(0, 60.0 / beat_tl)])
    rec = {"kind": "composed_layer", "route": "route1", "tool": "composer.py layer", "version": "2.40.0",
           "made": now_iso(), "backend": backend, "render_seconds": secs,
           "instruments": [lic], "palette": sorted(parts), "key": kc, "bed": F["render"]["file"],
           "motif": {"file": os.path.abspath(motif_path), "brand": Mo.get("brand"), "adopted_by": Mo.get("adopted_by"),
                     "statement": Mo.get("statement"), "diff": Mo.get("diff"), "melody_check": Mo.get("melody_check")},
           "hits": [{"id": h["id"], "t": h["t"], "onset_s": float(h["t"]) + OFF} for h in hard],
           "button": {"t": t_btn, "notes": len(mot), "muted_under_speech": muted},
           "midi": MF.rel(job, mid), "human_contribution": Mo.get("statement"),
           "validators": "palette, instrument licence, key confirmed", "sha256": MF.sha256_file(out["mix"])}
    jdump(rec, out["mix"] + ".compose.json")
    licence = "own composition (composer.py, route 1); instruments: " + "; ".join(
        f"{lic.get('name') or lic.get('id')} ({lic.get('licence')})" for _ in [0])
    jdump({"source": "composed:route1", "paid_ads": "yes", "licence": licence}, out["mix"] + ".licence.json")
    for part, p in out["stems"].items():
        jdump({"kind": "stem", "sources": [{"file": MF.rel(job, out["mix"]), "role": "music"}], "part": part}, p + ".conform.json")
    L = {"made": now_iso(), "file": MF.rel(job, out["mix"]), "stems": {k: MF.rel(job, v) for k, v in out["stems"].items()},
         "parts": parts, "beat_s": beat_tl, "key": kc["key"], "motif": os.path.abspath(motif_path), "render_seconds": secs,
         "sha256": rec["sha256"], "gain_db": out["gain_db"]}
    jdump(L, os.path.join(job, LAYER))
    return L


def family(job: str, lengths: list | None = None, motif_path: str | None = None) -> dict:
    """B6: the length family from one idea — each length fitted by the same solver, ending inside its slot, with
    the mnemonic as its button; plus the alt mixes of the main cut (full = bed + layer, underscore = the bed)."""
    np = _np()
    H = MF.load_hits(job)
    F = jload(os.path.join(job, MF.FIT))
    if not F or not (F.get("render") or {}).get("file"):
        raise SystemExit("no fitted bed — `music_fit.py fit` and `render` first")
    B = jload(os.path.join(job, BRIEF)) or {}
    lengths = [float(x) for x in (lengths or B.get("lengths") or [])]
    if not lengths:
        raise SystemExit("no lengths — set them in the brief or pass --lengths 30,15,6")
    b = F["plans"][F.get("picked", 0)]
    M = jload(os.path.join(job, b["map"]))
    plan0 = MF.Plan.from_dict(b["plan"])
    track_abs = MF.absj(job, plan0.track)
    x = MF.decode(track_abs, SR, 2)
    ecd = float(B.get("end_card_s") or (H.get("end_card") or {}).get("dur") or 4.0)
    Mo = jload(motif_path) if motif_path else None
    kc = (H.get("track") or {}).get("key_confirmed")
    out = {"made": now_iso(), "lengths": [], "alt_mixes": {}}
    od = os.path.join(job, FAMILY_DIR)
    os.makedirs(od, exist_ok=True)
    stem = os.path.splitext(os.path.basename(plan0.track))[0]
    for Lsec in sorted(set(lengths), reverse=True):
        Hs = {"fps": H.get("fps"), "duration": Lsec, "start": 0.0, "end_card": {"t": max(0.5, Lsec - ecd), "dur": ecd},
              "hits": [{"id": "BUTTON", "t": max(0.5, Lsec - ecd), "priority": "must", "tier": "hard", "want": "button"}],
              "track": dict(H.get("track") or {}, **{"in": (H.get("track") or {}).get("in", "phrase")})}
        cands = MF.plans_for(M, Hs, plan0.track, f"{Lsec:g}s")
        if not cands:
            out["lengths"].append({"length": Lsec, "problem": "no plan fits this length"})
            continue
        best = min(cands, key=lambda p: MF.score_plan(p, M, Hs)[0])
        y = MF.assemble(x, SR, best, M)
        if abs(best.ratio - 1.0) > 1e-6:
            td = tempfile.mkdtemp(prefix="fam-")
            y = MF.decode(MF.stretch_file(MF.encode(y, SR, os.path.join(td, "a.wav")), os.path.join(td, "b.wav"), best.ratio), SR, 2)
            shutil.rmtree(td, ignore_errors=True)
        n_end = int(Lsec * SR) - int(0.02 * SR)              # the music ends inside the slot
        y = y[:n_end].copy() if len(y) > n_end else np.concatenate([y, np.zeros((n_end - len(y), 2), np.float32)])
        f_ = min(int(0.75 * SR), len(y))
        y[-f_:] *= np.linspace(1, 0, f_, dtype=np.float32)[:, None]
        if Mo and kc:
            beat_tl = (60.0 / float(M["tempo"])) / best.ratio
            mot = transpose_diatonic(Mo["notes"], Mo["key"], kc["key"])
            last = max(float(n["beat"]) for n in mot)
            tb = Hs["end_card"]["t"] + 0.008
            notes = [{"t": tb - (last - float(n["beat"])) * beat_tl, "dur": float(n["dur"]) * beat_tl,
                      "pitch": int(n["pitch"]), "vel": int(n.get("vel", 90))} for n in mot]
            ly = render_builtin({Mo.get("timbre") or "bell": [n for n in notes if n["t"] >= 0]}, len(y) / SR)
            y = y + sum(ly.values())[:len(y)]
        pk = float(np.max(np.abs(y))) or 1.0
        if pk > 10 ** (HEADROOM_DB / 20):
            y = y * (10 ** (HEADROOM_DB / 20) / pk)
        p = os.path.join(od, f"{stem}.{Lsec:g}s.wav")
        MF.encode(y, SR, p)
        srcs = [{"file": plan0.track, "role": "music"}]
        if Mo and os.path.isfile(os.path.join(job, LAYER)):
            srcs.append({"file": (jload(os.path.join(job, LAYER)) or {}).get("file"), "role": "music"})
        jdump({"kind": "music_family", "preview": True, "note": MF.PREVIEW_NOTE.replace("REBUILD.json", "this length's plan"),
               "sources": srcs, "plan": best.as_dict(), "length": Lsec}, p + ".conform.json")
        out["lengths"].append({"length": Lsec, "file": MF.rel(job, p), "edits": best.edits, "ratio": best.ratio,
                               "ends_at_s": round(len(y) / SR, 3)})
    bed = MF.absj(job, F["render"]["file"])
    out["alt_mixes"]["underscore"] = F["render"]["file"]
    L = jload(os.path.join(job, LAYER))
    if L:
        a = MF.decode(bed, SR, 2)
        c = MF.decode(MF.absj(job, L["file"]), SR, 2)
        n = max(len(a), len(c))
        full = np.zeros((n, 2), np.float32)
        full[:len(a)] += a
        full[:len(c)] += c
        pk = float(np.max(np.abs(full))) or 1.0
        if pk > 10 ** (HEADROOM_DB / 20):
            full *= 10 ** (HEADROOM_DB / 20) / pk
        p = os.path.join(od, f"{stem}.full.wav")
        MF.encode(full, SR, p)
        jdump({"kind": "alt_mix", "preview": True, "note": MF.PREVIEW_NOTE.replace("REBUILD.json", "the bed and the layer"),
               "sources": [{"file": F["render"]["file"]}, {"file": L["file"]}]}, p + ".conform.json")
        out["alt_mixes"]["full"] = MF.rel(job, p)
    jdump(out, os.path.join(job, "07-edit", "music", "FAMILY.json"))
    return out


# ── the element sheet: what every sound is, and what it needs disclosed ──────────────────────────────────
def _class_of(job: str, rel_: str, rows: dict, depth: int = 0) -> str:
    f = os.path.join(job, rel_)
    if os.path.isfile(f + ".gen.json"):
        return "ai-generated"
    if os.path.isfile(f + ".compose.json"):
        return "sample-rendered"
    sc = jload(f + ".conform.json")
    if sc and depth < 4:
        kinds = {_class_of(job, s.get("file") or "", rows, depth + 1) for s in sc.get("sources") or [] if s.get("file")}
        for k in ("ai-generated", "sample-rendered", "human", "library"):
            if k in kinds:
                return k
    r = rows.get(rel_) or rows.get(os.path.basename(rel_)) or {}
    src = (r.get("source") or "").lower()
    if src.startswith("ai") or (r.get("tool") or "").strip():
        return "ai-generated"
    if src.startswith(("talent", "own-recording", "client")):
        return "human"
    if src.startswith("composed"):
        return "sample-rendered"
    return "library"


def elements(job: str) -> dict:
    import mix_qa as MQ  # noqa: E402
    rows = {}
    for r in MQ.read_manifest(job):
        rows[r.get("file", "")] = r
        rows[os.path.basename(r.get("file", ""))] = r
    files = MQ.audio_files(job)
    B = jload(os.path.join(job, BRIEF)) or {}
    terr = {t.upper() for m in B.get("media_plan") or [] for t in m.get("territories") or []}
    eu = set((jload(os.path.join(SKILL, "assets", "ai-audio-licences.json")) or {}).get("eu_regions") or [])
    E = []
    for f in files:
        k = _class_of(job, f, rows)
        g = jload(os.path.join(job, f + ".gen.json")) or {}
        E.append({"file": f, "class": k, "vendor": g.get("vendor"), "vocals": g.get("vocals"), "use": g.get("use")})
    kinds = {e["class"] for e in E}
    disc = []
    if "ai-generated" in kinds:
        disc.append("TikTok: switch on the AI-generated content toggle on EVERY campaign and every duplicate (a duplicate "
                    "resets it) — audio 'completely AI-generated or significantly modified by AI'")
        disc.append("YouTube: an upload that carries C2PA metadata is labelled automatically, and the label cannot be "
                    "removed — tell the client before upload")
        disc.append("The client consented in writing before the generated material entered the cut (IPA/ISBA Principle 11)")
    if any(e.get("vocals") == "ai" for e in E):
        disc.append("AI vocals: disclosed as AI-generated wherever the ad runs" + (" — in the EU, Article 50(4) applies to a "
                    "realistic synthetic voice" if (terr & eu) else ""))
    if "sample-rendered" in kinds:
        lab = B.get("route1_platform_label", "ask")
        disc.append({"yes": "Route-1 music: AI-composed — platform AI toggles ON (the owner's choice)",
                     "no": "Route-1 music: AI-composed, rendered from licensed samples — disclosed to the client on this "
                           "sheet; platform toggles off (the owner's choice; counsel pending)",
                     "ask": "Route-1 music: AI-composed, rendered from licensed samples — the owner decides the platform "
                            "toggle per campaign (counsel pending, K10); disclosed to the client on this sheet"}[lab if lab in ("yes", "no") else "ask"])
    sheet = {"made": now_iso(), "elements": E, "disclosure": disc, "territories": sorted(terr),
             "listing_sha": hashlib.sha256("\n".join(sorted(files)).encode()).hexdigest()}
    jdump(sheet, os.path.join(job, ELEMENTS_JSON))
    L = ["# Element sheet — every sound in the film, what it is, and what it needs disclosed", "",
         "Written by `composer.py elements` (v2.40). Classes: library · human · sample-rendered (composed here, route 1) "
         "· ai-generated (route 2). Give this sheet to the client with the cut.", "",
         "| file | class | vendor | vocals | use |", "|---|---|---|---|---|"]
    for e in E:
        L.append(f"| {e['file']} | {e['class']} | {e.get('vendor') or ''} | {e.get('vocals') or ''} | {e.get('use') or ''} |")
    L += ["", "## Disclosure", ""] + [f"- {d}" for d in disc or ["Nothing AI-made in the audio."]]
    p = os.path.join(job, ELEMENTS)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return sheet


# ── Resolve: the Fairlight copy of the console script ────────────────────────────────────────────────────
def _origin(job: str, rel_: str) -> str:
    k = _class_of(job, rel_, {})
    return {"ai-generated": "generated", "sample-rendered": "composed"}.get(k, "library")


def console_copy(job: str, fairlight_preset: str = "") -> str:
    """07-edit/resolve-production-console.compose.py: on A5 the ORIGINAL track's segments, as `music_fit.py rebuild`
    places them (2026-11-05: a Python render is a preview, never imported into Resolve), the composed layer on
    A6, every stem on its own NAMED, DISABLED stereo track (switch one on in Fairlight to rebalance), clip colours by
    origin (library Blue, composed Purple, generated Orange), the spotting cues, the hits and the music seams as
    markers whose custom data carries each hit's window, and an optional Fairlight preset. NOT placed: the alt mix
    (06-music/family/<stem>.full.wav) and the length family (06-music/family/<stem>.<L>s.wav) — both are cut or mixed
    in Python, so they are previews; each is rebuilt in Resolve (FAMILY.json lists each length's plan) and
    MUSIC_FAMILY stays empty. Nothing is deleted and nothing is placed over a clip."""
    H = MF.load_hits(job)
    F = jload(os.path.join(job, MF.FIT)) or {}
    fps = float(H.get("fps") or F.get("fps") or 24)
    src = open(MF.CONSOLE, encoding="utf-8").read()
    elems, nxt = [], 7
    if F.get("plans"):
        b = F["plans"][F.get("picked", 0)]
        M = (jload(os.path.join(job, b["map"])) or {}) if b.get("map") else {}
        RB = MF.current_rebuild(job)
        mk = MF.merge_markers(MF.sparse_markers(job, F, M, H), MF.rebuild_markers(RB))
        mf = MF.console_music_fit(job, RB, COLORS[_origin(job, RB["original"]["file"])])
        src = _splice(src, "MUSIC_FIT = {}  # __MUSIC_FIT__", "MUSIC_FIT = " + repr(mf) + "  # __MUSIC_FIT__")
        src = _splice(src, "\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True")
    else:
        mk = []
    L = jload(os.path.join(job, LAYER))
    if L:
        elems.append({"file": os.path.abspath(os.path.join(job, L["file"])), "track": 6, "name": "A6 music",
                      "color": COLORS["composed"], "enabled": True, "role": "composed layer"})
        for part, f in sorted((L.get("stems") or {}).items()):
            elems.append({"file": os.path.abspath(os.path.join(job, f)), "track": nxt, "name": f"STEM {part} (composed)",
                          "color": COLORS["stem"], "enabled": False, "role": "stem"})
            nxt += 1
    # (2026-11-05) the alt mix and the length family are previews made in Python: never placed (MF.is_preview)
    elems = [e for e in elems if not MF.is_preview(e["file"])]
    S = jload(os.path.join(job, SPOT)) or {}
    for c in S.get("cues") or []:
        if isinstance(c.get("in_s"), (int, float)):
            dur = max(1, int(round((float(c.get("out_s") or c["in_s"]) - float(c["in_s"])) * fps)))
            mk.append((int(round(float(c["in_s"]) * fps)), "Purple", f"Cue {c.get('id')} {c.get('function') or ''}".strip(),
                       f"{c.get('target_feeling') or ''} · {c.get('withhold_or_release') or ''}", dur, ""))
    for h in H.get("hits") or []:
        if isinstance(h.get("t"), (int, float)) and MF.tier_of(h) == "hard" and h.get("strategy") != "play_through":
            win = 1000.0 / fps
            fr = int(round(float(h["t"]) * fps))
            mk = [m for m in mk if not (m[0] == fr and m[1] == "Green")]
            mk.append((fr, "Green", f"Hit {h['id']} {h.get('want')}", f"hard · window 0 to +{win:.0f} ms, never early", 1,
                       json.dumps({"hit": h["id"], "tier": "hard", "window_ms": [0, round(win, 1)], "onset": "transient_peak"})))
    fam = []                    # (2026-11-05) the family's lengths are cut in Python: previews, rebuilt in Resolve
    seen, mk2 = set(), []
    for m in sorted(mk, key=lambda m: m[0]):
        if m[0] in seen or m[0] < 0:
            continue
        seen.add(m[0])
        mk2.append(m)
    src = _splice(src, "MARKERS = []  # __DETECT_BEATS_MARKERS__", "MARKERS = " + repr(mk2) + "  # __DETECT_BEATS_MARKERS__")
    src = _splice(src, "MUSIC_ELEMENTS = []  # __MUSIC_ELEMENTS__", "MUSIC_ELEMENTS = " + repr(elems) + "  # __MUSIC_ELEMENTS__")
    src = _splice(src, "\nPLACE_MUSIC_ELEMENTS = False", "\nPLACE_MUSIC_ELEMENTS = " + repr(bool(elems)))
    src = _splice(src, "MUSIC_FAMILY = []  # __MUSIC_FAMILY__", "MUSIC_FAMILY = " + repr(fam) + "  # __MUSIC_FAMILY__")
    src = _splice(src, "\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False")
    if fairlight_preset:
        src = _splice(src, 'FAIRLIGHT_PRESET = ""', "FAIRLIGHT_PRESET = " + repr(fairlight_preset))
    src = src.replace('"""\nDaVinci Resolve — the ONE production/editing-setup console script',
                      f'"""\nFilled in by composer.py console ({now_iso()}): the music for Fairlight — the ORIGINAL track\'s '
                      f'segments on A5 (music_fit.py rebuild; crossfades and fades in Fairlight by computer control, '
                      f'REBUILD.md), the composed layer, its stems, markers.\nNot placed: the alt mix and the length family '
                      f'— previews cut in Python; rebuild each in Resolve.\n\n'
                      f'DaVinci Resolve — the ONE production/editing-setup console script', 1)
    out = os.path.join(job, "07-edit", COMPOSE_COPY)
    open(out, "w", encoding="utf-8").write(src)
    return out


def _splice(src: str, old: str, new: str) -> str:
    if old not in src:
        raise RuntimeError(f"resolve-production-console.py no longer contains {old!r} — update composer.console_copy()")
    return src.replace(old, new, 1)


# ── package C: the route-1 note engine ───────────────────────────────────────────────────────────────────
def _hit_class(d: float, fps: float, tier: str) -> str:
    return MF.classify(d, fps, tier)


def solve(job: str, bpm_lo: float = 70.0, bpm_hi: float = 140.0, play_through: list | None = None, step: float = 0.01,
          top: int = 3) -> dict:
    """A tempo map that puts every hard hit on a downbeat: one constant tempo, 4/4, at most one inserted 2/4 or 3/4
    bar (a single beat change "usually not conspicuous", MusicTech). Ranked by weighted hit error; a hit no tempo
    can land is named so the owner picks it to play through (`--play-through`)."""
    H = MF.load_hits(job)
    fps = float(H.get("fps") or 24)
    pt = set(play_through or [])
    if pt:
        for h in H.get("hits") or []:
            if h.get("id") in pt:
                h["strategy"] = "play_through"
        jdump(H, os.path.join(job, MF.HITS))
    hard = [h for h in H.get("hits") or [] if MF.tier_of(h) == "hard" and h.get("strategy") != "play_through"
            and isinstance(h.get("t"), (int, float)) and h.get("want") != "stop_down"]
    soft = [h for h in H.get("hits") or [] if MF.tier_of(h) == "soft" and h.get("strategy") == "catch"
            and isinstance(h.get("t"), (int, float))]
    start = float(H.get("start") or 0.0)
    dur = float(H.get("duration") or 0) or (max([float(h["t"]) for h in hard] or [30.0]) + 4.0)
    if not hard:
        raise SystemExit("no hard hits to solve for — mark the director-called hits (tier hard) in HITS.json")
    f = 1.0 / fps
    cands = []
    bpm = bpm_lo
    while bpm <= bpm_hi + 1e-9:
        beat = 60.0 / bpm
        nbars = int(math.ceil((dur - start) / (4 * beat))) + 2
        inserts = [None] + [(j, k) for j in range(1, min(nbars, 40)) for k in (2, 3)]
        for ins in inserts:
            bars = [4] * nbars
            if ins:
                bars.insert(ins[0], ins[1])
            tm = TempoMap(bpm, start, bars)
            dbs = tm.downbeats_s(len(bars))
            pen, rows = 0.0, []
            for h, w in [(x, 3.0) for x in hard] + [(x, 1.0) for x in soft]:
                t = float(h["t"])
                grid = dbs if h.get("want") != "beat" else [tm.time(b) for b in range(int(tm.beat(dur)) + 2)]
                d = min((g - t for g in grid), key=abs)
                cls = _hit_class(d, fps, MF.tier_of(h))
                pen += w * {"on": 0.0, "warn": 0.3}.get(cls, 0.6 if -f <= d < 0 else 1.0 + min(abs(d) / beat, 1.0))
                rows.append({"id": h["id"], "t": t, "grid_s": round(t + d, 4), "d_ms": round(1000 * d, 1), "class": cls,
                             "tier": MF.tier_of(h)})
            pen += 0.25 if ins else 0.0
            cands.append((round(pen, 4), round(bpm, 3), ins, rows, tm))
        bpm = round(bpm + step, 6)
    cands.sort(key=lambda c: (c[0], abs(c[1] - (bpm_lo + bpm_hi) / 2)))
    picked, seen = [], []
    for c in cands:
        if any(abs(c[1] - s) < 1.0 for s in seen):
            continue
        seen.append(c[1])
        picked.append(c)
        if len(picked) >= top:
            break
    maps = [{"score": c[0], "bpm": c[1], "insert": ({"bar": c[2][0], "beats": c[2][1]} if c[2] else None),
             "tempo": c[4].as_dict(), "hits": c[3], "unlanded": [r["id"] for r in c[3] if r["class"] not in ("on", "warn")]}
            for c in picked]
    T = {"made": now_iso(), "fps": fps, "start": start, "duration": dur, "range": [bpm_lo, bpm_hi], "maps": maps,
         "picked": 0, "play_through": sorted(pt),
         "note": "pick with `solve --pick N`; a hit in `unlanded` cannot land — play it through or move the range"}
    jdump(T, os.path.join(job, TEMPO))
    return T


def plan_template(job: str, force: bool = False) -> str:
    """07-edit/music/PLAN.json — the skeleton the agent fills: the key, a section per spotting cue on bar lines, a
    Roman numeral per bar ('?' until written), the parts from the palette, where the motif plays."""
    p = os.path.join(job, PLAN)
    if os.path.isfile(p) and not force:
        raise SystemExit(f"{PLAN} exists — not overwritten (--force)")
    T = jload(os.path.join(job, TEMPO))
    if not T:
        raise SystemExit("no tempo map — `composer.py solve <job>` first")
    tm = TempoMap.from_dict(T["maps"][T.get("picked", 0)]["tempo"])
    bars_total = len(tm.bars)
    end_bar = 0
    while end_bar < bars_total and tm.downbeats_s(end_bar + 1)[-1] < T["duration"] - 1e-6:
        end_bar += 1
    S = jload(os.path.join(job, SPOT)) or {}
    H = MF.load_hits(job)
    kc = ((H.get("track") or {}).get("key_confirmed") or {}).get("key")
    dbs = tm.downbeats_s(bars_total)

    def bar_at(t):
        return max(0, min(range(len(dbs)), key=lambda i: abs(dbs[i] - t)))
    cuts = sorted({0} | {bar_at(float(c["in_s"])) for c in S.get("cues") or [] if isinstance(c.get("in_s"), (int, float))}
                  | {end_bar})
    cuts = [c for c in cuts if c <= end_bar]
    secs = []
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        if b <= a:
            continue
        cue = next((c for c in S.get("cues") or [] if bar_at(float(c.get("in_s") or 0)) == a), {})
        en = {"establish": "low", "underscore": "low", "build": "mid", "hit": "high", "release": "high",
              "button": "mid", "transition": "mid", "silence": "low"}.get(cue.get("function"), "mid")
        secs.append({"name": cue.get("id") or f"S{i + 1}", "bars": [a, b], "energy": en, "chords": ["?"] * (b - a),
                     "parts": ["pad", "sub", "piano"] + (["kick", "hat"] if en != "low" else []), "motif": False,
                     "feeling": cue.get("target_feeling") or ""})
    if secs:
        secs[-1]["motif"] = True
    d = {"status": "TEMPLATE — write the key and a Roman numeral per bar ('I', 'vi', 'IV', 'V7', 'bVII'); choose parts "
                   "from the palette; then `composer.py plan lint` and `realise`",
         "key": kc or "?", "tempo_map": T["maps"][T.get("picked", 0)]["tempo"], "bars": end_bar, "sections": secs,
         "motif": "", "palette_override": None, "humanise": True, "seed": 1, "made": now_iso()}
    return jdump(d, p)


def plan_problems(job: str) -> list:
    P = []
    D = jload(os.path.join(job, PLAN))
    if not D:
        return [f"no {PLAN} — `composer.py plan template <job>`"]
    try:
        tonic, mode = parse_key(D.get("key") or "")
    except ValueError as e:
        return [str(e)]
    exp = 0
    parts = set()
    for s in D.get("sections") or []:
        a, b = (s.get("bars") or [None, None])[:2]
        if a != exp or not isinstance(b, int) or b <= a:
            P.append(f"section {s.get('name')}: bars [{a}, {b}] — sections must run on from bar {exp}")
            exp = b if isinstance(b, int) else exp
            continue
        exp = b
        ch = s.get("chords") or []
        if len(ch) != b - a:
            P.append(f"section {s.get('name')}: {len(ch)} chords for {b - a} bars — one per bar")
        for c in ch:
            try:
                parse_roman(c, tonic, mode)
            except ValueError as e:
                P.append(f"section {s.get('name')}: {e}")
        if s.get("energy") not in ("low", "mid", "high"):
            P.append(f"section {s.get('name')}: energy low, mid or high")
        parts |= set(s.get("parts") or [])
        if s.get("motif") and not os.path.isfile(D.get("motif") or ""):
            P.append(f"section {s.get('name')} plays the motif and the plan names no MOTIF.json (`motif`)")
    if exp != D.get("bars"):
        P.append(f"the sections end at bar {exp}; the film needs {D.get('bars')} bars")
    P += palette_problems(sorted(parts), D.get("palette_override"))
    return P


RANGES = {"pad": (48, 84), "sub": (28, 52), "piano": (36, 96), "bell": (60, 100), "pluck": (52, 96), "arp": (52, 96),
          "lead": (60, 91), "texture": (36, 84)}
PERC = ("kick", "snare", "hat", "impact")


def realise(job: str) -> dict:
    """The plan → notes. Pads voiced by the nearest move (and never in parallel fifths or octaves with the bass),
    the bass on the roots, piano and arps from the chord tones, drums by energy, an impact on every hard hit, a
    beat of silence before a stop-down, the motif where the plan says — then the validators. Refused on any
    violation; nothing renders until it passes."""
    Pp = plan_problems(job)
    if Pp:
        raise SystemExit("the plan does not lint:\n  - " + "\n  - ".join(Pp))
    D = jload(os.path.join(job, PLAN))
    T = jload(os.path.join(job, TEMPO))
    H = MF.load_hits(job)
    tm = TempoMap.from_dict(D["tempo_map"])
    tonic, mode = parse_key(D["key"])
    rng = random.Random(int(D.get("seed") or 1))
    starts = tm.bar_starts(len(tm.bars))
    parts: dict = {}
    chords_per_bar = []
    for s in D["sections"]:
        for k, c in enumerate(s["chords"]):
            chords_per_bar.append((s, s["bars"][0] + k, parse_roman(c, tonic, mode)))
    prev_v, prev_bass = None, None
    vel = {"low": 58, "mid": 72, "high": 86}
    for s, bi, ch in chords_per_bar:
        b0, nb = starts[bi], tm.bars[bi] if bi < len(tm.bars) else 4
        en = s["energy"]
        ps = set(s.get("parts") or [])
        if ch["root"] is None:
            continue
        bass = 36 + ((ch["root"] - 36) % 12)
        if "pad" in ps:
            cands = []
            for lo in (50, 52, 55):
                cands.append(nearest_voicing(ch["pcs"], prev_v, lo, lo + 26, 4))
            def par(v):
                if prev_v is None or prev_bass is None:
                    return False
                i1, i2 = (prev_v[-1] - prev_bass) % 12, (v[-1] - bass) % 12
                return i1 == i2 and i1 in (0, 7) and (v[-1] - prev_v[-1]) * (bass - prev_bass) > 0
            v = next((c for c in cands if not par(c)), cands[0])
            if par(v):
                v = v[:-1] + [v[-2] + 12 if v[-2] + 12 <= RANGES["pad"][1] else v[-1]]
            for p in v:
                parts.setdefault("pad", []).append({"beat": b0, "dur": nb * 0.98, "pitch": p, "vel": vel[en] - 6})
            prev_v = v
        if "sub" in ps:
            parts.setdefault("sub", []).append({"beat": b0, "dur": (nb / 2 if en != "low" and nb >= 4 else nb) * 0.95,
                                                "pitch": bass, "vel": vel[en]})
            if en != "low" and nb >= 4:
                parts["sub"].append({"beat": b0 + nb / 2, "dur": nb / 2 * 0.9, "pitch": bass, "vel": vel[en] - 8})
        prev_bass = bass
        tones = sorted({60 + ((p - 60) % 12) for p in ch["pcs"]})
        if "piano" in ps:
            if en == "low":
                for p in tones[:3]:
                    parts.setdefault("piano", []).append({"beat": b0, "dur": nb * 0.9, "pitch": p, "vel": vel[en]})
            else:
                pat = tones + [tones[0] + 12] if (bi // 2) % 2 == 0 else [tones[0] + 12] + tones[::-1]
                for k in range(int(nb * 2)):
                    parts.setdefault("piano", []).append({"beat": b0 + k * 0.5, "dur": 0.45, "pitch": pat[k % len(pat)],
                                                          "vel": vel[en] - 4 + (6 if k % 4 == 0 else 0)})
        for arp in ("arp", "pluck"):
            if arp in ps:
                stepb = 0.25 if en == "high" else 0.5
                seq = [t + 12 for t in tones] + [tones[1] + 12]
                for k in range(int(nb / stepb)):
                    parts.setdefault(arp, []).append({"beat": b0 + k * stepb, "dur": stepb * 0.8,
                                                      "pitch": seq[(k + bi) % len(seq)], "vel": vel[en] - 10})
        if "bell" in ps:
            parts.setdefault("bell", []).append({"beat": b0, "dur": nb * 0.5, "pitch": tones[-1] + 12, "vel": vel[en] - 8})
        if "texture" in ps:
            parts.setdefault("texture", []).append({"beat": b0, "dur": nb, "pitch": 48 + ch["root"], "vel": 50})
        if "kick" in ps:
            hits_ = [0, 2] if en == "mid" else (list(range(int(nb))) if en == "high" else [0])
            for k in hits_:
                if k < nb:
                    parts.setdefault("kick", []).append({"beat": b0 + k, "dur": 0.4, "pitch": DRUM_NOTES["kick"], "vel": vel[en] + 10})
        if "snare" in ps and en == "high":
            for k in (1, 3):
                if k < nb:
                    parts.setdefault("snare", []).append({"beat": b0 + k, "dur": 0.3, "pitch": DRUM_NOTES["snare"], "vel": vel[en]})
        if "hat" in ps:
            stepb = {"low": 2.0, "mid": 0.5, "high": 0.25}[en]
            for k in range(int(nb / stepb)):
                parts.setdefault("hat", []).append({"beat": b0 + k * stepb, "dur": 0.1, "pitch": DRUM_NOTES["hat"],
                                                    "vel": vel[en] - 20 + (8 if k % 2 == 0 else 0)})
    # the motif where the plan puts it, transposed by degree into the plan's key
    Mo = jload(D.get("motif") or "") if D.get("motif") else None
    if Mo:
        for s in D["sections"]:
            if s.get("motif"):
                b0 = starts[s["bars"][0]]
                for n in transpose_diatonic(Mo["notes"], Mo["key"], D["key"]):
                    parts.setdefault(Mo.get("timbre") or "bell", []).append(
                        {"beat": b0 + float(n["beat"]), "dur": float(n["dur"]), "pitch": int(n["pitch"]), "vel": int(n.get("vel", 90)), "motif": True})
    # an impact on every hard hit, at its grid time
    mp = T["maps"][T.get("picked", 0)] if T else {"hits": []}
    for r in mp.get("hits") or []:
        if r.get("tier") == "hard":
            parts.setdefault("impact", []).append({"beat": round(tm.beat(r["grid_s"]), 4), "dur": 1.0, "pitch": 49, "vel": 118,
                                                   "hit": r["id"]})
    # a beat of accented silence before each stop-down
    for h in H.get("hits") or []:
        if h.get("want") == "stop_down" and isinstance(h.get("t"), (int, float)):
            hb = tm.beat(float(h["t"]))
            for k in list(parts):
                kept = []
                for n in parts[k]:
                    if n["beat"] < hb - 1 and n["beat"] + n["dur"] > hb - 1:
                        n = dict(n, dur=max(0.05, hb - 1 - n["beat"]))
                    if hb - 1 <= n["beat"] < hb:
                        continue
                    kept.append(n)
                parts[k] = kept
    total_beats = sum(tm.bars[:D["bars"]])
    problems = validate(parts, tonic, mode, chords_per_bar, starts, total_beats)   # the notes as written, before humanising
    if D.get("humanise", True):
        for k, ns in parts.items():
            for n in ns:
                if k == "impact" or n.get("motif"):
                    continue
                n["vel"] = max(20, min(127, int(n["vel"]) + rng.randint(-6, 6)))
                n["beat"] = round(n["beat"] + rng.uniform(-0.012, 0.012) / tm.beat_s if n["beat"] > 0 else n["beat"], 4)
    sc = {"made": now_iso(), "key": key_name(tonic, mode), "tempo_map": tm.as_dict(), "bars": D["bars"],
          "parts": {k: sorted(v, key=lambda n: n["beat"]) for k, v in parts.items()},
          "validators": {"passed": not problems, "problems": problems, "checked": ["key", "range", "bar length",
                                                                                  "parallels", "copy-paste repeats"]}}
    jdump(sc, os.path.join(job, SCORE))
    write_midi(os.path.join(job, "07-edit", "music", "SCORE.mid"), sc["parts"], [(0, tm.bpm)], tm.midi_meters())
    if problems:
        raise SystemExit("the score does not validate:\n  - " + "\n  - ".join(problems[:20]))
    return sc


def validate(parts: dict, tonic: int, mode: str, chords_per_bar: list, starts: list, total_beats: float) -> list:
    P = []
    sc = scale_pcs(tonic, mode)
    bar_of = lambda b: max(0, max(i for i, s in enumerate(starts[:len(chords_per_bar)] or [0]) if s <= b + 1e-6))
    for k, ns in parts.items():
        if k in PERC:
            continue
        lo, hi = RANGES.get(k.split("_")[0], (21, 108))
        for n in ns:
            p = int(n["pitch"])
            if not lo <= p <= hi:
                P.append(f"{k}: note {p} at beat {n['beat']:.2f} outside {lo}–{hi} (range)")
            bi = bar_of(n["beat"])
            ch = chords_per_bar[bi][2] if bi < len(chords_per_bar) else {"pcs": []}
            if p % 12 not in sc and p % 12 not in set(ch.get("pcs") or []):
                P.append(f"{k}: {PCS[p % 12]} at beat {n['beat']:.2f} is outside the key and the bar's chord (key)")
    for k, ns in parts.items():
        for n in ns:
            if n["beat"] > total_beats + 1e-6 or n["beat"] + n["dur"] > total_beats + 4.0:
                P.append(f"{k}: a note at beat {n['beat']:.2f} runs past the music's end ({total_beats:g} beats) (bar length)")
                break
    # parallels: the pad's top voice against the bass, chord to chord
    pad = parts.get("pad") or []
    sub = parts.get("sub") or []
    tops, basses = {}, {}
    for n in pad:
        b = round(n["beat"], 2)
        tops[b] = max(tops.get(b, 0), int(n["pitch"]))
    for n in sub:
        basses.setdefault(round(n["beat"], 2), int(n["pitch"]))
    common = sorted(set(tops) & set(basses))
    for a, b in zip(common, common[1:]):
        i1, i2 = (tops[a] - basses[a]) % 12, (tops[b] - basses[b]) % 12
        if i1 == i2 and i1 in (0, 7) and (tops[b] - tops[a]) * (basses[b] - basses[a]) > 0:
            P.append(f"pad over bass: parallel {'octaves' if i1 == 0 else 'fifths'} from beat {a:g} to {b:g} (parallels)")
    # verbatim repeats: the same bar content in a melodic part more than four bars running
    for k, ns in parts.items():
        if k in PERC or k in ("pad", "sub", "texture"):
            continue
        sig = {}
        for n in ns:
            bi = bar_of(n["beat"])
            sig.setdefault(bi, []).append((round(n["beat"] - starts[bi], 2), int(n["pitch"])))
        run, last = 1, None
        for bi in sorted(sig):
            cur = tuple(sorted(sig[bi]))
            run = run + 1 if cur == last else 1
            last = cur
            if run > 4:
                P.append(f"{k}: the same bar {run} times running from bar {bi - run + 1} (copy-paste repeat)")
                break
    return P


def render_score(job: str, backend: str = "numpy", instrument: str = "builtin", part_instruments: dict | None = None) -> dict:
    sc = jload(os.path.join(job, SCORE))
    if not sc:
        raise SystemExit("no score — `composer.py realise <job>` first")
    if not sc["validators"]["passed"]:
        raise SystemExit("the score did not validate — fix the plan and realise again")
    tm = TempoMap.from_dict(sc["tempo_map"])
    lic = [instrument_licence(instrument if backend != "numpy" else "builtin")]
    for v in (part_instruments or {}).values():
        lic.append(instrument_licence(v))
    bad = [x for x in lic if str(x.get("paid_ads")).lower() != "yes"]
    if bad:
        raise SystemExit("refused: " + "; ".join(f"{x.get('file')}: {x.get('why') or x.get('licence') or 'not cleared for paid ads'}" for x in bad))
    pp = palette_problems(list(sc["parts"]), (jload(os.path.join(job, PLAN)) or {}).get("palette_override"))
    if pp:
        raise SystemExit("refused: " + "; ".join(pp))
    length = tm.time(sum(tm.bars[:sc["bars"]])) + 2.0
    t0 = time.time()
    if backend == "numpy":
        stems_ = render_builtin({k: notes_to_seconds(v, tm) for k, v in sc["parts"].items()}, length)
    else:
        stems_ = render_external(backend, sc["parts"], [(0, tm.bpm)], tm.midi_meters(), length, instrument, part_instruments)
        if tm.start > 0:                                     # the MIDI starts at beat 0; the film's music starts later
            np = _np()
            lead = int(round(tm.start * SR))
            stems_ = {k: np.concatenate([np.zeros((lead, 2), np.float32), v])[:len(v)] for k, v in stems_.items()}
    secs = round(time.time() - t0, 2)
    name = os.path.basename(os.path.abspath(job)) + ".score"
    out = write_stems(stems_, os.path.join(job, COMPOSE_DIR), name)
    rec = {"kind": "composed_score", "route": "route1", "tool": "composer.py render", "version": "2.40.0",
           "made": now_iso(), "backend": backend, "render_seconds": secs, "instruments": lic,
           "palette": sorted(sc["parts"]), "key": sc["key"], "tempo_map": sc["tempo_map"],
           "plan": MF.rel(job, os.path.join(job, PLAN)), "plan_sha256": MF.sha256_file(os.path.join(job, PLAN)),
           "validators": sc["validators"], "midi": "07-edit/music/SCORE.mid",
           "human_contribution": "", "sha256": MF.sha256_file(out["mix"])}
    jdump(rec, out["mix"] + ".compose.json")
    jdump({"source": "composed:route1", "paid_ads": "yes",
           "licence": "own composition (composer.py, route 1); instruments: " + "; ".join(
               f"{x.get('name') or x.get('id')} ({x.get('licence')})" for x in lic)}, out["mix"] + ".licence.json")
    for part, p in out["stems"].items():
        jdump({"kind": "stem", "sources": [{"file": MF.rel(job, out["mix"]), "role": "music"}], "part": part}, p + ".conform.json")
    return {"file": MF.rel(job, out["mix"]), "stems": {k: MF.rel(job, v) for k, v in out["stems"].items()},
            "render_seconds": secs, "gain_db": out["gain_db"]}


# ── gate A: the automatic outlier check ──────────────────────────────────────────────────────────────────
def features(path: str) -> dict:
    np = _np()
    x = MF.decode(path, SR, 2)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS", r)
    L, R = x[:, 0].astype(np.float64), x[:, 1].astype(np.float64)
    st = float(np.mean((L ** 2 + R ** 2) / 2)) + 1e-12
    mono = float(np.mean(((L + R) / 2) ** 2)) + 1e-12
    m = x.mean(1)[::2].astype(np.float64)
    sr2 = SR // 2
    n, hop = 2048, 1024
    fr = [m[i:i + n] * np.hanning(n) for i in range(0, max(0, len(m) - n), hop)]
    if not fr:
        return {"file": path, "lufs": None}
    S = np.abs(np.fft.rfft(np.array(fr), axis=1))
    freqs = np.fft.rfftfreq(n, 1 / sr2)
    hb = S[:, freqs >= 8000]
    flux = float(np.mean(np.maximum(0, np.diff(hb, axis=0)))) / (float(np.mean(hb)) + 1e-9) if len(hb) > 1 else 0.0
    edges = np.geomspace(60, 11000, 33)
    bands = np.stack([S[:, (freqs >= a) & (freqs < b)].sum(1) for a, b in zip(edges, edges[1:])], 1)
    lb = np.log1p(bands)
    lb = lb / (np.linalg.norm(lb, axis=1, keepdims=True) + 1e-9)
    fps_ = sr2 / hop
    gap = int(4 * fps_)
    run_need = int(2 * fps_)
    rep = 0
    if len(lb) > gap + run_need:
        sim = lb @ lb.T
        verb = np.zeros(len(lb), bool)
        k = np.ones(run_need)
        for lag in range(gap, len(lb) - run_need):
            d = (np.diagonal(sim, lag) > 0.9995).astype(float)
            full = np.convolve(d, k, mode="valid") >= run_need - 1e-9      # a run of run_need frames starts here
            if full.any():
                for i in np.nonzero(full)[0]:
                    verb[i + lag:i + lag + run_need] = True
        rep = float(verb.mean())
    return {"file": path, "lufs": float(lufs[-1]) if lufs else None, "true_peak": float(tp[-1]) if tp and tp[-1] != "-inf" else None,
            "mono_loss_db": round(10 * math.log10(mono / st), 2), "hf_flux": round(flux, 4), "verbatim_repeat_share": round(rep, 3)}


def gate_a(path: str, refs: str, min_refs: int = 5) -> dict:
    """B13 gate A: a candidate is flagged where it falls outside the 5th–95th percentile of the reference tracks
    (the owner's library cues for the mood). With fewer than 20 references the percentiles are wide: said so."""
    np = _np()
    files = sorted(f for f in glob.glob(os.path.join(refs, "**", "*"), recursive=True)
                   if f.lower().endswith((".wav", ".mp3", ".flac", ".aif", ".aiff", ".m4a")))
    if len(files) < min_refs:
        raise SystemExit(f"{len(files)} reference track(s) in {refs} — gate A needs {min_refs} at least (20–50 per mood "
                         f"is the research's number)")
    cache = os.path.join(cine_home(), "gate-a-cache")
    os.makedirs(cache, exist_ok=True)
    R = []
    for f in files:
        cp = os.path.join(cache, MF.sha256_file(f) + ".json")
        r = jload(cp)
        if not r:
            r = features(f)
            jdump(r, cp)
        R.append(r)
    c = features(path)
    flags, rows = [], []
    for k in ("lufs", "true_peak", "mono_loss_db", "hf_flux", "verbatim_repeat_share"):
        vals = [r[k] for r in R if isinstance(r.get(k), (int, float))]
        if len(vals) < min_refs or c.get(k) is None:
            continue
        lo, hi = float(np.percentile(vals, 5)), float(np.percentile(vals, 95))
        out = not (lo <= c[k] <= hi)
        rows.append({"measure": k, "value": c[k], "p5": round(lo, 3), "p95": round(hi, 3), "outside": out})
        if out:
            flags.append(f"{k} {c[k]} outside the references' 5–95th percentile [{lo:.3f}, {hi:.3f}]")
    if (c.get("true_peak") or -99) > -1.0:
        flags.append(f"true peak {c['true_peak']} dBFS — above −1 dBTP")
    rep = {"made": now_iso(), "file": path, "refs": refs, "n_refs": len(files), "rows": rows, "flags": flags,
           "note": None if len(files) >= 20 else f"only {len(files)} references — the percentiles are wide (20–50 per mood)"}
    jdump(rep, path + ".gate-a.json")
    return rep


# ── package D: generated music — the whitelist, the record, AI vocals, the blind bake-off ─────────────────
def generators() -> dict:
    return jload(GENERATORS, {}) or {}


def vendor_row(vendor: str) -> tuple[str, dict]:
    v = re.sub(r"[^a-z0-9]+", "_", (vendor or "").lower()).strip("_")
    rows = generators().get("vendors") or {}
    for k, r in rows.items():
        if v == k or v in (r.get("aliases") or []):
            return k, r
    return v, {}


def prompt_problems(prompt: str) -> list:
    """Never artist names, titles or existing lyrics in a prompt (the GEMA outputs came from title and lyric
    prompts). Patterns and the owner's denylist live in assets/music-generators.json."""
    G = generators().get("prompt_rules") or {}
    P = []
    for pat in G.get("patterns") or []:
        if re.search(pat, prompt or "", re.I):
            P.append(f"the prompt matches {pat!r} — describe the music (tempo, instruments, mood), never a work or an artist")
    for q in re.findall(r"[\"“”']([^\"“”']{3,})[\"“”']", prompt or ""):
        if len(q.split()) >= 2:
            P.append(f"the prompt quotes {q!r} — a quoted phrase reads as a title or a lyric")
    for name in G.get("artists_denylist") or []:
        if re.search(r"\b" + re.escape(name) + r"\b", prompt or "", re.I):
            P.append(f"the prompt names {name!r}")
    return P


def generated_record(job: str, file: str, vendor: str, plan: str, prompt: str, terms_url: str, use: str,
                     terms_file: str | None = None, model: str = "", stems: str = "none", vocals: str = "none",
                     generated_at: str | None = None, human_edits: str = "") -> dict:
    """C7-D as the owner amended it (2026-10-27): consent first, a named whitelist, the terms snapshotted at
    generation. Temp use is allowed from any vendor not excluded outright; shipping only from the whitelist."""
    fa = MF.absj(job, file)
    if not os.path.isfile(fa):
        raise SystemExit(f"{file}: not on disk")
    if use not in ("temp", "ship"):
        raise SystemExit("--use temp or ship")
    key, row = vendor_row(vendor)
    st = row.get("status") or "unknown"
    P = []
    if st in ("excluded_always", "unknown"):
        P.append(f"{vendor}: {row.get('why') or 'not in assets/music-generators.json — read its terms and add a row first'}")
    if use == "ship":
        if st != "whitelist":
            P.append(f"{vendor} is {st} for shipping — {row.get('why') or 'only whitelisted vendors ship'}")
        if (plan or "").lower() in [p.lower() for p in row.get("plans_blocked") or []]:
            P.append(f"{vendor} {plan}: this plan does not allow commercial use")
        if not terms_file or not os.path.isfile(terms_file):
            P.append("--terms-file: save the governing terms page as it reads today (text or PDF) — vendor terms changed "
                     "about once a quarter through 2025–26")
        if stems == "separated":
            P.append("stems separated from generated stereo carry bleed and a watery top — native stems only (K15)")
    if not terms_url:
        P.append("--terms-url: the terms page that governs this output")
    P += prompt_problems(prompt)
    when = parse_date(generated_at) or dt.datetime.fromtimestamp(os.path.getmtime(fa))
    c = consent_before(job, "generated", when)
    if not c:
        P.append("no written client consent to generated music dated before this generation — record it first "
                 "(`composer.py consent … --scope generated`; IPA/ISBA Principle 11: before inclusion, not at delivery)")
    if vocals == "ai" and not consent_before(job, "ai_vocals", when):
        P.append("AI vocals: no client consent to AI vocals (--scope ai_vocals) dated before the generation")
    if P:
        raise SystemExit("refused:\n  - " + "\n  - ".join(P))
    B = jload(os.path.join(job, BRIEF)) or {}
    region = ",".join(sorted({t.upper() for m in B.get("media_plan") or [] for t in m.get("territories") or []}))
    rec = {"kind": "generated_music", "route": "route2", "vendor": key, "status": st, "plan": plan, "model": model,
           "prompt": prompt, "use": use, "stems": stems, "vocals": vocals, "generated_at": when.isoformat(timespec="seconds"),
           "terms": {"url": terms_url, "file": os.path.abspath(terms_file) if terms_file else None,
                     "sha256": MF.sha256_file(terms_file) if terms_file and os.path.isfile(terms_file) else None,
                     "snapshot": now_iso(), "registry_date": row.get("terms_date")},
           "consent": c, "human_edits": human_edits, "indemnity": "none (no self-serve music generator indemnifies; "
           "research 2026-10-27)", "sha256": MF.sha256_file(fa), "recorded": now_iso()}
    jdump(rec, fa + ".gen.json")
    jdump({"source": f"ai:{key}", "paid_ads": "yes" if use == "ship" else "no",
           "licence": f"{key} {plan} terms (snapshot {rec['terms']['snapshot'][:10]}; no indemnity, copyright may not vest)",
           "tool": key, "version": model or "unspecified", "plan": plan, "region": region}, fa + ".licence.json")
    return rec


def vocals_record(job: str, file: str, lyrics_file: str, lyrics_by: str, voice: str, disclosure: str,
                  no_soundalike: bool) -> dict:
    """AI vocals, case by case (2026-10-27: "AI vocals - needed sometimes"): original lyrics by a named
    person, a voice described without any artist, no soundalike, the disclosure written, the client's consent
    to AI vocals before the generation."""
    fa = MF.absj(job, file)
    g = jload(fa + ".gen.json")
    P = []
    if not g:
        P.append(f"{file}: no generation record — `composer.py generated record` first")
    elif g.get("vocals") != "ai":
        P.append(f"{file}: its generation record says vocals {g.get('vocals')!r} — record it with --vocals ai")
    if not lyrics_file or not os.path.isfile(lyrics_file) or len(open(lyrics_file, encoding="utf-8").read().split()) < 4:
        P.append("--lyrics-file: the lyrics as written, by a person (never an existing song's lyrics)")
    if not (lyrics_by or "").strip():
        P.append("--lyrics-by: who wrote the lyrics (the owner, the client's writer)")
    P += [x.replace("prompt", "voice description") for x in prompt_problems(voice)]
    if not no_soundalike:
        P.append("--no-soundalike: state that the voice imitates no real singer (Article 50(4), personality rights, and "
                 "ElevenLabs bars mimicking a recording artist)")
    if not (disclosure or "").strip():
        P.append("--disclosure: how the AI vocal is disclosed (platform toggles; in the EU a realistic synthetic voice is "
                 "disclosed under Article 50(4))")
    if g and not consent_before(job, "ai_vocals", parse_date(g.get("generated_at"))):
        P.append("no client consent to AI vocals dated before the generation (--scope ai_vocals)")
    if P:
        raise SystemExit("refused:\n  - " + "\n  - ".join(P))
    rec = {"kind": "ai_vocals", "file": file, "lyrics_file": os.path.abspath(lyrics_file),
           "lyrics_sha256": MF.sha256_file(lyrics_file), "lyrics_by": lyrics_by, "voice": voice,
           "no_soundalike": True, "disclosure": disclosure, "recorded": now_iso()}
    jdump(rec, fa + ".vocals.json")
    return rec


# the blind bake-off (B13 gate B; K7: before a route, palette or vendor is first used, then each quarter)
def _binom_cdf(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n


def _loudness(path: str) -> float:
    f = features(path)
    return f.get("lufs") if f.get("lufs") is not None else -23.0


def bakeoff_init(job: str, library: str, candidate: str, subject: str, vo: str | None = None, picture: str | None = None,
                 excerpt_s: float = 6.0, seed: int | None = None) -> str:
    """Level-matched excerpts of the library cue and the candidate, under the VO (and the picture, when given), each
    excerpt's pair labelled a/b at random, plus one hidden duplicate with the labels swapped. Listeners pick per
    excerpt; trials pool across listeners (3+ who are not the composer, 30+ trials)."""
    np = _np()
    if not re.match(r"^(vendor:[a-z0-9_]+|route1:score|motif:.+)$", subject or ""):
        raise SystemExit("--subject vendor:<name>, route1:score or motif:<brand>")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = os.path.join(job, "09-qa", "music", f"bakeoff-{stamp}")
    os.makedirs(d, exist_ok=True)
    A = MF.decode(MF.absj(job, library), SR, 2)
    Bc = MF.decode(MF.absj(job, candidate), SR, 2)
    n = min(len(A), len(Bc))
    A, Bc = A[:n], Bc[:n]
    ga = 10 ** ((-16.0 - _loudness(MF.absj(job, library))) / 20)
    gb = 10 ** ((-16.0 - _loudness(MF.absj(job, candidate))) / 20)
    A, Bc = A * ga, Bc * gb
    if vo:
        V = MF.decode(MF.absj(job, vo), SR, 2)[:n]
        A[:len(V)] += V
        Bc[:len(V)] += V
    rng = random.Random(seed if seed is not None else stamp)
    L = int(excerpt_s * SR)
    starts = list(range(0, max(1, n - L + 1), max(1, L // 2))) or [0]      # half-overlapping excerpts
    trials, key = [], {}
    for i, s0 in enumerate(starts, start=1):
        flip = rng.random() < 0.5
        trials.append({"trial": i, "start_s": round(s0 / SR, 2), "dur_s": round(min(L, n - s0) / SR, 2)})
        key[str(i)] = {"a": "candidate" if flip else "library", "b": "library" if flip else "candidate"}
    dup = rng.choice(trials)
    j = len(trials) + 1
    trials.append({"trial": j, "start_s": dup["start_s"], "dur_s": dup["dur_s"], "duplicate_of": None})
    key[str(j)] = {"a": key[str(dup["trial"])]["b"], "b": key[str(dup["trial"])]["a"], "duplicate_of": dup["trial"]}
    for t in trials:
        s0, s1 = int(t["start_s"] * SR), int(t["start_s"] * SR) + int(t["dur_s"] * SR)
        for lab in ("a", "b"):
            src = Bc if key[str(t["trial"])][lab] == "candidate" else A
            y = src[s0:s1].copy()
            f_ = min(int(0.02 * SR), len(y) // 2)
            if f_:
                y[:f_] *= np.linspace(0, 1, f_, dtype=np.float32)[:, None]
                y[-f_:] *= np.linspace(1, 0, f_, dtype=np.float32)[:, None]
            w = os.path.join(d, f"t{t['trial']:02d}-{lab}.wav")
            MF.encode(np.clip(y, -1, 1), SR, w)
            if picture:
                mp4 = w[:-4] + ".mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t["start_s"]), "-t", str(t["dur_s"]), "-i",
                                MF.absj(job, picture), "-i", w, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264",
                                "-preset", "veryfast", "-c:a", "aac", "-shortest", mp4], check=True, stdin=subprocess.DEVNULL)
    kp = jdump(key, os.path.join(d, "KEY.json"))
    jdump({"subject": subject, "made": now_iso(), "library": library, "candidate": candidate, "vo": vo, "picture": picture,
           "trials": [{k: v for k, v in t.items() if k != "duplicate_of"} for t in trials], "key_sha256": MF.sha256_file(kp),
           "sessions": [], "rule": "listen on a phone speaker, under the picture and VO; for each trial pick the one that "
           "serves the film better; do not open KEY.json"}, os.path.join(d, "BAKEOFF.json"))
    return d


def bakeoff_record(d: str, listener: str, role: str, picks: str) -> dict:
    Bk = jload(os.path.join(d, "BAKEOFF.json"))
    if not Bk:
        raise SystemExit(f"{d}: no BAKEOFF.json")
    if role not in ("other", "composer"):
        raise SystemExit("--role other or composer (the composer's own picks are kept and never counted)")
    pk = {}
    for x in re.split(r"[,\s]+", picks.strip()):
        if not x:
            continue
        m = re.match(r"^(\d+):([ab])$", x)
        if not m:
            raise SystemExit(f"--picks: {x!r} — write 1:a,2:b,…")
        pk[m.group(1)] = m.group(2)
    want = {str(t["trial"]) for t in Bk["trials"]}
    if set(pk) != want:
        raise SystemExit(f"--picks: one pick per trial ({len(want)}): missing {sorted(want - set(pk))}")
    s = {"listener": listener, "role": role, "picks": pk, "recorded": now_iso()}
    Bk["sessions"].append(s)
    jdump(Bk, os.path.join(d, "BAKEOFF.json"))
    return s


def bakeoff_result(d: str) -> dict:
    Bk = jload(os.path.join(d, "BAKEOFF.json"))
    key = jload(os.path.join(d, "KEY.json"))
    if MF.sha256_file(os.path.join(d, "KEY.json")) != Bk.get("key_sha256"):
        raise SystemExit("KEY.json changed after the bake-off was set up — the result would not be blind")
    n = w = 0
    used, dropped, listeners = [], [], set()
    for s in Bk["sessions"]:
        if s["role"] != "other":
            dropped.append(f"{s['listener']}: the composer's own picks are not counted")
            continue
        dup = next((t for t, k in key.items() if k.get("duplicate_of")), None)
        if dup:
            orig = str(key[dup]["duplicate_of"])
            a = key[orig][s["picks"][orig]]
            b = key[dup][s["picks"][dup]]
            if a != b:
                dropped.append(f"{s['listener']}: picked differently on the hidden duplicate — session not counted")
                continue
        listeners.add(s["listener"])
        for t, lab in s["picks"].items():
            if key[t].get("duplicate_of"):
                continue
            n += 1
            w += key[t][lab] == "candidate"
        used.append(s["listener"])
    res = {"subject": Bk["subject"], "trials": n, "candidate_wins": w, "listeners": len(listeners), "dropped": dropped}
    if n < 30 or len(listeners) < 3:
        res["result"] = "incomplete"
        res["why"] = f"{n} trials from {len(listeners)} listener(s) — 30+ pooled trials from 3+ listeners who are not the composer"
    else:
        p_worse = _binom_cdf(w, n)
        p_better = 1 - _binom_cdf(w - 1, n)
        res.update({"p_worse": round(p_worse, 4), "p_better": round(p_better, 4)})
        if p_worse <= 0.05:
            res["result"] = "fail"
            res["why"] = f"the candidate lost: {w}/{n} wins is significantly worse than the library cue (p = {p_worse:.3f})"
        else:
            res["result"] = "prefer" if p_better <= 0.05 else "pass"
            res["why"] = (f"{w}/{n} wins — " + ("preferred over the library cue" if res["result"] == "prefer"
                          else "not worse than the library cue"))
    Bk["result"] = dict(res, decided=now_iso())
    jdump(Bk, os.path.join(d, "BAKEOFF.json"))
    if res["result"] in ("pass", "prefer"):
        reg = os.path.join(cine_home(), "music-bakeoffs.json")
        R = jload(reg, []) or []
        R.append({"subject": Bk["subject"], "date": now_iso(), "trials": n, "wins": w, "result": res["result"],
                  "dir": os.path.abspath(d)})
        jdump(R, reg)
    return res


def bakeoff_passed(subject: str, days: int = BAKEOFF_DAYS) -> dict | None:
    R = jload(os.path.join(cine_home(), "music-bakeoffs.json"), []) or []
    ok = [r for r in R if r.get("subject") == subject and r.get("result") in ("pass", "prefer")
          and (dt.datetime.now() - (parse_date(r.get("date")) or dt.datetime(1970, 1, 1))).days <= days]
    return ok[-1] if ok else None


# ── the check `approve export` runs (C5: rules refuse, measures warn) ────────────────────────────────────
def _listing_sha(job: str) -> str:
    import mix_qa as MQ  # noqa: E402
    return hashlib.sha256("\n".join(sorted(MQ.audio_files(job))).encode()).hexdigest()


def layer_offsets(job: str, L: dict, H: dict) -> list:
    """Each hard hit's impact onset measured on the rendered layer (the transient peak), in ms from its frame."""
    np = _np()
    x = MF.decode(MF.absj(job, L["file"]), SR, 1)
    t, env, _, _, _ = MF.spectral(np.ascontiguousarray(x[::2]), SR // 2)
    fps = float(H.get("fps") or 24)
    out = []
    for n in (L.get("parts") or {}).get("impact") or []:
        h = next((h for h in H.get("hits") or [] if h.get("id") == n.get("hit")), None)
        if not h:
            continue
        T = float(h["t"])
        win = [(float(t[i]), float(env[i])) for i in range(len(t)) if T - 0.06 <= t[i] <= T + 0.12]
        if not win:
            continue
        tp = max(win, key=lambda z: z[1])[0]
        d = tp - T
        out.append({"hit": h["id"], "offset_ms": round(1000 * d, 1), "class": MF.classify(d, fps, MF.tier_of(h))})
    return out


def check_job(job: str) -> tuple[list, list]:
    P, W = [], []
    comp = sorted(glob.glob(os.path.join(job, "06-music", "**", "*.compose.json"), recursive=True))
    gen = sorted(glob.glob(os.path.join(job, "06-music", "**", "*.gen.json"), recursive=True))
    made_here = bool(comp or gen)
    if not made_here and not os.path.isfile(os.path.join(job, BRIEF)):
        return P, ["no composer's brief — a library-only film; `composer.py brief init` plans the music (package A)"]
    bp, bw = brief_problems(job)
    sp, sw = spot_problems(job)
    (P if made_here else W).extend([f"brief: {x}" for x in bp] + [f"spotting: {x}" for x in sp])
    W += [f"brief: {x}" for x in bw] + [f"spotting: {x}" for x in sw]
    H = jload(os.path.join(job, MF.HITS)) or {}
    import mix_qa as MQ  # noqa: E402
    listed = {r.get("file", "") for r in MQ.read_manifest(job)}
    for cj in comp:
        R = jload(cj) or {}
        f = cj[:-len(".compose.json")]
        rel_ = MF.rel(job, f)
        if not os.path.isfile(f):
            P.append(f"{rel_}: its composition record has no audio")
            continue
        if MF.sha256_file(f) != R.get("sha256"):
            P.append(f"{rel_}: changed after it was rendered — render it again (the record is about other bytes)")
        for lic in R.get("instruments") or []:
            if str(lic.get("paid_ads")).lower() != "yes":
                P.append(f"{rel_}: instrument {lic.get('file') or lic.get('id')} is not cleared for paid ads")
        P += [f"{rel_}: {x}" for x in palette_problems(R.get("palette") or [], (jload(os.path.join(job, PLAN)) or {}).get("palette_override"))]
        if R.get("kind") == "composed_layer":
            kc = (H.get("track") or {}).get("key_confirmed") or {}
            if not kc.get("key") or kc.get("key") != (R.get("key") or {}).get("key"):
                P.append(f"{rel_}: the bed's key is not confirmed by ear, or changed since the layer was made (K9)")
            mo = R.get("motif") or {}
            if not mo.get("adopted_by") or not (R.get("human_contribution") or "").strip():
                P.append(f"{rel_}: the motif carries no record of the owner's edit (K2: the skill drafts, the owner edits)")
            if not (mo.get("melody_check") or {}).get("checked"):
                P.append(f"{rel_}: the motif was never checked against existing melodies")
            brand = mo.get("brand") or ""
            if brand and not bakeoff_passed(f"motif:{brand}", 10 ** 5):
                W.append(f"{rel_}: the {brand} motif has not had its blind test (K7: a hero motif is blind-tested before first use)")
            L = jload(os.path.join(job, LAYER)) or {}
            if L.get("sha256") == R.get("sha256"):
                for o in layer_offsets(job, L, H):
                    if o["class"] != "on":
                        W.append(f"{rel_}: hit {o['hit']} impact at {o['offset_ms']:+.0f} ms ({o['class']}; tiered window, never early)")
            H2 = dict(H, fx=list(H.get("fx") or []) + [{"kind": "impact", "t": n["t"]} for n in (L.get("parts") or {}).get("impact") or []])
            W += [f"accent budget: {x}" for x in MF.accent_budget(job, H2) if "impact" in x]
        if R.get("kind") == "composed_score":
            if not (R.get("validators") or {}).get("passed"):
                P.append(f"{rel_}: the score did not pass its validators")
            pp = os.path.join(job, PLAN)
            if os.path.isfile(pp) and MF.sha256_file(pp) != R.get("plan_sha256"):
                P.append(f"{rel_}: the plan changed after the score was rendered — realise and render again")
            if not bakeoff_passed("route1:score"):
                P.append(f"{rel_}: no blind bake-off of route-1 scores against library cues in the last {BAKEOFF_DAYS} days "
                         f"(K7) — `composer.py bakeoff init … --subject route1:score`")
            if not (R.get("human_contribution") or "").strip():
                W.append(f"{rel_}: the score's authorship rests on the agent's plan — record the person's edits "
                         f"(human_contribution) if they made any; copyright may not vest without them")
    for gj in gen:
        R = jload(gj) or {}
        f = gj[:-len(".gen.json")]
        rel_ = MF.rel(job, f)
        if not os.path.isfile(f):
            continue
        if MF.sha256_file(f) != R.get("sha256"):
            P.append(f"{rel_}: changed after it was recorded — record it again, naming the human edits")
        if R.get("use") == "temp":
            if rel_ in listed:
                P.append(f"{rel_}: generated for temp use and listed in the audio manifest — temp tracks are never delivered")
            continue
        key, row = vendor_row(R.get("vendor") or "")
        if row.get("status") != "whitelist":
            P.append(f"{rel_}: {key} is no longer whitelisted ({row.get('status')}) — {row.get('why') or ''}".rstrip(" —"))
        tf = (R.get("terms") or {}).get("file")
        if not tf or not os.path.isfile(tf) or MF.sha256_file(tf) != (R.get("terms") or {}).get("sha256"):
            P.append(f"{rel_}: the terms snapshot is missing or changed")
        if not consent_before(job, "generated", parse_date(R.get("generated_at"))):
            P.append(f"{rel_}: no client consent dated before the generation (IPA/ISBA Principle 11)")
        P += [f"{rel_}: {x}" for x in prompt_problems(R.get("prompt") or "")]
        if R.get("stems") == "separated":
            P.append(f"{rel_}: separated stems from generated stereo — native stems only")
        if R.get("vocals") == "ai" and not os.path.isfile(f + ".vocals.json"):
            P.append(f"{rel_}: AI vocals without their record (`composer.py vocals record`: lyrics by a person, no soundalike, "
                     f"the disclosure, consent)")
        if not bakeoff_passed(f"vendor:{key}"):
            P.append(f"{rel_}: no passing blind bake-off of {key} against the library cue in the last {BAKEOFF_DAYS} days (K5, K7)")
    if made_here:
        E = jload(os.path.join(job, ELEMENTS_JSON))
        if not E:
            P.append("no element sheet — `composer.py elements <job>` (every sound's origin and what it needs disclosed)")
        elif E.get("listing_sha") != _listing_sha(job):
            P.append("the element sheet is stale — the audio changed since; `composer.py elements <job>` again")
        else:
            W += [f"disclose: {d}" for d in E.get("disclosure") or []]
    B = jload(os.path.join(job, BRIEF)) or {}
    Fam = jload(os.path.join(job, "07-edit", "music", "FAMILY.json")) or {}
    have = {round(float(x.get("length") or 0)) for x in Fam.get("lengths") or [] if x.get("file")}
    dur = float(H.get("duration") or 0)
    for Lsec in B.get("lengths") or []:
        if abs(float(Lsec) - dur) > 0.5 and round(float(Lsec)) not in have:
            W.append(f"deliverables: no {Lsec:g} s version of the music (`composer.py family`)")
    if "full" in ((B.get("deliverables") or {}).get("alt_mixes") or []) and os.path.isfile(os.path.join(job, LAYER)) \
            and not (Fam.get("alt_mixes") or {}).get("full"):
        W.append("deliverables: the full alt mix (bed + layer) is not rendered (`composer.py family`)")
    return P, W


# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    import py_compile
    np = _np()
    fails = []

    def check(name, ok, detail=""):
        print(("PASS  " if ok else "FAIL  ") + name + (f" — {detail}" if detail and not ok else ""))
        if not ok:
            fails.append(name)

    def refused(fn, *a, **k):
        try:
            fn(*a, **k)
            return ""
        except SystemExit as e:
            return str(e) or "refused"
    with tempfile.TemporaryDirectory() as td:
        os.environ["CINE_HOME"] = os.path.join(td, "home")
        job = os.path.join(td, "job")
        for d in ("06-music", "07-edit/titles", "09-qa"):
            os.makedirs(os.path.join(job, d), exist_ok=True)
        MF.synth_track(os.path.join(job, "06-music", "bed.wav"), stems_dir=None)
        fps = 24.0
        clips = [(0, 3.0), (3.0, 6.05), (6.05, 10.0), (10.0, 16.0), (16.0, 22.0), (22.0, 30.0)]
        jdump({"fps": fps, "tracks": {"video1": [{"name": f"S{i + 1}_v1.mp4", "start_s": a, "duration_s": b - a}
                                                 for i, (a, b) in enumerate(clips)],
                                      "audio1": [{"name": "VO_1.wav", "start_s": 3.2, "duration_s": 4.0}]}},
              os.path.join(job, "07-edit", "timeline-dump.json"))
        jdump({"id": "T9", "kind": "endcard", "at_s": 26.0, "duration_s": 4.0}, os.path.join(job, "07-edit", "titles", "T9.title.json"))
        MF.hits_init(job)
        H = MF.load_hits(job)
        for h in H["hits"]:
            if abs(h["t"] - 10.0) < 1e-6:
                h.update(type="reveal", priority="must", tier="hard", want="downbeat", strategy="catch")
        H["track"].update(file="06-music/bed.wav", vocals="none", edits_allowed="yes")
        jdump(H, os.path.join(job, MF.HITS))
        MF.fit(job, engine="numpy")
        MF.render(job)
        # A: the paperwork
        brief_init(job)
        check("A: a fresh brief does not lint (the director has answers to give)", len(brief_problems(job)[0]) >= 4)
        B = jload(os.path.join(job, BRIEF))
        B.update(media_plan=[{"platform": "meta", "placement": "reels", "territories": ["RO", "GB"]}],
                 references=[{"ref": "library: warm-folk-02", "why_liked": "the pulse under the VO, not the tune"}],
                 role="texture", vo_density="light", lengths=[30, 15], route="hybrid",
                 mnemonic={"needed": True, "brand_name": "ACME", "syllables": "ac-ME", "language": "ro"})
        jdump(B, os.path.join(job, BRIEF))
        check("A: the filled brief lints clean", not brief_problems(job)[0], json.dumps(brief_problems(job)))
        spot_init(job)
        check("A: the spotting note needs a function, a feeling and withhold-or-release per cue", len(spot_problems(job)[0]) >= 3)
        pic_ = (jload(os.path.join(job, SPOT)) or {}).get("picture") or {}
        check("(2.68) the spotting note is pre-filled from the picture: the voice windows from the cut, the must-hits, "
              "and Energy as picture intent (never a loudness curve)",
              pic_.get("voice") == MF.cuts_of(job)[3] and "must_hits" in pic_ and "energy_by_shot" in pic_
              and "not a loudness curve" in pic_.get("note", ""), json.dumps(pic_)[:300])
        S = jload(os.path.join(job, SPOT))
        S["cues"] = [{"id": "M1", "in_s": 0.0, "out_s": 10.0, "function": "establish", "target_feeling": "warm",
                      "temp": "warm-folk-02", "temp_why": "the pulse", "withhold_or_release": "withhold"},
                     {"id": "M2", "in_s": 10.0, "out_s": 30.0, "function": "release", "target_feeling": "proud",
                      "withhold_or_release": "release", "end_card_mood": "warm"}]
        jdump(S, os.path.join(job, SPOT))
        check("A: the filled spotting note lints clean", not spot_problems(job)[0], json.dumps(spot_problems(job)))
        S["fps"] = 30
        jdump(S, os.path.join(job, SPOT))
        check("A: a spotting note at the wrong fps refuses", any("fps" in x for x in spot_problems(job)[0]))
        S["fps"] = fps
        jdump(S, os.path.join(job, SPOT))
        # B: the motif — drafted by the skill, edited by the owner
        home = os.path.join(td, "brand-acme")
        motif_draft(home, "ACME", "C", "ac-ME", "warm")
        Dr = jload(os.path.join(home, "MOTIF-DRAFTS.json"))
        d1 = Dr["drafts"][0]
        check("B: three drafts of 3–6 notes, the last syllable long", len(Dr["drafts"]) == 3
              and all(3 <= len(d["notes"]) <= 6 for d in Dr["drafts"]) and d1["notes"][-1]["dur"] >= 0.9)
        same = os.path.join(td, "same.json")
        jdump({"notes": d1["notes"]}, same)
        check("B: adopting the draft unchanged is refused (K2: the owner edits)", "refused" in refused(motif_adopt, home, 1, same, "Dana"))
        ed = [dict(n) for n in d1["notes"]]
        ed[0]["pitch"] += 2
        ed[1]["pitch"] -= 1
        ed[-1]["dur"] = 1.5
        edp = os.path.join(td, "edited.json")
        jdump({"notes": ed}, edp)
        Mo = motif_adopt(home, 1, edp, "Dana")
        check("B: the owner's edit is adopted with its diff and statement", Mo["diff"]["changed_fraction"] >= 1 / 3
              and "Dana" in Mo["statement"] and os.path.isfile(os.path.join(home, "MOTIF.mid")))
        home2 = os.path.join(td, "brand-other")
        motif_draft(home2, "OTHER", "G", "", "bright")
        cp = [dict(n, pitch=n["pitch"] + 7) for n in ed]
        cpp = os.path.join(td, "copy.json")
        jdump({"notes": cp}, cpp)
        check("B: another client's motif with the same intervals and rhythm is refused (melody check)",
              "exactly" in refused(motif_adopt, home2, 1, cpp, "Dana", "", True))
        check("B: no layer before the bed's key is confirmed by ear (K9)",
              "key confirm" in refused(layer, job, os.path.join(home, "MOTIF.json")))
        Fj = jload(os.path.join(job, MF.FIT))
        Mk = jload(os.path.join(job, Fj["plans"][Fj.get("picked", 0)]["map"]))
        key_confirm(job, Mk["key"]["name"].replace(" major", "").replace(" minor", "m"), "Dana")
        L = layer(job, os.path.join(home, "MOTIF.json"))
        H = MF.load_hits(job)
        offs = layer_offsets(job, L, H)
        check("B: the layer's impacts land on the hard hits, 0 to +1 frame, measured on the render",
              bool(offs) and all(o["class"] == "on" for o in offs), json.dumps(offs))
        lay = os.path.join(job, L["file"])
        check("B: the layer is 48 kHz with stems, a composition record and a licence sidecar",
              os.path.isfile(lay + ".compose.json") and os.path.isfile(lay + ".licence.json") and len(L["stems"]) >= 2
              and all(os.path.isfile(os.path.join(job, f) + ".conform.json") for f in L["stems"].values()))
        x = MF.decode(lay, SR, 2)
        tb = (MF.load_hits(job)["end_card"]["t"])
        seg = np.abs(x[int((tb - 0.02) * SR):int((tb + 0.1) * SR)]).max()
        check("B: the mnemonic's last note lands on the end card", seg > 0.05)
        Fa = family(job, [15], os.path.join(home, "MOTIF.json"))
        f15 = next(z for z in Fa["lengths"] if z["length"] == 15)
        check("B: the 15 s version ends inside its slot, and the full alt mix is rendered",
              f15.get("file") and f15["ends_at_s"] <= 15.0 and (Fa["alt_mixes"] or {}).get("full"), json.dumps(Fa))
        # C: the note engine
        T = solve(job, 70, 140)
        m0 = T["maps"][0]
        check("C: the solver puts both hard hits on downbeats", not m0["unlanded"] and all(r["class"] == "on" for r in m0["hits"]
                                                                                            if r["tier"] == "hard"), json.dumps(m0))
        plan_template(job)
        D = jload(os.path.join(job, PLAN))
        cyc = ["I", "V", "vi", "IV"]
        D["key"] = "C"
        for s in D["sections"]:
            s["chords"] = [cyc[i % 4] for i in range(s["bars"][1] - s["bars"][0])]
        D["motif"] = os.path.join(home, "MOTIF.json")
        jdump(D, os.path.join(job, PLAN))
        check("C: the filled plan lints", not plan_problems(job), json.dumps(plan_problems(job)))
        D2 = json.loads(json.dumps(D))
        D2["sections"][0]["chords"][0] = "Q9"
        D2["sections"][0]["parts"].append("solo_violin")
        jdump(D2, os.path.join(job, PLAN))
        pp = plan_problems(job)
        check("C: a chord that is not a Roman numeral and a part outside the palette are refused",
              any("Roman" in x for x in pp) and any("palette" in x for x in pp), json.dumps(pp))
        jdump(D, os.path.join(job, PLAN))
        sc = realise(job)
        check("C: the score realises and passes its validators", sc["validators"]["passed"], json.dumps(sc["validators"]))
        bad = validate({"pad": [{"beat": 0, "dur": 4, "pitch": 61, "vel": 80}], "sub": [{"beat": 0, "dur": 4, "pitch": 80, "vel": 80}]},
                       0, "major", [({}, 0, parse_roman("I", 0, "major"))], [0], 16)
        check("C: the validators catch an out-of-key note and an out-of-range bass", any("key" in x for x in bad)
              and any("range" in x for x in bad), json.dumps(bad))
        rep = validate({"piano": [{"beat": b + o, "dur": 0.4, "pitch": 60, "vel": 80} for b in range(0, 24, 4) for o in (0, 1)]},
                       0, "major", [({}, i, parse_roman("I", 0, "major")) for i in range(6)], list(range(0, 24, 4)), 24)
        check("C: the same bar six times running is a copy-paste repeat", any("copy-paste" in x for x in rep), json.dumps(rep))
        R = render_score(job)
        scp = os.path.join(job, R["file"])
        P, W = check_job(job)
        check("C: a route-1 score with no blind bake-off is refused (K7)", any("route1" in x for x in P), json.dumps(P))
        bd = bakeoff_init(job, Fj["render"]["file"], R["file"], "route1:score", seed=7)
        Bk = jload(os.path.join(bd, "BAKEOFF.json"))
        key = jload(os.path.join(bd, "KEY.json"))
        dup = next(t for t, k in key.items() if k.get("duplicate_of"))
        for i, who in enumerate(["ana", "dan", "ioana", "mihai"]):
            pk = {}
            for t in Bk["trials"]:
                tt = str(t["trial"])
                want = "candidate" if (int(tt) + i) % 2 == 0 else "library"
                pk[tt] = next(lab for lab in ("a", "b") if key[tt][lab] == want)
            orig = str(key[dup]["duplicate_of"])
            pk[dup] = next(lab for lab in ("a", "b") if key[dup][lab] == key[orig][pk[orig]])
            bakeoff_record(bd, who, "other", ",".join(f"{k}:{v}" for k, v in pk.items()))
        bakeoff_record(bd, "dana", "composer", ",".join(f"{t['trial']}:a" for t in Bk["trials"]))
        res = bakeoff_result(bd)
        check("C: the blind bake-off pools 30+ trials from 3+ listeners, drops the composer, and passes at even odds",
              res["result"] in ("pass", "prefer") and res["trials"] >= 30 and any("composer" in x for x in res["dropped"]), json.dumps(res))
        check("C: with the bake-off passed, the score is not refused for it", not any("route1" in x for x in check_job(job)[0]))
        check("C: binomial rule: 10/30 is significantly worse, 11/30 is not, 20/30 is preferred",
              _binom_cdf(10, 30) <= 0.05 < _binom_cdf(11, 30) and 1 - _binom_cdf(19, 30) <= 0.05)
        refs = os.path.join(td, "refs")
        for i in range(5):
            MF.synth_track(os.path.join(refs, f"r{i}.wav"), bpm=100 + 6 * i, bars=8, pitch=200 + 20 * i)
        ga = gate_a(scp, refs)
        check("C: gate A measures the cue against the references and says when there are too few", len(ga["rows"]) >= 4
              and ga["note"] and "references" in ga["note"], json.dumps(ga))
        # D: generated music
        gdir = os.path.join(job, GEN_DIR)
        os.makedirs(gdir, exist_ok=True)
        g1 = os.path.join(gdir, "gen1.wav")
        shutil.copy(os.path.join(job, Fj["render"]["file"]), g1)
        terms = os.path.join(td, "elevenlabs-terms-2026-10-27.txt")
        open(terms, "w").write("Eleven Music Model-Specific Terms. Last updated: 09 October 2026.")
        args = dict(vendor="elevenlabs", plan="creator", prompt="warm folk pulse, acoustic guitar, 96 BPM, instrumental",
                    terms_url="https://elevenlabs.io/eleven-music-model-specific-terms", use="ship", terms_file=terms)
        check("D: no generation before the client's written consent (IPA/ISBA Principle 11)",
              "consent" in refused(generated_record, job, "06-music/generated/gen1.wav", **args))
        consent_add(job, "Jordan", "yes, you may use AI-generated music in our ads", ["generated"],
                    (dt.datetime.now() - dt.timedelta(hours=1)).isoformat(timespec="seconds"))
        check("D: an excluded vendor cannot ship", "suno" in refused(generated_record, job, "06-music/generated/gen1.wav",
                                                                     **dict(args, vendor="suno")).lower())
        check("D: the free plan cannot ship", "plan" in refused(generated_record, job, "06-music/generated/gen1.wav",
                                                                 **dict(args, plan="free")))
        check("D: an artist or a quoted title in the prompt is refused",
              "prompt" in refused(generated_record, job, "06-music/generated/gen1.wav",
                                  **dict(args, prompt='in the style of Coldplay, like "Viva la Vida"')))
        g = generated_record(job, "06-music/generated/gen1.wav", **args)
        check("D: a whitelisted vendor with the terms snapshot and prior consent is recorded",
              g["terms"]["sha256"] and os.path.isfile(g1 + ".licence.json"))
        check("D: a generated bed with no passing bake-off for its vendor is refused at export",
              any("bake-off of elevenlabs" in x for x in check_job(job)[0]))
        g2 = os.path.join(gdir, "gen2.wav")
        shutil.copy(g1, g2)
        check("D: AI vocals need the client's consent to AI vocals", "ai_vocals" in refused(
            generated_record, job, "06-music/generated/gen2.wav", **dict(args, prompt="warm folk song, female voice, original lyrics"), vocals="ai"))
        consent_add(job, "Jordan", "AI vocals are fine for the summer spot", ["ai_vocals"],
                    (dt.datetime.now() - dt.timedelta(hours=1)).isoformat(timespec="seconds"))
        generated_record(job, "06-music/generated/gen2.wav", **dict(args, prompt="warm folk song, female voice, original lyrics"), vocals="ai")
        ly = os.path.join(td, "lyrics.txt")
        open(ly, "w").write("Sun on the roof, light in the house, every day ours")
        check("D: AI vocals without the no-soundalike statement are refused",
              "soundalike" in refused(vocals_record, job, "06-music/generated/gen2.wav", ly, "Dana", "warm female alto",
                                      "TikTok AI toggle on; disclosed in the EU", False))
        vocals_record(job, "06-music/generated/gen2.wav", ly, "Dana", "warm female alto", "TikTok AI toggle on; disclosed in the EU", True)
        g3 = os.path.join(gdir, "gen3.wav")
        shutil.copy(g1, g3)
        generated_record(job, "06-music/generated/gen3.wav", **dict(args, vendor="google_lyria", use="temp", terms_file=None))
        import mix_qa as MQ  # noqa: E402
        MQ.write_manifest(job)
        P, W = check_job(job)
        check("D: a temp-only generated track listed in the mix is refused", any("temp" in x and "gen3" in x for x in P), json.dumps(P))
        check("D: the element sheet is required once anything is composed or generated", any("element sheet" in x for x in P))
        el = elements(job)
        kinds = {e["class"] for e in el["elements"]}
        check("D: the element sheet classes each sound and writes the TikTok toggle and the EU vocal disclosure",
              {"sample-rendered", "ai-generated"} <= kinds and any("TikTok" in d for d in el["disclosure"])
              and any("Article 50(4)" in d for d in el["disclosure"]), json.dumps(el["disclosure"]))
        row = next(r for r in MQ.read_manifest(job) if r.get("file", "").endswith("gen1.wav"))
        check("D: the manifest row carries the generator's tool, plan and region", row.get("tool") == "elevenlabs"
              and row.get("plan") == "creator" and "RO" in (row.get("region") or ""), json.dumps(row))
        open(os.path.join(job, "06-music", "late.wav"), "wb").write(open(g1, "rb").read())
        check("D: the element sheet goes stale when the audio changes", any("stale" in x for x in check_job(job)[0]))
        os.remove(os.path.join(job, "06-music", "late.wav"))
        # Resolve: the Fairlight copy
        cpth = console_copy(job, "Cine Music")
        con = open(cpth).read()
        py_compile.compile(cpth, doraise=True)
        mline = next(x for x in con.splitlines() if x.startswith("MUSIC_FIT = "))
        eline = next(x for x in con.splitlines() if x.startswith("MUSIC_ELEMENTS = "))
        RBc = jload(os.path.join(job, MF.REBUILD))
        check("Resolve: the Fairlight copy places the ORIGINAL's segments on A5 (the rebuild, never the render), the "
              "layer on A6, stems on named disabled tracks, cue, hit and seam markers with their windows, and the named "
              "Fairlight preset",
              "PLACE_MUSIC_FIT = True" in con and os.path.abspath(os.path.join(job, "06-music", "bed.wav")) in mline
              and "'segments': [{" in mline and ".fit.wav" not in mline and RBc and RBc["placed_by_script"]
              and "PLACE_MUSIC_ELEMENTS = True" in con and "'A6 music'" in con
              and "STEM impact (composed)" in con and "'enabled': False" in con and "Cue M2" in con
              and "window_ms" in con and "Music seam" in con and "FAIRLIGHT_PRESET = 'Cine Music'" in con, mline)
        check("Resolve: the alt mix and the length family are previews — neither is placed (no ALT track, MUSIC_FAMILY "
              "empty), though both were rendered",
              ".full.wav" not in eline and "ALT full mix" not in eline and "MUSIC_FAMILY = []  # __MUSIC_FAMILY__" in con
              and (Fa["alt_mixes"] or {}).get("full") and not any(MF.is_preview(e["file"]) for e in
                                                                 __import__("ast").literal_eval(eline[len("MUSIC_ELEMENTS = "):eline.index("  # __MUSIC_ELEMENTS__")]))
              and jload(os.path.join(job, f15["file"]) + ".conform.json").get("preview") is True, eline)
    os.environ.pop("CINE_HOME", None)
    print("\nselftest OK — the brief, the spotting note and consent lint; the owner's edit adopts a motif and a copy of "
          "another client's is refused; the layer lands its impacts 0..+1 frame on the hits and the mnemonic on the end "
          "card; the family ends inside its slots; the solver lands the hard hits, the plan lints, the score validates "
          "and renders; the blind bake-off pools listeners and drops the composer; generated music needs consent first, "
          "the whitelist, the terms snapshot and its bake-off; AI vocals need their record; the element sheet and the "
          "Fairlight copy are written" if not fails else f"\nFAIL — {len(fails)} failing")
    return 1 if fails else 0


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("brief", "spot"):
        g = sub.add_parser(name).add_subparsers(dest="sub")
        p = g.add_parser("init"); p.add_argument("job"); p.add_argument("--force", action="store_true")
        p = g.add_parser("lint"); p.add_argument("job")
    p = sub.add_parser("consent"); p.add_argument("job"); p.add_argument("--by", required=True); p.add_argument("--quote", required=True)
    p.add_argument("--scope", required=True); p.add_argument("--date")
    g = sub.add_parser("key").add_subparsers(dest="sub")
    p = g.add_parser("confirm"); p.add_argument("job"); p.add_argument("--key", required=True); p.add_argument("--by", required=True)
    g = sub.add_parser("motif").add_subparsers(dest="sub")
    p = g.add_parser("draft"); p.add_argument("home"); p.add_argument("--brand", required=True); p.add_argument("--key", required=True)
    p.add_argument("--syllables", default=""); p.add_argument("--feeling", default="warm"); p.add_argument("--n", type=int, default=3)
    p = g.add_parser("adopt"); p.add_argument("home"); p.add_argument("--draft", type=int, required=True)
    p.add_argument("--edited", required=True); p.add_argument("--by", required=True); p.add_argument("--statement", default="")
    p.add_argument("--written-by-owner", action="store_true"); p.add_argument("--midi-dir", action="append", default=[])
    p = sub.add_parser("layer"); p.add_argument("job"); p.add_argument("--motif", required=True)
    p.add_argument("--backend", default="numpy", choices=["numpy", "fluidsynth", "sfizz"]); p.add_argument("--instrument", default="builtin")
    p.add_argument("--stab", action="store_true")
    p = sub.add_parser("family"); p.add_argument("job"); p.add_argument("--lengths"); p.add_argument("--motif")
    p = sub.add_parser("solve"); p.add_argument("job"); p.add_argument("--bpm", default="70-140")
    p.add_argument("--play-through", action="append", default=[]); p.add_argument("--pick", type=int)
    g = sub.add_parser("plan").add_subparsers(dest="sub")
    p = g.add_parser("template"); p.add_argument("job"); p.add_argument("--force", action="store_true")
    p = g.add_parser("lint"); p.add_argument("job")
    p = sub.add_parser("realise"); p.add_argument("job")
    p = sub.add_parser("render"); p.add_argument("job"); p.add_argument("--backend", default="numpy", choices=["numpy", "fluidsynth", "sfizz"])
    p.add_argument("--instrument", default="builtin"); p.add_argument("--part-instrument", action="append", default=[])
    p = sub.add_parser("gate-a"); p.add_argument("wav"); p.add_argument("--refs", required=True)
    g = sub.add_parser("generated").add_subparsers(dest="sub")
    p = g.add_parser("record"); p.add_argument("job"); p.add_argument("--file", required=True); p.add_argument("--vendor", required=True)
    p.add_argument("--plan", required=True); p.add_argument("--prompt", required=True); p.add_argument("--terms-url", required=True)
    p.add_argument("--terms-file"); p.add_argument("--use", required=True, choices=["temp", "ship"]); p.add_argument("--model", default="")
    p.add_argument("--stems", default="none", choices=["none", "native", "separated"]); p.add_argument("--vocals", default="none", choices=["none", "ai", "human"])
    p.add_argument("--generated-at"); p.add_argument("--human-edits", default="")
    g = sub.add_parser("vocals").add_subparsers(dest="sub")
    p = g.add_parser("record"); p.add_argument("job"); p.add_argument("--file", required=True); p.add_argument("--lyrics-file", required=True)
    p.add_argument("--lyrics-by", required=True); p.add_argument("--voice", required=True); p.add_argument("--disclosure", required=True)
    p.add_argument("--no-soundalike", action="store_true")
    g = sub.add_parser("bakeoff").add_subparsers(dest="sub")
    p = g.add_parser("init"); p.add_argument("job"); p.add_argument("--library", required=True); p.add_argument("--candidate", required=True)
    p.add_argument("--subject", required=True); p.add_argument("--vo"); p.add_argument("--picture"); p.add_argument("--excerpt", type=float, default=6.0)
    p = g.add_parser("record"); p.add_argument("dir"); p.add_argument("--listener", required=True); p.add_argument("--role", required=True)
    p.add_argument("--picks", required=True)
    p = g.add_parser("result"); p.add_argument("dir")
    p = sub.add_parser("elements"); p.add_argument("job")
    p = sub.add_parser("console"); p.add_argument("job"); p.add_argument("--fairlight-preset", default="")
    p = sub.add_parser("check"); p.add_argument("job")
    a = ap.parse_args()
    if not a.selftest:
        import cine_home as _ch
        _ch.merge_now()                     # (3.0.0) the one-time merge from ~/.cinematography
    if a.selftest:
        return selftest()
    c, s = a.cmd, getattr(a, "sub", None)

    def lint_out(P, W):
        for x in P:
            print("REFUSE", x)
        for x in W:
            print("NOTE  ", x)
        return 1 if P else 0
    if c == "brief" and s == "init":
        print(MF.rel(a.job, brief_init(a.job, a.force))); return 0
    if c == "brief" and s == "lint":
        return lint_out(*brief_problems(a.job))
    if c == "spot" and s == "init":
        print(MF.rel(a.job, spot_init(a.job, a.force))); return 0
    if c == "spot" and s == "lint":
        return lint_out(*spot_problems(a.job))
    if c == "consent":
        print(json.dumps(consent_add(a.job, a.by, a.quote, [x.strip() for x in a.scope.split(",")], a.date), ensure_ascii=False)); return 0
    if c == "key" and s == "confirm":
        print(json.dumps(key_confirm(a.job, a.key, a.by))); return 0
    if c == "motif" and s == "draft":
        print(motif_draft(a.home, a.brand, a.key, a.syllables, a.feeling, a.n)); return 0
    if c == "motif" and s == "adopt":
        M = motif_adopt(a.home, a.draft, a.edited, a.by, a.statement, a.written_by_owner, a.midi_dir)
        print(f"MOTIF.json: {len(M['notes'])} notes, {M['diff']['changed_fraction']:.0%} changed by {M['adopted_by']}; "
              f"melody matches: {len(M['melody_check']['matches'])}"); return 0
    if c == "layer":
        L = layer(a.job, a.motif, a.backend, a.instrument, a.stab)
        print(f"{L['file']} ({L['render_seconds']} s to render), stems: {', '.join(L['stems'])}"); return 0
    if c == "family":
        F = family(a.job, [float(x) for x in a.lengths.split(",")] if a.lengths else None, a.motif)
        print(json.dumps(F, indent=1)); return 0
    if c == "solve":
        if a.pick is not None:
            T = jload(os.path.join(a.job, TEMPO)); T["picked"] = a.pick; jdump(T, os.path.join(a.job, TEMPO))
        else:
            lo, hi = [float(x) for x in a.bpm.split("-")]
            T = solve(a.job, lo, hi, a.play_through)
        for i, m in enumerate(T["maps"]):
            print(f"{'*' if i == T['picked'] else ' '} {i}: {m['bpm']} BPM" + (f", a {m['insert']['beats']}/4 bar at bar {m['insert']['bar']}" if m["insert"] else "")
                  + f" — score {m['score']}" + (f", cannot land: {', '.join(m['unlanded'])}" if m["unlanded"] else ""))
        return 0
    if c == "plan" and s == "template":
        print(MF.rel(a.job, plan_template(a.job, a.force))); return 0
    if c == "plan" and s == "lint":
        return lint_out(plan_problems(a.job), [])
    if c == "realise":
        sc = realise(a.job); print(f"{sum(len(v) for v in sc['parts'].values())} notes in {len(sc['parts'])} parts; validators passed"); return 0
    if c == "render":
        pi = dict(x.split("=", 1) for x in a.part_instrument)
        R = render_score(a.job, a.backend, a.instrument, pi); print(json.dumps(R, indent=1)); return 0
    if c == "gate-a":
        G = gate_a(a.wav, a.refs)
        for r in G["rows"]:
            print(f"{'OUT ' if r['outside'] else 'ok  '} {r['measure']}: {r['value']} [{r['p5']}, {r['p95']}]")
        if G["note"]:
            print("NOTE", G["note"])
        return 1 if G["flags"] else 0
    if c == "generated" and s == "record":
        g = generated_record(a.job, a.file, a.vendor, a.plan, a.prompt, a.terms_url, a.use, a.terms_file, a.model, a.stems,
                             a.vocals, a.generated_at, a.human_edits)
        print(f"{a.file}: {g['vendor']} ({g['status']}), {g['use']}, terms snapshot {g['terms']['snapshot']}"); return 0
    if c == "vocals" and s == "record":
        vocals_record(a.job, a.file, a.lyrics_file, a.lyrics_by, a.voice, a.disclosure, a.no_soundalike); print("recorded"); return 0
    if c == "bakeoff" and s == "init":
        print(bakeoff_init(a.job, a.library, a.candidate, a.subject, a.vo, a.picture, a.excerpt)); return 0
    if c == "bakeoff" and s == "record":
        bakeoff_record(a.dir, a.listener, a.role, a.picks); print("recorded"); return 0
    if c == "bakeoff" and s == "result":
        r = bakeoff_result(a.dir); print(json.dumps(r, indent=1)); return 0 if r["result"] in ("pass", "prefer") else 1
    if c == "elements":
        E = elements(a.job); print(f"{ELEMENTS}: {len(E['elements'])} element(s)"); [print(" -", d) for d in E["disclosure"]]; return 0
    if c == "console":
        print(MF.rel(a.job, console_copy(a.job, a.fairlight_preset)))
        Fam = jload(os.path.join(a.job, "07-edit", "music", "FAMILY.json")) or {}
        if Fam.get("lengths") or (Fam.get("alt_mixes") or {}).get("full"):
            print("  not placed: the alt mix and the length family (06-music/family/) are previews cut in Python — rebuild "
                  "each in Resolve from the original (FAMILY.json lists each length's plan)")
        return 0
    if c == "check":
        return lint_out(*check_job(a.job))
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
