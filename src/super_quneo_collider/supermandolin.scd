// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("supermandolin", { arg out=0, sustain=1, pan=0, accelerate=0, freq=440, detune=0.2, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env = EnvGen.ar(Env.linen(0.002, 0.996, 0.002, 1,-3), timeScale:sustain, doneAction: 0);
    var sound = Decay.ar(Impulse.ar(0,0,0.1), 0.1*(freq.cpsmidi)/69) * WhiteNoise.ar;
    var pitch = freq * Line.kr(1, 1+accelerate, sustain);
    sound = CombL.ar(sound, 0.05, pitch.reciprocal*(1-(detune/100)), sustain)
    + CombL.ar(sound, 0.05, pitch.reciprocal*(1+(detune/100)), sustain);
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
