// awesome-synthdefs/co34pt/SynthDefs/co34pt_synthdefs.scd — theseanco/awesome-synthdefs (https://github.com/theseanco/awesome-synthdefs), by theseanco; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dfm1", { arg out=0, freq=440, mul=0.5, res=1, type=0, noise=0.0003, atk=0.01, rel=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  var sig, env;
  env = EnvGen.ar(Env.perc(atk,rel),doneAction: 0);
  sig = DFM1.ar(SinOsc.ar,freq,res,1,type,noise,mul);
  sig = sig*env;
  snd = Splay.ar([sig]);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
