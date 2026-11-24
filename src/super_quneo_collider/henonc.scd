// awesome-synthdefs/co34pt/SynthDefs/co34pt_synthdefs.scd — theseanco/awesome-synthdefs (https://github.com/theseanco/awesome-synthdefs), by theseanco; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("henonc", { arg out=0, freq=440, a=1.3, b=0.3, x0=0.30501993062401, x1=0.20938865431933, atk=0.01, sus=1, rel=1, ts=1, pan=0, amp=0.3, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var sig,env;
    sig = HenonC.ar(freq,a,b,x0,x1,amp);
    sig = LeakDC.ar(sig);
  snd = Pan2.ar(sig,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
