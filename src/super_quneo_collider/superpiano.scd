// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superpiano", { arg out=0, sustain=1, pan=0, velocity=1, detune=0.1, muffle=1, stereo=0.2, freq=440, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env = EnvGen.ar(Env.linen(0.002, 0.996, 0.002, 1,-3), timeScale:sustain, doneAction: 0);
    // the +0.01 to freq is because of edge case rounding internal to the MdaPiano synth
    var sound = MdaPiano.ar(freq+0.01, vel:velocity*100, hard:0.8*velocity, decay:0.1*sustain,
      tune:0.5, random:0.05, stretch:detune, muffle:0.8*muffle, stereo:stereo);
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
