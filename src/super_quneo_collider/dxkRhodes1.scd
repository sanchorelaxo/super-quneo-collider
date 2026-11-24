// dxkSynthDefs/dxkPitched.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkRhodes1", { arg out=0, freq=440, pan=0, amp=0.1, vel=0.8, modIndex=0.2, mix=0.2, lfoSpeed=0.4, lfoDepth=0.1, att=0.001, decay=1.5, rel=0.1, gate=1, fade=1;
  var stopFade, fadeEnv;
    
    var env1, env2, env3, env4;
    var osc1, osc2, osc3, osc4, snd;

    lfoSpeed = lfoSpeed * 12;

    env1 = EnvGen.ar(Env.adsr(att, 0.833*decay, 0.0, 0.04, curve: \lin),gate);
    env2 = EnvGen.ar(Env.adsr(att, 0.667*decay, 0.0, 0.04, curve: \lin),gate);
    env3 = EnvGen.ar(Env.adsr(att, decay, 0.0, 0.04, curve: \lin),gate);
    env4 = EnvGen.ar(Env.adsr(att, decay, 0.0, 0.04, curve: \lin),gate);

    osc4 = SinOsc.ar(freq) * 2pi * 2 * 0.535887 * modIndex * env4 * vel;
    osc3 = SinOsc.ar(freq * 2, osc4) * env3 * vel;
    osc2 = SinOsc.ar(freq * 30) * 2pi * 0.108819 * env2 * vel;
    osc1 = SinOsc.ar(freq * 2, osc2) * env1 * vel;
    snd = Mix((osc3 * (1 - mix)) + (osc1 * mix));
    snd = snd * (SinOsc.ar(lfoSpeed) * lfoDepth + 1);

    // using the doneAction: 2 on the other envs can create clicks (bc of the linear curve maybe?)
    snd = snd * EnvGen.ar(Env.asr(att, 1, rel), gate, doneAction: 0);
    snd = Pan2.ar(snd, pan, amp);
  snd = snd;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
