"""
Database models and operations for the Investment Register.
Uses SQLAlchemy with SQLite for local storage.
"""

import os
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'investments.db')

# Create engine
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class AssetClass(enum.Enum):
    PUBLIC_EQUITY = "Public Equities"
    PRIVATE_BUSINESS = "Private Business"
    VENTURE_FUND = "Venture Fund"
    VENTURE_ENTITY = "Venture Entity"
    REAL_ESTATE = "Real Estate"
    GOLD = "Gold"
    CRYPTO = "Crypto"
    CASH = "Cash & Equivalents"
    BONDS = "Bonds"
    DERIVATIVES = "Derivatives/Options"


class TransactionType(enum.Enum):
    BUY = "Buy"
    SELL = "Sell"
    DIVIDEND = "Dividend"
    DISTRIBUTION = "Distribution"
    CAPITAL_CALL = "Capital Call"
    CAPITAL_RETURN = "Capital Return"
    INTEREST = "Interest"
    FEE = "Fee"
    TRANSFER_IN = "Transfer In"
    TRANSFER_OUT = "Transfer Out"
    VALUATION = "Valuation Update"


class Entity(Base):
    """Investment entity (HoldCo, Personal, etc.)"""
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    entity_type = Column(String(50))  # corporation, individual, trust, etc.
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    investments = relationship("Investment", back_populates="entity")


class Investment(Base):
    """Individual investment/position"""
    __tablename__ = 'investments'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    symbol = Column(String(20))  # For public equities, crypto
    asset_class = Column(String(50), nullable=False)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)

    # Currency
    currency = Column(String(3), default='CAD')

    # Current position
    quantity = Column(Float, default=0)
    cost_basis = Column(Float, default=0)  # Total cost basis
    cost_per_unit = Column(Float, default=0)

    # Current valuation
    current_price = Column(Float, default=0)
    current_value = Column(Float, default=0)
    last_price_update = Column(DateTime)

    # For illiquid investments
    last_nav = Column(Float)  # Last reported NAV
    last_nav_date = Column(Date)

    # Metadata
    purchase_date = Column(Date)  # Initial purchase
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # For market data lookup
    exchange = Column(String(20))  # TSX, NYSE, NASDAQ, etc.
    data_source = Column(String(50))  # yahoo, kraken, manual

    # Relationships
    entity = relationship("Entity", back_populates="investments")
    transactions = relationship("Transaction", back_populates="investment", order_by="Transaction.date")
    valuations = relationship("Valuation", back_populates="investment", order_by="Valuation.date")

    @property
    def unrealized_gain(self) -> float:
        """Calculate unrealized gain/loss"""
        return self.current_value - self.cost_basis

    @property
    def unrealized_gain_pct(self) -> float:
        """Calculate unrealized gain/loss percentage"""
        if self.cost_basis == 0:
            return 0
        return (self.current_value - self.cost_basis) / self.cost_basis * 100


class Transaction(Base):
    """Investment transactions"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)

    # Transaction details
    quantity = Column(Float, default=0)
    price_per_unit = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default='CAD')
    fx_rate = Column(Float, default=1.0)  # FX rate to CAD at time of transaction

    # Fees and taxes
    fees = Column(Float, default=0)
    taxes_withheld = Column(Float, default=0)

    # For tracking realized gains
    realized_gain = Column(Float, default=0)

    # Metadata
    notes = Column(Text)
    reference = Column(String(100))  # External reference number
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    investment = relationship("Investment", back_populates="transactions")


class Valuation(Base):
    """Manual valuations for illiquid investments"""
    __tablename__ = 'valuations'

    id = Column(Integer, primary_key=True)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    value_per_unit = Column(Float)
    source = Column(String(100))  # NAV statement, appraisal, etc.
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    investment = relationship("Investment", back_populates="valuations")


class FXRate(Base):
    """Historical FX rates"""
    __tablename__ = 'fx_rates'

    id = Column(Integer, primary_key=True)
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    date = Column(Date, nullable=False)
    rate = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Benchmark(Base):
    """Benchmark performance data"""
    __tablename__ = 'benchmarks'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100))
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PortfolioSnapshot(Base):
    """Daily portfolio snapshots for performance tracking"""
    __tablename__ = 'portfolio_snapshots'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    total_value_cad = Column(Float, nullable=False)
    total_cost_basis = Column(Float, nullable=False)

    # By entity
    entity_id = Column(Integer, ForeignKey('entities.id'))

    # Allocation snapshot (JSON stored as text)
    allocation_json = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# Database operations
def init_db():
    """Initialize the database"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(engine)

    # Create default entities if they don't exist
    session = Session()
    try:
        if session.query(Entity).count() == 0:
            session.add(Entity(name="HoldCo", entity_type="corporation", description="Main holding corporation"))
            session.add(Entity(name="Personal", entity_type="individual", description="Personal investments"))
            session.commit()
    finally:
        session.close()


def get_session():
    """Get a database session"""
    return Session()


# CRUD Operations
def get_all_entities(session) -> List[Entity]:
    """Get all entities"""
    return session.query(Entity).all()


def get_all_investments(session, active_only: bool = True) -> List[Investment]:
    """Get all investments"""
    query = session.query(Investment)
    if active_only:
        query = query.filter(Investment.is_active == True)
    return query.all()


def get_investments_by_entity(session, entity_id: int, active_only: bool = True) -> List[Investment]:
    """Get investments for a specific entity"""
    query = session.query(Investment).filter(Investment.entity_id == entity_id)
    if active_only:
        query = query.filter(Investment.is_active == True)
    return query.all()


def get_investments_by_asset_class(session, asset_class: str, active_only: bool = True) -> List[Investment]:
    """Get investments for a specific asset class"""
    query = session.query(Investment).filter(Investment.asset_class == asset_class)
    if active_only:
        query = query.filter(Investment.is_active == True)
    return query.all()


def get_investment_by_id(session, investment_id: int) -> Optional[Investment]:
    """Get a specific investment by ID"""
    return session.query(Investment).filter(Investment.id == investment_id).first()


def get_investment_by_symbol(session, symbol: str) -> Optional[Investment]:
    """Get a specific investment by symbol"""
    return session.query(Investment).filter(Investment.symbol == symbol).first()


def add_investment(session, **kwargs) -> Investment:
    """Add a new investment"""
    investment = Investment(**kwargs)
    session.add(investment)
    session.commit()
    return investment


def add_transaction(session, **kwargs) -> Transaction:
    """Add a new transaction"""
    transaction = Transaction(**kwargs)
    session.add(transaction)
    session.commit()

    # Update investment position
    update_investment_position(session, transaction.investment_id)

    return transaction


def update_investment_position(session, investment_id: int):
    """Recalculate investment position from transactions"""
    investment = get_investment_by_id(session, investment_id)
    if not investment:
        return

    transactions = session.query(Transaction).filter(
        Transaction.investment_id == investment_id
    ).order_by(Transaction.date).all()

    quantity = 0
    cost_basis = 0

    for tx in transactions:
        if tx.transaction_type in ['Buy', 'Capital Call', 'Transfer In']:
            quantity += tx.quantity
            cost_basis += tx.total_amount
        elif tx.transaction_type in ['Sell', 'Capital Return', 'Transfer Out']:
            if quantity > 0:
                # Calculate cost basis for sold units (average cost method)
                avg_cost_per_unit = cost_basis / quantity if quantity else 0
                cost_basis -= avg_cost_per_unit * tx.quantity
            quantity -= tx.quantity

    investment.quantity = quantity
    investment.cost_basis = cost_basis
    investment.cost_per_unit = cost_basis / quantity if quantity > 0 else 0

    # Update purchase date to first transaction
    if transactions:
        buy_transactions = [t for t in transactions if t.transaction_type in ['Buy', 'Capital Call', 'Transfer In']]
        if buy_transactions:
            investment.purchase_date = buy_transactions[0].date

    session.commit()


def add_valuation(session, investment_id: int, date: date, value: float, source: str = None, notes: str = None) -> Valuation:
    """Add a manual valuation for an investment"""
    investment = get_investment_by_id(session, investment_id)
    if not investment:
        raise ValueError(f"Investment {investment_id} not found")

    value_per_unit = value / investment.quantity if investment.quantity > 0 else value

    valuation = Valuation(
        investment_id=investment_id,
        date=date,
        value=value,
        value_per_unit=value_per_unit,
        source=source,
        notes=notes
    )
    session.add(valuation)

    # Update investment current value
    investment.last_nav = value
    investment.last_nav_date = date
    investment.current_value = value
    investment.current_price = value_per_unit

    session.commit()
    return valuation


def get_latest_fx_rate(session, from_currency: str, to_currency: str) -> float:
    """Get the latest FX rate"""
    if from_currency == to_currency:
        return 1.0

    rate = session.query(FXRate).filter(
        FXRate.from_currency == from_currency,
        FXRate.to_currency == to_currency
    ).order_by(FXRate.date.desc()).first()

    return rate.rate if rate else 1.0


def save_fx_rate(session, from_currency: str, to_currency: str, rate_date: date, rate: float):
    """Save an FX rate"""
    fx_rate = FXRate(
        from_currency=from_currency,
        to_currency=to_currency,
        date=rate_date,
        rate=rate
    )
    session.add(fx_rate)
    session.commit()


def get_portfolio_summary(session) -> dict:
    """Get a summary of the entire portfolio"""
    investments = get_all_investments(session, active_only=True)

    total_value_cad = 0
    total_cost_basis = 0
    by_entity = {}
    by_asset_class = {}

    for inv in investments:
        # Convert to CAD if needed
        fx_rate = get_latest_fx_rate(session, inv.currency, 'CAD')
        value_cad = inv.current_value * fx_rate
        cost_cad = inv.cost_basis * fx_rate

        total_value_cad += value_cad
        total_cost_basis += cost_cad

        # By entity
        entity_name = inv.entity.name
        if entity_name not in by_entity:
            by_entity[entity_name] = {'value': 0, 'cost': 0}
        by_entity[entity_name]['value'] += value_cad
        by_entity[entity_name]['cost'] += cost_cad

        # By asset class
        if inv.asset_class not in by_asset_class:
            by_asset_class[inv.asset_class] = {'value': 0, 'cost': 0}
        by_asset_class[inv.asset_class]['value'] += value_cad
        by_asset_class[inv.asset_class]['cost'] += cost_cad

    return {
        'total_value_cad': total_value_cad,
        'total_cost_basis': total_cost_basis,
        'total_gain': total_value_cad - total_cost_basis,
        'total_gain_pct': ((total_value_cad - total_cost_basis) / total_cost_basis * 100) if total_cost_basis > 0 else 0,
        'by_entity': by_entity,
        'by_asset_class': by_asset_class,
        'investment_count': len(investments)
    }


# Initialize database on module import
init_db()
