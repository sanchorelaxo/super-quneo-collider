// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("supernoise", { arg out=0, sustain=1, pan=0, freq=440, accelerate=0, slide=0, pitch1=1, rate=1, resonance=0, voice=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env, basefreq, sound, ffreq, acc;
    env = EnvGen.ar(Env.linen(0.01, 0.98, 0.01,1,-1), timeScale:sustain, doneAction: 0);
    acc = accelerate * freq * 4;
    basefreq = freq * 8 + wrap2(acc* Line.kr(-1,1+(2*rate-2), sustain), acc);
    ffreq = basefreq*5*pitch1* Line.kr(1,1+slide, sustain);
    ffreq = clip(ffreq, 60,20000);
    sound = XFade2.ar( LFDNoise0.ar(basefreq.min(22000), 0.5),
      XFade2.ar(BrownNoise.ar(0.5), WhiteNoise.ar(0.5), basefreq.cpsmidi/127),
      2*voice-1);
    sound = HPF.ar(BMoog.ar(sound, ffreq, resonance, 3), 20);
    sound = clip(sound, -1,1) * 0.3;
  
  snd = Pan2.ar(sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
