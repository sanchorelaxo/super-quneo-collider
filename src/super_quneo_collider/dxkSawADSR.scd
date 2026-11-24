// dxkSynthDefs/dxkSimpleOsc.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkSawADSR", { arg out=0, freq=440, amp=1, pan=0, att=0.01, decay=0.3, sus=0.5, rel=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sig,env;
  env = EnvGen.ar(Env.adsr(att,decay,sus,rel),gate, doneAction: 0);
  sig = Saw.ar(freq, amp);
  sig = Pan2.ar(sig, pan);
  
  snd = sig*env;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
