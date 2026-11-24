// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superkick", { arg out=0, sustain=1, pan=0, accelerate=0, n=0, pitch1=1, decay=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env, sound, dur, clickdur;
    env = EnvGen.ar(Env.linen(0.01, 0, 0.5, 1, -3), timeScale:sustain, doneAction: 0);
    sound = SinOsc.ar((n - 25.5).midicps);
    clickdur = 0.02*sustain*decay;
    sound = sound + (LPF.ar(WhiteNoise.ar(1), 1500*pitch1*Line.kr(1,1+accelerate,clickdur) ) * Line.ar(1, 0, clickdur));
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
