import contextlib
import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from super_quneo_collider.map import helper_lines, load_catalog, load_mapping
from super_quneo_collider.server import ColliderApp, _build_server

SRC = Path(__file__).resolve().parent.parent / "src" / "super_quneo_collider"
MAPPING = SRC / "mapping.json"
CATALOG = SRC / "catalog.json"

# SPEC §9.5, byte for byte: the helper text the UI shows for formant.
FORMANT_HELPER = [
    "vSlider0 -> fundfreq     40-10240 Hz (exp)",
    "vSlider1 -> formantfreq  40-10240 Hz (exp)",
    "vSlider2 -> bwfreq       40-10240 Hz (exp)",
    "vSlider3 -> timeScale    0.1-4.0",
    "rotary   -> pan          L..R",
]


class FakeMidi:
    def __init__(self):
        self._state = {"present": True, "port": "24:0", "cc": {}, "note": {}}
        self.calls = []

    def state(self):
        return self._state

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")


class FakeSc:
    """Records every call, so "selection writes nothing" is checkable."""

    def __init__(self):
        self.calls = []
        self.spawns = []
        self.params = []
        self.on_node_end = None

    def boot(self):
        self.calls.append(("boot",))
        return True

    def load_defs(self):
        self.calls.append(("load_defs",))
        return True

    def spawn(self, def_name, node, **args):
        self.calls.append(("spawn", def_name, node, dict(args)))
        self.spawns.append((def_name, node, dict(args)))
        return True

    def set_param(self, node, param, value):
        self.calls.append(("set_param", node, param, value))

    def set_params(self, node, **args):
        self.calls.append(("set_params", node, dict(args)))
        self.params.append((node, dict(args)))

    def emit_node_end(self, node):
        """Stand in for scsynth's /n_end arriving on the receive thread."""
        if self.on_node_end is not None:
            self.on_node_end(node)

    def stop(self):
        self.calls.append(("stop",))


def make_app(router=None, active=None, fade=True):
    return ColliderApp(
        mapping=load_mapping(MAPPING),
        catalog=load_catalog(CATALOG),
        midi=FakeMidi(),
        sc=FakeSc(),
        node=1000,
        router=router if router is not None else (lambda: []),
        active=active,
        fade=fade,
    )


# --- status ---------------------------------------------------------------


def test_status_shape():
    st = make_app().status()
    assert isinstance(st["present"], bool)
    assert isinstance(st["examples"], list)
    assert isinstance(st["activeExample"], str)
    assert isinstance(st["helper"], list)
    assert isinstance(st["sliders"], dict)
    assert isinstance(st["cc"], dict)
    assert isinstance(st["note"], dict)


def test_status_lists_all_nine_examples():
    st = make_app().status()
    assert [e["id"] for e in st["examples"]] == [
        "bubbles",
        "formant",
        "sine",
        "klang",
        "simpleFM",
        "chainsaw",
        "drummer",
        "gabberkick",
        "hoover",
    ]


def test_every_example_declares_a_def_source_and_gesture():
    for entry in make_app().status()["examples"]:
        assert entry["def"]
        assert entry["source"]
        assert entry["gesture"] in ("continuous", "oneshot")


def test_bubbles_is_the_default_active_example():
    assert make_app().status()["activeExample"] == "bubbles"


def test_status_exposes_midi_cc_and_note_state():
    app = make_app()
    app.midi._state["cc"] = {15: {61: 64}}
    app.midi._state["note"] = {15: {36: True}}
    st = app.status()
    assert st["cc"] == {15: {61: 64}}
    assert st["note"] == {15: {36: True}}


def test_status_helper_matches_the_spec_block_for_formant():
    app = make_app(active="formant")
    assert app.status()["helper"] == FORMANT_HELPER


def test_status_helper_is_derived_from_the_catalog():
    app = make_app(active="formant")
    assert app.status()["helper"] == helper_lines(app.catalog, "formant")
    # Change the catalog and the text follows: nothing here is hand-written.
    app.catalog["examples"]["formant"]["params"][0]["min"] = 55
    assert "55-10240 Hz" in "\n".join(app.status()["helper"])


def test_status_starts_on_the_examples_defaults():
    # Before any CC arrives the parameter state is the catalog's defaults.
    app = make_app(active="klang")
    assert app.status()["sliders"] == {"nPartials": 12, "nChans": 5}


# --- scaling through the active example -----------------------------------


def test_on_cc_triggers_bubble_with_value():
    app = make_app()
    app.on_cc(61, 127)
    assert app.status()["sliders"]["wobble"] == 10.0
    # activity spawns a voice carrying the current value, under a real node id
    # (a -1 here is what made every slider move leave an untracked drone)
    def_name, node, args = app.sc.spawns[0]
    assert (def_name, node) == ("bubbles", 1000)
    assert args["wobble"] == 10.0
    assert args["fade"] == 1
    assert app.status()["voices"] == [1000]


def test_on_cc_accumulates_params_into_the_one_live_voice():
    # A slider sweep shapes ONE voice: the first CC starts it, later CCs retune
    # it.  Stacking a node per CC is what left drones ringing.
    app = make_app()
    app.on_cc(61, 63)
    app.on_cc(69, 64)
    assert app.status()["sliders"]["wobble"] == 4.961
    assert app.status()["sliders"]["innerWobble"] == 8.063
    assert len(app.sc.spawns) == 1
    node, args = app.sc.params[-1]
    assert node == app.sc.spawns[0][1]
    assert args == {
        "wobble": 4.961,
        "innerWobble": 8.063,
        "releaseTime": 4,
        "fade": 1,
    }


def test_on_cc_unbound_ignored():
    app = make_app()
    app.on_cc(85, 64)  # unbound in bubbles (only three of four vSliders are)
    assert app.sc.spawns == []


def test_on_cc_uses_the_active_examples_curve():
    app = make_app(active="formant")
    app.on_cc(61, 63)  # exponential, not linear
    assert app.status()["sliders"]["fundfreq"] == 626.179


def test_on_cc_reads_the_channel_14_rotary():
    # formant's pan lives on rotary 0, which emits on channel 14.
    app = make_app(active="formant")
    app.on_cc(1, 127, 14)
    assert app.status()["sliders"]["pan"] == 1.0
    app.on_cc(1, 0, 14)
    assert app.status()["sliders"]["pan"] == -1.0


@pytest.mark.parametrize(
    "example,cc,raw,param,expected",
    [
        ("formant", 61, 127, "fundfreq", 10240.0),
        ("formant", 61, 0, "fundfreq", 40.0),
        ("sine", 61, 127, "freq", 2000.0),
        ("klang", 61, 127, "nPartials", 32),
        ("klang", 69, 127, "nChans", 8),
    ],
)
def test_an_examples_variables_scale_to_the_bound_control(
    example, cc, raw, param, expected
):
    # SPEC §6, "an example's variables scale to the bound control".
    app = make_app(active=example)
    app.on_cc(cc, raw)
    assert app.status()["sliders"][param] == expected


@pytest.mark.parametrize(
    "example,param",
    [("formant", "fundfreq"), ("sine", "freq"), ("klang", "nPartials")],
)
def test_selecting_an_example_rebinds_loccc_61(example, param):
    # SPEC §6, "selecting an example re-binds the control surface".
    app = make_app()
    assert app.status()["sliders"] == {
        "wobble": 0.4,
        "innerWobble": 8,
        "releaseTime": 4,
    }
    assert app.select_example(example) is True
    assert app.status()["activeExample"] == example
    app.on_cc(61, 127)
    assert param in app.status()["sliders"]
    assert "wobble" not in app.status()["sliders"]


def test_klang_spawns_int_params_as_ints():
    app = make_app(active="klang")
    app.on_cc(61, 127)
    app.on_cc(69, 127)
    # The first control starts the voice with the state as it stands...
    _def, _node, args = app.sc.spawns[-1]
    assert args == {"nPartials": 32, "nChans": 5, "fade": 1}
    # ...the second retunes that same node in one /n_set.
    node, retune = app.sc.params[-1]
    assert node == 1000
    assert retune == {"nPartials": 32, "nChans": 8, "fade": 1}
    # SC compares nPartials/nChans against integer indices: they must stay ints.
    assert all(isinstance(v, int) for v in list(args.values()) + list(retune.values()))


def test_unknown_example_is_rejected():
    app = make_app()
    assert app.select_example("nope") is False
    assert app.status()["activeExample"] == "bubbles"


# --- selection touches nothing but the control plane ----------------------


def test_selecting_an_example_never_writes_to_the_board():
    # SPEC §6: no preset is flashed and no MIDI is sent to the QuNeo.
    app = make_app()
    app.start()
    sc_before = list(app.sc.calls)
    midi_before = list(app.midi.calls)
    assert app.select_example("sine") is True
    assert app.sc.calls == sc_before
    assert app.midi.calls == midi_before
    # nothing was sounding, so there was nothing to stop
    assert app.sc.spawns == []


def test_selecting_an_example_spawns_the_new_def_on_the_next_activity():
    app = make_app()
    app.start()
    app.select_example("formant")
    app.on_cc(61, 64)
    assert app.sc.spawns[-1][0] == "formant"


# --- stopping the sound ---------------------------------------------------


def test_selecting_an_example_fades_out_the_sounding_voice():
    # "the sound has to stop when a new selection is made" -- stopped with the
    # def's 3 s stop fade (gate 0), not a hard cut.
    app = make_app()
    app.start()
    app.on_cc(61, 64)
    assert app.select_example("formant") is True
    assert app.sc.params == [(1000, {"gate": 0})]
    assert app.status()["voices"] == []
    # the next activity is the new example, under a fresh node id
    app.on_cc(61, 64)
    assert app.sc.spawns[-1][0] == "formant"
    assert app.sc.spawns[-1][1] == 1001


def test_switching_twice_does_not_retune_a_voice_that_is_already_fading():
    app = make_app()
    app.start()
    app.on_cc(61, 64)
    app.select_example("sine")
    app.select_example("klang")
    assert app.sc.params == [(1000, {"gate": 0})]


def test_a_finished_voice_is_forgotten_so_the_next_activity_respawns():
    app = make_app()
    app.start()
    app.on_cc(61, 64)
    app.sc.emit_node_end(1000)  # scsynth reports /n_end
    assert app.status()["voices"] == []
    app.on_cc(61, 64)
    assert len(app.sc.spawns) == 2
    assert app.sc.spawns[-1][1] == 1001


# --- the fade checkbox ----------------------------------------------------


def test_the_ceiling_is_on_unless_it_is_turned_off():
    app = make_app()
    assert app.status()["fadeEnabled"] is True
    assert make_app(fade=False).status()["fadeEnabled"] is False


def test_turning_the_ceiling_off_lets_the_next_voice_ring():
    app = make_app()
    app.start()
    assert app.set_fade(False) is False
    app.on_cc(61, 64)
    assert app.sc.spawns[-1][2]["fade"] == 0
    assert app.status()["fadeEnabled"] is False


def test_changing_the_ceiling_stops_what_is_sounding():
    # The new mode only applies to the next voice, so the old one is faded out.
    app = make_app()
    app.start()
    app.on_cc(61, 64)
    assert app.set_fade(False) is False
    assert app.sc.params == [(1000, {"gate": 0})]
    assert app.set_fade(False) is False  # no change -> no second stop
    assert app.sc.params == [(1000, {"gate": 0})]


def test_turning_the_ceiling_back_on_is_reported():
    app = make_app(fade=False)
    assert app.set_fade(True) is True
    assert app.status()["fadeEnabled"] is True


# --- start ----------------------------------------------------------------


def test_start_boots_loads_and_stays_silent_until_a_control_moves():
    # "bubbles is still being played on startup. remove that." -- boot delivers
    # the defs and starts MIDI; the board is silent until a control moves.
    app = make_app()
    app.start()
    assert ("boot",) in app.sc.calls
    assert ("load_defs",) in app.sc.calls
    assert app.midi.calls == ["start"]
    assert app.sc.spawns == []
    assert app.status()["voices"] == []


def test_start_wires_the_node_end_hook_into_the_voice_registry():
    app = make_app()
    assert app.sc.on_node_end == app.voice_ended


def test_start_routes_audio():
    calls = []
    app = make_app(router=lambda: calls.append("route"))
    app.start()
    assert calls == ["route"]


# --- HTTP -----------------------------------------------------------------


@contextlib.contextmanager
def running_server():
    app = make_app()
    server = _build_server(app, "127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, app
    finally:
        server.shutdown()
        thread.join(timeout=2)


def _request(port, method, path, payload=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        return resp.status, resp.getheader("Content-Type"), resp.read()
    finally:
        conn.close()


def test_api_collider_content_type():
    with running_server() as (port, _app):
        status, ctype, _body = _request(port, "GET", "/api/collider")
        assert status == 200
        assert ctype == "application/json"


def test_api_collider_lists_the_examples():
    with running_server() as (port, _app):
        _status, _ctype, body = _request(port, "GET", "/api/collider")
        payload = json.loads(body)
        assert [e["id"] for e in payload["examples"]] == [
            "bubbles",
            "formant",
            "sine",
            "klang",
            "simpleFM",
            "chainsaw",
            "drummer",
            "gabberkick",
            "hoover",
        ]
        assert payload["activeExample"] == "bubbles"


def test_api_select_switches_the_active_example():
    with running_server() as (port, app):
        status, ctype, body = _request(
            port, "POST", "/api/collider/example", {"id": "klang"}
        )
        assert status == 200
        assert ctype == "application/json"
        assert json.loads(body)["activeExample"] == "klang"
        assert app.active == "klang"


def test_api_select_returns_the_helper_text_for_the_new_example():
    with running_server() as (port, _app):
        _status, _ctype, body = _request(
            port, "POST", "/api/collider/example", {"id": "formant"}
        )
        assert json.loads(body)["helper"] == FORMANT_HELPER


def test_api_select_rejects_an_unknown_example():
    with running_server() as (port, app):
        status, _ctype, body = _request(
            port, "POST", "/api/collider/example", {"id": "nope"}
        )
        assert status == 400
        assert "unknown example" in json.loads(body)["error"]
        assert app.active == "bubbles"


def test_api_select_rejects_a_malformed_body():
    with running_server() as (port, _app):
        conn = HTTPConnection("127.0.0.1", port, timeout=3)
        try:
            conn.request("POST", "/api/collider/example", body=b"{not json")
            assert conn.getresponse().status == 400
        finally:
            conn.close()


def test_static_js_content_type():
    with running_server() as (port, _app):
        status, ctype, _body = _request(port, "GET", "/src/board.js")
        assert status == 200
        assert ctype == "text/javascript"


def test_static_json_content_type():
    with running_server() as (port, _app):
        status, ctype, _body = _request(port, "GET", "/LAYOUT.json")
        assert status == 200
        assert ctype == "application/json"


def test_static_html_content_type():
    with running_server() as (port, _app):
        status, ctype, _body = _request(port, "GET", "/index.html")
        assert status == 200
        assert ctype == "text/html"


# --- HTTP: a query string is not part of the route --------------------------


def test_the_root_serves_the_page():
    with running_server() as (port, _app):
        status, ctype, body = _request(port, "GET", "/")
        assert status == 200
        assert ctype == "text/html"
        assert b'id="fade"' in body


def test_static_serving_ignores_a_query_string():
    with running_server() as (port, _app):
        status, ctype, body = _request(port, "GET", "/index.html?v=2")
        assert status == 200
        assert ctype == "text/html"
        assert b'id="fade"' in body


def test_the_api_ignores_a_query_string():
    with running_server() as (port, _app):
        status, ctype, _body = _request(port, "GET", "/api/collider?t=1")
        assert status == 200
        assert ctype == "application/json"


def test_posting_ignores_a_query_string():
    with running_server() as (port, app):
        status, _ctype, body = _request(
            port, "POST", "/api/collider/fade?t=1", {"enabled": False}
        )
        assert status == 200
        assert json.loads(body)["fadeEnabled"] is False
        assert app.fade is False


def test_a_missing_static_file_is_still_404_with_a_query_string():
    with running_server() as (port, _app):
        status, _ctype, _body = _request(port, "GET", "/nope.js?x=1")
        assert status == 404


def test_a_traversal_attempt_is_still_404_with_a_query_string():
    with running_server() as (port, _app):
        status, _ctype, _body = _request(port, "GET", "/../pyproject.toml?x=1")
        assert status == 404


# --- HTTP: the fade checkbox ----------------------------------------------


def test_api_select_stops_the_sounding_voice():
    with running_server() as (port, app):
        app.on_cc(61, 64)  # a voice the bridge knows about
        status, _ctype, _body = _request(
            port, "POST", "/api/collider/example", {"id": "formant"}
        )
        assert status == 200
        assert app.sc.params == [(1000, {"gate": 0})]


def test_api_fade_toggles_the_ceiling():
    with running_server() as (port, _app):
        _status, ctype, body = _request(
            port, "POST", "/api/collider/fade", {"enabled": False}
        )
        assert ctype == "application/json"
        assert json.loads(body)["fadeEnabled"] is False
        _status, _ctype, body = _request(
            port, "POST", "/api/collider/fade", {"enabled": True}
        )
        assert json.loads(body)["fadeEnabled"] is True


def test_api_fade_rejects_a_non_boolean():
    with running_server() as (port, app):
        status, _ctype, body = _request(
            port, "POST", "/api/collider/fade", {"enabled": "yes"}
        )
        assert status == 400
        assert "enabled" in json.loads(body)["error"]
        assert app.status()["fadeEnabled"] is True


def test_api_rejects_an_unknown_post_path():
    with running_server() as (port, _app):
        status, _ctype, _body = _request(port, "POST", "/api/collider/nope", {})
        assert status == 404


# --- corner triggers: oneshot / gated-note / drone (SPEC §9.6/§9.7) --------


def test_oneshot_note_on_spawns_a_fresh_voice_per_press():
    app = make_app(active="gabberkick")
    app.start()
    app.on_note(3, True)
    assert len(app.sc.spawns) == 1
    def_name, first_node, _args = app.sc.spawns[0]
    assert def_name == "gabberkick"
    assert first_node >= 1000
    # a second press is a second voice, under a distinct node id
    app.on_note(3, True)
    assert len(app.sc.spawns) == 2
    assert app.sc.spawns[1][1] != first_node
    # note-off does not spawn and does not retune a oneshot
    app.on_note(3, False)
    assert len(app.sc.spawns) == 2
    assert not any(call[0] == "set_param" for call in app.sc.calls)


def test_oneshot_slider_move_does_not_spawn():
    app = make_app(active="gabberkick")
    app.start()
    app.on_cc(85, 90)  # the reserved vSlider3 -> bend
    assert app.status()["sliders"]["bend"] == 0.825
    assert app.sc.spawns == []
    assert app.sc.params == []


def test_gated_note_spawns_on_press_and_gates_off_on_release():
    app = make_app(active="hoover")
    app.start()
    app.on_note(5, True)
    assert len(app.sc.spawns) == 1
    def_name, node, args = app.sc.spawns[0]
    assert def_name == "hoover"
    # gate=1 is the def default, so the spawn carries no gate key
    assert "gate" not in args
    # release gates the live voice off
    app.on_note(5, False)
    assert ("set_param", node, "gate", 0) in app.sc.calls
    # a later press re-gates the still-alive voice instead of stacking a second
    app.on_note(3, True)
    assert len(app.sc.spawns) == 1
    assert ("set_param", node, "gate", 1) in app.sc.calls


def test_gated_note_slider_move_shapes_but_does_not_start_a_voice():
    # A note-onset entry's voice exists only while a pad is held (SPEC §9.7:
    # hoover "sounds only while a pad is held"). Moving its bound slider must
    # shape the next note but never start a drone on its own.
    app = make_app(active="hoover")
    app.start()
    app.on_cc(61, 90)  # vSlider0 -> freq, with no pad down
    assert app.sc.spawns == []
    assert app.sc.params == []
    assert app.status()["sliders"]["freq"] != 440  # shaped, ready for the next note


def test_gated_note_slider_sweep_retunes_the_held_voice():
    # While a pad is held the note-onset voice lives; sweeping vSlider0 retunes
    # that voice (SPEC §9.7: "vSlider0 sweeps pitch") rather than stacking a new
    # one.  This is the sibling of the no-spawn test above: the guard must stop
    # a fresh spawn, not the retune of an already-sounding voice.
    app = make_app(active="hoover")
    app.start()
    app.on_note(5, True)
    node = app.sc.spawns[0][1]
    app.on_cc(61, 90)
    assert len(app.sc.spawns) == 1
    assert app.sc.params[-1][0] == node
    assert app.sc.params[-1][1]["freq"] != 440


def test_drone_starts_on_select_and_fades_on_deselect():
    app = make_app(active="bubbles")
    app.start()
    assert app.select_example("simpleFM") is True
    assert len(app.sc.spawns) == 1
    assert app.sc.spawns[0][0] == "simpleFM"
    drone = app.sc.spawns[0][1]
    # deselecting to a cc-onset example fades the drone and stays silent
    assert app.select_example("bubbles") is True
    assert app.sc.params == [(drone, {"gate": 0})]
    assert len(app.sc.spawns) == 1


def test_status_reports_onset_per_example():
    st = make_app().status()
    by_id = {e["id"]: e for e in st["examples"]}
    assert by_id["simpleFM"]["onset"] == "select"
    assert by_id["chainsaw"]["onset"] == "select"
    assert by_id["drummer"]["onset"] == "select"
    assert by_id["hoover"]["onset"] == "note"
    assert by_id["bubbles"]["onset"] == "cc"
    assert by_id["gabberkick"]["onset"] == "cc"
