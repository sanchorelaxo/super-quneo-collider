// supercollider.js examples -- "Simple FM" drone (SPEC §9.7).
// Upstream: { SinOsc.ar(SinOsc.kr([1, 3]).exprange(100, 2e3), 0, 0.2) }.play
// The [1, 3] LFO rates are promoted to one modRate arg; the 1:3 beat is kept
// so one slider scales a stereo LFO without changing the timbre. Drone: starts
// on select, freed on deselect (onset=select).
SynthDef("simpleFM", { arg out=0, modRate=1, gate=1, fade=1;
  var stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  var fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  var sig = SinOsc.ar(SinOsc.kr([modRate, modRate * 3]).exprange(100, 2e3), 0, 0.2) * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});