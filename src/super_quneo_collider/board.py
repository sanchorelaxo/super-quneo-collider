"""The one write the bridge makes to the QuNeo: blanking the board.

Everything else in this package reads the board through the ALSA sequencer
(see :mod:`super_quneo_collider.midi`). This is the write side, and it exists
because a sweep of remote note-off / CC=0 messages is not enough to darken the
board: the rotaries and the long slider are lit from the board's own memory,
so they survive any number of remote messages. Re-sending the preset-load
message re-initialises that memory and clears every LED at once.

Two properties make the reload safe to fire while the bridge is running:

* it emits no CC and no note, so the state the bridge mirrors from the same
  device cannot be polluted by its own reset (one identity SysEx comes back);
* it is idempotent, so boot, page load and the reset button can all call it.

The address is an ALSA rawmidi port name (``hw:2,0,0``) resolved from
``amidi -l``, which keeps this dependency-free: ``amidi`` ships with alsa-utils
and is already the package's ALSA tool of choice.

Loading a preset also re-selects it, and the board flashes pad ``slot + 1`` as
its "preset loaded" tell. Slot 0 is therefore the preset the bridge maps
(BasicSC) and the one a reset reloads.
"""
from __future__ import annotations

import re
import subprocess

# SysEx delimiters, manufacturer and product identity of the QuNeo.
SYSEX_START = 0xF0
SYSEX_END = 0xF7
PACKET_START = 0x01
MANUFACTURER_ID = (0x00, 0x01, 0x5F)  # Keith McMillen Instruments
PRODUCT_CODE = (0x7A, 0x1E, 0x00)  # QuNeo
PREAMBLE = (0x00, 0x02)
LOAD_PRESET = 0x30  # opcode, followed by the preset slot
MAX_SLOT = 15

# The preset the bridge is bound to, and the one a reset reloads.
RELOAD_PRESET_SLOT = 0

# A port name in `amidi -l` output, e.g. "hw:2,0,0".
_PORT_RE = re.compile(r"\b(hw:\d+,\d+,\d+)\b")
_DEVICE_NAME = "QuNeo"


class _ChunkedEncoder:
    """The QuNeo's 7-bit chunked SysEx writer.

    A byte-for-byte port of queneo-editor's ``SyxEncoder`` (test_board pins the
    reference frames it produces). Two details are the board's, not a textbook
    SysEx encoder's: every eighth byte carries the high bits of the seven
    before it, so an 0x80 data byte escapes the status range; and the CRC is
    folded into the stream it is checksumming, which is why the CRC is read
    once and then emitted.
    """

    GROUP = 7

    def __init__(self) -> None:
        self.buf = bytearray()
        self.reset()

    def reset(self) -> None:
        """Start a packet body: fresh CRC and a fresh 7-byte group."""
        self.crc = 0xFFFF
        self._hi = 0
        self._hi_count = 0

    def raw(self, value: int) -> None:
        """Append a byte verbatim (delimiters and identity only)."""
        self.buf.append(value & 0xFF)

    def _write(self, value: int) -> None:
        self.buf.append(value & 0x7F)

    def encode(self, value: int) -> None:
        self._write(value & 0x7F)
        self._hi |= value & 0x80
        self._hi >>= 1
        self._hi_count += 1
        if self._hi_count == self.GROUP:
            self._hi_count = 0
            self._write(self._hi)

    def crc_byte(self, value: int) -> None:
        value &= 0xFF
        crc = (self.crc << 8) & 0xFFFF
        temp = (self.crc >> 8) ^ value
        quick = (temp ^ (temp >> 4)) & 0xFFFF
        crc ^= quick
        quick = (quick << 5) & 0xFFFF
        crc ^= quick
        quick = (quick << 7) & 0xFFFF
        self.crc = (crc ^ quick) & 0xFFFF

    def encode_crc(self, value: int) -> None:
        self.crc_byte(value)
        self.encode(value)

    def encode_crc_int(self) -> None:
        """Emit the CRC so far, as the two bytes the board expects."""
        value = self.crc
        self.encode_crc((value >> 8) & 0xFF)
        self.encode_crc(value & 0xFF)

    def flush(self) -> None:
        """Pad the open group with zeroes so its high-bit trailer lands."""
        while self._hi_count:
            self.encode_crc(0)


def reload_frame(slot: int = RELOAD_PRESET_SLOT) -> bytes:
    """The preset-load SysEx for ``slot``: the command that blanks the board."""
    slot = int(slot)
    if not 0 <= slot <= MAX_SLOT:
        raise ValueError(f"preset slot out of range 0..{MAX_SLOT}: {slot}")
    encoder = _ChunkedEncoder()
    encoder.raw(SYSEX_START)
    for byte in MANUFACTURER_ID + PRODUCT_CODE:
        encoder.raw(byte)
    encoder.raw(PACKET_START)
    encoder.reset()
    for byte in PREAMBLE + (LOAD_PRESET, slot):
        encoder.encode_crc(byte)
    encoder.encode_crc_int()
    encoder.flush()
    encoder.raw(SYSEX_END)
    return bytes(encoder.buf)


def _amidi(argv: list[str], run=None):
    """Run ``amidi``; ``None`` if the tool is not installed after all."""
    runner = run or subprocess.run
    try:
        return runner(argv, capture_output=True, text=True, check=False)
    except OSError:
        return None


def _parse_port(listing: str) -> str | None:
    for line in listing.splitlines():
        if _DEVICE_NAME in line:
            match = _PORT_RE.search(line)
            if match:
                return match.group(1)
    return None


def find_rawmidi_port(listing: str | None = None, run=None) -> str | None:
    """The port to write to, e.g. ``hw:2,0,0``; ``None`` without a board.

    Pass ``listing`` (the text of ``amidi -l``) to parse a captured listing;
    otherwise ``amidi`` is asked.
    """
    if listing is None:
        done = _amidi(["amidi", "-l"], run)
        if done is None or done.returncode != 0 or not done.stdout:
            return None
        listing = done.stdout
    return _parse_port(listing)


def darken(port: str | None = None, slot: int = RELOAD_PRESET_SLOT, run=None) -> bool:
    """Reload ``slot`` on the board, clearing every LED.

    Returns True only when the message was handed to a working ``amidi``: the
    caller decides what to do about a board that is not there.
    """
    if port is None:
        port = find_rawmidi_port(run=run)
    if port is None:
        return False
    frame = reload_frame(slot)
    done = _amidi(["amidi", "-p", port, "-S", frame.hex(" ")], run)
    return done is not None and done.returncode == 0
