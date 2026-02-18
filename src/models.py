"""
Family Office Wealth OS - Database Models
Canonical data model for the wealth management system.
"""

import os
import enum
from datetime import datetime, date
from typing import Optional, List
from cryptography.fernet import Fernet
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime,
    Boolean, ForeignKey, Text, JSON, Numeric, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'wealth_os.db')

# Encryption key - stored locally
KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '.encryption_key')

def get_encryption_key():
    """Get or create encryption key for sensitive data."""
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
        with open(KEY_PATH, 'wb') as f:
            f.write(key)
        os.chmod(KEY_PATH, 0o600)  # Restrict access
        return key

# Initialize encryption
_fernet = None
def get_fernet():
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_encryption_key())
    return _fernet

def encrypt_value(value: str) -> str:
    """Encrypt a sensitive value."""
    if value is None:
        return None
    return get_fernet().encrypt(value.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    """Decrypt a sensitive value."""
    if encrypted is None:
        return None
    return get_fernet().decrypt(encrypted.encode()).decode()

# Create engine
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class EntityType(enum.Enum):
    CORPORATION = "corporation"
    INDIVIDUAL = "individual"
    TRUST = "trust"
    PARTNERSHIP = "partnership"
    FOUNDATION = "foundation"

class AccountType(enum.Enum):
    BANK = "bank"
    BROKERAGE = "brokerage"
    CUSTODIAN = "custodian"
    CREDIT_FACILITY = "credit_facility"

class InvestmentCategory(enum.Enum):
    PUBLIC_EQUITY = "Public Equity"
    FIXED_INCOME = "Fixed Income"
    FUND = "Fund"
    PRIVATE_DIRECT = "Private Direct"
    REAL_ESTATE = "Real Estate"
    CASH = "Cash"
    CRYPTO = "Crypto"
    OTHER = "Other"

class InvestmentStatus(enum.Enum):
    ACTIVE = "Active"
    EXITED = "Exited"
    WRITTEN_OFF = "Written-off"

class ValuationMethod(enum.Enum):
    MARKET_PRICE = "market_price"
    STATEMENT_NAV = "statement_nav"
    APPRAISAL = "appraisal"
    MODEL_ESTIMATE = "model_estimate"
    MANUAL = "manual"

class ValuationConfidence(enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class CashflowType(enum.Enum):
    ACTUAL = "Actual"
    FORECAST = "Forecast"
    SCHEDULED = "Scheduled"

class CashflowCategory(enum.Enum):
    CAPITAL_CALL = "Capital Call"
    DISTRIBUTION = "Distribution"
    FEES = "Fees"
    PAYROLL = "Payroll"
    REAL_ESTATE_OPS = "Real Estate Ops"
    DEBT_SERVICE = "Debt Service"
    TAX = "Tax"
    TRANSFER = "Transfer"
    INCOME = "Income"
    EXPENSE = "Expense"
    OTHER = "Other"

class DecisionStatus(enum.Enum):
    DRAFT = "Draft"
    PENDING = "Pending"
    APPROVED = "Approved"
    DECLINED = "Declined"
    IMPLEMENTED = "Implemented"

class DecisionType(enum.Enum):
    NEW_INVESTMENT = "New Investment"
    CAPITAL_CALL = "Fund Capital Call"
    REBALANCE = "Rebalance"
    INCREASE = "Increase Position"
    DECREASE = "Decrease Position"
    EXIT = "Exit Position"
    FX_CONVERSION = "FX Conversion"
    TRANSFER = "Transfer"
    REAL_ESTATE_SPEND = "Real Estate Spend"
    POLICY_EXCEPTION = "Policy Exception"

class FreshnessStatus(enum.Enum):
    FRESH = "Fresh"          # <= 7 days
    AGING = "Aging"          # 8-30 days
    STALE = "Stale"          # 31-120 days
    VERY_STALE = "Very Stale"  # > 120 days


# ============================================================================
# MODELS
# ============================================================================

class User(Base):
    """System users for authentication."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(200))
    email = Column(String(255))
    role = Column(String(50), default='ADVISOR')  # PRINCIPAL, ADVISOR, VIEWER
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class Entity(Base):
    """Investment entity (corporation, trust, individual, etc.)"""
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    entity_type = Column(String(50))  # corporation, individual, trust
    base_currency = Column(String(3), default='CAD')
    description = Column(Text)
    tags = Column(JSON)  # e.g., ["HoldingCo", "Active"]

    # Hierarchy
    parent_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)

    # Metadata
    owner_metadata = Column(JSON)  # Additional ownership info
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="entity")
    investments = relationship("Investment", back_populates="entity")
    cashflow_items = relationship("CashflowItem", back_populates="entity")
    risks = relationship("Risk", back_populates="entity")
    children = relationship("Entity", backref="parent", remote_side=[id])


class Account(Base):
    """Bank or brokerage account."""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)

    institution_name = Column(String(200), nullable=False)  # RBC, BMO, etc.
    account_name = Column(String(200))  # Friendly name
    account_number_encrypted = Column(String(500))  # Encrypted account number
    account_type = Column(String(50))  # bank, brokerage, custodian, credit_facility
    currency = Column(String(3), default='CAD')

    # For credit facilities
    credit_limit = Column(Float, default=0)
    credit_limit_encrypted = Column(String(500))  # Encrypted
    interest_rate = Column(Float)

    # Balance tracking (encrypted for sensitive data)
    current_balance = Column(Float, default=0)
    current_balance_encrypted = Column(String(500))

    # Data freshness
    data_source = Column(String(50), default='manual')  # manual, feed, statement_extract
    last_refreshed_at = Column(DateTime)
    freshness_status = Column(String(20), default='Fresh')

    # Metadata
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="accounts")
    investments = relationship("Investment", back_populates="account")

    def set_account_number(self, number: str):
        """Encrypt and store account number."""
        self.account_number_encrypted = encrypt_value(number)

    def get_account_number(self) -> str:
        """Decrypt and return account number."""
        return decrypt_value(self.account_number_encrypted)

    def set_balance(self, balance: float):
        """Store balance (encrypted for display, plain for calculations)."""
        self.current_balance = balance
        self.current_balance_encrypted = encrypt_value(str(balance))

    @property
    def account_number_masked(self) -> str:
        """Return masked account number for display."""
        number = self.get_account_number()
        if number and len(number) > 4:
            return '*' * (len(number) - 4) + number[-4:]
        return number


class Investment(Base):
    """Master investment record."""
    __tablename__ = 'investments'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)

    # Core info
    name = Column(String(300), nullable=False)
    symbol = Column(String(30))  # Ticker for public equities
    category = Column(String(50), nullable=False)  # Public Equity, Fund, Private Direct, etc.
    subtype = Column(String(100))  # T-bill, VC fund, PE fund, property, etc.
    currency = Column(String(3), default='CAD')

    # Position
    units = Column(Float, default=0)  # Shares, units
    share_class = Column(String(50))
    ownership_pct = Column(Float)  # For private investments

    # Cost basis (encrypted values available)
    cost_basis = Column(Float, default=0)
    cost_basis_encrypted = Column(String(500))
    cost_basis_date = Column(Date)
    cost_per_unit = Column(Float, default=0)

    # Current valuation
    current_value = Column(Float, default=0)
    current_value_encrypted = Column(String(500))
    current_price = Column(Float, default=0)
    last_price_update = Column(DateTime)

    # For funds/illiquid investments
    last_nav = Column(Float)
    last_nav_date = Column(Date)

    # Status and metadata
    status = Column(String(20), default='Active')  # Active, Exited, Written-off
    purchase_date = Column(Date)
    notes = Column(Text)  # Thesis, key terms

    # Data source tracking
    data_source = Column(String(50), default='manual')  # yahoo, manual, statement
    exchange = Column(String(20))  # TSX, NYSE, etc.

    # Freshness
    freshness_status = Column(String(20), default='Fresh')

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="investments")
    account = relationship("Account", back_populates="investments")
    valuations = relationship("Valuation", back_populates="investment", order_by="desc(Valuation.valuation_date)")
    commitments = relationship("Commitment", back_populates="investment")
    transactions = relationship("Transaction", back_populates="investment", order_by="Transaction.date")

    @property
    def unrealized_gain(self) -> float:
        """Calculate unrealized gain/loss."""
        return self.current_value - self.cost_basis

    @property
    def unrealized_gain_pct(self) -> float:
        """Calculate unrealized gain/loss percentage."""
        if self.cost_basis == 0:
            return 0
        return (self.current_value - self.cost_basis) / self.cost_basis * 100

    def set_values_encrypted(self):
        """Encrypt sensitive values."""
        self.cost_basis_encrypted = encrypt_value(str(self.cost_basis))
        self.current_value_encrypted = encrypt_value(str(self.current_value))


class Valuation(Base):
    """Investment valuation record with full audit trail."""
    __tablename__ = 'valuations'

    id = Column(Integer, primary_key=True)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=False)

    valuation_date = Column(Date, nullable=False)

    # Values in multiple currencies
    value_native = Column(Float, nullable=False)
    currency_native = Column(String(3), nullable=False)
    value_cad = Column(Float)
    value_usd = Column(Float)
    fx_rate_used = Column(Float)

    # Valuation metadata
    method = Column(String(50))  # market_price, statement_nav, appraisal, manual
    source = Column(String(100))  # custodian_feed, manager_statement, manual_entry
    confidence = Column(String(20), default='Medium')  # High, Medium, Low

    # Audit
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    audit_reason = Column(Text)  # Why this valuation was recorded

    # Document link
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=True)

    notes = Column(Text)

    # Relationships
    investment = relationship("Investment", back_populates="valuations")
    document = relationship("Document")


class Commitment(Base):
    """Fund commitment tracking for alternatives."""
    __tablename__ = 'commitments'

    id = Column(Integer, primary_key=True)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=False)

    # Commitment amounts
    total_commitment = Column(Float, nullable=False)
    total_commitment_currency = Column(String(3), default='CAD')
    unfunded_commitment = Column(Float, default=0)

    # Dates
    commitment_date = Column(Date)
    expected_end_date = Column(Date)

    # Call pattern
    expected_call_pattern = Column(String(50))  # front-loaded, steady, unknown

    # Tracking
    capital_called = Column(Float, default=0)
    distributions_received = Column(Float, default=0)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Freshness
    last_statement_date = Column(Date)
    freshness_status = Column(String(20), default='Fresh')

    # Relationships
    investment = relationship("Investment", back_populates="commitments")


class Transaction(Base):
    """Investment transactions."""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=False)

    transaction_type = Column(String(50), nullable=False)  # Buy, Sell, Dividend, etc.
    date = Column(Date, nullable=False)

    # Transaction details
    quantity = Column(Float, default=0)
    price_per_unit = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default='CAD')
    fx_rate = Column(Float, default=1.0)

    # Fees
    fees = Column(Float, default=0)
    taxes_withheld = Column(Float, default=0)

    # Realized gains
    realized_gain = Column(Float, default=0)

    # Metadata
    notes = Column(Text)
    reference = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    investment = relationship("Investment", back_populates="transactions")


class CashflowItem(Base):
    """Cashflow tracking (actual and forecast)."""
    __tablename__ = 'cashflow_items'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=True)

    # Timing
    date = Column(Date, nullable=False)

    # Amount (positive = inflow, negative = outflow)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='CAD')

    # Classification
    cashflow_type = Column(String(20), nullable=False)  # Actual, Forecast, Scheduled
    category = Column(String(50))  # Capital Call, Distribution, Fees, etc.

    # Details
    description = Column(String(500))
    confidence = Column(String(20), default='Medium')  # For forecasts

    # Source
    source = Column(String(50), default='manual')  # manual, extracted, rule_generated
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(100))  # e.g., "monthly", "quarterly"

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="cashflow_items")


class RealEstateProperty(Base):
    """Real estate property tracking."""
    __tablename__ = 'real_estate_properties'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=True)  # Link to investment

    # Property details
    name = Column(String(200), nullable=False)
    address = Column(String(500))
    property_type = Column(String(50))  # residential, commercial, land

    # Ownership
    ownership_pct = Column(Float, default=100.0)
    held_by = Column(String(200))  # Personally, Corp, Trust

    # Valuation
    fair_market_value = Column(Float, default=0)
    fmv_encrypted = Column(String(500))
    last_appraisal_date = Column(Date)
    purchase_price = Column(Float, default=0)
    purchase_date = Column(Date)

    # Financing
    mortgage_balance = Column(Float, default=0)
    mortgage_rate = Column(Float)
    mortgage_payment_monthly = Column(Float, default=0)

    # Operations
    is_income_producing = Column(Boolean, default=False)
    annual_rental_income = Column(Float, default=0)
    annual_operating_costs = Column(Float, default=0)
    annual_property_tax = Column(Float, default=0)
    annual_insurance = Column(Float, default=0)

    # Net carry
    @property
    def net_annual_carry(self) -> float:
        """Calculate net annual carrying cost."""
        income = self.annual_rental_income if self.is_income_producing else 0
        costs = (
            self.annual_operating_costs +
            self.annual_property_tax +
            self.annual_insurance +
            (self.mortgage_payment_monthly * 12)
        )
        return income - costs

    # Metadata
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Document(Base):
    """Document storage and linking."""
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)

    # Document info
    title = Column(String(300), nullable=False)
    doc_type = Column(String(50))  # statement, capital_call, distribution_notice, appraisal, memo
    file_path = Column(String(500))  # Local file path
    file_name = Column(String(300))
    file_size = Column(Integer)
    mime_type = Column(String(100))

    # Dates
    doc_date = Column(Date)  # Date on the document
    received_date = Column(Date)

    # Linking
    entity_ids = Column(JSON)  # List of entity IDs
    investment_ids = Column(JSON)  # List of investment IDs
    account_ids = Column(JSON)  # List of account IDs

    # Extraction
    extracted_fields = Column(JSON)  # Key-value pairs extracted
    extraction_confidence = Column(Float)
    needs_review = Column(Boolean, default=False)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))


class Decision(Base):
    """Decision tracking for principal approval workflow."""
    __tablename__ = 'decisions'

    id = Column(Integer, primary_key=True)

    # Status
    status = Column(String(20), default='Draft')  # Draft, Pending, Approved, Declined, Implemented
    decision_type = Column(String(50), nullable=False)  # New Investment, Capital Call, etc.

    # Ownership
    proposer_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)
    impacted_entity_ids = Column(JSON)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(Date)
    approved_at = Column(DateTime)
    implemented_at = Column(DateTime)

    # Content
    summary = Column(String(500), nullable=False)  # 1-2 lines
    rationale = Column(Text)
    options = Column(JSON)  # Structured options
    risk_notes = Column(Text)

    # Approvals
    approvals = Column(JSON)  # List of approval records

    # Links
    investment_ids = Column(JSON)
    document_ids = Column(JSON)

    # AI assistance
    ai_assist_log = Column(JSON)  # What AI suggested

    # Metadata
    notes = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FXRateSnapshot(Base):
    """FX rate snapshots."""
    __tablename__ = 'fx_rate_snapshots'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    pair = Column(String(10), nullable=False)  # USDCAD, EURCAD
    rate = Column(Float, nullable=False)
    source = Column(String(50), default='manual')  # manual, bank_of_canada, api

    # Unique constraint on pair + date
    __table_args__ = (
        Index('ix_fx_pair_date', 'pair', 'timestamp'),
    )


class ActivityLog(Base):
    """Activity log for 'What Changed' feature."""
    __tablename__ = 'activity_log'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Event type
    event_type = Column(String(50), nullable=False)  # valuation_change, cash_change, etc.

    # Affected objects
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)

    # Change details
    description = Column(String(500))
    old_value = Column(Float)
    new_value = Column(Float)
    change_amount = Column(Float)
    change_pct = Column(Float)

    # Threshold
    is_material = Column(Boolean, default=False)  # Met threshold for material change

    # Source
    source = Column(String(100))
    created_by = Column(String(100))


class PortfolioSnapshot(Base):
    """Daily portfolio snapshots for performance tracking."""
    __tablename__ = 'portfolio_snapshots'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)  # Null = consolidated

    # Values
    total_value_cad = Column(Float, nullable=False)
    total_value_usd = Column(Float)
    total_cost_basis = Column(Float, nullable=False)

    # Allocation snapshot
    allocation_json = Column(JSON)

    # FX
    usd_cad_rate = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('date', 'entity_id', name='uq_snapshot_date_entity'),
    )


class Benchmark(Base):
    """Benchmark data for performance comparison."""
    __tablename__ = 'benchmarks'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)  # ^GSPC, ^GSPTSE
    name = Column(String(100))
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uq_benchmark_symbol_date'),
    )


class Risk(Base):
    """Risk register entry."""
    __tablename__ = 'risks'

    id = Column(Integer, primary_key=True)

    # Core fields
    title = Column(String(300), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False)

    # Entity linkage
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True)

    # Optional linkage to investments
    investment_id = Column(Integer, ForeignKey('investments.id'), nullable=True)

    # Risk owner
    risk_owner = Column(String(200))

    # Assessment scales (0-5)
    likelihood = Column(Integer, default=0)
    impact = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)

    # Status
    status = Column(String(50), default='Identified')

    # Mitigation
    mitigation_plan = Column(Text)
    mitigation_actions = Column(Text)

    # Review schedule
    review_frequency = Column(String(50))
    next_review_date = Column(Date)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="risks")
    investment = relationship("Investment")


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def init_db():
    """Initialize the database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(engine)

    # Create default entities if they don't exist
    session = Session()
    try:
        if session.query(Entity).count() == 0:
            session.add(Entity(
                name="Wilkinson Ventures Ltd",
                entity_type="corporation",
                base_currency="CAD",
                description="Main holding corporation",
                tags=["HoldingCo"]
            ))
            session.add(Entity(
                name="Andrew Wilkinson",
                entity_type="individual",
                base_currency="CAD",
                description="Personal investments"
            ))
            session.commit()
    finally:
        session.close()


def get_session():
    """Get a database session."""
    return Session()


def calculate_freshness(last_updated: datetime) -> str:
    """Calculate freshness status based on last update time."""
    if last_updated is None:
        return "Very Stale"

    days_old = (datetime.utcnow() - last_updated).days

    if days_old <= 7:
        return "Fresh"
    elif days_old <= 30:
        return "Aging"
    elif days_old <= 120:
        return "Stale"
    else:
        return "Very Stale"


# Don't auto-initialize on import - let the app control this
