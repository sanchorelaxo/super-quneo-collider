// dxkSynthDefs/dxkPitched.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkSawIter", { arg out=0, freq=440, att=0.01, dec=0.3, sus=0.5, rel=1, pan=0, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var temp,sum, env, n_saw = 10;
  sum = 0;
  env = EnvGen.ar(Env.adsr(att, dec, sus, rel), gate, doneAction: 0);
  n_saw.do{|count|
    temp = SinOsc.ar(freq
      * (count+1)
      * LFNoise1.kr({Rand(0.05, 0.2)}).range(0.98, 1.02)
    );
    sum = sum + temp;
  };
  sum = sum * n_saw.reciprocal;
  sum = Pan2.ar(sum*env*amp, pan);
  snd = sum;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
