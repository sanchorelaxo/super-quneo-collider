from pathlib import Path

from super_quneo_collider.map import scale, load_mapping, param_for_cc, scale_cc, channels

MAPPING = Path(__file__).resolve().parent.parent / "src" / "super_quneo_collider" / "mapping.json"


def test_scale_wobble():
    assert scale(0, 0.0, 10.0) == 0.0
    assert scale(63, 0.0, 10.0) == 4.961
    assert scale(127, 0.0, 10.0) == 10.0


def test_scale_inner_wobble():
    assert scale(0, 0.0, 16.0) == 0.0
    assert scale(64, 0.0, 16.0) == 8.063
    assert scale(127, 0.0, 16.0) == 16.0


def test_scale_release_time():
    assert scale(0, 2.0, 6.0) == 2.0
    assert scale(64, 2.0, 6.0) == 4.016
    assert scale(127, 2.0, 6.0) == 6.0


def test_param_for_cc_binds_loccc():
    m = load_mapping(MAPPING)
    assert param_for_cc(m, 61) == ("wobble", 0.0, 10.0)
    assert param_for_cc(m, 69) == ("innerWobble", 0.0, 16.0)
    assert param_for_cc(m, 77) == ("releaseTime", 2.0, 6.0)


def test_unbound_loccc_produces_nothing():
    assert param_for_cc(load_mapping(MAPPING), 85) is None


def test_scale_cc_end_to_end():
    assert scale_cc(load_mapping(MAPPING), 61, 127) == ("wobble", 10.0)


def test_mapping_carries_quark_values():
    m = load_mapping(MAPPING)
    assert m["channel"] == 15
    assert m["controls"]["vSliderButton0"] == {
        "noteNum": 20,
        "pressCC": 60,
        "locCC": 61,
        "param": "wobble",
        "min": 0.0,
        "max": 10.0,
    }


def test_mapping_lists_all_30_midi_controls():
    assert len(load_mapping(MAPPING)["controls"]) == 30


def test_mapping_carries_pad_note_and_cc():
    pad0 = load_mapping(MAPPING)["controls"]["padButton0"]
    assert pad0["noteNum"] == 0
    assert pad0["pressCC"] == 0
    assert pad0["xCC"] == 1
    assert pad0["yCC"] == 2


def test_mapping_carries_rotary_channel_and_cc():
    rot0 = load_mapping(MAPPING)["controls"]["rotaryButton0"]
    assert rot0["channel"] == 14
    assert rot0["noteNum"] == 0
    assert rot0["locCC"] == 1
    rot1 = load_mapping(MAPPING)["controls"]["rotaryButton1"]
    assert rot1["channel"] == 14
    assert rot1["noteNum"] == 4
    assert rot1["locCC"] == 9


def test_mapping_carries_mapped_button_notes():
    controls = load_mapping(MAPPING)["controls"]
    assert controls["buttonButton0"]["noteNum"] == 36
    assert controls["buttonButton1"]["noteNum"] == 37
    assert controls["buttonButton2"]["noteNum"] == 38


def test_channels_spans_default_and_rotary():
    assert channels(load_mapping(MAPPING)) == {14, 15}


def test_param_for_cc_survives_pads_without_loccc():
    # pads carry xCC/yCC but no locCC; param_for_cc must not KeyError over them
    assert param_for_cc(load_mapping(MAPPING), 61) == ("wobble", 0.0, 10.0)
