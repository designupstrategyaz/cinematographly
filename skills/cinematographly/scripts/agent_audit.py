#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""agent_audit.py — what did an agent's steps go on? (v2.70.0, Wave 5 A13)

Reads one Claude Code transcript (a session's or a subagent's .jsonl) and counts the agent's tool calls by kind:
reading reference files, reading images, searching, writing, running commands, other. It also measures the image data
the run carried in its context (base64 bytes in tool results) and lists the files read more than once.

Why: a practitioner reported that most of an ad-generation agent's steps went to re-opening reference files it could
have been handed up front (a public post, numbers not verified). Before giving an agent more files to read — Wave 5
gives the take reviewer the approved sheets — measure what it already spends its steps on, then measure again.

  agent_audit.py <transcript.jsonl> [--refs PATTERN] [--json]
      --refs  a regex for paths that count as reference material (default: sheets, references, _reference, 02-startframes,
              DEVELOPMENT, CHECKPOINT, .md under references/)
  agent_audit.py --selftest

It works on any Claude Code transcript; nothing in it is specific to this plugin. Read-only.
"""
from __future__ import annotations
import argparse, collections, json, os, re, sys, tempfile

DEFAULT_REFS = r"(sheet|_reference|/references/|02-startframes|DEVELOPMENT\.md|CHECKPOINT\.md|character|prop)"
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _kind(name: str, inp: dict, refs: re.Pattern) -> str:
    n = (name or "").lower()
    path = str((inp or {}).get("file_path") or (inp or {}).get("path") or "")
    if n in ("read",):
        if path.lower().endswith(IMG_EXT):
            return "read image"
        return "read reference" if refs.search(path) else "read other"
    if n in ("grep", "glob") or n.endswith("search"):
        return "search"
    if n in ("write", "edit", "notebookedit"):
        return "write"
    if n == "bash":
        return "command"
    return "other"


def audit(path: str, refs: str = DEFAULT_REFS) -> dict:
    rx = re.compile(refs, re.I)
    kinds, reads = collections.Counter(), collections.Counter()
    img_bytes = img_blocks = steps = 0
    for line in open(path, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        msg = ev.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                steps += 1
                k = _kind(b.get("name"), b.get("input") or {}, rx)
                kinds[k] += 1
                if k.startswith("read"):
                    reads[str((b.get("input") or {}).get("file_path") or "")] += 1
            elif b.get("type") == "tool_result":
                inner = b.get("content")
                for c in inner if isinstance(inner, list) else []:
                    if isinstance(c, dict) and c.get("type") == "image":
                        img_blocks += 1
                        img_bytes += len(str((c.get("source") or {}).get("data") or ""))
            elif b.get("type") == "image":
                img_blocks += 1
                img_bytes += len(str((b.get("source") or {}).get("data") or ""))
    rereads = {p: n for p, n in reads.items() if n > 1 and p}
    ref_steps = kinds["read reference"] + kinds["read image"]
    return {"transcript": path, "steps": steps, "by_kind": dict(kinds.most_common()),
            "reference_share": round(ref_steps / steps, 3) if steps else 0.0,
            "image_blocks": img_blocks, "image_base64_kb": round(img_bytes / 1024, 1),
            "read_more_than_once": dict(sorted(rereads.items(), key=lambda x: -x[1])[:10]),
            "hint": ("most steps re-open reference material: hand the agent a compact summary in its brief"
                     if steps and ref_steps / steps > 0.5 else "")}


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        tp = os.path.join(td, "t.jsonl")
        ev = []
        for _ in range(3):
            ev.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/job/_reference/Ana_sheet.md"}}]}})
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/job/09-qa/S1.sheet.png"}}]}})
        ev.append({"type": "user", "message": {"content": [{"type": "tool_result", "content": [
            {"type": "image", "source": {"data": "A" * 4096}}]}]}})
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Grep", "input": {"pattern": "x"}},
            {"type": "tool_use", "name": "Write", "input": {"file_path": "/job/out.md"}}]}})
        open(tp, "w").write("\n".join(json.dumps(e) for e in ev) + "\nnot json\n")
        r = audit(tp)
        assert r["steps"] == 6 and r["by_kind"]["read reference"] == 3 and r["by_kind"]["read image"] == 1, r
        assert r["by_kind"]["search"] == 1 and r["by_kind"]["write"] == 1, r
        assert r["image_blocks"] == 1 and r["image_base64_kb"] == 4.0, r
        assert r["read_more_than_once"] == {"/job/_reference/Ana_sheet.md": 3}, r
        assert r["reference_share"] == round(4 / 6, 3) and "compact summary" in r["hint"], r
        r2 = audit(tp, refs=r"nothing-matches")
        assert r2["by_kind"].get("read reference", 0) == 0 and r2["by_kind"]["read other"] == 3, r2
    print("selftest OK — tool calls counted by kind (reference reads, image reads, search, write), image data in "
          "context measured, re-read files listed, the reference pattern configurable, and a bad line skipped")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript", nargs="?")
    ap.add_argument("--refs", default=DEFAULT_REFS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.transcript:
        ap.print_help(); return 2
    r = audit(a.transcript, a.refs)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"{r['steps']} steps · reference/image reads {r['reference_share']:.0%} · images in context "
              f"{r['image_blocks']} ({r['image_base64_kb']} KB base64)")
        for k, v in r["by_kind"].items():
            print(f"  {k:16} {v}")
        for p, n in r["read_more_than_once"].items():
            print(f"  read {n}×  {p}")
        if r["hint"]:
            print("  → " + r["hint"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
