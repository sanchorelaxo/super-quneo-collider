// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkGong1", { arg out=0, t_trig=1, freq=100, amp=1, dr=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var modsig, modf = freq * [1.16, 3.14, 1.005];
  var idx = [[0.01, 0.3],[0.01,0.38], [0.01, 0.5]] * modf;
  var idxscaler = Array.fill(idx.size, {|i| idx[i][1] - idx[i][0]});
  var modenv = Array.newClear(modf.size);
  var ampenv, carsig, lfo, output;

  lfo = SinOsc.ar(3, 0, XLine.kr(freq*0.005, freq*0.05, dr));

  modenv[0] = EnvGen.kr(
    Env(levels: [0,1,1,0], times: [0.75*dr, 0.24*dr, 0.01*dr]), t_trig,
    doneAction: 0);

  modenv[1] = EnvGen.kr(
    Env(levels: [0,1,0], times: [0.02*dr, 0.98*dr]), t_trig,
    doneAction: 0);

  modenv[2] = EnvGen.kr(
    Env(levels: [ 0, 0.3, 1, 0.5, 0], times: [0.15 * dr, 0.15 *dr, 0.45*dr, 0.25*dr]), t_trig,
    doneAction: 0);

  // Exp curve...
  ampenv = EnvGen.kr(
    Env(levels: [ 0, 1, 0.001], times: [0.002, dr - 0.002], curve: \exp), t_trig,
    doneAction: 0);

  modsig = Mix.new(SinOsc.ar(modf) * ((idx + idxscaler)*modenv));
  carsig = SinOsc.ar(freq + lfo + modsig)*modf.size.reciprocal;
  output = carsig * ampenv * amp;
  output = Pan2.ar(output, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
