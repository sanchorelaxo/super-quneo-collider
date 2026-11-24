// Synthdefs/clap_oto309.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("clap_oto309", { arg out=0, amp=0.1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  var env1, env2, son, noise1, noise2;

  env1 = EnvGen.ar(Env.new([0, 1, 0, 1, 0, 1, 0, 1, 0], [0.001, 0.013, 0, 0.01, 0, 0.01, 0, 0.03], [0, -3, 0, -3, 0, -3, 0, -4]));
  env2 = EnvGen.ar(Env.new([0, 1, 0], [0.02, 0.3], [0, -4]), doneAction: 0);

  noise1 = WhiteNoise.ar(env1);
  noise1 = HPF.ar(noise1, 600);
  noise1 = BPF.ar(noise1, 2000, 3);

  noise2 = WhiteNoise.ar(env2);
  noise2 = HPF.ar(noise2, 1000);
  noise2 = BPF.ar(noise2, 1200, 0.7, 0.7);

  son = noise1 + noise2;
  son = son * 2;
  son = son.softclip * amp;
  snd = Pan2.ar(son, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
