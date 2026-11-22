// Renderer tests — run against real WebGL in the browser harness. Verifies
// buildBoard produces a canvas + four 8-segment ladders and that lightSegments
// lights exactly N segments. No animate() loop is started here, so the test is
// deterministic.

import { test, assert, assertEqual } from './harness.js';
import { loadLayout } from '../src/board.js';
import { buildBoard, lightSegments, SEGMENTS } from '../src/render.js';

function makeContainer() {
  const el = document.createElement('div');
  el.style.width = '400px';
  el.style.height = '300px';
  document.body.appendChild(el);
  return el;
}

test('buildBoard renders a canvas and four 8-segment ladders', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const canvas = container.querySelector('canvas');
    assert(canvas, 'renderer appends a canvas');
    assertEqual(board.sliderSegments.size, 4, 'four sliders');
    for (const [id, segs] of board.sliderSegments) {
      assertEqual(segs.length, SEGMENTS, `${id} has ${SEGMENTS} segments`);
    }
  } finally {
    board.dispose();
    container.remove();
  }
});

test('lightSegments lights the first N segments and clears the rest', async () => {
  const layout = await loadLayout('../LAYOUT.json');
  const container = makeContainer();
  const board = buildBoard(layout, container);
  try {
    const segments = board.sliderSegments.get('vSliderButton0');
    lightSegments(segments, 4);
    const lit = segments.filter((m) => m.material.emissive.getHex() === 0xff5522).length;
    assertEqual(lit, 4, 'four segments lit at half range');
    const dark = segments.filter((m) => m.material.emissive.getHex() === 0x000000).length;
    assertEqual(dark, SEGMENTS - 4, 'remaining segments dark');
  } finally {
    board.dispose();
    container.remove();
  }
});
