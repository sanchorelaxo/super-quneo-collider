// tidal-synths/rhodes.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("rhodes", { arg out=0, sustain=1, pan=0, accelerate=0, freq=440, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sig, in, n = 6, max = 0.04, min = 0.01, delay, pitch, detune, hammer, amp, env;
  amp = 0.9;
  freq = freq.cpsmidi;
  hammer = Decay2.ar(Impulse.ar(0.001), 0.008, 0.04, LFNoise2.ar([2000,4000].asSpec.map(amp), 0.25));
  sig = Mix.ar(Array.fill(3, { arg i;
      detune = #[-0.04, 0, 0.03].at(i);
      delay = (1/(freq + detune).midicps);
      CombL.ar(hammer, delay, delay, 50 * amp)
    }) );

  sig = HPF.ar(sig,50);
    env = EnvGen.ar(Env.perc(0.0001,sustain, amp * 4, -1), doneAction: 0);
  snd = Pan2.ar(sig, pan, env);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
