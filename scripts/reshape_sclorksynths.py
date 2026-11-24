"""Reshape upstream SCLOrkSynths ``.scd`` files into catalog fragments (SPEC §9.8).

Turning ``SynthDef("name", {arg out = 0, ...; ...}).add;`` plus a ``metadata:``
block into a bare fragment that ``sc.py`` ships in the boot batch is a
deterministic, body-preserving transform (plan Decision 1):

1. take the function body verbatim between its opening ``{`` and matching ``}``,
2. remove the upstream ``DetectSilence.ar(...)`` free,
3. demote every remaining ``doneAction: 2`` to ``doneAction: 0``,
4. drop the upstream ``Out.ar(...)`` line,
5. append the canonical guard tail (byte-identical to the shipped fragments), so
   ``DetectSilence`` alone owns the free.

Only the ARG LIST, the output expression, and the provenance header need human
judgment (upstream order varies: ``out`` is not always first, def names are
sometimes symbols, some defs write ``Pan2.ar(snd, pan, amp)``).  Those live in
the per-def ``config`` below; the body is never retyped.

Negative arg defaults are a trap: ``arg cur=-6`` does not parse (SuperCollider
lexes ``=-`` as a binary operator and then reports "unexpected BINOP, expecting
ELLIPSIS"), while ``arg cur= -6`` does.  ``reshape()`` normalises ``=-`` to
``= -`` so upstream ``curve=-6``/``crv=-8`` style defaults survive unchanged,
and ``out=0``/``gate=1``/``fade=1`` keep the exact spacing the guard test counts.

This is a one-off import helper, not a general parser: it assumes the every
def's body has a single top-level ``var ...;`` declaration and that no ``//``
comment contains an unpaired ``{``/``}``.
"""

from __future__ import annotations

import re
from pathlib import Path

UPSTREAM = Path("/tmp/SCLOrkSynths/SynthDefs")
OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "super_quneo_collider"

SYNTH_OPEN = re.compile(r"SynthDef\(\s*[\\\"']?(\w+)")
ARG_BLOCK = re.compile(r"^\s*arg\b.*?;", re.DOTALL | re.MULTILINE)
VAR_DECL = re.compile(r"^(\s*var\b[^;]*?);", re.MULTILINE)
DETECT_SILENCE = re.compile(r"\s*DetectSilence\.ar\([^)]*\);")
OUT_AR = re.compile(r"\s*Out\.ar\(.*?\);", re.DOTALL)
DONE_ACTION_2 = re.compile(r"doneAction:\s*2")


def guard_tail(out_expr: str) -> str:
    """The canonical voice-contract tail, byte-for-byte as the guard test counts it."""
    return (
        "  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);\n"
        "  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);\n"
        "  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);\n"
        "  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);\n"
        f"  Out.ar(out, {out_expr});\n"
    )


def _matching_close(text: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced braces")


def reshape(cfg: dict) -> str:
    text = (UPSTREAM / cfg["bank"] / cfg["file"]).read_text()
    # Strip the leading /* ... */ comment header.
    text = re.sub(r"\A\s*/\*.*?\*/\s*", "", text, flags=re.DOTALL)

    m = SYNTH_OPEN.search(text)
    name = m.group(1)
    body_open = text.index("{", m.end())
    body_close = _matching_close(text, body_open)
    body = text[body_open + 1 : body_close]
    body = body.expandtabs(2)                  # normalize upstream tabs to 2-space

    body = ARG_BLOCK.sub("", body, count=1)        # drop the upstream arg block
    body = DETECT_SILENCE.sub("", body, count=1)   # drop the upstream free
    body = DONE_ACTION_2.sub("doneAction: 0", body)  # demote perc envelopes
    body = OUT_AR.sub("", body, count=1)           # guard reproduces the Out

    # Append the guard's two extra locals onto the single top-level var decl.
    body = VAR_DECL.sub(lambda m: f"{m.group(1)}, stopFade, fadeEnv;", body, count=1)

    header = (
        f"// SCLOrkSynths/{cfg['bank']}/{cfg['file']} — {cfg['credit']}\n"
        f"// category: {cfg['category']}, tags: {cfg['tags']}. {cfg['note']}\n"
    )
    # A negative default spelled ``name=-N`` fails to parse; ``name= -N`` is
    # valid.  Normalise only the ``=-`` adjacency so positive ``out=0``/``gate=1``/
    # ``fade=1`` keep the exact spacing the guard test pins.
    arg = cfg["arg"].replace("=-", "= -")
    return (
        f"{header}"
        f'SynthDef("{name}", {{ {arg}\n'
        f"{body.strip()}\n"
        f"{guard_tail(cfg['out'])}"
        "});\n"
    )


# --- the nine percussion defs (plan Task 1 pilot) ---------------------------

PERCUSSION = [
    {
        "file": "abstractDrum.scd",
        "bank": "percussion",
        "credit": "by Josh Mitchell",
        "category": "percussion",
        "tags": "[pitched, modal]",
        "note": "oneshot; modal 'abstract drum'".lower(),
        "arg": "arg out=0, freq=140, amp=1, pan=0, att=0.001, dec=0.01, rel=1, position=0.5, ampSlope=3, decCoef=0.15, hiFreqSus=0, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "frameDrum.scd",
        "bank": "percussion",
        "credit": "by Josh Mitchell",
        "category": "percussion",
        "tags": "[unpitched, modal]",
        "note": "oneshot; modal frame drum".lower(),
        "arg": "arg out=0, pan=0, freq=170, amp=0.5, att=0.0025, dec=0.0025, rel=5, crv=0, decCoef=0.225, position=0.8, thumpAmp=0.5, thumpDec=0.2, exBlend=0, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "kalimba.scd",
        "bank": "percussion",
        "credit": "by Nathan Ho aka Snappizz (mod. Mitchell & Ruviaro)",
        "category": "percussion",
        "tags": "[pitched, kalimba]",
        "note": "oneshot; kalimba, resonators".lower(),
        "arg": "arg out=0, freq=440, amp=0.1, att=0.001, rel=3, pan=0, crv=-8, mix=0.1, clickRel=0.01, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "marimba1.scd",
        "bank": "percussion",
        "credit": "unknown (mod. Ruviaro & Mitchell)",
        "category": "percussion",
        "tags": "[marimba, pitched, keyboard]",
        "note": "oneshot; BPF marimba".lower(),
        "arg": "arg out=0, freq=440, amp=0.4, pan=0, rq=0.02, shelffreq=220, rs=0.81, shelfamp=2, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "metalPlate.scd",
        "bank": "percussion",
        "credit": "by Josh Mitchell",
        "category": "percussion",
        "tags": "[pitched, modal]",
        "note": "oneshot; clamped metallic plate".lower(),
        "arg": "arg out=0, freq=3000, amp=0.5, rel=2, pan=0, crv=0, ratio=1, decCoef=0.31, xpos=0.5, ypos=0.5, thumpDec=0.75, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "modalMarimba.scd",
        "bank": "percussion",
        "credit": "by Josh Mitchell",
        "category": "percussion",
        "tags": "[pitched, modal]",
        "note": "oneshot; modal idiophone".lower(),
        "arg": "arg out=0, freq=440, amp=0.1, att=0.001, dec=0.1, rel=0.5, pan=0, decCoef=2, position=0.414, ampSlope=3, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "pmCrotales.scd",
        "bank": "percussion",
        "credit": "Author Unknown (mod. Ruviaro & Mitchell)",
        "category": "percussion",
        "tags": "[pitched, bell]",
        "note": "oneshot; PM crotales".lower(),
        "arg": "arg out=0, freq=261, tone=3, att=0, rel=2, curve=-6, amp=0.8, pan=0, modLo=5.25, modHi=5.5, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "steelDrum.scd",
        "bank": "percussion",
        "credit": "Josh Mitchell",
        "category": "percussion",
        "tags": "[pitched, steelDrum, steelPan]",
        "note": "oneshot; steel drum".lower(),
        "arg": "arg out=0, freq=440, amp=0.1, pan=0, att=0.01, dec=1.5, curve=-6, filterHarmonic=6, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan)",
    },
    {
        "file": "xylophone.scd",
        "bank": "percussion",
        "credit": "nicolaariutti & Ze Craum (mod. Ruviaro & Mitchell)",
        "category": "bells",
        "tags": "[pitched]",
        "note": "oneshot; xylophone".lower(),
        "arg": "arg out=0, freq=440, amp=0.01, pan=0, att=0.001, rel=2, exciterRel=0.05, gate=1, fade=1;",
        "out": "Pan2.ar(snd, pan, amp)",
    },
]


def main() -> None:
    for cfg in PERCUSSION:
        fragment = reshape(cfg)
        out = OUT_DIR / cfg["file"]
        out.write_text(fragment)
        print(f"wrote {out.name} ({len(fragment)} bytes)")


if __name__ == "__main__":
    main()