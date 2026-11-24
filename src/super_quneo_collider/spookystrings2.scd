// Synthdefs/spookystrings.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("spookystrings2", { arg out=0, freq=440, amp=0.1, cutoff=8000, rq=0.2, pan=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var saw, pulse, filter, env, lfo, pulsewidthlfo;

  lfo = LFTri.kr([3.5,5],Rand(0,2.0)!2);

  pulsewidthlfo = SinOsc.kr(4.5);

  saw = Saw.ar(freq*(1.0+(0.052*lfo[0])));

  pulse = Pulse.ar(freq*(1.0+(0.072*lfo[1])),pulsewidthlfo*0.25+0.5);

  //combine, equal mix
  pulse = 0.5*(saw+pulse);

  //filter specification not the clearest, so just going for slow attack to brightness
  filter = BLowPass.ar(pulse,XLine.kr(678,cutoff,0.378),rq);

  env = EnvGen.ar(Env.adsr(0.1,0.0,1.0,3),gate,doneAction: 0);
  snd = Pan2.ar(filter*env*amp,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
