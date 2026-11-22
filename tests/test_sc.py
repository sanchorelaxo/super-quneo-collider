import os

import pytest

from super_quneo_collider.sc import ScServer, resolve_sclang, resolve_scsynth

scsynth_ok = pytest.mark.skipif(
    resolve_scsynth() is None, reason="scsynth not installed"
)


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
def test_bubbles_defaults():
    s = ScServer()
    try:
        s.boot()
        s.load_bubbles()
        s.spawn_bubbles(1000)
        assert s.get_param(1000, "wobble") == pytest.approx(0.4, abs=1e-3)
        assert s.get_param(1000, "innerWobble") == pytest.approx(8.0, abs=1e-3)
        assert s.get_param(1000, "releaseTime") == pytest.approx(4.0, abs=1e-3)
    finally:
        s.stop()


@scsynth_ok
def test_n_set_changes_param():
    s = ScServer()
    try:
        s.boot()
        s.load_bubbles()
        s.spawn_bubbles(1000)
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


def test_load_bubbles_terminates_clean():
    # Inject a fake spawn that asserts the argv is positional-file (not stdin),
    # returns exit 0, and a probe that confirms the def registered; load_bubbles
    # must wait() on sclang and then confirm delivery before returning True.
    calls = []
    s = ScServer(
        spawn=RecordingSpawn(calls),
        def_script="/tmp/bubbles.scd",
        probe=lambda *a, **k: {"numDefs": 1},
    )
    assert s.load_bubbles() is True
    argv = calls[0]
    assert "/tmp/bubbles.scd" in argv and "0.exit" not in argv


def test_load_bubbles_confirms_def_via_status():
    # load_bubbles must NOT return True merely because sclang exited 0; it must
    # poll scsynth and only succeed once numDefs shows the def registered.
    calls = []

    class SlowProbe:
        def __init__(self):
            self.n = 0

        def __call__(self):
            self.n += 1
            return {"numDefs": 1 if self.n > 2 else 0}

    s = ScServer(spawn=RecordingSpawn(calls), probe=SlowProbe())
    assert s.load_bubbles() is True


def test_load_bubbles_times_out_if_def_never_confirms():
    calls = []

    class NeverConfirms:
        def __call__(self):
            return {"numDefs": 0}

    s = ScServer(spawn=RecordingSpawn(calls), probe=NeverConfirms())
    assert s.load_bubbles(timeout=0.2) is False


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
