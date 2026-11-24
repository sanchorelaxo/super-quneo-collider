// Synthdefs/drumkit1.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("snare", { arg out=0, amp=0.1, sinfreq=180, att=0.01, rel=0.2, ffreq=2000, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var snd1 = WhiteNoise.ar(amp);
  var snd2 = SinOsc.ar(sinfreq,0,amp);
  var env = EnvGen.kr(Env.perc(att, rel), doneAction: 0);
  var sum = HPF.ar(snd1 * env, ffreq)+(snd2*env);
  snd = Pan2.ar(sum, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
