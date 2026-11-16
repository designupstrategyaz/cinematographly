# Script Craft — writing for the ear, and testing whether it worked

`script-format.md` is the shape a script takes. `craft-cheatsheet.md` is the story logic under it.
**This file is the writing itself** — the sentence-level craft of lines that will be *spoken*, and
the self-test that tells you whether they're any good before you spend a credit on them.

It exists because the skill had a production engine and no writing engine. A perfectly generated,
perfectly graded, perfectly compliant video of a mediocre script is a mediocre video.

§§2b–2c add the layer directly under the line — how a single beat turns, and which parts of the
screenwriting canon survive at 40 seconds and which actively damage it.

---

## 0. Your studio's own writing system — optional

If your studio already has a prose writing system (a voice profile per client, an anti-AI-pattern list, a
scoring discipline, a lexical scanner), use it alongside this file: load the client's voice profile before
the first draft and run your scanner on the finished script. Nothing here depends on one — every rule this
skill needs is written into this file and §§2–7 below.

**What a prose system does *not* cover, which is most of what this skill writes:**

- **Character dialogue** — two people talking to each other, where each line has to *react* to the
  last one: turn-taking, subtext, interruption.
- **UGC first-person monologue** — a person talking to a phone, mid-thought, with disfluency as a
  feature rather than a defect. Prose discipline actively fights this: it strips the "um," the
  false start and the self-correction that make it read as real.

So: **a prose system for what transfers, this file for what doesn't, and be explicit about which is which.**

**Where common prose rules do NOT transfer to spoken lines:**

| Prose rule | What happens in speech |
|---|---|
| Vary sentence length for burstiness | Still true, but the unit is the **breath**, not the word count — and the variance is heard as rhythm, not seen as texture |
| Remove filler and hedging | **Partly inverted for UGC.** Real speech hedges. "I don't know if it's just me but—" is a credibility signal on camera and a defect on a page |
| Contractions where natural | **Contractions are near-mandatory.** An uncontracted line reads as a written line being performed |
| Avoid repetition | Speech repeats. Real people restate, circle back, and say the same thing twice with different words |
| Em-dashes are a tell | Irrelevant in speech — but relevant again in **captions**, which are read |

**And the reverse: prose rules that get *stricter* in speech.** No compound sentences. No subordinate
clause the listener has to hold open. One idea per line. The listener cannot re-read, so anything
that requires holding two things at once is simply lost.

## 1. The master test: read it aloud

**Every line gets said out loud before it is approved.** Not scanned, not "read in your head" — out
loud, at delivery pace. This is the single highest-yield gate in the whole writing process and it
costs nothing.

What you are listening for:

- **A stumble.** If you trip, the actor trips, the TTS mangles it, and the viewer notices. Rewrite —
  don't practise until you can say it.
- **A breath you can't take.** If the line needs a breath in the middle, it is two lines or it is
  too long.
- **A stress peak that lands on the wrong word.** Say it and hear which word carries the emphasis.
  If it isn't the word the line is about, restructure so it is — usually by moving it later.
- **A written rhythm.** Perfectly balanced clauses, parallel construction, a triplet — these read
  well and *sound* composed. Composed is the opposite of spoken.
- **A line that lands too early.** [PRIMARY · Tom Pope, *Good Scripts, Bad Scripts* — via a local
  extraction, read 2026-08-28] Pope's "less is more": Rick and Ilsa speak six times in the whole of
  *Casablanca*, and the rationing is what holds the tension. The 40-second version is a line that
  answers the hook's question at 0:12 instead of 0:35. You hear it as a slump — the rest of the
  script suddenly has nothing left to be about.

**Beside it, the buy test — before the script goes for approval.** Two questions, in this order:
*can you say what happens in the middle of the service or product — what the buyer actually gets?*
and *would you pay for it on the strength of this draft?* A no to either is a question for the
client, not another draft: the missing thing is information the writer does not have. It does not
lower `develop.py`'s three-draft minimum; it decides what the next step is. [PRACTITIONER · course notes]

## 2. Speakability mechanics

- **The unit is the breath, not the word.** "10–15 words" is a proxy for "one comfortable breath with
  one stress peak." A 16-word line with a simple shape says fine; an 11-word line with three
  consonant clusters does not.
- **Front-load the subject.** The listener has no re-read. Say who and what first, qualify after.
  "We handle the paperwork — all of it" beats "All of the paperwork is something we handle."
- **One idea per line.** Two ideas in one line means the second is lost.
- **Kill subordinate clauses.** Anything the listener has to hold open while you finish is gone by
  the time you close it. Split into two lines.
- **Watch consonant clusters and sibilant runs.** Three /s/ sounds in six words is a tongue-twister
  in any language. This is the most common cause of a stumble.
- **Numbers, acronyms and units are pronunciation decisions, not text.** Write them the way they will
  be *said*, or the TTS will guess: "2026" as two thousand twenty-six or twenty twenty-six; "CAEN 01"
  as letters or a word; "€50,000" with the currency before or after. Decide, write it explicitly,
  and keep the display form in the caption.
- **Diacritics are load-bearing for TTS.** In Romanian a missing `ș` or `ț` changes the word the model
  says. The locked-script rule and the caption rule both depend on the text being right.
- **On the native-audio path (Path B, `ai-generation.md` Step 4)** the pronunciation controls above
  move from the text into QA: you cannot pre-spell what the model will say, so the **verbatim word
  check** (listen against the script — brand names, numbers, the CTA) replaces them. Write Path B
  lines *more* conservatively: simple words, no homographs, digits written out.
- **Homographs need disambiguation.** A word with two pronunciations will be read wrong roughly half
  the time; rephrase rather than hope.

## 2b. Below the line — the beat, the turn, and the chain

`craft-cheatsheet.md` §1 states the rules ("every scene turns a value") and `script-format.md` sets
the timing plan they live in. **This section is how you build one turn and how you test it** when a
"scene" is a single 8–12 second clip carrying one spoken line — which is the only unit this skill
ever actually writes.

*Provenance for §§2b–2c and the citations added through the rest of this file: six screenwriting
books, read here through local extractions rather than through the books themselves. Tagged
`[PRIMARY]` where the extraction worked from the full text with quoted passages and line or page
markers (Cowgill, Pope, Rubie & Provost), and `[SECONDARY]` where it is paraphrase, partial, or
partly reconstructed — McKee, whose source PDF was a scan, OCR'd in samples and completed from the
book's canonical framework set; Cooper & Dancyger, front matter and Part I only; Dancyger & Rush,
full depth but no quoted text. The tag rates how well the claim is grounded, not how good the book
is.*

- **The beat is the line.** [SECONDARY · Robert McKee, *Story* — via a local extraction, read
  2026-08-28] McKee's hierarchy runs beat → scene → sequence → act → story, where a beat is one
  exchange of action and reaction and a scene is the smallest unit that turns a value. **At 40
  seconds you have beats and one scene-sized whole, and nothing above that.** That is not a
  limitation to work around; it is why the bottom of his hierarchy is the only part worth importing
  and the rest is §2c's problem.
- **A turn has three parts and the third one has no words.** [PRIMARY · Linda Cowgill, *The Art of
  Plotting* — via a local extraction, read 2026-08-28] Her "plotted point" is set-up + climax +
  **reaction**; a turning point that skips the reaction registers as information rather than as
  change. The house failure is exactly this — the line that flips the value gets written, the
  half-second on the face afterwards does not, because it has no dialogue and therefore no row in
  the script. Write it as a silent beat (§3) and give it time in the shotlist.
  `script-format.md`'s "value-turn as a visual reaction" is the same instruction from the format
  side.
- **The over-plotting law — the single most useful import in this section.** [PRIMARY · Cowgill]
  *"When you overplot in terms of action, you underplot in terms of character and emotion."* Every
  extra thing that happens costs the seconds that would have shown what any of it did to anyone. In
  a 40-second ad the "action" is usually product points: three benefits fit, none of them gets a
  reaction, and the script is busy and flat at the same time. **Count the claims and cut one to buy
  the reaction beat.** This is the Rule of One (`persuasion-psychology.md` §2) arriving from the
  craft side rather than the persuasion side, which is a reason to trust it more, not less.
- **The gap: what they expected against what they got.** [SECONDARY · McKee] His central mechanism
  is the split between the result a character expects from an action and the result the world
  actually returns. Per line the test is two columns — *expected* / *got*. A line where the two
  match is dead air even when the information is true and the delivery is good. For this skill the
  gap is usually pre-loaded by the category: the viewer expects a catch, and the script's job is to
  open that gap honestly rather than to deny it exists.
- **Causality, not chronology — and it is testable in thirty seconds.** [PRIMARY · Cowgill;
  PRIMARY · Pope] Cowgill's causality is A causes B causes C, not A then B then C, and her rewrite
  of the familiar advice is **"dramatize, don't tell"** — showing a character do disconnected things
  reveals nothing at all. Pope's narrative inevitability is the same claim from the other end: each
  unit's resolution creates the next unit's problem, so no unit can be removed without the whole
  losing coherence. **The test: shuffle the middle lines.** If the script still reads, the lines are
  a list with a voice on it. This is the monologue counterpart to §3's reactivity test, and it is
  now dimension 5 of the scorecard (reactivity and its monologue form, §6).
- **Label every line NEW or EXPAND.** [PRIMARY · Pope] He goes through the whole of *Network*
  marking each scene as introducing a new problem or expanding an existing one, and treats a scene
  that does neither as dead air. It is the most mechanical test in any of these six books and it
  costs about a minute on a nine-line script. **Anything marked "neither" is the first cut** — and
  at 40 seconds you will usually find one, because the line that exists only to set up another line
  is the hardest one to see when you were the person who wrote it.
- **The narrative question goes in the first beat of the unit, not the last.** [PRIMARY · Peter
  Rubie & Gary Provost, *How to Tell a Story* — via a local extraction, read 2026-08-28] Their
  before-and-after: a boy undressing quietly is nothing; move "he hoped his brother wouldn't wake
  and beat him" to the *front* of the same paragraph and every floorboard creak becomes
  load-bearing. Nothing changed but the position of the question. This is the mechanism under the
  curiosity-gap hook (`persuasion-psychology.md` §3) and it supplies the part that file leaves
  implicit — **where** the question goes. It applies inside the body too: a mid-script line that is
  going to matter needs its question already installed.
- **Tell the viewer before you tell the character.** [PRIMARY · Cowgill] Her suspense chapter is
  Hitchcock's: the audience knowing about the bomb under the table is worth more than the bang. A
  single-voice ad has only one character, so the form that survives is **state the consequence,
  withhold the cause** — which is why the curiosity gap is the most-reached-for hook type in
  `modes/ugc-volume.md` §5. Note that this shape puts the consequence *in the text*: the consequence
  is the concrete anchor, the cause is the withheld term — exactly the balance the field evidence
  supports (`hook-craft.md` §1). **A "curiosity gap" that withholds the consequence as well is not
  this move**; it is the vague end of the curve, and it tests worse. Cowgill supplies the reason it
  works, and a reason is what makes a move adaptable rather than merely copyable.
- **Exposition rides on friction.** [PRIMARY · Pope; PRIMARY · Cowgill] Pope's "sweetener": Gittes
  learns where the water goes from a boy on a swaybacked horse rather than from a document, because
  the odd image is what lets the fact through unnoticed. Cowgill's version is to bicker while you
  inform. The facts a promo has to land — price, deadline, code, guarantee — are exposition, and a
  flat statement of them is the most skippable thing in the script. Route each one through the
  speaker's surprise, irritation or disbelief: *"they actually let me keep it for thirty days"* does
  the work of *"there's a thirty-day guarantee"* and sounds like a person while doing it.

**Where these six books disagree — kept, not smoothed.**

- **Cooper & Dancyger against this skill's main format.** [SECONDARY · Patricia Cooper & Ken
  Dancyger, *Writing the Short Film* — via a local extraction, read 2026-08-28] The most on-point
  book in the set says the defining constraint of short form is that **images carry the story and
  dialogue is the smallest layer**: cut dialogue ruthlessly, and if an image can carry the
  information the line is wasted screen time. A UGC monologue is 40 seconds of a person talking with
  no cutaway. **Both survive, on different formats.** For the skit they are simply right, and
  `craft-cheatsheet.md` §1 already carries it. For the monologue the rule inverts at the surface and
  holds underneath: the image *is* the face, the visual events are the hesitation and the look away,
  and their actual reason — *screen time spent on words the picture could carry is wasted* — is
  what tells you which words to keep. In a monologue the picture is a face, so the words worth
  keeping are the ones a face cannot say: the number, the name, the admission.
- **Cowgill against Dancyger & Rush on the passive speaker, and this one is live.** Cowgill treats
  a protagonist things merely happen to as a defect to be provoked into action. Dancyger & Rush
  treat it as a legitimate design with its own toolkit [SECONDARY · Ken Dancyger & Jeff Rush,
  *Alternative Scriptwriting* — via a local extraction, read 2026-08-28]: subtext over text, small
  action over dialogue, the surrounding characters carrying the plot. **The UGC speaker is passive
  by construction** — they did not act, something happened to them and they are reporting it.
  Applying Cowgill's fix produces "so I decided to take control of it", which is precisely the
  register that reads as an ad. **This file sides with Dancyger & Rush for the monologue and with
  Cowgill for the skit**, where a character who wants nothing genuinely has no scene to be in.
- **Dancyger against Dancyger, worth knowing before you quote either.** *Writing the Short Film*
  calls the compressed three act (20/60/20) the default that works most reliably in short form.
  *Alternative Scriptwriting*, with Rush, calls the restorative three act a convention that distorts
  any story that is not restorative, protagonist-driven and plot-dominant. Run their own three-part
  test on a 40-second ad: restorative — partly; protagonist-driven — usually not; plot-dominant —
  no. **Two of three answers are "no", which by their own rule means three-act will distort it.**
  The later book wins here and §2c follows it.
- **Pope's rationing against Cowgill's reaction beat.** Pope: withhold, keep the principals apart,
  cut anything that releases tension early. Cowgill: every action needs its reaction plotted or the
  audience learns nothing from it. At 40 seconds the two bid for the same seconds and nothing in
  either book settles it. **The working split, which is a judgement and not a finding:** spend the
  reaction beat once, at the turn, and follow Pope everywhere else.

## 2c. What does not transfer from feature screenwriting to a 40-second ad

Naming the inapplicable is worth as much as importing the applicable, because the failure mode is
specific and recurring: someone reads a screenwriting book, brings back three-act structure, and
spends eight seconds of a forty-second ad on a first act. **These books were written for 90–120
minutes, for an audience who chose the film and will sit through a slow opening, and for a form
whose smallest structural unit — a scene — runs two to four minutes.** A 35–55 second single-voice
ad has one scene's worth of runtime in total, one character, no act breaks, and a viewer who did not
choose it and is deciding inside the first second.

**The rule that sorts almost all of it: feature craft transfers downward, not upward.** Everything
at or below the beat and the scene — the gap, the value turn, subtext, causality, the reaction, the
strength of the opposition, exposition through friction — is directly usable, because those
mechanisms operate on a timescale the format actually has. Everything above the scene — act,
sequence, segment, subplot, arc — is not, because the format has no room for a second of anything.

| Feature concept | Why it does not transfer | What does the job here |
|---|---|---|
| Three-act structure and act breaks (McKee, Pope; Cooper & Dancyger's 20/60/20) | 20% of 40 seconds is 8 seconds, and the hook already needs 6–7 of them. There are no act breaks because there is no act | The hook / body / button timing plan in `script-format.md` — a timing plan, not a structure |
| The inciting incident as its own beat (McKee) | It presupposes a balanced world shown first and then upset; there is no runtime for the balanced world | The hook *is* the inciting incident — `modes/ugc-volume.md` §5, routed by awareness (`persuasion-psychology.md` §2) |
| The false-second-act diagnosis (Pope) | There is no second act to be false | The NEW/EXPAND label and the shuffle test (§2b) |
| Segments: 18–25 main ideas, 7–13 chapters (Cowgill) | One main idea, and the Rule of One says so independently | The one-sentence control idea (`script-format.md`) |
| Subplot as the vehicle for theme (Rubie & Provost) | A second strand needs runtime it does not have, and breaks the Rule of One | The single turn carries the theme, or nothing does |
| The third force / agent for change (Cowgill) | It resolves at a midpoint. There is no midpoint | The single turn |
| Chekhov's gun and planted foreshadowing (Cowgill) | A plant twenty seconds before its payoff reads as repetition, not as a plant | **Across episodes, not inside one** — the character signature in `script-format.md` is exactly this move at series scale |
| The crisis as a dilemma between irreconcilable goods (McKee) | The viewer is not choosing between two goods; they are deciding whether to believe one claim | The objection, at its strongest (§6, dimension 12) |
| An image system of 2–3 recurring motifs (Cooper & Dancyger; McKee) | You get one, and it is usually the brand accent | `brand-system.md`, `production-design.md` |
| Non-linear order, flashback, reordering for effect (Pope) | The viewer has no chronology to reconstruct and will not invest in assembling one | Nothing — write it in order |
| The ~4:1 information-to-action ratio (Rubie & Provost) | A prose ratio, and it **inverts** here: at 40 seconds close to every line must move, and the static ones are the first cut | Signal-to-noise and the NEW/EXPAND label (§6) |
| The antihero's redemption arc (Pope) | It runs on the audience's willingness to wait, and there is no wait | The value turn |
| Ensemble and balanced casts (Cooper & Dancyger's own anti-pattern) | Already excluded by the format — one voice, or two in a skit | — |

**One import is genuinely dangerous rather than merely useless: the three-act reflex.** It arrives
disguised as good practice, it survives review because everyone in the room recognises it, and it
costs the hook. If a script has a setup section, it has a first act, and the first act is eating the
hook's seconds.

## 2d. Measured bands — what real scripts actually do (v2.51)

[MEASURED · script corpus 2026-11-05] The owner asked for published scripts to be analysed so script generation
learns from them. The corpus was built from first-party sources only:

- 39 screenplays: features, TV and shorts, from studio awards PDFs and writers' own sites.
- 38 interviews: NASA and NEA (public domain), Democracy Now! and TED (Creative Commons).
- 67 ads with their spoken words verbatim: US federal public-service spots, and award-annual scripts printed by
  Communication Arts.
- 24 beat records of longer brand films.

The texts stay with the author. The plugin carries only the numbers, in `assets/script-bands.json`; the write-up
is in the author's research notes (not shipped). **These are reference bands, not rules:**
`script_score.py` prints them beside a script's own numbers and never fails on them. `--house` is the only way one
becomes a threshold, and it has to be passed explicitly.

**Three registers, three different shapes.** Figures are median (p10–p90).

| | Scripted dialogue | Talking head (real answers) | Ad VO and dialogue (TV / social) |
|---|---|---|---|
| Sentence | 5.6 words (4.8–6.7) | 16 words (13–22) | 7.3 words (5–11) |
| A turn or line | 6 words; 69 % of speeches are 10 words or fewer; p90 about 21 | about 100 words (16–219): a 30–40 s soundbite | first spoken sentence 10 words (3–16) |
| Questions | 18 % of sentences (14–23 %) | — | — |
| Contractions | 5.9 per 100 words (4.3–7.0) | — | — |
| Speeches cut off / trailing off | about 4 % each (0–9 %): one per scene at most | — | — |
| Fillers | — | 1.4 per 100 words (0.4–2.8) in edited transcripts, so a floor | — |
| Sentences opening on a connective (but, so, and, then, now…) | about 5 % | about 30 % | — |

**Pace and budget (ads).**
- **Words a second:** spoken words run about 2.2 a second (1.15–2.83).
- **Award-annual spots speak less,** about 1.8 a second, and give a quarter or more of the runtime to picture and
  sound.
- **Word budgets:** a 15 s spot holds 35–45 spoken words. A 30 s spot holds 37–81, median 63.
- **Crowded:** above about 2.8 words a second a script is crowded. Below about 1.15 it is picture-led, which is fine
  when meant.
- **`estimate_duration.py`'s 2.4 words a second** sits inside this band, so it stays.

**Where things fall in an ad.**
- **The CTA:** in 15–30 s spots the spoken CTA starts at 82–91 % of the spoken words, the last eighth. In 60–120 s
  brand films it mostly lives on the end card: only 2 of 11 such records speak one.
- **Hook and turn:** in the long-film records the hook ends at about 16 % of the words and the turn arrives at about
  54 %.
- **The brand:** award spots first name the brand about a third of the way in, though the range is wide (8–90 %).
  Public-service spots name it at the end, with the CTA. That is data for hook-craft §5b, not a rule.
- **Supers and direct address:** a TV spot carries about 3 supers. "You / your" runs about 3.4 per 100 spoken words
  on TV and about 8 in social and UGC scripts.

**The short-closer finding, stated correctly.** Real speakers end a multi-sentence answer on a short statement (8
words or fewer) about as often as they use short sentences anywhere: 31 % against 32 %. Their closers are not
systematically punchier. The written-copy tell is the ratio, not the short line: **every turn running long and then
landing on a punch.** `script_score.py --ugc` warns when at least half the multi-sentence lines end short while short
sentences overall are at most two-thirds of that share.

**What the numbers cannot tell you:**
- The bands describe what professionals and real speakers do. They say nothing about whether a line works.
- Feature-film figures (scenes about half a page, action paragraphs of 3 lines or fewer, first dialogue near page 1.5)
  are informational for the short-film and episode modes only. §2c still governs what transfers.
- The interview figures come from edited news and talk transcripts, so fillers and false starts are undercounted. Raw
  UGC runs messier.
- Interview planning (the host spends about a third of the words; open questions are about a quarter of host turns;
  anecdotes are rare unless asked for) is held at Tier B until a longer interview sample confirm it.

## 3. Dialogue — the part a prose system doesn't cover

**The reactivity test.** Every line must *react* to the one before it — answer it, resist it, deflect
it, top it. **If two adjacent lines could swap speakers without breaking anything, you have written
narration and put two names on it.** This is the most reliable single test for whether a scene is
alive, and it fails silently: split narration reads as fine dialogue on the page and as nothing on
screen.

- **Subtext over statement.** A hesitation, a deflection, or a question sells doubt better than "I'm
  worried about the cost." The character says the *second* thing they'd say, not the first.
- **Characters want different things in the scene.** If both want the same outcome, there is no
  scene — just an announcement in two voices.
- **Give each character a different sentence shape.** One clips, one rambles; one asks, one asserts.
  Two characters with identical rhythm are one character. This survives translation and it is what
  makes a recurring cast recognisable by ear.
- **Interruption and overlap are real speech** — but this skill generates one line per clip, so an
  interruption has to be *written* (a cut-off word, a `—`) and *cut* rather than performed across a
  clip boundary. Plan it at the shotlist, not in the edit.
- **The silent beat is a line.** The look before the answer is often the strongest thing in the
  scene, and it is free: it goes in the shot description, not the dialogue.
- **Only-this-person lines.** [PRIMARY · Pope] His diagnosis of *Falling in Love* is that the
  dialogue is realistic, competent and characterless — nothing either lead says could only be said
  by them, so the audience attaches to the sidelined spouses instead. The test here is cheap: take a
  line and ask whether any of the client's other personas could say it. If yes it is **register, not
  character** — the right voice with no person in it. This is the failing test behind the
  scorecard's character-distinctness dimension (§6).
- **The objection is the antagonist, so write it at full strength.** [SECONDARY · McKee] *"A
  protagonist and his story can only be as intellectually fascinating and emotionally compelling as
  the forces of antagonism make them"*, and weak antagonism is his most-cited cause of weak stories.
  [PRIMARY · Cowgill] adds that opponents should embody opposing *ideas* rather than merely take
  opposing positions, and [PRIMARY · Rubie & Provost] that the villain is the hero of his own story
  — so write the objection from inside it. In an ad the antagonist is the viewer's reason not to
  buy. **A strawman objection answered easily is the most reliable way to make an ad read as an
  ad**, because it fires the persuasion-knowledge alarm (`persuasion-psychology.md` §6) instead of
  defusing it. Use the real objection, in the words the objection list gave you (`ideation.md` §2).
- **The costly admission does more than any adjective.** [PRIMARY · Cowgill; PRIMARY · Rubie &
  Provost; SECONDARY · McKee] All three converge: character is revealed by a choice that costs
  something, not by description — the poor man who returns the wallet tells you more than the rich
  man doing the same. The spoken-ad version is a line where the speaker gives something up: what
  they wasted, what they got wrong, what they still don't like about it. It is also among the safest
  lines in the script under `compliance.md`, because a specific admitted number is substantiable and
  a hedged claim is defensible.
- **Repetition can be the climax.** [PRIMARY · Pope] Mamet's *The Verdict* spends its second act on
  physical action and then climaxes in spare, repetitive, accusatory speech — "dialogue as litany" —
  which lands harder than any event could. A 35–55 second ad has no spectacle to climax on either,
  so its button is verbal by default, and patterned repetition is available and under-used: the same
  phrase returned to with a different weight is a closing device. Note that this **agrees with §0's
  "speech repeats" row and disagrees with the prose avoid-repetition rule** — in spoken form that rule is
  wrong, and the disagreement is deliberate.

**For UGC first-person monologue,** the rules invert in a specific way:

- **Start mid-thought.** Real UGC has no preamble. "—and that's the part nobody tells you" is a
  legitimate opening.
- **Write in the disfluency.** One false start, one self-correction, one filler per 40 seconds is
  about right. Zero reads as scripted; three reads as a bit.
  [MEASURED · §2d] Edited interviews run about 1.4 fillers per 100 words, roughly one per 40 s at speaking
  pace. That confirms the floor. Above about 3 per 100 words it tips into a bit.
- **Let sentences run, and let them start on "so", "and" and "but".** Real answers average about 16 words a
  sentence, against 6 in scripted dialogue, and about a third of their sentences open on a connective. A UGC line
  built from six-word sentences reads as copy.
- **Don't save a punch for the end of every line.** Real speakers end short only as often as they speak short
  anywhere. A line that runs long and then lands on a three-word kicker, every time, is the written-copy tell
  (`script_score.py --ugc` asks about it).
- **Hedge the claim.** "I don't know if it's placebo but" outperforms certainty, reads as honest,
  *and* is safer under `compliance.md`. Rare alignment of craft, conversion and compliance — take it.
- **One tangent, briefly.** A person who stays perfectly on topic for 45 seconds is reading.

## 4. Voice — condition before drafting, don't audit after

The generation-time lesson, and it holds here: **an anti-pattern list tells the model what
not to do, which leaves it in its default distribution. A voice profile tells it what to do.** Load
the profile *before* the first draft; auditing afterwards only rearranges hits inside the same
biased distribution.

- Load the client's voice profile (if your studio keeps one) at drafting time, and name it in the brief note.
- No profile for a client yet? For short, low-stakes work use the house register and say so. For a
  recurring account, **build one** — two or three approved scripts are enough to seed it, and it
  pays back from the second episode.
- A profile is a client asset. Note it in `clients/<brand>.md` §2 beside the voices.

**Two different things get called "voice", and only one of them is in a voice profile.** The profile
above is an *author register* — lexical fingerprint, line length, rhythm, the words this person does
and does not use. [SECONDARY · Dancyger & Rush] name a second thing: voice as **mode** — satire,
fable, docudrama, melodrama — which decides what the piece can *mean* rather than how it sounds. The
same skeptic beats played as satire and as docudrama are two different videos with identical events.

- **Name the mode explicitly or it defaults.** Their anti-pattern is voice-by-default, and the
  default in AI-assisted promo is a flat melodrama-lite. That is a large part of why so much of it
  reads the same even when the words differ.
- **It is already in the ideation grid.** The "emotional register" axis of `ideation.md` §4 is this
  choice. Naming it as a mode makes it a craft decision with known demands rather than an adjective
  in a brief.
- **Tone shifts have to be set up, and at 40 seconds you get one.** [SECONDARY · Dancyger & Rush]
  An unearned shift reads as a mistake. The one shift you have is almost always the value turn — so
  spending it somewhere else means the turn arrives in the same register it left, which is the flat
  script's most common single cause.

## 5. Where the words are locked

For a locked-script client (`clients/<brand>.md` §0), none of §1–§4 licenses a rewrite. What is still
open: the **shot description**, the **silent beats**, the **reaction**, the **order of B-roll**, the
**caption line-breaks**, the **mode and tone** (§4), and the **delivery direction** for the voice
generation. The last two are underused — the same locked line delivered wearily instead of brightly
is a different scene, and a locked script played in a different mode is a different video.

If a locked line is genuinely unspeakable, that is a **new approved script**, not an edit. Raise it.

## 6. The scorecard — self-testing a script

> ⛔ **The scorecard grades a draft; it does not make one good.** Score a script only once it is a whole
> draft: v3 or later, and on the 2.67 template the fourth writing pass (§7), with a specific critique recorded
> between each version (`scripts/develop.py`, enforced by `gate.py approve script`). Scoring draft one and shipping it is
> the failure the development gate exists to stop: the scorecard will happily give 8/10 to the best
> version of the wrong idea.

A rating discipline retuned for spoken video. **Twelve dimensions exist;
eight are scored 1–10 before the script goes to storyboard — the four universal ones plus four you
choose.** (v2.67.0) The card is the writer's note. No tool can hear a script, so no gate reads the numbers: what is
checked is in §7, the tests a person can read beside each option. Each dimension names the test that makes it fail, because a
dimension you cannot fail is a dimension you cannot score.

> **This is the only definition of the scorecard.** If another file says seven systems or eleven
> dimensions, that file is stale — fix it, and say so in `memory/LEDGER.md`. The count drifted
> across four files once already and the fix cost more than the drift.

**Universal — always scored, never traded away:**

1. **Speakability** — read aloud without a stumble; every line one breath, one stress peak, one idea.
   *Fails when* you have to practise a line before you can say it.
2. **Human voice** — sounds like this person talking, not like copy being performed. Uneven rhythm,
   contractions, the specific detail only someone who was there would say. *Fails when* the rhythm
   is even across every line, or a UGC monologue carries zero disfluency.
3. **Signal-to-noise** — every line earns its seconds. In 45 seconds there is no room for a line that
   only sets up another line. *Fails when* a line can be labelled neither NEW nor EXPAND (§2b) —
   Pope's *Network* test, and the cheapest minute in the whole scorecard.

4. **Claim safety** — `claims_lint.py` clean, or every flagged phrase carries written client
   approval recorded against it. *Fails when* a claim's substantiation is "the client said so" with
   nothing written down. **This is universal because it is the one dimension whose failure is not a
   quality problem but a legal one**, and because it was previously in the optional pool, where a
   scorer under time pressure could legitimately never score it. It is also the cheapest to run —
   it is a script, not a judgement.

**Choose four of the remaining eight:**

5. **Reactivity — and its monologue form, inevitability.** Dialogue: no two adjacent lines could
   swap speakers. **Monologue: no two adjacent lines could swap order.** *Fails when* you shuffle
   the middle of the script and nothing breaks — that is a list with a voice on it, not a script.
   The monologue half is new and it matters, because most of what this skill writes has one speaker
   and the dialogue-only form left the dominant format unscored.
6. **Hook strength** — routed from the viewer's awareness level (`persuasion-psychology.md` §2),
   then built to carry **one concrete anchor and one withheld term**. *Fails when* it has neither —
   a mood with nothing to want — **or when it has no withheld term**, which is a summary wearing a
   hook's punctuation. ⛔ Scoring this dimension **higher for being vaguer is the error the evidence
   most clearly contradicts**: the concreteness/click relationship is curvilinear and turns over, so
   there is a peak in the middle and both ends are worse (`hook-craft.md` §1). Then check the three
   legs: the viewer knows they don't know (salience), cares about the answer (importance), and
   believes watching will fill it (epiphany) — §2 there. **Importance is the one that fails most
   often and the one rewriting cannot fix**; it comes from the audience, not the line. The question
   belongs in the **first** beat, not the last (§2b), and the brand does not belong in the first
   beat at all unless the client has tested otherwise (`hook-craft.md` §5).
7. **Value turn** — every scene flips something (doubt→interest, worry→relief). Count the turns. A
   turn has three parts: set-up, flip, **reaction**. *Fails when* the flip is written and the
   reaction is not — the viewer is then told a fact and never shown what it did to anyone. Cap a
   flip-without-reaction script at 6.
8. **Concreteness** — named numbers, objects, moments. Abstractions are unmemorable and, in
   claims-sensitive categories, usually also unsubstantiable.
9. **Visual sit** — every line has a concrete image to sit on; nothing is a talking head with nothing
   to cut to.
10. **Character distinctness** — each voice recognisable with the names removed. *Fails when* a line
    could be said by any of the client's other personas: that is register, not character (§3).
11. **Payoff** — the dramatic question posed early is answered, and the ending is a button, not a
    summary. *Fails when* the button answers a *different* question than the hook asked. This is
    the quietest failure in a rewritten script, because each pass moves the ending a little and
    nobody re-reads the hook against it. Pope's spine test: name the opening promise, then check
    that the ending pays off *that* promise and not a substitute that crept in.
12. **Antagonism** — the objection in the script is the audience's real objection, at its strongest,
    in their words. *Fails when* the objection is one the product obviously beats. A strawman
    answered easily is the most reliable way to make an ad read as an ad (§3), and this dimension is
    new because the scorecard previously scored how well the script argued and never scored what it
    was arguing against.

**The writer's bar:** a 6 or lower on any universal is a rewrite, not a polish. (Until v2.67.0 this line said
"nothing below 7 ships" as if a tool enforced it; none did.)

**Three of these tests are mechanical and none of them needs the tool** — the shuffle (5), the
NEW/EXPAND label (3), and the hook's question checked against the button's answer (11). They take
about a minute on a nine-line script and they fail loudly, so run them before scoring anything else.
A script that fails them will not be rescued by the other nine dimensions.

`scripts/script_score.py` mechanises the measurable half of this — line lengths and their variance,
spoken duration, contraction rate, stumble candidates, hook length, CTA count, speaker alternation,
banned-phrase hits — and prints what to fix first. `--hook-anchors` and `--brand <name>` add the two
mechanical halves of dimension 6: whether the hook window holds any concrete anchor at all, and
whether the brand is sitting in it. **Both are one-sided by construction** — the tool can see a
missing anchor and a present brand; it cannot see a missing gap, because "nothing is withheld" is not
a property of the text. **It cannot hear the script.** The read-aloud, the reactivity test and the
three legs of the gap stay human, and the script says so.

## 6b. ⚡ Writing for a generative camera — the three things a live production supplies for free

⛔ **Deliberately NOT a scorecard change.** §6 is the only definition of the scorecard and its count
has drifted across files once already. These are craft notes, scored inside the existing dimensions
(mostly 5, 7 and 11), not a thirteenth.

`[SECONDARY · course notes · derived from the revisions, not asserted by the source]`
A screenplay is written for a human production that fills in enormous amounts by itself. An actor
invents the pause. A stunt performer actually misses. A camera operator feels where to look. **None
of that exists here**, and the script is the only place to put it back. Three specific consequences:

**1. The silence has to be written, because nothing will improvise it.** A screenplay can leave a
beat implicit — *She looks away.* — and trust the actor. A model renders what is on the page and
nothing else, so an unwritten pause is simply absent, and a scene with no air in it plays as if in a
single breath. Write the beats as beats, and give a beat that carries a realisation **its own shot**
(`refinement-loop.md` §3: a pause that needs a frame is a planning fault, not a prompt fault). The
course's rule of thumb — **1–2 seconds before a character speaks after something lands on them** —
is a reasonable default, not a measurement.

**2. Write the fracture, not the feeling.** "Sad" is unactable by a person and unrenderable by a
model. What both can do is a **named break point**: the pitch drops on one named word; the voice
cracks on another; nostrils flare; the eyes flick down. ⚡ Note where the strongest line in the
course's film puts its break — inside the line itself: **two numbers set against each other, with a
dash between them.** The dash is the writing. Two numbers in opposition with the pause between them
is the whole story compressed, and the delivery note is already inside the line. And the line a
character **cannot finish** beats the line they finish: the course cut a line that stated the
failure outright and replaced it with the same line breaking off before the admission, which is
stronger precisely because the fracture is now the content.

**3. ⛔ Supply the causality, because the model is obliging.** This one has no equivalent in any
screenwriting book, and it is the sharpest difference in the whole corpus. In live action you write
*he misses* and you shoot a miss. Here, *he misses* competes with the model's prior that stories
resolve — reach for a prize and it tends to hand it to you. So **any outcome that depends on
someone failing must be made mechanically necessary in the text**: state how far a body can travel
in a dive (about two metres) against how far away the target lies (about eight), so the shortfall
follows from physics alone; or state that an obstacle moves faster than the person can, so it closes
the gap first. The general form:
**write the causality, not just the event.** A withheld outcome needs a mechanism; a stated
impossibility is weaker than a described one.

> ⚠️ A fourth thing worth noticing rather than adopting: **the 15-second ceiling is a dramatic form,
> not only a technical limit.** One beat, one turn, one scene — which is roughly *enter late, leave
> early* enforced by the tool. The constraint is doing craft work, and a script written to it reads
> tighter than one cut down to it. Whether that generalises past short-form is not something this
> corpus can tell us.

## 7. Iteration — staged, bounded, and it stops

**Three kinds of pass, in this order.** Polishing before the structure is right wastes the polish. Structure is the
first writing pass (v1, logic); lines and polish are the two fix passes (v5, v6) in the table below.

- **Pass 1 — structure.** Does it answer one question? Does every scene turn a value? Is anything
  missing, repeated, or in the wrong order? Is it inside the duration window? Run the two
  mechanical tests here rather than by eye: **shuffle the middle lines**, and **label each line NEW
  or EXPAND** (§2b).
- **Pass 2 — lines.** Speakability, reactivity, length variance, front-loading, subordinate clauses.
- **Pass 3 — polish.** Anti-pattern scan, claims lint, caption line-breaks, pronunciation decisions.

**One revision table** (v2.67.0; it replaces three rules that overlapped: at least three drafts in `develop.py`, at
most three fix passes here, and the four writing passes of §7b). Planned with three review rounds each by Grok 4.7
and Sonnet 5.5; both cut a stored 1–10 score as a diary the agent writes.

| Drafts | What | Checked by `develop.py` (jobs from the 2.67 template) |
|---|---|---|
| v1–v4 | **The four writing passes of §7b, in order:** logic, coverage, continuity, timing. A critique between each, naming the line or beat | at least four drafts; two consecutive drafts with the same text fail (a floor: it catches a copy, not a lazy pass) |
| v1 or v2 | **A cold read:** `cine-cold-reader` reads that draft's file and nothing else, and says what it is for, who speaks, what the hook asks, what the ending answers, and whether a line tries to be funny. A wrong premise is cheapest to find here. When the stranger's "ending answers" is not the writer's "hook asks", the next pass changes the ending, not the side notes | a `cold read:` file in the v1 or v2 block, stamped against that draft's file |
| v5–v6 | **At most two fix passes:** lines, then polish (the passes above). Fix the weakest thing first, with the minimum change, and look at what it cost elsewhere | a seventh draft fails unless their words say why: `waiver: "…"` under Drafts |
| options | **Two short options** on the concept they picked (§7b), each in its own file `01-script/options/<A|B>.md`. Beside each, the person reads: `hook asks:` and `ending answers:` (dimension 11), `cannot swap:` two adjacent spoken lines that break when swapped (dimension 5), the option's own cold read, and their answer to the comedy question when it tries to be funny (`comedy-craft.md` §9; ask about the line the cold reader named: "does the grass line make you cringe…?" tells the writer what to cut) | every field present; the swap lines adjacent in the file; the cold read stamped against the option's current spoken lines (`develop.py stamp`); a cold read that finds a joke where the option says `comedy: none` fails; on the picked option, any comedy answer other than "Nothing in it makes me cringe, or irritates, disgusts or embarrasses me" fails |
| signed | **The signed file is the option they picked.** `gate.py approve script --artifact` | their sentence (`their words:`) is a spoken line of the signed file, not a note in it; with a `waiver:`, the signed file's spoken lines are the picked option's, in order; the comedy answer is checked against the session transcript like an approval quote |

- **Stop after the second fix.** Document what is still weak and ship, or escalate to the person. The convergence
  rule that stood here ("stop when a pass does not raise the lowest score") is gone: no scores are stored, so
  there is nothing to converge on.
- **Voice deficit reverses the strategy.** If the script gets *flatter* as you strip patterns, stop stripping and
  start adding voice from the profile. Stripping is subtraction; voice is the thing that was supposed to be left.
- **The critics** (`cine-script-critic`, one axis each) run between drafts: logic, coverage, continuity, timing,
  hook, claims, and (v2.67.0) voice.

**One method disagreement worth holding open.** McKee argues structure-first [SECONDARY · McKee]:
build a step-outline in which every scene's turning value is written down before a line of dialogue
exists, on the grounds that most rewriting is caused by drafting into an unsound structure. Against
that, `editing-storytelling.md` §7.2 carries a working-editor argument to **build the opening
last** — openings are routinely assembled in post out of material never scripted as an opening.
**Both are
right about different halves of a 40-second script.** The step-outline is four lines long here, so
its cost is near zero and there is no reason to skip it. The hook is the exception: outline the turn
first, and leave the first six seconds deliberately unresolved until you have footage and an A/B
(`modes/ugc-volume.md` §1).

A script with two documented weak spots and a clear reason is operationally better than five passes
of churn. **The empirical test is the hook A/B, not another rewrite** — three hooks against a locked
body resolve in days and tell you something no amount of self-scoring will
(`modes/ugc-volume.md` §1).

## 7b. Scripts in four passes, then two options for them (v2.49, house rule 11; v2.65.0)

Author, 2026-11-05: proposed scripts lacked consistency, enough shots, and logic. So a script is **written** in
four passes, each with its own check, before §7's fix loop polishes it. Each pass ends in a draft, and its check
is the specific critique `develop.py` asks for between drafts (SKILL.md §4 item 3). After the last pass the
person sees **two short alternatives** on the concept they picked, side by side, each with the checks it passed
(v2.65.0: until then only one finished script was shown, and the person could only approve it). Each option keeps
**one sentence of theirs**, word for word, from the taste session or their material (`ideation.md` §0), or their
`waiver:` says why not; the earlier drafts stay in `00-brief/DEVELOPMENT.md` as the record, and `develop.py` checks
the `## Script options` section.

1. **Story logic.** The premise in one line. Cause and effect from beat to beat: every beat is caused by the one
   before it, and every action has a motive the viewer can see. *Check:* say each beat as "because …, so …"; a
   beat that only works as "and then" is cut or given its cause. The shuffle test (§2b) runs here.
2. **Coverage.** Enough shots for the duration, and **each shot with a function** (`shot-handoff.md` §6, the
   function enum for inserts). *Check:* the shot count against the length — at least the coverage floor of `direction.md` §3
   for every exchange (the speaker, the listener reaction, an insert, the B-roll) — and every shot's function
   written in one line. A beat with no shot to sit on, or a shot with no function, fails the pass. The festival
   films' median clip was 10 s `[SECONDARY · festival study 2026-11-05]`: a 40 s script carried by three shots
   is under-shot.
3. **Continuity.** Who is where, in every scene; wardrobe, props and time of day per scene; screen direction
   across the cuts. *Check:* a one-line continuity row per scene (the people and their positions, what each wears
   and holds, the time of day, which way they face and move). It becomes the scene's wardrobe and props sheet
   (`character-and-props.md` §8.3g) and the scene board's reference (`review-and-approval.md` §11).
4. **Cut-down and read-aloud timing.** Cut every line that does not earn its seconds, then read the whole script
   aloud at pace against a clock (§1) and run `estimate_duration.py`. *Check:* inside the format's duration
   window, no stumble, every line one breath.

**What the owner sees:** the fourth draft, and under it one short block — the four checks, each with its result
("story logic: 7 beats, each caused; coverage: 14 shots for 38 s, every exchange with its reaction; continuity: 3
scenes, rows written; read aloud: 37.5 s"). A pass that failed its check is redone before the next pass starts,
not noted and carried on.

**How it meets §7.** §7's table is the one count: these four passes are v1–v4, then at most two fix passes. Pass 1
here is the structure pass. `develop.py` checks the count (on the 2.67 template), that each draft's file exists, and
that no two consecutive drafts are the same file; it cannot see which pass made which change: that stays the
critique's job.

### Festival-short story patterns (v2.49; HFF-07)

From 12 festival films and one screenplay read for structure `[SECONDARY · festival study 2026-11-05]`. Patterns
with their sources, not rules; reach for them in pass 1.

- **A one-line premise, then a repeating device that escalates.** A sheep that keeps coming back; every purchase
  feeding a creature that grows; one impossible floor after another; one coat across three ages of a life. The
  device gives the viewer a rule to learn and the story a way to raise the stakes without new exposition.
- **Low on-camera dialogue.** Four of the twelve were wordless or nearly; another carried most of its words in
  voice-over over short visual scenes. Its screenplay ran about a page a minute, with about four of every five
  words action. This dodges the weakest part of AI film: one entry's comments praised its sound and faulted its
  acting. A line that the picture can carry is a line the model does not have to act.
- **Plant the twist early.** One film seeds the clues for its ending from the start; another carries a private
  structure the audience only sees at the end. A twist with no planted clue reads as a cheat.
- **Tone as a rule you defend.** One author rebuilt whole sequences that drifted into horror. Write the tone as a
  rule in the brief and in the clip's `[TONE]` block (`prompting-craft.md` §12), and check takes against it.
- **A visual system tied to story phases.** One film's palette moves through four emotional phases; another fills
  the apartment and grows the creature as the loop repeats; a third warms one scene against the cold of the rest.
  `emotional-journey.md` owns the arc; this is the colour script (`character-and-props.md` §7) doing the arc's work.

These are 3–19 minute festival films, not 40-second ads. The device and the planted clue survive the cut-down;
a four-phase palette needs the length to read.

## 8. Before the script leaves your hands

- [ ] Written in the four passes of §7b (story logic, coverage, continuity, cut-down and read-aloud), and shown
      with the checks the last pass passed
- [ ] Voice profile loaded **before** drafting, and named in the brief note
- [ ] Read aloud end to end, at pace, no stumbles
- [ ] Reactivity test passed — no adjacent lines could swap speakers
- [ ] Shuffle test passed — the middle lines cannot be reordered without something breaking
- [ ] Every line labelled NEW or EXPAND; nothing marked "neither" survived
- [ ] The objection is the real one, at its strongest, in the viewer's words
- [ ] The button answers the question the hook asked — the same question, not a cousin
- [ ] Mode and tone named (§4); exactly one tone shift, and it is the turn
- [ ] Every line: one breath, one idea, front-loaded subject, no held-open clause
- [ ] Numbers, acronyms, units written as they will be *said*; diacritics correct
- [ ] Scorecard run as the writer's note; any universal at 6 or lower rewritten; the lowest two named
- [ ] `script_score.py` run and its flags addressed or dismissed with a reason
- [ ] `claims_lint.py` clean or client-approved (claims-sensitive categories)
- [ ] `estimate_duration.py` inside the format's duration window
- [ ] Every line has a concrete visual to sit on
- [ ] Exactly one CTA

**Cross-refs:** `script-format.md` (the shape) · `ideation.md` (where the angle came from) ·
`craft-cheatsheet.md` (story logic) · `persuasion-psychology.md` (awareness routing, stickiness) ·
`compliance.md` (the claims gate) · `typography-and-captions.md` (the read version of these words) ·
`modes/ugc-volume.md` §5 (hook types) · `clients/<brand>.md` §0 and §2 (locks and voice) ·
`editing-storytelling.md` §7 (the same transfer question, asked of the editing canon).
