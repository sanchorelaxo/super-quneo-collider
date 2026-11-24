"""scsynth lifecycle: one-shot sclang SynthDef delivery + OSC control plane.

The bridge boots a raw ``scsynth`` (no resident sclang ``Server``), so every
SynthDef in the catalog is delivered by a single one-shot ``sclang`` run at
startup (D3/D7), and everything after that is pyliblo3: ``/s_new``, ``/n_set``,
``/s_get`` and ``/status``.  Because all four examples arrive at boot, switching
examples is a pure control-plane event: no compile, no board write.

Raw scsynth has no "default group 1" (that group is created by sclang's
``Server`` when it connects).  The root node is group 0, so ``/s_new`` targets
group 0 with addAction ``addToHead`` (0).

pyliblo3's reply callback order is ``cb(path, args, types, src)``; ``/s_get``
replies arrive as ``/n_set [node, "param", value]`` and ``/status`` replies as
``/status.reply [unused, numUgens, ...]``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

try:
    import liblo
except ImportError:  # pragma: no cover - liblo alias availability
    import pyliblo3 as liblo

_SCSYNTH_BIN = "scsynth"
_SCLANG_BIN = "sclang"
_DEF_DIR = Path(__file__).resolve().parent
# Every example in catalog.json, in catalog order.  Each *.scd is a fragment
# that evaluates to one SynthDef; load_defs() composes them into one batch.
_DEF_SCRIPTS = (
    "bubbles.scd",
    "formant.scd",
    "sine.scd",
    "simpleFM.scd",
    "chainsaw.scd",
    "drummer.scd",
    "gabberkick.scd",
    "hoover.scd",
    "abstractDrum.scd",
    "kalimba.scd",
    "marimba1.scd",
    "modalMarimba.scd",
    "pmCrotales.scd",
    "steelDrum.scd",
    "xylophone.scd",
    # SCLOrkSynths import (SPEC §9.8), bank by bank.
    # Community import (SPEC §9.9) — 7 repos, reshaped by
    # scripts/reshape_community_synthdefs.py; order = catalog.json order.
    "acid309.scd",
    "bass8.scd",
    "cs80lead.scd",
    "fmtribe.scd",
    "basicFM.scd",
    "ambi.scd",
    "bell.scd",
    "blip.scd",
    "bug.scd",
    "dbass.scd",
    "donk.scd",
    "dub.scd",
    "glass.scd",
    "keys.scd",
    "klank.scd",
    "nylon.scd",
    "pads.scd",
    "piano.scd",
    "pluck.scd",
    "prophet.scd",
    "sawbass.scd",
    "scatter.scd",
    "soft.scd",
    "soprano.scd",
    "spark.scd",
    "viola.scd",
    "pbass.scd",
    "rhodes.scd",
    "bass.scd",
    "enotamboura.scd",
    "fm.scd",
    "dxt.scd",
    "fm7.scd",
    "fm7algo.scd",
    "moogbass.scd",
    "sc303.scd",
    "supermandolin.scd",
    "supergong.scd",
    "superpiano.scd",
    "superhex.scd",
    "superkick.scd",
    "super808.scd",
    "superhat.scd",
    "supersnare.scd",
    "superclap.scd",
    "supersiren.scd",
    "supersquare.scd",
    "supersaw.scd",
    "superpwm.scd",
    "supercomparator.scd",
    "superchip.scd",
    "supernoise.scd",
    "superfork.scd",
    "superhammond.scd",
    "supervibe.scd",
    "superhoover.scd",
    "superzow.scd",
    "superstatic.scd",
    "supergrind.scd",
    "superwavemechanics.scd",
    "supertron.scd",
    "superreese.scd",
    "theremin.scd",
    "winwood.scd",
    "wobble.scd",
    "sinenv.scd",
    "dfm1.scd",
    "bpfsaw.scd",
    "henon.scd",
    "henonc.scd",
    "sinfb.scd",
    "ring1.scd",
    "ring2.scd",
    "ring3.scd",
    "ring4.scd",
    "pulse3.scd",
    "sinfb3.scd",
    "saw3.scd",
    "tri3.scd",
    "PMCrotale.scd",
    "apad_mh.scd",
    "babblingbrook_jmc.scd",
    "bassfoundation.scd",
    "basshighend.scd",
    "beating.scd",
    "blowbotl.scd",
    "bowed.scd",
    "cheappiano.scd",
    "clap_oto309.scd",
    "cymbal808_ryan.scd",
    "cymbalic_mcld.scd",
    "defaultB.scd",
    "drum_kick.scd",
    "snare.scd",
    "everythingrhodes.scd",
    "fatvelocitybass.scd",
    "waveguideFlute.scd",
    "forest_bird_pj.scd",
    "goeysynth.scd",
    "handclapsmash.scd",
    "handclapsmash2.scd",
    "harpsichord1.scd",
    "jilet.scd",
    "justwannahavefun.scd",
    "kik.scd",
    "kick3.scd",
    "kick_chrp.scd",
    "kick_oto309.scd",
    "kraftySnr.scd",
    "moogbasstone2.scd",
    "mrostinato.scd",
    "oneclap_thor.scd",
    "organdonor.scd",
    "ping_mh.scd",
    "plastickystrings.scd",
    "plucking.scd",
    "poly.scd",
    "prophet5pwmstrings.scd",
    "pwmbling.scd",
    "ressquares.scd",
    "sillyVoice.scd",
    "singleoscillatorwobble.scd",
    "situationsynth.scd",
    "snare_oto309.scd",
    "snare_stein.scd",
    "solo.scd",
    "sos_bell.scd",
    "spacetheremin.scd",
    "spookystrings.scd",
    "spookystrings2.scd",
    "string.scd",
    "synchronicity.scd",
    "tonewheeltwo.scd",
    "trianglewavebells.scd",
    "voicform.scd",
    "werkit.scd",
    "werkit2.scd",
    "whoorgan.scd",
    "winwoodlead.scd",
    "dxkBd1.scd",
    "dxkBd2.scd",
    "dxkBd3.scd",
    "dxkHh1.scd",
    "dxkHh2.scd",
    "dxkHh3.scd",
    "dxkSd1.scd",
    "dxkSd2.scd",
    "dxkSd3.scd",
    "dxkCymb808.scd",
    "dxkCymb808_2.scd",
    "dxkGong1.scd",
    "dxkClap1.scd",
    "dxkCowbell1.scd",
    "dxkArBusSet.scd",
    "dxkCheapPno.scd",
    "dxkDesyp1.scd",
    "dxkAcid.scd",
    "dxkRhodes1.scd",
    "dxkSawIter.scd",
    "dxkPortBass.scd",
    "dxkBpfSaw.scd",
    "dxkPulseASR.scd",
    "dxkPulseLinen.scd",
    "dxkPulseADSR.scd",
    "dxkPulseTriangle.scd",
    "dxkPulseSine.scd",
    "dxkSinASR.scd",
    "dxkSinLinen.scd",
    "dxkSinADSR.scd",
    "dxkSinTriangle.scd",
    "dxkSinSine.scd",
    "dxkVarSawASR.scd",
    "dxkVarSawLinen.scd",
    "dxkVarSawADSR.scd",
    "dxkVarSawTriangle.scd",
    "dxkVarSawSine.scd",
    "dxkSawASR.scd",
    "dxkSawLinen.scd",
    "dxkSawADSR.scd",
    "dxkSawTriangle.scd",
    "dxkSawSine.scd",
    "dxkSin2ASR.scd",
    "dxkSin2Linen.scd",
    "dxkSin2ADSR.scd",
    "dxkSin2Triangle.scd",
    "dxkSin2Sine.scd",
    "dxkDtmf.scd",
    "dxkClik.scd",
    "dxkClikFilt.scd",
    "dxkWNoiseBPFADSR.scd",
    "dxkWNoizBPFASR.scd",
    "dxkSimpleFm.scd",
    "acid_oto309.scd",
)
# The same defs by name, in the same order, for callers that talk about them.
DEF_NAMES = tuple(Path(name).stem for name in _DEF_SCRIPTS)

# The voice ceiling: nothing rings past VOICE_CAP_SECONDS, and the last
# VOICE_FADE_SECONDS of it is a fade.  Those two numbers are baked into every
# def fragment (an envelope has to survive /d_recv, so it cannot be added from
# here); test_sc.py pins the fragments and these constants together.
VOICE_CAP_SECONDS = 12.0
VOICE_FADE_SECONDS = 3.0

_STATUS_KEYS = (
    "numUgens",
    "numSynths",
    "numGroups",
    "numDefs",
    "avgCPU",
    "peakCPU",
    "nominalSampleRate",
    "actualSampleRate",
)


def resolve_scsynth() -> str | None:
    return _resolve_bin(_SCSYNTH_BIN)


def resolve_sclang() -> str | None:
    return _resolve_bin(_SCLANG_BIN)


def _typed(value):
    """The OSC type for a def argument.

    Integer parameters (``gate``, ``fade``) must not arrive as floats: SC
    compares them against integer indices.
    """
    return value if isinstance(value, int) else float(value)


def _resolve_bin(name: str) -> str | None:
    p = shutil.which(name)
    if p:
        return p
    for cand in (f"/usr/bin/{name}", f"/usr/local/bin/{name}"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


class ScServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 57110,
        scsynth_path: str | None = None,
        sclang_path: str | None = None,
        def_scripts=None,
        spawn=None,
        probe=None,
        clock=time.monotonic,
    ):
        self.host = host
        self.port = port
        self._scsynth_path = scsynth_path
        self._sclang_path = sclang_path
        if def_scripts is None:
            def_scripts = [str(_DEF_DIR / name) for name in _DEF_SCRIPTS]
        self._def_scripts = [str(p) for p in def_scripts]
        self._spawn = spawn if spawn is not None else subprocess.Popen
        self._clock = clock
        self._probe = probe if probe is not None else self.status
        self._proc = None

        # Called with the node id whenever scsynth reports a finished node.
        # Empty by default; the bridge uses it to forget dead voices.
        self.on_node_end = None

        # Receive side is initialised lazily on first OSC use.
        self._target = None
        self._server = None
        self._cond = None
        self._replies = {}
        self._stop = threading.Event()
        self._recv_thread = None

    # -- OSC plumbing ------------------------------------------------------
    def _ensure_server(self) -> None:
        if self._server is not None:
            return
        self._target = liblo.Address(self.host, self.port)
        self._cond = threading.Condition()
        self._replies = {}
        self._server = liblo.Server()
        self._server.add_method(None, None, self._dispatch)
        self._stop.clear()
        self._recv_thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._recv_thread.start()

    def _dispatch(self, path, args, types, src, user_data=None):
        with self._cond:
            self._replies[path] = (list(args), types)
            self._cond.notify_all()
        # Node ends arrive from scsynth's receive thread; a hook that raises
        # must not take the thread down with it.
        if path == "/n_end" and self.on_node_end is not None:
            try:
                self.on_node_end(int(args[0]))
            except Exception:
                pass

    def _serve_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._server.recv(100)
            except Exception:
                pass

    def _send(self, path: str, *args) -> None:
        self._ensure_server()
        self._server.send(self._target, path, *args)

    def _rpc(self, wait_for: str, path: str, *args, timeout: float = 3.0):
        self._ensure_server()
        with self._cond:
            self._replies.pop(wait_for, None)
        self._server.send(self._target, path, *args)
        deadline = self._clock() + timeout
        with self._cond:
            while wait_for not in self._replies:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    return None
                self._cond.wait(timeout=remaining)
            return self._replies[wait_for]

    # -- lifecycle ---------------------------------------------------------
    def boot(self) -> bool:
        if self._probe():
            self._register_for_node_ends()
            return True
        argv = [
            self._scsynth_path or resolve_scsynth(),
            "-u",
            str(self.port),
            "-B",
            self.host,
        ]
        self._proc = self._spawn(argv)
        deadline = self._clock() + 5.0
        while self._clock() < deadline:
            if self._probe():
                self._register_for_node_ends()
                return True
            time.sleep(0.1)
        return False

    def _register_for_node_ends(self) -> None:
        """Ask scsynth to report /n_end (and /n_go) for every node.

        scsynth says nothing about a node finishing until the client opts in
        with /notify, and the bridge needs to know: a voice that has faded out
        must be forgotten, or later activity would "retune" a node that no
        longer exists instead of starting a fresh one.
        """
        try:
            self._send("/notify", 1)
        except Exception:  # pragma: no cover - OSC unavailable
            pass

    def batch_source(self) -> str:
        """Compose the one sclang script that delivers every catalogued def.

        Each ``*.scd`` is a fragment that evaluates to a SynthDef, so it is
        wrapped in ``d = { ... }.value;``: that keeps multi-statement fragments
        (formant puts three entries in ``Spec.specs`` before its SynthDef) legal
        and still leaves the def as the fragment's value.
        """
        lines = [
            "// generated by super_quneo_collider.sc.ScServer.batch_source",
            "(",
            f'var addr = NetAddr("{self.host}", {self.port});',
            "var d;",
        ]
        for path in self._def_scripts:
            lines.append(f"// def: {path}")
            lines.append("d = {")
            lines.append(Path(path).read_text().rstrip())
            lines.append("}.value;")
            lines.append('addr.sendMsg("/d_recv", d.asBytes);')
        lines.append(f'"super-quneo-collider: {len(self._def_scripts)} defs sent".postln;')
        lines.append("0.exit;")
        lines.append(")")
        return "\n".join(lines) + "\n"

    def load_defs(self, timeout: float = 10.0) -> bool:
        """Deliver every catalogued SynthDef in a single sclang run (D7)."""
        fd, script = tempfile.mkstemp(prefix="sqc-defs-", suffix=".scd")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(self.batch_source())
            proc = self._spawn([self._sclang_path or resolve_sclang(), script])
            if proc.wait() != 0:
                return False
        finally:
            try:
                os.unlink(script)
            except OSError:  # pragma: no cover - best effort
                pass
        # scsynth does not ack /d_recv, and the one-shot sclang exits as soon as
        # the messages are queued, so an immediate /s_new can race the delivery.
        # Confirm the defs actually registered (numDefs reaches the catalog size)
        # before returning, otherwise the caller's /s_new hits "SynthDef not
        # found".  scsynth pre-registers a handful of its own, so this is a
        # lower bound rather than an equality check.
        deadline = self._clock() + timeout
        while self._clock() < deadline:
            st = self._probe()
            if st and st.get("numDefs", 0) >= len(self._def_scripts):
                return True
            time.sleep(0.1)
        return False

    def spawn(self, def_name: str, node: int = 1000, **args) -> bool:
        flat = ["/s_new", str(def_name), int(node), 0, 0]
        for key, value in args.items():
            flat.append(str(key))
            flat.append(_typed(value))
        self._send(*flat)
        return True

    def set_params(self, node: int, **args) -> None:
        """Retune a live node: one /n_set carrying every parameter and value.

        The whole state goes in one message so a retune is applied as a single
        edit rather than a run of partial ones.
        """
        flat = ["/n_set", int(node)]
        for key, value in args.items():
            flat.append(str(key))
            flat.append(_typed(value))
        self._send(*flat)

    def set_param(self, node: int, param: str, value: float) -> None:
        self._send("/n_set", int(node), param, _typed(value))

    def get_param(self, node: int, param: str) -> float | None:
        reply = self._rpc("/n_set", "/s_get", int(node), param)
        if not reply:
            return None
        args, _types = reply
        for i in range(1, len(args) - 1, 2):
            if args[i] == param:
                return args[i + 1]
        return None

    def status(self) -> dict | None:
        reply = self._rpc("/status.reply", "/status")
        if not reply:
            return None
        args, _types = reply
        # scsynth replies with a leading unused int, then the eight fields.
        return dict(zip(_STATUS_KEYS, args[1:]))

    def stop(self) -> None:
        try:
            if self._server is not None:
                self._server.send(self._target, "/quit")
        except Exception:
            pass
        if self._proc is not None:
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
                    self._proc.wait(timeout=2)
            except Exception:
                pass
        self._stop.set()
