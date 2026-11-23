# Corner Triggers + Documentation Examples (§9.6 + §9.7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development (write the failing test first, watch it go RED, then make it GREEN; verify each task independently and as the full suite before committing). This plan executes the approved design in `docs/superpowers/specs/2026-11-23-corner-triggers-and-doc-examples-design.md` (Approach A).

## Goal

Grow the catalog from 4 Stage-1 entries to 9, introducing the `oneshot` gesture path and the `onset` sub-flavor end-to-end. The five new entries are the four supercollider.js documentation examples (Simple FM, Chainsaw, Drummer, Gabber Rave) reshaped into catalog-shaped SynthDefs:

| example id | gesture | onset | trigger surface | min-1 binding |
|---|---|---|---|---|
| `simpleFM` | continuous | select (drone) | none (auto-start on select) | vSlider0 -> modRate 0.1-20 Hz (exp) |
| `chainsaw` | continuous | select (drone) | none (auto-start on select) | vSlider0 -> amp 0-1 (lin) |
| `drummer` | continuous | select (drone) | none (auto-start on select) | vSlider0 -> tempo 0.5-16 Hz (exp) |
| `gabberkick` | oneshot | (corner) | any pad corner fires a fresh hit | vSlider3 -> bend 0.4-1 (lin) |
| `hoover` | continuous | note (gated) | pad press = gate 1, release = gate 0 | vSlider0 -> freq 40-2000 Hz (exp) |

DoD (§7): no new preset is flashed and selection never writes to the board. Every entry maps at least one control on the preset-0 (BasicSC) surface. All nine defs are delivered at boot in the one-shot `sc.load_defs()` batch; selection is control-plane only (D7/D8).

## Out of scope

Corner *addressing* (`index = pad*4 + quadrant`) is the mechanism §9.6 defines for §9.8's *pitched* oneshots (kalimba/bells -> corner index -> freq). §9.7's only oneshot (`gabberkick`) is unpitched and fires from any corner at default args, so no index -> freq mapping is needed yet. The addressing primitive, pitched flavor, and kits (arming many corners) land with §9.8. Likewise all §9.9 SCLOrkSynths/community imports.

## Shared guard template (all nine defs, byte-for-byte)

Every `.scd` already carries this tail (copy from `src/super_quneo_collider/sine.scd`) and the guard test in `tests/test_sc.py` (`test_every_catalogued_def_carries_the_stop_fade_and_the_ceiling`) counts each of these eight substrings exactly `len(DEF_NAMES)` times:

```
  var stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  var fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  ...
  <sig> = <sig> * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(<sig>, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, <sig>);
```

The five new defs must reproduce this tail verbatim (same `stopFade`/`fadeEnv` names, one `doneAction: 2`, two `doneAction: 0`). The only thing that changes per def is the signal-building section above it. For `gabberkick` the stop fade and ceiling are inert (the percussive hit ends and `DetectSilence` frees long before any 12 s ceiling), which is fine — the uniform contract stays, and `DetectSilence` still owns the free.

---

## Task F1 — Catalog: five entries with `gesture`/`onset`

Add the five entries to `src/super_quneo_collider/catalog.json` and teach the tests that nine examples exist.

**RED first:**
- `tests/test_map.py::test_catalog_lists_the_four_stage_one_examples` (line 99) -> rename to `test_catalog_lists_all_nine_examples` and assert the full id list `["bubbles", "formant", "sine", "klang", "simpleFM", "chainsaw", "drummer", "gabberkick", "hoover"]`.
- `tests/test_server.py::test_status_lists_the_four_examples` (line 106) -> same nine-id assertion.
- Add new assertions to `test_every_example_binds_at_least_one_parameter` / a new test that the three drones carry `onset == "select"`, `hoover` carries `onset == "note"`, `gabberkick` carries `gesture == "oneshot"`, and the other four have no `onset` key (defaults to `cc`).

**GREEN:** append these entries (sinclair note: `source` is `"examples.html"` for all five, matching the coarse-provenance convention already used by `"SCLOrkSynths"`):

```json
"simpleFM":   { "def": "simpleFM",   "source": "examples.html", "gesture": "continuous", "onset": "select",
  "params": [ { "name": "modRate", "control": "vSliderButton0", "cc": 61, "min": 0.1, "max": 20, "curve": "exp", "default": 1 } ] },
"chainsaw":   { "def": "chainsaw",   "source": "examples.html", "gesture": "continuous", "onset": "select",
  "params": [ { "name": "amp",     "control": "vSliderButton0", "cc": 61, "min": 0.0, "max": 1.0, "curve": "lin", "default": 0.3 } ] },
"drummer":    { "def": "drummer",    "source": "examples.html", "gesture": "continuous", "onset": "select",
  "params": [ { "name": "tempo",   "control": "vSliderButton0", "cc": 61, "min": 0.5, "max": 16, "curve": "exp", "default": 4 } ] },
"gabberkick": { "def": "gabberkick", "source": "examples.html", "gesture": "oneshot",
  "params": [ { "name": "bend",    "control": "vSliderButton3", "cc": 85, "min": 0.4, "max": 1.0, "curve": "lin", "default": 1 } ] },
"hoover":     { "def": "hoover",     "source": "examples.html", "gesture": "continuous", "onset": "note",
  "params": [ { "name": "freq",    "control": "vSliderButton0", "cc": 61, "min": 40, "max": 2000, "curve": "exp", "default": 440 } ] }
```

Every param already carries `cc`/`curve`/`min`/`max`/`default` and, when the control is ch 14, `channel` — so `test_catalog_cc_and_channel_agree_with_the_inventory` holds (all five bind sliders on ch 15, no `channel` override). `vSliderButton0` -> cc 61, `vSliderButton3` -> cc 85, per `mapping.json`.

Verify: `pytest tests/test_map.py tests/test_server.py` green.

---

## Task F2 — Five SynthDefs + boot delivery

Write the five `.scd` fragments and list them in `sc.py`'s `_DEF_SCRIPTS`.

**RED first:**
- `tests/test_sc.py::test_load_defs_uses_one_sclang_run` (line 145): change the probe's `{"numDefs": 4}` to `{"numDefs": len(DEF_NAMES)}`.
- `tests/test_sc.py::test_load_defs_confirms_defs_via_status` (line 166): change `4` to `len(DEF_NAMES)`.
- `tests/test_sc.py::test_load_defs_fails_when_sclang_exits_nonzero` (line 191): change the dead probe `{"numDefs": 9}` to `len(DEF_NAMES)` (or leave; it is unreachable — prefer `len(DEF_NAMES)` for consistency).
- Fix the stale "four"/"Stage-1 four" comments and the test name `test_load_defs_delivers_all_four_examples` -> `test_load_defs_delivers_all_examples` (the assertions already use `len(DEF_NAMES)`).

**GREEN:** in `sc.py`, extend the `_DEF_SCRIPTS` tuple with `simpleFM`, `chainsaw`, `drummer`, `gabberkick`, `hoover` (order matches catalog). Write the five fragments in `src/super_quneo_collider/` (names = the def symbol). Upstream sources were retrieved 2026-11-23 from https://supercollider.github.io/examples — copy the signal section verbatim and apply only the reshape deltas below, then append the guard tail.

### simpleFM.scd
Upstream `{ SinOsc.ar(SinOsc.kr([1, 3]).exprange(100, 2e3), 0, 0.2) }.play`. Reshape: promote `[1, 3]` to one `modRate` arg while keeping the 1:3 stereo beat.

```scd
// supercollider.js examples -- "Simple FM" drone (SPEC §9.7).
// Upstream: { SinOsc.ar(SinOsc.kr([1, 3]).exprange(100, 2e3), 0, 0.2) }.play
// The [1, 3] LFO rates are promoted to one modRate arg; the 1:3 beat is kept
// so one slider scales a stereo LFO without changing the timbre. Drone: starts
// on select, freed on deselect (onset=select).
SynthDef("simpleFM", { arg out=0, modRate=1, gate=1, fade=1;
  var stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  var fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  var sig = SinOsc.ar(SinOsc.kr([modRate, modRate * 3]).exprange(100, 2e3), 0, 0.2) * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});
```

### chainsaw.scd
Upstream (Julian Rohrhuber, 2007): two local closures `f` (a per-saw nonlinear LFSaw/LFNoise warper with `.clip2(1.0)`) and `g` (`func <> func` composed n times), then `freq = g.(f, 4).value(LFSaw.kr(0.2 * [1, 1.1])).exprange(6, 11000)` and `BPF.ar(Saw.ar(freq).product, [70, 800, 9000, 5242], 0.2).sum.dup * 0.3`.

Reshape deltas:
- Wrap the `{ ... }.play` body in `SynthDef("chainsaw", { arg out=0, amp=0.3, gate=1, fade=1; ... })`; drop any unused `var amp` inside `f`.
- Keep the `f` and `g` closures **verbatim** (re-fetch the source to transcribe them exactly — do not paraphrase the `.choose`/`.coin`/`LinExp` arithmetic).
- Keep `freq = g.(f, 4).value(LFSaw.kr(0.2 * [1, 1.1])).exprange(6, 11000);` verbatim.
- Promote the trailing `* 0.3` master gain to `* amp` (the `amp` arg).
- Append the guard tail (the `BPF ... .sum.dup * amp` becomes `sig`, which then gets `* stopFade * Select.kr(...)` etc.).

Note in the fragment header: `f`'s `ExpRand`/`.coin`/`.choose` are evaluated **once**, when sclang compiles the def at boot, so the stochastic timbre is fixed per session (D8 forbids recompiling on selection). This is inherent to the one-def/one-compile delivery model, not a reshape.

```scd
// supercollider.js examples -- "Chainsaw" self-running noise machine
// (Julian Rohrhuber, 2007), SPEC §9.7.  The upstream { }.play body is wrapped
// in a SynthDef; the local f/g closures stay local. f's ExpRand/.coin/.choose
// run once at boot-compile, so the timbre is fixed per session (D8: no compile
// on selection). Master gain * 0.3 -> amp (vSlider0). Drone (onset=select).
SynthDef("chainsaw", { arg out=0, amp=0.3, gate=1, fade=1;
  var f, g, freq, sig, stopFade, fadeEnv;
  f = { | saw |
    // < f's body VERBATIM from upstream: rate, freq, u, clip2(1.0) >
  };
  g = { | func, n = 5 | n.do { func = func <> func }; func };
  freq = g.(f, 4).value(LFSaw.kr(0.2 * [1, 1.1])).exprange(6, 11000);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  sig = BPF.ar(Saw.ar(freq).product, [70, 800, 9000, 5242], 0.2).sum.dup * amp * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});
```

### drummer.scd
Upstream (Thor Magnusson, 2006): `tempo = Impulse.ar(tempo)` with `PulseDivider.ar(tempo, 4, 2)` snare, `PulseDivider.ar(tempo, 4, 0)` bdrum, `Decay2.ar(tempo, ...)` hihat, `Out.ar(0, (snare + bdrum + hihat) * 0.4 ! 2)`.

Reshape: promote `var tempo = 4` to `arg tempo=4`; rename the internal clock to `imp` so the arg stays the single settable control (`Impulse.ar(tempo)` reads it live). Drum sum kept as upstream `(snare + bdrum + hihat) * 0.4 ! 2` (the `! 2` is the upstream's own stereoization).

```scd
// supercollider.js examples -- "Drummer" (Thor Magnusson, 2006), SPEC §9.7.
// var tempo = 4 is promoted to arg tempo (vSlider0, 0.5-16 Hz); the internal
// clock UGen is renamed `imp` so tempo stays one live-settable control. Drone.
SynthDef("drummer", { arg out=0, tempo=4, gate=1, fade=1;
  var imp, snare, bdrum, hihat, sig, stopFade, fadeEnv;
  imp = Impulse.ar(tempo);
  snare = WhiteNoise.ar(Decay2.ar(PulseDivider.ar(imp, 4, 2), 0.005, 0.5));
  bdrum = SinOsc.ar(Line.ar(120, 60, 1), 0, Decay2.ar(PulseDivider.ar(imp, 4, 0), 0.005, 0.5));
  hihat = HPF.ar(WhiteNoise.ar(1), 10000) * Decay2.ar(imp, 0.005, 0.5);
  sig = (snare + bdrum + hihat) * 0.4 ! 2;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  sig = sig * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});
```

### gabberkick.scd
Upstream `\gabberkick` from the Gabber Rave page. Reshape deltas:
- Promote `\freq.kr(440)` -> `arg freq=440`, `\bend.kr(1)` -> `arg bend=1`; `\gate.kr(1)` is replaced; `\ffreq.kr(3000)` -> literal `3000` (the user chose `bend`, not `ffreq`, as the reserved slider, so `ffreq` stays fixed); `\amp.kr(0.1)` -> literal `* 0.1` at the `Out`.
- Replace the gated amplitude `Env.asr(0.001, 1, 0.05).ar(2, \gate.kr(1))` with a self-ending percussive hit `Env.perc(0.001, 0.3).ar`, so the kick decays and `DetectSilence` frees it (the source's own `legato: 0.8` -> a finite hit). This is an envelope reshape only; timbre is unchanged.

```scd
// supercollider.js examples -- "Gabber Rave" kick (SPEC §9.7).  oneshot:
// a pad press /s_new's this def and DetectSilence frees it. The upstream gated
// amplitude Env.asr is reshaped to a self-ending Env.perc (the source's legato
// 0.8 -> a finite hit). bend -> vSlider3 (0.4-1 pitch-drop amount); ffreq stays 3000.
SynthDef("gabberkick", { arg out=0, freq=440, bend=1, gate=1, fade=1;
  var snd, high, lfo, stopFade, fadeEnv;
  freq = freq * (Env.perc(0.001, 0.08, curve: -1).ar * 48 * bend).midiratio;
  snd = Saw.ar(freq);
  snd = (snd * 100).tanh + ((snd.sign - snd) * -8.dbamp);
  high = HPF.ar(snd, 300);
  lfo = SinOsc.ar(8, [0, 0.5pi]).range(0, 0.01);
  high = high.dup(2) + (DelayC.ar(high, 0.01, lfo) * -2.dbamp);
  snd = LPF.ar(snd, 100).dup(2) + high;
  snd = RLPF.ar(snd, 7000, 2);
  snd = BPeakEQ.ar(snd, 3000 * XLine.kr(1, 0.8, 0.3), 0.5, 15);
  snd = snd * Env.perc(0.001, 0.3).ar;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd * 0.1);
});
```

Note: `freq = freq * (...)` reassigns the `freq` arg exactly as upstream reassigns its `var freq`, so `/n_set freq` still retunes — the control is read in the RHS before the local shadow.

### hoover.scd
Upstream `\hoover` from the Gabber Rave page. Reshape deltas:
- Promote `\freq.kr(440)` -> `arg freq=440`, `\out.kr(0)` -> `arg out=0`; both `\gate.kr(1)` references -> the `gate` arg; `\amp.kr(0.1)` -> literal `* 0.1`.
- Keep the `20 { DelayN.ar(Saw.ar(...) + Saw.ar(...), 0.01, Rand(0, 0.01)) }` layer, `Splay`, `FreeVerb2` all verbatim.

```scd
// supercollider.js examples -- "Gabber Rave" hoover lead (SPEC §9.7). Gated
// (onset=note): pad press gate 1, release gate 0; vSlider0 -> freq. The two
// upstream \gate.kr(1) references use the one promoted gate arg.
SynthDef("hoover", { arg out=0, freq=440, gate=1, fade=1;
  var snd, bw, stopFade, fadeEnv;
  freq = freq * Env([-5, 6, 0], [0.1, 1.7], [\lin, -4]).kr.midiratio;
  bw = 1.035;
  snd = { DelayN.ar(Saw.ar(freq * ExpRand(bw, 1 / bw)) + Saw.ar(freq * 0.5 * ExpRand(bw, 1 / bw)), 0.01, Rand(0, 0.01)) }.dup(20);
  snd = (Splay.ar(snd) * 3).atan;
  snd = snd * Env.asr(0.01, 1.0, 1.0).kr(0, gate);
  snd = FreeVerb2.ar(snd[0], snd[1], 0.3, 0.9);
  snd = snd * Env.asr(0, 1.0, 4, 6).kr(2, gate);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd * 0.1);
});
```

The guard test counts `gate=1` exactly once per def: hoover's `arg ... gate=1` is the single literal (the two usage sites are the bare `gate`), and its two upstream `Env.asr` calls (`(0.01, 1.0, 1.0)` and `(0, 1.0, 4, 6)`) do not collide with the counted `Env.asr(0.01, 1, 3)`.

Verify: `pytest tests/test_sc.py tests/test_server.py tests/test_map.py tests/test_midi.py` green. A real `sclang` is not required for these tests (the probes are fakes); run the scsynth-backed `test_load_defs_delivers_all_examples` in Task F7.

---

## Task F3 — Helper text: name the corner for a oneshot

**RED:** add to `tests/test_map.py` a test that `helper_lines(catalog, "gabberkick")` starts with `["corner -> gabberkick", "vSlider3 -> bend  0.4-1.0"]` and that the four continuous examples' helper output is unchanged from today (formant/klang/sine assertions already pin this).

**GREEN:** `src/super_quneo_collider/map.py::helper_lines` — before building the aligned param lines, if `catalog["examples"][example_id].get("gesture") == "oneshot"`, prepend `f"corner -> {entry['def']}"`. Leave the existing aligned loop untouched so the four Stage-1 entries emit byte-identical text.

---

## Task F4 — MIDI note events reach the app

The watcher currently records note on/off into `state()["note"]` (for client lighting) but never forwards notes to the bridge. Add an optional note callback.

**RED:** add to `tests/test_midi.py` a test that drives `parse_aseqdump_line`-shaped note lines through `_pump` (use the existing injectable `spawn`/`port_finder` fixtures) and asserts the callback receives `(note, on, channel)` for both a velocity>0 note-on and a note-off, and that a velocity-0 "Note on" is delivered as `on=False`.

**GREEN:** `src/super_quneo_collider/midi.py`:
- `MidiWatcher.__init__`: add `on_note=None` keyword, store `self._on_note = on_note`.
- `_pump` note branch (lines ~306-308): after updating `self._note` and `self._save()`, call `if self._on_note is not None: self._on_note(ev["note"], ev["on"], ev["channel"])`.
- `server.py::serve`: define `_on_note(note, on, channel)` -> `app.on_note(note, on, channel)` and pass `on_note=_on_note` to the `MidiWatcher(...)`.

The existing `MidiWatcher(on_event=...)` call sites keep working because `on_note` defaults to `None`.

---

## Task F5 — Server routing: oneshot / gated-note / drone

**RED:** extend `tests/test_server.py` (use the existing `make_app()` with `FakeSc`, which records `spawn`, `set_param`, `set_params`):

1. `test_oneshot_note_on_spawns_a_fresh_voice_per_press`: select `gabberkick`; `app.on_note(3, True)` -> one `spawn` of `gabberkick`; a second `app.on_note(3, True)` -> a second `spawn` with a distinct node id; `app.on_note(3, False)` -> no new node, no `set_param`.
2. `test_oneshot_slider_move_does_not_spawn`: select `gabberkick`; `app.on_cc(85, 90)` updates `status()["sliders"]["bend"]` to the scaled value but records **no** `spawn`/`set_params`.
3. `test_gated_note_spawns_on_press_and_gates_off_on_release`: select `hoover`; `app.on_note(5, True)` -> one `spawn` of `hoover` at gate=1 (def default); `app.on_note(5, False)` -> `sc.set_param(node, "gate", 0)`; a third event on any pad does not spawn a second overlapping voice while one is alive.
4. `test_drone_starts_on_select_and_fades_on_deselect`: select `simpleFM` -> auto `spawn` of `simpleFM`; selecting `bubbles` -> `set_params(gate=0)` on the drone node then no spawn (bubbles is `onset` = cc and silent at boot).

**GREEN:** `src/super_quneo_collider/server.py`:

- Add an `onset` property alongside `gesture`: `return self.catalog["examples"][self.active].get("onset", "cc")`.
- `select_example`: after `self._bind()`, add `if self.onset == "select": self._trigger()` so a drone starts on selection (and `_stop_voices()` above already faded the previous voice).
- `on_cc`: after updating `self.sliders[...]`, only call `self._trigger()` when the active example is **not** a oneshot (`if self.gesture != "oneshot": self._trigger()`), so the reserved slider tunes the next hit instead of firing one.
- Add `on_note(self, note, on, channel=None)`:
  - `if self.gesture == "oneshot": if on: self._trigger(); return`
  - `if self.onset != "note": return` (cc and select onsets do not bind notes)
  - note-on -> `_gate_on()`; note-off -> `_gate_off()`.
- Add `_gate_on` (spawn via `self._trigger()` if `self._live(self.active)` is None, else `self.sc.set_param(node, "gate", 1)`) and `_gate_off` (`self.sc.set_param(node, "gate", 0)` when a live node exists).
- `status()`: include `"onset": self.onset` in each example dict (derived; the frontend ignores unknown keys).

Note `on_note`'s note number is deliberately not mapped to `freq` — §9.7's only pitched/gated entry (hoover) takes pitch from vSlider0, and pad->freq mapping is §9.8's pitched-oneshot work. `gate=1` on spawn is the def default, so `_trigger`'s existing `args` (sliders + `fade`) need no gate key.

---

## Task F6 — Frontend fixtures: nine examples

**RED/GREEN:** `client/tests/examples.test.js` hardcodes the four-entry `STATE.examples` fixture and asserts `exampleIds` / options / `select.options.length === 4`. Add the five new entries (`{ id, def: id, source: 'examples.html', gesture: 'continuous' | 'oneshot' }`) and change the three count assertions 4 -> 9. No production frontend change is required: the picker, lighting (`board.js padQuadrant`), and tick poll already drive off catalog/status, and a oneshot's corner press lights through the existing `note` state.

Verify: run the frontend browser-harness suite (per `DEV_STATUS.md` it is 21 green) — `cd client && <the harness command recorded in DEV_STATUS/README>`.

---

## Task F7 — Full suite + live board verification (preset 0)

1. `pytest` — all 59 (now +new) backend tests green.
2. Frontend harness green (21 + fixture updates).
3. Physical board (preset 0 / BasicSC, currently connected): run the bridge against `sclang`/`scsynth`, then verify by ear and by `curl /api/collider`:
   - select each of the four Stage-1 entries still sounds;
   - `simpleFM`, `chainsaw`, `drummer` start on selection and fade on deselect (drone);
   - `hoover` sounds only while a pad is held (gated note), vSlider0 sweeps pitch;
   - `gabberkick` fires a hit on any pad corner press, vSlider3 varies the pitch-drop;
   - all nine ids appear in `/api/collider`, and `load_defs` registers 9 defs (numDefs >= 9).
4. Update `DEV_STATUS.md` (backend/frontend counts, the nine-entry catalog, the new `onset` field, the §9.6/§9.7 increment note).

Commit each task as its own incremental commit (per the project's convention), then a final `git status` clean.

---

## Execution method

When you are happy with this plan, choose one:

- **Subagent-driven** — I dispatch subagents to execute these tasks in parallel where safe (F1+F2 share catalog, F4+F5 share midi/server).
- **Native** — I implement task by task here, committing after each verified step.

(Reply with the choice, or point out any task to adjust first.)