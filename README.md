# DSTU Assistant 🎓

Личный ассистент по учёбе: Telegram-бот + REST API + (позже) веб/PWA.
Расписание с чётными/нечётными неделями, переносами и отменами пар,
захват лекций с автоэкспортом в **Obsidian**, задачи с дедлайнами,
напоминания и утренний бриф.

Хостинг — Raspberry Pi 4B, всё в Docker. Один пользователь (владелец).

## Архитектура

```
   Telegram-бот ─┐
                 ├─▶  Backend (FastAPI + aiogram)  ─▶  SQLite
   Веб/PWA ──────┘        (один код, 2 контейнера)   ─▶  папка Markdown
                                                          └▶ Syncthing ▶ Obsidian
```

| Компонент | Технологии |
|-----------|-----------|
| API | FastAPI, SQLAlchemy 2 (async), aiosqlite |
| Бот | aiogram 3 (на кнопках), APScheduler (напоминания/бриф) |
| БД | SQLite (WAL, общий том для api и bot) |
| Экспорт | Markdown → Obsidian vault (папки по предметам + Daily) |

## Запуск на Raspberry Pi

```bash
git clone https://github.com/sudxxt-afk/dstu_assistant.git
cd dstu_assistant
cp .env.example .env
nano .env            # вписать BOT_TOKEN и API_TOKEN

docker compose up -d --build
```

**Первый вход:** напиши боту в Telegram — он ответит твоим числовым ID.
Впиши его в `.env` → `ALLOWED_USER_ID`, затем:

```bash
docker compose up -d        # перезапуск бота с новым ID
```

Теперь бот отвечает только тебе. Кнопки: Сегодня / Завтра / Неделя /
Следующая / Лекция / Задачи / Настройки.

## Obsidian

Том `app_data` монтирует `/data/vault` — это и есть хранилище заметок.
Папку `vault` синхронизируй **Syncthing**'ом в свой Obsidian vault
(или укажи путь к vault напрямую томом в `docker-compose.yml`).

Структура:
```
vault/
├── <Предмет>/<YYYY-MM-DD>.md   # заметки лекций + вложения
└── Daily/<YYYY-MM-DD>.md       # утренняя заметка: расписание + задачи
```

## Наполнение расписания

Пока — через REST API (заголовок `X-API-Token`). Веб-панель — следующий этап.

```bash
# предмет
curl -H "X-API-Token: $API_TOKEN" -H "Content-Type: application/json" \
  -X POST localhost:8000/api/subjects -d '{"name":"Матан","teacher":"Иванов"}'

# пара: weekday 1=Пн..7=Вс, parity every|odd|even
curl -H "X-API-Token: $API_TOKEN" -H "Content-Type: application/json" \
  -X POST localhost:8000/api/lessons \
  -d '{"subject_id":1,"type":"лекция","weekday":1,"pair_number":2,"room":"301","parity":"odd"}'
```

Доки API: `http://<pi>:8000/docs`

### Настройки семестра
Чётность недели считается от даты начала семестра (`PUT /api/config`).
`week1_is_odd` — является ли первая неделя семестра нечётной.
Расписание звонков — `PUT /api/bells`.

## Безопасность
- Токен бота и `API_TOKEN` лежат только в `.env` (в git не коммитятся).
- Доступ к боту — только по `ALLOWED_USER_ID`.
- Наружу API лучше выставлять через Cloudflare Tunnel (HTTPS), а не голым портом.

## Статус / дорожная карта
- [x] Бэкенд, бот на кнопках, расписание, лекции→Obsidian, задачи, напоминания, бриф
- [ ] Веб-панель / PWA (ввод расписания, пуши)
- [ ] Редактирование расписания прямо из бота
