// SCLOrkSynths/percussion/modalMarimba.scd — by Josh Mitchell
// category: percussion, tags: [pitched, modal]. oneshot; modal idiophone
SynthDef("modalMarimba", { arg out=0, freq=440, amp=0.1, att=0.001, dec=0.1, rel=0.5, pan=0, decCoef=2, position=0.414, ampSlope=3, gate=1, fade=1;
var freqarray, amparray, decarray, mallet, snd, stopFade, fadeEnv;

  // Array of frequencies, determined by solutions to the dynamic beam equation
  freqarray = Array.fill(30, { arg i; i + 1.5});
        freqarray[0] = 1.50561873;
      freqarray[1] = 2.49975267;
      freqarray = freqarray/1.50561873; // Normalize to freqarray[0] = 1

  // Array of amplitudes
  amparray = Array.fill(30, { arg i;
    if (freqarray[i] > 20000)
        { 0 }
        {
            sin(((i + 1) * pi) * position) *
            (ampSlope * (freqarray[i]).log2).dbamp
        }
  });

  // Array of Decay times
  decarray = Array.fill(30, { arg i;
    exp(-1 * i * decCoef)
  }); // The decay times are dropping off exponentially

  // Hit the object
  mallet = Decay2.ar(
    in: Impulse.ar(0),
    attackTime: att,
    decayTime: dec, 
    mul: 0.1);

  // Bank of resonators
  snd = Klank.ar(
    specificationsArrayRef: Ref.new([freqarray, amparray, decarray]),
    input: mallet,
    freqscale: freq,
    decayscale: rel);

  // Output stuff
  snd = Mix.ar(snd) * amp;
  snd = Limiter.ar(snd);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan));
});
