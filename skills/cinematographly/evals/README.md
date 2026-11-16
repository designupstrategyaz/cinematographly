# evals/

The behavioural eval cases (`claude plugin eval`, testing whether an agent handed this skill follows its process)
are development material and are not part of the public release.

What ships, and runs in `run_tests.py`:

- `scripts/test_preproduction.py` — the whole pre-production stage walked through the real command-line tools,
  asserting a refusal at every point. No network, no credits.
- `scripts/eval_lint.py` — checks eval cases statically, if you write your own (`claude plugin eval` looks for
  them in an `evals/` folder at the plugin root).
