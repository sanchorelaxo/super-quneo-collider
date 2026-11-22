"""MIDI presence + live slider CC events for the QuNeo bridge.

The QuNeo over USB exposes an ALSA sequencer port "QuNeo MIDI 1"; touching a
vertical slider emits a control-change event there. The midi module discovers
the port from /proc/asound/seq/clients and pumps aseqdump output into a small
state dict the server exposes at /api/collider (slider positions).

Nothing here may spawn a real subprocess or read the real /proc during tests:
port discovery and the aseqdump spawn are injected, and the watcher only ever
touches the filesystem through the passed-in path.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from super_quneo_collider import midi

# Verbatim shape of /proc/asound/seq/clients while a QuNeo is plugged in
# (captured live: sequencer client 24, port "QuNeo MIDI 1").
QUEO_CLIENTS = """Client   0 : "System" [Kernel]
  Port   0 : "Timer" (RWeX) [In/Out]
Client  14 : "Midi Through" [Kernel]
  Port   0 : "Midi Through Port-0" (RWe-) [In/Out]
Client  24 : "QuNeo" [Kernel Legacy]
  Port   0 : "QuNeo MIDI 1" (RWeX) [In/Out]
"""

# A second live shape to prove the client number is discovered, not assumed.
QUEO_CLIENTS_ALT = """Client  16 : "QuNeo" [Kernel Legacy]
  Port   0 : "QuNeo MIDI 1" (RWeX) [In/Out]
"""

NO_QUEO_CLIENTS = """Client  14 : "Midi Through" [Kernel]
  Port   0 : "Midi Through Port-0" (RWe-) [In/Out]
"""

QUEO_NO_MIDI_PORT = """Client  24 : "QuNeo" [Kernel Legacy]
  Port   0 : "QuNeo " (RWe-) [In/Out]
"""


def write_clients(tmp_path, text):
    path = tmp_path / "clients"
    path.write_text(text)
    return path


class TestPortDiscovery:
    def test_finds_the_quneo_midi_port(self, tmp_path):
        assert midi.find_quneo_midi_port(path=write_clients(tmp_path, QUEO_CLIENTS)) == "24:0"

    def test_reads_the_client_number_instead_of_assuming(self, tmp_path):
        assert midi.find_quneo_midi_port(path=write_clients(tmp_path, QUEO_CLIENTS_ALT)) == "16:0"

    def test_returns_none_without_a_quneo(self, tmp_path):
        assert midi.find_quneo_midi_port(path=write_clients(tmp_path, NO_QUEO_CLIENTS)) is None

    def test_returns_none_when_quneo_has_no_midi_port(self, tmp_path):
        assert midi.find_quneo_midi_port(path=write_clients(tmp_path, QUEO_NO_MIDI_PORT)) is None


class TestEventParsing:
    def test_parses_a_channel_0_cc_line(self):
        ev = midi.parse_aseqdump_line(
            " 24:0   Control change          0, controller 19, value 41"
        )
        assert ev == {"channel": 0, "cc": 19, "value": 41}

    def test_parses_a_channel_15_cc_line(self):
        ev = midi.parse_aseqdump_line(
            " 24:0   Control change         15, controller 61, value 64"
        )
        assert ev == {"channel": 15, "cc": 61, "value": 64}

    def test_ignores_note_events(self):
        assert midi.parse_aseqdump_line(" 24:0   Note on                 0, note 7, velocity 127") is None

    def test_ignores_the_header(self):
        assert midi.parse_aseqdump_line("Source  Event                  Ch  Data") is None
        assert midi.parse_aseqdump_line("") is None


class FakeProc:
    """Popen stand-in built on a REAL pipe, so the blocking reader thread's
    EOF semantics are exercised, not mocked around. The writer stays open
    unless close_writer=True (like a live aseqdump that never closes stdout)."""

    def __init__(self, lines=(), close_writer=False):
        self._r, self._w = os.pipe()
        for line in lines:
            os.write(self._w, (line + "\n").encode())
        if close_writer:
            os.close(self._w)
            self._w = None
        self._reader = open(self._r, encoding="utf-8")
        self._dead = close_writer
        self.terminated = False

    @property
    def stdout(self):
        return self._reader

    def poll(self):
        return -15 if self._dead else None

    def terminate(self):
        self.terminated = True
        self._dead = True
        if self._w is not None:
            try:
                os.close(self._w)  # raw fd: closing the write end gives EOF
            except OSError:
                pass
            self._w = None
        try:
            self._reader.close()
        except OSError:
            pass

    def wait(self, timeout=None):
        return -15 if self._dead else None


def make_watcher(lines=(), clients=QUEO_CLIENTS, tmp_path=None, close_writer=False, on_event=None):
    clients_path = write_clients(tmp_path, clients)
    spawned = []

    def fake_spawn(argv):
        proc = FakeProc(list(lines), close_writer=close_writer)
        spawned.append((argv, proc))
        return proc

    watcher = midi.MidiWatcher(
        port_finder=lambda: midi.find_quneo_midi_port(path=clients_path),
        spawn=fake_spawn,
        on_event=on_event,
    )
    return watcher, spawned


def wait_for(predicate, timeout=2.0):
    """Poll predicate until true; the reader runs on its own thread now."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


class TestWatcherState:
    def test_records_channel_15_cc(self, tmp_path):
        watcher, spawned = make_watcher(
            lines=[" 24:0   Control change         15, controller 61, value 64"],
            tmp_path=tmp_path,
        )
        watcher.tick()
        assert wait_for(lambda: watcher.state()["cc"].get(61) == 64)
        st = watcher.state()
        assert st["present"] is True and st["port"] == "24:0"

    def test_drops_cc_on_other_channels(self, tmp_path):
        watcher, _ = make_watcher(
            lines=[" 24:0   Control change          7, controller 61, value 99"],
            tmp_path=tmp_path,
            close_writer=True,  # single line then EOF: deterministic completion
        )
        watcher.tick()
        assert wait_for(lambda: watcher._proc is None)
        assert watcher.state()["cc"] == {}

    def test_fires_on_event_for_channel_15(self, tmp_path):
        seen = []
        watcher, _ = make_watcher(
            lines=[" 24:0   Control change         15, controller 61, value 64"],
            tmp_path=tmp_path,
            on_event=lambda cc, value: seen.append((cc, value)),
        )
        watcher.tick()
        assert wait_for(lambda: len(seen) == 1)
        assert seen == [(61, 64)]
