// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superhoover", { arg out=0, sustain=1, decay=0, pan=0, freq=440, accelerate=0, slide=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env = EnvGen.ar(Env.pairs([[0,0],[0.03,1],[0.2,1-decay],[0.95,1-decay],[1,0]], -1), timeScale:sustain, doneAction: 0);
  var pwm, mix, fglide;
  fglide = EnvGen.ar(Env.perc(0.05, 0.3, 1, \lin), timeScale:sustain) * (-1*slide/4) + 1;
  freq = freq * fglide * Line.kr(1, 1+accelerate, sustain);
  freq = SinOsc.kr( [2.94, 3.0, 3.07], [3.0, 5.5, 1.2] ).exprange(0.995, 1.005) * freq;
  // freq = SinOsc.kr( {2.9 rrand: 3.1}!3, {2pi.rand}!3 ).exprange(0.995, 1.005) * freq;
  pwm = SinOsc.kr( [1.3, 2.9, 4.4] ).range(1/8, 7/8);
  // pwm = SinOsc.kr( {1.0 rrand: 5.0}!3 ).range(1/8, 7/8);
  mix = ([1,0.9,1.1]*LFSaw.ar(freq*[0.25, 0.5, 1], [1, 1.01, 1.02]).range(0,1) * (1 - LFPulse.ar(freq*[0.5,1,2], [0,0,0], pwm))).sum * 0.15;
  mix = mix + LFPar.ar(freq * 0.25, 0, 0.1).sum;
  mix = BPeakEQ.ar(mix, 6000, 1, 3);
  mix = BPeakEQ.ar(mix, 3500, 1, 6);
  mix = mix.dup + CombC.ar(mix.dup, 1/200, SinOsc.kr(3, [0.5pi, 1.5pi]).range(1/300, 1/200), 0);
  snd = Pan2.ar(1.4*mix * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
