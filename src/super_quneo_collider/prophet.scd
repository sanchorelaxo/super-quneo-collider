// tidal-synths/foxdot/prophet.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("prophet", { arg out=0, bus=0, freq=440, amp=1.0, lforate=1, lfowidth=0.5, cutoff=6000, rq=0.4, pan=0.0, sus=0.1, fmod=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var lfo, pulse, filter, env;
    // Amp is way too much for foxdot
    amp = amp * 0.1;

    freq = freq + [0, fmod];

    lfo = LFTri.kr(lforate * [1, 1.01], Rand(0, 2.0)!2);

    pulse = Pulse.ar(freq * [1, 1.01], lfo * lfowidth + 0.5);

    filter = RLPF.ar(pulse, cutoff, rq);

    filter = BHiPass.ar(filter, 200);

    env = EnvGen.ar(Env([0,1,0.8,0.8,0], [0.01, 0, sus, sus]), doneAction:3);
  snd = Pan2.ar(Mix(filter) * env * amp * 0.5, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
