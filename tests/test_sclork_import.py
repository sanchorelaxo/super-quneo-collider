"""Source-import invariants for SCLOrkSynths fragments (SPEC §9.8).

The reshape (plan Decision 1) turns each upstream ``SynthDef(<name>, {...})``
plus its ``metadata:`` block and ``.add`` into a bare fragment that ``sc.py``
ships in the one boot-time sclang batch.  The guard test in ``test_sc.py``
already pins the voice contract (``out=0``/``gate=1``/``fade=1``/stop fade/
ceiling) across every def.  These tests pin the part it does not: a fragment's
provenance, that it is deliverable (no ``.add``/``.send``/``Server``), and that
only the guard's ``DetectSilence`` may free a voice (no upstream ``doneAction: 2``
survives the demotion to 0).
"""

import json
from pathlib import Path

from super_quneo_collider import sc

PKG = sc._DEF_DIR
CATALOG_PATH = PKG / "catalog.json"

# The seven percussion defs currently wired into the catalog are the import
# pilot (plan Task 1).  frameDrum and metalPlate remain on disk but are parked
# out of the catalog until their compiled size fits one /d_recv message.
PERCUSSION = (
    "abstractDrum",
    "kalimba",
    "marimba1",
    "modalMarimba",
    "pmCrotales",
    "steelDrum",
    "xylophone",
)


def _fragment(name: str) -> str:
    return (PKG / f"{name}.scd").read_text()


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text())


def _sclorksynths_fragments():
    for entry in _catalog()["examples"].values():
        if entry.get("source") == "SCLOrkSynths":
            yield entry["def"], _fragment(entry["def"])


def test_percussion_bank_is_imported():
    assert all(name in sc.DEF_NAMES for name in PERCUSSION)


def test_every_sclorksynths_fragment_is_delivery_clean():
    # Stripped of .add/metadata, the fragment must be a bare SynthDef whose
    # value { ... }.value can hand to .asBytes.  No Server reference may survive.
    for name, src in _sclorksynths_fragments():
        assert ".add" not in src, name
        assert ".send" not in src, name
        assert "Server" not in src, name
        assert "metadata" not in src, name


def test_only_the_guard_frees_an_imported_voice():
    # Exactly one free per def: the guard's DetectSilence (doneAction: 2).  An
    # upstream perc envelope's doneAction: 2 must have been demoted to 0, and
    # the upstream DetectSilence line removed outright (D10).
    for name, src in _sclorksynths_fragments():
        assert src.count("doneAction: 2") == 1, name


def test_every_sclorksynths_fragment_carries_provenance():
    for name, src in _sclorksynths_fragments():
        assert src.startswith("// SCLOrkSynths"), name