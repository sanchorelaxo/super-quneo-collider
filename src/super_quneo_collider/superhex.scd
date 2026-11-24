// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superhex", { arg out=0, rate=1, sustain=1, pan=0, freq=440, accelerate=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env = EnvGen.ar(Env.linen(0.02, 0.96, 0.02, 1,-3), timeScale:sustain, doneAction: 0);
    var tension = 0.05*freq/400 * Line.kr(1,accelerate+1, sustain);
    var loss = 1.0 - (0.01 * rate / freq);
    var sound = MembraneHexagon.ar(Decay.ar(Impulse.ar(0,0,1), 0.01), tension, loss);
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
