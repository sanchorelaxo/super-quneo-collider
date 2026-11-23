// Renderer tests — run against real WebGL in the browser harness. buildBoard
// builds a light for every control kind (vslider/hslider/lslider ladders,
// rotary ring, pad four-quadrant faces, button single face). Each light
// exposes setLit(value): sliders/rotaries take a 0..1 fraction, buttons take
// 0/1, pads take a quadrant 0..3 (or null for dark). The test can pin lighting
// direction without a running animate() loop. Direction contract: sliders fill
// from their LOW end — vsliders bottom-up (toward the top of the board),
// hsliders left-to-right (toward the right).

import { test, assert, assertEqual } from './harness.js';
import { loadLayout } from '../src/board.js';
import { buildBoard, SEGMENTS, RING } from '../src/render.js';

const LIT = 0xff5522;

function lit(mesh) {
  return mesh.material.emissive.getHex() === LIT;
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

test('a pad is four quadrant faces lit one at a time', async () => {
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
    light.setLit(null); // note off
    assertEqual(light.meshes.filter(lit).length, 0, 'all dark when null');
    light.setLit(0); // bottom-left
    assertEqual(light.meshes.filter(lit).length, 1, 'one quadrant lit');
    assert(lit(light.meshes[0]), 'quadrant 0 (bottom-left) lit');
    assert(!lit(light.meshes[3]), 'top-right stays dark');
    light.setLit(3); // top-right
    assert(lit(light.meshes[3]), 'quadrant 3 (top-right) lit');
    assert(!lit(light.meshes[0]), 'bottom-left now dark');
  } finally {
    board.dispose();
    container.remove();
  }
});

test('a rotary renders a RING of segments with one position indicator', async () => {
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
    light.setLit(1);
    assert(lit(light.meshes[RING - 1]), 'max value sits on the last segment');
    light.setLit(0.5);
    assertEqual(light.meshes.filter(lit).length, 1, 'exactly one lit at mid');
  } finally {
    board.dispose();
    container.remove();
  }
});
