// synthdefs/synthdef-sc303.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("sc303", { arg out=0, pan=0, freq=440, wave=0, pw=0.5, ctf=100, rq=0.2, attackTime=0.01, sustainLevel=1, decayTime=1, releaseTime=1, env=1000, amp=0.2, filtAttack=0.01, filtSustain=1, filtRelease=1, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  
   var  filEnv, volEnv, waves, sig;

   // can't use adsr with exp curve???
   //volEnv = EnvGen.ar(Env.adsr(1, 0, 1, dec, vol, 'exp'), In.kr(bus));
  // volEnv =  EnvGen .ar( Env .new([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime] ), gate, doneAction:2);
  volEnv = EnvGen.ar(Env.adsr(attackTime, decayTime, sustainLevel, releaseTime), gate, doneAction: 0);
  // filEnv =  EnvGen .ar( Env .new([0, 1, 0], [0.01, releaseTime] ), gate);
  filEnv = EnvGen.ar(Env.asr(filtAttack, filtSustain, filtRelease), gate);

  waves = [ Saw .ar(freq, volEnv),  Pulse .ar(freq, pw, volEnv)];

  sig = RLPF .ar(  Select .ar(wave, waves), ctf + (filEnv * env), rq).dup;
  snd = Pan2.ar(sig  * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
