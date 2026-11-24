// tidal-synths/foxdot/piano.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("piano", { arg out=0, vib=0, rate=0, sus=1, fmod=0, bus=0, amp=1, freq=440, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
var osc, env;freq = [freq, freq+fmod];
amp=(amp * 0.7);
osc=MdaPiano.ar((freq[0]), vel: (40 + (amp * 60)), decay: (sus / 4));
env=EnvGen.ar(Env(levels: [(amp * 1), (amp * 1)],curve: 'step',times: [sus]), doneAction: 0);
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
