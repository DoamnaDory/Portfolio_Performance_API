from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from sqlalchemy.future import select
from app.infrastructure.models_orm import Portfolio, Transaction
from app.domain.models import TransactionCreate, PortfolioCreate
from typing import List, Optional


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

    async def delete_portfolio(self, portfolio_id: int) -> bool:
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return False

        await self.db.execute(delete(Portfolio).where(Portfolio.id == portfolio_id))
        await self.db.commit()
        return True


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_transaction(self, tx: TransactionCreate) -> Transaction:
        db_tx = Transaction(**tx.model_dump())
        self.db.add(db_tx)
        await self.db.commit()
        await self.db.refresh(db_tx)
        return db_tx

    async def get_by_portfolio(self, portfolio_id: int) -> List[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.transaction_date.desc())
        )
        return result.scalars().all()