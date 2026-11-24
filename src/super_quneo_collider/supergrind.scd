// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("supergrind", { arg out=0, pan=0, freq=440, sustain=1, accelerate=0, detune=0, voice=0, rate=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env, trig, loop;
  freq = freq /2 * XLine.ar(1, exp(accelerate), sustain);
  env = EnvGen.ar(Env.linen(0.1, 0.8, 0.1), timeScale:sustain, doneAction: 0);
  trig = Impulse.kr(rate * Duty.kr(1, 0, Dseq(0.25 ! 3 ++ [2], inf)));
  loop = LocalIn.ar;
  loop = loop + Impulse.ar(SinOsc.ar(1/4, 0, freq/2, (voice+1.0)*freq));
  loop = Mix.ar(DelayC.ar(loop + trig, 1, 1/(2*freq+[detune, -1.0*detune])-ControlDur.ir))/2.0;
  LocalOut.ar(LeakDC.ar(loop).tanh);
  loop = loop + DelayC.ar(loop, 0.2, SinOsc.ar(1, 0, 1e-3, 0.1));
  loop = GVerb.ar(sin(loop + (8*trig)*4)).sin + loop;
  snd = Pan2.ar(0.3*loop * env, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
