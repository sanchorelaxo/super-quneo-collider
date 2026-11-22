// Board model — pure, no three.js import. Everything here is derived from
// LAYOUT.json (and mirrors the backend's mapping.json MIDI params), so the
// model layer is testable in the browser harness without a renderer.
//
// World-space conversion (millimetres, origin at the board top-left, y down):
//   world x = cx_mm - board.w / 2    (right is +x)
//   world z = cy_mm - board.h / 2    (front edge is +z)
//   world y = 0 is the board's top face

export async function loadLayout(url = './LAYOUT.json') {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`LAYOUT.json failed to load: ${res.status} ${res.statusText}`);
  return normalizeLayout(await res.json());
}

export function normalizeLayout(raw) {
  const b = raw.board;
  if (!b || !b.w || !b.h) throw new Error('LAYOUT.json is missing board dimensions');
  const channel = raw.channel ?? null;
  const controls = (raw.controls || []).map((c) => ({
    id: c.id,
    kind: c.kind,
    shape: c.shape,
    channel,
    noteNum: c.noteNum ?? null,
    pressCC: c.pressCC ?? null,
    locCC: c.locCC ?? null,
    param: c.param ?? null,
    min: c.min ?? null,
    max: c.max ?? null,
    cx_mm: c.cx_mm,
    cy_mm: c.cy_mm,
    w_mm: c.w_mm,
    h_mm: c.h_mm,
    world: {
      x: c.cx_mm - b.w / 2,
      y: 0,
      z: c.cy_mm - b.h / 2,
    },
  }));
  return {
    units: raw.units || 'mm',
    board: { w: b.w, h: b.h, thickness: b.thickness ?? 9.5, corner_radius: b.corner_radius ?? 6 },
    controls,
  };
}

/** Convenience lookup by control id. */
export function indexById(controls) {
  const map = new Map();
  for (const c of controls) map.set(c.id, c);
  return map;
}

/** Fraction of the control's param range a value occupies, clamped to [0, 1]. */
export function litFraction(control, value) {
  if (control.param == null || control.min == null || control.max == null) return null;
  const span = control.max - control.min;
  if (span <= 0) return 0;
  return Math.min(1, Math.max(0, (value - control.min) / span));
}

/** Number of lit LED segments for a value; 0 when the control is unbound. */
export function litSegments(control, value, segments = 8) {
  const f = litFraction(control, value);
  if (f == null) return 0;
  return Math.round(f * segments);
}
