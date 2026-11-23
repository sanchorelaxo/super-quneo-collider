// supercolliderjs examples/klang.scd -- reshaped (SPEC §9.3) so nPartials and
// nChans are board-controllable, with the shared stop fade and voice ceiling
// added.  Upstream they were `var` locals, which let the `!` duplication
// operator use them as array sizes; as SynthDef args they are UGens, and
// Array.fill cannot take a UGen count, so the partial bank is built up to fixed
// maxima and each slot is masked on/off by its own index.  The random
// 200-2000 Hz partials are still re-rolled on every spawn.
SynthDef("klang", { arg out=0, nPartials=12, nChans=5, gate=1, fade=1;
  var maxPartials = 32, maxChans = 8;
  var freqs = Array.fill(maxChans, { Array.fill(maxPartials, { rrand(200.0, 2000.0) }) });
  var amps = Array.fill(maxChans, { |chan|
    Array.fill(maxPartials, { |part| (part < nPartials) * (chan < nChans) })
  });
  var phases = Array.fill(maxChans, { Array.fill(maxPartials, 0) });
  var sig = Klang.ar(`[freqs, amps, phases], 1, 0);
  var own = EnvGen.kr(Env.sine(4), 1, 0.02, doneAction: 0);
  var stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  var fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  sig = Splay.ar(sig) * own * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});
