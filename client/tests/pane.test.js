// ColliderPane tests — SPEC §6 scenario 2: "collider pane applies param=value"
// and lights the slider proportionally. The pane emits through an onLit
// callback, so it is exercised without three.js.

import { test, assert, assertEqual } from './harness.js';
import { normalizeLayout, indexById } from '../src/board.js';
import { ColliderPane } from '../src/pane.js';
import { getState } from '../src/api.js';
import { stubFetch } from './fixture.js';

const INLINE = {
  units: 'mm',
  channel: 15,
  board: { w: 241, h: 185 },
  controls: [
    { id: 'vSliderButton0', kind: 'vslider', cx_mm: 19.2, cy_mm: 151.8, pressCC: 60, locCC: 61, param: 'wobble', min: 0, max: 10 },
    { id: 'vSliderButton1', kind: 'vslider', cx_mm: 38.0, cy_mm: 151.8, pressCC: 68, locCC: 69, param: 'innerWobble', min: 0, max: 16 },
    { id: 'vSliderButton2', kind: 'vslider', cx_mm: 56.9, cy_mm: 151.8, pressCC: 76, locCC: 77, param: 'releaseTime', min: 2, max: 6 },
    { id: 'vSliderButton3', kind: 'vslider', cx_mm: 75.7, cy_mm: 151.8, pressCC: 84, locCC: 85 },
  ],
};

function makePane() {
  const controls = normalizeLayout(INLINE).controls;
  const calls = [];
  const pane = new ColliderPane(controls, { segments: 8 });
  pane.onLit = (control, litSegments, fraction) => calls.push({ id: control.id, litSegments, fraction });
  return { pane, calls, byId: indexById(controls) };
}

test('apply lights a slider proportionally to its param value', () => {
  const { pane, calls } = makePane();
  assertEqual(pane.apply('wobble', 5.0), true, 'bound param applies');
  assertEqual(calls.length, 1, 'one lit callback');
  assertEqual(calls[0].id, 'vSliderButton0', 'correct control');
  assertEqual(calls[0].litSegments, 4, '0.5 of 8 segments');
});

test('apply honors the releaseTime lower bound as unlit', () => {
  const { pane, calls } = makePane();
  pane.apply('releaseTime', 2.0);
  assertEqual(calls[0].litSegments, 0, 'releaseTime 2.0 -> 0 segments');
});

test('apply lights full when a value hits the param max', () => {
  const { pane, calls } = makePane();
  pane.apply('innerWobble', 16.0);
  assertEqual(calls[0].litSegments, 8, 'innerWobble 16.0 -> all 8 segments');
});

test('apply is a no-op for an unknown param', () => {
  const { pane, calls } = makePane();
  assertEqual(pane.apply('notAParam', 1.0), false, 'unknown param ignored');
  assertEqual(calls.length, 0, 'no lit callback');
});

test('applyState lights every control in the state payload', () => {
  const { pane, calls } = makePane();
  const applied = pane.applyState({ present: true, sliders: { wobble: 5.0, innerWobble: 8.0 } });
  assertEqual(applied, 2, 'two bound params applied');
  const litIds = calls.map((c) => c.id).sort();
  assertEqual(litIds, ['vSliderButton0', 'vSliderButton1'], 'both controls lit');
});

test('applyState handles an absent board (present false)', () => {
  const { pane, calls } = makePane();
  const applied = pane.applyState({ present: false, sliders: {} });
  assertEqual(applied, 0, 'nothing to light');
  assertEqual(calls.length, 0, 'no callbacks');
});

test('getState parses the /api/collider payload', async () => {
  const stub = stubFetch({ routes: { '/api/collider': { present: true, sliders: { wobble: 5.0 } } } });
  try {
    const state = await getState();
    assertEqual(state.present, true, 'present flag');
    assertEqual(state.sliders.wobble, 5.0, 'wobble value');
  } finally {
    stub.restore();
  }
});
