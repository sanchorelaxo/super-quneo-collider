// dxkSynthDefs/dxkPitched.scd — derekxkwan/dxkSynthDefs (https://github.com/derekxkwan/dxkSynthDefs), by derekxkwan; license: GPL-3.0
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("dxkCheapPno", { arg out=0, t_trig=1, freq=440, amp=1, len=1, pan=0, lopprop=3, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 
  var output, n = 6, max = 0.04, min = 0.01, delay, pitch, detune, hammer;
  var midifreq = freq.cpsmidi;
  hammer = Decay2.ar(Trig.ar(t_trig, SampleDur.ir), 0.08, 0.04, LFNoise2.ar([2000,4000].asSpec.map(amp), 0.25));
  output = Mix.ar(Array.fill(3, { arg i;
      detune = #[-0.04, 0, 0.03].at(i);
      delay = (1/(midifreq + detune).midicps);
      CombL.ar(hammer, delay, delay, 50*amp)
    }) );

  output = HPF.ar(output,freq) * EnvGen.ar(Env.perc(0.01,len, amp, -1), doneAction: 0);
  output = Pan2.ar(LPF.ar(output, lopprop * freq), pan);
  snd = output;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
