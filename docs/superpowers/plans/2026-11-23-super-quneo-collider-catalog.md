# super-quneo-collider — the example catalog (increment 2, Stage 1)

**Goal:** SPEC §9 / D7–D9. Replace the hard-coded `bubbles` binding with a selectable
example catalog. This plan covers **Stage 1** only: the four supercolliderjs entries
(`bubbles`, `formant`, `sine`, `klang`) end to end, each `continuous` on the slider
ladder of §9.2. Stage 2 — the four documentation examples, the 109 SCLOrkSynths defs,
`gesture: oneshot` pad corners, and the full 117-entry select — is planned separately
and builds directly on this stage.

**Spec:** SPEC.md §9.1–§9.5; §3 D7/D8; §6 "Feature: Select a sound example"
(scenarios 1–7); §7 DoD bullets 8, 9, 11.

**Out of scope in this stage (deliberately):** `gesture: oneshot`, pad-corner
addressing (index = pad\*4 + quadrant), gate handling for gated synths, the
`exampleCatalog` grouping by source, the 113 further entries.

## Rulings

- **`bubbles` stays on the slider ladder, catalogued `continuous`.** §9.2/§5/§6 and the
  existing base test all bind it to the vSliders; D9's literal rule (Env.linen +
  doneAction: 2 with no `gate` ⇒ `oneshot`) would move it to a pad corner and
  contradict them. D9's read rule is applied from Stage 2, where it does not conflict.
  *Cost if wrong:* one word in `catalog.json` changes; behaviour is unaffected.
- **`on_event` grows the MIDI channel: `on_cc(channel, cc, value)`.** ch14 cc1
  (`rotaryButton0` → formant `pan`) and ch15 cc1 (pad `xCC`) share a controller number,
  so a channel-blind binding cannot resolve `pan`. *Cost if wrong:* one signature
  reverted across `midi.py`, `server.py` and their tests.
- **Selecting an example resets accumulated slider state to that example's `default`s.**
  Otherwise the newly bound params inherit the previous example's parameter names.
  *Cost if wrong:* the next spawn carries the source default rather than the stale
  position of the example you just left — the safer of the two.
- **Helper text is generated server-side** and exposed as `helper: [line, ...]` on
  `/api/collider`, so SPEC §9.5's block is unit-tested in Python byte for byte.
  *Cost if wrong:* the field moves to the client.
- **Each `*.scd` holds the SynthDef expression assigned to `d`; `sc.load_defs()`
  composes one sclang batch** that `/d_recv`s every def and exits. The SynthDef bodies
  stay verbatim from supercolliderjs apart from delivery mechanics (`.add` removed in
  favour of an explicit blob send; `klang` `var` → `arg`; `sine` reshaped per §9.3).
  *Cost if wrong:* the composition moves into a checked-in `defs.scd`.

## Tasks

### F1 — `catalog.json`, and catalog-driven bindings in `map.py`

Files: `src/super_quneo_collider/catalog.json` (new), `mapping.json`, `map.py`,
`tests/test_map.py`.

1. RED — `tests/test_map.py`: replace the `param_for_cc`/`scale_cc` tests with:
   - `load_catalog()` returns 4 examples, ordered `bubbles, formant, sine, klang`,
     `default == "bubbles"`;
   - `scale_value(raw, lo, hi, curve)`: lin `0→lo`, `127→hi`, `64→` midpoint;
     exp `0→lo`, `127→hi` (raw 0 must NOT be 0 Hz); int `127→` hi, rounded;
   - `bindings(catalog, "formant", mapping)` keys `(15, 61)`→fundfreq and
     `(14, 1)`→pan, resolving `control` → `mapping.json` identity (never a literal);
   - the Gherkin table: formant cc61 raw 127→10240.0, raw 0→40.0; sine cc61
     127→2000.0; klang cc61 127→32; klang cc69 127→8;
   - `helper_lines(...)` for formant equals SPEC §9.5's block exactly;
   - every example binds ≥1 param.
2. GREEN — `mapping.json`: drop `param`/`min`/`max` from `vSliderButton0..2`.
   `catalog.json`: 4 entries, `params` with `name/control/cc/min/max/curve/default`
   (+`channel` only where it differs from the preset channel, +`unit` for the Hz
   params and `rangeLabel: "L..R"` for `pan`). `map.py`: `load_catalog`, `scale_value`
   (lin/exp/int), `bindings`, `example_ids`, `default_example_id`, `helper_lines`;
   delete `param_for_cc`/`scale_cc`.
3. `pytest tests/test_map.py`.

### F2 — the four SynthDefs in one sclang batch

Files: `bubbles.scd` (rewritten), `formant.scd`, `sine.scd`, `klang.scd` (new),
`sc.py`, `tests/test_sc.py`.

1. RED — `tests/test_sc.py`: `load_defs()` composes ONE `sclang` argv whose script
   contains all four def names and a trailing `0.exit`; `load_defs` reports ready when
   `/status` reports `numDefs >= 4`; `spawn_bubbles` generalises to `spawn(def, node,
   **args)` reaching `/s_new`; keep the existing boot/status/stop tests.
2. GREEN — write the four `.scd` files (formant verbatim incl. `Spec.specs.put`, klang
   `nPartials`/`nChans` promoted to `arg`s, sine per §9.3, bubbles as today); `sc.py`
   generates the batch script into a temp file, spawns sclang once, then polls
   `/status`.
3. Verify against the real server: `.venv/bin/python` boots scsynth, loads all four,
   asserts `numDefs >= 4`, and `/s_new`s each def with the Gherkin's args.

### F3 — the bridge selects and re-binds (`server.py`, `midi.py`)

Files: `server.py`, `midi.py`, `tests/test_server.py`, `tests/test_midi.py`.

1. RED — `midi.py`: `on_event` is called with the channel (`on_cc(channel, cc,
   value)`), including a ch14 event. `server.py`: `GET /api/collider` carries
   `examples` (ordered ids) and `activeExample == "bubbles"`; `POST
   /api/collider/example {"id": "formant"}` moves `activeExample`, resets `sliders` to
   the new defaults, and the next locCC 61 spawns formant's `fundfreq`; an unknown id
   is a 400 and leaves the active example alone; selecting writes nothing to the
   QuNeo (no MIDI output call recorded) and performs no compile.
2. GREEN — implement.
3. `pytest tests/test_server.py tests/test_midi.py`.

### F4 — the select and the helper text (`client/`)

Files: `client/src/select.js` (new), `client/src/api.js`, `client/index.html`,
`client/tests/select.test.js` (new), `client/tests/index.html`.

1. RED — `select.test.js`: `exampleOptions(state)` returns `state.examples` in order
   with the active one marked; `helperLines(state)` returns `state.helper`;
   `chooseExample(id, post)` POSTs `{"id": id}` to `/api/collider/example`;
   `selectMarkup` (or equivalent) renders one `<option>` per example.
2. GREEN — `api.js` gains `getState`'s sibling `selectExample`; `index.html` gains the
   top-left `<select id="example">` + `<pre id="helper">` wired to the poller.
3. Run the browser harness over HTTP via the bridge's own `serve()` and read
   `window.__TESTS__` through CDP (no bundler, no node_modules).

### F5 — live verification on the connected QuNeo

Boot the real bridge (QuNeo at ALSA client 24), GET `/api/collider` (4 examples,
`activeExample: bubbles`), POST `formant`, touch vSlider0, read back `sliders`, and
confirm the helper text and the lit board in the browser. Commit per task; no
`git push`.
