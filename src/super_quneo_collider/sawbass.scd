// tidal-synths/foxdot/sawbass.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("sawbass", { arg out=0, amp=1, sus=0.2, pan=0, bus=0, freq=440, cutoff=1000, rq=0.5, drive=2.0, fmod=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var osc1, osc2, filter, filter2, env, filterenv, ab;
    amp = amp * 0.2;
    freq = (freq / 4) + fmod;
    osc1 = Saw.ar(freq);
    osc2 = Mix(Saw.ar(freq * [0.25,1,1.5], [0.5,0.4,0.1]));
    filterenv = EnvGen.ar(Env.adsr(0.0, 0.5, 0.2, sus), 1, doneAction: 0);
    filter =  RLPF.ar(osc1 + osc2, cutoff * filterenv + 100, rq);
    ab = abs(filter);
    filter2 = (filter * (ab + drive) / (filter ** 2 + (drive - 1) * ab + 1));
    filter2 = BLowShelf.ar(filter2, 300, 1.0, -12);
    filter2 = BPeakEQ.ar(filter2, 1600, 1.0, -6);
    //env = EnvGen.ar(Env.adsr(0.01, 0.0, sus / 2, 0.05), 1, doneAction:3);
    env = EnvGen.ar(Env([0,1,0.8,0.8,0], [0.01, 0, sus, 0.05]), doneAction:3);
  snd = Pan2.ar((filter + filter2) * env * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
