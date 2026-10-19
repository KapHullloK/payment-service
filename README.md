# Payment service

Сервис платежей на FastAPI и PostgreSQL. Суммы в API указаны в копейках.

## Запуск

Нужны Docker и Docker Compose. Скопируйте пример настроек и замените
`DATABASE_PASSWORD` и `WEBHOOK_SECRET`:

```sh
cp .env.example .env
docker compose up
```

`DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USERNAME`, `DATABASE_PASSWORD` и
`DATABASE_NAME` задают подключение к PostgreSQL. В Compose хост и порт внутри
сети автоматически становятся `db:5432`. `APP_HOST`, `APP_PORT` и `APP_RELOAD`
управляют запуском API; порт Compose следует за `APP_PORT`. `WEBHOOK_SECRET` —
общий секрет для подписи уведомлений банка. Локальный `.env` исключён из Git и
Docker-образа.

Compose передаёт переменные API из `.env` через `env_file`. Для PostgreSQL
значения `DATABASE_*` сопоставляются с необходимыми ему `POSTGRES_*` в
`compose.yaml`.

Compose ждёт готовности PostgreSQL, запускает одноразовый сервис `migrate` и
после успешного применения миграций запускает API на `http://localhost:8000`.
Применить миграции повторно при работающем API можно командой:

```sh
docker compose run --rm migrate
```

## Запросы к API

На новой базе тарифы получают ID `1`, `2`, `3`. Если база уже использовалась,
возьмите актуальные ID из ответа `/tariffs`, а ID платежа — из ответа
`POST /payments`.

```sh
curl http://localhost:8000/tariffs

curl -i -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: course-001' \
  --data-binary '{"tariff_id":1,"email":"student@example.com","method":"card","promo_code":"kvitto10"}'

curl -i -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  --data-binary '{"tariff_id":2,"email":"installment@example.com","method":"installment","installment_months":3}'

curl http://localhost:8000/payments/1
curl http://localhost:8000/payments
curl 'http://localhost:8000/payments?email=student%40example.com'
curl 'http://localhost:8000/payments?status=pending'
curl 'http://localhost:8000/payments?email=student%40example.com&status=pending'
```

Повторный `POST /payments` с тем же `Idempotency-Key` вернёт существующий платёж.

Для вебхука задайте `PAYMENT_ID` из ответа создания платежа. Подпись
вычисляется по исходным байтам `BODY` с секретом из контейнера API;
`curl --data-binary` отправляет ровно это же тело:

```sh
PAYMENT_ID=1
BODY=$(printf '{"payment_id":%s,"status":"succeeded"}' "$PAYMENT_ID")
SIGNATURE=$(printf '%s' "$BODY" | docker compose exec -T api python -c 'import hashlib, hmac, os, sys; print(hmac.new(os.environ["WEBHOOK_SECRET"].encode(), sys.stdin.buffer.read(), hashlib.sha256).hexdigest())')

curl -i -X POST http://localhost:8000/webhooks/bank \
  -H 'Content-Type: application/json' \
  -H "X-Signature: $SIGNATURE" \
  --data-binary "$BODY"
```

Успешный переход возвращает `{"result":"ok"}`. Повторное уведомление о том же
статусе возвращает `409` и `{"error":"invalid_transition"}`.

## Тесты и проверки

Для локальных тестов нужны Python 3.12+ и Poetry, для интеграционных — ещё и
Docker. Интеграционные тесты сами поднимают отдельную PostgreSQL-базу через
Testcontainers и применяют миграции.

```sh
poetry install
poetry run pytest -q tests/test_pricing.py
poetry run pytest -q tests/test_api.py tests/test_database.py tests/test_webhook.py
poetry run pytest -q
poetry run ruff check .
```

GitHub Actions выполняет Ruff и все тесты при каждом `push`.
