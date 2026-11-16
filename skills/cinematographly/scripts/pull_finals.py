#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
pull_finals.py — one move: download the CHOSEN Higgsfield finals straight into the job's project
folders, correctly named. Kills the manual "favorite → download to ~/Downloads → move → rename".

Runs on the Mac (or a Claude-on-Mac session). Input is a small "finals manifest" that Claude
builds from the Higgsfield MCP (`show_generations` / `job_display` return the result URLs) plus the
shot IDs you picked. You do the human "which take is final" call (Cinema Studio favorites, or just
tell Claude the job IDs); this script does the download + filing + naming.

Manifest (JSON list; url is the asset's https result URL from the MCP):
[
  {"shot":"S0B",   "subject":"intro-drone", "model":"cinema", "kind":"broll", "url":"https://.../x.mp4"},
  {"shot":"S1-C1", "subject":"host",     "model":"seedance", "kind":"clip",  "url":"https://.../y.mp4"},
  {"shot":"S1-C1", "subject":"host",     "model":"tasha",  "kind":"voice", "url":"https://.../z.wav"},
  {"shot":"S1-C1", "subject":"host",     "model":"gptimg", "kind":"frame", "url":"https://.../f.png"}
]

kind → lane folder:
  frame|startframe → 02-startframes    clip|video → 03-clips    broll → 04-broll
  voice|audio      → 05-voice          music      → 06-music

Filename: <SHOT>_<subject>_<model>_v<N>.<ext>  (N auto-increments; won't overwrite).

Every file it files is TRACED: a row in <project>/.gate/pulled.jsonl with the file's sha256, its shot,
kind, url and job id — which is what `gate.py reconcile --files` matches the job's media against, so a
clip that came from anywhere else (a browser generation, a hand-made render) shows up as untraced.

An EVALUATION job (`Tier: evaluation` in 00-brief/CHECKPOINT.md, job_tier.py) files into
_eval/<lane>/ with EVAL in the name — <SHOT>_<subject>_<model>_EVAL_v<N>.<ext> — and export_qc.py
refuses anything filed that way.

Usage:
  python3 pull_finals.py --project ~/<project>/creative/videos/<job-folder> \\
      --manifest finals.json
  cat finals.json | python3 pull_finals.py --project <dir> -        # manifest on stdin
  python3 pull_finals.py --project <dir> --manifest finals.json --dry-run
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import job_tier  # noqa: E402

LANE = {"frame": "02-startframes", "startframe": "02-startframes",
        "clip": "03-clips", "video": "03-clips",
        "broll": "04-broll",
        "voice": "05-voice", "audio": "05-voice",
        "music": "06-music"}
EXT_DEFAULT = {"frame": "png", "startframe": "png", "clip": "mp4", "video": "mp4",
               "broll": "mp4", "voice": "wav", "audio": "wav", "music": "mp3"}


def ext_of(item):
    if item.get("ext"):
        return item["ext"].lstrip(".")
    url = item.get("url", "").split("?")[0]
    if "." in url.rsplit("/", 1)[-1]:
        return url.rsplit(".", 1)[-1][:5]
    return EXT_DEFAULT.get(item.get("kind", "").lower(), "bin")


def dest_path(root, item, evaluation=False):
    kind = item.get("kind", "").lower()
    lane = LANE.get(kind)
    if not lane:
        raise ValueError(f"unknown kind '{kind}' (shot {item.get('shot')})")
    folder = os.path.join(root, job_tier.EVAL_DIR, lane) if evaluation else os.path.join(root, lane)
    os.makedirs(folder, exist_ok=True)
    shot = item.get("shot", "SHOT")
    subj = item.get("subject", "asset")
    model = item.get("model", "gen")
    ext = ext_of(item)
    n = 1
    while True:
        name = f"{shot}_{subj}_{model}{'_EVAL' if evaluation else ''}_v{n}.{ext}"
        p = os.path.join(folder, name)
        if not os.path.exists(p):
            return p
        n += 1


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "acme-pull-finals/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(path)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_pull(root, item, path):
    """The trace row `gate.py reconcile --files` matches by hash."""
    row = {"ts": __import__("datetime").datetime.now().astimezone().replace(microsecond=0).isoformat(),
           "shot": item.get("shot"), "kind": item.get("kind"), "url": item.get("url"),
           "job_id": item.get("job_id") or item.get("id"), "path": os.path.relpath(path, root),
           "sha256": sha256_file(path), "source": "pull_finals"}
    os.makedirs(os.path.join(root, ".gate"), exist_ok=True)
    with open(os.path.join(root, ".gate", "pulled.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def selftest():
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "src.mp4"); open(src, "wb").write(b"generated clip bytes")
        for name, extra in (("prod", ""), ("ev", "Tier: evaluation\n")):
            root = os.path.join(td, name); os.makedirs(os.path.join(root, "00-brief"))
            open(os.path.join(root, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\n" + extra)
        it = {"shot": "S3", "subject": "hands", "model": "kling", "kind": "broll",
              "url": "file://" + src, "job_id": "job_abc"}
        p = dest_path(os.path.join(td, "prod"), it)
        check("production files into the lane folder, no EVAL",
              p.endswith(os.path.join("04-broll", "S3_hands_kling_v1.mp4")))
        size = download(it["url"], p)
        row = record_pull(os.path.join(td, "prod"), it, p)
        check("the download lands", size == len(b"generated clip bytes"))
        trace = os.path.join(td, "prod", ".gate", "pulled.jsonl")
        check("a trace row is written with the file's sha256",
              os.path.isfile(trace) and json.loads(open(trace).readline())["sha256"] == sha256_file(p)
              and row["job_id"] == "job_abc")
        ev = os.path.join(td, "ev")
        pe = dest_path(ev, it, evaluation=job_tier.tier(ev) == "evaluation")
        check("an evaluation job files under _eval/ with EVAL in the name",
              pe.endswith(os.path.join("_eval", "04-broll", "S3_hands_kling_EVAL_v1.mp4")))
        check("and that file is refused for shipping", bool(job_tier.ship_refusal(pe)))
    print("-" * 60)
    print("selftest OK — lane filing, the trace row and its hash, and the evaluation lane (_eval/, EVAL, "
          "refused for shipping)" if ok else "selftest FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Download chosen Higgsfield finals into the job's project folders.")
    ap.add_argument("--project", required=True, help="project root, e.g. ~/<project>/creative/videos/<job-folder>")
    ap.add_argument("--manifest", help="finals manifest JSON file (or pass - / omit to read stdin)")
    ap.add_argument("stdin_flag", nargs="?", help="pass - to read the manifest from stdin")
    ap.add_argument("--dry-run", action="store_true", help="show what would be filed, download nothing")
    ap.add_argument("--selftest", action="store_true")
    if "--selftest" in sys.argv:
        return selftest()
    a = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(a.project))
    if a.manifest and a.manifest != "-":
        items = json.load(open(os.path.expanduser(a.manifest), encoding="utf-8"))
    else:
        items = json.load(sys.stdin)
    if isinstance(items, dict):
        items = items.get("finals") or items.get("items") or [items]

    evaluation = job_tier.files_as_eval(job_tier.job_root(root) or root)   # (v2.72.0) a job that ran in the lane too
    print(f"Project: {root}" + ("   ⚠ EVALUATION job — filing into _eval/, EVAL names, never ships"
                                if evaluation else ""))
    print(f"{'#':>2}  {'shot':<8}{'kind':<7}→ destination")
    ok = fail = 0
    for i, it in enumerate(items, 1):
        try:
            p = dest_path(root, it, evaluation=evaluation)
        except ValueError as e:
            print(f"{i:>2}  ⚠ {e}")
            fail += 1
            continue
        rel = os.path.relpath(p, root)
        if a.dry_run:
            print(f"{i:>2}  {it.get('shot',''):<8}{it.get('kind',''):<7}→ {rel}   (dry-run)")
            continue
        try:
            size = download(it["url"], p)
            record_pull(root, it, p)
            print(f"{i:>2}  {it.get('shot',''):<8}{it.get('kind',''):<7}→ {rel}   ({size/1e6:.1f} MB)")
            ok += 1
        except Exception as e:
            print(f"{i:>2}  ✗ {it.get('shot','')} — {e}")
            fail += 1
    if not a.dry_run:
        print(f"\nFiled {ok} asset(s)" + (f", {fail} failed" if fail else "") + f" under {root}")
        print("Next: python3 build_fcpxml.py --project <this dir> --slug <slug> --bpm <bpm>")


if __name__ == "__main__":
    sys.exit(main() or 0)
