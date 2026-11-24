// SCLOrkSynths/percussion/pmCrotales.scd — Author Unknown (mod. Ruviaro & Mitchell)
// category: percussion, tags: [pitched, bell]. oneshot; pm crotales
SynthDef("pmCrotales", { arg out=0, freq=261, tone=3, att=0, rel=2, curve= -6, amp=0.8, pan=0, modLo=5.25, modHi=5.5, gate=1, fade=1;
var env, snd, mod, stopFade, fadeEnv;

  env = Env.perc(attackTime: 0, releaseTime: rel, curve: curve).kr(doneAction: 0);

  mod = Rand(modLo, modHi);

  snd = PMOsc.ar(
        carfreq: freq,
        modfreq: mod * freq,
        pmindex: env * tone,
        mul: env * amp
      );

  snd = HPF.ar(snd, freq / 2);

  snd = Mix.ar(snd) * 0.1;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan));
});
