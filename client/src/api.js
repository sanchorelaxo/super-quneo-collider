// Thin client for the bridge's /api/collider endpoint, which returns the live
// hardware state as JSON:
//   { present: bool, sliders: { param: value },
//     cc:   { channel: { ccNumber: value } },
//     note: { channel: { noteNumber: bool } } }
// `present` reflects whether the backend report is live (true once the synth
// and QuNeo watcher are up), not whether the board is physically connected.

export async function getState(url = '/api/collider') {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) {
    throw new Error(`/api/collider failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
