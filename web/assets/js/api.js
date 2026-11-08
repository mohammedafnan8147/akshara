let csrfToken = null;

export function setCsrf(token) {
  csrfToken = token || null;
}

async function request(path, options = {}) {
  const { method = "GET", body, raw = false, headers = {}, signal } = options;
  const h = { ...headers };
  if (csrfToken) h["X-CSRF-Token"] = csrfToken;
  let payload = body;
  if (body != null && !raw) {
    h["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(path, {
    method, body: payload, headers: h, credentials: "same-origin", signal,
  });
  const contentType = res.headers.get("content-type") || "";
  let data = null;
  if (contentType.includes("application/json")) {
    try { data = await res.json(); } catch { data = null; }
  } else {
    data = await res.text();
  }
  if (!res.ok) {
    if (res.status === 401 && !path.includes("/login")) {
      window.dispatchEvent(new CustomEvent("akshara:unauthorized"));
    }
    const err = new Error((data && data.error) || `Request failed (${res.status})`);
    err.status = res.status;
    err.code = data?.code;
    err.details = data?.details;
    throw err;
  }
  return data;
}

export const api = {
  login: (email, password) => request("/api/login", { method: "POST", body: { email, password } }),
  demoLogin: (email) => request("/api/demo-login", { method: "POST", body: { email } }),
  logout: () => request("/api/logout", { method: "POST", body: {} }),
  session: () => request("/api/session"),
  dashboard: () => request("/api/dashboard"),
  documents: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    });
    return request("/api/documents?" + qs.toString());
  },
  document: (id) => request(`/api/documents/${encodeURIComponent(id)}`),
  updateField: (id, value) => request(`/api/fields/${encodeURIComponent(id)}`, { method: "PATCH", body: { value } }),
  action: (id, action, body = {}) => request(`/api/documents/${encodeURIComponent(id)}/${action}`, { method: "POST", body }),
  analytics: (days = 14) => request(`/api/analytics?days=${days}`),
  audit: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    });
    return request("/api/audit?" + qs.toString());
  },
  settings: () => request("/api/settings"),
  saveSettings: (updates) => request("/api/settings", { method: "PUT", body: updates }),
  resetDemo: () => request("/api/admin/reset", { method: "POST", body: {} }),
  samples: () => request("/api/intake/samples"),
  intakeDemo: (sampleId) => request("/api/intake/demo", { method: "POST", body: { sample_id: sampleId } }),
  intakeUpload: (file, docType, language = "en") => request("/api/intake/upload", {
    method: "POST",
    raw: true,
    body: file,
    headers: {
      "X-Filename": encodeURIComponent(file.name || "upload.jpg"),
      "X-Doc-Type": docType,
      "X-Doc-Language": language,
      "Content-Type": file.type || "application/octet-stream",
    },
  }),
};
