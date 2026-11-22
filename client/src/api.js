// Thin client for the bridge's /api/collider endpoint, which returns the live
// synth-parameter state as JSON: { present: bool, sliders: { param: value } }.
// `present` reflects whether the backend report is live (true once the synth
// and QuNeo watcher are up), not whether the board is physically connected.

export async function getState(url = '/api/collider') {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) {
    throw new Error(`/api/collider failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
