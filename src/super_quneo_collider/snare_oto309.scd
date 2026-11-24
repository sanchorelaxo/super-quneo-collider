// Synthdefs/snare_oto309.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("snare_oto309", { arg out=0, amp=0.1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  var env0, env1, env2, env1m, oscs, noise, son;

  env0 = EnvGen.ar(Env.new([0.5, 1, 0.5, 0], [0.005, 0.03, 0.10], [-4, -2, -4]));
  env1 = EnvGen.ar(Env.new([110, 60, 49], [0.005, 0.1], [-4, -5]));
  env1m = env1.midicps;
  env2 = EnvGen.ar(Env.new([1, 0.4, 0], [0.05, 0.13], [-2, -2]), doneAction: 0);

  oscs = LFPulse.ar(env1m, 0, 0.5, 1, -0.5) + LFPulse.ar(env1m * 1.6, 0, 0.5, 0.5, -0.25);
  oscs = LPF.ar(oscs, env1m*1.2, env0);
  oscs = oscs + SinOsc.ar(env1m, 0.8, env0);

  noise = WhiteNoise.ar(0.2);
  noise = HPF.ar(noise, 200, 2);
  noise = BPF.ar(noise, 6900, 0.6, 3) + noise;
  noise = noise * env2;

  son = oscs + noise;
  son = son.clip2(1) * amp;
  snd = Pan2.ar(son, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
