// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("super808", { arg out=0, rate=1, sustain=1, pan=0, voice=0, n=0, freq=440, amp=(-12.dbamp), gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env, sound;
    n = ((n>0)*n) + ((n<1)*3);
  // freq = (n*10).midicps;
    env = EnvGen.ar(Env.linen(0.01, 0, 1, 1, -3), timeScale:sustain, doneAction: 0);
    sound = LPF.ar(SinOscFB.ar(XLine.ar(freq.expexp(10, 2000, 1000, 8000), freq, 0.025/rate), voice), 9000);
  snd = Pan2.ar(sound * env * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
