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
        self._state = {"present": True, "port": "24:0", "cc": {}}
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

    def boot(self):
        self.booted = True
        return True

    def load_bubbles(self):
        self.loaded = True
        return True

    def spawn_bubbles(self, node):
        self.spawned = node
        return True

    def set_param(self, node, param, value):
        self.sets.append((node, param, value))


def make_app():
    return ColliderApp(
        mapping=load_mapping(MAPPING), midi=FakeMidi(), sc=FakeSc(), node=1000
    )


def test_status_shape():
    st = make_app().status()
    assert isinstance(st["present"], bool)
    assert isinstance(st["sliders"], dict)


def test_on_cc_scales_and_sets_param():
    app = make_app()
    app.on_cc(61, 127)
    assert app.status()["sliders"]["wobble"] == 10.0
    assert (1000, "wobble", 10.0) in app.sc.sets


def test_on_cc_unbound_ignored():
    app = make_app()
    app.on_cc(85, 64)
    assert app.status()["sliders"] == {}
    assert app.sc.sets == []


def test_three_sliders_independent():
    app = make_app()
    app.on_cc(61, 63)
    app.on_cc(69, 64)
    assert app.status()["sliders"]["wobble"] == 4.961
    assert app.status()["sliders"]["innerWobble"] == 8.063
    assert (1000, "wobble", 4.961) in app.sc.sets
    assert (1000, "innerWobble", 8.063) in app.sc.sets


def test_start_boots_and_spawns():
    app = make_app()
    app.start()
    assert app.sc.booted and app.sc.loaded and app.sc.spawned == 1000


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
