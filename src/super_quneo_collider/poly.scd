// Synthdefs/poly.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("poly", { arg out=0, freq=400, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
    var aEnv, fEnv, osc1, osc2, flt;
    aEnv = EnvGen.kr(Env.asr(0.2, 1, 0.1), gate, doneAction: 0);
    fEnv = EnvGen.kr(Env.asr(7, 1, 0.2), levelScale: 12000);
    osc1 = Pulse.ar(freq * [1, 1.007], LFCub.kr(2, 0, 0.3, 0.5));
    osc2 = Pulse.ar(freq / 2, 0.3);
    flt = RLPF.ar(osc1 + osc2, fEnv, 0.9, aEnv);
  
  snd = flt;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
