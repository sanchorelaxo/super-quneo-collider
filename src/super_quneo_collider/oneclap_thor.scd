// Synthdefs/oneclap_thor.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("oneclap_thor", { arg out=0, t_trig=1, amp=0.1, filterfreq=1000, rq=0.1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
var env, signal, attack,� noise, hpf1, hpf2;
  noise = WhiteNoise.ar(1)+SinOsc.ar([filterfreq/2,filterfreq/2+4 ], pi*0.5, XLine.kr(1,0.01,4));
  noise = PinkNoise.ar(1)+SinOsc.ar([(filterfreq)*XLine.kr(1,0.01,3), (filterfreq+4)*XLine.kr(1,0.01,3) ], pi*0.5, XLine.kr(1,0.01,4));
  //signal = signal * SinOsc.ar(1,0.75);
  hpf1 = RLPF.ar(noise, filterfreq, rq);
  hpf2 = RHPF.ar(noise, filterfreq/2, rq/4);
  env = EnvGen.kr(Env.perc(0.003, 0.00035));
  signal = (hpf1+hpf2) * env;
  signal = CombC.ar(signal, 0.5, 0.03, 0.031)+CombC.ar(signal, 0.5, 0.03016, 0.06);
  //signal = Decay2.ar(signal, 0.5);
  signal = FreeVerb.ar(signal, 0.23, 0.15, 0.2);
  snd = Pan2.ar(signal * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
