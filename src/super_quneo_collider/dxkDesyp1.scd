// dxkSynthDefs/dxkPitched.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("dxkDesyp1", { arg out=0, freq=440, att=0.001, dec=0.001, sus=0.75, rel=0.125, lfofreq=3, lopfreq=800, rq=0.5, detune1=12, detune2=8, amp=1, pan=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var env = EnvGen.ar(Env.adsr(att, dec, sus, rel, amp), gate, doneAction: 0);
  var nvoices1 = 5, nvoices2 = 7;

  var osc1 = {
    var m = 2**(detune1/1200).rand2;
    var lfo = SinOsc.ar(lfofreq.rand).range(0,1);
    DelayC.ar(LFSaw.ar(m * freq/2), 0.02, freq.reciprocal.rand * lfo);
  }.dup(nvoices1);

  var osc2 = {
    var m = 2**(detune2/1200).rand2;
    var lfo = SinOsc.ar(lfofreq.rand).range(0,1);
    DelayC.ar(LFSaw.ar(m * freq), 0.02, freq.reciprocal.rand * lfo);
  }.dup(nvoices2);

  var output = BLowPass4.ar(osc1, lopfreq, rq) + osc2 / 4;
  output = Pan2.ar(output*env, pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
