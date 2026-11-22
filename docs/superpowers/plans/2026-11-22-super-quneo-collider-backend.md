# Super Quneo Collider — Backend Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python bridge that turns a QuNeo vertical-slider MIDI CC into a live SuperCollider "bubbles" synth parameter change and exposes the state as JSON at `/api/collider`.

**Architecture:** A stdlib HTTP server owns a QuNeo MIDI watcher (ported from op1-web, CC-aware), a pure mapping/scaling module, and an scsynth lifecycle module (boot + one-shot sclang SynthDef delivery + pyliblo3 OSC control plane). The server composes them: on a channel-15 CC event it scales the raw value and sends `/n_set`, and it serves the resulting slider state over HTTP.

**Tech Stack:** Python 3 (src layout), stdlib `http.server`, `pyliblo3` 0.17.0, `scsynth`/`sclang` 3.13.0 (Ubuntu package), `pytest`.

**Spec:** `SPEC.md` (sections 3, 4, 5, 6; appendix). Spike results and hard limits live in `DEV_STATUS.md`.

## Global Constraints

- Package `super_quneo_collider`, src layout (`src/super_quneo_collider/`), pytest as the only required test runner.
- OSC via pyliblo3 0.17.0. scsynth control address `127.0.0.1:57110`. Synth spawn `/s_new`, param change `/n_set`, status `/status`.
- SynthDef delivery is a one-shot `sclang` subprocess at bridge startup ONLY; Python never sends `/d_recv` (pyliblo3 cannot send OSC blobs).
- pyliblo3 reply callback order is `cb(path, args, types, src)` — NOT the `(path, types, args, src)` order inherited from queneo-editor's `osc_service.py:227`.
- QuNeo ALSA port is resolved by NAME (`"QuNeo"` client, `"QuNeo MIDI 1"` port), never by number.
- The MIDI channel filter is 15 (0-indexed); it lives in `mapping.json`, not hard-coded.
- Scaling is linear `0..127 -> [lo, hi]`, rounded to 3 decimals.
- Everything pure/testable: injectable port discovery, subprocess spawn, OSC sender, and clock. No hardware and no scsynth where the spec states "no hardware and no scsynth".
- No auto-flashing. The runtime bridge never imports or invokes the test rig.

## Review Focus

The five conditions the spec implies but no single task's happy-path test covers, most likely to bite a real user first:

1. **`aseqdump` "Control change" line layout.** The CC line has a different column/whitespace shape than the Note line op1-web already parses; a naive copy of the Note regex fails. → Task 3, `test_parse_cc_line` (pinned to a real captured line).
2. **A CC arriving on a non-15 channel must be dropped.** The physical board ships a default preset that emits on channel 0; without the filter the bridge misreads unrelated CC streams. → Task 3, `test_watcher_ignores_other_channel`.
3. **Boot must be idempotent.** Re-running the bridge with scsynth already up must reuse the running server, not spawn a second one fighting for the port. → Task 4, `test_boot_idempotent`.
4. **One-shot sclang must terminate.** The delivery subprocess must be invoked by positional file and end in `0.exit` so it returns exit 0 instead of hanging in a REPL. → Task 4, `test_load_bubbles_terminates_clean`.
5. **An unbound controller must produce no parameter and no OSC.** locCC 85 (vSliderButton3) is unbound; a value there must not crash the bridge or emit `/n_set`. → Task 2, `test_unbound_loccc_produces_nothing`; Task 5, `test_on_cc_unbound_ignored`.

---

### Task 1: Project scaffold and packaging

**Files:**
- Create: `pyproject.toml`
- Create: `src/super_quneo_collider/__init__.py`
- Create: `install.sh`
- Create: `README.md`
- Test: `tests/test_package.py`

**Interfaces:**
- Produces: an importable `super_quneo_collider` package (so `pytest` can import later modules), a runnable `install.sh` that is idempotent, and a compact `README.md`.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_package.py
def test_package_imports():
    import super_quneo_collider
    assert super_quneo_collider.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_package.py -v` (create `.venv` first with `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`)
Expected: FAIL with `ModuleNotFoundError: super_quneo_collider`

- [ ] **Step 3: Implement the package skeleton**

`pyproject.toml`: name `super-quneo-collider`, src layout, `requires-python >= 3.11`, runtime dependency `pyliblo3`, optional `[dev]` extra with `pytest`. `src/super_quneo_collider/__init__.py` exposes `__version__ = "0.1.0"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_package.py -v`
Expected: PASS

- [ ] **Step 5: Write `install.sh` and `README.md`**

`install.sh` (idempotent): if `scsynth`/`sclang` are absent, `apt-get install -y supercollider`; create `.venv` with the system `python3` if absent; `pip install -e ".[dev]"`. Re-runs must be no-ops. `README.md`: compact setup + run guide (idempotent install, then the run command).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml install.sh README.md src/super_quneo_collider/__init__.py tests/test_package.py
git commit -m "chore: project scaffold, packaging, and idempotent install"
```

---

### Task 2: Mapping and scaling (map.py + mapping.json)

**Files:**
- Create: `src/super_quneo_collider/mapping.json`
- Create: `src/super_quneo_collider/map.py`
- Test: `tests/test_map.py`

**Interfaces:**
- Consumes: `super_quneo_collider` package (Task 1).
- Produces:
  - `mapping.json` — a JSON object with a top-level `"channel": 15` and a `"controls"` object keyed by board control id; each control carries `noteNum`, `pressCC`, `locCC`, and, for bound sliders, `param`, `min`, `max`.
  - `scale(raw: int, lo: float, hi: float) -> float`
  - `load_mapping(path) -> dict`
  - `param_for_cc(mapping: dict, cc: int) -> tuple[str, float, float] | None`
  - `scale_cc(mapping: dict, cc: int, raw: int) -> tuple[str, float] | None`

`mapping.json` contents (exact, from SPEC section 5):

```json
{
  "channel": 15,
  "controls": {
    "vSliderButton0": {"noteNum": 20, "pressCC": 60, "locCC": 61, "param": "wobble", "min": 0.0, "max": 10.0},
    "vSliderButton1": {"noteNum": 24, "pressCC": 68, "locCC": 69, "param": "innerWobble", "min": 0.0, "max": 16.0},
    "vSliderButton2": {"noteNum": 28, "pressCC": 76, "locCC": 77, "param": "releaseTime", "min": 2.0, "max": 6.0},
    "vSliderButton3": {"noteNum": 32, "pressCC": 84, "locCC": 85}
  }
}
```

Scaling is `scale(raw, lo, hi) = round(lo + raw / 127 * (hi - lo), 3)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_map.py
from pathlib import Path
from super_quneo_collider.map import scale, load_mapping, param_for_cc, scale_cc

MAPPING = Path(__file__).resolve().parent.parent / "src" / "super_quneo_collider" / "mapping.json"

def test_scale_wobble():
    assert scale(0, 0.0, 10.0) == 0.0
    assert scale(63, 0.0, 10.0) == 4.961
    assert scale(127, 0.0, 10.0) == 10.0

def test_scale_inner_wobble():
    assert scale(0, 0.0, 16.0) == 0.0
    assert scale(64, 0.0, 16.0) == 8.063
    assert scale(127, 0.0, 16.0) == 16.0

def test_scale_release_time():
    assert scale(0, 2.0, 6.0) == 2.0
    assert scale(64, 2.0, 6.0) == 4.016
    assert scale(127, 2.0, 6.0) == 6.0

def test_param_for_cc_binds_loccc():
    m = load_mapping(MAPPING)
    assert param_for_cc(m, 61) == ("wobble", 0.0, 10.0)
    assert param_for_cc(m, 69) == ("innerWobble", 0.0, 16.0)
    assert param_for_cc(m, 77) == ("releaseTime", 2.0, 6.0)

def test_unbound_loccc_produces_nothing():
    assert param_for_cc(load_mapping(MAPPING), 85) is None

def test_scale_cc_end_to_end():
    assert scale_cc(load_mapping(MAPPING), 61, 127) == ("wobble", 10.0)

def test_mapping_carries_quark_values():
    m = load_mapping(MAPPING)
    assert m["channel"] == 15
    assert m["controls"]["vSliderButton0"] == {
        "noteNum": 20, "pressCC": 60, "locCC": 61, "param": "wobble", "min": 0.0, "max": 10.0
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_map.py -v`
Expected: FAIL with `ModuleNotFoundError: super_quneo_collider.map`

- [ ] **Step 3: Implement `map.py`**

Write `mapping.json` exactly as above, then `scale`, `load_mapping`, `param_for_cc` (scan `controls` for the entry whose `locCC` equals `cc`; return `(param, min, max)` or `None`), and `scale_cc` (compose `param_for_cc` + `scale`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_map.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/super_quneo_collider/map.py src/super_quneo_collider/mapping.json tests/test_map.py
git commit -m "feat: mapping + linear CC scaling (locCC -> param)"
```

---

### Task 3: QuNeo MIDI watcher (midi.py)

**Files:**
- Create: `src/super_quneo_collider/midi.py`
- Test: `tests/test_midi.py`

**Interfaces:**
- Consumes: nothing beyond the package.
- Produces:
  - `SEQ_CLIENTS_PATH = "/proc/asound/seq/clients"`
  - `find_quneo_midi_port(path: str = SEQ_CLIENTS_PATH) -> str | None`
  - `parse_aseqdump_line(line: str) -> dict | None` — returns `{"channel": int, "cc": int, "value": int}` for a Control-change line, else `None`.
  - `class MidiWatcher` — constructor kwargs `port_finder=find_quneo_midi_port`, `spawn=None`, `clock=time.monotonic`, `channel=15`, `on_event=None`. Methods `start()`, `stop()`, `state()`.

`state()` returns `{"present": bool, "port": str | None, "cc": dict[int, int]}`. On each parsed Control-change on `channel`, the watcher records `cc[cc] = value` and calls `on_event(cc, value)`.

The CC regex (verified against a real captured line ` 24:0   Control change          0, controller 19, value 41`):

```
r"^\s*\d+:\d+\s+Control change\s+(\d+), controller (\d+), value (\d+)\s*$"
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_midi.py
from super_quneo_collider.midi import find_quneo_midi_port, parse_aseqdump_line, MidiWatcher

def test_find_port_present(tmp_path):
    seq = tmp_path / "clients"
    seq.write_text(
        'Client  20 : "QuNeo" [Kernel Legacy]\n'
        '  Port   0 : "QuNeo MIDI 1" (RWeX) [In/Out]\n'
    )
    assert find_quneo_midi_port(str(seq)) == "20:0"

def test_find_port_present_second_example(tmp_path):
    seq = tmp_path / "clients"
    seq.write_text(
        'Client  24 : "QuNeo" [Kernel Legacy]\n'
        '  Port   0 : "QuNeo MIDI 1" (RWeX) [In/Out]\n'
    )
    assert find_quneo_midi_port(str(seq)) == "24:0"

def test_find_port_absent(tmp_path):
    seq = tmp_path / "clients"
    seq.write_text('Client  14 : "Midi Through" [Kernel Legacy]\n')
    assert find_quneo_midi_port(str(seq)) is None

def test_parse_cc_line_real_capture():
    # Real line captured from `aseqdump -p 24:0` on 2026-11-22.
    assert parse_aseqdump_line(" 24:0   Control change          0, controller 19, value 41") == {
        "channel": 0, "cc": 19, "value": 41
    }

def test_parse_cc_line_channel_15():
    assert parse_aseqdump_line(" 24:0   Control change         15, controller 61, value 64") == {
        "channel": 15, "cc": 61, "value": 64
    }

def test_parse_ignores_note():
    assert parse_aseqdump_line(" 24:0   Note on                 0, note 7, velocity 127") is None

def test_parse_ignores_header():
    assert parse_aseqdump_line("Source  Event                  Ch  Data") is None

def test_watcher_records_channel_15_cc():
    w = MidiWatcher(spawn=FakeSpawn([" 24:0   Control change         15, controller 61, value 64\n"]))
    w.start(); w.tick()
    assert w.state()["present"] is True
    assert w.state()["cc"][61] == 64

def test_watcher_ignores_other_channel():
    w = MidiWatcher(spawn=FakeSpawn([" 24:0   Control change          7, controller 61, value 99\n"]))
    w.start(); w.tick()
    assert w.state()["cc"] == {}

def test_watcher_fires_on_event():
    seen = []
    w = MidiWatcher(spawn=FakeSpawn([" 24:0   Control change         15, controller 61, value 64\n"]),
                    on_event=lambda cc, v: seen.append((cc, v)))
    w.start(); w.tick()
    assert seen == [(61, 64)]
```

`FakeSpawn` is a tiny test double in `tests/test_midi.py` whose `popen` returns an object with `.stdout` iterating the given lines and `.terminate()`/`.wait()` no-ops.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_midi.py -v`
Expected: FAIL with `ModuleNotFoundError: super_quneo_collider.midi`

- [ ] **Step 3: Implement `midi.py`**

Port op1-web's `midi.py` structure (client/port regex over `/proc/asound/seq/clients`, `aseqdump` subprocess with `stdbuf -oL`, a dedicated reader thread, `_terminate_orphan_readers`) and swap the event model: `parse_aseqdump_line` recognizes only Control change (the regex above), and the watcher filters on `channel`, records `cc -> value`, and fires `on_event`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_midi.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add src/super_quneo_collider/midi.py tests/test_midi.py
git commit -m "feat: CC-aware QuNeo MIDI watcher (channel-15 filter)"
```

---

### Task 4: scsynth lifecycle and OSC (sc.py + bubbles.scd)

**Files:**
- Create: `src/super_quneo_collider/sc.py`
- Create: `src/super_quneo_collider/bubbles.scd`
- Test: `tests/test_sc.py`

**Interfaces:**
- Consumes: the package; `pyliblo3` (`liblo`/`pyliblo3` import fallback), scsynth/sclang 3.13.0.
- Produces:
  - `resolve_scsynth() -> str | None`
  - `resolve_sclang() -> str | None`
  - `class ScServer` — constructor kwargs `host="127.0.0.1"`, `port=57110`, `scsynth_path=None`, `sclang_path=None`, `def_script=None`, `spawn=None`, `probe=None`, `clock=time.monotonic`. Methods `boot() -> bool`, `load_bubbles() -> bool`, `spawn_bubbles(node: int = 1000) -> bool`, `set_param(node: int, param: str, value: float) -> None`, `get_param(node: int, param: str) -> float | None`, `status() -> dict | None`, `stop()`.

Mechanics (from `DEV_STATUS.md`, do not rediscover): boot cmd `scsynth -u 57110 -B 127.0.0.1`; delivery via one-shot `sclang bubbles.scd` (positional file, ends `0.exit`, spawn then `wait()`); OSC `/s_new`, `/n_set`, `/s_get`; `/s_get` replies arrive as `/n_set` `[node, "param", value]`; pyliblo3 callback order `cb(path, args, types, src)`.

`bubbles.scd` (verbatim SynthDef from SPEC section 5):

```supercollider
var addr = NetAddr("127.0.0.1", 57110);
var d = SynthDef("bubbles", { arg out=0, wobble=0.4, innerWobble=8, releaseTime=4;
  var f, zout;
  f = LFSaw.kr(wobble, 0, 24, LFSaw.kr([innerWobble, innerWobble / 1.106], 0, 3, 80)).midicps;
  zout = CombN.ar(SinOsc.ar(f, 0, 0.04), 0.2, 0.2, 4);
  zout = zout * EnvGen.kr(Env.linen(releaseTime: releaseTime), doneAction: 2);
  Out.ar(out, zout);
});
addr.sendMsg("/d_recv", d.asBytes);
0.exit;
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sc.py
import os
import pytest
from super_quneo_collider.sc import resolve_scsynth, resolve_sclang, ScServer

scsynth_ok = pytest.mark.skipif(resolve_scsynth() is None, reason="scsynth not installed")

def test_resolve_scsynth_exists():
    p = resolve_scsynth()
    assert p and os.path.isfile(p) and os.access(p, os.X_OK)

def test_resolve_sclang_exists():
    p = resolve_sclang()
    assert p and os.path.isfile(p) and os.access(p, os.X_OK)

@scsynth_ok
def test_boot_answers_status():
    s = ScServer()
    try:
        assert s.boot() is True
        st = s.status()
        assert st and st["numUgens"] > 0
    finally:
        s.stop()

@scsynth_ok
def test_bubbles_defaults():
    s = ScServer()
    try:
        s.boot(); s.load_bubbles(); s.spawn_bubbles(1000)
        assert s.get_param(1000, "wobble") == pytest.approx(0.4, abs=1e-3)
        assert s.get_param(1000, "innerWobble") == pytest.approx(8.0, abs=1e-3)
        assert s.get_param(1000, "releaseTime") == pytest.approx(4.0, abs=1e-3)
    finally:
        s.stop()

@scsynth_ok
def test_n_set_changes_param():
    s = ScServer()
    try:
        s.boot(); s.load_bubbles(); s.spawn_bubbles(1000)
        s.set_param(1000, "wobble", 10.0)
        assert s.get_param(1000, "wobble") == pytest.approx(10.0, abs=1e-3)
    finally:
        s.stop()

def test_load_bubbles_terminates_clean():
    # Inject a fake spawn that asserts the argv is positional-file (not stdin),
    # returns exit 0; load_bubbles must wait() and return True.
    calls = []
    s = ScServer(spawn=RecordingSpawn(calls), def_script="/tmp/bubbles.scd")
    assert s.load_bubbles() is True
    argv = calls[0]
    assert "/tmp/bubbles.scd" in argv and "0.exit" not in argv

def test_boot_idempotent():
    # First boot: probe returns None -> spawn fires once. Second boot: probe
    # returns a valid status -> spawn does NOT fire again.
    spawns = []
    class Prober:
        def __init__(self): self.n = 0
        def __call__(self, *a, **k):
            self.n += 1
            return {"numUgens": 8} if self.n > 1 else None
    s = ScServer(spawn=lambda argv: spawns.append(argv), probe=Prober())
    assert s.boot() is True
    assert s.boot() is True
    assert len(spawns) == 1
```

`RecordingSpawn` and `Prober` are test doubles defined in the test module.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_sc.py -v`
Expected: FAIL with `ModuleNotFoundError: super_quneo_collider.sc`

- [ ] **Step 3: Implement `sc.py` and `bubbles.scd`**

`resolve_scsynth`/`resolve_sclang` via `shutil.which` then `/usr/bin` fallback. `ScServer.boot()` first probes `/status`; if answered, reuse (return True) without spawning; otherwise spawn `scsynth -u 57110 -B 127.0.0.1` and wait for the `/status` reply (<=5s). `load_bubbles()` spawns `sclang <def_script>` and `wait()`s for exit 0. `spawn_bubbles()` sends `/s_new "bubbles"`. `set_param()` sends `/n_set`. `get_param()` sends `/s_get` and reads the `/n_set` reply with the `cb(path, args, types, src)` order. `status()` sends `/status` and returns the reply (with `numUgens`). `stop()` sends `quit` and terminates the process.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_sc.py -v`
Expected: PASS (unit tests always; `@scsynth_ok` tests pass when scsynth is installed)

- [ ] **Step 5: Commit**

```bash
git add src/super_quneo_collider/sc.py src/super_quneo_collider/bubbles.scd tests/test_sc.py
git commit -m "feat: scsynth lifecycle + one-shot sclang SynthDef delivery + OSC"
```

---

### Task 5: HTTP server and live bridge (server.py)

**Files:**
- Create: `src/super_quneo_collider/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `scale_cc`/`load_mapping` (Task 2), `MidiWatcher` (Task 3), `ScServer` (Task 4).
- Produces:
  - `class ColliderApp` — constructor kwargs `mapping`, `midi`, `sc`, `node=1000`. Methods `start()`, `status()`, `on_cc(cc: int, raw: int) -> None`.
  - `serve(config=None) -> None` — boots the app and serves HTTP on `127.0.0.1` with `GET /api/collider`.

`on_cc` scales `cc/raw` via the mapping and, if bound, stores `sliders[param] = value` and calls `sc.set_param(node, param, value)`. `status()` returns `{"present": midi.state()["present"], "sliders": {...}}`. `start()` runs `sc.boot()`, `sc.load_bubbles()`, `sc.spawn_bubbles(node)`, then `midi.start()`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_server.py
from pathlib import Path
from super_quneo_collider.map import load_mapping
from super_quneo_collider.server import ColliderApp

MAPPING = Path(__file__).resolve().parent.parent / "src" / "super_quneo_collider" / "mapping.json"

class FakeMidi:
    def __init__(self): self._state = {"present": True, "port": "24:0", "cc": {}}
    def state(self): return self._state

class FakeSc:
    def __init__(self): self.sets = []; self.booted = False; self.loaded = False; self.spawned = None
    def boot(self): self.booted = True; return True
    def load_bubbles(self): self.loaded = True; return True
    def spawn_bubbles(self, node): self.spawned = node; return True
    def set_param(self, node, param, value): self.sets.append((node, param, value))

def make_app():
    return ColliderApp(mapping=load_mapping(MAPPING), midi=FakeMidi(), sc=FakeSc(), node=1000)

def test_status_shape():
    st = make_app().status()
    assert isinstance(st["present"], bool)
    assert isinstance(st["sliders"], dict)

def test_on_cc_scales_and_sets_param():
    app = make_app()
    app.on_cc(61, 127)
    assert app.status()["sliders"]["wobble"] == 10.0
    assert (1000, "wobble", 10.0) in app.sc.sets

def test_on_cc_unbound_ignored():
    app = make_app()
    app.on_cc(85, 64)
    assert app.status()["sliders"] == {}
    assert app.sc.sets == []

def test_three_sliders_independent():
    app = make_app()
    app.on_cc(61, 63)
    app.on_cc(69, 64)
    assert app.status()["sliders"]["wobble"] == 4.961
    assert app.status()["sliders"]["innerWobble"] == 8.063
    assert (1000, "wobble", 4.961) in app.sc.sets
    assert (1000, "innerWobble", 8.063) in app.sc.sets

def test_start_boots_and_spawns():
    app = make_app()
    app.start()
    assert app.sc.booted and app.sc.loaded and app.sc.spawned == 1000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_server.py -v`
Expected: FAIL with `ModuleNotFoundError: super_quneo_collider.server`

- [ ] **Step 3: Implement `server.py`**

`ColliderApp` composes the three injected services. `serve()` follows op1-web's stdlib `ThreadingHTTPServer` pattern: `GET /api/collider` returns `self.app.status()` as JSON (`Cache-Control: no-store`), everything else falls through to the static client directory.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_server.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full suite and commit**

Run: `.venv/bin/pytest -v`
Expected: all tests PASS

```bash
git add src/super_quneo_collider/server.py tests/test_server.py
git commit -m "feat: HTTP /api/collider and live CC -> /n_set bridge"
```

---

## Out of scope for this plan (follow-on plans)

- **Frontend** — the three.js board model and poller (`client/`), which extends `LAYOUT.json` with the quark params (SPEC D4) and lights sliders from `/api/collider`. It uses the browser test harness, not pytest, and consumes the HTTP contract fixed in Task 5.
- **Test rig + e2e** — `tests/helpers/quneo_flash.py` (boots queneo-editor's editor server to flash the BasicSC preset) and the gherkin-driven hardware test (SPEC section 6, last feature). The runtime bridge never imports it.
