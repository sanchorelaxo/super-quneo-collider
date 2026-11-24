// Synthdefs/bowed.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("bowed", { arg out=0, amp=1.0, freq=420, bowOffset=0.0, bowSlope=0.5, bowPosition=0.75, vibFreq=6.127, vibGain=0.0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
  var betaRatio = 0.027236 + (0.2*bowPosition);
  var baseDelay = freq.reciprocal;
  var lastOut = LocalIn.ar(2);
  var vibrato = SinOsc.ar(vibFreq, 0, vibGain);
  var neckDelay = baseDelay*(1.0-betaRatio) + (baseDelay*vibrato);
  var neck = DelayL.ar(lastOut[0], 0.05, neckDelay);
  var bridge = DelayL.ar(lastOut[1], 0.025, baseDelay*betaRatio);
  var stringFilter = OnePole.ar(bridge*0.95, 0.55);
  var adsr = amp*EnvGen.ar(Env.adsr(0.02, 0.005, 1.0, 0.01), gate, doneAction: 0);
  var bridgeRefl = stringFilter.neg;
  var nutRefl = neck.neg;
  var stringVel = bridgeRefl + nutRefl;
  var velDiff = adsr - stringVel;
  var slope = 5.0 - (4.0*bowSlope);
  var bowtable = (( ((velDiff+bowOffset)*slope) + 0.75 ).abs ).pow(-4).clip(0, 1);
  var newVel = velDiff*bowtable;
  LocalOut.ar([bridgeRefl, nutRefl] + newVel);
  snd = Resonz.ar( bridge*0.5, 500, 0.85 );
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
