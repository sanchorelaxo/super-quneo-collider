// ColliderPane — SPEC §6 "collider pane". Maps the bridge's raw cc/note state
// (/api/collider) onto every board control's lit fraction and emits it through
// `onLit(control, fraction)`. Fraction is 0..1: continuous controls derive it
// from their channel's locCC, pads/buttons from their channel's note on/off.
// The pane carries no three.js dependency; the renderer subscribes via onLit.

import { controlFraction } from './board.js';

export class ColliderPane {
  /**
   * @param {Array<object>} controls normalized board controls (from board.js)
   * @param {{segments?: number}} [opts] reserved — segment count lives in the renderer
   */
  constructor(controls, { segments = 8 } = {}) {
    this.controls = controls;
    this.segments = segments;
    this.onLit = null; // (control, fraction) => void
  }

  /**
   * Push one lit frame for the whole board from a /api/collider state object.
   * Emits onLit for every control (dark or lit) and returns the control count.
   */
  applyState(state) {
    const cc = (state && state.cc) || {};
    const note = (state && state.note) || {};
    let applied = 0;
    for (const control of this.controls) {
      const fraction = controlFraction(control, cc, note);
      if (this.onLit) this.onLit(control, fraction);
      applied++;
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
