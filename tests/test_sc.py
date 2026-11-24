import json
import os
import threading
from pathlib import Path

import pytest

from super_quneo_collider.sc import (
    DEF_NAMES,
    VOICE_CAP_SECONDS,
    VOICE_FADE_SECONDS,
    ScServer,
    resolve_sclang,
    resolve_scsynth,
)

scsynth_ok = pytest.mark.skipif(
    resolve_scsynth() is None, reason="scsynth not installed"
)

# The catalog's examples, in catalog order.


def test_def_scripts_cover_every_catalog_example():
    # Every catalog entry maps to one shipped def fragment, in catalog order:
    # sc.py's _DEF_SCRIPTS (and DEF_NAMES) must enumerate them 1:1 (D7).
    catalog = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "src"
            / "super_quneo_collider"
            / "catalog.json"
        ).read_text()
    )
    defs = tuple(v["def"] for v in catalog["examples"].values())
    assert DEF_NAMES == tuple(defs)
    assert len(DEF_NAMES) == 15


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
        assert st and st["numUgens"] >= 0 and st["nominalSampleRate"] > 0
    finally:
        s.stop()


@scsynth_ok
def test_load_defs_delivers_all_examples():
    # D7: every example arrives at boot through the same one-shot sclang path,
    # so switching examples later is a pure control-plane event.
    s = ScServer()
    try:
        assert s.boot() is True
        assert s.load_defs() is True
        st = s.status()
        assert st["numDefs"] >= len(DEF_NAMES)
    finally:
        s.stop()


@scsynth_ok
def test_bubbles_defaults():
    s = ScServer()
    try:
        s.boot()
        s.load_defs()
        s.spawn("bubbles", 1000)
        assert s.get_param(1000, "wobble") == pytest.approx(0.4, abs=1e-3)
        assert s.get_param(1000, "innerWobble") == pytest.approx(8.0, abs=1e-3)
        assert s.get_param(1000, "releaseTime") == pytest.approx(4.0, abs=1e-3)
    finally:
        s.stop()


@scsynth_ok
def test_formant_and_sine_defaults():
    # Each example is its own def with its own defaults; the bridge spawns
    # whichever one the catalog says is active.
    s = ScServer()
    try:
        s.boot()
        s.load_defs()
        s.spawn("formant", 1000)
        assert s.get_param(1000, "fundfreq") == pytest.approx(440.0, abs=1e-2)
        assert s.get_param(1000, "bwfreq") == pytest.approx(100.0, abs=1e-2)
        s.spawn("sine", 1002, freq=880.0)
        assert s.get_param(1002, "freq") == pytest.approx(880.0, abs=1e-2)
    finally:
        s.stop()


@scsynth_ok
def test_n_set_changes_param():
    s = ScServer()
    try:
        s.boot()
        s.load_defs()
        s.spawn("bubbles", 1000)
        s.set_param(1000, "wobble", 10.0)
        assert s.get_param(1000, "wobble") == pytest.approx(10.0, abs=1e-3)
    finally:
        s.stop()


class _FakeProc:
    def __init__(self, returncode=0):
        self.returncode = returncode

    def wait(self, timeout=None):
        return self.returncode

    def poll(self):
        return self.returncode

    def terminate(self):
        pass


class RecordingSpawn:
    def __init__(self, calls):
        self.calls = calls

    def __call__(self, argv):
        self.calls.append(list(argv))
        return _FakeProc(0)


def test_batch_source_wraps_every_def_once():
    s = ScServer()
    src = s.batch_source()
    assert src.count('addr.sendMsg("/d_recv"') == len(DEF_NAMES)
    assert src.count("\nd = {\n") == len(DEF_NAMES)
    # `{ ... }.value` keeps multi-statement fragments (formant's Spec.specs
    # lines) legal while still yielding the SynthDef.
    assert src.count("\n}.value;\n") == len(DEF_NAMES)
    for name in DEF_NAMES:
        assert f"/{name}.scd" in src
    assert src.rstrip().endswith(")")
    assert "0.exit;" in src


def test_load_defs_uses_one_sclang_run():
    # One sclang process for every example: the defs travel as a composed batch,
    # so adding catalog entries does not add startup processes.
    calls = []
    s = ScServer(spawn=RecordingSpawn(calls), probe=lambda *a, **k: {"numDefs": len(DEF_NAMES)})
    assert s.load_defs() is True
    assert len(calls) == 1
    argv = calls[0]
    assert argv[0] == resolve_sclang()
    assert argv[1].endswith(".scd")
    # The generated batch is a temp file, and it is cleaned up again.
    assert not os.path.exists(argv[1])


def test_load_defs_confirms_defs_via_status():
    # load_defs must NOT return True merely because sclang exited 0; it must
    # poll scsynth and only succeed once numDefs shows every def registered.
    calls = []

    class SlowProbe:
        def __init__(self):
            self.n = 0

        def __call__(self):
            self.n += 1
            return {"numDefs": len(DEF_NAMES) if self.n > 2 else 0}

    s = ScServer(spawn=RecordingSpawn(calls), probe=SlowProbe())
    assert s.load_defs() is True


def test_load_defs_times_out_if_defs_never_confirm():
    calls = []

    class NeverConfirms:
        def __call__(self):
            return {"numDefs": 1}

    s = ScServer(spawn=RecordingSpawn(calls), probe=NeverConfirms())
    assert s.load_defs(timeout=0.2) is False


def test_load_defs_fails_when_sclang_exits_nonzero():
    calls = []

    class BadSpawn:
        def __call__(self, argv):
            calls.append(list(argv))
            return _FakeProc(1)

    s = ScServer(spawn=BadSpawn(), probe=lambda *a, **k: {"numDefs": len(DEF_NAMES)})
    assert s.load_defs() is False
    assert len(calls) == 1


def test_spawn_sends_the_named_def_with_its_args():
    s = ScServer()
    sent = []
    s._send = lambda *a: sent.append(a)
    s.spawn("sine", 1000, freq=440.0)
    assert sent[0] == ("/s_new", "sine", 1000, 0, 0, "freq", 440.0)


def test_boot_idempotent():
    # First boot: probe returns None -> spawn fires once. Second boot: probe
    # returns a valid status -> spawn does NOT fire again.
    spawns = []

    class Prober:
        def __init__(self):
            self.n = 0

        def __call__(self, *a, **k):
            self.n += 1
            return {"numUgens": 8} if self.n > 1 else None

    s = ScServer(spawn=lambda argv: spawns.append(argv), probe=Prober())
    assert s.boot() is True
    assert s.boot() is True
    assert len(spawns) == 1


# --- node notifications ----------------------------------------------------


def test_boot_asks_scsynth_to_report_node_ends():
    # scsynth is mute about /n_end until the client registers with /notify.
    # Without it the bridge cannot tell a finished voice from a live one, so a
    # voice that already stopped would look alive and be retuned instead of
    # respawned (and a leak could never be noticed).
    sent = []
    s = ScServer(probe=lambda *a, **k: {"numUgens": 8})
    s._send = lambda *a: sent.append(a)
    assert s.boot() is True
    assert ("/notify", 1) in sent


def test_node_end_reaches_the_hook_with_its_node_id():
    s = ScServer()
    s._cond = threading.Condition()
    s._replies = {}
    ended = []
    s.on_node_end = ended.append
    s._dispatch("/n_end", [3000, 0, -1, -1, 0], "iiiii", None)
    assert ended == [3000]
    assert "/n_end" in s._replies  # the generic reply cache is untouched


def test_a_raising_node_end_hook_cannot_kill_the_receive_loop():
    s = ScServer()
    s._cond = threading.Condition()
    s._replies = {}

    def boom(_node):
        raise RuntimeError("boom")

    s.on_node_end = boom
    s._dispatch("/n_end", [3001, 0, -1, -1, 0], "iiiii", None)


def test_set_params_sends_one_message_with_every_pair():
    # One /n_set for the whole state: a retune must not be applied piecemeal.
    s = ScServer()
    sent = []
    s._send = lambda *a: sent.append(a)
    s.set_params(3000, wobble=4.961, nPartials=32, fade=1)
    assert sent == [("/n_set", 3000, "wobble", 4.961, "nPartials", 32, "fade", 1)]


# --- the voice ceiling and the stop fade (the shipped def contract) --------
# The rule: nothing rings past VOICE_CAP_SECONDS, and the last
# VOICE_FADE_SECONDS of it is a fade.  `gate 0` fades that same window out of a
# voice at any age (selection change, fade toggle); `fade 0` bypasses the
# ceiling so a voice may ring on.  The numbers live in the fragments, so these
# tests read them back out of the batch that actually ships to sclang.


def test_every_catalogued_def_carries_the_stop_fade_and_the_ceiling():
    src = ScServer().batch_source()
    n = len(DEF_NAMES)
    assert src.count("arg out=0") == n
    assert src.count("gate=1") == n
    assert src.count("fade=1") == n
    assert src.count("Env.asr(0.01, 1, 3)") == n
    assert src.count("Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin')") == n
    assert src.count("Select.kr(fade > 0, [1, fadeEnv])") == n
    assert src.count("DetectSilence.ar(") == n


def test_the_ceiling_matches_the_stated_cap_and_fade():
    assert (VOICE_CAP_SECONDS, VOICE_FADE_SECONDS) == (12.0, 3.0)
    hold = VOICE_CAP_SECONDS - VOICE_FADE_SECONDS
    src = ScServer().batch_source()
    n = len(DEF_NAMES)
    assert src.count(f"Env.asr(0.01, 1, {VOICE_FADE_SECONDS:g})") == n
    assert (
        src.count(
            f"Env.new([0, 1, 1, 0], [0.01, {hold:g}, {VOICE_FADE_SECONDS:g}], 'lin')"
        )
        == n
    )
