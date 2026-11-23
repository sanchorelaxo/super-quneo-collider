# Plan: voice lifecycle, the 12 s ceiling, and the fade checkbox

Date: 2026-11-23
Spec: `SPEC.md` D10, "Feature: Nothing outlives its welcome", DoD bullet on bounded voices.

## Why

Three failures in the live bridge, reported in this order:

1. The sound kept playing when a new example was selected.
2. `sine` (and anything without its own envelope) never stopped. "SuperCollider is
   still fuzzing out on audio."
3. `bubbles` sounded at boot with no one touching the board.

Then the ask that shaped the design: force a 3 s fade-out on anything past 12 s,
and make that fade-out optional with a checkbox beside the select.

## The shape

Root cause of 1 and 2 was one line: `_trigger()` sent `/s_new <def> -1`, so every CC
spawned an untracked node that the bridge could never stop. Fix the ownership, and
both go away.

`Ruling: the bridge picks the node id and tracks one live voice per continuous example
— because you can only stop what you own — cost if wrong: a `oneshot` kit needs more
than one tracked node, so the tracker becomes a set later.`

`Ruling: the 12 s ceiling and the 3 s stop fade go INSIDE the .scd fragments, not in
the bridge — because defs are delivered as one `/d_recv` blob and the wrapper is the
only place that covers every example — cost if wrong: a def copied from upstream
without the wrapper leaks; the pytest def-contract test catches that.`

`Ruling: the ceiling env is driven by a constant (1), not by gate — because an EnvGen
with an open gate holds at its release node and never frees the node — cost if wrong:
nothing frees at 12 s and the drone returns (proven wrong the hard way, see Evidence).`

`Ruling: DetectSilence (doneAction 2) owns the free in both modes; every example's own
envelope is demoted to doneAction 0 — because the free must not depend on whether the
ceiling is on — cost if wrong: a def whose body goes silent frees early, which is the
behavior we already wanted for one-shots.`

`Ruling: the fade is a def ARG (fade=1) short-circuited with Select.kr(fade > 0, [1,
fadeEnv]) — because that is a per-spawn switch with no recompile and no node surgery —
cost if wrong: changing the mode cannot affect an already-running voice, so set_fade
stops what is sounding.`

`Ruling: the bridge is the state of record for the checkbox; the page mirrors
fadeEnabled on every poll — because two sources of truth for a switch that also lives
in the def is how you get a box that lies — cost if wrong: a bridge that omits the
field leaves the ceiling ON, which is the safe default.`

## Tasks (TDD, in order)

1. RED `tests/test_sc.py`: `VOICE_CAP_SECONDS`/`VOICE_FADE_SECONDS` exist; `boot()`
   sends `/notify 1`; an `/n_end` reply calls `on_node_end(int(args[0]))`.
   GREEN: constants, `_register_for_node_ends()`, `_dispatch` branch.
2. RED `tests/test_sc.py`: `set_params(node, **params)` sends one `/n_set` and keeps
   ints int. GREEN: `set_params` + `_typed`.
3. RED `tests/test_sc.py` (def contract): every `DEF_NAMES` fragment carries `gate=1`,
   `fade=1`, the stop fade, the gate-independent cap, and DetectSilence.
   GREEN: rewrite all four `.scd` with the wrapper.
4. RED `tests/test_server.py`: `start()` spawns nothing; a CC spawns exactly one node
   at a bridge-chosen id; a second CC sends no `/s_new`; selecting stops the sounding
   voice with gate 0; `/api/collider` reports `fadeEnabled` and `voices`.
   GREEN: `_voices`/`_lock`/`_next_node`, `_trigger` rewrite, `voice_ended`, `start()`
   boot spawn removed.
5. RED `tests/test_server.py`: `POST /api/collider/fade` toggles and 400s a
   non-boolean. GREEN: `_POST_ROUTES` + `_apply_post` + `set_fade`.
6. RED `client/tests/examples.test.js`: the checkbox reflects `fadeEnabled` (and
   defaults ON when it is absent), a toggle POSTs the new value and re-renders from the
   reply, and a failed POST lands in the helper text. GREEN: `setFade`, `applyPicker`,
   `mountExamplePicker`, `#fade` in `client/index.html`.
7. RED `tests/test_server.py`: a query string is not part of the route (static, API,
   POST), while `/` still serves the page, a missing file is still 404, and a traversal
   attempt is still 404. GREEN: strip it with `urlsplit(self.path).path` in the handler.

Each task ends green on its own. Task 7 exists because the browser-cache workaround
(`?v=2`) hit a 404 and exposed the verbatim `self.path` comparison.

## Evidence (real scsynth, not inferred)

- `~/.hermes/cache/scratch/live_ceiling2.py` drives the real `ColliderApp`, the real
  defs and a real scsynth with a `StubMidi`, hooking `on_node_end`:
  ceiling on -> freed at 12.62 s; ceiling off -> still ringing at 13.5 s, then gate 0
  -> freed 3.45 s later. Same stop fade on select.
- `live_defs.py`: `numDefs: 4`, all four defs load and sound; `formant` and `klang`
  self-reap in ~2.7 s at default args (upstream behavior, not a regression).
- `bubbles_level.py`: a bus-0 amplitude meter. The earlier "bubbles is silent" reading
  was a probe bug (reused node id 1500, so the def never spawned); at distinct ids
  `bubbles` measures 0.01-0.09 and `formant` is upstream's 0.1 s blip.
- Live HTTP: `GET /api/collider` -> `fadeEnabled: True`, `voices: []`, no boot sound;
  `?v=2` now serves the page; unchecking the box flips the bridge to
  `fadeEnabled: false` and rechecking flips it back, surviving a poll cycle.
