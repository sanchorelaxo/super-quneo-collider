// Admin buttons — the two controls in the page's bottom right corner, and the
// bridge calls behind them.
//
// "Reset Board" blanks the board and hands the emptied state to the page, which
// drops the pane's latched pads so the three.js board goes dark with the real
// one. "Restart Server" only clears itself once a *different* process answers
// /api/collider: the reply it gets back comes from the bridge that is about to
// be replaced, so the click cannot be settled by its own response.
//
// The bridge calls are injected, so none of this needs a server; the two api
// functions are exercised separately against a stubbed fetch.

import { test, assert, assertEqual } from './harness.js';
import { mountAdmin } from '../src/admin.js';
import { resetBoard, restartServer } from '../src/api.js';
import { jsonResponse, stubFetch } from './fixture.js';

const BLANK = { present: true, pid: 100, uptime_s: 42.5, boot: 'boot-a', cc: {}, note: {} };

function makeAdmin(api, hooks = {}) {
  const reset = document.createElement('button');
  const restart = document.createElement('button');
  const note = document.createElement('div');
  document.body.append(reset, restart, note);
  return {
    mounted: mountAdmin({ reset, restart, note }, api, hooks),
    reset,
    restart,
    note,
    cleanup() {
      reset.remove();
      restart.remove();
      note.remove();
    },
  };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

// A page load has to start dark.  The bridge keeps the cc/note it mirrored and
// reloads them from its state file, so the first poll lights sliders and
// rotaries from a session that is over, while the hardware still holds whatever
// that session left lit.  One reset at mount puts both back to dark.
test('a page load blanks the board once, without a click', async () => {
  const resets = [];
  const seen = [];
  const { reset, note, cleanup } = makeAdmin(
    {
      resetBoard: async () => {
        resets.push('reset');
        return BLANK;
      },
      restartServer: async () => BLANK,
    },
    { resetOnLoad: true, onReset: (state) => seen.push(state) },
  );
  try {
    await flush();
    assertEqual(resets.length, 1, 'reset fired on mount');
    assertEqual(seen.length, 1, 'the pane got the emptied state');
    assertEqual(note.textContent, 'board reset', 'note');
    assertEqual(reset.disabled, false, 'the button still works afterwards');
  } finally {
    cleanup();
  }
});

test('without resetOnLoad the mount is quiet', async () => {
  const resets = [];
  const { cleanup } = makeAdmin({
    resetBoard: async () => {
      resets.push('reset');
      return BLANK;
    },
    restartServer: async () => BLANK,
  });
  try {
    await flush();
    assertEqual(resets.length, 0, 'nothing sent until a click');
  } finally {
    cleanup();
  }
});

test('reset hands the emptied state back to the page', async () => {
  const seen = [];
  const { mounted, reset, note, cleanup } = makeAdmin(
    { resetBoard: async () => BLANK, restartServer: async () => BLANK },
    { onReset: (state) => seen.push(state) },
  );
  try {
    assertEqual(await mounted.resetBoard(), true, 'reports success');
    assertEqual(seen.length, 1, 'onReset called once');
    assertEqual(seen[0], BLANK, 'with the state the bridge replied');
    assertEqual(note.textContent, 'board reset', 'note');
    assertEqual(note.className, 'ok', 'marked as fine');
    assertEqual(reset.disabled, false, 'the button comes back');
  } finally {
    cleanup();
  }
});

test('reset shows the bridge reason when it refuses', async () => {
  const seen = [];
  const { mounted, reset, note, cleanup } = makeAdmin(
    {
      resetBoard: async () => {
        throw new Error('the board did not accept the reset');
      },
      restartServer: async () => BLANK,
    },
    { onReset: (state) => seen.push(state) },
  );
  try {
    assertEqual(await mounted.resetBoard(), false, 'reports failure');
    assertEqual(seen.length, 0, 'a refused reset does not blank the pane');
    assertEqual(note.textContent, 'the board did not accept the reset', 'note');
    assertEqual(note.className, 'bad', 'marked as a failure');
    assertEqual(reset.disabled, false, 'back, so it can be retried');
  } finally {
    cleanup();
  }
});

// A restart hands the process image over (os.execve), so the pid is the same one
// when the bridge comes back: what changes is the boot id it reports. That is
// the tell the button waits for, and the uptime it quotes starts over.
test('restart stays disabled until a freshly booted bridge answers', async () => {
  const { mounted, restart, note, cleanup } = makeAdmin({
    resetBoard: async () => BLANK,
    restartServer: async () => BLANK,
  });
  try {
    assertEqual(await mounted.restartServer(), true, 'accepted');
    assertEqual(restart.disabled, true, 'waiting for the bridge to come back');
    assertEqual(note.textContent, 'restarting the bridge…', 'note');

    // The bridge that took the request, still answering while it hands over.
    mounted.observe({ ...BLANK, uptime_s: 43.0 });
    assertEqual(restart.disabled, true, 'still the old process answering');
    assertEqual(note.textContent, 'restarting the bridge…', 'note unchanged');

    // Same pid, new process image.
    mounted.observe({ present: true, pid: 100, uptime_s: 0.2, boot: 'boot-b' });
    assertEqual(restart.disabled, false, 'the new process answered');
    assertEqual(note.textContent, 'bridge restarted (up 0.2 s)', 'note');
    assertEqual(note.className, 'ok', 'marked as fine');
  } finally {
    cleanup();
  }
});

test('a bridge that reports no boot id settles on the pid alone', async () => {
  const { mounted, restart, cleanup } = makeAdmin({
    resetBoard: async () => BLANK,
    restartServer: async () => ({ present: true, pid: 100, uptime_s: 42.5 }),
  });
  try {
    assertEqual(await mounted.restartServer(), true, 'accepted');
    assertEqual(restart.disabled, true, 'waiting');
    mounted.observe({ present: true, pid: 200, uptime_s: 1.0 });
    assertEqual(restart.disabled, false, 'a different process answered');
  } finally {
    cleanup();
  }
});

test('observe is quiet when no restart is in flight', async () => {
  const { mounted, restart, note, cleanup } = makeAdmin({
    resetBoard: async () => BLANK,
    restartServer: async () => BLANK,
  });
  try {
    mounted.observe({ present: true, pid: 777, uptime_s: 0.2 });
    assertEqual(note.textContent, '', 'nothing to say');
    assertEqual(restart.disabled, false, 'untouched');
  } finally {
    cleanup();
  }
});

test('a restart that cannot hand over reports why and stays usable', async () => {
  const { mounted, restart, note, cleanup } = makeAdmin({
    resetBoard: async () => BLANK,
    restartServer: async () => {
      throw new Error('cannot restart a bridge that is on an ephemeral port');
    },
  });
  try {
    assertEqual(await mounted.restartServer(), false, 'refused');
    assertEqual(restart.disabled, false, 'still usable');
    assertEqual(note.className, 'bad', 'marked as a failure');
    assert(note.textContent.includes('ephemeral'), 'the bridge reason is shown');
  } finally {
    cleanup();
  }
});

test('a click during a restart is ignored', async () => {
  const calls = [];
  let release;
  const { reset, restart, cleanup } = makeAdmin({
    resetBoard: async () => {
      calls.push('reset');
      return BLANK;
    },
    restartServer: () =>
      new Promise((resolve) => {
        release = resolve;
      }),
  });
  try {
    restart.click(); // still in flight: the bridge is going away
    reset.click();
    await flush();
    assertEqual(calls, [], 'the reset never reached the bridge');
    release(BLANK);
    await flush();
  } finally {
    cleanup();
  }
});

test('the buttons are wired to their handlers', async () => {
  const calls = [];
  const { reset, restart, cleanup } = makeAdmin({
    resetBoard: async () => {
      calls.push('reset');
      return BLANK;
    },
    restartServer: async () => {
      calls.push('restart');
      return BLANK;
    },
  });
  try {
    reset.click();
    await flush();
    restart.click();
    await flush();
    assertEqual(calls, ['reset', 'restart'], 'both clicks landed');
  } finally {
    cleanup();
  }
});

// --- the two bridge calls --------------------------------------------------

test('resetBoard posts to the reset route', async () => {
  const calls = [];
  const stub = stubFetch({ routes: { '/api/collider/reset': BLANK }, calls });
  try {
    const state = await resetBoard();
    assertEqual(state.present, true, 'reply');
    assertEqual(calls[0].url, '/api/collider/reset', 'url');
    assertEqual(calls[0].opts.method, 'POST', 'method');
  } finally {
    stub.restore();
  }
});

test('restartServer posts to the restart route', async () => {
  const calls = [];
  const stub = stubFetch({ routes: { '/api/collider/restart': { pid: 4242 } }, calls });
  try {
    const state = await restartServer();
    assertEqual(state.pid, 4242, 'reply');
    assertEqual(calls[0].url, '/api/collider/restart', 'url');
    assertEqual(calls[0].opts.method, 'POST', 'method');
  } finally {
    stub.restore();
  }
});

test('resetBoard surfaces the reason the bridge refused', async () => {
  const stub = stubFetch({
    routes: {
      '/api/collider/reset': jsonResponse({ error: 'the board did not accept the reset' }, 400),
    },
  });
  try {
    await resetBoard();
    assert(false, 'a refusal has to throw');
  } catch (err) {
    assertEqual(
      err.message,
      'resetting the board failed: the board did not accept the reset',
      'the bridge reason reaches the caller',
    );
  } finally {
    stub.restore();
  }
});
