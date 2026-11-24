// dxkSynthDefs/dxkSynthsMisc.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkDtmf", { arg out=0, number=0, mul=1, pan=0, att=0.001, decay=0.001, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var output, env, freqarr, freqs;
  //A = 10, B = 11, C = 12, D = 13, * =14, E = 15
  // freq pairs
  freqarr = [[941, 1336], [697, 1209], [697, 1336], [697, 1477],
    [770, 1209], [770, 1336], [770, 1477],
    [852, 1209], [852, 1336], [852, 1477],
    [697, 1633], [770, 1633], [852, 1633],
    [941, 1633], [941, 1209], [941, 1477]];
  
  freqs = Select.kr(number, freqarr);
  output = SinOsc.ar(freqs, 0, mul);
  output = Mix.new(output)*0.5;
  env = EnvGen.ar(Env.asr(att, 1, decay), gate, doneAction: 0);
  output = output * env;
  output = Pan2.ar(output, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
