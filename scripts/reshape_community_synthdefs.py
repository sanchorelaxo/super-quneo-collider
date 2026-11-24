"""Reshape + guard the community SynthDefs (SPEC §9.9).

Reads the eight community `.scd` collections cloned to ``/tmp/sqc-community``
(same tree the §9.9 sizing probe scanned), applies the §9.9.1 dedupe key and the
§9.9.2 reshape rules, then emits one guarded ``.scd`` fragment per net-new def
into ``src/super_quneo_collider/`` — the same fragment shape §9.8 ships.

Pipeline (all mechanical, no per-def judgement):

1. **Scan.** Every ``SynthDef`` in the collected files, minus the files the
   §9.9 survey rules out (effects, sequencers, buffer players).
2. **SuperDirt glue** (§9.9.2). ``DirtPan.ar(sig, ~dirt.numChannels, ..)`` ->
   ``Pan2.ar(sig, ..)``; ``OffsetOut`` -> ``Out``; the foxdot/tidal
   ``In.kr(bus, 1)`` control-bus read -> the def's own ``freq`` control;
   ``ReplaceOut.ar(bus, sig)`` -> routed to the def's ``out``.
3. **Exclusions.** Buffer players are dropped (they cannot sound from the
   select alone, §9.9.2); audio-rate input readers (``In.ar``) are dropped
   because they are effects/routers, not voices; a name already carried by a
   checked-in fragment is dropped (§9.9.1, normalised name).
4. **Guard** (identical to §9.8 Decision 1): the def's own output becomes
   ``snd``, its own ``doneAction: 2`` becomes ``0``, and the fragment gains the
   shared stop fade, the 12 s ceiling and ``DetectSilence`` as the only freeing
   action.
5. **Gesture** (§9.9.3): a ``gate`` argument means ``continuous``; a
   self-ending envelope and no ``gate`` means ``oneshot``.
6. **Params** (§9.9.5): the first two or three non-``out``/``pan`` arguments in
   declaration order bind to the vertical-slider ladder, round-robin across the
   four rungs so no rung is over-used and every entry gets at least two.

Usage::

    python3 scripts/reshape_community_synthdefs.py --dry-run
    python3 scripts/reshape_community_synthdefs.py --write
    python3 scripts/reshape_community_synthdefs.py --write --check

``--check`` compiles every emitted fragment offline with sclang (the same
``{ <fragment> }.value`` mechanism the probe used) and reports any failure.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "super_quneo_collider"
COMMUNITY = Path("/tmp/sqc-community")
CATALOG = SRC / "catalog.json"
SC_PY = SRC / "sc.py"

# Scratch OSC port for the server-acceptance probe, clear of the app's own
# server port so a running instrument is never disturbed.
PROBE_PORT = 57900

# ---------------------------------------------------------------------------
# sources — mirrors the §9.9 survey table; dict order is import order
# ---------------------------------------------------------------------------
# source key -> (relative path under COMMUNITY, [skip substrings])
SOURCES = {
    "tidal-synths": ("tidal-synths", ["loadAll.scd"]),
    "loopier/synthdefs": ("synthdefs", [
        "synthdef-fx", "synthdef-granular", "synthdef-bit3sequencer",
        "synthdef-bufrd", "synthdef-playbuf", "synthdef-loopbuf", "synthdef-roda",
        "DEV-seqadora", "synthdefs.scd",
    ]),
    "awesome-synthdefs": ("awesome-synthdefs", ["co34pt_SynthDef_Examples",
                                                "ExampleUser_Examples"]),
    "everythingwillbetakenaway/Synthdefs": ("Synthdefs", [
        "linndrum", "psw", "Record Scratcher", "sctweets2", "sctweets",
        "startupaltetstts", "gogo", "someextraDEFS",
    ]),
    "derekxkwan/dxkSynthDefs": ("dxkSynthDefs", []),
    "redFrik/sInstruments": ("sInstruments", []),
    "supercollider-quarks/SynthDefPool": ("SynthDefPool", []),
}

# source key -> (catalog source, author, url, license) for the §9.9.4 header
REPO_META = {
    "tidal-synths": ("diegodorado/tidal-synths", "diegodorado",
                     "https://github.com/diegodorado/tidal-synths", "none stated"),
    "loopier/synthdefs": ("loopier/synthdefs", "loopier",
                          "https://github.com/loopier/synthdefs", "none stated"),
    "awesome-synthdefs": ("theseanco/awesome-synthdefs", "theseanco",
                          "https://github.com/theseanco/awesome-synthdefs", "none stated"),
    "everythingwillbetakenaway/Synthdefs": (
        "everythingwillbetakenaway/Synthdefs", "everythingwillbetakenaway",
        "https://github.com/everythingwillbetakenaway/Synthdefs", "none stated"),
    "derekxkwan/dxkSynthDefs": ("derekxkwan/dxkSynthDefs", "derekxkwan",
                                "https://github.com/derekxkwan/dxkSynthDefs", "GPL-3.0"),
    "redFrik/sInstruments": ("redFrik/sInstruments", "redFrik",
                             "https://github.com/redFrik/sInstruments", "GPL-3.0"),
    "supercollider-quarks/SynthDefPool": (
        "supercollider-quarks/SynthDefPool", "supercollider-quarks",
        "https://github.com/supercollider-quarks/SynthDefPool", "quark"),
}

# GPL sources: the copyleft travels with the file (§9.9.4), so the upstream
# LICENSE is copied in beside the imported defs.
LICENSE_COPY = {
    "derekxkwan/dxkSynthDefs": ("dxkSynthDefs/LICENSE.txt", "LICENSE.dxkSynthDefs"),
    "redFrik/sInstruments": ("sInstruments/LICENSE", "LICENSE.sInstruments"),
}

SINSTR_KEEP = "instruments/sStream.scd"

BUFFER_UGENS = re.compile(
    r"\b(PlayBuf|BufRd|BufWr|RecordBuf|Warp1|DiskIn|DiskOut|SoundIn|Vocal)\b"
)
SYNTH_OPEN = re.compile(r"SynthDef(?:\.new)?\s*\(\s*[\\\"']?([A-Za-z_]\w*)")
# DirtPan.ar(A, ~dirt.numChannels, C, D) -> Pan2.ar(A, C, D)
DIRTPAN = re.compile(
    r"DirtPan\.ar\((\s*[^,]+?),\s*~dirt\.numChannels\s*,\s*([^,]+?),\s*([^)]+?)\)"
)

# Audio-rate input: an effect/router, not a sound source.  LocalIn is ours.
# ReplaceOut.ar is *not* an input: it is how the foxdot/tidal defs write their
# own voice to the SuperDirt bus, so it is the def's output (§9.9.2).
IN_AR = re.compile(r"(?<!Local)(?<![\w.])In\s*\.\s*ar\s*\(")
# The SuperDirt control-bus read that carries the note's frequency:
# In.kr(bus), In.kr(bus, 1), In.kr(cbus), In.kr(fltBus, 1).
IN_KR_BUS = re.compile(
    r"(?<![\w.])In\s*\.\s*kr\s*\(\s*(?:bus|cbus|fltBus)\s*(?:,\s*\d+\s*)?\)"
)
# `<name> = In.kr(<bus>)`: the whole statement is redundant once the def owns
# the value (its own arg carries it), so it is cut rather than rewritten.
EXACT_BUS_READ = re.compile(r"^(\w+)\s*=\s*In\s*\.\s*kr\s*\([^)]*\)$", re.DOTALL)
# A control-bus write means nothing in a self-contained one-voice def.
REPLACE_OUT_KR = re.compile(r"^ReplaceOut\s*\.\s*kr\s*\(", re.IGNORECASE)
# `gate = 1;` inside the body would collide with the guard's own gate arg.
GATE_ASSIGN = re.compile(r"^gate\s*=\s*(?:1|1\.0)$")
# what may stand as an argument default
LITERAL = re.compile(
    r"^(?:[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|true|false|nil|null)$"
)
OUT_AR = re.compile(r"^\s*(?:\w+\s*=\s*)?(?:Out|ReplaceOut|XOut|OffsetOut)\s*\.\s*ar\s*\(")
DETECT_SILENCE = re.compile(r"^\s*DetectSilence\s*\.\s*ar\s*\(")
DONE_ACTION_2 = re.compile(r"doneAction\s*:\s*2\b")
CTRL_VAR = re.compile(r"^var\s+(\w+)\s*=\s*\\\w+\s*\.\s*(?:kr|ar)\s*\(([^)]*)\)$")

# arguments that are glue, not musical params (§9.9.5 binds the real ones)
GLUE_ARGS = {
    "out", "gate", "fade", "pan", "bus", "fltBus", "cbus", "in", "ins",
    "t_trig", "trig", "accelerate", "startPos", "buf", "bufnum", "numChans",
    "chans", "doneAction",
}

# explicit defaults for args the upstream left nil
NIL_DEFAULT = {
    "freq": "440", "amp": "0.3", "bus": "0", "fltBus": "0", "cbus": "0",
    "in": "0", "pan": "0", "sus": "1", "sustain": "1", "rel": "1",
    "release": "1", "att": "0.01", "dec": "0.2", "rate": "1", "dur": "1",
    "t_trig": "0", "accelerate": "0", "vib": "0", "fmod": "0",
}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


# ---------------------------------------------------------------------------
# extraction (same walk as the §9.9 sizing probe)
# ---------------------------------------------------------------------------
def matching_close(text: str, open_idx: int) -> int:
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if c == '"':
            j = text.find('"', i + 1)
            i = n if j == -1 else j + 1
            continue
        if c == "'":
            j = text.find("'", i + 1)
            i = n if j == -1 else j + 1
            continue
        if c == "$":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"unbalanced braces from {open_idx}")


def extract_defs(text: str) -> list[tuple[str, str]]:
    out = []
    pos = 0
    while True:
        m = SYNTH_OPEN.search(text, pos)
        if not m:
            break
        try:
            open_idx = text.index("{", m.end())
            close_idx = matching_close(text, open_idx)
        except ValueError:
            pos = m.end()
            continue
        out.append((m.group(1), text[open_idx + 1:close_idx].expandtabs(2)))
        pos = close_idx + 1
    return out


def reshape_glue(body: str) -> str:
    body = DIRTPAN.sub(r"Pan2.ar(\1, \2, \3)", body)
    return body.replace("OffsetOut", "Out")


def scan() -> list[dict]:
    """Every candidate SynthDef, in source-then-name order, first name wins."""
    rows: list[dict] = []
    seen: set[str] = set()
    for source, (rel, skips) in SOURCES.items():
        root = COMMUNITY / rel
        for fp in sorted(root.rglob("*.scd")):
            relp = str(fp.relative_to(root))
            if any(s in relp for s in skips):
                continue
            if source == "redFrik/sInstruments" and relp != SINSTR_KEEP:
                continue
            if source == "derekxkwan/dxkSynthDefs" and not any(
                    k in relp for k in (
                        "dxkDrums", "dxkPitched", "dxkModal", "dxkSupSynths",
                        "dxkSimpleOsc", "dxkMisc", "dxkSynthsMisc")):
                continue
            for name, body in extract_defs(fp.read_text(errors="replace")):
                if name in seen:
                    continue
                seen.add(name)
                rows.append({
                    "name": name,
                    "source": source,
                    "file": str(fp.relative_to(COMMUNITY)),
                    "body": reshape_glue(body),
                })
    return rows


# ---------------------------------------------------------------------------
# statement-level surgery
# ---------------------------------------------------------------------------
def blank_comments(code: str) -> str:
    """Same length as ``code`` with comments (not strings) blanked out."""
    out = list(code)
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = code.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c == "/" and nxt == "*":
            j = code.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c in "\"'$":
            j = code.find(c, i + 1) if c != "$" else i + 2
            i = n if j == -1 else j + 1
            continue
        i += 1
    return "".join(out)


def iter_statements(code: str):
    """Yield (start, end) for every depth-0 statement; ``end`` excludes ``;``."""
    depth = 0
    start = 0
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            yield (start, i)
            start = i + 1
        i += 1
    if code[start:].strip():
        yield (start, n)


def find_statement(code: str, pattern: re.Pattern, last: bool = False):
    hits = [sp for sp in iter_statements(code) if pattern.match(code[sp[0]:sp[1]])]
    if not hits:
        return None
    return hits[-1] if last else hits[0]


def call_args(code: str, lp: int):
    """Split ``code[lp] == '('``'s arguments at depth 0; return (args, close)."""
    depth = 0
    args, cur = [], ""
    i = lp
    n = len(code)
    while i < n:
        c = code[i]
        if c in "([{":
            depth += 1
            if depth == 1 and c == "(":
                i += 1
                continue
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append(cur.strip())
                return args, i
        if depth == 1 and c == ",":
            args.append(cur.strip())
            cur = ""
        else:
            cur += c
        i += 1
    raise ValueError("unbalanced call")


def _top_level(text: str, target: str) -> int:
    depth = 0
    for i, c in enumerate(text):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == target and depth == 0:
            return i
    return -1


def parse_header(body: str):
    """Return (style, [(name, default_or_None)], header_end, ctrl_statements)."""
    code = blank_comments(body)
    off = len(body) - len(body.lstrip())
    head = body[off:]
    if head.startswith("arg"):
        end = _top_level(code[off:], ";")
        if end == -1:
            raise ValueError("arg header without ';'")
        return "arg", _split_args(head[3:end]), off + end + 1, []
    if head.startswith("|"):
        end = code.find("|", off + 1)
        if end == -1:
            raise ValueError("pipe header without closing '|'")
        return "pipe", _split_args(head[1:end - off]), end + 1, []
    # Control style: no header at all.  Promote every `var x = \y.kr(default)`
    # read to an argument: the guard declares the same name either way
    # (§9.9.2 — `\y.kr(..)` is already OSC-addressable), so `arg x=default`
    # replaces the statement without touching a single use in the body, and the
    # value becomes a bindable param instead of an anonymous control.
    promoted, spans = [], []
    for sp in iter_statements(code):
        m = CTRL_VAR.match(code[sp[0]:sp[1]].strip())
        if not m:
            continue
        name, default = m.group(1), m.group(2).strip()
        spans.append(sp)
        if name in ("out", "gate", "fade"):
            promoted.append((name, default or "0"))
        else:
            # a control default may be an expression (`440 * 2`); an argument
            # default has to be a literal, so fall back when it is not one
            promoted.append((name, default if LITERAL.match(default) else ""))
    return "ctrl", promoted, off, spans


def _arg_chunks(code: str) -> list[tuple[int, int]]:
    """Depth-0 token spans of a header: split on commas *and* whitespace.

    Community defs write both `|freq=440, amp=0.1|` and `| out=0 gate=1 freq=40
    fltBus |`, so a comma-only split is not enough.  Chunks, not arguments: the
    caller re-joins the ones that belong to one value.
    """
    chunks: list[tuple[int, int]] = []
    depth, start = 0, None
    for i, c in enumerate(code):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if depth == 0 and (c.isspace() or c == "," or c == "="):
            # `=` is a boundary too: community defs write `amp=0.1` with no
            # space, and without this the whole `name=value` is one token.
            if start is not None:
                chunks.append((start, i))
                start = None
            continue
        if start is None:
            start = i
    if start is not None:
        chunks.append((start, len(code)))
    return chunks


def _split_args(text: str) -> list[tuple[str, str | None]]:
    """Header text -> [(name, default_or_None)] in declaration order."""
    code = blank_comments(text)
    chunks = _arg_chunks(code)
    out: list[tuple[str, str | None]] = []
    i = 0
    while i < len(chunks):
        s, e = chunks[i]
        tok = text[s:e]
        if tok == "=":
            i += 1
            continue
        nxt = text[chunks[i + 1][0]:chunks[i + 1][1]] if i + 1 < len(chunks) else None
        if re.fullmatch(r"[A-Za-z_]\w*", tok) and nxt == "=":
            name = tok
            i += 2
            if i >= len(chunks):
                out.append((name, None))
                continue
            vs, ve = chunks[i]
            i += 1
            while i < len(chunks):
                s2, e2 = chunks[i]
                t2 = text[s2:e2]
                if t2 == "=":
                    break
                nxt2 = (text[chunks[i + 1][0]:chunks[i + 1][1]]
                        if i + 1 < len(chunks) else None)
                if re.fullmatch(r"[A-Za-z_]\w*", t2) and (
                        nxt2 == "=" or not re.fullmatch(r"[A-Za-z_]\w*", text[vs:ve])):
                    break            # `freq=440 amp=1` / `freq=40 fltBus`
                ve = e2
                i += 1
            out.append((name, text[vs:ve].strip()))
            continue
        if re.fullmatch(r"[A-Za-z_]\w*", tok):
            out.append((tok, None))              # bare arg: `| out freq pan |`
            i += 1
            continue
        if out:                                  # stray token: keep it with its value
            prev = out[-1]
            out[-1] = (prev[0], ((prev[1] + " ") if prev[1] else "") + tok)
        i += 1
    return out


def apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    out = text
    for start, end, repl in sorted(edits, key=lambda e: -e[0]):
        out = out[:start] + repl + out[end:]
    return out


def _varname(chunk: str) -> str | None:
    """Leading identifier of a `var` name-list chunk (`x`, `x = 1`, `x=1`)."""
    m = re.match(r"\s*([A-Za-z_]\w*)", chunk)
    return m.group(1) if m else None


def prune_var_names(text: str, forbidden: set[str]) -> str:
    """Drop `var` declarations of names the guard's arg line already declares.

    A promoted control read (`var gate = \\gate.kr(1);`) or a body that assigns
    the guard's own name (`var ... gate;` next to `gate=1;`) would otherwise be
    declared twice — `arg gate=1` followed by `var gate` does not compile.

    The name list is split at depth-0 commas only: `var fifth = min(\\fifth.kr(0),
    1) * overtone;` carries a comma inside its initializer, and splitting there
    mangles the statement into a `var` that follows other statements (a syntax
    error in SC, where every `var` must precede the first statement).
    """
    code = blank_comments(text)
    edits: list[tuple[int, int, str]] = []
    for sp in iter_statements(code):
        cstmt = code[sp[0]:sp[1]]
        if not re.match(r"\s*var\b", cstmt):
            continue
        stmt = text[sp[0]:sp[1]]
        off = cstmt.find("var") + len("var")
        names_code, names_txt = cstmt[off:], stmt[off:]
        parts: list[tuple[int, int]] = []
        depth, part_start = 0, 0
        for i, c in enumerate(names_code):
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == "," and depth == 0:
                parts.append((part_start, i))
                part_start = i + 1
        parts.append((part_start, len(names_code)))
        keep = [names_txt[a:b] for a, b in parts
                if _varname(names_code[a:b]) not in forbidden]
        if not keep:
            start = sp[0]
            while start > 0 and text[start - 1] in " \t":
                start -= 1
            end = sp[1] + 1 if text[sp[1]:sp[1] + 1] == ";" else sp[1]
            if text[end:end + 1] == "\n":
                end += 1
            edits.append((start, end, ""))
        elif len(keep) != len(parts):
            edits.append((sp[0], sp[1], "var" + ",".join(keep)))
    return apply_edits(text, edits)


# ---------------------------------------------------------------------------
# reshape
# ---------------------------------------------------------------------------
def classify(args, code: str) -> str:
    if any(n == "gate" for n, _ in args):
        return "continuous"
    if DONE_ACTION_2.search(code):
        return "oneshot"
    return "continuous"


DEPRECATED_SUBS = ((re.compile(r"\.asInt\b"), ".asInteger"),)


def fix_deprecated(text: str) -> str:
    """Retire calls sclang 3.13 warns about on every def load.

    ``asInt`` (deprecated since 3.11) makes the server log a deprecation
    warning per call site for the life of the process, so the import rewrites
    it to the surviving ``asInteger``.
    """
    for pat, repl in DEPRECATED_SUBS:
        text = pat.sub(repl, text)
    return text


def build_fragment(row: dict) -> dict:
    name, body, source = row["name"], row["body"], row["source"]
    code = blank_comments(body)
    style, args, header_end, ctrl_spans = parse_header(body)
    gesture = classify(args, code)
    arg_names = {n for n, _ in args}

    # Statement surgery reads `scan`, whose header (arg/pipe) or promoted
    # control reads (ctrl) are blanked to spaces: a pipe header carries no `;`,
    # so leaving it in would glue the first real statement onto it.  Blanking is
    # length-preserving, so scan/code/body share one index space.
    off = len(body) - len(body.lstrip())
    if style in ("arg", "pipe"):
        scan = code[:off] + " " * (header_end - off) + code[header_end:]
    else:
        scan = code
        for sp in ctrl_spans:
            scan = scan[:sp[0]] + " " * (sp[1] + 1 - sp[0]) + scan[sp[1] + 1:]

    edits: list[tuple[int, int, str]] = []
    removed: list[tuple[int, int]] = []

    def cut(sp, eat_newline: bool = False) -> None:
        start = sp[0]
        while start > 0 and body[start - 1] in " \t":
            start -= 1
        end = sp[1] + 1 if body[sp[1]:sp[1] + 1] == ";" else sp[1]
        if eat_newline and body[end:end + 1] == "\n":
            end += 1
        removed.append((start, end))
        edits.append((start, end, ""))

    def inside(idx: int) -> bool:
        return any(a <= idx < b for a, b in removed)

    if style in ("arg", "pipe"):
        edits.append((off, header_end, ""))
        removed.append((off, header_end))
    else:
        for sp in ctrl_spans:
            cut(sp, eat_newline=True)

    # SuperDirt control-bus glue (§9.9.2).  The note's pitch arrived over a
    # control bus: when the statement's own target is the def's argument the
    # argument already carries the value, so the statement goes; otherwise the
    # read becomes the def's own `freq` control, which keeps a filter tracking
    # the note instead of freezing on bus 0's default.
    bus_read = False
    for sp in list(iter_statements(scan)):
        if inside(sp[0]):
            continue
        m = EXACT_BUS_READ.match(scan[sp[0]:sp[1]].strip())
        if m and m.group(1) in arg_names:
            cut(sp, eat_newline=True)
            bus_read = True
    for m in IN_KR_BUS.finditer(scan):
        if inside(m.start()):
            continue
        bus_read = True
        edits.append((m.start(), m.end(), "freq"))
    if bus_read and "freq" not in arg_names:
        args = args + [("freq", "440")]
        arg_names.add("freq")

    # the def's own number frees nothing (D10)
    for m in DONE_ACTION_2.finditer(scan):
        if not inside(m.start()):
            edits.append((m.start(), m.end(), "doneAction: 0"))

    # its own DetectSilence is replaced by the guard's
    ds = find_statement(scan, DETECT_SILENCE)
    if ds and not inside(ds[0]):
        cut(ds, eat_newline=True)

    # a control-bus write and a bare `gate = 1;` are dead in a one-voice def
    for sp in list(iter_statements(scan)):
        if inside(sp[0]):
            continue
        st = scan[sp[0]:sp[1]].strip()
        if REPLACE_OUT_KR.match(st) or GATE_ASSIGN.match(st):
            cut(sp, eat_newline=True)

    # the def's own output becomes snd (every candidate emits audio exactly once)
    out_sp = None
    for sp in iter_statements(scan):
        if inside(sp[0]):
            continue
        if OUT_AR.match(scan[sp[0]:sp[1]]):
            out_sp = sp
    if not out_sp:
        raise ValueError("no audio output")
    raw_stmt = body[out_sp[0]:out_sp[1]]
    raw_lp = blank_comments(raw_stmt).index("(")
    raw_exprs = _raw_args(raw_stmt, raw_lp)
    if len(raw_exprs) == 1:
        expr = raw_exprs[0]                        # Out.ar(sig)
    elif len(raw_exprs) == 2:
        expr = raw_exprs[1]                        # Out.ar(out, sig)
    else:
        expr = "[" + ", ".join(raw_exprs[1:]) + "]"  # Out.ar(out, l, r, ...)
    cut(out_sp)

    inner = apply_edits(body, edits).strip("\n")
    inner = prune_var_names(inner, arg_names | {"out", "gate", "fade"})

    # --- arg header ------------------------------------------------------
    bespoke, seen = [], set()
    for aname, adef in args:
        if aname in ("out", "gate", "fade") or aname in seen:
            continue
        seen.add(aname)
        if adef is None or adef.strip() in ("", "nil"):
            adef = NIL_DEFAULT.get(aname, _nil_fallback(aname))
        if style == "ctrl" and not LITERAL.match(str(adef).strip()):
            # the control default was an expression (`440 * 2`, `88.midicps`);
            # an argument default has to be a literal
            adef = NIL_DEFAULT.get(aname, _nil_fallback(aname))
        if bus_read and aname == "freq" and _num(adef) in (None, 0):
            adef = "440"          # the pitch used to arrive over the bus
        bespoke.append(f"{aname}={adef}")
    argline = "arg out=0"
    if bespoke:
        argline += ", " + ", ".join(bespoke)
    argline += ", gate=1, fade=1;"

    # --- var declarations -------------------------------------------------
    declared = set()
    for sp in iter_statements(code):
        st = code[sp[0]:sp[1]].strip()
        if st.startswith("var"):
            declared.update(re.findall(r"[A-Za-z_]\w*", st[5:]))
    missing = [v for v in ("snd", "stopFade", "fadeEnv") if v not in declared]
    varline = f"var {', '.join(missing)};" if missing else ""

    # --- header comment (§9.9.4) -----------------------------------------
    repo, author, url, lic = REPO_META[source]
    header = (
        f"// {row['file']} — {repo} ({url}), by {author}; license: {lic}\n"
        f"// SPEC §9.9 import, reshaped per §9.9.2. gesture: {gesture}\n"
    )

    tail = [
        f"snd = {expr};",
        "stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);",
        "fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);",
        "snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);",
        "DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);",
        "Out.ar(out, snd);",
    ]
    parts = [f'SynthDef("{name}", {{ {argline}']
    if varline:
        parts.append("  " + varline)
    parts.append(inner)
    for line in tail:
        parts.append("  " + line)
    parts.append("});")
    fragment = fix_deprecated(header + "\n".join(parts) + "\n")
    return {
        "name": name,
        "source": source,
        "file": row["file"],
        "gesture": gesture,
        "args": args,
        "fragment": fragment,
    }


def _raw_args(stmt: str, lp: int) -> list[str]:
    """Argument texts (verbatim, from the original source) of a call."""
    depth = 0
    args, cur = [], ""
    i = lp
    n = len(stmt)
    while i < n:
        c = stmt[i]
        if c in "([{":
            depth += 1
            if depth == 1 and c == "(":
                i += 1
                continue
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append(cur.strip())
                return args
        if depth == 1 and c == ",":
            args.append(cur.strip())
            cur = ""
        else:
            cur += c
        i += 1
    return args


def _nil_fallback(name: str) -> str:
    n = name.lower()
    if "freq" in n or n in ("hz", "pitch"):
        return "440"
    if any(k in n for k in ("amp", "vol", "level", "gain", "lvl")):
        return "0.3"
    if any(k in n for k in ("rate", "speed", "ratio", "scale")):
        return "1"
    if any(k in n for k in ("att", "atk")):
        return "0.01"
    if any(k in n for k in ("rel", "dec", "sus", "dur", "time")):
        return "1"
    return "0"


# ---------------------------------------------------------------------------
# params + slider ladder (§9.9.5)
# ---------------------------------------------------------------------------
VSLIDERS = [("vSliderButton0", 61), ("vSliderButton1", 69),
            ("vSliderButton2", 77), ("vSliderButton3", 85)]

RANGE_RULES = [
    (re.compile(r"freq|fundfreq|formantfreq|pitch|hz|carfreq|modfreq|centerfreq"),
     (40.0, 4000.0, "exp")),
    (re.compile(r"cutoff|ctf|lpf|hpf|bpf|ffreq|filtfreq|reso?freq"),
     (20.0, 12000.0, "exp")),
    (re.compile(r"sustainlevel|^level$|mix|wet|dry|blend|duty|pw$|^pw|width|"
                r"^rq$|^res$|^q$|feedback|^fb$|damp|amount"),
     (0.0, 1.0, "lin")),
    (re.compile(r"att|atk"), (0.001, 2.0, "exp")),
    (re.compile(r"rel|dec|sus|dur|time|len|hold|release"), (0.05, 8.0, "exp")),
    (re.compile(r"rate|speed|ratio|mult|spread|detune|index|^n$|partials"),
     (0.1, 20.0, "exp")),
    (re.compile(r"amp|vol|level|gain|lvl"), (0.0, 1.0, "lin")),
]


def _num(text: str):
    try:
        f = float(text)
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) and "." not in str(text) else f


def params_for(args, start: int) -> list[dict]:
    cands = [(n, d) for n, d in args if n not in GLUE_ARGS]
    picked = cands[:3] if len(cands) >= 3 else cands[:2]
    out = []
    for i, (pname, pdef) in enumerate(picked):
        default = _num(pdef if pdef is not None else "0")
        if default is None:
            default = 0
        lo, hi, curve = 0.0, 1.0, "lin"
        for pat, rng in RANGE_RULES:
            if pat.search(pname):
                lo, hi, curve = rng
                break
        else:
            hi = max(1.0, abs(float(default)) * 4) if default else 1.0
        if lo == 0 and curve == "exp":
            lo = 0.01
        control, cc = VSLIDERS[(start + i) % len(VSLIDERS)]
        out.append({
            "name": pname,
            "control": control,
            "cc": cc,
            "min": lo,
            "max": hi,
            "curve": curve,
            "default": default,
        })
    return out


# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------
GUARD_STRINGS = (
    "arg out=0", "gate=1", "fade=1", "Env.asr(0.01, 1, 3)",
    "Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin')",
    "Select.kr(fade > 0, [1, fadeEnv])", "DetectSilence.ar(",
    # the guard's DetectSilence is the only thing allowed to free the voice
    "doneAction: 2",
)


def plan() -> tuple[list[dict], list[tuple[str, str]]]:
    """Return (accepted rows, dropped (name, reason)).

    A candidate is dropped when the board cannot drive it: buffer players,
    audio-rate-input effects (§9.9.2), names already in the catalog (§9.9.1),
    defs with no audio output, and defs whose arguments leave nothing bindable
    for the slider ladder (§9.9.5).
    """
    shipped = {norm(p.stem) for p in SRC.glob("*.scd")}
    catalog = json.loads(CATALOG.read_text())
    shipped |= {norm(e["def"]) for e in catalog["examples"].values()}
    kept, dropped = [], []
    for row in scan():
        name, body = row["name"], row["body"]
        code = blank_comments(body)
        if BUFFER_UGENS.search(code):
            dropped.append((name, "buffer player (§9.9.2)"))
            continue
        if IN_AR.search(code):
            dropped.append((name, "audio-rate input = effect/router (§9.9.2)"))
            continue
        if norm(name) in shipped:
            dropped.append((name, "name already in the catalog (§9.9.1)"))
            continue
        try:
            frag = build_fragment(row)
        except ValueError as exc:
            dropped.append((name, f"reshape: {exc}"))
            continue
        if not re.search(r"(?<![\w.])Out\s*\.\s*ar\s*\(", blank_comments(frag["fragment"])):
            dropped.append((name, "no audio output"))
            continue
        params = params_for(frag["args"], len(kept))
        if not params:
            dropped.append((name, "nothing bindable (§9.9.5)"))
            continue
        frag["params"] = params
        kept.append(frag)
    return kept, dropped


def def_scripts_block(names: list[str]) -> str:
    lines = ["_DEF_SCRIPTS = ("]
    for n in names[:15]:
        lines.append(f'    "{n}.scd",')
    lines.append("    # SCLOrkSynths import (SPEC §9.8), bank by bank.")
    lines.append("    # Community import (SPEC §9.9) — 7 repos, reshaped by")
    lines.append("    # scripts/reshape_community_synthdefs.py; order = catalog.json order.")
    for n in names[15:]:
        lines.append(f'    "{n}.scd",')
    lines.append(")")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write fragments + catalog")
    ap.add_argument("--check", action="store_true", help="compile the fragments offline")
    ap.add_argument("--dry-run", action="store_true", help="report only")
    ap.add_argument("--sample", type=int, default=0, help="print N sample fragments")
    ap.add_argument("--prune", action="store_true",
                    help="drop shipped defs that fail to compile, that scsynth "
                         "refuses to receive, or that bind no parameters")
    args = ap.parse_args()

    if args.prune:
        return prune_uncompilable()

    kept, dropped = plan()
    print(f"accepted={len(kept)} dropped={len(dropped)}")
    reasons: dict[str, int] = {}
    for _, why in dropped:
        reasons[why] = reasons.get(why, 0) + 1
    for why, n in sorted(reasons.items()):
        print(f"  dropped {n}: {why}")

    manifest = []
    for frag in kept:
        manifest.append({"def": frag["name"], "source": REPO_META[frag["source"]][0],
                         "gesture": frag["gesture"], "params": frag["params"]})

    # guard self-check
    bad = []
    for frag in kept:
        text = blank_comments(frag["fragment"])
        for s in GUARD_STRINGS:
            if text.count(s) != 1:
                bad.append((frag["name"], s, text.count(s)))
    print(f"guard self-check failures: {len(bad)}")
    for row in bad[:20]:
        print("   ", row)

    if args.sample:
        for frag in kept[:args.sample]:
            print("=" * 70)
            print(frag["fragment"])
        for name in ("pluck", "res", "sc303", "bass8", "dxkBd1", "sinfb"):
            for frag in kept:
                if frag["name"] == name:
                    print("=" * 70)
                    print(frag["fragment"])

    if args.check:
        return check(kept)

    if not args.write:
        print("(dry run — nothing written)")
        return 0

    if bad:
        print("refusing to write: guard self-check failed")
        return 1

    out_dir = SRC
    for frag in kept:
        (out_dir / f"{frag['name']}.scd").write_text(frag["fragment"])
    for rel, dest in LICENSE_COPY.values():
        src = COMMUNITY / rel
        if src.exists():
            shutil.copyfile(src, out_dir / dest)
            print(f"license copied: {dest}")

    catalog = json.loads(CATALOG.read_text())
    for entry in manifest:
        catalog["examples"][entry["def"]] = entry
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")

    names = list(catalog["examples"].keys())
    src = SC_PY.read_text()
    new_src, n = re.subn(r"_DEF_SCRIPTS = \(\n.*?\n\)\n",
                         def_scripts_block(names), src, count=1, flags=re.DOTALL)
    if n != 1:
        print("could not rewrite _DEF_SCRIPTS")
        return 1
    compile(new_src, str(SC_PY), "exec")  # syntax check before writing
    SC_PY.write_text(new_src)
    print(f"wrote {len(kept)} fragments, catalog.json ({len(names)} examples), sc.py")
    return 0


def shipped_names() -> list[str]:
    """The def names sc.py currently delivers, in catalog order."""
    block = re.search(r"_DEF_SCRIPTS = \(\n(.*?)\n\)\n", SC_PY.read_text(), re.DOTALL)
    if block is None:
        raise SystemExit("sc.py has no _DEF_SCRIPTS block")
    return [n[:-4] for n in re.findall(r'"([^"]+\.scd)"', block.group(1))]


def compile_shipped(names: list[str]) -> tuple[list[str], list[str]]:
    """Compile every shipped fragment in one sclang run.

    Returns (ok, failed).  The fragments are read from ``SRC`` exactly as the
    app reads them, and each is wrapped in ``d = { ... }.value;`` the way
    ``sc.ScServer.batch_source`` delivers it, so a def that compiles here is a
    def the app can /d_recv.  ``asBytes`` is what forces the compile.
    """
    tmp = Path("/home/rjodouin/.hermes/cache/scratch/section99_check")
    tmp.mkdir(parents=True, exist_ok=True)
    lines = ["var fail = 0;", "var bench = { |name|", "  var src, d;",
             f'  src = File.readAllString("{tmp}" ++ "/" ++ name ++ ".scd");',
             "  try {", '    d = ("{" ++ src ++ "\\n}.value").interpret;',
             '    d.asBytes;', '    ("OK\\t" ++ name).postln;',
             '  } { |e| fail = fail + 1; ("ERR\\t" ++ name).postln; };', "};"]
    for name in names:
        (tmp / f"{name}.scd").write_text((SRC / f"{name}.scd").read_text())
        lines.append(f'bench.("{name}");')
    lines += ['("FAILURES\\t" ++ fail).postln;', "0.exit;"]
    script = tmp / "shipped.scd"
    script.write_text("\n".join(lines))
    out = subprocess.run(["/usr/bin/sclang", str(script)],
                         capture_output=True, text=True, timeout=1800)
    done = [ln for ln in out.stdout.splitlines() if ln.startswith("OK\t")]
    errs = [ln.split("\t")[1] for ln in out.stdout.splitlines()
            if ln.startswith("ERR\t")]
    if not done and not errs:
        print(out.stdout[-2000:], out.stderr[-2000:])
    return [ln.split("\t")[1] for ln in done], errs


def drop_defs(bad: list[str], why: str) -> None:
    """Remove shipped defs from the catalog and ``sc.py``, and delete the file.

    Unlike a hand-authored def (which is *parked*: kept on disk, out of the
    catalog), a mechanically imported fragment is a build product. Re-clone the
    upstream sources in ``COMMUNITY`` and re-run this script to regenerate one.
    """
    catalog = json.loads(CATALOG.read_text())
    for n in bad:
        (SRC / f"{n}.scd").unlink(missing_ok=True)
        catalog["examples"].pop(n, None)
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")

    keep = list(catalog["examples"].keys())
    src = SC_PY.read_text()
    new_src, n = re.subn(r"_DEF_SCRIPTS = \(\n.*?\n\)\n",
                         def_scripts_block(keep), src, count=1, flags=re.DOTALL)
    if n != 1:
        print("could not rewrite _DEF_SCRIPTS")
        return
    compile(new_src, str(SC_PY), "exec")
    SC_PY.write_text(new_src)
    print(f"dropped {len(bad)} {why}; catalog.json + sc.py now list {len(keep)}")


def server_rejects(names: list[str], port: int = PROBE_PORT) -> list[str]:
    """Names scsynth itself refuses — sclang compiling is not enough.

    A def whose graph needs more interconnect buffers than scsynth has compiles
    happily in sclang and is then dropped by the server on ``/d_recv``
    (``exception in GraphDef_Recv: exceeded number of interconnect buffers``).
    The app notices only because ``numDefs`` never reaches the catalog size.

    Each probe gets a fresh server: that is what makes the ``numDefs`` check
    exact, since a server already holding the defs satisfies it immediately.
    """
    sys.path.insert(0, str(REPO / "src"))
    from super_quneo_collider.sc import ScServer

    ports = itertools.count(port)

    def refused(subset: list[str]) -> bool:
        s = ScServer(port=next(ports))
        if not s.boot():
            raise SystemExit("probe server failed to boot")
        try:
            s._def_scripts = [str(SRC / f"{n}.scd") for n in subset]
            s.load_defs(timeout=20.0)
            return (s.status() or {}).get("numDefs", 0) < len(subset)
        finally:
            s.stop()

    def walk(subset: list[str]) -> list[str]:
        if not subset or not refused(subset):
            return []
        if len(subset) == 1:
            return subset
        mid = len(subset) // 2
        return walk(subset[:mid]) + walk(subset[mid:])

    return walk(list(names))


def prune_uncompilable() -> int:
    """Drop shipped defs sclang cannot compile, then defs scsynth refuses.

    A fragment that fails to compile is worse than a missing one: the app
    delivers every def in a single sclang run, so one broken def aborts the
    batch and the instrument gets nothing at all.  A def the *server* refuses
    is the same story one step later — it also leaves ``load_defs`` short.
    """
    names = shipped_names()
    ok, bad = compile_shipped(names)
    print(f"shipped={len(names)} compiled={len(ok)} uncompilable={len(bad)}")
    for n in bad:
        print("  drop:", n)
    if bad:
        drop_defs(bad, "uncompilable defs")

    names = shipped_names()
    rejects = server_rejects(names)
    if rejects:
        if len(rejects) * 4 > len(names):
            print(f"refusing to drop {len(rejects)}/{len(names)}: "
                  "the server rejects a quarter of the catalog, so the probe "
                  "is more likely wrong than the defs")
            return 1
        for n in rejects:
            print("  server-rejected:", n)
        drop_defs(rejects, "server-rejected defs")

    catalog = json.loads(CATALOG.read_text())
    blank = [n for n, e in catalog["examples"].items() if not e.get("params")]
    if blank:
        for n in blank:
            print("  unplayable:", n)
        drop_defs(blank, "defs that bind nothing (§9.9.5)")
    if not bad and not rejects and not blank:
        print("nothing to prune")
    return 0


def check(kept: list[dict]) -> int:
    tmp = Path("/home/rjodouin/.hermes/cache/scratch/section99_check")
    tmp.mkdir(parents=True, exist_ok=True)
    lines = ['var fail = 0;', "var bench = { |name|", "  var src, d;",
             f'  src = File.readAllString("{tmp}" ++ "/" ++ name ++ ".scd");',
             "  try {", '    d = ("{ " ++ src ++ "\\n}").value;',
             '    d.asBytes;', '    ("OK\\t" ++ name).postln;',
             '  } { |e| fail = fail + 1; ("ERR\\t" ++ name ++ "\\t" ++ e).postln; };',
             "};"]
    for frag in kept:
        (tmp / f"{frag['name']}.scd").write_text(frag["fragment"])
        lines.append(f'bench.("{frag["name"]}");')
    lines.append('("FAILURES\\t" ++ fail).postln;')
    lines.append("0.exit;")
    script = tmp / "check.scd"
    script.write_text("\n".join(lines))
    out = subprocess.run(["/usr/bin/sclang", str(script)],
                         capture_output=True, text=True, timeout=1200)
    errs = [ln for ln in out.stdout.splitlines() if ln.startswith("ERR\t")]
    ok = sum(1 for ln in out.stdout.splitlines() if ln.startswith("OK\t"))
    print(f"compiled OK={ok} errors={len(errs)}")
    for ln in errs[:40]:
        print("  ", ln)
    if not errs and "FAILURES" not in out.stdout:
        print(out.stdout[-2000:])
        print(out.stderr[-2000:], file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
