// Renderer for the collider board — three.js, no build step. Builds a dark
// board slab plus one light handle per physical control, and lets the caller
// drive each control's lit fraction via light.setLit(0..1). Lighting direction:
//   vsliders fill bottom-up (toward the top of the board),
//   hsliders/lsliders fill left-to-right (toward the right),
//   pads/buttons are a single binary face,
//   rotaries are a RING of segments with one position indicator lit.
// Kept separate from the pane/model so the pure logic stays renderer-free.

import * as THREE from '../vendor/three.module.js';

export const SEGMENTS = 8; // ladder segments per slider
export const RING = 12;    // position segments per rotary ring

const LIT = 0xff5522;     // lit colour (amber)
const UNLIT = 0x232330;   // unlit colour (dark grey)
const Y_TOP = 0.35;       // light meshes float just above the slab face (y = 0)

/** One lit state applied to a single mesh's material. */
function setMeshLit(mesh, on) {
  mesh.material.emissive.setHex(on ? LIT : 0x000000);
  mesh.material.emissiveIntensity = on ? 1.1 : 0;
  mesh.material.color.setHex(on ? LIT : UNLIT);
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
    case 'lslider':
      return buildLadder(control, 'h');
    case 'rotary':
      return buildRing(control);
    case 'pad':
    case 'button':
    default:
      return buildBinary(control);
  }
}

/**
 * A slider ladder of SEGMENTS discrete blocks. `orient` 'v' stacks along z
 * (index 0 = bottom edge, filling toward the top), 'h' stacks along x
 * (index 0 = left edge, filling toward the right).
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
      const litCount = Math.round(Math.min(1, Math.max(0, fraction)) * SEGMENTS);
      meshes.forEach((m, i) => setMeshLit(m, i < litCount));
    },
  };
}

/** A rotary ring of RING segments with a single position indicator lit. */
function buildRing(control) {
  const meshes = [];
  const r = (Math.min(control.w_mm, control.h_mm) / 2) * 0.8;
  const seg = (Math.min(control.w_mm, control.h_mm) * 0.18);

  for (let i = 0; i < RING; i++) {
    const angle = (i / RING) * Math.PI * 2;
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
      meshes.forEach((m, i) => setMeshLit(m, i === idx));
    },
  };
}

/** A pad or button as a single flat face, binary lit while fraction > 0. */
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
