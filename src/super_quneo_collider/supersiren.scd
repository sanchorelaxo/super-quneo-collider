// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("supersiren", { arg out=0, sustain=1, pan=0, freq=440, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env, sound;
    env = EnvGen.ar(Env.linen(0.05, 0.9, 0.05, 1, -2), timeScale:sustain, doneAction: 0);
    sound = VarSaw.ar(freq * (1.0 + EnvGen.kr(Env.linen(0.25,0.5,0.25,3,0), timeScale:sustain, doneAction: 0)),
      0, width:Line.kr(0.05,1,sustain));
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
