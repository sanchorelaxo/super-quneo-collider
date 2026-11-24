// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superchip", { arg out=0, sustain=1, pan=0, freq=440, rate=1, slide=0, pitch2=2, pitch3=3, accelerate=0, voice=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env, basefreq, sound, va, vb, vc;
    env = EnvGen.ar(Env.linen(0.01, 0.98, 0.01,1,-1), timeScale:sustain, doneAction: 0);
    basefreq = freq + wrap2(slide * 100 * Line.kr(-1,1+(2*rate-2),sustain), slide * 100);
    basefreq = basefreq * Line.kr(1, accelerate+1, sustain);
    va = (voice < 0.5) * 15;
    vb = ((2*voice) % 1 < 0.5) * 15;
    vc = ((4*voice) % 1 < 0.5) * 15;
    sound= AY.ar( AY.freqtotone(basefreq), AY.freqtotone(pitch2*basefreq), AY.freqtotone(pitch3*basefreq),
      vola:va, volb:vb, volc:vc)/2;
    sound = tanh(sound)*2;
  
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
