// Synthdefs/solo.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("solo", { arg out=0, freq=90, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
    var aEnv, fEnv, osc, flt;
    aEnv = EnvGen.kr(Env.asr(0.2, 1, 2), gate);
    fEnv = EnvGen.kr(Env.adsr(0.4, 1.2, 0.7, 2), gate, 800);
    osc = Saw.ar(Lag.kr(freq, 0.1) * [1, 1.005]);
    flt = LPF.ar(osc, fEnv + 600, aEnv);
  
  snd = flt;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
