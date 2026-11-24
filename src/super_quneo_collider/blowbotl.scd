// Synthdefs/blowbot1.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("blowbotl", { arg out=0, amp=1.0, freq=20, rq=0.1, noise=0.1, vibFreq=5.2, vibGain=0.9, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
  var lastOut = LocalIn.ar(1);
  var adsr = amp*EnvGen.ar(Env.adsr(0.005, 0.01, 1.0, 0.010), gate, doneAction: 0);
  var vibrato = SinOsc.ar(vibFreq, 0, vibGain);
  var pressureDiff = (adsr+vibrato) - lastOut;
  var jet = (pressureDiff * (pressureDiff.squared - 1.0)).clip2(1.0);
  var randPressure = WhiteNoise.ar(noise)*adsr*(1.0 + pressureDiff);

  var resonator = Resonz.ar(adsr+randPressure - (jet*pressureDiff), freq, rq);
  LocalOut.ar(resonator);
  snd = LeakDC.ar(resonator);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
