// Synthdefs/kick_chrp.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("kick_chrp", { arg out=0, amp=0.1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 

var ampenv, pitchenv;

ampenv   = EnvGen.ar(Env.perc(0, 0.2, curve: 0), doneAction: 0);
pitchenv = EnvGen.ar(Env.perc(0, 0.1, curve: -20).exprange(0, 1000), doneAction: 0);
  snd = Pan2.ar(SinOsc.ar(pitchenv) * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
