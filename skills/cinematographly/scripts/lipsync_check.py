#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""lipsync_check.py — mechanical half of the speaking-clip gate: did the model SAY the line?

Transcribes a generated clip's own audio and compares it to the scripted line, word by word. It
exists because the human half of this gate (`qa_log.py`, which now demands a quoted word you heard)
is still self-reported, and because the failure that cost this pipeline three episodes was not
subtle: the model moved a mouth decoratively while the audio said something else, and a checkmark
recorded that the mouth moved.

⛔ WHAT THIS DOES NOT DO — read this before trusting a PASS
-----------------------------------------------------------
**It verifies the AUDIO CONTENT. It does not verify LIP ARTICULATION.** A clip can transcribe
perfectly and still show a mouth flapping out of phase with it — that is a visual judgement no
transcript can make. So a PASS here means "the right words are in the audio", which catches:

  - the wrong take, or the wrong shot's audio attached to this picture
  - the model paraphrasing, dropping or inventing words instead of speaking the script
  - the wrong language, or a voice that never rendered (silence)
  - a VO conform that slipped so far the words no longer align with the cut

and does NOT catch phase, articulation, or the phoneme-shape mismatch that reads as dubbing. Those
still require playing the audio over the picture and naming a word you heard. **Use both halves.**
Anyone treating this script as the whole gate has rebuilt the original mistake with better tooling.

Requirements
------------
ffmpeg (audio extraction) and a local Whisper: `faster_whisper`, `whisper`, or the `whisper` CLI.
None of them exist in the device VM, so this runs where the media and the models live — Claude Code
on the Mac. It refuses loudly rather than degrading when ASR is unavailable.

Usage
-----
  python3 lipsync_check.py CLIP.mp4 --line "Panourile scad factura de la prima lună" --lang ro
  python3 lipsync_check.py CLIP.mp4 --line-file 01-script/S03.txt --project ./Proiect-Video-7-SLUG
  python3 lipsync_check.py CLIP.mp4 --line "..." --max-wer 0.15 --json
  python3 lipsync_check.py --selftest

With --project, the transcript and the score are written to `09-qa/lipsync/<clip>.txt` as the
gate's artifact — evidence that required the work, per realism-qa.md §6.

Exit codes: 0 within tolerance · 1 over tolerance (RETAKE) or no speech found · 2 usage/IO/no ASR.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, tempfile, unicodedata

APOS = re.compile(r"['’]")          # deleted, not spaced: "don't" and "dont" must match
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
WS = re.compile(r"\s+")


def normalise(text: str, fold: bool = False) -> list[str]:
    t = APOS.sub("", (text or "").lower())
    if fold:  # diacritics -> ASCII, so "lună" == "luna" when the ASR drops them
        t = "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))
    t = PUNCT.sub(" ", t)
    return [w for w in WS.sub(" ", t).strip().split(" ") if w]


def wer(ref: list[str], hyp: list[str]) -> tuple[float, int, int, int]:
    """Levenshtein over words. Returns (wer, substitutions, deletions, insertions)."""
    n, m = len(ref), len(hyp)
    if n == 0:
        return (0.0 if m == 0 else 1.0), 0, 0, m
    prev = list(range(m + 1))
    ops_prev = [(0, 0, j) for j in range(m + 1)]          # (sub, del, ins)
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        ops_cur = [(0, i, 0)] + [(0, 0, 0)] * m
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                cur[j], ops_cur[j] = prev[j - 1], ops_prev[j - 1]
                continue
            sub, dele, ins = prev[j - 1] + 1, prev[j] + 1, cur[j - 1] + 1
            best = min(sub, dele, ins)
            cur[j] = best
            if best == sub:
                s, d, i2 = ops_prev[j - 1]; ops_cur[j] = (s + 1, d, i2)
            elif best == dele:
                s, d, i2 = ops_prev[j]; ops_cur[j] = (s, d + 1, i2)
            else:
                s, d, i2 = ops_cur[j - 1]; ops_cur[j] = (s, d, i2 + 1)
        prev, ops_prev = cur, ops_cur
    s, d, i2 = ops_prev[m]
    return prev[m] / n, s, d, i2


def extract_audio(clip: str, out_wav: str) -> None:
    if not shutil.which("ffmpeg"):
        print("error: ffmpeg not found — needed to extract the clip's audio.", file=sys.stderr)
        raise SystemExit(2)
    r = subprocess.run(["ffmpeg", "-y", "-i", clip, "-vn", "-ac", "1", "-ar", "16000", out_wav],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out_wav):
        print(f"error: could not extract audio from {clip}:\n{r.stderr.strip()[-400:]}", file=sys.stderr)
        raise SystemExit(2)


def transcribe(wav: str, lang: str | None, model: str) -> tuple[str, str]:
    """Return (text, backend). Refuses rather than degrading when no ASR is installed."""
    try:
        from faster_whisper import WhisperModel                       # type: ignore
        segs, _ = WhisperModel(model, device="auto", compute_type="int8").transcribe(wav, language=lang)
        return " ".join(s.text for s in segs).strip(), f"faster_whisper/{model}"
    except ImportError:
        pass
    try:
        import whisper                                                # type: ignore
        return whisper.load_model(model).transcribe(wav, language=lang)["text"].strip(), f"whisper/{model}"
    except ImportError:
        pass
    if shutil.which("whisper"):
        with tempfile.TemporaryDirectory() as d:
            cmd = ["whisper", wav, "--model", model, "--output_format", "txt", "--output_dir", d]
            if lang:
                cmd += ["--language", lang]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                for f in os.listdir(d):
                    if f.endswith(".txt"):
                        return open(os.path.join(d, f), encoding="utf-8").read().strip(), f"whisper-cli/{model}"
    print("error: no speech recogniser available (tried faster_whisper, whisper, the whisper CLI).\n"
          "       This gate runs where the media and the models are — Claude Code on the Mac.\n"
          "       Install one (`pip install faster-whisper`) or run the human half of the gate\n"
          "       instead: qa_log.py with a quoted word you actually heard.", file=sys.stderr)
    raise SystemExit(2)


SELFTEST_CASES = [
    # (reference, hypothesis, fold, expected wer)
    ("Panourile scad factura", "Panourile scad factura", False, 0.0),
    ("Panourile scad factura", "panourile, scad FACTURA!", False, 0.0),      # normalisation
    ("factura de la prima lună", "factura de la prima luna", False, 0.2),    # diacritic drop counts (1 of 5)
    ("factura de la prima lună", "factura de la prima luna", True, 0.0),     # ...unless folded
    ("one two three four", "one two four", False, 0.25),                     # deletion
    ("one two three", "one two three four", False, 1 / 3),                   # insertion
    ("one two three", "one five three", False, 1 / 3),                       # substitution
    ("hello world", "", False, 1.0),                                         # silence
]


def selftest() -> int:
    for ref, hyp, fold, want in SELFTEST_CASES:
        got, s, d, i = wer(normalise(ref, fold), normalise(hyp, fold))
        assert abs(got - want) < 1e-9, f"{ref!r} vs {hyp!r} fold={fold}: got {got}, want {want}"
    assert normalise("Ață, șiș — LUNĂ!", True) == ["ata", "sis", "luna"]
    assert normalise("don't stop") == ["dont", "stop"], normalise("don't stop")
    assert normalise("dont stop") == normalise("don't stop")   # ASR apostrophe drift must not score
    print(f"selftest OK — {len(SELFTEST_CASES)} WER cases + normalisation")
    print("NOTE: this proves the scoring maths, NOT that a PASS means the lips match. "
          "Read the docstring's ⛔ section.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", nargs="?", help="the generated clip (mp4/mov)")
    ap.add_argument("--line", help="the scripted line this shot speaks")
    ap.add_argument("--line-file", help="file containing the scripted line")
    ap.add_argument("--lang", default=None, help="ISO code (ro, en). Omit to let the model detect it "
                                                 "— detection failure is itself a finding.")
    ap.add_argument("--model", default="small", help="whisper model size (default small)")
    ap.add_argument("--max-wer", type=float, default=0.25,
                    help="word error rate tolerance (default 0.25). Generation paraphrase is the "
                         "thing being caught; ASR noise is the thing being tolerated.")
    ap.add_argument("--fold-diacritics", action="store_true",
                    help="treat luna == lună (recommended for Romanian, where ASR often drops them)")
    ap.add_argument("--project", help="write the artifact to <project>/09-qa/lipsync/")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.clip:
        print("error: give a clip (or --selftest). See --help.", file=sys.stderr)
        return 2
    if not os.path.exists(a.clip):
        print(f"error: no such file: {a.clip}", file=sys.stderr)
        return 2
    line = a.line
    if a.line_file:
        try:
            line = open(a.line_file, encoding="utf-8").read()
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    if not line or not line.strip():
        print("error: --line or --line-file is required — there is nothing to check against, and a "
              "check with no reference is the gate this file exists to replace.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        extract_audio(a.clip, wav)
        text, backend = transcribe(wav, a.lang, a.model)

    ref, hyp = normalise(line, a.fold_diacritics), normalise(text, a.fold_diacritics)
    if not hyp:
        print("RETAKE: no speech found in the clip's audio. Either the voice never rendered, or the "
              "clip is silent and the VO is supposed to arrive at the edit — check which, because "
              "they need different fixes.", file=sys.stderr)
        return 1
    score, subs, dels, ins = wer(ref, hyp)
    ok = score <= a.max_wer

    payload = {"clip": os.path.basename(a.clip), "backend": backend, "wer": round(score, 3),
               "max_wer": a.max_wer, "verdict": "PASS" if ok else "RETAKE",
               "substitutions": subs, "deletions": dels, "insertions": ins,
               "expected": " ".join(ref), "heard": " ".join(hyp)}
    if a.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"{'PASS' if ok else 'RETAKE'} — WER {score:.0%} (tolerance {a.max_wer:.0%}) · {backend}")
        print(f"  expected: {' '.join(ref)}")
        print(f"  heard   : {' '.join(hyp)}")
        print(f"  {subs} substitution(s), {dels} deletion(s), {ins} insertion(s)")
        if not ok:
            print("  The model did not say the script. That is a RETAKE regardless of how the mouth "
                  "looks — and if the words are close but reordered, check you are not listening to "
                  "a different take than the one on the timeline.")
        print("  ⛔ This checked the AUDIO, not the lips. Still play it over the picture and log a "
              "quoted word you heard (qa_log.py).")

    if a.project:
        outdir = os.path.join(a.project, "09-qa", "lipsync")
        os.makedirs(outdir, exist_ok=True)
        out = os.path.join(outdir, os.path.splitext(os.path.basename(a.clip))[0] + ".txt")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"  artifact: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
