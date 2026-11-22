# super-quneo-collider — SPEC

A Gherkin specification. This is the design contract for the project, pending your
approval. Nothing in `src/` is implemented until this document is reviewed and agreed.

---

## 1. The problem, in one paragraph

A Keith McMillen QuNeo slider, touched on the physical board, changes the sound of a
running SuperCollider "bubbles" synth in real time, while a three.js model of that same
board lights up to show the change. The whole loop runs through a local Python bridge.

What we already have, tested and working:

- `op1-web` — a Python bridge that discovers an ALSA MIDI port by reading
  `/proc/asound/seq/clients`, pumps live events out of an `aseqdump` subprocess, exposes
  them as JSON at `/api/midi`, and lights a three.js model from that JSON. This is the
  MIDI-to-three.js pattern we are porting.
- `queneo-editor` — the three.js QuNeo board model (`LAYOUT.json` + `board.js`), and a
  `pyliblo3` OSC service that already sends OSC messages.
- `supercolliderjs` (crucialfelix) — the *approach* we adopt: a thin language client
  boots `scsynth`, compiles the SynthDef, and drives synth params over OSC. Its
  `examples/bubbles.js` is the exact synth and the exact values we reproduce.
- `supercollider-quarks/QuNeo` — the `BasicSC_QuNeo` preset that defines which MIDI
  note/CC each control emits.

---

## 2. System context

```
 +----------------+   MIDI (USB)     +-------------------------+
 |   QuNeo board  | ---------------> |  ALSA sequencer          |
 |  (real device) |   CC / note      |  (/proc/asound/seq/...)  |
 +----------------+                  +------------+------------+
                                                   | aseqdump subprocess
                                                   v
                          +------------------------------------------+
                          |  Python bridge  (super-quneo-collider)   |
                          |   - MIDI watcher (QuNeo port)            |
                          |   - slider -> param scaling (0-127)      |
                          |   - HTTP /api/collider (JSON state)      |
                          |   - OSC client -> scsynth                |
                          +-------+--------------------+-------------+
                                  | OSC (/s_new, /n_set) | HTTP JSON polling
                                  v                       v
                         +------------------+    +---------------------+
                         | scsynth (Ubuntu  |    | three.js board       |
                         | supercollider    |    | (ported midi pane +  |
                         | pkg, port 57110) |    |  quneo LAYOUT.json)  |
                         +------------------+    +---------------------+
```

Numbers flow one way: QuNeo slider -> MIDI CC -> bridge -> (a) OSC into scsynth, and
(b) JSON state into the three.js model. Nothing runs back to the board in this spec.

Preset loading is out of band: the `BasicSC_QuNeo` preset (or any custom preset we
later design) reaches the board only for testing, driven by a test-only rig that starts
queneo-editor's editor API server and flashes over its `/api/editor/send` endpoint (see
D6). This project never writes to the QuNeo at runtime and contains no auto-flashing
code.

---

## 3. Architecture decisions

D1. **The bridge is Python, not the supercolliderjs npm package.**
    supercolliderjs *boots* scsynth and *sends* OSC from Node. That is the approach we
    copy, but the client language is Python so we reuse the two already-tested assets:
    op1-web's MIDI watcher and queneo-editor's pyliblo3 OSC service. Rejected
    alternative: depend on Node + supercolliderjs, which duplicates the MIDI-to-three.js
    plumbing we already trust.

D2. **OSC via pyliblo3** (the `liblo`/`pyliblo3` import already present in
    `osc_service.py`). scsynth default address `127.0.0.1:57110`. Synth spawn is
    `/s_new`; live param change is `/n_set`; status is `/status`.

D3. **SynthDef delivery.** Faithful to supercolliderjs: a one-shot `sclang`
    invocation compiles and stores the `bubbles` SynthDef onto the running scsynth at
    bridge startup. After that the hot path (every slider tick) is pure Python + OSC,
    no sclang in the loop. (This is the one-spike risk — see section 8.)

D4. **The board model adopts the QuNeo quark control structure.** `LAYOUT.json` gains
    the same params the quark `QuNeo.sc` controls carry: `noteNum`, `pressCC`, `locCC`
    (plus `xCC`/`yCC` for drum pads, `widthCC` for the long slider) and `channel`. One
    mapping table (section 5) ties each board control id to these values from
    `BasicSC_QuNeo.scd`, so the three.js model and the MIDI watcher share one source of
    truth.

D5. **The base-test binding.** Three of the four vertical sliders drive the three
    `bubbles` params (section 5). This is the "values changed live by a QuNeo slider"
    acceptance test, matching `bubbles.js`'s own ranges (wobble 0-10, innerWobble 0-16,
    releaseTime 2-6).

D6. **Presets reach the real QuNeo board for testing only, via a test rig — never via
    this project's runtime.** super-quneo-collider's bridge never writes to the QuNeo;
    it only reads the MIDI the loaded preset emits. When a test needs a preset on the
    board, a test-only rig (`tests/helpers/quneo_flash.py`) starts queneo-editor's
    existing editor API server (`create_editor_app` in `queneo-editor/src/queneo_editor/
    editor/server.py`) with a MIDI `sender` callable wired to the QuNeo output port,
    then POSTs `/api/editor/send` (`{"name": <preset>, "slot": N}`) and
    `/api/editor/reload`. SysEx generation and MIDI output stay in queneo-editor (where
    they already work); the runtime bridge never imports or invokes the rig, and there
    is no auto-flashing.

---

## 4. Component and file layout

```
super-quneo-collider/
  SPEC.md                        <- this file
  README.md                      <- compact setup + run guide (idempotent)
  install.sh                     <- idempotent package install (supercollider, python deps)
  pyproject.toml                 <- python project, pytest
  src/super_quneo_collider/
    server.py                    <- HTTP server, /api/collider, boots scsynth + watcher
    midi.py                      <- QuNeo port discovery + aseqdump watcher (ported
                                    from op1-web midi.py, CC-aware)
    map.py                       <- slider -> param scaling (pure function, unit-tested)
    mapping.json                 <- control id -> noteNum/pressCC/locCC/channel + param
    sc.py                        <- scsynth lifecycle + OSC (/s_new, /n_set, /status)
    bubbles.scd                  <- the bubbles SynthDef (verbatim from bubbles.js)
    client/
      index.html                 <- ported midi pane + three.js board
      src/*.js                   <- board model, collider pane, poller, api
      vendor/three.module.js ...
      LAYOUT.json                <- queneo-editor layout, extended with MIDI params
  tests/
    helpers/
      quneo_flash.py              <- test rig: boots queneo-editor server, flashes a preset
    test_map.py
    test_midi.py
    test_sc.py
    test_server.py               <- /api/collider contract
  tests/e2e/                     <- gherkin-driven end-to-end (section 7)
```

---

## 5. The collider mapping (source of truth)

Vertical sliders (BasicSC preset, all on channel 15 — 0-indexed, i.e. MIDI channel 16):

| board id          | quark | noteNum | pressCC | locCC | synth param | range      |
|-------------------|-------|---------|---------|-------|-------------|------------|
| vSliderButton0    | VSlider | 20   | 60      | 61    | wobble       | 0.0 - 10.0 |
| vSliderButton1    | VSlider | 24   | 68      | 69    | innerWobble  | 0.0 - 16.0 |
| vSliderButton2    | VSlider | 28   | 76      | 77    | releaseTime  | 2.0 - 6.0  |
| vSliderButton3    | VSlider | 32   | 84      | 85    | (unbound)    |            |

Scaling is linear on the raw CC value `0..127`:

- `wobble      = round(raw/127 * 10, 3)`
- `innerWobble = round(raw/127 * 16, 3)`
- `releaseTime = round(2 + raw/127 * 4, 3)`

The `bubbles` SynthDef (verbatim from supercolliderjs `examples/bubbles.js`):

```
SynthDef("bubbles", { arg out=0, wobble=0.4, innerWobble=8, releaseTime=4;
  var f, zout;
  f = LFSaw.kr(wobble, 0, 24, LFSaw.kr([innerWobble, innerWobble / 1.106], 0, 3, 80)).midicps;
  zout = CombN.ar(SinOsc.ar(f, 0, 0.04), 0.2, 0.2, 4);
  zout = zout * EnvGen.kr(Env.linen(releaseTime: releaseTime), doneAction: 2);
  Out.ar(out, zout);
});
```

The full BasicSC table (pads, horizontal sliders, long sliders, buttons, circles) is the
appendix at the bottom; it feeds D4 so every board control carries a quark-compatible
note/CC, but only the three vertical sliders above are bound to synth params.

---

## 6. Gherkin features

### Feature: SuperCollider is available

Background:
  Given the `supercollider` Ubuntu package is installed

  Scenario: the server binary exists
    When the bridge resolves the scsynth binary
    Then the scsynth binary path exists and is executable

  Scenario: the language binary exists
    When the bridge resolves the sclang binary
    Then the sclang binary path exists and is executable

  Scenario: scsynth boots and answers status
    Given no scsynth is currently running
    When the bridge boots scsynth on 127.0.0.1:57110
    Then an /status OSC message is answered within 5 seconds
    And the reported numUgens is greater than 0

  Scenario: the bubbles SynthDef is loaded
    Given scsynth is running
    When the bridge loads the bubbles SynthDef via a one-shot sclang evaluation
    Then a /s_new for "bubbles" completes without error
    And the synth reports the default args wobble=0.4, innerWobble=8, releaseTime=4

  Scenario: boot is idempotent
    Given scsynth is already running and answered /status
    When the bridge boots scsynth again
    Then the bridge reuses the running server instead of spawning a second one

### Feature: QuNeo MIDI discovery

Background:
  Given the ALSA sequencer file `/proc/asound/seq/clients` is readable

  Scenario Outline: the QuNeo MIDI port is found
    Given the sequencer file contains "<client>", "<port>" for "<device>" "<portName>"
    When the watcher discovers the QuNeo port
    Then state.present is true
    And the port is "client:port"

    Examples:
      | device | portName        | client | port |
      | QuNeo  | QuNeo MIDI 1     | 20     | 0    |
      | QuNeo  | QuNeo MIDI 1     | 24     | 0    |

  Scenario: no QuNeo means not present
    Given the sequencer file contains no client named "QuNeo"
    When the watcher discovers the QuNeo port
    Then state.present is false

  Scenario Outline: a control-change event is parsed
    Given the watcher reads an aseqdump line for a Control change
    When the event is "channel 15, controller <cc>, value <raw>"
    Then the watcher records a slider event with cc=<cc> and raw=<raw>

    Examples:
      | cc | raw |
      | 61 | 64  |
      | 69 | 127 |
      | 77 | 0   |

  Scenario: events outside channel 15 are ignored
    Given the watcher reads an aseqdump line for a Control change
    When the event is "channel 7, controller 61, value 99"
    Then no slider event is recorded

### Feature: Slider value maps to a synth parameter

Scenario Outline: raw CC scales to the bound parameter
  Given the mapping binds locCC <cc> to parameter <param>
  When the raw value <raw> arrives
  Then the scaled value is <expected>

  Examples:
    | cc | param       | raw | expected |
    | 61 | wobble      | 0   | 0.0      |
    | 61 | wobble      | 63  | 4.961    |
    | 61 | wobble      | 127 | 10.0     |
    | 69 | innerWobble | 0   | 0.0      |
    | 69 | innerWobble | 64  | 8.063    |
    | 69 | innerWobble | 127 | 16.0     |
    | 77 | releaseTime | 0   | 2.0      |
    | 77 | releaseTime | 64  | 4.016    |
    | 77 | releaseTime | 127 | 6.0      |

Scenario: an unbound controller produces no parameter
  Given the mapping has no entry for locCC 85
  When the raw value 64 arrives on locCC 85
  Then no parameter value is produced

### Feature: Live synth update

Scenario: a slider change reaches the synth
  Given scsynth is running with a spawned "bubbles" synth at node <node>
  When the bridge receives locCC 61 value 127
  Then the bridge sends /n_set for node <node> with wobble=10.0

  Examples:
    | node |
    | 1000 |

Scenario: three sliders update independently
  Given scsynth is running with a spawned "bubbles" synth at node 1000
  When locCC 61 value 63 arrives
  And locCC 69 value 64 arrives
  Then /n_set is sent with wobble=4.961
  And /n_set is sent with innerWobble=8.063

### Feature: The bridge exposes state over HTTP

Scenario: the collider state endpoint
  Given the bridge and watcher are running
  When the client GETs /api/collider
  Then the response is JSON with a boolean "present"
  And a "sliders" object keyed by parameter name

Scenario Outline: a slider value appears in the API
  Given watcher state has <param> = <value>
  When the client GETs /api/collider
  Then sliders.<param> equals <value>

  Examples:
    | param       | value |
    | wobble      | 4.961 |
    | innerWobble | 8.063 |
    | releaseTime | 4.016 |

### Feature: The three.js board lights the slider

Scenario Outline: the model exposes a slider with quark params
  Given the board model is built from LAYOUT.json
  When the model looks up <boardId>
  Then the control carries channel 15, pressCC <pressCC> and locCC <locCC>

  Examples:
    | boardId         | pressCC | locCC |
    | vSliderButton0  | 60      | 61    |
    | vSliderButton1  | 68      | 69    |
    | vSliderButton2  | 76      | 77    |
    | vSliderButton3  | 84      | 85    |

Scenario Outline: a value lights the slider proportionally
  Given the board model is rendered
  When the collider pane applies <param> = <value>
  Then the slider's lit segment count reflects a value of <value> on its <param> range

  Examples:
    | param       | value | litFraction |
    | wobble      | 5.0   | 0.5         |
    | innerWobble | 16.0  | 1.0         |
    | releaseTime | 2.0   | 0.0         |

### Feature: The bubbles base test (end to end)

  Scenario: motion on the real QuNeo changes the sound and the board
    Given the QuNeo is connected and running the BasicSC preset (flashed by the
    test rig via queneo-editor's editor API server, per D6)
    And scsynth is running with the bubbles SynthDef and a spawned synth
    And the three.js board is open in a browser
    When I touch vertical slider 0 fully up
    Then the synth's wobble changes to 10.0 and the sound modulates
    And the vSliderButton0 model lights up fully
    When I touch vertical slider 2
    Then the synth's releaseTime changes on the 2.0 to 6.0 range
    And the vSliderButton2 model lights proportionally

---

## 7. Definition of Done

- `install.sh` is idempotent (re-runs are no-ops) and installs the `supercollider`
  package plus the Python deps into the project venv, on Ubuntu "resolute".
- Every Gherkin scenario above is automated: backend as `pytest` tests (the `behave`
  step layer is optional; `pytest` is the required runner), frontend via the existing
  queneo three.js test harness style.
- The MIDI watcher, mapping, and OSC client are pure/testable (injectable discovery
  and subprocess handles), so tests run with no hardware and no scsynth where stated,
  and with a real scsynth boot where stated.
- The hardware path (section 6, last feature) is exercised manually by the user, using
  `quneo-rig` to hold the board and camera, once the board position and camera mount
  are set up.
- Preset flashing is test-only: it is driven by `tests/helpers/quneo_flash.py`, which
  boots queneo-editor's editor server; the runtime bridge never imports, starts, or
  invokes it.

---

## 8. Open risks and the first validating spike

1. **SynthDef delivery (D3) — RESOLVED by the spike (2026-11-22).** One-shot sclang
   works: run `sclang script.scd` (positional file, NOT stdin) with a trailing `0.exit`.
   `SynthDef(...).asBytes` returns an `Int8Array`, and
   `NetAddr("127.0.0.1", 57110).sendMsg("/d_recv", bytes)` delivers it as an OSC blob.
   Python then drives the control plane over pyliblo3: `/s_new` → `/n_set` → `/s_get`
   (verified live: `wobble` default 0.4 → 10.0). The stated fallback (pre-compiled
   `.scsyndef` loaded via python `/d_recv`) is NOT viable: pyliblo3 0.17.0 serialises a
   python `bytes` argument as an OSC string (truncated at the first NUL byte) and exposes
   no blob type. So sclang stays in the delivery path — but one-shot at bridge startup
   only; it is idle for the rest of the run.

2. **aseqdump Control-change line format** differs from the Note format already parsed
   in op1-web. The CC regex is new and is unit-tested against a captured real
   `aseqdump` output snippet before hardware is involved.

3. **QuNeo channel.** BasicSC puts everything on channel 15 (0-indexed, MIDI channel
   16). The watcher filters on this; if the board ships a different default on this
   machine, the channel lives in `mapping.json`, not hard-coded.

---

## Appendix — full BasicSC_QuNeo mapping (from the QuNeo quark)

Drum pads (each: noteNum, pressCC, xCC, yCC, channel 15):

```
createDrumPad(00, 00, 00, 01, 02, 15)  ... createDrumPad(15, 15, 45, 46, 47, 15)
```
(note = index, pressCC = index, xCC = index+1, yCC = index+2)

Horizontal sliders (noteNum, pressCC, locCC, channel 15):

```
createHSlider(00, 39, 092, 093, 15)  createHSlider(01, 43, 100, 101, 15)
createHSlider(02, 47, 108, 109, 15)  createHSlider(03, 51, 116, 117, 15)
createHSlider(04, 40, 094, 095, 15)  createHSlider(05, 44, 102, 103, 15)
createHSlider(06, 48, 110, 111, 15)  createHSlider(07, 52, 118, 119, 15)
createHSlider(08, 41, 096, 097, 15)  createHSlider(09, 45, 104, 105, 15)
createHSlider(10, 49, 112, 113, 15)  createHSlider(11, 53, 120, 121, 15)
createHSlider(12, 42, 098, 099, 15)  createHSlider(13, 46, 106, 107, 15)
createHSlider(14, 50, 114, 115, 15)  createHSlider(15, 54, 122, 123, 15)
```

Vertical sliders (noteNum, pressCC, locCC, channel 15):

```
createVSlider(00, 20, 60, 61, 15)  createVSlider(01, 24, 68, 69, 15)
createVSlider(02, 28, 76, 77, 15)  createVSlider(03, 32, 84, 85, 15)
createVSlider(04, 21, 62, 63, 15)  createVSlider(05, 25, 70, 71, 15)
createVSlider(06, 29, 78, 79, 15)  createVSlider(07, 33, 86, 87, 15)
createVSlider(08, 22, 64, 65, 15)  createVSlider(09, 26, 72, 73, 15)
createVSlider(10, 30, 80, 81, 15)  createVSlider(11, 34, 88, 89, 15)
createVSlider(12, 23, 66, 67, 15)  createVSlider(13, 27, 74, 75, 15)
createVSlider(14, 31, 82, 83, 15)  createVSlider(15, 35, 90, 91, 15)
```

Long sliders (noteNum, pressCC, locCC, widthCC, channel 15):

```
createLSlider(00, 16, 48, 49, 50, 15)  createLSlider(01, 17, 51, 52, 53, 15)
createLSlider(02, 18, 54, 55, 56, 15)   createLSlider(03, 19, 57, 58, 59, 15)
```

Buttons (noteNum, pressCC, channel 15):

```
createButton(00, 36, 124, 15)  createButton(01, 37, 125, 15)  createButton(02, 38, 126, 15)
```

Circle controls (noteNum, pressCC, locCC, channel 14):

```
createCircle(00, 00, 00, 01, 14)  createCircle(01, 04, 08, 09, 14)
createCircle(02, 01, 02, 03, 14)  createCircle(03, 05, 10, 11, 14)
createCircle(04, 02, 04, 05, 14)  createCircle(05, 06, 12, 13, 14)
createCircle(06, 03, 06, 07, 14)  createCircle(07, 07, 14, 15, 14)
```
