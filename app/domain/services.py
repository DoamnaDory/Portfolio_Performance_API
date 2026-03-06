from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models import PortfolioPerformance
from app.infrastructure.repositories import TransactionRepository


class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_performance(self,
                                    portfolio_id: int) -> PortfolioPerformance:
        repo = TransactionRepository(self.db)
        transactions = await repo.get_by_portfolio(
            portfolio_id)

        if not transactions:
            return PortfolioPerformance(
                portfolio_id=portfolio_id,
                total_invested=Decimal(0),
                current_value=Decimal(0),
                roi_percent=Decimal(0)
            )

        holdings = {}
        total_invested = Decimal(0)

        for tx in transactions:
            ticker = tx.ticker
            qty = Decimal(str(tx.quantity))
            price = Decimal(str(tx.price))

            if tx.transaction_type == "buy":
                holdings[ticker] = holdings.get(ticker, Decimal(0)) + qty
                total_invested += qty * price
            elif tx.transaction_type == "sell":
                holdings[ticker] = holdings.get(ticker, Decimal(0)) - qty

        # Заглушка для текущих цен
        current_prices = {"AAPL": Decimal("150"), "MSFT": Decimal("300"),
                          "TSLA": Decimal("200")}
        current_value = Decimal(sum(
            holdings.get(ticker, Decimal(0)) * current_prices.get(ticker,
                                                                  Decimal(0))
            for ticker in holdings
        ))

        roi = ((current_value - total_invested) / total_invested * 100) if total_invested > 0 else Decimal(0)

        return PortfolioPerformance(
            portfolio_id=portfolio_id,
            total_invested=total_invested,
            current_value=current_value,
            roi_percent=round(roi, 2)
        )
