#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""Edge/corner-case tests for the pipeline scripts (pull_finals, build_fcpxml, master_to_jobs).
Run: python3 scripts/test_pipeline.py  (stdlib unittest, no deps, no network)."""
import os
import sys
import tempfile
import unittest
import xml.dom.minidom as minidom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pull_finals as pf          # noqa: E402
import build_fcpxml as bf         # noqa: E402
import master_to_jobs as mj       # noqa: E402


class TestPullFinals(unittest.TestCase):
    def test_ext_from_query_url(self):
        self.assertEqual(pf.ext_of({"url": "https://cdn/x.mp4?token=abc&e=1", "kind": "clip"}), "mp4")

    def test_ext_default_by_kind(self):
        self.assertEqual(pf.ext_of({"url": "https://cdn/noext", "kind": "voice"}), "wav")
        self.assertEqual(pf.ext_of({"url": "https://cdn/noext", "kind": "frame"}), "png")

    def test_ext_explicit_strips_dot(self):
        self.assertEqual(pf.ext_of({"url": "https://cdn/x", "kind": "clip", "ext": ".mov"}), "mov")

    def test_lane_mapping_all_kinds(self):
        d = tempfile.mkdtemp()
        cases = {"frame": "02-startframes", "startframe": "02-startframes", "clip": "03-clips",
                 "video": "03-clips", "broll": "04-broll", "voice": "05-voice", "audio": "05-voice",
                 "music": "06-music"}
        for kind, lane in cases.items():
            p = pf.dest_path(d, {"shot": "S1", "subject": "x", "model": "m", "kind": kind, "url": "u.mp4"})
            self.assertIn(os.sep + lane + os.sep, p, kind)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            pf.dest_path(tempfile.mkdtemp(), {"shot": "S1", "kind": "sfx", "url": "u"})

    def test_version_autoincrement(self):
        d = tempfile.mkdtemp()
        it = {"shot": "S1-C1", "subject": "host", "model": "kling", "kind": "clip", "url": "u.mp4"}
        p1 = pf.dest_path(d, it); open(p1, "w").close()
        p2 = pf.dest_path(d, it); open(p2, "w").close()
        p3 = pf.dest_path(d, it)
        self.assertTrue(p1.endswith("v1.mp4") and p2.endswith("v2.mp4") and p3.endswith("v3.mp4"))


class TestSortAndTime(unittest.TestCase):
    def test_shot_order(self):
        toks = ["CTA", "S2-C1", "S1-C2", "S0B", "INTRO", "S10-C1", "B2", "S1-C1", "S2B", "B1"]
        ordered = sorted(toks, key=bf.sort_key)
        self.assertEqual(ordered[0], "INTRO")
        self.assertEqual(ordered[1], "S0B")
        self.assertEqual(ordered[-1], "CTA")
        # scenes ascending, S1 before S2 before S10, B-roll after scenes, before CTA
        self.assertLess(ordered.index("S1-C1"), ordered.index("S2-C1"))
        self.assertLess(ordered.index("S2-C1"), ordered.index("S10-C1"))
        self.assertLess(ordered.index("S10-C1"), ordered.index("B1"))
        self.assertLess(ordered.index("B2"), ordered.index("CTA"))
        self.assertLess(ordered.index("S1-C1"), ordered.index("S1-C2"))

    def test_rt_rational(self):
        # (3.0.0) reduced rationals on whole frames; 23.976 is frame-exact
        self.assertEqual(bf.rt(5, 30), "5s")
        self.assertEqual(bf.rt(5, 24), "5s")
        self.assertEqual(bf.rt(1 / 30.0, 30), "1/30s")
        self.assertEqual(bf.rt(2.5, 30), "5/2s")
        self.assertEqual(bf.rt(1.001, "24000/1001"), "1001/1000s")

    def test_xml_escape(self):
        self.assertEqual(bf.xml('A & B <c> "d"'), "A &amp; B &lt;c&gt; &quot;d&quot;")

    def test_shot_token(self):
        self.assertEqual(bf.shot_token("/x/03-clips/S3-C2_guest_kling_v2.mp4"), "S3-C2")


class TestBuildFcpxmlIntegration(unittest.TestCase):
    def _proj(self, clips=None, broll=None, voices=None):
        d = tempfile.mkdtemp()
        for lane, names in (("03-clips", clips or []), ("04-broll", broll or []), ("05-voice", voices or [])):
            os.makedirs(os.path.join(d, lane), exist_ok=True)
            for n in names:
                open(os.path.join(d, lane, n), "w").close()
        return d

    def _run(self, d, argv):
        old = sys.argv
        # A timeline resolution is now REQUIRED (no house format — references/delivery-format.md),
        # so every invocation names one. Tests that specifically exercise the refusal pass their own.
        base = ["build_fcpxml.py", "--project", d, "--slug", "T"]
        if not any(f in argv for f in ("--format", "--width", "--height")):
            base += ["--format", "vertical-1080"]
        sys.argv = base + argv
        try:
            bf.main()
        finally:
            sys.argv = old
        p = os.path.join(d, "07-edit", "T-rough.fcpxml")
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None

    def test_no_clips_errors(self):
        with self.assertRaises(SystemExit):
            self._run(self._proj(), ["--bpm", "0"])

    def test_broll_only_ok(self):
        doc = self._run(self._proj(broll=["S0B_intro_cinema_v1.mp4"]), ["--bpm", "0"])
        self.assertIn("S0B", doc)
        minidom.parseString(doc)  # well-formed

    def test_voice_without_matching_clip_ignored(self):
        # voice for S9 but no S9 clip → must not crash, S9 vo not placed
        doc = self._run(self._proj(clips=["S1-C1_v_kling_v1.mp4"], voices=["S9-C1_p_andre_v1.wav"]),
                        ["--bpm", "0"])
        self.assertIn("S1-C1", doc)
        self.assertNotIn("S9-C1-vo", doc)

    def test_bpm_markers_and_wellformed(self):
        doc = self._run(self._proj(clips=["S1-C1_v_kling_v1.mp4", "S2-C1_p_kling_v1.mp4"],
                                   voices=["S1-C1_v_tasha_v1.wav"]), ["--bpm", "120"])
        self.assertIn("<marker", doc)
        minidom.parseString(doc)

    def test_special_chars_filename_encoded_wellformed(self):
        # '&' in a filename must be URL-encoded in the file:// src and keep the XML well-formed
        doc = self._run(self._proj(clips=["S1-C1_R&D_kling_v1.mp4"]), ["--bpm", "0"])
        self.assertIn("R%26D", doc)          # special char URL-encoded in the src path
        minidom.parseString(doc)             # still well-formed

    def test_no_underscore_filename_does_not_crash(self):
        doc = self._run(self._proj(clips=["randomclip.mp4"]), ["--bpm", "0"])
        self.assertIsNotNone(doc)
        minidom.parseString(doc)

    def test_fps_comes_from_the_preset(self):
        # ⛔ the default used to be 30 while vertical-1080's fps_default is 24
        doc = self._run(self._proj(clips=["S1-C1_v_kling_v1.mp4"]), ["--bpm", "0"])
        self.assertIn('frameDuration="1/24s"', doc)

    def test_no_fps_and_no_preset_refuses(self):
        doc = self._run(self._proj(clips=["S1-C1_v_kling_v1.mp4"]),
                        ["--width", "1080", "--height", "1920"])
        self.assertIsNone(doc)

    def test_noaudio_sibling_replaces_its_original(self):
        # strip_embedded_audio.py writes `<name>_noaudio.<ext>` next to the original — one shot, not two
        doc = self._run(self._proj(clips=["S1-C1_v_kling_v1.mp4", "S1-C1_v_kling_v1_noaudio.mp4",
                                          "S2-C1_p_kling_v1.mp4"]), ["--bpm", "0"])
        self.assertIn("S1-C1_v_kling_v1_noaudio.mp4", doc)
        self.assertNotIn("S1-C1_v_kling_v1.mp4", doc)
        self.assertIn("S2-C1_p_kling_v1.mp4", doc)


class TestMasterToJobs(unittest.TestCase):
    def test_multiline_and_elements(self):
        txt = ("[S1-C1] video host\nelements: @Host Business, @lake-house\n"
               "prompt: line one,\nline two.\n\n[S2B] broll\nprompt: drone.\n")
        jobs = mj.parse(txt)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["elements"], ["@Host Business", "@lake-house"])
        self.assertEqual(jobs[0]["prompt"], "line one, line two.")
        self.assertEqual(jobs[0]["subject"], "host")
        self.assertEqual(jobs[1]["kind"], "broll")
        self.assertIsNone(jobs[1]["subject"])
        self.assertEqual(jobs[1]["elements"], [])

    def test_missing_prompt_and_case(self):
        jobs = mj.parse("[S3] IMAGE\n")
        self.assertEqual(jobs[0]["prompt"], "")
        self.assertEqual(jobs[0]["kind"], "image")

    def test_ignores_leading_noise(self):
        jobs = mj.parse("# title\nsome notes\n\n[S1-C1] video\nprompt: hi.\n")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["shot"], "S1-C1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
