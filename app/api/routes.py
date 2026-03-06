from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.domain.models import TransactionCreate, PortfolioPerformance
from app.domain.services import PortfolioService
from app.infrastructure.repositories import TransactionRepository

router = APIRouter()


@router.post("/transactions/", response_model=dict)
async def add_transaction(transaction: TransactionCreate, db: AsyncSession = Depends(get_db)):
    repo = TransactionRepository(db)
    await repo.add_transaction(transaction)
    return {"message": "Transaction added successfully"}


@router.get("/portfolios/{portfolio_id}/performance", response_model=PortfolioPerformance)
async def get_portfolio_performance(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    service = PortfolioService(db)
    performance = await service.calculate_performance(portfolio_id)
    if performance is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return performance