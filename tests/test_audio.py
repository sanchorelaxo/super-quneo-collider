from super_quneo_collider.audio import route_supercollider


class FakeRun:
    def __init__(self, sink="", outs=(), ins=(), links=()):
        self.sink = sink
        self.outs = list(outs)
        self.ins = list(ins)
        self.links = list(links)
        self.calls = []

    def _links_output(self):
        # Faithful-ish `pw-link -l`: each port, then its outgoing/incoming
        # connections indented beneath it.
        lines = []
        for out, inp in self.links:
            lines.append(out)
            lines.append(f"  |-> {inp}")
            lines.append(inp)
            lines.append(f"  |<- {out}")
        return "\n".join(lines)

    def __call__(self, args):
        self.calls.append(list(args))
        cmd = args[0]
        if cmd == "pactl":
            return self.sink
        if cmd == "pw-link":
            if args[1] == "-o":
                return "\n".join(self.outs)
            if args[1] == "-i":
                return "\n".join(self.ins)
            if args[1] == "-l":
                return self._links_output()
            return ""  # -d and bare connect: no stdout to speak of
        return ""


def test_pairs_sc_outputs_with_sink_inputs():
    run = FakeRun(
        sink="bluez_output.FOO",
        outs=["SuperCollider:out_1", "SuperCollider:out_2", "SuperCollider:out_3"],
        ins=["bluez_output.FOO:playback_FL", "bluez_output.FOO:playback_FR"],
    )
    linked = route_supercollider(run)
    assert linked == [
        ("SuperCollider:out_1", "bluez_output.FOO:playback_FL"),
        ("SuperCollider:out_2", "bluez_output.FOO:playback_FR"),
    ]
    # the extra SuperCollider:out_3 has no sink channel and is dropped


def test_filters_other_clients_and_monitor_ports():
    run = FakeRun(
        sink="alsa_output.analog-stereo",
        outs=[
            "Rhythmbox:output_FL",
            "SuperCollider:out_1",
            "SuperCollider:out_2",
            "PulseAudio Volume Control:input_FL",
        ],
        ins=[
            "alsa_output.analog-stereo:monitor_FL",
            "alsa_output.analog-stereo:playback_FL",
            "alsa_output.analog-stereo:playback_FR",
            "bluez_output.OTHER:playback_FL",
        ],
    )
    linked = route_supercollider(run)
    assert linked == [
        ("SuperCollider:out_1", "alsa_output.analog-stereo:playback_FL"),
        ("SuperCollider:out_2", "alsa_output.analog-stereo:playback_FR"),
    ]


def test_no_default_sink_returns_empty():
    run = FakeRun(sink="", outs=["SuperCollider:out_1"], ins=[])
    assert route_supercollider(run) == []


def test_no_supercollider_ports_returns_empty():
    run = FakeRun(sink="sink.name", outs=[], ins=["sink.name:playback_FL"])
    assert route_supercollider(run) == []


def test_disconnects_stale_links_when_the_default_moves():
    # The default sink changed (Bluetooth paired after boot): the old link to
    # the stale sink must be dropped and a fresh one to the new default made.
    run = FakeRun(
        sink="new.sink",
        outs=["SuperCollider:out_1", "SuperCollider:out_2"],
        ins=["new.sink:playback_FL", "new.sink:playback_FR"],
        links=[
            ("SuperCollider:out_1", "old.sink:playback_FL"),
            ("SuperCollider:out_2", "old.sink:playback_FR"),
        ],
    )
    linked = route_supercollider(run)
    assert linked == [
        ("SuperCollider:out_1", "new.sink:playback_FL"),
        ("SuperCollider:out_2", "new.sink:playback_FR"),
    ]
    assert ["pw-link", "-d", "SuperCollider:out_1", "old.sink:playback_FL"] in run.calls
    assert ["pw-link", "-d", "SuperCollider:out_2", "old.sink:playback_FR"] in run.calls
    assert ["pw-link", "SuperCollider:out_1", "new.sink:playback_FL"] in run.calls
    assert ["pw-link", "SuperCollider:out_2", "new.sink:playback_FR"] in run.calls


def test_re_routing_is_idempotent_when_the_sink_is_unchanged():
    # Re-running against the same default must not churn the graph: no unlink,
    # no relink, just the read-only discovery (get-default-sink, -o, -i, -l).
    run = FakeRun(
        sink="sink.name",
        outs=["SuperCollider:out_1", "SuperCollider:out_2"],
        ins=["sink.name:playback_FL", "sink.name:playback_FR"],
        links=[
            ("SuperCollider:out_1", "sink.name:playback_FL"),
            ("SuperCollider:out_2", "sink.name:playback_FR"),
        ],
    )
    linked = route_supercollider(run)
    assert linked == [
        ("SuperCollider:out_1", "sink.name:playback_FL"),
        ("SuperCollider:out_2", "sink.name:playback_FR"),
    ]
    assert all(
        c[0] == "pactl" or (c[0] == "pw-link" and c[1] in ("-o", "-i", "-l"))
        for c in run.calls
    )