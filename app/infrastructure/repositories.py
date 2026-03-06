from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.domain.models import TransactionCreate
from app.infrastructure.models_orm import Transaction, Portfolio


class TransactionRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def add_transaction(self, tx_data: TransactionCreate):
        db_tx = Transaction(
            portfolio_id=tx_data.portfolio_id,
            ticker=tx_data.ticker,
            quantity=tx_data.quantity,
            price=tx_data.price,
            transaction_type=tx_data.transaction_type
        )
        self.db_session.add(db_tx)
        await self.db_session.commit()
        await self.db_session.refresh(db_tx)

    async def get_transactions_by_portfolio(self, portfolio_id: int):
        result = await self.db_session.execute(
            select(Transaction).where(Transaction.portfolio_id == portfolio_id)
        )
        return result.scalars().all()