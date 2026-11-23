"""Route scsynth's SuperCollider outputs to the current default pipewire sink.

scsynth appears in the pipewire graph as a "SuperCollider" client with
``out_1..out_N`` ports, but nothing auto-connects those ports to a playback
sink, so the synth is computed but never heard.  This module keeps those ports
linked to whichever sink is currently default, re-discovering the default on
every call so the audio follows a sink change (e.g. a Bluetooth speaker that
pairs after boot).

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


def _current_sc_links(run=_run) -> list[tuple[str, str]]:
    """Parse ``pw-link -l`` into the ``(out, in)`` pairs SuperCollider owns.

    ``pw-link -l`` lists each port with its ``|->`` outgoing links indented
    beneath it (and the mirror ``|<-`` under the destination).  Reading only
    the ``|->`` line under a ``SuperCollider:out_N`` source yields each link
    exactly once.
    """
    links: list[tuple[str, str]] = []
    src: str | None = None
    for raw in run(["pw-link", "-l"]).splitlines():
        if raw.startswith(" "):
            arrow = raw.strip()
            if arrow.startswith("|->"):
                dest = arrow[3:].strip()
                if src and src.startswith("SuperCollider:out_") and dest:
                    links.append((src, dest))
        elif raw.strip():
            src = raw.strip()
    return links


def route_supercollider(run=_run) -> list[tuple[str, str]]:
    """Keep SuperCollider outputs linked to the current default sink.

    Re-discovers the default sink on every call, disconnects any link whose
    sink no longer matches, and brings up anything the current default is still
    missing.  Idempotent: running it again against an unchanged sink links and
    unlinks nothing.

    Returns the ``(output_port, sink_input_port)`` pairs now in force, or ``[]``
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
    desired = list(zip(outs, ins))
    current = _current_sc_links(run)

    desired_set = set(desired)
    current_set = set(current)
    # Drop links that point at a sink that is no longer default.
    for out, inp in current:
        if (out, inp) not in desired_set:
            run(["pw-link", "-d", out, inp])
    # Bring up anything the current default is still missing.
    for out, inp in desired:
        if (out, inp) not in current_set:
            run(["pw-link", out, inp])
    return desired


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