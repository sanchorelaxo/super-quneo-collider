// SCLOrkSynths/percussion/steelDrum.scd — Josh Mitchell
// category: percussion, tags: [pitched, steelDrum, steelPan]. oneshot; steel drum
SynthDef("steelDrum", { arg out=0, freq=440, amp=0.1, pan=0, att=0.01, dec=1.5, curve= -6, filterHarmonic=6, gate=1, fade=1;
var resFreqArray, resAmpArray, resDecArray, enva, envb, envc, snda, sndb, sndc, snd, stopFade, fadeEnv;

  //Arrays for the bank of resonators, mostly harmonics near 5ths and 9ths, and random amplitudes:
  resFreqArray = [2, 2.98, 4.75, 6.21, 9, 9.15, 11.87];
  resAmpArray = [0.35, 0.23, 0.10, 0.06, 0.07, 0.05, 0.01];
  resDecArray = [0.86, 0.72, 0.37, 0.55, 0.32, 0.21, 0.16];

  //Custom envelope shapes attempting to capture the aparrent "bloom" of a note:
  enva = Env.pairs([[0, 0], [att, 1], [(att + dec), 0]], curve).kr;
  envb = Env.pairs([[0, 0], [(att * 5), 0.25], [(att * 6), 0.75], [((att * 6) + (dec / 2)), 0]], curve).kr;
  envc = Env.pairs([[0, 0], [(att * 5), 0.1], [(att * 8), 0.5], [((att * 8) + (dec / 3)), 0]], curve).kr;

  //Fundamental, octave up, and a bank of enharmonic resonators excited by a metalic sound:
  snda = SinOsc.ar(freq: freq, mul: enva);
  sndb = SinOsc.ar(freq: freq * 2.015, mul: envb);
  sndc = DynKlank.ar(
    specificationsArrayRef:
        Ref.new([
          resFreqArray * freq,
          resAmpArray,
          resDecArray * dec
        ]),
    input:
    LPF.ar(HPF.ar(CombN.ar(PinkNoise.ar(1), 1/freq, 1/freq, -1, envc), freq * 2), freq * filterHarmonic)
  );

  //Output stages with a tiny bit of compression to smooth things out:

  snd = Mix.ar([snda, sndb, sndc]) * (amp / 3);
  snd = Limiter.ar(snd, amp);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan));
});
