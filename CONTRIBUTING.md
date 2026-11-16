# Contributing

Thank you for helping. Cinematographly is source-available under the Cinematographly Studio License 1.1
(`LICENSE`), so contributions work a little differently from an open-source project.

## Reporting a problem

Open an issue on GitHub with: what you asked for, what happened, what you expected, the output of
`/cinematographly:doctor`, and the app you use it in (Claude Code, Claude, Cursor or ChatGPT) with its version. Leave out client names, keys and anything private.
A way past the spend gate is a security issue: see `SECURITY.md` instead of opening an issue.

Final Cut Pro and Premiere Pro imports are not tested on our machines. A short report of what came through
(clips, handles, voice-over, markers, any one-frame slip) is especially welcome.

## Sending a change

1. Run the tests: `python3 skills/cinematographly/scripts/run_tests.py` (and `claude plugin validate --strict .`).
2. Every new script starts with the two licence header lines the other scripts carry; the build refuses a
   script without them.
3. Keep changes small and say why in the pull request.

## The licence for your contribution

By sending a contribution (a pull request, a patch, or code in an issue) you confirm that you wrote it or have
the right to grant the rights below, and that if an employer or client owns your work, they have authorised this
grant. You grant Design UpStrategy AZ LLC a perpetual, worldwide, non-exclusive, royalty-free, irrevocable
licence to use, copy, change, distribute, sublicense, and relicense the contribution, including under commercial
licences, and a licence under any patent you can license that the contribution alone necessarily infringes. You
keep the copyright. The contribution is provided as it is, with no warranty. Adding this line to each commit
records your agreement:

    Signed-off-by: Your Name <you@example.com>

Contributions without the sign-off cannot be merged.

## Maintainers: the publish manifest

`.cinematographly-publish.json` lists the files the last release shipped. The release tool uses it to delete
only files it shipped before; leave it in place.
