// Synthdefs/snare_stein.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("snare_stein", { arg out=0, amp=0.1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
var snare, filtWhite;

filtWhite = LPF.ar(WhiteNoise.ar(1), 7040, 1);

snare = ((SinOsc.ar(330,0,0.25) * EnvGen.ar(Env.perc(0.0005,0.055)))
� � � � � � � � � � � �+(SinOsc.ar(185,0,0.25) * EnvGen.ar(Env.perc(0.0005,0.075)))
� � � � � � � � � � � �+(filtWhite * EnvGen.ar(Env.perc(0.0005,0.2), doneAction: 0) * 0.2)
� � � � � � � � � � � �+(HPF.ar(filtWhite, 523, 1) * EnvGen.ar(Env.perc(0.0005,0.183)) * 0.2)
� � � � � � � � � � � �);
  snd = Pan2.ar(snare * amp * 10, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
