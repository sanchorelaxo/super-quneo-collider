// dxkSynthDefs/dxkSynthsMisc.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkWNoizBPFASR", { arg out=0, freq=440, rq=0.1, att=0.001, rel=0.001, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env, output, noise;
  noise = WhiteNoise.ar();
  env = EnvGen.ar(Env.asr(att, 1, rel), gate, doneAction: 0);
  output = BPF.ar(noise, freq, rq, amp);
  output = output * env;
  output = Pan2.ar(output, pan); 
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
