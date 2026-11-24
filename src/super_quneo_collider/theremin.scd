// synthdefs/synthdef-theremin.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("theremin", { arg out=0, mod=7, detune=0, freq=440, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
  var f, a, z, env;
  a = SinOsc.ar(freq + (freq * SinOsc.ar(mod,0,0.02)), mul: amp);
  z = Mix.ar(a);

  env = EnvGen.ar(Env.linen(\attackTime.kr(0.05), \sustainTime.kr(0.9), \releaseTime.kr(0.05)),gate,doneAction: 0);
  snd = Pan2.ar(z * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
