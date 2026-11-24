// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superstatic", { arg out=0, sustain=1, pan=0, freq=440, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env = EnvGen.ar(Env.sine(1, 0.5), timeScale:sustain, doneAction: 0);
  var sound = Dust.ar(freq*40) > 0.5;
  sound = Pulse.ar(freq*sound*4,0.5,0.5);
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
