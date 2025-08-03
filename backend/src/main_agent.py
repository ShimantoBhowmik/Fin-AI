"""
Main Stock Analysis Agent - Orchestrates the entire analysis workflow
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger

from .config import settings
from .models import StockRequest, AnalysisReport, StockData
from .browser_agent import StockBrowserAgent
from .llm_service import StockAnalysisLLM, NewsAnalyzer
from .data_processor import StockDataProcessor
from .report_generator import ReportGenerator


class StockAnalysisAgent:
    """Main orchestrator for stock analysis workflow"""

    def __init__(self):
        self.browser_agent = StockBrowserAgent()
        self.llm_service = StockAnalysisLLM()
        self.news_analyzer = NewsAnalyzer()
        self.data_processor = StockDataProcessor()
        self.report_generator = ReportGenerator()

        # Track analysis state
        self.current_analysis = None
        self.analysis_results = []

    async def analyze_stocks(self, request: StockRequest) -> AnalysisReport:
        """Main analysis workflow"""
        print(f"🚀 Starting stock analysis for: {', '.join(request.tickers)}")

        # Initialize prompt tracking
        llm_prompts_used = {}
        system_prompts_used = {
            "stock_analysis_system_prompt": self.llm_service.system_prompt,
            "news_sentiment_system_prompt": self.news_analyzer.sentiment_system_prompt,
        }

        try:
            # Initialize browser agent
            await self.browser_agent.initialize()

            # Step 1: Extract data for each ticker
            stocks_data = []
            for ticker in request.tickers:
                print(f"📊 Analyzing {ticker}...")

                # Extract stock data via browser
                stock_data = await self.browser_agent.extract_stock_data(
                    ticker=ticker,
                    include_news=request.include_news,
                    include_reddit=request.include_reddit,
                )

                # Add technical indicators
                technical_indicators = (
                    self.data_processor.calculate_technical_indicators(
                        ticker, period=request.date_range or "1y"
                    )
                )

                # Add valuation metrics
                valuation_metrics = self.data_processor.calculate_valuation_metrics(
                    stock_data
                )

                # Store additional analysis data
                stock_data.technical_indicators = technical_indicators
                stock_data.valuation_metrics = valuation_metrics

                # Store prompts used for this stock
                stock_data.llm_prompts_used = {}

                # Analyze news sentiment if news is available
                if stock_data.news:
                    sentiment_analysis = await self.news_analyzer.analyze_sentiment(
                        stock_data.news
                    )
                    stock_data.news_sentiment = sentiment_analysis

                stocks_data.append(stock_data)
                print(f"✅ Completed analysis for {ticker}")

            # Step 2: Generate insights for each stock
            print("🧠 Generating AI insights...")
            for stock_data in stocks_data:
                insights = await self.llm_service.generate_insights(
                    stock_data, store_prompts_in=stock_data.llm_prompts_used
                )
                stock_data.insights = insights

                # Add to global prompt tracking
                llm_prompts_used.update(stock_data.llm_prompts_used)

            # Step 3: Comparative analysis if multiple stocks
            comparative_analysis = {}
            if len(stocks_data) > 1:
                print("🔍 Performing comparative analysis...")
                comparative_analysis = self.data_processor.compare_stocks(stocks_data)

            # Step 4: Portfolio-level analysis
            portfolio_metrics = self.data_processor.calculate_portfolio_metrics(
                stocks_data
            )

            # Step 6: Create comprehensive insights
            all_insights = []
            for stock_data in stocks_data:
                all_insights.extend(getattr(stock_data, "insights", []))

            # Add comparative insights
            if comparative_analysis:
                all_insights.extend(
                    self._extract_comparative_insights(comparative_analysis)
                )

            # Step 7: Generate final report
            print("📋 Generating final report...")
            
            # Generate executive summary from insights
            summary = self._generate_executive_summary(all_insights, stocks_data)
            
            analysis_report = AnalysisReport(
                request=request,
                stocks_data=stocks_data,
                insights=all_insights,
                summary=summary,
                system_prompts_used=system_prompts_used,
            )

            # Generate formatted report
            report_path = await self.report_generator.generate_report(analysis_report)
            analysis_report.report_path = report_path

            print(f"🎉 Analysis complete! Report saved to: {report_path}")
            return analysis_report

        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            raise
        finally:
            # Clean up browser resources
            await self.browser_agent.close()

    def _generate_executive_summary(self, insights: List[str], stocks_data: List[StockData]) -> str:
        """Generate an executive summary from the analysis"""
        if not stocks_data:
            return "No stocks were analyzed."
        
        # Create a simple summary based on the stocks analyzed
        tickers = [stock.ticker for stock in stocks_data]
        total_stocks = len(stocks_data)
        
        # Calculate basic stats
        positive_changes = sum(1 for stock in stocks_data if stock.price_info.change > 0)
        negative_changes = sum(1 for stock in stocks_data if stock.price_info.change < 0)
        
        summary_parts = []
        
        if total_stocks == 1:
            stock = stocks_data[0]
            direction = "up" if stock.price_info.change > 0 else "down" if stock.price_info.change < 0 else "flat"
            summary_parts.append(f"Analysis of {stock.ticker} ({stock.company_name}) shows the stock is {direction} {abs(stock.price_info.change_percent):.2f}% at ${stock.price_info.current_price:.2f}.")
        else:
            summary_parts.append(f"Analysis of {total_stocks} stocks: {', '.join(tickers)}.")
            summary_parts.append(f"{positive_changes} stocks are up, {negative_changes} are down.")
        
        # Add insights summary
        if insights:
            summary_parts.append(f"Generated {len(insights)} analytical insights covering fundamental analysis, technical indicators, and market sentiment.")
        
        return " ".join(summary_parts)

    async def close(self):
        """Close browser resources"""
        try:
            await self.browser_agent.close()
        except Exception as e:
            logger.warning(f"Error closing browser agent: {e}")

    def _format_request_context(self, request: StockRequest) -> str:
        """Format the analysis request for LLM context"""
        context_parts = [
            f"Tickers: {', '.join(request.tickers)}",
            f"Date Range: {request.date_range or 'Default (1 year)'}",
            f"Requested Metrics: {', '.join([m.value for m in request.metrics])}",
            f"Include News: {'Yes' if request.include_news else 'No'}",
        ]
        return " | ".join(context_parts)

    def _extract_comparative_insights(
        self, comparative_analysis: Dict[str, Any]
    ) -> List[str]:
        """Extract insights from comparative analysis"""
        insights = []

        # Valuation insights
        if "valuation" in comparative_analysis:
            pe_data = comparative_analysis["valuation"].get("ranked_by_pe", [])
            if pe_data:
                lowest_pe = pe_data[0]
                highest_pe = pe_data[-1]
                insights.append(
                    f"Most attractive valuation (lowest P/E): {lowest_pe['ticker']} (P/E: {lowest_pe['pe_ratio']:.2f})"
                )
                insights.append(
                    f"Highest valuation (highest P/E): {highest_pe['ticker']} (P/E: {highest_pe['pe_ratio']:.2f})"
                )

        # Dividend insights
        if "fundamentals" in comparative_analysis:
            dividend_data = comparative_analysis["fundamentals"].get(
                "ranked_by_dividend_yield", []
            )
            if dividend_data:
                highest_dividend = dividend_data[0]
                insights.append(
                    f"Highest dividend yield: {highest_dividend['ticker']} ({highest_dividend['dividend_yield']:.2f}%)"
                )

        return insights

    async def quick_analysis(self, ticker: str) -> Dict[str, Any]:
        """Perform a quick analysis of a single stock"""
        print(f"⚡ Quick analysis for {ticker}")

        try:
            # Create a simple request
            request = StockRequest(
                tickers=[ticker], include_news=True
            )

            # Run basic analysis
            await self.browser_agent.initialize()
            stock_data = await self.browser_agent.extract_stock_data(
                ticker=ticker,
                include_news=True,
            )

            # Add technical indicators
            technical_indicators = self.data_processor.calculate_technical_indicators(
                ticker
            )

            # Generate quick insights
            insights = await self.llm_service.generate_insights(stock_data)

            return {
                "ticker": ticker,
                "current_price": stock_data.price_info.current_price,
                "change_percent": stock_data.price_info.change_percent,
                "pe_ratio": stock_data.fundamentals.pe_ratio,
                "market_cap": stock_data.fundamentals.market_cap,
                "technical_indicators": technical_indicators,
                "insights": insights,
                "news_count": len(stock_data.news),
            }

        except Exception as e:
            print(f"❌ Error in quick analysis: {e}")
            return {"error": str(e)}
        finally:
            await self.browser_agent.close()

    async def monitor_stocks(
        self, tickers: List[str], alert_thresholds: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """Monitor stocks for significant changes"""
        print(f"👁️ Monitoring {len(tickers)} stocks...")

        # This is a simplified monitoring function
        # In production, you'd implement continuous monitoring with proper scheduling

        alerts = []
        monitoring_data = {}

        try:
            await self.browser_agent.initialize()

            for ticker in tickers:
                try:
                    stock_data = await self.browser_agent.extract_stock_data(
                        ticker=ticker,
                        include_news=False,
                    )

                    # Check for alerts
                    change_percent = abs(stock_data.price_info.change_percent)
                    threshold = (
                        alert_thresholds.get(ticker, 5.0) if alert_thresholds else 5.0
                    )

                    if change_percent > threshold:
                        alerts.append(
                            {
                                "ticker": ticker,
                                "change_percent": stock_data.price_info.change_percent,
                                "current_price": stock_data.price_info.current_price,
                                "alert_type": "significant_move",
                            }
                        )

                    monitoring_data[ticker] = {
                        "price": stock_data.price_info.current_price,
                        "change_percent": stock_data.price_info.change_percent,
                        "timestamp": datetime.now(),
                    }

                except Exception as e:
                    print(f"⚠️ Error monitoring {ticker}: {e}")
                    continue

            return {
                "monitoring_data": monitoring_data,
                "alerts": alerts,
                "monitored_count": len(monitoring_data),
                "alert_count": len(alerts),
            }

        except Exception as e:
            print(f"❌ Error in monitoring: {e}")
            return {"error": str(e)}
        finally:
            await self.browser_agent.close()


# Convenience function for CLI usage
async def analyze_stocks_cli(tickers: List[str], **kwargs) -> AnalysisReport:
    """CLI convenience function"""
    agent = StockAnalysisAgent()

    request = StockRequest(
        tickers=tickers,
        date_range=kwargs.get("date_range"),
        include_news=kwargs.get("include_news", True),
    )

    return await agent.analyze_stocks(request)
