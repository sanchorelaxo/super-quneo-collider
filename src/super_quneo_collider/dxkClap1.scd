// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkClap1", { arg out=0, t_trig=1, rel=0.3, hip1=600, bp1=2000, brq1=3, hip2=1000, bp2=1200, brq2=0.7, ampn2=0.7, pan=0, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
    var env1, env2, output, noise1, noise2;
    var env1lvl, env1time, env1curve;
    var env2lvl, env2time, env2curve;

    env1lvl = [0, 1, 0, 1, 0, 1, 0, 1, 0];
    env1time = [0.001, 0.013, 0, 0.01, 0, 0.01, 0, 0.03];
    env1curve = [0, -3, 0, -3, 0, -3, 0, -4];
    env2lvl = [0,1,0];
    env2time = [0.02, rel];
    env2curve = [0, -4];

      env1 = EnvGen.ar(Env.new(env1lvl, env1time, env1curve), t_trig); //attack
      env2 = EnvGen.ar(Env.new(env2lvl, env2time, env2curve), t_trig, doneAction: 0); //release

    noise1 = WhiteNoise.ar(env1);
    noise1 = HPF.ar(noise1, hip1);
    noise1 = BPF.ar(noise1, bp1, brq1);

    noise2 = WhiteNoise.ar(env2);
    noise2 = HPF.ar(noise2, hip2);
    noise2 = BPF.ar(noise2, bp2, brq2, ampn2);

    output = noise1 + noise2;
    output = output.softclip * amp;
    output = Pan2.ar(output, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
