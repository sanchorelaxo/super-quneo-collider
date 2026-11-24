// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superwavemechanics", { arg out=0, pan=0, freq=440, sustain=1, accelerate=0, detune=0, voice=0, resonance=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env, sound, i, r, d, bwr, sz;
  freq = freq * XLine.ar(1, exp(accelerate), sustain);
  env = EnvGen.ar(Env.sine(1.0), timeScale:sustain, doneAction: 0);
  i = TIRand.kr(0, 3, Impulse.kr(sustain/8).dup(8));
  r = [3,5,8,9]/8;
  detune = min(detune, 1.5);
  d = Rand(1.6*i - detune, 1.7*i + detune).round(0.25);
  sound = Resonz.ar(WhiteNoise.ar(0.5), freq * r * d, 0.01 + voice.linexp(0,1,1e-3,1));
  sound = HPF.ar(Limiter.ar(55 * GVerb.ar(sound, resonance.linexp(0,1,99,0.1),10) ), 30).sanitize;
  snd = Pan2.ar(sound.flat * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
