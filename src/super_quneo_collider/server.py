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
"""

from __future__ import annotations

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

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

    def start(self) -> None:
        """Boot scsynth, deliver the defs, route audio, watch MIDI.

        Nothing is spawned here.  The board is silent until a control moves, so
        the app never plays on its own at startup.
        """
        self.sc.boot()
        self.sc.load_defs()
        # link scsynth's audio into the default sink (best effort)
        self.router()
        self.midi.start()

    def on_cc(self, cc: int, raw: int, channel: int | None = None) -> None:
        channel = self.mapping.get("channel", 15) if channel is None else int(channel)
        b = self.bindings.get((channel, cc))
        if b is None:
            return
        self.sliders[b["param"]] = scale_value(raw, b["min"], b["max"], b["curve"])
        self._trigger()

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
                }
                for example_id, entry in self.catalog["examples"].items()
            ],
            "activeExample": self.active,
            "def": self.def_name,
            "helper": helper_lines(self.catalog, self.active),
            "sliders": dict(self.sliders),
            "fadeEnabled": self.fade,
            "voices": sorted(self._voices),
            "cc": state["cc"],
            "note": state["note"],
        }


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

    midi = MidiWatcher(
        channels=channels(mapping),
        on_event=_on_cc,
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
    )
    app.start()

    try:
        _serve_http(app, host, http_port)
    finally:
        app.sc.stop()
        app.midi.stop()


def _default_state_file() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "super-quneo-collider" / "state.json"


def _guess_type(path: str) -> str:
    ctype, _ = mimetypes.guess_type(path)
    return ctype or "application/octet-stream"


_POST_ROUTES = ("/api/collider/example", "/api/collider/fade")


def _apply_post(app: ColliderApp, path: str, payload: dict) -> str | None:
    """Apply one control-plane POST.  Returns an error message, or None if fine."""
    if path == "/api/collider/example":
        wanted = payload.get("id")
        return None if app.select_example(wanted) else f"unknown example: {wanted}"
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
