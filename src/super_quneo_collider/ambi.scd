// tidal-synths/foxdot/ambi.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("ambi", { arg out=0, amp=1, sus=1, pan=0, freq=440, vib=0, fmod=0, rate=0, bus=0, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var osc, env, filter;    freq = [freq, freq+fmod];
    freq = freq + ( (XLine.kr(Rand(freq/4,freq*4),freq, sus*3/4))  * SinOsc.ar(freq * (2**rate/4)));
    osc=SinOsc.ar(freq, phase:Rand(0,2)!2);
    env = EnvGen.ar(Env([0,0.5 * amp, 0.5 * amp,0],[sus/4, sus*3/4, sus/4]));
    filter = BHiPass.ar(filter, 200);
    osc = osc * env * 0.25;
    osc = Pan2.ar(osc, pan);
  snd = osc;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
