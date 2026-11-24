// tidal-synths/foxdot/dbass.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dbass", { arg out=0, amp=1, sus=1, pan=0, freq=440, vib=0, fmod=0, rate=0, bus=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var osc, env;    freq = [freq, freq+fmod] * Line.ar(Rand(0.5,1.5),1,0.02);
    freq=(freq / 4);
    amp=(amp * 0.8);
    osc=( VarSaw.ar(freq, width: LFTri.ar((0.5 * rate)/sus, iphase:0.9, add:0.8, mul: 0.2), mul: amp));
    env=EnvGen.ar(Env([0,1,0.8,0.8,0], [0.02, 0.01, sus/2, sus/2]), doneAction: 0);
    osc=(osc * env);
    osc = Mix(osc) * 0.5;
    osc = Pan2.ar(osc, pan);
  snd = osc;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
