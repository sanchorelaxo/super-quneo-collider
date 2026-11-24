// dxkSynthDefs/dxkPitched.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkAcid", { arg out=0, freq=440, rq=0.3, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env1, env2, output;
    freq = Lag.kr(freq, 0.12 * (1-Trig.kr(gate, 0.001)) * gate);
    env1 = EnvGen.ar(Env.new([0, 1.0, 0, 0], [0.001, 2.0, 0.04], [0, -4, -4], 2), gate, amp);
    env2 = EnvGen.ar(Env.adsr(0.001, 0.8, 1, 0.8, 1.4, -4), gate);
    output = LFPulse.ar(freq, 0.0, 0.51, 2, -1);

    output = RLPF.ar(output, freq * env2, rq);
    output = output * env1;
    output = Pan2.ar(output, pan);
  
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
