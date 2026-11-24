// AdminButtons — the two controls in the page's bottom right corner.
//
// "Reset Board" blanks the board: the bridge reloads the QuNeo's preset (the
// only thing that also clears the rotaries and the cross fader, which light
// themselves and survive a sweep of remote messages) and forgets the state it
// had mirrored.  The page then drops the pane's latched pads, so the three.js
// board goes dark with the hardware.
//
// "Restart Server" asks the bridge to replace itself.  A bridge answers before
// it goes, so its own reply cannot say whether the new copy is up: the button
// stays disabled, the page keeps polling, and `observe()` settles it when a
// different boot id answers.  The hand-over is an `execve`, which keeps the pid,
// so a pid is only the fallback tell for a bridge that reports no boot id.
//
// The bridge calls are passed in, so this module holds no fetch of its own.

/**
 * @param {{reset: HTMLElement, restart: HTMLElement, note: HTMLElement}} refs
 * @param {{resetBoard: () => Promise<object>, restartServer: () => Promise<object>}} api
 * @param {{onReset?: (state: object) => void, resetOnLoad?: boolean}} [hooks]
 *   onReset gets the emptied state the bridge replied with, i.e. what the pane
 *   should now show.  resetOnLoad fires one reset as the page mounts, so a load
 *   starts dark instead of lit from whatever the bridge still had mirrored.
 */
export function mountAdmin(
  { reset, restart, note },
  { resetBoard, restartServer },
  { onReset = () => {}, resetOnLoad = false } = {},
) {
  let busy = false;
  let waiting = null; // {boot, pid} of the bridge that is on its way out

  function say(text, kind = '') {
    if (!note) return;
    note.textContent = text;
    note.className = kind;
  }

  function release() {
    busy = false;
    if (reset) reset.disabled = false;
    if (restart) restart.disabled = false;
  }

  async function doReset() {
    if (busy) return false;
    busy = true;
    if (reset) reset.disabled = true;
    try {
      const state = await resetBoard();
      onReset(state);
      say('board reset', 'ok');
      return true;
    } catch (err) {
      say(err.message, 'bad');
      return false;
    } finally {
      busy = false;
      if (reset) reset.disabled = false;
    }
  }

  async function doRestart() {
    if (busy) return false;
    busy = true;
    if (restart) restart.disabled = true;
    say('restarting the bridge…');
    try {
      const state = await restartServer();
      // What the page has to see replaced before this is done: the boot id of
      // the bridge that answered, plus its pid for a bridge with no boot id.
      waiting =
        state && (state.boot || state.pid != null)
          ? { boot: state.boot ?? null, pid: state.pid ?? null }
          : null;
      if (!waiting) {
        // A bridge with nothing to compare: let the page's own poll speak.
        release();
        say('restart asked for', 'ok');
      }
      return true;
    } catch (err) {
      say(err.message, 'bad');
      release();
      return false;
    }
  }

  /** Called from the page's poll: a bridge answered, so say what came back. */
  function observe(state) {
    if (!waiting || !state) return;
    const booted = state.boot != null && state.boot !== waiting.boot;
    const swapped =
      state.boot == null && state.pid != null && waiting.pid != null && state.pid !== waiting.pid;
    if (!booted && !swapped) return;
    const up = state.uptime_s;
    waiting = null;
    release();
    say(up == null ? 'bridge restarted' : `bridge restarted (up ${up} s)`, 'ok');
  }

  if (reset) reset.addEventListener('click', doReset);
  if (restart) restart.addEventListener('click', doRestart);

  // A page load is a fresh start: the board is still holding whatever the last
  // session left lit, and the bridge reloads the cc/note it mirrored from its
  // state file, so the first poll would light sliders and rotaries from that
  // session.  Resetting as the page mounts puts both back to dark.  It is one
  // SysEx, and the board answers it by blinking pad 1 ("preset loaded").
  if (resetOnLoad) doReset();

  return { resetBoard: doReset, restartServer: doRestart, observe };
}
