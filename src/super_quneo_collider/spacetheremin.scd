// Synthdefs/spacetheremin.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("spacetheremin", { arg out=0, freq=440, amp=0.1, lforate=6, lfowidth=0.5, cutoff=4000, rq=0.25, lagTime=0.1, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var lfo, osc, filter, env;

  lfo = LFTri.kr(lforate+(LFNoise1.kr(5,0.3,0.3)),Rand(0,2.0));

  osc = Saw.ar((freq.lag(lagTime).cpsmidi+(lfo*lfowidth)).midicps,0.5);

  filter = BLowPass4.ar(osc,cutoff.lag(lagTime*4),rq);

  env = EnvGen.ar(Env.adsr(0.6,0.0,1.0,0.05),gate,doneAction: 0);
  snd = Pan2.ar(filter*env*amp.lag(lagTime*4),pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
