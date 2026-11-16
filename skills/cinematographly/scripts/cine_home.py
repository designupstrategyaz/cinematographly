#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""cine_home.py — the one place that says where Cinematographly keeps its state.

Since 3.0.0 the plugin is named `cinematographly` and its home is `~/.cinematographly` (the gate's open job, the
session transcript pointer, the connector settings, the logs, the SFX catalogues). `CINE_HOME` in the environment
still wins. On first use the old home, `~/.cinematography`, is merged in once:

  * every file and folder that is missing in the new home is copied (nothing is ever overwritten);
  * an append-only log present in both homes gets the old lines appended once;
  * when both homes hold an `active-job`, the newer one wins and the older is kept as `active-job.from-cinematography`;
  * a marker (`.merged-from-cinematography`) records that it happened, so it runs once.

An open job therefore survives the upgrade. The old folder is left in place.

  python3 cine_home.py where       # print the home in use and whether a merge happened
  python3 cine_home.py --selftest
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, tempfile, time

NAME = "cinematographly"
OLD_NAME = "cinematography"
MARKER = ".merged-from-cinematography"
LOGS = ("bypass.log",)                    # append-only logs: old lines appended once


def default_home(user_home: str | None = None) -> str:
    return os.path.join(user_home or os.path.expanduser("~"), "." + NAME)


def old_home(user_home: str | None = None) -> str:
    return os.path.join(user_home or os.path.expanduser("~"), "." + OLD_NAME)


def merge_old(new: str, old: str) -> dict:
    """Merge `old` into `new` once. Returns what it did (empty when there was nothing to do)."""
    done: dict = {}
    if not os.path.isdir(old) or os.path.isfile(os.path.join(new, MARKER)):
        return done
    os.makedirs(new, exist_ok=True)
    copied, appended, kept = [], [], []
    for root, dirs, files in os.walk(old):
        rel = os.path.relpath(root, old)
        dst_root = new if rel == "." else os.path.join(new, rel)
        os.makedirs(dst_root, exist_ok=True)
        for f in files:
            src, dst = os.path.join(root, f), os.path.join(dst_root, f)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                copied.append(os.path.join(rel, f) if rel != "." else f)
            elif rel == "." and f in LOGS:
                with open(src, encoding="utf-8", errors="replace") as a, open(dst, "a", encoding="utf-8") as b:
                    b.write(a.read())
                appended.append(f)
            elif rel == "." and f == "active-job":
                if os.path.getmtime(src) > os.path.getmtime(dst):
                    shutil.copy2(dst, dst + ".from-" + NAME)
                    shutil.copy2(src, dst)
                    kept.append("active-job (old was newer; the new one kept as active-job.from-cinematographly)")
                else:
                    shutil.copy2(src, dst + ".from-" + OLD_NAME)
                    kept.append("active-job (new was newer; the old one kept as active-job.from-cinematography)")
    with open(os.path.join(new, MARKER), "w", encoding="utf-8") as fh:
        fh.write(f"merged {old} at {time.strftime('%Y-%m-%dT%H:%M:%S')}\ncopied {len(copied)} · appended {appended} · "
                 f"{'; '.join(kept)}\n")
    done = {"copied": copied, "appended": appended, "kept": kept}
    return done


def home(merge: bool = True) -> str:
    """The home in use: `CINE_HOME` if set (never merged into), else ~/.cinematographly, merged from the old home once."""
    env = os.environ.get("CINE_HOME")
    if env:
        return env
    new = default_home()
    if merge:
        try:
            merge_old(new, old_home())
        except OSError:
            pass                  # a merge that cannot run must never stop the gate; doctor reports it
    return new


def paths(home_dir: str | None = None) -> dict:
    """The three paths every script uses, from ONE place: the home, the open-job pointer, the transcript pointer."""
    h = home_dir or home(merge=False)
    return {"home": h, "active": os.path.join(h, "active-job"), "transcript": os.path.join(h, "transcript-path")}


def merge_now() -> dict:
    """The one-time merge from ~/.cinematography, for the main() of every script that reads or writes the home
    (gate, composer, sfx_conform). Never on import, never in a self-test, never when CINE_HOME is set; a merge that
    cannot run never stops the caller (doctor reports the old home)."""
    if os.environ.get("CINE_HOME"):
        return {}
    try:
        return merge_old(default_home(), old_home())
    except OSError:
        return {}


CONFIG_KEYS = ("studio", "clients_dir", "memory_dir", "jobs_dir")   # written by setup.py; read after the env, before fallbacks


def config(home_dir: str | None = None) -> dict:
    """`<home>/config.json` as a dict ({} when missing or unreadable). Never merges, never writes."""
    p = os.path.join(home_dir or home(merge=False), "config.json")
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def config_dir(key: str, home_dir: str | None = None) -> str | None:
    """A folder the config names under `key`, only when it exists (a stale entry falls through to the fallbacks)."""
    v = config(home_dir).get(key)
    if isinstance(v, str) and v.strip():
        v = os.path.abspath(os.path.expanduser(v))
        if os.path.isdir(v):
            return v
    return None


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        old, new = old_home(td), default_home(td)
        os.makedirs(os.path.join(old, "sfx-catalogues"))
        open(os.path.join(old, "connectors.json"), "w").write('{"higgsfield": ["x"]}')
        open(os.path.join(old, "sfx-catalogues", "lib.json"), "w").write("{}")
        open(os.path.join(old, "bypass.log"), "w").write("old line\n")
        open(os.path.join(old, "active-job"), "w").write("/jobs/old")
        os.makedirs(new)
        open(os.path.join(new, "bypass.log"), "w").write("new line\n")
        open(os.path.join(new, "active-job"), "w").write("/jobs/new")
        os.utime(os.path.join(old, "active-job"), (time.time() - 100, time.time() - 100))
        r = merge_old(new, old)
        assert open(os.path.join(new, "connectors.json")).read() == '{"higgsfield": ["x"]}', "a missing file is copied"
        assert os.path.isfile(os.path.join(new, "sfx-catalogues", "lib.json")), "folders are copied recursively"
        assert open(os.path.join(new, "bypass.log")).read() == "new line\nold line\n", "logs: old lines appended once"
        assert open(os.path.join(new, "active-job")).read() == "/jobs/new", "the newer open job wins"
        assert open(os.path.join(new, "active-job.from-cinematography")).read() == "/jobs/old", "the older is kept"
        assert r["copied"] and os.path.isfile(os.path.join(new, MARKER))
        assert merge_old(new, old) == {}, "the merge runs once"
        assert open(os.path.join(new, "bypass.log")).read() == "new line\nold line\n", "…and never appends twice"
        # the old job newer than the new one: it wins, the new one is kept beside it
        new2, old2 = os.path.join(td, "n2"), os.path.join(td, "o2")
        os.makedirs(new2); os.makedirs(old2)
        open(os.path.join(new2, "active-job"), "w").write("/jobs/new")
        open(os.path.join(old2, "active-job"), "w").write("/jobs/old")
        os.utime(os.path.join(new2, "active-job"), (time.time() - 100, time.time() - 100))
        merge_old(new2, old2)
        assert open(os.path.join(new2, "active-job")).read() == "/jobs/old"
        assert open(os.path.join(new2, "active-job.from-cinematographly")).read() == "/jobs/new"
        # CINE_HOME wins and is never merged into
        saved = os.environ.get("CINE_HOME")
        os.environ["CINE_HOME"] = os.path.join(td, "elsewhere")
        try:
            assert home() == os.path.join(td, "elsewhere")
        finally:
            os.environ.pop("CINE_HOME") if saved is None else os.environ.__setitem__("CINE_HOME", saved)
    # (3.0.0) the rename, checked in the id slots only (the English word and cinematography-craft.md stay)
    import json, re
    here = os.path.dirname(os.path.abspath(__file__))
    skill = os.path.dirname(here)
    plugin = os.path.dirname(os.path.dirname(skill))
    assert os.path.basename(skill) == NAME, ("the skill folder", skill)
    assert json.load(open(os.path.join(plugin, ".claude-plugin", "plugin.json")))["name"] == NAME, "plugin.json name"
    assert re.search(r"^name:\s*" + NAME + r"\s*$", open(os.path.join(skill, "SKILL.md")).read(), re.M), "SKILL.md name:"
    hooks = open(os.path.join(plugin, "hooks", "hooks.json")).read()
    assert "skills/" + OLD_NAME + "/" not in hooks and hooks.count("skills/" + NAME + "/scripts/") >= 5, "hook paths"
    doubled = NAME + "ly"
    import build_bundle                                   # only what ships is held to it (a plan or note may say it)
    for rel in build_bundle.collect(plugin):
        if rel.endswith((".py", ".md", ".json")) and not rel.endswith("cine_home.py"):
            try:
                assert doubled not in open(os.path.join(plugin, rel), encoding="utf-8").read(), ("a doubled rename", rel)
            except UnicodeDecodeError:
                pass
    with tempfile.TemporaryDirectory() as td:            # one function gives all three paths
        p = paths(td)
        assert p == {"home": td, "active": os.path.join(td, "active-job"), "transcript": os.path.join(td, "transcript-path")}
        # ⛔ HOME is pointed at the temp folder too: a broken guard must never reach the real ~/.cinematography (a
        # sabotage run on 2026-11-15 merged the real one before this line existed)
        old_env, old_home_env = os.environ.get("CINE_HOME"), os.environ.get("HOME")
        os.environ["CINE_HOME"] = td; os.environ["HOME"] = td
        os.makedirs(os.path.join(td, "." + OLD_NAME)); open(os.path.join(td, "." + OLD_NAME, "x"), "w").write("x")
        try:
            assert merge_now() == {} and not os.path.exists(os.path.join(td, "." + NAME)), "CINE_HOME set: never merged"
        finally:
            for k, v in (("CINE_HOME", old_env), ("HOME", old_home_env)):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    with tempfile.TemporaryDirectory() as td:
        h = os.path.join(td, "h"); os.makedirs(h); real = os.path.join(td, "clients"); os.makedirs(real)
        assert config(h) == {} and config_dir("clients_dir", h) is None, "no config file: nothing"
        open(os.path.join(h, "config.json"), "w").write(json.dumps({"clients_dir": real, "memory_dir": td + "/gone"}))
        assert config_dir("clients_dir", h) == real, "an existing folder from the config is answered"
        assert config_dir("memory_dir", h) is None, "a folder that does not exist falls through"
        open(os.path.join(h, "config.json"), "w").write("[1, 2]")
        assert config(h) == {}, "a config that is not an object is ignored"
    print("selftest OK — copy-if-missing (files and folders), old log lines appended once, the newer open job wins and "
          "the older is kept, the merge runs once, CINE_HOME wins and is never merged into; the id slots carry "
          "the new name (folder, plugin.json, SKILL.md, hook paths) and no doubled rename exists")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("cmd", nargs="?", choices=["where"])
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    h = home()
    mk = os.path.join(h, MARKER)
    print(f"home: {h}" + (" (CINE_HOME)" if os.environ.get("CINE_HOME") else "") +
          (f"\n{open(mk).read().strip()}" if os.path.isfile(mk) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
