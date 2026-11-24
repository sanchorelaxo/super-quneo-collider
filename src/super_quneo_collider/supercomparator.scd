// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("supercomparator", { arg out=0, rate=1, decay=0, sustain=1, pan=0, accelerate=0, freq=440, voice=0.5, resonance=0.5, lfo=1, pitch1=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env = EnvGen.ar(Env.pairs([[0,0],[0.05,1],[0.2,1-decay],[0.95,1-decay],[1,0]], -3), timeScale:sustain, doneAction: 0);
    var basefreq = freq * Line.kr(1, 1+accelerate, sustain);
    var sound = VarSaw.ar(basefreq, 0, Line.ar(0,1,sustain));
    var freqlist =[ 1.000, 2.188,  5.091,  8.529,  8.950,  9.305, 13.746, 14.653, 19.462, 22.003, 24.888, 25.991,
      26.085, 30.509, 33.608, 35.081, 40.125, 42.023, 46.527, 49.481]**(voice/5);
    sound = Splay.arFill(16, {|i| sound > LFTri.ar(freqlist[i])}, 1);
    sound = MoogFF.ar(
      sound,
      pitch1 * 4 * basefreq + SinOsc.ar(basefreq/64*rate, 0, lfo*basefreq/2) + LFNoise2.ar(1,lfo*basefreq),
      LFNoise2.ar(0,0.1,4*resonance));
  
  snd = Pan2.ar(0.5*sound * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
