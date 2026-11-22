// One-shot SynthDef delivery for the super-quneo-collider bridge.
// Runs via `sclang bubbles.scd` (positional file) and exits with `0.exit`.
var addr = NetAddr("127.0.0.1", 57110);
var d = SynthDef("bubbles", { arg out=0, wobble=0.4, innerWobble=8, releaseTime=4;
  var f, zout;
  f = LFSaw.kr(wobble, 0, 24, LFSaw.kr([innerWobble, innerWobble / 1.106], 0, 3, 80)).midicps;
  zout = CombN.ar(SinOsc.ar(f, 0, 0.04), 0.2, 0.2, 4);
  zout = zout * EnvGen.kr(Env.linen(releaseTime: releaseTime), doneAction: 2);
  Out.ar(out, zout);
});
addr.sendMsg("/d_recv", d.asBytes);
0.exit;
