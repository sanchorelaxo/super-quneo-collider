// awesome-synthdefs/co34pt/SynthDefs/co34pt_synthdefs.scd — theseanco/awesome-synthdefs (https://github.com/theseanco/awesome-synthdefs), by theseanco; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("ring3", { arg out=0, f=50, a=3, d=1, pan=0, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    
    var sig, env;
    env = Line.kr(0,1,d);
    env = FreeSelfWhenDone.kr(env);
    sig = Impulse.ar(0);
    sig = Ringz.ar(sig,f,d,a);
  snd = Pan2.ar(sig.tanh,pan) * amp;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
