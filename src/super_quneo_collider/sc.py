"""scsynth lifecycle: one-shot sclang SynthDef delivery + OSC control plane.

The bridge boots a raw ``scsynth`` (no resident sclang ``Server``), so the
"bubbles" SynthDef is delivered by a one-shot ``sclang bubbles.scd`` at
startup, and everything after that is pyliblo3: ``/s_new``, ``/n_set``,
``/s_get`` and ``/status``.

Raw scsynth has no "default group 1" (that group is created by sclang's
``Server`` when it connects).  The root node is group 0, so ``/s_new`` targets
group 0 with addAction ``addToHead`` (0).

pyliblo3's reply callback order is ``cb(path, args, types, src)``; ``/s_get``
replies arrive as ``/n_set [node, "param", value]`` and ``/status`` replies as
``/status.reply [unused, numUgens, ...]``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

try:
    import liblo
except ImportError:  # pragma: no cover - liblo alias availability
    import pyliblo3 as liblo

_SCSYNTH_BIN = "scsynth"
_SCLANG_BIN = "sclang"
_DEFAULT_DEF_SCRIPT = Path(__file__).resolve().parent / "bubbles.scd"

_STATUS_KEYS = (
    "numUgens",
    "numSynths",
    "numGroups",
    "numDefs",
    "avgCPU",
    "peakCPU",
    "nominalSampleRate",
    "actualSampleRate",
)


def resolve_scsynth() -> str | None:
    return _resolve_bin(_SCSYNTH_BIN)


def resolve_sclang() -> str | None:
    return _resolve_bin(_SCLANG_BIN)


def _resolve_bin(name: str) -> str | None:
    p = shutil.which(name)
    if p:
        return p
    for cand in (f"/usr/bin/{name}", f"/usr/local/bin/{name}"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


class ScServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 57110,
        scsynth_path: str | None = None,
        sclang_path: str | None = None,
        def_script: str | None = None,
        spawn=None,
        probe=None,
        clock=time.monotonic,
    ):
        self.host = host
        self.port = port
        self._scsynth_path = scsynth_path
        self._sclang_path = sclang_path
        self._def_script = str(def_script) if def_script else str(_DEFAULT_DEF_SCRIPT)
        self._spawn = spawn if spawn is not None else subprocess.Popen
        self._clock = clock
        self._probe = probe if probe is not None else self.status
        self._proc = None

        # Receive side is initialised lazily on first OSC use.
        self._target = None
        self._server = None
        self._cond = None
        self._replies = {}
        self._stop = threading.Event()
        self._recv_thread = None

    # -- OSC plumbing ------------------------------------------------------
    def _ensure_server(self) -> None:
        if self._server is not None:
            return
        self._target = liblo.Address(self.host, self.port)
        self._cond = threading.Condition()
        self._replies = {}
        self._server = liblo.Server()
        self._server.add_method(None, None, self._dispatch)
        self._stop.clear()
        self._recv_thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._recv_thread.start()

    def _dispatch(self, path, args, types, src, user_data=None):
        with self._cond:
            self._replies[path] = (list(args), types)
            self._cond.notify_all()

    def _serve_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._server.recv(100)
            except Exception:
                pass

    def _send(self, path: str, *args) -> None:
        self._ensure_server()
        self._server.send(self._target, path, *args)

    def _rpc(self, wait_for: str, path: str, *args, timeout: float = 3.0):
        self._ensure_server()
        with self._cond:
            self._replies.pop(wait_for, None)
        self._server.send(self._target, path, *args)
        deadline = self._clock() + timeout
        with self._cond:
            while wait_for not in self._replies:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    return None
                self._cond.wait(timeout=remaining)
            return self._replies[wait_for]

    # -- lifecycle ---------------------------------------------------------
    def boot(self) -> bool:
        if self._probe():
            return True
        argv = [
            self._scsynth_path or resolve_scsynth(),
            "-u",
            str(self.port),
            "-B",
            self.host,
        ]
        self._proc = self._spawn(argv)
        deadline = self._clock() + 5.0
        while self._clock() < deadline:
            if self._probe():
                return True
            time.sleep(0.1)
        return False

    def load_bubbles(self, timeout: float = 5.0) -> bool:
        argv = [self._sclang_path or resolve_sclang(), self._def_script]
        proc = self._spawn(argv)
        if proc.wait() != 0:
            return False
        # scsynth does not ack /d_recv, and the one-shot sclang exits as soon as
        # the message is queued, so an immediate /s_new can race the delivery.
        # Confirm the def actually registered (numDefs climbs past zero) before
        # returning, otherwise the caller's /s_new hits "SynthDef not found".
        deadline = self._clock() + timeout
        while self._clock() < deadline:
            st = self._probe()
            if st and st.get("numDefs", 0) >= 1:
                return True
            time.sleep(0.1)
        return False

    def spawn_bubbles(self, node: int = 1000) -> bool:
        self._send("/s_new", "bubbles", int(node), 0, 0)
        return True

    def set_param(self, node: int, param: str, value: float) -> None:
        self._send("/n_set", int(node), param, float(value))

    def get_param(self, node: int, param: str) -> float | None:
        reply = self._rpc("/n_set", "/s_get", int(node), param)
        if not reply:
            return None
        args, _types = reply
        for i in range(1, len(args) - 1, 2):
            if args[i] == param:
                return args[i + 1]
        return None

    def status(self) -> dict | None:
        reply = self._rpc("/status.reply", "/status")
        if not reply:
            return None
        args, _types = reply
        # scsynth replies with a leading unused int, then the eight fields.
        return dict(zip(_STATUS_KEYS, args[1:]))

    def stop(self) -> None:
        try:
            if self._server is not None:
                self._server.send(self._target, "/quit")
        except Exception:
            pass
        if self._proc is not None:
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
                    self._proc.wait(timeout=2)
            except Exception:
                pass
        self._stop.set()
