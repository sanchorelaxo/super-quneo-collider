// Synthdefs/forest_bird_pj.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("forest_bird_pj", { arg out=0, amp=0.1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;

  snd = Pan2.ar(
    BPF.ar(BrownNoise.ar,SinOsc.kr(LFNoise2.kr(50,50,50),0,100,2000),0.001,10)
    * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
