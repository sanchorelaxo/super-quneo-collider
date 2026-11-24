// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkHh1", { arg out=0, t_trig=1, basefreq=40, att=0.001, len=0.1, rq=0.1, hpfreq=7000, lopfreq=10000, pan=0, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var freqarr, output, env;
  freqarr = basefreq * [2,3,4.16, 5.43, 6.79,8.21];
  output = Mix.ar(Pulse.ar(freqarr, mul:1/freqarr.size));
  output = BPF.ar(output, 10000, rq);
  output = RHPF.ar(output, 7000, rq);
  env = EnvGen.ar(Env.perc(att, len, amp), t_trig, doneAction: 0);
  output = output *env;
  output = Pan2.ar(output, pan);
  snd = output * (amp * 3);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
