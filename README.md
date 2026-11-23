# super-quneo-collider

QuNeo vertical-slider MIDI CC to a live SuperCollider "bubbles" synth
parameter, exposed over HTTP at `/api/collider`. A three.js model of the board
mirrors the physical QuNeo's lit/unlit state across the full control surface.

![QuNeo controller on laptop running step sequencer](docs/quneo-setup.jpg)

## Install

```bash
./install.sh   # idempotent: supercollider + .venv + editable install
```

## Run

```bash
.venv/bin/python -m super_quneo_collider.server
```

Then open `http://127.0.0.1:8686` for the board, and hit
`http://127.0.0.1:8686/api/collider` for
`{"present": bool, "sliders": {...}, "cc": {...}, "note": {...}}`.

The bridge boots scsynth, loads the `bubbles` SynthDef, spawns one bubble so the
synth is audible on load, and links scsynth's pipewire output (the
"SuperCollider" client) to the default audio sink with `pw-link` (best effort).
QuNeo activity (a vSlider CC on channel 15) triggers a fresh bubble carrying the
accumulated slider values.

## Board mirror

The three.js board reflects the real QuNeo, not just the three bound sliders:

- vSliders fill toward the top, horizontal and long sliders toward the right,
  pads light their pressed corner and stay lit after release (the QuNeo latches
  x/y), buttons latch, and the two rotaries show a position indicator on a ring.
- Raw CC and note state is tracked per MIDI channel (channel 15 controls plus
  the two channel-14 rotaries), so every control lights in step with the board.
- Last-known state persists to `$XDG_STATE_HOME/super-quneo-collider/state.json`
  and reloads on boot, so a bridge restart does not blank the board.

## Audio

On boot the bridge auto-routes scsynth into your default pipewire sink. If your
sink changes (or you want a different output), reconnect manually:

```bash
pw-link SuperCollider:out_1 "$(pactl get-default-sink)":playback_FL
pw-link SuperCollider:out_2 "$(pactl get-default-sink)":playback_FR
```

Requires a pipewire/pulse system with `pw-link` and `pactl` on `PATH`.

## Test

```bash
.venv/bin/pytest
```

Backend tests run with no hardware. Frontend tests are browser-harness based
(open `client/tests/index.html`); tests marked `scsynth_ok` exercise a real
scsynth boot and skip when scsynth is not installed.
