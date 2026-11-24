// SCLOrkSynths/percussion/abstractDrum.scd — by Josh Mitchell
// category: percussion, tags: [pitched, modal]. oneshot; modal 'abstract drum'
SynthDef("abstractDrum", { arg out=0, freq=140, amp=1, pan=0, att=0.001, dec=0.01, rel=1, position=0.5, ampSlope=3, decCoef=0.15, hiFreqSus=0, gate=1, fade=1;
var freqarray, amparray, decarray, exciter, snd, stopFade, fadeEnv;

  // Setting up arrays for Klank
  freqarray = Array.fill(8, {
    arg i = 1;
    (
      Array.fill((i + 1), {
        arg j;
        (j + 1).pow(2)
      }) +
      (i + 1).pow(2)
    ).sqrt

  });
  freqarray = freqarray.flatten/(2.sqrt);

  amparray = Array.fill(36, {
    arg i;
    if (freqarray[i] > 20000)
      { 0 }
      {
          sin(((i + 1) * pi) * position) *
            (ampSlope * (freqarray[i]).log2).dbamp
        }
  });
  amparray = amparray/ampSlope;

  decarray = Array.fill(36, {
    arg i;
    exp(-1 * i * decCoef) + hiFreqSus
  });
  decarray = decarray/decarray[0];

  // Exciter
  exciter = Decay2.ar(
    in: Impulse.ar(0),
    attackTime: att,
    decayTime: dec,
    mul: 0.005); // This keeps the volume at a sane level

  // The actual sound-makey part
  snd = Klank.ar(
    specificationsArrayRef:
        Ref.new([freqarray, amparray, decarray]),
    input: exciter,
    freqscale: freq,
    decayscale: rel);

  // Output Stuff
  snd = Mix.ar(snd * amp * 2);
  snd = Limiter.ar(snd);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan));
});
