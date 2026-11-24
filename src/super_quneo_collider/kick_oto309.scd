// Synthdefs/kick_oto309.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("kick_oto309", { arg out=0, amp=0.5, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  var env0, env1, env1m, son;

  env0 =  EnvGen.ar(Env.new([0.5, 1, 0.5, 0], [0.005, 0.06, 0.26], [-4, -2, -4]), doneAction: 0);
  env1 = EnvGen.ar(Env.new([110, 59, 29], [0.005, 0.29], [-4, -5]));
  env1m = env1.midicps;

  son = LFPulse.ar(env1m, 0, 0.5, 1, -0.5);
  son = son + WhiteNoise.ar(1);
  son = LPF.ar(son, env1m*1.5, env0);
  son = son + SinOsc.ar(env1m, 0.5, env0);

  son = son * 1.2;
  son = son.clip2(1);
  snd = Pan2.ar(son * amp);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
