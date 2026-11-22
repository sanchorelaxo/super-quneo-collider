from pathlib import Path

from super_quneo_collider.map import scale, load_mapping, param_for_cc, scale_cc

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
