// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("supertron", { arg out=0, pan=0, freq=440, sustain=1, voice=0, detune=0, accelerate=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sound, aenv, s1, s2;
  aenv = EnvGen.ar(Env.linen(0.05, 0.85, 0.1, 1, 'lin'), timeScale:sustain, doneAction: 0);
  freq = freq * XLine.ar(1, exp(accelerate), sustain);
  sound = LocalIn.ar(1);
  sound = Mix.ar( Pulse.ar(freq+[1+detune,-1-detune], RLPF.ar(sound, freq/6.1, 1.5).range(0,1-(voice/1.5))) );
  sound = LeakDC.ar(sound);
  LocalOut.ar(sound);
  snd = Pan2.ar(sound * aenv, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
