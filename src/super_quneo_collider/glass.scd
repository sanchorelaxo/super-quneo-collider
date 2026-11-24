// tidal-synths/foxdot/glass.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("glass", { arg out=0, vib=0, rate=0, sus=1, fmod=0, bus=0, amp=1, freq=440, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
var osc, env;freq = [freq, freq+fmod];
sus=(sus * 1.5);
amp=(amp * 1.5);
freq=(freq * [1, (1 + (0.005 * rate))]);
osc=Klank.ar(`[[2, 4, 9, 16], [1, 1, 1, 1], [2, 2, 2, 2]], (PinkNoise.ar(0.0005).dup * SinOsc.ar((freq / 4), mul: 0.5, add: 1)), freq);
env=EnvGen.ar(Env(levels: [0, amp, 0],curve: 'lin',times: (sus * 2)), doneAction: 0);
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
