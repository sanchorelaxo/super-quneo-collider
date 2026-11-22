# Plan — super-quneo-collider frontend (three.js collider board)

Status: approved for implementation (user "just continue impl", 2026-11-22).

## Scope

The backend plan is complete (5 tasks, 31 passing tests, live bridge smoke-tested).
This plan implements the remaining SPEC Definition of Done item: the three.js
board at `src/super_quneo_collider/client/` that lights the 4 vertical sliders
proportionally as `/api/collider` reports synth params change.

Explicitly OUT of scope (per SPEC §7): the hardware path (manual, user's camera
rig) and preset flashing as a runtime feature (test-only helper, deferred).

## Source of truth

- SPEC.md §6 "The three.js board lights the slider" (lines 307-330) — exact
  acceptance. Scenarios:
  1. model exposes slider: lookup vSliderButtonN carries channel 15, pressCC,
     locCC. Examples: 0→60/61, 1→68/69, 2→76/77, 3→84/85.
  2. value lights slider: collider pane applies param=value; lit segment count
     reflects value on the param range. Examples (litFraction): wobble 5.0→0.5,
     innerWobble 16.0→1.0, releaseTime 2.0→0.0.
- `src/super_quneo_collider/mapping.json` — channel 15, 4 vSliderButton controls
  with noteNum/pressCC/locCC; vSliderButton0-2 carry param/min/max
  (wobble 0-10, innerWobble 0-16, releaseTime 2-6); vSliderButton3 has NO param.
- queneo-editor `3d-web/LAYOUT.json` — vslider geometry (board 241x185mm; the
  4 sliders at cx 19.2/38.0/56.9/75.7, cy 151.8, w 11.9, h 48.0).
- queneo-editor `3d-web/tests/` — the "existing queneo three.js test harness
  style" (harness.js test/assert/assertEqual/runAll → window.__TESTS__).

## Constraints

- The collider LAYOUT.json mirrors mapping.json's MIDI params (channel 15,
  pressCC, locCC, param/min/max). mapping.json remains the backend runtime's
  source of truth; the client is self-contained and does not import Python.
- Pure model logic (normalizeLayout, indexById, litFraction) lives in a module
  with NO three.js import so it is testable without a renderer.
- litFraction is the tested unit (SPEC examples are floats). litSegments is a
  render helper: `round(litFraction * segments)`.
- Tests run in the browser (zero-build harness) served over HTTP by the bridge's
  own `serve()` (it already serves `client/` statically). Driven via CDP.
- No bundler, no npm, no node_modules. `vendor/three.module.js` is a single file
  copied verbatim from queneo-editor.

## Tasks (TDD — RED before GREEN)

### Task F1 — LAYOUT.json + board model
Files: `client/LAYOUT.json`, `client/src/board.js`,
`client/tests/harness.js`, `client/tests/board.test.js`, `client/tests/index.html`.
- `LAYOUT.json`: board {w 241, h 185, thickness 9.5, corner_radius 6} + the 4
  vslider controls (geometry copied + merged MIDI params, channel 15).
- `board.js` (pure): `normalizeLayout(raw)`, `indexById(controls)`,
  `litFraction(control, value)` → clamp((value-min)/(max-min), 0, 1) or null
  when unbound, `litSegments(control, value, segments=8)`.

### Task F2 — API client + collider pane
Files: `client/src/api.js`, `client/src/pane.js`, `client/tests/pane.test.js`.
- `api.js`: `getState(url='/api/collider')` → {present, sliders}.
- `pane.js`: ColliderPane — `registry` param→control, `apply(param, value)`,
  `applyState(state)`; computes litFraction + litSegments and updates a
  per-control `onLit(control, litSegments, litFraction)` callback (render
  subscribed separately, keeping the pane testable with no THREE).

### Task F3 — three.js render + index.html
Files: `client/index.html`, `client/src/render.js`,
`client/vendor/three.module.js`, (copied from queneo-editor).
- Minimal board: dark slab + 4 vertical slider ladders, each N segments.
- Poll `/api/collider` on an interval, feed pane, light segments via `onLit`.

### Task F4 — browser-harness verification (CDP)
- Serve via `serve()`; load `client/tests/index.html` in the browser; assert
  `window.__TESTS__` all `ok`. Verify the live board lights when `/api/collider`
  reports a non-default slider (poll an externally-set value).

## Rulings (record as they are made)
- Record each judgment as `Ruling: <what> — <why> — <cost if wrong>`.

## Definition of Done
- `client/tests/index.html` exercises board model + pane; all tests pass in the
  browser harness; the model lookup returns exact channel/pressCC/locCC and the
  litFraction examples from SPEC §6 pass.
- Live board (browser pointed at the running bridge) lights vSliderButton0
  proportionally when wobble changes.
