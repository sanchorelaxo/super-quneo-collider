// tidal-synths/fmtribe.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("basicFM", { arg out=0, amp=1, carFreq=1000, modFreq=100, modAmount=2000, clipAmount=0.1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var modEnv = EnvGen.ar(Env.adsr(0.5, 0.5, 0.7, 0.1, peakLevel: modAmount), gate);
    var mod = SinOsc.ar(modFreq) * modEnv;
    var car = SinOsc.ar(carFreq + mod);
    var ampEnv = EnvGen.ar(Env.adsr(0.1, 0.3, 0.7, 0.2, peakLevel: amp), gate, doneAction: 0);
    var clip = clipAmount * 500;
  
  snd = (car * ampEnv * clip).clip(-0.7, 0.7) * 0.1;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
