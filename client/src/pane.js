// ColliderPane — SPEC §6 "collider pane". Maps the bridge's raw cc/note state
// (/api/collider) onto every board control's lit value and emits it through
// `onLit(control, value)`. value is 0..1 for sliders/rotaries (from locCC),
// 0/1 for buttons (from note on/off), and a four-corner array 0..1 each for
// pads (pressure spread across xCC/yCC, LATCHED after release so the pad
// stays aglow after touch; null only before its first press). A control the
// board has reported nothing for is null, which draws dark — silence is not
// position 0, because 0 lights the rotary rings and the crossfader window.
// The pane carries no three.js dependency; the renderer subscribes via onLit.

import { controlFraction, padCorners } from './board.js';

export class ColliderPane {
  /**
   * @param {Array<object>} controls normalized board controls (from board.js)
   * @param {{segments?: number}} [opts] reserved — segment count lives in the renderer
   */
  constructor(controls, { segments = 8 } = {}) {
    this.controls = controls;
    this.segments = segments;
    this.onLit = null; // (control, value) => void
    this._padLatch = new Map(); // control id -> last lit corners (pads latch)
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
      const value = control.kind === 'pad'
        ? this._padValue(control, cc, note)
        : controlFraction(control, cc, note);
      if (this.onLit) this.onLit(control, value);
      applied++;
    }
    return applied;
  }

  /**
   * A pad latches: it lights from the live x/y/pressure while pressed and
   * keeps that lighting after the note lifts (the physical QuNeo leaves the
   * pad's corners aglow after touch). Returns the four-corner array, or null
   * before the pad has ever been touched.
   */
  _padValue(control, cc, note) {
    const corners = padCorners(control, cc, note);
    if (corners != null) {
      this._padLatch.set(control.id, corners);
      return corners;
    }
    return this._padLatch.get(control.id) ?? null;
  }

  /** Poll the endpoint once and apply the result. */
  async poll(get = undefined) {
    const fetchState = get || (await import('./api.js')).getState;
    const state = await fetchState();
    this.applyState(state);
    return state;
  }

  /**
   * Forget every latched pad and push an all-dark frame.
   *
   * "Reset Board" means the three.js board goes dark. An emptied state reports
   * nothing for any control, and a control with nothing reported draws dark,
   * so every light goes out; dropping the pad latch is what darkens pads still
   * holding their last-lit corners.
   */
  clearLit() {
    this._padLatch.clear();
    return this.applyState({ cc: {}, note: {} });
  }
}
