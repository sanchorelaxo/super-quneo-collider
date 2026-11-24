// synthdefs/synthdef-fm.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("fm", { arg out=0, freq=500, mRatio=1, cRatio=1, index=1, iScale=5, iAtk=0.01, iRel=1, ciAtk=4, ciRel=(-4), atk=0.01, rel=1, cAtk=4, cRel=(-4), amp=0.2, pan=0, fx=0, fxsend=(-25), gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  var car, mod, env, iEnv;

  //index of modulation
  iEnv = EnvGen.kr(
    Env(
      [index, index*iScale, index],
      [iAtk, iRel],
      [ciAtk, ciRel]
    )
  );

  //amplitude envelope
  env = EnvGen.kr(Env.perc(atk,rel,curve:[cAtk,cRel]),doneAction: 0);

  //modulator/carrier
  mod = SinOsc.ar(freq * mRatio, mul:freq * mRatio * iEnv);
  car = SinOsc.ar(freq * cRatio + mod) * env * amp;

  car = Pan2.ar(car, pan);
  // Out.ar(fx, car * fxsend.dbamp);
  snd = car;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
