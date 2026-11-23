// supercolliderjs examples/sine.js -- SynthDef body (SPEC §9.1).
// This file is a *fragment*: it evaluates to the SynthDef.  sc.load_defs()
// wraps it in `d = { ... }.value;` and sends the compiled blob with /d_recv,
// so every example arrives through one sclang run instead of one per def.
//
// Upstream is a bare oscillator with no envelope, so a slider move left a node
// ringing forever.  Every example here carries the same two guards instead:
//   gate  -- 1 while the bridge wants sound; 0 runs a 3 s stop fade, so a
//            selection change fades the voice out rather than cutting it.
//   fade  -- 1 (default) applies the 12 s ceiling: nothing rings past it.
//            0 bypasses the ceiling entirely (the fade checkbox), leaving the
//            voice to be stopped by its gate or by DetectSilence.
// DetectSilence owns the free in every case, so no voice leaks.
SynthDef("sine", { arg out=0, freq=440, gate=1, fade=1;
  var stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  var fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  var sig = SinOsc.ar(freq) * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(sig, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, sig);
});
