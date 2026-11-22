"""Live bridge: MIDI CC -> SynthDef parameter, exposed as HTTP JSON.

``ColliderApp`` composes the mapping (Task 2), the ``MidiWatcher`` (Task 3)
and the ``ScServer`` (Task 4).  ``on_cc`` scales a raw CC through the mapping
and, when the control is bound to a parameter, stores the value and forwards
it to scsynth with ``/n_set``.  ``serve()`` is the process entry point: it
boots the app, wires the watcher's ``on_event`` to ``on_cc``, and serves
``GET /api/collider`` on ``127.0.0.1``.
"""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from super_quneo_collider.map import load_mapping, scale_cc
from super_quneo_collider.midi import MidiWatcher
from super_quneo_collider.sc import ScServer

_DEFAULT_MAPPING = Path(__file__).resolve().parent / "mapping.json"
_DEFAULT_CLIENT_DIR = Path(__file__).resolve().parent.parent.parent / "client"


class ColliderApp:
    def __init__(self, mapping, midi, sc, node=1000):
        self.mapping = mapping
        self.midi = midi
        self.sc = sc
        self.node = int(node)
        self.sliders: dict[str, float] = {}

    def start(self) -> None:
        self.sc.boot()
        self.sc.load_bubbles()
        self.sc.spawn_bubbles(self.node)
        self.midi.start()

    def on_cc(self, cc: int, raw: int) -> None:
        r = scale_cc(self.mapping, cc, raw)
        if r is None:
            return
        param, value = r
        self.sliders[param] = value
        self.sc.set_param(self.node, param, value)

    def status(self) -> dict:
        return {
            "present": self.midi.state()["present"],
            "sliders": dict(self.sliders),
        }


def serve(config=None) -> None:
    config = config or {}
    node = int(config.get("node", 1000))
    host = config.get("host", "127.0.0.1")
    port = int(config.get("port", 57110))
    http_port = int(config.get("http_port", 8686))
    mapping_path = config.get("mapping", str(_DEFAULT_MAPPING))

    mapping = load_mapping(mapping_path)
    channel = mapping.get("channel", 15)

    app = None

    def _on_cc(cc: int, raw: int) -> None:
        app.on_cc(cc, raw)

    midi = MidiWatcher(channel=channel, on_event=_on_cc)
    sc = ScServer(host=host, port=port)
    app = ColliderApp(mapping=mapping, midi=midi, sc=sc, node=node)
    app.start()

    try:
        _serve_http(app, host, http_port)
    finally:
        app.sc.stop()
        app.midi.stop()


def _guess_type(path: str) -> str:
    ctype, _ = mimetypes.guess_type(path)
    return ctype or "application/octet-stream"


def _make_handler(app: ColliderApp, client_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler naming)
            if self.path == "/api/collider":
                body = json.dumps(app.status()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._serve_static()

        def _serve_static(self):
            if not client_dir.is_dir():
                self.send_error(404)
                return
            rel = self.path.lstrip("/") or "index.html"
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
