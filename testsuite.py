"""
Fixed Comprehensive Test Suite for Cryptocurrency MCP Server
Compatible with pytest-asyncio and Pydantic V2
"""

import pytest
import pytest_asyncio  # Important: separate import
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

# Import from main module
from mainserver import (
    CryptoMCPServer,
    MarketDataRequest,
    HistoricalDataRequest,
    TickerData,
    OHLCVData,
    OrderBookData,
    Exchange,
    TimeFrame,
    CacheManager,
    ExchangeManager
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cache_manager():
    """Fixture for CacheManager"""
    return CacheManager()


@pytest.fixture
def mock_exchange():
    """Fixture for mocked exchange"""
    exchange = Mock()
    exchange.id = "binance"
    exchange.name = "Binance"
    exchange.markets = {
        "BTC/USDT": {"id": "BTCUSDT", "symbol": "BTC/USDT"},
        "ETH/USDT": {"id": "ETHUSDT", "symbol": "ETH/USDT"}
    }
    exchange.has = {
        'fetchTicker': True,
        'fetchOHLCV': True,
        'fetchOrderBook': True
    }
    exchange.timeframes = {'1h': '1h', '1d': '1d'}
    exchange.rateLimit = 1000
    return exchange


@pytest_asyncio.fixture  # Changed from @pytest.fixture
async def mcp_server():
    """Fixture for MCP server - Now properly async"""
    server = CryptoMCPServer()
    yield server
    # Cleanup
    server.clear_cache()


@pytest.fixture
def sample_ticker_data():
    """Fixture for sample ticker data"""
    return {
        'symbol': 'BTC/USDT',
        'timestamp': int(datetime.now().timestamp() * 1000),
        'last': 50000.0,
        'bid': 49999.0,
        'ask': 50001.0,
        'high': 51000.0,
        'low': 49000.0,
        'baseVolume': 1000.0,
        'percentage': 2.5
    }


@pytest.fixture
def sample_ohlcv_data():
    """Fixture for sample OHLCV data"""
    base_time = datetime.now().timestamp() * 1000
    return [
        [base_time - 3600000, 49000, 50000, 48500, 49500, 100],  # 1h ago
        [base_time - 7200000, 48000, 49500, 47500, 49000, 120],  # 2h ago
        [base_time - 10800000, 47500, 48500, 47000, 48000, 110], # 3h ago
    ]


# ============================================================================
# Data Model Tests
# ============================================================================

class TestDataModels:
    """Test data models and validation"""
    
    def test_market_data_request_valid(self):
        """Test valid market data request"""
        request = MarketDataRequest(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE
        )
        assert request.symbol == "BTC/USDT"
        assert request.exchange == Exchange.BINANCE
    
    def test_market_data_request_symbol_normalization(self):
        """Test symbol is normalized to uppercase"""
        request = MarketDataRequest(symbol="btc/usdt")
        assert request.symbol == "BTC/USDT"
    
    def test_market_data_request_invalid_symbol(self):
        """Test invalid symbol format raises error"""
        with pytest.raises(ValueError, match="Symbol must be in format BASE/QUOTE"):
            MarketDataRequest(symbol="BTCUSDT")
    
    def test_historical_data_request_defaults(self):
        """Test historical data request with defaults"""
        request = HistoricalDataRequest(symbol="BTC/USDT")
        assert request.timeframe == TimeFrame.H1
        assert request.limit == 100
        assert request.since is None
    
    def test_historical_data_request_limit_validation(self):
        """Test limit validation"""
        with pytest.raises(ValueError):
            HistoricalDataRequest(symbol="BTC/USDT", limit=0)
        
        with pytest.raises(ValueError):
            HistoricalDataRequest(symbol="BTC/USDT", limit=1001)
    
    def test_ticker_data_model(self):
        """Test ticker data model"""
        ticker = TickerData(
            symbol="BTC/USDT",
            exchange="binance",
            timestamp=datetime.now(),
            last=50000.0,
            bid=49999.0,
            ask=50001.0,
            high=51000.0,
            low=49000.0,
            volume=1000.0,
            change_24h=2.5
        )
        assert ticker.last == 50000.0
        assert ticker.symbol == "BTC/USDT"
    
    def test_ohlcv_data_model(self):
        """Test OHLCV data model"""
        ohlcv = OHLCVData(
            timestamp=datetime.now(),
            open=49000.0,
            high=50000.0,
            low=48500.0,
            close=49500.0,
            volume=100.0
        )
        assert ohlcv.close == 49500.0
        assert ohlcv.high >= ohlcv.low


# ============================================================================
# Cache Manager Tests
# ============================================================================

class TestCacheManager:
    """Test cache manager functionality"""
    
    def test_cache_initialization(self, cache_manager):
        """Test cache manager initializes correctly"""
        assert len(cache_manager.ticker_cache) == 0
        assert len(cache_manager.ohlcv_cache) == 0
        assert len(cache_manager.orderbook_cache) == 0
    
    def test_ticker_cache_set_get(self, cache_manager):
        """Test setting and getting ticker from cache"""
        ticker = TickerData(
            symbol="BTC/USDT",
            exchange="binance",
            timestamp=datetime.now(),
            last=50000.0,
            bid=49999.0,
            ask=50001.0,
            high=51000.0,
            low=49000.0,
            volume=1000.0
        )
        
        cache_manager.set_ticker("binance", "BTC/USDT", ticker)
        cached = cache_manager.get_ticker("binance", "BTC/USDT")
        
        assert cached is not None
        assert cached.last == 50000.0
        assert cached.symbol == "BTC/USDT"
    
    def test_cache_miss(self, cache_manager):
        """Test cache miss returns None"""
        cached = cache_manager.get_ticker("binance", "ETH/USDT")
        assert cached is None
    
    def test_ohlcv_cache(self, cache_manager):
        """Test OHLCV caching"""
        ohlcv_data = [
            OHLCVData(
                timestamp=datetime.now(),
                open=49000.0,
                high=50000.0,
                low=48500.0,
                close=49500.0,
                volume=100.0
            )
        ]
        
        cache_manager.set_ohlcv("binance", "BTC/USDT", "1h", 100, ohlcv_data)
        cached = cache_manager.get_ohlcv("binance", "BTC/USDT", "1h", 100)
        
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].close == 49500.0
    
    def test_cache_clear_all(self, cache_manager):
        """Test clearing all caches"""
        ticker = TickerData(
            symbol="BTC/USDT",
            exchange="binance",
            timestamp=datetime.now(),
            last=50000.0,
            bid=49999.0,
            ask=50001.0,
            high=51000.0,
            low=49000.0,
            volume=1000.0
        )
        
        cache_manager.set_ticker("binance", "BTC/USDT", ticker)
        assert len(cache_manager.ticker_cache) > 0
        
        cache_manager.clear_all()
        assert len(cache_manager.ticker_cache) == 0
        assert len(cache_manager.ohlcv_cache) == 0
    
    def test_cache_key_generation(self, cache_manager):
        """Test cache key generation is consistent"""
        key1 = cache_manager._generate_key("ticker", exchange="binance", symbol="BTC/USDT")
        key2 = cache_manager._generate_key("ticker", symbol="BTC/USDT", exchange="binance")
        key3 = cache_manager._generate_key("ticker", exchange="kraken", symbol="BTC/USDT")
        
        assert key1 == key2  # Same params in different order
        assert key1 != key3  # Different exchange


# ============================================================================
# Exchange Manager Tests
# ============================================================================

class TestExchangeManager:
    """Test exchange manager functionality"""
    
    def test_exchange_manager_initialization(self):
        """Test exchange manager initializes"""
        manager = ExchangeManager()
        assert len(manager.exchanges) > 0
    
    def test_get_exchange_valid(self):
        """Test getting a valid exchange"""
        manager = ExchangeManager()
        exchange = manager.get_exchange("binance")
        assert exchange is not None
    
    def test_get_exchange_invalid(self):
        """Test getting invalid exchange raises error"""
        manager = ExchangeManager()
        with pytest.raises(ValueError, match="not supported"):
            manager.get_exchange("invalid_exchange")
    
    @pytest.mark.asyncio
    async def test_load_markets(self, mock_exchange):
        """Test loading markets for an exchange"""
        manager = ExchangeManager()
        manager.exchanges["binance"] = mock_exchange
        
        # Create async mock for load_markets
        mock_exchange.load_markets = AsyncMock()
        mock_exchange.markets = None  # Simulate unloaded markets
        
        await manager.load_markets("binance")
        
        # Verify load_markets was called
        mock_exchange.load_markets.assert_called_once()


# ============================================================================
# MCP Server Core Tests
# ============================================================================

class TestCryptoMCPServer:
    """Test main MCP server functionality"""
    
    @pytest.mark.asyncio
    async def test_get_ticker_success(self, mcp_server, mock_exchange, sample_ticker_data):
        """Test successful ticker retrieval"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
        mock_exchange.load_markets = AsyncMock()
        
        request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        ticker = await mcp_server.get_ticker(request)
        
        assert ticker.last == 50000.0
        assert ticker.symbol == "BTC/USDT"
        assert ticker.exchange == "binance"
        assert mcp_server.request_count > 0
    
    @pytest.mark.asyncio
    async def test_get_ticker_cache_hit(self, mcp_server, mock_exchange, sample_ticker_data):
        """Test ticker cache hit"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
        mock_exchange.load_markets = AsyncMock()
        
        request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        
        # First call - cache miss
        ticker1 = await mcp_server.get_ticker(request)
        call_count_1 = mock_exchange.fetch_ticker.call_count
        
        # Second call - should hit cache
        ticker2 = await mcp_server.get_ticker(request)
        call_count_2 = mock_exchange.fetch_ticker.call_count
        
        assert ticker1.last == ticker2.last
        assert call_count_2 == call_count_1  # No additional API call
    
    @pytest.mark.asyncio
    async def test_get_ticker_network_error(self, mcp_server, mock_exchange):
        """Test ticker retrieval with network error"""
        import ccxt
        
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ticker = AsyncMock(side_effect=ccxt.NetworkError("Connection failed"))
        mock_exchange.load_markets = AsyncMock()
        
        request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        
        with pytest.raises(RuntimeError, match="Network error"):
            await mcp_server.get_ticker(request)
        
        assert mcp_server.error_count > 0
    
    @pytest.mark.asyncio
    async def test_get_ohlcv_success(self, mcp_server, mock_exchange, sample_ohlcv_data):
        """Test successful OHLCV retrieval"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=sample_ohlcv_data)
        mock_exchange.load_markets = AsyncMock()
        
        request = HistoricalDataRequest(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            timeframe=TimeFrame.H1,
            limit=3
        )
        ohlcv = await mcp_server.get_ohlcv(request)
        
        assert len(ohlcv) == 3
        assert isinstance(ohlcv[0], OHLCVData)
        assert ohlcv[0].close == 49500.0
    
    @pytest.mark.asyncio
    async def test_get_ohlcv_with_since(self, mcp_server, mock_exchange, sample_ohlcv_data):
        """Test OHLCV retrieval with since parameter"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=sample_ohlcv_data)
        mock_exchange.load_markets = AsyncMock()
        
        since_date = datetime.now() - timedelta(days=1)
        request = HistoricalDataRequest(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            timeframe=TimeFrame.H1,
            limit=3,
            since=since_date
        )
        ohlcv = await mcp_server.get_ohlcv(request)
        
        assert len(ohlcv) == 3
        # Verify since was converted to timestamp
        call_args = mock_exchange.fetch_ohlcv.call_args
        assert call_args[1]['since'] is not None
    
    @pytest.mark.asyncio
    async def test_get_orderbook_success(self, mcp_server, mock_exchange):
        """Test successful orderbook retrieval"""
        orderbook_data = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'bids': [[50000, 1.0], [49999, 2.0]],
            'asks': [[50001, 1.5], [50002, 2.5]]
        }
        
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_order_book = AsyncMock(return_value=orderbook_data)
        mock_exchange.load_markets = AsyncMock()
        
        request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        orderbook = await mcp_server.get_orderbook(request, limit=2)
        
        assert len(orderbook.bids) == 2
        assert len(orderbook.asks) == 2
        assert orderbook.bids[0][0] == 50000
    
    @pytest.mark.asyncio
    async def test_get_multi_exchange_ticker(self, mcp_server, mock_exchange, sample_ticker_data):
        """Test multi-exchange ticker retrieval"""
        # Mock multiple exchanges
        for exchange_name in ["binance", "kraken"]:
            mock = Mock()
            mock.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
            mock.load_markets = AsyncMock()
            mock.markets = {"BTC/USDT": {}}
            mcp_server.exchange_manager.exchanges[exchange_name] = mock
        
        result = await mcp_server.get_multi_exchange_ticker(
            "BTC/USDT",
            [Exchange.BINANCE, Exchange.KRAKEN]
        )
        
        assert len(result) == 2
        assert "binance" in result
        assert "kraken" in result
    
    @pytest.mark.asyncio
    async def test_get_price_statistics(self, mcp_server, mock_exchange, sample_ohlcv_data):
        """Test price statistics calculation"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=sample_ohlcv_data)
        mock_exchange.load_markets = AsyncMock()
        
        request = HistoricalDataRequest(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            timeframe=TimeFrame.H1,
            limit=3
        )
        stats = await mcp_server.get_price_statistics(request)
        
        assert 'current_price' in stats
        assert 'highest_price' in stats
        assert 'lowest_price' in stats
        assert 'average_price' in stats
        assert 'volatility' in stats
        assert 'price_change_percent' in stats
        assert stats['period'] == 3
    
    @pytest.mark.asyncio
    async def test_calculate_volatility(self, mcp_server):
        """Test volatility calculation"""
        prices = [100, 105, 103, 107, 104]
        volatility = mcp_server._calculate_volatility(prices)
        
        assert volatility > 0
        assert isinstance(volatility, float)
    
    @pytest.mark.asyncio
    async def test_get_server_status(self, mcp_server):
        """Test server status retrieval"""
        status = await mcp_server.get_server_status()
        
        assert 'status' in status
        assert status['status'] == 'running'
        assert 'uptime_seconds' in status
        assert 'total_requests' in status
        assert 'cache_stats' in status
        assert 'supported_exchanges' in status
        assert len(status['supported_exchanges']) > 0
    
    @pytest.mark.asyncio
    async def test_get_exchange_info(self, mcp_server, mock_exchange):
        """Test exchange info retrieval"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.load_markets = AsyncMock()
        mock_exchange.countries = ["US"]
        
        info = await mcp_server.get_exchange_info("binance")
        
        assert 'id' in info
        assert 'name' in info
        assert 'has' in info
        assert info['has']['ticker'] is True
    
    @pytest.mark.asyncio
    async def test_search_symbols(self, mcp_server, mock_exchange):
        """Test symbol search"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.load_markets = AsyncMock()
        
        results = await mcp_server.search_symbols("BTC", "binance")
        
        assert len(results) > 0
        assert any("BTC" in symbol for symbol in results)
    
    def test_clear_cache(self, mcp_server):
        """Test cache clearing"""
        # Add something to cache
        ticker = TickerData(
            symbol="BTC/USDT",
            exchange="binance",
            timestamp=datetime.now(),
            last=50000.0,
            bid=49999.0,
            ask=50001.0,
            high=51000.0,
            low=49000.0,
            volume=1000.0
        )
        mcp_server.cache.set_ticker("binance", "BTC/USDT", ticker)
        
        # Clear cache
        mcp_server.clear_cache()
        
        # Verify cache is empty
        cached = mcp_server.cache.get_ticker("binance", "BTC/USDT")
        assert cached is None


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests with real (mocked) scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, mcp_server, mock_exchange, sample_ticker_data, sample_ohlcv_data):
        """Test complete workflow: ticker -> historical -> stats"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=sample_ohlcv_data)
        mock_exchange.load_markets = AsyncMock()
        
        # Get ticker
        ticker_request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        ticker = await mcp_server.get_ticker(ticker_request)
        assert ticker.last == 50000.0
        
        # Get historical data
        hist_request = HistoricalDataRequest(
            symbol="BTC/USDT",
            exchange=Exchange.BINANCE,
            timeframe=TimeFrame.H1,
            limit=3
        )
        ohlcv = await mcp_server.get_ohlcv(hist_request)
        assert len(ohlcv) == 3
        
        # Get statistics
        stats = await mcp_server.get_price_statistics(hist_request)
        assert 'current_price' in stats
        
        # Check server tracked requests
        assert mcp_server.request_count >= 3
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mcp_server, mock_exchange, sample_ticker_data):
        """Test error handling and recovery"""
        import ccxt
        
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.load_markets = AsyncMock()
        
        # First call fails
        mock_exchange.fetch_ticker = AsyncMock(side_effect=ccxt.NetworkError("Network error"))
        
        request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        
        with pytest.raises(RuntimeError):
            await mcp_server.get_ticker(request)
        
        initial_error_count = mcp_server.error_count
        
        # Second call succeeds
        mock_exchange.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
        ticker = await mcp_server.get_ticker(request)
        
        assert ticker.last == 50000.0
        assert mcp_server.error_count == initial_error_count  # No new errors
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mcp_server, mock_exchange, sample_ticker_data):
        """Test handling concurrent requests"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
        mock_exchange.load_markets = AsyncMock()
        
        # Create multiple concurrent requests
        requests = [
            MarketDataRequest(symbol=f"BTC/USDT", exchange=Exchange.BINANCE)
            for _ in range(10)
        ]
        
        tasks = [mcp_server.get_ticker(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(r.last == 50000.0 for r in results)


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance and stress tests"""
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, mcp_server, mock_exchange, sample_ticker_data):
        """Test cache improves performance"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
        mock_exchange.load_markets = AsyncMock()
        
        request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        
        # First call - should hit API
        await mcp_server.get_ticker(request)
        api_calls_1 = mock_exchange.fetch_ticker.call_count
        
        # Multiple subsequent calls - should hit cache
        for _ in range(10):
            await mcp_server.get_ticker(request)
        
        api_calls_2 = mock_exchange.fetch_ticker.call_count
        
        # Should still be just 1 API call
        assert api_calls_2 == api_calls_1
    
    @pytest.mark.asyncio
    async def test_request_counting(self, mcp_server, mock_exchange, sample_ticker_data):
        """Test request counting accuracy"""
        mcp_server.exchange_manager.exchanges["binance"] = mock_exchange
        mock_exchange.fetch_ticker = AsyncMock(return_value=sample_ticker_data)
        mock_exchange.load_markets = AsyncMock()
        
        initial_count = mcp_server.request_count
        
        request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
        for _ in range(5):
            await mcp_server.get_ticker(request)
        
        assert mcp_server.request_count == initial_count + 5


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])