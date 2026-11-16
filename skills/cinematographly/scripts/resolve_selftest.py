#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
resolve_selftest.py — prove DaVinci Resolve is ready for automation (MCP or script).

Run this ON THE MAC, from a terminal, with DaVinci Resolve **Studio** open. It talks to Resolve
through the external scripting API — the same API the MCP server inside Resolve Studio 21.1 exposes
through `run_script` — creates a throwaway project + timeline + marker, then deletes the project.
The MCP route itself is verified by read-back: references/environments.md §3.

Preconditions (the script checks/º explains each):
  1. DaVinci Resolve **Studio** 18.5+ is OPEN (the free edition cannot be scripted).
  2. Resolve ▸ Preferences ▸ System ▸ General ▸ **"External scripting using" = Local**, then restart Resolve.
  3. Python **3.10–3.12** (Resolve's supported range).

Usage:
  python3 resolve_selftest.py
  python3 resolve_selftest.py --keep            # don't delete the test project
  python3 resolve_selftest.py --import /path/to/a/clip.mp4   # also test a media import
"""
import argparse
import os
import sys

MAC_API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
MAC_LIB = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"


def bootstrap():
    """Make `import DaVinciResolveScript` work, via env vars or the standard macOS paths."""
    api = os.environ.get("RESOLVE_SCRIPT_API", MAC_API)
    lib = os.environ.get("RESOLVE_SCRIPT_LIB", MAC_LIB)
    mod = os.path.join(api, "Modules")
    if mod not in sys.path:
        sys.path.append(mod)
    os.environ.setdefault("RESOLVE_SCRIPT_API", api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
    try:
        import DaVinciResolveScript as dvr  # noqa
        return dvr, None
    except Exception as e:
        return None, e


def ok(msg):
    print(f"  ✅ {msg}")


def bad(msg, fix=None):
    print(f"  ❌ {msg}")
    if fix:
        print(f"     → {fix}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="keep the test project instead of deleting it")
    ap.add_argument("--import", dest="import_path", help="also import this media file to test ingest")
    a = ap.parse_args()

    print("DaVinci Resolve automation self-test")
    print("-" * 40)

    # 0) Python version
    v = sys.version_info
    if (3, 10) <= (v.major, v.minor) <= (3, 12):
        ok(f"Python {v.major}.{v.minor} (in the supported 3.10–3.12 range)")
    else:
        bad(f"Python {v.major}.{v.minor} — Resolve scripting wants 3.10–3.12",
            "run this with a 3.10–3.12 interpreter (e.g. `python3.11 resolve_selftest.py`)")

    # 1) module bootstrap
    dvr, err = bootstrap()
    if dvr is None:
        # ⚠ Resolve 21.1 (2026-09-08) moved EXTERNAL scripting access — which is exactly what this
        # file does — behind Studio, per two of three secondary sources; a third says only console
        # scripting survives in the free edition. No PRIMARY yet (editing-and-audio.md, the 21.1
        # note). This message already said "Install Resolve Studio", so the guidance is unchanged —
        # but on 21.1 a failure here may mean the EDITION, not the path.
        bad(f"Could not import DaVinciResolveScript ({err})",
            "Install Resolve Studio (on 21.1+ external scripting appears to REQUIRE it — "
            "unverified, see editing-and-audio.md); if it's in a non-default path set RESOLVE_SCRIPT_API / "
            "RESOLVE_SCRIPT_LIB. macOS default lib: " + MAC_LIB)
        return 2
    ok("Loaded the DaVinciResolveScript module")

    # 2) connect to a running Resolve
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        bad("scriptapp('Resolve') returned None — can't reach Resolve",
            "Open DaVinci Resolve **Studio**, and set Preferences ▸ System ▸ General ▸ "
            "'External scripting using' = Local, then restart Resolve.")
        return 3
    try:
        ok(f"Connected to Resolve — version {resolve.GetVersionString()}")
    except Exception:
        ok("Connected to Resolve")

    pm = resolve.GetProjectManager()
    if pm is None:
        bad("No ProjectManager", "restart Resolve")
        return 4

    # 3) create a throwaway project + timeline + marker
    name = "cine_selftest_DELETE_ME"
    proj = pm.CreateProject(name) or pm.LoadProject(name)
    if proj is None:
        bad("Could not create a project",
            "a project with this name may exist and be open; close it or pass --keep")
        return 5
    ok(f"Created project '{name}'")

    mp = proj.GetMediaPool()
    tl = mp.CreateEmptyTimeline("selftest_timeline")
    if tl is None:
        bad("Could not create a timeline")
        return 6
    ok("Created an empty timeline")

    added = tl.AddMarker(0, "Blue", "beat", "self-test", 1)
    markers = tl.GetMarkers() or {}
    if added and markers:
        ok(f"Added a timeline marker (now {len(markers)} marker(s)) — markers + timeline API work")
    else:
        bad("AddMarker/GetMarkers didn't behave as expected (non-fatal)")

    if a.import_path:
        p = os.path.abspath(os.path.expanduser(a.import_path))
        items = mp.ImportMedia([p]) if os.path.exists(p) else None
        if items:
            ok(f"Imported media into the pool: {os.path.basename(p)}")
        else:
            bad(f"Media import failed for {p}", "check the path exists and is a supported format")

    # 4) cleanup
    if a.keep:
        ok(f"Left project '{name}' in place (--keep)")
    else:
        pm.CloseProject(proj)
        pm.DeleteProject(name)
        ok(f"Cleaned up (deleted '{name}')")

    print("-" * 40)
    print("✅ PASS — Resolve is scriptable from outside.")
    print("Next: on Resolve Studio 21.1+ the MCP server ships inside Resolve — check it with")
    print("      `claude mcp get \"DaVinci Resolve\"` and verify it per references/environments.md §3.")
    print("      Renders are QUEUED (render-mp4.py) and started by a person — never by a script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
