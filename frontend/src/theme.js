// Тема: "system" (по настройке ОС) | "light" | "dark". Хранится в localStorage,
// применяется атрибутом data-theme на <html> (токены в styles/tokens.css).
import { ref } from "vue";

const KEY = "theme";
const COLORS = { light: "#faf9f5", dark: "#141413" };

function read() {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export const theme = ref(read());

function apply(mode) {
  const root = document.documentElement;
  if (mode === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", mode);

  // цвет системной строки браузера: явная тема перекрывает media-варианты
  document.querySelectorAll('meta[name="theme-color"]').forEach((m) => {
    const media = m.getAttribute("media") || "";
    const own = media.includes("dark") ? "dark" : "light";
    m.setAttribute("content", COLORS[mode === "system" ? own : mode]);
  });
}

export function setTheme(mode) {
  theme.value = mode;
  try {
    if (mode === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, mode);
  } catch {
    /* хранилище недоступно — тема действует до перезагрузки */
  }
  apply(mode);
}

export const initTheme = () => apply(theme.value);
