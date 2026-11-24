from pathlib import Path

import pytest

from super_quneo_collider.map import (
    bindings,
    channels,
    default_example_id,
    default_params,
    example_ids,
    helper_lines,
    load_catalog,
    load_mapping,
    scale,
    scale_value,
)

SRC = Path(__file__).resolve().parent.parent / "src" / "super_quneo_collider"
MAPPING_PATH = SRC / "mapping.json"
CATALOG_PATH = SRC / "catalog.json"


@pytest.fixture
def mapping():
    return load_mapping(MAPPING_PATH)


@pytest.fixture
def catalog():
    return load_catalog(CATALOG_PATH)


# --- the inventory -------------------------------------------------------

def test_mapping_carries_quark_values(mapping):
    assert mapping["channel"] == 15
    assert mapping["controls"]["vSliderButton0"] == {"noteNum": 20, "pressCC": 60, "locCC": 61}


def test_mapping_lists_all_30_midi_controls(mapping):
    assert len(mapping["controls"]) == 30


def test_mapping_carries_pad_note_and_cc(mapping):
    pad0 = mapping["controls"]["padButton0"]
    assert pad0["noteNum"] == 0
    assert pad0["pressCC"] == 0
    assert pad0["xCC"] == 1
    assert pad0["yCC"] == 2


def test_mapping_carries_rotary_channel_and_cc(mapping):
    rot0 = mapping["controls"]["rotaryButton0"]
    assert rot0["channel"] == 14
    assert rot0["noteNum"] == 0
    assert rot0["locCC"] == 1
    rot1 = mapping["controls"]["rotaryButton1"]
    assert rot1["channel"] == 14
    assert rot1["noteNum"] == 4
    assert rot1["locCC"] == 9


def test_mapping_carries_mapped_button_notes(mapping):
    controls = mapping["controls"]
    assert controls["buttonButton0"]["noteNum"] == 36
    assert controls["buttonButton1"]["noteNum"] == 37
    assert controls["buttonButton2"]["noteNum"] == 38


def test_channels_spans_default_and_rotary(mapping):
    assert channels(mapping) == {14, 15}


# --- scaling -------------------------------------------------------------

def test_scale_is_linear():
    assert scale(0, 0.0, 10.0) == 0.0
    assert scale(63, 0.0, 10.0) == 4.961
    assert scale(127, 0.0, 10.0) == 10.0


def test_scale_value_exp_bottoms_out_at_lo_not_zero():
    assert scale_value(0, 40, 10240, "exp") == 40.0
    assert scale_value(127, 40, 10240, "exp") == 10240.0
    assert scale_value(0, 40, 2000, "exp") == 40.0
    assert scale_value(127, 40, 2000, "exp") == 2000.0


def test_scale_value_int_rounds_to_whole_counts():
    assert scale_value(0, 1, 32, "int") == 1
    assert scale_value(127, 1, 32, "int") == 32
    assert scale_value(64, 1, 32, "int") == 17
    assert isinstance(scale_value(64, 1, 32, "int"), int)
    assert scale_value(127, 1, 8, "int") == 8


# --- the catalog ---------------------------------------------------------

def test_catalog_lists_all_examples(catalog):
    assert example_ids(catalog) == [
        "bubbles",
        "formant",
        "sine",
        "simpleFM",
        "chainsaw",
        "drummer",
        "gabberkick",
        "hoover",
        "abstractDrum",
        "kalimba",
        "marimba1",
        "modalMarimba",
        "pmCrotales",
        "steelDrum",
        "xylophone",
    ]


def test_catalog_onset_and_gesture_distinguish_drones_from_one_shots(catalog):
    examples = catalog["examples"]
    # the three drones are re-tunable, so they bind on selection (onset select)...
    for drone in ("simpleFM", "chainsaw", "drummer"):
        assert examples[drone]["onset"] == "select"
    # ...hoover re-triggers on note... and gabberkick is a one-shot...
    assert examples["hoover"]["onset"] == "note"
    assert examples["gabberkick"]["gesture"] == "oneshot"
    assert "onset" not in examples["gabberkick"]
    # ...while the three stage-one examples declare no onset (default: cc),
    # and gabberkick (oneshot) also defaults to cc onset.
    for legacy in ("bubbles", "formant", "sine"):
        assert "onset" not in examples[legacy]


def test_bubbles_is_the_default(catalog):
    assert default_example_id(catalog) == "bubbles"


def test_every_example_declares_a_gesture(catalog):
    for example_id in example_ids(catalog):
        assert catalog["examples"][example_id]["gesture"] in ("continuous", "oneshot")


def test_every_example_binds_at_least_one_parameter(catalog):
    for example_id in example_ids(catalog):
        assert catalog["examples"][example_id]["params"]


def test_catalog_cc_and_channel_agree_with_the_inventory(catalog, mapping):
    for example_id in example_ids(catalog):
        for param in catalog["examples"][example_id]["params"]:
            control = mapping["controls"][param["control"]]
            assert param["cc"] == control["locCC"]
            assert param.get("channel", mapping["channel"]) == control.get(
                "channel", mapping["channel"]
            )


def test_bindings_resolve_through_the_inventory(catalog, mapping):
    bound = bindings(catalog, "formant", mapping)
    assert bound[(15, 61)]["param"] == "fundfreq"
    assert bound[(15, 61)]["min"] == 40
    assert bound[(15, 61)]["max"] == 10240
    assert bound[(15, 69)]["param"] == "formantfreq"
    assert bound[(15, 77)]["param"] == "bwfreq"
    assert bound[(15, 85)]["param"] == "timeScale"


def test_bindings_key_on_channel_for_the_rotary(catalog, mapping):
    bound = bindings(catalog, "formant", mapping)
    assert bound[(14, 1)]["param"] == "pan"
    # ch15 cc1 is padButton0's xCC, which formant does not bind
    assert (15, 1) not in bound


def test_bindings_are_scoped_to_the_active_example(catalog, mapping):
    assert bindings(catalog, "sine", mapping) == {
        (15, 61): {"param": "freq", "min": 40, "max": 2000, "curve": "exp", "default": 440}
    }
    assert bindings(catalog, "bubbles", mapping)[(15, 61)]["param"] == "wobble"


def test_unbound_loccc_produces_nothing(catalog, mapping):
    assert (15, 85) not in bindings(catalog, "bubbles", mapping)


@pytest.mark.parametrize(
    "example_id,cc,raw,param,expected",
    [
        ("formant", 61, 127, "fundfreq", 10240.0),
        ("formant", 61, 0, "fundfreq", 40.0),
        ("sine", 61, 127, "freq", 2000.0),
        ("sine", 61, 0, "freq", 40.0),
    ],
)
def test_example_variables_scale_to_the_bound_control(
    catalog, mapping, example_id, cc, raw, param, expected
):
    binding = bindings(catalog, example_id, mapping)[(15, cc)]
    assert binding["param"] == param
    assert scale_value(raw, binding["min"], binding["max"], binding["curve"]) == expected


def test_default_params_are_the_catalog_defaults(catalog, mapping):
    assert default_params(catalog, "bubbles", mapping) == {
        "wobble": 0.4,
        "innerWobble": 8,
        "releaseTime": 4,
    }
    assert default_params(catalog, "formant", mapping) == {
        "fundfreq": 440,
        "formantfreq": 440,
        "bwfreq": 100,
        "timeScale": 1,
        "pan": 0,
    }


# --- helper text (SPEC §9.5) ---------------------------------------------

def test_helper_text_for_formant_matches_the_spec_block(catalog):
    assert helper_lines(catalog, "formant") == [
        "vSlider0 -> fundfreq     40-10240 Hz (exp)",
        "vSlider1 -> formantfreq  40-10240 Hz (exp)",
        "vSlider2 -> bwfreq       40-10240 Hz (exp)",
        "vSlider3 -> timeScale    0.1-4.0",
        "rotary   -> pan          L..R",
    ]


def test_helper_text_names_the_active_examples_variables(catalog):
    assert helper_lines(catalog, "sine") == ["vSlider0 -> freq  40-2000 Hz (exp)"]


def test_helper_lines_name_the_corner_for_a_oneshot(catalog):
    assert helper_lines(catalog, "gabberkick") == [
        "corner -> gabberkick",
        "vSlider3 -> bend  0.4-1.0",
    ]
