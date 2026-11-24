// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("supersquare", { arg out=0, rate=1, decay=0, sustain=1, pan=0, accelerate=0, freq=440, voice=0.5, semitone=12, resonance=0.2, lfo=1, pitch1=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env = EnvGen.ar(Env.pairs([[0,0],[0.05,1],[0.2,1-decay],[0.95,1-decay],[1,0]], -3), timeScale:sustain, doneAction: 0);
    var basefreq = freq* Line.kr(1, 1+accelerate, sustain);
    var basefreq2 = basefreq / (2**(semitone/12));
    var lfof1 = min(basefreq*10*pitch1, 22000);
    var lfof2 = min(lfof1 * (lfo + 1), 22000);
    var sound = (0.7 * Pulse.ar(basefreq, voice)) + (0.3 * Pulse.ar(basefreq2, voice));
    sound = MoogFF.ar(
      sound,
      SinOsc.ar(basefreq/64*rate, 0).range(lfof1,lfof2),
      resonance*4);
    sound = sound.tanh * 2;
  
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
