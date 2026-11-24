// tidal-synths/acid309.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("acid309", { arg out=0, sustain=1, pan=0, accelerate=0, freq=440, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
var env1, env2, son, pitch, amp;      amp = 0.5;
    pitch = freq.cpsmidi;
    pitch = Lag.kr(pitch, 0.12 * (1-Trig.kr(gate, 0.001)) * gate);
    env1 = EnvGen.ar(Env.new([0, 1.0, 0, 0], [0.001, 2.0, 0.04], [0, -4, -4], 2), gate, amp, doneAction: 0);
    env2 = EnvGen.ar(Env.adsr(0.001, 0.8, 0, 0.8, 70, -4), gate);
    son = LFPulse.ar(pitch.midicps, 0.0, 0.51, 2, -1);

    son = RLPF.ar(son, (pitch + env2).midicps, 0.3);
  
  snd = Pan2.ar(son, pan, env1);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
