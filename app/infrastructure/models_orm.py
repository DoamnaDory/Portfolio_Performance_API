from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Table
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(String, nullable=False)
    quantity = Column(Numeric(18, 8), nullable=False)
    price = Column(Numeric(18, 8), nullable=False)
    transaction_type = Column(String, nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)