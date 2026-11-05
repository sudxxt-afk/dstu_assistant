/**
 * Cloudflare Worker — реверс-прокси к Notion API.
 *
 * Зачем: провайдер Pi режет api.notion.com по SNI (как и Telegram), плюс
 * у хоста Pi нет IPv6-маршрута. Бэкенд ходит на этот воркер (адрес
 * *.workers.dev не блокируется), а воркер форвардит запрос в api.notion.com
 * уже из сети Cloudflare.
 *
 * Прозрачно проксирует метод, путь (/v1/...), заголовки
 * (Authorization, Notion-Version) и тело.
 *
 * Деплой (как у tg-proxy):
 *   1. https://dash.cloudflare.com -> Workers & Pages -> Create -> Worker
 *   2. Назвать (напр. notion-proxy), Deploy, затем Edit code
 *   3. Вставить этот файл целиком, Deploy
 *   4. Скопировать URL вида https://notion-proxy.<сабдомен>.workers.dev
 *      и прописать в .env: NOTION_API_BASE=https://notion-proxy.<сабдомен>.workers.dev
 */
export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.protocol = "https:";
    url.hostname = "api.notion.com";
    url.port = "";

    const proxied = new Request(url.toString(), request);
    proxied.headers.set("Host", "api.notion.com");
    return fetch(proxied);
  },
};
