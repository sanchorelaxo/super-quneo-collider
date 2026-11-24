// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkBd3", { arg out=0, freq=43, att=0.005, ampnoise=1, rel=0.32, pan=0, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
    var env0, env1, env1m, output;

    env0 =  EnvGen.ar(Env.new([0.5, 1, 0.5, 0], [att, 0.1875*rel, 0.8125*rel], [-4, -2, -4]), doneAction: 0);
    env1 = EnvGen.ar(Env.new([2.52*freq, 1.35155167*freq, freq], [att, 0.90625*rel], [-4, -5]));


    output = LFPulse.ar(env1, 0, 0.5, 1, -0.5);
    output = output + WhiteNoise.ar(ampnoise);
    output = LPF.ar(output, env1*1.5, env0);
    output = output + SinOsc.ar(env1, 0.5, env0);

    output = output * 1.2;
    output = output.clip2(1)*amp;
      output = Pan2.ar(output, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
