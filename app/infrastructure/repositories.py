from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select
from sqlalchemy.future import select
from app.infrastructure.models_orm import Portfolio, Transaction
from app.domain.models import TransactionCreate, PortfolioCreate
from typing import List, Optional
from datetime import datetime, timezone


class PortfolioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_portfolio(self, portfolio: PortfolioCreate) -> Portfolio:
        db_portfolio = Portfolio(name=portfolio.name)
        self.db.add(db_portfolio)
        await self.db.commit()
        await self.db.refresh(db_portfolio)
        return db_portfolio

    async def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        return result.scalars().first()

    async def get_all_portfolios(self) -> List[Portfolio]:
        result = await self.db.execute(select(Portfolio))
        return result.scalars().all()

    async def get_portfolio_with_transaction_count(self, portfolio_id: int) -> \
    Optional[tuple[Portfolio, int]]:
        result = await self.db.execute(
            select(Portfolio,
                   func.count(Transaction.id).label("transaction_count"))
            .outerjoin(Transaction, Transaction.portfolio_id == Portfolio.id)
            .where(Portfolio.id == portfolio_id)
            .group_by(Portfolio.id)
        )
        row = result.first()
        return (row[0], row[1]) if row else None

    async def get_all_portfolios_with_transaction_count(self) -> List[
        tuple[Portfolio, int]]:
        result = await self.db.execute(
            select(Portfolio,
                   func.count(Transaction.id).label("transaction_count"))
            .outerjoin(Transaction, Transaction.portfolio_id == Portfolio.id)
            .group_by(Portfolio.id)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def delete_portfolio(self, portfolio_id: int) -> bool:
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return False

        await self.db.execute(
            delete(Portfolio).where(Portfolio.id == portfolio_id))
        await self.db.commit()
        return True


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_transaction(self, tx: TransactionCreate) -> Transaction:
        """
        Добавить транзакцию для указанного портфеля.
        """

        data = tx.model_dump()

        if "transaction_date" in data and data["transaction_date"] is not None:
            dt = data["transaction_date"]
            if dt.tzinfo is not None:
                # Переводим в UTC и отбрасываем информацию о таймзоне
                data["transaction_date"] = dt.astimezone(timezone.utc).replace(
                    tzinfo=None)

        db_tx = Transaction(**data)
        self.db.add(db_tx)
        await self.db.commit()
        await self.db.refresh(db_tx)
        return db_tx

    async def get_by_portfolio(self, portfolio_id: int) -> List[Transaction]:
        """
        Возвращает все транзакции для указанного портфеля.
        """

        result = await self.db.execute(
            select(Transaction).where(Transaction.portfolio_id == portfolio_id)
        )
        return result.scalars().all()
