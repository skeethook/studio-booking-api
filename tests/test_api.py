from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import WORK_HOURS, db

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture(autouse=True)
def clean_db():
    db.reset()
    yield
    db.reset()


@pytest.fixture
def client():
    return TestClient(app)


def booking_body(**changes):
    body = {
        "client_name": "Иван",
        "phone": "+79991234567",
        "service_id": 3,
        "day": TOMORROW,
        "time": "12:00",
        "comment": "тест",
    }
    body.update(changes)
    return body


# служебные ручки


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# услуги: query и path параметры


def test_services_default(client):
    response = client.get("/services")
    assert response.status_code == 200
    assert len(response.json()) == 8


def test_services_filter_category(client):
    items = client.get("/services", params={"category": "nails"}).json()
    assert [s["id"] for s in items] == [3, 4]


def test_services_filter_max_price(client):
    items = client.get("/services", params={"max_price": 1800}).json()
    assert all(s["price"] <= 1800 for s in items)
    assert {s["id"] for s in items} == {3, 5, 6}


def test_services_sort_by_price(client):
    prices = [s["price"] for s in client.get("/services", params={"sort": "price"}).json()]
    assert prices == sorted(prices)


def test_services_limit(client):
    items = client.get("/services", params={"limit": 2}).json()
    assert len(items) == 2


def test_services_combined_query(client):
    items = client.get(
        "/services", params={"category": "hair", "max_price": 3000, "sort": "price"}
    ).json()
    assert [s["id"] for s in items] == [1]


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 51},
        {"max_price": -1},
        {"sort": "color"},
        {"category": "unknown"},
    ],
)
def test_services_invalid_query(client, params):
    assert client.get("/services", params=params).status_code == 422


def test_service_by_id(client):
    response = client.get("/services/3")
    assert response.status_code == 200
    assert response.json()["name"] == "Маникюр"


def test_service_not_found(client):
    assert client.get("/services/999").status_code == 404


def test_service_invalid_path(client):
    assert client.get("/services/abc").status_code == 422
    assert client.get("/services/0").status_code == 422


# слоты


def test_slots_all_free(client):
    data = client.get("/slots", params={"service_id": 3, "day": TOMORROW}).json()
    assert data["free"] == WORK_HOURS
    assert data["busy"] == []
    assert data["category"] == "nails"


def test_slots_after_booking(client):
    client.post("/bookings", json=booking_body())
    data = client.get("/slots", params={"service_id": 3, "day": TOMORROW}).json()
    assert "12:00" in data["busy"]
    assert "12:00" not in data["free"]


def test_slots_other_category_not_affected(client):
    client.post("/bookings", json=booking_body())
    data = client.get("/slots", params={"service_id": 1, "day": TOMORROW}).json()
    assert data["busy"] == []


def test_slots_service_not_found(client):
    response = client.get("/slots", params={"service_id": 999, "day": TOMORROW})
    assert response.status_code == 404


def test_slots_past_day(client):
    response = client.get("/slots", params={"service_id": 3, "day": YESTERDAY})
    assert response.status_code == 400


def test_slots_missing_params(client):
    assert client.get("/slots").status_code == 422
    assert client.get("/slots", params={"service_id": 3}).status_code == 422
    assert client.get("/slots", params={"service_id": 3, "day": "не дата"}).status_code == 422


# записи: body параметры


def test_create_booking(client):
    response = client.post("/bookings", json=booking_body())
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "active"
    assert data["service_name"] == "Маникюр"
    assert data["price"] == 1800
    assert data["day"] == TOMORROW


def test_create_booking_without_comment(client):
    body = booking_body()
    del body["comment"]
    response = client.post("/bookings", json=body)
    assert response.status_code == 201
    assert response.json()["comment"] is None


def test_create_booking_slot_taken(client):
    assert client.post("/bookings", json=booking_body()).status_code == 201
    response = client.post("/bookings", json=booking_body(client_name="Анна"))
    assert response.status_code == 409


def test_create_booking_same_time_other_category(client):
    assert client.post("/bookings", json=booking_body()).status_code == 201
    response = client.post("/bookings", json=booking_body(service_id=1))
    assert response.status_code == 201


def test_create_booking_wrong_time(client):
    response = client.post("/bookings", json=booking_body(time="09:30"))
    assert response.status_code == 400


def test_create_booking_past_day(client):
    response = client.post("/bookings", json=booking_body(day=YESTERDAY))
    assert response.status_code == 400


def test_create_booking_unknown_service(client):
    response = client.post("/bookings", json=booking_body(service_id=999))
    assert response.status_code == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"client_name": "И"},
        {"phone": "123"},
        {"phone": "телефон"},
        {"service_id": 0},
        {"day": "завтра"},
        {"time": "9:00"},
        {"comment": "x" * 201},
    ],
)
def test_create_booking_validation(client, changes):
    response = client.post("/bookings", json=booking_body(**changes))
    assert response.status_code == 422


def test_create_booking_empty_body(client):
    assert client.post("/bookings", json={}).status_code == 422


def test_get_booking(client):
    created = client.post("/bookings", json=booking_body()).json()
    response = client.get(f"/bookings/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_booking_not_found(client):
    assert client.get("/bookings/42").status_code == 404


def test_list_bookings_filters(client):
    other_day = (date.today() + timedelta(days=2)).isoformat()
    client.post("/bookings", json=booking_body(time="10:00"))
    client.post("/bookings", json=booking_body(time="11:00"))
    client.post("/bookings", json=booking_body(day=other_day))
    assert len(client.get("/bookings").json()) == 3
    assert len(client.get("/bookings", params={"day": TOMORROW}).json()) == 2
    assert len(client.get("/bookings", params={"status": "cancelled"}).json()) == 0
    assert client.get("/bookings", params={"status": "done"}).status_code == 422


def test_list_bookings_sorted(client):
    client.post("/bookings", json=booking_body(time="15:00"))
    client.post("/bookings", json=booking_body(time="10:00"))
    times = [b["time"] for b in client.get("/bookings").json()]
    assert times == ["10:00", "15:00"]


def test_cancel_booking(client):
    created = client.post("/bookings", json=booking_body()).json()
    response = client.delete(f"/bookings/{created['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert client.get(f"/bookings/{created['id']}").json()["status"] == "cancelled"


def test_cancel_frees_slot(client):
    created = client.post("/bookings", json=booking_body()).json()
    client.delete(f"/bookings/{created['id']}")
    data = client.get("/slots", params={"service_id": 3, "day": TOMORROW}).json()
    assert "12:00" in data["free"]
    assert client.post("/bookings", json=booking_body()).status_code == 201


def test_cancel_twice(client):
    created = client.post("/bookings", json=booking_body()).json()
    client.delete(f"/bookings/{created['id']}")
    assert client.delete(f"/bookings/{created['id']}").status_code == 409


def test_cancel_not_found(client):
    assert client.delete("/bookings/42").status_code == 404


def test_phone_rejects_non_ascii_digits(client):
    response = client.post("/bookings", json=booking_body(phone="٠٩٩٩١٢٣٤٥٦٧"))
    assert response.status_code == 422


def test_time_rejects_non_ascii_digits(client):
    response = client.post("/bookings", json=booking_body(time="١٢:٠٠"))
    assert response.status_code == 422


def test_name_with_only_spaces_rejected(client):
    assert client.post("/bookings", json=booking_body(client_name="   ")).status_code == 422


def test_name_is_stripped(client):
    response = client.post("/bookings", json=booking_body(client_name="  Иван  "))
    assert response.status_code == 201
    assert response.json()["client_name"] == "Иван"


def test_same_slot_from_many_threads(client):
    from concurrent.futures import ThreadPoolExecutor

    def send(_):
        return client.post("/bookings", json=booking_body()).status_code

    with ThreadPoolExecutor(max_workers=16) as pool:
        codes = list(pool.map(send, range(32)))
    assert codes.count(201) == 1
    assert codes.count(409) == 31
