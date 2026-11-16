#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""doctor.py — is this machine ready? What a concept needs first, then what later steps need.

  doctor.py            # the report; exit 1 when something a concept needs is RED
  doctor.py --json
  doctor.py --selftest

NEEDED FOR A CONCEPT (red stops you):
  Python 3.9+ as `python3` (the hooks call it) · the spend gate answering exactly as hooks.json runs it ·
  no old `cinematography` plugin installed or enabled beside this one (two gates on one call) ·
  a studio folder and config (setup) · a client profile · the environment variables that override the config ·
  the open job and whether it expired.
NEEDED LATER (amber, with the fix):
  the picture/sound check packages · ffmpeg · Node (HyperFrames / GSAP titles) · DaVinci Resolve Studio ·
  your Higgsfield connector named for the gate (before the first paid call).

It reads; it never installs, enables, uninstalls or edits anything, and it never writes your home folder
(the gate is run against a throwaway one).
"""
from __future__ import annotations
import argparse, glob, json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cine_home  # noqa: E402

SKILL = os.path.dirname(HERE)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL))
OLD = cine_home.OLD_NAME
ACTIVE_MAX_AGE_S = 24 * 3600            # gate.py's own limit
MAX_DEPTH = 7                           # how deep ~/.claude/plugins is searched for an old plugin.json

OK, AMBER, RED = "ok", "amber", "red"


def row(level, area, msg, fix=""):
    return {"level": level, "area": area, "msg": msg, "fix": fix}


# ---------- needed for a concept ----------

def check_python() -> list:
    out = []
    py = shutil.which("python3")
    if not py:
        return [row(RED, "python", "no `python3` on PATH: the hooks call `python3`, so the gate cannot start",
                    "install Python 3.9 or newer so `python3` runs in a new terminal")]
    r = subprocess.run([py, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], capture_output=True, text=True)
    v = r.stdout.strip()
    try:
        ok = tuple(int(x) for x in v.split(".")) >= (3, 9)
    except ValueError:
        ok = False
    out.append(row(OK if ok else RED, "python", f"python3 = {py} ({v or 'did not run'})",
                   "" if ok else "the gate needs Python 3.9 or newer as `python3`"))
    return out


def hook_commands(plugin_root: str = PLUGIN_ROOT) -> list:
    """The PreToolUse command strings that run gate.py, as hooks.json writes them."""
    d = json.load(open(os.path.join(plugin_root, "hooks", "hooks.json"), encoding="utf-8"))
    return [h["command"] for e in d["hooks"]["PreToolUse"] for h in e.get("hooks", [])
            if "gate.py" in h.get("command", "")]


def run_hook(cmd: str, payload: dict, plugin_root: str, home_dir: str) -> tuple:
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": plugin_root, "CINE_HOME": home_dir}
    for k in ("CINE_JOB", "CINE_GATE"):
        env.pop(k, None)
    r = subprocess.run(["/bin/sh", "-c", cmd], input=json.dumps(payload), capture_output=True, text=True,
                       env=env, timeout=30)
    return r.returncode, r.stdout, r.stderr


def check_hook(plugin_root: str = PLUGIN_ROOT) -> list:
    """Run the gate's hook command exactly as hooks.json writes it, twice: a read tool must come back `{}`, a paid
    tool with no job open must come back with a deny decision. Exit codes alone never pass."""
    try:
        cmds = hook_commands(plugin_root)
    except (OSError, ValueError, KeyError) as e:
        return [row(RED, "gate", f"hooks/hooks.json unreadable: {e}", "reinstall the plugin")]
    if not cmds:
        return [row(RED, "gate", "hooks.json runs no gate.py hook", "reinstall the plugin")]
    base = {"hook_event_name": "PreToolUse", "session_id": "doctor", "transcript_path": "", "cwd": os.getcwd()}
    with tempfile.TemporaryDirectory() as home_dir:
        try:
            rc, out, err = run_hook(cmds[0], {**base, "tool_name": "mcp__Higgsfield__balance", "tool_input": {}},
                                    plugin_root, home_dir)
            read_ok = rc == 0 and json.loads(out or "null") == {}
            rc2, out2, err2 = run_hook(cmds[0], {**base, "tool_name": "mcp__Higgsfield__generate_video",
                                                 "tool_input": {"params": {"prompt": "x"}}}, plugin_root, home_dir)
            dec = ((json.loads(out2 or "null") or {}).get("hookSpecificOutput") or {}).get("permissionDecision")
        except (ValueError, subprocess.TimeoutExpired, OSError) as e:
            return [row(RED, "gate", f"the gate's hook did not answer in JSON ({type(e).__name__})",
                        "run `python3 scripts/gate.py --selftest`; reinstall the plugin if it fails")]
    if read_ok and dec == "deny":
        return [row(OK, "gate", "the spend gate answers as hooks.json runs it (a read passes, a paid call with no "
                                 "job open is denied)")]
    why = (err or err2 or out2 or "").strip().splitlines()[-1:] or ["no output"]
    return [row(RED, "gate", f"the spend gate did not answer as expected (read {'ok' if read_ok else 'failed'}, "
                             f"paid call decision {dec!r}): {why[0][:200]}",
                "run `python3 scripts/gate.py --selftest`; reinstall the plugin if it fails")]


def _old_plugin_jsons(plugins_dir: str) -> list:
    hits = []
    base = plugins_dir.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(plugins_dir):
        if root.count(os.sep) - base >= MAX_DEPTH:
            dirs[:] = []
        if "SKILL.md" in files and root.replace(os.sep, "/").endswith("/skills/" + OLD):   # the old skill folder itself
            hits.append(os.path.dirname(os.path.dirname(root)))
        if "plugin.json" in files and os.path.basename(root) == ".claude-plugin":
            try:
                if json.load(open(os.path.join(root, "plugin.json"), encoding="utf-8")).get("name") == OLD \
                        and os.path.dirname(root) not in hits:
                    hits.append(os.path.dirname(root))
            except (OSError, ValueError, AttributeError):
                pass
    return hits


def check_old_plugin(user_home: str | None = None) -> list:
    """RED when a plugin named `cinematography` is installed or enabled (two gates would run on one call)."""
    uh = user_home or os.path.expanduser("~")
    claude = os.path.join(uh, ".claude")
    out, unread = [], []
    plugins = os.path.join(claude, "plugins")
    if os.path.isdir(plugins):
        try:
            hits = _old_plugin_jsons(plugins)
        except OSError:
            hits, unread = [], unread + [plugins]
        for h in hits[:5]:
            out.append(row(RED, "old plugin", f"the old `{OLD}` plugin is installed: {h}",
                           f"in Claude Code run `/plugin`, find `{OLD}` and uninstall it (or `claude plugin uninstall "
                           f"{OLD}@<marketplace>`), then restart"))
        inst = os.path.join(plugins, "installed_plugins.json")
        if os.path.isfile(inst):
            try:
                txt = open(inst, encoding="utf-8").read()
                keys = [k for k in json.loads(txt).get("plugins", {}) if str(k).startswith(OLD + "@")] \
                    if isinstance(json.loads(txt), dict) else []
                for k in keys:
                    out.append(row(RED, "old plugin", f"`{k}` is listed as installed", f"`claude plugin uninstall {k}`"))
            except (OSError, ValueError, AttributeError):
                unread.append(inst)
    settings = os.path.join(claude, "settings.json")
    if os.path.isfile(settings):
        try:
            en = json.load(open(settings, encoding="utf-8")).get("enabledPlugins") or {}
            for k, v in (en.items() if isinstance(en, dict) else []):
                if str(k).startswith(OLD + "@") and v:
                    out.append(row(RED, "old plugin", f"`{k}` is enabled in {settings}",
                                   f"disable or uninstall it: `claude plugin uninstall {k}`"))
        except (OSError, ValueError, AttributeError):
            unread.append(settings)
    for u in unread:
        out.append(row(AMBER, "old plugin", f"could not read {u}, so an old `{OLD}` plugin could not be ruled out",
                       f"look for `{OLD}` in `/plugin` and uninstall it if present"))
    desk = glob.glob(os.path.join(uh, "Library", "Application Support", "Claude", "local-agent-mode-sessions",
                                  "*", "*", "rpm", "*", "skills", OLD, "SKILL.md"))
    if desk:
        out.append(row(AMBER, "old plugin", f"the Claude desktop app's sessions carry an old `{OLD}` skill "
                                            f"({len(desk)} cop{'y' if len(desk) == 1 else 'ies'})",
                       f"remove the `{OLD}` plugin in the desktop app's plugin settings"))
    return out or [row(OK, "old plugin", f"no old `{OLD}` plugin installed or enabled")]


def check_config(home_dir: str | None = None) -> list:
    hd = home_dir or cine_home.home(merge=False)
    cfg = cine_home.config(hd)
    out = []
    if not cfg:
        out.append(row(AMBER, "studio", f"no studio config ({os.path.join(hd, 'config.json')})",
                       "run `/cinematographly:setup` (makes a studio folder and the config)"))
    else:
        for k in ("clients_dir", "memory_dir", "jobs_dir"):
            d = cine_home.config_dir(k, hd)
            out.append(row(OK if d else AMBER, "studio", f"{k}: {d or cfg.get(k) or 'not set'}"
                           + ("" if d else " (missing)"), "" if d else "re-run `/cinematographly:setup`"))
    for env, key in (("CINE_CLIENTS", "clients_dir"), ("CINE_MEMORY", "memory_dir"), ("CINE_HOME", None)):
        v = os.environ.get(env)
        if not v:
            continue
        c = cine_home.config_dir(key, hd) if key else None
        if c and os.path.abspath(os.path.expanduser(v)) != c:
            out.append(row(AMBER, "studio", f"{env}={v} overrides the configured {key} ({c})",
                           f"unset {env} to use the config, or point the config at it"))
        else:
            out.append(row(OK, "studio", f"{env}={v} (set in the environment; it wins over the config)"))
    clients = os.environ.get("CINE_CLIENTS") or cine_home.config_dir("clients_dir", hd)
    if clients and os.path.isdir(clients):
        profs = sorted(f[:-3] for f in os.listdir(clients) if f.endswith(".md") and not f.startswith("_"))
        out.append(row(OK if profs else AMBER, "studio",
                       f"client profiles: {', '.join(profs[:8]) or 'none'}" + (" …" if len(profs) > 8 else ""),
                       "" if profs else f"copy _TEMPLATE.md in {clients} to <client>.md and answer its section 0"))
    return out


def check_hookless(home_dir: str | None = None) -> list:
    """(3.1) Hookless is set only by `studio_setup.py --hookless`; while it is on, approvals are not checked."""
    hd = home_dir or cine_home.home(merge=False)
    if cine_home.config(hd).get("hookless") is True:
        return [row(AMBER, "approvals", "hookless is ON: approvals are recorded UNVERIFIED (for Cowork / evals, where "
                                         "the plugin's hooks never run)",
                    "if hooks do run here, turn it off: `studio_setup.py --hooked`")]
    return []


def check_job(home_dir: str | None = None) -> list:
    hd = home_dir or cine_home.home(merge=False)
    p = os.path.join(hd, "active-job")
    if not os.path.isfile(p):
        return [row(OK, "job", "no job open (a concept starts with `/cinematographly:new-job`)")]
    try:
        rec = json.load(open(p, encoding="utf-8"))
        rec = rec if isinstance(rec, dict) else {}
    except (OSError, ValueError):
        rec = {}
    job, ts = rec.get("job") or "?", rec.get("ts") or 0
    try:
        age = time.time() - float(ts)
    except (TypeError, ValueError):
        age = ACTIVE_MAX_AGE_S + 1
    if not os.path.isdir(job):
        return [row(AMBER, "job", f"the open job's folder is gone ({job})", "open another: `gate.py open <job-dir>`")]
    if age > ACTIVE_MAX_AGE_S:
        return [row(AMBER, "job", f"the open job expired ({int(age // 3600)} h old): {os.path.basename(job)}",
                    f"re-open it: `python3 scripts/gate.py open {job}`")]
    return [row(OK, "job", f"open: {os.path.basename(job)} ({int(age // 60)} min ago)")]


def check_migration(user_home: str | None = None, home_dir: str | None = None) -> list:
    """The old home (~/.cinematography) is merged into the new one the first time the gate runs; say so."""
    if os.environ.get("CINE_HOME") and home_dir is None:
        return []
    hd = home_dir or cine_home.home(merge=False)
    old = cine_home.old_home(user_home)
    if not os.path.isdir(old):
        return []
    if os.path.isfile(os.path.join(hd, cine_home.MARKER)):
        return [row(OK, "settings", f"the old settings ({old}) were merged into {hd}")]
    names = sorted(f for f in os.listdir(old) if not f.startswith("."))[:6]
    return [row(OK, "settings", f"old settings in {old} ({', '.join(names) or 'empty'}) are merged into {hd} the first "
                                f"time the gate runs; nothing there is overwritten")]


def _old_connectors(user_home: str | None, hd: str) -> list:
    if os.path.isfile(os.path.join(hd, cine_home.MARKER)):
        return []
    try:
        con = json.load(open(os.path.join(cine_home.old_home(user_home), "connectors.json"), encoding="utf-8"))
        return list(con.get("higgsfield") or []) if isinstance(con, dict) else []
    except (OSError, ValueError):
        return []


# ---------- needed later ----------

def check_later(home_dir: str | None = None, user_home: str | None = None) -> list:
    hd = home_dir or cine_home.home(merge=False)
    out = []
    py = shutil.which("python3") or sys.executable
    probe = "import importlib.util as u; print(','.join(m for m in ('numpy','cv2','PIL') if not u.find_spec(m)))"
    r = subprocess.run([py, "-c", probe], capture_output=True, text=True)
    miss = [m for m in r.stdout.strip().split(",") if m]
    out.append(row(AMBER if miss or r.returncode else OK, "checks",
                   f"picture/sound check packages: {'missing ' + ', '.join(miss) if miss else 'present'}",
                   "run `/cinematographly:setup --install-deps`" if miss else ""))
    for tool, why in (("ffmpeg", "the clip, mix and export checks"), ("ffprobe", "reading clip lengths and rates"),
                      ("node", "HyperFrames and GSAP titles (GSAP keeps its own licence)")):
        w = shutil.which(tool)
        out.append(row(OK if w else AMBER, "tools", f"{tool}: {w or 'not found'} ({why})",
                       "" if w else f"install {tool} when you reach that step"))
    resolve = [p for p in ("/Applications/DaVinci Resolve/DaVinci Resolve.app",
                           "/Applications/DaVinci Resolve Studio/DaVinci Resolve.app") if os.path.isdir(p)]
    out.append(row(OK if resolve else AMBER, "tools", f"DaVinci Resolve: {resolve[0] if resolve else 'not found'} "
                   "(edit, titles, sound by computer control; Final Cut Pro and Premiere Pro get an XML timeline)",
                   "" if resolve else "install DaVinci Resolve Studio for the edit step, or use the XML export"))
    try:
        con = json.load(open(os.path.join(hd, "connectors.json"), encoding="utf-8"))
        hf = con.get("higgsfield") if isinstance(con, dict) else None
    except (OSError, ValueError):
        hf = None
    hf = hf or [x for x in os.environ.get("CINE_HIGGSFIELD_CONNECTORS", "").split(",") if x.strip()]
    try:
        seen = json.load(open(os.path.join(hd, "seen-connectors.json"), encoding="utf-8"))
        seen = seen if isinstance(seen, dict) else {}
    except (OSError, ValueError):
        seen = {}
    if hf:
        out.append(row(OK, "connector", f"Higgsfield connector named for the gate ({len(hf)})"))
    elif _old_connectors(user_home, hd):
        out.append(row(OK, "connector", "Higgsfield connector named in the old settings; it comes across with the merge"))
    else:
        hint = (f"; seen but not named: {', '.join(sorted(seen)[:3])} (`gate.py connectors --seen`)" if seen else "")
        out.append(row(AMBER, "connector", "no Higgsfield connector named yet — fine for a concept; a claude.ai "
                       "connector's paid calls will ask until it is named" + hint,
                       "`python3 scripts/gate.py connectors --higgsfield <uuid>` (the uuid is in the tool names)"))
    return out


def check_studio_answers(home_dir: str | None = None) -> list:
    """(3.1) The studio questions still unanswered, and rates that are undated or older than 30 days."""
    out = []
    try:
        import studio, rate_card
    except Exception:                                          # noqa: BLE001
        return out
    if studio.studio_dir():
        left = studio.unanswered(required_only=True)        # the production settings have house defaults
        out.append(row(OK if not left else AMBER, "studio",
                       "studio questions: all answered" if not left else
                       f"studio questions unanswered ({len(left)}): {', '.join(left[:6])}{' …' if len(left) > 6 else ''}",
                       "" if not left else "ask them in the chat, then `studio.py set --answers <file>` "
                                           "(answers pre-fill new clients and jobs and never approve; a studio no on music or likeness blocks export, and the monthly ceiling adds a stop)"))
    stale = 0
    try:
        for tab in (rate_card.load_table(), rate_card.load_image_table()):
            for res in tab.values():
                for e in (res.values() if isinstance(res, dict) else []):
                    if isinstance(e, dict) and rate_card.stale_note(e, rate_card.DEFAULT_STALE_DAYS):
                        stale += 1
    except SystemExit:
        stale = -1
    if stale:
        out.append(row(AMBER, "rates", "the rate table cannot be read" if stale < 0 else
                       f"{stale} rate(s) undated or older than 30 days",
                       "re-read them on your account (scripts/refresh_costs.md) into <studio>/rates-override.json"))
    return out


def first_run(rep: dict) -> list:
    """(3.1) The four first-run steps, in order, from what the checks found."""
    rows = rep["concept"] + rep["later"]
    has = lambda area, word: any(r["area"] == area and r["level"] == OK and word in r["msg"] for r in rows)  # noqa: E731
    return [("studio folder (/cinematographly:setup)", has("studio", "clients_dir")),
            ("Higgsfield connector named (gate.py connectors --higgsfield <id>)", has("connector", "named")),
            ("a client (/cinematographly:new-client, or the sample acme)", has("studio", "client profiles")),
            ("a job (/cinematographly:new-job, or /cinematographly:demo to read one first)", has("job", "open:"))]


def report(user_home: str | None = None, home_dir: str | None = None, plugin_root: str = PLUGIN_ROOT) -> dict:
    concept = check_python() + check_hook(plugin_root) + check_old_plugin(user_home) + check_config(home_dir) \
        + check_migration(user_home, home_dir) + check_hookless(home_dir) + check_job(home_dir)
    later = check_later(home_dir, user_home) + check_studio_answers(home_dir)
    return {"concept": concept, "later": later, "red": any(r["level"] == RED for r in concept + later)}


def render(rep: dict) -> str:
    mark = {OK: "  ok  ", AMBER: " AMBER", RED: "  RED "}
    lines = ["First run"] + [f"  {'✓' if done else '·'} {i}. {step}" for i, (step, done) in enumerate(first_run(rep), 1)]
    for title, key in (("Needed for a concept", "concept"), ("Needed later", "later")):
        lines.append(title)
        for r in rep[key]:
            lines.append(f"{mark[r['level']]}  {r['area']:<10} {r['msg']}")
            if r["fix"]:
                lines.append(f"{'':8}  {'':<10} → {r['fix']}")
    lines.append("RED above: fix it before the first concept." if rep["red"] else
                 "Ready for a concept: `/cinematographly:new-job <client> <slug>` (amber items can wait).")
    return "\n".join(lines)


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        uh = os.path.join(td, "user"); hd = os.path.join(td, "home")
        os.makedirs(os.path.join(uh, ".claude", "plugins")); os.makedirs(hd)
        lv = lambda rows: {r["level"] for r in rows}  # noqa: E731
        assert lv(check_old_plugin(uh)) == {OK}, check_old_plugin(uh)
        # an old plugin.json deep in the cache → red
        old = os.path.join(uh, ".claude", "plugins", "cache", "mk", OLD, "2.51.0", ".claude-plugin")
        os.makedirs(old); json.dump({"name": OLD}, open(os.path.join(old, "plugin.json"), "w"))
        assert RED in lv(check_old_plugin(uh)), "an installed old plugin is red"
        os.remove(os.path.join(old, "plugin.json"))
        # the new plugin in a folder that is still called `cinematography` (the private monorepo) is not red
        json.dump({"name": cine_home.NAME}, open(os.path.join(old, "plugin.json"), "w"))
        os.makedirs(os.path.join(os.path.dirname(old), "skills", cine_home.NAME))
        open(os.path.join(os.path.dirname(old), "skills", cine_home.NAME, "SKILL.md"), "w").write("x")
        assert lv(check_old_plugin(uh)) == {OK}, "a folder's name alone is not an old install"
        sk = os.path.join(uh, ".claude", "plugins", "marketplaces", "m", "x", "skills", OLD)
        os.makedirs(sk); open(os.path.join(sk, "SKILL.md"), "w").write("x")
        assert RED in lv(check_old_plugin(uh)), "the old skill folder (a synced or stale copy) is red"
        import shutil as _sh; _sh.rmtree(os.path.join(uh, ".claude", "plugins", "marketplaces"))
        # enabled in settings → red; unreadable settings → amber
        st = os.path.join(uh, ".claude", "settings.json")
        json.dump({"enabledPlugins": {OLD + "@mk": True, cine_home.NAME + "@x": True}}, open(st, "w"))
        r = check_old_plugin(uh)
        assert RED in lv(r) and any(OLD + "@mk" in x["msg"] for x in r), r
        json.dump({"enabledPlugins": {OLD + "@mk": False}}, open(st, "w"))
        assert lv(check_old_plugin(uh)) == {OK}, "a disabled entry is not red"
        open(st, "w").write("{not json")
        assert AMBER in lv(check_old_plugin(uh)), "could not check → amber, never ok"
        os.remove(st)
        # the gate's hook, run as hooks.json writes it
        assert lv(check_hook()) == {OK}, check_hook()
        broken = os.path.join(td, "broken")
        shutil.copytree(PLUGIN_ROOT, broken, ignore=shutil.ignore_patterns("_*", "evals", ".git"))
        gp = os.path.join(broken, "skills", cine_home.NAME, "scripts", "gate.py")
        open(gp, "w").write("import sys\nprint('{}')\n")          # answers {} to everything: reads pass, spend passes
        assert lv(check_hook(broken)) == {RED}, "a gate that allows a paid call is red, though it exits 0"
        open(gp, "w").write("raise SystemExit(3)\n")
        assert lv(check_hook(broken)) == {RED}, "a gate that cannot answer is red"
        # config and job
        assert AMBER in lv(check_config(hd)), "no config → amber with the setup command"
        for k in ("CINE_CLIENTS", "CINE_MEMORY"):
            os.environ.pop(k, None)
        cd = os.path.join(td, "clients"); os.makedirs(cd); open(os.path.join(cd, "acme.md"), "w").write("x")
        json.dump({"clients_dir": cd, "memory_dir": cd, "jobs_dir": cd}, open(os.path.join(hd, "config.json"), "w"))
        os.environ["CINE_HOME"] = hd
        r = check_config(hd)
        assert lv(r) == {OK} and any("acme" in x["msg"] for x in r), r
        os.environ["CINE_CLIENTS"] = td
        assert any(x["level"] == AMBER and "overrides" in x["msg"] for x in check_config(hd)), "env hiding the config"
        os.environ.pop("CINE_CLIENTS")
        assert lv(check_job(hd)) == {OK}
        json.dump({"job": cd, "ts": time.time() - ACTIVE_MAX_AGE_S - 60}, open(os.path.join(hd, "active-job"), "w"))
        r = check_job(hd)
        assert lv(r) == {AMBER} and "expired" in r[0]["msg"] and "gate.py open" in r[0]["fix"], r
        json.dump({"job": cd, "ts": time.time()}, open(os.path.join(hd, "active-job"), "w"))
        assert lv(check_job(hd)) == {OK}
        # the connector: amber before it is named, with the seen uuid; ok after
        os.environ.pop("CINE_HIGGSFIELD_CONNECTORS", None)
        json.dump({"5c5c5c5c-1111-4222-8333-944444444444": {"tools": ["generate_image"]}},
                  open(os.path.join(hd, "seen-connectors.json"), "w"))
        c = [x for x in check_later(hd, uh) if x["area"] == "connector"][0]
        assert c["level"] == AMBER and "5c5c5c5c" in c["msg"], c
        json.dump({"higgsfield": ["5c5c5c5c-1111-4222-8333-944444444444"]}, open(os.path.join(hd, "connectors.json"), "w"))
        assert [x for x in check_later(hd, uh) if x["area"] == "connector"][0]["level"] == OK
        # the old home: reported as merged-on-first-use, its connector counted, until the marker says it is done
        oh = cine_home.old_home(uh); os.makedirs(oh)
        json.dump({"higgsfield": ["aaaaaaaa-1111-4222-8333-944444444444"]}, open(os.path.join(oh, "connectors.json"), "w"))
        os.remove(os.path.join(hd, "connectors.json"))
        m = check_migration(uh, hd)
        assert m and "merged into" in m[0]["msg"] and "first time" in m[0]["msg"], m
        c = [x for x in check_later(hd, uh) if x["area"] == "connector"][0]
        assert c["level"] == OK and "old settings" in c["msg"], c
        open(os.path.join(hd, cine_home.MARKER), "w").write("merged")
        assert "were merged" in check_migration(uh, hd)[0]["msg"]
        assert [x for x in check_later(hd, uh) if x["area"] == "connector"][0]["level"] == AMBER, "after the merge, the new home decides"
        st = os.path.join(td, "studio"); os.makedirs(st); os.environ["CINE_STUDIO"] = st
        try:
            sr = check_studio_answers(hd)
            assert any(r["area"] == "studio" and r["level"] == AMBER and f"unanswered ({len(__import__('studio').QUESTIONS) - len(__import__('studio').OPTIONAL)})" in r["msg"] for r in sr), sr
            json.dump({"approvers": ["Sam Reyes"]}, open(os.path.join(st, "studio.json"), "w"))
            assert any(f"unanswered ({len(__import__('studio').QUESTIONS) - len(__import__('studio').OPTIONAL) - 1})" in r["msg"] for r in check_studio_answers(hd)), "an answer is counted"
        finally:
            os.environ.pop("CINE_STUDIO", None)
        fr = first_run({"concept": [row(OK, "studio", "clients_dir: x"), row(OK, "studio", "client profiles: acme")],
                        "later": [row(AMBER, "connector", "no Higgsfield connector named yet")]})
        assert [d for _, d in fr] == [True, False, True, False], fr
        json.dump({"hookless": True}, open(os.path.join(hd, "config.json"), "w"))
        assert any(r["area"] == "approvals" and r["level"] == AMBER for r in check_hookless(hd)), "hookless is shown"
        os.remove(os.path.join(hd, "config.json"))
        assert check_hookless(hd) == []
        rep = report(uh, hd)
        assert not rep["red"] and "Ready for a concept" in render(rep), render(rep)
    print("selftest OK — the gate's hook is run as hooks.json writes it and passes only on a read {} and a paid-call "
          "deny (a gate that allows or cannot answer is red); an old plugin installed or enabled is red, unreadable "
          "settings amber, a folder name alone is not; no config amber; an env override that hides the config amber; "
          "an expired job amber with the reopen command; an unnamed connector amber with the uuid the gate saw")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rep = report()
    print(json.dumps(rep, indent=1) if a.json else render(rep))
    return 1 if any(r["level"] == RED for r in rep["concept"]) else 0


if __name__ == "__main__":
    sys.exit(main())
