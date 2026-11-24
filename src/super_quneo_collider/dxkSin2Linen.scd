// dxkSynthDefs/dxkSimpleOsc.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkSin2Linen", { arg out=0, freq=440, detune=0.01, amp=1, pan=0, att=0.01, rel=1, sus=1, curve=\lin, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sig,env;
  env = EnvGen.ar(Env.linen(att,sus,rel,1,curve),gate, doneAction: 0);
  sig = SinOsc.ar([freq,freq*(1+detune)], 0, amp);
  sig = Mix.new(sig);
  sig = Pan2.ar(sig, pan);
  
  snd = sig*env;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
