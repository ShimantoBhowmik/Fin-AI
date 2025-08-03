"""
Data processing and analysis module
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger

from .models import StockData, FundamentalMetrics, StockPrice
from .config import settings


class StockDataProcessor:
    """Process and analyze stock data"""

    def __init__(self):
        self.cache = {}  # Simple in-memory cache for processed data

    def calculate_technical_indicators(
        self, ticker: str, period: str = "1y"
    ) -> Dict[str, Any]:
        """Calculate technical indicators using yfinance data"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)

            if hist.empty:
                logger.warning(f"No historical data available for {ticker}")
                return {}

            # Calculate moving averages
            hist["MA20"] = hist["Close"].rolling(window=20).mean()
            hist["MA50"] = hist["Close"].rolling(window=50).mean()
            hist["MA200"] = hist["Close"].rolling(window=200).mean()

            # Calculate RSI
            hist["RSI"] = self._calculate_rsi(hist["Close"])

            # Calculate Bollinger Bands
            bb_period = 20
            bb_std = 2
            rolling_mean = hist["Close"].rolling(window=bb_period).mean()
            rolling_std = hist["Close"].rolling(window=bb_period).std()
            hist["BB_Upper"] = rolling_mean + (rolling_std * bb_std)
            hist["BB_Lower"] = rolling_mean - (rolling_std * bb_std)

            # Get latest values
            latest = hist.iloc[-1]

            indicators = {
                "moving_averages": {
                    "ma20": latest["MA20"],
                    "ma50": latest["MA50"],
                    "ma200": latest["MA200"],
                },
                "rsi": latest["RSI"],
                "bollinger_bands": {
                    "upper": latest["BB_Upper"],
                    "lower": latest["BB_Lower"],
                    "current_position": self._bollinger_position(
                        latest["Close"], latest["BB_Upper"], latest["BB_Lower"]
                    ),
                },
                "volume_analysis": {
                    "avg_volume_20d": hist["Volume"].tail(20).mean(),
                    "current_volume": latest["Volume"],
                    "volume_ratio": (
                        latest["Volume"] / hist["Volume"].tail(20).mean()
                        if hist["Volume"].tail(20).mean() > 0
                        else 0
                    ),
                },
            }

            logger.info(f"Calculated technical indicators for {ticker}")
            return indicators

        except Exception as e:
            logger.error(f"Error calculating technical indicators for {ticker}: {e}")
            return {}

    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _bollinger_position(
        self, current_price: float, upper_band: float, lower_band: float
    ) -> str:
        """Determine position relative to Bollinger Bands"""
        if current_price > upper_band:
            return "above_upper"
        elif current_price < lower_band:
            return "below_lower"
        else:
            return "within_bands"

    def calculate_valuation_metrics(self, stock_data: StockData) -> Dict[str, Any]:
        """Calculate additional valuation metrics"""
        try:
            fundamentals = stock_data.fundamentals
            price = stock_data.price_info.current_price

            metrics = {}

            # Price to Book ratio (if we have book value)
            if fundamentals.roe and fundamentals.eps:
                # Estimate book value per share: EPS / ROE * 100
                book_value_per_share = (fundamentals.eps / fundamentals.roe) * 100
                metrics["pb_ratio"] = (
                    price / book_value_per_share if book_value_per_share > 0 else None
                )

            # Dividend information
            if fundamentals.dividend_yield:
                annual_dividend = (price * fundamentals.dividend_yield) / 100
                metrics["annual_dividend"] = annual_dividend

            # Market cap analysis
            if fundamentals.market_cap:
                if fundamentals.market_cap > 200_000_000_000:
                    metrics["market_cap_category"] = "Large Cap"
                elif fundamentals.market_cap > 10_000_000_000:
                    metrics["market_cap_category"] = "Mid Cap"
                elif fundamentals.market_cap > 2_000_000_000:
                    metrics["market_cap_category"] = "Small Cap"
                else:
                    metrics["market_cap_category"] = "Micro Cap"

            # 52-week performance
            if fundamentals.fifty_two_week_range:
                range_high = fundamentals.fifty_two_week_range.high
                range_low = fundamentals.fifty_two_week_range.low

                position_in_range = (
                    (price - range_low) / (range_high - range_low)
                    if range_high > range_low
                    else 0
                )
                metrics["52w_position_percent"] = position_in_range * 100

                # Distance from highs/lows
                metrics["distance_from_52w_high"] = (
                    (range_high - price) / range_high
                ) * 100
                metrics["distance_from_52w_low"] = (
                    (price - range_low) / range_low
                ) * 100

            logger.info(f"Calculated valuation metrics for {stock_data.ticker}")
            return metrics

        except Exception as e:
            logger.error(
                f"Error calculating valuation metrics for {stock_data.ticker}: {e}"
            )
            return {}

    def compare_stocks(self, stocks_data: List[StockData]) -> Dict[str, Any]:
        """Compare multiple stocks and provide relative analysis"""
        try:
            if len(stocks_data) < 2:
                return {"message": "Need at least 2 stocks for comparison"}

            comparison = {
                "valuation": {},
                "fundamentals": {},
                "rankings": {},
            }

            # Valuation comparison (P/E ratios)
            pe_data = []
            for stock in stocks_data:
                if stock.fundamentals.pe_ratio:
                    pe_data.append(
                        {
                            "ticker": stock.ticker,
                            "pe_ratio": stock.fundamentals.pe_ratio,
                        }
                    )

            if pe_data:
                pe_data.sort(key=lambda x: x["pe_ratio"])
                comparison["valuation"]["ranked_by_pe"] = pe_data

                # Calculate average P/E
                avg_pe = sum(item["pe_ratio"] for item in pe_data) / len(pe_data)
                comparison["valuation"]["average_pe"] = avg_pe

            # Fundamental comparison
            dividend_stocks = [
                {
                    "ticker": stock.ticker,
                    "dividend_yield": stock.fundamentals.dividend_yield,
                }
                for stock in stocks_data
                if stock.fundamentals.dividend_yield
            ]

            if dividend_stocks:
                dividend_stocks.sort(key=lambda x: x["dividend_yield"], reverse=True)
                comparison["fundamentals"]["ranked_by_dividend_yield"] = dividend_stocks

            # Market cap comparison
            market_cap_data = [
                {"ticker": stock.ticker, "market_cap": stock.fundamentals.market_cap}
                for stock in stocks_data
                if stock.fundamentals.market_cap
            ]

            if market_cap_data:
                market_cap_data.sort(key=lambda x: x["market_cap"], reverse=True)
                comparison["fundamentals"]["ranked_by_market_cap"] = market_cap_data

            logger.info(f"Completed comparison analysis for {len(stocks_data)} stocks")
            return comparison

        except Exception as e:
            logger.error(f"Error comparing stocks: {e}")
            return {"error": "Failed to compare stocks"}

    def calculate_portfolio_metrics(
        self, stocks_data: List[StockData], weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Calculate portfolio-level metrics"""
        try:
            if not stocks_data:
                return {}

            # Equal weights if not provided
            if weights is None:
                weights = [1.0 / len(stocks_data)] * len(stocks_data)

            if len(weights) != len(stocks_data):
                logger.warning(
                    "Weights length doesn't match stocks count, using equal weights"
                )
                weights = [1.0 / len(stocks_data)] * len(stocks_data)

            # Portfolio daily return
            weighted_returns = sum(
                stock.price_info.change_percent * weight
                for stock, weight in zip(stocks_data, weights)
            )

            # Portfolio value metrics
            total_market_cap = sum(
                stock.fundamentals.market_cap or 0 for stock in stocks_data
            )

            # Average P/E ratio (weighted)
            pe_ratios = [
                stock.fundamentals.pe_ratio
                for stock in stocks_data
                if stock.fundamentals.pe_ratio
            ]
            avg_pe = sum(pe_ratios) / len(pe_ratios) if pe_ratios else None

            # Dividend yield (weighted)
            dividend_yields = []
            for stock, weight in zip(stocks_data, weights):
                if stock.fundamentals.dividend_yield:
                    dividend_yields.append(stock.fundamentals.dividend_yield * weight)

            weighted_dividend_yield = sum(dividend_yields) if dividend_yields else None

            portfolio_metrics = {
                "number_of_stocks": len(stocks_data),
                "weighted_daily_return": weighted_returns,
                "total_market_cap": total_market_cap,
                "average_pe_ratio": avg_pe,
                "weighted_dividend_yield": weighted_dividend_yield,
                "sector_diversification": self._analyze_sector_diversification(
                    stocks_data
                ),
                "risk_metrics": {
                    "high_pe_stocks": len(
                        [
                            s
                            for s in stocks_data
                            if s.fundamentals.pe_ratio and s.fundamentals.pe_ratio > 25
                        ]
                    ),
                    "dividend_paying_stocks": len(
                        [
                            s
                            for s in stocks_data
                            if s.fundamentals.dividend_yield
                            and s.fundamentals.dividend_yield > 0
                        ]
                    ),
                    "negative_performers": len(
                        [s for s in stocks_data if s.price_info.change_percent < 0]
                    ),
                },
            }

            logger.info(f"Calculated portfolio metrics for {len(stocks_data)} stocks")
            return portfolio_metrics

        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {}

    def _analyze_sector_diversification(
        self, stocks_data: List[StockData]
    ) -> Dict[str, Any]:
        """Analyze sector diversification (simplified version)"""
        # This is a simplified implementation
        # In a real scenario, you'd fetch sector information from financial APIs

        # For now, categorize based on common patterns in ticker symbols
        sectors = {}
        for stock in stocks_data:
            # This is a very basic categorization - in practice, you'd use proper sector data
            ticker = stock.ticker.upper()
            if ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]:
                sector = "Technology"
            elif ticker in ["JPM", "BAC", "WFC", "GS", "MS"]:
                sector = "Financial"
            elif ticker in ["JNJ", "PFE", "MRK", "ABT", "UNH"]:
                sector = "Healthcare"
            else:
                sector = "Other"

            sectors[sector] = sectors.get(sector, 0) + 1

        return {
            "sectors": sectors,
            "diversification_score": (
                len(sectors) / len(stocks_data) if stocks_data else 0
            ),
        }
