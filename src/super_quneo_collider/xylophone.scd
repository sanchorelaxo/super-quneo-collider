// SCLOrkSynths/percussion/xylophone.scd — nicolaariutti & Ze Craum (mod. Ruviaro & Mitchell)
// category: bells, tags: [pitched]. oneshot; xylophone
SynthDef("xylophone", { arg out=0, freq=440, amp=0.01, pan=0, att=0.001, rel=2, exciterRel=0.05, gate=1, fade=1;
var exciter, snd, stopFade, fadeEnv;

  exciter = Impulse.ar(0);

  snd = DynKlank.ar(
    specificationsArrayRef:
            Ref.new([
              [1, 3, 3.971, 5.024, 5.903, 7.13, 8.91],   // harmonics
              [1, 0.95, 0.0891, 0.65, 0.794, 0.53, 0.1], // amplitudes
              [1, 0.593, 0.19, 0.16, 0.26, 0.02, 0.05]     // ring times
            ]),
    input: exciter,
    freqscale: freq,
    decayscale: rel
  );
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan, amp));
});
