import csv
import logging
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.models import PortfolioPerformance, TransactionType, \
    PortfolioResponse, PortfolioCreate
from app.infrastructure.models_orm import Portfolio, Transaction
from app.infrastructure.repositories import TransactionRepository, \
    PortfolioRepository

logger = logging.getLogger(__name__)


@dataclass
class Holding:
    """
    Холдинг по одному тикеру: количество и средняя цена покупки.
    """

    quantity: Decimal
    avg_cost: Decimal


class PriceService:
    """
    Сервис для получения актуальных цен акций из csv-файла
    """

    def __init__(
            self,
            csv_path: Optional[str] = None,
            ticker_map_path: Optional[str] = None
    ):
        """
        :param csv_path: Путь к csv-файлу с ценами. Если не указан, берётся из настроек.
        :param ticker_map_path: Путь к json-файлу с маппингом тикеров. Если не указан, берётся из настроек.
        """
        self.csv_path = Path(csv_path or settings.prices_csv_path)
        self.ticker_map_path = Path(ticker_map_path or settings.ticker_map_path)
        self._prices: Optional[Dict[str, Decimal]] = None
        self._ticker_map: Optional[Dict[str, str]] = None

    def _load_ticker_map(self) -> Dict[str, str]:
        """
        Загружает маппинг тикеров из json-файла.
        """

        path = self.ticker_map_path
        if not path.exists():
            logger.error("Файл с маппингом тикеров не найден: %s", path)
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logger.error("Неверный формат json: ожидается словарь")
                    return {}
                return {k.upper(): v for k, v in data.items()}
        except Exception as e:
            logger.exception("Ошибка загрузки маппинга тикеров из %s", path)
            return {}

    @property
    def ticker_map(self) -> Dict[str, str]:
        """
        Ленивая загрузка маппинга тикеров.
        """

        if self._ticker_map is None:
            self._ticker_map = self._load_ticker_map()
        return self._ticker_map

    def _load_prices(self) -> Dict[str, Decimal]:
        """
        Загружает цены из csv-файла и возвращает словарь {название_компании: цена}.
        """

        prices = {}
        path = self.csv_path

        if not path.exists():
            logger.warning("csv-файл с ценами не найден: %s", path)
            return prices

        try:
            with open(path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f, delimiter=',')
                for row in reader:
                    name = row.get('Название', '').strip()
                    price_str = row.get('Послед.', '0').replace(',', '.').strip()
                    if not name or not price_str:
                        continue
                    try:
                        prices[name] = Decimal(price_str)
                    except Exception as e:
                        logger.warning("Не удалось распарсить цену для '%s': %s",
                                       name, e)
        except Exception as e:
            logger.error("Ошибка при чтении csv-файла %s: %s", path, e)

        return prices

    @property
    def prices(self) -> Dict[str, Decimal]:
        """
        Ленивая загрузка цен (кэшируется после первого чтения).
        """

        if self._prices is None:
            self._prices = self._load_prices()
        return self._prices

    def get_price(self, ticker: str) -> Optional[Decimal]:
        """
        Возвращает текущую цену для указанного тикера или None, если цена не найдена."""
        company_name = self.get_company_name(ticker)
        if not company_name:
            logger.debug("Не найден маппинг для тикера %s", ticker)
            return None

        price = self.prices.get(company_name)
        if price is None:
            logger.debug("Цена для компании '%s' (тикер %s) отсутствует в csv",
                         company_name, ticker)
            return None

        return price

    def get_company_name(self, ticker: str) -> Optional[str]:
        """
        Возвращает название компании по тикеру или None, если тикер не найден.
        """
        return self.ticker_map.get(ticker.upper())


class PortfolioService:
    """
    Сервис для расчёта метрик эффективности инвестиционного портфеля и crud операций с портфелями."""

    def __init__(self, db: AsyncSession,
                 price_service: Optional[PriceService] = None):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.portfolio_repo = PortfolioRepository(db)
        self.price_service = price_service

    async def create_portfolio(self,
                               portfolio_create: PortfolioCreate) -> PortfolioResponse:
        db_portfolio = await self.portfolio_repo.create_portfolio(
            portfolio_create)
        portfolio_data = {
            "id": db_portfolio.id,
            "name": db_portfolio.name,
            "created_at": db_portfolio.created_at,
            "transaction_count": 0
        }
        return PortfolioResponse.model_validate(portfolio_data)

    async def get_portfolio(self, portfolio_id: int) -> Optional[
        PortfolioResponse]:
        portfolio_with_count = await self.portfolio_repo.get_portfolio_with_transaction_count(
            portfolio_id)
        if not portfolio_with_count:
            return None
        portfolio, count = portfolio_with_count
        portfolio_data = {
            "id": portfolio.id,
            "name": portfolio.name,
            "created_at": portfolio.created_at,
            "transaction_count": count
        }
        return PortfolioResponse.model_validate(portfolio_data)

    async def get_all_portfolios(self) -> List[PortfolioResponse]:
        portfolios_with_counts = await self.portfolio_repo.get_all_portfolios_with_transaction_count()
        result = []
        for portfolio, count in portfolios_with_counts:
            portfolio_data = {
                "id": portfolio.id,
                "name": portfolio.name,
                "created_at": portfolio.created_at,
                "transaction_count": count
            }
            result.append(PortfolioResponse.model_validate(portfolio_data))
        return result

    async def delete_portfolio(self, portfolio_id: int) -> bool:
        return await self.portfolio_repo.delete_portfolio(portfolio_id)

    async def add_transaction(self, transaction_data)  -> Transaction:
        """
        Добавляет транзакцию через репозиторий.
        """
        return await self.transaction_repo.add_transaction(transaction_data)

    async def get_transactions_for_portfolio(self, portfolio_id: int) -> List[Transaction]:
        """
        Получает транзакции для портфеля через репозиторий.
        """
        return await self.transaction_repo.get_by_portfolio(portfolio_id)

    async def calculate_performance(self,
                                    portfolio_id: int) -> PortfolioPerformance:
        """
        Рассчитывает эффективность портфеля:
        - total_invested: сумма всех покупок с учётом продаж (по средней цене)
        - current_value: текущая рыночная стоимость остатка акций
        - roi_percent: доходность в процентах
        """
        portfolio_exists = await self.get_portfolio(portfolio_id)

        transactions = await self.transaction_repo.get_by_portfolio(portfolio_id)

        if not transactions:
            return PortfolioPerformance(
                portfolio_id=portfolio_id,
                total_invested=Decimal(0),
                current_value=Decimal(0),
                roi_percent=Decimal(0)
            )

        holdings: Dict[str, Holding] = {}
        total_invested = Decimal(0)

        for tx in transactions:
            ticker = tx.ticker.upper()
            qty = Decimal(str(tx.quantity))
            price = Decimal(str(tx.price))

            if tx.transaction_type == TransactionType.BUY.value:
                # Обработка покупки
                if ticker in holdings:
                    old = holdings[ticker]
                    total_cost = (old.quantity * old.avg_cost) + (qty * price)
                    new_qty = old.quantity + qty
                    avg_cost = total_cost / new_qty if new_qty > 0 else Decimal(
                        0)
                    holdings[ticker] = Holding(new_qty, avg_cost)
                else:
                    holdings[ticker] = Holding(qty, price)

                total_invested += qty * price

            elif tx.transaction_type == TransactionType.SELL.value:
                # Обработка продажи
                if ticker not in holdings or holdings[ticker].quantity < qty:
                    logger.warning(
                        "Попытка продать %s акций %s, но в портфеле только %s ",
                        qty, ticker, holdings.get(ticker, Holding(Decimal(0),
                                                                  Decimal(
                                                                      0))).quantity
                    )
                    continue

                holding = holdings[ticker]
                holding.quantity -= qty
                total_invested -= qty * holding.avg_cost

                if holding.quantity == 0:
                    del holdings[ticker]

        # Расчёт текущей стоимости
        current_value = Decimal(0)
        missing_prices = []

        for ticker, holding in holdings.items():
            if self.price_service:
                price = self.price_service.get_price(ticker)
                if price is not None:
                    current_value += holding.quantity * price
                else:
                    missing_prices.append(ticker)
            else:
                logger.warning(
                    "PriceService не предоставлен, невозможно рассчитать текущую стоимость.")

        if missing_prices:
            logger.warning(
                "Для следующих тикеров не найдены текущие цены: %s ",
                ", ".join(missing_prices)
            )

        # Расчёт доходности
        if total_invested > 0:
            roi = (current_value - total_invested) / total_invested * 100
        else:
            roi = Decimal(0)

        return PortfolioPerformance(
            portfolio_id=portfolio_id,
            total_invested=total_invested,
            current_value=current_value,
            roi_percent=roi
        )
