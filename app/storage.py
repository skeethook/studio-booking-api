from datetime import date, datetime
from threading import Lock

from app.models import Booking, BookingCreate, Service, Status

# Слоты по часу, последний начинается в 18:00
WORK_HOURS = [f"{hour:02d}:00" for hour in range(10, 19)]

SERVICES = [
    Service(id=1, name="Стрижка женская", category="hair", price=2500),
    Service(id=2, name="Окрашивание волос", category="hair", price=6000),
    Service(id=3, name="Маникюр", category="nails", price=1800),
    Service(id=4, name="Педикюр", category="nails", price=2200),
    Service(id=5, name="Коррекция бровей", category="brows", price=1200),
    Service(id=6, name="Окрашивание бровей", category="brows", price=900),
    Service(id=7, name="Чистка лица", category="skin", price=3500),
    Service(id=8, name="Массаж лица", category="skin", price=2800),
]


def find_service(service_id: int) -> Service | None:
    for service in SERVICES:
        if service.id == service_id:
            return service
    return None


class Storage:
    """Хранилище записей в памяти. У каждой категории свой мастер, слот занят в рамках категории."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._bookings: dict[int, Booking] = {}
            self._next_id = 1

    def busy_times(self, day: date, category: str) -> list[str]:
        with self._lock:
            times = {
                b.time
                for b in self._bookings.values()
                if b.day == day and b.category == category and b.status == "active"
            }
        return sorted(times)

    def create(self, data: BookingCreate, service: Service) -> Booking | None:
        """Возвращает None, если слот уже занят."""
        with self._lock:
            taken = any(
                b.day == data.day
                and b.time == data.time
                and b.category == service.category
                and b.status == "active"
                for b in self._bookings.values()
            )
            if taken:
                return None
            booking = Booking(
                id=self._next_id,
                client_name=data.client_name,
                phone=data.phone,
                service_id=service.id,
                service_name=service.name,
                category=service.category,
                price=service.price,
                day=data.day,
                time=data.time,
                comment=data.comment,
                status="active",
                created_at=datetime.now(),
            )
            self._bookings[booking.id] = booking
            self._next_id += 1
            return booking

    def get(self, booking_id: int) -> Booking | None:
        with self._lock:
            return self._bookings.get(booking_id)

    def list(self, day: date | None = None, status: Status | None = None) -> list[Booking]:
        with self._lock:
            items = list(self._bookings.values())
        if day is not None:
            items = [b for b in items if b.day == day]
        if status is not None:
            items = [b for b in items if b.status == status]
        return sorted(items, key=lambda b: (b.day, b.time, b.id))

    def cancel(self, booking_id: int) -> Booking | None:
        with self._lock:
            booking = self._bookings.get(booking_id)
            if booking is None:
                return None
            booking.status = "cancelled"
            return booking


db = Storage()
