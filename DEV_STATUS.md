# DEV_STATUS — super-quneo-collider

Last updated: 2026-11-23

## Current state

- The bridge, the three.js board, and the full-board lit-state mirror are all
  implemented, tested, and live. No longer spec-only.
- **MILESTONE (2026-11-22):** the three.js board mirrors the physical QuNeo's
  lit/unlit state across the full 38-control surface, driven by live CC/note
  MIDI state from the bridge — not just the 3 synth-bound sliders. A pad pressed
  on the real board lights the same pad on the model, in the same orientation
  and brightness, and the state survives a bridge restart.
- Backend: **140** pytest green. Frontend: **49** browser-harness tests green.

## Corner triggers + doc examples (§9.6/§9.7) — landed 2026-11-23

The example catalog grew from 4 Stage-1 entries to 9, and the bridge now routes
MIDI into every entry through three onset modes instead of CC-only bubbling.

- Catalog: 9 entries — `bubbles`, `formant`, `sine`, `klang`, then `simpleFM`,
  `chainsaw`, `drummer`, `gabberkick`, `hoover`. The five additions all import
  from `examples.html`.
- New `onset` sub-flavor per entry (`cc` default / `note` / `select`):
  - `simpleFM` / `chainsaw` / `drummer` → `onset: select` (drone starts on
    selection, fades on deselect).
  - `hoover` → `onset: note` (gated — sounds only while a pad is held; vSlider0
    sweeps pitch).
  - `gabberkick` → `gesture: oneshot`, `onset: cc` (a fresh hit fires on every
    pad corner press; vSlider3 shapes the pitch-drop).
  - the four Stage-1 entries stay `cc` / continuous, untouched.
- `on_note` dispatches by gesture first (oneshot → fresh `_trigger`), then by
  onset (note → gate open/close); select- and cc-onset entries ignore notes.
- `/api/collider` now reports `onset` per example, and `status()` reflects it.
- DoD (§7): no preset is flashed and selection never writes to the board; all
  nine defs are delivered at boot in the one-shot `sc.load_defs()` batch
  (numDefs ≥ 9); selection remains control-plane only.

## Milestone detail (full-board lit-state mirror)

Prior to this, the bridge parsed only control-change events and tracked only the
3 synth-bound vertical sliders. Now the watcher parses both CC and Note
on/off lines and keeps raw control state for the whole surface, so unmapped
controls light too.

- `mapping.json` carries a 30-control MIDI inventory (16 pads + 4 hSliders +
  4 vSliders + 1 lSlider + 3 lit buttons + 2 rotaries) from `BasicSC_QuNeo.scd`.
  `client/LAYOUT.json` is regenerated as the 38-control merge of editor geometry
  + those MIDI bindings (per-control `channel`, so ch14 rotaries do not collide
  with ch15 pad `xCC`/`yCC`).
- `midi.py` keeps CC and note state **keyed by MIDI channel** — a pad `xCC`
  (ch15) and a rotary `locCC` (ch14) may share a controller number, as may a pad
  note (ch15) and a rotary note (ch14). A flat `{number: value}` map would merge
  distinct controls.
- `/api/collider` now exposes `{present, sliders, cc, note}`. `cc` and `note`
  are per-channel maps; `sliders` (synth params) stays for bubble spawning, so
  the endpoint is backward compatible.
- Frontend derives lit state from raw `cc`/`note`, not synth params:
  - vSlider fills toward the TOP (0 = dark, max = full).
  - hSlider / lSlider fills toward the RIGHT.
  - pad lights a four-corner brightness field from live x/y and pressCC while its
    note is down, and latches those corners after release (dark only before its
    first press); button latches.
  - rotary renders a ring with a single position indicator at the value's angle.
- LED colour is **per-position, not a value ramp** (matching the hardware):
  - hSlider / vSlider: a fixed 8-light 3-2-3 green/yellow/red ladder, filled
    from the low end — the value chooses how many light, never the hue.
  - lSlider (crossfader): 17 fixed-colour lights (3 red / 3 green / 2 yellow /
    centre blue / 2 yellow / 3 green / 3 red) swept by a 3-light window.
  - rotaries: red indicator only.
  - pads: each corner keeps the green→yellow→red pressure ramp.
- **Unmapped buttons (8 of 11).** `BasicSC_QuNeo` binds notes/CCs to only three
  physical buttons. The other eight render in the model but carry no
  `noteNum`/`pressCC`, so they stay dark until a note arrives on their channel:
  `buttonButton3` triangle-right, `buttonButton4..7` left-right arrows,
  `buttonButton8` rhombus, `buttonButton9..10` up-down arrows.
- **State persistence:** the QuNeo emits nothing on ALSA subscribe, so a bridge
  restart used to blank every control back to dark. `MidiWatcher` now accepts an
  optional `state_file`; `serve()` defaults it to
  `$XDG_STATE_HOME/super-quneo-collider/state.json`, reloads it on boot, and
  atomically re-saves on every CC/note mutation (temp file + `os.replace`). A
  missing or corrupt file degrades to an empty board, never a crash.

## Pad quadrant lighting ("4×4×4" surface) — landed 2026-11-22

Each physical pad resolves its press into a four-corner brightness field, not a
single binary face. `board.js` exposes `padCorners(control, cc, note)` which
reads the pad's `pressCC` and `xCC`/`yCC` (already tracked per-channel in
`/api/collider`) and returns `[bottom-left, bottom-right, top-left, top-right]`,
each corner 0..1 — or `null` when the pad is dark. `render.js` builds each pad
as four quadrant meshes driven directly by that array (16 pads × 4 = 64 touch
points); `pane.js` routes pads through `padCorners`. Backend capture and mapping
were already in place, so this was a frontend-only change.

Convention (QuNeo manual): X-Axis low→high is left→right, Y-Axis low→high is
bottom→top. The latched x/y position bilinearly spreads the press pressure
across the four corners — a centred finger lights all four evenly, an
off-centre finger favours the nearer corner. The pad is pressure-driven and
note-gated at the *board* level (`padCorners` is null while the note is off),
but the pane *latches* the last lit corners after release so the pad stays
aglow until the next press, matching the hardware. Pressure comes from
`pressCC` (falling back to full when that CC is unbound). Before the live x/y
position is first reported for a pad it stays dark.

No remaining work is outstanding from this milestone.

## Spike result (D3): PASSED on 2026-11-22

D3 acceptance is met. Full round-trip against a live scsynth:

- `/d_recv` (blob) delivered `bubbles` successfully via one-shot sclang.
- `/s_new "bubbles"` → node, no `/fail` (def stored and instantiable).
- `/s_get wobble` → 0.400 (the declared default).
- `/n_set 1000 wobble 10.0` → `/s_get wobble` → 10.000 (live arg change works).

## Verified mechanics (do not rediscover)

### scsynth boot

```
scsynth -u 57110 -B 127.0.0.1
```

- No backend flag; it auto-detects JACK (this box is pipewire-jack).
- Boots 48 kHz / block 1024, logs `SuperCollider 3 server ready`, binds UDP 127.0.0.1:57110.
- Keep it running in a background term for the spike; quit with the `quit` OSC msg or ctrl-c.

### One-shot sclang (the delivery mechanism)

- Invoke **by positional file, NOT stdin**: `sclang /path/script.scd`.
  - stdin (`sclang < script.scd`) fails: `SCLang Input: Operation not supported`.
  - `-D` is "no input" daemon mode (hangs with a script). Do not use it.
  - `-r` calls `Main.run` on startup.
- End every script with `0.exit` so sclang terminates (exit 0).
- `postln` goes to stdout. NOTE: stdout is **block-buffered** when redirected/piped,
  so a script killed by `timeout` loses its `postln` output. Use `stdbuf -oL -eL sclang
  ...` for line-buffered output, or write progress to your own file, when diagnosing.
- A syntax error does NOT exit: it prints `ERROR: Command line parse failed` and drops
  into the REPL, which then hangs on non-tty stdin. (This masqueraded as an "asBytes
  hang" during the spike — it was a parse error from bare `postln` after a `++` chain.)

### SynthDef delivery: sclang sends the blob, python never does

```
var addr = NetAddr("127.0.0.1", 57110);
var d = SynthDef("bubbles", { ... });
addr.sendMsg("/d_recv", d.asBytes);   // Int8Array -> OSC blob ('b')
0.exit;
```

- `SynthDef(...).asBytes` returns an `Int8Array` (1113 bytes for bubbles).
- sclang maps `Int8Array` → OSC blob `'b'`, which scsynth's `/d_recv` requires.
- `Server.remote(...).send(def)` does NOT work headless: its internal `serverRunning`
  check rejects the send ("server not running").

### Python (pyliblo3 0.17.0) control plane

- pyliblo3 handles `/s_new`, `/n_set`, `/s_get`, ints/floats/strings fine.
- `/s_get` replies arrive back as `/n_set` (args `[node_id, "param", value]`).

## Hard limits found (architecture consequences)

1. **pyliblo3 cannot send OSC blobs.** A python `bytes` argument is serialised as an OSC
   string `'s'` — truncated at the first NUL byte — and there is no `Blob` type exposed.
   Therefore python can NEVER `/d_recv` a SynthDef. The SPEC §8 fallback (pre-compiled
   `.scsyndef` + python `/d_recv`) is not viable on pyliblo3. sclang must deliver, at
   bridge startup only; it is idle for the rest of the run.

2. **pyliblo3 callback order is `(path, args, types, src)`**, where `args` is a list and
   `types` is the tag string (e.g. `'isf'`). This is the OPPOSITE of the comment in
   `queneo-editor/src/queneo_editor/services/osc_service.py:227`, whose `_handle_osc(self,
   path, types, args, src)` treats the second arg as the tag string. On pyliblo3 0.17.0
   that handler mis-parses real OSC messages (its `types` is actually the args list).
   The 35 unit tests pass only because they do not exercise a real pyliblo3 round-trip.
   → When porting `osc_service.py` to this project, use `cb(path, args, types, src)`.

## Port status (the real sc.py / osc_service.py port)

The port that the spike gated is DONE and shipped:

- [x] Use `cb(path, args, types, src)` — fixed the inherited callback order.
- [x] Deliver `bubbles` via a one-shot `sclang` subprocess at startup (`sc.py`).
- [x] Python control plane via pyliblo3: `/s_new` on trigger, `/n_set` mapping,
      `/s_get`/`numDefs` for the D3 defaults check.
- [x] No python `/d_recv` anywhere — it cannot work on pyliblo3.

## Spike scratch (throwaway, /tmp)

- `/tmp/deliver_def.scd` — the working sclang `/d_recv` delivery (reference for the port).
- `/tmp/spike_roundtrip.py` — the working pyliblo3 `/s_new`/`/n_set`/`/s_get` round-trip.
- `/tmp/asbytes_probe.scd`, `/tmp/sc_min.scd` — one-shot invocation + asBytes probes.
- `/tmp/synthdefs/bubbles.scsyndef` — compiled def (1113 bytes, `SCgf` magic).
- `/tmp/scsynth.log` — scsynth boot log.

## Environment facts

- scsynth / sclang both 3.13.0 at `/usr/bin/scsynth` and `/usr/bin/sclang`.
- toolchain venv: `.venv` in this project (CPython 3.14, pyliblo3 0.17.0); the
  queneo-editor venv remains at `/home/rjodouin/Documents/git/queneo-editor/.venv`.
- QuNeo ALSA client "QuNeo MIDI 1" resolves by NAME, never by number.
- Frontend is zero-build: three.module.js vendored, browser-harness tests run
  from `client/tests/index.html`.
