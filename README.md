# Cryptocurrency Market Data MCP Server

A production-ready Model Context Protocol (MCP) server for retrieving real-time and historical cryptocurrency market data from major exchanges using CCXT.

## Features

### Core Functionality
- **Real-time Market Data**: Get current ticker prices, order books, and trades
- **Historical Data**: Retrieve OHLCV (candlestick) data with customizable timeframes
- **Multi-Exchange Support**: Query data from Binance, Coinbase, Kraken, Bitfinex, and Huobi
- **Price Analytics**: Calculate statistics, volatility, and price movements
- **Smart Caching**: Automatic caching with TTL for improved performance
- **Error Handling**: Robust error handling with retry logic and graceful degradation
- **Async Architecture**: Built on asyncio for high-performance concurrent requests

### Supported Operations
1. **Real-time Ticker Data** - Current price, bid/ask, volume, 24h change
2. **Order Book** - Current bids and asks with depth
3. **Historical OHLCV** - Candlestick data for technical analysis
4. **Price Statistics** - Volatility, average price, price changes
5. **Multi-Exchange Comparison** - Compare prices across exchanges
6. **Symbol Search** - Find available trading pairs
7. **Server Status** - Monitor performance and health

## Requirements

- Python 3.9+
- pip or conda for package management
- Internet connection for API access

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/mcp-crypto-server.git
cd mcp-crypto-server
```

### 2. Create Virtual Environment
```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n mcp-crypto python=3.9
conda activate mcp-crypto
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
import asyncio
from mcp_crypto_server import (
    CryptoMCPServer,
    MarketDataRequest,
    HistoricalDataRequest,
    Exchange,
    TimeFrame
)

async def main():
    # Initialize server
    server = CryptoMCPServer()
    
    # Get real-time ticker
    ticker_request = MarketDataRequest(
        symbol="BTC/USDT",
        exchange=Exchange.BINANCE
    )
    ticker = await server.get_ticker(ticker_request)
    print(f"BTC Price: ${ticker.last:,.2f}")
    
    # Get historical data
    hist_request = HistoricalDataRequest(
        symbol="BTC/USDT",
        exchange=Exchange.BINANCE,
        timeframe=TimeFrame.H1,
        limit=24  # Last 24 hours
    )
    ohlcv = await server.get_ohlcv(hist_request)
    print(f"Retrieved {len(ohlcv)} candles")
    
    # Get price statistics
    stats = await server.get_price_statistics(hist_request)
    print(f"24h Change: {stats['price_change_percent']:.2f}%")
    print(f"Volatility: ${stats['volatility']:,.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Running Tests

```bash
# Run all tests
pytest test_mcp_crypto_server.py -v

# Run with coverage
pytest test_mcp_crypto_server.py --cov=mcp_crypto_server --cov-report=html

# Run specific test class
pytest test_mcp_crypto_server.py::TestCryptoMCPServer -v

# Run with verbose output
pytest test_mcp_crypto_server.py -vv -s
```

## API Documentation

### Data Models

#### MarketDataRequest
```python
MarketDataRequest(
    symbol: str,        # Trading pair (e.g., "BTC/USDT")
    exchange: Exchange  # Exchange enum (BINANCE, COINBASE, etc.)
)
```

#### HistoricalDataRequest
```python
HistoricalDataRequest(
    symbol: str,
    exchange: Exchange,
    timeframe: TimeFrame,  # M1, M5, M15, M30, H1, H4, D1, W1, MO1
    limit: int = 100,      # Number of candles (1-1000)
    since: Optional[datetime] = None  # Start date
)
```

### Core Methods

#### `get_ticker(request: MarketDataRequest) -> TickerData`
Get real-time ticker information.

**Returns:**
- `symbol`: Trading pair
- `last`: Last traded price
- `bid`/`ask`: Current bid and ask prices
- `high`/`low`: 24h high and low
- `volume`: 24h trading volume
- `change_24h`: 24h percentage change

**Example:**
```python
request = MarketDataRequest(symbol="ETH/USDT", exchange=Exchange.BINANCE)
ticker = await server.get_ticker(request)
print(f"ETH: ${ticker.last:.2f} ({ticker.change_24h:+.2f}%)")
```

#### `get_ohlcv(request: HistoricalDataRequest) -> List[OHLCVData]`
Get historical candlestick data.

**Returns:** List of OHLCV candles with:
- `timestamp`: Candle timestamp
- `open`, `high`, `low`, `close`: OHLC prices
- `volume`: Trading volume

**Example:**
```python
request = HistoricalDataRequest(
    symbol="BTC/USDT",
    exchange=Exchange.BINANCE,
    timeframe=TimeFrame.D1,
    limit=30  # Last 30 days
)
candles = await server.get_ohlcv(request)
for candle in candles[-5:]:  # Last 5 days
    print(f"{candle.timestamp}: ${candle.close:,.2f}")
```

#### `get_orderbook(request: MarketDataRequest, limit: int = 20) -> OrderBookData`
Get current order book.

**Example:**
```python
request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
orderbook = await server.get_orderbook(request, limit=10)
print(f"Best bid: ${orderbook.bids[0][0]:,.2f}")
print(f"Best ask: ${orderbook.asks[0][0]:,.2f}")
```

#### `get_price_statistics(request: HistoricalDataRequest) -> Dict`
Calculate comprehensive price statistics.

**Returns:**
- `current_price`: Latest price
- `highest_price`/`lowest_price`: Price range
- `average_price`: Mean price
- `volatility`: Standard deviation
- `price_change_percent`: Percentage change
- `total_volume`/`average_volume`: Volume metrics

**Example:**
```python
request = HistoricalDataRequest(
    symbol="BTC/USDT",
    timeframe=TimeFrame.H1,
    limit=168  # One week of hourly data
)
stats = await server.get_price_statistics(request)
print(f"Weekly Stats for BTC:")
print(f"  Range: ${stats['lowest_price']:,.2f} - ${stats['highest_price']:,.2f}")
print(f"  Average: ${stats['average_price']:,.2f}")
print(f"  Volatility: ${stats['volatility']:,.2f}")
print(f"  Change: {stats['price_change_percent']:+.2f}%")
```

#### `get_multi_exchange_ticker(symbol: str, exchanges: List[Exchange]) -> Dict`
Compare prices across multiple exchanges.

**Example:**
```python
prices = await server.get_multi_exchange_ticker(
    "BTC/USDT",
    [Exchange.BINANCE, Exchange.KRAKEN, Exchange.COINBASE]
)
for exchange, ticker in prices.items():
    print(f"{exchange}: ${ticker.last:,.2f}")
```

### Utility Methods

#### `get_server_status() -> Dict`
Get server health and statistics.

```python
status = await server.get_server_status()
print(f"Uptime: {status['uptime_seconds']:.0f}s")
print(f"Requests: {status['total_requests']}")
print(f"Error Rate: {status['error_rate']:.2%}")
```

#### `search_symbols(query: str, exchange: str) -> List[str]`
Search for trading pairs.

```python
results = await server.search_symbols("ETH", "binance")
print(f"Found {len(results)} symbols containing 'ETH'")
for symbol in results[:10]:
    print(f"  {symbol}")
```

#### `clear_cache()`
Clear all cached data.

```python
server.clear_cache()
```

## Architecture

### Design Principles

1. **Separation of Concerns**
   - `CryptoMCPServer`: Main API interface
   - `ExchangeManager`: Exchange connection handling
   - `CacheManager`: Intelligent caching
   - Data models: Type-safe request/response handling

2. **Async-First**
   - All I/O operations are async
   - Supports concurrent requests
   - Efficient resource utilization

3. **Error Resilience**
   - Graceful error handling at every level
   - Detailed logging
   - Automatic retries (via CCXT)
   - Error counting and monitoring

4. **Performance Optimization**
   - Multi-level caching with TTL
   - Rate limiting compliance
   - Connection pooling
   - Minimal data transformation

### Cache Strategy

The server implements a three-tier caching system:

| Cache Type | TTL | Purpose |
|------------|-----|---------|
| Ticker | 10s | Real-time price data |
| OHLCV | 60s | Historical candles |
| Order Book | 5s | Order book snapshots |

Cache keys are generated using MD5 hashes of parameters for consistency.

## Testing

### Test Coverage

The test suite includes:

- **Unit Tests**: Individual component testing
  - Data model validation
  - Cache operations
  - Exchange management
  - Request/response handling

- **Integration Tests**: End-to-end workflows
  - Complete data retrieval flows
  - Error handling and recovery
  - Concurrent request handling

- **Performance Tests**: Efficiency validation
  - Cache performance
  - Request counting
  - Memory usage

### Test Structure

```
tests/
├── test_data_models.py      # Model validation tests
├── test_cache_manager.py    # Cache functionality tests
├── test_exchange_manager.py # Exchange connection tests
├── test_mcp_server.py        # Core server tests
├── test_integration.py       # Integration tests
└── test_performance.py       # Performance tests
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest test_mcp_crypto_server.py::TestDataModels -v
pytest test_mcp_crypto_server.py::TestCacheManager -v

# Integration tests
pytest test_mcp_crypto_server.py::TestIntegration -v

# With coverage report
pytest --cov=mcp_crypto_server --cov-report=term-missing
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file for optional configuration:

```bash
# Logging
LOG_LEVEL=INFO
LOG_FILE=mcp_server.log

# Cache TTLs (seconds)
TICKER_CACHE_TTL=10
OHLCV_CACHE_TTL=60
ORDERBOOK_CACHE_TTL=5

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=1200

# Exchange API Keys (optional, for authenticated endpoints)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

### Custom Configuration

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
import logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'mcp_server.log')),
        logging.StreamHandler()
    ]
)
```

## Examples

### Example 1: Price Alert System

```python
async def price_alert(server, symbol, threshold):
    """Alert when price crosses threshold"""
    request = MarketDataRequest(symbol=symbol, exchange=Exchange.BINANCE)
    
    while True:
        ticker = await server.get_ticker(request)
        if ticker.last > threshold:
            print(f"ALERT: {symbol} is ${ticker.last:,.2f} (above ${threshold:,.2f})")
            break
        await asyncio.sleep(10)

# Usage
asyncio.run(price_alert(server, "BTC/USDT", 50000))
```

### Example 2: Arbitrage Detection

```python
async def find_arbitrage(server, symbol):
    """Find price differences across exchanges"""
    exchanges = [Exchange.BINANCE, Exchange.KRAKEN, Exchange.COINBASE]
    prices = await server.get_multi_exchange_ticker(symbol, exchanges)
    
    prices_list = [(ex, ticker.last) for ex, ticker in prices.items()]
    prices_list.sort(key=lambda x: x[1])
    
    lowest = prices_list[0]
    highest = prices_list[-1]
    spread = ((highest[1] - lowest[1]) / lowest[1]) * 100
    
    print(f"Arbitrage Opportunity for {symbol}:")
    print(f"  Buy: {lowest[0]} @ ${lowest[1]:,.2f}")
    print(f"  Sell: {highest[0]} @ ${highest[1]:,.2f}")
    print(f"  Spread: {spread:.2f}%")
```

### Example 3: Technical Analysis

```python
async def calculate_sma(server, symbol, period=20):
    """Calculate Simple Moving Average"""
    request = HistoricalDataRequest(
        symbol=symbol,
        timeframe=TimeFrame.H1,
        limit=period
    )
    candles = await server.get_ohlcv(request)
    prices = [c.close for c in candles]
    sma = sum(prices) / len(prices)
    
    current_price = prices[-1]
    signal = "BUY" if current_price > sma else "SELL"
    
    print(f"SMA({period}): ${sma:,.2f}")
    print(f"Current: ${current_price:,.2f}")
    print(f"Signal: {signal}")
```

## Error Handling

The server implements comprehensive error handling:

```python
try:
    ticker = await server.get_ticker(request)
except ValueError as e:
    print(f"Invalid request: {e}")
except RuntimeError as e:
    print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

Common error scenarios:
- **Network errors**: Automatic retry via CCXT
- **Invalid symbols**: Validation before API call
- **Rate limiting**: Built-in rate limiting compliance
- **Exchange downtime**: Graceful degradation

## Performance Considerations

### Optimization Tips

1. **Use caching effectively**: Repeated queries within TTL use cache
2. **Batch requests**: Use multi-exchange queries for parallel execution
3. **Choose appropriate timeframes**: Longer timeframes = less data
4. **Set reasonable limits**: Balance data needs with performance
5. **Monitor server status**: Check error rates and adjust usage

### Benchmarks

Typical performance (on standard hardware):
- Single ticker request: ~100-300ms (first call)
- Cached ticker request: ~1ms
- OHLCV request (100 candles): ~200-500ms
- Multi-exchange comparison: ~300-600ms (parallel)

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest -v

# Format code
black mcp_crypto_server.py
isort mcp_crypto_server.py

# Type checking
mypy mcp_crypto_server.py
```

## License

MIT License - see LICENSE file for details

## Acknowledgments

- **CCXT**: Cryptocurrency exchange integration
- **Pydantic**: Data validation
- **cachetools**: Efficient caching

## Support

- GitHub Issues: [Report bugs or request features]
- Documentation: [Full API reference]
- Email: your.email@example.com

## Roadmap

### Planned Features
- [ ] WebSocket support for real-time streaming
- [ ] More exchanges (FTX, Gemini, etc.)
- [ ] Advanced technical indicators (RSI, MACD, Bollinger Bands)
- [ ] Portfolio tracking
- [ ] Historical data export (CSV, JSON)
- [ ] Backtesting framework
- [ ] Alert notifications (email, SMS, webhook)
- [ ] REST API wrapper for HTTP access
- [ ] GraphQL interface

### Version History

**v1.0.0** (Current)
- Initial release
- Core MCP functionality
- 5 major exchanges
- Comprehensive test suite
- Smart caching
- Price analytics

---
