// Synthdefs/werkit.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("werkit", { arg out=0, pan=0.0, freq=440, amp=0.1, cutoff=100, rq=0.1, att=0.01, dec=0, sus=1, rel=1, delay=0.3, gate=1, fade=1;
  var stopFade, fadeEnv;
  

  var source, filter, env, snd, delayEnv;
  source = WhiteNoise.ar;
  filter = BLowPass4.ar(source, freq, rq) * 0.3;
  env = EnvGen.ar(
    envelope: Env.adsr(att, dec, sus, rel, amp),
    gate: gate,
    doneAction: 0);
  snd = (0.7 * filter + (0.3 * filter.distort)) * env;
  snd = Pan2.ar(snd, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
