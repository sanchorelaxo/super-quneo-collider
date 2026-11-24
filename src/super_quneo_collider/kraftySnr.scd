// Synthdefs/kraftsnr.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("kraftySnr", { arg out=0, amp=1, freq=2000, rq=3, decay=0.3, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
  var sig = PinkNoise.ar(amp),
  env = EnvGen.kr(Env.perc(0.01, decay), doneAction: 0);
  sig = BPF.ar(sig, freq, rq, env);
  snd = Pan2.ar(sig, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
