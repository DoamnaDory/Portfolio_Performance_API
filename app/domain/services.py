from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models import PortfolioPerformance
from app.infrastructure.repositories import TransactionRepository
from typing import Optional


class PortfolioService:
    def __init__(self, db_session: AsyncSession):
        self.repo = TransactionRepository(db_session)

    async def calculate_performance(self, portfolio_id: int) -> Optional[
        PortfolioPerformance]:
        # 1. Получаем транзакции (асинхронно!)
        transactions = await self.repo.get_transactions_by_portfolio(
            portfolio_id)

        # 2. Проверяем, есть ли транзакции
        if not transactions:
            return None  # Возвращаем None, если портфель не найден или пуст

        # 3. Считаем метрики
        total_invested = Decimal(0)
        total_sold = Decimal(0)
        current_holdings = {}

        for tx in transactions:
            if tx.transaction_type == "buy":
                total_invested += tx.quantity * tx.price
                current_holdings[tx.ticker] = current_holdings.get(tx.ticker,
                                                                   Decimal(
                                                                       0)) + tx.quantity
            elif tx.transaction_type == "sell":
                total_sold += tx.quantity * tx.price
                current_holdings[tx.ticker] = current_holdings.get(tx.ticker,
                                                                   Decimal(
                                                                       0)) - tx.quantity

        # Заглушка для текущих цен (в реальности это пришло бы извне)
        current_prices = {"AAPL": Decimal(150), "MSFT": Decimal(300)}
        current_value = Decimal(0)

        for ticker, qty in current_holdings.items():
            if qty > 0:
                price = current_prices.get(ticker, Decimal(0))
                current_value += qty * price

        net_invested = total_invested - total_sold
        roi = Decimal(0)
        if net_invested > 0:
            roi = ((current_value - net_invested) / net_invested) * Decimal(100)

        return PortfolioPerformance(
            portfolio_id=portfolio_id,
            total_invested=net_invested,
            current_value=current_value,
            roi=roi
        )