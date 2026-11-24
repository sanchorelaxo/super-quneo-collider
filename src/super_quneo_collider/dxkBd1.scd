// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkBd1", { arg out=0, t_trig=1, basefreq=45, overdrive=2, len=0.5, att=0.002, fgprop=0.3, fgdprop=0.9, noisiness=0.2, lop=1250, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  //fgprop = frequency glide in proportion to freq
  //fgdprop = freq glide duration in proportion to dur
  //freq = fundamental
  var freqenv, noise, main, fgdur, fgact, env;
  fgdur = Clip.ir(len * fgdprop, 0, len); //real value of fgdprop
  fgact = fgprop*basefreq; //actual hz to glide over
  freqenv = EnvGen.ar(Env.perc(att, fgdur, fgact, -4),t_trig);
  freqenv = (freqenv + basefreq) + PinkNoise.ar(noisiness);
  main = SinOsc.ar(freqenv);
  main = LPF.ar(main, lop);
  env = EnvGen.ar(Env.perc(att, len, amp, -4), t_trig, doneAction: 0);
  main = main * env;
  main = (main * overdrive).tanh;
  main = Pan2.ar(main, pan);
  snd = main;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
