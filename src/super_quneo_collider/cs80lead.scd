// tidal-synths/cs80lead.scd — diegodorado/tidal-synths (https://github.com/diegodorado/tidal-synths), by diegodorado; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("cs80lead", { arg out=0, freq=880, amp=0.5, attack=0.75, decay=0.5, sustain=0.8, release=1.0, fatt=0.75, fdecay=0.5, fsus=0.8, frel=1.0, cutoff=200, pan=0, dtune=0.002, vibrate=4, vibdepth=0.015, ratio=1, cbus=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
    
    var env,fenv,vib,ffreq,sig;    env=EnvGen.kr(Env.adsr(attack,decay,sustain,release),gate,levelScale:1,doneAction: 0);
    fenv=EnvGen.kr(Env.adsr(fatt,fdecay,fsus,frel,curve:2),gate,levelScale:1,doneAction: 0);
    vib=SinOsc.kr(vibrate).range(-1*vibdepth,vibdepth)+1;
    freq=Line.kr(freq,freq*ratio,5);
    freq=freq*vib;
    sig=Mix.ar(Saw.ar([freq,freq*(1+dtune)]));
    // keep this below nyquist!!
    ffreq=max(fenv*freq*12,cutoff)+100;
    sig=LPF.ar(sig,ffreq);


  
  snd = Pan2.ar(sig, pan, env);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
