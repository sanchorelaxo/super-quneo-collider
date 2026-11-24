// dxkSynthDefs/dxkDrums.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkSd3", { arg out=0, t_trig=1, basefreq=150, att=0.001, len=0.3, lopfreq=1200, rq=0.3, tone=0.7, snare=0.5, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var freqs, rqs, bpmuls, fenv, drumhead, snares, noise, nmul, lonoise, hinoise, output, nenv, rand,  lofreq, hifreq, loenv, hienv, lomul;

  //random number
  rand = TIRand.kr(0,101, t_trig);
  
  freqs = basefreq * [1, 2.03, 3.26, 4.6];
  rqs = rq * [1/2, 1, 1/2, 1/2];
  bpmuls = 3 * [8.333, 10, 5, 1];
  fenv = EnvGen.ar(Env.perc(att, len), t_trig, doneAction: 0);
  noise = WhiteNoise.ar(1.4)+1.4;
  noise = Select.ar(noise, [DC.ar(-1), DC.ar(0), DC.ar(1)]);
  nmul = rand/800.0 + 0.875;
  nenv = EnvGen.ar(Env.perc(att, len*0.46, nmul), t_trig);
  noise = noise * nenv;
  
  //drum head formants
  drumhead = Resonz.ar(LPF.ar(noise, lopfreq), freqs, rqs, bpmuls);
  drumhead = drumhead * tone;

  //snares
  lofreq = rand + 900;
  hifreq = lofreq* 0.95;
  lonoise = LPF.ar(noise, lofreq);
  lomul = (rand/500.0) + 0.4;
  loenv = EnvGen.ar(Env.perc(att, len*0.66,lomul), t_trig);
  lonoise = lonoise * loenv;
  hinoise = HPF.ar(noise, hifreq);
  hienv = EnvGen.ar(Env.perc(att, len*0.466), t_trig);
  hinoise = hinoise * hienv;
  snares = lonoise + hinoise;
  snares = snares * snare;
  output = drumhead + snares;
  output = Pan2.ar(output, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
