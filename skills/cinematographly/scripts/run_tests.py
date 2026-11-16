#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""run_tests.py — one command over every script: compile, --help, self-checks, unit suites.

The scripts are the skill's enforcement layer; this is the enforcement layer's own check. Run after
touching any script, before committing skill changes, and as part of Claude Code setup.

  python3 run_tests.py            # everything
  python3 run_tests.py --quick    # compile + --help only (no unit suites)

Exit codes: 0 all green · 1 failures · 2 environment error.
"""
from __future__ import annotations
import argparse, os, py_compile, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# Console-paste scripts run inside Resolve's injected environment — importable/compilable, but
# executing --help would fail on the missing `resolve` global by design. Compile-only.
CONSOLE_PASTE = {"render-mp4.py", "resolve-production-console.py", "resolve_selftest.py"}
SUITES = ["test_estimate_duration.py", "test_pipeline.py", "test_gate.py", "test_preproduction.py",
          "test_console_scripts.py"]   # the console-paste scripts EXECUTED against a fake Resolve
# Scripts carrying their own built-in check, run as `<script> --selftest` in the full pass.
SELFTEST = ["cine_home.py", "shot_manifest.py", "review_pack.py", "deliver.py", "studio.py", "new_client.py", "demo.py", "new_job.py", "studio_setup.py", "doctor.py", "next_step.py", "cut_plan.py", "timeline_export.py", "sheet_split.py", "genlab.py", "agent_audit.py", "beat_plan.py", "clip_qa.py", "develop.py", "gate.py", "prompt_lint.py", "provenance.py", "rate_card.py", "frameio_comments_to_edl.py", "lipsync_check.py", "pixabay_search.py", "refsource.py", "eval_lint.py", "eval_run.py", "board.py", "breakdown.py", "shotlist.py", "storyboard.py", "animatic.py",
            "series_registry.py", "series_batch.py", "series_join.py", "skill_audit.py",
            "name_lint.py", "script_score.py", "qa_log.py", "export_qc.py",
            "claims_lint.py", "batch_plan.py", "ledger.py", "pull_metrics.py",
            "stage_timer.py", "film_breakdown.py", "film_db.py", "motion_track.py", "sequence_lint.py",
            "contact_sheet.py", "blocking.py", "blocking_rig.py", "blocking_kit.py", "blocking_camera.py",
            "blocking_env.py", "blocking_look.py", "job_tier.py", "pull_finals.py", "shot_graph.py", "replicate.py",
            "action_points.py", "motion_qa.py", "mix_qa.py", "sfx_conform.py", "look_qa.py", "grade_luts.py",
            "title_card.py", "title_qa.py", "aerial_qa.py", "flyover.py", "music_fit.py", "composer.py", "soundoff.py", "srt_qa.py", "world.py",
            "native.py", "shell_gate.py", "fusion_titles.py", "resolve_library.py", "switches.py",
            "region_repair.py", "fanout.py", "gen_index.py", "client_files.py", "memory_home.py", "build_bundle.py",
            "cost_model.py"]


def tool_versions() -> str:
    """The tools a result depends on, in one line, so a run names its environment. Four checks that a release
    had recorded as passing were red on ffmpeg 8.1.1 with OpenCV 5.0.0 [measured 2026-11-10], and the tools of
    the passing run were written down nowhere."""
    parts = [f"Python {sys.version.split()[0]}"]
    for mod in ("cv2", "numpy", "yaml"):
        try:
            parts.append(f"{mod} {__import__(mod).__version__}")
        except Exception:                                                   # noqa: BLE001
            parts.append(f"{mod} ABSENT")
    try:
        head = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=20).stdout.split("\n")[0]
        parts.append("ffmpeg " + (head.split()[2] if head.startswith("ffmpeg version") else "version unreadable"))
    except Exception:                                                       # noqa: BLE001
        parts.append("ffmpeg ABSENT")
    return " · ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    # (3.0.0) every test runs against a throwaway home: a studio's own ~/.cinematographly/config.json (clients_dir,
    # memory_dir, jobs_dir) must never change what a self-test finds, and no test may write the real home.
    _home = None
    if not os.environ.get("CINE_HOME"):
        _home = tempfile.TemporaryDirectory(prefix="cine-home-")
        os.environ["CINE_HOME"] = _home.name
    tools = tool_versions()
    print(f"Tools: {tools}")

    scripts = sorted(f for f in os.listdir(HERE) if f.endswith(".py") and f != os.path.basename(__file__))
    fails = []

    # ⛔ SELFTEST is hand-maintained, so a new script's built-in check was simply never run — the
    # check that does not run is the oldest failure in this project (found 2026-09-30, when
    # film_breakdown.py's selftest sat unexecuted behind a green RESULT line). A script that offers
    # --selftest and is not listed now FAILS the suite, which is the only way a list stays current.
    declared = set(SELFTEST) | set(SUITES) | CONSOLE_PASTE
    for f in scripts:
        if f in declared or f.startswith("_"):
            continue
        try:
            src = open(os.path.join(HERE, f), encoding="utf-8").read()
        except OSError:
            continue
        if '"--selftest"' in src or "'--selftest'" in src:
            fails.append((f, "carries a --selftest that run_tests never runs — add it to SELFTEST"))

    for f in scripts:
        try:
            py_compile.compile(os.path.join(HERE, f), doraise=True)
            ok = "compile"
        except py_compile.PyCompileError as e:
            fails.append((f, f"COMPILE: {e}")); print(f"  [FAIL] {f:<32} compile"); continue
        if f in CONSOLE_PASTE or f.startswith("test_"):
            print(f"  [ ok ] {f:<32} {ok} (console-paste/suite — no --help run)"); continue
        r = subprocess.run([sys.executable, os.path.join(HERE, f), "--help"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            fails.append((f, f"--help exited {r.returncode}: {r.stderr.strip()[:100]}"))
            print(f"  [FAIL] {f:<32} --help"); continue
        head = open(os.path.join(HERE, f), encoding="utf-8").read(2500).lower()
        if f in ("script_score.py", "slop_check.py", "contact_sheet.py",
                 "frameio_comments_to_edl.py", "pixabay_search.py", "lipsync_check.py",
                 "clip_qa.py", "gate.py", "prompt_lint.py", "develop.py", "provenance.py") \
                and not any(k in head for k in ("what it cannot do", "what this tool is not",
                                                "cannot see", "mechanical checks only")):
            print(f"  [warn] {f:<32} honest-limits section not found in docstring head")
        print(f"  [ ok ] {f:<32} compile + --help")

    if not a.quick:
        for s in SELFTEST:
            p = os.path.join(HERE, s)
            if not os.path.exists(p):
                fails.append((s, "selftest script missing")); continue
            r = subprocess.run([sys.executable, p, "--selftest"], capture_output=True, text=True, timeout=120)
            ok = r.returncode == 0
            print(f"  [{'PASS' if ok else 'FAIL'}] {s:<32} built-in selftest")
            if not ok:
                fails.append((s, (r.stderr or r.stdout).strip()[-200:]))
        for s in SUITES:
            p = os.path.join(HERE, s)
            if not os.path.exists(p):
                fails.append((s, "suite missing")); continue
            r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=300)
            ok = r.returncode == 0
            print(f"  [{'PASS' if ok else 'FAIL'}] {s:<32} unit suite")
            if not ok:
                fails.append((s, r.stderr.strip()[-200:]))
        # scripts/INDEX.md is generated, and a generated file nobody checks goes stale exactly as the
        # hand-written counts did ("45 scripts" in a folder of 88, found 2026-11-10). So the suite
        # fails while the index does not match the files. The fix is one command, named in the output.
        r = subprocess.run([sys.executable, "-B", os.path.join(HERE, "gen_index.py"), "--check"],
                           capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] {'INDEX.md':<32} generated index matches the files")
        if not ok:
            why = [ln for ln in r.stdout.splitlines() if ln.startswith(("STALE", "FINDING"))]
            fails.append(("INDEX.md", " · ".join(why)[:300] or (r.stderr or r.stdout).strip()[-200:]))

    print("-" * 60)
    if fails:
        print(f"RESULT: FAIL ({len(fails)})")
        for f, why in fails:
            print(f"  {f}: {why}")
        print(f"  ran on: {tools}")
        return 1
    print(f"RESULT: OK — {len(scripts)} scripts"
          + ("" if a.quick else f", {len(SUITES)} suites, {len(SELFTEST)} selftests"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
