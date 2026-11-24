// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkHh2", { arg out=0, t_trig=1, len=0.125, att=0.001, rq=0.35, lp=10000, bplow=5000, bphigh=8000, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var bpenv, main, env,glide;
  env = EnvGen.ar(Env.perc(att, len, 1 -8), doneAction: 0);
  glide = (bphigh-bplow).abs;
  main = WhiteNoise.ar() *env;
  bpenv = EnvGen.ar(Env.perc(att, len, glide, -8));
  bpenv = (glide-bpenv)+bplow.min(bphigh);
  main = BPF.ar(main, bpenv, rq);
  main = LPF.ar(main, lp);
  main = main * amp;
  main = Pan2.ar(main, pan);
  snd = main;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
