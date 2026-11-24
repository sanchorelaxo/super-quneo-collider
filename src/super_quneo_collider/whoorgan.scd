// Synthdefs/whoorgan.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("whoorgan", { arg out=0, freq=440, amp=0.1, cutoff=8000, rq=0.8, pan=(-0.1), gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var osc, filter, env;
  var basefreq =  ((freq.cpsmidi)+[0,0.1]).midicps;

  //osc = Mix(Blip.ar(basefreq,16))*0.5;

    osc = Mix.fill(10,{|i| SinOsc.ar(basefreq*(i+1),0.0,(0.25+(0.75*LFNoise0.kr(10.1+i,0.5,0.5)))/(1.0+(0.5*i)))})*0.2;

  filter =  BLowPass.ar(osc,2000+(amp*cutoff),rq);

  env = EnvGen.ar(Env.adsr(0.02,0.1,0.9,1.0),gate,doneAction: 0);
  snd = Pan2.ar(Mix(filter)*env*amp,pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
