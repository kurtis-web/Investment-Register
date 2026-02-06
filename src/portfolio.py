"""
Portfolio analytics and management for the Investment Register.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

from .database import (
    get_session, get_all_investments, get_all_entities,
    get_investments_by_entity, get_investments_by_asset_class,
    get_latest_fx_rate, Investment, Transaction, Entity
)
from .market_data import (
    get_stock_price, get_crypto_price, get_gold_price,
    get_usd_cad_rate, get_fx_rate
)
from .calculations import (
    calculate_simple_return, calculate_irr, calculate_unrealized_gain,
    calculate_concentration_risk, calculate_liquidity_analysis,
    format_currency, format_percentage
)


# Asset class to liquidity mapping
LIQUID_ASSET_CLASSES = ['Public Equities', 'Crypto', 'Gold', 'Cash & Equivalents', 'Bonds']


def update_market_prices(session) -> Dict[str, any]:
    """
    Update current prices for all investments from market data.

    Returns:
        Summary of updates
    """
    investments = get_all_investments(session, active_only=True)
    updated = 0
    errors = []
    usd_cad = get_usd_cad_rate()

    for inv in investments:
        try:
            price_data = None

            if inv.asset_class == 'Public Equities' and inv.symbol:
                price_data = get_stock_price(inv.symbol, inv.exchange)

            elif inv.asset_class == 'Crypto' and inv.symbol:
                price_data = get_crypto_price(inv.symbol)

            elif inv.asset_class == 'Gold':
                price_data = get_gold_price()

            if price_data and price_data.get('price'):
                price = price_data['price']
                price_currency = price_data.get('currency', 'USD')

                # Convert to investment currency if needed
                if price_currency != inv.currency:
                    if price_currency == 'USD' and inv.currency == 'CAD':
                        price = price * usd_cad
                    elif price_currency == 'CAD' and inv.currency == 'USD':
                        price = price / usd_cad

                inv.current_price = price
                inv.current_value = price * inv.quantity
                inv.last_price_update = datetime.now()
                updated += 1

            elif inv.asset_class in ['Private Business', 'Venture Fund', 'Venture Entity', 'Real Estate']:
                # Use last NAV or cost basis for illiquid investments
                if inv.last_nav:
                    inv.current_value = inv.last_nav
                    inv.current_price = inv.last_nav / inv.quantity if inv.quantity > 0 else inv.last_nav
                else:
                    inv.current_value = inv.cost_basis
                    inv.current_price = inv.cost_per_unit

        except Exception as e:
            errors.append(f"{inv.name}: {str(e)}")

    session.commit()

    return {
        'updated': updated,
        'total': len(investments),
        'errors': errors,
        'usd_cad_rate': usd_cad
    }


def get_portfolio_overview(session) -> Dict:
    """
    Get complete portfolio overview.

    Returns:
        Comprehensive portfolio data
    """
    investments = get_all_investments(session, active_only=True)
    entities = get_all_entities(session)
    usd_cad = get_usd_cad_rate()

    # Calculate totals
    total_value_cad = 0
    total_cost_basis_cad = 0
    by_entity = {}
    by_asset_class = {}
    holdings_list = []

    for inv in investments:
        # Convert to CAD
        fx_rate = usd_cad if inv.currency == 'USD' else 1.0
        value_cad = inv.current_value * fx_rate
        cost_cad = inv.cost_basis * fx_rate

        total_value_cad += value_cad
        total_cost_basis_cad += cost_cad

        # By entity
        entity_name = inv.entity.name
        if entity_name not in by_entity:
            by_entity[entity_name] = {'value': 0, 'cost': 0, 'investments': []}
        by_entity[entity_name]['value'] += value_cad
        by_entity[entity_name]['cost'] += cost_cad
        by_entity[entity_name]['investments'].append(inv.id)

        # By asset class
        if inv.asset_class not in by_asset_class:
            by_asset_class[inv.asset_class] = {'value': 0, 'cost': 0, 'investments': []}
        by_asset_class[inv.asset_class]['value'] += value_cad
        by_asset_class[inv.asset_class]['cost'] += cost_cad
        by_asset_class[inv.asset_class]['investments'].append(inv.id)

        # Add to holdings list
        gain = calculate_unrealized_gain(value_cad, cost_cad)
        holdings_list.append({
            'id': inv.id,
            'name': inv.name,
            'symbol': inv.symbol,
            'asset_class': inv.asset_class,
            'entity': entity_name,
            'quantity': inv.quantity,
            'cost_basis': cost_cad,
            'current_value': value_cad,
            'current_price': inv.current_price,
            'currency': inv.currency,
            'unrealized_gain': gain['amount'],
            'unrealized_gain_pct': gain['percentage'],
            'weight': 0,  # Will be calculated below
            'is_liquid': inv.asset_class in LIQUID_ASSET_CLASSES,
            'last_updated': inv.last_price_update
        })

    # Calculate weights
    for h in holdings_list:
        if total_value_cad > 0:
            h['weight'] = (h['current_value'] / total_value_cad) * 100

    # Calculate entity and asset class weights
    for entity_name, data in by_entity.items():
        data['weight'] = (data['value'] / total_value_cad * 100) if total_value_cad > 0 else 0
        data['gain'] = data['value'] - data['cost']
        data['gain_pct'] = (data['gain'] / data['cost'] * 100) if data['cost'] > 0 else 0

    for asset_class, data in by_asset_class.items():
        data['weight'] = (data['value'] / total_value_cad * 100) if total_value_cad > 0 else 0
        data['gain'] = data['value'] - data['cost']
        data['gain_pct'] = (data['gain'] / data['cost'] * 100) if data['cost'] > 0 else 0

    # Risk analysis
    concentration = calculate_concentration_risk(holdings_list)
    liquidity = calculate_liquidity_analysis(holdings_list)

    # Overall gain
    total_gain = total_value_cad - total_cost_basis_cad
    total_gain_pct = (total_gain / total_cost_basis_cad * 100) if total_cost_basis_cad > 0 else 0

    return {
        'summary': {
            'total_value_cad': total_value_cad,
            'total_cost_basis_cad': total_cost_basis_cad,
            'total_gain': total_gain,
            'total_gain_pct': total_gain_pct,
            'investment_count': len(investments),
            'usd_cad_rate': usd_cad
        },
        'by_entity': by_entity,
        'by_asset_class': by_asset_class,
        'holdings': holdings_list,
        'risk': {
            'concentration': concentration,
            'liquidity': liquidity
        }
    }


def get_allocation_chart_data(portfolio_data: Dict, group_by: str = 'asset_class') -> List[Dict]:
    """
    Prepare data for allocation pie chart.

    Args:
        portfolio_data: Output from get_portfolio_overview
        group_by: 'asset_class' or 'entity'
    """
    if group_by == 'asset_class':
        source = portfolio_data['by_asset_class']
    else:
        source = portfolio_data['by_entity']

    chart_data = []
    for name, data in source.items():
        chart_data.append({
            'name': name,
            'value': data['value'],
            'weight': data['weight']
        })

    # Sort by value descending
    chart_data.sort(key=lambda x: x['value'], reverse=True)

    return chart_data


def get_recent_activity(session, limit: int = 10) -> List[Dict]:
    """
    Get recent transactions across all investments.
    """
    transactions = session.query(Transaction).order_by(
        Transaction.date.desc()
    ).limit(limit).all()

    activity = []
    for tx in transactions:
        activity.append({
            'date': tx.date,
            'investment': tx.investment.name,
            'type': tx.transaction_type,
            'amount': tx.total_amount,
            'currency': tx.currency,
            'notes': tx.notes
        })

    return activity


def get_performance_by_period(session, period: str = '1m') -> Dict:
    """
    Calculate portfolio performance for a specific period.

    Args:
        period: '1m' (month), '3m' (quarter), '1y' (year), 'ytd'
    """
    today = date.today()

    if period == '1m':
        start_date = today - timedelta(days=30)
    elif period == '3m':
        start_date = today - timedelta(days=90)
    elif period == '1y':
        start_date = today - timedelta(days=365)
    elif period == 'ytd':
        start_date = date(today.year, 1, 1)
    else:
        start_date = today - timedelta(days=30)

    # For a real implementation, we'd use portfolio snapshots
    # For now, return placeholder that will be populated as data accumulates
    portfolio = get_portfolio_overview(session)

    return {
        'period': period,
        'start_date': start_date,
        'end_date': today,
        'current_value': portfolio['summary']['total_value_cad'],
        'total_gain': portfolio['summary']['total_gain'],
        'total_gain_pct': portfolio['summary']['total_gain_pct']
    }


def calculate_portfolio_irr(session) -> Optional[float]:
    """
    Calculate overall portfolio IRR from all transactions.
    """
    investments = get_all_investments(session, active_only=True)
    usd_cad = get_usd_cad_rate()

    all_cash_flows = []
    total_current_value = 0

    for inv in investments:
        fx_rate = usd_cad if inv.currency == 'USD' else 1.0

        # Get all transactions for this investment
        for tx in inv.transactions:
            tx_fx = usd_cad if tx.currency == 'USD' else 1.0
            amount_cad = tx.total_amount * tx_fx

            # Investments are negative cash flows, returns are positive
            if tx.transaction_type in ['Buy', 'Capital Call']:
                all_cash_flows.append((tx.date, -amount_cad))
            elif tx.transaction_type in ['Sell', 'Capital Return', 'Dividend', 'Distribution']:
                all_cash_flows.append((tx.date, amount_cad))

        # Add current value
        total_current_value += inv.current_value * fx_rate

    if not all_cash_flows:
        return None

    return calculate_irr(all_cash_flows, total_current_value)


def get_holdings_for_display(session, sort_by: str = 'value', filter_entity: str = None, filter_asset_class: str = None) -> List[Dict]:
    """
    Get holdings formatted for display with optional filtering and sorting.
    """
    portfolio = get_portfolio_overview(session)
    holdings = portfolio['holdings']

    # Apply filters
    if filter_entity:
        holdings = [h for h in holdings if h['entity'] == filter_entity]

    if filter_asset_class:
        holdings = [h for h in holdings if h['asset_class'] == filter_asset_class]

    # Sort
    reverse = True
    if sort_by == 'name':
        holdings.sort(key=lambda x: x['name'])
        reverse = False
    elif sort_by == 'value':
        holdings.sort(key=lambda x: x['current_value'], reverse=True)
    elif sort_by == 'gain':
        holdings.sort(key=lambda x: x['unrealized_gain'], reverse=True)
    elif sort_by == 'gain_pct':
        holdings.sort(key=lambda x: x['unrealized_gain_pct'], reverse=True)
    elif sort_by == 'weight':
        holdings.sort(key=lambda x: x['weight'], reverse=True)

    return holdings


def get_target_vs_actual_allocation(session, target_allocation: Dict[str, float]) -> Dict:
    """
    Compare actual allocation vs target allocation.

    Args:
        target_allocation: Dict mapping asset class to target percentage (as decimal)
    """
    portfolio = get_portfolio_overview(session)
    total_value = portfolio['summary']['total_value_cad']

    comparison = {}

    for asset_class, target_pct in target_allocation.items():
        actual_data = portfolio['by_asset_class'].get(asset_class, {'value': 0, 'weight': 0})
        actual_pct = actual_data['weight']
        target_pct_display = target_pct * 100

        diff = actual_pct - target_pct_display
        diff_value = (diff / 100) * total_value

        comparison[asset_class] = {
            'target_pct': target_pct_display,
            'actual_pct': actual_pct,
            'difference_pct': diff,
            'difference_value': diff_value,
            'action': 'reduce' if diff > 0 else ('add' if diff < 0 else 'on_target')
        }

    return {
        'comparison': comparison,
        'total_value': total_value
    }


def generate_rebalancing_suggestions(session, target_allocation: Dict[str, float], threshold_pct: float = 5.0) -> List[Dict]:
    """
    Generate rebalancing suggestions based on target allocation.

    Args:
        target_allocation: Target allocation by asset class
        threshold_pct: Only suggest rebalancing if deviation exceeds this threshold
    """
    comparison = get_target_vs_actual_allocation(session, target_allocation)
    suggestions = []

    for asset_class, data in comparison['comparison'].items():
        if abs(data['difference_pct']) >= threshold_pct:
            action = data['action']
            amount = abs(data['difference_value'])

            suggestions.append({
                'asset_class': asset_class,
                'action': action,
                'amount': amount,
                'current_pct': data['actual_pct'],
                'target_pct': data['target_pct'],
                'difference_pct': data['difference_pct'],
                'priority': 'high' if abs(data['difference_pct']) >= threshold_pct * 2 else 'medium'
            })

    # Sort by priority and amount
    suggestions.sort(key=lambda x: (x['priority'] == 'high', abs(x['difference_pct'])), reverse=True)

    return suggestions
