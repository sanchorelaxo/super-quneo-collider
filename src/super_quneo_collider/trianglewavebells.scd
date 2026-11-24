// Synthdefs/trianglewavebells.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("trianglewavebells", { arg out=0, pan=0.0, freq=440, amp=1.0, att=0.01, dec=0.1, sus=1, rel=0.5, lforate=10, lfowidth=0.0, cutoff=100, rq=0.5, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  

  var osc1, osc2, vibrato, filter, env;
  vibrato = SinOsc.ar(lforate, Rand(0, 2.0));
  osc1 = Saw.ar(freq * (1.0 + (lfowidth * vibrato)), 0.75);
  osc2 = Mix(LFTri.ar((freq.cpsmidi + [11.9, 12.1]).midicps));
  filter = RHPF.ar((osc1 + (osc2 * 0.5)) * 0.5, cutoff, rq);
  env = EnvGen.ar(
    envelope: Env.adsr(att, dec, sus, rel, amp),
    gate: gate,
    doneAction: 0);
  snd = Pan2.ar(filter * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
