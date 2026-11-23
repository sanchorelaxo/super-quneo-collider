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

// Choosing an example POSTs its id; the bridge replies with the full new state
// (activeExample, helper, sliders) so the client re-renders in one round trip.
// Selection is a control-plane event: it never flashes a preset or sends MIDI.
export async function selectExample(id, url = '/api/collider/example') {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id }),
  });
  if (!res.ok) {
    throw new Error(`selecting ${id} failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// The fade checkbox posts the ceiling's on/off state. Turning it off lets a
// voice ring past 12 s; turning it on restores the forced fade. Either way the
// bridge fades out whatever is already sounding, and replies with the new state.
export async function setFade(enabled, url = '/api/collider/fade') {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) {
    throw new Error(`setting the fade to ${enabled} failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
