#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
client_files.py — where a client's file is on THIS machine. The one place the planning tools ask.

The plugin ships no real client. A studio's profiles (`<brand>.md`), cost files (`costs.<brand>.json`)
and script numbers (`script.<brand>.json`) live OUTSIDE it, because a plugin update replaces the
plugin's own `clients/` folder. Until v2.53.0 four tools (batch_plan, beat_plan, estimate_duration,
script_score) read the plugin's folder only, so a studio that kept its files outside could open a
job at the gate and then be told "no cost file" by the estimator.

Looked for, in order. It is the order gate.find_profile uses, so a profile and its numbers are
found in the same place:

  1. the folder `CINE_CLIENTS` names (when it is not set: `clients_dir` in ~/.cinematographly/config.json,
     written by setup.py; with neither, the plugin's own `clients/`);
  2. a `_cine-clients/` folder beside or above each starting point: the job, the script file, and
     always the working folder;
  3. the plugin's own `clients/` (the templates, `_lab`, and the invented sample client `acme`).

  python3 client_files.py where costs.acme.json [--from PATH ...]   # the path; exit 1 = not found
  python3 client_files.py --selftest

What it cannot do: it finds a file by its NAME. It does not read it, and it does not check that a
cost file and a profile found in two different folders belong to the same account.
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cine_home  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_CLIENTS = os.path.join(os.path.dirname(HERE), "clients")
PRIVATE_DIR = "_cine-clients"
MAX_UP = 12            # how many folders above a starting point are asked; gate.find_profile uses the same


def search_dirs(*starts: str | None) -> list[str]:
    """The folders asked, in order, without repeats. A start may be a folder or a file in one."""
    dirs = [os.environ.get("CINE_CLIENTS") or cine_home.config_dir("clients_dir") or PLUGIN_CLIENTS]
    for s in [*starts, os.getcwd()]:
        if not s or s == "-":
            continue
        d = os.path.abspath(s)
        if not os.path.isdir(d):
            d = os.path.dirname(d)
        for _ in range(MAX_UP):
            dirs.append(os.path.join(d, PRIVATE_DIR))
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    dirs.append(PLUGIN_CLIENTS)
    seen, out = set(), []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def find(filename: str, *starts: str | None) -> str | None:
    """Full path of `filename` (a bare name such as `costs.acme.json`), or None.

    A name carrying a folder is refused: `--client ../x` must not read a file outside the client folders."""
    if not filename or os.path.basename(filename) != filename or filename in (".", ".."):
        return None
    for d in search_dirs(*starts):
        p = os.path.join(d, filename)
        if os.path.isfile(p):
            return p
    return None


def where_looked(*starts: str | None) -> str:
    """One sentence for a refusal: the places asked, so the fix is a place to put the file."""
    env = os.environ.get("CINE_CLIENTS")
    cfg = cine_home.config_dir("clients_dir")
    first = (f"CINE_CLIENTS ({env})" if env else f"the configured clients folder ({cfg})" if cfg
             else "CINE_CLIENTS (not set; no clients folder configured: run setup)")
    return (f"looked in {first}, a `{PRIVATE_DIR}/` folder beside or above the job and the working "
            f"folder, and the plugin's clients/")


def selftest() -> int:
    fails: list[str] = []

    def check(name: str, cond: bool, info: str = "") -> None:
        print(f"  {'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  — {info}"))
        if not cond:
            fails.append(name)

    global PLUGIN_CLIENTS
    real_plugin, real_env, real_cwd = PLUGIN_CLIENTS, os.environ.get("CINE_CLIENTS"), os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as td:
            td = os.path.realpath(td)
            plugin = os.path.join(td, "plugin", "clients")
            envdir = os.path.join(td, "studio-clients")
            job = os.path.join(td, "work", "videos", "clients", "brand", "04-projects", "job-01001")
            private = os.path.join(td, "work", "videos", PRIVATE_DIR)
            elsewhere = os.path.join(td, "elsewhere")
            for d in (plugin, envdir, job, private, elsewhere):
                os.makedirs(d)

            def put(folder: str, name: str) -> str:
                p = os.path.join(folder, name)
                open(p, "w", encoding="utf-8").write("{}")
                return p

            PLUGIN_CLIENTS = plugin
            os.chdir(elsewhere)
            os.environ.pop("CINE_CLIENTS", None)

            check("nothing anywhere: no answer", find("costs.x.json", job) is None)
            in_plugin = put(plugin, "costs.x.json")
            check("the plugin's clients/ is the last resort", find("costs.x.json", job) == in_plugin)
            in_private = put(private, "costs.y.json")
            check("a `_cine-clients/` folder above the job is found", find("costs.y.json", job) == in_private)
            script = os.path.join(job, "01-script", "SCRIPT.md")
            check("a start may be a file that does not exist yet (its folder is used)",
                  find("costs.y.json", script) == in_private)
            check("a start that is unrelated finds nothing", find("costs.y.json", elsewhere) is None)
            os.chdir(job)
            check("the working folder is always a starting point", find("costs.y.json") == in_private)
            os.chdir(elsewhere)

            put(private, "costs.x.json")
            check("CINE_CLIENTS not set: the plugin's folder is asked before a `_cine-clients/` (as the gate does)",
                  find("costs.x.json", job) == in_plugin)
            os.environ["CINE_CLIENTS"] = envdir
            check("CINE_CLIENTS set, file not in it: the `_cine-clients/` copy wins over the plugin's",
                  find("costs.x.json", job) == os.path.join(private, "costs.x.json"))
            in_env = put(envdir, "costs.x.json")
            check("CINE_CLIENTS set and holding the file: it wins over every other folder",
                  find("costs.x.json", job) == in_env)

            check("SABOTAGE a name carrying a folder is refused", find(os.path.join("..", "costs.x.json"), envdir) is None
                  and find(in_env, job) is None)
            check("SABOTAGE an empty name is refused", find("", job) is None and find("..", job) is None)
            check("a refusal names CINE_CLIENTS and its value", envdir in where_looked(job))
            os.environ.pop("CINE_CLIENTS")
            check("a refusal says when CINE_CLIENTS is not set", "not set" in where_looked(job))
            # (3.0.0) the config setup.py writes: after CINE_CLIENTS, before the plugin's folder
            real_home = os.environ.get("CINE_HOME")
            cfg_home = os.path.join(td, "cfg-home"); os.makedirs(cfg_home)
            cfg_cli = os.path.join(td, "cfg-clients"); os.makedirs(cfg_cli)
            in_cfg = put(cfg_cli, "costs.x.json")
            open(os.path.join(cfg_home, "config.json"), "w").write('{"clients_dir": "%s"}' % cfg_cli)
            os.environ["CINE_HOME"] = cfg_home
            check("SABOTAGE clients_dir in the config is asked first when CINE_CLIENTS is not set",
                  find("costs.x.json", job) == in_cfg)
            check("a refusal names the configured folder", cfg_cli in where_looked(job))
            os.environ["CINE_CLIENTS"] = envdir
            check("CINE_CLIENTS still wins over the config", find("costs.x.json", job) == in_env)
            os.environ.pop("CINE_CLIENTS")
            if real_home is None:
                os.environ.pop("CINE_HOME")
            else:
                os.environ["CINE_HOME"] = real_home

            # the claim in the docstring: a profile is found where gate.find_profile finds it
            put(private, "brand.md"); put(envdir, "brand.md"); put(envdir, "only-env.md"); put(private, "only-private.md")
            probe = ("import gate, sys; print(gate.find_profile(sys.argv[1], sys.argv[2]) or '')")
            for label, env_on in (("CINE_CLIENTS set", True), ("CINE_CLIENTS not set", False)):
                env = {k: v for k, v in os.environ.items() if k != "CINE_CLIENTS"}
                if env_on:
                    env["CINE_CLIENTS"] = envdir
                    os.environ["CINE_CLIENTS"] = envdir
                else:
                    os.environ.pop("CINE_CLIENTS", None)
                PLUGIN_CLIENTS = real_plugin                      # gate.py reads the real plugin folder
                same = True
                detail = ""
                for name in ("brand", "only-env", "only-private", "_lab", "nobody-at-all"):
                    r = subprocess.run([sys.executable, "-B", "-c", probe, name, job], capture_output=True,
                                       text=True, cwd=HERE, env=env)
                    theirs = os.path.realpath(r.stdout.strip()) if r.stdout.strip() else None
                    mine = find(f"{name}.md", job)
                    mine = os.path.realpath(mine) if mine else None
                    if r.returncode != 0 or theirs != mine:
                        same, detail = False, f"{name}: gate {theirs} / here {mine} {r.stderr[-200:]}"
                check(f"{label}: five profile names resolve exactly where gate.find_profile resolves them",
                      same, detail)
                PLUGIN_CLIENTS = plugin

            # the four tools that ask this module really do: a client whose files exist ONLY outside the plugin
            import json
            name = "zz-outside-only"
            spec = {"client": name, "runtime_target_s": 41, "hook_seconds_min": 3, "cta_seconds": 4,
                    "beat_seconds": 8.5, "max_words_per_line": 14, "speakers": 1, "lang": "en"}
            preset = {"start_frame": 2, "broll": 10, "voiceover_line": 0.6, "retry": 1.15,
                      "dialogue_clip_per_second": 2.5, "kling_dialogue": 10.0}
            costs = {"client": name, "plan": {"monthly_credits": 4321, "videos_per_month_min": 3,
                                              "videos_per_month_max": 4, "credit_price_usd": 0},
                     "default_preset": "economy", "presets": {"economy": preset, "quality": preset},
                     "last_verified": ""}
            script = os.path.join(job, "01-script", "SCRIPT.md")
            os.makedirs(os.path.dirname(script))
            open(script, "w", encoding="utf-8").write(
                "[SCENE 1 — INTRO 0:00-0:03]\nRider: My chain snapped on the way to work again.\n\n"
                "[SCENE 2]\nRider: The shop had it fixed the same week.\nRider: Book a service before winter.\n")
            base_env = {k: v for k, v in os.environ.items() if k != "CINE_CLIENTS"}

            def tool(args: list[str], cwd: str, env_dir: str | None):
                env = dict(base_env)
                if env_dir:
                    env["CINE_CLIENTS"] = env_dir
                return subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, cwd=cwd, env=env)

            def jget(r, *keys):
                try:
                    d = json.loads(r.stdout)
                    for k in keys:
                        d = d[k]
                    return d
                except (ValueError, KeyError, TypeError):
                    return None

            bp = [os.path.join(HERE, "beat_plan.py"), "plan", "--client", name, "--json"]
            ba = [os.path.join(HERE, "batch_plan.py"), "--count", "4", "--personas", "a,b", "--hooks", "h1,h2",
                  "--bodies", "b1,b2", "--client", name, "--seconds-per-video", "30", "--json"]
            ed = [os.path.join(HERE, "estimate_duration.py"), "--client", name, "--intro", "3", "--cta", "4", script]
            ss = [os.path.join(HERE, "script_score.py"), script, "--client", name]
            r = tool(bp, elsewhere, None)
            check("before the files exist, beat_plan.py refuses this client (the checks below are not vacuous)",
                  r.returncode == 1 and "REFUSED" in r.stderr, r.stderr[-200:])
            for folder, how, cwd, env_dir in ((envdir, "CINE_CLIENTS", elsewhere, envdir),
                                              (private, "a `_cine-clients/` above the working folder", job, None)):
                s_p, c_p = put(folder, f"script.{name}.json"), put(folder, f"costs.{name}.json")
                json.dump(spec, open(s_p, "w", encoding="utf-8"))
                json.dump(costs, open(c_p, "w", encoding="utf-8"))
                r = tool(bp, cwd, env_dir)
                check(f"beat_plan.py reads script numbers from {how}", jget(r, "runtime_s") == 41, r.stderr[-200:])
                r = tool(ba, cwd, env_dir)
                check(f"batch_plan.py reads the cost file from {how}", jget(r, "cost", "monthly_plan") == 4321,
                      r.stderr[-200:])
                r = tool(ed, elsewhere, env_dir)       # found from the SCRIPT's folder when the working folder is unrelated
                check(f"estimate_duration.py reads the cost file from {how.replace('the working folder', 'the script')}",
                      r.returncode == 0 and f"client: {name}" in r.stdout, r.stderr[-200:])
                r = tool(ss, elsewhere, env_dir)
                check(f"script_score.py reads script numbers from {how.replace('the working folder', 'the script')}",
                      r.returncode in (0, 1) and "script_score" in r.stdout and "no script." not in r.stderr,
                      r.stderr[-200:])
                if env_dir is None:            # (v2.59.2) from an unrelated working folder, through the job
                    r = tool(bp + ["--from", job], elsewhere, None)
                    check("beat_plan.py --from <job> finds the `_cine-clients/` above the job from anywhere",
                          jget(r, "runtime_s") == 41, r.stderr[-200:])
                    r = tool(ba + ["--out", os.path.join(job, "batch.json")], elsewhere, None)
                    check("batch_plan.py finds it from the --out file's folder",
                          jget(r, "cost", "monthly_plan") == 4321, r.stderr[-200:])
                os.remove(s_p); os.remove(c_p)
    finally:
        PLUGIN_CLIENTS = real_plugin
        os.chdir(real_cwd)
        if real_env is None:
            os.environ.pop("CINE_CLIENTS", None)
        else:
            os.environ["CINE_CLIENTS"] = real_env
    print(f"SELFTEST: {'OK' if not fails else 'FAIL'} ({len(fails)} failed)")
    return 1 if fails else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("where", help="print where a client file is found")
    w.add_argument("filename")
    w.add_argument("--from", dest="starts", nargs="*", default=[], help="job folder or script file to start from")
    a = ap.parse_args()
    if a.cmd != "where":
        ap.print_help()
        return 2
    p = find(a.filename, *a.starts)
    if not p:
        print(f"not found: {a.filename} ({where_looked(*a.starts)})", file=sys.stderr)
        return 1
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
