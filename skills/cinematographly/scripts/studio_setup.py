#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""studio_setup.py — make a studio folder and tell every tool where it is. Safe to re-run: it never overwrites.

  studio_setup.py [STUDIO_DIR]            # default: ~/Cinematographly
  studio_setup.py --install-deps          # also install the picture/sound check packages (numpy, OpenCV, Pillow)
  studio_setup.py --selftest

What it makes (only what is missing):

  STUDIO_DIR/
    _cine-clients/   your client profiles, cost and script files (the templates and the sample `acme` are copied in)
    _cine-memory/    your studio's history: close-out notes, proposed rule changes, the ledger
    jobs/            one folder per job (new_job.py makes them)

and `~/.cinematographly/config.json` (or `$CINE_HOME/config.json`) naming those three folders. The tools look there
after the environment (`CINE_CLIENTS`, `CINE_MEMORY` still win) and before their old fallbacks. Your files live
outside the plugin because a plugin update replaces the plugin's own folders.

The spend gate needs none of the packages; a concept and a script need none of them either.
"""
from __future__ import annotations
import argparse, glob, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cine_home  # noqa: E402
import memory_home  # noqa: E402

SKILL = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL))
PLUGIN_CLIENTS = os.path.join(SKILL, "clients")
# copied into a new studio: the templates and the invented sample client. Never the bench file or its index.
CLIENT_FILES = ("_TEMPLATE.md", "_STYLE-GUIDE-TEMPLATE.md", "costs._TEMPLATE.json", "script._TEMPLATE.json",
                "acme.md", "costs.acme.json", "script.acme.json")
DEFAULT_STUDIO = os.path.join(os.path.expanduser("~"), "Cinematographly")


def pip_line() -> list:
    return [sys.executable, "-m", "pip", "install", "-r", os.path.join(PLUGIN_ROOT, "requirements.txt")]


def setup(studio: str, home_dir: str | None = None) -> dict:
    """Make what is missing. Returns {"made": [...], "kept": [...], "config": path}."""
    studio = os.path.abspath(os.path.expanduser(studio))
    home_dir = home_dir or cine_home.home(merge=True)
    made, kept = [], []
    clients = os.path.join(studio, "_cine-clients")
    jobs = os.path.join(studio, "jobs")
    for d in (studio, clients, jobs):
        if os.path.isdir(d):
            kept.append(d)
        else:
            os.makedirs(d); made.append(d)
    for f in CLIENT_FILES:
        src, dst = os.path.join(PLUGIN_CLIENTS, f), os.path.join(clients, f)
        if os.path.exists(dst):
            kept.append(dst)
        elif os.path.isfile(src):
            shutil.copy2(src, dst); made.append(dst)
    mem_existed = os.path.isdir(os.path.join(studio, memory_home.PRIVATE_DIR))
    memory = memory_home.init(studio)
    (kept if mem_existed else made).append(memory)

    os.makedirs(home_dir, exist_ok=True)
    cfg_path = os.path.join(home_dir, "config.json")
    cfg = cine_home.config(home_dir)
    want = {"studio": studio, "clients_dir": clients, "memory_dir": memory, "jobs_dir": jobs}
    changed = False
    for k, v in want.items():
        cur = cfg.get(k)
        if isinstance(cur, str) and cur and os.path.isdir(os.path.expanduser(cur)):
            if os.path.abspath(os.path.expanduser(cur)) != v:
                kept.append(f"config {k} = {cur} (kept; it is not this studio's folder — edit {cfg_path} to change)")
            continue
        cfg[k] = v; changed = True
    if changed:
        tmp = cfg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2); fh.write("\n")
        os.replace(tmp, cfg_path)
        made.append(cfg_path)
    else:
        kept.append(cfg_path)
    return {"made": made, "kept": kept, "config": cfg_path, "studio": studio}


def _hooks_seen(hd: str) -> bool:
    """Any session record with a transcript: a real hook ran here (the same test as gate.hooks_seen)."""
    for fp in glob.glob(os.path.join(hd, "sessions", "*.json")):
        try:
            if (json.load(open(fp, encoding="utf-8")) or {}).get("transcript"):
                return True
        except (OSError, ValueError, AttributeError):
            continue
    return False


def set_hookless(on: bool, home_dir: str | None = None) -> int:
    """(3.1) The one place 'hookless' is set. Never inferred: on a hooked home an approval whose transcript cannot be
    resolved is refused; hookless records it UNVERIFIED (and says so on the approval row and in doctor)."""
    hd = home_dir or cine_home.home(merge=True)
    os.makedirs(hd, exist_ok=True)
    cfg = cine_home.config(hd)
    if on and _hooks_seen(hd):
        print("REFUSED: hooks have recorded session transcripts in this home, so it is not hookless: approvals here "
              "are checked against what the person wrote. `--hookless` is for Cowork or eval homes where hooks never "
              "run (build review 1).", file=sys.stderr)
        return 1
    if on:
        cfg["hookless"] = True
    else:
        cfg.pop("hookless", None)
    p = os.path.join(hd, "config.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2); fh.write("\n")
    os.replace(tmp, p)
    print("hookless: approvals here are recorded UNVERIFIED (no transcript to check them against); batch approvals "
          "(`gate.py allow`) need a checked quote and are not available" if on else
          "hooked: an approval whose transcript cannot be resolved is refused")
    return 0


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        home_dir, studio = os.path.join(td, "home"), os.path.join(td, "My Studio")
        r = setup(studio, home_dir)
        cfg = json.load(open(r["config"], encoding="utf-8"))
        assert cfg["clients_dir"] == os.path.join(studio, "_cine-clients") and cfg["jobs_dir"] == os.path.join(studio, "jobs")
        assert os.path.isdir(cfg["memory_dir"]) and cfg["memory_dir"].endswith("_cine-memory"), cfg
        assert os.path.isfile(os.path.join(studio, "_cine-clients", "acme.md")), "the sample client is copied"
        assert not os.path.exists(os.path.join(studio, "_cine-clients", "_lab.md")), "the bench file never is"
        # re-run: nothing overwritten, a user's edit survives, a deleted piece is repaired
        acme = os.path.join(studio, "_cine-clients", "acme.md")
        open(acme, "a", encoding="utf-8").write("\nmy edit\n")
        shutil.rmtree(os.path.join(studio, "jobs"))
        r2 = setup(studio, home_dir)
        assert open(acme, encoding="utf-8").read().endswith("my edit\n"), "an edited file is never overwritten"
        assert os.path.isdir(os.path.join(studio, "jobs")) and os.path.join(studio, "jobs") in r2["made"], "repaired"
        assert r2["config"] in r2["kept"], "an unchanged config is not rewritten"
        # a config naming another existing studio is kept, and said so
        other = os.path.join(td, "other"); setup(other, os.path.join(td, "home2"))
        json.dump({"clients_dir": os.path.join(other, "_cine-clients")}, open(os.path.join(td, "home2", "config.json"), "w"))
        r3 = setup(studio, os.path.join(td, "home2"))
        assert cine_home.config(os.path.join(td, "home2"))["clients_dir"] == os.path.join(other, "_cine-clients")
        assert any("kept" in k and "clients_dir" in k for k in r3["kept"]), r3["kept"]
        assert cine_home.config(os.path.join(td, "home2"))["jobs_dir"] == os.path.join(studio, "jobs"), "a missing key is filled"
        # the tools now find the studio's files from anywhere, through the config
        env = {**os.environ, "CINE_HOME": home_dir}
        env.pop("CINE_CLIENTS", None); env.pop("CINE_MEMORY", None)
        probe = ("import client_files, memory_home; print(client_files.find('costs.acme.json') or '');"
                 "print(memory_home.home() or '')")
        out = subprocess.run([sys.executable, "-B", "-c", probe], capture_output=True, text=True, cwd=HERE, env=env)
        lines = out.stdout.split("\n")
        assert lines[0] == os.path.join(studio, "_cine-clients", "costs.acme.json"), out.stdout + out.stderr
        assert lines[1] == cfg["memory_dir"], out.stdout
    with tempfile.TemporaryDirectory() as td:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            set_hookless(True, td)
        assert cine_home.config(td).get("hookless") is True
        with contextlib.redirect_stdout(io.StringIO()):
            set_hookless(False, td)
        assert "hookless" not in cine_home.config(td), "--hooked undoes it"
        os.makedirs(os.path.join(td, "sessions"), exist_ok=True)
        json.dump({"last": 1, "transcript": "/x/t.jsonl"}, open(os.path.join(td, "sessions", "abc.json"), "w"))
        assert set_hookless(True, td) == 1 and "hookless" not in cine_home.config(td), \
            "(build review 1) a home where hooks recorded a transcript refuses --hookless"
    print("selftest OK — a studio folder (clients with the sample, history, jobs) and a config naming them; re-running "
          "repairs what is missing and overwrites nothing; a config naming another studio is kept and reported; "
          "client_files and memory_home find the studio's files through the config")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("studio", nargs="?", default=None)
    ap.add_argument("--install-deps", action="store_true")
    ap.add_argument("--hookless", action="store_true",
                    help="(3.1) this environment never runs the plugin's hooks (Cowork, evals): record approvals UNVERIFIED")
    ap.add_argument("--hooked", action="store_true", help="(3.1) undo --hookless")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.hookless or a.hooked:
        if a.studio:                              # (build review 3) the advertised `setup <folder> --hookless`
            print(f"note: {a.studio} was not set up — `--hookless`/`--hooked` only change the setting; run setup "
                  f"without them to make the studio folder", file=sys.stderr)
        return set_hookless(bool(a.hookless))
    studio = a.studio or cine_home.config().get("studio") or DEFAULT_STUDIO
    r = setup(studio)
    print(f"studio: {r['studio']}")
    for p in r["made"]:
        print(f"  made  {p}")
    for p in r["kept"]:
        print(f"  kept  {p}")
    rc = 0
    if a.install_deps:
        print("installing: " + " ".join(pip_line()))
        rc = subprocess.call(pip_line())
    else:
        print("picture and sound checks need: " + " ".join(pip_line()) + "   (or re-run with --install-deps)")
    print("next: /cinematographly:doctor, then /cinematographly:new-job acme first-promo --mode A --approver \"Your Name\"")
    return rc


if __name__ == "__main__":
    sys.exit(main())
