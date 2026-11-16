#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""region_repair.py — masked-region repair: fix ONE region of an otherwise good generated take, and prove that
nothing else in the shot changed.

WHY. A festival-winning AI film (Fukushima) cleaned up its takes this way:
paint the one wrong region of a generated clip solid black, hand the masked clip to the video model as the clip
to edit (here: Seedance 2.5, `mode: video_edit`, the clip as `video_references`) with a prompt that says "rebuild
only the black area", and get the same shot back with that region fixed — a wrong gauge, a mangled prop, a bad
hand. Roto was locked out of this plugin; the owner allows it for this one job, built as "tracked box first,
plus SAM 2 for organic shapes" (assets/project-switches.json, the advanced-VFX entry).

⛔ This tool never calls Higgsfield or any network service. It PREPARES the masked plate and a prompt stub, and
CHECKS what comes back. The repair call goes through gate.py like any other generation. All edits and SFX are
done in DaVinci Resolve. The final blend is ALWAYS a Fusion comp in Resolve, built by computer control (driving
the Resolve window), never through the scripting API (the computer-control rule). `fusion` writes what that comp
needs: the matte, the track and a node-by-node recipe. `composite` writes a PREVIEW only (PREVIEW-…), never
imported into Resolve as footage. `qa --render` measures Resolve's render of the comp.

  track CLIP --box x,y,w,h [--at S] [--engine box|sam2] [--frames A-B]
        follow the region through the clip → REGION-<label>.json, MASKS-<label>/ (or .mkv), CHECK-<label>.png
  mask --region REGION-<label>.json --contains "…" [--pad 12] [--feather 0] [--ref-image F …] [--allow-lost]
        → MASKED-<label>.mp4 (the plate: the region pure black), REPAIR-<label>.json, REPAIR-<label>.prompt.md
  composite REPAIRED --job REPAIR-<label>.json [--out PREVIEW-<label>.mov] [--feather 8] [--retime]
        [--audio source|repaired|none]
        → a PREVIEW of the blend (its name must start with PREVIEW-): only the masked region taken from the
          model's clip, every pixel outside it the source's. Never imported into Resolve as footage.
  fusion --job REPAIR-<label>.json --repaired REPAIRED [--feather 8] [--retime] [--label L]
        → FUSION-<label>/: matte/%06d.png (grown, feathered, numbered from 0 at the work-range start),
          track.csv + track.json, RECIPE.md (the Fusion comp, node by node), fusion.json
  qa --render RENDER.mov --repaired REPAIRED --job REPAIR-<label>.json [--cut A-B]
        → QA-<label>.json, QA-<label>.png on Resolve's render of the comp; exit 1 on any FAIL, with the reason
  qa --composite PREVIEW-<label>.mov --repaired REPAIRED --job REPAIR-<label>.json      (the same, on the preview)
  --job takes the REPAIR-<label>.json, or the folder that holds it.
  --selftest

Usage
-----
  python3 scripts/region_repair.py track S3_take2.mp4 --box 812,420,140,96 --at 1.5 --label s3-gauge
  python3 scripts/region_repair.py track S3_take2.mp4 --box 42%,39%,7%,9% --frames 36-150 --label s3-gauge
  python3 scripts/region_repair.py track S3_take2.mp4 --engine sam2 --point 880,470 --at 1.5 \\
          --sam2-checkpoint ~/sam2/checkpoints/sam2.1_hiera_large.pt --sam2-config configs/sam2.1/sam2.1_hiera_l.yaml
  python3 scripts/region_repair.py mask --region repair/REGION-s3-gauge.json \\
          --contains "a round brass pressure gauge, white face, black numbers 0 to 10, red needle resting at 4"
  (fill the stub, prompt_lint.py it, make the call through gate.py, download the result)
  python3 scripts/region_repair.py composite repair/s3-gauge_repaired.mp4 --job repair/REPAIR-s3-gauge.json
          (optional: a preview, repair/PREVIEW-s3-gauge.mov, measured with qa --composite)
  python3 scripts/region_repair.py fusion --job repair/REPAIR-s3-gauge.json --repaired repair/s3-gauge_repaired.mp4
  (build the comp in Resolve's Fusion page by computer control, following repair/FUSION-s3-gauge/RECIPE.md;
   render the whole clip from Resolve)
  python3 scripts/region_repair.py qa --render repair/RENDER-s3-gauge.mov \\
          --repaired repair/s3-gauge_repaired.mp4 --job repair/REPAIR-s3-gauge.json
  then a contact sheet of the render (contact_sheet.py) before anyone sees it.

track
-----
  --box x,y,w,h on the frame at --at seconds (default 0), in pixels or each value with % of the frame.
  --engine box (default): OpenCV's main module only. Lucas-Kanade flow on features inside the box with a
    forward-backward check and a RANSAC similarity (position and scale), re-centred on the anchor's look;
    template matching plus ECC when the flow fails. Every frame gets a confidence (the box's correlation with
    the anchor and with the previous frame). A frame that fails is marked LOST — its box is null, never
    invented — and the tracker searches wider on each later frame to re-acquire the region by its look.
    It tracks forwards and backwards from --at. The boxes are lightly smoothed in time (--smooth passes;
    the raw box is kept beside each one).
  --engine sam2: the `sam2` package (facebookresearch, the video predictor), only if it is importable, with
    --sam2-checkpoint and --sam2-config, prompted with --point x,y and/or the box. Without it: exit 2 with the
    install steps. This tool never downloads a package or a weight.
  --frames A-B: the source frames the cut uses. Work is limited to them plus --handles (12 frames each side),
    never under 4 s when the clip allows (video_edit wants a source of at least 4 s, motion-design.md §2.4),
    rounded up to whole seconds [ASSUMED: the call takes whole seconds and must match the plate]. The range is
    recorded, and `qa --cut` refuses a later, longer cut that runs past it.
  Exit 1 when any frame is lost (the files are still written, so the check sheet can be read).

mask
----
  The plate: the work range of the source, same size, frame rate, frame count and sound, the region (the
  tracked mask grown by --pad px) filled pure black, H.264 CRF 10 (the format the upload takes).
  --feather softens the black outward only: the grown region itself stays pure black. Refuses lost frames
  unless --allow-lost (they stay unmasked, on purpose: the repair switches off on those frames). Each
  --ref-image is hashed and its provenance sidecar read (provenance.py); a missing one or an ai-generated one is
  a loud warning, because the house rule is no AI images as references and prompt_lint/gate decide.
  REPAIR-<label>.prompt.md is a STUB in our own words, never a finished prompt: frontmatter for seedance_2_5
  `mode: video_edit` with the plate as `video_references`, optional image references for what belongs in the
  region, and blocks that say: keep the first frame and every pixel outside the black area; keep the timing,
  the camera, the light and its changes, and the sound; rebuild only the black area; what it must contain and
  how it moves with the camera (from the track).

composite (a PREVIEW only)
---------
  The final blend is a Fusion comp built in Resolve by computer control, so this output is a
  PREVIEW. Its file name must start with PREVIEW- (default: PREVIEW-<label>.mov beside the job; any other name
  is refused), its sidecar says "preview": true, and it is never imported into Resolve as footage.
  Scales the model's clip to the source size (a different aspect is refused: the picture was reframed and the
  mask no longer lines up), refuses a frame count that differs from the plate's by more than one unless
  --retime, and takes ONLY the masked region from it: alpha 1 deep inside the grown region, a smoothstep ramp
  of --feather px INSIDE its edge, 0 everywhere outside, so every pixel outside the mask is the source's. The
  ramp runs over the pad, where the source's pixels are good; a feather wider than the pad is warned. The
  output is the source's full length: frames outside the work range are the source's frames. Source sound by
  default (stream-copied when the container allows). Writes `<out>.repair.json` beside it.
    .mov → ProRes 4444, qscale 1 (the default; round trip within 1–2 levels)
    .mkv → FFV1 RGB, lossless (the exact proof)
    .mp4 → H.264 CRF 10 (lossy everywhere: warned)

fusion (what the Fusion comp needs — the deliverable blend)
------
  Writes FUSION-<label>/ beside the job (or under --out):
    matte/%06d.png  the matte exactly as composite blends it: the tracked mask grown by the job's pad
                    (region_hard), a smoothstep ramp of --feather px inside the edge (inner_alpha), 8-bit, the
                    full source size, the value in R, G, B and alpha alike. Numbered from 0 at the work-range
                    start, so the Loader needs no trim; it sits at Global In = the work-range start (recorded as
                    global_offset). A frame left unmasked (--allow-lost) is black.
    track.csv/.json per frame: the region's centre in Fusion's coordinates (x / width, 1 − y / height), its size
                    against the frame, its scale against the first tracked frame; lost frames flagged. For keying
                    a Transform by hand only: alignment is not automated yet.
    RECIPE.md       the node-by-node build in the Fusion page (MediaIn1, a Loader for the repaired clip, a Loader
                    for the matte, Merge with the matte as Effect Mask on Luminance, MediaOut1), the checks, the
                    render and the qa command, with the paths and frame numbers filled in.
    fusion.json     what qa --render checks against: the job, the repaired clip and the matte (sha256), the feather.
  Same refusals as composite (aspect, frame count). With --retime it also writes repaired-conformed.mov (ProRes
  4444, the source size, mapped to the plate's frames) and the recipe loads that instead.

qa (every frame measured, the first and the last included)
--
  --render FILE: Resolve's render of the Fusion comp — the whole source clip, same size and frame rate. No
    composite sidecar: identity is checked against the job's source and masks and the repaired clip and matte
    fusion recorded (FUSION-<label>/fusion.json); the pad comes from the job, the feather from the FUSION record;
    the drift tolerance from the render's codec (probed; anything but ProRes or FFV1 is held to H.264's).
  --composite FILE: the tool's PREVIEW (reads its .repair.json).
  (a) drift outside the mask: in the model's raw clip (how much it changed elsewhere: WARN, it is discarded) and
      in the measured file (should be ~0). Above the codec's tolerance it is a WARN, printed first with its
      numbers: drift outside the region is reported, never blocking, and changes neither the verdict nor the exit
      code (for now: revisit after the first real job).
  (b) the seam, PER SIDE (left, right, top, bottom bands of the pad just inside the edge) and PER CHANNEL
      (R, G, B and luma), signed — opposite errors on two edges cannot cancel. FAIL over SEAM_MAX levels.
  (c) inside against surround: sharpness (Laplacian variance), grain (robust noise sigma), black level (2nd
      percentile) and saturation, each against the source's ring AND the source's own region — a patch that is
      too sharp, too clean or at the wrong black level against both is warned (content differs, so WARN)
  (d) the sheet QA-<label>.png: the worst seam frames plus the first and last, cropped to the region — source,
      the model's clip, the measured file (render or preview), |difference| x8, the same +2 stops and -2 stops —
      because a seam that hides at normal exposure shows when pushed. No words on the sheet: the layout is in the JSON.
  (e) temporal flicker inside the mask against the surround (and a one-frame pop), compared with the
      source's own; texture boil (WARN)
  (f) frame count, frame rate and duration: the measured file against the source (FAIL), the model's clip
      against the plate
  (g) the region came back still black, or with a black rim on any side → FAIL
  (h) coverage: deep inside the region, where the model's clip and the source differ, the measured file must be
      the model's clip. FAIL on frames where it is nearer the source (the matte or a Loader is off), and FAIL
      when the model's frame before or after matches better (the repaired clip sits one frame late or early).
  plus the hashes: the source, the masks, the job and the model's clip must be the ones composite (or fusion)
  used.

Exit codes: 0 pass / done · 1 findings or refused (lost frames, a mismatch, a composite not named PREVIEW-…,
any qa FAIL; drift never sets it) · 2 usage, IO or a missing dependency (numpy, OpenCV, ffmpeg/ffprobe; SAM 2
for --engine sam2).

⛔ WHAT IT CANNOT DO — read the check sheet, the qa sheet and a contact sheet before anyone sees the result.
  * qa cannot say the repair is RIGHT. It proves the outside is untouched and measures the seam, the texture,
    the flicker and the black. Whether the gauge now reads 4, whether the hand has five fingers, whether the prop
    is the client's — that is a human read of the frames, at speed, in the cut with its neighbours.
  * The box engine follows a rectangle: position and scale, not rotation or shape. It covers more than the
    defect, so the model rebuilds the box's background too. Organic shapes (hands, hair, cloth) want
    --engine sam2 or a larger pad. A region with no texture cannot be followed and is reported lost. The
    template fallback needs the box inside the frame; the flow works on a box partly out of it. Occlusion is
    marked lost and re-acquired by look only.
  * SAM 2 segments; it does not understand the shot. Its edges boil from frame to frame; the qa flicker and
    boil checks see the result, not the cause. The selftest cannot run SAM 2 without its package and a
    checkpoint: it runs the glue against a stand-in and says so.
  * Mattes are hard: motion blur, hair, smoke and transparency are not separated.
  * The seam is measured in the pad, which assumes the pad holds good source pixels (the tracked region holds
    the defect). With --pad under 4 the band reaches into the defect and the seam reads high.
  * The texture checks compare content that legitimately differs (a gauge against a wall), so they warn and
    never fail; they are not per brightness band.
  * Colour: 8-bit RGB working space for 8-bit sources (16-bit for deeper ones); the matrix and range come from
    the file's tags, and an untagged file is ASSUMED BT.709 at 720 lines and above (BT.601 below), recorded.
    A variable-frame-rate clip is warned and not supported.
  * It does not upload, call, approve or lint. prompt_lint.py lints the stub; gate.py makes the call.
  * It does not build the Fusion comp. RECIPE.md is followed in Resolve by a person, or by Claude through
    computer control; qa --render sees the render, not the node tree. Alignment (a shift or re-crop of the
    model's clip against the source) is not automated: track.csv is there to key a Transform by hand.
  * The Fusion page's frame numbers are ASSUMED to start at 0 on the clip's first frame (the whole clip on the
    timeline, untrimmed); the recipe's checks on the first and last frame of the work range confirm it.
  * Thresholds marked [ASSUMED] are set on synthetic clips, not calibrated on real repairs.

THRESHOLDS [ASSUMED unless noted]: LOST_CONF 0.50, PREV_MIN 0.55, REACQ_NCC 0.72, VIS_MIN 0.25 (track);
HANDLES 12 frames, MIN_PLATE_S 4.0 (vendor deck, not measured), MAX_PLATE_S 20 (vendor deck); drift tolerance
(a WARN, provisional) mean/p99.9 levels: lossless 0/1, ProRes 0.5/2, H.264 1.0/6; COVER_DIFF 12 levels,
COVER_MIN 0.5, OFFSET_RATIO 0.5; SEAM_MAX 3.0, SEAM_PEAK 6.0 levels; RIM_PX 4,
RIM_FAIL 0.30; BLACK_Y 12; STILL_BLACK_FAIL 0.50, WARN 0.15; texture ratios SHARP 0.5–2.0, NOISE 0.6–1.67,
black level ±10 levels, saturation 0.67–1.5; FLICKER_ABS 1.5, FLICKER_REL 2.0, POP_ABS 6.0, POP_REL 3.0;
BOIL_REL 2.0, BOIL_ABS 1.5; raw drift WARN at 4.0 signed / 8.0 mean absolute.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

TOOL = "region_repair.py"
SCHEMA = 2                    # 2 = the 2.49 rebuild (per-side seam, texture, slam, ranges)

# ---- thresholds (see the docstring; [ASSUMED] unless a source is named) ------------------------------------
ANALYSIS_MAX = 960            # the tracker's working size: the long side, px
ANALYSIS_CAP = 1920           # ... never above this, even for a small box
BOX_MIN_AN = 40               # a box's short side at the working size, px, when the clip allows
FLOW_MIN_PTS = 8              # features that must agree before the flow step is trusted
FB_MAX = 1.0                  # forward-backward error, px
LOST_CONF = 0.50              # [ASSUMED] below this confidence the frame is lost
PREV_MIN = 0.55               # [ASSUMED] correlation with the previous frame's box
REACQ_NCC = 0.72              # [ASSUMED] correlation with the anchor needed to re-acquire
VIS_MIN = 0.25                # [ASSUMED] share of the box inside the frame
ANCHOR_MIN = 0.30             # [ASSUMED] the region must still look somewhat like itself on the anchor frame
STEP_SCALE = 0.04             # [ASSUMED] the most the box may grow or shrink in one frame
SCALE_RANGE = (0.4, 2.5)      # [ASSUMED] the box against its size on the anchor frame
MIXED_INLIERS = 0.75          # [ASSUMED] median inlier share under this = the box holds two motions
CONF_GOOD = 0.80              # sheet colour: green at and above
HANDLES = 12                  # [ASSUMED] frames each side of the cut (VES handbook examples run 4–8)
MIN_PLATE_S = 4.0             # [VENDOR · Seedance 2.5 deck, motion-design.md §2.4 — not measured here]
MAX_PLATE_S = 20.0            # [VENDOR · same deck: "under 20 s"]
MAX_REFS = 5                  # [VENDOR · same deck: 1–5 images with a video edit]
DRIFT_TOL = {"ffv1": (0.0, 1.0), "prores": (0.5, 2.0), "h264": (1.0, 6.0)}   # [ASSUMED] (mean, p99.9) levels
# Author, 2026-11-05: "Region repair failures: should a failed drift check block a take, or only report it? —
# report it. Not sure." So drift is a WARN, never a FAIL and never the exit code. PROVISIONAL: revisit after the
# first real job.
DRIFT_NOTE = "drift outside the region (reported, not blocking for now)"
PREVIEW_PREFIX = "PREVIEW-"   # author, 2026-11-05: the tool's composite is a preview; the blend is a Fusion comp
FUSION_FEATHER = 8.0          # the matte's ramp inside the edge, px (composite's default too)
COVER_DIFF = 12.0             # [ASSUMED] luma levels: where the model's clip and the source differ this much, a
COVER_MIN_PX = 30             #   pixel decides whose picture the result shows; frames with fewer are not judged
COVER_MIN = 0.5               # [ASSUMED] share of deciding pixels that must be nearer the model's clip
OFFSET_RATIO = 0.5            # [ASSUMED] the model's neighbour frame matching this much better = a 1-frame offset
OFFSET_MIN = 2.0              # [ASSUMED] levels: a median error under this is already a match
RAW_DRIFT_SIGNED = 4.0        # [ASSUMED] WARN: the model shifted the picture outside the region
RAW_DRIFT_ABS = 8.0           # [ASSUMED]
SEAM_MAX = 3.0                # [ASSUMED] levels, median over frames of a side's signed step, any channel
SEAM_PEAK = 6.0               # [ASSUMED] levels, 90th percentile of a side's per-frame step (WARN)
SEAM_MIN_PX = 20              # a side with fewer band pixels is not measured
RIM_PX = 4                    # the rim: the band this many px inside the edge
RIM_FAIL = 0.30               # [ASSUMED] share of a side's rim black in the model's clip and not in the source
BLACK_Y = 12.0                # [ASSUMED] luma (0–255, RGB) under which a pixel counts as black
STILL_BLACK_FAIL = 0.50       # [ASSUMED] share of the region still black (beyond the source's own)
STILL_BLACK_WARN = 0.15       # [ASSUMED]
RING_MIN = 12                 # the surround: px outside the edge
SHARP_LO, SHARP_HI = 0.5, 2.0       # [ASSUMED] Laplacian variance ratio, patch / reference
NOISE_LO, NOISE_HI = 0.6, 1.67      # [ASSUMED] noise sigma ratio
NOISE_FLOOR = 0.5                   # a reference noise under this is too clean to judge against
BLACK_LEVEL_DIFF = 10.0             # [ASSUMED] levels, 2nd percentile of luma
SAT_LO, SAT_HI = 0.67, 1.5          # [ASSUMED] mean saturation ratio
FLICKER_ABS, FLICKER_REL = 1.5, 2.0  # [ASSUMED] std of the frame-to-frame change of (patch − surround)
POP_ABS, POP_REL = 6.0, 3.0          # [ASSUMED] one frame's jump, levels, and against the source's largest
BOIL_ABS, BOIL_REL = 1.5, 2.0        # [ASSUMED] mean frame-to-frame change inside the region


class Refused(Exception):
    """A finding or a refusal: exit 1."""


class Usage(Exception):
    """Usage, IO or a dependency: exit 2."""


_JSON = [False]


def say(*x):
    print(*x, file=sys.stderr if _JSON[0] else sys.stdout)


def warn(msg):
    print(f"⚠ {msg}", file=sys.stderr)


# ---- dependencies -------------------------------------------------------------------------------------------
def deps():
    """numpy and OpenCV (the main module; no contrib trackers are used), or (None, None)."""
    try:
        import numpy as np
        import cv2
    except Exception:
        return None, None
    return np, cv2


def need_np():
    np, cv2 = deps()
    if np is None:
        raise Usage("numpy and OpenCV are required: python3 -m pip install numpy opencv-python "
                    "(the main module is enough; opencv-contrib is not needed)")
    return np, cv2


def need_ff():
    miss = [b for b in ("ffmpeg", "ffprobe") if not shutil.which(b)]
    if miss:
        raise Usage(f"{' and '.join(miss)} not found on PATH — install ffmpeg (macOS: brew install ffmpeg; "
                    f"Debian/Ubuntu: apt install ffmpeg)")


SAM2_HELP = """SAM 2 is not importable here ({why}).
This tool never downloads packages or weights. To use --engine sam2, install it yourself:
  python3 -m pip install 'torch>=2.5.1' 'torchvision>=0.20.1'
  git clone https://github.com/facebookresearch/sam2.git
  cd sam2 && python3 -m pip install -e .
  cd checkpoints && ./download_ckpts.sh        # or fetch one checkpoint, e.g. sam2.1_hiera_large.pt
then run with
  --engine sam2 --sam2-checkpoint <sam2>/checkpoints/sam2.1_hiera_large.pt --sam2-config configs/sam2.1/sam2.1_hiera_l.yaml
(the config name is resolved inside the sam2 package). Or use --engine box."""


def sam2_import():
    """(builder, torch, why): the video-predictor builder and torch, or (None, None, the reason)."""
    try:
        import torch  # noqa: F401
        from sam2.build_sam import build_sam2_video_predictor
        return build_sam2_video_predictor, torch, ""
    except Exception as e:                       # ImportError, or a broken install
        return None, None, f"{type(e).__name__}: {e}"


# ---- small utilities ----------------------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path):
    if not os.path.isfile(path):
        raise Usage(f"{path}: not found")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        raise Usage(f"{path}: not valid JSON ({e})")


def write_json(path, d):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def file_rec(path, base):
    p = os.path.abspath(path)
    try:
        rel = os.path.relpath(p, base)
    except ValueError:
        rel = p
    return {"path": p, "rel": rel}


def resolve(rec, base, what):
    for p in (os.path.join(base, rec.get("rel") or "") if rec.get("rel") else "", rec.get("path") or ""):
        if p and os.path.exists(p):
            return p
    raise Usage(f"{what} not found (looked for {rec.get('rel')!r} beside the record and {rec.get('path')!r})")


def label_of(path):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", os.path.splitext(os.path.basename(path))[0]).strip("-.") or "region"


def spans(frames):
    out = []
    for f in sorted(frames):
        if out and f == out[-1][1] + 1:
            out[-1][1] = f
        else:
            out.append([f, f])
    return out


def spans_txt(frames):
    return ", ".join(f"{a}" if a == b else f"{a}–{b}" for a, b in spans(frames)) or "none"


def r4(x):
    return None if x is None else round(float(x), 4)


# ---- probing and ffmpeg I/O ---------------------------------------------------------------------------------
MATRIX_SCALE = {"bt709": "bt709", "smpte170m": "smpte170m", "bt470bg": "bt470", "bt601": "bt601",
                "bt2020nc": "bt2020", "bt2020c": "bt2020", "fcc": "fcc", "smpte240m": "smpte240m"}
_BAD_TAG = ("", "unknown", "reserved", "unspecified")
# The names `setparams` takes for the two tags tag_filter() sets. ffprobe's `gamma22` and `gamma28` are its `bt470m`
# and `bt470bg`; a name it does not know is left to the output option alone.
_SP_PRIMARIES = ("bt709", "bt470m", "bt470bg", "smpte170m", "smpte240m", "film", "bt2020", "smpte428", "smpte431",
                 "smpte432", "jedec-p22", "ebu3213")
_SP_TRANSFER = {**{k: k for k in ("bt709", "smpte170m", "smpte240m", "linear", "log100", "log316", "iec61966-2-4",
                                  "bt1361e", "iec61966-2-1", "bt2020-10", "bt2020-12", "smpte2084", "smpte428",
                                  "arib-std-b67")}, "gamma22": "bt470m", "gamma28": "bt470bg"}


def tag_filter(color):
    """The `setparams` filter that puts a file's primaries and transfer on its frames, or "" when neither has a
    name the filter knows.

    ⛔ The output options -color_primaries and -color_trc are not enough on their own. ffmpeg 8.1.1 drops both
    for raw frames on a pipe, which is how every writer here is fed: the file is written with neither tag, the
    next probe reads it as untagged, and a repaired clip no longer carries its source's two tags
    [measured 2026-11-10 · ffmpeg 8.1.1 · H.264 .mp4 and .mov, ProRes .mov, FFV1 .mkv, 8- and 16-bit input,
    three tag sets: kept in 0 of 18 with the options alone, in 18 of 18 with this filter]. Range and matrix
    survive as options, so they stay options."""
    parts = []
    if color.get("primaries") in _SP_PRIMARIES:
        parts.append(f"color_primaries={color['primaries']}")
    if _SP_TRANSFER.get(color.get("transfer")):
        parts.append(f"color_trc={_SP_TRANSFER[color['transfer']]}")
    return "setparams=" + ":".join(parts) if parts else ""


def _frac(s):
    try:
        a, b = str(s).split("/")
        return float(a) / float(b) if float(b) else 0.0
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0.0


_FPS_PASS = []


def fps_pass():
    """`-fps_mode passthrough` on ffmpeg 5+, `-vsync passthrough` before it: every decoded frame, no dup/drop."""
    if not _FPS_PASS:
        try:
            v = subprocess.run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True).stdout
            m = re.search(r"ffmpeg version n?(\d+)\.", v)
            _FPS_PASS.extend(["-fps_mode", "passthrough"] if (not m or int(m.group(1)) >= 5)
                             else ["-vsync", "passthrough"])
        except OSError:
            _FPS_PASS.extend(["-vsync", "passthrough"])
    return _FPS_PASS


def count_frames(path):
    """Frames in the first video stream: packets read (one per frame for H.264/HEVC/ProRes/FFV1 — no decode),
    then decoded frames if the packet count is unreadable. Every step that decodes a clip also checks the count
    it actually read."""
    for entry, flag in (("nb_read_packets", "-count_packets"), ("nb_read_frames", "-count_frames")):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", flag, "-show_entries",
                            f"stream={entry}", "-of", "default=nk=1:nw=1", path],
                           capture_output=True, text=True, errors="replace")
        try:
            n = int((r.stdout or "").strip().splitlines()[0])
            if n > 0:
                return n
        except (ValueError, IndexError):
            continue
    raise Usage(f"{path}: ffprobe could not count its frames")


_PROBES = {}


def probe(path):
    """Size (rotation applied), frame rate, frame count, pixel format, colour tags, audio. Cached per file
    state (path, size, mtime) within one run."""
    if not os.path.isfile(path):
        raise Usage(f"{path}: not found")
    st_ = os.stat(path)
    key = (os.path.abspath(path), st_.st_size, st_.st_mtime_ns)
    if key not in _PROBES:
        _PROBES[key] = _probe(path)
    return json.loads(json.dumps(_PROBES[key]))


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True, errors="replace")
    try:
        d = json.loads(r.stdout or "{}")
    except ValueError:
        d = {}
    st = d.get("streams") or []
    vs = [s for s in st if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")]
    if not vs:
        raise Usage(f"{path}: no video stream ({(r.stderr or '').strip()[:200]})")
    v = vs[0]
    au = [s for s in st if s.get("codec_type") == "audio"]
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    rot = 0
    for sd in v.get("side_data_list") or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = rot or int(float((v.get("tags") or {}).get("rotate", 0) or 0))
    if abs(rot) % 180 == 90:
        w, h = h, w
    rate = v.get("r_frame_rate") or v.get("avg_frame_rate") or "0/1"
    fps = _frac(rate) or _frac(v.get("avg_frame_rate"))
    avg = _frac(v.get("avg_frame_rate"))
    if not fps:
        raise Usage(f"{path}: no frame rate")
    pix = v.get("pix_fmt") or ""
    m = re.search(r"(\d+)(?:le|be)$", pix)
    bits = int(m.group(1)) if m else 8
    rgb = pix.startswith(("gbr", "rgb", "bgr", "argb", "abgr", "0rgb", "0bgr", "gray"))
    cs = (v.get("color_space") or "").lower()
    assumed = []
    if cs not in MATRIX_SCALE:
        cs = "bt709" if (h >= 720 or w >= 1280) else "smpte170m"
        if not rgb:
            assumed.append(f"matrix {cs} (untagged)")
    rng = "pc" if (v.get("color_range") == "pc" or pix.startswith("yuvj")) else "tv"
    prim = (v.get("color_primaries") or "").lower()
    trc = (v.get("color_transfer") or "").lower()
    if prim in _BAD_TAG:
        prim = "bt709" if cs == "bt709" else "smpte170m"
        assumed.append(f"primaries {prim} (untagged)")
    if trc in _BAD_TAG:
        trc = "bt709" if cs == "bt709" else "smpte170m"
        assumed.append(f"transfer {trc} (untagged)")
    frames = count_frames(path)
    audio = None
    if au:
        a = au[0]
        audio = {"codec": a.get("codec_name"), "rate": int(a.get("sample_rate") or 0),
                 "channels": int(a.get("channels") or 0)}
    return {"w": w, "h": h, "fps": fps, "rate": rate if _frac(rate) else f"{fps:.6f}", "frames": frames,
            "duration": round(frames / fps, 6), "pix_fmt": pix, "bits": bits, "rgb": rgb,
            "vfr": bool(avg and abs(avg - fps) > 0.01 * fps), "codec": v.get("codec_name"),
            "color": {"matrix": cs, "range": rng, "primaries": prim, "transfer": trc, "assumed": assumed},
            "audio": audio}


def src_rec(info, path, base):
    rec = file_rec(path, base)
    rec.update({"sha256": sha256_file(path), "width": info["w"], "height": info["h"], "fps": info["fps"],
                "rate": info["rate"], "frames": info["frames"], "duration": info["duration"],
                "pix_fmt": info["pix_fmt"], "color": info["color"], "audio": info["audio"]})
    return rec


def work_pix(info):
    return "rgb48le" if info["bits"] > 8 else "rgb24"


def vf_read(info, W, H, pix, flags):
    if pix == "gray":
        return f"scale={W}:{H}:flags=area,format=gray"
    base = f"scale=w={W}:h={H}:flags={flags}+accurate_rnd+full_chroma_int"
    if not info.get("rgb"):
        c = info["color"]
        base += f":in_color_matrix={MATRIX_SCALE.get(c['matrix'], 'bt709')}:in_range={c['range']}"
    return base + f",format={pix}"


class Reader:
    """Frames from ffmpeg, in order, as numpy arrays (H×W×3, or H×W for gray)."""

    def __init__(self, path, info, size=None, pix="rgb24", start=0, count=None, flags="lanczos", raw=False):
        np = deps()[0]
        self.np = np
        self.W, self.H = size or (info["w"], info["h"])
        self.pix = pix
        self.ch = 1 if pix == "gray" else 3
        self.dtype = np.uint16 if pix in ("rgb48le", "gray16le") else np.uint8
        self.nbytes = self.W * self.H * self.ch * (2 if self.dtype == np.uint16 else 1)
        vf = []
        if start or count is not None:
            t = f"trim=start_frame={int(start)}" + (f":end_frame={int(start) + int(count)}" if count is not None else "")
            vf.append(t + ",setpts=PTS-STARTPTS")
        if not raw:
            vf.append(vf_read(info, self.W, self.H, pix, flags))
        cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-map", "0:v:0", "-an", "-sn", "-dn"] + fps_pass()
        if vf:
            cmd += ["-vf", ",".join(vf)]
        cmd += ["-f", "rawvideo", "-pix_fmt", pix, "-"]
        self.err = tempfile.TemporaryFile()
        self.path = path
        self.n = 0
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=self.err, bufsize=max(self.nbytes, 1 << 16))

    def read(self):
        buf = self.p.stdout.read(self.nbytes)
        if len(buf) < self.nbytes:
            return None
        self.n += 1
        a = self.np.frombuffer(buf, self.dtype)
        return a.reshape(self.H, self.W) if self.ch == 1 else a.reshape(self.H, self.W, 3)

    def close(self, check=False):
        try:
            self.p.stdout.close()
        except Exception:
            pass
        if self.p.poll() is None:
            self.p.kill()
        rc = self.p.wait()
        if check and rc not in (0, -9) and self.n == 0:
            self.err.seek(0)
            raise Usage(f"ffmpeg could not read {self.path}: {self.err.read().decode(errors='replace')[:300]}")
        self.err.close()


def audio_args(container, codec, copy):
    codec = (codec or "").lower()
    if container == "mp4":
        return ["-c:a", "copy"] if copy and codec in ("aac", "mp3", "alac", "ac3", "eac3") else \
            ["-c:a", "aac", "-b:a", "320k"]
    if container == "mov":
        return ["-c:a", "copy"] if copy and (codec.startswith("pcm_") or codec in ("aac", "alac")) else \
            ["-c:a", "pcm_s24le"]
    return ["-c:a", "copy"] if copy else ["-c:a", "pcm_s24le"]


class Writer:
    """A video from raw frames on stdin: h264 (plate / .mp4), prores (4444, .mov), ffv1 (RGB lossless, .mkv),
    mask (FFV1 gray). `audio`: {path, codec, start, dur, offset, copy} muxed from another file."""

    def __init__(self, out, W, H, rate, info, kind, pix_in="rgb24", audio=None):
        if kind == "h264" and (W % 2 or H % 2):
            raise Usage(f"{W}x{H} is odd: H.264 4:2:0 needs an even size")
        container = {".mp4": "mp4", ".m4v": "mp4", ".mov": "mov"}.get(os.path.splitext(out)[1].lower(), "mkv")
        cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", pix_in, "-s", f"{W}x{H}",
               "-r", str(rate), "-i", "-"]
        amap = []
        if audio:
            if audio.get("offset"):
                cmd += ["-itsoffset", f"{audio['offset']:.6f}"]
            if audio.get("start"):
                cmd += ["-ss", f"{audio['start']:.6f}"]
            if audio.get("dur"):
                cmd += ["-t", f"{audio['dur']:.6f}"]
            cmd += ["-i", audio["path"]]
            amap = ["-map", "1:a:0"]
        cmd += ["-map", "0:v:0"] + amap
        if info is not None and kind != "mask":
            c = info["color"]
            tags = ["-color_primaries", c["primaries"], "-color_trc", c["transfer"]]
            yuv_tags = ["-colorspace", c["matrix"], "-color_range", c["range"]] + tags
            on_frames = tag_filter(c)      # the two tags the options alone lose on ffmpeg 8.1 (see tag_filter)

            def to_yuv(pf):
                return ["-vf", f"scale=out_color_matrix={MATRIX_SCALE.get(c['matrix'], 'bt709')}:"
                               f"out_range={c['range']}:flags=accurate_rnd+full_chroma_int,format={pf}"
                               + ("," + on_frames if on_frames else "")]
        if kind == "h264":
            cmd += to_yuv("yuv420p") + ["-c:v", "libx264", "-preset", "slow", "-crf", "10", "-pix_fmt", "yuv420p"] \
                + yuv_tags + (["-movflags", "+faststart"] if container == "mp4" else [])
        elif kind == "prores":
            cmd += to_yuv("yuv444p10le") + ["-c:v", "prores_ks", "-profile:v", "4", "-qscale:v", "1",
                                            "-vendor", "apl0", "-pix_fmt", "yuv444p10le"] + yuv_tags
        elif kind == "ffv1":
            cmd += (["-vf", on_frames] if on_frames else []) + [
                "-c:v", "ffv1", "-level", "3", "-g", "1", "-slicecrc", "1",
                "-pix_fmt", "gbrp16le" if pix_in == "rgb48le" else "gbrp"] + tags
        elif kind == "mask":
            cmd += ["-c:v", "ffv1", "-level", "3", "-g", "1", "-pix_fmt", "gray"]
        else:
            raise Usage(f"unknown writer kind {kind}")
        if audio:
            cmd += audio_args(container, audio.get("codec"), audio.get("copy", False))
        cmd += [out]
        self.out = out
        self.err = tempfile.TemporaryFile()
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=self.err)
        self.n = 0

    def write(self, a):
        np = deps()[0]
        try:
            self.p.stdin.write(np.ascontiguousarray(a).tobytes())
        except BrokenPipeError:
            self.close()
            raise
        self.n += 1

    def close(self):
        try:
            self.p.stdin.close()
        except Exception:
            pass
        rc = self.p.wait()
        self.err.seek(0)
        msg = self.err.read().decode(errors="replace")
        self.err.close()
        if rc != 0:
            raise Usage(f"ffmpeg failed writing {self.out}: {msg.strip()[:400]}")


def out_kind(path):
    ext = os.path.splitext(path)[1].lower()
    k = {".mov": "prores", ".mkv": "ffv1", ".mp4": "h264", ".m4v": "h264"}.get(ext)
    if not k:
        raise Usage(f"--out {path}: use .mov (ProRes 4444), .mkv (FFV1, lossless) or .mp4 (H.264)")
    return k


def job_path(p, label=None):
    """--job: the REPAIR-<label>.json, or the folder that holds it (--label picks one when there are several)."""
    p = os.path.abspath(os.path.expanduser(p))
    if not os.path.isdir(p):
        return p
    if label and os.path.isfile(os.path.join(p, f"REPAIR-{label}.json")):
        return os.path.join(p, f"REPAIR-{label}.json")
    found = sorted(f for f in os.listdir(p) if re.fullmatch(r"REPAIR-.+\.json", f))
    if len(found) == 1:
        return os.path.join(p, found[0])
    raise Usage(f"--job {p}: a folder with {len(found) or 'no'} REPAIR-<label>.json file(s)"
                + (f" and none for --label {label}" if label else "") + " — "
                + ("give the file, or --label" if found else "run mask first"))


# ---- parsing and the work range -----------------------------------------------------------------------------
def _num(tok, full):
    tok = tok.strip()
    try:
        return float(tok[:-1]) / 100.0 * full if tok.endswith("%") else float(tok)
    except ValueError:
        raise Usage(f"not a number: {tok!r}")


def parse_box(s, W, H):
    parts = [p for p in re.split(r"[,\s]+", (s or "").strip()) if p]
    if len(parts) != 4:
        raise Usage("--box takes x,y,w,h — pixels, or each value with % of the frame (e.g. 40%,30%,10%,12%)")
    x, y, w, h = _num(parts[0], W), _num(parts[1], H), _num(parts[2], W), _num(parts[3], H)
    if w < 4 or h < 4:
        raise Usage(f"--box {s}: the box is under 4 px on a side")
    x0, y0, x1, y1 = max(0.0, x), max(0.0, y), min(float(W), x + w), min(float(H), y + h)
    if x1 - x0 < 4 or y1 - y0 < 4:
        raise Usage(f"--box {s} lies outside the {W}x{H} frame")
    return (x0, y0, x1 - x0, y1 - y0), (x0, y0, x1, y1) != (x, y, x + w, y + h)


def parse_point(s, W, H):
    parts = [p for p in re.split(r"[,\s]+", (s or "").strip()) if p]
    if len(parts) != 2:
        raise Usage("--point takes x,y (pixels or %)")
    x, y = _num(parts[0], W), _num(parts[1], H)
    if not (0 <= x < W and 0 <= y < H):
        raise Usage(f"--point {s} lies outside the {W}x{H} frame")
    return (x, y)


def parse_frames(s, n):
    m = re.fullmatch(r"\s*(\d+)\s*[-–:]\s*(\d+)\s*", s or "")
    if not m:
        raise Usage("--frames takes A-B, the first and last source frame the cut uses (0-based)")
    a, b = int(m.group(1)), int(m.group(2))
    if not (0 <= a <= b < n):
        raise Usage(f"--frames {s}: the clip has frames 0–{n - 1}")
    return a, b


def plan_range(n, fps, cut, handles, min_s=MIN_PLATE_S):
    """The frames to work on: the cut plus handles, never under min_s when the clip allows, rounded up to
    whole seconds [ASSUMED: the call takes whole seconds and its duration must match the plate]."""
    notes = []
    if cut is None:
        s, e = 0, n - 1
        if n / fps < min_s - 1e-6:
            notes.append(f"the clip is {n / fps:.2f} s: video_edit wants a source of at least {min_s:g} s — pad a "
                         f"freeze on its last frame first (motion-design.md §2.4); not done here")
        return {"cut": None, "handles": 0, "work": [s, e], "rounded_to_whole_seconds": False, "notes": notes}
    a, b = cut
    s, e = max(0, a - handles), min(n - 1, b + handles)
    if s > a - handles or e < b + handles:
        notes.append("the handles are clipped by the clip's ends")
    need = int(math.ceil(min_s * fps - 1e-6))
    length = e - s + 1
    target = max(need, length)
    target = max(target, int(round(math.ceil(target / fps - 1e-6) * fps)))
    if target > n:
        target = n
    while e - s + 1 < target:
        grew = False
        if e < n - 1:
            e += 1
            grew = True
        if e - s + 1 < target and s > 0:
            s -= 1
            grew = True
        if not grew:
            break
    if e - s + 1 < need:
        notes.append(f"the clip is {n / fps:.2f} s: video_edit wants a source of at least {min_s:g} s — pad a "
                     f"freeze on its last frame first (motion-design.md §2.4); not done here")
    return {"cut": [a, b], "handles": handles, "work": [s, e], "rounded_to_whole_seconds": True, "notes": notes}


# ---- the box engine -----------------------------------------------------------------------------------------
LK = None


def _lk(cv2):
    return dict(winSize=(15, 15), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))


def _center(b):
    return (b[0] + b[2] / 2.0, b[1] + b[3] / 2.0)


def _visible(b, W, H):
    x0, y0, x1, y1 = max(0.0, b[0]), max(0.0, b[1]), min(float(W), b[0] + b[2]), min(float(H), b[1] + b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0) / max(1e-6, b[2] * b[3])


def _patch(np, cv2, img, b, size):
    """The box's content at `size` (w, h), sub-pixel, borders replicated."""
    w, h = max(4, int(round(b[2]))), max(4, int(round(b[3])))
    p = cv2.getRectSubPix(img, (w, h), _center(b))
    if (w, h) != tuple(size):
        p = cv2.resize(p, tuple(size), interpolation=cv2.INTER_AREA if w > size[0] else cv2.INTER_LINEAR)
    return p.astype(np.float32)


def _ncc(np, a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum()) / d if d > 1e-6 else 0.0


def _subpix(np, res, ml):
    x, y = ml
    h, w = res.shape
    dx = dy = 0.0
    if 0 < x < w - 1:
        l, c, r = float(res[y, x - 1]), float(res[y, x]), float(res[y, x + 1])
        den = l - 2 * c + r
        if abs(den) > 1e-9:
            dx = max(-0.5, min(0.5, 0.5 * (l - r) / den))
    if 0 < y < h - 1:
        u, c, d = float(res[y - 1, x]), float(res[y, x]), float(res[y + 1, x])
        den = u - 2 * c + d
        if abs(den) > 1e-9:
            dy = max(-0.5, min(0.5, 0.5 * (u - d) / den))
    return dx, dy


def _search(np, cv2, img, tmpl, center, radius, scales):
    """Best (ncc, box) for `tmpl` at each scale within `radius` px of `center`; None if nothing fits."""
    H, W = img.shape[:2]
    th0, tw0 = tmpl.shape[:2]
    best = None
    radius = int(max(1, radius))
    for s in scales:
        tw, th = int(round(tw0 * s)), int(round(th0 * s))
        if tw < 6 or th < 6 or tw >= W or th >= H:
            continue
        t = tmpl if (tw, th) == (tw0, th0) else cv2.resize(
            tmpl, (tw, th), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
        if float(t.std()) < 1.0:
            continue
        x0 = int(math.floor(center[0] - tw / 2.0 - radius))
        y0 = int(math.floor(center[1] - th / 2.0 - radius))
        x1, y1 = x0 + tw + 2 * radius + 1, y0 + th + 2 * radius + 1
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 - x0 < tw or y1 - y0 < th:
            continue
        res = cv2.matchTemplate(img[y0:y1, x0:x1].astype(np.float32), t, cv2.TM_CCOEFF_NORMED)
        res = np.nan_to_num(res, nan=-1.0, posinf=-1.0, neginf=-1.0)
        _, mv, _, ml = cv2.minMaxLoc(res)
        dx, dy = _subpix(np, res, ml)
        if best is None or mv > best[0]:
            best = (float(mv), (x0 + ml[0] + dx, y0 + ml[1] + dy, float(tw), float(th)))
    return best


def _flow_step(np, cv2, a, b, box):
    """The box carried from frame a to frame b by the features inside it: (box, inliers) or None."""
    H, W = a.shape[:2]
    x, y, w, h = box
    mx, my = 0.08 * w, 0.08 * h
    x0, y0 = int(max(0, math.floor(x + mx))), int(max(0, math.floor(y + my)))
    x1, y1 = int(min(W, math.ceil(x + w - mx))), int(min(H, math.ceil(y + h - my)))
    if x1 - x0 < 6 or y1 - y0 < 6:
        return None
    m = np.zeros(a.shape[:2], np.uint8)
    m[y0:y1, x0:x1] = 255
    p0 = cv2.goodFeaturesToTrack(a, maxCorners=400, qualityLevel=0.005, minDistance=3, blockSize=5, mask=m)
    if p0 is None or len(p0) < FLOW_MIN_PTS:
        return None
    lk = _lk(cv2)
    p1, s1, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, **lk)
    if p1 is None:
        return None
    p0r, s2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, **lk)
    fbe = np.linalg.norm((p0 - p0r).reshape(-1, 2), axis=1)
    ok = (s1.ravel() == 1) & (s2.ravel() == 1) & (fbe < FB_MAX)
    if ok.sum() < FLOW_MIN_PTS:
        return None
    ga, gb = p0.reshape(-1, 2)[ok], p1.reshape(-1, 2)[ok]
    M, inl = cv2.estimateAffinePartial2D(ga, gb, method=cv2.RANSAC, ransacReprojThreshold=1.5, maxIters=2000,
                                         confidence=0.995)
    if M is None or inl is None:
        return None
    inl = inl.ravel().astype(bool)
    if inl.sum() < FLOW_MIN_PTS or inl.sum() < 0.5 * len(ga):
        return None
    s = math.hypot(M[0, 0], M[1, 0])
    if not 0.85 < s < 1.18:
        return None
    s = min(1.0 + STEP_SCALE, max(1.0 - STEP_SCALE, s))
    cx, cy = _center(box)
    ncx = M[0, 0] * cx + M[0, 1] * cy + M[0, 2]
    ncy = M[1, 0] * cx + M[1, 1] * cy + M[1, 2]
    nw, nh = w * s, h * s
    return (ncx - nw / 2, ncy - nh / 2, nw, nh), int(inl.sum()), float(inl.sum()) / len(ga)


def _recenter(np, cv2, img, anchor, aw, box):
    """Pull a flow box onto the anchor's look nearby, in place and in scale — the flow chain drifts; the
    anchor does not."""
    s = box[2] / aw
    r = max(2, int(round(0.12 * min(box[2], box[3]))))
    best = _search(np, cv2, img, anchor, _center(box), r, (s * 0.97, s, s * 1.03))
    if best is None:
        return box
    cur = _ncc(np, anchor, _patch(np, cv2, img, box, (anchor.shape[1], anchor.shape[0])))
    if best[0] >= 0.6 and best[0] > cur + 0.02:
        c, bw, bh = _center(best[1]), best[1][2], best[1][3]
        return (c[0] - bw / 2, c[1] - bh / 2, bw, bh)
    return box


def _ecc_refine(np, cv2, img, anchor, aw, box):
    try:
        s = box[2] / aw
        tw, th = max(6, int(round(anchor.shape[1] * s))), max(6, int(round(anchor.shape[0] * s)))
        t = anchor if (tw, th) == (anchor.shape[1], anchor.shape[0]) else cv2.resize(anchor, (tw, th))
        p = _patch(np, cv2, img, box, (tw, th))
        warp = np.eye(2, 3, dtype=np.float32)
        crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-4)
        rho, warp = cv2.findTransformECC(t, p, warp, cv2.MOTION_TRANSLATION, crit, None, 3)
        dx, dy = float(warp[0, 2]), float(warp[1, 2])
        if rho < 0.5 or abs(dx) > tw / 2 or abs(dy) > th / 2:
            return None
        return (box[0] + dx, box[1] + dy, box[2], box[3])
    except Exception:
        return None


def _score(np, cv2, a, b, prev_box, nb, anchor):
    H, W = b.shape[:2]
    rel = nb[2] / float(anchor.shape[1])
    asz = (anchor.shape[1], anchor.shape[0])
    na = _ncc(np, anchor, _patch(np, cv2, b, nb, asz))
    psz = (max(6, int(round(prev_box[2]))), max(6, int(round(prev_box[3]))))
    npv = _ncc(np, _patch(np, cv2, a, prev_box, psz), _patch(np, cv2, b, nb, psz))
    vis = _visible(nb, W, H)
    conf = 0.5 * (max(0.0, na) + max(0.0, npv))
    return {"box": nb, "conf": conf, "ncc_anchor": na, "ncc_prev": npv, "visible": vis,
            "ok": (conf >= LOST_CONF and npv >= PREV_MIN and na >= ANCHOR_MIN and vis >= VIS_MIN
                   and SCALE_RANGE[0] <= rel <= SCALE_RANGE[1])}


def _follow(np, cv2, a, b, box, vel, anchor, aw):
    cands = []
    fl = _flow_step(np, cv2, a, b, box)
    if fl is not None:
        nb = _recenter(np, cv2, b, anchor, aw, fl[0])
        c = _score(np, cv2, a, b, box, nb, anchor)
        c.update(method="flow", inliers=fl[1], inlier_share=fl[2])
        cands.append(c)
    if not cands or not cands[0]["ok"]:
        pred = (box[0] + vel[0], box[1] + vel[1], box[2], box[3])
        r = max(8.0, 0.5 * max(box[2], box[3]) + abs(vel[0]) + abs(vel[1]))
        prev_t = _patch(np, cv2, a, box, (max(6, int(round(box[2]))), max(6, int(round(box[3])))))
        hits = [h for h in (_search(np, cv2, b, prev_t, _center(pred), r, (0.96, 1.0, 1.04)),
                            _search(np, cv2, b, anchor, _center(pred), r,
                                    tuple(box[2] / aw * f for f in (0.96, 1.0, 1.04)))) if h]
        if hits:
            nb = max(hits, key=lambda h: h[0])[1]
            method = "template"
            e = _ecc_refine(np, cv2, b, anchor, aw, nb)
            if e is not None:
                nb, method = e, "template+ecc"
            c = _score(np, cv2, a, b, box, nb, anchor)
            c.update(method=method, inliers=None)
            cands.append(c)
    if not cands:
        return {"ok": False, "conf": 0.0, "method": "none"}
    return max(cands, key=lambda c: (c["ok"], c["conf"]))


def _reacquire(np, cv2, img, last_box, vel, gap, anchor, aw):
    H, W = img.shape[:2]
    c = _center(last_box)
    c = (min(W - 1.0, max(0.0, c[0] + vel[0] * gap)), min(H - 1.0, max(0.0, c[1] + vel[1] * gap)))
    r = min(max(W, H), max(2.0 * max(last_box[2], last_box[3]), 8.0 * gap))
    s0 = last_box[2] / aw
    best = _search(np, cv2, img, anchor, c, r, tuple(s0 * f for f in (0.85, 0.92, 1.0, 1.08, 1.17)))
    if best is None:
        return {"ok": False, "conf": 0.0, "method": "reacquire"}
    vis = _visible(best[1], W, H)
    rel = best[1][2] / float(anchor.shape[1])
    return {"ok": best[0] >= REACQ_NCC and vis >= VIS_MIN and SCALE_RANGE[0] <= rel <= SCALE_RANGE[1],
            "box": best[1], "conf": best[0], "method": "reacquire",
            "ncc_anchor": best[0], "ncc_prev": None, "visible": vis, "inliers": None}


def track_box(np, cv2, frames, k, box0):
    """Per-frame records at the working size: box (or None when lost), confidence, method."""
    n = len(frames)
    aw, ah = max(6, int(round(box0[2]))), max(6, int(round(box0[3])))
    anchor = _patch(np, cv2, frames[k], box0, (aw, ah))
    if float(anchor.std()) < 2.0:
        raise Refused("the box holds almost no texture on the anchor frame (under 2 grey levels of variation): "
                      "there is nothing to follow — draw it to include the region's edges, or use --engine sam2")
    recs = [None] * n
    recs[k] = {"box": tuple(box0), "conf": 1.0, "method": "anchor", "ncc_anchor": 1.0, "ncc_prev": 1.0,
               "lost": False}
    for step in (1, -1):
        p_i, p_box, vel, lost = k, tuple(box0), (0.0, 0.0), False
        i = k + step
        while 0 <= i < n:
            got = (_reacquire(np, cv2, frames[i], p_box, vel, abs(i - p_i), anchor, aw) if lost
                   else _follow(np, cv2, frames[p_i], frames[i], p_box, vel, anchor, aw))
            if got.get("ok"):
                b = tuple(float(v) for v in got["box"])
                gap = abs(i - p_i)
                d = ((_center(b)[0] - _center(p_box)[0]) / gap, (_center(b)[1] - _center(p_box)[1]) / gap)
                vel = d if lost else (0.5 * vel[0] + 0.5 * d[0], 0.5 * vel[1] + 0.5 * d[1])
                rec = {"box": b, "conf": got["conf"], "method": got["method"], "ncc_anchor": got.get("ncc_anchor"),
                       "ncc_prev": got.get("ncc_prev"), "lost": False}
                if got.get("inliers") is not None:
                    rec["inliers"] = got["inliers"]
                    rec["inlier_share"] = got["inlier_share"]
                if lost:
                    rec["reacquired"] = True
                lost, p_i, p_box = False, i, b
            else:
                rec = {"box": None, "conf": float(got.get("conf") or 0.0), "method": got.get("method", "lost"),
                       "lost": True}
                lost = True
            recs[i] = rec
            i += step
    return recs


def smooth_boxes(np, boxes, passes, keep=None):
    """[1,2,1]/4 on centre and size inside each run of found boxes; `keep` (the anchor) is not moved."""
    out = [None if b is None else list(b) for b in boxes]
    if passes <= 0:
        return [None if b is None else tuple(b) for b in out]
    i, n = 0, len(out)
    while i < n:
        if out[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < n and out[j + 1] is not None:
            j += 1
        if j - i >= 2:
            c = np.array([[b[0] + b[2] / 2, b[1] + b[3] / 2, b[2], b[3]] for b in out[i:j + 1]], np.float64)
            for _ in range(passes):
                c[1:-1] = 0.25 * c[:-2] + 0.5 * c[1:-1] + 0.25 * c[2:]
            for t in range(i, j + 1):
                if t == keep:
                    continue
                cx, cy, w, h = c[t - i]
                out[t] = [cx - w / 2, cy - h / 2, w, h]
        i = j + 1
    return [None if b is None else tuple(b) for b in out]


def _bg_step(np, cv2, a, b, box):
    """The scene's motion between two frames, from features outside the region: a 2×3 matrix or None."""
    H, W = a.shape[:2]
    m = np.full(a.shape[:2], 255, np.uint8)
    if box is not None:
        x, y, w, h = box
        m[int(max(0, y - 0.25 * h)):int(min(H, y + 1.25 * h)), int(max(0, x - 0.25 * w)):int(min(W, x + 1.25 * w))] = 0
    p0 = cv2.goodFeaturesToTrack(a, maxCorners=300, qualityLevel=0.01, minDistance=8, blockSize=5, mask=m)
    if p0 is None or len(p0) < 30:
        return None
    lk = _lk(cv2)
    p1, s1, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, **lk)
    if p1 is None:
        return None
    p0r, s2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, **lk)
    ok = (s1.ravel() == 1) & (s2.ravel() == 1) & (np.linalg.norm((p0 - p0r).reshape(-1, 2), axis=1) < 1.0)
    if ok.sum() < 30:
        return None
    M, inl = cv2.estimateAffinePartial2D(p0.reshape(-1, 2)[ok], p1.reshape(-1, 2)[ok], method=cv2.RANSAC,
                                         ransacReprojThreshold=1.5, maxIters=2000, confidence=0.995)
    if M is None or inl is None or inl.sum() < 25:
        return None
    return M


def scene_carry(np, cv2, frames, boxes_an):
    """Where a point fixed to the scene at the region's first centre ends up (working-size px), or None."""
    first = next((i for i, b in enumerate(boxes_an) if b is not None), None)
    last = next((i for i in range(len(boxes_an) - 1, -1, -1) if boxes_an[i] is not None), None)
    if first is None or last is None or last <= first:
        return None
    p = list(_center(boxes_an[first]))
    cur = boxes_an[first]
    for i in range(first, last):
        cur = boxes_an[i] or cur
        M = _bg_step(np, cv2, frames[i], frames[i + 1], cur)
        if M is None:
            return None
        p = [M[0, 0] * p[0] + M[0, 1] * p[1] + M[0, 2], M[1, 0] * p[0] + M[1, 1] * p[1] + M[1, 2]]
    return {"first": first, "last": last, "carried": p}


def motion_summary(recs, W, H, carry=None, sx=1.0, sy=1.0):
    """The region's path in plain words, for the prompt stub, and the numbers behind them."""
    good = [r for r in recs if r.get("box")]
    if len(good) < 2:
        return {"words": "It stays where the black area is on every frame.", "dx_pct": 0.0, "dy_pct": 0.0,
                "scale": 1.0, "fixed_to_scene": None, "cut_by_edge": []}
    b0, b1 = good[0]["box"], good[-1]["box"]
    c0, c1 = _center(b0), _center(b1)
    dx, dy = (c1[0] - c0[0]) / W * 100, (c1[1] - c0[1]) / H * 100
    sc = math.sqrt((b1[2] * b1[3]) / max(1e-6, b0[2] * b0[3]))

    def where(c):
        hz = "left of centre" if c[0] < 0.4 * W else ("right of centre" if c[0] > 0.6 * W else "near the centre")
        vt = "high in the frame" if c[1] < 0.4 * H else ("low in the frame" if c[1] > 0.6 * H else "at mid height")
        return f"{hz}, {vt}"
    words = [f"At the start it sits {where(c0)}."]
    mv = []
    if abs(dx) >= 2:
        mv.append(f"{'right' if dx > 0 else 'left'} by about {abs(dx):.0f} % of the frame width")
    if abs(dy) >= 2:
        mv.append(f"{'down' if dy > 0 else 'up'} by about {abs(dy):.0f} % of the frame height")
    words.append(("Across the shot it moves " + " and ".join(mv) + ".") if mv else "It stays in the same place in the frame.")
    words.append(f"It grows by about {100 * (sc - 1):.0f} %." if sc > 1.04 else
                 (f"It shrinks by about {100 * (1 - sc):.0f} %." if sc < 0.96 else "It keeps its size."))
    fixed = None
    if carry is not None:
        px, py = carry["carried"][0] / sx, carry["carried"][1] / sy
        dev = math.hypot((px - c1[0]) / W, (py - c1[1]) / H) * 100
        fixed = dev < 3.0
        words.append("It is fixed to the scene: it moves only as the camera moves." if fixed else
                     "It moves on its own as well as with the camera.")
    else:
        words.append("(The camera's own motion could not be measured from the background.)")
    edge = [r["f"] for r in good if _visible(r["box"], W, H) < 0.98]
    if edge:
        words.append(f"On frames {spans_txt(edge)} the edge of the frame cuts it.")
    return {"words": " ".join(words), "dx_pct": round(dx, 2), "dy_pct": round(dy, 2), "scale": round(sc, 4),
            "fixed_to_scene": fixed, "cut_by_edge": spans(edge)}


# ---- masks --------------------------------------------------------------------------------------------------
def box_mask(np, W, H, box):
    m = np.zeros((H, W), np.uint8)
    if box is None:
        return m
    x0, y0 = max(0, int(math.floor(box[0]))), max(0, int(math.floor(box[1])))
    x1, y1 = min(W, int(math.ceil(box[0] + box[2]))), min(H, int(math.ceil(box[1] + box[3])))
    if x1 > x0 and y1 > y0:
        m[y0:y1, x0:x1] = 255
    return m


def masks_sha(base, mrec, s, e):
    if mrec["kind"] == "mkv":
        return sha256_file(os.path.join(base, mrec["path"]))
    h = hashlib.sha256()
    d = os.path.join(base, mrec["dir"])
    for f in range(s, e + 1):
        p = os.path.join(d, f"{f:06d}.png")
        if not os.path.isfile(p):
            raise Usage(f"mask {p} missing — re-run track")
        with open(p, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()


def write_masks(np, cv2, kind, outdir, label, W, H, rate, s, gen):
    """`gen` yields (source frame, mask) in order. Returns the masks record (relative to outdir)."""
    if kind == "png":
        d = os.path.join(outdir, f"MASKS-{label}")
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            if re.fullmatch(r"\d{6}\.png", f):
                os.remove(os.path.join(d, f))
        n = 0
        for f, m in gen:
            cv2.imwrite(os.path.join(d, f"{f:06d}.png"), m)
            n += 1
        return {"kind": "png", "dir": f"MASKS-{label}", "pattern": "%06d.png", "first": s, "count": n}
    p = os.path.join(outdir, f"MASKS-{label}.mkv")
    w = Writer(p, W, H, rate, None, "mask", pix_in="gray")
    n = 0
    for f, m in gen:
        w.write(m)
        n += 1
    w.close()
    return {"kind": "mkv", "path": f"MASKS-{label}.mkv", "first": s, "count": n}


def iter_masks(np, cv2, base, mrec, W, H, s, e):
    if mrec["kind"] == "png":
        d = os.path.join(base, mrec["dir"])
        for f in range(s, e + 1):
            m = cv2.imread(os.path.join(d, f"{f:06d}.png"), cv2.IMREAD_GRAYSCALE)
            if m is None or m.shape != (H, W):
                raise Usage(f"mask {f:06d}.png missing or the wrong size in {d}")
            yield m
        return
    rd = Reader(os.path.join(base, mrec["path"]), {"w": W, "h": H}, pix="gray", raw=True)
    try:
        for _ in range(s, e + 1):
            m = rd.read()
            if m is None:
                raise Usage(f"{mrec['path']} has fewer frames than the work range")
            yield m
    finally:
        rd.close()


def region_hard(np, cv2, m, pad, shape):
    """The tracked mask grown by `pad` px: (uint8 0/255 full frame, bbox x0,y0,x1,y1 or None)."""
    H, W = m.shape[:2]
    b = np.where(m > 127, np.uint8(255), np.uint8(0))
    x, y, w, h = cv2.boundingRect(b)
    if w == 0 or h == 0:
        return b, None
    if pad > 0:
        x0, y0 = max(0, x - pad - 1), max(0, y - pad - 1)
        x1, y1 = min(W, x + w + pad + 1), min(H, y + h + pad + 1)
        se = cv2.getStructuringElement(cv2.MORPH_RECT if shape == "rect" else cv2.MORPH_ELLIPSE,
                                       (2 * pad + 1, 2 * pad + 1))
        b[y0:y1, x0:x1] = cv2.dilate(b[y0:y1, x0:x1], se)
        x, y, w, h = cv2.boundingRect(b[y0:y1, x0:x1])
        x, y = x + x0, y + y0
    return b, (x, y, x + w, y + h)


def _crop(bbox, margin, W, H):
    return (max(0, bbox[0] - margin), max(0, bbox[1] - margin), min(W, bbox[2] + margin), min(H, bbox[3] + margin))


def plate_alpha(np, cv2, hard, bbox, feather):
    """1 on the grown region; with feather > 0 a smoothstep falloff OUTSIDE it (the region stays pure black)."""
    a = (hard > 0).astype(np.float32)
    if feather > 0 and bbox is not None:
        H, W = hard.shape[:2]
        x0, y0, x1, y1 = _crop(bbox, int(math.ceil(feather)) + 2, W, H)
        d = cv2.distanceTransform(np.where(hard[y0:y1, x0:x1] > 0, 0, 255).astype(np.uint8), cv2.DIST_L2, 5)
        t = np.clip(1.0 - d / float(feather), 0.0, 1.0)
        a[y0:y1, x0:x1] = np.maximum(a[y0:y1, x0:x1], t * t * (3 - 2 * t))
    return a


def inner_alpha(np, cv2, hard, bbox, feather):
    """The composite's alpha: 0 outside the grown region, a smoothstep ramp of `feather` px inside its edge,
    1 deeper in. Returned for the crop (x0, y0, x1, y1) only, with the crop."""
    H, W = hard.shape[:2]
    x0, y0, x1, y1 = _crop(bbox, 2, W, H)
    hc = hard[y0:y1, x0:x1]
    if feather <= 0:
        return (hc > 0).astype(np.float32), (x0, y0, x1, y1)
    d = cv2.distanceTransform(hc, cv2.DIST_L2, 5)
    t = np.clip(d / float(feather), 0.0, 1.0)
    return (t * t * (3 - 2 * t)) * (hc > 0), (x0, y0, x1, y1)


# ---- SAM 2 --------------------------------------------------------------------------------------------------
def _to_np(np, x):
    if hasattr(x, "detach"):
        x = x.detach().float().cpu().numpy()
    return np.asarray(x, dtype=np.float32)


def track_sam2(np, cv2, clip, info, s, e, k, box, point, ckpt, cfg, outdir, label, masks_kind,
               builder=None, torch_mod=None):
    """SAM 2's video predictor, prompted on frame k (source numbering) with a point and/or a box. Writes the
    masks; returns (records, masks record). `builder`/`torch_mod` default to the real package."""
    if builder is None:
        builder, torch_mod, why = sam2_import()
        if builder is None:
            raise Usage(SAM2_HELP.format(why=why))
        for p, what in ((ckpt, "--sam2-checkpoint"), (cfg, "--sam2-config")):
            if not p:
                raise Usage(f"--engine sam2 needs {what} (this tool never downloads weights)\n" + SAM2_HELP.format(
                    why="no checkpoint or config given"))
        if not os.path.isfile(os.path.expanduser(ckpt)):
            raise Usage(f"--sam2-checkpoint {ckpt}: not found (this tool never downloads weights)")
        ckpt = os.path.expanduser(ckpt)
    W, H, n = info["w"], info["h"], e - s + 1
    with tempfile.TemporaryDirectory(prefix="rr-sam2-") as td:
        jd = os.path.join(td, "frames")
        os.makedirs(jd)
        vf = f"trim=start_frame={s}:end_frame={e + 1},setpts=PTS-STARTPTS," + vf_read(info, W, H, "rgb24", "bicubic")
        r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", clip, "-map", "0:v:0", "-an"] + fps_pass() +
                           ["-vf", vf, "-q:v", "2", "-start_number", "0", os.path.join(jd, "%05d.jpg")],
                           capture_output=True, text=True)
        got = len([f for f in os.listdir(jd) if f.endswith(".jpg")])
        if r.returncode != 0 or got != n:
            raise Usage(f"could not extract the work range for SAM 2 ({got} of {n} frames): {r.stderr.strip()[:200]}")
        if torch_mod is not None and getattr(torch_mod, "cuda", None) and torch_mod.cuda.is_available():
            device = "cuda"
        elif torch_mod is not None and getattr(getattr(torch_mod, "backends", None), "mps", None) is not None \
                and torch_mod.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        predictor = builder(cfg, ckpt, device=device)
        ctx = contextlib.ExitStack()
        if torch_mod is not None:
            ctx.enter_context(torch_mod.inference_mode())
            if device == "cuda":
                ctx.enter_context(torch_mod.autocast("cuda", dtype=torch_mod.bfloat16))
        pd = os.path.join(td, "masks")
        os.makedirs(pd)
        stats = {}
        with ctx:
            state = predictor.init_state(video_path=jd)
            kw = {"inference_state": state, "frame_idx": k - s, "obj_id": 1}
            if point is not None:
                kw["points"] = np.array([point], np.float32)
                kw["labels"] = np.array([1], np.int32)
            if box is not None:
                kw["box"] = np.array([box[0], box[1], box[0] + box[2], box[1] + box[3]], np.float32)
            predictor.add_new_points_or_box(**kw)
            for rev in (False, True):
                for fi, _ids, logits in predictor.propagate_in_video(state, start_frame_idx=k - s, reverse=rev):
                    lg = _to_np(np, logits)                 # (objects, 1, H, W): object 1 is the only one
                    lg = lg.reshape(-1, lg.shape[-2], lg.shape[-1])[0]
                    if lg.shape != (H, W):
                        lg = cv2.resize(lg, (W, H), interpolation=cv2.INTER_LINEAR)
                    m = np.where(lg > 0, np.uint8(255), np.uint8(0))
                    f = s + int(fi)
                    cv2.imwrite(os.path.join(pd, f"{f:06d}.png"), m)
                    area = int((m > 0).sum())
                    if area:
                        x, y, w, h = cv2.boundingRect(m)
                        sig = 1.0 / (1.0 + np.exp(-np.clip(lg[m > 0], -30, 30)))
                        conf = float(2 * (sig.mean() - 0.5))
                        ys, xs = np.nonzero(m)
                        cen = [round(float(xs.mean()), 1), round(float(ys.mean()), 1)]
                    else:
                        x = y = w = h = 0
                        conf, cen = 0.0, None
                    stats[f] = {"area": area, "bbox": [x, y, w, h] if area else None, "conf": conf, "centroid": cen}
        lost_floor = max(16, int(1e-5 * W * H))
        recs = []
        for f in range(s, e + 1):
            st = stats.get(f)
            if st is None:
                st = {"area": 0, "bbox": None, "conf": 0.0, "centroid": None}
                cv2.imwrite(os.path.join(pd, f"{f:06d}.png"), np.zeros((H, W), np.uint8))
            lost = st["area"] < lost_floor
            recs.append({"f": f, "box": None if lost else [float(v) for v in st["bbox"]], "conf": round(st["conf"], 4),
                         "method": "sam2", "lost": lost, "area": st["area"],
                         "area_frac": round(st["area"] / float(W * H), 6), "centroid": st["centroid"]})
        a0 = next((r["area"] for r in recs if r["f"] == k), 0) or 1
        for r in recs:
            if not r["lost"] and (r["area"] > 2.5 * a0 or r["area"] < a0 / 2.5):
                r["jump"] = True
        gen = ((f, cv2.imread(os.path.join(pd, f"{f:06d}.png"), cv2.IMREAD_GRAYSCALE)) for f in range(s, e + 1))
        mrec = write_masks(np, cv2, masks_kind, outdir, label, W, H, info["rate"], s, gen)
    return recs, {"device": device}, mrec


# ---- the track check sheet (no words: colours and tiles; the layout is in the JSON) ---------------------------
GREEN, AMBER, RED, WHITE, BLUE, GREY = (60, 200, 60), (0, 170, 255), (40, 40, 230), (255, 255, 255), (230, 120, 30), (90, 90, 90)


def _conf_col(c, lost):
    return RED if lost else (GREEN if c >= CONF_GOOD else AMBER)


def track_sheet(np, cv2, path, frames_an, sx, sy, recs, s, k, cut, masks_dir=None):
    n = len(frames_an)
    lost_starts = [a for a, _ in spans([r["f"] for r in recs if r["lost"]])]
    re_acq = [r["f"] for r in recs if r.get("reacquired")]
    must = [s, s + n - 1, k] + lost_starts + re_acq
    even = [s + int(round(i * (n - 1) / 11.0)) for i in range(12)]
    pick = []
    for f in must + even:
        if f not in pick:
            pick.append(f)
    pick = sorted(pick[:16])
    tw = 320
    ah, aw = frames_an[0].shape[:2]
    th = int(round(tw * ah / aw))
    cols = 4
    rows = int(math.ceil(len(pick) / cols))
    cell_h = th + 14
    sheet = np.full((rows * cell_h + 30, cols * tw, 3), 24, np.uint8)
    ts = tw / float(aw)
    for idx, f in enumerate(pick):
        r = recs[f - s]
        tile = cv2.cvtColor(cv2.resize(frames_an[f - s], (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_GRAY2BGR)
        col = WHITE if f == k else _conf_col(r["conf"], r["lost"])
        if masks_dir is not None and not r["lost"]:
            m = cv2.imread(os.path.join(masks_dir, f"{f:06d}.png"), cv2.IMREAD_GRAYSCALE)
            if m is not None:
                m = cv2.resize(m, (tw, th), interpolation=cv2.INTER_NEAREST)
                cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(tile, cs, -1, col, 2)
        elif r.get("box"):
            b = r["box"]
            p0 = (int(round(b[0] * sx * ts)), int(round(b[1] * sy * ts)))
            p1 = (int(round((b[0] + b[2]) * sx * ts)), int(round((b[1] + b[3]) * sy * ts)))
            cv2.rectangle(tile, p0, p1, col, 2)
        if r["lost"]:
            cv2.rectangle(tile, (0, 0), (tw - 1, th - 1), RED, 4)
        y0, x0 = (idx // cols) * cell_h, (idx % cols) * tw
        sheet[y0:y0 + th, x0:x0 + tw] = tile
        bar = int(round((tw - 8) * max(0.0, min(1.0, r["conf"]))))
        sheet[y0 + th + 3:y0 + th + 11, x0 + 4:x0 + 4 + max(1, bar)] = col
    # timeline: one column per work frame, colour = confidence (black = lost, white = the anchor); blue = the cut
    ty = rows * cell_h + 8
    W_ = cols * tw
    for i, r in enumerate(recs):
        xa, xb = int(i * W_ / n), max(int(i * W_ / n) + 1, int((i + 1) * W_ / n))
        c = WHITE if r["f"] == k else ((0, 0, 0) if r["lost"] else _conf_col(r["conf"], False))
        sheet[ty + 6:ty + 20, xa:xb] = c
    if cut:
        xa, xb = int((cut[0] - s) * W_ / n), int((cut[1] - s + 1) * W_ / n)
        sheet[ty:ty + 4, xa:max(xa + 1, xb)] = BLUE
    cv2.imwrite(path, sheet)
    return pick


# ---- track --------------------------------------------------------------------------------------------------
def analysis_scale(W, H, box):
    sc = min(1.0, ANALYSIS_MAX / float(max(W, H)))
    if box is not None and min(box[2], box[3]) * sc < BOX_MIN_AN:
        sc = min(1.0, BOX_MIN_AN / float(min(box[2], box[3])))
    sc = min(sc, ANALYSIS_CAP / float(max(W, H)), 1.0)
    aw, ah = max(2, int(round(W * sc / 2)) * 2), max(2, int(round(H * sc / 2)) * 2)
    return aw, ah


def cmd_track(a):
    np, cv2 = need_np()
    need_ff()
    info = probe(a.clip)
    W, H, n, fps = info["w"], info["h"], info["frames"], info["fps"]
    if info["vfr"]:
        warn(f"{a.clip} looks like variable frame rate (avg {info['rate']}): frame numbers may not map to time; "
             f"conform it to a constant rate first")
    if n < 2:
        raise Usage(f"{a.clip}: {n} frame(s) — nothing to track")
    box, clipped = parse_box(a.box, W, H) if a.box else (None, False)
    point = parse_point(a.point, W, H) if a.point else None
    if a.engine == "box" and box is None:
        raise Usage("--box x,y,w,h is required for the box engine")
    if a.engine == "sam2" and box is None and point is None:
        raise Usage("--engine sam2 needs --point x,y and/or --box x,y,w,h")
    if clipped:
        warn(f"--box was clipped to the frame: {[round(v, 1) for v in box]}")
    k = int(round(a.at * fps))
    if not 0 <= k < n:
        raise Usage(f"--at {a.at} s is frame {k}; the clip has frames 0–{n - 1}")
    cut = parse_frames(a.frames, n) if a.frames else None
    rng = plan_range(n, fps, cut, a.handles)
    s, e = rng["work"]
    if not s <= k <= e:
        raise Usage(f"--at {a.at} s is frame {k}, outside the work range {s}–{e} (the cut {a.frames} plus handles): "
                    f"draw the box on a frame inside it")
    for note in rng["notes"]:
        warn(note)
    label = a.label or label_of(a.clip)
    outdir = os.path.abspath(a.out or os.path.join(os.path.dirname(os.path.abspath(a.clip)), "repair"))
    os.makedirs(outdir, exist_ok=True)
    nw = e - s + 1
    aw, ah = analysis_scale(W, H, box)
    sx, sy = aw / float(W), ah / float(H)
    rd = Reader(a.clip, info, size=(aw, ah), pix="gray", start=s, count=nw, flags="area")
    frames = []
    while True:
        f = rd.read()
        if f is None:
            break
        frames.append(np.array(f))
    rd.close(check=True)
    if len(frames) != nw:
        raise Usage(f"decoded {len(frames)} frames of the work range {s}–{e}, expected {nw}")
    extra = {}
    masks_dir = None
    if a.engine == "box":
        b_an = (box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy)
        if _visible(b_an, aw, ah) < 0.5:
            raise Usage("the box is mostly outside the frame on the anchor frame")
        raw = track_box(np, cv2, frames, k - s, b_an)
        sm = smooth_boxes(np, [r["box"] for r in raw], a.smooth, keep=k - s)
        recs = []
        for i, r in enumerate(raw):
            f = s + i
            rec = {"f": f, "t": round(f / fps, 4), "lost": r["lost"], "conf": round(float(r["conf"]), 4),
                   "method": r["method"]}
            if sm[i] is not None:
                rec["box"] = [round(sm[i][0] / sx, 2), round(sm[i][1] / sy, 2), round(sm[i][2] / sx, 2),
                              round(sm[i][3] / sy, 2)]
                rec["raw"] = [round(r["box"][0] / sx, 2), round(r["box"][1] / sy, 2), round(r["box"][2] / sx, 2),
                              round(r["box"][3] / sy, 2)]
            else:
                rec["box"] = None
            for key in ("ncc_anchor", "ncc_prev"):
                if r.get(key) is not None:
                    rec[key] = round(float(r[key]), 4)
            if r.get("inliers") is not None:
                rec["inliers"] = r["inliers"]
                rec["inlier_share"] = round(r["inlier_share"], 3)
            if r.get("reacquired"):
                rec["reacquired"] = True
            recs.append(rec)
        mrec = write_masks(np, cv2, a.masks, outdir, label, W, H, info["rate"], s,
                           ((r["f"], box_mask(np, W, H, r["box"])) for r in recs))
        pad_shape = "rect"
    else:
        recs, extra, mrec = track_sam2(np, cv2, a.clip, info, s, e, k, box, point, a.sam2_checkpoint,
                                       a.sam2_config, outdir, label, a.masks)
        for r in recs:
            r["t"] = round(r["f"] / fps, 4)
        pad_shape = "ellipse"
        if mrec["kind"] == "png":
            masks_dir = os.path.join(outdir, mrec["dir"])
    mrec["sha256"] = masks_sha(outdir, mrec, s, e)
    boxes_an = [None if r.get("box") is None else (r["box"][0] * sx, r["box"][1] * sy, r["box"][2] * sx,
                                                   r["box"][3] * sy) for r in recs]
    carry = scene_carry(np, cv2, frames, boxes_an)
    motion = motion_summary(recs, W, H, carry, sx, sy)
    sheet = os.path.join(outdir, f"CHECK-{label}.png")
    tiles = track_sheet(np, cv2, sheet, frames, sx, sy, recs, s, k, cut, masks_dir)
    lost = [r["f"] for r in recs if r["lost"]]
    twarn = list(rng["notes"])
    shares = sorted(r["inlier_share"] for r in recs if "inlier_share" in r)
    if shares and shares[len(shares) // 2] < MIXED_INLIERS:
        twarn.append(f"the features inside the box do not move together (median {shares[len(shares) // 2]:.2f} agree): "
                     f"the box holds two motions, the region and what is behind it — draw it tighter around the "
                     f"region, or use --engine sam2")
    if motion.get("scale") and not 0.8 <= motion["scale"] <= 1.25:
        twarn.append(f"the box changes size by x{motion['scale']:.2f} across the shot: confirm it on the check sheet "
                     f"(a box drifting onto the background grows or shrinks)")
    for w_ in twarn[len(rng["notes"]):]:
        warn(w_)
    region = {
        "tool": TOOL, "schema": SCHEMA, "kind": "region", "label": label, "created": now(), "engine": a.engine,
        "source": src_rec(info, a.clip, outdir),
        "anchor": {"frame": k, "t": round(k / fps, 4), "box": None if box is None else [round(v, 2) for v in box],
                   "point": None if point is None else [round(v, 2) for v in point]},
        "range": rng, "pad_shape": pad_shape, "analysis_size": [aw, ah], "smooth_passes": a.smooth,
        "frames": recs, "lost": lost, "lost_spans": spans(lost),
        "reacquired": [r["f"] for r in recs if r.get("reacquired")],
        "jumps": [r["f"] for r in recs if r.get("jump")],
        "masks": mrec, "motion": motion, "warnings": twarn,
        "check_sheet": {"path": os.path.basename(sheet), "tiles": tiles,
                        "layout": "tiles in frame order, 4 a row: the frame (working size, grey) with the box or "
                                  "the mask outline; outline and bar colour = confidence (green >= "
                                  f"{CONF_GOOD}, amber, red = lost; white = the anchor); the bar under a tile is its "
                                  "confidence; the strip at the bottom has one column per work frame (black = lost, "
                                  "white = the anchor) and a blue bar over the cut range"},
        "thresholds": {"LOST_CONF": LOST_CONF, "PREV_MIN": PREV_MIN, "REACQ_NCC": REACQ_NCC, "VIS_MIN": VIS_MIN,
                       "assumed": True},
    }
    region.update(extra)
    rp = os.path.join(outdir, f"REGION-{label}.json")
    if os.path.isfile(rp):
        say(f"replacing {rp} (a REPAIR job made from the old one will refuse: its masks changed)")
    write_json(rp, region)
    if a.json:
        print(json.dumps(region, indent=1))
    confs = [r["conf"] for r in recs if not r["lost"]]
    say(f"track [{a.engine}] {os.path.basename(a.clip)}: frames {s}–{e} ({nw}, {nw / fps:.2f} s) from frame {k}; "
        f"confidence min {min(confs) if confs else 0:.2f} · median {sorted(confs)[len(confs) // 2] if confs else 0:.2f}")
    say(f"  motion: {motion['words']}")
    if region["reacquired"]:
        say(f"  re-acquired on frames {spans_txt(region['reacquired'])}")
    if region["jumps"]:
        warn(f"the mask's area jumps on frames {spans_txt(region['jumps'])}: read the check sheet")
    say(f"  wrote {rp}\n        {os.path.join(outdir, mrec.get('dir') or mrec.get('path'))}\n        {sheet}")
    if lost:
        say(f"FINDING: {len(lost)} frame(s) LOST: {spans_txt(lost)} — no box was invented for them. Read "
            f"{os.path.basename(sheet)}; re-track (another --at, a tighter box, --engine sam2), or mask with "
            f"--allow-lost to leave them unmasked on purpose.")
        return 1
    return 0


# ---- mask ---------------------------------------------------------------------------------------------------
def _provenance(path):
    for c in (path + ".json", os.path.splitext(path)[0] + ".json"):
        if os.path.isfile(c):
            try:
                with open(c, encoding="utf-8") as f:
                    d = json.load(f)
                return c, str(d.get("source") or d.get("source_kind") or "").strip().lower(), d
            except (OSError, ValueError):
                return c, "unreadable", {}
    return None, None, {}


def aspect_str(W, H):
    for name, r in (("16:9", 16 / 9), ("9:16", 9 / 16), ("21:9", 21 / 9), ("4:3", 4 / 3), ("3:4", 3 / 4),
                    ("1:1", 1.0), ("4:5", 0.8), ("5:4", 1.25), ("2:3", 2 / 3), ("3:2", 1.5)):
        if abs(W / H - r) / r < 0.01:
            return name
    g = math.gcd(W, H)
    return f"{W // g}:{H // g}"


def prompt_stub(job, refs, plate_rel):
    W, H = job["source"]["width"], job["source"]["height"]
    dur = job["plate"]["duration"]
    whole = abs(dur - round(dur)) < 0.5 / job["source"]["fps"]
    res = "1080p" if min(W, H) >= 1080 else "720p"
    lines = ["---",
             f"# REPAIR STUB written by {TOOL} mask on {job['created'][:10]}. Fill every <…>, lint it",
             "# (prompt_lint.py), and make the call through gate.py like any other generation. A draft of the call,",
             "# not an approval. Every image reference is a real, cleared photograph with a provenance sidecar",
             "# (provenance.py record), never an AI image.",
             "shot: <SHOT>",
             "kind: clip",
             "model: seedance_2_5",
             "mode: video_edit",
             f"resolution: {res}          # the source is {W}x{H}; never under 720p (the video floor); the Fusion "
             f"comp scales the result back",
             (f"duration: {int(round(dur))}" if whole else f"duration: <{max(4, int(math.ceil(dur)))}>") +
             f"               # the plate runs {dur:.3f} s ({job['plate']['frames']} frames at "
             f"{job['source']['fps']:.3f} fps): the call matches it" +
             ("" if whole else "; a whole-second call will need fusion --retime"),
             f"aspect: {aspect_str(W, H)}",
             "generate_audio: false      # the Fusion comp keeps the source's own sound (MediaIn1 on the timeline)",
             "function: repair one region of an approved take; nothing else in the shot changes",
             "payload: the same shot, with <what was wrong> put right",
             "refs:",
             f"  - role: video_references, what: masked plate, file: {plate_rel}, sha256: {job['plate']['sha256']}, "
             f"value: <media id after upload>"]
    for i, r in enumerate(refs, 1):
        lines.append(f"  - role: image_references, what: region contents, file: {r['rel']}, value: <media id>, "
                     f"not: its background, its light, its framing")
    lines += ["---", "",
              "[SOURCE]",
              "@Video 1 is the finished shot with one area painted solid black. This is an edit of @Video 1.", "",
              "[KEEP]",
              "Keep the first frame of @Video 1 as it is everywhere outside the black area. Keep every part of the "
              "picture outside the black area exactly as it is in @Video 1, frame for frame. Keep the timing, the "
              "camera and its move, the framing and the lens, the light and every change in the light, and the "
              "sound.", "",
              "[CHANGE]",
              "Rebuild only the black area, and nothing else.",
              f"In the black area there is: {job['contains']}.",
              "It fills the black area on every frame, exactly where the black area is and at its size. "
              + job["motion"]["words"], "",
              "[LIGHT MATCH]",
              "Light it with the light already in the shot: the same direction, colour and softness. Match the grain, "
              "the sharpness and the black level of the picture around it. Leave no black edge, outline or halo.", ""]
    if refs:
        lines.append("[REFERENCES]")
        for i, _r in enumerate(refs, 1):
            lines.append(f"@Image {i} shows {job['contains']}: its shape, material and colour only — not its "
                         f"background, not its light.")
        lines.append("")
    lines += ["[SUPPRESS]",
              "no change outside the black area, no new objects, no extra hands or fingers, no text, letters or "
              "logos, no cut, no speed change, no zoom or reframe", ""]
    return "\n".join(lines)


def cmd_mask(a):
    np, cv2 = need_np()
    need_ff()
    rp = os.path.abspath(a.region)
    region = load_json(rp)
    if region.get("kind") != "region":
        raise Usage(f"{a.region} is not a REGION record from track")
    base = os.path.dirname(rp)
    src = resolve(region["source"], base, "the source clip")
    if sha256_file(src) != region["source"]["sha256"]:
        raise Refused(f"{src} changed after it was tracked (sha256 differs): track it again")
    info = probe(src)
    W, H, fps = info["w"], info["h"], info["fps"]
    s, e = region["range"]["work"]
    nw = e - s + 1
    mrec = region["masks"]
    if masks_sha(base, mrec, s, e) != mrec["sha256"]:
        raise Refused("the mask files changed after track wrote them: track again")
    contains = " ".join((a.contains or "").split())
    if len(contains.split()) < 2:
        raise Refused("--contains must say in words what belongs in the region (at least two words): the model "
                      "rebuilds what it is told, and the prompt stub is built on it")
    if re.search(r"watermark", contains, re.I):
        raise Refused("--contains uses the word 'watermark': the vendor refuses it and still charges "
                      "(scenario-common-patterns.md E10) — describe the thing itself")
    if a.pad < 0 or a.feather < 0:
        raise Usage("--pad and --feather are 0 or more")
    lost = list(region.get("lost") or [])
    cut = (region["range"] or {}).get("cut")
    warnings = []
    if lost and not a.allow_lost:
        raise Refused(f"{len(lost)} frame(s) were lost by the tracker ({spans_txt(lost)}): their mask is empty, so "
                      f"the repair would switch off there. Re-track (another --at, a tighter box, --engine sam2), "
                      f"or pass --allow-lost to leave them unmasked on purpose")
    if lost:
        in_cut = [f for f in lost if cut and cut[0] <= f <= cut[1]] if cut else lost
        warnings.append(f"--allow-lost: frames {spans_txt(lost)} stay unmasked; the repair switches off there"
                        + (f", {len(in_cut)} of them inside the cut" if in_cut else ""))
    refs = []
    if len(a.ref_image or []) > MAX_REFS:
        raise Refused(f"{len(a.ref_image)} reference images: a video edit takes 1–{MAX_REFS} (vendor deck)")
    for p in a.ref_image or []:
        if not os.path.isfile(p):
            raise Usage(f"--ref-image {p}: not found")
        side, kind, _d = _provenance(p)
        rec = file_rec(p, base)
        rec.update({"sha256": sha256_file(p), "provenance": side, "source_kind": kind})
        if side is None:
            warnings.append(f"{os.path.basename(p)} has no provenance sidecar: prompt_lint refuses a reference "
                            f"without one (provenance.py record)")
        elif kind in ("ai-generated", "ai", "generated"):
            warnings.append(f"⛔ {os.path.basename(p)}'s provenance says {kind}: the house rule is no AI images as "
                            f"references — use a real, cleared photograph (or the gate's own approved route)")
        refs.append(rec)
    dur = nw / fps
    if dur < MIN_PLATE_S - 1e-6:
        warnings.append(f"the plate runs {dur:.2f} s: video_edit wants at least {MIN_PLATE_S:g} s (pad a freeze on "
                        f"its last frame, motion-design.md §2.4)")
    if dur > MAX_PLATE_S + 1e-6:
        warnings.append(f"the plate runs {dur:.2f} s: the vendor deck says a video-edit source is under "
                        f"{MAX_PLATE_S:g} s — limit it with track --frames")
    label = region["label"]
    plate = os.path.join(base, f"MASKED-{label}.mp4")
    full = (s == 0 and e == info["frames"] - 1)
    audio = None
    if info["audio"]:
        audio = {"path": src, "codec": info["audio"]["codec"], "copy": full,
                 "start": 0.0 if full else s / fps, "dur": None if full else nw / fps}
    rd = Reader(src, info, pix="rgb24", start=s, count=nw)
    wr = Writer(plate, W, H, info["rate"], info, "h264", "rgb24", audio)
    shape = region.get("pad_shape", "rect")
    per = []
    black_px = 0
    try:
        for j, m in enumerate(iter_masks(np, cv2, base, mrec, W, H, s, e)):
            fr = rd.read()
            if fr is None:
                raise Usage(f"{src} ended at work frame {j} of {nw}")
            hard, bbox = region_hard(np, cv2, m, a.pad, shape)
            if bbox is None:
                wr.write(fr)
                per.append({"f": s + j, "bbox": None, "area": 0})
                continue
            al = plate_alpha(np, cv2, hard, bbox, a.feather)
            x0, y0, x1, y1 = _crop(bbox, int(math.ceil(a.feather)) + 2, W, H)
            out = np.array(fr)
            sub = out[y0:y1, x0:x1].astype(np.float32) * (1.0 - al[y0:y1, x0:x1, None])
            out[y0:y1, x0:x1] = np.clip(np.round(sub), 0, 255).astype(np.uint8)
            wr.write(out)
            area = int((hard > 0).sum())
            black_px += area
            per.append({"f": s + j, "bbox": list(bbox), "area": area})
    finally:
        rd.close()
        wr.close()
    pinfo = probe(plate)
    if pinfo["frames"] != nw or (pinfo["w"], pinfo["h"]) != (W, H) or abs(pinfo["fps"] - fps) > 1e-3:
        raise Usage(f"the plate came out {pinfo['w']}x{pinfo['h']} at {pinfo['fps']:.3f} fps with {pinfo['frames']} "
                    f"frames; expected {W}x{H} at {fps:.3f} with {nw}")
    if info["audio"] and not pinfo["audio"]:
        raise Usage("the plate lost the source's sound")
    job = {
        "tool": TOOL, "schema": SCHEMA, "kind": "repair", "label": label, "created": now(),
        "region": dict(file_rec(rp, base), sha256=sha256_file(rp)),
        "source": region["source"], "range": region["range"], "engine": region["engine"],
        "pad": a.pad, "feather": a.feather, "pad_shape": shape, "contains": contains, "ref_images": refs,
        "allow_lost": bool(a.allow_lost), "unmasked": lost, "masks": mrec, "motion": region["motion"],
        "repaired_span": [s, e],
        "plate": dict(file_rec(plate, base), sha256=sha256_file(plate), frames=pinfo["frames"], fps=pinfo["fps"],
                      duration=round(nw / fps, 6), width=W, height=H, audio=bool(pinfo["audio"]),
                      codec="H.264 CRF 10, 4:2:0, colour tags of the source",
                      start_frame=s, start_s=round(s / fps, 6)),
        "frames": per, "warnings": warnings,
    }
    pr = os.path.join(base, f"REPAIR-{label}.prompt.md")
    job["prompt"] = os.path.basename(pr)
    with open(pr, "w", encoding="utf-8") as f:
        f.write(prompt_stub(job, refs, os.path.relpath(plate, os.path.dirname(base)) if os.path.basename(base) ==
                            "repair" else os.path.basename(plate)))
    jp = os.path.join(base, f"REPAIR-{label}.json")
    write_json(jp, job)
    for w_ in warnings:
        warn(w_)
    if a.json:
        print(json.dumps(job, indent=1))
    say(f"mask: {os.path.basename(plate)} — frames {s}–{e} ({nw}, {dur:.3f} s), {W}x{H}, region grown by {a.pad} px"
        + (f", feathered {a.feather} px outward" if a.feather else "") + f"; sound {'kept' if pinfo['audio'] else 'none'}")
    say(f"  wrote {plate}\n        {jp}\n        {pr}  (a stub: fill it, lint it, call through gate.py)")
    return 0


# ---- composite ----------------------------------------------------------------------------------------------
def _check_job(job, jp, base):
    if job.get("kind") != "repair":
        raise Usage(f"{jp} is not a REPAIR record from mask")
    src = resolve(job["source"], base, "the source clip")
    if sha256_file(src) != job["source"]["sha256"]:
        raise Refused(f"{src} changed after the plate was made (sha256 differs)")
    s, e = job["range"]["work"]
    if masks_sha(base, job["masks"], s, e) != job["masks"]["sha256"]:
        raise Refused("the masks changed after the plate was made: mask again")
    return src


def frame_map(n_plate, n_rep, retime):
    if n_rep == n_plate:
        return list(range(n_plate)), "identity"
    if abs(n_rep - n_plate) == 1 and not retime:
        return [min(j, n_rep - 1) for j in range(n_plate)], (
            "off by one: the model's extra last frame is dropped" if n_rep > n_plate
            else "off by one: the model's last frame is held for the plate's last")
    if n_plate == 1:
        return [0], "retimed"
    return [int(round(j * (n_rep - 1) / float(n_plate - 1))) for j in range(n_plate)], "retimed"


class MappedReader:
    """The model's clip, conformed to the source size, read through the frame map (monotonic)."""

    def __init__(self, path, info, W, H, pix):
        self.rd = Reader(path, info, size=(W, H), pix=pix, flags="lanczos")
        self.idx, self.cur = -1, None

    def get(self, i):
        while self.idx < i:
            f = self.rd.read()
            if f is None:
                break
            self.cur, self.idx = f, self.idx + 1
        return self.cur

    def close(self):
        self.rd.close()


def preview_refusal(out, label):
    """The composite is a PREVIEW (2026-11-05): its name must say so, or it is refused."""
    name = os.path.basename(out)
    if name.startswith(PREVIEW_PREFIX):
        return None
    return (f"--out {name}: the tool's composite is a PREVIEW only, so its file name must start with "
            f"{PREVIEW_PREFIX} (e.g. {PREVIEW_PREFIX}{label}.mov, the default). It is never imported into Resolve "
            f"as footage: the deliverable blend is a Fusion comp built in Resolve by computer control (the "
            f"computer-control rule) — run `fusion --job … --repaired …` for its matte, track and recipe")


def cmd_composite(a):
    np, cv2 = need_np()
    need_ff()
    jp = job_path(a.job)
    job = load_json(jp)
    base = os.path.dirname(jp)
    if job.get("kind") != "repair":
        raise Usage(f"{jp} is not a REPAIR record from mask")
    out = os.path.abspath(a.out or os.path.join(base, f"{PREVIEW_PREFIX}{job['label']}.mov"))
    why = preview_refusal(out, job["label"])
    if why:
        raise Refused(why)
    src = _check_job(job, jp, base)
    info = probe(src)
    rinfo = probe(a.repaired)
    W, H, n, fps = info["w"], info["h"], info["frames"], info["fps"]
    s, e = job["range"]["work"]
    nplate = job["plate"]["frames"]
    warnings = []
    ar_s, ar_r = W / float(H), rinfo["w"] / float(rinfo["h"])
    if abs(ar_r - ar_s) / ar_s > 0.01:
        raise Refused(f"the model's clip is {rinfo['w']}x{rinfo['h']} ({ar_r:.3f}:1), the source {W}x{H} "
                      f"({ar_s:.3f}:1): the picture was reframed and the mask no longer lines up")
    if abs(rinfo["frames"] - nplate) > 1 and not a.retime:
        raise Refused(f"the model's clip has {rinfo['frames']} frames, the plate {nplate}: the timing moved. Use "
                      f"--retime only after reading both (it maps frames proportionally and can hide a drift), or "
                      f"make the call again with the plate's duration")
    if abs(rinfo["fps"] - fps) > 0.01:
        warnings.append(f"the model's clip runs at {rinfo['fps']:.3f} fps, the source at {fps:.3f}"
                        + ("; frames mapped by --retime" if a.retime else ""))
    fmap, mapping = frame_map(nplate, rinfo["frames"], a.retime)
    if mapping != "identity":
        warnings.append(f"frame map: {mapping}")
    kind = out_kind(out)
    if kind == "h264":
        warnings.append(".mp4 is H.264: lossy everywhere, so the pixels outside the mask change by the compression — "
                        "the .mkv is the exact proof")
    if a.feather > job["pad"]:
        warnings.append(f"--feather {a.feather} is wider than the pad ({job['pad']} px): the ramp reaches into the "
                        f"tracked region, where the source still holds the defect")
    if (rinfo["w"], rinfo["h"]) != (W, H):
        warnings.append(f"the model's clip is {rinfo['w']}x{rinfo['h']}: scaled to {W}x{H} (lanczos)")
    pix = work_pix(info) if kind in ("prores", "ffv1") else "rgb24"
    audio = None
    if a.audio == "source" and info["audio"]:
        audio = {"path": src, "codec": info["audio"]["codec"], "copy": True}
    elif a.audio == "repaired":
        if not rinfo["audio"]:
            raise Refused("--audio repaired: the model's clip has no sound")
        audio = {"path": a.repaired, "codec": rinfo["audio"]["codec"], "copy": s == 0, "offset": s / fps}
    elif a.audio == "source" and not info["audio"]:
        warnings.append("the source has no sound")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    rs = Reader(src, info, pix=pix)
    rr = MappedReader(a.repaired, rinfo, W, H, pix)
    wr = Writer(out, W, H, info["rate"], info, kind, pix, audio)
    masks = iter_masks(np, cv2, base, job["masks"], W, H, s, e)
    pad, shape, fe = job["pad"], job.get("pad_shape", "rect"), float(a.feather)
    hi = 65535.0 if pix == "rgb48le" else 255.0
    dtype = np.uint16 if pix == "rgb48le" else np.uint8
    unmasked = set(job.get("unmasked") or [])
    replaced = 0
    try:
        for f in range(n):
            S = rs.read()
            if S is None:
                raise Usage(f"{src} ended at frame {f} of {n}")
            if s <= f <= e:
                m = next(masks)
                R = rr.get(fmap[f - s])
                if R is None:
                    raise Usage(f"{a.repaired} ended before frame {fmap[f - s]}")
                hard, bbox = region_hard(np, cv2, m, pad, shape)
                if bbox is not None and f not in unmasked:
                    al, (x0, y0, x1, y1) = inner_alpha(np, cv2, hard, bbox, fe)
                    O = np.array(S)
                    sa = S[y0:y1, x0:x1].astype(np.float32)
                    ra = R[y0:y1, x0:x1].astype(np.float32)
                    O[y0:y1, x0:x1] = np.clip(np.round(sa + (ra - sa) * al[..., None]), 0, hi).astype(dtype)
                    wr.write(O)
                    replaced += 1
                    continue
            wr.write(S)
    finally:
        rs.close()
        rr.close()
        with contextlib.suppress(Exception):
            masks.close()
        wr.close()
    oinfo = probe(out)
    if oinfo["frames"] != n:
        raise Usage(f"the composite came out with {oinfo['frames']} frames, the source has {n}")
    side = {
        "tool": TOOL, "schema": SCHEMA, "kind": "composite", "created": now(), "label": job["label"],
        "preview": True,
        "deliverable": "no — a preview, never imported into Resolve as footage. The deliverable blend is the Fusion "
                       "comp built in Resolve by computer control (fusion writes its matte, track and RECIPE.md; "
                       "qa --render measures Resolve's render).",
        "job": dict(file_rec(jp, os.path.dirname(out)), sha256=sha256_file(jp)),
        "source": {"path": os.path.abspath(src), "sha256": job["source"]["sha256"]},
        "repaired": dict(file_rec(a.repaired, os.path.dirname(out)), sha256=sha256_file(a.repaired),
                         width=rinfo["w"], height=rinfo["h"], fps=rinfo["fps"], frames=rinfo["frames"],
                         audio=bool(rinfo["audio"])),
        "conform": {"scaled": (rinfo["w"], rinfo["h"]) != (W, H), "from": [rinfo["w"], rinfo["h"]], "to": [W, H],
                    "filter": "lanczos"},
        "mapping": mapping, "retime": bool(a.retime), "map": fmap if mapping != "identity" else None,
        "feather": fe, "pad": pad, "audio": a.audio, "repaired_span": [s, e], "frames_replaced": replaced,
        "out": dict(file_rec(out, os.path.dirname(out)), sha256=sha256_file(out), kind=kind, frames=oinfo["frames"],
                    fps=oinfo["fps"], width=oinfo["w"], height=oinfo["h"], audio=bool(oinfo["audio"]),
                    codec={"prores": "ProRes 4444 qscale 1", "ffv1": "FFV1 RGB lossless",
                           "h264": "H.264 CRF 10"}[kind]),
        "warnings": warnings,
    }
    sp = out + ".repair.json"
    write_json(sp, side)
    for w_ in warnings:
        warn(w_)
    if a.json:
        print(json.dumps(side, indent=1))
    say(f"composite (PREVIEW): {os.path.basename(out)} — {n} frames, the region taken from the model's clip on "
        f"{replaced} frame(s) ({s}–{e}), feather {fe:g} px inside the edge, sound: {a.audio}")
    say(f"  wrote {out}\n        {sp}")
    say("  a PREVIEW only: never import it into Resolve as footage. The deliverable blend is a Fusion comp built "
        "in Resolve by computer control.")
    say(f"  next: qa --composite {os.path.basename(out)} --repaired {os.path.basename(a.repaired)} --job "
        f"{os.path.basename(jp)} (the preview); fusion --job {os.path.basename(jp)} --repaired "
        f"{os.path.basename(a.repaired)} (the comp's matte, track and recipe)")
    return 0


# ---- fusion: what the Fusion comp needs (the deliverable blend, built by computer control) ------------------
TRACK_COLS = ("frame", "source_frame", "lost", "x", "y", "w", "h", "scale", "px_x", "px_y", "px_w", "px_h")


def seq_sha(d, count):
    """sha256 over d/000000.png … d/<count-1>.png in order, or None when one is missing."""
    h = hashlib.sha256()
    for i in range(count):
        p = os.path.join(d, f"{i:06d}.png")
        if not os.path.isfile(p):
            return None
        with open(p, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()


def _q(p):
    return shlex.quote(p)


def fusion_recipe(d):
    """RECIPE.md: the node-by-node build in Resolve's Fusion page, for a person or for Claude by computer control,
    with the real paths and frame numbers."""
    W, H, fps, n, s, e, nw = d["W"], d["H"], d["fps"], d["n"], d["s"], d["e"], d["nw"]
    fg = "Resize1" if d["resize"] else "Loader1"
    L = [f"# Fusion recipe: {d['label']}", "",
         f"Written by {TOOL} fusion on {d['created'][:10]}. This comp is the final blend of the repair. Build it in DaVinci Resolve's Fusion page by computer control: drive the Resolve window. "
         f"Never build or wire the nodes through the scripting API. It cross-wired inputs (the computer-control rule).", "",
         f"The tool's own composite ({PREVIEW_PREFIX}{d['label']}.mov) is a preview only. Never import it as footage.",
         "", "## The files", "",
         f"- Source clip (MediaIn1): `{d['src']}`. {W}x{H}, {fps:.3f} fps, {n} frames (0 to {n - 1}).",
         f"- Repaired clip (Loader1): `{d['loader']}`. {d['lw']}x{d['lh']}, {d['lframes']} frames."
         + (" A copy conformed by fusion --retime: the source's size, the plate's frame count." if d["conformed"]
            else ""),
         f"- Matte (Loader2): `{d['matte_first']}` to `{os.path.basename(d['matte_last'])}`. {nw} frames, {W}x{H}, "
         f"8-bit. The matte is in R, G, B and alpha alike: white = the repair, black = the source. Matte frame 0 is "
         f"source frame {s}. Grown {d['pad']} px ({d['shape']}) and feathered {d['fe']:g} px inside the edge, "
         f"exactly as the tool blends it.",
         f"- Track, for keying a Transform by hand only: `{d['csv']}`.",
         f"- Work range: source frames {s} to {e} ({nw} frames). Global offset: {s}.", "",
         "## Build the comp", ""]
    steps = [
        f"In the Edit page, put the whole source clip on a {W}x{H}, {fps:.3f} fps timeline, untrimmed, so its "
        f"first frame is source frame 0. Open the clip in the Fusion page. Comp frame N is now source frame N. "
        f"If the Fusion time ruler does not start at 0, add its first frame number to every frame number below.",
        "MediaIn1 is the source clip. Leave it as it is.",
        f"Add a Loader (Loader1) and load `{d['loader']}`. On its File tab, set Global In to {s}."
        + (" Set Hold Last Frame to 1: the model's clip is one frame short, so its last frame is held for the "
           "plate's last." if d["hold_last"] else "")
        + (" The model's clip has one extra frame at the end. It is not used: the matte ends before it."
           if d["extra_last"] else "")
        + f" If Resolve's Loader cannot read this file, drag the clip from the Media Pool into the Node Editor "
          f"instead. That makes a MediaIn node; set its Global In to {s} the same way.",
    ]
    if d["resize"]:
        steps.append(f"Add a Resize node (Resize1) after Loader1: Width {W}, Height {H}, Keep Frame Aspect off, "
                     f"Filter Method Lanczos. The model's clip is {d['lw']}x{d['lh']}; the source is {W}x{H}.")
    steps += [
        f"Add a second Loader (Loader2) and load `{d['matte_first']}`. It reads the whole sequence, {nw} frames. On "
        f"its File tab, set Global In to {s}. It needs no trim: matte frame 0 is the first frame of the work range.",
        "Add a Bitmap mask node (Bitmap1) and connect Loader2 to its input. Set its Channel to Luminance (Alpha "
        "also works: the files carry the matte in alpha too). Always set the channel explicitly: a bitmap mask "
        "with no channel set blocks everything. If you connect Loader2 straight to the Effect Mask instead, set "
        "that mask's channel to Luminance before going on.",
        f"Add a Merge (Merge1). Background (the orange input) = MediaIn1. Foreground (the green input) = {fg}. "
        f"Effect Mask (the blue input) = Bitmap1. Leave Merge1 at its defaults: Blend 1.0, Apply Mode Normal, "
        f"Center 0.5, 0.5, Size 1.0.",
        f"Only if the repaired clip is shifted against the source: add a Transform between {fg} and Merge1 and key "
        f"its Center by hand from track.csv (Fusion coordinates: x across, y up from the bottom). Alignment is not "
        f"automated yet.",
        "Connect Merge1 to MediaOut1.",
    ]
    L += [f"{i}. {t}" for i, t in enumerate(steps, 1)]
    checks = [
        f"Comp frame {s} (the first frame of the work range) and comp frame {e} (the last): view Merge1 at full "
        f"size (100 %, not Fit). The region shows the repair, its edge does not show, and nothing outside it moved. "
        f"Compare with MediaIn1 on the same frames.",
    ]
    around = [f for f in (s - 1, e + 1) if 0 <= f < n]
    if around:
        checks.append(f"Comp frame{'s' if len(around) > 1 else ''} {' and '.join(str(f) for f in around)}, just "
                      f"outside the work range: the picture is the untouched source.")
    checks += [
        f"View Bitmap1 on comp frame {d['mid']}: white over the region, black everywhere else. Not all white, not "
        f"all black.",
        "If the region sits brighter or darker than its surround at full size, Loader1 may be reading the colour "
        "differently from MediaIn1 (project colour management). Bring the clip in from the Media Pool as a MediaIn "
        "instead and check again.",
        "After any comp import (a .comp file or pasted nodes), open every Loader again: importing a comp turns "
        "Loaders into empty MediaIns. Load the files again and set Global In again.",
        "Never wire, rewire or set nodes through the scripting API. It cross-wired inputs. Build and fix by computer "
        "control only.",
        "Render with no grade on the clip, or with grades bypassed. A grade reads as drift in qa.",
    ]
    L += ["", "## Check before you render", ""] + [f"{i}. {t}" for i, t in enumerate(checks, 1)]
    cmd = (f"python3 {_q(d['script'])} qa --render {_q(d['render'])} --repaired {_q(d['repaired'])} "
           f"--job {_q(d['job'])}" + (f" --fusion {_q(d['fusion_dir'])}" if d["fusion_dir"] else ""))
    render = [
        f"In the Deliver page, render this clip alone: the whole clip, {n} frames, {W}x{H}, {fps:.3f} fps. Use "
        f"QuickTime ProRes 4444 (qa holds ProRes to its tolerance; H.264 is held to a looser one). Save it as "
        f"`{d['render']}`.",
        f"Measure it:\n\n       {cmd}\n\n   Exit 0 is needed. A FAIL means fix the comp and render again. Drift "
        f"outside the region is reported, not blocking (for now).",
        "Build a contact sheet of the render (contact_sheet.py), first and last frame included, before anyone "
        "sees it.",
    ]
    L += ["", "## Render and measure", ""] + [f"{i}. {t}" for i, t in enumerate(render, 1)]
    if d["warnings"]:
        L += ["", "## Warnings", ""] + [f"- {w_}" for w_ in d["warnings"]]
    return "\n".join(L) + "\n"


def cmd_fusion(a):
    np, cv2 = need_np()
    need_ff()
    jp = job_path(a.job, a.label)
    job = load_json(jp)
    base = os.path.dirname(jp)
    src = _check_job(job, jp, base)
    info = probe(src)
    rinfo = probe(a.repaired)
    W, H, n, fps = info["w"], info["h"], info["frames"], info["fps"]
    s, e = job["range"]["work"]
    nw = e - s + 1
    nplate = job["plate"]["frames"]
    label = a.label or job["label"]
    if a.feather < 0:
        raise Usage("--feather is 0 or more")
    warnings = []
    ar_s, ar_r = W / float(H), rinfo["w"] / float(rinfo["h"])
    if abs(ar_r - ar_s) / ar_s > 0.01:
        raise Refused(f"the model's clip is {rinfo['w']}x{rinfo['h']} ({ar_r:.3f}:1), the source {W}x{H} "
                      f"({ar_s:.3f}:1): the picture was reframed and the matte no longer lines up")
    if abs(rinfo["frames"] - nplate) > 1 and not a.retime:
        raise Refused(f"the model's clip has {rinfo['frames']} frames, the plate {nplate}: the timing moved. Make "
                      f"the call again with the plate's duration, or use --retime after reading both (it writes a "
                      f"copy mapped proportionally to the plate's frames, which can hide a drift)")
    if abs(rinfo["fps"] - fps) > 0.01:
        warnings.append(f"the model's clip runs at {rinfo['fps']:.3f} fps, the source at {fps:.3f}: Fusion takes its "
                        f"frames one for one")
    fmap, mapping = frame_map(nplate, rinfo["frames"], a.retime)
    if mapping != "identity":
        warnings.append(f"frame map: {mapping}")
    if a.feather > job["pad"]:
        warnings.append(f"--feather {a.feather:g} is wider than the pad ({job['pad']} px): the ramp reaches into the "
                        f"tracked region, where the source still holds the defect")
    for w_ in job.get("warnings") or []:
        if "--allow-lost" in w_:
            warnings.append(w_)
    fd = os.path.join(os.path.abspath(a.out or base), f"FUSION-{label}")
    md = os.path.join(fd, "matte")
    os.makedirs(md, exist_ok=True)
    for f_ in os.listdir(md):
        if re.fullmatch(r"\d{6}\.png", f_):
            os.remove(os.path.join(md, f_))
    pad, shape, fe = int(job["pad"]), job.get("pad_shape", "rect"), float(a.feather)
    unmasked = set(job.get("unmasked") or [])
    rows = []
    ref = None
    masks = iter_masks(np, cv2, base, job["masks"], W, H, s, e)
    try:
        for i, m in enumerate(masks):
            f = s + i
            hard, bbox = region_hard(np, cv2, m, pad, shape)
            mt = np.zeros((H, W), np.uint8)
            lost = bbox is None or f in unmasked
            if not lost:
                al, (x0, y0, x1, y1) = inner_alpha(np, cv2, hard, bbox, fe)
                mt[y0:y1, x0:x1] = np.clip(np.round(al * 255.0), 0, 255).astype(np.uint8)
            cv2.imwrite(os.path.join(md, f"{i:06d}.png"), cv2.merge([mt, mt, mt, mt]))
            row = {"frame": i, "source_frame": f, "lost": lost}
            if not lost:
                bx0, by0, bx1, by1 = bbox
                bw, bh = bx1 - bx0, by1 - by0
                if ref is None:
                    ref = float(bw * bh)
                row.update(x=round((bx0 + bw / 2.0) / W, 6), y=round(1.0 - (by0 + bh / 2.0) / H, 6),
                           w=round(bw / float(W), 6), h=round(bh / float(H), 6),
                           scale=round(math.sqrt(bw * bh / ref), 6), px_x=int(bx0), px_y=int(by0), px_w=int(bw),
                           px_h=int(bh))
            rows.append(row)
    finally:
        with contextlib.suppress(Exception):
            masks.close()
    if len(rows) != nw:
        raise Usage(f"wrote {len(rows)} matte frames, the work range has {nw}")
    lost_rows = [r["source_frame"] for r in rows if r["lost"]]
    with open(os.path.join(fd, "track.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(TRACK_COLS) + "\n")
        for r in rows:
            fh.write(",".join("1" if (c == "lost" and r[c]) else "0" if c == "lost" else str(r.get(c, ""))
                              for c in TRACK_COLS) + "\n")
    write_json(os.path.join(fd, "track.json"), {
        "tool": TOOL, "schema": SCHEMA, "kind": "fusion-track", "label": label, "width": W, "height": H, "fps": fps,
        "global_offset": s, "work": [s, e],
        "coordinates": "Fusion's: x = the region's centre x / the frame width, y = 1 − centre y / the frame height "
                       "(0,0 bottom left, 1,1 top right); w, h = the region's size / the frame's width and height; "
                       "scale = the square root of its area against its area on the first tracked frame. The "
                       "region is the grown one the matte holds (its bounding box).",
        "columns": {"frame": "matte frame = comp frame − global_offset", "source_frame": "the source's frame",
                    "lost": "1 = no region on this frame (the matte is black, the source shows)",
                    "px_x, px_y, px_w, px_h": "the same box in source pixels, y down"},
        "frames": rows, "lost": lost_rows})
    conformed = None
    loader = os.path.abspath(a.repaired)
    lw, lh, lframes = rinfo["w"], rinfo["h"], rinfo["frames"]
    if mapping == "retimed":
        cpath = os.path.join(fd, "repaired-conformed.mov")
        pix = "rgb48le" if rinfo["bits"] > 8 else "rgb24"
        rr = MappedReader(a.repaired, rinfo, W, H, pix)
        wr = Writer(cpath, W, H, info["rate"], info, "prores", pix)
        try:
            for j in range(nw):
                R = rr.get(fmap[j])
                if R is None:
                    raise Usage(f"{a.repaired} ended before frame {fmap[j]}")
                wr.write(R)
        finally:
            rr.close()
            wr.close()
        ci = probe(cpath)
        if ci["frames"] != nw:
            raise Usage(f"the conformed copy came out with {ci['frames']} frames, the work range has {nw}")
        conformed = dict(file_rec(cpath, fd), sha256=sha256_file(cpath), frames=nw, width=W, height=H,
                         codec="ProRes 4444 qscale 1, scaled (lanczos) and mapped to the plate's frames")
        loader, lw, lh, lframes = cpath, W, H, nw
    msha = seq_sha(md, nw)
    rec = {
        "tool": TOOL, "schema": SCHEMA, "kind": "fusion", "label": label, "created": now(),
        "job": dict(file_rec(jp, fd), sha256=sha256_file(jp)),
        "source": {"path": os.path.abspath(src), "sha256": job["source"]["sha256"], "width": W, "height": H,
                   "fps": fps, "frames": n},
        "repaired": dict(file_rec(a.repaired, fd), sha256=sha256_file(a.repaired), width=rinfo["w"],
                         height=rinfo["h"], fps=rinfo["fps"], frames=rinfo["frames"]),
        "conformed": conformed, "loader": file_rec(loader, fd),
        "work": [s, e], "global_offset": s, "plate_frames": nplate,
        "mapping": mapping, "retime": bool(a.retime), "map": fmap if mapping != "identity" else None,
        "matte": {"dir": "matte", "pattern": "%06d.png", "first": 0, "count": nw, "source_first": s, "sha256": msha,
                  "pad": pad, "pad_shape": shape, "feather": fe, "bits": 8,
                  "channels": "R = G = B = alpha = the matte: 0 outside the grown region, a smoothstep ramp over "
                              "the feather inside its edge, 255 deeper in (the blend composite uses)",
                  "unmasked": lost_rows},
        "track": {"csv": "track.csv", "json": "track.json"}, "recipe": "RECIPE.md",
        "build": "a Fusion comp in Resolve, by computer control, never through the scripting API (the computer-control rule)",
        "warnings": warnings,
    }
    write_json(os.path.join(fd, "fusion.json"), rec)
    rp = os.path.join(fd, "RECIPE.md")
    with open(rp, "w", encoding="utf-8") as fh:
        fh.write(fusion_recipe({
            "label": label, "created": rec["created"], "W": W, "H": H, "fps": fps, "n": n, "s": s, "e": e, "nw": nw,
            "src": os.path.abspath(src), "loader": loader, "lw": lw, "lh": lh, "lframes": lframes,
            "conformed": conformed is not None, "resize": (lw, lh) != (W, H),
            "hold_last": conformed is None and lframes == nw - 1, "extra_last": conformed is None and lframes == nw + 1,
            "matte_first": os.path.join(md, "000000.png"), "matte_last": os.path.join(md, f"{nw - 1:06d}.png"),
            "pad": pad, "shape": shape, "fe": fe, "csv": os.path.join(fd, "track.csv"), "mid": s + nw // 2,
            "script": os.path.abspath(__file__), "render": os.path.join(base, f"RENDER-{label}.mov"),
            "repaired": os.path.abspath(a.repaired), "job": jp, "warnings": warnings,
            "fusion_dir": None if fd == os.path.join(base, f"FUSION-{job['label']}") else fd}))
    for w_ in warnings:
        warn(w_)
    if a.json:
        print(json.dumps(rec, indent=1))
    say(f"fusion: {fd} — matte {nw} frames (000000.png = source frame {s}, Global In {s}), grown {pad} px, "
        f"feathered {fe:g} px; track.csv ({len(lost_rows)} lost); RECIPE.md"
        + ("; repaired-conformed.mov (--retime)" if conformed else ""))
    say(f"  next: build the comp in Resolve's Fusion page by computer control, following {rp}; render the whole "
        f"clip from Resolve; then qa --render <the render> --repaired {os.path.basename(a.repaired)} --job "
        f"{os.path.basename(jp)}")
    return 0


# ---- qa -----------------------------------------------------------------------------------------------------
def _luma(np, x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


SIDES = ("left", "right", "top", "bottom")


def _sides(np, mask, bb):
    """Split mask pixels by the nearest edge of the bbox (x0, y0, x1, y1), crop coordinates."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return ys, xs, np.zeros(0, int)
    d = np.stack([xs - bb[0], (bb[2] - 1) - xs, ys - bb[1], (bb[3] - 1) - ys])
    return ys, xs, np.argmin(d, axis=0)


def _tex(np, cv2, Yc, rgb, region):
    """Laplacian variance, robust noise sigma, 2nd-percentile luma, mean saturation over a region of a crop."""
    if region.sum() < 30:
        return None
    er = cv2.erode(region.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    if er.sum() < 20:
        er = region
    lap = cv2.Laplacian(Yc, cv2.CV_32F, ksize=3)
    y8 = np.clip(np.round(Yc), 0, 255).astype(np.uint8)
    hp = Yc - cv2.medianBlur(y8, 3).astype(np.float32)
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    return {"sharp": float(lap[er].var()), "noise": float(1.4826 * np.median(np.abs(hp[er]))),
            "black": float(np.percentile(Yc[region], 2)), "sat": float(sat[region].mean())}


def _stops(np, x, stops):
    lin = np.power(np.clip(x.astype(np.float32) / 255.0, 0, 1), 2.4) * (2.0 ** stops)
    return np.clip(np.power(np.clip(lin, 0, 1), 1 / 2.4) * 255.0, 0, 255).astype(np.uint8)


def qa_sheet(np, cv2, path, rows, verdict):
    """rows: [(frame, {src, rep, comp, hard}, {side: status}, black_status)]. Colour tiles only."""
    col = {"PASS": GREEN, "WARN": AMBER, "FAIL": RED, "n/a": GREY}
    th = 200
    built = []
    for f, crops, sides, blk in rows:
        S, R, C, Hm = crops["src"], crops["rep"], crops["comp"], crops["hard"]
        h, w = S.shape[:2]
        tw = max(40, min(360, int(round(th * w / float(h)))))

        def fit(x, interp=cv2.INTER_AREA):
            return cv2.resize(x, (tw, th), interpolation=interp)
        diff = np.clip(np.abs(C.astype(np.int16) - S.astype(np.int16)) * 8, 0, 255).astype(np.uint8)
        src_t = fit(S).copy()
        hm = fit(Hm, cv2.INTER_NEAREST)
        cs, _ = cv2.findContours((hm > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(src_t, cs, -1, (0, 255, 255), 1)
        tiles = [src_t, fit(R), fit(C), fit(diff), fit(_stops(np, C, 2.0)), fit(_stops(np, C, -2.0))]
        status = np.full((th, 28, 3), 24, np.uint8)
        for i, sd in enumerate(SIDES + ("black",)):
            st = blk if sd == "black" else sides.get(sd, "n/a")
            c = col.get(st, GREY)
            y0 = 6 + i * 38
            status[y0:y0 + 30, 4:24] = c[::-1]           # RGB tiles: reverse the BGR constant
        built.append(np.hstack([status] + [np.pad(t, ((0, 0), (2, 2), (0, 0)), constant_values=24) for t in tiles]))
    if not built:
        return []
    wmax = max(b.shape[1] for b in built)
    built = [np.pad(b, ((0, 6), (0, wmax - b.shape[1]), (0, 0)), constant_values=24) for b in built]
    top = np.zeros((14, wmax, 3), np.uint8)
    top[:] = col.get(verdict, GREY)[::-1]
    sheet = np.vstack([top] + built)
    cv2.imwrite(path, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
    return [r[0] for r in rows]


def _qa_preview(a, jp, cpath, rsha, F):
    """--composite: the tool's PREVIEW, measured against the record composite wrote beside it."""
    sp = cpath + ".repair.json"
    if not os.path.isfile(sp):
        raise Usage(f"{sp} missing — qa --composite reads the record composite writes beside its output; run "
                    f"composite first, or measure Resolve's render of the Fusion comp with qa --render")
    side = load_json(sp)
    if side["job"]["sha256"] != sha256_file(jp):
        F("identity", "the REPAIR record changed after composite ran")
    if rsha != side["repaired"]["sha256"]:
        F("identity", f"{os.path.basename(a.repaired)} is not the clip composite used (sha256 differs)")
    if sha256_file(cpath) != side["out"]["sha256"]:
        F("identity", f"{os.path.basename(cpath)} changed after composite wrote it")
    return {"mode": "preview", "what": "the composite", "key": "composite", "kind": side["out"]["kind"],
            "feather": float(side.get("feather", 0)), "map": side.get("map"), "mapping": side.get("mapping"),
            "retime": bool(side.get("retime")), "audio_expected": side.get("audio") == "source",
            "record": {"sidecar": os.path.basename(sp), "preview": bool(side.get("preview")),
                       "note": "this measured the tool's PREVIEW; the deliverable is Resolve's render of the "
                               "Fusion comp — measure it with qa --render"}}


def _qa_render(a, job, jp, base, rsha, rinfo, cinfo, F, Wn):
    """--render: Resolve's render of the Fusion comp. No composite sidecar: identity comes from the job and from
    the FUSION record (the repaired clip and the matte fusion wrote), the pad from the job, the feather from the
    FUSION record, the drift tolerance from the render's own codec."""
    nplate = job["plate"]["frames"]
    fz = os.path.abspath(os.path.expanduser(a.fusion)) if a.fusion else os.path.join(base, f"FUSION-{job['label']}")
    fj = fz if fz.endswith(".json") else os.path.join(fz, "fusion.json")
    fus = load_json(fj) if os.path.isfile(fj) else None
    rec = {"fusion": fj if fus else None}
    if fus:
        if fus.get("kind") != "fusion":
            raise Usage(f"{fj} is not a FUSION record from fusion")
        fdir = os.path.dirname(fj)
        if fus["job"]["sha256"] != sha256_file(jp):
            F("identity", "the REPAIR record changed after fusion wrote the matte")
        if fus["repaired"]["sha256"] != rsha:
            F("identity", f"{os.path.basename(a.repaired)} is not the clip fusion was given (sha256 differs)")
        mt = fus["matte"]
        if seq_sha(os.path.join(fdir, mt["dir"]), int(mt["count"])) != mt["sha256"]:
            F("identity", "the matte files changed, or went missing, after fusion wrote them")
        if fus.get("conformed"):
            try:
                cp = resolve(fus["conformed"], fdir, "the conformed copy")
                if sha256_file(cp) != fus["conformed"]["sha256"]:
                    F("identity", f"{os.path.basename(cp)} changed after fusion wrote it")
            except Usage as ex:
                F("identity", str(ex))
        fe = float(mt["feather"])
        if a.feather is not None and abs(float(a.feather) - fe) > 1e-9:
            Wn("identity", f"--feather {a.feather:g} ignored: fusion built the matte at {fe:g} px")
        fmap, mapping, retime = fus.get("map"), fus.get("mapping"), bool(fus.get("retime"))
    else:
        # (v2.50, the review) the deliverable comp is built from `fusion`'s recipe, so its record must exist: without
        # it nothing proves the comp used this repaired clip and this matte (and not the PREVIEW composite)
        fe = float(a.feather) if a.feather is not None else FUSION_FEATHER
        F("identity", f"no FUSION record at {fj}: run `region_repair.py fusion` and build the comp from its RECIPE.md "
                      f"(or pass --fusion) — qa cannot prove the repaired clip and the matte are the ones the comp used")
        retime = abs(rinfo["frames"] - nplate) > 1
        fmap, mapping = frame_map(nplate, rinfo["frames"], retime)
    codec = (cinfo.get("codec") or "").lower()
    kind = codec if codec in DRIFT_TOL else "h264"
    rec.update(codec=codec or None, tolerance_of=kind,
               note="Resolve's render of the Fusion comp (the deliverable blend)")
    return {"mode": "render", "what": "the render", "key": "render", "kind": kind, "feather": fe,
            "map": fmap if mapping != "identity" else None, "mapping": mapping, "retime": retime,
            "audio_expected": True, "record": rec}


def cmd_qa(a):
    np, cv2 = need_np()
    need_ff()
    jp = job_path(a.job)
    job = load_json(jp)
    if job.get("kind") != "repair":
        raise Usage(f"{jp} is not a REPAIR record from mask")
    base = os.path.dirname(jp)
    cpath = os.path.abspath(a.render or a.composite)
    res = {"fails": [], "warns": [], "checks": {}}

    def F(check, msg):
        res["fails"].append({"check": check, "why": msg})

    def Wn(check, msg):
        res["warns"].append({"check": check, "why": msg})
    # identity: the files qa measures are the ones composite (or fusion) used
    src = resolve(job["source"], base, "the source clip")
    if sha256_file(src) != job["source"]["sha256"]:
        F("identity", "the source changed after the plate was made")
    s, e = job["range"]["work"]
    if masks_sha(base, job["masks"], s, e) != job["masks"]["sha256"]:
        F("identity", "the masks changed after the plate was made")
    sinfo, rinfo, cinfo = probe(src), probe(a.repaired), probe(cpath)
    rsha = sha256_file(a.repaired)
    ctx = (_qa_render(a, job, jp, base, rsha, rinfo, cinfo, F, Wn) if a.render else
           _qa_preview(a, jp, cpath, rsha, F))
    ctx["path"] = cpath
    what, render = ctx["what"], ctx["mode"] == "render"
    W, H, n, fps = sinfo["w"], sinfo["h"], sinfo["frames"], sinfo["fps"]
    # (f) counts
    cnt = {"source": [n, round(fps, 4)], ctx["key"]: [cinfo["frames"], round(cinfo["fps"], 4)],
           "repaired": [rinfo["frames"], round(rinfo["fps"], 4)], "plate": job["plate"]["frames"]}
    st_f = "PASS"
    if cinfo["frames"] != n or abs(cinfo["fps"] - fps) > 0.01 or (cinfo["w"], cinfo["h"]) != (W, H):
        F("counts", f"{what} is {cinfo['w']}x{cinfo['h']}, {cinfo['frames']} frames at {cinfo['fps']:.3f} fps; "
                    f"the source {W}x{H}, {n} at {fps:.3f}"
                    + (" — render the whole source clip, untrimmed, at its size and frame rate" if render else ""))
        st_f = "FAIL"
    if abs(rinfo["frames"] - job["plate"]["frames"]) > 1 and not ctx["retime"]:
        F("counts", f"the model's clip has {rinfo['frames']} frames, the plate {job['plate']['frames']}")
        st_f = "FAIL"
    elif ctx["mapping"] not in (None, "identity"):
        Wn("counts", f"frame map: {ctx['mapping']}")
        st_f = "WARN" if st_f == "PASS" else st_f
    if sinfo["audio"] and ctx["audio_expected"] and not cinfo["audio"]:
        Wn("counts", f"the source has sound and {what} has none")
    cnt["duration_s"] = {"source": round(n / fps, 4),
                         ctx["key"]: round(cinfo["frames"] / max(cinfo["fps"], 1e-6), 4)}
    res["checks"]["counts"] = dict(status=st_f, **cnt)
    if cinfo["frames"] != n or (cinfo["w"], cinfo["h"]) != (W, H):
        return _qa_finish(np, cv2, a, job, base, res, None, [], ctx)
    # (--cut) a later cut against the repaired span
    cut = parse_frames(a.cut, n) if a.cut else None
    cf, cw = cut_findings(cut, s, e, job.get("unmasked") or [])
    for x in cf:
        F("cut", x)
    for x in cw:
        Wn("cut", x)
    kind = ctx["kind"]
    tol_mean, tol_p = DRIFT_TOL[kind]
    if kind == "ffv1" and sinfo["bits"] > 8:       # a 16-bit composite read back at 8 bits rounds once more
        tol_mean, tol_p = 0.5, 1.0
    guard = 1 if kind == "ffv1" else 2
    pad, fe, shape = int(job["pad"]), float(ctx["feather"]), job.get("pad_shape", "rect")
    fmap = ctx["map"] or list(range(e - s + 1))
    pix = "rgb24"
    rs = Reader(src, sinfo, pix=pix)
    rc = Reader(cpath, cinfo, pix=pix)
    rr = MappedReader(a.repaired, rinfo, W, H, pix)
    last_r = None                 # the model's frame on the previous work frame (the one-frame-late test)
    pcov = None                   # the previous judged frame's crop, for the one-frame-early test
    masks = iter_masks(np, cv2, base, job["masks"], W, H, s, e)
    hist = np.zeros(256, np.int64)
    raw_sum, raw_abs, raw_n = np.zeros(3), 0.0, 0
    SB = max(pad, 4)
    RING = max(RING_MIN, pad)
    per = []
    prev = None
    keep = {}
    top = []
    gk = cv2.getStructuringElement(cv2.MORPH_RECT, (2 * guard + 1, 2 * guard + 1))
    unmasked = set(job.get("unmasked") or [])
    tex_every = max(1, int(round((e - s + 1) / 50.0)))     # texture is a median: ~50 frames are plenty
    try:
        for f in range(n):
            S, C = rs.read(), rc.read()
            if S is None or C is None:
                break
            dfull = cv2.absdiff(C, S)                         # every pixel; the region is taken back out below
            hist += np.bincount(dfull.ravel(), minlength=256)[:256]
            if not (s <= f <= e):
                continue
            j = f - s
            m = next(masks)
            R = rr.get(fmap[j])
            r_prev, last_r = last_r, R
            hard, bbox = region_hard(np, cv2, m, pad, shape)
            if bbox is None or f in unmasked:
                pcov = None
                continue
            gx0, gy0, gx1, gy1 = _crop(bbox, guard + 1, W, H)
            gm = cv2.dilate(hard[gy0:gy1, gx0:gx1], gk) > 0
            hist -= np.bincount(dfull[gy0:gy1, gx0:gx1][gm].ravel(), minlength=256)[:256]
            # the model's own drift outside the region: every 2nd pixel each way, 8 px clear of the region
            fx0, fy0, fx1, fy1 = _crop(bbox, 8, W, H)
            dd = R[::2, ::2].astype(np.float32) - S[::2, ::2].astype(np.float32)
            ex = np.ones(dd.shape[:2], bool)
            ex[fy0 // 2:(fy1 + 1) // 2, fx0 // 2:(fx1 + 1) // 2] = False
            rd_ = dd[ex]
            raw_sum += rd_.sum(axis=0)
            raw_abs += float(np.abs(rd_).sum())
            raw_n += rd_.shape[0]
            # the local crop
            M = RING + SB + int(fe) + 6
            x0, y0, x1, y1 = _crop(bbox, M, W, H)
            hc = hard[y0:y1, x0:x1]
            Sc, Rc, Cc = (X[y0:y1, x0:x1].astype(np.float32) for X in (S, R, C))
            Ys, Yr, Yc = _luma(np, Sc), _luma(np, Rc), _luma(np, Cc)
            din = cv2.distanceTransform(hc, cv2.DIST_L2, 5)
            dout = cv2.distanceTransform(np.where(hc > 0, 0, 255).astype(np.uint8), cv2.DIST_L2, 5)
            inside = hc > 0
            band = inside & (din <= SB)
            rim = inside & (din <= RIM_PX)
            core = inside & (din > max(fe, pad, 2))
            if core.sum() < 30:
                core = inside & (din > max(1.0, min(fe, pad)))
            if core.sum() < 30:
                core = inside
            ring = (~inside) & (dout <= RING)
            bb = (bbox[0] - x0, bbox[1] - y0, bbox[2] - x0, bbox[3] - y0)
            rec = {"f": f, "seam": {}, "raw_seam": {}, "rim": {}}
            ys, xs, sd = _sides(np, band, bb)
            dc = np.dstack([Cc - Sc, (Yc - Ys)[..., None]])
            dr = np.dstack([Rc - Sc, (Yr - Ys)[..., None]])
            for i, nm in enumerate(SIDES):
                sel = sd == i
                if sel.sum() >= SEAM_MIN_PX:
                    rec["seam"][nm] = dc[ys[sel], xs[sel]].mean(axis=0).tolist()
                    rec["raw_seam"][nm] = dr[ys[sel], xs[sel]].mean(axis=0).tolist()
            ys, xs, sd = _sides(np, rim, bb)
            for i, nm in enumerate(SIDES):
                sel = sd == i
                if sel.sum() >= SEAM_MIN_PX // 2:
                    rec["rim"][nm] = float((Yr[ys[sel], xs[sel]] < BLACK_Y).mean() - (Ys[ys[sel], xs[sel]] < BLACK_Y).mean())
            rec["black"] = float((Yr[core] < BLACK_Y).mean() - (Ys[core] < BLACK_Y).mean())
            if j % tex_every == 0:
                rec["tex_patch"] = _tex(np, cv2, Yc, Cc, core)
                rec["tex_ring"] = _tex(np, cv2, Yc, Cc, ring)
                rec["tex_src"] = _tex(np, cv2, Ys, Sc, core)
            # (h) coverage: deep inside, where the model's clip and the source differ, whose picture is it?
            dif = core & (np.abs(Yr - Ys) > COVER_DIFF)
            if pcov is not None and pcov["f"] == f - 1 and R is not pcov["R"]:
                px0, py0, px1, py1 = pcov["box"]
                Yn = _luma(np, R[py0:py1, px0:px1].astype(np.float32))
                pcov["rec"]["err_early"] = float(np.median(np.abs(pcov["Yc"] - Yn)[pcov["dif"]]))  # f-1 shows f
            pcov = None
            if int(dif.sum()) >= COVER_MIN_PX:
                er_ = np.abs(Yc - Yr)[dif]
                rec["cover"] = float((er_ < np.abs(Yc - Ys)[dif]).mean())
                rec["cover_err"] = float(np.median(er_))
                if r_prev is not None and r_prev is not R:
                    Yp = _luma(np, r_prev[y0:y1, x0:x1].astype(np.float32))
                    rec["err_late"] = float(np.median(np.abs(Yc - Yp)[dif]))    # frame f shows the model's f-1
                pcov = {"f": f, "box": (x0, y0, x1, y1), "Yc": Yc, "dif": dif, "R": R, "rec": rec}
            mr = float(Yc[ring].mean()) if ring.any() else float(Yc.mean())
            rec["rel_c"] = float(Yc[core].mean()) - mr
            rec["rel_s"] = float(Ys[core].mean()) - mr
            if prev is not None:
                px0, py0, pYc, pYs, pcore = prev
                ox0, oy0, ox1, oy1 = max(x0, px0), max(y0, py0), min(x1, px0 + pYc.shape[1]), min(y1, py0 + pYc.shape[0])
                if ox1 > ox0 and oy1 > oy0:
                    a_ = (slice(oy0 - y0, oy1 - y0), slice(ox0 - x0, ox1 - x0))
                    b_ = (slice(oy0 - py0, oy1 - py0), slice(ox0 - px0, ox1 - px0))
                    both = core[a_] & pcore[b_]
                    if both.sum() >= 30:
                        rec["boil_c"] = float(np.abs(Yc[a_] - pYc[b_])[both].mean())
                        rec["boil_s"] = float(np.abs(Ys[a_] - pYs[b_])[both].mean())
            prev = (x0, y0, Yc, Ys, core)
            score = max([abs(v) for sv in rec["seam"].values() for v in sv] or [0.0])
            rec["score"] = score
            per.append(rec)
            crop = {"src": S[y0:y1, x0:x1].copy(), "rep": R[y0:y1, x0:x1].copy(), "comp": C[y0:y1, x0:x1].copy(),
                    "hard": hc.copy()}
            sc_ = 160.0 / max(1, crop["src"].shape[0])
            if sc_ < 1:
                crop = {k_: cv2.resize(v, (max(1, int(v.shape[1] * sc_)), 160),
                                       interpolation=cv2.INTER_NEAREST if k_ == "hard" else cv2.INTER_AREA)
                        for k_, v in crop.items()}
            if not keep:
                keep["first"] = (f, crop)
            keep["last"] = (f, crop)
            top.append((score, f, crop))
            top = sorted(top, key=lambda t: -t[0])[:3]
    finally:
        rs.close()
        rc.close()
        rr.close()
        with contextlib.suppress(Exception):
            masks.close()
    # (a) drift
    tot = int(hist.sum())
    cum = np.cumsum(hist)
    p999 = int(np.searchsorted(cum, 0.999 * tot)) if tot else 0
    mean_abs = float((hist * np.arange(256)).sum() / max(1, tot))
    mx = int(np.nonzero(hist)[0].max()) if tot else 0
    st = "PASS"
    if mean_abs > tol_mean + 1e-9 or p999 > tol_p:
        # author, 2026-11-05: report it, never block (provisional) — a WARN, kept out of res["fails"]
        Wn("drift", f"{DRIFT_NOTE}: pixels outside the mask differ from the source in {what}: mean "
                    f"{mean_abs:.3f}, p99.9 {p999}, max {mx} levels (tolerance for {kind}: mean {tol_mean}, p99.9 "
                    f"{tol_p})" + (" — a grade, a level change or a misplaced matte in the comp shows here"
                                   if render else ""))
        st = "WARN"
    raw_signed = (raw_sum / max(1, raw_n)).tolist()
    raw_mabs = raw_abs / max(1, raw_n * 3)
    rst = "PASS"
    if max(abs(v) for v in raw_signed) > RAW_DRIFT_SIGNED or raw_mabs > RAW_DRIFT_ABS:
        Wn("drift_raw", f"the model changed the picture outside the region: mean shift R/G/B "
                        f"{', '.join(f'{v:+.1f}' for v in raw_signed)}, mean |change| {raw_mabs:.1f} levels — the blend "
                        f"discards it, but the region was lit to match the model's own picture: read the seam")
        rst = "WARN"
    res["checks"]["drift"] = {"status": st, "blocking": False, "provisional": DRIFT_NOTE,
                              ctx["key"]: {"mean": round(mean_abs, 4), "p99_9": p999, "max": mx,
                                           "tolerance": [tol_mean, tol_p], "codec": kind},
                              "raw": {"status": rst, "signed_rgb": [round(v, 3) for v in raw_signed],
                                      "mean_abs": round(raw_mabs, 3)}}
    if not per:
        F("region", "no frame of the work range had a mask: nothing was repaired")
        return _qa_finish(np, cv2, a, job, base, res, None, [], ctx)
    # (h) coverage: the repair is in the measured file, on the right frames
    cov = [r for r in per if "cover" in r]
    st_c = "PASS" if cov else "n/a"
    cv_rec = {"judged": len(cov), "of": len(per), "diff_levels": COVER_DIFF, "min_share": COVER_MIN}
    if cov:
        miss = [r["f"] for r in cov if r["cover"] < COVER_MIN]
        cv_rec.update(share_min=round(min(r["cover"] for r in cov), 3),
                      share_median=round(float(np.median([r["cover"] for r in cov])), 3),
                      err_median=round(float(np.median([r["cover_err"] for r in cov])), 3), missing=miss)
        if miss:
            F("coverage", f"the repair is missing from {what} on {len(miss)} of {len(cov)} judged frame(s): "
                          f"{spans_txt(miss)} — inside the region the picture there is nearer the source than the "
                          f"model's clip" + (" (check the matte Loader's Global In, and the mask channel set to "
                                             "Luminance)" if render else ""))
            st_c = "FAIL"
        for key, word, fix in (("err_late", "late", "it shows the model's frame before"),
                               ("err_early", "early", "it shows the model's frame after")):
            pairs = [(r["cover_err"], r[key]) for r in cov if key in r]
            if len(pairs) < 3:
                continue
            m0, m1 = float(np.median([p[0] for p in pairs])), float(np.median([p[1] for p in pairs]))
            cv_rec[f"{word}_median"] = round(m1, 3)
            if m0 > OFFSET_MIN and m1 < OFFSET_RATIO * m0:
                F("coverage", f"the repaired clip runs one frame {word} in {what}: on most frames {fix} (median "
                              f"error {m1:.1f} levels, against {m0:.1f} for the right frame)"
                              + (f" — set the repaired Loader's Global In to {s}" if render else ""))
                st_c = "FAIL"
    elif render:
        Wn("coverage", f"coverage not judged: inside the region the model's clip and the source differ by under "
                       f"{COVER_DIFF:g} levels on every frame, so qa cannot see whose picture the render shows — "
                       f"read the frames")
        st_c = "WARN"
    res["checks"]["coverage"] = dict(status=st_c, **cv_rec)
    # (b) seam per side, per channel
    seam = {}
    side_status = {}
    chans = ("R", "G", "B", "Y")
    for nm in SIDES:
        vals = np.array([r["seam"][nm] for r in per if nm in r["seam"]])
        raws = np.array([r["raw_seam"][nm] for r in per if nm in r["raw_seam"]])
        if not len(vals):
            seam[nm] = {"status": "n/a", "frames": 0}
            side_status[nm] = "n/a"
            continue
        med = np.median(vals, axis=0)
        p90 = np.percentile(np.abs(vals), 90, axis=0)
        stt = "PASS"
        worst = int(np.argmax(np.abs(med)))
        if abs(med[worst]) > SEAM_MAX:
            stt = "FAIL"
            F("seam", f"{nm} edge: the patch sits {med[worst]:+.1f} levels off the source on {chans[worst]} "
                      f"(median over {len(vals)} frames; limit ±{SEAM_MAX}) — "
                      f"{', '.join(f'{c} {v:+.1f}' for c, v in zip(chans, med))}")
        elif float(p90.max()) > SEAM_PEAK:
            stt = "WARN"
            Wn("seam", f"{nm} edge: on some frames the step reaches {float(p90.max()):.1f} levels (90th percentile)")
        seam[nm] = {"status": stt, "frames": len(vals), "median": {c: round(float(v), 3) for c, v in zip(chans, med)},
                    "p90_abs": {c: round(float(v), 3) for c, v in zip(chans, p90)},
                    "raw_median": {c: round(float(v), 3) for c, v in zip(chans, np.median(raws, axis=0))}}
        side_status[nm] = stt
    if pad < 4:
        Wn("seam", f"--pad {pad} is under 4 px: the seam band reaches into the tracked region (the defect)")
    res["checks"]["seam"] = {"status": _worst([v["status"] for v in seam.values()]), "band_px": SB,
                             "sides": seam, "measure": f"mean({ctx['key']} - source) in the band of the pad just inside "
                                                       "each edge, per channel, signed; median over frames"}
    # (g) black: still black, black rim
    blk = np.array([r["black"] for r in per])
    sb = [r["f"] for r in per if r["black"] > STILL_BLACK_FAIL]
    st_b = "PASS"
    if sb:
        F("black", f"the region came back still black on {len(sb)} frame(s): {spans_txt(sb)}")
        st_b = "FAIL"
    elif float(blk.max()) > STILL_BLACK_WARN:
        Wn("black", f"part of the region is still black (up to {100 * float(blk.max()):.0f} % beyond the source's own "
                    f"black) on frames {spans_txt([r['f'] for r in per if r['black'] > STILL_BLACK_WARN])}")
        st_b = "WARN"
    rims = {}
    for nm in SIDES:
        v = np.array([r["rim"][nm] for r in per if nm in r["rim"]])
        if not len(v):
            continue
        med, hi_share = float(np.median(v)), float((v > 0.5).mean())
        rims[nm] = {"median": round(med, 3), "share_frames_over_half": round(hi_share, 3)}
        if med > RIM_FAIL or hi_share >= 0.10:
            F("black", f"a black rim on the {nm} edge: {100 * med:.0f} % of the rim black in the model's clip and "
                       f"not in the source (median), {100 * hi_share:.0f} % of frames over half"
                       + (f" — the {fe:g} px feather softens it, it is still the model leaving the edge unfilled" if fe else ""))
            st_b = "FAIL"
    res["checks"]["black"] = {"status": st_b, "still_black_max": round(float(blk.max()), 4),
                              "still_black_frames": sb, "rim": rims, "black_y": BLACK_Y}
    # (c) texture
    tex = {}
    st_t = "PASS"

    def med_of(key, metric):
        v = [r[key][metric] for r in per if r.get(key)]
        return float(np.median(v)) if v else None
    for metric in ("sharp", "noise", "black", "sat"):
        tex[metric] = {k_: r4(med_of(k_, metric)) for k_ in ("tex_patch", "tex_ring", "tex_src")}
    p_, r_, s_ = (tex["sharp"][k_] for k_ in ("tex_patch", "tex_ring", "tex_src"))
    if None not in (p_, r_, s_) and min(r_, s_) > 1e-6:
        if p_ > SHARP_HI * max(r_, s_):
            Wn("texture", f"the patch is too sharp: Laplacian variance {p_:.1f} against {r_:.1f} around it and {s_:.1f} "
                          f"in the source's own region")
            st_t = "WARN"
        elif p_ < SHARP_LO * min(r_, s_):
            Wn("texture", f"the patch is too soft: Laplacian variance {p_:.1f} against {r_:.1f} around it and {s_:.1f} "
                          f"in the source's own region")
            st_t = "WARN"
    p_, r_, s_ = (tex["noise"][k_] for k_ in ("tex_patch", "tex_ring", "tex_src"))
    if None not in (p_, r_, s_) and min(r_, s_) > NOISE_FLOOR:
        if p_ < NOISE_LO * min(r_, s_):
            Wn("texture", f"the patch is too clean: noise {p_:.2f} against {r_:.2f} around it and {s_:.2f} in the "
                          f"source's own region — add the plate's grain in the grade, not here")
            st_t = "WARN"
        elif p_ > NOISE_HI * max(r_, s_):
            Wn("texture", f"the patch is noisier than the plate: {p_:.2f} against {r_:.2f} and {s_:.2f}")
            st_t = "WARN"
    p_, r_, s_ = (tex["black"][k_] for k_ in ("tex_patch", "tex_ring", "tex_src"))
    if None not in (p_, r_, s_) and abs(p_ - r_) > BLACK_LEVEL_DIFF and abs(p_ - s_) > BLACK_LEVEL_DIFF:
        Wn("texture", f"the patch's black level is {p_:.0f} against {r_:.0f} around it and {s_:.0f} in the source's "
                      f"own region (2nd percentile of luma)")
        st_t = "WARN"
    p_, r_, s_ = (tex["sat"][k_] for k_ in ("tex_patch", "tex_ring", "tex_src"))
    if None not in (p_, r_, s_) and min(r_, s_) > 0.02:
        if not (SAT_LO * min(r_, s_) <= p_ <= SAT_HI * max(r_, s_)):
            Wn("texture", f"the patch's saturation {p_:.2f} sits outside the plate's ({r_:.2f} around, {s_:.2f} in "
                          f"the source's region)")
            st_t = "WARN"
    res["checks"]["texture"] = {"status": st_t, "medians": tex,
                                "note": f"patch = {what} inside the region's core; ring = the surround; src = the "
                                        "source's own region. Content differs, so this warns and never fails."}
    # (e) flicker, pop, boil
    rc_ = np.array([r["rel_c"] for r in per])
    rs_ = np.array([r["rel_s"] for r in per])
    st_e = "PASS"
    fl = {}
    if len(per) >= 3:
        dc_, ds_ = np.diff(rc_), np.diff(rs_)
        fc, fs = float(dc_.std()), float(ds_.std())
        lim = max(FLICKER_ABS, FLICKER_REL * fs)
        fl = {"patch_std": round(fc, 3), "source_std": round(fs, 3), "limit": round(lim, 3)}
        if fc > lim:
            F("flicker", f"the patch flickers against its surround: frame-to-frame std {fc:.2f} levels, the source's "
                         f"{fs:.2f} (limit {lim:.2f})")
            st_e = "FAIL"
        jmax = int(np.argmax(np.abs(dc_)))
        pop, spop = float(abs(dc_[jmax])), float(np.abs(ds_).max())
        fl.update(pop=round(pop, 3), pop_frame=per[jmax + 1]["f"], source_pop=round(spop, 3))
        if pop > POP_ABS and pop > POP_REL * max(spop, 0.5):
            F("flicker", f"a one-frame pop of {pop:.1f} levels into frame {per[jmax + 1]['f']} (the source's largest is "
                         f"{spop:.1f})")
            st_e = "FAIL"
    bc = [r["boil_c"] for r in per if "boil_c" in r]
    bs = [r["boil_s"] for r in per if "boil_s" in r]
    if bc and bs:
        mbc, mbs = float(np.mean(bc)), float(np.mean(bs))
        fl.update(boil=round(mbc, 3), source_boil=round(mbs, 3))
        if mbc > BOIL_ABS and mbc > BOIL_REL * max(mbs, 0.25):
            Wn("flicker", f"the patch's texture boils: mean frame-to-frame change {mbc:.2f} levels against the "
                          f"source's {mbs:.2f}")
            st_e = "WARN" if st_e == "PASS" else st_e
    res["checks"]["flicker"] = dict(status=st_e, **fl)
    # (d) the sheet
    rows = []
    seen = set()
    for f, crop in [keep.get("first")] + [(t[1], t[2]) for t in top] + [keep.get("last")]:
        if f in seen:
            continue
        seen.add(f)
        r = next(r for r in per if r["f"] == f)
        ss = {nm: ("FAIL" if nm in r["seam"] and max(abs(v) for v in r["seam"][nm]) > SEAM_MAX else
                   ("PASS" if nm in r["seam"] else "n/a")) for nm in SIDES}
        bst = "FAIL" if r["black"] > STILL_BLACK_FAIL or any(v > 0.5 for v in r["rim"].values()) else "PASS"
        rows.append((f, crop, ss, bst))
    rows.sort(key=lambda t: t[0])
    return _qa_finish(np, cv2, a, job, base, res, rows, per, ctx)


def cut_findings(cut, s, e, unmasked):
    """(fails, warns) for a cut (A, B) against the repaired span s–e — the warning a longer, later cut needs."""
    fails, warns = [], []
    if cut:
        ca, cb = cut
        if ca < s or cb > e:
            fails.append(f"the cut uses frames {ca}–{cb}; the repair covers {s}–{e}: frames "
                         f"{spans_txt([f for f in range(ca, cb + 1) if f < s or f > e])} are unrepaired — track and "
                         f"repair again with --frames {ca}-{cb}")
        unm = [f for f in unmasked if ca <= f <= cb]
        if unm:
            warns.append(f"frames {spans_txt(unm)} inside the cut were left unmasked (--allow-lost): the repair "
                         f"switches off there")
    elif unmasked:
        warns.append(f"frames {spans_txt(unmasked)} were left unmasked (--allow-lost): the repair switches off there")
    return fails, warns


def _worst(sts):
    for s in ("FAIL", "WARN", "PASS"):
        if s in sts:
            return s
    return "n/a"


def _qa_finish(np, cv2, a, job, base, res, rows, per, ctx):
    # drift is reported and never changes the verdict or the exit code (2026-11-05, provisional)
    drift_w = [w_ for w_ in res["warns"] if w_["check"] == "drift"]
    verdict = "FAIL" if res["fails"] else ("WARN" if len(res["warns"]) > len(drift_w) else "PASS")
    outdir = os.path.abspath(a.out_dir or base)
    os.makedirs(outdir, exist_ok=True)
    label = job["label"]
    png = os.path.join(outdir, f"QA-{label}.png")
    shown = qa_sheet(np, cv2, png, rows, verdict) if rows else []
    nm = "render" if ctx["mode"] == "render" else "composite"
    rep = {"tool": TOOL, "schema": SCHEMA, "kind": "qa", "label": label, "created": now(), "verdict": verdict,
           "drift_reported": bool(drift_w), "mode": ctx["mode"], "measured": ctx["record"],
           nm: dict(file_rec(ctx["path"], outdir), sha256=sha256_file(ctx["path"])),
           "repaired": dict(file_rec(a.repaired, outdir), sha256=sha256_file(a.repaired)),
           "job": dict(file_rec(job_path(a.job), outdir)),
           "repaired_span": job.get("repaired_span"), "fails": res["fails"], "warns": res["warns"],
           "checks": res["checks"], "frames_measured": len(per),
           "sheet": {"path": os.path.basename(png) if shown else None, "rows": shown,
                     "columns": ["status", "source (mask outline)", "model's clip (conformed)", nm,
                                 f"|{nm} - source| x8", f"{nm} +2 stops", f"{nm} -2 stops"],
                     "status_squares": list(SIDES) + ["black"],
                     "layout": "one row per frame listed in rows (the first, the worst seams, the last), cropped to "
                               "the region and its surround; the top bar is the verdict; status squares green = "
                               "pass, amber = warn, red = fail, grey = not measured"},
           "thresholds": {"SEAM_MAX": SEAM_MAX, "SEAM_PEAK": SEAM_PEAK, "RIM_FAIL": RIM_FAIL, "BLACK_Y": BLACK_Y,
                          "STILL_BLACK_FAIL": STILL_BLACK_FAIL, "FLICKER_ABS": FLICKER_ABS,
                          "FLICKER_REL": FLICKER_REL, "POP_ABS": POP_ABS, "DRIFT_TOL": DRIFT_TOL,
                          "drift_blocking": False, "COVER_DIFF": COVER_DIFF, "COVER_MIN": COVER_MIN,
                          "OFFSET_RATIO": OFFSET_RATIO, "assumed": True},
           "cannot": "qa cannot say the repair is right: read the frames, at speed, in the cut, and build a contact "
                     "sheet before anyone sees it"}
    jpth = os.path.join(outdir, f"QA-{label}.json")
    write_json(jpth, rep)
    if a.json:
        print(json.dumps(rep, indent=1))
    say(f"qa {label} [{ctx['mode']}: {os.path.basename(ctx['path'])}]: {verdict}"
        + (" (drift reported, not blocking)" if drift_w else "") + f" — {len(per)} frame(s) of the region measured")
    for w_ in drift_w:                             # reported prominently, never blocking
        say(f"  ⚠ DRIFT — {w_['why']}")
    if ctx["mode"] == "preview":
        say("  (a PREVIEW: the deliverable is Resolve's render of the Fusion comp — measure it with qa --render)")
    for k_, c in rep["checks"].items():
        say(f"  {c.get('status', '?'):<5} {k_}")
    for w_ in res["warns"]:
        say(f"  WARN  {w_['check']}: {w_['why']}")
    for f_ in res["fails"]:
        say(f"  FAIL  {f_['check']}: {f_['why']}")
    say(f"  wrote {jpth}" + (f"\n        {png}" if shown else ""))
    say("  qa cannot say the repair is RIGHT: read the sheet, watch it in the cut, and build a contact sheet first.")
    return 1 if res["fails"] else 0


# ---- selftest -----------------------------------------------------------------------------------------------
def _iou(a, b):
    ax1, ay1, bx1, by1 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0.0, min(ax1, bx1) - max(a[0], b[0])), max(0.0, min(ay1, by1) - max(a[1], b[1]))
    inter = iw * ih
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def _fixture(np, cv2):
    """5 s, 640x360, 30 fps: a textured scene under a small camera pan, and a textured plate (the 'gauge')
    moving across it on its own, with a magenta blotch on it (the defect)."""
    W, H, N = 640, 360, 150
    rng = np.random.default_rng(11)
    tex = cv2.GaussianBlur((rng.random((H + 80, W + 240)) * 255).astype(np.float32), (0, 0), 2.2)
    tex = cv2.normalize(tex, None, 40, 200, cv2.NORM_MINMAX)
    bg = np.dstack([tex, tex * 0.92 + 8, tex * 0.8 + 20]).clip(0, 255).astype(np.float32)
    ow, oh = 72, 54
    o = cv2.GaussianBlur((rng.random((oh, ow)) * 255).astype(np.float32), (0, 0), 1.2)
    o = cv2.normalize(o, None, 70, 230, cv2.NORM_MINMAX)
    good = np.dstack([o, o * 0.85 + 10, o * 0.6 + 30]).clip(0, 255)
    good[:3], good[-3:], good[:, :3], good[:, -3:] = 25, 25, 25, 25
    good[14:18, 10:60] = (240, 230, 210)
    good[36:40, 10:44] = (30, 60, 160)
    bad = good.copy()
    cv2.circle(bad, (ow // 2, oh // 2), 11, (225, 40, 205), -1)

    def gt(i):
        cx = 170 + 1.8 * i
        cy = 190 - 0.35 * i + 8 * math.sin(2 * math.pi * i / 75.0)
        return (cx - ow / 2, cy - oh / 2, float(ow), float(oh))

    def render(i, defect=True):
        ox, oy = 4 + 0.9 * i, 30 + 6 * math.sin(2 * math.pi * i / 150.0)
        fr = cv2.warpAffine(bg, np.float32([[1, 0, -ox], [0, 1, -oy]]), (W, H), flags=cv2.INTER_LINEAR)
        x, y, _, _ = gt(i)
        A = np.float32([[1, 0, x], [0, 1, y]])
        layer = cv2.warpAffine(bad if defect else good, A, (W, H), flags=cv2.INTER_LINEAR)
        al = cv2.warpAffine(np.ones((oh, ow), np.float32), A, (W, H), flags=cv2.INTER_LINEAR)[..., None]
        return np.clip(np.round(fr * (1 - al) + layer * al), 0, 255).astype(np.uint8)
    return W, H, N, gt, render


def _raw_tags(path):
    """(primaries, transfer) exactly as ffprobe reads them: "" for a tag the file does not carry."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=color_primaries,color_transfer", "-of", "json", path], capture_output=True, text=True)
    s = (json.loads(r.stdout or "{}").get("streams") or [{}])[0]
    return (s.get("color_primaries") or "", s.get("color_transfer") or "")


def _enc(np, path, frames, W, H, fps=30, audio=False, crf=12):
    vf = ("scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,"
          "setparams=color_primaries=bt709:color_trc=bt709")      # on the frames: see tag_filter
    cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={len(frames) / fps:.3f}",
                "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"selftest: ffmpeg could not write {path}")


def _run(argv):
    """main() in-process with its output captured: (exit code, stdout+stderr)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            rc = main(argv)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 2
    return rc, buf.getvalue()


def _decode_all(np, path, W, H):
    info = probe(path)
    rd = Reader(path, info, pix="rgb24")
    out = []
    while True:
        f = rd.read()
        if f is None:
            break
        out.append(np.array(f))
    rd.close()
    return np.stack(out)


class _FakePredictor:
    """A stand-in for SAM 2's video predictor: returns the ground-truth rectangle as logits."""

    def __init__(self, np, W, H, gt, s):
        self.np, self.W, self.H, self.gt, self.s = np, W, H, gt, s
        self.calls = []

    def init_state(self, video_path):
        n = len([f for f in os.listdir(video_path) if f.endswith(".jpg")])
        return {"n": n, "dir": video_path}

    def add_new_points_or_box(self, inference_state, frame_idx, obj_id, points=None, labels=None, box=None):
        self.calls.append(("prompt", frame_idx, None if box is None else box.tolist()))

    def propagate_in_video(self, inference_state, start_frame_idx=None, reverse=False):
        np = self.np
        rng_ = range(start_frame_idx, -1, -1) if reverse else range(start_frame_idx, inference_state["n"])
        for fi in rng_:
            x, y, w, h = self.gt(self.s + fi)
            lg = np.full((1, 1, self.H, self.W), -8.0, np.float32)
            lg[0, 0, int(round(y)):int(round(y + h)), int(round(x)):int(round(x + w))] = 8.0
            yield fi, [1], lg


def selftest():
    t0 = time.time()
    np, cv2 = deps()
    # pure functions — run anywhere
    assert spans([3, 4, 5, 9]) == [[3, 5], [9, 9]]
    assert frame_map(10, 10, False)[1] == "identity" and frame_map(10, 11, False)[0][-1] == 9
    assert frame_map(10, 9, False)[0][-1] == 8 and frame_map(10, 20, True)[0][-1] == 19
    r = plan_range(300, 30.0, (100, 130), 12)
    assert r["work"][1] - r["work"][0] + 1 >= 120 and r["work"][0] <= 88 and r["work"][1] >= 142, r
    assert (r["work"][1] - r["work"][0] + 1) % 30 == 0, r
    r = plan_range(90, 30.0, (10, 20), 12)
    assert r["work"] == [0, 89] and r["notes"], r                         # a 3 s clip: all of it, and a note
    assert plan_range(150, 30.0, None, 12)["work"] == [0, 149]
    assert cut_findings((20, 90), 10, 120, []) == ([], [])
    fl, _w = cut_findings((5, 130), 10, 120, [])
    assert fl and "5–9, 121–130" in fl[0], fl                      # a longer, later cut is refused
    assert cut_findings((20, 90), 10, 120, [40, 41])[1] and cut_findings(None, 10, 120, [40])[1]
    if np is None:
        print("selftest OK — ⛔ numpy/OpenCV absent: only the pure functions ran; NOTHING was tracked or measured")
        return 0
    b, _ = parse_box("10%,20%,25%,50%", 640, 360)
    assert [round(v, 6) for v in b] == [64.0, 72.0, 160.0, 180.0], b
    b, clipped = parse_box("600,300,100,100", 640, 360)
    assert clipped and b == (600.0, 300.0, 40.0, 60.0), b
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("selftest OK — ⛔ ffmpeg/ffprobe absent: the pure functions ran; the end-to-end leg did NOT run")
        return 0
    done = []
    with tempfile.TemporaryDirectory(prefix="rr-selftest-") as td:
        W, H, N, gt, render = _fixture(np, cv2)
        clip = os.path.join(td, "fixture.mp4")
        _enc(np, clip, [render(i) for i in range(N)], W, H, audio=True)
        rep = os.path.join(td, "repair")
        # 0. every writer tags its file with the source's primaries and transfer (tag_filter). Read with the raw
        # probe: probe() fills an untagged file with a guess, and a guess can equal what was asked for.
        assert tag_filter({"primaries": "bt709", "transfer": "gamma22"}) == "setparams=color_primaries=bt709:color_trc=bt470m"
        assert tag_filter({"primaries": "unknown-to-ffmpeg", "transfer": ""}) == ""
        src_tags = _raw_tags(clip)
        assert src_tags == ("bt709", "bt709"), src_tags
        for kind, ext, pix in (("h264", ".mp4", "rgb24"), ("prores", ".mov", "rgb48le"), ("ffv1", ".mkv", "rgb24")):
            for prim, trc in (("bt709", "iec61966-2-1"), ("smpte170m", "smpte170m")):
                tp = os.path.join(td, f"tags-{kind}-{prim}{ext}")
                wr = Writer(tp, 64, 48, "30/1", {"color": {"matrix": prim, "range": "tv", "primaries": prim,
                                                           "transfer": trc, "assumed": []}}, kind, pix)
                for _ in range(3):
                    wr.write(np.zeros((48, 64, 3), np.uint16 if pix == "rgb48le" else np.uint8))
                wr.close()
                assert _raw_tags(tp) == (prim, trc), (kind, prim, trc, _raw_tags(tp))
        done.append("every writer (H.264, ProRes, FFV1) tags its file with the source's primaries and transfer")
        # 1. track (box engine), anchored mid-clip so it runs forwards and backwards
        g = gt(60)
        rc, out = _run(["track", clip, "--box", ",".join(f"{v:.2f}" for v in g), "--at", "2.0", "--label", "st",
                        "--out", rep])
        assert rc == 0, out
        region = load_json(os.path.join(rep, "REGION-st.json"))
        assert len(region["frames"]) == N and not region["lost"], region["lost"]
        ious = [_iou(fr["box"], gt(fr["f"])) for fr in region["frames"]]
        assert min(ious) >= 0.8, (min(ious), int(np.argmin(ious)))
        assert region["motion"]["fixed_to_scene"] is False, region["motion"]
        assert os.path.isfile(os.path.join(rep, "CHECK-st.png"))
        done.append(f"box track IoU ≥ {min(ious):.3f} on all {N} frames (forwards and backwards from frame 60)")
        # 2. mask: the plate, its record and the stub
        rc, out = _run(["mask", "--region", os.path.join(rep, "REGION-st.json"), "--pad", "12", "--contains",
                        "a small grey instrument plate with a white bar and a blue bar, no blotch"])
        assert rc == 0, out
        job = load_json(os.path.join(rep, "REPAIR-st.json"))
        plate = os.path.join(rep, "MASKED-st.mp4")
        pi = probe(plate)
        assert (pi["w"], pi["h"], pi["frames"]) == (W, H, N) and abs(pi["fps"] - 30) < 1e-6 and pi["audio"], pi
        P = _decode_all(np, plate, W, H)
        S = _decode_all(np, clip, W, H)
        masks = list(iter_masks(np, cv2, rep, job["masks"], W, H, 0, N - 1))
        hards = [region_hard(np, cv2, m, 12, "rect")[0] for m in masks]
        for j in (0, 60, N - 1):
            core = cv2.erode(hards[j], np.ones((5, 5), np.uint8)) > 0
            assert float(np.median(P[j][core])) <= 3 and float(np.percentile(P[j][core], 99)) <= 24, j
        stub = open(os.path.join(rep, "REPAIR-st.prompt.md"), encoding="utf-8").read()
        for need in ("mode: video_edit", "video_references", "[KEEP]", "first frame", "outside the black area",
                     "timing", "camera", "light", "sound", "[CHANGE]", "Rebuild only the black area",
                     "no blotch", "moves on its own"):
            assert need in stub, need
        assert "watermark" not in stub.lower()
        done.append("plate: same size, rate, 150 frames and sound, region pure black; the prompt stub's blocks")
        # 2b. a lost frame is refused without --allow-lost
        bad = dict(region)
        bad["frames"] = [dict(fr) for fr in region["frames"]]
        bad["frames"][70].update(box=None, lost=True)
        bad["lost"] = [70]
        badp = os.path.join(rep, "REGION-lost.json")
        write_json(badp, bad)
        rc, out = _run(["mask", "--region", badp, "--contains", "a small grey instrument plate"])
        assert rc == 1 and "lost" in out, (rc, out)
        os.remove(badp)
        done.append("mask refuses a lost frame without --allow-lost")
        # 3. the model's clip, faked: the region rebuilt clean, the rest drifted +7 levels
        clean = [render(i, defect=False) for i in range(N)]

        def fake(one_sided=False):
            fr_ = []
            for i in range(N):
                hd, bb = region_hard(np, cv2, masks[i], 12, "rect")
                x = clean[i].astype(np.float32)
                x[hd == 0] += 7.0
                if one_sided:
                    strip = np.zeros_like(hd)
                    strip[:, bb[0]:bb[0] + 18] = 255
                    sel = (hd > 0) & (strip > 0)
                    x[sel] = x[sel] * 0.85 + 30.0
                fr_.append(np.clip(np.round(x), 0, 255).astype(np.uint8))
            return fr_
        good = fake()
        goodp = os.path.join(td, "good_repaired.mp4")
        _enc(np, goodp, [cv2.resize(f, (960, 540), interpolation=cv2.INTER_CUBIC) for f in good], 960, 540, crf=14)
        onep = os.path.join(td, "onesided_repaired.mp4")
        _enc(np, onep, fake(one_sided=True), W, H, crf=14)
        shortp = os.path.join(td, "short_repaired.mp4")
        _enc(np, shortp, good[:140], W, H, crf=14)
        jp = os.path.join(rep, "REPAIR-st.json")
        # 4. composite = a PREVIEW (2026-11-05): a name that does not say so is refused
        bad_out = os.path.join(rep, "COMP-good.mov")
        rc, out = _run(["composite", goodp, "--job", jp, "--out", bad_out])
        assert rc == 1 and PREVIEW_PREFIX in out and "Fusion comp" in out and not os.path.exists(bad_out), (rc, out)
        done.append("composite refuses an --out not named PREVIEW-… (a preview; the blend is a Fusion comp)")
        compk = os.path.join(rep, "PREVIEW-good.mkv")
        rc, out = _run(["composite", goodp, "--job", jp, "--out", compk])
        assert rc == 0, out
        assert load_json(compk + ".repair.json")["preview"] is True
        C = _decode_all(np, compk, W, H)
        assert C.shape[0] == N and probe(compk)["audio"], C.shape
        outside = np.stack([h == 0 for h in hards])
        d = np.abs(C.astype(np.int16) - S.astype(np.int16))
        assert int(d[outside].max()) == 0, int(d[outside].max())
        cl = np.stack(clean)
        cen = np.zeros((N, H, W), bool)
        for i in range(N):
            x, y, w, h = gt(i)
            cv2.circle(cen[i].view(np.uint8), (int(round(x + w / 2)), int(round(y + h / 2))), 9, 1, -1)
        fixed = float(np.abs(C.astype(np.int16) - cl.astype(np.int16))[cen].mean())
        before = float(np.abs(S.astype(np.int16) - cl.astype(np.int16))[cen].mean())
        assert fixed < 8 and before > 40, (fixed, before)
        done.append(f"preview (FFV1): every pixel outside the mask equals the source (max |Δ| 0) on all {N} "
                    f"frames; the defect is gone (|Δ| to the clean render {before:.0f} → {fixed:.1f})")
        compm = os.path.join(rep, "PREVIEW-st.mov")
        rc, out = _run(["composite", goodp, "--job", rep])           # the default name; --job as the folder
        assert rc == 0 and os.path.isfile(compm), out
        Cm = _decode_all(np, compm, W, H)
        dm = np.abs(Cm.astype(np.int16) - S.astype(np.int16))[outside]
        p999 = float(np.percentile(dm, 99.9))
        assert p999 <= 2 and float(dm.mean()) <= 0.5 and int(dm.max()) <= 4, (p999, float(dm.mean()), int(dm.max()))
        done.append(f"preview (ProRes 4444, the default PREVIEW-st.mov): outside the mask within {p999:.0f} levels "
                    f"(p99.9), max {int(dm.max())}, mean {float(dm.mean()):.2f}")
        rc, out = _run(["composite", shortp, "--job", jp, "--out", os.path.join(rep, "PREVIEW-short.mkv")])
        assert rc == 1 and "frames" in out, (rc, out)
        done.append("composite refuses 140 frames against a 150-frame plate without --retime")
        # 5. qa on the previews: the good one passes; the one-sided seam and the still-black region fail
        rc, out = _run(["qa", "--composite", compk, "--repaired", goodp, "--job", jp])
        qa = load_json(os.path.join(rep, "QA-st.json"))
        assert rc == 0 and qa["verdict"] in ("PASS", "WARN") and qa["mode"] == "preview", out
        assert qa["checks"]["drift"]["composite"]["max"] == 0, qa["checks"]["drift"]
        assert qa["checks"]["drift"]["raw"]["status"] == "WARN", qa["checks"]["drift"]   # the +7 the model added
        assert qa["checks"]["coverage"]["status"] == "PASS", qa["checks"]["coverage"]
        assert os.path.isfile(os.path.join(rep, "QA-st.png"))
        done.append("qa passes the good preview (drift 0; the model's +7 outside drift reported; coverage on "
                    f"{qa['checks']['coverage']['judged']} frames)")
        comp1 = os.path.join(rep, "PREVIEW-one.mkv")
        rc, out = _run(["composite", onep, "--job", jp, "--out", comp1])
        assert rc == 0, out
        rc, out = _run(["qa", "--composite", comp1, "--repaired", onep, "--job", jp])
        qa = load_json(os.path.join(rep, "QA-st.json"))
        sides = qa["checks"]["seam"]["sides"]
        assert rc == 1 and sides["left"]["status"] == "FAIL", (rc, sides)
        assert all(sides[k_]["status"] != "FAIL" for k_ in ("right", "top", "bottom")), sides
        assert qa["checks"]["drift"]["status"] == "PASS", qa["checks"]["drift"]
        done.append(f"qa FAILs the one-sided black level on the left edge only (left {sides['left']['median']['Y']:+.1f}, "
                    f"right {sides['right']['median']['Y']:+.1f} levels luma)")
        compb = os.path.join(rep, "PREVIEW-black.mkv")
        rc, out = _run(["composite", plate, "--job", jp, "--out", compb])
        assert rc == 0, out
        rc, out = _run(["qa", "--composite", compb, "--repaired", plate, "--job", jp])
        qa = load_json(os.path.join(rep, "QA-st.json"))
        assert rc == 1 and any(f_["check"] == "black" and "still black" in f_["why"] for f_ in qa["fails"]), out
        done.append("qa FAILs a region that came back still black")
        # 5b. fusion: the matte (grown, feathered, numbered from 0), the track, the recipe with real paths
        rc, out = _run(["fusion", "--job", jp, "--repaired", goodp])
        assert rc == 0, out
        fd = os.path.join(rep, "FUSION-st")
        md = os.path.join(fd, "matte")
        fz = load_json(os.path.join(fd, "fusion.json"))
        mfiles = sorted(os.listdir(md))
        assert mfiles[0] == "000000.png" and mfiles[-1] == f"{N - 1:06d}.png" and len(mfiles) == N, mfiles[:3]
        assert fz["global_offset"] == 0 and fz["matte"]["feather"] == FUSION_FEATHER and fz["matte"]["count"] == N

        def want_matte(m_):
            hd, bb = region_hard(np, cv2, m_, 12, "rect")
            al, (x0, y0, x1, y1) = inner_alpha(np, cv2, hd, bb, FUSION_FEATHER)
            ex = np.zeros((H, W), np.uint8)
            ex[y0:y1, x0:x1] = np.clip(np.round(al * 255.0), 0, 255).astype(np.uint8)
            return ex
        for j in (0, 60, N - 1):
            mt = cv2.imread(os.path.join(md, f"{j:06d}.png"), cv2.IMREAD_UNCHANGED)
            assert mt is not None and mt.shape == (H, W, 4) and mt.dtype == np.uint8, None if mt is None else mt.shape
            ex = want_matte(masks[j])
            assert all(np.array_equal(mt[..., c_], ex) for c_ in range(4)), j          # R = G = B = alpha
            assert int((ex > 0).sum()) > int((masks[j] > 0).sum()), j                    # grown past the box
            assert int(((ex > 0) & (ex < 255)).sum()) > 0 and int((ex == 255).sum()) > 0, j   # feathered
        tl = open(os.path.join(fd, "track.csv"), encoding="utf-8").read().splitlines()
        assert tl[0].split(",") == list(TRACK_COLS) and len(tl) == N + 1, tl[:2]
        row = dict(zip(TRACK_COLS, tl[61].split(",")))
        x, y, w, h = gt(60)
        assert row["source_frame"] == "60" and row["lost"] == "0", row
        assert abs(float(row["x"]) - (x + w / 2) / W) < 4.0 / W and abs(float(row["y"]) - (1 - (y + h / 2) / H)) < 4.0 / H, \
            (row, (x + w / 2) / W, 1 - (y + h / 2) / H)
        recipe = open(os.path.join(fd, "RECIPE.md"), encoding="utf-8").read()
        for need in (os.path.abspath(clip), os.path.abspath(goodp), os.path.join(md, "000000.png"), "MediaIn1",
                     "Loader1", "Loader2", "Bitmap1", "Channel to Luminance", "Merge1", "Effect Mask", "MediaOut1",
                     "Global In to 0", "Resize1", f"Width {W}, Height {H}", "Comp frame 0", f"comp frame {N - 1}",
                     "computer control", "scripting API", "empty MediaIns", "qa --render", os.path.abspath(jp),
                     "Transform"):
            assert need in recipe, need
        done.append(f"fusion: matte/000000–{N - 1:06d}.png = the blend's own alpha (grown 12 px, feathered "
                    f"{FUSION_FEATHER:g} px, R=G=B=A), track.csv in Fusion coordinates, RECIPE.md with the real paths")
        rep2 = os.path.join(td, "repair2")                     # a work range that starts after frame 0
        rc, out = _run(["track", clip, "--box", ",".join(f"{v:.2f}" for v in g), "--at", "2.0", "--frames", "70-100",
                        "--label", "sub", "--out", rep2])
        assert rc == 0, out
        rc, out = _run(["mask", "--region", os.path.join(rep2, "REGION-sub.json"), "--contains",
                        "a small grey instrument plate with a white bar and a blue bar, no blotch"])
        assert rc == 0, out
        job2 = load_json(os.path.join(rep2, "REPAIR-sub.json"))
        s2, e2 = job2["range"]["work"]
        assert s2 > 0, (s2, e2)
        subp = os.path.join(td, "sub_repaired.mp4")
        _enc(np, subp, good[s2:e2 + 1], W, H, crf=14)
        rc, out = _run(["fusion", "--job", rep2, "--label", "sub", "--repaired", subp])   # the folder + --label
        assert rc == 0, out
        fd2 = os.path.join(rep2, "FUSION-sub")
        fz2 = load_json(os.path.join(fd2, "fusion.json"))
        mf2 = sorted(os.listdir(os.path.join(fd2, "matte")))
        assert mf2[0] == "000000.png" and len(mf2) == e2 - s2 + 1 and fz2["global_offset"] == s2, (mf2[:2], fz2["work"])
        m2 = next(iter_masks(np, cv2, rep2, job2["masks"], W, H, s2, s2))
        mt = cv2.imread(os.path.join(fd2, "matte", "000000.png"), cv2.IMREAD_UNCHANGED)
        assert np.array_equal(mt[..., 0], want_matte(m2)), "matte frame 0 is not source frame s"
        tl2 = open(os.path.join(fd2, "track.csv"), encoding="utf-8").read().splitlines()
        assert tl2[1].split(",")[:2] == ["0", str(s2)], tl2[1]
        r2 = open(os.path.join(fd2, "RECIPE.md"), encoding="utf-8").read()
        assert f"Global In to {s2}" in r2 and f"Matte frame 0 is source frame {s2}" in r2 and "Resize1" not in r2
        assert f"Comp frame {s2}" in r2 and f"comp frame {e2}" in r2, "the recipe's checks name the work range"
        done.append(f"fusion on a work range {s2}–{e2}: matte/000000.png is source frame {s2} (Global In {s2}, no "
                    f"trim), the --job folder + --label resolve the job")
        # 5c. qa --render: Resolve's render, measured without the composite's sidecar
        rend = os.path.join(rep, "RENDER-st.mov")
        shutil.copyfile(compm, rend)                            # the good preview under another name, no sidecar
        assert not os.path.exists(rend + ".repair.json")
        rc, out = _run(["qa", "--render", rend, "--repaired", goodp, "--job", jp])
        qa = load_json(os.path.join(rep, "QA-st.json"))
        assert rc == 0 and qa["verdict"] in ("PASS", "WARN") and qa["mode"] == "render", out
        assert qa["measured"]["fusion"] and qa["measured"]["tolerance_of"] == "prores", qa["measured"]
        assert qa["checks"]["drift"]["status"] == "PASS" and qa["checks"]["coverage"]["status"] == "PASS", out
        assert not any(w_["check"] == "identity" for w_ in qa["warns"] + qa["fails"]), out
        done.append(f"qa --render passes a 'Resolve render' (the good preview copied, no sidecar): identity from the "
                    f"job and fusion.json, ProRes tolerance from the probed codec, coverage on "
                    f"{qa['checks']['coverage']['judged']} frames")
        Dr = C.copy()
        for i in range(N):
            x0, y0, x1, y1 = _crop(region_hard(np, cv2, masks[i], 12, "rect")[1], 40, W, H)
            sel = np.ones((H, W), bool)
            sel[y0:y1, x0:x1] = False
            Dr[i][sel] = np.clip(Dr[i][sel].astype(np.int16) + 5, 0, 255).astype(np.uint8)
        driftp = os.path.join(rep, "RENDER-drift.mp4")
        _enc(np, driftp, Dr, W, H, audio=True, crf=12)
        rc, out = _run(["qa", "--render", driftp, "--repaired", goodp, "--job", jp])
        qa = load_json(os.path.join(rep, "QA-st.json"))
        dws = [w_ for w_ in qa["warns"] if w_["check"] == "drift"]
        assert rc == 0 and qa["checks"]["drift"]["status"] == "WARN" and dws and DRIFT_NOTE in dws[0]["why"], out
        assert not any(f_["check"] == "drift" for f_ in qa["fails"]) and qa["measured"]["tolerance_of"] == "h264", out
        assert "⚠ DRIFT" in out and qa["drift_reported"] is True, out
        assert qa["verdict"] == ("WARN" if len(qa["warns"]) > len(dws) else "PASS"), qa["verdict"]   # drift aside
        done.append(f"qa --render: a render drifted +5 levels outside the region → a drift WARN (mean "
                    f"{qa['checks']['drift']['render']['mean']:.1f}), exit 0 — reported, not blocking (provisional)")
        rc, out = _run(["qa", "--render", clip, "--repaired", goodp, "--job", jp])   # the matte blocked everything
        qa = load_json(os.path.join(rep, "QA-st.json"))
        assert rc == 1 and any(f_["check"] == "coverage" and "missing" in f_["why"] for f_ in qa["fails"]), out
        Lt = [C[0]]
        for i in range(1, N):
            hd, bb = region_hard(np, cv2, masks[i], 12, "rect")
            al, (x0, y0, x1, y1) = inner_alpha(np, cv2, hd, bb, FUSION_FEATHER)
            o_ = S[i].astype(np.float32)
            o_[y0:y1, x0:x1] += (C[i - 1][y0:y1, x0:x1].astype(np.float32) - o_[y0:y1, x0:x1]) * al[..., None]
            Lt.append(np.clip(np.round(o_), 0, 255).astype(np.uint8))
        latep = os.path.join(rep, "RENDER-late.mp4")
        _enc(np, latep, Lt, W, H, audio=True, crf=12)
        rc, out = _run(["qa", "--render", latep, "--repaired", goodp, "--job", jp])
        qa = load_json(os.path.join(rep, "QA-st.json"))
        assert rc == 1 and any(f_["check"] == "coverage" and "one frame late" in f_["why"] for f_ in qa["fails"]), out
        done.append("qa --render FAILs coverage on a render that is the plain source (the repair missing), and on "
                    "one whose repaired clip runs a frame late (a Global In off by one)")
        # 6. SAM 2
        builder, _torch, why = sam2_import()
        if builder is None:
            rc, out = _run(["track", clip, "--engine", "sam2", "--box", ",".join(f"{v:.2f}" for v in g), "--at", "2.0",
                            "--label", "sam", "--out", rep])
            assert rc == 2 and "pip install -e" in out, (rc, out)
            sam_note = ("⛔ SAM 2 is NOT installed here, so the SAM 2 path was NOT exercised: `--engine sam2` exits 2 "
                        "with the install steps, and its glue (frame extraction, the prompt, both propagation "
                        "directions, the masks) ran against a stand-in predictor")
        else:
            sam_note = ("⛔ SAM 2 is importable, but the selftest does NOT run it (it needs a checkpoint); its glue ran "
                        "against a stand-in predictor")
        info = probe(clip)
        rngs = plan_range(N, 30.0, (50, 80), 12)
        s_, e_ = rngs["work"]
        fake_pred = _FakePredictor(np, W, H, gt, s_)
        recs, _x, mrec = track_sam2(np, cv2, clip, info, s_, e_, 60, g, None, "-", "-", rep, "sam", "png",
                                    builder=lambda cfg, ck, device="cpu": fake_pred, torch_mod=None)
        assert (e_ - s_ + 1) >= 120 and len(recs) == e_ - s_ + 1 and not any(r["lost"] for r in recs), (s_, e_)
        assert fake_pred.calls and fake_pred.calls[0][1] == 60 - s_
        mi = [_iou(r["box"], gt(r["f"])) for r in recs]
        assert min(mi) >= 0.9, min(mi)
        done.append(f"SAM 2 glue on --frames 50-80: work range {s_}–{e_} ({(e_ - s_ + 1) / 30:.0f} s), masks IoU ≥ "
                    f"{min(mi):.2f} (stand-in)")
    el = time.time() - t0
    print(f"selftest OK ({el:.1f} s) — END TO END on a synthetic 5 s clip (textured scene, camera pan, a moving plate "
          f"with a defect):")
    for d_ in done:
        print(f"  · {d_}")
    print(f"  · {sam_note}")
    return 0


# ---- the command line ---------------------------------------------------------------------------------------
def build_parser():
    R = argparse.RawDescriptionHelpFormatter
    ap = argparse.ArgumentParser(prog="region_repair.py", description=__doc__, formatter_class=R)
    ap.add_argument("--selftest", action="store_true", help="build a synthetic clip and run every step on it")
    sub = ap.add_subparsers(dest="cmd", metavar="{track,mask,composite,fusion,qa}")
    t = sub.add_parser("track", formatter_class=R, help="follow the region through the clip",
                       description="Follow ONE region through the clip, forwards and backwards from --at. Writes "
                                   "REGION-<label>.json, the masks and CHECK-<label>.png. Exit 1 when any frame is "
                                   "lost (no box is invented for it).")
    t.add_argument("clip")
    t.add_argument("--box", help="x,y,w,h on the --at frame: pixels, or each value with %% of the frame")
    t.add_argument("--at", type=float, default=0.0, help="seconds: the frame the box is drawn on (default 0)")
    t.add_argument("--engine", choices=["box", "sam2"], default="box",
                   help="box (default, OpenCV main module) or sam2 (facebookresearch sam2, only if installed)")
    t.add_argument("--point", help="sam2: x,y on the --at frame, inside the region (pixels or %%)")
    t.add_argument("--sam2-checkpoint", help="sam2: the checkpoint file (never downloaded here)")
    t.add_argument("--sam2-config", help="sam2: the model config, e.g. configs/sam2.1/sam2.1_hiera_l.yaml")
    t.add_argument("--frames", help="A-B: the source frames the cut uses; work = these plus --handles, ≥ 4 s, whole "
                                    "seconds")
    t.add_argument("--handles", type=int, default=HANDLES, help=f"frames each side of --frames (default {HANDLES})")
    t.add_argument("--masks", choices=["png", "mkv"], default="png",
                   help="png: a folder of PNG masks (default); mkv: one FFV1 grey video")
    t.add_argument("--smooth", type=int, default=1, help="box engine: [1,2,1] smoothing passes in time (0 = off)")
    t.add_argument("--label", help="the name in the output files (default: the clip's name)")
    t.add_argument("--out", help="output folder (default: repair/ beside the clip)")
    t.add_argument("--json", action="store_true", help="print the REGION record")
    m = sub.add_parser("mask", formatter_class=R, help="the black-masked plate, the job record, the prompt stub",
                       description="Make the plate the model edits: the work range of the source with the region "
                                   "(grown by --pad) filled pure black, same size, rate, frame count and sound. "
                                   "Writes MASKED-<label>.mp4, REPAIR-<label>.json and REPAIR-<label>.prompt.md (a "
                                   "stub to fill, lint and send through gate.py).")
    m.add_argument("--region", required=True, help="REGION-<label>.json from track")
    m.add_argument("--contains", required=True, help="what belongs in the region, in words")
    m.add_argument("--pad", type=int, default=12, help="grow the tracked region by this many px (default 12)")
    m.add_argument("--feather", type=float, default=0.0,
                   help="soften the black outward by this many px (default 0: a hard edge)")
    m.add_argument("--ref-image", action="append", help="an image of what belongs in the region (repeatable, up to 5); "
                                                        "a real, cleared photograph with a provenance sidecar")
    m.add_argument("--allow-lost", action="store_true", help="leave lost frames unmasked on purpose")
    m.add_argument("--json", action="store_true", help="print the REPAIR record")
    c = sub.add_parser("composite", formatter_class=R, help="a PREVIEW of the blend (never imported into Resolve)",
                       description="A PREVIEW of the blend: ONLY the masked region of the model's clip onto the source, "
                                   "every pixel outside the mask the source's. Its name must start with PREVIEW- "
                                   "(default PREVIEW-<label>.mov beside the job; any other name is refused). Never "
                                   "imported into Resolve as footage: the deliverable blend is the Fusion comp, built "
                                   "in Resolve by computer control (see fusion). .mov = ProRes "
                                   "4444, .mkv = FFV1 lossless, .mp4 = H.264 (lossy). Writes <out>.repair.json "
                                   "beside it.")
    c.add_argument("repaired", help="the clip the model returned")
    c.add_argument("--job", required=True, help="REPAIR-<label>.json from mask, or the folder that holds it")
    c.add_argument("--out", help="the preview: PREVIEW-<label>.mov (default, beside the job), or a PREVIEW-….mkv / "
                                 ".mp4")
    c.add_argument("--feather", type=float, default=FUSION_FEATHER,
                   help=f"the ramp inside the region's edge, px (default {FUSION_FEATHER:g})")
    c.add_argument("--retime", action="store_true",
                   help="accept a frame count that differs by more than one, mapping frames proportionally")
    c.add_argument("--audio", choices=["source", "repaired", "none"], default="source",
                   help="whose sound the preview carries (default: the source's)")
    c.add_argument("--json", action="store_true", help="print the composite record")
    z = sub.add_parser("fusion", formatter_class=R,
                       help="the matte, track and recipe for the Fusion comp (the deliverable blend)",
                       description="Write FUSION-<label>/ for the Fusion comp that makes the final blend in Resolve, "
                                   "built by computer control, never through the scripting API (the "
                                   "computer-control rule): matte/%06d.png (the matte exactly as the tool blends it — grown by the "
                                   "job's pad, feathered — 8-bit, full size, numbered from 0 at the work-range "
                                   "start), track.csv and track.json (the region per frame in Fusion's "
                                   "coordinates), RECIPE.md (the node-by-node build, the checks, the render and the "
                                   "qa command, with paths and frame numbers filled in) and fusion.json.")
    z.add_argument("--job", required=True, help="REPAIR-<label>.json from mask, or the folder that holds it")
    z.add_argument("--repaired", required=True, help="the clip the model returned")
    z.add_argument("--label", help="picks REPAIR-<label>.json when --job is a folder; names FUSION-<label>/ "
                                   "(default: the job's label)")
    z.add_argument("--feather", type=float, default=FUSION_FEATHER,
                   help=f"the matte's ramp inside the region's edge, px (default {FUSION_FEATHER:g}, as composite)")
    z.add_argument("--retime", action="store_true",
                   help="accept a frame count that differs by more than one: writes repaired-conformed.mov "
                        "(mapped proportionally, the source size) for the Loader")
    z.add_argument("--out", help="the folder FUSION-<label>/ goes in (default: beside the job)")
    z.add_argument("--json", action="store_true", help="print the FUSION record")
    q = sub.add_parser("qa", formatter_class=R, help="the gate on the result: exit 1 on any FAIL (drift only warns)",
                       description="Measure Resolve's render of the Fusion comp (--render) or the tool's preview "
                                   "(--composite) against the source and the model's clip: drift outside the mask "
                                   "(reported, not blocking for now), the seam per side and "
                                   "per channel, texture against the surround, a ±2-stop slam on the sheet, flicker, "
                                   "counts, a still-black region or black rim, and coverage (the repair is there, on "
                                   "the right frames). Writes QA-<label>.json and QA-<label>.png. Exit 1 on any FAIL.")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--render", help="Resolve's render of the Fusion comp: the whole source clip, the same size and "
                                    "frame rate (no sidecar needed)")
    g.add_argument("--composite", help="the tool's PREVIEW-… (reads its .repair.json)")
    q.add_argument("--repaired", required=True, help="the model's clip the comp (or composite) used")
    q.add_argument("--job", required=True, help="REPAIR-<label>.json, or the folder that holds it")
    q.add_argument("--fusion", help="--render: the FUSION-<label> folder or its fusion.json (default: beside the job)")
    q.add_argument("--feather", type=float,
                   help=f"--render without a FUSION record: the matte's feather, px (default {FUSION_FEATHER:g})")
    q.add_argument("--cut", help="A-B: source frames a (new) cut uses; FAIL if they run past the repaired span")
    q.add_argument("--out-dir", help="where QA-<label>.* go (default: beside the job)")
    q.add_argument("--json", action="store_true", help="print the QA record")
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help()
        return 2
    _JSON[0] = bool(getattr(a, "json", False))
    try:
        return {"track": cmd_track, "mask": cmd_mask, "composite": cmd_composite, "fusion": cmd_fusion,
                "qa": cmd_qa}[a.cmd](a)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    except Usage as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (OSError, subprocess.SubprocessError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    finally:
        _JSON[0] = False


if __name__ == "__main__":
    sys.exit(main())
