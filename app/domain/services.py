import csv
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models import PortfolioPerformance
from app.infrastructure.repositories import TransactionRepository


class PriceService:
    """Сервис для получения актуальных цен акций из CSV-файла"""

    # Маппинг тикеров на названия компаний из файла
    TICKER_TO_COMPANY = {
        "AAPL": "Apple",
        "MSFT": "Microsoft",
        "NVDA": "NVIDIA",
        "AMZN": "Amazon.com",
        "BA": "Boeing",
        "CVX": "Chevron",
        "CAT": "Caterpillar",
        "DIS": "Walt Disney",
        "CSCO": "Cisco",
        "GS": "Goldman Sachs",
        "JPM": "JPMorgan",
        "KO": "Coca-Cola",
        "MCD": "McDonald's",
        "MRK": "Merck&Co",
        "MMM": "3M",
        "WMT": "Walmart",
        "HD": "Home Depot",
        "IBM": "IBM",
        "VZ": "Verizon",
        "TRV": "The Travelers",
        "JNJ": "J&J",
        "AXP": "American Express",
        "HON": "Honeywell",
        "CRM": "Salesforce Inc",
        "V": "Visa A",
        "UNH": "UnitedHealth",
        "NKE": "Nike",
        "PG": "P&G",
        "SWK": "Sherwin-Williams",
        "AMGN": "Amgen",
    }

    def __init__(self, csv_path: str = "data/Американские фондовые рынки.csv"):
        self.csv_path = Path(csv_path)
        self._prices: Optional[Dict[str, Decimal]] = None

    def _load_prices(self) -> Dict[str, Decimal]:
        """Загружает цены из CSV-файла"""
        prices = {}
        path = self.csv_path

        if not path.exists():
            return prices  # Если файл не найден, возвращаем пустой словарь

        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                name = row.get('Название', '').strip()
                price_str = row.get('Послед.', '0').replace(',', '.').strip()
                try:
                    prices[name] = Decimal(price_str)
                except:
                    continue

        return prices

    @property
    def prices(self) -> Dict[str, Decimal]:
        """Ленивая загрузка цен (кэшируется после первого чтения)"""
        if self._prices is None:
            self._prices = self._load_prices()
        return self._prices

    def get_price(self, ticker: str) -> Decimal:
        """Получает цену по тикуру"""
        company_name = self.TICKER_TO_COMPANY.get(ticker.upper())
        if not company_name:
            return Decimal(0)

        return self.prices.get(company_name, Decimal(0))


class PortfolioService:
    """Сервис для расчёта метрик эффективности инвестиционного портфеля."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.price_service = PriceService()

    async def calculate_performance(self,
                                    portfolio_id: int) -> PortfolioPerformance:
        repo = TransactionRepository(self.db)
        transactions = await repo.get_by_portfolio(portfolio_id)

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
            ticker = tx.ticker.upper()
            qty = Decimal(str(tx.quantity))
            price = Decimal(str(tx.price))

            if tx.transaction_type == "buy":
                # Обновляем среднюю цену покупки и количество
                existing_qty = holdings.get(ticker, {}).get("quantity",
                                                            Decimal(0))
                existing_cost = holdings.get(ticker, {}).get("avg_cost",
                                                             Decimal(0))

                total_cost = (existing_qty * existing_cost) + (qty * price)
                total_qty = existing_qty + qty
                avg_cost = total_cost / total_qty if total_qty > 0 else Decimal(
                    0)

                holdings[ticker] = {"quantity": total_qty, "avg_cost": avg_cost}
                total_invested += qty * price

            elif tx.transaction_type == "sell":
                # Продажа: уменьшаем количество
                holding = holdings.get(ticker)
                if not holding or holding["quantity"] < qty:
                    continue

                holding["quantity"] -= qty
                total_invested -= qty * holding["avg_cost"]

                if holding["quantity"] <= 0:
                    del holdings[ticker]

        # Считаем текущую стоимость с ценами из файла
        current_value = Decimal(0)
        for ticker, data in holdings.items():
            current_price = self.price_service.get_price(ticker)
            current_value += data["quantity"] * current_price

        # Расчёт
        roi_percent = ((
                                   current_value - total_invested) / total_invested * 100) if total_invested > 0 else Decimal(
            0)

        total_invested = total_invested.quantize(Decimal('0.001'))
        current_value = current_value.quantize(Decimal('0.001'))
        roi_percent = roi_percent.quantize(Decimal('0.001'))

        return PortfolioPerformance(
            portfolio_id=portfolio_id,
            total_invested=total_invested,
            current_value=current_value,
            roi_percent=roi_percent
        )
