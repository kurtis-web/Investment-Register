"""
Data importers for the Investment Register.
Supports CSV/Excel import and Google Sheets integration.
"""

import os
import pandas as pd
import yaml
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import json

from .database import (
    get_session, Entity, Investment, Transaction, Valuation,
    add_investment, add_transaction, add_valuation,
    get_all_entities, get_investment_by_symbol
)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')


class CSVImporter:
    """Import investments and transactions from CSV/Excel files."""

    # Expected column mappings
    INVESTMENT_COLUMNS = {
        'name': ['name', 'investment_name', 'investment', 'holding', 'security'],
        'symbol': ['symbol', 'ticker', 'code'],
        'asset_class': ['asset_class', 'class', 'type', 'asset_type', 'category'],
        'entity': ['entity', 'account', 'owner', 'entity_name'],
        'currency': ['currency', 'ccy'],
        'exchange': ['exchange', 'market'],
        'quantity': ['quantity', 'qty', 'units', 'shares'],
        'cost_basis': ['cost_basis', 'cost', 'total_cost', 'book_value'],
        'cost_per_unit': ['cost_per_unit', 'avg_cost', 'average_cost', 'unit_cost'],
        'current_value': ['current_value', 'market_value', 'value'],
        'current_price': ['current_price', 'price', 'last_price'],
        'purchase_date': ['purchase_date', 'date', 'acquired_date', 'buy_date'],
        'notes': ['notes', 'description', 'comments']
    }

    TRANSACTION_COLUMNS = {
        'investment_name': ['investment_name', 'investment', 'name', 'holding', 'security'],
        'symbol': ['symbol', 'ticker'],
        'date': ['date', 'transaction_date', 'trade_date'],
        'type': ['type', 'transaction_type', 'action'],
        'quantity': ['quantity', 'qty', 'units', 'shares'],
        'price': ['price', 'unit_price', 'price_per_unit'],
        'amount': ['amount', 'total', 'total_amount', 'value'],
        'currency': ['currency', 'ccy'],
        'fees': ['fees', 'commission', 'charges'],
        'notes': ['notes', 'description', 'memo']
    }

    ASSET_CLASS_MAPPING = {
        'stock': 'Public Equities',
        'stocks': 'Public Equities',
        'equity': 'Public Equities',
        'equities': 'Public Equities',
        'public equity': 'Public Equities',
        'public equities': 'Public Equities',
        'private': 'Private Business',
        'private business': 'Private Business',
        'private equity': 'Private Business',
        'venture': 'Venture Fund',
        'venture fund': 'Venture Fund',
        'vc': 'Venture Fund',
        'venture entity': 'Venture Entity',
        'real estate': 'Real Estate',
        'property': 'Real Estate',
        'gold': 'Gold',
        'precious metals': 'Gold',
        'crypto': 'Crypto',
        'cryptocurrency': 'Crypto',
        'bitcoin': 'Crypto',
        'cash': 'Cash & Equivalents',
        'money market': 'Cash & Equivalents',
        'bond': 'Bonds',
        'bonds': 'Bonds',
        'fixed income': 'Bonds',
        'derivative': 'Derivatives/Options',
        'derivatives': 'Derivatives/Options',
        'option': 'Derivatives/Options',
        'options': 'Derivatives/Options',
    }

    TRANSACTION_TYPE_MAPPING = {
        'buy': 'Buy',
        'purchase': 'Buy',
        'acquired': 'Buy',
        'sell': 'Sell',
        'sold': 'Sell',
        'sale': 'Sell',
        'dividend': 'Dividend',
        'div': 'Dividend',
        'distribution': 'Distribution',
        'dist': 'Distribution',
        'capital call': 'Capital Call',
        'call': 'Capital Call',
        'capital return': 'Capital Return',
        'return of capital': 'Capital Return',
        'interest': 'Interest',
        'fee': 'Fee',
        'fees': 'Fee',
        'transfer in': 'Transfer In',
        'transfer out': 'Transfer Out',
    }

    def __init__(self):
        self.errors = []
        self.warnings = []

    def _find_column(self, df: pd.DataFrame, field: str, column_mappings: Dict) -> Optional[str]:
        """Find the actual column name in the dataframe for a given field."""
        possible_names = column_mappings.get(field, [field])
        df_columns_lower = {c.lower().strip(): c for c in df.columns}

        for name in possible_names:
            if name.lower() in df_columns_lower:
                return df_columns_lower[name.lower()]

        return None

    def _normalize_asset_class(self, value: str) -> str:
        """Normalize asset class value to standard format."""
        if not value:
            return 'Public Equities'
        return self.ASSET_CLASS_MAPPING.get(value.lower().strip(), value)

    def _normalize_transaction_type(self, value: str) -> str:
        """Normalize transaction type to standard format."""
        if not value:
            return 'Buy'
        return self.TRANSACTION_TYPE_MAPPING.get(value.lower().strip(), value)

    def _parse_date(self, value) -> Optional[date]:
        """Parse various date formats."""
        if pd.isna(value):
            return None

        if isinstance(value, (datetime, date)):
            return value if isinstance(value, date) else value.date()

        if isinstance(value, str):
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m-%d-%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue

        return None

    def _parse_number(self, value) -> float:
        """Parse various number formats."""
        if pd.isna(value):
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = value.replace('$', '').replace(',', '').replace('C', '').replace('US', '').strip()
            # Handle parentheses for negative numbers
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        return 0.0

    def preview_investments(self, file_path: str) -> Tuple[pd.DataFrame, List[str]]:
        """
        Preview investments from a CSV/Excel file.

        Returns:
            Tuple of (normalized dataframe, list of issues)
        """
        self.errors = []
        self.warnings = []

        # Read file
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        # Find columns
        column_map = {}
        for field in self.INVESTMENT_COLUMNS.keys():
            col = self._find_column(df, field, self.INVESTMENT_COLUMNS)
            if col:
                column_map[field] = col
            elif field in ['name']:
                self.errors.append(f"Required column '{field}' not found")

        if self.errors:
            return pd.DataFrame(), self.errors

        # Build normalized dataframe
        normalized = pd.DataFrame()

        for field, col in column_map.items():
            if field == 'asset_class':
                normalized[field] = df[col].apply(self._normalize_asset_class)
            elif field in ['purchase_date']:
                normalized[field] = df[col].apply(self._parse_date)
            elif field in ['quantity', 'cost_basis', 'cost_per_unit', 'current_value', 'current_price']:
                normalized[field] = df[col].apply(self._parse_number)
            else:
                normalized[field] = df[col]

        # Fill defaults
        if 'currency' not in normalized.columns:
            normalized['currency'] = 'CAD'
        if 'entity' not in normalized.columns:
            normalized['entity'] = 'HoldCo'
        if 'asset_class' not in normalized.columns:
            normalized['asset_class'] = 'Public Equities'

        return normalized, self.warnings

    def import_investments(self, file_path: str, session=None) -> Dict:
        """
        Import investments from CSV/Excel file.

        Returns:
            Import results with counts and errors
        """
        close_session = False
        if session is None:
            session = get_session()
            close_session = True

        df, issues = self.preview_investments(file_path)

        if self.errors:
            return {'success': False, 'errors': self.errors, 'imported': 0}

        # Get entities
        entities = {e.name: e.id for e in get_all_entities(session)}

        imported = 0
        skipped = 0

        try:
            for idx, row in df.iterrows():
                try:
                    # Get or create entity
                    entity_name = row.get('entity', 'HoldCo')
                    if entity_name not in entities:
                        self.warnings.append(f"Row {idx+1}: Unknown entity '{entity_name}', using HoldCo")
                        entity_name = 'HoldCo'

                    entity_id = entities.get(entity_name, entities.get('HoldCo'))

                    # Check for existing investment by symbol
                    symbol = row.get('symbol')
                    if symbol:
                        existing = get_investment_by_symbol(session, symbol)
                        if existing:
                            self.warnings.append(f"Row {idx+1}: Investment with symbol '{symbol}' already exists, skipping")
                            skipped += 1
                            continue

                    # Create investment
                    investment = Investment(
                        name=row['name'],
                        symbol=row.get('symbol'),
                        asset_class=row.get('asset_class', 'Public Equities'),
                        entity_id=entity_id,
                        currency=row.get('currency', 'CAD'),
                        exchange=row.get('exchange'),
                        quantity=row.get('quantity', 0),
                        cost_basis=row.get('cost_basis', 0),
                        cost_per_unit=row.get('cost_per_unit', 0),
                        current_value=row.get('current_value', row.get('cost_basis', 0)),
                        current_price=row.get('current_price', row.get('cost_per_unit', 0)),
                        purchase_date=row.get('purchase_date'),
                        notes=row.get('notes'),
                        data_source='import'
                    )

                    session.add(investment)
                    imported += 1

                except Exception as e:
                    self.errors.append(f"Row {idx+1}: {str(e)}")

            session.commit()

        except Exception as e:
            session.rollback()
            self.errors.append(f"Import failed: {str(e)}")
            return {'success': False, 'errors': self.errors, 'imported': 0}

        finally:
            if close_session:
                session.close()

        return {
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'warnings': self.warnings,
            'errors': self.errors
        }

    def sync_investments(self, file_path: str, session=None) -> Dict:
        """
        Sync investments from CSV/Excel file using upsert logic.
        Matches existing investments by symbol (or name+entity) and updates them
        instead of skipping duplicates. Creates new records for unmatched rows.

        Returns:
            Sync results with created/updated counts and errors
        """
        close_session = False
        if session is None:
            session = get_session()
            close_session = True

        df, issues = self.preview_investments(file_path)

        if self.errors:
            return {'success': False, 'errors': self.errors, 'created': 0, 'updated': 0}

        entities = {e.name: e.id for e in get_all_entities(session)}

        created = 0
        updated = 0

        try:
            for idx, row in df.iterrows():
                try:
                    entity_name = row.get('entity', 'HoldCo')
                    if entity_name not in entities:
                        self.warnings.append(f"Row {idx+1}: Unknown entity '{entity_name}', using HoldCo")
                        entity_name = 'HoldCo'

                    entity_id = entities.get(entity_name, entities.get('HoldCo'))

                    # Try to find existing investment by symbol first, then by name+entity
                    existing = None
                    symbol = row.get('symbol')
                    if symbol and pd.notna(symbol) and str(symbol).strip():
                        existing = get_investment_by_symbol(session, str(symbol).strip())

                    if existing is None:
                        name = row.get('name', '')
                        existing = session.query(Investment).filter(
                            Investment.name == name,
                            Investment.entity_id == entity_id
                        ).first()

                    if existing:
                        # Update existing investment
                        for field in ['quantity', 'cost_basis', 'cost_per_unit', 'current_value', 'current_price']:
                            val = row.get(field)
                            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                                setattr(existing, field, val)

                        if row.get('asset_class'):
                            existing.asset_class = row['asset_class']
                        if row.get('currency'):
                            existing.currency = row['currency']
                        if row.get('exchange') and pd.notna(row.get('exchange')):
                            existing.exchange = row['exchange']
                        if row.get('notes') and pd.notna(row.get('notes')):
                            existing.notes = row['notes']
                        if row.get('purchase_date') and pd.notna(row.get('purchase_date')):
                            existing.purchase_date = row['purchase_date']

                        existing.data_source = 'google_sheets'
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                    else:
                        # Create new investment
                        investment = Investment(
                            name=row['name'],
                            symbol=row.get('symbol') if pd.notna(row.get('symbol', None)) else None,
                            asset_class=row.get('asset_class', 'Public Equities'),
                            entity_id=entity_id,
                            currency=row.get('currency', 'CAD'),
                            exchange=row.get('exchange') if pd.notna(row.get('exchange', None)) else None,
                            quantity=row.get('quantity', 0),
                            cost_basis=row.get('cost_basis', 0),
                            cost_per_unit=row.get('cost_per_unit', 0),
                            current_value=row.get('current_value', row.get('cost_basis', 0)),
                            current_price=row.get('current_price', row.get('cost_per_unit', 0)),
                            purchase_date=row.get('purchase_date'),
                            notes=row.get('notes') if pd.notna(row.get('notes', None)) else None,
                            data_source='google_sheets'
                        )
                        session.add(investment)
                        created += 1

                except Exception as e:
                    self.errors.append(f"Row {idx+1}: {str(e)}")

            session.commit()

        except Exception as e:
            session.rollback()
            self.errors.append(f"Sync failed: {str(e)}")
            return {'success': False, 'errors': self.errors, 'created': 0, 'updated': 0}

        finally:
            if close_session:
                session.close()

        return {
            'success': True,
            'created': created,
            'updated': updated,
            'warnings': self.warnings,
            'errors': self.errors
        }

    def preview_transactions(self, file_path: str) -> Tuple[pd.DataFrame, List[str]]:
        """Preview transactions from a CSV/Excel file."""
        self.errors = []
        self.warnings = []

        # Read file
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        # Find columns
        column_map = {}
        for field in self.TRANSACTION_COLUMNS.keys():
            col = self._find_column(df, field, self.TRANSACTION_COLUMNS)
            if col:
                column_map[field] = col

        # Check required columns
        if 'date' not in column_map:
            self.errors.append("Required column 'date' not found")
        if 'investment_name' not in column_map and 'symbol' not in column_map:
            self.errors.append("Required column 'investment_name' or 'symbol' not found")

        if self.errors:
            return pd.DataFrame(), self.errors

        # Build normalized dataframe
        normalized = pd.DataFrame()

        for field, col in column_map.items():
            if field == 'type':
                normalized[field] = df[col].apply(self._normalize_transaction_type)
            elif field == 'date':
                normalized[field] = df[col].apply(self._parse_date)
            elif field in ['quantity', 'price', 'amount', 'fees']:
                normalized[field] = df[col].apply(self._parse_number)
            else:
                normalized[field] = df[col]

        # Fill defaults
        if 'currency' not in normalized.columns:
            normalized['currency'] = 'CAD'
        if 'type' not in normalized.columns:
            normalized['type'] = 'Buy'

        return normalized, self.warnings

    def import_transactions(self, file_path: str, session=None) -> Dict:
        """Import transactions from CSV/Excel file."""
        close_session = False
        if session is None:
            session = get_session()
            close_session = True

        df, issues = self.preview_transactions(file_path)

        if self.errors:
            return {'success': False, 'errors': self.errors, 'imported': 0}

        imported = 0

        try:
            for idx, row in df.iterrows():
                try:
                    # Find investment
                    investment = None
                    if row.get('symbol'):
                        investment = get_investment_by_symbol(session, row['symbol'])

                    if not investment and row.get('investment_name'):
                        investment = session.query(Investment).filter(
                            Investment.name.ilike(f"%{row['investment_name']}%")
                        ).first()

                    if not investment:
                        self.warnings.append(f"Row {idx+1}: Investment not found, skipping")
                        continue

                    # Calculate amount if not provided
                    amount = row.get('amount', 0)
                    if amount == 0 and row.get('quantity') and row.get('price'):
                        amount = row['quantity'] * row['price']

                    # Create transaction
                    transaction = Transaction(
                        investment_id=investment.id,
                        transaction_type=row.get('type', 'Buy'),
                        date=row['date'],
                        quantity=row.get('quantity', 0),
                        price_per_unit=row.get('price', 0),
                        total_amount=amount,
                        currency=row.get('currency', 'CAD'),
                        fees=row.get('fees', 0),
                        notes=row.get('notes')
                    )

                    session.add(transaction)
                    imported += 1

                except Exception as e:
                    self.errors.append(f"Row {idx+1}: {str(e)}")

            session.commit()

            # Update investment positions
            from .database import update_investment_position
            investments = session.query(Investment).all()
            for inv in investments:
                update_investment_position(session, inv.id)

        except Exception as e:
            session.rollback()
            self.errors.append(f"Import failed: {str(e)}")
            return {'success': False, 'errors': self.errors, 'imported': 0}

        finally:
            if close_session:
                session.close()

        return {
            'success': True,
            'imported': imported,
            'warnings': self.warnings,
            'errors': self.errors
        }


class GoogleSheetsImporter:
    """Import data from Google Sheets."""

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path
        self.client = None

    def connect(self) -> bool:
        """Connect to Google Sheets API."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            if not self.credentials_path:
                return False

            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly'
            ]

            credentials = Credentials.from_service_account_file(
                self.credentials_path, scopes=scopes
            )

            self.client = gspread.authorize(credentials)
            return True

        except Exception as e:
            print(f"Google Sheets connection error: {e}")
            return False

    def get_sheet_data(self, sheet_url: str, worksheet_name: str = None) -> Optional[pd.DataFrame]:
        """Get data from a Google Sheet."""
        if not self.client:
            if not self.connect():
                return None

        try:
            spreadsheet = self.client.open_by_url(sheet_url)

            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.sheet1

            data = worksheet.get_all_records()
            return pd.DataFrame(data)

        except Exception as e:
            print(f"Error reading sheet: {e}")
            return None

    def import_from_sheet(self, sheet_url: str, import_type: str = 'investments', worksheet_name: str = None, session=None) -> Dict:
        """
        Import investments or transactions from Google Sheet.

        Args:
            sheet_url: URL of the Google Sheet
            import_type: 'investments' or 'transactions'
            worksheet_name: Specific worksheet to use
        """
        df = self.get_sheet_data(sheet_url, worksheet_name)

        if df is None:
            return {'success': False, 'errors': ['Failed to read Google Sheet'], 'imported': 0}

        # Save to temp CSV and use CSV importer
        temp_path = '/tmp/gsheet_import.csv'
        df.to_csv(temp_path, index=False)

        importer = CSVImporter()

        if import_type == 'investments':
            return importer.import_investments(temp_path, session)
        else:
            return importer.import_transactions(temp_path, session)

    def sync_from_sheet(self, sheet_url: str = None, worksheet_name: str = None, session=None) -> Dict:
        """
        Sync investments from Google Sheet using upsert logic.
        Reads sheet URL and worksheet from config if not provided.
        Updates last_sync_time in config on success.

        Returns:
            Sync results with created/updated counts and errors
        """
        # Load config for defaults
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            config = {}

        gs_config = config.get('google_sheets', {})

        if not sheet_url:
            sheet_url = gs_config.get('sheet_url', '')
        if not worksheet_name:
            worksheet_name = gs_config.get('worksheet_name', '') or None

        if not sheet_url:
            return {'success': False, 'errors': ['No Google Sheet URL configured'], 'created': 0, 'updated': 0}

        # Use credentials from config if not set
        if not self.credentials_path:
            self.credentials_path = gs_config.get('credentials_path', '')
            if self.credentials_path and not os.path.isabs(self.credentials_path):
                self.credentials_path = os.path.join(os.path.dirname(CONFIG_PATH), self.credentials_path)

        if not self.credentials_path or not os.path.exists(self.credentials_path):
            return {'success': False, 'errors': ['Google credentials file not found'], 'created': 0, 'updated': 0}

        # Read sheet data
        df = self.get_sheet_data(sheet_url, worksheet_name)

        if df is None:
            return {'success': False, 'errors': ['Failed to read Google Sheet'], 'created': 0, 'updated': 0}

        # Save to temp CSV and delegate to sync_investments
        temp_path = '/tmp/gsheet_sync.csv'
        df.to_csv(temp_path, index=False)

        importer = CSVImporter()
        result = importer.sync_investments(temp_path, session)

        # Update last_sync_time in config on success
        if result.get('success'):
            config.setdefault('google_sheets', {})
            config['google_sheets']['last_sync_time'] = datetime.now().isoformat()
            try:
                with open(CONFIG_PATH, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
            except Exception:
                pass

        return result


def generate_import_template(template_type: str = 'investments') -> pd.DataFrame:
    """Generate a template CSV for importing data."""

    if template_type == 'investments':
        return pd.DataFrame({
            'name': ['Apple Inc.', 'Private Company X', 'Venture Fund ABC'],
            'symbol': ['AAPL', '', ''],
            'asset_class': ['Public Equities', 'Private Business', 'Venture Fund'],
            'entity': ['HoldCo', 'HoldCo', 'Personal'],
            'currency': ['USD', 'CAD', 'USD'],
            'exchange': ['NASDAQ', '', ''],
            'quantity': [100, 1, 1],
            'cost_basis': [15000, 50000, 100000],
            'cost_per_unit': [150, 50000, 100000],
            'current_value': [17500, 75000, 120000],
            'current_price': [175, 75000, 120000],
            'purchase_date': ['2023-01-15', '2022-06-01', '2021-03-20'],
            'notes': ['Tech holding', 'Local business investment', 'Series A fund']
        })

    else:  # transactions
        return pd.DataFrame({
            'investment_name': ['Apple Inc.', 'Apple Inc.', 'Private Company X'],
            'symbol': ['AAPL', 'AAPL', ''],
            'date': ['2023-01-15', '2023-07-01', '2022-06-01'],
            'type': ['Buy', 'Dividend', 'Capital Call'],
            'quantity': [100, 0, 0],
            'price': [150, 0, 0],
            'amount': [15000, 50, 50000],
            'currency': ['USD', 'USD', 'CAD'],
            'fees': [10, 0, 0],
            'notes': ['Initial purchase', 'Q2 dividend', 'Initial investment']
        })
