// tidal-synths/foxdot/pads.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("pads", { arg out=0, amp=1, sus=1, pan=0, freq=440, vib=0, fmod=0, rate=0, bus=0, atk=0.1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    var osc, env, filter;    freq = [freq, freq+fmod];
    amp=(amp * 2);
    freq = freq * [1, 1.01];

    osc = SinOsc.ar(Line.kr(freq * 4, freq, 0.01) + (Line.kr(10, (freq * 2), sus) * Pulse.ar(freq * rate, width: SinOsc.kr(0.225/sus))), mul:0.5);

    env = EnvGen.ar(Env([0, 0.8, 0.5, 0],[atk, 0.5 * sus, 0.7 * sus]));

    osc = RHPF.ar(osc, [Line.kr(400, 1000, sus), Line.kr(4000,900,sus)], 0.5);

    osc = osc * env * amp;

    osc = Mix(osc) * 0.5;
    osc = Pan2.ar(osc, pan);
  snd = osc;
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
