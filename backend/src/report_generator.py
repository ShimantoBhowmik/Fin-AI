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
    """Generate formatted reports from analysis data"""

    def __init__(self):
        self.reports_dir = settings.reports_dir

        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)

    async def generate_report(self, analysis_report: AnalysisReport) -> str:
        """Generate a comprehensive analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tickers_str = "_".join(analysis_report.request.tickers)

        # Generate different format reports
        markdown_path = await self._generate_markdown_report(
            analysis_report, timestamp, tickers_str
        )
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
        """Generate a Markdown report"""

        markdown_template = """# Stock Analysis Report
        
**Generated:** {{generated_at}}  
**Tickers:** {{tickers}}  
**Analysis Date:** {{analysis_date}}

## Executive Summary

{{summary}}

## Individual Stock Analysis

{% for stock in stocks_data %}
### {{stock.ticker}} - {{stock.company_name}}

**Current Price:** ${{stock.price_info.current_price}} ({{stock.price_info.change_percent|round(2)}}%)  
**Last Updated:** {{stock.price_info.last_updated.strftime('%Y-%m-%d %H:%M')}}

#### Fundamental Metrics
{% if stock.fundamentals.pe_ratio %}
- **P/E Ratio:** {{stock.fundamentals.pe_ratio|round(2)}}
{% endif %}
{% if stock.fundamentals.roe %}
- **ROE:** {{stock.fundamentals.roe|round(2)}}%
{% endif %}
{% if stock.fundamentals.dividend_yield %}
- **Dividend Yield:** {{stock.fundamentals.dividend_yield|round(2)}}%
{% endif %}
{% if stock.fundamentals.market_cap %}
- **Market Cap:** ${{"{:,.0f}".format(stock.fundamentals.market_cap)}}
{% endif %}
{% if stock.fundamentals.volume %}
- **Volume:** {{"{:,}".format(stock.fundamentals.volume)}}
{% endif %}
{% if stock.fundamentals.fifty_two_week_range %}
- **52-Week Range:** ${{stock.fundamentals.fifty_two_week_range.low}} - ${{stock.fundamentals.fifty_two_week_range.high}}
{% endif %}

#### Key Insights
{% for insight in stock.insights %}
- {{insight}}
{% endfor %}

{% if stock.news_summary %}
#### News Summary
{{stock.news_summary}}
{% endif %}

{% if stock.reddit_sentiment %}
#### Reddit Sentiment Analysis
**Overall Sentiment:** {{stock.reddit_sentiment.overall_sentiment.title()}} (Confidence: {{(stock.reddit_sentiment.confidence_score * 100)|round(1)}}%)  
**Posts Analyzed:** {{stock.reddit_sentiment.posts_analyzed}}  
**Summary:** {{stock.reddit_sentiment.sentiment_summary}}

{% if stock.reddit_sentiment.key_discussions %}
**Key Discussion Points:** {{stock.reddit_sentiment.key_discussions|join(', ')}}
{% endif %}
{% endif %}

{% if stock.news %}
#### Recent News ({{stock.news|length}} articles)
{% for news_item in stock.news[:5] %}
- **{{news_item.title}}** - {{news_item.source}} ({{news_item.published_date.strftime('%Y-%m-%d')}})
{% endfor %}
{% endif %}

---
{% endfor %}

{% if comparative_analysis %}
## Comparative Analysis

### Performance Ranking
{% if comparative_analysis.performance.ranked_by_daily_change %}
{% for stock in comparative_analysis.performance.ranked_by_daily_change %}
{{loop.index}}. **{{stock.ticker}}**: {{stock.price_change_percent|round(2)}}%
{% endfor %}
{% endif %}

### Valuation Comparison
{% if comparative_analysis.valuation.ranked_by_pe %}
**P/E Ratios (Low to High):**
{% for stock in comparative_analysis.valuation.ranked_by_pe %}
- **{{stock.ticker}}**: {{stock.pe_ratio|round(2)}}
{% endfor %}
{% endif %}

{% if comparative_analysis.fundamentals.ranked_by_dividend_yield %}
**Dividend Yields (High to Low):**
{% for stock in comparative_analysis.fundamentals.ranked_by_dividend_yield %}
- **{{stock.ticker}}**: {{stock.dividend_yield|round(2)}}%
{% endfor %}
{% endif %}
{% endif %}

{% if portfolio_metrics %}
## Portfolio Analysis

- **Total Stocks:** {{portfolio_metrics.number_of_stocks}}
- **Weighted Daily Return:** {{portfolio_metrics.weighted_daily_return|round(2)}}%
{% if portfolio_metrics.average_pe_ratio %}
- **Average P/E Ratio:** {{portfolio_metrics.average_pe_ratio|round(2)}}
{% endif %}
{% if portfolio_metrics.weighted_dividend_yield %}
- **Weighted Dividend Yield:** {{portfolio_metrics.weighted_dividend_yield|round(2)}}%
{% endif %}

### Risk Metrics
- **High P/E Stocks (>25):** {{portfolio_metrics.risk_metrics.high_pe_stocks}}
- **Dividend Paying Stocks:** {{portfolio_metrics.risk_metrics.dividend_paying_stocks}}
- **Negative Performers:** {{portfolio_metrics.risk_metrics.negative_performers}}
{% endif %}

## Key Insights Summary

{% for insight in insights %}
- {{insight}}
{% endfor %}

{% if system_prompts_used or any_llm_prompts %}
## AI Analysis Transparency

### System Prompts Used

{% for prompt_name, prompt_content in system_prompts_used.items() %}
#### {{prompt_name.replace('_', ' ').title()}}
```
{{prompt_content}}
```

{% endfor %}

### LLM Prompts Used for Individual Stocks

{% for stock in stocks_data %}
{% if stock.llm_prompts_used %}
#### {{stock.ticker}} - LLM Prompts
{% for prompt_name, prompt_content in stock.llm_prompts_used.items() %}
**{{prompt_name.replace('_', ' ').title()}}:**
```
{{prompt_content}}
```

{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

---
*Report generated by Stock Analysis Agent*  
*Powered by Browserbase, Stagehand, and Ollama*
"""

        template = Template(markdown_template)

        # Prepare template data
        template_data = {
            "generated_at": report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "tickers": ", ".join(report.request.tickers),
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "summary": report.summary,
            "stocks_data": report.stocks_data,
            "insights": report.insights,
            "comparative_analysis": getattr(report, "comparative_analysis", {}),
            "portfolio_metrics": getattr(report, "portfolio_metrics", {}),
            "system_prompts_used": getattr(report, "system_prompts_used", {}),
            "any_llm_prompts": any(
                getattr(stock, "llm_prompts_used", {}) for stock in report.stocks_data
            ),
        }

        # Render the template
        markdown_content = template.render(**template_data)

        # Save to file
        filename = f"stock_analysis_{tickers_str}_{timestamp}.md"
        file_path = self.reports_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return file_path

    async def _generate_json_report(
        self, report: AnalysisReport, timestamp: str, tickers_str: str
    ) -> Path:
        """Generate a JSON report for programmatic access"""

        # Convert report to dict, handling datetime serialization
        report_dict = self._serialize_report_data(report)

        filename = f"stock_analysis_{tickers_str}_{timestamp}.json"
        file_path = self.reports_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return file_path

    def _serialize_report_data(self, report: AnalysisReport) -> Dict[str, Any]:
        """Convert report to JSON-serializable format"""

        def serialize_datetime(obj, seen=None):
            if seen is None:
                seen = set()

            # Prevent infinite recursion by tracking object IDs
            obj_id = id(obj)
            if obj_id in seen:
                return "<circular reference>"

            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, BaseModel):
                seen.add(obj_id)
                try:
                    result = {
                        k: serialize_datetime(v, seen)
                        for k, v in obj.model_dump().items()
                    }
                    seen.remove(obj_id)
                    return result
                except:
                    seen.discard(obj_id)
                    return str(obj)
            elif hasattr(obj, "__dict__") and not isinstance(
                obj, (str, int, float, bool, type(None))
            ):
                seen.add(obj_id)
                try:
                    result = {
                        k: serialize_datetime(v, seen)
                        for k, v in obj.__dict__.items()
                        if not k.startswith("_")
                    }
                    seen.remove(obj_id)
                    return result
                except:
                    seen.discard(obj_id)
                    return str(obj)
            elif isinstance(obj, list):
                return [serialize_datetime(item, seen) for item in obj]
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v, seen) for k, v in obj.items()}
            else:
                return obj

        try:
            return serialize_datetime(report)
        except Exception as e:
            print(f"Error serializing report data: {e}")
            # Fallback to basic serialization
            return {
                "ticker": getattr(report, "request", {}).get("tickers", []),
                "summary": getattr(report, "summary", ""),
                "insights": getattr(report, "insights", []),
                "generated_at": (
                    report.generated_at.isoformat()
                    if hasattr(report, "generated_at")
                    else datetime.now().isoformat()
                ),
                "error": "Serialization failed, using minimal data",
            }



    

    async def _create_performance_chart(
        self, stocks_data: List[StockData], timestamp: str, tickers_str: str
    ):
        """Create performance summary chart"""

        # Create a summary metrics chart
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle("Stock Analysis Summary", fontsize=16)

        tickers = [stock.ticker for stock in stocks_data]

        # 1. Price changes
        changes = [stock.price_info.change_percent for stock in stocks_data]
        colors = ["green" if c >= 0 else "red" for c in changes]
        ax1.bar(tickers, changes, color=colors, alpha=0.7)
        ax1.set_title("Daily Price Changes (%)")
        ax1.set_ylabel("Change (%)")
        ax1.tick_params(axis="x", rotation=45)
        ax1.axhline(y=0, color="black", linestyle="-", alpha=0.3)

        # 2. Market Cap (if available)
        market_caps = [
            stock.fundamentals.market_cap / 1e9 if stock.fundamentals.market_cap else 0
            for stock in stocks_data
        ]
        if any(cap > 0 for cap in market_caps):
            ax2.bar(tickers, market_caps, color="skyblue", alpha=0.7)
            ax2.set_title("Market Cap (Billions $)")
            ax2.set_ylabel("Market Cap ($B)")
            ax2.tick_params(axis="x", rotation=45)
        else:
            ax2.text(
                0.5,
                0.5,
                "Market Cap Data\nNot Available",
                ha="center",
                va="center",
                transform=ax2.transAxes,
            )
            ax2.set_title("Market Cap (Billions $)")

        # 3. P/E Ratios (if available)
        pe_ratios = [
            stock.fundamentals.pe_ratio if stock.fundamentals.pe_ratio else 0
            for stock in stocks_data
        ]
        if any(pe > 0 for pe in pe_ratios):
            ax3.bar(tickers, pe_ratios, color="lightcoral", alpha=0.7)
            ax3.set_title("P/E Ratios")
            ax3.set_ylabel("P/E Ratio")
            ax3.tick_params(axis="x", rotation=45)
        else:
            ax3.text(
                0.5,
                0.5,
                "P/E Ratio Data\nNot Available",
                ha="center",
                va="center",
                transform=ax3.transAxes,
            )
            ax3.set_title("P/E Ratios")

        # 4. Dividend Yields (if available)
        dividend_yields = [
            (
                stock.fundamentals.dividend_yield
                if stock.fundamentals.dividend_yield
                else 0
            )
            for stock in stocks_data
        ]
        if any(div > 0 for div in dividend_yields):
            ax4.bar(tickers, dividend_yields, color="lightgreen", alpha=0.7)
            ax4.set_title("Dividend Yields (%)")
            ax4.set_ylabel("Dividend Yield (%)")
            ax4.tick_params(axis="x", rotation=45)
        else:
            ax4.text(
                0.5,
                0.5,
                "Dividend Yield Data\nNot Available",
                ha="center",
                va="center",
                transform=ax4.transAxes,
            )
            ax4.set_title("Dividend Yields (%)")

        plt.tight_layout()

        filename = f"performance_summary_{tickers_str}_{timestamp}.png"
        filepath = self.charts_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"📈 Performance summary chart saved: {filepath}")

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

        if stock_data.reddit_sentiment:
            sentiment = stock_data.reddit_sentiment.overall_sentiment.title()
            confidence = stock_data.reddit_sentiment.confidence_score * 100
            summary_parts.append(f"Reddit: {sentiment} ({confidence:.0f}%)")

        return " | ".join(summary_parts)
