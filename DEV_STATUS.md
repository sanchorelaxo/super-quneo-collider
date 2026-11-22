# DEV_STATUS — super-quneo-collider

Last updated: 2026-11-22

## Current state

- Project is spec-only. No runtime code yet.
- The §8 validating spike for D3 (SynthDef delivery) is COMPLETE and PASSED.
- SPEC.md §8 risk #1 is now marked RESOLVED.

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

## Port action items (for the real sc.py / osc_service.py port)

- [ ] Use `cb(path, args, types, src)` — fix the inherited callback order.
- [ ] Deliver `bubbles` via a one-shot `sclang` subprocess at startup (spawn, then
      `wait()`), exactly as the spike's `deliver_def.scd`.
- [ ] Python control plane via pyliblo3: `/s_new` on pad press, `/n_set` on CC change,
      `/s_get` for the D3-spec defaults check.
- [ ] Do not attempt python `/d_recv`; it cannot work on pyliblo3.

## Spike scratch (throwaway, /tmp)

- `/tmp/deliver_def.scd` — the working sclang `/d_recv` delivery (reference for the port).
- `/tmp/spike_roundtrip.py` — the working pyliblo3 `/s_new`/`/n_set`/`/s_get` round-trip.
- `/tmp/asbytes_probe.scd`, `/tmp/sc_min.scd` — one-shot invocation + asBytes probes.
- `/tmp/synthdefs/bubbles.scsyndef` — compiled def (1113 bytes, `SCgf` magic).
- `/tmp/scsynth.log` — scsynth boot log (still running in background this session).

## Environment facts

- scsynth / sclang both 3.13.0 at `/usr/bin/scsynth` and `/usr/bin/sclang`.
- toolchain venv: `/home/rjodouin/Documents/git/queneo-editor/.venv` (CPython 3.14.4,
  pyliblo3 0.17.0). Rebuilt after the OS upgrade to 3.14.
- QuNeo ALSA client "QuNeo MIDI 1" resolves by NAME, never by number.
