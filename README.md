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

## Test

```bash
.venv/bin/pytest
```

Tests marked `scsynth_ok` exercise a real scsynth boot and skip when
scsynth is not installed.
