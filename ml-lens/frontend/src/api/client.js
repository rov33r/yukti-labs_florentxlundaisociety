const API_BASE = 'http://localhost:8000'

const post = (path, body) =>
  fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => r.json())

export const computeDiff = (manifest, baseParams, deltas) =>
  post('/diff/', { manifest, base_params: baseParams, deltas })
