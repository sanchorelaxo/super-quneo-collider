// Test doubles for the browser harness — mirrors queneo-editor 3d-web fixtures.
// No server involved: `stubFetch` swaps global fetch so getState() can be tested
// against a deterministic /api/collider payload.

export function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function stubFetch({ routes = {}, calls = null } = {}) {
  const origin = globalThis.fetch;
  globalThis.fetch = async (url, opts) => {
    if (calls) calls.push({ url, opts });
    for (const [pattern, handler] of Object.entries(routes)) {
      if (String(url).includes(pattern)) return jsonResponse(handler);
    }
    return jsonResponse({});
  };
  return {
    restore() { globalThis.fetch = origin; },
  };
}
