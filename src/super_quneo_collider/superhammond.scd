// synthdefs/synthdef-superdirt.scd — loopier/synthdefs (https://github.com/loopier/synthdefs), by loopier; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: oneshot
SynthDef("superhammond", { arg out=0, sustain=1, decay=0, pan=0, freq=440, vibrato=0.5, vrate=7, voice=0, perc=0, percf=2, amp=(-12.dbamp), gate=1, fade=1;
  var snd, stopFade, fadeEnv;
  var freqs, amps, sound, click, env, ampscale, attrel;
  attrel = (sustain/2).clip(0,0.005);
  env = EnvGen.ar(Env.linen(attrel, sustain-(2*attrel), attrel), doneAction: 0);
  freqs = [0.5, 1.4988, 1, 2, 2.9976, 4, 5.0409, 5.9953, 8] * freq;
  freqs = 2**(freqs < 63) * freqs; // fold up bottom register
  freqs = freqs / (2**(freqs > 6000)); // fold down high harmonics
  freqs = freqs / (2**(freqs > 6000)); // do it again for the really high notes
  amps = SelectX.kr(voice, #[
    [1, 4, 5, 4, 3, 1, 0, 0, 0], // 0: bass violin 16'
    [0, 0, 8, 0, 4, 0, 0, 0, 0], // 1: tibia 8'
    [0, 7, 8, 1, 2, 0, 0, 0, 0], // 2: bassoon 8'
    [0, 0, 7, 8, 8, 8, 8, 7, 2], // 3: french trumpet 8'
    [4, 0, 5, 5, 4, 5, 3, 3, 6], // 4: string ensemble
    [8, 8, 5, 3, 2, 4, 5, 8, 8], // 5: Blues
    [8, 8, 8, 0 ,0, 0, 0, 0, 3], // 6: Jazz 1
    [8, 8, 8, 8, 8, 8, 8, 8, 8], // 7: Full Shout
    [8, 0, 0, 0, 0, 0, 8, 8, 8], // 8: Bro' Jack
    [0, 0, 8, 8, 0, 0, 0, 0, 0]  // 9: Jazz 2
  ]);
  amps = amps - [0, 0, 0, 0, 0, 0, 0.5, 1, 1.5]; // damp brilliance a bit
  amps = 2**(amps-8);
  click = WhiteNoise.ar(1) * XLine.ar(1,1e-6, 0.1);
  sound = 0.5 * Mix.ar( SinOsc.ar(freqs*(2*click+1), (2pi ! 9).rand, amps/amps.sum) );
  sound = perc * 0.5 * SinOsc.ar(freq*percf, 2pi.rand) * XLine.ar(1,1e-6,2*decay+1) + sound;
  sound = sound + BAllPass.ar(sound, 1000*LFTri.kr(vrate,0,vibrato/2,1));
  snd = Pan2.ar(sound * env * amp, pan);
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
