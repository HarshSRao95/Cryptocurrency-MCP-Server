"""
Example usage scenarios for MCP Crypto Server
"""

import asyncio
from datetime import datetime, timedelta
from mainserver import (
    CryptoMCPServer,
    MarketDataRequest,
    HistoricalDataRequest,
    Exchange,
    TimeFrame
)


# ============================================================================
# Example 1: Basic Price Monitoring
# ============================================================================

async def example_price_monitoring():
    """Monitor current prices for multiple cryptocurrencies"""
    print("\n=== Example 1: Price Monitoring ===\n")
    
    server = CryptoMCPServer()
    
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
    
    for symbol in symbols:
        try:
            request = MarketDataRequest(symbol=symbol, exchange=Exchange.BINANCE)
            ticker = await server.get_ticker(request)
            
            print(f"{symbol:12} ${ticker.last:>10,.2f}  "
                  f"24h: {ticker.change_24h:>+6.2f}%  "
                  f"Vol: {ticker.volume:>12,.0f}")
        except Exception as e:
            print(f"{symbol:12} Error: {e}")


# ============================================================================
# Example 2: Historical Data Analysis
# ============================================================================

async def example_historical_analysis():
    """Analyze historical price movements"""
    print("\n=== Example 2: Historical Analysis ===\n")
    
    server = CryptoMCPServer()
    
    request = HistoricalDataRequest(
        symbol="BTC/USDT",
        exchange=Exchange.BINANCE,
        timeframe=TimeFrame.D1,
        limit=30  # Last 30 days
    )
    
    candles = await server.get_ohlcv(request)
    
    # Calculate daily returns
    returns = []
    for i in range(1, len(candles)):
        daily_return = ((candles[i].close - candles[i-1].close) / candles[i-1].close) * 100
        returns.append(daily_return)
    
    avg_return = sum(returns) / len(returns)
    max_gain = max(returns)
    max_loss = min(returns)
    
    print(f"BTC/USDT - 30 Day Analysis:")
    print(f"  Average Daily Return: {avg_return:+.2f}%")
    print(f"  Best Day: {max_gain:+.2f}%")
    print(f"  Worst Day: {max_loss:+.2f}%")
    print(f"  Total Return: {((candles[-1].close - candles[0].close) / candles[0].close) * 100:+.2f}%")


# ============================================================================
# Example 3: Multi-Exchange Price Comparison
# ============================================================================

async def example_price_comparison():
    """Compare prices across multiple exchanges"""
    print("\n=== Example 3: Multi-Exchange Comparison ===\n")
    
    server = CryptoMCPServer()
    
    symbol = "BTC/USDT"
    exchanges = [Exchange.BINANCE, Exchange.KRAKEN, Exchange.COINBASE]
    
    prices = await server.get_multi_exchange_ticker(symbol, exchanges)
    
    if len(prices) < 2:
        print("Not enough exchanges responded")
        return
    
    print(f"Price Comparison for {symbol}:")
    exchange_prices = [(ex, ticker.last) for ex, ticker in prices.items()]
    exchange_prices.sort(key=lambda x: x[1])
    
    for exchange, price in exchange_prices:
        print(f"  {exchange:12} ${price:,.2f}")
    
    # Calculate spread
    lowest = exchange_prices[0][1]
    highest = exchange_prices[-1][1]
    spread = ((highest - lowest) / lowest) * 100
    
    print(f"\n  Spread: {spread:.2f}%")
    print(f"  Arbitrage Opportunity: Buy on {exchange_prices[0][0]}, Sell on {exchange_prices[-1][0]}")


# ============================================================================
# Example 4: Order Book Analysis
# ============================================================================

async def example_orderbook_analysis():
    """Analyze order book depth"""
    print("\n=== Example 4: Order Book Analysis ===\n")
    
    server = CryptoMCPServer()
    
    request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
    orderbook = await server.get_orderbook(request, limit=10)
    
    print(f"Order Book for {request.symbol}:")
    print(f"\nTop 5 Asks (Sell Orders):")
    for i, (price, amount) in enumerate(orderbook.asks[:5], 1):
        print(f"  {i}. ${price:,.2f} x {amount:.4f} BTC")
    
    print(f"\nTop 5 Bids (Buy Orders):")
    for i, (price, amount) in enumerate(orderbook.bids[:5], 1):
        print(f"  {i}. ${price:,.2f} x {amount:.4f} BTC")
    
    # Calculate spread
    best_ask = orderbook.asks[0][0]
    best_bid = orderbook.bids[0][0]
    spread = best_ask - best_bid
    spread_pct = (spread / best_bid) * 100
    
    print(f"\nBid-Ask Spread: ${spread:.2f} ({spread_pct:.3f}%)")


# ============================================================================
# Example 5: Price Statistics and Volatility
# ============================================================================

async def example_statistics():
    """Calculate comprehensive price statistics"""
    print("\n=== Example 5: Price Statistics ===\n")
    
    server = CryptoMCPServer()
    
    symbols = ["BTC/USDT", "ETH/USDT"]
    
    for symbol in symbols:
        request = HistoricalDataRequest(
            symbol=symbol,
            exchange=Exchange.BINANCE,
            timeframe=TimeFrame.H1,
            limit=168  # One week of hourly data
        )
        
        stats = await server.get_price_statistics(request)
        
        print(f"\n{symbol} - Weekly Statistics:")
        print(f"  Current Price: ${stats['current_price']:,.2f}")
        print(f"  Average Price: ${stats['average_price']:,.2f}")
        print(f"  High: ${stats['highest_price']:,.2f}")
        print(f"  Low: ${stats['lowest_price']:,.2f}")
        print(f"  Volatility: ${stats['volatility']:,.2f}")
        print(f"  Change: {stats['price_change_percent']:+.2f}%")
        print(f"  Total Volume: {stats['total_volume']:,.0f}")


# ============================================================================
# Example 6: Moving Average Crossover Strategy
# ============================================================================

async def example_moving_average():
    """Implement simple moving average crossover"""
    print("\n=== Example 6: Moving Average Strategy ===\n")
    
    server = CryptoMCPServer()
    
    # Get historical data
    request = HistoricalDataRequest(
        symbol="BTC/USDT",
        exchange=Exchange.BINANCE,
        timeframe=TimeFrame.H1,
        limit=50
    )
    
    candles = await server.get_ohlcv(request)
    prices = [c.close for c in candles]
    
    # Calculate SMAs
    sma_short_period = 10
    sma_long_period = 20
    
    sma_short = sum(prices[-sma_short_period:]) / sma_short_period
    sma_long = sum(prices[-sma_long_period:]) / sma_long_period
    current_price = prices[-1]
    
    print(f"BTC/USDT Moving Average Analysis:")
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  SMA({sma_short_period}): ${sma_short:,.2f}")
    print(f"  SMA({sma_long_period}): ${sma_long:,.2f}")
    
    # Generate signal
    if sma_short > sma_long:
        if current_price > sma_short:
            signal = "STRONG BUY"
        else:
            signal = "BUY"
    else:
        if current_price < sma_short:
            signal = "STRONG SELL"
        else:
            signal = "SELL"
    
    print(f"\n  Signal: {signal}")


# ============================================================================
# Example 7: Price Alert System
# ============================================================================

async def example_price_alert():
    """Monitor price and trigger alerts"""
    print("\n=== Example 7: Price Alert System ===\n")
    
    server = CryptoMCPServer()
    
    symbol = "BTC/USDT"
    target_price = 50000
    check_interval = 10  # seconds
    max_checks = 5  # For demo purposes
    
    print(f"Monitoring {symbol} for price above ${target_price:,.2f}")
    print(f"Checking every {check_interval} seconds...\n")
    
    request = MarketDataRequest(symbol=symbol, exchange=Exchange.BINANCE)
    
    for i in range(max_checks):
        ticker = await server.get_ticker(request)
        current_price = ticker.last
        
        print(f"Check {i+1}: ${current_price:,.2f} ", end="")
        
        if current_price > target_price:
            print(f"🚨 ALERT! Price is above target!")
            break
        else:
            diff = target_price - current_price
            print(f"(${diff:,.2f} below target)")
        
        if i < max_checks - 1:
            await asyncio.sleep(check_interval)


# ============================================================================
# Example 8: Symbol Search and Discovery
# ============================================================================

async def example_symbol_search():
    """Search for trading pairs"""
    print("\n=== Example 8: Symbol Search ===\n")
    
    server = CryptoMCPServer()
    
    search_terms = ["BTC", "ETH", "USDT"]
    
    for term in search_terms:
        results = await server.search_symbols(term, "binance")
        print(f"\nSymbols containing '{term}' (showing first 10):")
        for symbol in results[:10]:
            print(f"  {symbol}")


# ============================================================================
# Example 9: Volume Analysis
# ============================================================================

async def example_volume_analysis():
    """Analyze trading volume patterns"""
    print("\n=== Example 9: Volume Analysis ===\n")
    
    server = CryptoMCPServer()
    
    request = HistoricalDataRequest(
        symbol="BTC/USDT",
        exchange=Exchange.BINANCE,
        timeframe=TimeFrame.H1,
        limit=24  # Last 24 hours
    )
    
    candles = await server.get_ohlcv(request)
    
    volumes = [c.volume for c in candles]
    avg_volume = sum(volumes) / len(volumes)
    current_volume = volumes[-1]
    
    # Find volume spikes
    volume_threshold = avg_volume * 1.5
    spikes = [i for i, v in enumerate(volumes) if v > volume_threshold]
    
    print(f"BTC/USDT - 24h Volume Analysis:")
    print(f"  Average Volume: {avg_volume:,.0f}")
    print(f"  Current Volume: {current_volume:,.0f}")
    print(f"  Volume vs Average: {(current_volume / avg_volume * 100):.1f}%")
    print(f"  Volume Spikes Detected: {len(spikes)}")
    
    if spikes:
        print(f"\n  Spike Times:")
        for spike_idx in spikes[-5:]:  # Last 5 spikes
            candle = candles[spike_idx]
            print(f"    {candle.timestamp.strftime('%Y-%m-%d %H:%M')} - "
                  f"{candle.volume:,.0f} ({(candle.volume / avg_volume * 100):.1f}% of avg)")


# ============================================================================
# Example 10: Server Monitoring
# ============================================================================

async def example_server_monitoring():
    """Monitor server health and performance"""
    print("\n=== Example 10: Server Monitoring ===\n")
    
    server = CryptoMCPServer()
    
    # Make some requests first
    request = MarketDataRequest(symbol="BTC/USDT", exchange=Exchange.BINANCE)
    await server.get_ticker(request)
    await server.get_ticker(request)  # Should hit cache
    
    # Get server status
    status = await server.get_server_status()
    
    print("Server Status:")
    print(f"  Status: {status['status']}")
    print(f"  Uptime: {status['uptime_seconds']:.1f} seconds")
    print(f"  Total Requests: {status['total_requests']}")
    print(f"  Total Errors: {status['total_errors']}")
    print(f"  Error Rate: {status['error_rate']:.2%}")
    
    print(f"\n  Cache Statistics:")
    print(f"    Ticker Cache Size: {status['cache_stats']['ticker_size']}")
    print(f"    OHLCV Cache Size: {status['cache_stats']['ohlcv_size']}")
    
    print(f"\n  Supported Exchanges: {', '.join(status['supported_exchanges'])}")
    print(f"  Supported Timeframes: {', '.join(status['supported_timeframes'])}")


# ============================================================================
# Main Runner
# ============================================================================

async def run_all_examples():
    """Run all examples"""
    examples = [
        example_price_monitoring,
        example_historical_analysis,
        example_price_comparison,
        example_orderbook_analysis,
        example_statistics,
        example_moving_average,
        example_price_alert,
        example_symbol_search,
        example_volume_analysis,
        example_server_monitoring
    ]
    
    for example in examples:
        try:
            await example()
            await asyncio.sleep(1)  # Brief pause between examples
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
            continue


if __name__ == "__main__":
    print("=" * 60)
    print("MCP Crypto Server - Usage Examples")
    print("=" * 60)
    
    asyncio.run(run_all_examples())
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)