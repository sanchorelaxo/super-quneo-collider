# super-quneo-collider

QuNeo vertical-slider MIDI CC to a live SuperCollider "bubbles" synth
parameter, exposed over HTTP at `/api/collider`.

## Install

```bash
./install.sh   # idempotent: supercollider + .venv + editable install
```

## Run

```bash
.venv/bin/python -m super_quneo_collider.server
```

Then hit `http://127.0.0.1:PORT/api/collider` for `{"present": bool, "sliders": {...}}`.

The bridge boots scsynth, loads the `bubbles` SynthDef, spawns one bubble so the
synth is audible on load, and links scsynth's pipewire output (the
"SuperCollider" client) to the default audio sink with `pw-link` (best effort).
QuNeo activity (a vSlider CC on channel 15) triggers a fresh bubble carrying the
accumulated slider values.

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

Tests marked `scsynth_ok` exercise a real scsynth boot and skip when
scsynth is not installed.
