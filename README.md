# Payment service

API платежей на FastAPI и PostgreSQL. Денежные суммы указаны в копейках.

## Запуск

Нужны Docker и Docker Compose. Скопируйте пример настроек в `.env`, замените
`DATABASE_PASSWORD` и `WEBHOOK_SECRET`, затем запустите сервис:

```sh
cp .env.example .env
docker compose up --build
```

Compose запустит PostgreSQL, применит миграции и откроет API на
`http://localhost:8000` (или на порту из `APP_PORT` в `.env`).

## Тесты

Нужны Python 3.12+, Poetry и работающий Docker: интеграционные тесты сами
запускают PostgreSQL через Testcontainers.

```sh
poetry install
poetry run pytest -q
```

## Примеры запросов

Получить тарифы:

```sh
curl http://localhost:8000/tariffs
```

Создать платёж (подставьте `tariff_id` из ответа `/tariffs`):

```sh
curl -i -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: course-001' \
  --data-binary '{"tariff_id":1,"email":"student@example.com","method":"card","promo_code":"kvitto10"}'
```
