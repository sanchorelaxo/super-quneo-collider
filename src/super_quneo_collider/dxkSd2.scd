// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkSd2", { arg out=0, t_trig=1, basefreq=180, freq1amp=0.75, freq2amp=1, lopfreq=1000, hipfreq=950, lopamp=0.5, hipamp=1, att=0.001, len=0.1, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var oscs, oenv1, oenv2, noise, lonoise, loenv, hinoise, hienv, output;
  oscs = SinOsc.ar([basefreq, basefreq*1.83], 0, [0.75, 1]);
  oenv1 = EnvGen.ar(Env.perc(att, len*0.53), t_trig);
  oenv2 = EnvGen.ar(Env.perc(att, len), t_trig, doneAction: 0);
  oscs = Mix.new(oscs * [oenv1, oenv2]);
  noise = WhiteNoise.ar();
  lonoise = LPF.ar(noise, lopfreq);
  loenv = EnvGen.ar(Env.perc(att, len*0.6, lopamp), t_trig);
  lonoise = lonoise * loenv;
  hinoise = HPF.ar(noise, hipfreq);
  hienv = EnvGen.ar(Env.perc(att, len*0.46,hipamp), t_trig);
  hinoise = hinoise*hienv;
  output = oscs + lonoise + hinoise;
  output = Pan2.ar(output, pan)*amp;
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
