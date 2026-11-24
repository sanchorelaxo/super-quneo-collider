// SCLOrkSynths/percussion/kalimba.scd — by Nathan Ho aka Snappizz (mod. Mitchell & Ruviaro)
// category: percussion, tags: [pitched, kalimba]. oneshot; kalimba, resonators
SynthDef("kalimba", { arg out=0, freq=440, amp=0.1, att=0.001, rel=3, pan=0, crv= -8, mix=0.1, clickRel=0.01, gate=1, fade=1;
var note, env, body, snd, stopFade, fadeEnv;

  env = Env.perc(
    attackTime:att * 3, releaseTime: rel,
    curve: crv).kr(doneAction: 0);

  note = SinOsc.ar(freq) * env;

  body = DynKlank.ar(
    specificationsArrayRef:
    Ref.new([
      [240 * ExpRand(0.9, 1.1), 2020 * ExpRand(0.9, 1.1), 3151 * ExpRand(0.9, 1.1)],
      [-7, 0, 3].dbamp, // same as 10.pow([-7, 0, 3] / 20),
      [0.75, 0.04, 0.06] + clickRel
    ]),
    input:
    // Try BrownNoise, GrayNoise, etc. here, but you may need to change ring times above
    (PinkNoise.ar * Env.perc(att, clickRel).kr)
  );

  snd = (note * (1 - mix)) + (body * mix) * amp;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan));
});
