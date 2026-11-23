import json


def scale(raw: int, lo: float, hi: float) -> float:
    return round(lo + raw / 127 * (hi - lo), 3)


def load_mapping(path) -> dict:
    with open(path) as f:
        return json.load(f)


def param_for_cc(mapping: dict, cc: int):
    for control in mapping["controls"].values():
        if control.get("locCC") == cc and "param" in control:
            return (control["param"], control["min"], control["max"])
    return None


def scale_cc(mapping: dict, cc: int, raw: int):
    p = param_for_cc(mapping, cc)
    if p is None:
        return None
    param, lo, hi = p
    return (param, scale(raw, lo, hi))


def channels(mapping: dict) -> set[int]:
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
