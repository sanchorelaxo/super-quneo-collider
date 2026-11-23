// supercollider.js examples -- "Chainsaw" self-running noise machine
// (Julian Rohrhuber, 2007), SPEC §9.7.  The upstream { }.play body is wrapped
// in a SynthDef; the local f/g closures stay local. f's ExpRand/.coin/.choose
// run once at boot-compile, so the timbre is fixed per session (D8: no compile
// on selection). Master gain * 0.3 -> amp (vSlider0). Drone (onset=select).
SynthDef("chainsaw", { arg out=0, amp=0.3, gate=1, fade=1;
  var f, g, freq, sig, stopFade, fadeEnv;
  f = { | saw |
    var freq, u, rate;
    rate = ExpRand(0.1, 2);
    freq = if (0.6.coin) {
      LFNoise1.kr(rate.dup).exprange(0.01, 10)
    } {
      LFNoise1.kr(rate.dup).exprange(10, 50)
    };
    u = LFSaw.kr(LinExp.kr(saw, -1, 1, freq, freq * LFNoise1.kr(rate.dup).exprange(2, 10)));
    u = if (0.5.coin) {
      u * [1 - saw, saw.reverse].choose
    } {
      u * LFSaw.kr(freq * 0.1, 0, 0.1, 1)
    };
    u.clip2(1.0)
  };
  g = { | func, n = 5 | n.do { func = func <> func }; func };
  freq = g.(f, 4).value(LFSaw.kr(0.2 * [1, 1.1])).exprange(6, 11000);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  sig = BPF.ar(Saw.ar(freq).product, [70, 800, 9000, 5242], 0.2).sum.dup * amp * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});