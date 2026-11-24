// Synthdefs/ressquares.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("ressquares", { arg out=0, freq=440, amp=0.1, cutoff=8000, rq=0.8, pan=(-0.1), gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var pulse, filter, env;

  //2 cents detune for second oscillator
  pulse = Mix(Pulse.ar( ((freq.cpsmidi)+[0,0.02]).midicps, 0.5))*0.5;

  filter =  BLowPass.ar(pulse,100+cutoff,rq);

  env = EnvGen.ar(Env.adsr(0.002,0.1,1.0,0.2),gate,doneAction: 0);
  snd = Pan2.ar(filter*env*amp,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
