// Example picker tests — SPEC §6 "Select a sound example" (D8) and the §9.5
// helper block. Everything the picker shows comes from the bridge's catalog, so
// these tests drive it with a catalog payload shaped like /api/collider's and
// check that an unknown-to-the-code example id flows straight through.

import { test, assert, assertEqual } from './harness.js';
import { applyPicker, exampleIds, fillOptions, helperText, mountExamplePicker } from '../src/examples.js';
import { selectExample, setFade } from '../src/api.js';
import { stubFetch } from './fixture.js';

const HELPER = [
  'vSlider0 -> fundfreq     40-10240 Hz (exp)',
  'vSlider1 -> formantfreq  40-10240 Hz (exp)',
  'vSlider2 -> bwfreq       40-10240 Hz (exp)',
  'vSlider3 -> timeScale    0.1-4.0',
  'rotary   -> pan          L..R',
];

const STATE = {
  present: true,
  activeExample: 'bubbles',
  examples: [
    { id: 'bubbles', def: 'bubbles', source: 'bubbles.js', gesture: 'continuous' },
    { id: 'formant', def: 'formant', source: 'formant.scd', gesture: 'continuous' },
    { id: 'sine', def: 'sine', source: 'sine-wave.js', gesture: 'continuous' },
    { id: 'klang', def: 'klang', source: 'klang.scd', gesture: 'continuous' },
  ],
  helper: ['vSlider0 -> wobble      0-10',
           'vSlider1 -> innerWobble 0-16',
           'vSlider2 -> releaseTime 2-6'],
};

function makePicker() {
  const select = document.createElement('select');
  const helper = document.createElement('pre');
  document.body.append(select, helper);
  return {
    select,
    helper,
    cleanup() { select.remove(); helper.remove(); },
  };
}

test('applyPicker fills the select from the catalog, in the bridge order', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    applyPicker(select, helper, STATE);
    assertEqual(exampleIds(STATE), ['bubbles', 'formant', 'sine', 'klang'], 'catalog ids');
    assertEqual([...select.options].map((o) => o.value), ['bubbles', 'formant', 'sine', 'klang'], 'options');
    assertEqual(select.value, 'bubbles', 'default selection is the active example');
  } finally {
    cleanup();
  }
});

test('applyPicker shows the helper block the bridge sent', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    const formant = { ...STATE, activeExample: 'formant', helper: HELPER };
    applyPicker(select, helper, formant);
    assertEqual(helper.textContent, HELPER.join('\n'), 'helper text');
    assert(helper.textContent.includes('rotary   -> pan'), 'pan line present');
  } finally {
    cleanup();
  }
});

test('applyPicker does not rebuild unchanged options (an open dropdown stays open)', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    applyPicker(select, helper, STATE);
    const first = select.options[0];
    applyPicker(select, helper, { ...STATE });
    assert(select.options[0] === first, 'same option element reused');
    assertEqual(select.options.length, 4, 'still four options');
  } finally {
    cleanup();
  }
});

test('applyPicker follows a selection made elsewhere', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    applyPicker(select, helper, STATE);
    const first = select.options[0];
    applyPicker(select, helper, { ...STATE, activeExample: 'klang' });
    assertEqual(select.value, 'klang', 'value follows the bridge');
    assert(select.options[0] === first, 'options were not rebuilt');
  } finally {
    cleanup();
  }
});

test('applyPicker leaves the value alone while the user is choosing', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    applyPicker(select, helper, STATE);
    select.value = 'sine'; // the user's in-flight pick
    applyPicker(select, helper, { ...STATE, activeExample: 'klang' }, { isFocused: () => true });
    assertEqual(select.value, 'sine', 'focused picker is not yanked');
  } finally {
    cleanup();
  }
});

test('the picker is data-driven: an id the code has never seen still renders', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    const future = {
      ...STATE,
      activeExample: 'kick808',
      examples: [{ id: 'kick808', def: 'kick808', source: 'SCLOrkSynths', gesture: 'oneshot' }],
      helper: ['pad3/q3 -> kick808   /s_new'],
    };
    applyPicker(select, helper, future);
    assertEqual([...select.options].map((o) => o.value), ['kick808'], 'catalog entry rendered');
    assertEqual(select.value, 'kick808', 'selected');
    assert(helper.textContent.includes('/s_new'), 'helper text rendered');
  } finally {
    cleanup();
  }
});

test('applyPicker tolerates a state with no catalog yet', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    assertEqual(fillOptions(select, {}), 0, 'no options');
    assertEqual(helperText({}), '', 'no helper text');
    applyPicker(select, helper, { present: false });
    assertEqual(select.options.length, 0, 'still empty');
    assertEqual(helper.textContent, '', 'helper cleared');
  } finally {
    cleanup();
  }
});

test('selectExample POSTs the id and returns the bridge state', async () => {
  const calls = [];
  const stub = stubFetch({
    routes: { '/api/collider/example': { ...STATE, activeExample: 'formant', helper: HELPER } },
    calls,
  });
  try {
    const state = await selectExample('formant');
    assertEqual(state.activeExample, 'formant', 'reply active example');
    assertEqual(calls.length, 1, 'one request');
    assertEqual(calls[0].opts.method, 'POST', 'POST');
    assertEqual(calls[0].opts.body, JSON.stringify({ id: 'formant' }), 'body carries the id');
    assertEqual(calls[0].opts.headers['Content-Type'], 'application/json', 'json content type');
  } finally {
    stub.restore();
  }
});

test('selectExample surfaces a rejected id', async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () => new Response('{"error":"unknown example: nope"}', { status: 400 });
  try {
    let err = null;
    try { await selectExample('nope'); } catch (e) { err = e; }
    assert(err, 'threw');
    assertEqual(err.message.includes('400'), true, 'mentions the status');
  } finally {
    globalThis.fetch = orig;
  }
});

test('mountExamplePicker re-renders the picker when an example is chosen', async () => {
  const { select, helper, cleanup } = makePicker();
  try {
    const seen = [];
    let posted = null;
    const post = async (id) => {
      posted = id;
      return { ...STATE, activeExample: id, helper: id === 'formant' ? HELPER : STATE.helper };
    };
    const render = mountExamplePicker({ select, helper, onState: (s) => seen.push(s.activeExample), post });
    render(STATE);
    select.value = 'formant';
    select.dispatchEvent(new Event('change'));
    await new Promise((r) => setTimeout(r, 10));
    assertEqual(posted, 'formant', 'posted id');
    assertEqual(select.value, 'formant', 'value held');
    assertEqual(helper.textContent, HELPER.join('\n'), 'helper text swapped');
    assertEqual(seen, ['formant'], 'onState called with the reply');
  } finally {
    cleanup();
  }
});

test('mountExamplePicker reports a failed selection instead of throwing', async () => {
  const { select, helper, cleanup } = makePicker();
  try {
    const post = async () => { throw new Error('unknown example: nope'); };
    const render = mountExamplePicker({ select, helper, post });
    render(STATE);
    select.value = 'sine';
    select.dispatchEvent(new Event('change'));
    await new Promise((r) => setTimeout(r, 10));
    assert(helper.textContent.includes('could not select sine'), `helper reports the failure, got: ${helper.textContent}`);
  } finally {
    cleanup();
  }
});

// --- the 12 s fade checkbox, beside the select ----------------------------

function makeFade() {
  const fade = document.createElement('input');
  fade.type = 'checkbox';
  document.body.append(fade);
  return fade;
}

test('applyPicker mirrors the bridge fade state into the checkbox', () => {
  const { select, helper, cleanup } = makePicker();
  const fade = makeFade();
  try {
    applyPicker(select, helper, { ...STATE, fadeEnabled: false }, { fade });
    assertEqual(fade.checked, false, 'ceiling reported off');
    applyPicker(select, helper, { ...STATE, fadeEnabled: true }, { fade });
    assertEqual(fade.checked, true, 'ceiling reported on');
    // a bridge that does not report the flag leaves the ceiling on by default
    applyPicker(select, helper, STATE, { fade });
    assertEqual(fade.checked, true, 'on unless the bridge says otherwise');
  } finally {
    cleanup();
    fade.remove();
  }
});

test('the picker still renders when no checkbox is wired up', () => {
  const { select, helper, cleanup } = makePicker();
  try {
    applyPicker(select, helper, { ...STATE, fadeEnabled: false });
    assertEqual(select.value, 'bubbles', 'selection still rendered');
  } finally {
    cleanup();
  }
});

test('changing the checkbox POSTs the new ceiling and renders the reply', async () => {
  const { select, helper, cleanup } = makePicker();
  const fade = makeFade();
  try {
    const posted = [];
    const postFade = async (enabled) => {
      posted.push(enabled);
      return { ...STATE, fadeEnabled: enabled, helper: enabled ? STATE.helper : ['ceiling off'] };
    };
    const render = mountExamplePicker({ select, helper, fade, postFade });
    render({ ...STATE, fadeEnabled: true });
    fade.checked = false;
    fade.dispatchEvent(new Event('change'));
    await new Promise((r) => setTimeout(r, 10));
    assertEqual(posted, [false], 'posted the new state');
    assertEqual(helper.textContent, 'ceiling off', 'reply rendered');
    fade.checked = true;
    fade.dispatchEvent(new Event('change'));
    await new Promise((r) => setTimeout(r, 10));
    assertEqual(posted, [false, true], 'posted both changes');
    assertEqual(helper.textContent, STATE.helper.join('\n'), 'back on');
  } finally {
    cleanup();
    fade.remove();
  }
});

test('a failed ceiling change is reported instead of thrown', async () => {
  const { select, helper, cleanup } = makePicker();
  const fade = makeFade();
  try {
    const postFade = async () => { throw new Error('enabled must be true or false'); };
    const render = mountExamplePicker({ select, helper, fade, postFade });
    render(STATE);
    fade.checked = false;
    fade.dispatchEvent(new Event('change'));
    await new Promise((r) => setTimeout(r, 10));
    assert(
      helper.textContent.includes('could not change the fade'),
      `helper reports the failure, got: ${helper.textContent}`,
    );
  } finally {
    cleanup();
    fade.remove();
  }
});

test('setFade POSTs enabled and returns the bridge state', async () => {
  const calls = [];
  const stub = stubFetch({
    routes: { '/api/collider/fade': { ...STATE, fadeEnabled: false } },
    calls,
  });
  try {
    const state = await setFade(false);
    assertEqual(state.fadeEnabled, false, 'reply carries the new state');
    assertEqual(calls.length, 1, 'one request');
    assertEqual(calls[0].opts.method, 'POST', 'POST');
    assertEqual(calls[0].opts.body, JSON.stringify({ enabled: false }), 'body carries the flag');
    assertEqual(calls[0].opts.headers['Content-Type'], 'application/json', 'json content type');
  } finally {
    stub.restore();
  }
});

test('setFade surfaces a rejected flag', async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () => new Response('{"error":"enabled must be true or false"}', { status: 400 });
  try {
    let err = null;
    try { await setFade('yes'); } catch (e) { err = e; }
    assert(err, 'threw');
    assertEqual(err.message.includes('400'), true, 'mentions the status');
  } finally {
    globalThis.fetch = orig;
  }
});
