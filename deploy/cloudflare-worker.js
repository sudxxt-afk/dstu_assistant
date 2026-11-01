/**
 * Cloudflare Worker — реверс-прокси к Telegram Bot API.
 *
 * Зачем: провайдер режет api.telegram.org по SNI. Бот ходит на этот
 * воркер (адрес *.workers.dev не блокируется), а воркер форвардит запрос
 * в api.telegram.org уже из сети Cloudflare.
 *
 * Прозрачно проксирует и методы (/bot<token>/<method>),
 * и скачивание файлов (/file/bot<token>/<path>).
 *
 * Деплой:
 *   1. https://dash.cloudflare.com → Workers & Pages → Create → Worker
 *   2. Назвать (напр. tg-proxy), Deploy, затем Edit code
 *   3. Вставить этот файл целиком, Deploy
 *   4. Скопировать URL вида https://tg-proxy.<сабдомен>.workers.dev
 */
export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.protocol = "https:";
    url.hostname = "api.telegram.org";
    url.port = "";

    const proxied = new Request(url.toString(), request);
    proxied.headers.set("Host", "api.telegram.org");
    return fetch(proxied);
  },
};
