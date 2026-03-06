from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime


# Портфели

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class PortfolioResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# Транзакции

class TransactionCreate(BaseModel):
    portfolio_id: int
    ticker: str = Field(..., min_length=1, max_length=20)
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    transaction_type: str = Field(..., pattern="^(buy|sell)$")


class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    quantity: Decimal
    price: Decimal
    transaction_type: str
    transaction_date: datetime

    class Config:
        from_attributes = True


# Метрики

class PortfolioPerformance(BaseModel):
    portfolio_id: int
    total_invested: Decimal
    current_value: Decimal
    roi_percent: Decimal