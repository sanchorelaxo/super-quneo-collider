from super_quneo_collider.audio import route_supercollider


class FakeRun:
    def __init__(self, sink="", outs=(), ins=()):
        self.sink = sink
        self.outs = list(outs)
        self.ins = list(ins)
        self.calls = []

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
            return ""
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
