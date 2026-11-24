// Synthdefs/cymbalic_mcld.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("cymbalic_mcld", { arg out=0, pan=0, amp=0.1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
  var lodriver, locutoffenv, hidriver, hicutoffenv, freqs, res, thwack;

  locutoffenv = EnvGen.ar(Env.perc(0.5, 5)) * 20000 + 10;
  lodriver = LPF.ar(WhiteNoise.ar(0.1), locutoffenv);

  hicutoffenv = 10001 - (EnvGen.ar(Env.perc(1, 3)) * 10000);
  hidriver = HPF.ar(WhiteNoise.ar(0.1), hicutoffenv);
  hidriver = hidriver * EnvGen.ar(Env.perc(1, 2, 0.25));

  thwack = EnvGen.ar(Env.perc(0.001,0.001,1));

  // This bit will regenerate new freqs every time you evaluate the SynthDef!
  freqs  = {exprand(300, 20000)}.dup(100);

  res    = Ringz.ar(lodriver + hidriver + thwack, freqs).mean;
  snd = Pan2.ar(((res * 1) + (lodriver * 2) + thwack) * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
