import argparse
import asyncio
import csv
import json
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.database import engine
from app.domain.models import PortfolioCreate, TransactionCreate, TransactionType
from app.infrastructure.repositories import PortfolioRepository, \
    TransactionRepository

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфигурация
NUM_PORTFOLIOS = 5
TRANSACTIONS_PER_PORTFOLIO = 3
QUANTITY_MIN = 1
QUANTITY_MAX = 100
PRICE_VARIATION_MIN = -0.30
PRICE_VARIATION_MAX = 0.30
DATE_RANGE_DAYS = 365
BUY_SELL_RATIO = 0.8


def load_ticker_map() -> dict:
    """
    Загружает маппинг тикеров из json-файла, указанного в настройках.
    """

    path = Path(settings.ticker_map_path)
    if not path.exists():
        logger.error(f"Файл маппинга тикеров не найден: {path}")
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Загружено {len(data)} тикеров из {path}")
            return data
    except Exception as e:
        logger.exception(f"Ошибка загрузки маппинга тикеров: {e}")
        return {}


def load_prices_from_csv(csv_path: Path) -> dict:
    """
    Загружает цены из csv-файла.
    Возвращает словарь {название_компании: Decimal(цена)}.
    """

    prices = {}
    if not csv_path.exists():
        logger.warning(
            f"CSV файл не найден: {csv_path}. Цены будут заданы по умолчанию (100).")
        return prices

    try:
        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                name = row.get('Название', '').strip()
                price_str = row.get('Послед.', '0').replace(',', '.').strip()
                if not name or not price_str:
                    continue
                try:
                    prices[name] = Decimal(price_str)
                except Exception:
                    logger.debug(
                        f"Не удалось преобразовать цену '{price_str}' для {name}")
                    continue
        logger.info(f"Загружено цен для {len(prices)} компаний из {csv_path}")
    except Exception as e:
        logger.exception(f"Ошибка чтения CSV-файла: {e}")

    return prices


async def create_random_transactions(
        db: AsyncSession,
        portfolio_id: int,
        tickers: list,
        ticker_map: dict,
        prices: dict,
        num_transactions: int
):
    """
    Создаёт случайные транзакции для портфеля, используя предоставленные маппинг и цены.
    """

    repo = TransactionRepository(db)
    holdings = {}  # ticker: quantity

    for i in range(num_transactions):
        ticker = random.choice(tickers)
        company_name = ticker_map.get(ticker)
        if not company_name:
            logger.warning(
                f"Пропуск тикера {ticker}: нет названия компании в маппинге.")
            continue

        # Текущая цена из загруженных данных, иначе 100
        current_price = prices.get(company_name, Decimal('100'))

        quantity = Decimal(random.randint(QUANTITY_MIN, QUANTITY_MAX))
        variation = Decimal(
            str(random.uniform(PRICE_VARIATION_MIN, PRICE_VARIATION_MAX)))
        buy_price = (current_price * (Decimal('1') + variation)).quantize(
            Decimal('0.01'))

        transaction_type = TransactionType.BUY if random.random() < BUY_SELL_RATIO else TransactionType.SELL
        if transaction_type == TransactionType.SELL:
            held_qty = holdings.get(ticker, 0)
            if held_qty < quantity:
                logger.debug(
                    f"Недостаточно {ticker} ({company_name}) для продажи. Имеется: {held_qty}, запрошено: {quantity}. Пропускаем."
                )
                continue
            holdings[ticker] = held_qty - quantity
        else:  # buy
            holdings[ticker] = holdings.get(ticker, 0) + quantity

        # Случайная дата в пределах последнего года
        days_ago = random.randint(1, DATE_RANGE_DAYS)
        transaction_date = datetime.utcnow() - timedelta(days=days_ago)

        transaction_data = TransactionCreate(
            portfolio_id=portfolio_id,
            ticker=ticker,
            quantity=quantity,
            price=buy_price,
            transaction_type=transaction_type,
            transaction_date=transaction_date
        )

        await repo.add_transaction(transaction_data)
        logger.debug(
            f"Добавлена транзакция: {transaction_type} {quantity}x {ticker} ({company_name}) @ {buy_price:.2f}"
        )


async def generate_portfolios(
        num_portfolios: int,
        transactions_per_portfolio: int,
        clear_existing: bool
):
    """
    Основная функция генерации портфелей и транзакций.
    """

    # Загружаем данные один раз
    ticker_map = load_ticker_map()
    if not ticker_map:
        logger.error("Не удалось загрузить маппинг тикеров. Завершение.")
        return

    tickers = list(ticker_map.keys())
    logger.info(f"Доступно тикеров для генерации: {len(tickers)}")

    csv_path = Path(settings.prices_csv_path)
    prices = load_prices_from_csv(csv_path)

    async with AsyncSession(engine) as db:
        portfolio_repo = PortfolioRepository(db)

        if clear_existing:
            logger.warning(
                "Очистка существующих портфелей и транзакций не реализована в этом скрипте.")
            logger.warning(
                "Пожалуйста, выполните очистку вручную или используйте сброс БД.")

        logger.info(f"Создание {num_portfolios} портфелей...")

        for i in range(num_portfolios):
            portfolio_name = f"Тестовый портфель #{i + 1}"
            portfolio_create = PortfolioCreate(name=portfolio_name)
            portfolio = await portfolio_repo.create_portfolio(portfolio_create)
            logger.info(
                f"Создан портфель: {portfolio.name} (ID: {portfolio.id})")

            logger.info(
                f"Создание {transactions_per_portfolio} транзакций для портфеля {portfolio.id}...")
            await create_random_transactions(
                db, portfolio.id, tickers, ticker_map, prices,
                transactions_per_portfolio
            )

            # Сбрасываем промежуточные изменения, но не коммитим до конца
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
        f"Запуск генератора с параметрами: портфелей={args.portfolios}, транзакций={args.transactions}, очистка={args.clear}"
    )

    asyncio.run(
        generate_portfolios(args.portfolios, args.transactions, args.clear))


if __name__ == "__main__":
    main()
