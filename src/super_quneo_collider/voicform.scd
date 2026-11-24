// Synthdefs/voiceform.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("voicform", { arg out=0, freq=440, amp=0.25, voiceGain=0.25, noiseGain=0.2, sweepRate=0.01, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 

  var voiced = Pulse.ar(freq, 0.1, voiceGain);
  var onezero = OneZero.ar(voiced, -0.9);
  var onepole = OnePole.ar(onezero, 0.97 - (amp*0.2));
  var noise = WhiteNoise.ar(noiseGain*0.1);
  var excitation = onepole + noise;

  var ffreqs = Control.names([\ffreq]).kr([770, 1153, 2450, 3140]);
  var fradii = Control.names([\bw]).kr([0.950, 0.970, 0.780, 0.8]);
  var famps = Control.names([\gain]).kr([1.0, 0.355, 0.0355, 0.011]);

  var filters = TwoPole.ar(excitation, Lag.kr(ffreqs, sweepRate), Lag.kr(fradii, sweepRate), Lag.kr(famps, sweepRate) );
  snd = amp*Mix(filters);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
