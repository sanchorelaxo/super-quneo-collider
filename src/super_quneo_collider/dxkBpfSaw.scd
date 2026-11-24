// dxkSynthDefs/dxkPitched.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkBpfSaw", { arg out=0, atk=2, sus=0, rel=3, ts=1, c1=1, c2=(-1), freq=500, detune=0.2, pan=0, cfhzmin=0.1, cfhzmax=0.3, cfmin=500, cfmax=2000, rqmin=0.1, rqmax=0.2, lsf=200, ldb=0, amp=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var sig, env;
  env = EnvGen.kr(Env([0,1,1,0],[atk,sus,rel],[c1,0,c2]),timeScale:ts,doneAction: 0);
  sig = Saw.ar(freq*{LFNoise1.kr(0.5,detune).midiratio}!2);
  sig = BPF.ar(
    sig,
    {LFNoise1.kr(
      LFNoise1.kr(4).exprange(cfhzmin,cfhzmax)
    ).exprange(cfmin,cfmax)}!2,
    {LFNoise1.kr(0.1).exprange(rqmin,rqmax)}!2
  );
  sig = BLowShelf.ar(sig,lsf,0.5,ldb);
  sig = Balance2.ar(sig[0],sig[1],pan);
  sig = sig*env*amp;
  snd = sig;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
