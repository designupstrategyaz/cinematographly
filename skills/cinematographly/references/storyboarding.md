# Storyboarding: see the film before paying for it

**Stage 3, and the start-frame sheet in stage 5** (version 2.66.0). Read this when the shot list exists and before
any paid picture. It owns: asking for the person's own pictures, the storyboard page, the animatic, the two picture
sign-offs (`storyboard` and `startframes`), and what is still not measured.

**Why it exists.** A 2026-11-14 review of the plugin (Grok 4.7 and Sonnet 5.5, five lead roles each) found that stage
3 showed a shot list and a shot board and asked the person for nothing. The first time anyone saw the film as
pictures in time was the first paid clip. Both reviewers ranked this second, after "the person meets the work too
late" (fixed in 2.65.0 by `ideation.md` §0).

---

## §1. Reject at the cheapest stage

The order of cost is fixed: a drawing, then a timed reel of drawings, then a still, then video. Vendor list prices
put a still one to two orders of magnitude below a second of video (R3 C5, vendor pages, 2026-11). Every change made
on a panel is free. The same change made after the clips costs every clip it touches.

Professional practice is staged the same way:
- **Boards for the pitch and boards for production are different documents.** A pitch board has a few polished
  frames so a client grasps the idea. A production board carries every shot, with its framing, camera, movement,
  screen direction and continuity. Wikipedia's storyboard-artist article, citing John Hart, *The Art of the
  Storyboard* (2nd ed., 2013), describes it this way; the book itself was not opened.
- **The timed reel is the working deliverable.** Story reels with rough timing and scratch sound are what board
  artists hand over, and sequences are recut from them (The Animation Guild, "Board Artists").
- **Feedback comes before scouting and casting,** because changes are easiest on the board (Boords, "How to storyboard
  a TV commercial", 2026-10-18).

Approved stills then become the start frames and references for generation. Every vendor guide that was opened
agrees that identity is locked by reference images, never by description (R3 C1).

## §2. Ask for their pictures first

Before the storyboard page is built, ask the person for **a sketch or a phone photo for the three to five shots that
carry the film**. Stick figures are fine; the point is their composition, not their drawing.

- **Why.** Material that starts from the person's own idea keeps the work varied and keeps it theirs. An AI that
  shows its own examples first fixes people on those examples (Wadinambiarachchi et al., CHI 2024). The same finding
  drives `ideation.md` §0.
- **How to ask.** One question, with the shots named: "For S1-C1, S2B and the CTA, could you sketch or photograph
  how you see them? Rough is perfect."
- **Never redraw theirs.** Their sketch goes on the panel as it is. Where their composition cannot be generated as
  drawn, say what would change and why, and let them choose.
- **Their idea is always one of the options.** When start-frame options are proposed for a shot they sketched, one
  option follows their composition.
- **A skip is recorded in their words.** If they would rather not draw, write `skipped: "<what they said>"`.

In the shot list:
```
## Their sketches
- S1-C1: 01-script/storyboard/their/hands.jpg: "like my gran's hands"
- CTA: 01-script/storyboard/their/door.jpg
```
or `skipped: "<their words>"`. `gate.py approve storyboard` refuses while there is neither a sketch of theirs on a
real shot nor a quoted skip.

## §3. The storyboard page

`board.py storyboard <job>` writes `01-script/BOARD-storyboard.html`: one panel per shot, in cut order, read from the
shot list (the Sequence chain gives order, size, move, seconds and energy; the shot table gives the line and the
action).

Each panel carries:
- the picture: their sketch first, then a drawing or blocking frame saved as `01-script/storyboard/<SHOT>.png`
  (or `.jpg`, `.webp`), otherwise a drawn placeholder that shows the shot size;
- the shot, its size, move, seconds and energy;
- the line it carries, in quotation marks;
- what happens in it, and what changes (the Turn column);
- who or what the shot looks at.

The film's **energy curve** runs along the top: one point per shot at its middle, a line at every cut, plotted over
the real running time (`sequence-grammar.md` §2d plans energy like music). A long flat stretch, or a peak in the
wrong place, is visible here in a way no table shows.

Boords and StudioBinder add direction arrows and line-of-action notes on each panel. Draw those on the drawing when
the shot needs them; `sequence_lint.py` checks the chain's direction rules.

## §4. The animatic

`animatic.py <job>` writes `01-script/ANIMATIC.mp4`: each panel held for its planned seconds, with a band giving the
shot, size, move, seconds and line. It is free and local (Pillow and ffmpeg).

- **Mute by default.** `--voice <file>` lays a scratch read under it: the person's own phone recording, or a free
  system voice (on a Mac, `say -o scratch.aiff -f lines.txt`). ⛔ Never a paid voice. A scratch track that costs
  money is a voice approval in disguise, and voice is signed at stage 6.
- **Watch it once at speed, with the person.** Look for:
  - a shot too short to read, above all one with text in it;
  - a hold with nothing happening in it (`direction.md` §2b: if the start and the end of a shot are the same, the
    shot is dead);
  - a line that cannot be said in its shot's seconds;
  - the energy you planned not being the energy you feel.
- **Fix it in the shot list, rebuild, watch again.** Both the page and the reel record the shot list they were built
  from, and the sign-off refuses a stale one.

## §5. Sign the start frames side by side

Start frames are approved one at a time (`gate.py approve frame:<SHOT>`). One at a time, each looks fine. Side by
side, a face that drifts, a key light that changes side or a colour that wanders is plain. Image-to-video models
lose identity as errors build up across frames (R3 C2: ConsID-Gen, CVPR 2026, abstract only), so a drift in a start
frame becomes a drift in every clip made from it.

`board.py frames <job>` writes `01-script/BOARD-frames.html`: every approved start frame in cut order, with the
shots still missing a frame named at the top. Show it, then `gate.py approve startframes`. A frame approved after
the sheet was signed, such as a retake, needs the sheet rebuilt and signed again before its clip.

Shots built from reference sheets instead of a start frame (`form: scene`, `character-and-props.md` §8.3g) have no
frame to sheet. Their sheets were approved at stage 4.

## §6. What the gate checks

The two sign-offs are part of the chain for jobs whose `00-brief/DEVELOPMENT.md` was made from the 2.65 template or
later (the line `develop-template: 2.65`). A job already in production when this version is installed keeps its old
chain, and `gate.py status` does not name them.

| Sign-off | Comes after | Blocks until signed | Refused while |
|---|---|---|---|
| `storyboard` | `script` | every paid image or video; `cast`, every sheet and frame approval, `clips` | the shot list is missing or has a `<NEEDS DIRECTION>` field; a shot has no seconds; no sketch of theirs and no quoted skip; the page or the animatic is missing or was built from a different shot list |
| `startframes` | `storyboard`, the frames themselves | each clip, until a sheet is signed after its frame | no frame is approved; the sheet is missing or shows a different set of approved frames |

The signed thing is fixed by the gate, not chosen: `storyboard` records the shot list, `startframes` records the
sheet. Editing a blocking card or a performance card does not unsign the storyboard. Changing a shot, its order,
size, move, seconds or line does, because that is a different film.

`storyboard.py <job>` lists what `approve storyboard` still needs.

## §7. What is not measured

- **No one has published a keep rate.** No studio or creator log of takes per approved shot was found. "Three takes
  per shot" appears in every guide, and none measured it (R3 C4). Quote it as ASSUMED, and log your own takes per
  approved shot from the first job: that log is the only real number available.
- **Fixing a seed and prompt length** are folklore for consistency: no test was found (R3 C3).
- **The creativity studies** behind §2 use short text and image tasks, not video storyboards.
- **The books** (Hart; Katz, *Film Directing Shot by Shot*; Paez and Jew, *Professional Storyboarding*) are named
  from secondary sources and were not opened. What they say about commercial sign-off is not established here.

The R3 tags refer to the review's storyboarding research note (24 sources, each marked opened, search-only or
refused), which is kept with the review outside the plugin.
