// Socket.IO via the WebUI brick's client (libs/arduino.js), plus REST helpers.

export function connect({ onConnect, onDisconnect, handlers }) {
  const ui = new WebUI({ transports: ["websocket", "polling"] });
  ui.on_connect(onConnect);
  ui.on_disconnect(onDisconnect);
  for (const [event, fn] of Object.entries(handlers)) ui.on_message(event, fn);
  return ui;
}

async function request(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not JSON */ }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  status: () => request("GET", "/api/status"),
  config: () => request("GET", "/api/config"),
  putConfig: (changes) => request("PUT", "/api/config", changes),
  zero: () => request("POST", "/api/zero"),
  trigger: () => request("POST", "/api/record/trigger"),
  swings: () => request("GET", "/api/swings"),
  swing: (id) => request("GET", `/api/swings/${encodeURIComponent(id)}`),
  deleteSwing: (id) => request("DELETE", `/api/swings/${encodeURIComponent(id)}`),
  csvUrl: (id) => `/api/swings/${encodeURIComponent(id)}.csv`,
};
