"""The preset-0 MIDI inventory, and the example catalog that re-binds it.

``mapping.json`` is the fixed half: which channel, noteNum, pressCC and locCC
each physical control emits. ``catalog.json`` is the variable half: one entry
per selectable audio example, each listing ``param -> control`` bindings.

A binding resolves its MIDI identity through the inventory by control id, so a
catalog entry never carries a second copy of the wire protocol. The ``cc`` and
``channel`` fields are kept alongside it for readability and asserted equal to
the inventory by the tests.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MAPPING = HERE / "mapping.json"
DEFAULT_CATALOG = HERE / "catalog.json"

CURVES = ("lin", "exp", "int")


def scale(raw: int, lo: float, hi: float) -> float:
    """Linear map of a 7-bit CC value onto ``[lo, hi]``, rounded to 3 decimals."""
    return round(lo + raw / 127 * (hi - lo), 3)


def scale_value(raw: int, lo: float, hi: float, curve: str = "lin"):
    """Map a raw CC onto ``[lo, hi]`` along the parameter's own curve.

    ``exp`` keeps a frequency slider musical (raw 0 lands on ``lo``, not
    silence); ``int`` rounds, for the counts that index partials and channels.
    """
    if curve == "exp":
        return round(lo * (hi / lo) ** (raw / 127), 3)
    if curve == "int":
        return round(lo + raw / 127 * (hi - lo))
    return scale(raw, lo, hi)


def load_mapping(path=DEFAULT_MAPPING) -> dict:
    with open(path) as f:
        return json.load(f)


def load_catalog(path=DEFAULT_CATALOG) -> dict:
    with open(path) as f:
        return json.load(f)


def example_ids(catalog: dict) -> list:
    """The select's options, in catalog order (bubbles first)."""
    return list(catalog["examples"])


def default_example_id(catalog: dict) -> str:
    return catalog["default"]


def control_channel(mapping: dict, control: dict) -> int:
    """A control's channel: its own override, else the preset's default."""
    return control.get("channel", mapping.get("channel", 15))


def bindings(catalog: dict, example_id: str, mapping: dict) -> dict:
    """``{(channel, cc): binding}`` for one example, resolved via ``mapping``.

    Keyed by channel as well as controller number: the two rotaries live on
    channel 14 while the rest of the surface uses 15, so cc 1 on its own is
    ambiguous (formant's ``pan`` rotary versus a pad's xCC).
    """
    result = {}
    for param in catalog["examples"][example_id]["params"]:
        control = mapping["controls"][param["control"]]
        channel = control_channel(mapping, control)
        result[(channel, control["locCC"])] = {
            "param": param["name"],
            "min": param["min"],
            "max": param["max"],
            "curve": param.get("curve", "lin"),
            "default": param["default"],
        }
    return result


def default_params(catalog: dict, example_id: str, mapping: dict) -> dict:
    """The parameter state an example starts from, before any CC arrives."""
    return {b["param"]: b["default"] for b in bindings(catalog, example_id, mapping).values()}


def channels(mapping: dict) -> set:
    """Every MIDI channel the mapped controls can emit on.

    Controls inherit the top-level ``channel`` unless they override it (the
    two rotaries live on channel 14 while everything else uses 15), so the
    watcher must listen to the union rather than a single channel.
    """
    default = mapping.get("channel", 15)
    result = {default}
    for control in mapping["controls"].values():
        result.add(control.get("channel", default))
    return result


# --- helper text (SPEC §9.5) ---------------------------------------------

def _short_label(control_id: str) -> str:
    """``vSliderButton0`` -> ``vSlider0``; the one bound rotary is ``rotary``."""
    label = control_id.replace("Button", "")
    return "rotary" if label == "rotary0" else label


def _range_text(param: dict, control_id: str) -> str:
    """The right-hand column: a range, a unit, and the curve when it is not linear."""
    if control_id.startswith("rotary"):
        return "L..R"  # a bipolar rotary, so the ends are directions not units
    lo, hi = param["min"], param["max"]
    whole = isinstance(lo, int) and isinstance(hi, int)
    text = f"{lo}-{hi}" if whole else f"{lo:.1f}-{hi:.1f}"
    if param["name"].endswith("freq"):
        text += " Hz"
    curve = param.get("curve", "lin")
    if curve != "lin":
        text += f" ({curve})"
    return text


def helper_lines(catalog: dict, example_id: str) -> list:
    """One ``control -> param range`` line per binding, derived from the catalog."""
    entry = catalog["examples"][example_id]
    params = entry["params"]
    labels = [_short_label(p["control"]) for p in params]
    label_width = max(len(label) for label in labels)
    name_width = max(len(p["name"]) for p in params)
    lines = [
        f"{label:<{label_width}} -> {p['name']:<{name_width}}  {_range_text(p, p['control'])}"
        for label, p in zip(labels, params)
    ]
    if entry.get("gesture") == "oneshot":
        lines.insert(0, f"corner -> {entry['def']}")
    return lines
