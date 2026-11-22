// Zero-build browser test harness for the collider client's ES modules.
// Mirrors the queneo-editor 3d-web harness: test() registers, runAll()
// executes each against a timeout, and window.__TESTS__ publishes
// [{name, ok, error}] for a CDP driver (or a human) to read. Tests exercise
// the same modules index.html boots, with fetch stubbed where a server is
// involved, but here `loadLayout` can hit the real file over HTTP.

export const registry = [];

export function test(name, fn) {
  registry.push({ name, fn });
}

export function assert(cond, msg) {
  if (!cond) throw new Error(msg || 'assertion failed');
}

export function assertEqual(actual, expected, msg) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) {
    throw new Error(`${msg || 'not equal'}: actual=${a} expected=${e}`);
  }
}

/** Run every registered test; one hang cannot block the rest. */
export async function runAll(timeoutMs = 5000) {
  const results = [];
  for (const t of registry) {
    try {
      await Promise.race([
        Promise.resolve().then(() => t.fn()),
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error(`timed out after ${timeoutMs}ms`)), timeoutMs);
        }),
      ]);
      results.push({ name: t.name, ok: true });
    } catch (err) {
      results.push({ name: t.name, ok: false, error: String((err && err.message) || err) });
    }
  }
  window.__TESTS__ = results;
  return results;
}
