"""
Migration script to import data from the master spreadsheet into the database.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models import (
    Entity, Account, Investment, Valuation,
    Commitment, Transaction, CashflowItem, RealEstateProperty,
    FXRateSnapshot, encrypt_value, Base, DB_PATH
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def parse_date(val):
    """Parse date from various formats."""
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return pd.to_datetime(val).date()
    except:
        return None


def parse_float(val):
    """Parse float, handling NaN and strings."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, str):
        val = val.replace('$', '').replace(',', '').replace('%', '').strip()
        if val == '' or val == '-':
            return 0.0
    try:
        return float(val)
    except:
        return 0.0


def get_entity(entities, name):
    """Get entity by name or alias."""
    if pd.isna(name):
        return entities.get("Wilkinson Ventures Ltd")

    name = str(name).strip().upper()

    if name in ['WV', 'WVUS']:
        return entities.get("Wilkinson Ventures Ltd")
    elif name in ['PERSONAL', 'PERSONALLY', 'AW']:
        return entities.get("Andrew Wilkinson")

    # Fallback
    return entities.get("Wilkinson Ventures Ltd")


def migrate_spreadsheet(filepath: str, session):
    """
    Migrate data from the master spreadsheet.
    """
    close_session = False

    try:
        print(f"Loading spreadsheet: {filepath}")
        xl = pd.ExcelFile(filepath)
        print(f"Found sheets: {xl.sheet_names}")

        # Get or create entities
        entities = {}

        wv = session.query(Entity).filter(Entity.name == "Wilkinson Ventures Ltd").first()
        if not wv:
            wv = Entity(
                name="Wilkinson Ventures Ltd",
                entity_type="corporation",
                base_currency="CAD",
                tags=["HoldingCo"]
            )
            session.add(wv)
            session.flush()
        entities["Wilkinson Ventures Ltd"] = wv

        aw = session.query(Entity).filter(Entity.name == "Andrew Wilkinson").first()
        if not aw:
            aw = Entity(
                name="Andrew Wilkinson",
                entity_type="individual",
                base_currency="CAD"
            )
            session.add(aw)
            session.flush()
        entities["Andrew Wilkinson"] = aw

        # ====================================================================
        # 1. Import Banking - Extract FX Rates
        # ====================================================================
        print("\n--- Importing Banking & FX Rates ---")
        try:
            df_banking = pd.read_excel(xl, sheet_name='3. Banking', header=None)

            for idx, row in df_banking.iterrows():
                # Look for USD/CAD rate
                for col in range(len(row)):
                    cell = str(row.get(col, ''))
                    if 'USD/CAD' in cell:
                        # Rate should be in next column or nearby
                        for offset in [1, 2]:
                            if col + offset < len(row):
                                rate = parse_float(row.get(col + offset))
                                if 1.0 < rate < 2.0:  # Reasonable USD/CAD range
                                    fx = FXRateSnapshot(
                                        pair='USDCAD',
                                        rate=rate,
                                        source='spreadsheet_import'
                                    )
                                    session.add(fx)
                                    print(f"  FX Rate: USD/CAD = {rate}")
                                    break

            # Create bank accounts
            rbc_account = Account(
                entity_id=wv.id,
                institution_name='RBC',
                account_name='RBC Main',
                account_type='bank',
                currency='CAD',
                data_source='manual'
            )
            session.add(rbc_account)

            bmo_account = Account(
                entity_id=wv.id,
                institution_name='BMO',
                account_name='BMO Account',
                account_type='bank',
                currency='CAD',
                data_source='manual'
            )
            session.add(bmo_account)

            rbcds_account = Account(
                entity_id=wv.id,
                institution_name='RBC Dominion Securities',
                account_name='RBC DS Brokerage',
                account_type='brokerage',
                currency='CAD',
                data_source='manual'
            )
            session.add(rbcds_account)

            rbcdi_account = Account(
                entity_id=wv.id,
                institution_name='RBC Direct Investing',
                account_name='RBC DI',
                account_type='brokerage',
                currency='CAD',
                data_source='manual'
            )
            session.add(rbcdi_account)

            session.flush()
            print("  Created 4 bank/brokerage accounts")

        except Exception as e:
            print(f"  Warning: Banking import issue: {e}")

        # ====================================================================
        # 2. Import Investments (Sheet 5)
        # ====================================================================
        print("\n--- Importing Investments ---")
        try:
            df = pd.read_excel(xl, sheet_name='5. Investments', header=None)

            # Header is at row 6 (0-indexed)
            # Columns: 0=Type, 1=Notes, 2=Entity, 3=Company/Fund, 4=Type, 5=Units, 6=Date, 7=Cost CAD, 8=MTM CAD, 9=MTM USD

            imported = 0
            for idx in range(7, len(df)):  # Start after header
                row = df.iloc[idx]

                # Get company name from column 3
                name = row.get(3)
                if pd.isna(name) or str(name).strip() == '' or len(str(name).strip()) < 2:
                    continue

                name = str(name).strip()

                # Skip totals and headers
                if any(x in name.lower() for x in ['total', 'subtotal', 'sum']):
                    continue

                entity = get_entity(entities, row.get(2))
                units = parse_float(row.get(5))
                investment_date = parse_date(row.get(6))
                cost_cad = parse_float(row.get(7))
                mtm_cad = parse_float(row.get(8))
                mtm_usd = parse_float(row.get(9))

                # Calculate current value
                current_value = mtm_cad if mtm_cad > 0 else (mtm_usd * 1.37 if mtm_usd > 0 else cost_cad)

                # Skip if no values
                if cost_cad == 0 and current_value == 0:
                    continue

                # Check if already exists
                existing = session.query(Investment).filter(
                    Investment.name == name,
                    Investment.entity_id == entity.id
                ).first()

                if existing:
                    existing.cost_basis = cost_cad if cost_cad > 0 else existing.cost_basis
                    existing.current_value = current_value if current_value > 0 else existing.current_value
                    existing.units = units if units > 0 else existing.units
                else:
                    inv = Investment(
                        entity_id=entity.id,
                        name=name,
                        category="Private Direct",
                        currency='CAD',
                        units=units if units > 0 else 1,
                        cost_basis=cost_cad,
                        current_value=current_value,
                        cost_per_unit=cost_cad / units if units > 0 else cost_cad,
                        purchase_date=investment_date,
                        status='Active',
                        data_source='spreadsheet_import'
                    )
                    session.add(inv)
                    imported += 1

            session.flush()
            print(f"  Imported {imported} investments")

        except Exception as e:
            print(f"  Warning: Investments import issue: {e}")
            import traceback
            traceback.print_exc()

        # ====================================================================
        # 3. Import Fund Investments (Sheet 7)
        # ====================================================================
        print("\n--- Importing Fund Investments ---")
        try:
            df = pd.read_excel(xl, sheet_name='7. Fund Investments', header=None)

            # Header at row 1
            # Columns: 0=LP, 2=Entity, 3=Company/Fund, 4=Date, 5=Fee, 6=CAD(cost),
            #          7=MTM CAD, 8=MTM USD, 9=FMV, 12=Total Commitment CAD,
            #          13=Total Commitment USD, 14=Remaining Commitment

            imported = 0
            for idx in range(2, len(df)):  # Start after header
                row = df.iloc[idx]

                name = row.get(3)
                if pd.isna(name) or str(name).strip() == '' or len(str(name).strip()) < 2:
                    continue

                name = str(name).strip()

                if any(x in name.lower() for x in ['total', 'subtotal', 'sum']):
                    continue

                entity = get_entity(entities, row.get(2))
                investment_date = parse_date(row.get(4))
                cost_cad = parse_float(row.get(6))
                mtm_cad = parse_float(row.get(7))
                mtm_usd = parse_float(row.get(8))
                fmv = parse_float(row.get(9))
                total_commitment_cad = parse_float(row.get(12))
                total_commitment_usd = parse_float(row.get(13))
                remaining_commitment = parse_float(row.get(14))

                # Current value priority: FMV > MTM CAD > MTM USD converted
                current_value = fmv if fmv > 0 else (mtm_cad if mtm_cad > 0 else (mtm_usd * 1.37 if mtm_usd > 0 else cost_cad))

                # Total commitment (prefer CAD, convert USD if needed)
                total_commitment = total_commitment_cad if total_commitment_cad > 0 else (total_commitment_usd * 1.37 if total_commitment_usd > 0 else 0)

                if cost_cad == 0 and current_value == 0 and total_commitment == 0:
                    continue

                existing = session.query(Investment).filter(
                    Investment.name == name,
                    Investment.entity_id == entity.id
                ).first()

                if existing:
                    existing.cost_basis = cost_cad if cost_cad > 0 else existing.cost_basis
                    existing.current_value = current_value if current_value > 0 else existing.current_value
                    existing.category = "Fund"
                    inv = existing
                else:
                    inv = Investment(
                        entity_id=entity.id,
                        name=name,
                        category="Fund",
                        subtype="VC/PE Fund",
                        currency='CAD',
                        units=1,
                        cost_basis=cost_cad,
                        current_value=current_value if current_value > 0 else cost_cad,
                        purchase_date=investment_date,
                        status='Active',
                        data_source='spreadsheet_import'
                    )
                    session.add(inv)
                    session.flush()
                    imported += 1

                # Add commitment if available
                if total_commitment > 0 or remaining_commitment > 0:
                    existing_commit = session.query(Commitment).filter(
                        Commitment.investment_id == inv.id
                    ).first()

                    if existing_commit:
                        existing_commit.total_commitment = total_commitment
                        existing_commit.unfunded_commitment = remaining_commitment
                    else:
                        commit = Commitment(
                            investment_id=inv.id,
                            total_commitment=total_commitment,
                            total_commitment_currency='CAD',
                            unfunded_commitment=remaining_commitment,
                            capital_called=total_commitment - remaining_commitment if total_commitment > remaining_commitment else 0,
                            commitment_date=investment_date
                        )
                        session.add(commit)

            session.flush()
            print(f"  Imported {imported} fund investments")

        except Exception as e:
            print(f"  Warning: Fund investments import issue: {e}")
            import traceback
            traceback.print_exc()

        # ====================================================================
        # 4. Import RP Investments (Sheet 8)
        # ====================================================================
        print("\n--- Importing RP Investments ---")
        try:
            df = pd.read_excel(xl, sheet_name='8. RP Investments', header=None)

            # Header at row 1
            # Columns: 0=LP, 1=Note, 2=Entity, 3=Company/Fund, 4=Date, 5=%Ownership,
            #          6=Cost(CAD), 7=MTM CAD, 8=MTM USD, 9=FMV

            imported = 0
            for idx in range(2, len(df)):
                row = df.iloc[idx]

                name = row.get(3)
                if pd.isna(name) or str(name).strip() == '' or len(str(name).strip()) < 2:
                    continue

                name = str(name).strip()

                if any(x in name.lower() for x in ['total', 'subtotal', 'sum', 'direct wv']):
                    continue

                entity = get_entity(entities, row.get(2))
                ownership_pct = parse_float(row.get(5))
                cost_cad = parse_float(row.get(6))
                mtm_cad = parse_float(row.get(7))
                mtm_usd = parse_float(row.get(8))
                fmv = parse_float(row.get(9))

                current_value = fmv if fmv > 0 else (mtm_cad if mtm_cad > 0 else (mtm_usd * 1.37 if mtm_usd > 0 else cost_cad))

                if cost_cad == 0 and current_value == 0:
                    continue

                # Convert ownership to percentage
                if ownership_pct > 0 and ownership_pct <= 1:
                    ownership_pct = ownership_pct * 100

                existing = session.query(Investment).filter(
                    Investment.name == name,
                    Investment.entity_id == entity.id
                ).first()

                if not existing:
                    inv = Investment(
                        entity_id=entity.id,
                        name=name,
                        category="Private Direct",
                        subtype="Related Party",
                        currency='CAD',
                        units=1,
                        ownership_pct=ownership_pct if ownership_pct > 0 else None,
                        cost_basis=cost_cad,
                        current_value=current_value if current_value > 0 else cost_cad,
                        status='Active',
                        data_source='spreadsheet_import'
                    )
                    session.add(inv)
                    imported += 1

            session.flush()
            print(f"  Imported {imported} related party investments")

        except Exception as e:
            print(f"  Warning: RP investments import issue: {e}")

        # ====================================================================
        # 5. Import Real Estate (Sheet 9)
        # ====================================================================
        print("\n--- Importing Real Estate ---")
        try:
            df = pd.read_excel(xl, sheet_name='9. Real Estate', header=None)

            imported = 0
            for idx in range(3, len(df)):  # Skip headers
                row = df.iloc[idx]

                name = row.get(1)
                if pd.isna(name) or str(name).strip() == '':
                    continue

                name = str(name).strip()

                if any(x in name.lower() for x in ['real estate', 'total', 'nan']):
                    continue

                if len(name) < 3:
                    continue

                fmv = parse_float(row.get(2))
                held_by = str(row.get(3, '')).strip() if pd.notna(row.get(3)) else 'Personally'

                if fmv == 0:
                    continue

                # Determine entity
                if 'personal' in held_by.lower():
                    entity = entities["Andrew Wilkinson"]
                else:
                    entity = entities["Wilkinson Ventures Ltd"]

                # Check if exists
                existing = session.query(RealEstateProperty).filter(
                    RealEstateProperty.name == name
                ).first()

                if not existing:
                    is_income = 'apartment' in name.lower() or 'rental' in name.lower() or 'commercial' in name.lower()

                    prop = RealEstateProperty(
                        entity_id=entity.id,
                        name=name,
                        held_by=held_by,
                        fair_market_value=fmv,
                        is_income_producing=is_income
                    )
                    session.add(prop)

                    # Also create as investment
                    inv = Investment(
                        entity_id=entity.id,
                        name=f"Real Estate: {name}",
                        category="Real Estate",
                        currency='CAD',
                        units=1,
                        cost_basis=fmv,
                        current_value=fmv,
                        status='Active',
                        data_source='spreadsheet_import'
                    )
                    session.add(inv)
                    imported += 1

            session.flush()
            print(f"  Imported {imported} real estate properties")

        except Exception as e:
            print(f"  Warning: Real estate import issue: {e}")

        # ====================================================================
        # 6. Import Tiny stock data (Sheet 6)
        # ====================================================================
        print("\n--- Importing Tiny Stock ---")
        try:
            df = pd.read_excel(xl, sheet_name='6. Tiny', header=None)

            # Look for Tiny price
            for idx in range(len(df)):
                row = df.iloc[idx]
                if str(row.get(1, '')).strip() == 'Price':
                    price = parse_float(row.get(2))
                    if price > 0:
                        # Add/update Tiny investment
                        existing = session.query(Investment).filter(
                            Investment.name == 'Tiny Ltd',
                            Investment.symbol == 'TINY.V'
                        ).first()

                        if existing:
                            existing.current_price = price
                            existing.last_price_update = datetime.utcnow()
                        else:
                            inv = Investment(
                                entity_id=entities["Wilkinson Ventures Ltd"].id,
                                name='Tiny Ltd',
                                symbol='TINY.V',
                                category='Public Equity',
                                currency='CAD',
                                current_price=price,
                                exchange='TSXV',
                                data_source='yahoo',
                                status='Active'
                            )
                            session.add(inv)
                        print(f"  Tiny price: ${price}")
                        break

        except Exception as e:
            print(f"  Warning: Tiny import issue: {e}")

        # ====================================================================
        # Commit all changes
        # ====================================================================
        session.commit()
        print("\n" + "="*50)
        print("MIGRATION COMPLETE")
        print("="*50)

        # Print summary
        print(f"\nDatabase Summary:")
        print(f"  Entities: {session.query(Entity).count()}")
        print(f"  Accounts: {session.query(Account).count()}")
        print(f"  Investments: {session.query(Investment).count()}")
        print(f"  - Private Direct: {session.query(Investment).filter(Investment.category == 'Private Direct').count()}")
        print(f"  - Funds: {session.query(Investment).filter(Investment.category == 'Fund').count()}")
        print(f"  - Real Estate: {session.query(Investment).filter(Investment.category == 'Real Estate').count()}")
        print(f"  - Public Equity: {session.query(Investment).filter(Investment.category == 'Public Equity').count()}")
        print(f"  Commitments: {session.query(Commitment).count()}")
        print(f"  Real Estate Properties: {session.query(RealEstateProperty).count()}")
        print(f"  FX Rates: {session.query(FXRateSnapshot).count()}")

        # Calculate totals
        total_cost = session.query(Investment).with_entities(
            Investment.cost_basis
        ).all()
        total_value = session.query(Investment).with_entities(
            Investment.current_value
        ).all()

        total_cost_sum = sum([c[0] or 0 for c in total_cost])
        total_value_sum = sum([v[0] or 0 for v in total_value])

        print(f"\nPortfolio Totals (CAD):")
        print(f"  Total Cost Basis: ${total_cost_sum:,.2f}")
        print(f"  Total Current Value: ${total_value_sum:,.2f}")
        print(f"  Unrealized Gain/Loss: ${total_value_sum - total_cost_sum:,.2f}")

    except Exception as e:
        session.rollback()
        print(f"\nError during migration: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        if close_session:
            session.close()


def create_fresh_engine():
    """Create a fresh database engine."""
    engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    return engine

def reset_database():
    """Reset the database completely."""
    # Remove old database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Database reset.")

    # Create data directory if needed
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Create fresh engine and tables
    engine = create_fresh_engine()
    Base.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    spreadsheet_path = Path(__file__).parent.parent / "data" / "AW Total Financial Position - Master.xlsx"

    if len(sys.argv) > 1:
        if sys.argv[1] != '--reset':
            spreadsheet_path = Path(sys.argv[1])

    if not spreadsheet_path.exists():
        print(f"Error: Spreadsheet not found at {spreadsheet_path}")
        sys.exit(1)

    # Reset for clean import
    engine = reset_database()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        migrate_spreadsheet(str(spreadsheet_path), session)
    finally:
        session.close()
