// Renderer tests — run against real WebGL in the browser harness. buildBoard
// builds a light for every control kind (vslider/hslider ladders, lslider
// crossfader window, rotary ring, pad four-quadrant faces, button single
// face). Each light exposes setLit(value): sliders/rotaries take a 0..1
// fraction, buttons take 0/1, pads take a four-corner array [bl,br,tl,tr]
// (0..1 each, or null for dark). Direction contract: sliders fill from their
// LOW end — vsliders bottom-up, hsliders left-to-right. Colour is per-position,
// not a value ramp, matching the physical QuNeo: sliders are a fixed 8-light
// 3-2-3 green/yellow/red ladder; the crossfader is 17 fixed-colour lights
// swept by a 3-light window; rotaries light a single red indicator; pads keep
// a green -> yellow -> red pressure ramp on each corner.

import { test, assert, assertEqual } from './harness.js';
import { loadLayout } from '../src/board.js';
import { buildBoard, SEGMENTS, RING, CROSSFADER_SEGMENTS, rampColor } from '../src/render.js';

const GREEN = 0x00ff00;
const YELLOW = 0xffff00;
const RED = 0xff0000;
const BLUE = 0x0000ff;

function lit(mesh) {
  return mesh.material.emissiveIntensity > 0;
}

function colorOf(mesh) {
  return mesh.material.color.getHex();
}

function makeContainer() {
  const el = document.createElement('div');
  el.style.width = '400px';
  el.style.height = '300px';
  document.body.appendChild(el);
  return el;
}

test('buildBoard renders a canvas and a light for every control', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    assert(container.querySelector('canvas'), 'renderer appends a canvas');
    assertEqual(board.lights.size, 38, '38 lights, one per control');
    const kinds = new Set();
    for (const [, light] of board.lights) kinds.add(light.kind);
    for (const k of ['vslider', 'hslider', 'lslider', 'rotary', 'pad', 'button']) {
      assert(kinds.has(k), `a light of kind ${k} exists`);
    }
  } finally {
    board.dispose();
    container.remove();
  }
});

test('a vslider ladder has SEGMENTS boxes and fills bottom-up', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const light = board.lights.get('vSliderButton0');
    assertEqual(light.meshes.length, SEGMENTS, 'SEGMENTS boxes');
    // index 0 is the bottom of the board (larger world z)
    assert(light.meshes[0].position.z > light.meshes[SEGMENTS - 1].position.z, 'index 0 is the low end');
    light.setLit(0.1); // round(0.1 * 8) = 1 segment
    assertEqual(light.meshes.filter(lit).length, 1, 'one segment lit');
    assert(lit(light.meshes[0]), 'the lit segment is the bottom one');
    assert(!lit(light.meshes[SEGMENTS - 1]), 'the top segment stays dark');
  } finally {
    board.dispose();
    container.remove();
  }
});

test('a hslider ladder fills left-to-right (toward the right)', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const light = board.lights.get('hSliderButton0');
    assert(light.meshes[0].position.x < light.meshes[SEGMENTS - 1].position.x, 'index 0 is the left end');
    light.setLit(0.1);
    assertEqual(light.meshes.filter(lit).length, 1, 'one segment lit');
    assert(lit(light.meshes[0]), 'the lit segment is the leftmost');
    assert(!lit(light.meshes[SEGMENTS - 1]), 'the right segment stays dark');
  } finally {
    board.dispose();
    container.remove();
  }
});

test('sliders use a fixed 8-light 3-2-3 palette, filled by position', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const light = board.lights.get('hSliderButton0');
    light.setLit(1); // full: all 8 light, each from its fixed colour
    assertEqual(light.meshes.filter(lit).length, SEGMENTS, 'all SEGMENTS lit at 1');
    const colors = light.meshes.map(colorOf);
    assertEqual(colors[0], GREEN, 'position 1 (low) green');
    assertEqual(colors[2], GREEN, 'position 3 green');
    assertEqual(colors[3], YELLOW, 'position 4 yellow');
    assertEqual(colors[4], YELLOW, 'position 5 yellow');
    assertEqual(colors[5], RED, 'position 6 red');
    assertEqual(colors[7], RED, 'position 8 (high) red');
    // Partial fill lights only the low end, still with fixed colours.
    light.setLit(0.25); // round(0.25 * 8) = 2 segments
    assertEqual(light.meshes.filter(lit).length, 2, 'two segments lit at 0.25');
    assertEqual(colorOf(light.meshes[0]), GREEN, 'lit low segment stays green');
    assert(!lit(light.meshes[5]), 'red segment stays dark until the fill reaches it');
  } finally {
    board.dispose();
    container.remove();
  }
});

test('a pad is four quadrant faces lit from a four-corner value array', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const light = board.lights.get('padButton0');
    assertEqual(light.meshes.length, 4, 'four quadrant faces');
    // world convention: +z is the bottom edge, -x is the left edge, so
    // meshes[0] (bottom-left) sits low-right of meshes[3] (top-right).
    assert(light.meshes[0].position.z > light.meshes[2].position.z, 'bottom row is +z');
    assert(light.meshes[0].position.x < light.meshes[1].position.x, 'left column is -x');
    light.setLit(null); // no position yet (renderer darkens on null directly)
    assertEqual(light.meshes.filter(lit).length, 0, 'all dark when null');
    light.setLit([1, 0, 0, 0]); // bottom-left only
    assertEqual(light.meshes.filter(lit).length, 1, 'one quadrant lit');
    assert(lit(light.meshes[0]), 'bottom-left lit');
    assert(!lit(light.meshes[3]), 'top-right stays dark');
    assertEqual(colorOf(light.meshes[0]), RED, 'full pressure sits at the red end of the ramp');
    light.setLit([0, 0, 0, 1]); // top-right only
    assert(lit(light.meshes[3]), 'top-right lit');
    assert(!lit(light.meshes[0]), 'bottom-left now dark');
  } finally {
    board.dispose();
    container.remove();
  }
});

test('the crossfader has 17 fixed-colour lights swept by a 3-light window', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const light = board.lights.get('lSliderButton0');
    assertEqual(light.meshes.length, CROSSFADER_SEGMENTS, '17 lights');
    assert(light.meshes[0].position.x < light.meshes[CROSSFADER_SEGMENTS - 1].position.x, 'index 0 is the left end');
    light.setLit(0.5); // centre: window over indices 7, 8, 9
    assertEqual(light.meshes.filter(lit).length, 3, 'three-light window at centre');
    assertEqual(colorOf(light.meshes[7]), YELLOW, 'left of centre is yellow');
    assertEqual(colorOf(light.meshes[8]), BLUE, 'centre light is blue');
    assertEqual(colorOf(light.meshes[9]), YELLOW, 'right of centre is yellow');
    light.setLit(0.25); // centre on index 4: window over the green band 3-5
    const greenWin = light.meshes.filter(lit);
    assertEqual(greenWin.length, 3, 'three-light window over the green band');
    assert(greenWin.every((m) => colorOf(m) === GREEN), 'green band lights green');
    light.setLit(1); // full right: window clamps to two red lights
    const right = light.meshes.filter(lit);
    assertEqual(right.length, 2, 'window clamps to two lights at the right end');
    assert(right.every((m) => colorOf(m) === RED), 'right-end lights are red');
    light.setLit(0); // full left
    const left = light.meshes.filter(lit);
    assertEqual(left.length, 2, 'window clamps to two lights at the left end');
    assert(left.every((m) => colorOf(m) === RED), 'left-end lights are red');
  } finally {
    board.dispose();
    container.remove();
  }
});

test('the pad pressure ramp is green at low, yellow at mid, red at high', () => {
  assertEqual(rampColor(0).getHex(), GREEN, '0 -> green');
  assertEqual(rampColor(0.5).getHex(), YELLOW, '0.5 -> yellow');
  assertEqual(rampColor(1).getHex(), RED, '1 -> red');
  // Monotone through the ramp: green channel falls, red channel rises.
  const low = rampColor(0.1), mid = rampColor(0.5), high = rampColor(0.9);
  assert(low.g > low.r, 'low values are greener than red');
  assert(high.r > high.g, 'high values are redder than green');
});

test('a rotary renders a RING of segments with one red position indicator', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const light = board.lights.get('rotaryButton0');
    assertEqual(light.meshes.length, RING, 'RING segments');
    // 0 degrees must sit at north (the top of the board = minimum world z),
    // not east (3pm). Segment 0 is the unique topmost one after the fix.
    const zs = light.meshes.map((m) => m.position.z);
    assert(light.meshes[0].position.z === Math.min(...zs), '0 degrees sits at the north/top segment');
    light.setLit(0);
    assertEqual(light.meshes.filter(lit).length, 1, 'one segment lit at min');
    assert(lit(light.meshes[0]), 'min value sits on the first segment');
    assertEqual(colorOf(light.meshes[0]), RED, 'the indicator is red, always');
    light.setLit(1);
    assert(lit(light.meshes[RING - 1]), 'max value sits on the last segment');
    assertEqual(colorOf(light.meshes[RING - 1]), RED, 'indicator stays red at max');
    light.setLit(0.5);
    assertEqual(light.meshes.filter(lit).length, 1, 'exactly one lit at mid');
  } finally {
    board.dispose();
    container.remove();
  }
});

test('no data at all leaves the ring and the crossfader dark', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const ring = board.lights.get('rotaryButton0');
    const cross = board.lights.get('lSliderButton0');
    ring.setLit(0.25);
    cross.setLit(0.25);
    assertEqual(ring.meshes.filter(lit).length, 1, 'the ring shows a position when it has one');
    assertEqual(cross.meshes.filter(lit).length, 3, 'the crossfader shows its window');
    // null is not position 0. It is "the board has reported nothing", and on a
    // ring and on the crossfader position 0 is itself lit, so reading silence
    // as 0 leaves both aglow while the hardware is dark. The page resets the
    // board as it loads, and a reloaded board has nothing to report.
    ring.setLit(null);
    cross.setLit(null);
    assertEqual(ring.meshes.filter(lit).length, 0, 'a ring with no data is dark');
    assertEqual(cross.meshes.filter(lit).length, 0, 'a crossfader with no data is dark');
  } finally {
    board.dispose();
    container.remove();
  }
});
