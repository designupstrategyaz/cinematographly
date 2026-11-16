#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
memory_home.py — where a studio's own history is on THIS machine. The one place the tools ask.

The history is the close-out notes (`episodes/`), the proposed rule changes (`proposals/`) and the
studio's ledger of what landed (`LEDGER.md`). It names clients, jobs and people, so it is the
studio's and never ships: until v2.54.0 it sat inside the plugin as `memory/`, which meant anyone
given the plugin was given it, and a plugin update replaced it.

The plugin's own `memory/` now holds the templates only. A studio's history is looked for, in order:

  1. the folder `CINE_MEMORY` names (else `memory_dir` in ~/.cinematographly/config.json, from setup.py);
  2. a `_cine-memory/` folder beside or above each starting point: the job, and always the working
     folder.

There is no third place. With neither, `home()` answers None and a tool that would WRITE refuses: a
note written into the plugin's folder is lost at the next update.

A path written in the rules as `memory/<something>` is a pointer into that history. `resolve()`
answers where it is: in the studio's folder, or among the plugin's templates.

  python3 memory_home.py where [--from PATH ...]     # the folder; exit 1 = none found
  python3 memory_home.py init [--from PATH]          # create `_cine-memory/` with the templates
  python3 memory_home.py --selftest
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cine_home  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "memory")     # the plugin's own folder: templates only
PRIVATE_DIR = "_cine-memory"
MAX_UP = 12
# what the plugin's own memory/ may hold; anything else is a studio's history that must not ship
SHIPPED = {"README.md", os.path.join("episodes", "_TEMPLATE.md"), os.path.join("proposals", "README.md")}
REFUSAL = ("no studio history folder on this machine. Set CINE_MEMORY to a folder of yours, or create a "
           f"`{PRIVATE_DIR}/` folder above your jobs (`memory_home.py init` does it). Nothing is written into "
           "the plugin's own memory/: a plugin update replaces that folder.")


def home(*starts: str | None) -> str | None:
    """The studio's history folder, or None."""
    env = os.environ.get("CINE_MEMORY")
    if env:
        return os.path.abspath(env) if os.path.isdir(env) else None
    cfg = cine_home.config_dir("memory_dir")      # (3.0.0) written by setup.py
    if cfg:
        return cfg
    for s in [*starts, os.getcwd()]:
        if not s or s == "-":
            continue
        d = os.path.abspath(s)
        if not os.path.isdir(d):
            d = os.path.dirname(d)
        for _ in range(MAX_UP):
            p = os.path.join(d, PRIVATE_DIR)
            if os.path.isdir(p):
                return p
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    return None


def require(*starts: str | None) -> str:
    """The studio's history folder, or exit 2 with the fix. For tools that write."""
    h = home(*starts)
    if not h:
        env = os.environ.get("CINE_MEMORY")
        if env:
            print(f"REFUSED: CINE_MEMORY names {env}, which is not a folder.", file=sys.stderr)
        else:
            print(f"REFUSED: {REFUSAL}", file=sys.stderr)
        raise SystemExit(2)
    return h


def resolve(rel: str, *starts: str | None) -> tuple[str, str | None]:
    """Where `memory/<rel>` is. Returns (state, path): 'studio' or 'template' with the path, 'missing'
    when a studio folder exists and does not hold it, 'unchecked' when no studio folder was found."""
    rel = rel[len("memory/"):] if rel.startswith("memory/") else rel
    if rel.startswith(("/", "..")) or "/../" in rel:
        return "missing", None
    h = home(*starts)
    if h and os.path.exists(os.path.join(h, rel)):
        return "studio", os.path.join(h, rel)
    t = os.path.join(TEMPLATES, rel)
    if os.path.exists(t):
        return "template", t
    return ("missing" if h else "unchecked"), None


def shipped_extra() -> list[str]:
    """Files in the plugin's own memory/ that are not templates. Empty is the only right answer."""
    out = []
    for root, _dirs, files in os.walk(TEMPLATES):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), TEMPLATES)
            if rel not in SHIPPED and not f.startswith("."):
                out.append(rel)
    return sorted(out)


def init(start: str | None = None) -> str:
    """Create `_cine-memory/` in `start` (default: the working folder) with the templates. Never overwrites."""
    base = os.path.abspath(start or os.getcwd())
    target = os.path.join(base, PRIVATE_DIR)
    for sub in ("episodes", os.path.join("episodes", "_promoted"), "proposals"):
        os.makedirs(os.path.join(target, sub), exist_ok=True)
    for rel in sorted(SHIPPED - {"README.md"}):
        dst = os.path.join(target, rel)
        if not os.path.exists(dst) and os.path.exists(os.path.join(TEMPLATES, rel)):
            shutil.copy(os.path.join(TEMPLATES, rel), dst)
    led = os.path.join(target, "LEDGER.md")
    if not os.path.exists(led):
        open(led, "w", encoding="utf-8").write(
            "# Studio ledger — what changed in our rules, when, and what forced it\n\n"
            "One line per landed change. Newest first.\n\n"
            "| Date | Change | Files | Evidence |\n|---|---|---|---|\n")
    return target


def selftest() -> int:
    fails: list[str] = []

    def check(name: str, cond: bool, info: str = "") -> None:
        print(f"  {'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  — {info}"))
        if not cond:
            fails.append(name)

    real_env, real_cwd = os.environ.get("CINE_MEMORY"), os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as td:
            td = os.path.realpath(td)
            job = os.path.join(td, "work", "videos", "clients", "brand", "04-projects", "job-01001")
            elsewhere, envdir = os.path.join(td, "elsewhere"), os.path.join(td, "studio-history")
            for d in (job, elsewhere, envdir):
                os.makedirs(d)
            os.environ.pop("CINE_MEMORY", None)
            os.chdir(elsewhere)

            check("nothing anywhere: no home", home(job) is None)
            check("with no home, a pointer into the history is 'unchecked', never 'found'",
                  resolve("memory/LEDGER.md", job) == ("unchecked", None))
            check("a template resolves from the plugin's own folder",
                  resolve("memory/episodes/_TEMPLATE.md", job)[0] == "template")
            import contextlib, io
            said = io.StringIO()
            try:
                with contextlib.redirect_stderr(said):
                    require(job)
                refused = False
            except SystemExit as e:
                refused = e.code == 2 and "CINE_MEMORY" in said.getvalue()
            check("a tool that writes is refused when there is no home (exit 2)", refused)

            made = init(os.path.join(td, "work", "videos"))
            check("init creates `_cine-memory/` with the templates and an empty ledger",
                  os.path.isfile(os.path.join(made, "episodes", "_TEMPLATE.md"))
                  and os.path.isfile(os.path.join(made, "proposals", "README.md"))
                  and os.path.isfile(os.path.join(made, "LEDGER.md")))
            open(os.path.join(made, "LEDGER.md"), "a", encoding="utf-8").write("| 2026-01-01 | kept | x | y |\n")
            init(os.path.join(td, "work", "videos"))
            check("init never overwrites a ledger that is already there",
                  "kept" in open(os.path.join(made, "LEDGER.md"), encoding="utf-8").read())
            check("a `_cine-memory/` folder above the job is the home", home(job) == made)
            check("a start may be a file that does not exist yet", home(os.path.join(job, "09-qa", "x.md")) == made)
            check("an unrelated start finds nothing", home(elsewhere) is None)
            os.chdir(job)
            check("the working folder is always a starting point", home() == made)
            os.chdir(elsewhere)
            check("the studio's ledger resolves in the studio's folder",
                  resolve("memory/LEDGER.md", job) == ("studio", os.path.join(made, "LEDGER.md")))
            check("a dated note the studio does not hold is 'missing' once a home exists",
                  resolve("memory/episodes/2026-01-01-nothing.md", job) == ("missing", None))
            open(os.path.join(td, "work", "videos", "outside.md"), "w").write("not history")   # a real file, one level up
            check("SABOTAGE a pointer that climbs out of the folder is refused, though the file exists",
                  resolve("memory/../outside.md", job) == ("missing", None)
                  and resolve("memory/episodes/../../outside.md", job) == ("missing", None))

            os.environ["CINE_MEMORY"] = envdir
            check("CINE_MEMORY wins over a `_cine-memory/` folder", home(job) == envdir)
            os.environ["CINE_MEMORY"] = os.path.join(td, "no-such-folder")
            check("CINE_MEMORY naming no folder is no home (it does not fall through to another one)",
                  home(job) is None)
            os.environ.pop("CINE_MEMORY")
            # (3.0.0) the config setup.py writes: after CINE_MEMORY, before the `_cine-memory/` search
            real_home = os.environ.get("CINE_HOME")
            cfg_home = os.path.join(td, "cfg-home"); os.makedirs(cfg_home)
            cfg_mem = os.path.join(td, "cfg-memory"); os.makedirs(cfg_mem)
            open(os.path.join(cfg_home, "config.json"), "w").write('{"memory_dir": "%s"}' % cfg_mem)
            os.environ["CINE_HOME"] = cfg_home
            check("SABOTAGE memory_dir in the config wins over a `_cine-memory/` folder", home(job) == cfg_mem)
            os.environ["CINE_MEMORY"] = envdir
            check("CINE_MEMORY still wins over the config", home(job) == envdir)
            os.environ.pop("CINE_MEMORY")
            if real_home is None:
                os.environ.pop("CINE_HOME")
            else:
                os.environ["CINE_HOME"] = real_home

            # the two tools of the loop really ask this module
            ep = os.path.join(made, "episodes", "2026-01-02-sample.md")
            open(ep, "w", encoding="utf-8").write(
                "# 2026-01-02 · sample · mode B · a test note\n\n## What broke\n- the hook card was unreadable at 2 seconds\n\n"
                "## What fixed it\n- hold the hook card for 3 seconds\n")
            base_env = {k: v for k, v in os.environ.items() if k not in ("CINE_MEMORY", "CINE_CLIENTS")}

            def tool(args: list[str], cwd: str, env_dir: str | None = None):
                env = dict(base_env)
                if env_dir:
                    env["CINE_MEMORY"] = env_dir
                return subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, cwd=cwd, env=env)

            cons = os.path.join(HERE, "consolidate.py")
            r = tool([cons, "--dry-run"], elsewhere)
            check("consolidate.py refuses when there is no home", r.returncode == 2 and "REFUSED" in r.stderr,
                  f"rc={r.returncode} {r.stderr[-200:]}")
            r = tool([cons, "--dry-run"], job)
            check("consolidate.py reads the notes from a `_cine-memory/` above the working folder",
                  r.returncode == 0 and "1 episode(s)" in r.stdout and "hook card was unreadable" in r.stdout,
                  f"rc={r.returncode} {(r.stdout + r.stderr)[-300:]}")
            r = tool([cons, "--dry-run"], elsewhere, made)
            check("consolidate.py reads the notes from CINE_MEMORY",
                  r.returncode == 0 and "1 episode(s)" in r.stdout and "hook card was unreadable" in r.stdout,
                  f"rc={r.returncode} {(r.stdout + r.stderr)[-300:]}")
            before = set(os.listdir(os.path.join(TEMPLATES, "proposals")))
            r = tool([cons], job)
            written = [d for d in os.listdir(os.path.join(made, "proposals")) if os.path.isdir(os.path.join(made, "proposals", d))]
            check("consolidate.py writes its proposal into the studio's folder, and nothing into the plugin's",
                  r.returncode == 0 and len(written) == 1
                  and set(os.listdir(os.path.join(TEMPLATES, "proposals"))) == before, f"rc={r.returncode} {r.stderr[-200:]}")
            ev = os.path.join(HERE, "evaluate_promotion.py")
            if written:
                r = tool([ev, written[0]], job)
                check("evaluate_promotion.py finds that proposal in the studio's folder",
                      r.returncode in (0, 1) and "evaluate_promotion" in r.stdout and "no such proposal" not in (r.stdout + r.stderr).lower(),
                      f"rc={r.returncode} {(r.stdout + r.stderr)[-300:]}")
                r = tool([ev, written[0]], elsewhere)
                check("evaluate_promotion.py refuses when there is no home", r.returncode == 2 and "REFUSED" in r.stderr,
                      f"rc={r.returncode} {r.stderr[-200:]}")
                # its client-locks gate reads the studio's client folder, not the plugin's alone (v2.53.0 took
                # every real client out of the plugin, so a gate that read only the plugin checked nothing)
                open(os.path.join(made, "proposals", written[0], "PROPOSAL.md"), "w", encoding="utf-8").write(
                    "## Edit 1\n- file: zzbrand.md\n- change: loosen the firmness wording, it need not stay frozen\n"
                    "- evidence: 2026-01-02-sample\n")
                r = tool([ev, written[0]], job)
                check("with no client profile outside the plugin, the client-locks gate says NOT CHECKED and blocks",
                      r.returncode == 1 and "NOT CHECKED" in r.stdout and "overlap a lock" not in r.stdout,
                      f"rc={r.returncode} {r.stdout[-300:]}")
                cdir = os.path.join(td, "work", "videos", "_cine-clients")
                os.makedirs(cdir)
                open(os.path.join(cdir, "zzbrand.md"), "w", encoding="utf-8").write(
                    "# zzbrand\n\n## 0. Hard locks\n\n1. hard lock: firmness wording frozen for every script\n")
                r = tool([ev, written[0]], job)
                check("a hard lock in a profile OUTSIDE the plugin blocks a proposal that touches it",
                      r.returncode == 1 and "overlap a lock" in r.stdout, f"rc={r.returncode} {r.stdout[-300:]}")
                r = tool([ev, written[0]], elsewhere, made)
                check("run from a folder with no `_cine-clients/` above it, the gate still finds the one beside the "
                      "history folder", r.returncode == 1 and "overlap a lock" in r.stdout,
                      f"rc={r.returncode} {r.stdout[-300:]}")

        extra = shipped_extra()
        check("the plugin's own memory/ holds the templates and nothing else", not extra, f"unexpected: {extra[:8]}")
        check("every template the plugin promises is there",
              all(os.path.isfile(os.path.join(TEMPLATES, r)) for r in SHIPPED), str(sorted(SHIPPED)))
    finally:
        os.chdir(real_cwd)
        if real_env is None:
            os.environ.pop("CINE_MEMORY", None)
        else:
            os.environ["CINE_MEMORY"] = real_env
    print(f"SELFTEST: {'OK' if not fails else 'FAIL'} ({len(fails)} failed)")
    return 1 if fails else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("where", help="print the studio's history folder")
    w.add_argument("--from", dest="starts", nargs="*", default=[])
    i = sub.add_parser("init", help=f"create `{PRIVATE_DIR}/` with the templates (never overwrites)")
    i.add_argument("--from", dest="start", default=None, help="the folder to create it in (default: the working folder)")
    a = ap.parse_args()
    if a.cmd == "where":
        h = home(*a.starts)
        if not h:
            print(f"not found: {REFUSAL}", file=sys.stderr)
            return 1
        print(h)
        return 0
    if a.cmd == "init":
        print(init(a.start))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
