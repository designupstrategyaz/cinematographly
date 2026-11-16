#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
reconcile_costs.py — check a project's cost ledger against ACTUAL settled Higgsfield charges,
instead of trusting the `get_cost` preflight numbers the ledger was probably built from. Real
case on this account: a ledger read 207.35 credits logged; the actual settled total (summed from
`transactions` and cross-checked against the `balance` delta) was 191.90 — a 15.45cr overstatement
from preflight/settled drift on a couple of line items. This script automates the tedious, easy-
to-get-wrong part of catching that: summing a transaction list and diffing it against the ledger
and (optionally) a balance delta. It deliberately does NOT try to auto-attribute the difference to
one ledger line item vs another — that step needs a human reading both lists side by side, exactly
like the write-up in 99-costs/COSTS-<SLUG>.md's reconciliation section did.

This script has no network access and does not call the Higgsfield API itself — Claude fetches the
live data via the `mcp__Higgsfield__transactions` (and optionally `balance`) MCP tools, saves the
relevant slice to a JSON file, and hands it to this script. Keeping the live fetch and the
arithmetic separate means the arithmetic is fully testable offline.

Usage:
  python3 reconcile_costs.py --transactions transactions.json --ledger-total 207.35
  python3 reconcile_costs.py --transactions transactions.json --ledger-total 207.35 \\
      --balance-before 2654.66 --balance-after 2462.76

  --transactions   a JSON file: either a bare list of transaction objects, or an object with the
                    list under a "transactions"/"data"/"items" key (all three are tried). Each
                    transaction is expected to carry an amount under one of: amount, credits, cost,
                    credit_cost, value (first one found wins — printed so you can sanity-check it
                    picked the right field). Pre-filter the export to just the run/date-range being
                    reconciled before saving it — this script sums EVERYTHING it's given.
  --ledger-total    the running total currently logged in 99-costs/COSTS-<SLUG>.md for that range.
  --balance-before / --balance-after   optional — if both are given, checks that
                    (before - after) matches the summed transactions (catches a wrong sign
                    convention or a missing transaction in the export, same sanity check used to
                    verify the manual reconciliation this script replaces).
"""
import argparse
import json
import sys

AMOUNT_KEYS = ("amount", "credits", "cost", "credit_cost", "value")
LIST_KEYS = ("transactions", "data", "items")


def load_transactions(path):
    raw = json.load(open(path, encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    for k in LIST_KEYS:
        if isinstance(raw, dict) and isinstance(raw.get(k), list):
            return raw[k]
    raise SystemExit(f"Could not find a transaction list in {path} — expected a bare list or an "
                      f"object with one of {LIST_KEYS} holding the list.")


def extract_amount(tx, forced_key=None):
    if forced_key:
        if forced_key not in tx:
            raise SystemExit(f"--amount-key {forced_key!r} not found in transaction: {tx}")
        return float(tx[forced_key]), forced_key
    for k in AMOUNT_KEYS:
        if k in tx and tx[k] is not None:
            try:
                return float(tx[k]), k
            except (TypeError, ValueError):
                continue
    raise SystemExit(f"No usable amount field found in transaction (tried {AMOUNT_KEYS}): {tx}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transactions", required=True, help="JSON export of the transactions to reconcile")
    ap.add_argument("--ledger-total", type=float, required=True, help="the ledger's currently-logged total for this range")
    ap.add_argument("--amount-key", help="force which field holds the credit amount (skip auto-detection)")
    ap.add_argument("--balance-before", type=float, default=None)
    ap.add_argument("--balance-after", type=float, default=None)
    ap.add_argument("--sanity-tolerance", type=float, default=0.05, help="allowed drift for the balance-delta sanity check")
    a = ap.parse_args()

    txs = load_transactions(a.transactions)
    if not txs:
        raise SystemExit("Transaction list is empty — nothing to reconcile.")

    amounts, key_used = [], None
    for tx in txs:
        amt, key_used = extract_amount(tx, a.amount_key)
        amounts.append(abs(amt))  # ledger totals are logged as positive credit-spend

    actual_total = sum(amounts)

    print(f"Read {len(txs)} transaction(s) from {a.transactions} (amount field: '{key_used}')")
    print(f"Actual settled total:  {actual_total:.2f} credits")
    print(f"Ledger logged total:   {a.ledger_total:.2f} credits")
    delta = actual_total - a.ledger_total
    pct = (delta / a.ledger_total * 100) if a.ledger_total else float("nan")
    direction = "UNDER-stated (actual > ledger)" if delta > 0 else "OVER-stated (ledger > actual)" if delta < 0 else "exact match"
    print(f"Delta:                 {delta:+.2f} credits ({pct:+.1f}%) — ledger is {direction}")

    if a.balance_before is not None and a.balance_after is not None:
        balance_delta = a.balance_before - a.balance_after
        print(f"\nBalance sanity check: {a.balance_before:.2f} -> {a.balance_after:.2f} "
              f"= {balance_delta:.2f} credits spent")
        drift = abs(balance_delta - actual_total)
        if drift <= a.sanity_tolerance:
            print(f"  OK — matches the summed transactions (drift {drift:.2f}).")
        else:
            print(f"  ! MISMATCH — balance delta and summed transactions differ by {drift:.2f} "
                  f"credits. The --transactions export is likely missing entries, includes "
                  f"entries outside this range, or a sign convention is off. Don't trust the "
                  f"reconciliation above until this is resolved.")

    if abs(delta) < 0.01:
        print("\nLedger matches settled charges — nothing to fix.")
    else:
        print(f"\nUpdate the ledger's running total to {actual_total:.2f} and note the correction "
              f"(see COSTS-<SLUG>.md's existing reconciliation section for the write-up format). "
              f"This script doesn't attribute the {abs(delta):.2f}cr difference to a specific line "
              f"item — compare the transaction list against the ledger's per-item breakdown by eye.")

    sys.exit(0 if abs(delta) < 0.01 else 1)


if __name__ == "__main__":
    main()
