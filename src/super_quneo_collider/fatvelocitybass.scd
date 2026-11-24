// Synthdefs/fatvelocitybass.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("fatvelocitybass", { arg out=0, freq=440, amp=0.1, cutoff=12000, rq=0.25, lagTime=0.01, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var lfo, osc, filter, env;

  var basefreq =  ((freq.lag(lagTime).cpsmidi)+[0,11.95,31.03]).midicps;

  osc = Saw.ar(basefreq,[0.5,0.4,0.1]); //+PinkNoise.ar(Line.kr(1.0,0,0.03));

  env = EnvGen.ar(Env.adsr(0.01,1.0,1.0,0.25),gate,doneAction: 0);

  filter = BLowPass4.ar(osc,100+((amp.squared)*(freq+cutoff)),rq);
  snd = Pan2.ar(Mix(filter)*env*amp*0.8,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
