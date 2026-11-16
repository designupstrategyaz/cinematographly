#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
master_to_jobs.py — parse a simple MASTER-prompts file into a structured job list that Claude
feeds to the Higgsfield MCP (generate_image / generate_video) to BATCH-generate a whole video's
shots, instead of hand-driving the Cinema Studio UI shot by shot.

It does NOT call the MCP itself (MCP tools are Claude's to call). It turns your prompts into clean
jobs so Claude can loop them: for each job, resolve the @elements to element ids
(show_reference_elements action=list), embed <<<element_id>>> in the prompt (the backend injects the
character and rewrites to @name), and call generate_image/generate_video with the model + count.

MASTER format — one block per shot (blank line between blocks):

    [S1-C1] video host
    elements: @Host Business
    prompt: Cinematic documentary 9:16, the host at a village bench, warm golden hour,
    speaking to camera, natural mouth movement.

    [S2B] broll
    prompt: Low drone over a mountain village, morning light. No characters.

Header line = [<SHOT>] <kind: image|video|broll> [<subject>].  `elements:` lists @Element names
(optional). `prompt:` body may span multiple lines until the next blank line / block.

Usage:
  python3 master_to_jobs.py MASTER-image-prompts-all-scenes.md            # prints jobs JSON
  python3 master_to_jobs.py MASTER.md > jobs.json
"""
import json
import re
import sys

HDR = re.compile(r"^\s*\[([^\]]+)\]\s*(image|video|broll)\b\s*(.*)$", re.IGNORECASE)


def parse(text):
    jobs, cur = [], None
    field = None
    for raw in text.splitlines():
        m = HDR.match(raw)
        if m:
            if cur:
                jobs.append(cur)
            cur = {"shot": m.group(1).strip(), "kind": m.group(2).lower(),
                   "subject": (m.group(3).strip() or None), "elements": [], "prompt": ""}
            field = None
            continue
        if cur is None:
            continue
        if raw.strip() == "":
            field = None
            continue
        low = raw.strip().lower()
        if low.startswith("elements:"):
            cur["elements"] = [e.strip() for e in raw.split(":", 1)[1].split(",") if e.strip()]
            field = None
        elif low.startswith("prompt:"):
            cur["prompt"] = raw.split(":", 1)[1].strip()
            field = "prompt"
        elif field == "prompt":
            cur["prompt"] += " " + raw.strip()
    if cur:
        jobs.append(cur)
    for j in jobs:
        j["prompt"] = j["prompt"].strip()
    return jobs


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) >= 2 else 2)
    try:
        text = open(sys.argv[1], encoding="utf-8").read()
    except OSError as e:
        sys.exit(f"error: {e}")
    jobs = parse(text)
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
    n_v = sum(1 for j in jobs if j["kind"] in ("video", "broll"))
    print(f"\n// {len(jobs)} jobs ({n_v} video/broll, {len(jobs)-n_v} image). "
          f"Claude: resolve @elements → <<<id>>>, then generate_* per job.", file=sys.stderr)


if __name__ == "__main__":
    main()
