"""Демонстрация работы сервиса, в том числе POST запроса.

Запуск: python demo.py [адрес сервиса]
По умолчанию используется http://127.0.0.1:8000
"""
import json
import sys
from datetime import date, timedelta

import httpx

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def show(response: httpx.Response, expected: int) -> dict | list:
    request = response.request
    print(f"{request.method} {request.url} -> {response.status_code}")
    if request.content:
        print("тело запроса:", request.content.decode())
    data = response.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print()
    assert response.status_code == expected, f"ожидался статус {expected}"
    return data


def main() -> None:
    # первый запрос с большим таймаутом: бесплатный хостинг может просыпаться до минуты
    with httpx.Client(base_url=BASE_URL, timeout=90) as client:
        show(client.get("/health"), 200)

        print("query параметры")
        show(client.get("/services", params={"category": "nails", "sort": "price"}), 200)

        print("path параметр")
        show(client.get("/services/3"), 200)

        day = (date.today() + timedelta(days=30)).isoformat()
        slots = show(client.get("/slots", params={"service_id": 3, "day": day}), 200)

        print("POST запрос с телом")
        body = {
            "client_name": "Иван",
            "phone": "+79991234567",
            "service_id": 3,
            "day": day,
            "time": slots["free"][0],
            "comment": "demo.py",
        }
        booking = show(client.post("/bookings", json=body), 201)

        print("повторная запись на тот же слот")
        show(client.post("/bookings", json=body), 409)

        print("некорректное тело запроса")
        show(client.post("/bookings", json={**body, "phone": "123"}), 422)

        show(client.get(f"/bookings/{booking['id']}"), 200)

        print("отмена записи")
        show(client.delete(f"/bookings/{booking['id']}"), 200)


if __name__ == "__main__":
    main()
