// Synthdefs/bass.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("bassfoundation", { arg out=0, freq=440, amp=0.1, cutoff=1000, rq=0.5, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var osc, filter, env, filterenv;

  osc = Saw.ar(freq);

  filterenv = EnvGen.ar(Env.adsr(0.0,0.5,0.2,0.2),gate,doneAction: 0);
  filter =  RLPF.ar(osc,cutoff*filterenv+100,rq);

  env = EnvGen.ar(Env.adsr(0.01,0.0,0.9,0.05),gate,doneAction: 0);
  snd = Pan2.ar(filter*env*amp*2,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
