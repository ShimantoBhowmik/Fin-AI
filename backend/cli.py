"""
Command Line Interface for Stock Analysis Agent
"""

import asyncio
import click
from typing import List
from pathlib import Path

from src.main_agent import StockAnalysisAgent, analyze_stocks_cli
from src.models import StockRequest, MetricType
from src.config import settings


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Stock Analysis Agent - AI-powered stock analysis using browser automation"""
    pass


@cli.command()
@click.argument("tickers", nargs=-1, required=True)
@click.option(
    "--date-range",
    "-d",
    default="1y",
    help="Date range for analysis (1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y)",
)
@click.option("--no-news", is_flag=True, help="Skip news analysis")
@click.option("--no-reddit", is_flag=True, help="Skip Reddit sentiment analysis")
@click.option("--no-charts", is_flag=True, help="Skip chart screenshots")
@click.option(
    "--metrics",
    "-m",
    multiple=True,
    type=click.Choice([m.value for m in MetricType]),
    help="Specific metrics to analyze",
)
@click.option(
    "--output-dir", "-o", type=click.Path(), help="Output directory for reports"
)
def analyze(tickers, date_range, no_news, no_reddit, no_charts, metrics, output_dir):
    """Analyze one or more stocks

    Examples:

        # Analyze Apple stock
        python cli.py analyze AAPL

        # Analyze multiple stocks with custom date range
        python cli.py analyze AAPL MSFT GOOGL -d 6m

        # Analyze with specific metrics only
        python cli.py analyze TSLA -m price -m pe_ratio -m dividend_yield

        # Quick analysis without news or charts
        python cli.py analyze NVDA --no-news --no-charts
    """

    async def run_analysis():
        try:
            # Validate tickers
            tickers_list = [ticker.upper() for ticker in tickers]
            click.echo(f"🚀 Starting analysis for: {', '.join(tickers_list)}")

            # Set output directory if provided
            if output_dir:
                settings.reports_dir = Path(output_dir)

            # Create request
            request = StockRequest(
                tickers=tickers_list,
                date_range=date_range,
                include_news=not no_news,
                include_reddit=not no_reddit,
                metrics=(
                    [MetricType(m) for m in metrics]
                    if metrics
                    else [MetricType.PRICE, MetricType.PE_RATIO]
                ),
            )

            # Run analysis
            agent = StockAnalysisAgent()
            report = await agent.analyze_stocks(request)

            click.echo(f"\nAnalysis complete!")
            click.echo(f"Report saved to: {report.report_path}")

            # Print quick summary
            click.echo(f"\n📈 Quick Summary:")
            for stock in report.stocks_data:
                price_info = stock.price_info
                click.echo(
                    f"  {stock.ticker}: ${price_info.current_price:.2f} ({price_info.change_percent:+.2f}%)"
                )

        except Exception as e:
            click.echo(f"❌ Error: {e}")
            raise click.ClickException(str(e))

    asyncio.run(run_analysis())


@cli.command()
@click.argument("ticker")
def quick(ticker):
    """Quick analysis of a single stock

    Example:
        python cli.py quick AAPL
    """

    async def run_quick_analysis():
        try:
            click.echo(f"⚡ Quick analysis for {ticker.upper()}")

            agent = StockAnalysisAgent()
            result = await agent.quick_analysis(ticker.upper())

            if "error" in result:
                click.echo(f"❌ Error: {result['error']}")
                return

            # Display results
            click.echo(f"\n📊 {result['ticker']} Summary:")
            click.echo(
                f"  💰 Price: ${result['current_price']:.2f} ({result['change_percent']:+.2f}%)"
            )

            if result.get("pe_ratio"):
                click.echo(f"  📈 P/E Ratio: {result['pe_ratio']:.2f}")

            if result.get("market_cap"):
                cap_b = result["market_cap"] / 1e9
                click.echo(f"  🏢 Market Cap: ${cap_b:.1f}B")

            click.echo(f"  📰 News Articles: {result['news_count']}")

            # Show Reddit sentiment if available
            if result.get("reddit_sentiment"):
                sentiment = result["reddit_sentiment"]
                emoji = (
                    "🚀"
                    if sentiment["sentiment"] == "bullish"
                    else "📉" if sentiment["sentiment"] == "bearish" else "😐"
                )
                click.echo(
                    f"  {emoji} Reddit Sentiment: {sentiment['sentiment'].title()} ({sentiment['confidence']*100:.0f}% confidence)"
                )

            # Show top insights
            if result.get("insights"):
                click.echo(f"\n🧠 Key Insights:")
                for i, insight in enumerate(result["insights"][:3], 1):
                    click.echo(f"  {i}. {insight}")

        except Exception as e:
            click.echo(f"❌ Error: {e}")
            raise click.ClickException(str(e))

    asyncio.run(run_quick_analysis())


@cli.command()
@click.argument("tickers", nargs=-1, required=True)
@click.option(
    "--threshold",
    "-t",
    type=float,
    default=5.0,
    help="Alert threshold for price changes (%)",
)
@click.option(
    "--interval", "-i", type=int, default=300, help="Monitoring interval in seconds"
)
def monitor(tickers, threshold, interval):
    """Monitor stocks for significant changes

    Example:
        python cli.py monitor AAPL TSLA MSFT -t 3.0
    """

    async def run_monitoring():
        try:
            tickers_list = [ticker.upper() for ticker in tickers]
            alert_thresholds = {ticker: threshold for ticker in tickers_list}

            click.echo(
                f"👁️ Monitoring {len(tickers_list)} stocks (threshold: {threshold}%)"
            )
            click.echo(f"Tickers: {', '.join(tickers_list)}")
            click.echo("Press Ctrl+C to stop monitoring\n")

            agent = StockAnalysisAgent()

            while True:
                try:
                    result = await agent.monitor_stocks(tickers_list, alert_thresholds)

                    if "error" in result:
                        click.echo(f"❌ Monitoring error: {result['error']}")
                        break

                    # Display current status
                    timestamp = result["monitoring_data"][
                        list(result["monitoring_data"].keys())[0]
                    ]["timestamp"]
                    click.echo(f"📊 Update at {timestamp.strftime('%H:%M:%S')}:")

                    for ticker, data in result["monitoring_data"].items():
                        status_emoji = "📈" if data["change_percent"] >= 0 else "📉"
                        click.echo(
                            f"  {status_emoji} {ticker}: ${data['price']:.2f} ({data['change_percent']:+.2f}%)"
                        )

                    # Display alerts
                    if result["alerts"]:
                        click.echo(f"\n🚨 ALERTS ({len(result['alerts'])}):")
                        for alert in result["alerts"]:
                            click.echo(
                                f"  ⚠️ {alert['ticker']}: {alert['change_percent']:+.2f}% (${alert['current_price']:.2f})"
                            )

                    click.echo(f"Next update in {interval} seconds...\n")
                    await asyncio.sleep(interval)

                except KeyboardInterrupt:
                    click.echo("\n👋 Monitoring stopped by user")
                    break

        except Exception as e:
            click.echo(f"❌ Error: {e}")
            raise click.ClickException(str(e))

    asyncio.run(run_monitoring())


@cli.command()
def config():
    """Show current configuration"""

    click.echo("🔧 Stock Analysis Agent Configuration:")
    click.echo(f"  📁 Reports Directory: {settings.reports_dir}")
    click.echo(f"  🤖 Ollama URL: {settings.ollama_base_url}")
    click.echo(f"  🧠 Ollama Model: {settings.ollama_model}")
    click.echo(
        f"  🌐 Browserbase API Key: {'Set' if settings.browserbase_api_key else 'Not Set'}"
    )
    click.echo(f"  📊 Yahoo Finance URL: {settings.yahoo_finance_base_url}")


@cli.command()
def setup():
    """Setup and test the environment"""

    async def run_setup():
        click.echo("🔧 Setting up Stock Analysis Agent...")

        # Check directories
        click.echo(f"📁 Creating directories...")
        settings.reports_dir.mkdir(exist_ok=True)
        settings.temp_dir.mkdir(exist_ok=True)
        settings.logs_dir.mkdir(exist_ok=True)
        click.echo("✅ Directories created")

        # Test Ollama connection
        click.echo(f"🧠 Testing Ollama connection ({settings.ollama_base_url})...")
        try:
            from src.llm_service import StockAnalysisLLM

            llm = StockAnalysisLLM()
            response = await llm._generate_response(
                "Hello, respond with 'Connection successful'"
            )
            if "successful" in response.lower():
                click.echo("✅ Ollama connection successful")
            else:
                click.echo("⚠️ Ollama responded but may not be working correctly")
        except Exception as e:
            click.echo(f"❌ Ollama connection failed: {e}")
            click.echo("Please ensure Ollama is running: 'ollama serve'")

        # Test browser capabilities (without Browserbase for now)
        click.echo("🌐 Browser capabilities check:")
        if settings.browserbase_api_key:
            click.echo("✅ Browserbase API key configured")
        else:
            click.echo("⚠️ Browserbase API key not set")
            click.echo("Please set BROWSERBASE_API_KEY in your .env file")

        click.echo("\n🚀 Setup complete! Try: python cli.py quick AAPL")

    asyncio.run(run_setup())


if __name__ == "__main__":
    cli()
