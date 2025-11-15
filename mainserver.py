"""
Cryptocurrency Market Data MCP Server
A robust MCP server for retrieving real-time and historical cryptocurrency data
FIXED: Compatible with both sync and async CCXT operations
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import hashlib
import time
import inspect

import ccxt
from cachetools import TTLCache
from pydantic import BaseModel, Field, field_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

async def maybe_await(obj):
    """Helper to handle both sync and async returns from CCXT"""
    if inspect.iscoroutine(obj) or inspect.isawaitable(obj):
        return await obj
    return obj


# ============================================================================
# Data Models
# ============================================================================

class TimeFrame(str, Enum):
    """Supported timeframes for historical data"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MO1 = "1M"


class Exchange(str, Enum):
    """Supported cryptocurrency exchanges"""
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BITFINEX = "bitfinex"
    HUOBI = "huobi"


class MarketDataRequest(BaseModel):
    """Request model for market data"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTC/USDT)")
    exchange: Exchange = Field(default=Exchange.BINANCE)
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        if '/' not in v:
            raise ValueError("Symbol must be in format BASE/QUOTE (e.g., BTC/USDT)")
        return v.upper()


class HistoricalDataRequest(MarketDataRequest):
    """Request model for historical data"""
    timeframe: TimeFrame = Field(default=TimeFrame.H1)
    limit: int = Field(default=100, ge=1, le=1000)
    since: Optional[datetime] = None


class TickerData(BaseModel):
    """Ticker data model"""
    symbol: str
    exchange: str
    timestamp: datetime
    last: float
    bid: float
    ask: float
    high: float
    low: float
    volume: float
    change_24h: Optional[float] = None


class OHLCVData(BaseModel):
    """OHLCV (candlestick) data model"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OrderBookData(BaseModel):
    """Order book data model"""
    symbol: str
    exchange: str
    timestamp: datetime
    bids: List[List[float]]
    asks: List[List[float]]
    

# ============================================================================
# Cache Manager
# ============================================================================

class CacheManager:
    """Manages caching with TTL for different data types"""
    
    def __init__(self):
        self.ticker_cache = TTLCache(maxsize=1000, ttl=10)
        self.ohlcv_cache = TTLCache(maxsize=500, ttl=60)
        self.orderbook_cache = TTLCache(maxsize=500, ttl=5)
        
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_str = f"{prefix}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_ticker(self, exchange: str, symbol: str) -> Optional[TickerData]:
        """Get cached ticker data"""
        key = self._generate_key("ticker", exchange=exchange, symbol=symbol)
        return self.ticker_cache.get(key)
    
    def set_ticker(self, exchange: str, symbol: str, data: TickerData):
        """Cache ticker data"""
        key = self._generate_key("ticker", exchange=exchange, symbol=symbol)
        self.ticker_cache[key] = data
        
    def get_ohlcv(self, exchange: str, symbol: str, timeframe: str, 
                   limit: int) -> Optional[List[OHLCVData]]:
        """Get cached OHLCV data"""
        key = self._generate_key("ohlcv", exchange=exchange, symbol=symbol, 
                                 timeframe=timeframe, limit=limit)
        return self.ohlcv_cache.get(key)
    
    def set_ohlcv(self, exchange: str, symbol: str, timeframe: str, 
                  limit: int, data: List[OHLCVData]):
        """Cache OHLCV data"""
        key = self._generate_key("ohlcv", exchange=exchange, symbol=symbol, 
                                 timeframe=timeframe, limit=limit)
        self.ohlcv_cache[key] = data
        
    def clear_all(self):
        """Clear all caches"""
        self.ticker_cache.clear()
        self.ohlcv_cache.clear()
        self.orderbook_cache.clear()


# ============================================================================
# Exchange Manager
# ============================================================================

class ExchangeManager:
    """Manages connections to multiple exchanges"""
    
    def __init__(self):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._initialize_exchanges()
        
    def _initialize_exchanges(self):
        """Initialize exchange connections"""
        exchange_classes = {
            Exchange.BINANCE: ccxt.binance,
            Exchange.COINBASE: ccxt.coinbase,
            Exchange.KRAKEN: ccxt.kraken,
            Exchange.BITFINEX: ccxt.bitfinex,
            Exchange.HUOBI: ccxt.huobi,
        }
        
        for exchange_enum, exchange_class in exchange_classes.items():
            try:
                exchange = exchange_class({
                    'enableRateLimit': True,
                    'timeout': 30000,
                })
                self.exchanges[exchange_enum.value] = exchange
                logger.info(f"Initialized {exchange_enum.value} exchange")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_enum.value}: {e}")
    
    def get_exchange(self, exchange_name: str) -> ccxt.Exchange:
        """Get exchange instance by name"""
        exchange = self.exchanges.get(exchange_name.lower())
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not supported or not initialized")
        return exchange
    
    async def load_markets(self, exchange_name: str):
        """Load markets for an exchange (handles both sync and async)"""
        exchange = self.get_exchange(exchange_name)
        if not exchange.markets:
            # CCXT's load_markets can be sync or async depending on version
            result = exchange.load_markets()
            # If it returns a coroutine, await it
            await maybe_await(result)


# ============================================================================
# MCP Server Core
# ============================================================================

class CryptoMCPServer:
    """Main MCP Server for cryptocurrency market data"""
    
    def __init__(self):
        self.cache = CacheManager()
        self.exchange_manager = ExchangeManager()
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
        
    # ------------------------------------------------------------------------
    # Real-time Data Endpoints
    # ------------------------------------------------------------------------
    
    async def get_ticker(self, request: MarketDataRequest) -> TickerData:
        """
        Get real-time ticker data for a trading pair
        
        Args:
            request: Market data request with symbol and exchange
            
        Returns:
            TickerData with current market information
            
        Raises:
            ValueError: If symbol is invalid
            RuntimeError: If exchange API fails
        """
        self.request_count += 1
        
        # Check cache first
        cached = self.cache.get_ticker(request.exchange.value, request.symbol)
        if cached:
            logger.info(f"Cache hit for ticker {request.symbol} on {request.exchange.value}")
            return cached
        
        try:
            exchange = self.exchange_manager.get_exchange(request.exchange.value)
            await self.exchange_manager.load_markets(request.exchange.value)
            
            # Fetch ticker data (handle both sync and async)
            ticker = await maybe_await(exchange.fetch_ticker(request.symbol))
            
            # Convert to our model
            ticker_data = TickerData(
                symbol=request.symbol,
                exchange=request.exchange.value,
                timestamp=datetime.fromtimestamp(ticker['timestamp'] / 1000),
                last=ticker['last'],
                bid=ticker['bid'] or ticker['last'],
                ask=ticker['ask'] or ticker['last'],
                high=ticker['high'],
                low=ticker['low'],
                volume=ticker['baseVolume'],
                change_24h=ticker.get('percentage')
            )
            
            # Cache the result
            self.cache.set_ticker(request.exchange.value, request.symbol, ticker_data)
            
            logger.info(f"Fetched ticker for {request.symbol} on {request.exchange.value}")
            return ticker_data
            
        except ccxt.NetworkError as e:
            self.error_count += 1
            logger.error(f"Network error fetching ticker: {e}")
            raise RuntimeError(f"Network error: {str(e)}")
        except ccxt.ExchangeError as e:
            self.error_count += 1
            logger.error(f"Exchange error fetching ticker: {e}")
            raise RuntimeError(f"Exchange error: {str(e)}")
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error fetching ticker: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_orderbook(self, request: MarketDataRequest, 
                           limit: int = 20) -> OrderBookData:
        """
        Get current order book for a trading pair
        
        Args:
            request: Market data request
            limit: Number of orders to retrieve per side
            
        Returns:
            OrderBookData with bids and asks
        """
        self.request_count += 1
        
        try:
            exchange = self.exchange_manager.get_exchange(request.exchange.value)
            await self.exchange_manager.load_markets(request.exchange.value)
            
            orderbook = await maybe_await(exchange.fetch_order_book(request.symbol, limit))
            
            return OrderBookData(
                symbol=request.symbol,
                exchange=request.exchange.value,
                timestamp=datetime.fromtimestamp(orderbook['timestamp'] / 1000),
                bids=orderbook['bids'][:limit],
                asks=orderbook['asks'][:limit]
            )
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error fetching orderbook: {e}")
            raise RuntimeError(f"Failed to fetch orderbook: {str(e)}")
    
    # ------------------------------------------------------------------------
    # Historical Data Endpoints
    # ------------------------------------------------------------------------
    
    async def get_ohlcv(self, request: HistoricalDataRequest) -> List[OHLCVData]:
        """
        Get historical OHLCV (candlestick) data
        
        Args:
            request: Historical data request
            
        Returns:
            List of OHLCV data points
        """
        self.request_count += 1
        
        # Check cache
        cached = self.cache.get_ohlcv(
            request.exchange.value, 
            request.symbol, 
            request.timeframe.value,
            request.limit
        )
        if cached:
            logger.info(f"Cache hit for OHLCV {request.symbol}")
            return cached
        
        try:
            exchange = self.exchange_manager.get_exchange(request.exchange.value)
            await self.exchange_manager.load_markets(request.exchange.value)
            
            # Convert since to timestamp if provided
            since_ms = None
            if request.since:
                since_ms = int(request.since.timestamp() * 1000)
            
            # Fetch OHLCV data (handle both sync and async)
            ohlcv = await maybe_await(exchange.fetch_ohlcv(
                request.symbol,
                request.timeframe.value,
                since=since_ms,
                limit=request.limit
            ))
            
            # Convert to our model
            ohlcv_data = [
                OHLCVData(
                    timestamp=datetime.fromtimestamp(candle[0] / 1000),
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5]
                )
                for candle in ohlcv
            ]
            
            # Cache the result
            self.cache.set_ohlcv(
                request.exchange.value,
                request.symbol,
                request.timeframe.value,
                request.limit,
                ohlcv_data
            )
            
            logger.info(f"Fetched {len(ohlcv_data)} OHLCV candles for {request.symbol}")
            return ohlcv_data
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error fetching OHLCV: {e}")
            raise RuntimeError(f"Failed to fetch OHLCV data: {str(e)}")
    
    # ------------------------------------------------------------------------
    # Multi-Exchange Queries
    # ------------------------------------------------------------------------
    
    async def get_multi_exchange_ticker(self, symbol: str, 
                                       exchanges: Optional[List[Exchange]] = None) -> Dict[str, TickerData]:
        """
        Get ticker data from multiple exchanges simultaneously
        
        Args:
            symbol: Trading pair symbol
            exchanges: List of exchanges to query (defaults to all)
            
        Returns:
            Dictionary mapping exchange names to ticker data
        """
        if exchanges is None:
            exchanges = list(Exchange)
        
        # Create tasks for parallel execution
        tasks = []
        for exchange in exchanges:
            request = MarketDataRequest(symbol=symbol, exchange=exchange)
            tasks.append(self._safe_get_ticker(request))
        
        # Execute in parallel
        results = await asyncio.gather(*tasks)
        
        # Filter out None results (failed requests)
        return {
            exchange.value: result 
            for exchange, result in zip(exchanges, results)
            if result is not None
        }
    
    async def _safe_get_ticker(self, request: MarketDataRequest) -> Optional[TickerData]:
        """Safely get ticker data, returning None on error"""
        try:
            return await self.get_ticker(request)
        except Exception as e:
            logger.warning(f"Failed to get ticker from {request.exchange.value}: {e}")
            return None
    
    # ------------------------------------------------------------------------
    # Price Analytics
    # ------------------------------------------------------------------------
    
    async def get_price_statistics(self, request: HistoricalDataRequest) -> Dict[str, Any]:
        """
        Calculate price statistics from historical data
        
        Args:
            request: Historical data request
            
        Returns:
            Dictionary with price statistics
        """
        ohlcv_data = await self.get_ohlcv(request)
        
        if not ohlcv_data:
            raise ValueError("No data available for statistics")
        
        prices = [candle.close for candle in ohlcv_data]
        volumes = [candle.volume for candle in ohlcv_data]
        
        return {
            'symbol': request.symbol,
            'exchange': request.exchange.value,
            'timeframe': request.timeframe.value,
            'period': len(ohlcv_data),
            'current_price': prices[-1],
            'highest_price': max(prices),
            'lowest_price': min(prices),
            'average_price': sum(prices) / len(prices),
            'price_change': prices[-1] - prices[0],
            'price_change_percent': ((prices[-1] - prices[0]) / prices[0]) * 100,
            'total_volume': sum(volumes),
            'average_volume': sum(volumes) / len(volumes),
            'volatility': self._calculate_volatility(prices),
            'start_time': ohlcv_data[0].timestamp.isoformat(),
            'end_time': ohlcv_data[-1].timestamp.isoformat()
        }
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate simple volatility (standard deviation)"""
        if len(prices) < 2:
            return 0.0
        
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return variance ** 0.5
    
    # ------------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------------
    
    async def get_server_status(self) -> Dict[str, Any]:
        """Get server status and statistics"""
        uptime = time.time() - self.start_time
        
        return {
            'status': 'running',
            'uptime_seconds': uptime,
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'cache_stats': {
                'ticker_size': len(self.cache.ticker_cache),
                'ohlcv_size': len(self.cache.ohlcv_cache),
                'orderbook_size': len(self.cache.orderbook_cache)
            },
            'supported_exchanges': [e.value for e in Exchange],
            'supported_timeframes': [t.value for t in TimeFrame]
        }
    
    async def get_exchange_info(self, exchange_name: str) -> Dict[str, Any]:
        """Get information about a specific exchange"""
        try:
            exchange = self.exchange_manager.get_exchange(exchange_name)
            await self.exchange_manager.load_markets(exchange_name)
            
            return {
                'id': exchange.id,
                'name': exchange.name,
                'countries': exchange.countries,
                'has': {
                    'ticker': exchange.has.get('fetchTicker', False),
                    'ohlcv': exchange.has.get('fetchOHLCV', False),
                    'orderbook': exchange.has.get('fetchOrderBook', False),
                    'trades': exchange.has.get('fetchTrades', False),
                },
                'timeframes': list(exchange.timeframes.keys()) if hasattr(exchange, 'timeframes') else [],
                'markets_count': len(exchange.markets) if exchange.markets else 0,
                'rate_limit': exchange.rateLimit
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get exchange info: {str(e)}")
    
    async def search_symbols(self, query: str, exchange_name: str = "binance") -> List[str]:
        """
        Search for trading pair symbols on an exchange
        
        Args:
            query: Search query (partial symbol)
            exchange_name: Exchange to search on
            
        Returns:
            List of matching symbols
        """
        try:
            exchange = self.exchange_manager.get_exchange(exchange_name)
            await self.exchange_manager.load_markets(exchange_name)
            
            query_upper = query.upper()
            matching_symbols = [
                symbol for symbol in exchange.markets.keys()
                if query_upper in symbol
            ]
            
            return sorted(matching_symbols)[:50]
            
        except Exception as e:
            raise RuntimeError(f"Failed to search symbols: {str(e)}")
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear_all()
        logger.info("Cache cleared")


# ============================================================================
# Example Usage
# ============================================================================

async def main():
    """Example usage of the MCP server"""
    server = CryptoMCPServer()
    
    try:
        # Get real-time ticker
        print("\n=== Real-time Ticker ===")
        ticker_request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        ticker = await server.get_ticker(ticker_request)
        print(f"BTC/USDT Price: ${ticker.last:,.2f}")
        print(f"24h Change: {ticker.change_24h:.2f}%")
        
        # Get historical data
        print("\n=== Historical Data ===")
        hist_request = HistoricalDataRequest(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            timeframe=TimeFrame.H1,
            limit=24
        )
        ohlcv = await server.get_ohlcv(hist_request)
        print(f"Retrieved {len(ohlcv)} hourly candles")
        print(f"Latest close: ${ohlcv[-1].close:,.2f}")
        
        # Get price statistics
        print("\n=== Price Statistics ===")
        stats = await server.get_price_statistics(hist_request)
        print(f"Average Price: ${stats['average_price']:,.2f}")
        print(f"24h Change: {stats['price_change_percent']:.2f}%")
        print(f"Volatility: ${stats['volatility']:,.2f}")
        
        # Multi-exchange comparison
        print("\n=== Multi-Exchange Comparison ===")
        multi_tickers = await server.get_multi_exchange_ticker(
            "BTC/USDT",
            [Exchange.BINANCE, Exchange.KRAKEN]
        )
        for exchange_name, ticker_data in multi_tickers.items():
            print(f"{exchange_name}: ${ticker_data.last:,.2f}")
        
        # Server status
        print("\n=== Server Status ===")
        status = await server.get_server_status()
        print(f"Total Requests: {status['total_requests']}")
        print(f"Error Rate: {status['error_rate']:.2%}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())