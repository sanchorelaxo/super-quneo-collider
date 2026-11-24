// SCLOrkSynths/percussion/metalPlate.scd — by Josh Mitchell
// category: percussion, tags: [pitched, modal]. oneshot; clamped metallic plate
SynthDef("metalPlate", { arg out=0, freq=3000, amp=0.5, rel=2, pan=0, crv=0, ratio=1, decCoef=0.31, xpos=0.5, ypos=0.5, thumpDec=0.75, gate=1, fade=1;
var exciter, freqArray, ampArray, decArray, snd, stopFade, fadeEnv;

  // Frequencies
  freqArray = Array.fill2D(16, 16, {
    arg i, j;
    (i + 1).pow(2) + (ratio * (j + 1)).pow(2)
  });
  freqArray = freqArray/(freqArray[0][1]);
  freqArray = freqArray * freq;

  // Amplitudes
  ampArray = Array.fill2D(16, 16, {
    arg i, j;
    ((1 - ((freqArray[i][j] - 19000)/1000).tanh)/2) *
    sin(((i + 1) * pi) * xpos) *
    sin(((j + 1) * pi) * ypos)
  });

  // Decay Times
  decArray = Array.fill2D(16, 16, {
    arg i, j;
    (
      if (j == 0)
            { thumpDec }
            { 1 }
    ) *
    exp(-1 * (i + j) * decCoef)
  });

  // Hit the plate
  exciter = Impulse.ar(0);

  // The Plate
  snd = Klank.ar(
    specificationsArrayRef:
        Ref.new([freqArray.flatten, ampArray.flatten, decArray.flatten]),
    input: exciter,
    decayscale: rel);

  // Output Stuff
  snd = HPF.ar(
    in: snd,
    freq: [freq, freq * 2, freq * 4, freq * 8, freq * 16, freq * 32, freq * 64]);
  snd = Mix.ar(snd/7) * amp;
  snd = Limiter.ar(snd);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan));
});
