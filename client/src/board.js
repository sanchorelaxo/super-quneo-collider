// Board model — pure, no three.js import. Everything here is derived from
// LAYOUT.json (device geometry merged with mapping.json's MIDI bindings), so
// the model layer is testable in the browser harness without a renderer.
//
// World-space conversion (millimetres, origin at the board top-left, y down):
//   world x = cx_mm - board.w / 2    (right is +x)
//   world z = cy_mm - board.h / 2    (top edge is -z, front/bottom edge is +z)
//   world y = 0 is the board's top face
//
// Lighting is derived from raw hardware state, not synth params:
//   - a slider or rotary lights from its channel's locCC value / 127
//   - a pad or button lights while its channel's note is on
// Channel is per-control so a ch15 pad xCC/yCC never collides with a ch14
// rotary locCC that happens to share the same number.

const CONTINUOUS_KINDS = new Set(['vslider', 'hslider', 'lslider', 'rotary']);
const BINARY_KINDS = new Set(['pad', 'button']);

export async function loadLayout(url = './LAYOUT.json') {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`LAYOUT.json failed to load: ${res.status} ${res.statusText}`);
  return normalizeLayout(await res.json());
}

export function normalizeLayout(raw) {
  const b = raw.board;
  if (!b || !b.w || !b.h) throw new Error('LAYOUT.json is missing board dimensions');
  const defaultChannel = raw.channel ?? null;
  const controls = (raw.controls || []).map((c) => ({
    id: c.id,
    kind: c.kind,
    shape: c.shape,
    channel: c.channel ?? defaultChannel,
    noteNum: c.noteNum ?? null,
    pressCC: c.pressCC ?? null,
    locCC: c.locCC ?? null,
    xCC: c.xCC ?? null,
    yCC: c.yCC ?? null,
    widthCC: c.widthCC ?? null,
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

/** Raw MIDI CC value (0..127) as a lit fraction clamped to [0, 1]. */
export function ccFraction(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value / 127));
}

/**
 * Lit fraction for a control given channel-keyed CC and note state.
 *
 * `cc`   is `{ channel: { ccNumber: value } }`.
 * `note` is `{ channel: { noteNumber: bool } }`.
 *
 * Continuous controls (sliders/rotaries) read their locCC; binary controls
 * (pads/buttons) light while their note is on. Anything without a binding
 * (e.g. an unmapped button) returns 0 and stays dark.
 */
export function controlFraction(control, cc, note) {
  const ch = control.channel;
  if (CONTINUOUS_KINDS.has(control.kind) && control.locCC != null) {
    const chCC = (cc && cc[ch]) || {};
    return ccFraction(chCC[control.locCC] ?? 0);
  }
  if (BINARY_KINDS.has(control.kind) && control.noteNum != null) {
    const chNote = (note && note[ch]) || {};
    return chNote[control.noteNum] === true ? 1 : 0;
  }
  return 0;
}
