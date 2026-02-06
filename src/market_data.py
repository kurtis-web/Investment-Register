"""
Market data integration for the Investment Register.
Fetches prices from Yahoo Finance, Kraken, and FX providers.
"""

import yfinance as yf
import requests
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
import pandas as pd
from functools import lru_cache
import time


class MarketDataProvider:
    """Unified market data provider"""

    def __init__(self):
        self.cache_timeout = 900  # 15 minutes
        self._cache = {}
        self._cache_timestamps = {}

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[key]) < self.cache_timeout

    def _set_cache(self, key: str, value):
        """Set cache value"""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()

    def _get_cache(self, key: str):
        """Get cache value if valid"""
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None

    # =========================================================================
    # Yahoo Finance - Stocks and ETFs
    # =========================================================================

    def get_stock_price(self, symbol: str, exchange: str = None) -> Optional[Dict]:
        """
        Get current stock price from Yahoo Finance.

        For TSX stocks, append .TO (e.g., RY.TO for Royal Bank)
        For TSX Venture, append .V
        """
        cache_key = f"stock_{symbol}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # Adjust symbol for Canadian exchanges
            yahoo_symbol = self._get_yahoo_symbol(symbol, exchange)

            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            # Get current price
            price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')

            if price is None:
                # Try to get from history
                hist = ticker.history(period='1d')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]

            if price is None:
                return None

            result = {
                'symbol': symbol,
                'yahoo_symbol': yahoo_symbol,
                'price': float(price),
                'currency': info.get('currency', 'USD'),
                'name': info.get('longName') or info.get('shortName', symbol),
                'change': info.get('regularMarketChange', 0),
                'change_pct': info.get('regularMarketChangePercent', 0),
                'previous_close': info.get('previousClose', price),
                'open': info.get('regularMarketOpen', price),
                'high': info.get('regularMarketDayHigh', price),
                'low': info.get('regularMarketDayLow', price),
                'volume': info.get('regularMarketVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'timestamp': datetime.now()
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            print(f"Error fetching stock price for {symbol}: {e}")
            return None

    def _get_yahoo_symbol(self, symbol: str, exchange: str = None) -> str:
        """Convert symbol to Yahoo Finance format"""
        symbol = symbol.upper()

        # Already has exchange suffix
        if '.' in symbol:
            return symbol

        # Add exchange suffix based on exchange parameter
        if exchange:
            exchange = exchange.upper()
            if exchange == 'TSX':
                return f"{symbol}.TO"
            elif exchange == 'TSXV':
                return f"{symbol}.V"
            elif exchange in ['NYSE', 'NASDAQ', 'US']:
                return symbol

        return symbol

    def get_stock_history(self, symbol: str, exchange: str = None, period: str = '1y') -> Optional[pd.DataFrame]:
        """Get historical stock data"""
        try:
            yahoo_symbol = self._get_yahoo_symbol(symbol, exchange)
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period=period)
            return hist
        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")
            return None

    def get_multiple_stock_prices(self, symbols: List[Tuple[str, str]]) -> Dict[str, Dict]:
        """
        Get prices for multiple stocks efficiently.
        symbols: List of (symbol, exchange) tuples
        """
        results = {}

        # Convert symbols
        yahoo_symbols = []
        symbol_map = {}
        for symbol, exchange in symbols:
            yahoo_sym = self._get_yahoo_symbol(symbol, exchange)
            yahoo_symbols.append(yahoo_sym)
            symbol_map[yahoo_sym] = symbol

        try:
            # Batch download
            data = yf.download(yahoo_symbols, period='1d', progress=False)

            if not data.empty:
                for yahoo_sym in yahoo_symbols:
                    original_sym = symbol_map[yahoo_sym]
                    try:
                        if len(yahoo_symbols) == 1:
                            price = data['Close'].iloc[-1]
                        else:
                            price = data['Close'][yahoo_sym].iloc[-1]

                        results[original_sym] = {
                            'symbol': original_sym,
                            'price': float(price),
                            'timestamp': datetime.now()
                        }
                    except:
                        pass

        except Exception as e:
            print(f"Error in batch stock fetch: {e}")

        return results

    # =========================================================================
    # Crypto - Kraken and fallback
    # =========================================================================

    def get_crypto_price(self, symbol: str) -> Optional[Dict]:
        """Get crypto price from Kraken or CoinGecko fallback"""
        cache_key = f"crypto_{symbol}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Try Kraken first
        result = self._get_kraken_price(symbol)

        # Fallback to CoinGecko
        if result is None:
            result = self._get_coingecko_price(symbol)

        if result:
            self._set_cache(cache_key, result)

        return result

    def _get_kraken_price(self, symbol: str) -> Optional[Dict]:
        """Get price from Kraken public API"""
        try:
            # Kraken uses different pair formats
            pair_map = {
                'BTC': 'XXBTZUSD',
                'ETH': 'XETHZUSD',
                'XRP': 'XXRPZUSD',
                'LTC': 'XLTCZUSD',
                'DOT': 'DOTUSD',
                'ADA': 'ADAUSD',
                'SOL': 'SOLUSD',
                'DOGE': 'XDGUSD',
                'LINK': 'LINKUSD',
                'MATIC': 'MATICUSD',
                'AVAX': 'AVAXUSD',
                'UNI': 'UNIUSD',
            }

            # Get Kraken pair name
            symbol_upper = symbol.upper()
            pair = pair_map.get(symbol_upper, f"{symbol_upper}USD")

            url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('error') and len(data['error']) > 0:
                return None

            result_data = data.get('result', {})
            if not result_data:
                return None

            # Get the first (and usually only) pair result
            pair_data = list(result_data.values())[0]

            price = float(pair_data['c'][0])  # Current price
            open_price = float(pair_data['o'])
            high = float(pair_data['h'][1])  # 24h high
            low = float(pair_data['l'][1])  # 24h low
            volume = float(pair_data['v'][1])  # 24h volume

            return {
                'symbol': symbol_upper,
                'price': price,
                'currency': 'USD',
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'change': price - open_price,
                'change_pct': ((price - open_price) / open_price * 100) if open_price else 0,
                'source': 'kraken',
                'timestamp': datetime.now()
            }

        except Exception as e:
            print(f"Kraken error for {symbol}: {e}")
            return None

    def _get_coingecko_price(self, symbol: str) -> Optional[Dict]:
        """Get price from CoinGecko (fallback)"""
        try:
            # CoinGecko ID mapping
            id_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'XRP': 'ripple',
                'LTC': 'litecoin',
                'DOT': 'polkadot',
                'ADA': 'cardano',
                'SOL': 'solana',
                'DOGE': 'dogecoin',
                'LINK': 'chainlink',
                'MATIC': 'matic-network',
                'AVAX': 'avalanche-2',
                'UNI': 'uniswap',
            }

            coin_id = id_map.get(symbol.upper(), symbol.lower())

            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            response = requests.get(url, timeout=10)
            data = response.json()

            if coin_id not in data:
                return None

            price = data[coin_id]['usd']
            change_pct = data[coin_id].get('usd_24h_change', 0)

            return {
                'symbol': symbol.upper(),
                'price': price,
                'currency': 'USD',
                'change_pct': change_pct,
                'source': 'coingecko',
                'timestamp': datetime.now()
            }

        except Exception as e:
            print(f"CoinGecko error for {symbol}: {e}")
            return None

    # =========================================================================
    # Gold Price
    # =========================================================================

    def get_gold_price(self) -> Optional[Dict]:
        """Get gold spot price (per troy ounce in USD)"""
        cache_key = "gold_spot"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # Use Yahoo Finance GLD ETF as proxy, adjust for ETF ratio
            ticker = yf.Ticker("GC=F")  # Gold Futures
            info = ticker.info

            price = info.get('regularMarketPrice') or info.get('previousClose')

            if price is None:
                # Fallback to GLD ETF (roughly 1/10 of gold price)
                gld = yf.Ticker("GLD")
                gld_price = gld.info.get('regularMarketPrice', 0)
                price = gld_price * 10  # Approximate conversion

            result = {
                'symbol': 'GOLD',
                'price': float(price),
                'currency': 'USD',
                'unit': 'troy_ounce',
                'source': 'yahoo',
                'timestamp': datetime.now()
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            print(f"Error fetching gold price: {e}")
            return None

    # =========================================================================
    # FX Rates
    # =========================================================================

    def get_fx_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get current FX rate"""
        if from_currency == to_currency:
            return 1.0

        cache_key = f"fx_{from_currency}_{to_currency}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            # Yahoo Finance FX
            pair = f"{from_currency}{to_currency}=X"
            ticker = yf.Ticker(pair)
            hist = ticker.history(period='1d')

            if not hist.empty:
                rate = float(hist['Close'].iloc[-1])
                self._set_cache(cache_key, rate)
                return rate

            return None

        except Exception as e:
            print(f"Error fetching FX rate {from_currency}/{to_currency}: {e}")
            return None

    def get_usd_cad_rate(self) -> float:
        """Get USD to CAD exchange rate"""
        rate = self.get_fx_rate('USD', 'CAD')
        return rate if rate else 1.35  # Fallback rate

    def get_historical_fx_rates(self, from_currency: str, to_currency: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """Get historical FX rates"""
        try:
            pair = f"{from_currency}{to_currency}=X"
            ticker = yf.Ticker(pair)
            hist = ticker.history(period=period)
            return hist
        except Exception as e:
            print(f"Error fetching historical FX: {e}")
            return None

    # =========================================================================
    # Benchmarks
    # =========================================================================

    def get_benchmark_data(self, symbol: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """Get benchmark index data"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            return hist
        except Exception as e:
            print(f"Error fetching benchmark {symbol}: {e}")
            return None

    def get_benchmark_returns(self, symbol: str, periods: List[str] = None) -> Dict[str, float]:
        """
        Calculate benchmark returns for specified periods.
        periods: ['1m', '3m', '6m', '1y', 'ytd']
        """
        if periods is None:
            periods = ['1m', '3m', '1y', 'ytd']

        results = {}

        try:
            ticker = yf.Ticker(symbol)

            # Get enough history
            hist = ticker.history(period='2y')

            if hist.empty:
                return results

            current_price = hist['Close'].iloc[-1]

            for period in periods:
                try:
                    if period == '1m':
                        start_date = datetime.now() - timedelta(days=30)
                    elif period == '3m':
                        start_date = datetime.now() - timedelta(days=90)
                    elif period == '6m':
                        start_date = datetime.now() - timedelta(days=180)
                    elif period == '1y':
                        start_date = datetime.now() - timedelta(days=365)
                    elif period == 'ytd':
                        start_date = datetime(datetime.now().year, 1, 1)
                    else:
                        continue

                    # Find closest date in history
                    mask = hist.index >= pd.Timestamp(start_date).tz_localize(hist.index.tz)
                    if mask.any():
                        start_price = hist.loc[mask, 'Close'].iloc[0]
                        results[period] = ((current_price - start_price) / start_price) * 100
                except:
                    pass

        except Exception as e:
            print(f"Error calculating benchmark returns for {symbol}: {e}")

        return results


# Singleton instance
market_data = MarketDataProvider()


# Convenience functions
def get_stock_price(symbol: str, exchange: str = None) -> Optional[Dict]:
    return market_data.get_stock_price(symbol, exchange)


def get_crypto_price(symbol: str) -> Optional[Dict]:
    return market_data.get_crypto_price(symbol)


def get_gold_price() -> Optional[Dict]:
    return market_data.get_gold_price()


def get_fx_rate(from_currency: str, to_currency: str) -> Optional[float]:
    return market_data.get_fx_rate(from_currency, to_currency)


def get_usd_cad_rate() -> float:
    return market_data.get_usd_cad_rate()


def get_benchmark_data(symbol: str, period: str = '1y') -> Optional[pd.DataFrame]:
    return market_data.get_benchmark_data(symbol, period)


def get_benchmark_returns(symbol: str) -> Dict[str, float]:
    return market_data.get_benchmark_returns(symbol)
