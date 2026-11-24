# Plan: SCLOrkSynths catalog import (SPEC §9.8)

Author: Hermes (hermes-agent persona)
Date: 2026-11-23
Branch: master
Feature type: data import + reshape pipeline (SPEC §9.8)
Project: super-quneo-collider

## Goal

Grow the catalog from its current 9 entries to 118 by importing the 109 SCLOrkSynths
SynthDefs (11 banks), and ship the §9.8 corner addressing that the corner-triggers increment
deliberately deferred (pitched one-shots map a pad corner to `freq`, 220 Hz → 880 Hz). Every imported def is delivered in the
single boot-time sclang batch (D7) and carries the full voice contract (D10): `out=0`,
`gate=1`, `fade=1`, the 3 s stop fade, the 12 s ceiling, and `DetectSilence` as the only
thing that frees a voice.

## Out of scope

- §9.9 (the ~190 community SynthDef collections). Separate follow-on plan, with its own
  reshape rules (§9.9.2), attribution header (§9.9.4), and dedupe key (§9.9.1). This plan
  only needs to establish the collision rule from §9.9.1 (see Decision 4) so §9.8 records a
  truthful `source` field that §9.9 can dedupe against.
- A multi-corner "kit" that arms several corners at once (§9.6 line 868). Selection stays
  single-active (D8). One corner = one sound.
- Any change to D1-D8 mechanics (Python bridge, pyliblo3 control plane, one-shot sclang
  delivery, mapping.json inventory, single-active select). We extend, not re-plumb.

## Decisions (the ones an implementer cannot infer)

### Decision 1 — the import reshape (what happens to each upstream `.scd`)

Upstream SCLOrkSynths files are `SynthDef("name", {arg out = 0, ...; ...}).add;` plus a
trailing `metadata: (credit: ..., category: ..., tags: ...)` block. They are NOT
drop-in: `sc.py`'s batch wraps each fragment as `{ <fragment> }.value` and calls
`.asBytes`, and the voice contract is enforced uniformly. Each file is reshaped to a
catalog fragment as follows:

1. **Header.** Drop the `metadata: (...)` object. Replace it with a `//` provenance header:
   `// SCLOrkSynths/<bank>/<file>.scd — <credit> — category: <category>, tags: <tags>`.
2. **Arg list.** Normalize to the guard-test's exact spellings: `arg out=0` first (upstream
   writes `out = 0` with spaces — collapse to `out=0`), then `gate=1`, `fade=1` if the def
   has them, otherwise append `gate=1, fade=1`. Keep every bespoke arg verbatim (its name,
   default, and spacing) because those are the bindable params. No arg may be dropped.
3. **Free demotion.** The def's own envelope must never free the node (D10). Remove the
   def's own `DetectSilence.ar(...)` line entirely, and rewrite every `doneAction: 2` in
   the def's envelopes to `doneAction: 0`. (Some defs, e.g. `kick_oto309`, `ping_mh`,
   have NEITHER — those simply keep running until our guard's `DetectSilence` frees them,
   which is the point of the fix.)
4. **Guard tail.** Take the def's final `Out.ar(out, <expr>)` (or `OffsetOut.ar`) and
   rewrite it to the canonical contract, where `<expr>` is the def's own output expression
   (multichannel `Pan2.ar(snd, pan)` et al. multiply fine, as the envelope is a scalar
   graph the multichannel sig broadcasts across):

```
var stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
var fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
var sig = <expr> * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
Out.ar(out, sig);
```

   The two `var stopFade`/`var fadeEnv` declarations are appended to the def's existing
   `var` block (every SCLOrkSynths def has one). This is byte-for-byte the guard that
   `test_every_catalogued_def_carries_the_stop_fade_and_the_ceiling` counts, so it must be
   reproduced exactly — no reformatting.
5. **Delivery.** Stripped of `.add;`, the fragment must end with the bare `});` of the
   `SynthDef`, so `{ ... }.value` returns the SynthDef for `.asBytes`. No `Server`, no
   `.add`, no `.send`.

This is a deterministic transformation, not judgment. The plan pins it once; the implementer
applies it 109 times and a test (Task 1) proves the invariant holds for every fragment.

### Decision 2 — gesture and onset are read, never hand-assigned (D9)

- `gate` arg present → `gesture: "continuous"`, `onset: "note"` (pad press = gate 1, release
  = gate 0). Most of the 43 continuous defs are gated ADSR synths.
- No `gate`, but a self-ending perc envelope (`doneAction: 2` on an Env) → `gesture:
  "oneshot"`, unpitched unless it has a `freq` arg.
- No `gate` and no free at all (a self-running drone, rare in this set) → `gesture:
  "continuous"`, `onset: "select"`.
A manifest test pins the per-def gesture/onset map so the read is deterministic and auditable,
rather than inferred ad hoc at spawn time. The mechanical classification (43 continuous /
66 oneshot) is the starting point; the manifest is the source of truth.

### Decision 3 — corner addressing and the pitched one-shot (the deferred §9.8 flank)

- Corner index `= pad * 4 + quadrant`, index 0..63 across 16 pads × 4 quadrants (X low→high
  left→right, Y low→high bottom→top, per §8). The QuNeo latches x/y, so the quadrant is read
  from the pad's most recent `xCC`/`yCC` position at note-on time (the addressing primitive
  the corner-triggers increment deferred).
- Unpitched one-shot (kick808, claps, hats): the corner fires the def at default args. One
  trailing timbre arg (`dist`, `ringTime`, ...) binds to the reserved slider so the def keeps
  its "min 1" control.
- Pitched one-shot (kalimba, bells, plucks, marimba, xylophone, ...): the corner sets `freq`.
  The mapping is `freq = 220 * (2 ** (2 * index / 63))`, i.e. a log sweep from 220 Hz at
  corner 0 to 880 Hz at corner 63 (§9.6), rounded to 2 decimals in the `/s_new` arg. A
  trailing timbre arg binds to the reserved slider.

### Decision 4 — collision rule with §9.9

Per §9.9.1 the dedupe key is "same name, different graph". When a §9.9 community import later
collides on a name, the SCLOrkSynths def wins. This plan only records `source:
"SCLOrkSynths"` on every imported entry (the client fixture already uses that string), so
§9.9's dedupe pass can detect the collision by name+source. Nothing more is needed now.

### Decision 5 — binding convention (min-1 per entry, ladder order)

- Continuous defs: `freq` (or the def's first musical arg) and `amp` on the first two slider
  ladder rungs in declaration order, then the next bespoke arg(s) on subsequent rungs. At
  least one param, always `amp` if nothing else is musical.
- Every param's `control` names a `mapping.json` control id (never a duplicated literal), and
  carries `cc`/`channel`/`min`/`max`/`curve`/`default` per §9.4.

## Tasks

### Task 1 — reshape pipeline contract + pilot bank (percussion, 9 defs)

- Author `scripts/` (or `tools/`) helper that reads an upstream `.scd` and emits a reshaped
  fragment per Decision 1, but first: reshape the 9 `percussion` defs BY HAND as the golden
  reference and pin them.
- Write `tests/test_sclork_import.py` asserting, over every shipped fragment: exactly one
  `arg out=0`, `gate=1`, `fade=1`, `Env.asr(0.01, 1, 3)`,
  `Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin')`, `Select.kr(fade > 0, [1, fadeEnv])`,
  `DetectSilence.ar(` (the existing guard test already does this once `DEF_NAMES` grows —
  this new test pins the SOURCE-import invariants: provenance header, no `.add`, no
  `doneAction: 2` anywhere in the body, `out=0` first arg).
- Add a real-sclang smoke test that loads the batch and asserts `numDefs >=
  len(DEF_NAMES)` for the newly added defs (mirroring `test_resolve_scsynth_exists`).
- Lift the hardcoded `== 9` counts (`tests/test_sc.py:37`, frontend fixtures) to a
  manifest-derived count so further imports don't trip them.
- Run the full backend suite; commit.

### Task 2 — apply the reshape to the remaining 10 banks (100 defs)

- One commit per bank, in this order, applying Decision 1 verbatim and recording each def in
  the gesture/onset manifest (Decision 2) and catalog (Decision 5):
  `bass` (13: 5 continuous / 8 oneshot), `bells` (6: 1/5), `drums` (31: 3/28), `guitar`
  (3: 0/3), `keyboards` (8: 4/4), `misc` (19: 12/7), `organ` (7: 7/0), `pads` (9: 7/2),
  `strings` (3: 3/0), `winds` (1: 1/0).
- Each bank lands as: its reshaped `.scd` fragments in `src/super_quneo_collider/`, its
  `catalog.json` entries with `source: "SCLOrkSynths"`, `gesture`/`onset`/`params`, and the
  fragment name appended to `sc.py`'s `_DEF_SCRIPTS` in catalog order.
- After each bank, run the backend suite and the guard test (they must stay green at each
  increment); commit each bank incrementally.
- Final State of this task: the catalog has all 118 entries, `DEF_NAMES` is 118 long, the
  guard test passes at `n = 118`, and `sc.load_defs()` registers 118 defs against real
  scsynth.

### Task 3 — corner addressing + pitched one-shot frequency

- Add the corner-index primitive: from a pad's latched `xCC`/`yCC` (already watched in
  `midi.py`), resolve quadrant → `index = pad*4 + quadrant` at note-on time.
- In `server.py`, extend the one-shot spawn path: if the active entry is a pitched one-shot
  (has a `freq` arg and `gesture: "oneshot"`), compute `freq` per Decision 3 and pass it as an
  `/s_new` arg; if unpitched, pass default args and route the trailing timbre arg to the
  reserved slider.
- Tests (`test_server.py`, `test_midi.py`): corner 0 → 220 Hz, corner 63 → 880 Hz, a corner,
  monotonic mapping, and that unpitched one-shots ignore `freq`. Update helper text so
  `map.py`'s `helper_lines` names the corner ("pad 3 · top-right -> kick808") per §9.6.

### Task 4 — full live verification and docs

- `git status` clean; backend suite green (140+ and growing in Task 2); frontend
  browser-harness suite re-run against the 118-entry select (green).
- `DEV_STATUS.md` updated to the 118-entry state; catalog `default` remains `bubbles`.

## Execution method

After this plan is approved, read `superpowers:executing-plans`, then work Task-by-Task.
Every task is its own RED-GREEN-REFACTOR cycle per the project's TDD convention: write the
failing test first, watch it fail, make it green, run the individual test AND the full suite,
then commit that task as one incremental commit. Finish with a clean `git status`. Do not
push. If any reshaped def fails to compile under real sclang/scsynth, stop and report the
failing def and its upstream file rather than guessing a fix.