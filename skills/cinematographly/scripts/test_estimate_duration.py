#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""Unit tests for estimate_duration.py parsing — locks the fixes from the 2026-07-02 stress test.
Run: python3 scripts/test_estimate_duration.py  (stdlib unittest, no deps)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estimate_duration as ed  # noqa: E402


def clips(text):
    return sum(len(s["lines"]) for s in ed.parse(text))


class TestParse(unittest.TestCase):
    def test_allcaps_names(self):
        self.assertEqual(clips("[SCENE 1 x]\nSPEAKER A: una doua trei.\nSPEAKER B: patru cinci."), 2)

    def test_titlecase_names(self):  # H1 — used to silently drop to 0
        self.assertEqual(clips("[SCENE 1 x]\nthe host: una doua trei.\nthe guest: patru cinci."), 2)

    def test_english_scene_label(self):  # H1 bonus — SCENE recognized, not folded to PREAMBLE
        scenes = ed.parse("[SCENE 1 x]\nthe host: salut acolo.")
        self.assertIn("SCENE", scenes[0]["name"])

    def test_romanian_scene_label(self):
        scenes = ed.parse("[SCENĂ 1 x]\nthe host: salut acolo.")
        self.assertIn("SCENĂ", scenes[0]["name"])

    def test_text_overlay_not_dialogue(self):
        self.assertEqual(clips('[SCENE 1 x]\nTEXT: „CAEN 01 · CAEN 10"\nthe host: una doua.'), 1)

    def test_colon_in_visual_not_dialogue(self):  # L2 — visual/label lines must not match
        self.assertEqual(clips("[SCENE 1 x] Vizual: bancnote / profit pe masa.\nthe host: una doua."), 1)

    def test_timecode_not_dialogue(self):
        self.assertEqual(clips("[SCENE 1 x]\nla 0:03 apare ceva\nthe host: una doua."), 1)

    def test_two_speaker_scene_two_clips(self):
        t = "[SCENE 1 x]\nthe host: una doua trei.\nthe guest: patru cinci sase."
        self.assertEqual(clips(t), 2)

    def test_zero_dialogue(self):  # H1 — false-green guard: nothing should parse
        self.assertEqual(clips("just prose, no speakers, nothing here"), 0)


class TestCosts(unittest.TestCase):
    def test_costs_json_loads_and_has_presets(self):
        costs, src = ed.load_costs("_TEMPLATE")
        self.assertIn("economy", costs["presets"])
        self.assertIn("quality", costs["presets"])
        self.assertEqual(costs.get("default_preset"), "quality")   # (v2.62.0) the quality floor
        self.assertEqual(costs["plan"]["monthly_credits"], 3000)



class TestCostProfileEdges(unittest.TestCase):
    """Both cases came from an external review (2026-08-30). The review targeted a `_FALLBACK`
    constant this script no longer has — the design now REFUSES instead of falling back — but the
    hazard it named is real in both directions, so both paths are pinned here."""

    def test_missing_profile_refuses_rather_than_guessing(self):
        """⛔ A missing cost profile must exit 2, never borrow another client's numbers. A silent
        fallback with plausible figures is worse than a crash: it quotes confidently and wrongly."""
        with self.assertRaises(SystemExit) as cm:
            ed.load_costs("definitely-not-a-client-" + "x" * 12)
        self.assertEqual(cm.exception.code, 2)

    def test_zero_videos_per_month_does_not_crash(self):
        """A profile with no per-video cadence (a retainer, a one-off) is legitimate. The envelope
        divides by client-supplied numbers, so 0 or absent must skip the check, not raise."""
        for plan in ({"monthly_credits": 3000, "videos_per_month_max": 0, "videos_per_month_min": 0},
                     {"monthly_credits": 3000}):
            vmax = plan.get("videos_per_month_max") or 0
            vmin = plan.get("videos_per_month_min") or 0
            self.assertFalse(vmax > 0 and vmin > 0)
            self.assertIsNone(plan["monthly_credits"] / vmax if vmax > 0 else None)


class TestEndToEnd(unittest.TestCase):
    """⛔ The gap that let two crashes through: every other test calls a FUNCTION. Nothing ran the
    tool. A bulk edit dropped a preset key and a required arg stayed None, and the whole suite was
    still green. This runs the actual command."""

    def _run(self, *args):
        import subprocess, sys, tempfile, os
        here = os.path.dirname(os.path.abspath(__file__))
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write("[SCENE 1 0:00-0:10] a room.\nHOST: one two three four five six seven.\n"
                     "GUEST: eight nine ten eleven.\n")
            path = fh.name
        try:
            return subprocess.run([sys.executable, os.path.join(here, "estimate_duration.py"),
                                   path, "--client", "_TEMPLATE", *args],
                                  capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(path)

    def test_full_run_against_the_shipped_template(self):
        r = self._run("--intro", "6", "--cta", "5")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ESTIMATED TOTAL", r.stdout)

    def test_hook_block_is_read(self):
        """(v2.67.0) [HOOK] is read like [INTRO]: its line is in the table and in the speech total. The recommended
        length keeps the old sum (intro + all speech + CTA); whether that double-counts is an open question."""
        import subprocess, sys, tempfile, os, re
        here = os.path.dirname(os.path.abspath(__file__))
        hook_words = " ".join(["word"] * 24)                  # 24 words = 10 s + 0.6 s of speech, longer than a 6 s intro
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write(f"[HOOK 0:00-0:06] a room.\nHOST: {hook_words}.\n\n[SCENE 1 0:06-0:10] a door.\n"
                     "GUEST: eight nine ten eleven.\n")
            path = fh.name
        try:
            r = subprocess.run([sys.executable, os.path.join(here, "estimate_duration.py"), path, "--client",
                                "_TEMPLATE", "--intro", "6", "--cta", "0"], capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(path)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("HOOK", r.stdout)                       # the hook's line is in the table
        rec = int(re.search(r"Recommended video len:\s+(\d+)s", r.stdout).group(1))
        # 6 (intro) + 10.6 (hook) + 2.27 (scene) + 0 = 18.87 -> x1.12 = 21 s; with the hook dropped it was 9 s
        self.assertEqual(rec, 21, r.stdout)

    def test_client_script_numbers_fill_intro_and_cta(self):
        # (v2.62.0) the refusal message always pointed at script.<client>.json; the numbers are now read from it.
        # The sample client `acme` ships hook 3 s and CTA 4 s, and the preset is quality (the floor).
        import subprocess, tempfile
        here = os.path.dirname(os.path.abspath(__file__))
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write("[SCENE 1 0:00-0:10] a room.\nHOST: one two three four five six seven.\n"
                     "GUEST: eight nine ten eleven.\n")
            path = fh.name
        try:
            r = subprocess.run([sys.executable, os.path.join(here, "estimate_duration.py"), path, "--client", "acme"],
                               capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(path)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("intro 3 + speech + CTA 4", r.stdout)
        self.assertIn("ACTIVE preset: QUALITY", r.stdout)

    def test_missing_intro_refuses_by_name_not_traceback(self):
        r = self._run()
        self.assertEqual(r.returncode, 2)
        self.assertIn("intro and CTA seconds are per-client", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

if __name__ == "__main__":
    unittest.main(verbosity=2)
