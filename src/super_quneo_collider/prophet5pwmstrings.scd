// Synthdefs/prophet3pwmstrings.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("prophet5pwmstrings", { arg out=0, pan=1, freq=440, amp=1.0, att=0.1, rel=0.09, sus=1, dec=0.5, lforate=1, lfowidth=0.5, cutoff=5200, rq=0.15, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  

  var lfo, pulse, filter, env;
  lfo = LFTri.ar(lforate * [1, 1.01], Rand(0, 2.0) ! 2);
  pulse = Pulse.ar(freq * [1, 1.01], lfo * lfowidth + 0.5);
  filter = RLPF.ar(pulse, cutoff, rq);
  env = EnvGen.ar(
    envelope: Env.adsr(att, dec, sus, rel, amp),
    gate: gate,
    doneAction: 0);
  snd = Pan2.ar(
    in: Mix(filter) * env * 0.5,
    pos: pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
