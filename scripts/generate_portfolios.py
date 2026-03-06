import argparse
import asyncio
import csv
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import engine
from app.domain.models import PortfolioCreate, TransactionCreate
from app.domain.services import PriceService
from app.infrastructure.repositories import PortfolioRepository, \
    TransactionRepository

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Пути
CSV_PATH = Path("data/Американские фондовые рынки.csv")

# Конфигурация
NUM_PORTFOLIOS = 5
TRANSACTIONS_PER_PORTFOLIO = 3
QUANTITY_MIN = 1
QUANTITY_MAX = 100
PRICE_VARIATION_MIN = -0.30
PRICE_VARIATION_MAX = 0.30
DATE_RANGE_DAYS = 365
BUY_SELL_RATIO = 0.8


def load_companies_from_csv(csv_path: Path) -> list:
    """
    Загружает список тикеров из CSV-файла, используя маппинг из PriceService.
    Возвращает список тикеров.
    """

    # Получаем обратный маппинг
    NAME_TO_TICKER = {v: k for k, v in PriceService.TICKER_TO_COMPANY.items()}

    tickers = []
    if not csv_path.exists():
        logger.error(f"CSV файл не найден: {csv_path}")
        return []

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            name = row.get('Название', '').strip()
            if name in NAME_TO_TICKER:
                ticker = NAME_TO_TICKER[name]
                tickers.append(ticker)

    logger.info(f"Загружено {len(tickers)} тикеров из CSV.")
    return tickers


async def create_random_transactions(
        db: AsyncSession,
        portfolio_id: int,
        tickers: list,
        num_transactions: int
):
    """
    Создаёт случайные транзакции для портфеля.
    """
    repo = TransactionRepository(db)
    holdings = {}  # ticker: quantity

    for i in range(num_transactions):
        # Выбираем случайный тикер из списка
        ticker = random.choice(tickers)
        company_name = PriceService.TICKER_TO_COMPANY.get(
            ticker)  # Получаем имя для логирования
        if not company_name:
            logger.warning(f"Нет названия для тикера {ticker}")
            continue

        # Читаем цены из файла, чтобы получить текущую цену для генерации покупки
        prices_map = {}
        with open(CSV_PATH, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                name = row.get('Название', '').strip()
                price_str = row.get('Послед.', '0').replace(',', '.').strip()
                try:
                    prices_map[name] = Decimal(price_str)
                except:
                    continue

        current_price = prices_map.get(company_name, Decimal('100'))

        quantity = Decimal(random.randint(QUANTITY_MIN, QUANTITY_MAX))
        variation = random.uniform(PRICE_VARIATION_MIN, PRICE_VARIATION_MAX)
        buy_price = current_price * (Decimal('1') + Decimal(variation))

        transaction_type = "buy" if random.random() < BUY_SELL_RATIO else "sell"

        if transaction_type == "sell":
            held_qty = holdings.get(ticker, 0)
            if held_qty < quantity:
                logger.debug(
                    f"Недостаточно {ticker} ({company_name}) для продажи. Имеется: {held_qty}, запрошено: {quantity}. Пропускаем.")
                continue
            holdings[ticker] = held_qty - quantity
        else:  # buy
            holdings[ticker] = holdings.get(ticker, 0) + quantity

        days_ago = random.randint(1, DATE_RANGE_DAYS)

        transaction_data = TransactionCreate(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price=buy_price,
            transaction_type=transaction_type
        )

        await repo.add_transaction(transaction_data)
        logger.debug(
            f"Добавлена транзакция: {transaction_type} {quantity}x {ticker} ({company_name}) @ {buy_price:.2f}")


async def generate_portfolios(
        num_portfolios: int,
        transactions_per_portfolio: int,
        clear_existing: bool
):
    """
    Основная функция генерации портфелей.
    """
    tickers = load_companies_from_csv(CSV_PATH)
    if not tickers:
        logger.error("Нет доступных тикеров для генерации. Завершение.")
        return

    async with AsyncSession(engine) as db:
        portfolio_repo = PortfolioRepository(db)

        if clear_existing:
            logger.warning("Очистка существующих портфелей...")
            logger.warning(
                "Очистка портфелей и транзакций НЕ РЕАЛИЗОВАНА в этом скрипте. "
                "Пожалуйста, очистите БД вручную, если необходимо.")

        logger.info(f"Создание {num_portfolios} портфелей...")

        for i in range(num_portfolios):
            portfolio_name = f"Тестовый портфель #{i + 1}"
            portfolio_create = PortfolioCreate(name=portfolio_name)
            portfolio = await portfolio_repo.create_portfolio(portfolio_create)
            logger.info(
                f"Создан портфель: {portfolio.name} (ID: {portfolio.id})")

            logger.info(
                f"Создание {transactions_per_portfolio} транзакций для портфеля {portfolio.id}...")
            await create_random_transactions(db, portfolio.id, tickers,
                                             transactions_per_portfolio)

            await db.flush()

        await db.commit()
        logger.info("Все портфели и транзакции успешно созданы.")


def main():
    parser = argparse.ArgumentParser(
        description="Генератор тестовых портфелей и транзакций.")
    parser.add_argument("--portfolios", type=int, default=NUM_PORTFOLIOS,
                        help="Количество портфелей для создания (по умолчанию: 5)")
    parser.add_argument("--transactions", type=int,
                        default=TRANSACTIONS_PER_PORTFOLIO,
                        help="Количество транзакций на портфель (по умолчанию: 3)")
    parser.add_argument("--clear", action='store_true',
                        help="Очистить существующие портфели перед созданием новых (НЕ РЕАЛИЗОВАНО)")

    args = parser.parse_args()

    logger.info(
        f"Запуск генератора с параметрами: портфелей={args.portfolios}, транзакций={args.transactions}, очистка={args.clear}")

    asyncio.run(
        generate_portfolios(args.portfolios, args.transactions, args.clear))


if __name__ == "__main__":
    main()
