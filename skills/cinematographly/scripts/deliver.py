#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""deliver.py — the delivery package: one folder per platform, ready to upload by hand. (3.1)

  deliver.py <job> --platform NAME [--platform NAME …] [--master FILE] [--title "…"] [--description "…"]
  deliver.py --selftest

Refused until the job's `export` is approved. For each platform it writes `10-export/DELIVERY/<platform>/`: the
master (copied, never re-encoded), the newest caption file from `08-captions/`, a cover frame (ffmpeg, the frame at
1 s), and `delivery.json` (title, description, the AI-disclosure line from the studio or the profile, the master's
sha256, the export approval it rests on). It never posts: uploading stays a person's action, and the gate's publish
class is unchanged.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
VIDEO = (".mp4", ".mov", ".m4v")


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def newest(paths: list) -> str | None:
    return max(paths, key=os.path.getmtime) if paths else None


def disclosure(job: str) -> str:
    """The client profile's disclosure mechanism wins; the studio's answer is the default when the profile has none.
    (3.1 review: the studio answer used to win, so "decided per client" was written into every delivery, and the
    profile was never read at all, because Job.profile_path is only set by validate().)"""
    import gate
    try:
        J = gate.Job(job)
        J.validate()
        txt = open(J.profile_path, encoding="utf-8").read() if J.profile_path else ""
        m = re.search(r"\*\*AI-disclosure mechanism per platform:\*\*\s*(.+)", txt)
        if m and "<" not in m.group(1):
            return m.group(1).strip()
    except Exception:                                     # noqa: BLE001
        pass
    try:
        import studio
        s = studio.load().get("ai_disclosure")
        if s:
            return str(s) + " (the studio's default: the client profile names no mechanism)"
    except Exception:                                     # noqa: BLE001
        pass
    return "not set: answer it in the client profile or /cinematographly:studio before uploading"


def build(job: str, platforms: list, master: str | None = None, title: str = "", description: str = "",
          cover=True) -> tuple[list, list]:
    import gate
    job = os.path.abspath(job)
    J = gate.Job(job)
    ok = J.approved("export")
    if not ok:
        return [], ["`export` is not approved for this job — deliver only what was approved (gate.py approve export)"]
    master = master or newest([p for p in glob.glob(os.path.join(job, "10-export", "*")) if p.lower().endswith(VIDEO)])
    if not master or not os.path.isfile(master):
        return [], ["no master in 10-export/ — pass --master"]
    if not platforms:
        return [], ["name at least one --platform"]
    # (3.1 review) when the export approval names a video file, deliver only that file (the row's `sha` column)
    _asha = (ok.get("sha") or "").strip() if isinstance(ok, dict) and str(ok.get("artifact") or "").lower().endswith(
        VIDEO) else ""
    # the approvals file stores the first 16 hex digits of the sha256 (build review 2, Sonnet): compare as a prefix
    if _asha and not (len(_asha) >= 16 and _sha(master).startswith(_asha.lower())):
        return [], [f"{os.path.basename(master)} is not the file the export approval names (its sha256 differs) — "
                    f"deliver the approved master with --master, or approve this one"]
    caps = newest(glob.glob(os.path.join(job, "08-captions", "*.srt")) + glob.glob(os.path.join(job, "08-captions", "*.vtt")))
    sha, out = _sha(master), []
    for plat in platforms:
        d = os.path.join(job, "10-export", "DELIVERY", re.sub(r"[^A-Za-z0-9_-]+", "-", plat).strip("-") or "platform")
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, os.path.basename(master))
        if not os.path.exists(dst) or _sha(dst) != sha:
            shutil.copy2(master, dst)
        if caps:
            shutil.copy2(caps, os.path.join(d, os.path.basename(caps)))
        if cover and shutil.which("ffmpeg"):
            cj = os.path.join(d, "cover.jpg")
            for ss in ("1", "0"):                        # a master shorter than 1 s has no frame at 1 s (3.1 review)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", ss, "-i", master, "-frames:v", "1", cj],
                               capture_output=True)
                if os.path.isfile(cj) and os.path.getsize(cj) > 0:
                    break
            if not os.path.isfile(cj):
                print(f"warning: no cover.jpg for {plat}: ffmpeg could not read a frame of {os.path.basename(master)}",
                      file=sys.stderr)
        meta = {"platform": plat, "title": title, "description": description, "ai_disclosure": disclosure(job),
                "master": os.path.basename(master), "master_sha256": sha,
                "captions": os.path.basename(caps) if caps else None,
                "export_approval": {k: ok.get(k) for k in ("ts", "by", "quote") if isinstance(ok, dict)},
                "made": dt.datetime.now().isoformat(timespec="seconds"),
                "note": "upload by hand; this package posts nothing"}
        json.dump(meta, open(os.path.join(d, "delivery.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        out.append(d)
    return out, []


def selftest() -> int:
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    body = src.split("def selftest", 1)[0]
    assert "mcp" + "__" not in body, "deliver.py names no tool: it cannot call a publish tool"
    assert all('"ffmpeg"' in ln for ln in body.split("\n") if "subprocess.run(" in ln), "the only process it runs is ffmpeg"
    import gate
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "j"); os.makedirs(os.path.join(job, "10-export")); os.makedirs(os.path.join(job, "08-captions"))
        open(os.path.join(job, "10-export", "master.mp4"), "wb").write(b"\x00" * 64)
        open(os.path.join(job, "08-captions", "x.srt"), "w").write("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
        real = gate.Job.approved
        try:
            gate.Job.approved = lambda self, st: None
            d, P = build(job, ["tiktok"], cover=False)
            assert not d and "not approved" in P[0], "no export approval: refused"
            gate.Job.approved = lambda self, st: {"ts": "t", "by": "Sam Reyes", "quote": "ship it now"} if st == "export" else None
            d, P = build(job, ["tiktok", "Instagram Reels"], title="Spring tune-up", cover=False)
            assert not P and len(d) == 2, P
            meta = json.load(open(os.path.join(d[0], "delivery.json")))
            assert meta["master_sha256"] == _sha(os.path.join(job, "10-export", "master.mp4"))
            assert meta["captions"] == "x.srt" and meta["export_approval"]["by"] == "Sam Reyes"
            assert os.path.isdir(os.path.join(job, "10-export", "DELIVERY", "Instagram-Reels"))
            gate.Job.approved = lambda self, st: {"ts": "t", "by": "Sam Reyes", "quote": "ship it now",
                                                  "artifact": "10-export/v3.mp4", "sha": "0" * 64} if st == "export" else None
            d, P = build(job, ["tiktok"], cover=False)
            assert not d and "not the file the export approval names" in P[0], "(3.1 review) another master is refused"
            _real16 = _sha(os.path.join(job, "10-export", "master.mp4"))[:16]           # as gate.py writes the row
            gate.Job.approved = lambda self, st: {"ts": "t", "by": "Sam Reyes", "quote": "ship it now",
                                                  "artifact": "10-export/master.mp4", "sha": _real16} if st == "export" else None
            d, P = build(job, ["tiktok"], cover=False)
            assert d and not P, ("(build review 2) the approved master itself is delivered", P)
            # (3.1 build review) the client profile's disclosure wins over the studio's default
            prof = os.path.join(td, "client.md")
            open(prof, "w").write("**AI-disclosure mechanism per platform:** TikTok AI-content toggle on every post\n")
            st = os.path.join(td, "studio"); os.makedirs(st)
            json.dump({"ai_disclosure": "decided per client"}, open(os.path.join(st, "studio.json"), "w"))
            real_v = gate.Job.validate
            os.environ["CINE_STUDIO"] = st
            try:
                def _v(self):
                    self.profile_path = prof
                    return []
                gate.Job.validate = _v
                assert disclosure(job) == "TikTok AI-content toggle on every post", disclosure(job)
                open(prof, "w").write("**AI-disclosure mechanism per platform:** <fill in>\n")
                assert disclosure(job).startswith("decided per client (the studio's default"), disclosure(job)
            finally:
                gate.Job.validate = real_v
                os.environ.pop("CINE_STUDIO", None)
        finally:
            gate.Job.approved = real
    print("selftest OK — refused without the export approval; one folder per platform with the master (same bytes), "
          "captions, delivery.json (disclosure, sha, the approval it rests on); the script calls no publish tool")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="?"); ap.add_argument("--platform", action="append", default=[])
    ap.add_argument("--master"); ap.add_argument("--title", default=""); ap.add_argument("--description", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.job:
        ap.print_help(); return 2
    out, P = build(a.job, a.platform, a.master, a.title, a.description)
    if P:
        print("REFUSED:\n  - " + "\n  - ".join(P), file=sys.stderr); return 1
    print("delivery packages (upload by hand):\n  " + "\n  ".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
