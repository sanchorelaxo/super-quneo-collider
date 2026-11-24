// tidal-synths/fmtribe.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("fmtribe", { arg out=0, pan=0, accelerate=0, freq=440, attack=0.1, decay=0.3, sustain=0.7, release=0.2, mattack=0.5, mdecay=0.5, msustain=0.7, mrelease=0.1, waveform=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var mod,modEnv,car,env,sig,clip;


    var modFreq = 50;
    var clipAmount = 0.1;
    freq = freq.cpsmidi;


  modEnv = EnvGen.ar(Env.adsr(mattack, mdecay, msustain, mrelease));
  mod = SinOsc.ar(modFreq) * modEnv;
  car = SinOsc.ar(freq + mod);
  env = EnvGen.ar(Env.adsr(attack, decay, sustain, release), doneAction: 0);


  clip = clipAmount * 500;
  sig = (car * clip).clip(-0.97, 0.97) * 0.751;
  snd = Pan2.ar(sig, pan, env);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
