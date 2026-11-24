// Synthdefs/plastickystrings.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("plastickystrings", { arg out=0, freq=440, amp=0.1, lforate=5900, lfowidth=0.01, cutoff=12000, rq=0.5, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var lfo, saw, filter, env;

  lfo = LFTri.ar(lforate,Rand(0,2.0));

  saw = Saw.ar(freq*(1.0+(lfowidth*lfo)),0.5);

  //filter = BBandPass.ar(saw,freq,4);
  filter = BHiPass.ar(saw,freq,rq);   //or using cutoff

  env = EnvGen.ar(Env.adsr(0.4,0.0,1.0,1.0),gate,doneAction: 0);
  snd = Pan2.ar(filter*env*amp,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
