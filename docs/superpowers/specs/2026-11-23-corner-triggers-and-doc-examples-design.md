# Corner triggers and the SuperCollider documentation examples — design

Date: 2026-11-23
Spec: SPEC.md §9.6 (trigger surfaces) and §9.7 (the four documentation examples)
Scope: the smallest coherent increment — corner-trigger infrastructure plus the four
`examples.html` sounds, proving the oneshot path end-to-end. §9.8/§9.9 out of scope.

## Intent and why

The catalog today ships four `supercolliderjs` entries, all `continuous` on the
slider ladder. Spec §9 wants ~117 selectable examples; most of §9.8 and much of
§9.9 are *oneshot*. That path does not exist yet: notes never reach the app, and
there is no corner addressing or drone behaviour. This increment introduces the
oneshot path end-to-end on the four documentation examples, the smallest set that
exercises it, so §9.8's 109 defs become mechanical authoring afterwards.

## Goals / non-goals / anti-goals

- Goal: a pad corner fires a oneshot; a gated lead answers a pad note; a
  self-running drone starts on select and frees on deselect. Five new entries land
  in `catalog.json` with conforming `.scd` fragments, all via the existing
  boot-time one-sclang `load_defs` path. BSD + browser tests stay green.
- Non-goal: §9.8 SCLOrkSynths, §9.9 community imports, pitched corner→freq mapping
  (kalimba-style), multi-corner "kits" (explicitly deferred by §9.6's last line).
- Anti-goal: any entry that plays on its own at boot, or leaves a voice ringing
  past the 12 s ceiling / un-stopped by DetectSilence.

## Constraints (established, not reopened)

- D7: every def delivered in one sclang batch at boot; selecting later compiles
  nothing.
- D8: single-active selection; selecting never writes to the board; "min 1" bound
  control per entry.
- D9: gesture read from the def (gate → continuous; self-ending perc → oneshot; the
  free is still DetectSilence-owned in every mode),
  never hand-assigned — except where §9.7 explicitly names a surface.
- Voice contract (from the voice-lifecycle plan): every def carries `out=0`,
  `gate=1`, `fade=1`, the 3 s stop fade, the 12 s ceiling, and `DetectSilence`,
  which owns the free in every mode. This is asserted by
  `test_every_catalogued_def_carries_the_stop_fade_and_the_ceiling` and must hold
  for the new fragments too.
- The four Stage-1 examples keep `gesture: "continuous"`, onset `"cc"` (unchanged
  behaviour).

## Approaches

**A (chosen): extend the existing single-def model.** Add one field, `onset`, to
continuous entries (`"cc"` default / `"note"` gated / `"select"` drone), route note
events to the app, and split Gabber Rave into its two defs. One def per entry
holds; the pattern "kick loop" is not a def and is deferred.

**B: a "mixed"/multi-def entry** so Gabber Rave stays one entry armed on two
surfaces. More model surgery (an entry simultaneously driving two defs) to serve a
single example, and §9.6's own deferral of "arms many corners at once" points the
other way. Rejected.

Chose A: it is the smallest change that satisfies §9.6/§9.7 and leaves the
single-def model intact for the 109-def §9.8 import.

## Catalog entries (five, in order)

| id | def | gesture | onset | min-1 binding |
|----|-----|---------|-------|---------------|
| simpleFM | simpleFM | continuous | select | vSlider0 → modRate, 0.1–20 Hz, exp, default 1 |
| chainsaw | chainsaw | continuous | select | vSlider0 → amp, 0–1 lin, default 0.3 |
| drummer | drummer | continuous | select | vSlider0 → tempo, 0.5–16 lin, default 4 |
| gabberkick | gabberkick | oneshot | (corner) | vSlider3 → bend, 0.4–1 lin, default 1 |
| hoover | hoover | continuous | note | vSlider0 → freq, 40–2000 Hz exp, default 440 |

## Reshapes (routing/envelope only, no timbre change — §9.3 rule)

- **simpleFM** — `{ SinOsc.ar(SinOsc.kr([1,3]).exprange(100,2e3), 0, 0.2) }.play`.
  Promote the LFO to `SinOsc.kr([modRate, modRate * modRatio])` and the exprange to
  `exprange(freqLo, freqHi)`; defaults 1/3/100/2000 reproduce the source. Only
  `modRate` is bound.
- **chainsaw** — fold the `f`/`g` helper functions inside the SynthDef function;
  the trailing `* 0.3` becomes `* amp`. `ExpRand`/`coin`/`choose` re-roll per
  spawn, so the "noise machine" re-randomises each start — faithful.
- **drummer** — `var tempo = 4` becomes an `arg`; the snare/bdrum/hihat graph is
  verbatim.
- **gabberkick** — `\name.kr` controls become `arg`; the sustained
  `Env.asr(0.001,1,0.05)` gate envelope is demoted to a percussive hit envelope
  (`Env.perc(0.001, 0.35, -4)`) so the corner hit decays and DetectSilence frees
  it. This matches how the source's own `legato: 0.8` pattern played it as a short
  hit. Reserved slider binds `bend` (the pitch-drop amount); `ffreq` (the EQ sweep)
  is the noted alternative.
- **hoover** — `\name.kr` controls become `arg`; the source's two gated `Env.asr`
  releases stay; `freq` drives vSlider0 and the pad is the gate.

## Data model and code changes

- `catalog.json`: add optional `onset` to continuous entries (`"cc"` default;
  `"note"`; `"select"`). Oneshot entries omit it (corner trigger is implied by the
  gesture). No other schema change; the reserved slider and the pads resolve
  through `mapping.json` exactly as they do today.
- `midi.py`: the note branch of `_pump` currently records `_note` but fires no
  callback. Add a distinct `on_note(note, on, channel)` callback, wired by
  `serve()` to the app, alongside the existing `on_event` (CC only).
- `map.py`: add corner addressing primitives — `pad_of_note`, `quadrant(pad, cc)`,
  `corner_index = pad*4 + quadrant` — mirroring the frontend's `padQuadrant`
  (x>63 → right, y>63 → top). Used for addressing and helper naming; the flattened
  0..63 index is computed now but its pitch use is §9.8.
- `server.py`: `on_cc` stops triggering a voice for oneshot (a reserved-slider move
  only updates the stored value); a new `on_note` drives gate (continuous `note`)
  and the corner fire (oneshot). `select_example` starts a drone (`onset: select`)
  after rebinding; the existing `_stop_voices` already frees it on deselect.
- `examples.js` / helper text: a oneshot entry names its corner ("corner → X",
  reserved-slider line); a drone notes "runs until you switch"; a gated entry notes
  "pad = note". Corner lighting already works via `padQuadrant` — no renderer change.

## Rulings (my calls — flag if you disagree)

1. Gabber Rave splits into two entries (`gabberkick`, `hoover`); the `Pbind`
   "kick loop" is a performance, not a def, and is deferred. This makes the
   documentation set five entries, not the literal "four" the spec's 117 count
   assumed.
2. Unpitched oneshot fires from **any** corner at default args (matches §9.8's
   "Corner → /s_new"); the pitch part of §9.6 is untouched until §9.8.
3. Corner depth at note-on reads the QuNeo's latched x/y; the very first touch of
   a never-before-mapped pad defaults to quadrant 0 (the QuNeo latches, so this is
   a once-per-pad edge case).
4. The reserved slider for a oneshot is vSlider3, matching §9.8's kick808 example.
5. The four Stage-1 entries keep their exact current behaviour and remains
   `gesture: "continuous"`, onset `"cc"`.