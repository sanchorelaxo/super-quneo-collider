// Synthdefs/goeysynth.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("goeysynth", { arg out=0, freq=440, amp=0.1, sustain=0.1, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
var source, env;

source= LPF.ar(Mix(LFPar.ar(freq*[0.999,1.001],0,amp)).distort,EnvGen.kr(Env([10000,2000,4000,1000],[0.005,Rand(0.009,0.05),0.005])));

env= EnvGen.kr(Env([0,1,0.4,0.7,0],[Rand(0.001,0.005),0.005,0.005,sustain]), doneAction: 0);
  snd = Pan2.ar(source*env,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
