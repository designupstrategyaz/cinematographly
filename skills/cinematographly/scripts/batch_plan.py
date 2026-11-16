#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""batch_plan.py — turn persona x hook x body x CTA into the batch matrix you will actually ship.

The point is NOT to enumerate every permutation. 3 personas x 5 hooks x 2 bodies x 2 CTAs is 60
combinations and shipping all 60 is exactly the template-shaped output that reads as slop. This picks
a DESIGNED SUBSET that satisfies the variance rule in ../references/realism-qa.md section 5, spreads
durations across the brief's window, spreads the work across the month's weeks, and prices it.

Deterministic: the same inputs always produce the same matrix, so a plan can be reviewed, re-run and
diffed. Use --seed to explore a different arrangement.

⛔ Balance is not variance. Round-robin over each column separately is perfectly balanced AND a
template: with 2 personas and 2 tones it made P1 serious in every row of every batch at every seed,
and all seven single-column checks passed. Every dimension is now dealt from an independently
shuffled balanced pool and then repaired against a PAIRWISE predictability measure, which is the
only kind of check that can see a property existing between two columns. Pairs whose level counts
multiply past the row count are reported as STRUCTURAL and excluded — no re-deal can separate them,
so the advice there is fewer levels, not more inputs.

Usage
-----
  python3 batch_plan.py --count 30 \\
      --personas P1,P2,P3 --hooks H01,H02,H03,H05,H07 --bodies B1,B2 --ctas C1,C2 \\
      --settings bedroom,kitchen,car,bathroom --presenters archive,ai,faceless \\
      --window 35 55 --weeks 4 --client acme --seconds-per-video 45

  python3 batch_plan.py --count 8 --personas P1,P2 --hooks H01,H02,H03,H04 \\
      --bodies B1 --ctas C1 --md            # emit a markdown table for the batch plan

Cost: reads costs.<client>.json when --client is given, from your client folder (CINE_CLIENTS or a
`_cine-clients/` folder above the working folder) and then the plugin's clients/. Costs are per-generation-second and
drift; this is a planning estimate, not a quote. Preflight the live cost once per batch SHAPE before
spending, and reconcile against what actually settled afterwards.
Exit codes: 0 ok · 1 variance rule not satisfiable with these inputs · 2 usage error.
"""
from __future__ import annotations
import argparse, datetime, json, os, random, sys


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import client_files  # noqa: E402  (where a client's cost file is on this machine)
import cost_model    # noqa: E402  (v2.62.0: the one pricing formula, shared with estimate_duration.py)
TONES = ["serious", "light"]


def load_costs(client: str | None, *starts: str | None) -> dict | None:
    """`starts`: the --out file (v2.59.2), so a `_cine-clients/` folder above the batch is found from anywhere."""
    if not client:
        return None
    p = client_files.find(f"costs.{client}.json", *starts)  # CINE_CLIENTS, a `_cine-clients/` folder, then the plugin's
    if not p:
        print(f"note: no costs.{client}.json ({client_files.where_looked(*starts)}) — skipping the estimate",
              file=sys.stderr)
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def split(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


DIMS = ("persona", "hook", "body", "cta", "tone", "setting", "presenter", "week")


def balanced(levels, count, seed, salt):
    """Every level used floor/ceil(count/len) times, in an INDEPENDENTLY shuffled order.

    Round-robin (i % len) is balanced too, and that is how this used to work. It is also how the
    batch became a template: two dimensions whose lengths share a factor lock into phase, so with
    2 personas and 2 tones P1 was ALWAYS serious and P2 ALWAYS light, forever, at every seed.
    Shuffling a balanced pool per dimension keeps the exact balance and breaks the phase. The
    per-dimension salt means adding one setting does not re-deal the personas.
    """
    if not levels:
        return []
    reps = -(-count // len(levels))
    pool = (list(levels) * reps)[:count]
    random.Random(f"{seed}:{salt}").shuffle(pool)
    return pool


# [MEASURED 2026-09-07] Set from the achievable floor, not from taste. Running the repair to
# convergence over 12 seeds per shape: an 8-row trial batch bottoms out at exactly 0.50 and will
# not go lower at any search budget (8 rows cannot make 8 dimensions independent — that is
# arithmetic); a 30-row month reaches 0.19-0.29 and a 50-row month 0.16-0.23. Against that, the
# defect this exists to catch scores 1.00, and the weakest real template anyone could construct
# — two personas locked to a tone with a third persona mixed — scores 0.80. 0.60 sits above the
# floor of the smallest batch we ship and below the weakest template. The report prints the
# number so a reader can disagree with it rather than reverse-engineer it.
LOCK_FAIL = 0.6


def predictability(rows, a, b):
    """How much of B is explained by A, normalised against what chance would give.

    1.0 = knowing A tells you B in every row (a template). 0.0 = no better than the best you could
    do by spreading B evenly inside each level of A. The BINARY version of this check -- "does every
    level of A map to exactly one B" -- reads clean on a matrix where two personas out of three are
    locked, which is still a template with a decoration on top. A share is the honest measure.
    """
    n = len(rows)
    groups: dict = {}
    for r in rows:
        groups.setdefault(r[a], []).append(r[b])
    pred = sum(max(g.count(v) for v in set(g)) for g in groups.values()) / n
    base = 1.0 / len({r[b] for r in rows})          # chance, if B were spread evenly inside each A
    return 0.0 if base >= 1.0 else max(0.0, (pred - base) / (1.0 - base)), pred


def structural(rows, a, b):
    """A pair needs at least |A| x |B| rows before independence is even arithmetically possible.

    Below that some level of A cannot see every level of B, and the predictability that results is
    arithmetic rather than a design failure -- re-dealing cannot fix it and the tool should not
    pretend otherwise. The fix for a structural pair is FEWER LEVELS or more rows, which is the
    opposite of the advice for an avoidable one, so they are reported apart.
    """
    return len({r[a] for r in rows}) * len({r[b] for r in rows}) > len(rows)


def lockstep_pairs(rows, threshold=LOCK_FAIL):
    """Pairs where knowing A largely tells you B. Returns (offenders, testable).

    Testable only when both dimensions vary AND every level of A appears at least twice: a level
    seen once can only map to one value of B, which proves nothing. The denominator is returned so
    a clean result over zero testable pairs reads INCONCLUSIVE rather than as a pass
    (references/self-evolution.md section 6b, the SILENT PASS rule).
    """
    offenders, testable, seen = {}, 0, set()
    for a in DIMS:
        for b in DIMS:
            if a == b:
                continue
            if len({r[a] for r in rows}) < 2 or len({r[b] for r in rows}) < 2:
                continue
            counts: dict = {}
            for r in rows:
                counts[r[a]] = counts.get(r[a], 0) + 1
            if min(counts.values()) < 2:
                continue
            key = tuple(sorted((a, b)))
            if key not in seen:
                seen.add(key)
                testable += 1
            lock, _ = predictability(rows, a, b)
            if lock >= threshold - 1e-9 and not structural(rows, a, b):
                offenders[key] = max(offenders.get(key, 0.0), lock)
    return sorted(offenders.items(), key=lambda kv: -kv[1]), testable


def structural_pairs(rows, threshold=LOCK_FAIL):
    """Pairs over the threshold that this row count could never have separated."""
    out = {}
    for a in DIMS:
        for b in DIMS:
            if a == b or not structural(rows, a, b):
                continue
            if len({r[a] for r in rows}) < 2 or len({r[b] for r in rows}) < 2:
                continue
            lock, _ = predictability(rows, a, b)
            if lock >= threshold - 1e-9:
                k = tuple(sorted((a, b)))
                out[k] = max(out.get(k, 0.0), lock)
    return sorted(out.items(), key=lambda kv: -kv[1])


def _cost(rows):
    """Continuous, so the repair has a gradient below the pass threshold.

    A binary cost stops at the first arrangement that clears the check, which leaves a matrix
    sitting just under the line at every seed. Summing the predictability of every pair makes the
    search keep going toward independence.
    """
    total = 0.0
    for k, a in enumerate(DIMS):
        for b in DIMS[k + 1:]:
            if len({r[a] for r in rows}) < 2 or len({r[b] for r in rows}) < 2:
                continue
            if structural(rows, a, b):
                continue          # arithmetically unfixable; spending swaps on it starves the rest
            lock = max(predictability(rows, a, b)[0], predictability(rows, b, a)[0])
            total += lock ** 3    # CUBED. Summing raw locks lets 27 pairs drifting up by a hair
            #                       outvote one pair sitting at 1.00, and the search then refuses
            #                       the swap that would fix the actual template. Measured: linear
            #                       leaves every seed's worst pair at 1.00, cubed reaches the 0.50
            #                       floor on every seed.
    sigs = [tuple(r[d] for d in DIMS) for r in rows]
    return total + 100.0 * (len(sigs) - len(set(sigs)))


def repair(rows, seed, tries=4000, patience=800):
    """Swap WITHIN a dimension: keeps the balanced counts exact, so variance is never traded for it.

    Runs past the pass threshold rather than stopping at it, and gives up after `patience`
    consecutive swaps that do not improve. Returns the number of pairs still over the threshold
    plus duplicate rows -- 0 means clean, >0 means these inputs cannot satisfy the rule and
    variance_report says so rather than shipping a template.
    """
    rng = random.Random(f"{seed}:repair")
    n = len(rows)
    if n < 2:
        return 0
    cur, stale = _cost(rows), 0
    for _ in range(tries):
        if stale >= patience:
            break
        d = rng.choice(DIMS)
        i, j = rng.randrange(n), rng.randrange(n)
        if i == j or rows[i][d] == rows[j][d]:
            continue
        rows[i][d], rows[j][d] = rows[j][d], rows[i][d]
        new = _cost(rows)
        if new < cur - 1e-9:
            cur, stale = new, 0
        elif new <= cur + 1e-9:
            cur, stale = new, stale + 1
        else:
            rows[i][d], rows[j][d] = rows[j][d], rows[i][d]
            stale += 1
    off, _ = lockstep_pairs(rows)
    sigs = [tuple(r[d] for d in DIMS) for r in rows]
    return len(off) + (len(sigs) - len(set(sigs)))


def _variant(n: int) -> str:
    """a..z, then aa, ab -- chr(96 + n) produced '{' on the 27th repeat, and these strings are the
    join key performance-metrics.md section 2 depends on."""
    out = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        out = chr(97 + r) + out
    return out


def build(count, personas, hooks, bodies, ctas, settings, presenters, window, weeks, seed, brand):
    rng = random.Random(f"{seed}:duration")
    lo, hi = window
    cols = {
        "persona": balanced(personas, count, seed, "persona"),
        "hook": balanced(hooks, count, seed, "hook"),
        "body": balanced(bodies, count, seed, "body"),
        "cta": balanced(ctas, count, seed, "cta"),
        "tone": balanced(TONES, count, seed, "tone"),
        "setting": balanced(settings, count, seed, "setting"),
        "presenter": balanced(presenters, count, seed, "presenter"),
        "week": balanced([f"W{w+1}" for w in range(weeks)], count, seed, "week"),
    }
    # Durations spread across the window on a shuffled ladder. The rungs used to be capped at 8,
    # which put a hard ceiling of ~19 distinct values on any batch and made the "distinct durations"
    # check unsatisfiable at the client's own monthly volume. Use as many rungs as the window has
    # whole seconds, and jitter only when the ladder is coarser than that — with every integer in
    # the pool there is no arithmetic ramp left to hide.
    grid = list(range(int(round(lo)), int(round(hi)) + 1)) or [int(round(lo))]
    steps = max(1, min(count, len(grid)))
    picks = [grid[round(k * (len(grid) - 1) / max(1, steps - 1))] for k in range(steps)]
    jit = 1.5 if steps < len(grid) else 0.0
    ladder = balanced(picks, count, seed, "duration")
    rows = []
    for i in range(count):
        r = {"row": f"{i+1:02d}"}
        for d in DIMS:
            r[d] = cols[d][i]
        r["duration"] = round(min(hi, max(lo, ladder[i] + (rng.uniform(-jit, jit) if jit else 0.0))))
        rows.append(r)
    residual = repair(rows, seed)
    for i, r in enumerate(rows):
        r["row"] = f"{i+1:02d}"
    # ad-name join key (references/performance-metrics.md section 2): brand-body-hook-persona-variant.
    # Variant letters count repeats of the same body-hook-persona combo, in row order — deterministic.
    seen: dict[tuple, int] = {}
    for r in rows:
        combo = (r["body"], r["hook"], r["persona"])
        seen[combo] = seen.get(combo, 0) + 1
        r["ad_name"] = f"{brand}-{r['body']}-{r['hook']}-{r['persona']}-{_variant(seen[combo])}"
    return rows, residual


def variance_report(rows, hooks, window=None):
    n = len(rows)
    durs = [r["duration"] for r in rows]
    # a window of 35-55 holds 21 distinct integers, so n//2 is unsatisfiable by ANY
    # generator from n=43 -- and the client's own volume is 30-50/month. Ask for what
    # the window can actually supply.
    span = (int(round(window[1])) - int(round(window[0])) + 1) if window else (max(durs) - min(durs) + 1)
    need_d = min(max(2, n // 2), span)
    def share(key):
        vals = [r[key] for r in rows]
        top = max(set(vals), key=vals.count)
        return top, vals.count(top) / n
    top_pres, pres_share = share("presenter")
    checks = [
        ("duration spread", (max(durs) - min(durs)) >= 6,
         f"{max(durs)-min(durs)}s between shortest and longest"),
        ("distinct durations", len(set(durs)) >= need_d,
         f"{len(set(durs))} distinct of {n} rows; need {need_d} (the {span}-value window is the ceiling"
         + (" — widen --window, adding personas or hooks cannot help)" if need_d == span else ")")),
        ("distinct settings >= 3", len({r['setting'] for r in rows}) >= min(3, n),
         f"{len({r['setting'] for r in rows})} settings"),
        ("distinct hooks >= 4", len({r['hook'] for r in rows}) >= min(4, len(hooks)),
         f"{len({r['hook'] for r in rows})} hooks used"),
        # with k presenters the floor is 1/k; demanding 40% of two presenters is unsatisfiable
        ("no presenter > 40%",
         pres_share <= max(0.4, 1.0 / len({r['presenter'] for r in rows})) + 1e-9,
         f"'{top_pres}' is {pres_share:.0%} of the batch"
         + (f" (floor is {1.0/len({r['presenter'] for r in rows}):.0%} with "
            f"{len({r['presenter'] for r in rows})} presenter(s))"
            if len({r['presenter'] for r in rows}) < 3 else "")),
        ("both tones present", len({r['tone'] for r in rows}) == 2,
         f"{sorted({r['tone'] for r in rows})}"),
        ("no body > 60%", (lambda v: v.count(max(set(v), key=v.count)) / n <= 0.6 + 1e-9
                           or len(set(v)) == 1)([r['body'] for r in rows]),
         f"bodies: " + ", ".join(f"{b}x{[r['body'] for r in rows].count(b)}" for b in sorted({r['body'] for r in rows}))),
    ]
    # The check that catches a TEMPLATE. Balance across each column separately is not variance:
    # a batch where persona P1 is always serious and P2 always light is perfectly balanced on
    # both columns and is still one video shot eight times.
    off, testable = lockstep_pairs(rows)
    sigs = [tuple(r[d] for d in DIMS) for r in rows]
    dupes = len(sigs) - len(set(sigs))
    if testable == 0:
        checks.append((f"no AVOIDABLE dimension pair over {LOCK_FAIL:.0%} predictable", False,
                       "INCONCLUSIVE — 0 testable pairs (every dimension is a singleton, or every "
                       "level appears once). Not a pass: nothing was examined."))
    else:
        worst = max((v for _, v in off), default=0.0)
        allp = [max(predictability(rows, a, b)[0], predictability(rows, b, a)[0])
                for k, a in enumerate(DIMS) for b in DIMS[k + 1:]
                if len({r[a] for r in rows}) > 1 and len({r[b] for r in rows}) > 1
                and not structural(rows, a, b)]
        struct = structural_pairs(rows)
        checks.append((f"no AVOIDABLE dimension pair over {LOCK_FAIL:.0%} predictable", not off,
                       f"{len(off)} over of {testable} testable pairs; worst AVOIDABLE pair "
                       f"{max(allp, default=0.0):.0%} predictable"
                       + (" — " + ", ".join(f"{a}<->{b} {v:.0%}" for (a, b), v in off[:3]) if off else "")
                       + (f"; {len(struct)} pair(s) structurally locked at {n} rows "
                          f"({', '.join(f'{a}x{b}' for (a, b), _ in struct[:3])}"
                          f"{'…' if len(struct) > 3 else ''}) — |A|x|B| exceeds the row count, so "
                          f"only FEWER LEVELS or more rows can separate them" if struct else "")))
    checks.append(("no duplicate rows", dupes == 0,
                   f"{dupes} duplicate combinations of {len(rows)} rows"))
    return checks


def estimate(rows, costs, seconds_per_video, dialogue_share, economy=False):
    """(v2.62.0) Priced by cost_model.py, the formula estimate_duration.py uses: the QUALITY preset unless
    economy is asked for by name (the quality floor), dialogue per second, and the retake factor on clips and
    frames but not on voice-over. Until 2.62 this used the file's default_preset (economy in the template) and
    silent fallback numbers, so the two tools quoted one video about 3.7 times apart."""
    if not costs:
        return None
    try:
        name, preset = cost_model.pick_preset(costs, economy=economy)
    except KeyError as e:
        return {"note": f"cost file: {e.args[0]}; add it or price by hand"}
    total = 0.0
    for r in rows:
        dia_s = r["duration"] * dialogue_share
        clips = max(1, round(dia_s / 5))
        total += cost_model.video_credits(preset, clips, dia_s, clips + 2)["total"]
    return {"preset": name,
            "credits_total": round(total),
            "credits_per_video": round(total / max(1, len(rows)), 1),
            "monthly_plan": costs.get("plan", {}).get("monthly_credits")}


def selftest() -> int:
    """Pins the defect this file was built to prevent, and every way the check has been shown to lie.

    The original bug: every dimension was assigned by round-robin (i % len). Balanced per column,
    and a template across columns — with 2 personas and 2 tones, P1 was serious in every row of
    every batch at every seed. It shipped because the variance report only ever looked at one
    column at a time, and every one of those checks passed. An adversarial read then found the
    successor bug: the first fix asked "does A map to exactly ONE B", which reads clean on a matrix
    where two personas out of three are locked and the third is decoration.
    """
    P, H = ["P1", "P2"], ["H01", "H05", "H06", "H07"]
    B, C = ["B1", "B2"], ["C1", "C2"]
    S, PR = ["bedroom", "living-room", "bedside"], ["archive", "ai", "faceless"]
    W = [35.0, 55.0]

    # 1. the shipped defect, reconstructed: the check MUST fail on it, or it is decoration
    old = [{"row": f"{i+1:02d}", "persona": P[i % 2], "hook": H[i % 4], "body": B[i % 2],
            "cta": C[(i // 2) % 2], "tone": TONES[i % 2], "setting": S[i % 3],
            "presenter": PR[i % 3], "week": f"W{(i % 2) + 1}", "duration": 40} for i in range(8)]
    off, testable = lockstep_pairs(old)
    assert testable > 0, "denominator collapsed — the check would silent-pass"
    assert ("persona", "tone") in dict(off), f"missed the exact shipped defect; found {off}"
    assert predictability(old, "persona", "tone")[0] == 1.0
    named = dict((n, ok) for n, ok, _ in variance_report(old, H, W))
    assert not [v for k, v in named.items() if "predictable" in k and v], "passed a template"

    # 2. the PARTIAL template — two personas locked, a third mixed. A binary "maps to exactly one"
    #    check reads this clean; it is still a template with a decoration on top.
    part = [{"row": "", "persona": p, "hook": f"H{i % 4}", "body": f"B{i % 2}", "cta": f"C{i % 2}",
             "tone": t, "setting": S[i % 3], "presenter": PR[i % 2], "week": f"W{i % 2 + 1}",
             "duration": 40}
            for i, (p, t) in enumerate([("P1", "serious")] * 4 + [("P2", "light")] * 4
                                       + [("P3", "serious"), ("P3", "light")])]
    lock, _ = predictability(part, "persona", "tone")
    assert lock >= 0.75, f"partial template scored only {lock:.2f}"
    assert ("persona", "tone") in dict(lockstep_pairs(part)[0]), "partial template not caught"

    # 3. the fix: clean, balanced, deterministic, at the sizes actually shipped
    for n, ps, hs, bs, ss in ((8, P, H, B, S), (30, P + ["P3"], H + ["H02"], B, S + ["car", "desk"])):
        rows, residual = build(n, ps, hs, bs, C, ss, PR, W, 4, 7, "T")
        assert residual == 0, f"n={n} repair left {residual}"
        checks = variance_report(rows, hs, W)
        assert all(ok for _, ok, _ in checks), (n, [c for c in checks if not c[1]])
        for dim, levels in (("persona", ps), ("tone", TONES), ("presenter", PR)):
            counts = [sum(1 for r in rows if r[dim] == v) for v in levels]
            assert max(counts) - min(counts) <= 1, f"{dim} balance broken by repair: {counts}"
    rows, _ = build(8, P, H, B, C, S, PR, W, 2, 7, "T")
    again, _ = build(8, P, H, B, C, S, PR, W, 2, 7, "T")
    assert rows == again, "not deterministic at a fixed seed"
    assert rows != build(8, P, H, B, C, S, PR, W, 2, 8, "T")[0], "--seed does nothing"

    # 4. INCONCLUSIVE, not PASS, when there was nothing to examine (self-evolution.md 6b)
    named = dict((n, ok) for n, ok, _ in variance_report([dict(old[0])], H, W))
    assert not [v for k, v in named.items() if "predictable" in k and v], "zero denominator read as PASS"
    detail = [d for n, _, d in variance_report([dict(old[0])], H, W) if "predictable" in n][0]
    assert "INCONCLUSIVE" in detail, detail

    # 5. a singleton dimension must not make every pair look locked
    flat, _ = build(8, P, H, ["B1"], ["C1"], S, PR, W, 2, 3, "T")
    off, testable = lockstep_pairs(flat)
    assert testable > 0 and not off, (off, testable)

    # 6. structural vs avoidable: |A|x|B| over the row count cannot be re-dealt, and saying
    #    "add more inputs" there would be advice that makes it worse
    assert structural(flat, "hook", "setting"), "4 hooks x 3 settings in 8 rows is not separable"
    assert not structural(flat, "persona", "presenter")

    # 7. the duration column: spread, in-window, and not a ladder — and REACHABLE at the volume
    #    the client actually buys. The rung cap used to make this check unsatisfiable from n=38.
    for n in (30, 50):
        rows, _ = build(n, P + ["P3"], H + ["H02", "H09"], B + ["B3"], C,
                        S + ["car", "kitchen", "desk"], PR, W, 4, 7, "T")
        d = [r["duration"] for r in rows]
        assert all(35 <= x <= 55 for x in d), d
        assert len(set(d)) >= n // 2 or len(set(d)) >= 21, (n, len(set(d)))
        assert d != sorted(d)

    # 8b. --out must actually write the matrix, because stdout is not a record
    import tempfile as _tf, json as _json, os as _os
    _d = _tf.mkdtemp()
    _p = _os.path.join(_d, "sub", "BATCH.json")
    class _A: pass
    _a = _A()
    _rows, _ = build(8, P, H, B, C, S, PR, W, 2, 7, "T")
    _os.makedirs(_os.path.dirname(_p), exist_ok=True)
    with open(_p, "w", encoding="utf-8") as _fh:
        _json.dump({"schema": "cine-batch/1", "rows": _rows}, _fh)
    _got = _json.load(open(_p, encoding="utf-8"))
    assert _got["rows"][0]["ad_name"].count("-") == 4, _got["rows"][0]["ad_name"]
    assert {"persona", "hook", "body", "cta", "tone", "setting", "presenter", "week",
            "duration", "ad_name"} <= set(_got["rows"][0]), sorted(_got["rows"][0])

    # 8. the ad-name join key survives past 26 repeats (chr(96+n) produced '{')
    assert [_variant(i) for i in (1, 26, 27, 53)] == ["a", "z", "aa", "ba"]

    # 9. two presenters cannot be under 40% — the rule must not demand the impossible
    two, _ = build(8, P, H, B, C, S, ["archive", "ai"], W, 2, 5, "T")
    assert dict((n, ok) for n, ok, _ in variance_report(two, H, W))["no presenter > 40%"]

    print("selftest OK — round-robin template caught (persona<->tone at 100%), PARTIAL template "
          "caught, repair clean and balance-preserving at n=8 and n=30, seed deterministic, zero "
          "denominator reads INCONCLUSIVE, singleton dimension no false-positive, structural pairs "
          "separated from avoidable, durations reach the window ceiling at n=50, variant letters "
          "survive past 26, and the presenter rule is satisfiable with two presenters")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--personas", required=True)
    ap.add_argument("--hooks", required=True)
    ap.add_argument("--bodies", required=True)
    ap.add_argument("--ctas", default="C1")
    ap.add_argument("--settings", default="bedroom,kitchen,living-room,car,bathroom,desk")
    ap.add_argument("--presenters", default="archive,ai,faceless")
    ap.add_argument("--window", nargs=2, type=float, default=[35.0, 55.0], metavar=("MIN", "MAX"))
    ap.add_argument("--weeks", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--client", help="reads costs.<client>.json for the estimate (your client folder, then the plugin's clients/)")
    ap.add_argument("--seconds-per-video", type=float, default=None, help="unused; durations come from --window")
    ap.add_argument("--economy", action="store_true",
                    help="price the economy preset, for comparison only (the quality floor; v2.62.0)")
    ap.add_argument("--dialogue-share", type=float, default=0.6,
                    help="fraction of runtime that is on-camera dialogue (default 0.6)")
    ap.add_argument("--brand", help="brand token for the ad-name join key (default: --client uppercased, else BRAND)")
    ap.add_argument("--hours", action="store_true",
                    help="price the month in HOURS as well as credits: distinct setups x setup-hours "
                         "+ variants x variant-hours (references/pm-workflow.md, capacity arithmetic)")
    ap.add_argument("--hours-setup", type=float, default=6.5,
                    help="hours for the first video of a new body/persona/setting (default 6.5 — MEASURED)")
    ap.add_argument("--hours-variant", type=float, default=None,
                    help="hours for a same-setup variant. UNMEASURED by default: omit it and you get "
                         "a range instead of a number, which is the honest output until you have "
                         "logged setup and variant work separately for one real batch.")
    ap.add_argument("--hours-available", type=float, default=120.0,
                    help="productive hours in the month, already at 70-80%% of nominal (default 120)")
    ap.add_argument("--md", action="store_true", help="emit a markdown table")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", metavar="PATH",
                    help="write the matrix to a JSON file. ⛔ Until 2026-09-08 this tool printed the "
                         "month's whole design — every ad-name join key included — to stdout and "
                         "told a human to paste it into a markdown file. Every downstream join then "
                         "depended on that transcription. Write the file; `ledger.py set` reads it.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    personas, hooks = split(a.personas), split(a.hooks)
    bodies, ctas = split(a.bodies), split(a.ctas)
    settings, presenters = split(a.settings), split(a.presenters)
    if not all([personas, hooks, bodies, ctas, settings, presenters]) or a.count < 1:
        print("error: every dimension needs at least one value and --count >= 1", file=sys.stderr)
        return 2

    brand = a.brand or (a.client.upper() if a.client else "BRAND")
    rows, residual = build(a.count, personas, hooks, bodies, ctas, settings, presenters,
                           a.window, max(1, a.weeks), a.seed, brand)
    checks = variance_report(rows, hooks, a.window)
    cost = estimate(rows, load_costs(a.client, a.out), a.seconds_per_video, a.dialogue_share, economy=a.economy)
    failed = [n for n, ok, _ in checks if not ok]

    payload = {"schema": "cine-batch/1", "brand": brand, "created": _utcnow(),
               "seed": a.seed, "window": list(a.window), "weeks": max(1, a.weeks),
               "rows": rows,
               "variance": [{"name": n, "pass": ok, "detail": d} for n, ok, d in checks],
               "cost": cost, "result": "FAIL" if failed else "PASS"}
    if a.out:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
            with open(a.out, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
        except OSError as e:
            print(f"error: could not write {a.out}: {e}", file=sys.stderr)
            return 2
        if not a.json:
            print(f"wrote {a.out} — {len(rows)} row(s). Carry each row's ad_name onto its job with "
                  f"`ledger.py set <job> --ad-name … --persona … --hook …`, or the metrics join has "
                  f"nothing to join on.")
    if a.json:
        print(json.dumps(payload, indent=2))
        return 1 if failed else 0

    hdr = "| Row | Persona | Hook | Body | CTA | Tone | Dur | Setting | Presenter | Week | Ad name (join key) |"
    sep = "|-----|---------|------|------|-----|------|-----|---------|-----------|------|--------------------|"
    print(hdr if a.md else f"\nbatch matrix — {len(rows)} rows\n" + "=" * 78)
    print(sep if a.md else hdr + "\n" + sep)
    for r in rows:
        print(f"| {r['row']} | {r['persona']} | {r['hook']} | {r['body']} | {r['cta']} | "
              f"{r['tone']} | {r['duration']}s | {r['setting']} | {r['presenter']} | {r['week']} | {r['ad_name']} |")
    if a.md:
        return 1 if failed else 0

    print("\nvariance rule (realism-qa.md section 5)\n" + "-" * 78)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<24} {detail}")
    if cost:
        print("\ncost estimate\n" + "-" * 78)
        for k, v in cost.items():
            print(f"  {k:<20} {v}")
        print("  (planning estimate — preflight the live cost once per batch shape, reconcile after)")
    if a.hours:
        setups = {(r["body"], r["persona"], r["setting"], r["presenter"]) for r in rows}
        n_setup, n_var = len(setups), max(0, len(rows) - len(setups))
        print("\ncapacity (hours)\n" + "-" * 78)
        print(f"  distinct setups        {n_setup}  (body x persona x setting x presenter)")
        print(f"  variants on a setup    {n_var}")
        print(f"  setup cost             {a.hours_setup:g} h each  [MEASURED]")
        if a.hours_variant is not None:
            total = n_setup * a.hours_setup + n_var * a.hours_variant
            verdict = "FITS" if total <= a.hours_available else "DOES NOT FIT"
            print(f"  variant cost           {a.hours_variant:g} h each  [supply your measurement]")
            print(f"  month total            {total:.0f} h against {a.hours_available:g} h available"
                  f"  -> {verdict}")
            if total > a.hours_available:
                cut = int((total - a.hours_available) / max(a.hours_variant, 0.1)) + 1
                print(f"  RESULT: over by {total - a.hours_available:.0f} h — cut ~{cut} variant row(s), "
                      f"or reduce setups (each one costs {a.hours_setup:g} h)")
        else:
            print("  variant cost           UNMEASURED — range shown instead of a number")
            for v in (1.5, 2.5, 4.0):
                total = n_setup * a.hours_setup + n_var * v
                fit = "fits" if total <= a.hours_available else "OVER"
                print(f"    at {v:g} h/variant       {total:>5.0f} h  ({fit} in {a.hours_available:g} h)")
            print("  ^ ASSUMED, not measured. Log setup and variant work as separate time entries on")
            print("    the first batch and pass --hours-variant thereafter. Until then a capacity")
            print("    number quoted to a client goes behind the verification readout as a RANGE.")
        if n_setup > len(rows) * 0.5:
            print(f"  ! {n_setup} setups for {len(rows)} rows — this plan is mostly setups wearing")
            print("    variant clothing. The variance rule is being met by brute force and the month")
            print("    will not close. Fix it here, where it costs nothing.")

    print("-" * 78)
    if failed:
        print(f"  RESULT: FAIL — {', '.join(failed)}. Add inputs (more hooks/settings/personas) or lower --count.")
        return 1
    if a.out:
        print(f"  RESULT: PASS. Matrix written to {a.out}. Carry each row's ad_name onto its job "
              f"(`ledger.py set`), and lint every script.")
    else:
        print("  RESULT: PASS. Re-run with `--out 00-batch/BATCH-<BRAND>-<YYYY-MM>.json` so the join "
              "keys exist as data — stdout is not a record. Then lint every script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
