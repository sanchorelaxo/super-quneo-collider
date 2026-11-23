// Example picker — SPEC §6 "Select a sound example" (D8). The picker is a pure
// view over the bridge's catalog: it renders whatever /api/collider reports
// (`examples`, `activeExample`, `helper`) and hard-codes no id, no parameter
// name and no range. The helper block arrives pre-formatted from the bridge,
// so the browser and the CLI can never disagree about it.
//
// Selection re-binds the control surface server-side; the picker's only job is
// to POST the id and render the reply. It sends no MIDI and flashes no preset.

import { selectExample, setFade } from './api.js';

/** The catalog's example ids, in the bridge's order. */
export function exampleIds(state) {
  return ((state && state.examples) || []).map((e) => e.id);
}

/**
 * Replace the <select>'s options with the catalog's examples. Rebuilding the
 * options on every 500 ms poll would close an open dropdown, so an unchanged
 * list is left alone.
 */
export function fillOptions(select, state) {
  const ids = exampleIds(state);
  const have = [...select.options].map((o) => o.value);
  if (have.length === ids.length && have.every((id, i) => id === ids[i])) {
    return have.length;
  }
  select.textContent = '';
  for (const id of ids) {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = id;
    select.append(opt);
  }
  return ids.length;
}

/** The helper block as plain text (the bridge already padded the columns). */
export function helperText(state) {
  return ((state && state.helper) || []).join('\n');
}

/**
 * Render a state object into the picker: options, selected value, helper text,
 * and the fade checkbox. `isFocused` is injectable so "don't yank the value
 * while the user is choosing" is testable without depending on browser window
 * focus. `fade` is the checkbox, if the page has one; a bridge that does not
 * report `fadeEnabled` leaves the ceiling on, which is its default.
 */
export function applyPicker(
  select,
  helper,
  state,
  { isFocused = () => select === document.activeElement, fade = null } = {},
) {
  fillOptions(select, state);
  if (!isFocused() && state && state.activeExample) select.value = state.activeExample;
  if (fade) fade.checked = !state || state.fadeEnabled !== false;
  helper.textContent = helperText(state);
  return select.value;
}

/**
 * Wire the picker to the bridge: a change POSTs the picked id, renders the
 * reply, and hands it to `onState`. The fade checkbox beside the select does
 * the same for the 12 s ceiling. A failure is reported in the helper block
 * rather than thrown into the poll loop (the next poll re-renders the truth).
 */
export function mountExamplePicker({
  select,
  helper,
  fade = null,
  onState,
  post = selectExample,
  postFade = setFade,
}) {
  const render = (state) => applyPicker(select, helper, state, { fade });

  select.addEventListener('change', async () => {
    const wanted = select.value;
    try {
      const state = await post(wanted);
      render(state);
      if (onState) onState(state);
    } catch (err) {
      helper.textContent = `could not select ${wanted}: ${err.message}`;
    }
  });

  if (fade) {
    fade.addEventListener('change', async () => {
      const enabled = fade.checked;
      try {
        const state = await postFade(enabled);
        render(state);
        if (onState) onState(state);
      } catch (err) {
        helper.textContent = `could not change the fade: ${err.message}`;
      }
    });
  }

  return render;
}
