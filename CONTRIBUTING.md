# Contributing

Thank you for helping. Cinematographly is source-available under the Cinematographly Studio License 1.0
(`LICENSE`), so contributions work a little differently from an open-source project.

## Reporting a problem

Open an issue on GitHub with: what you asked for, what happened, what you expected, the output of
`/cinematographly:doctor`, and your Claude Code version. Leave out client names, keys and anything private.
A way past the spend gate is a security issue: see `SECURITY.md` instead of opening an issue.

Final Cut Pro and Premiere Pro imports are not tested on our machines. A short report of what came through
(clips, handles, voice-over, markers, any one-frame slip) is especially welcome.

## Sending a change

1. Run the tests: `python3 skills/cinematographly/scripts/run_tests.py` (and `claude plugin validate --strict .`).
2. Every new script starts with the two licence header lines the other scripts carry; the build refuses a
   script without them.
3. Keep changes small and say why in the pull request.

## The licence for your contribution

By sending a contribution (a pull request, a patch or code in an issue) you confirm that you wrote it or have
the right to give it, and you grant Design UpStrategy AZ LLC a perpetual, worldwide, non-exclusive,
royalty-free, irrevocable licence to use, copy, change, distribute, sublicense and relicense it, including
under commercial licences. You keep the copyright in your contribution. Adding this line to each commit is
your agreement to this grant:

    Signed-off-by: Your Name <you@example.com>

Contributions without the sign-off cannot be merged.

## Maintainers: the publish manifest

`.cinematographly-publish.json` lists the files the last release shipped. The release tool uses it to delete
only files it shipped before; leave it in place.
