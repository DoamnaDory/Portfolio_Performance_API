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
from app.domain.services import PortfolioService, PriceService
from typing import List
from functools import lru_cache

router = APIRouter(prefix="/api/v1")


@lru_cache(maxsize=1)
def get_price_service() -> PriceService:
    return PriceService()


# Единая функция-зависимость для получения PortfolioService
def get_portfolio_service(db: AsyncSession = Depends(get_db),
                          price_service: PriceService = Depends(
                              get_price_service)):
    return PortfolioService(db, price_service)


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
        service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Создать новый портфель.

    - **name**: Название портфеля (например, 'Мои многомиллионные акции')
    """
    return await service.create_portfolio(portfolio)


@router.get(
    "/portfolios/",
    response_model=List[PortfolioResponse],
    summary="Получить список портфелей",
    description="Возвращает список всех созданных инвестиционных портфелей.",
    tags=["Портфели"]
)
async def get_portfolios(
        service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Получить список всех портфелей.
    """

    return await service.get_all_portfolios()


@router.get(
    "/portfolios/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Получить конкретный портфель",
    description="Возвращает детали конкретного портфеля по его ID.",
    tags=["Портфели"]
)
async def get_portfolio(
        portfolio_id: int,
        service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Получить детали портфеля по ID.

    - **portfolio_id**: Уникальный идентификатор портфеля
    """
    portfolio = await service.get_portfolio(portfolio_id)
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
        service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Удалить портфель по ID.

    - **portfolio_id**: Уникальный идентификатор портфеля
    """
    deleted = await service.delete_portfolio(portfolio_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Портфель не найден")


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
        service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Добавить новую транзакцию (покупка/продажа).

    - **portfolio_id**: ID портфеля, к которому относится транзакция
    - **ticker**: Тикер акции (например, 'AAPL')
    - **quantity**: Количество купленных/проданных акций
    - **price**: Цена за акцию
    - **transaction_type**: 'buy' или 'sell'
    """
    portfolio = await service.get_portfolio(transaction.portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Портфель не найден")

    await service.add_transaction(transaction)  # Вызываем метод сервиса
    return {"message": "Транзакция успешно добавлена",
            "portfolio_id": transaction.portfolio_id}


@router.get(
    "/portfolios/{portfolio_id}/transactions/",
    response_model=List[TransactionResponse],
    summary="Получить транзакции для портфеля",
    description="Возвращает историю транзакций для конкретного портфеля.",
    tags=["Транзакции"]
)
async def get_transactions(
        portfolio_id: int,
        service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Получить историю транзакций для портфеля.

    - **portfolio_id**: Уникальный идентификатор портфеля
    """
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Портфель не найден")

    return await service.get_transactions_for_portfolio(portfolio_id)


@router.get(
    "/portfolios/{portfolio_id}/performance",
    response_model=PortfolioPerformance,
    summary="Рассчитать доходность портфеля",
    description="Рассчитывает и возвращает ключевые метрики эффективности, такие как ROI, текущая стоимость и вложено средств.",
    tags=["Метрики"]
)
async def get_portfolio_performance(
        portfolio_id: int,
        service: PortfolioService = Depends(get_portfolio_service)
):
    result = await service.calculate_performance(portfolio_id)
    return result


@router.get("/", tags=["Main"])
async def root():
    """
    Эндпоинт для проверки работоспособности API.
    """
    return {"message": "Portfolio Performance API"}
