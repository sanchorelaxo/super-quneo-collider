"""The one write the bridge makes to the QuNeo: blanking the board.

Reads travel through the ALSA sequencer (see test_midi). This is the write
side: a 17-byte preset-reload SysEx over the rawmidi port. A sweep of remote
note-off / CC=0 messages cannot clear the board's locally driven LEDs (the
rotaries and the long slider stay lit), so reloading the preset is the only
command that truly darkens every light.

Nothing here may spawn a real subprocess: both the runner and the ``amidi -l``
listing are injected. The reference frames are the output of queneo-editor's
``build_reload_preset_command`` (captured live, then confirmed on the board).
"""
from __future__ import annotations

import subprocess

import pytest

from super_quneo_collider import board

# Live `amidi -l` on the machine that runs the bridge.
AMIDI_LISTING = """Dir Device    Name
IO  hw:2,0,0  QuNeo MIDI 1
"""

AMIDI_LISTING_WITH_OTHERS = """Dir Device    Name
IO  hw:0,0,0  HDA Intel PCH: ALC295 Analog
IO  hw:2,0,0  QuNeo MIDI 1
IO  hw:3,0,0  Loopback MIDI
"""

AMIDI_LISTING_WITHOUT_QUNEO = """Dir Device    Name
IO  hw:0,0,0  HDA Intel PCH: ALC295 Analog
"""

# Slots 0, 1, 2 and 15 straight out of the reference encoder.
REFERENCE_FRAMES = {
    0: "f0 00 01 5f 7a 1e 00 01 00 02 30 00 6f 35 00 10 f7",
    1: "f0 00 01 5f 7a 1e 00 01 00 02 30 01 7f 14 00 10 f7",
    2: "f0 00 01 5f 7a 1e 00 01 00 02 30 02 4f 77 00 10 f7",
    15: "f0 00 01 5f 7a 1e 00 01 00 02 30 0f 1e 5a 00 20 f7",
}


class FakeRun:
    """Stand-in for ``subprocess.run``: records argv, answers ``amidi -l``."""

    def __init__(self, listing=AMIDI_LISTING, returncode=0, raises=None):
        self.listing = listing
        self.returncode = returncode
        self.raises = raises
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if self.raises is not None:
            raise self.raises
        stdout = self.listing if list(argv[:2]) == ["amidi", "-l"] else ""
        return subprocess.CompletedProcess(argv, self.returncode, stdout, "")


def sends(fake):
    """Only the ``amidi -p <port> -S <hex>`` invocations, not the listing."""
    return [argv for argv in fake.calls if argv[:2] == ["amidi", "-p"]]


class TestReloadFrame:
    def test_slot_zero_matches_the_validated_command(self):
        assert board.reload_frame(0).hex(" ") == REFERENCE_FRAMES[0]

    @pytest.mark.parametrize("slot", sorted(REFERENCE_FRAMES))
    def test_matches_the_reference_encoder(self, slot):
        assert board.reload_frame(slot).hex(" ") == REFERENCE_FRAMES[slot]

    def test_defaults_to_the_slot_the_bridge_is_bound_to(self):
        assert board.reload_frame().hex(" ") == board.reload_frame(board.RELOAD_PRESET_SLOT).hex(" ")

    def test_is_a_17_byte_sysex_frame(self):
        frame = board.reload_frame(0)
        assert len(frame) == 17
        assert frame[0] == 0xF0
        assert frame[-1] == 0xF7

    def test_every_byte_between_the_delimiters_is_seven_bit(self):
        # The board reads 7-bit data; 0x80+ here would mean a broken encoder.
        assert all(byte < 0x80 for byte in board.reload_frame(7)[1:-1])

    def test_rejects_a_slot_the_board_does_not_have(self):
        with pytest.raises(ValueError):
            board.reload_frame(16)
        with pytest.raises(ValueError):
            board.reload_frame(-1)


class TestPortDiscovery:
    def test_reads_the_rawmidi_port_from_amidi(self):
        assert board.find_rawmidi_port(listing=AMIDI_LISTING) == "hw:2,0,0"

    def test_picks_the_queneo_out_of_a_busy_device_list(self):
        assert board.find_rawmidi_port(listing=AMIDI_LISTING_WITH_OTHERS) == "hw:2,0,0"

    def test_returns_none_without_a_queneo(self):
        assert board.find_rawmidi_port(listing=AMIDI_LISTING_WITHOUT_QUNEO) is None

    def test_asks_amidi_when_no_listing_is_given(self):
        fake = FakeRun()
        assert board.find_rawmidi_port(run=fake) == "hw:2,0,0"
        assert fake.calls == [["amidi", "-l"]]

    def test_survives_amidi_being_absent(self):
        assert board.find_rawmidi_port(run=FakeRun(raises=FileNotFoundError())) is None


class TestDarken:
    def test_sends_the_reload_frame_to_the_board(self):
        fake = FakeRun()
        assert board.darken(run=fake) is True
        argv = sends(fake)[0]
        assert argv[:4] == ["amidi", "-p", "hw:2,0,0", "-S"]
        assert argv[4] == board.reload_frame(board.RELOAD_PRESET_SLOT).hex(" ")

    def test_sends_exactly_one_message(self):
        fake = FakeRun()
        board.darken(run=fake)
        assert len(sends(fake)) == 1

    def test_takes_an_explicit_port_without_listing(self):
        fake = FakeRun()
        assert board.darken(port="hw:5,0,0", run=fake) is True
        assert sends(fake)[0][2] == "hw:5,0,0"
        assert ["amidi", "-l"] not in fake.calls

    def test_reports_failure_when_there_is_no_board(self):
        fake = FakeRun(listing=AMIDI_LISTING_WITHOUT_QUNEO)
        assert board.darken(run=fake) is False
        assert sends(fake) == []

    def test_reports_failure_when_amidi_fails(self):
        assert board.darken(run=FakeRun(returncode=1)) is False

    def test_reports_failure_when_amidi_is_missing(self):
        assert board.darken(run=FakeRun(raises=FileNotFoundError())) is False
