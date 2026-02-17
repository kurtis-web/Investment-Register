"""
Holdings Page - Detailed view of all investment positions with drill-down capability.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import (
    get_session, get_all_investments, get_all_entities,
    get_investment_by_id, add_investment, add_transaction, Entity
)
from src.portfolio import get_portfolio_overview, get_holdings_for_display, update_market_prices
from src.market_data import get_stock_price, get_crypto_price, get_usd_cad_rate
from src.calculations import format_currency, format_percentage
from src.styles import apply_dark_theme, COLORS, PLOTLY_LAYOUT, page_header, section_header
from src.importers import GoogleSheetsImporter

st.set_page_config(page_title="Holdings | Investment Register", page_icon="📈", layout="wide")

# Apply dark theme
apply_dark_theme()

page_header("Holdings", "Detailed view of all investment positions")

# --- Auto-sync from Google Sheets ---
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
try:
    with open(config_path, 'r') as f:
        _config = yaml.safe_load(f) or {}
except Exception:
    _config = {}

_gs_config = _config.get('google_sheets', {})

if _gs_config.get('auto_sync_on_load', False) and _gs_config.get('sheet_url'):
    _should_sync = True
    _last_sync = _gs_config.get('last_sync_time')
    if _last_sync:
        try:
            _last_sync_dt = datetime.fromisoformat(_last_sync)
            _minutes_since = (datetime.now() - _last_sync_dt).total_seconds() / 60
            if _minutes_since < 15:
                _should_sync = False
        except Exception:
            pass

    if _should_sync:
        _creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'google_credentials.json')
        if os.path.exists(_creds_path):
            _gs_importer = GoogleSheetsImporter(credentials_path=_creds_path)
            _sync_result = _gs_importer.sync_from_sheet()
            if _sync_result.get('success'):
                st.toast(
                    f"Auto-synced: {_sync_result.get('created', 0)} created, "
                    f"{_sync_result.get('updated', 0)} updated"
                )


# --- Auto-refresh market prices (cached for 15 min) ---
@st.cache_data(ttl=900, show_spinner=False)
def _cached_market_refresh():
    """Refresh market prices, cached for 15 minutes."""
    _session = get_session()
    try:
        result = update_market_prices(_session)
        return {
            'updated': result.get('updated', 0),
            'total': result.get('total', 0),
            'errors': result.get('errors', []),
            'timestamp': datetime.now().strftime('%H:%M')
        }
    finally:
        _session.close()

_refresh_result = _cached_market_refresh()

# Filters
session = get_session()

try:
    portfolio = get_portfolio_overview(session)
    entities = get_all_entities(session)
    entity_names = ["All"] + [e.name for e in entities]
    asset_classes = ["All"] + list(portfolio['by_asset_class'].keys())

    # Filter controls
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_entity = st.selectbox("Entity", entity_names)

    with col2:
        filter_asset_class = st.selectbox("Asset Class", asset_classes)

    with col3:
        sort_by = st.selectbox("Sort By", ["Value", "Name", "Gain ($)", "Gain (%)", "Weight"])
        sort_map = {"Value": "value", "Name": "name", "Gain ($)": "gain", "Gain (%)": "gain_pct", "Weight": "weight"}

    # Last refreshed indicator
    if _refresh_result:
        st.caption(
            f"Prices last refreshed at {_refresh_result['timestamp']} "
            f"({_refresh_result['updated']}/{_refresh_result['total']} updated)"
        )

    st.markdown("---")

    # Get filtered holdings
    holdings = get_holdings_for_display(
        session,
        sort_by=sort_map.get(sort_by, "value"),
        filter_entity=None if filter_entity == "All" else filter_entity,
        filter_asset_class=None if filter_asset_class == "All" else filter_asset_class
    )

    if not holdings:
        st.info("No holdings match your filters.")
    else:
        # Summary metrics
        total_value = sum(h['current_value'] for h in holdings)
        total_cost = sum(h['cost_basis'] for h in holdings)
        total_gain = total_value - total_cost
        total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Value", format_currency(total_value))
        with col2:
            st.metric("Total Cost", format_currency(total_cost))
        with col3:
            st.metric("Total Gain/Loss", format_currency(total_gain), delta=f"{total_gain_pct:+.1f}%")
        with col4:
            st.metric("Positions", len(holdings))

        st.markdown("---")

        # Holdings cards/expanders
        for holding in holdings:
            gain_color = "🟢" if holding['unrealized_gain'] >= 0 else "🔴"

            with st.expander(
                f"{gain_color} **{holding['name']}** | "
                f"{format_currency(holding['current_value'])} | "
                f"{holding['unrealized_gain_pct']:+.1f}%"
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("### Position Details")
                    st.markdown(f"**Asset Class:** {holding['asset_class']}")
                    st.markdown(f"**Entity:** {holding['entity']}")
                    if holding.get('symbol'):
                        st.markdown(f"**Symbol:** {holding['symbol']}")
                    st.markdown(f"**Currency:** {holding['currency']}")
                    st.markdown(f"**Quantity:** {holding['quantity']:,.4f}")

                with col2:
                    st.markdown("### Valuation")
                    st.markdown(f"**Current Price:** {format_currency(holding['current_price'], holding['currency'])}")
                    st.markdown(f"**Current Value:** {format_currency(holding['current_value'])}")
                    st.markdown(f"**Cost Basis:** {format_currency(holding['cost_basis'])}")
                    st.markdown(f"**Cost Per Unit:** {format_currency(holding['cost_basis'] / holding['quantity'] if holding['quantity'] > 0 else 0, holding['currency'])}")

                with col3:
                    st.markdown("### Performance")
                    gain_display = format_currency(holding['unrealized_gain'])
                    if holding['unrealized_gain'] >= 0:
                        st.success(f"**Gain:** +{gain_display} ({holding['unrealized_gain_pct']:+.1f}%)")
                    else:
                        st.error(f"**Loss:** {gain_display} ({holding['unrealized_gain_pct']:.1f}%)")

                    st.markdown(f"**Portfolio Weight:** {holding['weight']:.1f}%")
                    st.markdown(f"**Liquid:** {'Yes' if holding['is_liquid'] else 'No'}")

                    if holding.get('last_updated'):
                        st.caption(f"Last updated: {holding['last_updated']}")

                # Get real-time price if available
                if holding.get('symbol') and holding['asset_class'] in ['Public Equities', 'Crypto']:
                    st.markdown("---")
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("Refresh Price", key=f"refresh_{holding['id']}"):
                            with st.spinner("Fetching..."):
                                if holding['asset_class'] == 'Crypto':
                                    price_data = get_crypto_price(holding['symbol'])
                                else:
                                    price_data = get_stock_price(holding['symbol'])

                                if price_data:
                                    st.json(price_data)
                                else:
                                    st.warning("Could not fetch price")

        st.markdown("---")

        # Add new investment
        st.subheader("Add New Investment")

        with st.form("add_investment"):
            col1, col2 = st.columns(2)

            with col1:
                new_name = st.text_input("Investment Name*")
                new_symbol = st.text_input("Symbol (optional)")
                new_asset_class = st.selectbox("Asset Class*", [
                    "Public Equities", "Private Business", "Venture Fund",
                    "Venture Entity", "Real Estate", "Gold", "Crypto",
                    "Cash & Equivalents", "Bonds", "Derivatives/Options"
                ])
                new_entity = st.selectbox("Entity*", [e.name for e in entities])

            with col2:
                new_currency = st.selectbox("Currency", ["CAD", "USD"])
                new_quantity = st.number_input("Quantity", min_value=0.0, step=0.01)
                new_cost_basis = st.number_input("Total Cost Basis", min_value=0.0, step=100.0)
                new_exchange = st.text_input("Exchange (for stocks)", placeholder="e.g., TSX, NASDAQ")

            new_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add Investment")

            if submitted:
                if not new_name:
                    st.error("Investment name is required")
                else:
                    # Get entity ID
                    entity = session.query(Entity).filter(Entity.name == new_entity).first()

                    if entity:
                        investment = add_investment(
                            session,
                            name=new_name,
                            symbol=new_symbol if new_symbol else None,
                            asset_class=new_asset_class,
                            entity_id=entity.id,
                            currency=new_currency,
                            quantity=new_quantity,
                            cost_basis=new_cost_basis,
                            cost_per_unit=new_cost_basis / new_quantity if new_quantity > 0 else 0,
                            current_value=new_cost_basis,  # Start with cost
                            exchange=new_exchange if new_exchange else None,
                            notes=new_notes if new_notes else None,
                            data_source='manual'
                        )
                        st.success(f"Added: {new_name}")
                        st.rerun()
                    else:
                        st.error("Entity not found")

finally:
    session.close()
