"""Live bridge: MIDI CC -> the active example's SynthDef, exposed as HTTP JSON.

``ColliderApp`` composes the fixed MIDI inventory (``mapping.json``), the
selectable example catalog (``catalog.json``), the ``MidiWatcher`` and the
``ScServer``.  Exactly one example is active at a time (D8): selecting one only
re-binds the scaling and changes which def the next spawn names.  It never
touches the board and never compiles anything, because every def in the catalog
was already delivered at boot through the one-shot sclang path (D7).

``on_cc`` scales a raw CC along the active example's binding for that
``(channel, cc)`` and shapes the active example's voice: the first activity
starts a node the bridge owns under a real id (never scsynth's ``-1``), and
later activity retunes that same node with one ``/n_set``.  Selecting an
example, or toggling the ceiling, fades the live voice out (``gate 0`` -> the
def's 3 s stop fade) and forgets it.  ``serve()`` is the process entry point: it
boots the app, wires the watcher's ``on_event`` to ``on_cc``, and serves the
JSON API plus the static client on ``127.0.0.1``.

Two admin routes back the buttons in the client's bottom right corner: ``POST
/api/collider/reset`` blanks the board (see :mod:`super_quneo_collider.board`)
and forgets the state it had mirrored, and ``POST /api/collider/restart``
answers the caller, then replaces this process with a fresh copy of the bridge.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from super_quneo_collider import board
from super_quneo_collider.audio import route_audio
from super_quneo_collider.map import (
    DEFAULT_CATALOG,
    DEFAULT_MAPPING,
    bindings,
    channels,
    default_example_id,
    default_params,
    helper_lines,
    load_catalog,
    load_mapping,
    scale_value,
)
from super_quneo_collider.midi import MidiWatcher
from super_quneo_collider.sc import ScServer

_DEFAULT_CLIENT_DIR = Path(__file__).resolve().parent.parent.parent / "client"

# How often the bridge re-discovers the default sink.  The audio router is
# idempotent (it only unlinks/links what changed), so a short period is cheap
# and keeps scsynth following a sink that hot-swapped in after boot.
_RE_ROUTE_SECONDS = 3.0

# A restart answers first and hands the process over a beat later, so the client
# sees a clean reply instead of a connection that died mid-request.
_RESTART_DELAY = 0.4

# When this process was imported (what ``uptime_s`` counts from), and which
# process image this is.  A restart hands the image over with ``execve``, so the
# pid survives it: the boot id is what changes, and the client waits for a
# different one before it believes the new bridge is the one answering.
_STARTED_AT = time.monotonic()
_BOOT_ID = os.urandom(4).hex()


class ColliderApp:
    def __init__(
        self,
        mapping,
        catalog,
        midi,
        sc,
        node=1000,
        router=route_audio,
        active=None,
        fade=True,
        darken=None,
        replace=None,
        http_port=8686,
    ):
        self.mapping = mapping
        self.catalog = catalog
        self.midi = midi
        self.sc = sc
        self.node = int(node)
        self.router = router
        self.active = active or default_example_id(catalog)
        # The 12 s ceiling is on unless the fade checkbox turns it off.
        self.fade = bool(fade)
        # Where a restarted bridge has to come back, so the page can find it.
        self.http_port = int(http_port)
        # The one write to the board, and the process hand-over.  Both are
        # injected, so the tests never touch hardware or exec anything.
        self._darken = darken or board.darken
        self._replace = replace or _replace_process
        self.bindings: dict = {}
        self.sliders: dict[str, float] = {}
        self._bind()
        # The voices this bridge started and is therefore responsible for
        # stopping: node id -> the example it plays.  A voice checks out when
        # scsynth reports /n_end, so a dead node is never retuned.
        self._voices: dict[int, str] = {}
        self._next_node = self.node
        self._lock = threading.Lock()
        self.sc.on_node_end = self.voice_ended

    def _bind(self) -> None:
        """Point the surface at the active example: scaling + starting values."""
        self.bindings = bindings(self.catalog, self.active, self.mapping)
        self.sliders = default_params(self.catalog, self.active, self.mapping)

    @property
    def def_name(self) -> str:
        """The SynthDef the active example names."""
        return self.catalog["examples"][self.active]["def"]

    @property
    def gesture(self) -> str:
        """How the active example answers activity (``continuous``/``oneshot``)."""
        return self.catalog["examples"][self.active]["gesture"]

    @property
    def onset(self) -> str:
        """What starts the active example's voice (``cc``/``note``/``select``)."""
        return self.catalog["examples"][self.active].get("onset", "cc")

    def start(self) -> None:
        """Boot scsynth, deliver the defs, route audio, watch MIDI.

        No voice is spawned here.  The board is silent until a control moves,
        so the app never plays on its own at startup.
        """
        self.sc.boot()
        self.sc.load_defs()
        # link scsynth's audio into the default sink (best effort)
        self.router()
        self.midi.start()
        # Keep following the default sink: a Bluetooth speaker that pairs after
        # boot moves the default, so re-discover it on a short cadence instead
        # of waiting for a restart.
        self._route_thread = threading.Thread(
            target=self._route_loop, name="audio-route", daemon=True
        )
        self._route_thread.start()

    def _route_loop(self) -> None:
        """Re-discover the default sink and re-link scsynth when it moves."""
        while True:
            time.sleep(_RE_ROUTE_SECONDS)
            self.router()

    def on_cc(self, cc: int, raw: int, channel: int | None = None) -> None:
        channel = self.mapping.get("channel", 15) if channel is None else int(channel)
        b = self.bindings.get((channel, cc))
        if b is None:
            return
        self.sliders[b["param"]] = scale_value(raw, b["min"], b["max"], b["curve"])
        # A oneshot's reserved slider only shapes the next hit, so moving it
        # must not fire one (the corner/note does).  A note-onset entry's voice
        # exists only while its pad is held, so a slider move may shape a held
        # voice but must never start one on its own (the pad's note does).
        if self.gesture != "oneshot":
            if self.onset == "note" and self._live(self.active) is None:
                return
            self._trigger()

    def on_note(self, note, on, channel=None) -> None:
        """Route a pad note to the active example's voice (SPEC §9.6/§9.7).

        The note number is deliberately not mapped to ``freq`` here — the only
        pitched/gated entry (hoover) takes pitch from vSlider0, and pad->freq
        mapping is §9.8's pitched-oneshot work.
        """
        if self.gesture == "oneshot":
            if on:
                self._trigger()
            return
        if self.onset != "note":
            return  # cc- and select-onset examples do not bind notes
        if on:
            self._gate_on()
        else:
            self._gate_off()

    def select_example(self, example_id) -> bool:
        """Make ``example_id`` active, stopping whatever is sounding.

        Returns False for an unknown id.  Control plane only (D8): a selection
        changes nothing about the board or the MIDI stream, and nothing has to
        compile because every def was already delivered at boot (D7).  What it
        does change is the sound: the live voice is faded out and the next
        activity starts a fresh one under the new example.
        """
        if example_id not in self.catalog["examples"]:
            return False
        self._stop_voices()
        self.active = example_id
        self._bind()
        # A self-running drone starts the moment it is selected (its voice was
        # already faded out by _stop_voices above, so this spawns a fresh one).
        if self.onset == "select":
            self._trigger()
        return True

    def set_fade(self, enabled) -> bool:
        """Turn the 12 s ceiling on or off; returns the state now in force.

        Off lets a voice ring past the ceiling (the def still frees itself when
        it goes quiet).  The mode only applies to voices started after it
        changes, so changing it stops what is sounding instead of leaving a
        voice running under the old rule.
        """
        enabled = bool(enabled)
        if enabled != self.fade:
            self._stop_voices()
            self.fade = enabled
        return self.fade

    def voice_ended(self, node) -> None:
        """A node finished: forget it, so the next activity starts a fresh one."""
        with self._lock:
            self._voices.pop(int(node), None)

    def _stop_voices(self) -> None:
        """Fade every live voice out (``gate 0`` runs the def's stop fade)."""
        with self._lock:
            nodes = list(self._voices)
            self._voices.clear()
        for node in nodes:
            self.sc.set_params(node, gate=0)

    def _trigger(self) -> None:
        """Start or shape the active example's voice.

        A continuous example owns one voice: the first activity starts it and
        later activity retunes it, so a slider sweep is a single shaped sound
        rather than a pile of overlapping nodes.  An oneshot example starts a
        fresh voice per hit.  Either way the node id is one the bridge chose, so
        it can always be stopped later.
        """
        args = dict(self.sliders)
        args["fade"] = 1 if self.fade else 0
        with self._lock:
            node = None if self.gesture == "oneshot" else self._live(self.active)
            if node is None:
                node = self._next_node
                self._next_node += 1
                self._voices[node] = self.active
                spawn = True
            else:
                spawn = False
        if spawn:
            self.sc.spawn(self.def_name, node, **args)
        else:
            self.sc.set_params(node, **args)

    def _live(self, example_id) -> int | None:
        """The node currently playing ``example_id``, if any."""
        for node, example in self._voices.items():
            if example == example_id:
                return node
        return None

    def _gate_on(self) -> None:
        """Open the gate: spawn the gated voice, or re-open it if still alive."""
        node = self._live(self.active)
        if node is None:
            self._trigger()  # spawns at the def's default gate=1
        else:
            self.sc.set_param(node, "gate", 1)

    def _gate_off(self) -> None:
        """Close the gate on the live gated voice, if there is one."""
        node = self._live(self.active)
        if node is not None:
            self.sc.set_param(node, "gate", 0)

    def status(self) -> dict:
        state = self.midi.state()
        return {
            "present": state["present"],
            "examples": [
                {
                    "id": example_id,
                    "def": entry["def"],
                    "source": entry["source"],
                    "gesture": entry["gesture"],
                    "onset": entry.get("onset", "cc"),
                }
                for example_id, entry in self.catalog["examples"].items()
            ],
            "activeExample": self.active,
            "def": self.def_name,
            "helper": helper_lines(self.catalog, self.active),
            "sliders": dict(self.sliders),
            "fadeEnabled": self.fade,
            "voices": sorted(self._voices),
            # What the client watches while it waits for a restart to land.
            "pid": os.getpid(),
            "boot": _BOOT_ID,
            "uptime_s": round(time.monotonic() - _STARTED_AT, 1),
            "cc": state["cc"],
            "note": state["note"],
        }

    def reset_board(self) -> bool:
        """Blank the board, and forget the state it reported before the reset.

        Reloading the preset clears every LED, including the rotaries and the
        cross fader that hold their own lighting and survive a sweep of remote
        messages.  The mirrored values go with it: the board does not hold them
        any more, so the UI and the state file must not light up from them.
        """
        darkened = bool(self._darken())
        self.midi.clear()
        return darkened

    def restart(self, delay: float | None = None) -> str | None:
        """Hand this process over to a fresh copy of the bridge.

        Returns an error message if the hand-over would strand the page, else
        None.  The reply has to leave before the process goes: the client gets a
        normal answer, then polls until the new copy reports a fresh uptime.
        """
        if not self.http_port:
            return "cannot restart a bridge that is on an ephemeral port"
        seconds = _RESTART_DELAY if delay is None else delay
        threading.Timer(seconds, self._hand_over).start()
        return None

    def _hand_over(self) -> None:
        """Free scsynth's port, then become the new bridge.

        The stop comes first, because the child holds the port the incoming
        bridge boots its own server on; the exec comes last, because nothing
        after it runs.
        """
        self.sc.stop()
        self._replace()


def serve(config=None) -> None:
    config = config or {}
    node = int(config.get("node", 1000))
    host = config.get("host", "127.0.0.1")
    port = int(config.get("port", 57110))
    http_port = int(config.get("http_port", 8686))
    mapping_path = config.get("mapping", str(DEFAULT_MAPPING))
    catalog_path = config.get("catalog", str(DEFAULT_CATALOG))

    mapping = load_mapping(mapping_path)
    catalog = load_catalog(catalog_path)

    app = None

    def _on_cc(cc: int, raw: int, channel: int) -> None:
        app.on_cc(cc, raw, channel)

    def _on_note(note, on, channel) -> None:
        app.on_note(note, on, channel)

    midi = MidiWatcher(
        channels=channels(mapping),
        on_event=_on_cc,
        on_note=_on_note,
        state_file=config.get("state_file") or _default_state_file(),
    )
    sc = ScServer(host=host, port=port)
    app = ColliderApp(
        mapping=mapping,
        catalog=catalog,
        midi=midi,
        sc=sc,
        node=node,
        fade=config.get("fade", True),
        http_port=http_port,
    )
    app.start()

    try:
        _serve_http(app, host, http_port)
    finally:
        app.sc.stop()
        app.midi.stop()


def reexec_argv() -> list[str]:
    """The command that starts this bridge again, from wherever it was started.

    The module form, not a file path: a path depends on the working directory
    the bridge happened to be started from.
    """
    return [sys.executable, "-m", "super_quneo_collider.server"]


def _replace_process() -> None:
    """Exec a fresh bridge over this process.  Does not return."""
    os.execve(sys.executable, reexec_argv(), dict(os.environ))


def _default_state_file() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "super-quneo-collider" / "state.json"


def _guess_type(path: str) -> str:
    ctype, _ = mimetypes.guess_type(path)
    return ctype or "application/octet-stream"


_POST_ROUTES = (
    "/api/collider/example",
    "/api/collider/fade",
    "/api/collider/reset",
    "/api/collider/restart",
)


def _apply_post(app: ColliderApp, path: str, payload: dict) -> str | None:
    """Apply one control-plane POST.  Returns an error message, or None if fine."""
    if path == "/api/collider/example":
        wanted = payload.get("id")
        return None if app.select_example(wanted) else f"unknown example: {wanted}"
    if path == "/api/collider/reset":
        return None if app.reset_board() else "the board did not accept the reset"
    if path == "/api/collider/restart":
        return app.restart()
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        return "enabled must be true or false"
    app.set_fade(enabled)
    return None


def _make_handler(app: ColliderApp, client_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, code: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _route(self) -> str:
            # A browser may append a cache-busting query string or a fragment;
            # neither is part of the route, so both are stripped before matching.
            return urlsplit(self.path).path

        def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler naming)
            if self._route() == "/api/collider":
                self._json(200, app.status())
            else:
                self._serve_static(self._route())

        def do_POST(self):  # noqa: N802 (BaseHTTPRequestHandler naming)
            path = self._route()
            if path not in _POST_ROUTES:
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw or b"{}")
            except ValueError:
                self._json(400, {"error": "malformed JSON body"})
                return
            error = _apply_post(app, path, payload if isinstance(payload, dict) else {})
            if error is not None:
                self._json(400, {"error": error})
                return
            self._json(200, app.status())

        def _serve_static(self, path: str):
            if not client_dir.is_dir():
                self.send_error(404)
                return
            rel = path.lstrip("/") or "index.html"
            target = (client_dir / rel).resolve()
            if not str(target).startswith(str(client_dir.resolve())) or not target.is_file():
                self.send_error(404)
                return
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", _guess_type(rel))
            # Read from disk on every request: the client is plain modules with
            # no build step, so a reload has to get the file the edit just wrote.
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):  # keep stdout quiet
            pass

    return Handler


def _build_server(
    app: ColliderApp,
    host: str,
    port: int,
    client_dir: Path | None = None,
) -> ThreadingHTTPServer:
    client_dir = Path(client_dir) if client_dir else _DEFAULT_CLIENT_DIR
    return ThreadingHTTPServer((host, port), _make_handler(app, client_dir))


def _serve_http(app: ColliderApp, host: str, port: int) -> None:
    server = _build_server(app, host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
