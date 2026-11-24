// dxkSynthDefs/dxkPitched.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkPortBass", { arg out=0, freq=440, amp=0.5, slideTime=0.17, ffreq=1100, width=0.15, detune=1.005, preamp=4, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
    var    sig,
        env = Env.adsr(0.01, 0.3, 0.4, 0.1);
  freq = Lag.kr(freq, slideTime);
    sig = Mix(VarSaw.ar([freq, freq * detune], 0, width, preamp)).distort
        * EnvGen.kr(env, gate, doneAction: 0);
    sig = LPF.ar(sig, ffreq);
  sig = Pan2.ar(sig, pan, amp);
  snd = sig;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
