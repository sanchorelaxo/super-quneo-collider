// ColliderPane — the SPEC §6 "collider pane". Maps synth parameter values from
// /api/collider onto the board model's sliders and computes their lit segments.
// It emits through an `onLit(control, litSegments, fraction)` callback so the
// pane itself carries no three.js dependency; the renderer subscribes to it.

import { litFraction } from './board.js';

export class ColliderPane {
  /**
   * @param {Array<object>} controls normalized board controls (from board.js)
   * @param {{segments?: number}} [opts]
   */
  constructor(controls, { segments = 8 } = {}) {
    this.segments = segments;
    this.byParam = new Map(); // param name -> control
    this.values = new Map();  // param name -> latest value
    this.onLit = null;        // (control, litSegments, fraction) => void
    for (const c of controls) {
      if (c.param != null) this.byParam.set(c.param, c);
    }
  }

  /** Apply a single param=value pair. Returns false when the param is unbound. */
  apply(param, value) {
    const control = this.byParam.get(param);
    if (!control) return false;
    this.values.set(param, value);
    const fraction = litFraction(control, value);
    const lit = fraction == null ? 0 : Math.round(fraction * this.segments);
    if (this.onLit) this.onLit(control, lit, fraction);
    return true;
  }

  /** Apply a full /api/collider state object. Returns count of params applied. */
  applyState(state) {
    const sliders = (state && state.sliders) || {};
    let applied = 0;
    for (const [param, value] of Object.entries(sliders)) {
      if (this.apply(param, value)) applied++;
    }
    return applied;
  }

  /** Poll the endpoint once and apply the result. */
  async poll(get = undefined) {
    const fetchState = get || (await import('./api.js')).getState;
    const state = await fetchState();
    this.applyState(state);
    return state;
  }
}
