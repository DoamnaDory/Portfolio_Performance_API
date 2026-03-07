from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict, \
    field_serializer
from typing import Optional


class TransactionType(str, Enum):
    """
    Тип транзакции: покупка или продажа.
    """

    BUY = "buy"
    SELL = "sell"


class PortfolioCreate(BaseModel):
    """
    Создание нового портфеля
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["Мой первый портфель"],
        description="Название портфеля"
    )


class PortfolioResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    transaction_count: int = Field(...,
                                   description="Количество транзакций в портфеле")

    model_config = {'from_attributes': True}


class TransactionCreate(BaseModel):
    """
    Создание новой транзакции
    """

    portfolio_id: int
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=20,
        examples=["AAPL"],
        description="Тикер акции"
    )
    quantity: Decimal = Field(..., gt=0, description="Количество акций")
    price: Decimal = Field(..., gt=0, description="Цена за одну акцию")
    transaction_type: TransactionType = Field(..., description="Тип транзакции")
    transaction_date: Optional[datetime] = Field(
        None,
        description="Дата транзакции (если не указана, будет установлена текущая)"
    )

    @field_validator("transaction_date", mode="before")
    @classmethod
    def set_default_date(cls, v: Optional[datetime]) -> datetime:
        """
        Если дата не передана, устанавливаем текущую UTC.
        """

        return v or datetime.now(timezone.utc).replace(tzinfo=None)


class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    quantity: Decimal
    price: Decimal
    transaction_type: TransactionType
    transaction_date: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('quantity', 'price')
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))


class PortfolioPerformance(BaseModel):
    """
    Вычисление метрик для портфеля
    """

    portfolio_id: int
    total_invested: Decimal = Field(
        ..., description="Общая сумма инвестиций (сумма всех покупок)"
    )
    current_value: Decimal = Field(
        ..., description="Текущая стоимость портфеля по рыночным ценам"
    )
    roi_percent: Decimal = Field(
        ..., description="Доходность в процентах"
    )

    model_config = ConfigDict()

    @field_serializer('total_invested', 'current_value', 'roi_percent')
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
