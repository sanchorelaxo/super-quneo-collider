// tidal-synths/bass8.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("bass8", { arg out=0, amp=0.1, pan=0, freq=200, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
  var sig;
  var osc = Array.newClear(6);
  var env = Array.newClear(6);

  env[0] = EnvGen.kr(Env([0,1,0.051,0],[0.001,0.01,0.8], [4,-8]), 1);
  env[1] = EnvGen.kr(Env([0,1,0.051,0],[0.005,0.5,1.5], [0,-8], releaseNode:2), 1);
  env[2] = EnvGen.kr(Env([0,1,1,0],[0.01,0.01,0.2], [0,0,-4], releaseNode:2), gate);
  env[3] = EnvGen.kr(Env([0,1,0],[0.002,2.8], [0,-4]), 1);
  env[4] = EnvGen.kr(Env([0,1,1,0],[0.001,0.1,0.8], [4,0,-4], releaseNode:2), gate);
  env[5] = EnvGen.kr(Env([0,1,0],[0.001,3.0], [0,-4]), 1);

  freq = (freq / 4) * ((0..1)/1 - 0.5 * 0.0007 + 1);

  osc[0] = SinOsc.ar(freq * 11 + 0) * env[0];
  osc[1] = SinOsc.ar(freq * 6 * ( osc[0] * 2.5 + 1 )) * env[1];
  osc[2] = SinOsc.ar(freq * 2 * 1 + 0) * env[2];
  osc[3] = SinOsc.ar(freq * 1 * ( osc[2] * 2.5 + 1 ) + 0) * env[3];
  osc[4] = SinOsc.ar(freq * 1 * ( osc[1] * 2.5 + 1 ) * (osc[3] * 2.5 + 1)) * env[4];
  osc[5] = SinOsc.ar(freq * 2) * env[5];

  sig = osc * DC.ar([0.0, 0.0, 0.0,  0.0, 0.5, 0.5]);
  sig = sig * 0.5;
  sig = sig.flop.sum;
  sig = sig * EnvGen.ar(\adsr.kr( Env.adsr(0.001,0,1,0.01, 1,-1) ), gate, doneAction: 0);
  sig = sig * AmpComp.kr(freq);
  sig = sig.sum;
  snd = Pan2.ar(sig, pan, amp);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
