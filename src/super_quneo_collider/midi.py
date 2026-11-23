"""QuNeO MIDI presence and live slider control-change events.

A plugged-in QuNeo exposes an ALSA sequencer port called "QuNeo MIDI 1";
touching the vertical sliders emits control-change events there. This module
discovers the port by reading /proc/asound/seq/clients and pumps the events out
of an ``aseqdump`` subprocess into a small in-memory state the server exposes
at /api/collider (slider positions) and the presence pill.

Port discovery and process spawn are injectable so tests never touch the real
sequencer. Line reading runs on a dedicated blocking thread: reading lines off
a non-blocking pipe cannot tell "no data yet" from EOF (both look like ""),
which would make the poller kill a healthy aseqdump over and over.

Only control-change events on the configured channel (BasicSC_QuNeo uses 15)
are kept; parse understands every control-change line regardless of channel,
and the watcher drops the ones on a different channel.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path

SEQ_CLIENTS_PATH = "/proc/asound/seq/clients"
EVENT_HISTORY = 32

_CLIENT_RE = re.compile(r'^Client\s+(\d+)\s*:\s*"([^"]*)"')
_PORT_RE = re.compile(r'^\s+Port\s+(\d+)\s*:\s*"([^"]*)"')
_CC_RE = re.compile(
    r"^\s*\d+:\d+\s+Control change\s+(\d+), controller (\d+), value (\d+)\s*$"
)
_NOTE_RE = re.compile(
    r"^\s*\d+:\d+\s+Note (on|off)\s+(\d+), note (\d+), velocity (\d+)\s*$"
)


def find_quneo_midi_port(path: str | Path = SEQ_CLIENTS_PATH) -> str | None:
    """Return "<client>:<port>" for the QuNeo's MIDI port, or None.

    The QuNeo appears as sequencer client "QuNeo" with a port named
    "QuNeo MIDI 1". No matching client means the board is unplugged or not in
    its MIDI mode, so no sequencer entry means no controller.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    client: str | None = None
    for line in text.splitlines():
        m = _CLIENT_RE.match(line)
        if m:
            client = m.group(1) if "quneo" in m.group(2).lower() else None
            continue
        m = _PORT_RE.match(line)
        if client is not None and m and "quneo midi" in m.group(2).lower():
            return f"{client}:{m.group(1)}"
    return None


def parse_aseqdump_line(line: str) -> dict | None:
    """Structure aseqdump's control-change and note lines.

    Control change -> ``{"channel", "cc", "value"}``.
    Note on/off     -> ``{"channel", "note", "velocity", "on"}`` where ``on``
    is True only for a "Note on" whose velocity is non-zero (a note-on with
    velocity 0 is a running-status release).  Every other event -> None.
    """
    m = _CC_RE.match(line)
    if m:
        return {
            "channel": int(m.group(1)),
            "cc": int(m.group(2)),
            "value": int(m.group(3)),
        }
    m = _NOTE_RE.match(line)
    if m:
        velocity = int(m.group(4))
        return {
            "channel": int(m.group(2)),
            "note": int(m.group(3)),
            "velocity": velocity,
            "on": m.group(1) == "on" and velocity > 0,
        }
    return None


def aseqdump_argv(port: str) -> list[str]:
    """Line-buffered aseqdump: its stdout is a pipe, so force per-line flush."""
    return ["stdbuf", "-oL", "aseqdump", "-p", port]


def _default_spawn(argv: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )


def _terminate_orphan_readers() -> None:
    """SIGTERM still-alive aseqdump children inherited across an execve
    restart. They keep a sequencer subscription and their old image is gone,
    so nobody will ever terminate them; silence means a broken pipe can go
    unnoticed for a whole session."""
    me = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = entry.joinpath("stat").read_text()
            comm = stat.split("(", 1)[1].split(") ", 1)[0]
            ppid = int(stat.split(") ", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            continue
        if ppid == me and comm in ("stdbuf", "aseqdump"):
            try:
                os.kill(int(entry.name), signal.SIGTERM)
            except OSError:
                pass


def _reap_stray_children(deadline_seconds: float = 1.0) -> None:
    """Collect unreached children left by previous process generations."""
    _terminate_orphan_readers()
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:  # no children left
            return
        if pid == 0:
            time.sleep(0.05)


class MidiWatcher:
    """Track the QuNeo MIDI port and the current slider CC values."""

    def __init__(
        self,
        port_finder=None,
        spawn=None,
        clock=time.monotonic,
        channels: int | set[int] = 15,
        on_event=None,
    ) -> None:
        self._port_finder = port_finder or find_quneo_midi_port
        self._spawn = spawn or _default_spawn
        self._clock = clock
        self._channels = {channels} if isinstance(channels, int) else set(channels)
        self._on_event = on_event
        self._present: bool | None = None
        self._port: str | None = None
        self._proc = None
        # CC and note state are namespaced by MIDI channel: a pad xCC (ch 15)
        # and a rotary locCC (ch 14) can share a controller number, and a pad
        # note (ch 15) and a rotary note (ch 14) can share a note number, so a
        # flat {number: value} map would merge distinct controls.
        self._cc: dict[int, dict[int, int]] = {}
        self._note: dict[int, dict[int, bool]] = {}
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    # --- public --------------------------------------------------------
    def start(self, poll_seconds: float = 0.5) -> None:
        """Begin polling in a daemon thread; safe to call once per process."""
        if self._thread is not None:
            return
        _reap_stray_children()
        self._thread = threading.Thread(
            target=self._run, args=(poll_seconds,), daemon=True, name="midi-watcher"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self._teardown_locked()

    def state(self) -> dict:
        with self._lock:
            return {
                "present": self._present,
                "port": self._port,
                "cc": {ch: dict(vals) for ch, vals in self._cc.items()},
                "note": {ch: dict(vals) for ch, vals in self._note.items()},
            }

    def tick(self) -> None:
        """One poll cycle: refresh presence, (re)spawn the reader if needed."""
        with self._lock:
            try:
                port = self._port_finder()
            except OSError:
                port = None
            if port is None:
                self._teardown_locked()
                self._present = False
                self._port = None
                self._cc.clear()
                self._note.clear()
                return
            self._present = True
            self._port = port
            if self._proc is None or self._proc.poll() is not None:
                self._spawn_locked(port)

    # --- internals -----------------------------------------------------
    def _run(self, poll_seconds: float) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - keep the daemon alive
                pass
            self._stop.wait(poll_seconds)

    def _spawn_locked(self, port: str) -> None:
        self._teardown_locked()
        try:
            proc = self._spawn(aseqdump_argv(port))
        except OSError:
            return
        self._proc = proc
        threading.Thread(
            target=self._pump, args=(proc,), daemon=True, name="midi-pump"
        ).start()

    def _teardown_locked(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
            except OSError:
                pass
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    self._proc.kill()
                except OSError:
                    pass
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            self._proc = None

    def _pump(self, proc) -> None:
        try:
            for line in proc.stdout:
                with self._lock:
                    if self._proc is not proc:
                        return
                    ev = parse_aseqdump_line(line)
                    if ev is None:
                        continue
                    if ev["channel"] not in self._channels:
                        continue
                    if "note" in ev:
                        self._note.setdefault(ev["channel"], {})[ev["note"]] = ev["on"]
                    else:
                        self._cc.setdefault(ev["channel"], {})[ev["cc"]] = ev["value"]
                        if self._on_event is not None:
                            self._on_event(ev["cc"], ev["value"])
        except (OSError, ValueError):
            pass  # stdout closed by teardown or the child died
        finally:
            try:
                if proc.poll() is not None:
                    proc.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                pass
        with self._lock:
            if self._proc is proc:
                self._proc = None
                try:
                    if proc.poll() is None:
                        proc.terminate()
                        proc.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    pass
