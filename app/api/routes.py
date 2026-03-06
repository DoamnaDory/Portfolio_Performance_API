from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.domain.models import (
    TransactionCreate,
    PortfolioPerformance,
    PortfolioCreate,
    PortfolioResponse,
    TransactionResponse
)
from app.domain.services import PortfolioService
from app.infrastructure.repositories import TransactionRepository, PortfolioRepository
from typing import List

router = APIRouter(prefix="/api/v1")


# Портфели

@router.post(
    "/portfolios/",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый портфель",
    description="Создаёт новый инвестиционный портфель с указанным названием.",
    tags=["Портфели"]
)
async def create_portfolio(
    portfolio: PortfolioCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать новый портфель.

    - **name**: Название портфеля (например, 'Мои многомиллионные акции')
    """
    repo = PortfolioRepository(db)
    return await repo.create_portfolio(portfolio)


@router.get(
    "/portfolios/",
    response_model=List[PortfolioResponse],
    summary="Получить список портфелей",
    description="Возвращает список всех созданных инвестиционных портфелей.",
    tags=["Портфели"]
)
async def get_portfolios(db: AsyncSession = Depends(get_db)):
    """
    Получить список всех портфелей.
    """
    repo = PortfolioRepository(db)
    return await repo.get_all_portfolios()


@router.get(
    "/portfolios/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Получить конкретный портфель",
    description="Возвращает детали конкретного портфеля по его ID.",
    tags=["Портфели"]
)
async def get_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детали портфеля по ID.

    - **portfolio_id**: Уникальный идентификатор портфеля
    """
    repo = PortfolioRepository(db)
    portfolio = await repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Портфель не найден")
    return portfolio


@router.delete(
    "/portfolios/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить конкретный портфель",
    description="Удаляет портфель и все связанные с ним транзакции.",
    tags=["Портфели"]
)
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить портфель по ID.

    - **portfolio_id**: Уникальный идентификатор портфеля
    """
    repo = PortfolioRepository(db)
    deleted = await repo.delete_portfolio(portfolio_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Портфель не найден")
    return


# Транзакции
@router.post(
    "/transactions/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить новую транзакцию",
    description="Записывает новую транзакцию покупки или продажи для конкретного портфеля.",
    tags=["Транзакции"]
)
async def add_transaction(
    transaction: TransactionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Добавить новую транзакцию (покупка/продажа).

    - **portfolio_id**: ID портфеля, к которому относится транзакция
    - **ticker**: Тикер акции (например, 'AAPL')
    - **quantity**: Количество купленных/проданных акций
    - **price**: Цена за акцию
    - **transaction_type**: 'buy' или 'sell'
    """
    portfolio_repo = PortfolioRepository(db)
    portfolio = await portfolio_repo.get_portfolio(transaction.portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Портфель не найден")

    repo = TransactionRepository(db)
    await repo.add_transaction(transaction)
    return {"message": "Транзакция успешно добавлена", "portfolio_id": transaction.portfolio_id}


@router.get(
    "/portfolios/{portfolio_id}/transactions/",
    response_model=List[TransactionResponse],
    summary="Получить транзакции для портфеля",
    description="Возвращает историю транзакций для конкретного портфеля.",
    tags=["Транзакции"]
)
async def get_transactions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю транзакций для портфеля.

    - **portfolio_id**: Уникальный идентификатор портфеля
    """
    portfolio_repo = PortfolioRepository(db)
    portfolio = await portfolio_repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Портфель не найден")

    repo = TransactionRepository(db)
    return await repo.get_by_portfolio(portfolio_id)


# Метрики

@router.get(
    "/portfolios/{portfolio_id}/performance",
    response_model=PortfolioPerformance,
    summary="Рассчитать доходность портфеля",
    description="Рассчитывает и возвращает ключевые метрики эффективности, такие как ROI, текущая стоимость и вложено средств.",
    tags=["Метрики"]
)
async def get_portfolio_performance(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Рассчитать метрики эффективности портфеля.

    - **portfolio_id**: Уникальный идентификатор портфеля
    """
    portfolio_repo = PortfolioRepository(db)
    portfolio = await portfolio_repo.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Портфель не найден")

    service = PortfolioService(db)
    return await service.calculate_performance(portfolio_id)


# Main

@router.get("/", tags=["Main"])
async def root():
    """
    Эндпоинт для проверки работоспособности API.
    """
    return {"message": "Portfolio Performance API"}