// synthdefs/synthdef-eno.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("enotamboura", { arg out=0, feedback=0.07, freq=100, amp=0.3, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sig;  var env = EnvGen.kr(Env.new( [ 0, 0.5, 0.5, 0.5, 0.5], [1, 1, 1, 1] ), gate, doneAction: 0);
  // var env = EnvGen.kr(Env.adsr( \attackTime.kr(0.01), \decayTime.kr(0.3), \sustainLevel.kr(0.5), \releaseTime.kr(1)), gate, doneAction:2);
  sig = FM7.arAlgo(16,
    [
      [freq * 1, 0,    EnvGen.kr(Env.new( [ 0, 1, 0, 1, 0], [0.93, 0.29, 0.18, 0.39] ), gate, doneAction: 0) * 1],
      [freq * 0.5, 0, EnvGen.kr(Env.new( [ 0, 1, 1, 0, 0], [0.78, 0.98, 0.25, 0.22] ), gate, doneAction: 0) * 0.76],
      [freq * 3, 0,    EnvGen.kr(Env.new( [ 0, 1, 0, 1, 0], [0.29, 0.35, 0.22, 0.38] ), gate, doneAction: 0) * 0.67],
      [freq * 3, 0,    EnvGen.kr(Env.new( [ 0, 1, 0, 1, 0], [0.33, 0.35, 0.25, 0.99] ), gate, doneAction: 0) * 0.76],
      [freq * 12, 0,  EnvGen.kr(Env.new( [ 0, 1, 0, 1, 0], [0.36, 0.35, 0.15, 0.38] ), gate, doneAction: 0) * 0.72],
      [freq * 13, 0,  EnvGen.kr(Env.new( [ 0, 1, 0, 1, 0], [0.33, 0.35, 0.25, 0.99] ), gate, doneAction: 0) * 0.81],
    ],
    feedback;
  );

  sig = sig + (sig * LFTri.kr(0.35 * 19, mul: 0.51));
  snd = Pan2.ar(sig  * env * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
