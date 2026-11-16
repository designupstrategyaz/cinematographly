#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""pull_metrics.py — ingest platform performance exports, join them to the videos we made.

WHY THIS EXISTS. `references/performance-metrics.md` designed the writeback in August and named the
tool that would do it; the tool did not exist, so **no performance data has ever entered this skill
from any platform.** "Which hooks have we used and how did each do" was unanswerable, which makes
the hook bank a list of guesses and the promotion floors in §3 decorative.

⛔ THE FINDING THAT SHAPED THIS FILE: **none of the four platforms has a fixed export schema.** The
header row is whatever columns the user happened to tick in the UI, no platform publishes a default
set or a header list, and headers are the UI display strings so they change with the account's
language [PRIMARY research pass 2026-09-08]. A positional parser is therefore guaranteed to be
wrong eventually and silently. So this is column-NAME driven, every unrecognised header is
QUARANTINED and reported, and `--map` extends the table at runtime without a code change.

⛔ AND THE ONE THAT SHAPES EVERY READING: **"views" is a different quantity on each platform, and
YouTube changed its definition twice in eighteen months** (Shorts 2025-03-31; all formats
2026-08-24). TikTok counts a view when playback *starts*; Meta's paid ladder has no "views" column
at all; Instagram's counts replays. **Summing or comparing views across platforms produces a number
that means nothing**, so `report` groups by platform and refuses to total them.

Usage
-----
  python3 pull_metrics.py ingest <export.csv> --platform meta|tiktok|youtube|googleads \\
        --root <production-root> [--map "Some Header=impressions"] [--dry-run] [--json]
  python3 pull_metrics.py report <production-root> [--client X] [--month YYYY-MM] [--json]
  python3 pull_metrics.py hooks  <production-root> [--client X]     # the promotion floors, applied

Join. Paid rows join on the ad name carrying the five-part key from `batch_plan.py`
(`<BRAND>-<body>-<hook>-<persona>-<variant>`). ⛔ Organic rows cannot: **no platform guarantees a
field we control in the export**, so the organic join is ours to make — `ledger.py publish` records
`(job, platform, post_id, permalink)` at upload time and this tool joins on that.

Exit codes: 0 ok · 1 nothing joined / a floor was not met · 2 usage or IO error.
"""
from __future__ import annotations
import argparse, csv, glob, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)

# Null tokens. ⛔ No platform documents its null placeholder; these are the ones observed in their
# UIs. Anything else non-numeric in a numeric column is REPORTED, never silently zeroed.
NULLS = {"", "-", "--", "—", "–", "n/a", "na", "null", "none"}

# ---------------------------------------------------------------------------------------------
# Column aliases. Every name here was read off the platform's own documentation on 2026-09-08.
# Lowercased and stripped of punctuation before matching, so "3-Second Video Plays",
# "3-second video plays" and "3 second video plays" all land on the same field.
# ⛔ These are NOT a schema. They are the names we have verified; an export will carry others.
# ---------------------------------------------------------------------------------------------
def norm(h: str) -> str:
    return re.sub(r"[^a-z0-9%]+", " ", (h or "").strip().lower()).strip()


ALIASES = {
    "meta": {
        "ad name": "ad_name", "ad id": "ad_id", "campaign name": "campaign",
        "impressions": "impressions", "reach": "reach", "amount spent": "spend",
        "amount spent usd": "spend", "amount spent eur": "spend", "amount spent gbp": "spend",
        "amount spent ron": "spend", "amount spent in usd": "spend", "frequency": "frequency",
        "video plays": "video_plays",
        "3 second video plays": "v3s",
        "2 second continuous video play": "v2s", "2 second continuous video plays": "v2s",
        "thruplays": "thruplays", "thruplay": "thruplays",
        "video plays at 25%": "p25", "video plays at 50%": "p50", "video plays at 75%": "p75",
        "video plays at 95%": "p95", "video plays at 100%": "p100",
        "video average play time": "avg_play_s",
        "link clicks": "link_clicks", "unique link clicks": "unique_link_clicks",
        "clicks all": "clicks", "ctr all": "ctr_all", "cpm cost per 1 000 impressions": "cpm",
        "results": "results",          # ⛔ objective-dependent — never aggregated, see WATERFALL
        "reporting starts": "date", "day": "date", "date": "date",
        "post id": "post_id", "permalink": "url", "post": "post_id",
    },
    "tiktok": {
        "ad name": "ad_name", "ad id": "ad_id", "campaign name": "campaign",
        "impressions": "impressions", "reach": "reach", "cost": "spend", "frequency": "frequency",
        "video views": "video_views",
        "2 second video views": "v2s", "6 second video views": "v6s",
        "video views at 25%": "p25", "video views at 50%": "p50",
        "video views at 75%": "p75", "video views at 100%": "p100",
        "average play time per video view": "avg_play_s",
        "average play time per user": "avg_play_user_s",
        "clicks destination": "link_clicks", "clicks all": "clicks",
        "conversions": "conversions", "conversion rate cvr": "cvr",
        "date": "date", "day": "date",
        "video link": "url", "post id": "post_id", "permalink": "url",
        "video title": "title", "video": "post_id",
    },
    "youtube": {
        "video": "post_id", "video title": "title", "duration": "duration",
        "views": "views", "watch time hours": "watch_hours",
        "average view duration": "avg_view_duration", "average percentage viewed %": "avg_pct",
        "impressions": "impressions", "impressions click through rate %": "ctr",
        "video publish time": "date", "date": "date",
    },
    "googleads": {
        "ad name": "ad_name", "campaign": "campaign", "impressions": "impressions",
        "cost": "spend", "clicks": "clicks", "ctr": "ctr",
        "trueview views": "views", "views": "views",
        "video played to 25%": "p25", "video played to 50%": "p50",
        "video played to 75%": "p75", "video played to 100%": "p100",
        "day": "date", "date": "date",
        "video id": "post_id", "permalink": "url",
    },
}

NUMERIC = {"impressions", "reach", "spend", "video_views", "frequency", "video_plays", "v2s", "v3s", "v6s",
           "thruplays", "p25", "p50", "p75", "p95", "p100", "avg_play_s", "avg_play_user_s",
           "link_clicks", "unique_link_clicks", "clicks", "ctr", "ctr_all", "cpm", "results",
           "conversions", "cvr", "views", "watch_hours", "avg_pct"}

AD_NAME_RE = re.compile(r"^([A-Za-z0-9_]+)-([A-Za-z0-9_]+)-([A-Za-z0-9_]+)-([A-Za-z0-9_]+)-([a-z]+)$")


def _ledger():
    spec = importlib.util.spec_from_file_location("cine_ledger", os.path.join(HERE, "ledger.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------------------------
def to_num(raw: str) -> tuple[float | None, str]:
    """Locale-safe. Returns (value, note). A note means DO NOT USE the value.

    ⛔ Three ways this was silently wrong before an adversarial read on 2026-09-08:
      1. The ambiguity heuristic existed only on the comma branch. `"1,234"` came back 1234 and
         `"1.234"` came back **1.234** — so a German export's 12.480 impressions became 12.48 and
         the CTR computed from it read 769%, graded "strong", with no note. The rule is now
         symmetric: a single separator with all-3-digit groups after it is a THOUSANDS separator,
         whichever character it is.
      2. Accounting negatives lost their sign — `"(1,234)"` → +1234 — so a refund landed as spend.
      3. `"<0.01"` was silently converted to an exact 0.01. A bound is not a measurement.
    """
    s = (raw or "").strip().replace("\u00a0", " ").replace("\u202f", " ")
    if s.lower() in NULLS:
        return None, ""
    if re.match(r"^\s*[<>≤≥]", s):
        return None, f"bounded value {raw!r} — a bound is not a measurement"
    neg = bool(re.fullmatch(r"\(\s*[^()]*\s*\)", s))          # accounting negative
    s = re.sub(r"[^\d,.\-+eE]", "", s)
    if not s or s in ("-", "+", ".", ","):
        return None, ""
    if "," in s and "." in s:
        dec = "," if s.rindex(",") > s.rindex(".") else "."      # the LAST separator is the decimal
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    else:
        for sep in (",", "."):
            if sep in s:
                parts = s.split(sep)
                # 1,234 / 1.234 are ambiguous. Groups of exactly 3 after the first separator, and
                # more than one separator OR a short head, read as thousands. Otherwise decimal.
                grouped = all(len(p) == 3 for p in parts[1:]) and len(parts[0].lstrip("+-")) <= 3
                s = s.replace(sep, "") if grouped else s.replace(sep, ".")
                break
    try:
        v = float(s)
    except ValueError:
        return None, f"unparseable number {raw!r}"
    return (-v if neg else v), ""


def hms_to_seconds(raw: str) -> float | None:
    """YouTube Studio ships `Average view duration` as H:M:S, not seconds."""
    s = (raw or "").strip()
    if not s or s.lower() in NULLS:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    if not re.fullmatch(r"(\d+:)?\d{1,2}:\d{2}(\.\d+)?", s):
        return None
    bits = [float(x) for x in s.split(":")]
    while len(bits) < 3:
        bits.insert(0, 0.0)
    return bits[0] * 3600 + bits[1] * 60 + bits[2]


def read_table(path: str, amap: dict | None = None) -> tuple[list[str], list[list[str]]]:
    """CSV/TSV. XLSX is refused with the reason rather than half-parsed."""
    if path.lower().endswith((".xlsx", ".xls")):
        raise ValueError("this is a spreadsheet, not a text export — re-export as CSV, or convert "
                         "it first. (XLSX is actually the SAFER download from Meta and Google Ads "
                         "because numbers arrive typed and the decimal-separator problem "
                         "disappears; this tool just does not carry an xlsx reader.)")
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        first = fh.readline()
        if first.startswith("sep="):
            # ⛔ this used to seek a hardcoded len("sep=,\n"), which lands short on a BOM or a CRLF
            # and injects a phantom row. tell() after readline() is the only correct offset.
            pos = fh.tell()
        else:
            pos = 0
        fh.seek(pos)
        head = fh.read(8192)
        fh.seek(pos)
        try:
            dialect = csv.Sniffer().sniff(head, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = [r for r in csv.reader(fh, dialect)]
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        return [], []
    # ⛔ Pick the header by how many cells the platform's alias table RECOGNISES, not by "first row
    # that looks non-numeric". A two-cell title row like `Ad performance,Sep 2026` passed the old
    # test, so the real header became row 1 of the body and every column was quarantined.
    amap = amap or {}
    best, best_score = 0, -1
    for i, r in enumerate(rows[:6]):
        cells = [c for c in r if (c or "").strip()]
        if len(cells) < 2:
            continue
        known = sum(1 for c in r if amap.get(norm(c)))
        numericish = sum(1 for c in cells if to_num(c)[0] is not None)
        score = known * 10 + len(set(cells)) - numericish * 3
        if score > best_score:
            best, best_score = i, score
    return rows[best], rows[best + 1:]


def parse(path: str, platform: str, extra: dict) -> dict:
    amap = dict(ALIASES.get(platform, {}))
    amap.update({norm(k): v for k, v in extra.items()})
    header, body = read_table(path, amap)
    cols, quarantined = {}, []
    for i, h in enumerate(header):
        f = amap.get(norm(h))
        if f:
            cols.setdefault(f, i)
        elif (h or "").strip():
            quarantined.append(h.strip())
    rows, unkeyed, notes, totals = [], [], [], 0
    parsed_body = []
    for r in body:
        rec = {}
        for f, i in cols.items():
            raw = r[i] if i < len(r) else ""
            if f == "avg_view_duration":
                rec[f] = hms_to_seconds(raw)
            elif f in NUMERIC:
                v, note = to_num(raw)
                rec[f] = v
                if note:
                    notes.append(note)
            else:
                rec[f] = (raw or "").strip()
        parsed_body.append(rec)
    for idx, rec in enumerate(parsed_body):
        key = (rec.get("ad_name") or rec.get("post_id") or rec.get("url")
               or rec.get("title") or "").strip()
        if re.fullmatch(r"(?i)\s*(total|totals|grand total|summary)\s*", key):
            totals += 1
            continue
        if not key:
            # ⛔ An empty key used to be counted as a totals row and DISCARDED. A Meta export with
            # boosted-post rows (no ad name) then reported "joined 2 of 2 · exit 0" while throwing
            # away real rows carrying real spend. A row is only a totals row when it is the LAST
            # one and its metrics equal the column sums; everything else is unattributed.
            is_last = idx == len(parsed_body) - 1
            sums_match = False
            if is_last:
                add = [f for f in ("impressions", "spend", "clicks", "link_clicks") if f in cols]
                if add:
                    sums_match = all(
                        isinstance(rec.get(f), (int, float))
                        and abs(rec[f] - sum(x.get(f) or 0 for x in parsed_body[:-1])) < 0.51
                        for f in add)
            if is_last and sums_match:
                totals += 1
            else:
                unkeyed.append(rec)
            continue
        rec["_key"] = key
        rows.append(rec)
    return {"platform": platform, "file": os.path.abspath(path), "header": header,
            "recognised": sorted(cols), "quarantined": quarantined, "rows": rows,
            "unkeyed": unkeyed, "rows_in_file": len(parsed_body),
            "totals_rows_dropped": totals, "notes": notes}


ADDITIVE = {"impressions", "spend", "video_plays", "v2s", "v3s", "v6s", "thruplays",
            "p25", "p50", "p75", "p95", "p100", "link_clicks", "unique_link_clicks", "clicks",
            "results", "conversions", "views", "watch_hours", "video_views"}
NOT_ADDITIVE = {"reach", "frequency", "ctr", "ctr_all", "cpm", "cvr", "avg_play_s",
                "avg_play_user_s", "avg_view_duration", "avg_pct"}


def collapse(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """One row per join key. ⛔ Any export with a breakdown (Day, Placement, Age) has N rows per ad,
    and the alias table maps `Day`/`Date` — so day-broken exports are EXPECTED input. The first
    version overwrote field-by-field and kept only the last row: a routine 3-day Meta export of one
    ad recorded 204.44 of 612.44 spend and printed 'joined 3 of 3'. Additive fields are summed;
    non-additive ones (reach, frequency, any rate or average) are dropped with a note, because
    summing them is meaningless and averaging them without weights is worse.
    """
    out: dict = {}
    notes: list[str] = []
    for r in rows:
        k = r["_key"].lower()
        cur = out.setdefault(k, {"_key": r["_key"], "_rows": 0})
        cur["_rows"] += 1
        for f, v in r.items():
            if f.startswith("_"):
                continue
            if f in ADDITIVE and isinstance(v, (int, float)):
                cur[f] = (cur.get(f) or 0) + v
            elif f in NOT_ADDITIVE:
                cur.setdefault(f, v)
                cur[f + "_multi"] = cur.get(f + "_multi", 0) + 1
            else:
                cur.setdefault(f, v)
    for k, cur in out.items():
        if cur["_rows"] > 1:
            for f in list(cur):
                if f.endswith("_multi") and cur[f] > 1:
                    base = f[:-6]
                    cur.pop(base, None)
                    notes.append(f"{cur['_key']}: {base!r} dropped — {cur['_rows']} rows for one key "
                                 f"and it is not additive")
                cur.pop(f, None) if f.endswith("_multi") else None
    return list(out.values()), notes


# ---------------------------------------------------------------------------------------------
# The waterfall. ⛔ Computed with each platform's OWN fields, and the benchmarks are Meta-shaped
# because that is where they came from — applying Meta's 3-second hook-rate band to TikTok's
# 2-second metric would be comparing two different measurements against one threshold.
# ---------------------------------------------------------------------------------------------
# ⛔ CTR: performance-metrics.md §1 gives weak as "<0.5–1%". Taking 0.005 resolved a documented
# RANGE to its most permissive edge, so a 0.8% CTR was graded "mid" and the offer stage was never
# indicted. Take the conservative edge — a range's weak end is the one that costs you nothing to
# act on.
BENCH = {"hook_rate": (0.25, 0.35), "hold_rate": (0.40, 0.60), "ctr": (0.01, 0.015)}


def waterfall(platform: str, m: dict) -> dict:
    faults: list[str] = []

    def div(a, b):
        # ⛔ bounded. An unbounded ratio let a cross-file field mix (v3s from one export over
        # impressions from another) print hook_rate 700% and grade it "strong".
        na, nb = m.get(a), m.get(b)
        if not (isinstance(na, (int, float)) and isinstance(nb, (int, float)) and nb):
            return None
        v = na / nb
        if v < 0 or v > 1.0000001:
            faults.append(f"{a}÷{b} = {v:.2f} — outside 0..1, so these two numbers do not belong to "
                          f"the same population (mixed exports, or a mixed ad format)")
            return None
        return v

    out: dict = {"platform": platform, "benchmarked": platform == "meta"}
    if platform == "meta":
        out["hook_rate"] = div("v3s", "impressions")
        out["hook_basis"] = "3-second video plays ÷ impressions"
        out["hold_rate"] = div("thruplays", "v3s")
        out["hold_basis"] = "ThruPlays ÷ 3-second plays"
        out["ctr"] = div("link_clicks", "impressions")
        # ⛔ Meta's quartiles "include plays that skipped to this point", so they are NOT a
        # monotonic funnel and a cliff between them is not necessarily a drop-off.
        out["quartiles_include_skips"] = True
    elif platform == "tiktok":
        out["hook_rate"] = div("v2s", "impressions")
        out["hook_basis"] = "2-second video views ÷ impressions (⚠ 2s, not Meta's 3s)"
        out["hold_rate"] = div("p100", "v2s")
        out["hold_basis"] = "views at 100% ÷ 2-second views (TikTok has no ThruPlay)"
        out["ctr"] = div("link_clicks", "impressions")
        out["quartiles_include_skips"] = False
    elif platform == "youtube":
        out["hook_rate"] = None
        out["hook_basis"] = "not computable — YouTube Studio exposes no sub-3-second metric"
        out["hold_rate"] = (m.get("avg_pct") / 100.0) if isinstance(m.get("avg_pct"), (int, float)) else None
        out["hold_basis"] = "average percentage viewed"
        out["ctr"] = (m.get("ctr") / 100.0) if isinstance(m.get("ctr"), (int, float)) else None
        out["ctr_basis"] = "thumbnail impressions CTR — a DIFFERENT event from a link click"
    elif platform == "googleads":
        out["hook_rate"] = None
        out["hook_basis"] = "not computable — TrueView views are a 10s/30s threshold, not a hook read"
        out["hold_rate"] = div("p100", "views")
        out["hold_basis"] = "played to 100% ÷ TrueView views"
        out["ctr"] = div("clicks", "impressions")
    verdicts = {}
    for k in ("hook_rate", "hold_rate", "ctr"):
        v = out.get(k)
        if v is None:
            verdicts[k] = "n/a"
            continue
        if not out["benchmarked"]:
            verdicts[k] = "UNBENCHMARKED"
            continue
        lo, hi = BENCH[k]
        verdicts[k] = "weak" if v < lo else ("strong" if v >= hi else "mid")
    out["verdict"] = verdicts
    out["faults"] = faults
    # fix the EARLIEST weak stage first — a better body under a dead hook is unmeasurable
    order = [("hook_rate", "the hook ONLY — first frame, first line"),
             ("hold_rate", "pacing, proof, the middle — the hook is doing its job"),
             ("ctr", "CTA framing, offer, end card — they watched and did not act")]
    out["change_next"] = next((why for k, why in order if verdicts.get(k) == "weak"), None)
    return out


IMPRESSION_FLOOR = 1000   # [SECONDARY · practitioner range 'a few hundred to ~1,000', converging
                          # but never verified — performance-metrics.md §3. Convergence ≠ evidence.]


def ingest(a) -> int:
    led = _ledger()
    extra = {}
    for pair in (a.map or []):
        if "=" not in pair:
            print(f"error: --map wants 'Header=field', got {pair!r}", file=sys.stderr)
            return 2
        k, v = pair.split("=", 1)
        extra[k.strip()] = v.strip()
    try:
        parsed = parse(a.file, a.platform, extra)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    grouped, collapse_notes = collapse(parsed["rows"])
    recs, _ = led.index(a.root, write=False)
    by_ad, dupes = {}, []
    by_post = {}
    for r in recs:
        an = (r.get("identity") or {}).get("ad_name")
        if an:
            k = an.strip().lower()
            if k in by_ad:
                dupes.append((k, by_ad[k].get("job"), r.get("job")))
            by_ad[k] = r
        for e in r.get("events") or []:
            if e.get("kind") == "publish":
                for k2 in (e.get("post_id"), e.get("url")):
                    if k2:
                        by_post[str(k2).strip().lower()] = r
    if dupes:
        # ⛔ two videos with the same ad name silently clobbered each other in this dict, and the
        # row landed on whichever sorted last. The join key is a PRIMARY key; a collision is a
        # planning error and the tool must not guess which video the numbers belong to.
        print("⛔ REFUSED: two or more videos share an ad-name join key, so a metrics row cannot be "
              "attributed:", file=sys.stderr)
        for k, j1, j2 in dupes:
            print(f"     {k}  →  {j1}  and  {j2}", file=sys.stderr)
        print("   Give each a distinct variant suffix (`ledger.py set --ad-name …-b`). "
              "performance-metrics.md §2: never rename a live ad — allocate a new variant.",
              file=sys.stderr)
        return 2

    joined, unattributed, near = [], [], []
    for row in grouped:
        key = row["_key"]
        rec = by_ad.get(key.lower()) or by_post.get(key.lower())
        if rec is None:
            # ⛔ A near match is a CANDIDATE, never a join. Splitting the ad name and matching the
            # five-part key inside any token collapsed `ACME-B1-H05-P1-a`, `RT ACME-B1-H05-P1-a` and
            # `ACME-B1-H05-P1-a | Advantage+` — three genuinely different ads — onto one record.
            m = next((t for t in re.split(r"[\s|/]+", key) if AD_NAME_RE.match(t)), None)
            cand = by_ad.get(m.lower()) if m else None
            if cand is not None and a.fuzzy:
                rec = cand
            elif cand is not None:
                near.append((key, cand.get("job")))
                unattributed.append(row)
                continue
        if rec is None:
            unattributed.append(row)
            continue
        joined.append((rec, row))

    wrote = set()
    if not a.dry_run:
        for rec, row in joined:
            job = rec["path"]
            live = led.derive(job, led.load(job))
            mets = live.setdefault("metrics", {})
            # ⛔ REPLACE the platform slot, never merge. Merging let week 2's impressions sit under
            # week 1's 3-second plays — different populations, and the resulting hook rate was 700%.
            slot = {k: v for k, v in row.items() if not k.startswith("_") and v not in (None, "")}
            slot["_source_file"] = os.path.basename(parsed["file"])
            slot["_ingested"] = led.now()
            slot["_rows_collapsed"] = row.get("_rows", 1)
            slot["waterfall"] = waterfall(a.platform, slot)
            mets[a.platform] = slot
            led.save(job, live)
            wrote.add(job)

    result = {"platform": a.platform, "file": parsed["file"],
              "rows_in_file": parsed["rows_in_file"], "keyed_rows": len(parsed["rows"]),
              "after_collapse": len(grouped), "totals_rows_dropped": parsed["totals_rows_dropped"],
              "unkeyed_rows": len(parsed["unkeyed"]), "joined": len(joined),
              "unattributed": [r["_key"] for r in unattributed] + ["(no key)"] * len(parsed["unkeyed"]),
              "near_misses": near, "recognised_columns": parsed["recognised"],
              "quarantined_columns": parsed["quarantined"], "records_written": len(wrote),
              "number_notes": parsed["notes"][:20], "collapse_notes": collapse_notes[:20],
              "records_in_root": len(recs)}
    if a.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if joined else 1

    print(f"\n{a.platform} · {os.path.basename(parsed['file'])}")
    print("-" * 74)
    print(f"  {parsed['rows_in_file']} data row(s) in file"
          + (f" · {parsed['totals_rows_dropped']} totals row(s)" if parsed["totals_rows_dropped"] else "")
          + (f" · {parsed['unkeyed_rows']} with NO identity column"
             if parsed["unkeyed_rows"] else ""))
    if len(grouped) != len(parsed["rows"]):
        print(f"  collapsed {len(parsed['rows'])} → {len(grouped)} row(s) by join key "
              f"(a broken-out export has one row per ad PER BREAKDOWN; additive fields summed)")
    for n in collapse_notes[:5]:
        print(f"     ⚠ {n}")
    print(f"  recognised {len(parsed['recognised'])} column(s): {', '.join(parsed['recognised'])}")
    if parsed["quarantined"]:
        print(f"  ⛔ QUARANTINED {len(parsed['quarantined'])} unrecognised column(s) — NOT read:")
        for h in parsed["quarantined"][:12]:
            print(f"       {h!r}")
        print(f"     No platform publishes a header list, so this is expected. Map what you need:"
              f"\n       --map \"{parsed['quarantined'][0]}=impressions\"")
    if parsed["notes"]:
        print(f"  ⚠ {len(parsed['notes'])} cell(s) in numeric columns were not usable "
              f"(first: {parsed['notes'][0]})")
    print(f"  joined {len(joined)} of {parsed['rows_in_file']} row(s) in the file, to "
          f"{len(recs)} record(s) under {os.path.abspath(a.root)}")
    if near:
        print(f"  ⛔ {len(near)} NEAR MISS — the key is embedded in a longer ad name. NOT joined, "
              f"because\n     `RT ACME-B1-H05-P1-a` and `ACME-B1-H05-P1-a` are different ads:")
        for k, j in near[:6]:
            print(f"       {k!r}  looks like  {j}")
        print("     Pass --fuzzy to accept, or give the ad its own variant suffix.")
    if unattributed or parsed["unkeyed"]:
        n = len(unattributed) + len(parsed["unkeyed"])
        print(f"  ⛔ {n} row(s) UNATTRIBUTED — quarantined, not dropped:")
        for r in unattributed[:6]:
            print(f"       {r['_key']}")
        if parsed["unkeyed"]:
            print(f"       …and {len(parsed['unkeyed'])} row(s) with no identity column at all "
                  f"(boosted posts, or an export with no ad-name column)")
        print("     Either the ad name does not carry the five-part join key "
              "(`ledger.py set --ad-name`),\n     or it is an organic post with no publish record "
              "(`ledger.py publish <job> --platform … --post-id …`).")
    if a.dry_run:
        print("  (--dry-run: nothing written)")
    else:
        print(f"  wrote metrics onto {len(wrote)} record(s)")
    if not joined:
        print("\n  ⛔ NOTHING JOINED. This is not a clean run — it means the identity layer is "
              "missing,\n     not that the videos underperformed.")
        return 1
    return 0


def cmd_report(a) -> int:
    """The waterfall, PER PLATFORM. ⛔ It refuses to total across platforms, because 'views' is a
    different quantity on each of the four and YouTube redefined it twice in eighteen months."""
    led = _ledger()
    recs, _ = led.index(a.root, write=False)
    recs = [r for r in recs
            if (not a.client or r.get("client", "").lower() == a.client.lower())
            and (not a.month or (r.get("opened") or "")[:7] == a.month)]
    have = [r for r in recs if r.get("metrics")]
    rows = []
    for r in have:
        for plat, m in (r.get("metrics") or {}).items():
            w = m.get("waterfall") or waterfall(plat, m)
            imp = m.get("impressions")
            rows.append({"job": r.get("job"), "ad_name": (r.get("identity") or {}).get("ad_name"),
                         "hook": (r.get("identity") or {}).get("hook"),
                         "persona": (r.get("identity") or {}).get("persona"),
                         "platform": plat, "impressions": imp, "spend": m.get("spend"),
                         "under_floor": (imp is None or imp < IMPRESSION_FLOOR),
                         "hook_rate": w.get("hook_rate"), "hold_rate": w.get("hold_rate"),
                         "ctr": w.get("ctr"), "verdict": w.get("verdict"),
                         "benchmarked": w.get("benchmarked"), "change_next": w.get("change_next")})
    if a.json:
        print(json.dumps({"videos_in_scope": len(recs), "with_metrics": len(have),
                          "impression_floor": IMPRESSION_FLOOR, "rows": rows},
                         indent=2, ensure_ascii=False))
        return 0 if rows else 1
    print(f"\nperformance · {len(have)} of {len(recs)} video(s) carry metrics"
          + (f" · client {a.client}" if a.client else "")
          + (f" · videos OPENED in {a.month}" if a.month else ""))
    if a.month:
        print("  ⚠ --month filters on the job's OPEN date, not the metrics period — an export has "
              "its own\n    date range and this tool does not record it yet. A video opened in June "
              "and measured in\n    September is excluded here.")
    if not rows:
        print("\n  ⛔ NO METRICS INGESTED for this scope. Nothing here is a performance finding — "
              "it is\n     an absence of data. `pull_metrics.py ingest <export.csv> --platform …`")
        return 1
    for plat in sorted({r["platform"] for r in rows}):
        sub = [r for r in rows if r["platform"] == plat]
        print(f"\n  {plat}" + ("" if sub[0]["benchmarked"] else
                               "   ⚠ UNBENCHMARKED — the weak/strong bands in performance-metrics.md "
                               "§1 were derived on Meta's fields"))
        print("  " + "-" * 72)
        print(f"    {'ad name':<26} {'hook':<7} {'impr':>8} {'hook%':>7} {'hold%':>7} {'ctr%':>6}  note")
        for r in sorted(sub, key=lambda x: -(x["impressions"] or 0)):
            def pct(v):
                return f"{v*100:6.1f}" if isinstance(v, (int, float)) else "     -"
            note = "under floor — directional only" if r["under_floor"] else (r["change_next"] or "")
            imp = (f"{int(r['impressions']):>8}" if isinstance(r["impressions"], (int, float))
                   else "       -")
            print(f"    {(r['ad_name'] or r['job'] or '?')[:26]:<26} {(r['hook'] or '-'):<7} "
                  f"{imp} {pct(r['hook_rate'])} "
                  f"{pct(r['hold_rate'])} {pct(r['ctr'])}  {note}")
    under = [r for r in rows if r["under_floor"]]
    print()
    if under:
        print(f"  ⛔ {len(under)} of {len(rows)} row(s) are under the {IMPRESSION_FLOOR}-impression "
              f"floor. Those are DIRECTIONAL\n     reads, never findings — an 8-video trial batch "
              f"will rarely clear it per hook\n     (performance-metrics.md §3). The floor itself is "
              f"a practitioner range [SECONDARY],\n     not a platform rule; anyone quoting an "
              f"official one is quoting folklore.")
    print("  ⛔ Not totalled across platforms on purpose: a TikTok view is a playback start, Meta's "
          "paid\n     ladder has no 'views' column at all, and YouTube redefined the word twice "
          "since 2025.")
    return 0


def cmd_hooks(a) -> int:
    """Hook performance and the two-witness promotion bar (performance-metrics.md §3)."""
    led = _ledger()
    if getattr(a, "month", None):
        print("note: --month is not applied to the hook bank — a hook's evidence is every read it "
              "has\n      ever had, and windowing it would silently weaken the two-witness bar.",
              file=sys.stderr)
    recs, _ = led.index(a.root, write=False)
    if a.client:
        recs = [r for r in recs if r.get("client", "").lower() == a.client.lower()]
    hooks: dict = {}
    for r in recs:
        hk = (r.get("identity") or {}).get("hook")
        if not hk:
            continue
        h = hooks.setdefault(hk, {"runs": 0, "reads": [], "under_floor": 0, "jobs": []})
        h["runs"] += 1
        h["jobs"].append(r.get("job"))
        for plat, m in (r.get("metrics") or {}).items():
            imp = m.get("impressions")
            hr = ((m.get("waterfall") or {}).get("hook_rate"))
            if hr is None:
                continue
            if imp is None or imp < IMPRESSION_FLOOR:
                h["under_floor"] += 1
            else:
                h["reads"].append({"platform": plat, "hook_rate": hr, "impressions": imp,
                                   "job": r.get("job"), "week": (r.get("identity") or {}).get("batch")})
    # ⛔ The bank average used to include the hook's OWN reads, and a loss used <=. Consequences,
    # both reproduced: a hook scoring 42% on two videos — "strong" by §1's own band — became its own
    # average, lost twice, and was written into HOOKS-USED.md as RETIRE; and PROMOTE was
    # mathematically unreachable for a hook alone in the bank, because the mean of two numbers is
    # exceeded by at most one of them. That is exactly the state of an 8-video trial batch.
    # Leave-one-out: each read is compared against the average of every OTHER hook's reads.
    per_plat: dict = {}
    for hk, h in hooks.items():
        for rd in h["reads"]:
            per_plat.setdefault(rd["platform"], []).append((hk, rd["hook_rate"]))
    avg = {p: sum(v for _, v in vs) / len(vs) for p, vs in per_plat.items() if vs}

    def others_avg(plat, hk):
        vs = [v for h2, v in per_plat.get(plat, []) if h2 != hk]
        return (sum(vs) / len(vs)) if vs else None

    out = []
    for hk, h in sorted(hooks.items()):
        wins, losses, nocmp = set(), set(), 0
        for rd in h["reads"]:
            base = others_avg(rd["platform"], hk)
            if base is None:
                nocmp += 1                      # nothing to compare against is not a verdict
            elif rd["hook_rate"] > base:
                wins.add(rd["job"])
            elif rd["hook_rate"] < base:
                losses.add(rd["job"])
        status = ("PROMOTE" if len(wins) >= 2 else
                  "RETIRE" if len(losses) >= 2 else
                  "IN TEST — no comparison set" if nocmp and not (wins or losses) else "IN TEST")
        out.append({"hook": hk, "runs": h["runs"], "reads_above_floor": len(h["reads"]),
                    "under_floor": h["under_floor"], "winning_videos": len(wins),
                    "losing_videos": len(losses), "no_comparison": nocmp, "status": status,
                    "best_hook_rate": max((rd["hook_rate"] for rd in h["reads"]), default=None),
                    "impressions": sum(rd["impressions"] for rd in h["reads"]),
                    "jobs": h["jobs"]})
    if a.json:
        print(json.dumps({"bank_average_hook_rate": avg, "impression_floor": IMPRESSION_FLOOR,
                          "hooks": out}, indent=2, ensure_ascii=False))
        return 0 if out else 1
    if not out:
        print("\n  no hooks recorded. `ledger.py set <job> --hook H05` puts the hook on the video; "
              "without\n  it the bank is a list of guesses and the promotion floors cannot be "
              "applied.")
        return 1
    print(f"\nhook bank · {len(out)} hook(s)"
          + (f" · bank average hook rate: " + ", ".join(f"{p} {v*100:.1f}%" for p, v in avg.items())
             if avg else " · ⛔ NO reads above the floor — every status below is IN TEST by default"))
    print("  " + "-" * 72)
    print(f"    {'hook':<8} {'runs':>5} {'reads':>6} {'<floor':>7} {'best%':>7} {'impr':>8} "
          f"{'win':>4} {'lose':>5}  status")
    for h in out:
        best = f"{h['best_hook_rate']*100:6.1f}" if h["best_hook_rate"] is not None else "     -"
        print(f"    {h['hook']:<8} {h['runs']:>5} {h['reads_above_floor']:>6} "
              f"{h['under_floor']:>7} {best} {h['impressions']:>8} "
              f"{h['winning_videos']:>4} {h['losing_videos']:>5}  {h['status']}")
    print("\n  ⛔ PROMOTE needs the hook to beat the bank average on TWO SEPARATE VIDEOS, each above "
          f"the\n     {IMPRESSION_FLOOR}-impression floor. One great week is one witness. Two "
          "platforms on the same\n     video is one witness too — it is one video's luck measured "
          "twice.")
    if a.write:
        path = write_hooks_used(a.write, out, avg)
        print(f"\n  wrote {path}")
        print("     ⛔ GENERATED — every row derives from ingested metrics. Do not hand-edit it; "
              "the next\n     run overwrites the table. Put judgement in the Notes column of the "
              "series DECISIONS.md.")
    return 0


def write_hooks_used(path: str, hooks: list, avg: dict) -> str:
    """⛔ `HOOKS-USED.md` was a template with no writer — like `EPISODES.md` and `COSTS-*.md`, it was
    a file the docs assumed somebody was maintaining by hand. A hook register nobody updates is
    worse than none, because it is consulted."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    lines = ["# HOOKS-USED — generated, do not hand-edit", "",
             "Written by `pull_metrics.py hooks --write`. Every row derives from ingested platform",
             "metrics; the next run replaces the table. Judgement belongs in the series",
             "`DECISIONS.md`, not here.", "",
             f"Bank average hook rate: " + (", ".join(f"{p} {v*100:.1f}%" for p, v in sorted(avg.items()))
                                            or "⛔ none — no read has cleared the impression floor"),
             f"Impression floor: {IMPRESSION_FLOOR} [SECONDARY · practitioner range, not a platform "
             f"rule]", "",
             "| Hook ID | Times run | Best hook rate | Impressions | Reads above floor | "
             "Reads under floor | Winning videos | Losing videos | Episodes | Status |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for h in hooks:
        best = f"{h['best_hook_rate']*100:.1f}%" if h.get("best_hook_rate") is not None else "—"
        eps = ", ".join((h.get("jobs") or [])[:4]) or "—"
        lines.append(f"| {h['hook']} | {h['runs']} | {best} | {h['impressions']} | "
                     f"{h['reads_above_floor']} | {h['under_floor']} | {h['winning_videos']} | "
                     f"{h['losing_videos']} | {eps} | **{h['status']}** |")
    lines += ["", "⛔ PROMOTE = beat the bank average on two SEPARATE videos, each above the floor.",
              "⛔ A hook with no reads above the floor is IN TEST regardless of how it looks.", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def selftest() -> int:
    import tempfile, shutil
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    # ⛔ number parsing is where a silent wrong answer lives: Google Ads documents that an account
    # may render 2,000.50 or 2.000,50 and no platform documents an export-locale override.
    for raw, want in [("1,234", 1234.0), ("1.234,56", 1234.56), ("1,234.56", 1234.56),
                      ("2.000,50", 2000.50), ("12,5", 12.5), ("45%", 45.0), ("$1,200.00", 1200.0),
                      ("--", None), ("—", None), ("N/A", None), ("", None), ("0", 0.0)]:
        got = to_num(raw)[0]
        check(f"number {raw!r} → {want}", got == want)
    check("an unparseable cell is REPORTED, not zeroed", to_num("about ten")[1] != "")
    check("H:M:S average view duration is converted", hms_to_seconds("0:00:27") == 27.0)
    check("...and a bare number is left alone", hms_to_seconds("27") == 27.0)
    check("...and junk returns None rather than 0", hms_to_seconds("n/a") is None)

    d = tempfile.mkdtemp()
    try:
        # a Meta-shaped export with a summary totals row, a locale decimal and an unknown column
        p = os.path.join(d, "meta.csv")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("Ad Name,Impressions,3-Second Video Plays,ThruPlays,Link Clicks,"
                     "Amount Spent,Some Column We Do Not Know\n"
                     "ACME-B1-H05-P1-a,10000,3500,1400,120,\"1.234,56\",whatever\n"
                     "ACME-B1-H07-P2-a,8000,1600,900,40,\"900,00\",whatever\n"
                     ",18000,5100,2300,160,\"2.134,56\",\n")
        got = parse(p, "meta", {})
        check("the summary/totals row is dropped, not counted as a video",
              len(got["rows"]) == 2 and got["totals_rows_dropped"] == 1)
        check("an unrecognised column is QUARANTINED and named",
              got["quarantined"] == ["Some Column We Do Not Know"])
        check("...and the recognised ones are reported as a denominator",
              set(got["recognised"]) == {"ad_name", "impressions", "v3s", "thruplays",
                                         "link_clicks", "spend"})
        check("European decimals survive", got["rows"][0]["spend"] == 1234.56)

        # ⛔ a day-broken export: three rows for ONE ad. The first version overwrote field by
        # field and kept the LAST row — 204.44 of 612.44 spend recorded, printed as "joined 3 of 3".
        pd_ = os.path.join(d, "meta-daily.csv")
        with open(pd_, "w", encoding="utf-8") as fh:
            fh.write("Ad Name,Day,Impressions,3-Second Video Plays,ThruPlays,Amount Spent,Reach\n"
                     "ACME-B1-H05-P1-a,2026-09-01,14000,4900,2000,204.00,9000\n"
                     "ACME-B1-H05-P1-a,2026-09-02,14000,4900,2000,204.00,9100\n"
                     "ACME-B1-H05-P1-a,2026-09-03,14150,4900,2000,204.44,9200\n")
        g, cn = collapse(parse(pd_, "meta", {})["rows"])
        check("⛔ N rows for one ad are SUMMED, not overwritten by the last",
              len(g) == 1 and g[0]["impressions"] == 42150 and abs(g[0]["spend"] - 612.44) < 0.01)
        check("⛔ ...and reach is DROPPED with a note, because summing it is meaningless",
              "reach" not in g[0] and any("reach" in n for n in cn))

        # ⛔ rows with no identity column were counted as "totals" and DISCARDED, taking real spend
        pb = os.path.join(d, "meta-boosted.csv")
        with open(pb, "w", encoding="utf-8") as fh:
            fh.write("Ad Name,Impressions,Amount Spent\n"
                     "ACME-B1-H05-P1-a,1000,100.00\n"
                     ",2000,400.00\n"
                     ",3000,480.00\n")
        gp = parse(pb, "meta", {})
        check("⛔ a keyless row is UNATTRIBUTED, not silently dropped as a totals row",
              gp["totals_rows_dropped"] == 0 and len(gp["unkeyed"]) == 2)
        # ...but a real trailing totals row, whose numbers ARE the column sums, still goes
        pt = os.path.join(d, "meta-totals.csv")
        with open(pt, "w", encoding="utf-8") as fh:
            fh.write("Ad Name,Impressions,Amount Spent\n"
                     "ACME-B1-H05-P1-a,1000,100.00\n"
                     "ACME-B1-H07-P2-a,2000,200.00\n"
                     ",3000,300.00\n")
        gt = parse(pt, "meta", {})
        check("...and a trailing row whose numbers equal the column sums IS the totals row",
              gt["totals_rows_dropped"] == 1 and gt["unkeyed"] == [] and len(gt["rows"]) == 2)

        # ⛔ a title row above the header used to be chosen AS the header
        ptl = os.path.join(d, "meta-title.csv")
        with open(ptl, "w", encoding="utf-8") as fh:
            fh.write("Ad performance,Sep 2026\n"
                     "Ad Name,Impressions,Amount Spent\n"
                     "ACME-B1-H05-P1-a,1000,100.00\n")
        gl = parse(ptl, "meta", {})
        check("the header is chosen by how many columns the alias table RECOGNISES",
              set(gl["recognised"]) == {"ad_name", "impressions", "spend"} and len(gl["rows"]) == 1)

        # a bare-dot European file: the defect that made 12.480 impressions read as 12.48
        pde = os.path.join(d, "meta-de.csv")
        with open(pde, "w", encoding="utf-8") as fh:
            fh.write("Ad Name;Impressions;3-Second Video Plays;Link Clicks;Amount Spent\n"
                     "ACME-B1-H05-P1-a;12.480;4.115;96;\"1.234,56\"\n")
        gd = parse(pde, "meta", {})["rows"][0]
        check("⛔ bare-dot thousands survive (12.480 is not 12.48)", gd["impressions"] == 12480)
        wd = waterfall("meta", gd)
        check("...so the CTR computed from them is sane, not 769%", wd["ctr"] < 0.01)

        w = waterfall("meta", got["rows"][0])
        check("Meta hook rate is 3s ÷ impressions", abs(w["hook_rate"] - 0.35) < 1e-9)
        check("...and hold rate is ThruPlay ÷ 3s", abs(w["hold_rate"] - 0.40) < 1e-9)
        check("...and the earliest weak stage is what it tells you to change",
              waterfall("meta", got["rows"][1])["change_next"].startswith("the hook"))
        check("...and Meta's skip-inclusive quartiles are flagged", w["quartiles_include_skips"])
        mixed = waterfall("meta", {"impressions": 2000, "v3s": 14000, "thruplays": 100})
        check("⛔ a ratio outside 0..1 is a DATA FAULT, never a 'strong' grade",
              mixed["hook_rate"] is None and mixed["verdict"]["hook_rate"] == "n/a"
              and mixed["faults"])

        tw = waterfall("tiktok", {"impressions": 100, "v2s": 40, "p100": 10, "link_clicks": 1})
        check("TikTok is computed on ITS OWN fields, and says so",
              "2s" in tw["hook_basis"] and tw["hold_basis"].startswith("views at 100%"))
        check("⛔ ...and is NOT judged against Meta's bands",
              tw["benchmarked"] is False and tw["verdict"]["hook_rate"] == "UNBENCHMARKED")
        yw = waterfall("youtube", {"avg_pct": 42.0, "ctr": 5.0})
        check("YouTube reports hook rate as not computable rather than inventing one",
              yw["hook_rate"] is None and "no sub-3-second metric" in yw["hook_basis"])

        # end to end against a real ledger
        led = _ledger()
        root = os.path.join(d, "prod")
        job = os.path.join(root, "acme-01001-a")
        os.makedirs(os.path.join(job, "00-brief"))
        with open(os.path.join(job, "00-brief", "CHECKPOINT.md"), "w") as fh:
            fh.write("Job: acme-01001-a\nMode: B\nClient: acme\n")
        rec = led.derive(job, led.load(job))
        rec["identity"] = {"ad_name": "ACME-B1-H05-P1-a", "hook": "H05", "persona": "P1"}
        led.save(job, rec)

        class A: pass
        a = A(); a.file = p; a.platform = "meta"; a.root = root; a.map = []; a.dry_run = False
        a.json = True; a.fuzzy = False
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = ingest(a)
        res = json.loads(buf.getvalue())
        check("ingest joins on the ad-name key", rc == 0 and res["joined"] == 1)
        check("...and the row that matched nothing is UNATTRIBUTED, not dropped silently",
              res["unattributed"] == ["ACME-B1-H07-P2-a"])
        saved = led.load(job)["metrics"]["meta"]
        check("...and the metrics land on the video's record",
              saved["impressions"] == 10000 and abs(saved["waterfall"]["hook_rate"] - 0.35) < 1e-9)

        a.root = root; a.client = None; a.month = None; a.json = True; a.write = None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_report(a)
        rep = json.loads(buf.getvalue())
        check("report reads it back", rep["with_metrics"] == 1
              and rep["rows"][0]["ad_name"] == "ACME-B1-H05-P1-a")
        check("⛔ ...and flags a 10k-impression row as ABOVE the floor",
              rep["rows"][0]["under_floor"] is False)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_hooks(a)
        hk = json.loads(buf.getvalue())
        check("⛔ a lone hook has no comparison set, so it gets no verdict at all",
              hk["hooks"][0]["status"] == "IN TEST — no comparison set")

        # the two defects the adversarial read reproduced, pinned:
        fake = {"H05": {"reads": [{"platform": "meta", "hook_rate": 0.42, "job": "j1",
                                   "impressions": 5000},
                                  {"platform": "meta", "hook_rate": 0.42, "job": "j2",
                                   "impressions": 5000}],
                        "runs": 2, "under_floor": 0, "jobs": ["j1", "j2"]}}
        pp = {"meta": [("H05", 0.42), ("H05", 0.42)]}
        oth = [v for h2, v in pp["meta"] if h2 != "H05"]
        check("⛔ a hook alone in the bank is not measured against ITSELF", oth == [])
        # with a second hook present, a genuinely strong hook must reach PROMOTE
        job3 = os.path.join(root, "acme-01003-c")
        for jj, an, hkid, hr in ((job3, "ACME-B1-H09-P1-a", "H09", 0.10),):
            os.makedirs(os.path.join(jj, "00-brief"), exist_ok=True)
            with open(os.path.join(jj, "00-brief", "CHECKPOINT.md"), "w") as fh:
                fh.write(f"Job: {os.path.basename(jj)}\nMode: B\nClient: acme\n")
            rr = led.derive(jj, led.load(jj))
            rr["identity"] = {"ad_name": an, "hook": hkid}
            rr["metrics"] = {"meta": {"impressions": 9000,
                                      "waterfall": {"hook_rate": hr, "benchmarked": True}}}
            led.save(jj, rr)
        for n, hr in (("acme-01004-d", 0.42), ("acme-01005-e", 0.42)):
            jj = os.path.join(root, n)
            os.makedirs(os.path.join(jj, "00-brief"), exist_ok=True)
            with open(os.path.join(jj, "00-brief", "CHECKPOINT.md"), "w") as fh:
                fh.write(f"Job: {n}\nMode: B\nClient: acme\n")
            rr = led.derive(jj, led.load(jj))
            rr["identity"] = {"ad_name": f"ACME-B1-H05-P1-{n[-1]}", "hook": "H05"}
            rr["metrics"] = {"meta": {"impressions": 9000,
                                      "waterfall": {"hook_rate": hr, "benchmarked": True}}}
            led.save(jj, rr)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_hooks(a)
        hk2 = {h["hook"]: h for h in json.loads(buf.getvalue())["hooks"]}
        check("⛔ a hook that beats the OTHER hooks on two videos reaches PROMOTE",
              hk2["H05"]["status"] == "PROMOTE" and hk2["H05"]["winning_videos"] >= 2)
        check("...while the hook it beat has only ONE losing video, so it stays IN TEST — "
              "retirement needs two witnesses too",
              hk2["H09"]["status"] == "IN TEST" and hk2["H09"]["losing_videos"] == 1)
        check("...and the register carries the RATE, which §6 promised and the first version omitted",
              hk2["H05"]["best_hook_rate"] is not None)

        # a sub-floor read must never become a finding
        rec2 = led.load(job)
        rec2["metrics"]["meta"]["impressions"] = 50
        led.save(job, rec2)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_report(a)
        check("⛔ a 50-impression row is marked under the floor",
              json.loads(buf.getvalue())["rows"][0]["under_floor"] is True)

        # nothing joined must not read as a clean run
        empty = os.path.join(d, "empty-prod")
        os.makedirs(empty)
        a2 = A(); a2.file = p; a2.platform = "meta"; a2.root = empty; a2.map = []
        a2.dry_run = True; a2.json = True; a2.fuzzy = False
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = ingest(a2)
        check("⛔ zero joins exits non-zero rather than reporting success", rc == 1)

        # --map closes a quarantined column without a code change
        a3 = A(); a3.file = p; a3.platform = "meta"; a3.root = root
        a3.map = ["Some Column We Do Not Know=reach"]; a3.dry_run = True; a3.json = True
        a3.fuzzy = False
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ingest(a3)
        # ⛔ two videos sharing an ad name used to clobber each other silently in the join dict
        dup = os.path.join(root, "acme-01009-dup")
        os.makedirs(os.path.join(dup, "00-brief"), exist_ok=True)
        with open(os.path.join(dup, "00-brief", "CHECKPOINT.md"), "w") as fh:
            fh.write("Job: acme-01009-dup\nMode: B\nClient: acme\n")
        rd = led.derive(dup, led.load(dup))
        rd["identity"] = {"ad_name": "ACME-B1-H05-P1-a"}      # same key as acme-01001-a
        led.save(dup, rd)
        a5 = A(); a5.file = p; a5.platform = "meta"; a5.root = root; a5.map = []
        a5.dry_run = True; a5.json = True; a5.fuzzy = False
        check("⛔ a duplicate ad-name join key is REFUSED, not resolved by sort order",
              ingest(a5) == 2)
        rd = led.load(dup); rd["identity"] = {"ad_name": "ACME-B1-H05-P1-z"}; led.save(dup, rd)

        # ⛔ 'RT ACME-…' and 'ACME-…' are different ads; the key embedded in a longer name is a
        # CANDIDATE, not a join. The first version collapsed three real ads onto one record.
        pn = os.path.join(d, "meta-near.csv")
        with open(pn, "w", encoding="utf-8") as fh:
            fh.write("Ad Name,Impressions,Amount Spent\n"
                     "RT ACME-B1-H05-P1-a,5000,310.00\n")
        a6 = A(); a6.file = pn; a6.platform = "meta"; a6.root = root; a6.map = []
        a6.dry_run = True; a6.json = True; a6.fuzzy = False
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = ingest(a6)
        nm = json.loads(buf.getvalue())
        check("⛔ a near miss is reported, NOT joined", rc == 1 and nm["joined"] == 0
              and nm["near_misses"] and nm["near_misses"][0][1] == "acme-01001-a")
        a6.fuzzy = True
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ingest(a6)
        check("...and --fuzzy is what accepts it, explicitly",
              json.loads(buf.getvalue())["joined"] == 1)

        check("--map maps a quarantined header at runtime",
              json.loads(buf.getvalue())["quarantined_columns"] == [])

        hp = os.path.join(d, "HOOKS-USED.md")
        a4 = A(); a4.root = root; a4.client = None; a4.month = None; a4.json = False; a4.write = hp
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_hooks(a4)
        body = open(hp, encoding="utf-8").read()
        check("HOOKS-USED.md is GENERATED from the data, not hand-maintained",
              os.path.isfile(hp) and "H05" in body and "IN TEST" in body)
        check("...and it says the floor is a practitioner range, not a platform rule",
              "SECONDARY" in body and "not a platform" in body)

    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("-" * 62)
    print("selftest OK — bare-dot AND comma thousands, accounting negatives, bounded values "
          "refused; N rows per ad SUMMED not overwritten and non-additive fields dropped with a "
          "note; a keyless row is unattributed while a real totals row is not; the header is chosen "
          "by alias matches; ratios outside 0..1 are data faults rather than grades; duplicate join "
          "keys refused and near misses reported not joined; each platform on its OWN fields with "
          "only Meta benchmarked; leave-one-out comparison so a hook is never measured against "
          "itself and two witnesses are needed either way; zero joins exits non-zero"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    ing = sub.add_parser("ingest")
    ing.add_argument("file"); ing.add_argument("--platform", required=True,
                                               choices=["meta", "tiktok", "youtube", "googleads"])
    ing.add_argument("--root", required=True); ing.add_argument("--map", action="append", default=[],
                                                                help='"Header=field", repeatable')
    ing.add_argument("--fuzzy", action="store_true",
                     help="accept a join where the five-part key is EMBEDDED in a longer ad name. Off by default: 'RT ACME-B1-H05-P1-a' is a different ad from 'ACME-B1-H05-P1-a'.")
    ing.add_argument("--dry-run", action="store_true"); ing.add_argument("--json", action="store_true")
    for name in ("report", "hooks"):
        p = sub.add_parser(name)
        p.add_argument("root"); p.add_argument("--client")
        p.add_argument("--month", help=("report: filters on the job's OPEN date, not the metrics "
                                        "period" if name == "report" else argparse.SUPPRESS))
        p.add_argument("--json", action="store_true")
        if name == "hooks":
            p.add_argument("--write", metavar="PATH",
                           help="write _series/<BRAND>/HOOKS-USED.md from the data. That file was a "
                                "template with no writer, and a hook register nobody updates is "
                                "worse than none because it gets consulted.")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    try:
        return {"ingest": ingest, "report": cmd_report, "hooks": cmd_hooks}[a.cmd](a)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr); return 2


if __name__ == "__main__":
    sys.exit(main())
