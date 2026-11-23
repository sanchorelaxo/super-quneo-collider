// supercolliderjs examples/bubbles.js -- SynthDef body verbatim (SPEC §9.1),
// with the shared stop fade and voice ceiling added.  This file is a
// *fragment*: it evaluates to the SynthDef.  sc.load_defs() wraps it in
// `d = { ... }.value;` and sends the compiled blob with /d_recv, so every
// example arrives through one sclang run instead of one per def.
//
// bubbles still owns its decay (Env.linen, driven by releaseTime); the shared
// guards are added on top, so the example can be stopped on demand and can
// never outlast the ceiling.  The free comes from DetectSilence, not from an
// envelope, because the envelope is what the ceiling turns off.
SynthDef("bubbles", { arg out=0, wobble=0.4, innerWobble=8, releaseTime=4, gate=1, fade=1;
  var f, zout, decay, stopFade, fadeEnv;
  decay = EnvGen.kr(Env.linen(releaseTime: releaseTime), doneAction: 0);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  f = LFSaw.kr(wobble, 0, 24, LFSaw.kr([innerWobble, innerWobble / 1.106], 0, 3, 80)).midicps;
  zout = CombN.ar(SinOsc.ar(f, 0, 0.04), 0.2, 0.2, 4);
  zout = zout * decay * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(zout, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, zout);
});
