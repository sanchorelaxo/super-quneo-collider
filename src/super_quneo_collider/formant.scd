// supercolliderjs examples/formant.scd -- SynthDef body verbatim, including
// its Spec.specs exponential control curves (SPEC §9.1), with the shared stop
// fade and voice ceiling added.  Upstream `.add` is dropped so the blob travels
// over /d_recv like the rest.  The three Spec.specs lines are inert to us
// (Python does the scaling) but they are what the example documents about its
// own parameters, so they stay.
SynthDef(\formant, { arg out=0, fundfreq=440, formantfreq=440, bwfreq=100, timeScale=1, pan=0, gate=1, fade=1;
  var saw, envd, panned, stopFade, fadeEnv;
  saw = Formant.ar(fundfreq, formantfreq, bwfreq);
  envd = saw * EnvGen.kr(Env.sine(0.1, 0.2), timeScale: timeScale, doneAction: 0);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  panned = Pan2.ar(envd * AmpCompA.kr(fundfreq, 0.2, 0.7), pan);
  panned = panned * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(panned, 0.0001, 0.5, doneAction: 2);
  OffsetOut.ar(out, panned);
});
