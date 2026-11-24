// synthdefs/synthdef-moogbass.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("moogbass", { arg out=0, freq=440, amp=0.1, attackTime=0.2, fenvamount=0.5, cutoff=1000, gain=2.0, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var osc, filter, env, filterenv;

  //alternative: richer source
  osc = Mix(Pulse.ar(freq.lag(0.05)*[1.0,1.001,2.0],Rand(0.45,0.5)!3,0.33));

  filterenv = EnvGen.ar(Env.adsr(attackTime,0.0,1.0,0.2),gate,doneAction: 0);
  filter =  MoogFF.ar(osc,cutoff*(1.0+(fenvamount*filterenv)),gain);

  // env = EnvGen.ar(Env.adsr(0.001,0.3,0.9,0.2),gate,doneAction:2);
  env = EnvGen.ar(Env.adsr(attackTime, \decayTime.kr(0.3), \sustainLevel.kr(0.9), \releaseTime.kr(0.2)),gate,doneAction: 0);
  snd = Pan2.ar((0.7*filter+(0.3*filter.distort))*env*amp,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
