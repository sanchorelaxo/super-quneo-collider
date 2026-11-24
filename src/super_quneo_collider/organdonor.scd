// Synthdefs/organdonor.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("organdonor", { arg out=0, pan=0.0, freq=440, amp=0.1, att=0.01, dec=0.5, sus=1, rel=0.5, lforate=10, lfowidth=0.01, cutoff=100, rq=0.5, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  

  var vibrato, pulse, filter, env;
  vibrato = SinOsc.ar(lforate, Rand(0, 2.0));
  // up octave, detune by 4 cents
  // 11.96.midiratio = 1.9953843530485
  // up octave and a half, detune up by 10 cents
  // 19.10.midiratio = 3.0139733629359
  freq = freq * [1, 1.9953843530485, 3.0139733629359];
  freq = freq * (1.0 + (lfowidth * vibrato));
  pulse = VarSaw.ar(
    freq: freq,
    iphase: Rand(0.0, 1.0) ! 3,
    width: Rand(0.3, 0.5) ! 3,
    mul: [1.0,0.7,0.3]);
  pulse = Mix(pulse);
  filter = RLPF.ar(pulse, cutoff, rq);
  env = EnvGen.ar(
    envelope: Env.adsr(att, dec, sus, rel, amp),
    gate: gate,
    doneAction: 0);
  snd = Pan2.ar(filter * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
