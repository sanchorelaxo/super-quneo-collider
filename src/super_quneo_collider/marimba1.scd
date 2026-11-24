// SCLOrkSynths/percussion/marimba1.scd — unknown (mod. Ruviaro & Mitchell)
// category: percussion, tags: [marimba, pitched, keyboard]. oneshot; bpf marimba
SynthDef("marimba1", { arg out=0, freq=440, amp=0.4, pan=0, rq=0.02, shelffreq=220, rs=0.81, shelfamp=2, gate=1, fade=1;
var snd, stopFade, fadeEnv;

  snd = BPF.ar(
    in: Saw.ar(0),
    freq: freq,
    rq: rq);

  snd = BLowShelf.ar(
    in: snd,
    freq: shelffreq,
    rs: rs,
    db: shelfamp.ampdb);

  snd = Limiter.ar(snd) * amp;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, Pan2.ar(snd, pan));
});
