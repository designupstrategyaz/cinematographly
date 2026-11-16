#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""rate_card.py — what does N seconds of <model> at <resolution> cost? The one place that answers it.

Generation rates were scattered across prose, a vendor card, a third-party page and a client's cost
file, and three of those four disagreed. This reads ONE table — `assets/higgsfield-rates.json`
→ `rate_table` — and nothing else in the skill restates a rate.

  lookup  — credits for a model x resolution x duration (and USD, with --credit-price)
  table   — the whole matrix, cheapest first
  compare — the same shot priced across every roster model that can deliver it

⛔ Three things this refuses to do
----------------------------------
  * Price an OFF-ROSTER model. The table holds the approved models only; a rate is how a
    retired model gets quietly re-adopted on cost.
  * Price a duration the model cannot produce. Each entry carries the vendor's min/max seconds and
    a request outside them is refused, not clamped — a clamped quote is a wrong quote.
  * Pretend a measured rate is a stable one. Every rate is stamped with the date it was read off the
    Generate button; past --stale-days it warns, and where a reading is known to have moved it says so.

⛔ The prices are DISCOUNTED
---------------------------
The Generate button shows a promotional price with the list price struck through beside it. Where
list is known, `--list` prices at list. **Quote a client list unless the discount is contractually
yours** — a quote built on a promotion expires with it.

What it cannot do
-----------------
- **It cannot tell you the rate is still true.** It reports what was measured and when. The only
  authority is the Generate button on the account, today: see scripts/refresh_costs.md.
- It does not know your per-credit price. Pass --credit-price (from the invoice: monthly cost ÷
  monthly credits) for a USD figure; there is no default, because plan tiers differ ~2x.
- It says nothing about quality. Cheapest is a cost fact, not a casting decision.

Usage
-----
  python3 rate_card.py table
  python3 rate_card.py lookup --model minimax_h3 --res 2k --seconds 6
  python3 rate_card.py lookup --model seedance_2_5 --res 1080p --seconds 6 --list --credit-price 0.033
  python3 rate_card.py compare --seconds 6 --json

Exit codes: 0 ok · 1 refused (off roster, out of range, unknown resolution) · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, json, os, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
RATES = os.path.join(HERE, "..", "assets", "higgsfield-rates.json")
DEFAULT_STALE_DAYS = 30
# Any leading-underscore key in rate_table is documentation, not a model.
META_PREFIX = "_"


def override_path() -> str | None:
    """(3.1) `<studio>/rates-override.json`: rates the studio re-read off its own account. A plugin update replaces
    assets/higgsfield-rates.json, so refreshed rates live in the studio folder and win row by row."""
    try:
        import studio
        d = studio.studio_dir()
    except Exception:                                          # noqa: BLE001 — no studio is not an error here
        d = None
    return os.path.join(d, "rates-override.json") if d else None


def _override(key: str) -> dict:
    p = override_path()
    try:
        t = json.load(open(p, encoding="utf-8")).get(key) if p and os.path.isfile(p) else None
    except (OSError, ValueError):
        print(f"warning: {p} is not readable JSON — ignored", file=sys.stderr)
        return {}
    if t is not None and not isinstance(t, dict):
        print(f"warning: {p} `{key}` is not an object of models — ignored (format: scripts/refresh_costs.md)",
              file=sys.stderr)
        return {}
    return {k: v for k, v in (t or {}).items() if not k.startswith(META_PREFIX)}


PRICE_FIELDS = ("cr_per_s", "cr_per_image")      # what a quote multiplies; list prices may be null


def _merge(base: dict, ov: dict, key: str) -> dict:
    """(3.1 review) Merge an override FIELD BY FIELD: {model: {resolution: {field: value}}}. An override that names only
    `cr_per_s` and `measured` keeps the house row's other fields (min_s, max_s, …). A malformed entry warns and is
    skipped; it never replaces a good row or crashes a quote."""
    out = {m: dict(r) if isinstance(r, dict) else r for m, r in base.items()}
    for model, res in ov.items():
        if not isinstance(res, dict):
            print(f"warning: rates-override `{key}.{model}` is not an object of resolutions — ignored", file=sys.stderr)
            continue
        row = dict(out.get(model) or {})
        for r, fields in res.items():
            if not isinstance(fields, dict):
                print(f"warning: rates-override `{key}.{model}.{r}` is not an object of fields — ignored",
                      file=sys.stderr)
                continue
            bad = [k_ for k_ in PRICE_FIELDS if k_ in fields and not (
                isinstance(fields[k_], (int, float)) and not isinstance(fields[k_], bool) and fields[k_] > 0)]
            if bad:
                # (3.1 build review 1, Grok HIGH) a zero or negative price would pass every budget stop: refuse it
                print(f"warning: rates-override `{key}.{model}.{r}` {', '.join(bad)} must be a number above 0 — "
                      f"that entry is ignored", file=sys.stderr)
                continue
            row[r] = {**(row.get(r) if isinstance(row.get(r), dict) else {}), **fields}
        out[model] = row
    return out


def stale_note(e: dict, stale_days: int) -> str | None:
    """(3.1) A row with no `measured` date is stale too: an undated price warns, it is never trusted silently."""
    d = age_days(str(e.get("measured") or ""))
    if d is None:
        return "no `measured` date on this rate — re-read it off the Generate button before it decides money"
    if d > stale_days:
        return f"{d} days since this was read off the Generate button. Re-read before it decides money"
    return None


def load_table() -> dict:
    try:
        with open(RATES, encoding="utf-8") as fh:
            t = json.load(fh).get("rate_table")
    except FileNotFoundError:
        print(f"error: {RATES} not found.", file=sys.stderr); raise SystemExit(2)
    if not t:
        print("error: assets/higgsfield-rates.json has no rate_table.", file=sys.stderr)
        raise SystemExit(2)
    out = {k: v for k, v in t.items() if not k.startswith(META_PREFIX)}
    return _merge(out, _override("rate_table"), "rate_table")


def load_image_table() -> dict:
    """The PER-IMAGE half. Separate loader, because a still is not billed per second and pretending
    it is was how `estimate 0 cr` got written into a checkpoint and accepted by the gate."""
    try:
        with open(RATES, encoding="utf-8") as fh:
            t = json.load(fh).get("image_rate_table") or {}
    except FileNotFoundError:
        print(f"error: {RATES} not found.", file=sys.stderr); raise SystemExit(2)
    out = {k: v for k, v in t.items() if not k.startswith(META_PREFIX)}
    return _merge(out, _override("image_rate_table"), "image_rate_table")


def cmd_image(a, _t) -> int:
    """Price n stills. An unpriced model EXITS NONZERO with the words to put in the checkpoint —
    it never returns 0, because a zero estimate is indistinguishable from a free job."""
    t = load_image_table()
    e = (t.get(a.model) or {}).get(a.res)
    if not e:
        have = ", ".join(f"{m} ({'/'.join(sorted(rs))})" for m, rs in sorted(t.items())) or "nothing"
        print(f"UNPRICED: no per-image rate for {a.model!r} at {a.res!r}. Priced here: {have}.\n"
              f"  Do NOT write `estimate 0 cr` — that is 'I could not price it' wearing a figure,\n"
              f"  and the gate refuses it against a non-zero envelope. Either probe once with\n"
              f"  \"get_cost\": true and write what it returned, or write:\n"
              f"    Budget:  envelope <N> cr (<who>) · estimate UNPRICED [unpriced] — no rate for "
              f"{a.model} in assets/higgsfield-rates.json", file=sys.stderr)
        return 1
    total = e["cr_per_image"] * a.count
    if a.json:
        print(json.dumps({"model": a.model, "resolution": a.res, "count": a.count,
                          "cr_per_image": e["cr_per_image"], "credits": total,
                          "measured": e.get("measured")}, indent=2, ensure_ascii=False))
        return 0
    print(f"{a.model} · {a.res} · {a.count} image(s)")
    print(f"  {e['cr_per_image']:g} cr/image x {a.count} = {total:g} cr")
    print(f"  measured {e.get('measured')} · {e.get('readings', '')}")
    if e.get("superseded"):
        print(f"  !! {e['superseded']}")
    note = stale_note(e, a.stale_days)
    if note:
        print(f"  !! {note}")
    print(f"  -> checkpoint line:  estimate {total:g} cr [measured {e.get('measured')}]")
    return 0


def age_days(stamp: str) -> int | None:
    try:
        return (dt.date.today() - dt.date.fromisoformat(stamp[:10])).days
    except (ValueError, TypeError):
        return None


def per_call(entry: dict) -> bool:
    """A row whose price no per-second rate predicts (`"pricing": "per_call"`): kling4_0 since the
    owner's 2026-10-25 note. It is never quoted by the second — the call is probed instead."""
    return str(entry.get("pricing") or "").lower() == "per_call"


def probe_text(model: str, res: str, entry: dict) -> str:
    return (f"PROBE: {model} @ {res} is priced PER CALL — {entry.get('pricing_why') or 'its price does not follow duration'}\n"
            f"  Do not quote it by the second. Open the job with:\n"
            f"    Budget:  envelope <N> cr (<who>) · estimate UNPRICED [unpriced] — {model} is priced per call\n"
            f"  then probe each exact call inside the open job (`gate.py preflight <SHOT> --kind clip`, "
            f"then the call with \"get_cost\": true) and write what it returned: "
            f"estimate <sum> cr [measured <date> · get_cost].")


def price(entry: dict, seconds: float, use_list: bool) -> tuple[float, str]:
    rate = entry.get("list_cr_per_s") if use_list else entry["cr_per_s"]
    if use_list and rate is None:
        return entry["cr_per_s"] * seconds, "discounted (no list price recorded)"
    return rate * seconds, "list" if use_list else "discounted"


def cmd_lookup(a, table) -> int:
    if a.model not in table:
        print(f"REFUSED: {a.model!r} is not on the approved roster.\n"
              f"  Priced models: {', '.join(sorted(table))}\n"
              f"  ⛔ Off-roster models carry no rate on purpose — a rate is how one gets re-adopted "
              f"on cost.", file=sys.stderr)
        return 1
    res = table[a.model]
    if a.res not in res:
        print(f"REFUSED: {a.model} has no {a.res!r} entry. Measured: {', '.join(sorted(res))}",
              file=sys.stderr)
        return 1
    e = res[a.res]
    if not (e["min_s"] <= a.seconds <= e["max_s"]):
        print(f"REFUSED: {a.seconds}s is outside {a.model} {a.res}'s {e['min_s']}-{e['max_s']}s "
              f"range.\n  ⛔ Not clamped — a clamped quote is a wrong quote. Split the shot or pick "
              f"another model.", file=sys.stderr)
        return 1
    if per_call(e):
        if a.json:
            print(json.dumps({"model": a.model, "resolution": a.res, "seconds": a.seconds, "credits": None,
                              "pricing": "per_call", "why": e.get("pricing_why")}, indent=2, ensure_ascii=False))
        else:
            print(probe_text(a.model, a.res, e), file=sys.stderr)
        return 1
    cr, basis = price(e, a.seconds, a.list)
    out = {"model": a.model, "resolution": a.res, "seconds": a.seconds, "credits": round(cr, 2),
           "cr_per_s": e["cr_per_s"], "basis": basis, "measured": e.get("measured")}
    if a.credit_price:
        out["usd"] = round(cr * a.credit_price, 4)
    if a.json:
        print(json.dumps(out, indent=2)); return 0
    print(f"\n  {a.model} @ {a.res} · {a.seconds}s  →  {cr:.2f} credits   ({basis})")
    if a.credit_price:
        print(f"  {'':<{len(a.model)}}                 →  {cr * a.credit_price:,.3f} USD "
              f"at {a.credit_price}/credit")
    print(f"  rate {e['cr_per_s']} cr/s · range {e['min_s']}-{e['max_s']}s · measured {e.get('measured')}")
    if e.get("⛔"):
        print(f"  ⛔ {e['⛔']}")
    note = stale_note(e, a.stale_days)
    if note:
        print(f"  ⚠ {note} (scripts/refresh_costs.md).")
    if not a.list and e.get("list_cr_per_s"):
        print(f"  ⛔ This is the DISCOUNTED price. List is {e['list_cr_per_s']} cr/s "
              f"({e['list_cr_per_s'] * a.seconds:.2f} cr) — quote list unless the discount is yours.")
    print()
    return 0


def rows(table, seconds=None, use_list=False):
    out = []
    for m, res in table.items():
        for r, e in res.items():
            pc = per_call(e)
            row = {"model": m, "resolution": r, "cr_per_s": None if pc else e["cr_per_s"],
                   "list_cr_per_s": e.get("list_cr_per_s"), "min_s": e["min_s"], "max_s": e["max_s"],
                   "measured": e.get("measured"), "note": e.get("⛔"), "pricing": "per_call" if pc else "per_s"}
            if seconds is not None:
                row["fits"] = e["min_s"] <= seconds <= e["max_s"]
                row["credits"] = round(price(e, seconds, use_list)[0], 2) if (row["fits"] and not pc) else None
            out.append(row)
    # per-call rows sort LAST: a model with no predictable price is never "the cheapest"
    return sorted(out, key=lambda r: (r["cr_per_s"] is None, r["cr_per_s"] or 0))


def cmd_table(a, table) -> int:
    rs = rows(table)
    if a.json:
        print(json.dumps(rs, indent=2)); return 0
    print(f"\n  {'model':<16} {'res':<7} {'cr/s':>6} {'list':>6}  {'range':<9} measured")
    print("  " + "-" * 62)
    for r in rs:
        lst = f"{r['list_cr_per_s']:.1f}" if r["list_cr_per_s"] else "—"
        cps = f"{r['cr_per_s']:>6.1f}" if r["cr_per_s"] is not None else f"{'probe':>6}"
        print(f"  {r['model']:<16} {r['resolution']:<7} {cps} {lst:>6}  "
              f"{str(r['min_s']) + '-' + str(r['max_s']) + 's':<9} {r['measured']}")
        if r["note"]:
            print(f"  {'':<16} ⛔ {r['note']}")
    print("\n  ⛔ cr/s is the DISCOUNTED Generate-button price. Quote list unless the discount is "
          "yours.\n  ⛔ Cheapest is a cost fact, not a casting decision.\n")
    return 0


def cmd_compare(a, table) -> int:
    rs = [r for r in rows(table, a.seconds, a.list) if r["fits"]]
    if a.json:
        print(json.dumps(rs, indent=2)); return 0
    if not rs:
        print(f"REFUSED: no roster model produces {a.seconds}s.", file=sys.stderr); return 1
    print(f"\n  A {a.seconds}s shot, priced across the roster ({'list' if a.list else 'discounted'}):\n")
    for r in rs:
        if r["credits"] is None:
            print(f"  {'probe':>7}      {r['model']} @ {r['resolution']}   (priced per call — get_cost the exact call)")
            continue
        line = f"  {r['credits']:>7.2f} cr   {r['model']} @ {r['resolution']}"
        if a.credit_price:
            line += f"   ({r['credits'] * a.credit_price:,.3f} USD)"
        print(line)
    priced = [r for r in rs if r["credits"] is not None]
    if not priced:
        print("\n  ⛔ Cost is never an input to a quality decision (SKILL.md non-negotiable 5).\n")
        return 0
    cheap, dear = priced[0], priced[-1]
    if cheap["credits"] and dear["credits"] and cheap["credits"] > 0:
        print(f"\n  spread {dear['credits'] / cheap['credits']:.1f}x  "
              f"({cheap['model']} @ {cheap['resolution']} → {dear['model']} @ {dear['resolution']})")
    print("  ⛔ Cost is never an input to a quality decision (SKILL.md non-negotiable 5).\n")
    return 0


def selftest() -> int:
    # ⛔ THE HALF OF THE FILE THAT DID NOT EXIST (2026-09-17). Image models are billed per PICTURE,
    # the video schema is per SECOND, so there was nowhere to put a still's price and `rate_card.py`
    # could not price one. The consequence was not a missing feature — it was `estimate 0 cr
    # [estimated]` in a real checkpoint, accepted by the gate, with a 60-credit envelope compared
    # against nothing for a whole run. Both directions pinned: a priced model returns the figure,
    # an unpriced one REFUSES rather than returning zero.
    # (3.1) an undated rate warns; a studio override wins row by row and survives a plugin update
    assert stale_note({}, 30) and stale_note({"measured": "2000-01-01"}, 30)
    assert stale_note({"measured": dt.date.today().isoformat()}, 30) is None
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _td:
        _old = os.environ.get("CINE_STUDIO"); os.environ["CINE_STUDIO"] = _td
        try:
            _m = next(iter(load_image_table()))
            _r = next(iter(load_image_table()[_m]))
            json.dump({"image_rate_table": {_m: {_r: {"cr_per_image": 99.5, "measured": "2026-11-15", "readings": "x"}}}},
                      open(os.path.join(_td, "rates-override.json"), "w"))
            assert load_image_table()[_m][_r]["cr_per_image"] == 99.5, "the studio override wins"
            _vm = next(iter(load_table())); _vr = next(iter(load_table()[_vm]))
            _row = dict(load_table()[_vm][_vr], cr_per_s=7.25, measured="2026-11-15")
            json.dump({"rate_table": {_vm: {_vr: _row}}}, open(os.path.join(_td, "rates-override.json"), "w"))
            assert load_table()[_vm][_vr]["cr_per_s"] == 7.25, "the studio override wins for video rates too"
            json.dump({"rate_table": {_vm: {_vr: {"cr_per_s": 2.0, "measured": "2026-11-15"}}}},
                      open(os.path.join(_td, "rates-override.json"), "w"))
            _merged = load_table()[_vm][_vr]
            os.remove(os.path.join(_td, "rates-override.json"))
            _house = load_table()[_vm][_vr]
            assert _merged["cr_per_s"] == 2.0 and all(_merged.get(k_) == v_ for k_, v_ in _house.items()
                                                      if k_ not in ("cr_per_s", "measured")), \
                "(3.1 review) a partial override keeps the house row's other fields (it crashed on min_s)"
            json.dump({"rate_table": [1, 2]}, open(os.path.join(_td, "rates-override.json"), "w"))
            assert load_table()[_vm][_vr] == _house, "a malformed override is ignored, not a crash"
            json.dump({"rate_table": {_vm: {_vr: 5}}}, open(os.path.join(_td, "rates-override.json"), "w"))
            assert load_table()[_vm][_vr] == _house, "a malformed row is skipped, the house row kept"
            for _bad in (0, -1, "2", True):
                json.dump({"rate_table": {_vm: {_vr: {"cr_per_s": _bad, "measured": "2026-11-16"}}}},
                          open(os.path.join(_td, "rates-override.json"), "w"))
                assert load_table()[_vm][_vr] == _house, f"(3.1 review) an override price of {_bad!r} is ignored"
        finally:
            if _old is None:
                os.environ.pop("CINE_STUDIO", None)
            else:
                os.environ["CINE_STUDIO"] = _old
    it = load_image_table()
    assert it, "image_rate_table missing — a still cannot be priced"
    for m, res in it.items():
        for r, e in res.items():
            assert e.get("cr_per_image", 0) > 0 and e.get("measured") and e.get("readings"), (m, r)

    class _A:
        json = False; stale_days = 10_000; res = "2k"
        def __init__(self, model, count): self.model, self.count = model, count
    assert cmd_image(_A("nano_banana_pro", 6), {}) == 0
    assert cmd_image(_A("nano_banana_pro", 1), {}) == 0
    assert cmd_image(_A("a_model_nobody_priced", 4), {}) == 1      # refuses, never returns 0
    # v2.52.3: the primary image model has a measured row at ONE tier (2k, quality high). A tier
    # nobody measured still refuses — a row for 2k must not price a 4k picture.
    assert cmd_image(_A("gpt_image_2_6", 8), {}) == 0
    class _B(_A):
        res = "4k"
    assert cmd_image(_B("gpt_image_2_6", 1), {}) == 1
    assert cmd_image(_A("nano_banana_pro", 6), {}) == 0

    t = load_table()
    assert t, "rate_table missing"
    for m, res in t.items():
        for r, e in res.items():
            for k in ("cr_per_s", "min_s", "max_s", "measured"):
                assert k in e, (m, r, k)
            assert e["min_s"] < e["max_s"], (m, r)
            assert e["cr_per_s"] > 0
            if per_call(e):
                assert e.get("pricing_why"), (m, r, "a per-call row says why")
    # arithmetic matches the recorded readings
    assert abs(price(t["minimax_h3"]["2k"], 5, False)[0] - 10) < 1e-9
    assert abs(price(t["minimax_h3"]["2k"], 15, False)[0] - 30) < 1e-9
    assert abs(price(t["seedance_2_5"]["1080p"], 6, False)[0] - 54) < 1e-9
    assert abs(price(t["seedance_2_5"]["1080p"], 5, True)[0] - 80) < 1e-9
    assert abs(price(t["kling3_0"]["4k"], 14, False)[0] - 84) < 1e-9
    assert abs(price(t["kling3_0"]["1080p"], 3, False)[0] - 4.5) < 1e-9
    _priced = [r_ for r_ in rows(t) if r_["cr_per_s"] is not None]
    assert _priced[0]["cr_per_s"] <= _priced[-1]["cr_per_s"]
    # ⛔ a per-call row is NEVER quoted by the second (2026-10-25, on kling4_0): lookup refuses,
    # compare shows no figure, and it sorts last so it can never read as the cheapest
    assert per_call(t["kling4_0"]["1080p"])

    class _L:
        json = True; list = False; credit_price = None; stale_days = 10_000
        model, res, seconds = "kling4_0", "1080p", 5.0
    assert cmd_lookup(_L(), t) == 1
    assert rows(t)[-1]["model"] == "kling4_0" and rows(t, 5.0)[-1]["credits"] is None
    print("selftest OK — table shape, duration bounds, and the arithmetic reproduces every recorded "
          "Generate-button reading (H3 5s=10/15s=30 · Seedance 6s=54, list 5s=80 · Kling 4K 14s=84, "
          "1080p 3s=4.5), and a per-call row (kling4_0) that is never quoted by the second")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    for name, h in (("lookup", "price one model x resolution x duration"),
                    ("table", "the whole matrix, cheapest first"),
                    ("compare", "one shot priced across the roster"),
                    ("image", "price n STILLS (per image, not per second)")):
        s = sub.add_parser(name, help=h)
        s.add_argument("--json", action="store_true")
        s.add_argument("--list", action="store_true", help="price at LIST, not the promotional rate")
        s.add_argument("--credit-price", type=float, help="USD per credit, from the invoice")
        s.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
        if name == "lookup":
            s.add_argument("--model", required=True); s.add_argument("--res", required=True)
            s.add_argument("--seconds", type=float, required=True)
        if name == "compare":
            s.add_argument("--seconds", type=float, required=True)
        if name == "image":
            s.add_argument("--model", required=True)
            s.add_argument("--res", default="2k")
            s.add_argument("--count", type=int, default=1)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    t = {} if a.cmd == "image" else load_table()
    return {"lookup": cmd_lookup, "table": cmd_table, "compare": cmd_compare,
            "image": cmd_image}[a.cmd](a, t)


if __name__ == "__main__":
    sys.exit(main())
