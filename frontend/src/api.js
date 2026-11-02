const DEFAULT_BASE = `${location.protocol}//${location.hostname}:8000/api`;

export const apiBase = () => localStorage.getItem("api_base") || DEFAULT_BASE;
export const getToken = () => localStorage.getItem("api_token") || "";
export const setToken = (t) => localStorage.setItem("api_token", t);
export const setBase = (b) => (b ? localStorage.setItem("api_base", b) : localStorage.removeItem("api_base"));
export const clearAuth = () => localStorage.removeItem("api_token");

async function req(method, path, body) {
  const res = await fetch(apiBase() + path, {
    method,
    headers: { "X-API-Token": getToken(), "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) throw { status: 401, message: "Неверный токен" };
  if (!res.ok) throw { status: res.status, message: await res.text() };
  const txt = await res.text();
  return txt ? JSON.parse(txt) : null;
}

export const api = {
  get: (p) => req("GET", p),
  post: (p, b) => req("POST", p, b),
  put: (p, b) => req("PUT", p, b),
  patch: (p, b) => req("PATCH", p, b),
  del: (p) => req("DELETE", p),
};
