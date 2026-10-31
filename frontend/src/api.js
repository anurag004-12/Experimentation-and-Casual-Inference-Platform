// All talking to the backend goes through this file.
// "/api" is forwarded to FastAPI by the Vite proxy we set up in Step 1.
const BASE = "/api";

// Turn a failed response into a readable error message.
async function handle(res) {
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) message = body.detail;
    } catch (_) {
      // the body wasn't JSON; keep the default message
    }
    throw new Error(message);
  }
  return res.json();
}

// Send a form (used for file uploads).
export function postForm(path, form) {
  return fetch(`${BASE}${path}`, { method: "POST", body: form }).then(handle);
}

// Send JSON (used by the simulation cards).
export function postJson(path, body) {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(handle);
}