from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["hair", "nails", "brows", "skin"]
Status = Literal["active", "cancelled"]


def _example_day() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


class Service(BaseModel):
    id: int
    name: str
    category: Category
    price: int = Field(description="Цена в рублях")


class BookingCreate(BaseModel):
    """Тело запроса на создание записи."""

    client_name: str = Field(min_length=2, max_length=50, description="Имя клиента")
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$", description="Телефон, 10-15 цифр, можно с плюсом")
    service_id: int = Field(ge=1, description="Номер услуги из GET /services")
    day: date = Field(description="Дата визита, формат YYYY-MM-DD")
    time: str = Field(pattern=r"^[0-9]{2}:[0-9]{2}$", description="Время начала, формат HH:MM")
    comment: str | None = Field(default=None, max_length=200, description="Комментарий к записи")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "client_name": "Иван",
                    "phone": "+79991234567",
                    "service_id": 3,
                    "day": _example_day(),
                    "time": "12:00",
                    "comment": "Первый визит",
                }
            ]
        }
    )


class Booking(BaseModel):
    id: int
    client_name: str
    phone: str
    service_id: int
    service_name: str
    category: Category
    price: int
    day: date
    time: str
    comment: str | None
    status: Status
    created_at: datetime


class SlotsResponse(BaseModel):
    service_id: int
    category: Category
    day: date
    free: list[str]
    busy: list[str]
