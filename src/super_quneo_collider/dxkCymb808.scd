// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkCymb808", { arg out=0, t_trig=1, basefreq=205.35, len=0.25, sustain=0.5, att=0.001, pan=0, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var freqArray, sig1, sig2,env, sig1env, output, failsafe;
  freqArray = basefreq * [ 1, 1.4823959094229, 1.800048697346, 2.545458972486, 2.6322863403944, 3.9552471390309 ];
  sig2 = Pulse.ar(freqArray, 0.55, 0.9);
  sig2 = Mix.ar(sig2);
  sig1 = Pulse.ar(freqArray, 0.5);
  sig1 = Mix.ar(sig1);
  sig1 = ( BinaryOpUGen('==', sig1, 6) * 0.6) + ( BinaryOpUGen('==', sig1, 2)*0.2)+( BinaryOpUGen('==', sig1, 1)*0.9);
  sig1env = EnvGen.ar(Env([1.0, 1.0, 0.6], [att, len], -4), t_trig);
  env = EnvGen.ar(Env([1.0, 0.4, 0], [att, len, 0.05], -4), t_trig);
  output = sig1 + sig2;
  output = SOS.ar(output, 0.175812, 0.351623, 0.175812, 0.834059, -0.537305);
  output = SOS.ar(output, 0.669886, -1.33977, 0.669886, 0.968752, -0.710791);
  output = SOS.ar(output, 0.669886, -1.33977, 0.669886, 0.968752, -0.710791 );
  output = output * env;
  output = DelayN.ar(output, 0.005, 0.005);
  output = FreeVerb.ar(output, sustain);
  failsafe = FreeSelf.kr(Trig.kr(t_trig) * (amp <= 0));
  output = Pan2.ar(output*amp, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
