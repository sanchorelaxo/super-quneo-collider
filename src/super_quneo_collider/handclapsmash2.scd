// Synthdefs/handclapsmash.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("handclapsmash2", { arg out=0, amp=0.1, cutoff=12000, cutoff2=10000, rq=0.5, modamount=0.0, modrate=50, releaseTime=0.7, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var noise, filter, filterenv, modulation, env;

  noise = WhiteNoise.ar;

  filterenv = EnvGen.ar(Env([0.0,1.0,0.3,0.0],[0.0,0.3,0.3]));

  modulation = (LFSaw.ar(modrate).range(0.0,1.0))*EnvGen.ar(Env([1,1,0,0],[0.1,0.0,1.0]));

  //filter = BHiPass.ar(RLPF.ar(noise,cutoff*filterenv*(1.0+(modamount*modulation)),rq),150); //alternative
  filter = BHiPass.ar(RLPF.ar(noise,cutoff*filterenv+ (cutoff2*modamount*modulation),rq),150);

  //body
  filter = BPeakEQ.ar(filter,440,1.0,8);
  //snap
  filter = BPeakEQ.ar(filter,1200,1.0,14);

  //no gate, fixed percussion sound
  env = EnvGen.ar(Env.perc(0.005,releaseTime),doneAction: 0);
  snd = Pan2.ar(filter*env*amp,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
