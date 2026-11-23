// ColliderPane tests — SPEC §6 "The three.js board mirrors the live QuNeo LED
// state". Lighting now derives from the raw cc/note state (not synth params):
// sliders/rotaries light from their channel's locCC, pads/buttons light from
// their channel's note on/off. The pane emits onLit(control, fraction) so it
// stays renderer-free.

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
    { id: 'vSliderButton0', kind: 'vslider', shape: 'pill_track', cx_mm: 19.2, cy_mm: 151.8, w_mm: 11.9, h_mm: 48, locCC: 61 },
    { id: 'padButton0', kind: 'pad', shape: 'rounded_square', cx_mm: 30, cy_mm: 30, w_mm: 22, h_mm: 22, noteNum: 0 },
    { id: 'rotaryButton0', kind: 'rotary', shape: 'drum_circle', cx_mm: 90, cy_mm: 90, w_mm: 30, h_mm: 30, locCC: 1, channel: 14 },
    { id: 'buttonButton9', kind: 'button', shape: 'up_down_arrows', cx_mm: 120, cy_mm: 30, w_mm: 10, h_mm: 10 },
  ],
};

function makePane() {
  const controls = normalizeLayout(INLINE).controls;
  const calls = [];
  const pane = new ColliderPane(controls, { segments: 8 });
  pane.onLit = (control, fraction) => calls.push({ id: control.id, fraction });
  return { pane, calls, byId: indexById(controls) };
}

test('applyState lights every control, returning the control count', () => {
  const { pane, calls } = makePane();
  const applied = pane.applyState({ present: true, cc: {}, note: {} });
  assertEqual(applied, 4, 'all four controls touched');
  assertEqual(calls.length, 4, 'one callback per control');
});

test('applyState maps a slider value to a locCC fraction', () => {
  const { pane, calls } = makePane();
  pane.applyState({ present: true, cc: { 15: { 61: 95 } }, note: {} });
  const v0 = calls.find((c) => c.id === 'vSliderButton0');
  assert(v0, 'vslider lit');
  assertEqual(Math.abs(v0.fraction - 95 / 127) < 1e-9, true, 'fraction = 95/127');
});

test('applyState lights a pad while its note is on, dark on release', () => {
  const { pane, calls } = makePane();
  pane.applyState({ present: true, cc: {}, note: { 15: { 0: true } } });
  assertEqual(calls.find((c) => c.id === 'padButton0').fraction, 1, 'pad lit on note-on');
  calls.length = 0;
  pane.applyState({ present: true, cc: {}, note: { 15: { 0: false } } });
  assertEqual(calls.find((c) => c.id === 'padButton0').fraction, 0, 'pad dark on note-off');
});

test('applyState lights a rotary from its ch14 locCC, not ch15', () => {
  const { pane, calls } = makePane();
  pane.applyState({ present: true, cc: { 14: { 1: 127 }, 15: { 1: 0 } }, note: {} });
  const rot = calls.find((c) => c.id === 'rotaryButton0');
  assertEqual(rot.fraction, 1, 'rotary reads ch14 locCC 1');
});

test('applyState leaves the unmapped button dark', () => {
  const { pane, calls } = makePane();
  pane.applyState({ present: true, cc: {}, note: { 15: { 100: true } } });
  const btn = calls.find((c) => c.id === 'buttonButton9');
  assertEqual(btn.fraction, 0, 'unmapped button stays dark');
});

test('applyState handles an absent board (present false)', () => {
  const { pane, calls } = makePane();
  const applied = pane.applyState({ present: false, cc: {}, note: {} });
  assertEqual(applied, 4, 'still emits a dark frame for every control');
  assertEqual(calls.every((c) => c.fraction === 0), true, 'all dark');
});

test('getState parses the /api/collider payload including cc and note', async () => {
  const stub = stubFetch({
    routes: {
      '/api/collider': {
        present: true,
        sliders: { wobble: 5.0 },
        cc: { 15: { 61: 95 } },
        note: { 15: { 0: true } },
      },
    },
  });
  try {
    const state = await getState();
    assertEqual(state.present, true, 'present flag');
    assertEqual(state.cc['15'][61], 95, 'cc value nested by channel');
    assertEqual(state.note['15'][0], true, 'note on nested by channel');
  } finally {
    stub.restore();
  }
});
