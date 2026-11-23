# Plan — QuNeo board lit-state reflection (full 38-control surface)

Status: in review (scope approved by user 2026-11-22 "full board, all 38 controls
with backend note/CC state tracking and per-type lighting").

## Goal

The three.js board must mirror the physical QuNeo's lit/unlit state for the
entire control surface, not just the 4 mapped sliders. Backend and frontend both
change: the bridge today only parses control-change events and only tracks the
3 synth-bound sliders, so it cannot reflect pads (momentary note state) or
buttons/rotaries.

## Requirements (verbatim, user)

- "the board in threejs must reflect the lit/unlit state of the real board"
- "vsliders augment towards to top, hsliders augment towards the right"
- "main 4x4 drum pads do not stay lit once pressed, but sliders, rotaries and
  most other buttons do (ie. must know current value at all times)"
- "only are 2 rotaries on the quneo"

## Control inventory (physical board, from queneo-editor 3d-web/LAYOUT.json)

- 16 pads      padButton0..15   (rounded_square, 4x4 grid, note_offset 0..15)
- 4  vsliders  vSliderButton0..3  (pill_track, vertical)
- 4  hsliders  hSliderButton0..3  (pill_track, horizontal)
- 1  lslider   lSliderButton0     (pill_track, horizontal, long)
- 2  rotaries  rotaryButton0..1   (drum_circle)
- 11 buttons   buttonButton0..10  (circle/diamond/square/triangle/arrows/rhombus)

Total 38 controls. Geometry + grid are in the editor's LAYOUT.json (241x185mm
board, origin top-left, y down).

## MIDI mapping (from BasicSC_QuNeo.scd + QuNeo.sc quark signatures)

Quark signatures (arg order):
- createDrumPad(index, noteNum, pressCC, xCC, yCC, channel)
- createHSlider(index, noteNum, pressCC, locCC, channel)
- createVSlider(index, noteNum, pressCC, locCC, channel)
- createLSlider(index, noteNum, pressCC, locCC, widthCC, channel)
- createButton(index, noteNum, pressCC, channel)
- createCircle(index, noteNum, pressCC, locCC, channel)

Resolved (channel 15 = 0-indexed, per plan constraint):
- pads:    note 0..15; pressCC 3n, xCC 3n+1, yCC 3n+2.
- vsliders: vSliderButton0..3 -> note 20/24/28/32, pressCC 60/68/76/84,
           locCC 61/69/77/85. (vSlider0..2 carry param/min/max:
           wobble 0-10, innerWobble 0-16, releaseTime 2-6.)
- hsliders: hSliderButton0..3 -> note 39/43/47/51, pressCC 92/100/108/116,
           locCC 93/101/109/117.
- lslider:  lSliderButton0 -> note 16, pressCC 48, locCC 49, widthCC 50.
- buttons:  preset maps only 3 (note 36/37/38, pressCC 124/125/126). OPEN:
           which 3 physical buttons, and what the other 8 do.
- rotaries: preset maps 8 "circle" controls on channel 14 (2 physical
           drum-circles x 4 banks). OPEN: which circle pair is the 2 rotaries.

## State model

The bridge must track, and `/api/collider` must expose, raw control state:
- CC values (sliders/rotaries): `cc` map — persistent, `cc -> value` (0..127).
- note press state (pads/buttons): `note` map — `note -> on/off` (pads
  momentary; buttons latch).
- synth params (`sliders`) stay as-is for bubble spawning (backward compatible).

The frontend derives lit state from raw control state, not synth params, so
unmapped controls (hsliders, pads, rotaries, buttons) still light correctly.

## Direction rules

- vslider: fill toward the TOP (value 0 -> empty; value max -> lit to top).
- hslider/lslider: fill toward the RIGHT.
- pad: binary lit (momentary on/off).
- button: binary lit (latched).
- rotary: position indicator at the value's angle.

## Slices (TDD — RED before GREEN)

Backend (pytest, no hardware):
- B1 mapping.json -> full 38-control inventory (id, kind, channel, noteNum,
  pressCC, locCC [xCC/yCC/widthCC], optional param/min/max). load_mapping +
  map.py still resolve; new tests cover the added kinds.
- B2 midi.py parse_aseqdump_line -> also parse "Note on"/"Note off" lines into
  {note, channel, on}; MidiWatcher keeps a note map alongside cc. New tests.
- B3 server.py status() -> expose cc + note maps; wire on_note. New tests.

Frontend (browser harness, zero-build):
- F1 board.js normalizeLayout -> handle all kinds (pad/hslider/vslider/lslider/
  button/rotary) with grid + noteNum/CC fields; generalize litFraction to raw
  0..127; direction-aware segment ordering.
- F2 render.js -> ladders per orientation (vslider bottom-up, hslider/lslider
  left-right), pads as single LED, buttons as LED, rotaries as ring indicator.
- F3 pane.js/api.js -> map full state to per-control onLit (type-aware).

## Open questions (resolved 2026-11-22, user)

1. Rotaries: circle bank 0 — rotaryButton0 = note 0 / locCC 1 (ch 14),
   rotaryButton1 = note 4 / locCC 9 (ch 14).
2. Buttons: light only the 3 mapped (notes 36/37/38); the other 8 render as
   LEDs that stay dark until they get a note.

## Definition of Done

- Bridge exposes full raw control state (cc + note) and still spawns bubbles on
  mapped slider activity.
- three.js board renders all 38 controls; vslider fills to top, hslider/lslider
  fill right, pads light only while pressed, buttons latch, rotaries show
  position.
- Backend pytest + frontend browser harness both green; live board mirrors a
  hardware touch.
