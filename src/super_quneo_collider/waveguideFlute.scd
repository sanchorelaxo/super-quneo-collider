// Synthdefs/flute.scd — everythingwillbetakenaway/Synthdefs (https://github.com/everythingwillbetakenaway/Synthdefs), by everythingwillbetakenaway; license: none stated
// SPEC §9.9 import, reshaped per §9.9.2. gesture: continuous
SynthDef("waveguideFlute", { arg out=0, scl=0.2, freq=440, ipress=0.9, ibreath=0.09, ifeedbk1=0.4, ifeedbk2=0.4, dur=1, amp=2, gate=1, fade=1;
  var snd, stopFade, fadeEnv;
 

  var kenv1, kenv2, kenvibr, kvibr, sr, cr, block;
  var poly, signalOut, ifqc;
  var aflow1, asum1, asum2, afqc, atemp1, ax, apoly, asum3, avalue, atemp2, aflute1;
  var fdbckArray;

  sr = SampleRate.ir;
  cr = ControlRate.ir;
  block = cr.reciprocal;

  ifqc = freq;

  // noise envelope
  kenv1 = EnvGen.kr(Env.new(
    [ 0.0, 1.1 * ipress, ipress, ipress, 0.0 ], [ 0.06, 0.2, dur - 0.46, 0.2 ], 'linear' )
  );
  // overall envelope
  kenv2 = EnvGen.kr(Env.new(
    [ 0.0, amp, amp, 0.0 ], [ 0.1, dur - 0.02, 0.1 ], 'linear' ), doneAction: 0
  );
  // vibrato envelope
  kenvibr = EnvGen.kr(Env.new( [ 0.0, 0.0, 1, 1, 0.0 ], [ 0.5, 0.5, dur - 1.5, 0.5 ], 'linear') );

  // create air flow and vibrato
  aflow1 = LFClipNoise.ar( sr, kenv1 );
  kvibr = SinOsc.ar( 5, 0, 0.1 * kenvibr );

  asum1 = ( ibreath * aflow1 ) + kenv1 + kvibr;
  afqc = ifqc.reciprocal - ( asum1/20000 ) - ( 9/sr ) + ( ifqc/12000000 ) - block;

  fdbckArray = LocalIn.ar( 1 );

  aflute1 = fdbckArray;
  asum2 = asum1 + ( aflute1 * ifeedbk1 );

  //ax = DelayL.ar( asum2, ifqc.reciprocal * 0.5, afqc * 0.5 );
  ax = DelayC.ar( asum2, ifqc.reciprocal - block * 0.5, afqc * 0.5 - ( asum1/ifqc/cr ) + 0.001 );

  apoly = ax - ( ax.cubed );
  asum3 = apoly + ( aflute1 * ifeedbk2 );
  avalue = LPF.ar( asum3, 2000 );

  aflute1 = DelayC.ar( avalue, ifqc.reciprocal - block, afqc );

  fdbckArray = [ aflute1 ];

  LocalOut.ar( fdbckArray );

  signalOut = avalue;
  snd = [ signalOut * kenv2, signalOut * kenv2 ];
  stopFade = EnvGen.kr(Env.asr(0.01, 1, 3), gate, doneAction: 0);
  fadeEnv = EnvGen.kr(Env.new([0, 1, 1, 0], [0.01, 9, 3], 'lin'), 1, doneAction: 0);
  snd = snd * stopFade * Select.kr(fade > 0, [1, fadeEnv]);
  DetectSilence.ar(snd, 0.0001, 0.5, doneAction: 2);
  Out.ar(out, snd);
});
