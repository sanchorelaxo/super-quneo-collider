// Collider board model tests — SPEC §6 "The three.js board lights the slider".
// The model layer (normalizeLayout, indexById, litFraction, litSegments) is pure
// and imports no three.js, so these run against the real modules with no renderer.

import { test, assert, assertEqual } from './harness.js';
import {
  loadLayout,
  normalizeLayout,
  indexById,
  litFraction,
  litSegments,
} from '../src/board.js';

// Mirrors LAYOUT.json: global channel, per-control MIDI + param bindings.
const INLINE = {
  units: 'mm',
  channel: 15,
  board: { w: 241, h: 185, thickness: 9.5, corner_radius: 6 },
  controls: [
    { id: 'vSliderButton0', kind: 'vslider', shape: 'pill_track', cx_mm: 19.2, cy_mm: 151.8, w_mm: 11.9, h_mm: 48, pressCC: 60, locCC: 61, param: 'wobble', min: 0, max: 10 },
    { id: 'vSliderButton1', kind: 'vslider', shape: 'pill_track', cx_mm: 38.0, cy_mm: 151.8, w_mm: 11.9, h_mm: 48, pressCC: 68, locCC: 69, param: 'innerWobble', min: 0, max: 16 },
    { id: 'vSliderButton2', kind: 'vslider', shape: 'pill_track', cx_mm: 56.9, cy_mm: 151.8, w_mm: 11.9, h_mm: 48, pressCC: 76, locCC: 77, param: 'releaseTime', min: 2, max: 6 },
    { id: 'vSliderButton3', kind: 'vslider', shape: 'pill_track', cx_mm: 75.7, cy_mm: 151.8, w_mm: 11.9, h_mm: 48, pressCC: 84, locCC: 85 },
  ],
};

test('normalizeLayout computes world coords centred on the board', () => {
  const layout = normalizeLayout(INLINE);
  assertEqual(layout.board.w, 241, 'board width');
  assertEqual(layout.board.h, 185, 'board height');
  assertEqual(layout.controls.length, 4, 'four sliders');
  const c0 = layout.controls[0];
  assertEqual(c0.world.x, 19.2 - 120.5, 'world x = cx - w/2');
  assertEqual(c0.world.z, 151.8 - 92.5, 'world z = cy - h/2');
});

test('model lookup exposes channel 15, pressCC and locCC per slider', () => {
  const byId = indexById(normalizeLayout(INLINE).controls);
  const expected = {
    vSliderButton0: [60, 61],
    vSliderButton1: [68, 69],
    vSliderButton2: [76, 77],
    vSliderButton3: [84, 85],
  };
  for (const [id, [pressCC, locCC]] of Object.entries(expected)) {
    const c = byId.get(id);
    assert(c, `control ${id} present`);
    assertEqual(c.channel, 15, `${id} channel`);
    assertEqual(c.pressCC, pressCC, `${id} pressCC`);
    assertEqual(c.locCC, locCC, `${id} locCC`);
  }
});

test('litFraction maps a value onto its param range', () => {
  const byId = indexById(normalizeLayout(INLINE).controls);
  assertEqual(litFraction(byId.get('vSliderButton0'), 5.0), 0.5, 'wobble 5.0 -> 0.5');
  assertEqual(litFraction(byId.get('vSliderButton1'), 16.0), 1.0, 'innerWobble 16.0 -> 1.0');
  assertEqual(litFraction(byId.get('vSliderButton2'), 2.0), 0.0, 'releaseTime 2.0 -> 0.0');
});

test('litFraction clamps values outside the range', () => {
  const byId = indexById(normalizeLayout(INLINE).controls);
  const wobble = byId.get('vSliderButton0');
  assertEqual(litFraction(wobble, -1), 0, 'below min clamps to 0');
  assertEqual(litFraction(wobble, 11), 1, 'above max clamps to 1');
});

test('litFraction is null for an unbound control', () => {
  const byId = indexById(normalizeLayout(INLINE).controls);
  assertEqual(litFraction(byId.get('vSliderButton3'), 0.5), null, 'no param -> null');
});

test('litSegments counts lit LEDs proportionally', () => {
  const byId = indexById(normalizeLayout(INLINE).controls);
  assertEqual(litSegments(byId.get('vSliderButton0'), 5.0, 8), 4, '0.5 of 8 -> 4');
  assertEqual(litSegments(byId.get('vSliderButton1'), 16.0, 8), 8, '1.0 of 8 -> 8');
  assertEqual(litSegments(byId.get('vSliderButton2'), 2.0, 8), 0, '0.0 of 8 -> 0');
});

test('loadLayout reads the real LAYOUT.json and normalizes four sliders', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  assertEqual(layout.controls.length, 4, 'four vertical sliders in the file');
  const byId = indexById(layout.controls);
  assertEqual(byId.get('vSliderButton0').channel, 15, 'channel from the file');
  assertEqual(byId.get('vSliderButton2').pressCC, 76, 'pressCC from the file');
  assertEqual(byId.get('vSliderButton1').param, 'innerWobble', 'param from the file');
});
