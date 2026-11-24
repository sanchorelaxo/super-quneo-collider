// Synthdefs/harpsichord.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("harpsichord1", { arg out=0, freq=440, amp=0.1, pan=0, gate=1, fade=1;
  var stopFade, fadeEnv;
 
    var env, snd;
  env = Env.perc(level: amp).kr(doneAction: 0);
  snd = Pulse.ar(freq, 0.25, 0.75);
  snd = snd * env;
  snd = Pan2.ar(snd, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
