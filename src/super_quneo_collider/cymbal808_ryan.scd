// Synthdefs/cymbal808_ryan.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("cymbal808_ryan", { arg out=0, baseFreq=300, time=250, amp=0.1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  //var freqs = [baseFreq, baseFreq*1.3420, baseFreq*1.2312, baseFreq*1.6532, baseFreq*1.9523, baseFreq*2.1523];
  //var freqs = [78.6, 140.44, 123.87, 219.4, 787.5, 531.3];
  //var freqs = [205.35, 254.29, 294.03, 304.41, 369.64, 522.71];
  var freqs = [205.35, 304.41, 369.64, 522.71, 540.54, 812.21];
  var signal, pulseEnv;

  pulseEnv = EnvGen.ar(Env.new([1.0, 0.6], [time], [-0.5]), timeScale:(1/1000));
  signal = Mix.new(LFPulse.ar(freqs * 4.09));
  signal = (BinaryOpUGen('==', signal, 6.0) * 0.6) + (BinaryOpUGen('==', signal, 2.0) * 0.2) + (BinaryOpUGen('==', signal, 1.0) * 0.9); // XOR
��  signal = (signal * pulseEnv) + (Mix.new(LFPulse.ar(freqs, width:0.55)) * 0.9);
� signal = RLPF.ar(signal, 7000, 0.6);
�   signal = RHPF.ar(signal, 6800, 1.5);
� signal = RHPF.ar(signal, 6800, 1.5);
� signal = RHPF.ar(signal, 1200, 1.5);
  signal = signal + FreeVerb.ar(signal);
  signal = signal * EnvGen.ar(Env.new([0, 1, 0.4, 0, 0], [2, time, 50, 500], [0, -0.5, 0, -50]), timeScale:(1/1000), doneAction: 0);
  signal = [signal, DelayN.ar(signal, 0.005, 0.005)];
  snd = signal*4*amp;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
