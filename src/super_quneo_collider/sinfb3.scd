// awesome-synthdefs/co34pt/SynthDefs/co34pt_synthdefs.scd — theseanco/awesome-synthdefs (https://github.com/theseanco/awesome-synthdefs), by theseanco; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("sinfb3", { arg out=0, freq=440, width=0.5, atk=0.01, sus=0, rel=1, fb=0, amp=0.3, pan=0, det=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  var sig, sig2, sig3, env;
  env = EnvGen.ar(Env.linen(atk,sus,rel),1,1,0,1,2);
  sig = SinOscFB.ar(freq,fb);
  sig2 = SinOscFB.ar(freq + det,fb);
  sig3 = SinOscFB.ar(freq - det,fb);
  sig = Mix.ar([sig,sig2,sig3])*env;
  snd = Pan2.ar(sig,pan,amp);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
