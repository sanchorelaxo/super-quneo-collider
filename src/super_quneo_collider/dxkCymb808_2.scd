// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkCymb808_2", { arg out=0, t_trig=1, basefreq=300, len=0.25, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var freqs = basefreq * [ 1, 1.4823959094229, 1.800048697346, 2.545458972486, 2.6322863403944, 3.9552471390309 ];
  var signal, pulseEnv;

  pulseEnv = EnvGen.ar(Env([1.0, 0.6], [len], [-0.5]), t_trig);
  signal = Mix.new(LFPulse.ar(freqs * 4.09));
  signal = (BinaryOpUGen('==', signal, 6.0) * 0.6) + (BinaryOpUGen('==', signal, 2.0) * 0.2) + (BinaryOpUGen('==', signal, 1.0) * 0.9); // XOR
  signal = (signal * pulseEnv) + (Mix.new(LFPulse.ar(freqs, width:0.55)) * 0.9);
  signal = RLPF.ar(signal, 7000, 0.6);
  signal = RHPF.ar(signal, 6800, 1.5);
  signal = RHPF.ar(signal, 6800, 1.5);
  signal = RHPF.ar(signal, 1200, 1.5);
  signal = signal + FreeVerb.ar(signal);
  signal = signal * EnvGen.ar(Env([0, 1, 0.4, 0, 0], [0.002, len, 0.05, 0.5], [0, -0.5, 0, -50]), t_trig, doneAction: 0);
  signal = [signal, DelayN.ar(signal, 0.005, 0.005)];
  signal = Pan2.ar(signal, pan, amp * 0.4);
  snd = signal;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
