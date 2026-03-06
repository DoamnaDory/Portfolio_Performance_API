from pydantic import BaseModel
from decimal import Decimal
from typing import Optional


class TransactionCreate(BaseModel):
    portfolio_id: int
    ticker: str
    quantity: Decimal
    price: Decimal
    transaction_type: str  # 'buy' or 'sell'


class PortfolioPerformance(BaseModel):
    portfolio_id: int
    total_invested: Decimal
    current_value: Decimal
    roi: Decimal
