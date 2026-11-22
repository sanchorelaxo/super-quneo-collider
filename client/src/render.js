// Renderer for the collider board — three.js, no build step. Builds a dark
// board slab plus one LED ladder per vertical slider, and lights a ladder's
// segments to reflect a param value. Kept separate from the pane/model so the
// pure logic stays renderer-free.

import * as THREE from '../vendor/three.module.js';

export const SEGMENTS = 8;

const LIT = 0xff5522;    // lit segment colour (amber)
const UNLIT = 0x232330;  // unlit segment colour (dark grey)

/**
 * Build the board scene in `container`. Returns a handle with `sliderSegments`
 * (Map id → Mesh[]) plus an `animate()` loop and a `dispose()`.
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

  const sliderSegments = new Map();
  for (const c of layout.controls) {
    const segments = buildLadder(c);
    for (const m of segments) scene.add(m);
    sliderSegments.set(c.id, segments);
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
    sliderSegments,
    animate,
    dispose() {
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      if (renderer.domElement.parentNode === container) container.removeChild(renderer.domElement);
    },
  };
}

/** One vertical slider as an array of SEGMENTS boxes, stacked bottom-up in z. */
function buildLadder(control) {
  const segH = control.h_mm / SEGMENTS;
  const zTop = control.world.z - control.h_mm / 2;
  const baseMat = new THREE.MeshStandardMaterial({ color: UNLIT, roughness: 0.6, emissive: 0x000000 });

  const segments = [];
  for (let i = 0; i < SEGMENTS; i++) {
    const mat = baseMat.clone();
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(control.w_mm, 0.6, segH - 0.4),
      mat,
    );
    mesh.position.set(control.world.x, 0.35, zTop + segH / 2 + i * segH);
    segments.push(mesh);
  }
  return segments;
}

/** Light the first `litCount` segments of a ladder; clear the rest. */
export function lightSegments(segments, litCount) {
  segments.forEach((m, i) => {
    const on = i < litCount;
    m.material.emissive.setHex(on ? LIT : 0x000000);
    m.material.emissiveIntensity = on ? 1.1 : 0;
    m.material.color.setHex(on ? LIT : UNLIT);
  });
}
