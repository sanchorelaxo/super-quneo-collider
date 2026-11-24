// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superreese", { arg out=0, pan=0, freq=440, sustain=1, accelerate=0, detune=0, voice=0, amp=(-12.dbamp), gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sound;
  var env = EnvGen.ar(Env.linen(0.05, 0.8, 0.15), timeScale:sustain, doneAction: 0);
  var q1 = voice.linlin(0,2, 3.0, 0.5);
  var q2 = voice.linlin(0,2, 2.0, 7.0);
  freq = freq * XLine.ar(1, exp(accelerate), sustain);
  sound = Splay.ar( VarSaw.ar(freq*[-1*detune/100+0.99,detune/100+1.01], [0.7,0.5], [0.01,0.02]), 0.2, 1, levelComp:false );
  sound = RLPF.ar(sound, freq*10, 1.0/q1);
  sound = sound.clip2(1.0/5.0)* 5.0;
  sound = 0.35*RLPF.ar(sound, freq*20, 1.0/q2);
  snd = Pan2.ar(sound * env * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
