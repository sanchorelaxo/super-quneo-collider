"""Route scsynth's SuperCollider outputs to the default pipewire sink.

scsynth appears in the pipewire graph as a "SuperCollider" client with
``out_1..out_N`` ports, but nothing auto-connects those ports to a playback
sink, so the synth is computed but never heard.  This module links the two
together with ``pw-link``.

Everything here is best-effort: audio routing is environment-specific and must
never take the bridge down, so any missing ``pw-link``/``pactl`` binary or a
sink/port mismatch is tolerated (the functions just return what they could
not do).
"""

from __future__ import annotations

import subprocess
import time


def _run(args: list[str]) -> str:
    try:
        out = subprocess.run(
            args, capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip()
    except Exception:
        return ""


def route_supercollider(run=_run) -> list[tuple[str, str]]:
    """Connect SuperCollider outputs to the default sink. One shot.

    Returns the list of ``(output_port, sink_input_port)`` pairs actually
    linked (the pairs for which a ``pw-link`` connect was issued), or ``[]``
    when there is no default sink or no SuperCollider ports yet.
    """
    sink = run(["pactl", "get-default-sink"])
    if not sink:
        return []

    outs = sorted(
        line
        for line in run(["pw-link", "-o"]).splitlines()
        if line.startswith("SuperCollider:out_")
    )
    ins = sorted(
        line
        for line in run(["pw-link", "-i"]).splitlines()
        if line.startswith(f"{sink}:") and ":monitor_" not in line
    )

    linked: list[tuple[str, str]] = []
    for out_port, in_port in zip(outs, ins):
        run(["pw-link", out_port, in_port])
        linked.append((out_port, in_port))
    return linked


def route_audio(run=_run, attempts: int = 10, delay: float = 0.5) -> list[tuple[str, str]]:
    """Retry :func:`route_supercollider` until it links something or gives up.

    scsynth registers its pipewire client asynchronously after boot, so a
    brief retry covers the gap.
    """
    for _ in range(attempts):
        linked = route_supercollider(run)
        if linked:
            return linked
        time.sleep(delay)
    return []
