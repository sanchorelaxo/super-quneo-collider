// Synthdefs/jilet.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("jilet", { arg out=0, freq=4, amp=0.5, endReflection=1.5, jetReflection=0.5, jetRatio=10.72, noiseGain=0.35, vibFreq=5.925, vibGain=0.02, outputGain=0.20, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 

  var adsr = (amp*0.2) + EnvGen.ar(Env.adsr(0.005, 0.01, 1.1, 0.01), gate, doneAction: 0);
  var noise = WhiteNoise.ar(noiseGain);
  var vibrato = SinOsc.ar(vibFreq, 0, vibGain);

  var delay = (freq*0.66666).reciprocal;
  var lastOut = LocalIn.ar(1);
  var breathPressure = adsr*Mix([1.0, noise, vibrato]);
  var filter = LeakDC.ar(OnePole.ar(lastOut.neg, 0.7));
  var pressureDiff = breathPressure - (jetReflection*filter);
  var jetDelay = DelayL.ar(pressureDiff, 0.025, delay*jetRatio);
  var jet = (jetDelay * (jetDelay.squared - 1.0)).clip2(1.0);
  var boreDelay = DelayL.ar(jet + (endReflection*filter), 0.05, delay);
  LocalOut.ar(boreDelay);
  snd = 0.3*boreDelay*outputGain;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
