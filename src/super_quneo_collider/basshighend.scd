// Synthdefs/bass.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("basshighend", { arg out=0, freq=440, amp=0.1, cutoff=3000, rq=0.1, drive=10.0, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var osc, filter, env, filterenv;
  var ab;

  //osc = Mix(VarSaw.ar(freq*[0.25,1,1.5],Rand(0.0,1.0)!3,0.9,[0.5,0.4,0.1]));
  osc = Mix(Saw.ar(freq*[0.25,1,1.5],[0.5,0.4,0.1]));
  //osc = Mix(DPW4Saw.ar(freq*[0.25,1,1.5],[0.5,0.4,0.1]));
  filterenv = EnvGen.ar(Env.adsr(0.0,0.5,0.2,0.2),gate,doneAction: 0);
  filter =  RLPF.ar(osc,cutoff*filterenv+100,rq);

  //distortion
  //filter = filter.distort.softclip;

  ab = abs(filter);
  filter = (filter*(ab + drive)/(filter ** 2 + (drive - 1) * ab + 1));

  //remove low end
  filter = BLowShelf.ar(filter,300,1.0,-12);
  //dip at 1600Hz
  filter = BPeakEQ.ar(filter,1600,1.0,-6);

  env = EnvGen.ar(Env.adsr(0.01,0.0,0.9,0.05),gate,doneAction: 0);
  snd = Pan2.ar(filter*env*amp*2,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
