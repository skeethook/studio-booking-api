from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query

from app.models import Booking, BookingCreate, Category, Service, SlotsResponse, Status
from app.storage import SERVICES, WORK_HOURS, db, find_service

DESCRIPTION = """
Сервис онлайн-записи в студию. В нём есть каталог услуг, свободные слоты и управление записями.

* query-параметры: `/services`, `/slots`, `/bookings`
* path-параметры: `/services/{service_id}`, `/bookings/{booking_id}`
* body-параметры: `POST /bookings`

Данные хранятся в памяти и сбрасываются при перезапуске сервиса.
"""

app = FastAPI(title="Studio Booking API", version="1.0.0", description=DESCRIPTION)


def get_service_or_404(service_id: int) -> Service:
    service = find_service(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail=f"Услуга {service_id} не найдена")
    return service


def check_day_not_past(day: date) -> None:
    if day < date.today():
        raise HTTPException(status_code=400, detail="Дата не может быть в прошлом")


@app.get("/", tags=["service"], summary="Информация о сервисе")
def root() -> dict:
    return {"service": "Studio Booking API", "version": app.version, "docs": "/docs"}


@app.get("/health", tags=["service"], summary="Проверка работоспособности")
def health() -> dict:
    return {"status": "ok"}


@app.get("/services", response_model=list[Service], tags=["services"], summary="Список услуг")
def list_services(
    category: Annotated[Category | None, Query(description="Фильтр по категории")] = None,
    max_price: Annotated[int | None, Query(ge=0, description="Максимальная цена в рублях")] = None,
    sort: Annotated[
        str, Query(pattern="^(id|price|name)$", description="Поле сортировки: id, price или name")
    ] = "id",
    limit: Annotated[int, Query(ge=1, le=50, description="Сколько услуг вернуть")] = 10,
) -> list[Service]:
    items = list(SERVICES)
    if category is not None:
        items = [s for s in items if s.category == category]
    if max_price is not None:
        items = [s for s in items if s.price <= max_price]
    items.sort(key=lambda s: getattr(s, sort))
    return items[:limit]


@app.get(
    "/services/{service_id}",
    response_model=Service,
    tags=["services"],
    summary="Услуга по номеру",
)
def get_service(service_id: Annotated[int, Path(ge=1, description="Номер услуги")]) -> Service:
    return get_service_or_404(service_id)


@app.get(
    "/slots",
    response_model=SlotsResponse,
    tags=["bookings"],
    summary="Свободные слоты на день",
)
def get_slots(
    service_id: Annotated[int, Query(ge=1, description="Номер услуги")],
    day: Annotated[date, Query(description="Дата, формат YYYY-MM-DD")],
) -> SlotsResponse:
    service = get_service_or_404(service_id)
    check_day_not_past(day)
    busy = db.busy_times(day, service.category)
    free = [t for t in WORK_HOURS if t not in busy]
    return SlotsResponse(
        service_id=service.id, category=service.category, day=day, free=free, busy=busy
    )


@app.post(
    "/bookings",
    response_model=Booking,
    status_code=201,
    tags=["bookings"],
    summary="Создать запись",
)
def create_booking(data: BookingCreate) -> Booking:
    service = get_service_or_404(data.service_id)
    check_day_not_past(data.day)
    if data.time not in WORK_HOURS:
        raise HTTPException(
            status_code=400,
            detail=f"Время {data.time} недоступно, допустимые слоты: {', '.join(WORK_HOURS)}",
        )
    booking = db.create(data, service)
    if booking is None:
        raise HTTPException(status_code=409, detail="Этот слот уже занят")
    return booking


@app.get("/bookings", response_model=list[Booking], tags=["bookings"], summary="Список записей")
def list_bookings(
    day: Annotated[date | None, Query(description="Фильтр по дате")] = None,
    status: Annotated[Status | None, Query(description="Фильтр по статусу")] = None,
) -> list[Booking]:
    return db.list(day=day, status=status)


@app.get(
    "/bookings/{booking_id}",
    response_model=Booking,
    tags=["bookings"],
    summary="Запись по номеру",
)
def get_booking(booking_id: Annotated[int, Path(ge=1, description="Номер записи")]) -> Booking:
    booking = db.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail=f"Запись {booking_id} не найдена")
    return booking


@app.delete(
    "/bookings/{booking_id}",
    response_model=Booking,
    tags=["bookings"],
    summary="Отменить запись",
)
def cancel_booking(booking_id: Annotated[int, Path(ge=1, description="Номер записи")]) -> Booking:
    booking = db.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail=f"Запись {booking_id} не найдена")
    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail="Запись уже отменена")
    return db.cancel(booking_id)
