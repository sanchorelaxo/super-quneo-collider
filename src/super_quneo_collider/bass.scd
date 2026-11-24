// synthdefs/synthdef-bass.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("bass", { arg out=0, freq=440, amp=0.1, cutoff=1000, rq=0.2, pan=0.0, drive=2.0, filtertime=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var osc, filter, env, filterenv;
  var oschiend, filterhiend;
  var ab;
  var sig, sighiend;

  osc = Saw.ar(freq);
  oschiend = Mix(Saw.ar(freq*[0.25,1,1.5],[0.5,0.4,0.1]));

  filterenv = EnvGen.ar(Env.adsr(0.0,0.5,0.2,0.2),gate, timeScale: filtertime,doneAction: 0);
  filter =  RLPF.ar(osc,cutoff*filterenv+100,rq);

  filterhiend =  RLPF.ar(oschiend,cutoff*filterenv+100,rq);
  ab = abs(filterhiend);
  filterhiend = (filterhiend*(ab + drive)/(filterhiend ** 2 + (drive - 1) * ab + 1));
  //remove low end
  filterhiend = BLowShelf.ar(filterhiend,300,1.0,-12);
  //dip at 1600Hz
  filterhiend = BPeakEQ.ar(filterhiend,1600,1.0,-6);

  env = EnvGen.ar(Env.adsr(0.01,0.0,0.9,0.05),gate,doneAction: 0);

  sig = filter*env*amp*2;
  sighiend = filterhiend*env*amp*2;
  snd = Pan2.ar(filter*env*amp*2,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
