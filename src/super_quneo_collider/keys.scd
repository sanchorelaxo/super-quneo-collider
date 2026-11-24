// tidal-synths/foxdot/keys.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("keys", { arg out=0, amp=1, sus=1, pan=0, freq=440, vib=0, fmod=0, rate=0, bus=0, cutoff=400, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var osc, env;    freq = [freq, freq+fmod];
    freq = freq * [1, 1.005];

    amp = amp / 4;

    osc = SinOsc.ar(freq + (rate * 100) * XFade2.ar(LFPar.ar(freq * (1/2)), LFTri.ar(freq * 1)), phase: 0.2, mul: 0.8);

    osc = RHPF.ar(osc, 400, 3);

    env = EnvGen.ar(Env([0, 1, 0.9, 0.5, 0],[0.01, 0, 0.5 * sus, 1 * sus]));

    osc = Mix(osc) * env * amp;

    osc = Pan2.ar(osc, pan);
  snd = osc;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
