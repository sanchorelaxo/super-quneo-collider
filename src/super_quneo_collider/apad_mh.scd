// Synthdefs/apad_mh.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("apad_mh", { arg out=0, freq=880, amp=0.5, attack=0.4, decay=0.5, sustain=0.8, release=1.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env,sig,mod1,mod2,mod3;
  env=EnvGen.kr(Env.adsr(attack,decay,sustain,release),gate,levelScale:amp,doneAction: 0);
  mod1=SinOsc.kr(6).range(freq*0.99,freq*1.01);
  mod2=LFNoise2.kr(1).range(0.2,1);
  mod3=SinOsc.kr(rrand(4.0,6.0)).range(0.5,1);
  sig=SinOsc.ar([freq,mod1],0,env).distort;
  sig=sig*mod2*mod3;
  snd = sig;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
