// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkSd1", { arg out=0, t_trig=1, basefreq=300, len=0.125, fgprop=0.5, fgdprop=0.75, rq=0.1, lop=5000, att=0.002, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  //penv = pitch envelope
  //fgprop = frequency glide in proportion to freq
  //fgdprop = freq glide duration in proportion to dur
  //freqbase = fundamental
  var output, ampenv, penv, gaincomp = 9;
  output = WhiteNoise.ar()*gaincomp;
  penv = EnvGen.ar(Env.perc(att, len*fgdprop, basefreq*fgprop), t_trig);
  penv = penv + basefreq;
  output = BPF.ar(output,penv, rq);
  output = LPF.ar(output, lop, amp);
  ampenv = EnvGen.ar(Env.perc(att, len), t_trig, doneAction: 0);
  output = output * ampenv;
  output = Pan2.ar(output, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
