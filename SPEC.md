# super-quneo-collider — SPEC

A Gherkin specification. This is the design contract for the project, pending your
approval. Nothing in `src/` is implemented until this document is reviewed and agreed.

---

## 1. The problem, in one paragraph

A Keith McMillen QuNeo slider, touched on the physical board, changes the sound of a
running SuperCollider "bubbles" synth in real time, while a three.js model of that same
board mirrors its lit/unlit state across the full control surface (pads, sliders,
buttons, rotaries), so the model is a live picture of the physical board, not just a
readout of the three bound sliders. The whole loop runs through a local Python bridge.

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

Beyond `bubbles`, the bridge is growing a small catalog of audio examples: each
supercolliderjs `examples/` entry whose point is *manipulating sound* (not booting the
language/server, logging, or loading defs) becomes a selectable entry in the front-end
UI. `bubbles` is the first and default member of that catalog, not the whole program
(section 9).

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
(b) JSON state into the three.js model. One narrow exception, added after the spike:
the admin reset (`POST /api/collider/reset`, plus the reset the page fires as it loads)
sends the board a preset reload so a stale board can be blanked from the UI. It writes
no preset and changes no mapping: slot 0, the configuration the board already runs, is
re-selected.

Preset loading is out of band: the `BasicSC_QuNeo` preset (or any custom preset we
later design) reaches the board only for testing, driven by a test-only rig that starts
queneo-editor's editor API server and flashes over its `/api/editor/send` endpoint (see
D6). Apart from the admin reset above, this project never writes to the QuNeo at runtime
and contains no auto-flashing code.

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

D7. **A catalog of audio examples replaces the hard-coded `bubbles` binding.** `bubbles`
    becomes one of four selectable examples (`bubbles`, `formant`, `sine`, `klang`), each
    a verbatim — or minimally reshaped — supercolliderjs `examples/` SynthDef plus a list
    of `param -> control` bindings. The control surface is preset 0 (BasicSC) only: no
    new preset is flashed, and every example binds onto the SAME fixed controls the board
    already emits, in a fixed order (vSliders first, then hSliders, then the channel-14
    rotaries). All four SynthDefs are delivered at boot through the same one-shot sclang
    `/d_recv` path as `bubbles` (D3), so switching examples is a pure control-plane event:
    no compile, no board write, and the hot path stays Python + OSC. The example registry
    lives in `catalog.json`; `mapping.json` keeps only the fixed MIDI inventory
    (`channel`/`noteNum`/`pressCC`/`locCC`), and its `bubbles`-specific `param`/`min`/
    `max` move into the catalog's `bubbles` entry.

D8. **Exactly one example is active at a time; selection is a low-frequency write.** The
    front end owns a `<select>` (top-left of the board). Choosing an entry POSTs its id;
    the bridge swaps the active example, re-binds the slider scaling, and the next QuNeo
    activity spawns a fresh node from the newly active SynthDef. A mapping helper text,
    derived from the catalog (never hand-written), renders next to the select so the user
    sees which control drives which parameter for the current example.

D9. **The catalog spans every sourced SynthDef collection, and every example declares a
    gesture type.** On top of the four supercolliderjs entries (D7), the catalog adds the
    four SuperCollider documentation examples (`supercollider.github.io/examples.html`), all
    109 SCLOrkSynths SynthDefs (SCLOrkHub, 11 banks: bass, bells, drums, guitar, keyboards,
    misc, organ, pads, percussion, strings, winds), and the community collections catalogued
    in section 9.9. Every entry carries a `gesture`, either `continuous` or `oneshot`:

    - `continuous` — a synth with a `gate` argument (a sustained ADSR held while a pad is
      down) or a self-running drone. Its parameters bind to the slider/rotary ladder of
      9.2; a pad press sends gate=1 and a release sends gate=0. This is the `bubbles` model.
    - `oneshot` — a synth whose own envelope self-frees (Env.perc/Env.sine/Env.linen with
      doneAction: 2 and no `gate` arg). It binds to a pad CORNER, not a slider: pressing
      the corner sends /s_new and the synth frees itself. The 16 pads x 4 quadrants yield
      64 corners (see the appendix). Unpitched one-shots (kicks, claps, hats) fire at fixed
      args; pitched one-shots (kalimba, bells, plucks) read their pitch from the corner, so
      one example plays a scale across the grid. Any trailing timbre args still bind to a
      reserved slider when the user wants to shape the sound.

    The gesture is read off the SynthDef, never guessed: a `gate` arg implies `continuous`,
    and a doneAction:2 perc/sine envelope with no `gate` implies `oneshot`. Selection
    remains single-active (D8); a simultaneous multi-corner drum "kit" is a later
    increment and is out of scope here.

D10. **A voice is never a surprise: the bridge owns it, stops it on command, and caps its
    life.** Three rules, all enforced in the SynthDef wrapper rather than in the bridge,
    so they hold for every example and cannot be bypassed by a rogue def:

    - **One live voice per continuous example.** The bridge picks the node id (never
      `-1`), tracks it, and sends further activity for that example as `/n_set` on the
      live node. `oneshot` entries spawn per hit and are tracked the same way. When
      scsynth reports `/n_end` the bridge forgets the id (it needs `/notify 1`, which
      `boot()` sends), so a dead node is never retuned. The old behaviour — `/s_new`
      with an auto-assigned id on every CC — is what left `sine` droning forever.
    - **A 3 s stop fade.** Every def carries `gate` (`1` by default). A new selection, a
      release, or a change of ceiling mode sends `gate=0`, which runs
      `Env.asr(0.01, 1, 3)`, so sound fades out instead of clicking off. Nothing sounds
      at boot: `start()` loads defs and binds controls, but spawns nothing.
    - **A 12 s ceiling, optional at runtime.** A gate-independent
      `Env.new([0, 1, 1, 0], [0.01, 9, 3])` fades any voice out at 12 s, whatever the def
      does on its own. It must not be driven by `gate`, because an `EnvGen` with an open
      gate holds at its release node forever and would never free the node. The def
      argument `fade` (1 by default) is the switch: `fade=0` replaces the ceiling with a
      constant, so the voice rings until its gate closes or it goes silent. `free` is
      always owned by `DetectSilence` (doneAction 2), never by an example's own envelope
      (those are demoted to doneAction 0), so no voice leaks in either mode. The front end
      exposes the switch as a checkbox beside the `<select>`, backed by
      `POST /api/collider/fade` and `fadeEnabled` on `/api/collider`; the bridge is the
      state of record, and the page mirrors it on every poll.

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
    mapping.json                 <- control id -> noteNum/pressCC/locCC/channel (fixed
                                    preset-0 MIDI inventory; carries no per-example param)
    catalog.json                 <- example registry: id/label/gesture/SynthDef/param ->
                                    control bindings (source, corner, ranges, curves). It is
                                    the select's options + helper text + corner assignment
    sc.py                        <- scsynth lifecycle + OSC (/s_new, /n_set, /status)
    bubbles.scd                  <- the bubbles SynthDef (verbatim from bubbles.js)
    formant.scd                  <- the formant SynthDef (verbatim from formant.scd)
    sine.scd                     <- the sine SynthDef (reshaped from sine-wave.js)
    klang.scd                    <- the klang SynthDef (nPartials/nChans promoted to args)
    examples/*.scd               <- the 4 documentation examples, reshaped into named defs
    sclork/                      <- the SCLOrkSynths bank, vendored + loaded by its loader
    client/
      index.html                 <- ported midi pane + three.js board (top-left <select>)
      src/*.js                   <- board model, collider pane, poller, api + select.js
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
appendix at the bottom. It is realized in `mapping.json` as a 30-control MIDI inventory
(16 pads + 4 hSliders + 4 vSliders + 1 lSlider + 3 lit buttons + 2 rotaries), each
carrying its `channel`/`noteNum`/`pressCC`/`locCC` (and `xCC`/`yCC`/`widthCC` where the
kind needs them). The watcher tracks live CC and note state for every control, keyed by
MIDI channel so the channel-14 rotaries do not collide with channel-15 pad `xCC`/`yCC`.
Only the three vertical sliders above are bound to synth params. That binding is the
`bubbles` entry of the example catalog; when a different example is selected (section 9),
the same three sliders re-bind to that example's parameters.

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
  And a "cc" object of raw CC values keyed by channel then CC number
  And a "note" object of note on/off keyed by channel then note number

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

### Feature: The three.js board mirrors the full control surface

Scenario Outline: a slider lights along its fill direction
  Given the board model is rendered
  When the collider applies channel <channel> locCC <cc> = <value>
  Then the control's lit fraction is <fraction>, filled toward <direction>

  Examples:
    | channel | cc | value | fraction | direction |
    | 15      | 61 | 127   | 1.0      | top       |
    | 15      | 61 | 0     | 0.0      | top       |
    | 15      | 93 | 64    | ~0.5     | right     |
    | 15      | 49 | 64    | ~0.5     | right     |
    | 14      | 1  | 32    | ~0.25    | ring      |

Scenario: LED colour is fixed per position, not a value ramp
  Given the board model is rendered
  Then a slider lights a fixed 8-light ladder — 3 green, 2 yellow, 3 red — and the
    value chooses how many light, never the hue
  And the long slider (crossfader) lights a fixed 17-light run (3 red, 3 green,
    2 yellow, centre blue, 2 yellow, 3 green, 3 red) swept by a 3-light window,
    so only three are lit at a time
  And a rotary shows a single red position indicator, never a colour ramp
  And each pad corner keeps its green-yellow-red pressure ramp

Scenario Outline: a pressed pad lights a four-corner field from pressure and position
  Given channel 15 note <note> is on
  And the pad's live xCC reads <x>, yCC reads <y> and pressCC reads <press>
  Then the pad with noteNum <note> lights corners [<bl>, <br>, <tl>, <tr>]

  Examples:
    | note | x   | y   | press | bl  | br  | tl  | tr  |
    | 0    | 0   | 0   | 127   | 1   | 0   | 0   | 0   |
    | 0    | 127 | 0   | 127   | 0   | 1   | 0   | 0   |
    | 0    | 0   | 127 | 127   | 0   | 0   | 1   | 0   |
    | 0    | 127 | 127 | 127   | 0   | 0   | 0   | 1   |
    | 0    | 64  | 64  | 127   | ~0.25 | ~0.25 | ~0.25 | ~0.25 |
    | 15   | 127 | 127 | 127   | 0   | 0   | 0   | 1   |

Scenario: a pad latches its lit corners after release
  Given channel 15 pad note 0 was pressed and lit some corners
  When channel 15 note 0 turns off
  Then the pad with noteNum 0 keeps those corners lit

Scenario: a pad stays dark until its x/y location is first reported
  Given the board model is rendered
  When channel 15 note 0 turns on
  And no xCC or yCC has been reported for that pad
  Then the pad with noteNum 0 goes dark

Scenario: channel 14 and channel 15 do not collide
  Given the cc map holds channel 15 CC 1 = 100 (pad xCC)
  And the cc map holds channel 14 CC 1 = 10 (rotary locCC)
  Then padButton0 and rotaryButton0 light from their own channel's value

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

### Feature: Select a sound example

Scenario: the example catalog is exposed
  Given the bridge is running
  When the client GETs /api/collider
  Then the response lists examples "bubbles", "formant", "sine", "klang"

Scenario: bubbles is the default active example
  Given the bridge is running
  When the client GETs /api/collider
  Then activeExample equals "bubbles"

Scenario: every example binds at least one parameter
  Given the catalog of examples
  Then every example maps at least one parameter to a control

Scenario Outline: an example's variables scale to the bound control
  Given example "<example>" is active
  When locCC <cc> arrives with raw <raw>
  Then parameter "<param>" equals <expected>

  Examples:
    | example | cc | raw | param        | expected |
    | formant | 61 | 127 | fundfreq     | 10240.0  |
    | formant | 61 | 0   | fundfreq     | 40.0     |
    | sine    | 61 | 127 | freq         | 2000.0   |
    | klang   | 61 | 127 | nPartials    | 32       |
    | klang   | 69 | 127 | nChans       | 8        |

Scenario Outline: selecting an example re-binds the control surface
  Given example "bubbles" is active
  When the client selects "<example>"
  Then activeExample equals "<example>"
  And locCC 61 now scales to parameter "<param>"

  Examples:
    | example | param     |
    | formant | fundfreq  |
    | sine    | freq      |
    | klang   | nPartials |

Scenario: selecting an example shows the mapping helper text
  When the client selects "formant"
  Then the UI shows helper text naming each control-to-parameter binding for "formant"
  And the helper text is derived from the catalog, not hard-coded

Scenario: selecting an example never writes to the board
  Given the bridge is running and preset 0 is loaded
  When the client selects "sine"
  Then no preset is flashed and no MIDI is sent to the QuNeo

Scenario: the catalog covers every sourced collection
  Given the bridge is running
  When the client GETs /api/collider
  Then the response lists at least 117 examples
  And the list includes "kick808", "superSaw", "kalimba" and "Simple FM"
  And the list includes "bass8", "brute" and "sStream_Saw" from the section 9.9 sources

Scenario: the catalog lists each def name only once
  Given the catalog of examples
  Then no two examples share a normalised def name

Scenario: every example declares a gesture
  Given the catalog of examples
  Then every example declares a gesture of "continuous" or "oneshot"

Scenario Outline: a one-shot example triggers on a pad corner
  Given example "<example>" is active and is a one-shot
  When the user presses pad <pad> in quadrant <quadrant>
  Then the bridge sends /s_new for "<def>"
  And the helper text names "pad <pad>" and quadrant "<quadrant>"

  Examples:
    | example | pad | quadrant | def      |
    | kick808 | 3   | 3        | kick808  |
    | kalimba | 0   | 2        | kalimba  |

Scenario Outline: a pitched one-shot reads its pitch from the corner
  Given the "kalimba" example is active
  When the user presses corner index <index>
  Then /s_new for kalimba is sent with freq <freq>

  Examples:
    | index | freq   |
    | 0     | 220.0  |
    | 63    | 880.0  |

Scenario Outline: a continuous example re-binds the slider ladder
  Given "superSaw" is active
  When locCC <cc> arrives with raw <raw>
  Then parameter "<param>" equals <expected>

  Examples:
    | cc | raw | param       | expected |
    | 61 | 0   | detuneRatio | 1.0      |
    | 61 | 127 | detuneRatio | 1.05     |
    | 69 | 0   | spread      | 0.0      |
    | 69 | 127 | spread      | 1.0      |

Scenario: a gated example opens and closes on a pad press
  Given "superSaw" is active
  When channel 15 pad note 0 turns on
  Then /s_new for superSaw is sent with gate=1
  When channel 15 pad note 0 turns off
  Then /n_set for the spawned node is sent with gate=0

### Feature: Nothing outlives its welcome

Scenario: nothing sounds until the QuNeo is touched
  Given the bridge has just started
  Then no node has been spawned
  And /api/collider reports voices as an empty list

Scenario: the bridge owns the voice it starts
  Given example "sine" is active
  When locCC 61 arrives with raw 64
  Then /s_new for sine is sent once with a bridge-chosen node id
  And that id appears in /api/collider voices

Scenario: further activity retunes the live voice
  Given a voice is sounding for "sine"
  When locCC 61 arrives again
  Then no second /s_new is sent
  And the live node receives /n_set

Scenario: a voice is freed at the 12 s ceiling
  Given the ceiling is on
  When a voice is spawned
  Then scsynth frees it about 12 s later, through the stop fade
  And /api/collider stops reporting it

Scenario: a stop fades over 3 s rather than cutting
  Given a voice is sounding
  When the bridge stops it
  Then its gate closes and the sound fades out over about 3 s

Scenario: selecting an example stops the sounding voice
  Given a voice is sounding for "sine"
  When the client selects "formant"
  Then the sounding node receives gate=0
  And the next QuNeo activity spawns from the newly active example

Scenario: the 12 s ceiling can be switched off and on
  Given the bridge is running with the ceiling on
  When the client POSTs /api/collider/fade {"enabled": false}
  Then /api/collider reports fadeEnabled false
  And the next voice rings past 12 s until something stops it
  When the client POSTs /api/collider/fade {"enabled": true}
  Then the ceiling is back on
  And any voice sounding at that moment stops through the 3 s fade

Scenario: the fade checkbox beside the select shows the bridge's state
  Given the client page is open
  Then the checkbox reflects fadeEnabled from /api/collider
  And a bridge that omits fadeEnabled leaves the ceiling on

Scenario: toggling the checkbox writes to the bridge
  When the user toggles the checkbox
  Then the client POSTs the new value to /api/collider/fade
  And re-renders from the reply
  And a failed POST is shown in the helper text instead of thrown

Scenario: the bridge rejects a non-boolean ceiling
  When the client POSTs /api/collider/fade {"enabled": "yes"}
  Then the bridge answers 400

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
- The board mirror is full-surface: the bridge tracks CC and note state per MIDI
  channel, `/api/collider` exposes `cc` and `note` alongside `sliders`, and the
  three.js model lights every control type (vSlider fills to the top, h/lSlider to the
  right, pads latched after release — dark only before the first press — buttons
  latched, rotaries on a ring).
- Preset flashing is test-only: it is driven by `tests/helpers/quneo_flash.py`, which
  boots queneo-editor's editor server; the runtime bridge never imports, starts, or
  invokes it.
- The front end shows a `<select>` in the top-left listing the 117 catalog examples
  (grouped by source), defaulting to `bubbles`. Selecting an entry re-binds the bridge and
  shows the mapping helper text, derived from `catalog.json`.
- Every voice is owned and bounded, per D10: nothing sounds at boot, further activity
  retunes the live node instead of stacking new ones, a selection or release closes the
  gate into a 3 s fade, and a gate-independent 12 s ceiling frees anything still running.
  The ceiling is switchable from a checkbox beside the select (`POST /api/collider/fade`,
  `fadeEnabled` on `/api/collider`), with the bridge as the state of record. Both modes
  are proven on a real scsynth: capped at ~12.5 s with the ceiling on, still ringing at
  13.5 s with it off, and ~3.5 s from gate=0 to the node's end.
- Every example maps at least one variable to a control, all on the preset-0 (BasicSC)
  surface; no new preset is flashed and selection never writes to the board.
- All 117 SynthDefs are delivered at boot in one sclang batch (the SCLOrkSynths loader
  plus the documentation and supercolliderjs defs, same one-shot `/d_recv` path), so
  switching examples performs no compile and keeps the hot path pure Python + OSC.
- Every entry binds at least one parameter: `continuous` entries on the slider/rotary
  ladder, `oneshot` entries on a pad corner (with a reserved slider for any trailing
  timbre arg). The gesture is read off each SynthDef, never hand-assigned.

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

## 9. The example catalog

The QuNeo is locked to preset 0 (BasicSC, flashed to slot 0). Nothing here adds a new
preset: the catalog reuses the SAME fixed control surface the board already emits, and
re-binds it per example. This is the supercolliderjs approach made multi-option — each
entry is exactly what `bubbles` already is: a SynthDef plus a list of `param -> control`
bindings. `bubbles` is simply the default and first entry.

### 9.1 Which examples are in

Four of the sixteen `examples/` entries are audio manipulation (a self-contained audible
SynthDef whose sound you shape). The rest are language/server/utility demos and are out:

| file | example | note |
|------|---------|------|
| `bubbles.js`   | bubbles | verbatim (the current spec synth) |
| `formant.scd`  | formant | verbatim, incl. its `Spec.specs` exp curves |
| `sine-wave.js` | sine    | reshaped from dryadic `|freq| SinOsc.ar(freq)` into a named SynthDef |
| `klang.scd`    | klang   | reshaped: `nPartials`/`nChans` promoted from `var` to `arg` |

Excluded (language/server/utility): `boot-lang.js`, `lang-interpret.js`,
`lang-interpret-the-long-way.js`, `logger.js`, `server.js`, `server-plus.js`,
`server-plus-promises.js`, `serverp`, `package.json`/`package-lock.json` — and two that
produce sound but exist to demonstrate API mechanics rather than sound manipulation:
`synthdef-and-synth.js` (a SynthDef-loading walkthrough) and
`dryads-synth-event-list.js` (a drum-scheduler demo whose frequencies are random).

Further sources extend the catalog: the four SuperCollider documentation examples
(section 9.7), all 109 SCLOrkSynths SynthDefs (section 9.8), and the community collections
found in the GitHub survey of section 9.9. The first three sources give 117 entries
(4 supercolliderjs + 4 documentation + 109 SCLOrkSynths); section 9.9 adds roughly 190
deduplicated instrument SynthDefs on top, growing the select to about 300 entries. The
exact per-entry list is fixed at authoring time by the dedupe key of 9.9.1.

### 9.2 Example parameters and their QuNeo bindings

One example is active at a time; the same physical controls are re-bound to that
example's parameters. Binding order is fixed and top-to-bottom: vSlider0 → vSlider1 →
vSlider2 → vSlider3, then hSliders, then the channel-14 rotaries. The first variable of
an example always lands on vSlider0, and a one-variable example (sine) uses only that
one slider. This is the direct generalization of "bubbles is mapped to the vSliders".

| example  | vSlider0 (cc 61) | vSlider1 (cc 69) | vSlider2 (cc 77) | vSlider3 (cc 85) | extra |
|----------|------------------|------------------|------------------|------------------|-------|
| bubbles  | wobble 0–10 (lin) | innerWobble 0–16 (lin) | releaseTime 2–6 (lin) | — | — |
| formant  | fundfreq 40–10240 (exp) | formantfreq 40–10240 (exp) | bwfreq 40–10240 (exp) | timeScale 0.1–4 (lin) | pan −1–1 → rotary0 (ch14 cc 1) |
| sine     | freq 40–2000 (exp) | — | — | — | — |
| klang    | nPartials 1–32 (int) | nChans 1–8 (int) | — | — | — |

Defaults and curves track the source: `fundfreq`/`formantfreq` default 440, `bwfreq`
100; `sine.freq` defaults 440; `klang.nPartials` defaults 12 and `nChans` 5. Integer
parameters (`nPartials`, `nChans`) scale the raw CC to a rounded integer.

### 9.3 Reshapes (and why they stay faithful)

- **sine** — `sine-wave.js` compiles `|freq| SinOsc.ar(freq)` through the dryadic
  API. We express the same graph as `SynthDef("sine", { arg out=0, freq=440;
  Out.ar(out, SinOsc.ar(freq)); })` so it can be delivered and driven over OSC like
  `bubbles`. No timbre change.
- **klang** — `klang.scd` has no `arg`s; `nPartials` (12) and `nChans` (5) are local
  `var`s and the partial frequencies are `rrand`-generated at build time. We promote
  `nPartials` and `nChans` to `arg`s and keep the random 200–2000 Hz partials
  (re-rolled per spawn). This is the only reshape that changes a definition's shape;
  it exists solely to give the example at least one controllable variable.

### 9.4 Data model — `mapping.json` vs `catalog.json`

- `mapping.json` keeps its role as the FIXED preset-0 MIDI inventory: which
  `channel`/`noteNum`/`pressCC`/`locCC` each control emits. It drops its three
  `bubbles`-specific `param`/`min`/`max` fields.
- `catalog.json` is the new source of truth for the select and the helper text:

```json
{
  "default": "bubbles",
  "examples": {
    "formant": {
      "def": "formant",
      "source": "formant.scd",
      "params": [
        {"name": "fundfreq",    "control": "vSliderButton0", "cc": 61, "min": 40, "max": 10240, "curve": "exp", "default": 440},
        {"name": "formantfreq", "control": "vSliderButton1", "cc": 69, "min": 40, "max": 10240, "curve": "exp", "default": 440},
        {"name": "bwfreq",      "control": "vSliderButton2", "cc": 77, "min": 40, "max": 10240, "curve": "exp", "default": 100},
        {"name": "timeScale",   "control": "vSliderButton3", "cc": 85, "min": 0.1, "max": 4.0, "curve": "lin", "default": 1},
        {"name": "pan",         "control": "rotaryButton0",  "cc": 1, "channel": 14, "min": -1, "max": 1, "curve": "lin", "default": 0}
      ]
    }
  }
}
```

Each `param`'s `control` names a `mapping.json` control id, so the binding resolves its
MIDI identity through the inventory (never a duplicated literal).

### 9.5 Selection and helper text

- `/api/collider` gains `examples` (the ordered id list) and `activeExample` fields.
- `POST /api/collider/example` with `{"id": "formant"}` switches the active example:
  the bridge re-binds the slider scaling and the next QuNeo activity spawns a fresh
  node from the newly active SynthDef. No compile, no board write.
- The front end renders a `<select>` in the top-left corner from `examples`, defaulting
  to `bubbles`. On change it POSTs the id, then re-renders.
- A `fade` checkbox sits beside the select, checked by default, exposing the 12 s ceiling
  of D10. The bridge holds the state (`fadeEnabled`), so the page re-renders the box from
  each poll rather than trusting its own memory, and a toggle POSTs
  `/api/collider/fade {"enabled": <bool>}`.
- A helper text under the select is re-generated from the active example's `params`,
  one line per binding, e.g. for `formant`:

```
vSlider0 -> fundfreq     40-10240 Hz (exp)
vSlider1 -> formantfreq  40-10240 Hz (exp)
vSlider2 -> bwfreq       40-10240 Hz (exp)
vSlider3 -> timeScale    0.1-4.0
rotary   -> pan          L..R
```

### 9.6 Trigger surfaces: sliders for continuous, corners for one-shots

Every entry carries a `gesture` (D9) that decides its primary control surface.

`continuous` examples use the slider/rotary ladder of 9.2 unchanged. A gated synth also
uses a pad press as its note: press = gate=1 (spawn), release = gate=0 (release). A
self-running drone needs no note; it starts when selected and frees when deselected.

`oneshot` examples use the 64-corner pad surface. The corner is the trigger: a press on
corner `c` sends `/s_new` for the example's SynthDef, and the synth's doneAction frees it.
Corner addressing is `pad` (0..15) x `quadrant` (0..3), flattened to an index 0..63 where
index = pad*4 + quadrant. Two one-shot flavors:

- Unpitched (kick808, claps, hats): the corner fires the sound at its default args. A
  trailing timbre arg (`dist`, `ringTime`) binds to a reserved slider so the sound is still
  shapable — that is the "min 1" control.
- Pitched (kalimba, bells, plucks, marimba): the corner also sets pitch. The corner index
  maps to `freq` over a musical range, so a single example plays a scale across the grid
  (e.g. index 0..63 -> 220 Hz to 880 Hz). A trailing timbre arg (`mix`, `clickRel`) binds
  to a reserved slider.

Helper text names the corner for a one-shot (e.g. "pad 3 · top-right -> kick808") instead
of a slider binding. Selection stays single-active (D8); a kit that arms many corners at
once is deferred.

### 9.7 The SuperCollider documentation examples

`examples.html` showcases four examples. Three are `.play` functions or a `Pbind`
performance, not catalog-shaped SynthDefs, so each is reshaped into a named, OSC-driven
def as needed (the same rule as `sine`/`klang` in 9.3). All four are in:

| example    | gesture             | min-1 binding                                   | note |
|------------|---------------------|-------------------------------------------------|------|
| Simple FM  | continuous (drone)  | vSlider0 -> modRate (0.1-20 Hz)                 | `[1,3]` LFO exprange promoted to args |
| Chainsaw   | continuous (drone)  | vSlider0 -> amp (level)                         | self-running noise machine |
| Drummer    | continuous (drone)  | vSlider0 -> tempo                               | self-running bdrum/snare/hihat pattern |
| Gabber Rave| mixed               | gabberkick -> corner (oneshot); hoover -> pad + vSlider0 -> freq | two defs + a kick loop |

The three drones run for as long as they are selected and free on deselect; Gabber Rave
exposes its one-shot kick on a corner and its gated `hoover` lead on the pad/slider path.

### 9.8 SCLOrkSynths — the standard-arg convention and the 11 banks

SCLOrkSynths ships 109 SynthDefs grouped in 11 banks. They share a documented standard-arg
convention, which is what makes a deterministic (not hand-guessed) binding possible:

```
out = 0      pan = 0      freq = 440 (pitched synths only)
amp ~ 0.1-0.2   att = 0.01 (0.001 for percussive)   dec = 0.1   sus = 1
rel ~ 1 (up to ~3)   gate = 1 (ADSR synths only)    crv/curve = -8
```

Every synth adds a handful of bespoke timbre args on top (count, spread, detuneRatio,
blend, dist, mix, ringTime, clickRel, ...). Because `freq`/`amp`/`att`/`rel` are always
present, every one of the 109 has at least one bindable parameter — "min 1" holds by
construction.

Gesture is read off each def (D9): a `gate` arg -> `continuous` (pads, organ, strings,
wind, keyboards, lead bass and guitar voices, sustained pads), otherwise a
doneAction:2 perc envelope -> `oneshot` (all 31 drums, all 9 percussion, the 6 bells,
plucks, harpsichord, and percussive bass like `subBass1`/`acidOto309`).

Banks (109 total):

```
bass (13)         acidOto3091, acidOto3092, bassWarsaw, combs, doubleBass, fmBass,
                  ikedaBass, ksBass, moogBass, noQuarter, rubberBand, subBass1, subBass2
bells (6)         glockenspiel, prayerBell, pulseRisset, rissetBell, sosBell, tubularBell
drums (31)        blueNoise, clapElectro, clapGray, clapOto309, cymbal808, cymbalicMCLD,
                  hashercymbal, hihat1, hihatElectro, kick1, kick808, kickBlocks, kickRingz,
                  kick_chirp, kick_electro, kick_oto309, kik3, kraftySnare, neuroSnare,
                  oneclapThor, purpleNoise, snare1, snare909, snareElectro, snareOto309,
                  snareStein, sosHats, sosKick, sosSnare, sosTom, squareDrum
guitar (3)        distortedGuitar, modalElectricGuitar, pluck
keyboards (8)     cheapPiano1, cs80leadMH, defaultB, everythingRhodes, FMRhodes1,
                  FMRhodes2, harpsichord1, harpsichord2
misc (19)         beating, blip1, chaoscillator, crossoverDistortion, decimator, laserbeam,
                  moreHarmonics, musicBox, noisy, phazer, ping_mh, saturatingWavefolder,
                  sillyVoice, sputter, triangleWaveBells, trig_demo, vintageSine, werkit, werkit2
organ (7)         organDonor, organReed, organTonewheel0..4
pads (9)          apadMH, arpoctave, feedbackPad1..3, line, midSideSaw, sawSynth, superSaw
percussion (9)    abstractDrum, frameDrum, kalimba, marimba1, metalPlate, modalMarimba,
                  pmCrotales, steelDrum, xylophone
strings (3)       prophet5pwmStrings, strings, violin
winds (1)         waveguideFlute
```

Worked mappings (the four verified against their source):

- `kick808` — `oneshot`. Args: out, freq1=240, freq2=60, amp=1, ringTime=10, att,
  rel=1, dist=0.5, pan. Corner -> /s_new at defaults; `dist` 0..1 -> vSlider3.
- `kalimba` — `oneshot` (pitched). Args: out, freq=440, amp=0.1, att, rel=3, pan,
  crv=-8, mix=0.1, clickRel=0.01. Corner index 0..63 -> freq; `mix` 0..1 -> vSlider3.
- `subBass1` — `oneshot`. Env.perc, no gate. Corner -> /s_new; `blend` 0..1 -> vSlider3.
- `superSaw` — `continuous` (gate). Gated ADSR; pad press = gate. `detuneRatio` and
  `spread` -> vSlider0/vSlider1; `freq` -> pad x/y or vSlider2.

Full per-synth `catalog.json` authoring (exact bespoke args and ranges for the other 105)
is the implementation step. The spec fixes the convention and the gesture rule, so that
authoring is mechanical, not judgment.

also see https://github.com/SCLOrkHub/SCLOrkSynths/tree/master/in-process/Completed (might be simpler to impl on 1st pass?)

### 9.9 Further community SynthDef sources

Sections 9.7 and 9.8 fixed the shape: any collection of sound-generating SynthDefs that can
be delivered over `/d_recv` and driven by OSC is a candidate for the select. A GitHub survey
of `.scd` SynthDef collections turned up eight more sources. Each is a pool of *named,
self-contained SynthDefs*; the ones already folded into SCLOrkSynths are reference sources
only and contribute no new entries.

| source | stars | license | `.scd` | sound defs | notes |
|--------|-------|---------|-------|-----------|-------|
| `diegodorado/tidal-synths` | 45 | none stated | 28 | 28 (one per file) | SuperDirt-ready, so many route through `DirtPan`/`~dirt` (see 9.9.2); author credits the originals only loosely |
| `loopier/synthdefs` | 31 | none stated | 48 | ~60 | 34 named instruments plus the 27-def `super*` bundle in its SuperDirt file; drop the effects, buffer and sequencer files |
| `theseanco/awesome-synthdefs` | 75 | none stated | 4 bundles | 25, grows | an "awesome list" of packs; the `co34pt` bundle mixes buffer players with ~13 buffer-free synths |
| `everythingwillbetakenaway/Synthdefs` | 86 | none stated | 83 | ~40 (~15 net-new) | the largest pool; mostly the SynthDefPool/synthDEFaults lineage, so most names are already in 9.8 |
| `derekxkwan/dxkSynthDefs` | 26 | GPL-3.0 | 27 | ~40 | ships 248 defs, but most are stereo/mono effect, filter, delay and routing variants; the instruments live in `dxkDrums`/`dxkPitched`/`dxkModal`/`dxkSupSynths`/`dxkSimpleOsc` |
| `redFrik/sInstruments` | 27 | GPL-3.0 | 21 | 13 | only `instruments/sStream.scd` holds standalone defs (the `sStream` family); `sCluster`/`sDrone`/`sGliss` are GUI instrument *programs*, not defs |
| `supercollider-quarks/SynthDefPool` | 21 | (quark) | 16 | 11 (6 net-new) | the canonical upstream SCLOrkSynths borrowed from; nearly all names already duplicate 9.8 |
| `thormagnusson/sctweets` | 9 | none stated | 25 | 1 | 140-char one-liners, almost all anonymous `.play` functions, so not catalog-shaped; deferred |

Net-new against the current 117 is roughly 190 instrument SynthDefs, which would grow the
select to about 300 entries.

#### 9.9.1 The dedupe key

An entry is keyed by its **normalised def name** (lowercased, non-alphanumerics stripped:
`moogBass` == `moogbass`). Before authoring, every candidate is diffed against the names
already in the catalog. A colliding name is dropped, never imported twice. This is why
`SynthDefPool` and most of `everythingwillbetakenaway/Synthdefs` add few or no entries: their
defs are already in 9.8. Same-name-different-graph is rare; when it happens the SCLOrkSynths
version wins, because it is the one already standardised to the 9.8 argument convention.

#### 9.9.2 Reshapes (same rules as 9.3)

- **SuperDirt glue.** `tidal-synths` defs route through `DirtPan.ar(sig, ~dirt.numChannels,
  ...)` and some read the `~dirt` global. That global does not exist under a bare scsynth, so
  each def is rewritten to `Pan2.ar(sig, pan)` / `Out.ar(out, ...)` and stripped of `~dirt`
  and `OffsetOut`. Routing only, no timbre change.
- **Argument style.** `loopier` and `theseanco` write `\name.kr(default)` instead of `arg`,
  which is already OSC-addressable, so no `arg` promotion is needed: the `control -> param`
  binding reads the same name either way.
- **Buffer players are excluded.** A def whose sound needs a sample (`buf` arg, `PlayBuf`,
  `BufRd`, `Warp1`, `DiskIn`) cannot sound from the select alone. Those are dropped, or kept
  only once the catalog carries a default sample per entry (a later increment).
- **Programs, not defs.** `redFrik/sInstruments`'s `sCluster`/`sDrone`/`sGliss` are GUI
  instrument *programs* (`In.ar(\bus)`, `Element`s, a `createDrone` closure). Lifting one def
  out of each is a reshape, not a copy; they come last.
- **One-line tweets.** `sctweets` are anonymous `{ ... }.play` functions, not named defs, so
  each needs wrapping in `SynthDef(\name, { ... })` plus a name. Low priority.

#### 9.9.3 Gesture (the D9 read rule, unchanged)

Every imported def is classified by the same rule as 9.8: a `gate` argument implies
`continuous`; a self-freeing envelope (`Env.perc`/`Env.sine` with `doneAction: 2`) and no
`gate` implies `oneshot`. Worked examples, read from their sources:

- `bass8` (`tidal-synths`) - `continuous`. `arg out=0, amp=0.1, gate=1, pan=0, freq=200`; a
  six-oscillator sub-heavy bass with two `releaseNode:` envelopes driven by `gate`. `freq`
  and `amp` -> slider ladder; `gate` -> pad press.
- `rhodes` (`tidal-synths`) - `oneshot`. `|out, sustain=1, pan, accelerate, freq|` with
  `Env.perc(0.0001, sustain, ..., -1), doneAction:2`. `sustain` (0-8 s) -> a reserved slider;
  pitch from the corner.
- `brute` (`loopier/synthdefs`) - `continuous`. `\gate.kr(1)` plus `Env.adsr(...).kr(2,
  gate)`; args `freq, wave (0-2), pw, sub, fifth, overtone, attackTime, decayTime,
  sustainLevel, releaseTime, amp, pan`. `wave`/`pw` and the four ADSR times are five
  bindable params.
- `tb303` (`loopier/synthdefs`) - `continuous`. `\gate.kr(1)` with `Env.adsr(gate,
  doneAction:2)`; args `freq, cutoff, res, env, wave, attackTime/decayTime/sustainLevel/
  releaseTime, amp, pan`. `cutoff` and `res` are the classic two.
- `sStream_Saw` (`redFrik/sInstruments`) - `continuous` drone. The `sStream` family
  (`sStream_Sine`, `_Saw`, `_Pulse`, `_Formant`, `_Karplus`, `_Noise`, `_Pink`, `_VOsc`,
  `_SineFB`) share one argument shape; one slider picks the waveform, another the rate.
- `sinfb` (`theseanco/awesome-synthdefs`) - `continuous`. `arg freq=440, atk=0.01, sus=0,
  rel=1, fb=0, amp=0.3, out=0, pan=0`; the feedback index `fb` is the signature param.
  `bpfsaw` and the `pulse3`/`sinfb3`/`saw3`/`tri3` group follow the same shape.
- `dxkBd1` (`derekxkwan/dxkSynthDefs`, drums) - `oneshot`. The `dxkDrums` bank (`dxkBd1-3`,
  `dxkHh1-3`, `dxkSd1-4`, `dxkCymb808`, `dxkGong1`, `dxkClap1`, `dxkCowbell1`) maps to pad
  corners exactly like the 9.8 drum banks.

#### 9.9.4 Licensing and attribution

The bridge checks each def's `.scd` into `src/super_quneo_collider/`, so importing a def
redistributes it, it does not merely reference it. That makes each source's license
load-bearing:

- **GPL-3.0** (`derekxkwan/dxkSynthDefs`, `redFrik/sInstruments`) - copyable, but the
  copyleft travels with the file: keep the upstream `LICENSE` beside any imported def, and
  treat the catalog as GPL-compatible if it is ever published.
- **No license file** (`tidal-synths`, `loopier/synthdefs`, `theseanco/awesome-synthdefs`,
  `everythingwillbetakenaway/Synthdefs`) - "public on GitHub" is not a license. Keep the
  upstream URL and author in every imported def's header comment, use them locally, and
  replace or clear them before any public release.
- **`tidal-synths`** states outright that the originals "are surely not mine", so its
  provenance is the weakest; treat it as study-and-adapt.

A def is imported only once its header names the source repo, the upstream file and the
author, following the per-file SCLOrkSynths convention of 9.8.

#### 9.9.5 Authoring stays mechanical

As in 9.8, full per-def `catalog.json` authoring for the roughly 190 imported defs is the
implementation step. This section fixes the dedupe key (9.9.1), the reshape rules (9.9.2)
and the gesture read rule (9.9.3), so authoring is mechanical: for each net-new def, diff
the name, apply any reshape, read `gate` for the gesture, and bind the first two or three
non-`out`/`pan` arguments to the slider ladder in declaration order.

---

## Appendix — full BasicSC_QuNeo mapping (from the QuNeo quark)

Drum pads (each: noteNum, pressCC, xCC, yCC, channel 15):

```
createDrumPad(00, 00, 00, 01, 02, 15)  ... createDrumPad(15, 15, 45, 46, 47, 15)
```
(note = index, pressCC = index, xCC = index+1, yCC = index+2)

Each pad reports a continuous `xCC`/`yCC` position in addition to note on/off, so a
pad resolves its press into a four-corner brightness field (16 pads × 4 = 64 touch
points). X-Axis runs low→high left→right and Y-Axis low→high bottom→top (QuNeo
manual); `padCorners` in `board.js` folds the two axes plus the press pressure into a
four-corner array — `[bottom-left, bottom-right, top-left, top-right]`, each 0..1 —
and `render.js` lights the four quadrant meshes from that array. The QuNeo latches
x/y (`outDmXReturn`/`outDmYReturn` = -1 in the preset), so position is a continuous
field rather than a discrete corner: a centred finger lights all four corners evenly,
an off-centre finger favours the nearer corner. The pad is note-gated and
pressure-driven — it lights while its note is on (brightness from `pressCC`, falling
back to full when that CC is unbound). The board-level `padCorners` is null while the
note is off, but the pane latches the last-lit corners after release so the pad stays
aglow until its next press; it is dark only before its first press, until the live x/y
position is first reported. Backend `xCC`/`yCC` tracking and the
per-pad `mapping.json` bindings were already in place, so this was a frontend-only
change.

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

Only those three buttons are MIDI-mapped. The QuNeo carries eight further physical
buttons that have no quark binding and therefore stay dark in the model unless a note
arrives on their channel: triangle-right, four left-right arrows, rhombus, and two
up-down arrows (`buttonButton3..10`).

Circle controls (noteNum, pressCC, locCC, channel 14):

```
createCircle(00, 00, 00, 01, 14)  createCircle(01, 04, 08, 09, 14)
createCircle(02, 01, 02, 03, 14)  createCircle(03, 05, 10, 11, 14)
createCircle(04, 02, 04, 05, 14)  createCircle(05, 06, 12, 13, 14)
createCircle(06, 03, 06, 07, 14)  createCircle(07, 07, 14, 15, 14)
```
