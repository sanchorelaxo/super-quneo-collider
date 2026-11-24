// Synthdefs/PMCrotale.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("PMCrotale", { arg out=0, freq=261, tone=3, art=1, amp=0.8, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
var env, mod;

  env = Env.perc(0, art);
  mod = 5 + (1/IRand(2, 6));

  out = PMOsc.ar(freq, mod*freq,
    pmindex: EnvGen.kr(env, timeScale: art, levelScale: tone),
    mul: EnvGen.kr(env, timeScale: art, levelScale: 0.3));

  out = Pan2.ar(out, pan);

  out = out * EnvGen.kr(env, timeScale: 1.3*art,
    levelScale: Rand(0.1, 0.5), doneAction: 0); //Out.ar(bus, out);
  snd = out*amp;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
