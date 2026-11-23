from pathlib import Path

import contextlib
import threading
from http.client import HTTPConnection

from super_quneo_collider.map import load_mapping
from super_quneo_collider.server import ColliderApp, _build_server

MAPPING = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "super_quneo_collider"
    / "mapping.json"
)


class FakeMidi:
    def __init__(self):
        self._state = {"present": True, "port": "24:0", "cc": {}, "note": {}}
        self.started = False

    def state(self):
        return self._state

    def start(self):
        self.started = True


class FakeSc:
    def __init__(self):
        self.sets = []
        self.booted = False
        self.loaded = False
        self.spawned = None
        self.spawns = []

    def boot(self):
        self.booted = True
        return True

    def load_bubbles(self):
        self.loaded = True
        return True

    def spawn_bubbles(self, node, **args):
        self.spawned = node
        self.spawns.append((node, dict(args)))
        return True

    def set_param(self, node, param, value):
        self.sets.append((node, param, value))


def make_app(router=None):
    return ColliderApp(
        mapping=load_mapping(MAPPING),
        midi=FakeMidi(),
        sc=FakeSc(),
        node=1000,
        router=router if router is not None else (lambda: []),
    )


def test_status_shape():
    st = make_app().status()
    assert isinstance(st["present"], bool)
    assert isinstance(st["sliders"], dict)
    assert isinstance(st["cc"], dict)
    assert isinstance(st["note"], dict)


def test_status_exposes_midi_cc_and_note_state():
    app = make_app()
    app.midi._state["cc"] = {15: {61: 64}}
    app.midi._state["note"] = {15: {36: True}}
    st = app.status()
    assert st["cc"] == {15: {61: 64}}
    assert st["note"] == {15: {36: True}}


def test_on_cc_triggers_bubble_with_value():
    app = make_app()
    app.on_cc(61, 127)
    assert app.status()["sliders"]["wobble"] == 10.0
    # activity spawns a fresh bubble carrying the current value
    assert any(args.get("wobble") == 10.0 for _node, args in app.sc.spawns)


def test_on_cc_unbound_ignored():
    app = make_app()
    app.on_cc(85, 64)
    assert app.status()["sliders"] == {}
    assert app.sc.spawns == []


def test_on_cc_accumulates_params_into_trigger():
    app = make_app()
    app.on_cc(61, 63)
    app.on_cc(69, 64)
    assert app.status()["sliders"]["wobble"] == 4.961
    assert app.status()["sliders"]["innerWobble"] == 8.063
    # the latest triggered bubble carries the accumulated slider state
    _node, args = app.sc.spawns[-1]
    assert args["wobble"] == 4.961
    assert args["innerWobble"] == 8.063


def test_start_boots_and_spawns():
    app = make_app()
    app.start()
    assert app.sc.booted and app.sc.loaded
    # one initial bubble so the synth is audible on load
    assert (1000, {}) in app.sc.spawns


def test_start_routes_audio():
    calls = []
    app = make_app(router=lambda: calls.append("route"))
    app.start()
    assert calls == ["route"]


@contextlib.contextmanager
def running_server():
    app = make_app()
    server = _build_server(app, "127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        thread.join(timeout=2)


def _get(port, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        return resp.status, resp.getheader("Content-Type"), resp.read()
    finally:
        conn.close()


def test_api_collider_content_type():
    with running_server() as port:
        status, ctype, _body = _get(port, "/api/collider")
        assert status == 200
        assert ctype == "application/json"


def test_static_js_content_type():
    with running_server() as port:
        status, ctype, _body = _get(port, "/src/board.js")
        assert status == 200
        assert ctype == "text/javascript"


def test_static_json_content_type():
    with running_server() as port:
        status, ctype, _body = _get(port, "/LAYOUT.json")
        assert status == 200
        assert ctype == "application/json"


def test_static_html_content_type():
    with running_server() as port:
        status, ctype, _body = _get(port, "/index.html")
        assert status == 200
        assert ctype == "text/html"
