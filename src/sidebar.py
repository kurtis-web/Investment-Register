"""
Shared sidebar - Exchange rates and market indices.
Displayed on all pages except Settings.
"""

import streamlit as st
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import requests
except ImportError:
    requests = None


def get_stock_price(symbol):
    """Get current stock price from Yahoo Finance."""
    if not yf:
        return None
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return {
                'price': hist['Close'].iloc[-1],
                'change': hist['Close'].iloc[-1] - hist['Open'].iloc[-1],
                'change_pct': ((hist['Close'].iloc[-1] - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1] * 100)
            }
    except Exception:
        pass
    return None


def get_fx_rate(from_currency, to_currency):
    """Get FX rate from Bank of Canada or Yahoo Finance."""
    try:
        if to_currency == 'CAD' and requests:
            url = f"https://www.bankofcanada.ca/valet/observations/FX{from_currency}CAD/json?recent=1"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'observations' in data and len(data['observations']) > 0:
                    key = f"FX{from_currency}CAD"
                    if key in data['observations'][0]:
                        return float(data['observations'][0][key]['v'])

        if yf:
            ticker = yf.Ticker(f"{from_currency}{to_currency}=X")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
    except Exception:
        pass
    return None


@st.cache_data(ttl=900, show_spinner=False)
def _cached_sidebar_fx():
    """Get FX rates for sidebar, cached for 15 minutes."""
    usd_cad = get_fx_rate('USD', 'CAD')
    eur_cad = get_fx_rate('EUR', 'CAD')
    return {'usd_cad': usd_cad, 'eur_cad': eur_cad}


@st.cache_data(ttl=900, show_spinner=False)
def _cached_sidebar_indices():
    """Get market indices for sidebar, cached for 15 minutes."""
    indices = {
        'S&P 500': '^GSPC',
        'NASDAQ': '^IXIC',
        'Dow Jones': '^DJI',
        'TSX': '^GSPTSE',
        'Gold (USD)': 'GC=F',
        'Bitcoin (USD)': 'BTC-USD'
    }
    results = {}
    for name, symbol in indices.items():
        data = get_stock_price(symbol)
        if data:
            results[name] = data
    return {'data': results, 'timestamp': datetime.now().strftime('%H:%M')}


def render_sidebar():
    """Render shared sidebar with exchange rates and market indices."""
    with st.sidebar:
        st.markdown(
            "<p style='color: #666; font-size: 0.75rem; text-transform: uppercase; "
            "letter-spacing: 0.05em;'>Exchange Rates</p>",
            unsafe_allow_html=True
        )

        fx_data = _cached_sidebar_fx()

        if fx_data['usd_cad']:
            st.metric("USD/CAD", f"{fx_data['usd_cad']:.4f}")
        if fx_data['eur_cad']:
            st.metric("EUR/CAD", f"{fx_data['eur_cad']:.4f}")

        st.markdown("---")

        st.markdown(
            "<p style='color: #666; font-size: 0.75rem; text-transform: uppercase; "
            "letter-spacing: 0.05em;'>Major Indices</p>",
            unsafe_allow_html=True
        )

        indices_data = _cached_sidebar_indices()

        for name, data in indices_data['data'].items():
            st.metric(
                name,
                f"{data['price']:,.0f}",
                delta=f"{data['change_pct']:+.2f}%"
            )

        st.caption(f"Updated: {indices_data['timestamp']}")
