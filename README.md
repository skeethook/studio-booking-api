# Studio Booking API

Домашнее задание № 6, FastAPI.
Автор: Котляров Иван Александрович

Сервис онлайн-записи в студию. В нём есть каталог услуг, свободные слоты на день и управление записями. Данные хранятся в памяти и пропадают при перезапуске.

Правила записи: слоты по часу с 10:00 до 18:00. У каждой категории услуг (hair, nails, brows, skin) свой мастер, поэтому слот занят только внутри своей категории. Записаться на прошедшую дату нельзя. Время внутри сегодняшнего дня не проверяется.

Развёрнутый сервис: https://studio-booking-api.onrender.com
Документация и запросы из браузера: https://studio-booking-api.onrender.com/docs

Бесплатный хостинг засыпает, если 15 минут нет запросов. Первый запрос после паузы может идти до минуты.

## Запуск

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Документация Swagger: http://127.0.0.1:8000/docs

## Ручки

| Метод | Путь | Параметры |
|---|---|---|
| GET | `/` | нет |
| GET | `/health` | нет |
| GET | `/services` | query: `category`, `max_price`, `sort`, `limit` |
| GET | `/services/{service_id}` | path: `service_id` |
| GET | `/slots` | query: `service_id`, `day` |
| POST | `/bookings` | body: JSON с данными записи |
| GET | `/bookings` | query: `day`, `status` |
| GET | `/bookings/{booking_id}` | path: `booking_id` |
| DELETE | `/bookings/{booking_id}` | path: `booking_id` |

Коды ответов: 200 и 201 успех, 400 нарушено правило записи (время вне слотов или дата в прошлом), 404 не найдено, 409 слот занят или запись уже отменена, 422 данные не прошли проверку.

## Пример POST-запроса

```bash
curl -X POST https://studio-booking-api.onrender.com/bookings \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Иван", "phone": "+79991234567", "service_id": 3, "day": "2026-11-02", "time": "10:00", "comment": "demo"}'
```

Ответ, статус 201:

```json
{
  "id": 1,
  "client_name": "Иван",
  "phone": "+79991234567",
  "service_id": 3,
  "service_name": "Маникюр",
  "category": "nails",
  "price": 1800,
  "day": "2026-11-02",
  "time": "10:00",
  "comment": "demo",
  "status": "active",
  "created_at": "2026-10-03T12:34:29.303338"
}
```

Если отправить такой же запрос ещё раз, придёт 409 `{"detail": "Этот слот уже занят"}`. Если телефон неверный, придёт 422.

Скрипт `demo.py` проходит весь сценарий: услуги, слоты, создание записи, конфликт слота, ошибка проверки данных, чтение и отмена записи.

```bash
python demo.py                                    # локально
python demo.py https://studio-booking-api.onrender.com   # развёрнутый сервис
```

Скрипту нужен пакет `httpx` (есть в `requirements-dev.txt`).

## Тесты

```bash
pip install -r requirements-dev.txt
pytest --cov=app
```

50 тестов, покрытие кода около 99 процентов. Тесты проверяют все ручки, фильтры в запросах, проверку данных, конфликты слотов и отмену записи.

## Деплой на Render

1. Загрузить файлы проекта в репозиторий на GitHub.
2. На render.com выбрать New, затем Blueprint, указать репозиторий. Render прочитает `render.yaml` и соберёт образ по `Dockerfile`.
3. После сборки адрес сервиса появится на странице сервиса.

## Структура

```
app/main.py      ручки и правила записи
app/models.py    модели pydantic для запросов и ответов
app/storage.py   каталог услуг и хранилище записей в памяти
tests/           тесты pytest
demo.py          демонстрация работы сервиса
Dockerfile       образ для деплоя
render.yaml      настройки Render
```
