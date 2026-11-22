import json


def scale(raw: int, lo: float, hi: float) -> float:
    return round(lo + raw / 127 * (hi - lo), 3)


def load_mapping(path) -> dict:
    with open(path) as f:
        return json.load(f)


def param_for_cc(mapping: dict, cc: int):
    for control in mapping["controls"].values():
        if control["locCC"] == cc and "param" in control:
            return (control["param"], control["min"], control["max"])
    return None


def scale_cc(mapping: dict, cc: int, raw: int):
    p = param_for_cc(mapping, cc)
    if p is None:
        return None
    param, lo, hi = p
    return (param, scale(raw, lo, hi))
