// synthdefs/synthdef-fm7.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("fm7", { arg out=0, freq=440, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sig, env;var spread = 0;  var amps = Array.fill(6, { |i| (\amp++(i+1)).asSymbol.kr(0)});
  var ctls, mods;

  ctls = Array.fill(6, { |i|
    [freq * (\ratio++(i+1)).asSymbol.kr(i+1), 0, (\level++(i+1)).asSymbol.kr(1)];
  });

  mods = Array.fill(6, { |i|
    Array.fill(6, { |n| (\mod++(i+1)++(n+1)).asSymbol.kr(0)});
  });

  sig = FM7.ar(ctls, mods) * amps;
  sig = Gate.ar(sig, gate);
  spread = amps.sum / amps.size;
  sig = sig * (-10.dbamp);
  snd = Splay.ar(sig * amp, spread);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
