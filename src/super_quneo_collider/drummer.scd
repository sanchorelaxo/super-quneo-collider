// supercollider.js examples -- "Drummer" (Thor Magnusson, 2006), SPEC §9.7.
// var tempo = 4 is promoted to arg tempo (vSlider0, 0.5-16 Hz); the internal
// clock UGen is renamed `imp` so tempo stays one live-settable control. Drone.
SynthDef("drummer", { arg out=0, tempo=4, gate=1, fade=1;
  var imp, snare, bdrum, hihat, sig, stopFade, fadeEnv;
  imp = Impulse.ar(tempo);
  snare = WhiteNoise.ar(Decay2.ar(PulseDivider.ar(imp, 4, 2), 0.005, 0.5));
  bdrum = SinOsc.ar(Line.ar(120, 60, 1), 0, Decay2.ar(PulseDivider.ar(imp, 4, 0), 0.005, 0.5));
  hihat = HPF.ar(WhiteNoise.ar(1), 10000) * Decay2.ar(imp, 0.005, 0.5);
  sig = (snare + bdrum + hihat) * 0.4 ! 2;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  sig = sig * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});