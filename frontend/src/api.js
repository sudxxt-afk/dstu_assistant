// Один ориджин: nginx проксирует /api на бэкенд. Работает и по LAN, и по HTTPS.
const DEFAULT_BASE = "/api";

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

export async function login(password) {
  const res = await fetch(apiBase() + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw { status: res.status };
  const d = await res.json();
  setToken(d.token);
}

// Загрузить защищённый файл (вложение) и вернуть blob-URL для <img> / скачивания.
async function blobUrl(path) {
  const res = await fetch(apiBase() + path, {
    headers: { "X-API-Token": getToken() },
  });
  if (!res.ok) throw { status: res.status, message: await res.text() };
  return URL.createObjectURL(await res.blob());
}

// Загрузка файла (multipart). Content-Type ставит браузер (с boundary) — не задаём.
async function upload(path, file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(apiBase() + path, {
    method: "POST",
    headers: { "X-API-Token": getToken() },
    body: fd,
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
  blobUrl,
  upload,
};
