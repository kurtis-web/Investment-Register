"""
Financial calculations for the Investment Register.
IRR, returns, gains/losses, performance attribution.
"""

import numpy as np
import numpy_financial as npf
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
from scipy import optimize


def calculate_simple_return(current_value: float, cost_basis: float) -> float:
    """
    Calculate simple return (total return percentage).

    Returns:
        Return as percentage (e.g., 15.5 for 15.5%)
    """
    if cost_basis == 0:
        return 0.0
    return ((current_value - cost_basis) / cost_basis) * 100


def calculate_holding_period_return(
    beginning_value: float,
    ending_value: float,
    cash_flows: float = 0
) -> float:
    """
    Calculate holding period return.

    Args:
        beginning_value: Starting value
        ending_value: Ending value
        cash_flows: Net cash flows during period (contributions positive, withdrawals negative)

    Returns:
        Return as percentage
    """
    if beginning_value == 0:
        return 0.0

    return ((ending_value - beginning_value - cash_flows) / beginning_value) * 100


def calculate_irr(cash_flows: List[Tuple[date, float]], current_value: float, current_date: date = None) -> Optional[float]:
    """
    Calculate Internal Rate of Return (IRR).

    Args:
        cash_flows: List of (date, amount) tuples. Negative = investment, Positive = return
        current_value: Current portfolio value
        current_date: Date for the current value (defaults to today)

    Returns:
        Annualized IRR as percentage, or None if calculation fails
    """
    if not cash_flows:
        return None

    if current_date is None:
        current_date = date.today()

    # Sort cash flows by date
    sorted_flows = sorted(cash_flows, key=lambda x: x[0])

    # Add current value as final cash flow (positive, as it's what you could receive)
    all_flows = sorted_flows + [(current_date, current_value)]

    # Convert to days from first date
    first_date = all_flows[0][0]
    dates_days = [(cf[0] - first_date).days for cf in all_flows]
    amounts = [cf[1] for cf in all_flows]

    # Use XIRR calculation
    try:
        irr = xirr(dates_days, amounts)
        return irr * 100 if irr is not None else None
    except:
        return None


def xirr(dates_days: List[int], amounts: List[float]) -> Optional[float]:
    """
    Calculate XIRR (Extended Internal Rate of Return).

    Args:
        dates_days: Days from start for each cash flow
        amounts: Cash flow amounts

    Returns:
        Annual rate of return as decimal
    """
    if len(dates_days) < 2 or len(amounts) < 2:
        return None

    # Check if all amounts have same sign (no return possible)
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    def npv(rate):
        """Calculate NPV for a given rate"""
        total = 0
        for i, amount in enumerate(amounts):
            days = dates_days[i]
            total += amount / ((1 + rate) ** (days / 365.0))
        return total

    try:
        # Try to find rate where NPV = 0
        result = optimize.brentq(npv, -0.9999, 10, maxiter=1000)
        return result
    except ValueError:
        # Try with different bounds
        try:
            result = optimize.newton(npv, 0.1, maxiter=1000)
            return result
        except:
            return None


def calculate_time_weighted_return(
    period_returns: List[float]
) -> float:
    """
    Calculate Time-Weighted Return (TWR).

    Args:
        period_returns: List of periodic returns as decimals (e.g., 0.05 for 5%)

    Returns:
        Cumulative TWR as percentage
    """
    if not period_returns:
        return 0.0

    cumulative = 1.0
    for r in period_returns:
        cumulative *= (1 + r)

    return (cumulative - 1) * 100


def annualize_return(total_return_pct: float, years: float) -> float:
    """
    Annualize a total return.

    Args:
        total_return_pct: Total return as percentage
        years: Number of years

    Returns:
        Annualized return as percentage
    """
    if years <= 0:
        return 0.0

    total_return_decimal = total_return_pct / 100
    annualized = ((1 + total_return_decimal) ** (1 / years)) - 1

    return annualized * 100


def calculate_unrealized_gain(current_value: float, cost_basis: float) -> Dict[str, float]:
    """
    Calculate unrealized gain/loss.

    Returns:
        Dict with 'amount' and 'percentage'
    """
    gain = current_value - cost_basis
    pct = (gain / cost_basis * 100) if cost_basis != 0 else 0

    return {
        'amount': gain,
        'percentage': pct,
        'is_gain': gain >= 0
    }


def calculate_realized_gain(
    sell_amount: float,
    quantity_sold: float,
    cost_per_unit: float
) -> Dict[str, float]:
    """
    Calculate realized gain/loss on a sale.

    Returns:
        Dict with realized gain information
    """
    cost_basis_sold = quantity_sold * cost_per_unit
    gain = sell_amount - cost_basis_sold

    return {
        'proceeds': sell_amount,
        'cost_basis': cost_basis_sold,
        'gain': gain,
        'percentage': (gain / cost_basis_sold * 100) if cost_basis_sold != 0 else 0,
        'is_gain': gain >= 0
    }


def calculate_portfolio_return(
    holdings: List[Dict],
    period_start_values: Dict[str, float],
    period_start_date: date,
    period_end_date: date
) -> Dict[str, float]:
    """
    Calculate portfolio return for a period.

    Args:
        holdings: List of holding dicts with 'id', 'current_value', 'transactions'
        period_start_values: Dict mapping holding id to value at period start
        period_start_date: Start of period
        period_end_date: End of period

    Returns:
        Dict with portfolio return metrics
    """
    total_start_value = sum(period_start_values.values())
    total_end_value = sum(h['current_value'] for h in holdings)

    # Calculate net cash flows during period
    net_flows = 0
    for h in holdings:
        for tx in h.get('transactions', []):
            tx_date = tx['date']
            if period_start_date <= tx_date <= period_end_date:
                if tx['type'] in ['Buy', 'Capital Call']:
                    net_flows += tx['amount']
                elif tx['type'] in ['Sell', 'Capital Return']:
                    net_flows -= tx['amount']

    # Simple return
    simple_return = calculate_simple_return(total_end_value, total_start_value + net_flows)

    # Holding period return
    hpr = calculate_holding_period_return(total_start_value, total_end_value, net_flows)

    return {
        'start_value': total_start_value,
        'end_value': total_end_value,
        'net_cash_flows': net_flows,
        'simple_return': simple_return,
        'holding_period_return': hpr
    }


def calculate_performance_attribution(
    holdings: List[Dict],
    benchmark_return: float
) -> Dict[str, any]:
    """
    Calculate performance attribution.

    Args:
        holdings: List of holdings with 'asset_class', 'weight', 'return'
        benchmark_return: Benchmark return for the period

    Returns:
        Attribution analysis
    """
    # Group by asset class
    asset_class_data = {}
    total_portfolio_return = 0

    for h in holdings:
        asset_class = h.get('asset_class', 'Other')
        weight = h.get('weight', 0)
        ret = h.get('return', 0)

        if asset_class not in asset_class_data:
            asset_class_data[asset_class] = {
                'weight': 0,
                'return': 0,
                'contribution': 0,
                'holdings': []
            }

        asset_class_data[asset_class]['weight'] += weight
        asset_class_data[asset_class]['holdings'].append(h)

    # Calculate weighted returns and contributions
    for asset_class, data in asset_class_data.items():
        if data['weight'] > 0:
            weighted_return = sum(
                h.get('weight', 0) * h.get('return', 0)
                for h in data['holdings']
            ) / data['weight']
            data['return'] = weighted_return
            data['contribution'] = data['weight'] * weighted_return / 100
            total_portfolio_return += data['contribution']

    # Calculate alpha (excess return vs benchmark)
    alpha = total_portfolio_return - benchmark_return

    return {
        'by_asset_class': asset_class_data,
        'total_return': total_portfolio_return,
        'benchmark_return': benchmark_return,
        'alpha': alpha
    }


def calculate_risk_metrics(returns: List[float]) -> Dict[str, float]:
    """
    Calculate risk metrics from a series of returns.

    Args:
        returns: List of periodic returns as percentages

    Returns:
        Risk metrics including volatility, Sharpe ratio, max drawdown
    """
    if not returns or len(returns) < 2:
        return {
            'volatility': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'avg_return': 0
        }

    returns_array = np.array(returns)

    # Volatility (standard deviation of returns)
    volatility = np.std(returns_array)

    # Average return
    avg_return = np.mean(returns_array)

    # Sharpe ratio (assuming risk-free rate of 4%)
    risk_free_rate = 4.0 / 12  # Monthly risk-free rate
    if volatility > 0:
        sharpe_ratio = (avg_return - risk_free_rate) / volatility
    else:
        sharpe_ratio = 0

    # Max drawdown
    cumulative = np.cumprod(1 + returns_array / 100)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max * 100
    max_drawdown = np.min(drawdowns)

    return {
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'avg_return': avg_return
    }


def calculate_concentration_risk(holdings: List[Dict], threshold_pct: float = 20) -> Dict:
    """
    Calculate concentration risk.

    Args:
        holdings: List of holdings with 'name', 'value', 'asset_class'
        threshold_pct: Threshold for flagging concentration (default 20%)

    Returns:
        Concentration analysis
    """
    total_value = sum(h.get('value', 0) for h in holdings)

    if total_value == 0:
        return {'concentrated_positions': [], 'hhi': 0}

    concentrated = []
    weights_squared = 0

    for h in holdings:
        value = h.get('value', 0)
        weight = (value / total_value) * 100

        weights_squared += (weight / 100) ** 2

        if weight >= threshold_pct:
            concentrated.append({
                'name': h.get('name', 'Unknown'),
                'value': value,
                'weight': weight,
                'asset_class': h.get('asset_class', 'Unknown')
            })

    # Herfindahl-Hirschman Index (HHI)
    hhi = weights_squared * 10000

    return {
        'concentrated_positions': concentrated,
        'hhi': hhi,
        'is_concentrated': hhi > 2500 or len(concentrated) > 0,
        'threshold_used': threshold_pct
    }


def calculate_liquidity_analysis(holdings: List[Dict]) -> Dict:
    """
    Analyze portfolio liquidity.

    Args:
        holdings: List of holdings with 'value', 'asset_class', 'is_liquid'

    Returns:
        Liquidity analysis
    """
    total_value = sum(h.get('value', 0) for h in holdings)

    if total_value == 0:
        return {'liquid_pct': 0, 'illiquid_pct': 0}

    liquid_value = sum(h.get('value', 0) for h in holdings if h.get('is_liquid', False))
    illiquid_value = total_value - liquid_value

    liquid_by_class = {}
    for h in holdings:
        asset_class = h.get('asset_class', 'Unknown')
        if asset_class not in liquid_by_class:
            liquid_by_class[asset_class] = {'liquid': 0, 'illiquid': 0}

        if h.get('is_liquid', False):
            liquid_by_class[asset_class]['liquid'] += h.get('value', 0)
        else:
            liquid_by_class[asset_class]['illiquid'] += h.get('value', 0)

    return {
        'liquid_value': liquid_value,
        'illiquid_value': illiquid_value,
        'liquid_pct': (liquid_value / total_value) * 100,
        'illiquid_pct': (illiquid_value / total_value) * 100,
        'by_asset_class': liquid_by_class
    }


def calculate_income_yield(
    annual_income: float,
    current_value: float
) -> float:
    """
    Calculate income yield.

    Args:
        annual_income: Annual income from investments
        current_value: Current portfolio value

    Returns:
        Yield as percentage
    """
    if current_value == 0:
        return 0.0
    return (annual_income / current_value) * 100


def calculate_cost_basis_adjustment(
    current_cost_basis: float,
    current_quantity: float,
    transaction_type: str,
    transaction_quantity: float,
    transaction_price: float
) -> Dict[str, float]:
    """
    Calculate adjusted cost basis after a transaction.

    Uses average cost method.

    Returns:
        New cost basis and cost per unit
    """
    if transaction_type in ['Buy', 'Capital Call']:
        new_quantity = current_quantity + transaction_quantity
        new_cost_basis = current_cost_basis + (transaction_quantity * transaction_price)

    elif transaction_type in ['Sell', 'Capital Return']:
        if current_quantity <= 0:
            return {'cost_basis': 0, 'cost_per_unit': 0, 'quantity': 0}

        avg_cost = current_cost_basis / current_quantity
        new_quantity = current_quantity - transaction_quantity
        new_cost_basis = new_quantity * avg_cost

    else:
        return {
            'cost_basis': current_cost_basis,
            'cost_per_unit': current_cost_basis / current_quantity if current_quantity > 0 else 0,
            'quantity': current_quantity
        }

    return {
        'cost_basis': new_cost_basis,
        'cost_per_unit': new_cost_basis / new_quantity if new_quantity > 0 else 0,
        'quantity': new_quantity
    }


def format_currency(amount: float, currency: str = 'CAD') -> str:
    """Format amount as currency string"""
    if currency == 'CAD':
        return f"C${amount:,.2f}"
    elif currency == 'USD':
        return f"US${amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage string"""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"
