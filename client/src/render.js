// Renderer for the collider board — three.js, no build step. Builds a dark
// board slab plus one light handle per physical control, and lets the caller
// drive each control's lit state via light.setLit(value), where value is a
// 0..1 fraction for sliders/rotaries, a four-corner array [bl,br,tl,tr]
// (0..1 each, or null for dark) for pads, and 0/1 for buttons. Lighting
// direction:
//   vsliders fill bottom-up (toward the top of the board),
//   hsliders fill left-to-right (toward the right),
//   the lslider (crossfader) is a 3-light window that tracks the position,
//   pads light all four corner quadrants at once, each from its own value,
//   rotaries are a RING of segments with one position indicator lit,
//   starting at north (0 degrees / 12 o'clock) and advancing clockwise.
// Colour is per-position, not a value ramp, matching the physical QuNeo:
//   sliders are an 8-light ladder of FIXED green/yellow/red (3-2-3), filled
//   from the LOW end by position — the value picks HOW MANY light, not a hue;
//   pads keep a pressure ramp per corner (green low -> yellow -> red high);
//   rotaries light their single indicator red, always;
//   the crossfader has 17 FIXED-colour lights (red/green/yellow/blue/yellow/
//   green/red) swept by a 3-light window.
// Buttons stay amber (their on state is binary, no ramp).
// Kept separate from the pane/model so the pure logic stays renderer-free.

import * as THREE from '../vendor/three.module.js';

export const SEGMENTS = 8;             // ladder lights per v/h slider
export const RING = 12;                // position segments per rotary ring
export const CROSSFADER_SEGMENTS = 17; // lights on the long crossfader

const LIT = 0xff5522;     // button "on" colour (amber) — binary controls only
const UNLIT = 0x232330;   // unlit colour (dark grey)
const Y_TOP = 0.35;       // light meshes float just above the slab face (y = 0)

const BLACK = new THREE.Color(0x000000);
const UNLIT_COLOR = new THREE.Color(UNLIT);
const BUTTON_LIT = new THREE.Color(LIT);

const RAMP_GREEN = new THREE.Color(0x00ff00);
const RAMP_YELLOW = new THREE.Color(0xffff00);
const RAMP_RED = new THREE.Color(0xff0000);
const RAMP_BLUE = new THREE.Color(0x0000ff);

/** Green -> yellow -> red over value 0..1 (the pad pressure ramp). */
export function rampColor(value) {
  const v = Math.min(1, Math.max(0, value));
  const c = new THREE.Color();
  if (v <= 0.5) c.lerpColors(RAMP_GREEN, RAMP_YELLOW, v * 2);
  else c.lerpColors(RAMP_YELLOW, RAMP_RED, (v - 0.5) * 2);
  return c;
}

// Slider ladder: 8 fixed-colour lights — 3 green, 2 yellow, 3 red — filled
// from the low end by position (the value picks HOW MANY light, not a hue).
const SLIDER_COLORS = [
  RAMP_GREEN, RAMP_GREEN, RAMP_GREEN,
  RAMP_YELLOW, RAMP_YELLOW,
  RAMP_RED, RAMP_RED, RAMP_RED,
];

// Crossfader: 17 fixed-colour lights — 3 red, 3 green, 2 yellow, 1 blue, then
// the mirror back out (2 yellow, 3 green, 3 red). A 3-light window sweeps them.
const CROSSFADER_COLORS = [
  RAMP_RED, RAMP_RED, RAMP_RED,
  RAMP_GREEN, RAMP_GREEN, RAMP_GREEN,
  RAMP_YELLOW, RAMP_YELLOW,
  RAMP_BLUE,
  RAMP_YELLOW, RAMP_YELLOW,
  RAMP_GREEN, RAMP_GREEN, RAMP_GREEN,
  RAMP_RED, RAMP_RED, RAMP_RED,
];

// Rotary position indicator is always red.
const ROTARY_LIT = RAMP_RED;

/** Set a mesh's tint from a colour (dark when off). */
function setMeshTint(mesh, color, on) {
  mesh.material.emissive.copy(on ? color : BLACK);
  mesh.material.emissiveIntensity = on ? 1.1 : 0;
  mesh.material.color.copy(on ? color : UNLIT_COLOR);
}

/** Light a mesh from a 0..1 value through the pad pressure ramp (0 = dark). */
function setMeshValue(mesh, value) {
  const on = value > 0;
  setMeshTint(mesh, rampColor(value), on);
}

/** One lit state applied to a single mesh's material (binary buttons). */
function setMeshLit(mesh, on) {
  setMeshTint(mesh, BUTTON_LIT, on);
}

/** A fresh standard material so each mesh toggles independently. */
function freshMat() {
  return new THREE.MeshStandardMaterial({ color: UNLIT, roughness: 0.6, emissive: 0x000000 });
}

/**
 * Build the board scene in `container`. Returns a handle with `lights`
 * (Map id → { kind, meshes, setLit(fraction) }), plus `animate()` and
 * `dispose()`.
 */
export function buildBoard(layout, container) {
  const { w, h, thickness } = layout.board;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0a10);

  const camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / Math.max(1, container.clientHeight),
    0.1,
    2000,
  );
  camera.position.set(0, 110, 190);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  container.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  const key = new THREE.DirectionalLight(0xffffff, 0.9);
  key.position.set(60, 160, 140);
  scene.add(key);

  // board slab — top face at y = 0, body extends downward
  const slab = new THREE.Mesh(
    new THREE.BoxGeometry(w, thickness, h),
    new THREE.MeshStandardMaterial({ color: 0x14141c, roughness: 0.85, metalness: 0.2 }),
  );
  slab.position.y = -thickness / 2;
  scene.add(slab);

  const lights = new Map();
  for (const c of layout.controls) {
    const light = buildLight(c);
    for (const mesh of light.meshes) scene.add(mesh);
    lights.set(c.id, light);
  }

  function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }

  function onResize() {
    camera.aspect = container.clientWidth / Math.max(1, container.clientHeight);
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  }
  window.addEventListener('resize', onResize);

  return {
    scene,
    camera,
    renderer,
    lights,
    animate,
    dispose() {
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      if (renderer.domElement.parentNode === container) container.removeChild(renderer.domElement);
    },
  };
}

/** Route a control to its per-kind light builder. */
function buildLight(control) {
  switch (control.kind) {
    case 'vslider':
      return buildLadder(control, 'v');
    case 'hslider':
      return buildLadder(control, 'h');
    case 'lslider':
      return buildCrossfader(control);
    case 'rotary':
      return buildRing(control);
    case 'pad':
      return buildQuadPad(control);
    case 'button':
    default:
      return buildBinary(control);
  }
}

/**
 * A slider ladder of SEGMENTS discrete blocks, each with a fixed colour
 * (green/yellow/red from the low end). `orient` 'v' stacks along z
 * (index 0 = bottom edge, filling toward the top), 'h' stacks along x
 * (index 0 = left edge, filling toward the right). `setLit` lights the FIRST
 * `fraction * SEGMENTS` blocks, so the value grows the lit run without
 * changing any block's hue.
 */
function buildLadder(control, orient) {
  const meshes = [];
  const vertical = orient === 'v';

  for (let i = 0; i < SEGMENTS; i++) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(), freshMat());
    if (vertical) {
      const segH = control.h_mm / SEGMENTS;
      const zBottom = control.world.z + control.h_mm / 2;
      mesh.geometry = new THREE.BoxGeometry(control.w_mm, 0.6, segH - 0.4);
      mesh.position.set(control.world.x, Y_TOP, zBottom - segH / 2 - i * segH);
    } else {
      const segW = control.w_mm / SEGMENTS;
      const xLeft = control.world.x - control.w_mm / 2;
      mesh.geometry = new THREE.BoxGeometry(segW - 0.4, 0.6, control.h_mm);
      mesh.position.set(xLeft + segW / 2 + i * segW, Y_TOP, control.world.z);
    }
    meshes.push(mesh);
  }

  return {
    kind: control.kind,
    meshes,
    setLit(fraction) {
      const f = Math.min(1, Math.max(0, fraction));
      const litCount = Math.round(f * SEGMENTS);
      meshes.forEach((m, i) => setMeshTint(m, SLIDER_COLORS[i], i < litCount));
    },
  };
}

/** A rotary ring of RING segments with a single red position indicator lit. */
function buildRing(control) {
  const meshes = [];
  const r = (Math.min(control.w_mm, control.h_mm) / 2) * 0.8;
  const seg = (Math.min(control.w_mm, control.h_mm) * 0.18);

  for (let i = 0; i < RING; i++) {
    // 0 degrees = north (top of the board, -z). three.js angle 0 points to
    // +x (east / 3pm), so offset by -90deg to put segment 0 at 12 o'clock.
    const angle = (i / RING) * Math.PI * 2 - Math.PI / 2;
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(seg, 0.6, seg), freshMat());
    mesh.position.set(
      control.world.x + r * Math.cos(angle),
      Y_TOP,
      control.world.z + r * Math.sin(angle),
    );
    meshes.push(mesh);
  }

  return {
    kind: control.kind,
    meshes,
    setLit(fraction) {
      const f = Math.min(1, Math.max(0, fraction));
      const idx = Math.min(RING - 1, Math.floor(f * RING));
      // The position indicator is always lit red; the other segments stay
      // dark. Unlike a slider, value 0 is still "on".
      meshes.forEach((m, i) => setMeshTint(m, ROTARY_LIT, i === idx));
    },
  };
}

/** A pad as four quadrant faces, one per touch corner. meshes[] is indexed
 *  [0]=bottom-left, [1]=bottom-right, [2]=top-left, [3]=top-right in world
 *  space (+z is the bottom edge, -x is the left edge). setLit(corners) lights
 *  each quadrant from the matching element of a [bl,br,tl,tr] 0..1 array;
 *  null leaves the whole pad dark.
 */
function buildQuadPad(control) {
  const qw = control.w_mm / 2 - 1.5; // thin gap between quadrants
  const qh = control.h_mm / 2 - 1.5;
  const cx = control.world.x;
  const cz = control.world.z;
  const ox = control.w_mm / 4;
  const oz = control.h_mm / 4;
  const offsets = [
    [-ox, oz],  // bottom-left
    [ox, oz],   // bottom-right
    [-ox, -oz], // top-left
    [ox, -oz],  // top-right
  ];
  const meshes = offsets.map(([dx, dz]) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(qw, 0.6, qh), freshMat());
    mesh.position.set(cx + dx, Y_TOP, cz + dz);
    return mesh;
  });

  return {
    kind: control.kind,
    meshes,
    setLit(corners) {
      if (corners == null) meshes.forEach((m) => setMeshValue(m, 0));
      else meshes.forEach((m, i) => setMeshValue(m, corners[i] ?? 0));
    },
  };
}

/**
 * The crossfader (lslider): 17 fixed-colour lights swept by a three-light
 * window that tracks the position (never a cumulative ladder). Each light has
 * its own hue — red/green/yellow/blue/yellow/green/red from left to right — so
 * the window's colour falls out of its position, not a repaint of the bar.
 * The window is clamped at the ends (a position at the far left/right lights
 * only two segments).
 */
function buildCrossfader(control) {
  const meshes = [];
  const segW = control.w_mm / CROSSFADER_SEGMENTS;
  const xLeft = control.world.x - control.w_mm / 2;
  for (let i = 0; i < CROSSFADER_SEGMENTS; i++) {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(segW - 0.4, 0.6, control.h_mm),
      freshMat(),
    );
    mesh.position.set(xLeft + segW / 2 + i * segW, Y_TOP, control.world.z);
    meshes.push(mesh);
  }
  return {
    kind: control.kind,
    meshes,
    setLit(fraction) {
      const f = Math.min(1, Math.max(0, fraction));
      const center = Math.round(f * (CROSSFADER_SEGMENTS - 1));
      meshes.forEach((m, i) => setMeshTint(m, CROSSFADER_COLORS[i], Math.abs(i - center) <= 1));
    },
  };
}

/** A button as a single flat face, binary lit while fraction > 0. */
function buildBinary(control) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(control.w_mm, 0.6, control.h_mm),
    freshMat(),
  );
  mesh.position.set(control.world.x, Y_TOP, control.world.z);

  return {
    kind: control.kind,
    meshes: [mesh],
    setLit(fraction) {
      setMeshLit(mesh, fraction > 0);
    },
  };
}
