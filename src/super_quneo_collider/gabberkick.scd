// supercollider.js examples -- "Gabber Rave" kick (SPEC §9.7).  oneshot:
// a pad press /s_new's this def and DetectSilence frees it. The upstream gated
// amplitude Env.asr is reshaped to a self-ending Env.perc (the source's legato
// 0.8 -> a finite hit). bend -> vSlider3 (0.4-1 pitch-drop amount); ffreq stays 3000.
SynthDef("gabberkick", { arg out=0, freq=440, bend=1, gate=1, fade=1;
  var snd, high, lfo, stopFade, fadeEnv;
  freq = freq * (Env.perc(0.001, 0.08, curve: -1).ar * 48 * bend).midiratio;
  snd = Saw.ar(freq);
  snd = (snd * 100).tanh + ((snd.sign - snd) * -8.dbamp);
  high = HPF.ar(snd, 300);
  lfo = SinOsc.ar(8, [0, 0.5pi]).range(0, 0.01);
  high = high.dup(2) + (DelayC.ar(high, 0.01, lfo) * -2.dbamp);
  snd = LPF.ar(snd, 100).dup(2) + high;
  snd = RLPF.ar(snd, 7000, 2);
  snd = BPeakEQ.ar(snd, 3000 * XLine.kr(1, 0.8, 0.3), 0.5, 15);
  snd = snd * Env.perc(0.001, 0.3).ar;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd * 0.1);
});