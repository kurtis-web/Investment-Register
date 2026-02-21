"""
Family Office Wealth OS - Main Application
Comprehensive investment tracking and wealth management dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.models import (
    Entity, Account, Investment, Valuation, Commitment,
    RealEstateProperty, FXRateSnapshot, CashflowItem, ActivityLog,
    DB_PATH, Base
)
from src.styles import apply_dark_theme, COLORS
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import yfinance as yf
import requests

# Page configuration
st.set_page_config(
    page_title="Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply shared dark theme (same as all other pages)
apply_dark_theme()

# Database connection
@st.cache_resource
def get_engine():
    return create_engine(f'sqlite:///{DB_PATH}', echo=False)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def format_currency(value, currency='CAD'):
    """Format a number as currency."""
    if value is None:
        return "N/A"
    if currency == 'USD':
        return f"US${value:,.0f}"
    return f"${value:,.0f}"


def format_percentage(value):
    """Format a number as percentage."""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def get_freshness_badge(last_updated):
    """Get freshness status badge."""
    if last_updated is None:
        return "🔴 Unknown"

    if isinstance(last_updated, date) and not isinstance(last_updated, datetime):
        last_updated = datetime.combine(last_updated, datetime.min.time())

    days_old = (datetime.now() - last_updated).days

    if days_old <= 7:
        return "🟢 Fresh"
    elif days_old <= 30:
        return "🟡 Aging"
    elif days_old <= 120:
        return "🟠 Stale"
    else:
        return "🔴 Very Stale"


def get_portfolio_summary(session):
    """Get portfolio summary statistics."""
    investments = session.query(Investment).filter(Investment.is_active == True).all()

    total_cost = sum(inv.cost_basis or 0 for inv in investments)
    total_value = sum(inv.current_value or 0 for inv in investments)

    # By entity
    by_entity = {}
    entities = session.query(Entity).all()
    for entity in entities:
        entity_investments = [i for i in investments if i.entity_id == entity.id]
        value = sum(inv.current_value or 0 for inv in entity_investments)
        cost = sum(inv.cost_basis or 0 for inv in entity_investments)
        if value > 0:
            by_entity[entity.name] = {'value': value, 'cost': cost, 'count': len(entity_investments)}

    # By category
    by_category = {}
    for inv in investments:
        cat = inv.category or 'Other'
        if cat not in by_category:
            by_category[cat] = {'value': 0, 'cost': 0, 'count': 0}
        by_category[cat]['value'] += inv.current_value or 0
        by_category[cat]['cost'] += inv.cost_basis or 0
        by_category[cat]['count'] += 1

    # Commitments
    commitments = session.query(Commitment).all()
    total_commitment = sum(c.total_commitment or 0 for c in commitments)
    total_unfunded = sum(c.unfunded_commitment or 0 for c in commitments)

    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_gain': total_value - total_cost,
        'total_gain_pct': ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
        'investment_count': len(investments),
        'by_entity': by_entity,
        'by_category': by_category,
        'total_commitment': total_commitment,
        'total_unfunded': total_unfunded
    }


def render_dashboard():
    """Render the main dashboard."""
    session = get_session()

    try:
        summary = get_portfolio_summary(session)

        # Header
        st.markdown("""
        <h1 style="font-size: 2rem; margin-bottom: 0.5rem;">Wealth Dashboard</h1>
        <p style="color: #888; margin-bottom: 2rem;">Family Office Wealth OS</p>
        """, unsafe_allow_html=True)

        # Top metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Net Worth (CAD)",
                format_currency(summary['total_value']),
                delta=format_currency(summary['total_gain']),
                delta_color="normal" if summary['total_gain'] >= 0 else "inverse"
            )

        with col2:
            st.metric(
                "Total Cost Basis",
                format_currency(summary['total_cost'])
            )

        with col3:
            st.metric(
                "Unrealized Gain/Loss",
                format_percentage(summary['total_gain_pct']),
                delta=format_currency(summary['total_gain']),
                delta_color="normal" if summary['total_gain'] >= 0 else "inverse"
            )

        with col4:
            st.metric(
                "Investments",
                summary['investment_count']
            )

        # Second row - Commitments
        if summary['total_commitment'] > 0:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Commitments",
                    format_currency(summary['total_commitment'])
                )

            with col2:
                st.metric(
                    "Unfunded Commitments",
                    format_currency(summary['total_unfunded'])
                )

            with col3:
                called_pct = ((summary['total_commitment'] - summary['total_unfunded']) / summary['total_commitment'] * 100) if summary['total_commitment'] > 0 else 0
                st.metric(
                    "Capital Called",
                    f"{called_pct:.0f}%"
                )

        st.markdown("---")

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Allocation by Entity")
            if summary['by_entity']:
                df_entity = pd.DataFrame([
                    {'Entity': k, 'Value': v['value']}
                    for k, v in summary['by_entity'].items()
                ])
                fig = px.pie(
                    df_entity,
                    values='Value',
                    names='Entity',
                    hole=0.5,
                    color_discrete_sequence=COLORS['chart_colors']
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text_secondary']),
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.1),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Allocation by Category")
            if summary['by_category']:
                df_cat = pd.DataFrame([
                    {'Category': k, 'Value': v['value']}
                    for k, v in summary['by_category'].items()
                ])
                fig = px.pie(
                    df_cat,
                    values='Value',
                    names='Category',
                    hole=0.5,
                    color_discrete_sequence=COLORS['chart_colors']
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text_secondary']),
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.1),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Top Holdings
        st.subheader("Top Holdings")
        investments = session.query(Investment).filter(
            Investment.is_active == True,
            Investment.current_value > 0
        ).order_by(Investment.current_value.desc()).limit(15).all()

        if investments:
            holdings_data = []
            for inv in investments:
                holdings_data.append({
                    'Investment': inv.name[:50] + '...' if len(inv.name) > 50 else inv.name,
                    'Category': inv.category or 'Other',
                    'Cost Basis': inv.cost_basis or 0,
                    'Current Value': inv.current_value or 0,
                    'Gain/Loss': (inv.current_value or 0) - (inv.cost_basis or 0),
                    'Return %': (((inv.current_value or 0) - (inv.cost_basis or 0)) / (inv.cost_basis or 1) * 100) if inv.cost_basis else 0
                })

            df = pd.DataFrame(holdings_data)

            # Format for display
            st.dataframe(
                df.style.format({
                    'Cost Basis': '${:,.0f}',
                    'Current Value': '${:,.0f}',
                    'Gain/Loss': '${:+,.0f}',
                    'Return %': '{:+.1f}%'
                }),
                use_container_width=True,
                hide_index=True
            )

        # Fund Commitments Summary
        commitments = session.query(Commitment).join(Investment).filter(
            Commitment.unfunded_commitment > 0
        ).all()

        if commitments:
            st.markdown("---")
            st.subheader("Outstanding Fund Commitments")

            commit_data = []
            for c in commitments:
                commit_data.append({
                    'Fund': c.investment.name[:40] + '...' if len(c.investment.name) > 40 else c.investment.name,
                    'Total Commitment': c.total_commitment or 0,
                    'Called': (c.total_commitment or 0) - (c.unfunded_commitment or 0),
                    'Unfunded': c.unfunded_commitment or 0,
                    'Called %': ((c.total_commitment - c.unfunded_commitment) / c.total_commitment * 100) if c.total_commitment else 0
                })

            df_commit = pd.DataFrame(commit_data)
            st.dataframe(
                df_commit.style.format({
                    'Total Commitment': '${:,.0f}',
                    'Called': '${:,.0f}',
                    'Unfunded': '${:,.0f}',
                    'Called %': '{:.0f}%'
                }),
                use_container_width=True,
                hide_index=True
            )

    finally:
        session.close()


def render_holdings():
    """Render holdings page."""
    session = get_session()

    try:
        st.header("Holdings")

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            entities = session.query(Entity).all()
            entity_filter = st.selectbox(
                "Entity",
                ["All"] + [e.name for e in entities]
            )

        with col2:
            categories = session.query(Investment.category).distinct().all()
            category_filter = st.selectbox(
                "Category",
                ["All"] + [c[0] for c in categories if c[0]]
            )

        with col3:
            status_filter = st.selectbox(
                "Status",
                ["Active", "All", "Exited"]
            )

        # Query investments
        query = session.query(Investment)

        if entity_filter != "All":
            entity = session.query(Entity).filter(Entity.name == entity_filter).first()
            if entity:
                query = query.filter(Investment.entity_id == entity.id)

        if category_filter != "All":
            query = query.filter(Investment.category == category_filter)

        if status_filter == "Active":
            query = query.filter(Investment.is_active == True)
        elif status_filter == "Exited":
            query = query.filter(Investment.is_active == False)

        investments = query.order_by(Investment.current_value.desc()).all()

        # Summary
        total_cost = sum(inv.cost_basis or 0 for inv in investments)
        total_value = sum(inv.current_value or 0 for inv in investments)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Value", format_currency(total_value))
        with col2:
            st.metric("Total Cost", format_currency(total_cost))
        with col3:
            st.metric("Gain/Loss", format_currency(total_value - total_cost))

        st.markdown("---")

        # Holdings table
        holdings_data = []
        for inv in investments:
            entity = session.query(Entity).filter(Entity.id == inv.entity_id).first()
            holdings_data.append({
                'Name': inv.name,
                'Entity': entity.name if entity else 'Unknown',
                'Category': inv.category or 'Other',
                'Units': inv.units or 0,
                'Cost Basis': inv.cost_basis or 0,
                'Current Value': inv.current_value or 0,
                'Gain/Loss': (inv.current_value or 0) - (inv.cost_basis or 0),
                'Return %': (((inv.current_value or 0) - (inv.cost_basis or 0)) / (inv.cost_basis or 1) * 100) if inv.cost_basis else 0,
                'Updated': inv.updated_at.strftime('%Y-%m-%d') if inv.updated_at else 'Unknown'
            })

        if holdings_data:
            df = pd.DataFrame(holdings_data)
            st.dataframe(
                df.style.format({
                    'Units': '{:,.2f}',
                    'Cost Basis': '${:,.0f}',
                    'Current Value': '${:,.0f}',
                    'Gain/Loss': '${:+,.0f}',
                    'Return %': '{:+.1f}%'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No investments found matching the filters.")

    finally:
        session.close()


def render_performance():
    """Render performance page."""
    session = get_session()

    try:
        st.header("Performance")

        # Get all investments
        investments = session.query(Investment).filter(Investment.is_active == True).all()

        total_cost = sum(inv.cost_basis or 0 for inv in investments)
        total_value = sum(inv.current_value or 0 for inv in investments)
        total_gain = total_value - total_cost
        total_return_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Value", format_currency(total_value))
        with col2:
            st.metric("Total Cost", format_currency(total_cost))
        with col3:
            st.metric("Total Gain/Loss", format_currency(total_gain),
                     delta_color="normal" if total_gain >= 0 else "inverse")
        with col4:
            st.metric("Total Return", format_percentage(total_return_pct))

        st.markdown("---")

        # Performance by Category
        st.subheader("Performance by Category")

        categories = {}
        for inv in investments:
            cat = inv.category or 'Other'
            if cat not in categories:
                categories[cat] = {'cost': 0, 'value': 0, 'count': 0}
            categories[cat]['cost'] += inv.cost_basis or 0
            categories[cat]['value'] += inv.current_value or 0
            categories[cat]['count'] += 1

        cat_data = []
        for cat, data in categories.items():
            gain = data['value'] - data['cost']
            return_pct = (gain / data['cost'] * 100) if data['cost'] > 0 else 0
            cat_data.append({
                'Category': cat,
                'Count': data['count'],
                'Cost Basis': data['cost'],
                'Current Value': data['value'],
                'Gain/Loss': gain,
                'Return %': return_pct
            })

        df = pd.DataFrame(cat_data).sort_values('Current Value', ascending=False)
        st.dataframe(
            df.style.format({
                'Cost Basis': '${:,.0f}',
                'Current Value': '${:,.0f}',
                'Gain/Loss': '${:+,.0f}',
                'Return %': '{:+.1f}%'
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        # Top Gainers and Losers
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top Gainers")
            gainers = sorted(
                [inv for inv in investments if (inv.cost_basis or 0) > 0],
                key=lambda x: ((x.current_value or 0) - (x.cost_basis or 0)) / (x.cost_basis or 1),
                reverse=True
            )[:10]

            for inv in gainers:
                gain = (inv.current_value or 0) - (inv.cost_basis or 0)
                pct = (gain / inv.cost_basis * 100) if inv.cost_basis else 0
                if gain > 0:
                    st.write(f"**{inv.name[:30]}**: +{pct:.1f}% ({format_currency(gain)})")

        with col2:
            st.subheader("Top Losers")
            losers = sorted(
                [inv for inv in investments if (inv.cost_basis or 0) > 0],
                key=lambda x: ((x.current_value or 0) - (x.cost_basis or 0)) / (x.cost_basis or 1)
            )[:10]

            for inv in losers:
                gain = (inv.current_value or 0) - (inv.cost_basis or 0)
                pct = (gain / inv.cost_basis * 100) if inv.cost_basis else 0
                if gain < 0:
                    st.write(f"**{inv.name[:30]}**: {pct:.1f}% ({format_currency(gain)})")

    finally:
        session.close()


def render_public_equity():
    """Render public equity page with live prices."""
    session = get_session()

    try:
        st.header("Public Equity")

        # Get public equity investments
        public_equities = session.query(Investment).filter(
            Investment.category == "Public Equity",
            Investment.is_active == True
        ).all()

        if not public_equities:
            st.info("No public equity investments found.")

            # Option to add
            st.subheader("Add Public Equity")
            with st.form("add_public_equity"):
                name = st.text_input("Company Name")
                symbol = st.text_input("Ticker Symbol (e.g., AAPL, TINY.V)")

                entities = session.query(Entity).all()
                entity_id = st.selectbox(
                    "Entity",
                    [e.id for e in entities],
                    format_func=lambda x: next((e.name for e in entities if e.id == x), "")
                )

                col1, col2 = st.columns(2)
                with col1:
                    shares = st.number_input("Shares", min_value=0.0, step=1.0)
                with col2:
                    cost_basis = st.number_input("Total Cost Basis (CAD)", min_value=0.0, step=100.0)

                if st.form_submit_button("Add"):
                    if name and symbol:
                        new_inv = Investment(
                            entity_id=entity_id,
                            name=name,
                            symbol=symbol.upper(),
                            category="Public Equity",
                            units=shares,
                            cost_basis=cost_basis,
                            currency='CAD',
                            data_source='yahoo',
                            status='Active'
                        )
                        session.add(new_inv)
                        session.commit()
                        st.success(f"Added {name}")
                        st.rerun()
            return

        # Summary
        total_cost = sum(inv.cost_basis or 0 for inv in public_equities)
        total_value = sum(inv.current_value or 0 for inv in public_equities)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Value", format_currency(total_value))
        with col2:
            st.metric("Total Cost", format_currency(total_cost))
        with col3:
            st.metric("Gain/Loss", format_currency(total_value - total_cost))

        st.markdown("---")

        # Live prices
        st.subheader("Holdings with Live Prices")

        if st.button("Refresh Prices"):
            for inv in public_equities:
                if inv.symbol:
                    data = get_stock_price(inv.symbol)
                    if data and inv.units:
                        inv.current_price = data['price']
                        inv.current_value = data['price'] * inv.units
                        inv.last_price_update = datetime.now()
            session.commit()
            st.success("Prices updated!")
            st.rerun()

        equity_data = []
        for inv in public_equities:
            live_data = get_stock_price(inv.symbol) if inv.symbol else None

            current_price = live_data['price'] if live_data else (inv.current_price or 0)
            current_value = current_price * (inv.units or 0) if current_price else (inv.current_value or 0)
            change_pct = live_data['change_pct'] if live_data else 0

            equity_data.append({
                'Name': inv.name,
                'Symbol': inv.symbol or '',
                'Shares': inv.units or 0,
                'Price': current_price,
                'Day Change': change_pct,
                'Value': current_value,
                'Cost Basis': inv.cost_basis or 0,
                'Gain/Loss': current_value - (inv.cost_basis or 0),
                'Return %': ((current_value - (inv.cost_basis or 0)) / (inv.cost_basis or 1) * 100) if inv.cost_basis else 0
            })

        df = pd.DataFrame(equity_data)
        st.dataframe(
            df.style.format({
                'Shares': '{:,.0f}',
                'Price': '${:,.2f}',
                'Day Change': '{:+.2f}%',
                'Value': '${:,.0f}',
                'Cost Basis': '${:,.0f}',
                'Gain/Loss': '${:+,.0f}',
                'Return %': '{:+.1f}%'
            }),
            use_container_width=True,
            hide_index=True
        )

    finally:
        session.close()


def render_funds():
    """Render fund commitments page."""
    session = get_session()

    try:
        st.header("Fund Commitments")

        # Get all fund investments with commitments
        funds = session.query(Investment).filter(
            Investment.category == "Fund"
        ).all()

        # Summary
        commitments = session.query(Commitment).all()
        total_commitment = sum(c.total_commitment or 0 for c in commitments)
        total_unfunded = sum(c.unfunded_commitment or 0 for c in commitments)
        total_nav = sum(inv.current_value or 0 for inv in funds)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Commitments", format_currency(total_commitment))
        with col2:
            st.metric("Capital Called", format_currency(total_commitment - total_unfunded))
        with col3:
            st.metric("Unfunded", format_currency(total_unfunded))
        with col4:
            st.metric("Current NAV", format_currency(total_nav))

        st.markdown("---")

        # Funds table
        funds_data = []
        for inv in funds:
            commitment = session.query(Commitment).filter(Commitment.investment_id == inv.id).first()

            funds_data.append({
                'Fund': inv.name,
                'Commitment': commitment.total_commitment if commitment else 0,
                'Called': (commitment.total_commitment - commitment.unfunded_commitment) if commitment else 0,
                'Unfunded': commitment.unfunded_commitment if commitment else 0,
                'Current NAV': inv.current_value or 0,
                'TVPI': (inv.current_value / (commitment.total_commitment - commitment.unfunded_commitment)) if commitment and (commitment.total_commitment - commitment.unfunded_commitment) > 0 else 0,
                'Last Update': inv.updated_at.strftime('%Y-%m-%d') if inv.updated_at else 'Unknown'
            })

        if funds_data:
            df = pd.DataFrame(funds_data)
            st.dataframe(
                df.style.format({
                    'Commitment': '${:,.0f}',
                    'Called': '${:,.0f}',
                    'Unfunded': '${:,.0f}',
                    'Current NAV': '${:,.0f}',
                    'TVPI': '{:.2f}x'
                }),
                use_container_width=True,
                hide_index=True
            )

    finally:
        session.close()


def render_real_estate():
    """Render real estate page."""
    session = get_session()

    try:
        st.header("Real Estate")

        properties = session.query(RealEstateProperty).all()

        if not properties:
            st.info("No real estate properties found.")
            return

        # Summary
        total_fmv = sum(p.fair_market_value or 0 for p in properties)
        income_producing = [p for p in properties if p.is_income_producing]
        personal_use = [p for p in properties if not p.is_income_producing]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total FMV", format_currency(total_fmv))
        with col2:
            st.metric("Income Producing", len(income_producing))
        with col3:
            st.metric("Personal Use", len(personal_use))

        st.markdown("---")

        # Properties table
        props_data = []
        for p in properties:
            props_data.append({
                'Property': p.name,
                'Type': 'Income' if p.is_income_producing else 'Personal',
                'Held By': p.held_by or 'Unknown',
                'FMV': p.fair_market_value or 0,
                'Mortgage': p.mortgage_balance or 0,
                'Net Equity': (p.fair_market_value or 0) - (p.mortgage_balance or 0)
            })

        df = pd.DataFrame(props_data)
        st.dataframe(
            df.style.format({
                'FMV': '${:,.0f}',
                'Mortgage': '${:,.0f}',
                'Net Equity': '${:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )

    finally:
        session.close()


def render_liquidity():
    """Render liquidity/banking page."""
    session = get_session()

    try:
        st.header("Liquidity & Banking")

        # Get accounts
        accounts = session.query(Account).filter(Account.is_active == True).all()

        # Get cash investments
        cash_investments = session.query(Investment).filter(
            Investment.category == "Cash",
            Investment.is_active == True
        ).all()

        # Calculate totals
        total_cash = sum(inv.current_value or 0 for inv in cash_investments)

        # Get near-cash (T-bills, money market)
        near_cash = session.query(Investment).filter(
            Investment.is_active == True,
            Investment.name.ilike('%t-bill%') | Investment.name.ilike('%money market%') | Investment.name.ilike('%bdn%')
        ).all()
        total_near_cash = sum(inv.current_value or 0 for inv in near_cash)

        # Get unfunded commitments (liquidity needs)
        commitments = session.query(Commitment).all()
        total_unfunded = sum(c.unfunded_commitment or 0 for c in commitments)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Cash", format_currency(total_cash))
        with col2:
            st.metric("Near-Cash (T-Bills)", format_currency(total_near_cash))
        with col3:
            st.metric("Total Liquid", format_currency(total_cash + total_near_cash))
        with col4:
            st.metric("Unfunded Commitments", format_currency(total_unfunded))

        st.markdown("---")

        # Runway calculation
        st.subheader("Liquidity Runway")
        liquid_assets = total_cash + total_near_cash

        if total_unfunded > 0:
            runway_months = (liquid_assets / (total_unfunded / 24)) if total_unfunded > 0 else 999
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Months of Runway", f"{min(runway_months, 99):.0f}")
            with col2:
                coverage = (liquid_assets / total_unfunded * 100) if total_unfunded > 0 else 100
                st.metric("Commitment Coverage", f"{coverage:.0f}%")

        st.markdown("---")

        # Bank accounts
        st.subheader("Bank & Brokerage Accounts")
        if accounts:
            acct_data = []
            for acct in accounts:
                acct_data.append({
                    'Institution': acct.institution_name,
                    'Account': acct.account_name or 'Main',
                    'Type': acct.account_type or 'Unknown',
                    'Currency': acct.currency or 'CAD',
                    'Balance': acct.current_balance or 0,
                    'Last Updated': acct.last_refreshed_at.strftime('%Y-%m-%d') if acct.last_refreshed_at else 'Unknown'
                })

            df = pd.DataFrame(acct_data)
            st.dataframe(
                df.style.format({'Balance': '${:,.0f}'}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No bank accounts configured.")

        st.markdown("---")

        # Near-cash positions
        st.subheader("Near-Cash Positions")
        if near_cash:
            nc_data = []
            for inv in near_cash:
                nc_data.append({
                    'Name': inv.name,
                    'Value': inv.current_value or 0,
                    'Category': 'Near-Cash'
                })
            df = pd.DataFrame(nc_data)
            st.dataframe(
                df.style.format({'Value': '${:,.0f}'}),
                use_container_width=True,
                hide_index=True
            )

    finally:
        session.close()


def render_cashflow():
    """Render cashflow/runway page."""
    session = get_session()

    try:
        st.header("Cashflow & Runway")

        # Get commitments for expected outflows
        commitments = session.query(Commitment).join(Investment).filter(
            Commitment.unfunded_commitment > 0
        ).all()

        total_unfunded = sum(c.unfunded_commitment or 0 for c in commitments)

        # Get liquid assets
        liquid = session.query(Investment).filter(
            Investment.is_active == True,
            (Investment.category == "Cash") |
            Investment.name.ilike('%t-bill%') |
            Investment.name.ilike('%money market%')
        ).all()
        total_liquid = sum(inv.current_value or 0 for inv in liquid)

        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Available Liquidity", format_currency(total_liquid))
        with col2:
            st.metric("Expected Outflows (Commitments)", format_currency(total_unfunded))
        with col3:
            net = total_liquid - total_unfunded
            st.metric("Net Position", format_currency(net),
                     delta_color="normal" if net >= 0 else "inverse")

        st.markdown("---")

        # Commitment schedule
        st.subheader("Outstanding Commitments (Expected Capital Calls)")

        if commitments:
            commit_data = []
            for c in commitments:
                # Estimate timing (spread over next 2 years)
                commit_data.append({
                    'Fund': c.investment.name[:40] + '...' if len(c.investment.name) > 40 else c.investment.name,
                    'Unfunded': c.unfunded_commitment or 0,
                    'Est. Next 6mo': (c.unfunded_commitment or 0) * 0.25,
                    'Est. 6-12mo': (c.unfunded_commitment or 0) * 0.25,
                    'Est. 12-24mo': (c.unfunded_commitment or 0) * 0.50
                })

            df = pd.DataFrame(commit_data)
            st.dataframe(
                df.style.format({
                    'Unfunded': '${:,.0f}',
                    'Est. Next 6mo': '${:,.0f}',
                    'Est. 6-12mo': '${:,.0f}',
                    'Est. 12-24mo': '${:,.0f}'
                }),
                use_container_width=True,
                hide_index=True
            )

            # Timeline visualization
            st.subheader("Capital Call Timeline (Estimated)")
            timeline_data = pd.DataFrame({
                'Period': ['Next 6 months', '6-12 months', '12-24 months'],
                'Amount': [
                    sum(c.unfunded_commitment or 0 for c in commitments) * 0.25,
                    sum(c.unfunded_commitment or 0 for c in commitments) * 0.25,
                    sum(c.unfunded_commitment or 0 for c in commitments) * 0.50
                ]
            })

            fig = px.bar(
                timeline_data,
                x='Period',
                y='Amount',
                color_discrete_sequence=[COLORS['accent']]
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=COLORS['text_secondary']),
                xaxis=dict(gridcolor=COLORS['border']),
                yaxis=dict(gridcolor=COLORS['border']),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No outstanding commitments.")

    finally:
        session.close()


def get_live_fx_rate():
    """Get live USD/CAD rate from Bank of Canada."""
    try:
        # Bank of Canada Valet API
        url = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                rate = float(data['observations'][0]['FXUSDCAD']['v'])
                return rate
    except:
        pass
    return None


def get_stock_price(symbol):
    """Get current stock price from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return {
                'price': hist['Close'].iloc[-1],
                'change': hist['Close'].iloc[-1] - hist['Open'].iloc[-1],
                'change_pct': ((hist['Close'].iloc[-1] - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1] * 100)
            }
    except:
        pass
    return None


def render_settings():
    """Render settings and data management page."""
    session = get_session()

    try:
        st.header("Settings & Data Management")

        tab1, tab2, tab3 = st.tabs(["Update Values", "Add Investment", "Data Summary"])

        with tab1:
            st.subheader("Update Investment Values")

            investments = session.query(Investment).filter(
                Investment.is_active == True
            ).order_by(Investment.name).all()

            investment_names = [f"{inv.name[:50]}..." if len(inv.name) > 50 else inv.name for inv in investments]
            selected_idx = st.selectbox(
                "Select Investment",
                range(len(investments)),
                format_func=lambda x: investment_names[x] if x < len(investment_names) else ""
            )

            if investments and selected_idx is not None:
                inv = investments[selected_idx]

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Current Value:** {format_currency(inv.current_value)}")
                    st.write(f"**Cost Basis:** {format_currency(inv.cost_basis)}")
                with col2:
                    st.write(f"**Category:** {inv.category}")
                    st.write(f"**Last Updated:** {inv.updated_at.strftime('%Y-%m-%d') if inv.updated_at else 'Unknown'}")

                new_value = st.number_input(
                    "New Current Value (CAD)",
                    min_value=0.0,
                    value=float(inv.current_value or 0),
                    step=1000.0
                )

                if st.button("Update Value"):
                    inv.current_value = new_value
                    inv.updated_at = datetime.now()
                    session.commit()
                    st.success(f"Updated {inv.name} to {format_currency(new_value)}")
                    st.rerun()

        with tab2:
            st.subheader("Add New Investment")

            with st.form("add_investment"):
                name = st.text_input("Investment Name")

                entities = session.query(Entity).all()
                entity_id = st.selectbox(
                    "Entity",
                    [e.id for e in entities],
                    format_func=lambda x: next((e.name for e in entities if e.id == x), "")
                )

                category = st.selectbox(
                    "Category",
                    ["Private Direct", "Fund", "Public Equity", "Real Estate", "Cash", "Other"]
                )

                col1, col2 = st.columns(2)
                with col1:
                    cost_basis = st.number_input("Cost Basis (CAD)", min_value=0.0, step=1000.0)
                with col2:
                    current_value = st.number_input("Current Value (CAD)", min_value=0.0, step=1000.0)

                symbol = st.text_input("Symbol (for public equities)", value="")
                notes = st.text_area("Notes", value="")

                submitted = st.form_submit_button("Add Investment")

                if submitted and name:
                    new_inv = Investment(
                        entity_id=entity_id,
                        name=name,
                        category=category,
                        cost_basis=cost_basis,
                        current_value=current_value if current_value > 0 else cost_basis,
                        symbol=symbol if symbol else None,
                        notes=notes if notes else None,
                        currency='CAD',
                        units=1,
                        status='Active',
                        data_source='manual'
                    )
                    session.add(new_inv)
                    session.commit()
                    st.success(f"Added {name}")
                    st.rerun()

        with tab3:
            st.subheader("Data Summary")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Entities:**")
                for e in session.query(Entity).all():
                    count = session.query(Investment).filter(Investment.entity_id == e.id).count()
                    st.write(f"  - {e.name}: {count} investments")

            with col2:
                st.write("**Categories:**")
                categories = session.query(
                    Investment.category,
                    func.count(Investment.id),
                    func.sum(Investment.current_value)
                ).group_by(Investment.category).all()

                for cat, count, value in categories:
                    st.write(f"  - {cat}: {count} ({format_currency(value or 0)})")

            st.markdown("---")

            # Database info
            st.write(f"**Database Location:** `{DB_PATH}`")
            st.write(f"**Total Investments:** {session.query(Investment).count()}")
            st.write(f"**Active Investments:** {session.query(Investment).filter(Investment.is_active == True).count()}")

    finally:
        session.close()


def render_market_data():
    """Render market data page."""
    st.header("Market Data")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Exchange Rates")

        # Get live FX
        usd_cad = get_live_fx_rate()
        if usd_cad:
            st.metric("USD/CAD", f"{usd_cad:.4f}", help="Source: Bank of Canada")
        else:
            st.metric("USD/CAD", "N/A", help="Unable to fetch rate")

    with col2:
        st.subheader("Major Indices")

        indices = {
            'S&P 500': '^GSPC',
            'TSX': '^GSPTSE',
            'NASDAQ': '^IXIC',
            'Dow Jones': '^DJI'
        }

        for name, symbol in indices.items():
            data = get_stock_price(symbol)
            if data:
                st.metric(
                    name,
                    f"{data['price']:,.2f}",
                    delta=f"{data['change']:+.2f} ({data['change_pct']:+.2f}%)"
                )

    st.markdown("---")

    # Public equity holdings
    st.subheader("Public Equity Holdings")

    session = get_session()
    try:
        public_equities = session.query(Investment).filter(
            Investment.category == "Public Equity",
            Investment.is_active == True
        ).all()

        if public_equities:
            for inv in public_equities:
                if inv.symbol:
                    data = get_stock_price(inv.symbol)
                    if data:
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"**{inv.name}** ({inv.symbol})")
                        with col2:
                            st.write(f"${data['price']:.2f}")
                        with col3:
                            color = "green" if data['change'] >= 0 else "red"
                            st.markdown(f"<span style='color:{color}'>{data['change']:+.2f} ({data['change_pct']:+.2f}%)</span>", unsafe_allow_html=True)
        else:
            st.info("No public equities with symbols found.")

    finally:
        session.close()

    # Refresh button
    if st.button("Refresh Market Data"):
        st.rerun()


def get_fx_rate(from_currency, to_currency):
    """Get FX rate from Bank of Canada or Yahoo Finance."""
    try:
        if to_currency == 'CAD':
            # Try Bank of Canada first
            url = f"https://www.bankofcanada.ca/valet/observations/FX{from_currency}CAD/json?recent=1"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'observations' in data and len(data['observations']) > 0:
                    key = f"FX{from_currency}CAD"
                    if key in data['observations'][0]:
                        return float(data['observations'][0][key]['v'])

        # Fallback to Yahoo Finance
        ticker = yf.Ticker(f"{from_currency}{to_currency}=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
    except:
        pass
    return None


def main():
    """Main application entry point."""
    from src.sidebar import render_sidebar
    render_sidebar()
    render_dashboard()


if __name__ == "__main__":
    main()
