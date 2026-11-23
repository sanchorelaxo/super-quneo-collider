// supercollider.js examples -- "Gabber Rave" hoover lead (SPEC §9.7). Gated
// (onset=note): pad press gate 1, release gate 0; vSlider0 -> freq. The two
// upstream \gate.kr(1) references use the one promoted gate arg.
SynthDef("hoover", { arg out=0, freq=440, gate=1, fade=1;
  var snd, bw, stopFade, fadeEnv;
  freq = freq * Env([-5, 6, 0], [0.1, 1.7], [\lin, -4]).kr.midiratio;
  bw = 1.035;
  snd = { DelayN.ar(Saw.ar(freq * ExpRand(bw, 1 / bw)) + Saw.ar(freq * 0.5 * ExpRand(bw, 1 / bw)), 0.01, Rand(0, 0.01)) }.dup(20);
  snd = (Splay.ar(snd) * 3).atan;
  snd = snd * Env.asr(0.01, 1.0, 1.0).kr(0, gate);
  snd = FreeVerb2.ar(snd[0], snd[1], 0.3, 0.9);
  snd = snd * Env.asr(0, 1.0, 4, 6).kr(2, gate);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd * 0.1);
});