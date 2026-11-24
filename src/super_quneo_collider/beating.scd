// Synthdefs/beating.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("beating", { arg out=0, freq=440, amp=0.1, art=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env, snd1, snd2;
  env = EnvGen.ar(Env.perc(0.01, art), doneAction: 0);
  snd1 = SinOsc.ar(freq);
  snd2 = SinOsc.ar(Line.kr(freq+15, freq, art));
  snd = Pan2.ar(Mix([snd1, snd2]), 0, amp*env);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
