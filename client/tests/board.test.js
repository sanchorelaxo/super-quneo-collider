// Collider board model tests — SPEC §6 "The three.js board mirrors the live
// QuNeo LED state". The model layer (normalizeLayout, indexById, ccFraction,
// controlFraction) is pure and imports no three.js, so these run with no
// renderer. Channel is per-control (rotaries override to 14), so a ch15 pad
// xCC/yCC cannot collide with a ch14 rotary locCC.

import { test, assert, assertEqual } from './harness.js';
import {
  loadLayout,
  normalizeLayout,
  indexById,
  ccFraction,
  controlFraction,
  padQuadrant,
} from '../src/board.js';

const INLINE = {
  units: 'mm',
  channel: 15,
  board: { w: 241, h: 185, thickness: 9.5 },
  controls: [
    { id: 'vSliderButton0', kind: 'vslider', shape: 'pill_track', cx_mm: 19.2, cy_mm: 151.8, w_mm: 11.9, h_mm: 48, noteNum: 20, pressCC: 60, locCC: 61, param: 'wobble', min: 0, max: 10 },
    { id: 'padButton0', kind: 'pad', shape: 'rounded_square', cx_mm: 30, cy_mm: 30, w_mm: 22, h_mm: 22, noteNum: 0, pressCC: 0, xCC: 1, yCC: 2 },
    { id: 'rotaryButton0', kind: 'rotary', shape: 'drum_circle', cx_mm: 90, cy_mm: 90, w_mm: 30, h_mm: 30, noteNum: 0, pressCC: 0, locCC: 1, channel: 14 },
    { id: 'buttonButton9', kind: 'button', shape: 'up_down_arrows', cx_mm: 120, cy_mm: 30, w_mm: 10, h_mm: 10 },
  ],
};

test('normalizeLayout computes world coords centred on the board', () => {
  const layout = normalizeLayout(INLINE);
  assertEqual(layout.board.w, 241, 'board width');
  assertEqual(layout.board.h, 185, 'board height');
  assertEqual(layout.controls.length, 4, 'four controls');
  const c0 = layout.controls[0];
  assertEqual(c0.world.x, 19.2 - 120.5, 'world x = cx - w/2');
  assertEqual(c0.world.z, 151.8 - 92.5, 'world z = cy - h/2');
});

test('per-control channel override (rotary ch14) beats global ch15', () => {
  const byId = indexById(normalizeLayout(INLINE).controls);
  assertEqual(byId.get('vSliderButton0').channel, 15, 'vslider inherits global');
  assertEqual(byId.get('padButton0').channel, 15, 'pad inherits global');
  assertEqual(byId.get('rotaryButton0').channel, 14, 'rotary overrides to 14');
});

test('pad carries xCC/yCC, unmapped button carries no MIDI', () => {
  const byId = indexById(normalizeLayout(INLINE).controls);
  assertEqual(byId.get('padButton0').xCC, 1, 'pad xCC');
  assertEqual(byId.get('padButton0').yCC, 2, 'pad yCC');
  assertEqual(byId.get('buttonButton9').noteNum, null, 'unmapped button: no note');
  assertEqual(byId.get('buttonButton9').locCC, null, 'unmapped button: no locCC');
});

test('ccFraction maps raw CC 0..127 onto 0..1 and clamps', () => {
  assertEqual(ccFraction(0), 0, '0 -> 0');
  assertEqual(ccFraction(127), 1, '127 -> 1');
  assertEqual(Math.abs(ccFraction(64) - 64 / 127) < 1e-9, true, '64 -> 64/127');
  assertEqual(ccFraction(200), 1, 'clamps above 127');
  assertEqual(ccFraction(-5), 0, 'clamps below 0');
});

test('controlFraction: a slider lights from its own channel locCC', () => {
  const vslider = indexById(normalizeLayout(INLINE).controls).get('vSliderButton0');
  const cc = { 15: { 61: 95 } };
  const f = controlFraction(vslider, cc, {});
  assertEqual(Math.abs(f - 95 / 127) < 1e-9, true, 'fraction = 95/127');
});

test('controlFraction: rotary ch14 ignores the ch15 cc that shares its number', () => {
  const rotary = indexById(normalizeLayout(INLINE).controls).get('rotaryButton0');
  const cc = { 14: { 1: 127 }, 15: { 1: 0 } };
  assertEqual(controlFraction(rotary, cc, {}), 1, 'reads ch14 locCC 1, not ch15 cc 1');
});

test('padQuadrant: stays lit after the note goes off (x/y latches)', () => {
  const pad = indexById(normalizeLayout(INLINE).controls).get('padButton0');
  // The QuNeo latches x/y (Return = -1), so the corner persists after release.
  assertEqual(padQuadrant(pad, { 15: { 1: 127, 2: 127 } }), 3, 'x/y latched -> still top-right');
  assertEqual(padQuadrant(pad, { 15: { 1: 0, 2: 0 } }), 0, 'x/y latched -> still bottom-left');
});

test('padQuadrant: dark (null) only before x/y has been reported', () => {
  const pad = indexById(normalizeLayout(INLINE).controls).get('padButton0');
  assertEqual(padQuadrant(pad, {}), null, 'no cc -> dark');
  assertEqual(padQuadrant(pad, { 15: {} }), null, 'no x/y on channel -> dark');
  assertEqual(padQuadrant(pad, { 15: { 1: 127 } }), null, 'x only, no y -> dark');
  assertEqual(padQuadrant(pad, { 15: { 2: 127 } }), null, 'y only, no x -> dark');
});

test('padQuadrant: xCC left + yCC bottom resolves to bottom-left (0)', () => {
  const pad = indexById(normalizeLayout(INLINE).controls).get('padButton0');
  assertEqual(padQuadrant(pad, { 15: { 1: 0, 2: 0 } }), 0, 'x low + y low -> 0');
});

test('padQuadrant: xCC right + yCC bottom resolves to bottom-right (1)', () => {
  const pad = indexById(normalizeLayout(INLINE).controls).get('padButton0');
  assertEqual(padQuadrant(pad, { 15: { 1: 127, 2: 0 } }), 1, 'x high + y low -> 1');
});

test('padQuadrant: xCC left + yCC top resolves to top-left (2)', () => {
  const pad = indexById(normalizeLayout(INLINE).controls).get('padButton0');
  assertEqual(padQuadrant(pad, { 15: { 1: 0, 2: 127 } }), 2, 'x low + y high -> 2');
});

test('padQuadrant: xCC right + yCC top resolves to top-right (3)', () => {
  const pad = indexById(normalizeLayout(INLINE).controls).get('padButton0');
  assertEqual(padQuadrant(pad, { 15: { 1: 127, 2: 127 } }), 3, 'x high + y high -> 3');
});

test('padQuadrant reads its own channel (ch15 xCC/yCC, not ch14)', () => {
  const pad = indexById(normalizeLayout(INLINE).controls).get('padButton0');
  // ch14 rotary locCC 1 must not leak into the ch15 pad xCC
  assertEqual(padQuadrant(pad, { 15: { 1: 127, 2: 127 }, 14: { 1: 0 } }), 3, 'ch15 top-right wins');
});

test('controlFraction: an unmapped button is always dark', () => {
  const button = indexById(normalizeLayout(INLINE).controls).get('buttonButton9');
  assertEqual(controlFraction(button, {}, { 15: { 100: true } }), 0, 'no binding -> dark');
});

test('loadLayout reads the full 38-control board', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  assertEqual(layout.controls.length, 38, '38 physical controls');
  const byId = indexById(layout.controls);
  assertEqual(byId.get('padButton0').noteNum, 0, 'pad0 note 0');
  assertEqual(byId.get('padButton0').channel, 15, 'pad0 channel 15');
  assertEqual(byId.get('rotaryButton0').channel, 14, 'rotary0 channel 14');
  assertEqual(byId.get('rotaryButton0').locCC, 1, 'rotary0 locCC 1');
  assertEqual(byId.get('rotaryButton1').locCC, 9, 'rotary1 locCC 9');
  assertEqual(byId.get('lSliderButton0').locCC, 49, 'lSlider locCC 49');
  assertEqual(byId.get('hSliderButton0').locCC, 93, 'hSlider0 locCC 93');
  assertEqual(byId.get('vSliderButton2').param, 'releaseTime', 'vslider2 param');
});
