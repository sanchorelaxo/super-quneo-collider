// dxkSynthDefs/dxkSynthsMisc.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkSimpleFm", { arg out=0, freq=440, modharm=1, modidx=0.5, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  //harm = harmonicity ratio
  //modidx = modulation index
  var h, fm,  carrier, mod;
  var output;
  fm = freq * modharm;
  mod = SinOsc.ar(fm, mul: fm * modidx, add: freq);
  carrier = SinOsc.ar(mod, mul: amp);
  snd = carrier;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
