"""
Report generation module for creating formatted analysis reports
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template
from pydantic import BaseModel

from .config import settings
from .models import AnalysisReport, StockData


class ReportGenerator:
    """Generates analysis reports in various formats"""

    def __init__(self):
        self.reports_dir = settings.reports_dir

        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)

    async def generate_report(self, analysis_report: AnalysisReport) -> str:
        """Generate a comprehensive analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tickers_str = "_".join([stock.ticker for stock in analysis_report.stocks_data])

        # Generate markdown report
        markdown_path = await self._generate_markdown_report(
            analysis_report, timestamp, tickers_str
        )

        # Generate JSON report
        json_path = await self._generate_json_report(
            analysis_report, timestamp, tickers_str
        )

        print(f"📊 Reports generated:")
        print(f"  - Markdown: {markdown_path}")
        print(f"  - JSON: {json_path}")

        return str(markdown_path)

    async def _generate_markdown_report(
        self, report: AnalysisReport, timestamp: str, tickers_str: str
    ) -> Path:
        """Generate a markdown report"""

        # Create the markdown content
        content = []
        content.append(f"# Stock Analysis Report")
        content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Request ID:** {report.request_id}")
        content.append("")

        # Executive summary
        if report.summary:
            content.append("## Executive Summary")
            content.append(report.summary)
            content.append("")

        # Individual stock analysis
        content.append("## Stock Analysis")
        for stock_data in report.stocks_data:
            content.append(f"### {stock_data.ticker} - {stock_data.company_name}")
            content.append("")

            # Price information
            content.append("#### Price Information")
            price_info = stock_data.price_info
            content.append(f"- **Current Price:** ${price_info.current_price:.2f}")
            content.append(f"- **Change:** {price_info.change:+.2f} ({price_info.change_percent:+.2f}%)")
            content.append(f"- **Currency:** {price_info.currency}")
            content.append("")

            # Fundamental metrics
            content.append("#### Fundamentals")
            fundamentals = stock_data.fundamentals
            
            if fundamentals.previous_close:
                content.append(f"- **Previous Close:** ${fundamentals.previous_close:.2f}")
            if fundamentals.open:
                content.append(f"- **Open:** ${fundamentals.open:.2f}")
            if fundamentals.days_range:
                content.append(f"- **Day's Range:** {fundamentals.days_range}")
            if fundamentals.volume:
                content.append(f"- **Volume:** {fundamentals.volume:,}")
            if fundamentals.avg_volume:
                content.append(f"- **Avg Volume:** {fundamentals.avg_volume:,}")
            if fundamentals.market_cap:
                content.append(f"- **Market Cap:** ${fundamentals.market_cap:,.0f}")
            if fundamentals.beta:
                content.append(f"- **Beta:** {fundamentals.beta:.2f}")
            if fundamentals.pe_ratio:
                content.append(f"- **P/E Ratio:** {fundamentals.pe_ratio:.2f}")
            if fundamentals.target_est:
                content.append(f"- **1y Target Est:** ${fundamentals.target_est:.2f}")
            if fundamentals.earnings_date:
                content.append(f"- **Earnings Date:** {fundamentals.earnings_date}")
            if fundamentals.fifty_two_week_range:
                range_data = fundamentals.fifty_two_week_range
                content.append(f"- **52-Week Range:** ${range_data.low:.2f} - ${range_data.high:.2f}")
            content.append("")

            # News
            if stock_data.news:
                content.append("#### Recent News")
                for i, news_item in enumerate(stock_data.news[:5], 1):
                    content.append(f"{i}. **{news_item.title}**")
                    content.append(f"   - Source: {news_item.source}")
                    content.append(f"   - Date: {news_item.published_date.strftime('%Y-%m-%d')}")
                    content.append(f"   - URL: {news_item.url}")
                    content.append("")

            # LLM Insights
            if stock_data.insights:
                content.append("#### Analysis Insights")
                for insight in stock_data.insights:
                    content.append(f"- {insight}")
                content.append("")

        # Technical summary
        if len(report.stocks_data) > 1:
            content.append("## Comparative Analysis")
            content.append("| Ticker | Price | Change % | P/E | Market Cap |")
            content.append("|--------|-------|----------|-----|------------|")
            
            for stock in report.stocks_data:
                price = f"${stock.price_info.current_price:.2f}"
                change = f"{stock.price_info.change_percent:+.2f}%"
                pe = f"{stock.fundamentals.pe_ratio:.1f}" if stock.fundamentals.pe_ratio else "N/A"
                market_cap = f"${stock.fundamentals.market_cap/1e9:.1f}B" if stock.fundamentals.market_cap else "N/A"
                content.append(f"| {stock.ticker} | {price} | {change} | {pe} | {market_cap} |")
            content.append("")

        # Analysis metadata
        content.append("## Analysis Metadata")
        content.append(f"- **Analysis Timestamp:** {report.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"- **Duration:** {report.analysis_duration:.2f} seconds")
        content.append("")

        # Save the markdown file
        markdown_content = "\n".join(content)
        filename = f"stock_analysis_{tickers_str}_{timestamp}.md"
        filepath = self.reports_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return filepath

    async def _generate_json_report(
        self, report: AnalysisReport, timestamp: str, tickers_str: str
    ) -> Path:
        """Generate a JSON report"""

        # Serialize the report data
        report_data = self._serialize_report_data(report)

        # Save the JSON file
        filename = f"stock_analysis_{tickers_str}_{timestamp}.json"
        filepath = self.reports_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        return filepath

    def _serialize_report_data(self, report: AnalysisReport) -> Dict[str, Any]:
        """Serialize report data for JSON output"""
        try:
            return {
                "request_id": report.request_id,
                "summary": report.summary,
                "analysis_timestamp": report.analysis_timestamp.isoformat(),
                "analysis_duration": report.analysis_duration,
                "stocks_data": [
                    {
                        "ticker": stock.ticker,
                        "company_name": stock.company_name,
                        "price_info": {
                            "current_price": stock.price_info.current_price,
                            "change": stock.price_info.change,
                            "change_percent": stock.price_info.change_percent,
                            "currency": stock.price_info.currency,
                            "last_updated": stock.price_info.last_updated.isoformat(),
                        },
                        "fundamentals": {
                            "previous_close": stock.fundamentals.previous_close,
                            "open": stock.fundamentals.open,
                            "days_range": stock.fundamentals.days_range,
                            "volume": stock.fundamentals.volume,
                            "avg_volume": stock.fundamentals.avg_volume,
                            "market_cap": stock.fundamentals.market_cap,
                            "beta": stock.fundamentals.beta,
                            "pe_ratio": stock.fundamentals.pe_ratio,
                            "target_est": stock.fundamentals.target_est,
                            "earnings_date": stock.fundamentals.earnings_date,
                            "fifty_two_week_range": (
                                {
                                    "high": stock.fundamentals.fifty_two_week_range.high,
                                    "low": stock.fundamentals.fifty_two_week_range.low,
                                }
                                if stock.fundamentals.fifty_two_week_range
                                else None
                            ),
                        },
                        "news": [
                            {
                                "title": news.title,
                                "url": news.url,
                                "source": news.source,
                                "published_date": news.published_date.isoformat(),
                            }
                            for news in stock.news
                        ],
                        "insights": stock.insights or [],
                        "analysis_timestamp": stock.analysis_timestamp.isoformat(),
                    }
                    for stock in report.stocks_data
                ],
            }
        except Exception as e:
            print(f"⚠️ Error serializing report data: {e}")
            return {
                "request_id": report.request_id,
                "error": "Serialization failed, using minimal data",
            }

    def generate_quick_summary(self, stock_data: StockData) -> str:
        """Generate a quick text summary for a single stock"""

        summary_parts = [
            f"**{stock_data.ticker}** ({stock_data.company_name})",
            f"Price: ${stock_data.price_info.current_price:.2f} ({stock_data.price_info.change_percent:+.2f}%)",
        ]

        if stock_data.fundamentals.pe_ratio:
            summary_parts.append(f"P/E: {stock_data.fundamentals.pe_ratio:.2f}")

        if stock_data.fundamentals.market_cap:
            cap_b = stock_data.fundamentals.market_cap / 1e9
            summary_parts.append(f"Market Cap: ${cap_b:.1f}B")

        if stock_data.fundamentals.dividend_yield:
            summary_parts.append(
                f"Dividend: {stock_data.fundamentals.dividend_yield:.2f}%"
            )

        return " | ".join(summary_parts)
