// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkHh3", { arg out=0, t_trig=1, rel=0.2, hip1=1000, bp2=6000, brq1=2, brq2=0.9, bls2=3000, brs2=0.5, hip2=1000, hrq2=1.5, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var env1, env2, output, oscs1, noise, n = 5, n2 = 8;

    thisThread.randSeed = 4;

    env1 = EnvGen.ar(Env.new([0, 1.0, 0], [0.001, rel], [0, -12]), t_trig, doneAction: 0);
    env2 = EnvGen.ar(Env.new([0, 1.0, 0.05, 0], [0.002, 0.25*rel, 0.15*rel], [0, -4, -4]), t_trig, doneAction:0);

      //tone
    oscs1 = Mix.fill(n, {|i|
      SinOsc.ar(
        ( i.linlin(0, n-1, 42, 74) + rand2(4.0) ).midicps,
        SinOsc.ar( (i.linlin(0, n-1, 78, 80) + rand2(4.0) ).midicps, 0.0, 12),
        1/n
      )
    });

      oscs1 = BHiPass.ar(oscs1, hip1, brq1, env1);

      //noise
    noise = WhiteNoise.ar;
    noise = Mix.fill(n2, {|i|
      var freq;
      freq = (i.linlin(0, n-1, 40, 50) + rand2(4.0) ).midicps.reciprocal;
      CombN.ar(noise, 0.04, freq, 0.1)
    }) * (1/n) + noise;
    noise = BPF.ar(noise, bp2, brq2, 0.5, noise);
    noise = BLowShelf.ar(noise, bls2, brs2, -6);
    noise = BHiPass.ar(noise, hip2, hrq2, env2);

    output = noise + oscs1;
    output = output.softclip;
    output = output * amp;
    output = Pan2.ar(output, pan);
  
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
