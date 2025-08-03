"""
LLM Integration with Ollama for Stock Analysis
"""

import json
import ollama
from typing import List, Dict, Any
from loguru import logger

from .config import settings
from .models import StockData, NewsItem, AnalysisReport


class StockAnalysisLLM:
    """LLM service for stock analysis and report generation"""

    def __init__(self):
        self.model = "deepseek-r1:8b"  # Use deepseek-r1:8b for detailed analysis
        self.base_url = settings.ollama_base_url

        # System prompt that provides context and guidelines for all stock analysis tasks
        self.system_prompt = """
You are a financial analysis assistant.  
Your role is to take structured data about a stock (fundamentals, news, Reddit sentiment) and generate a detailed, professional financial report.

Rules:
1. Always respond in Markdown (.md) format, with proper headings, bullet points, and tables where relevant.
2. Organize the report into sections:
   - Fundamentals Overview – Key metrics in a table.
   - Latest News Summary – Bullet points summarizing top 5 news items.
   - Reddit Sentiment Analysis – Key insights from discussions.
   - Overall Market Outlook – Concise summary at the end.
3. Do not invent data – only use the provided inputs in <fundamentals>, <news>, and <reddit_sentiment>.
4. Use a professional and neutral tone. Avoid speculation.
5. Provide a final summary at the end.
6. Output only the Markdown content, with no extra explanations or text outside of the report.
"""



    async def generate_insights(
        self, stock_data: StockData, store_prompts_in: Dict[str, str] = None
    ) -> List[str]:
        """Generate analytical insights for a stock"""
        try:
            # Format stock data for analysis
            fundamentals_data = self._format_fundamentals_for_llm(stock_data)
            news_data = self._format_news_for_llm(stock_data)
            reddit_data = self._format_reddit_for_llm(stock_data)

            user_prompt = f"""Create a detailed financial report and send me the response in a Markdown format.

<fundamentals>
{fundamentals_data}
</fundamentals>

<news>
{news_data}
</news>

<reddit_sentiment>
{reddit_data}
</reddit_sentiment>"""

            # Store prompt if requested
            if store_prompts_in is not None:
                store_prompts_in[f"insights_{stock_data.ticker}"] = user_prompt

            response_text = await self._generate_response(user_prompt)
            
            # Since the response is now a complete markdown report, 
            # we'll return it as a single insight
            return [response_text] if response_text else []

        except Exception as e:
            logger.error(f"Error generating insights for {stock_data.ticker}: {e}")
            return [f"Unable to generate insights for {stock_data.ticker}."]

    def _format_fundamentals_for_llm(self, stock_data: StockData) -> str:
        """Format fundamental data in structured format"""
        fundamentals = stock_data.fundamentals
        
        data_parts = [
            f"Ticker: {stock_data.ticker}",
            f"Company: {stock_data.company_name}",
            f"Current Price: ${stock_data.price_info.current_price:.2f}",
            f"Change: {stock_data.price_info.change:+.2f} ({stock_data.price_info.change_percent:+.2f}%)",
        ]
        
        if fundamentals.pe_ratio:
            data_parts.append(f"P/E Ratio: {fundamentals.pe_ratio:.2f}")
        if fundamentals.market_cap:
            data_parts.append(f"Market Cap: ${fundamentals.market_cap:,.0f}")
        if fundamentals.volume:
            data_parts.append(f"Volume: {fundamentals.volume:,}")
        if fundamentals.avg_volume:
            data_parts.append(f"Avg Volume: {fundamentals.avg_volume:,}")
        if fundamentals.beta:
            data_parts.append(f"Beta: {fundamentals.beta:.2f}")
        if fundamentals.previous_close:
            data_parts.append(f"Previous Close: ${fundamentals.previous_close:.2f}")
        if fundamentals.open:
            data_parts.append(f"Open: ${fundamentals.open:.2f}")
        if fundamentals.days_range:
            data_parts.append(f"Day's Range: {fundamentals.days_range}")
        if fundamentals.fifty_two_week_range:
            data_parts.append(f"52-Week Range: ${fundamentals.fifty_two_week_range.low:.2f} - ${fundamentals.fifty_two_week_range.high:.2f}")
        if fundamentals.target_est:
            data_parts.append(f"1y Target Est: ${fundamentals.target_est:.2f}")
        if fundamentals.earnings_date:
            data_parts.append(f"Earnings Date: {fundamentals.earnings_date}")
        
        return "\n".join(data_parts)

    def _format_news_for_llm(self, stock_data: StockData) -> str:
        """Format news data in structured format"""
        if not stock_data.news:
            return "No recent news available"
        
        news_parts = []
        for i, news_item in enumerate(stock_data.news[:5], 1):
            news_parts.append(f"{i}. Title: {news_item.title}")
            news_parts.append(f"   Source: {news_item.source}")
            news_parts.append(f"   Date: {news_item.published_date.strftime('%Y-%m-%d')}")
            news_parts.append(f"   URL: {news_item.url}")
            news_parts.append("")
        
        return "\n".join(news_parts)

    def _format_reddit_for_llm(self, stock_data: StockData) -> str:
        """Format Reddit sentiment data in structured format"""
        if not stock_data.reddit_sentiment:
            return "No Reddit sentiment data available"
            
        reddit = stock_data.reddit_sentiment
        
        data_parts = [
            f"Overall Sentiment: {reddit.overall_sentiment.title()}",
            f"Confidence Score: {reddit.confidence_score:.2f}/1.0",
            f"Posts Analyzed: {reddit.posts_analyzed}",
            f"Summary: {reddit.sentiment_summary}"
        ]
        
        if reddit.key_discussions:
            data_parts.append("Key Discussion Points:")
            for i, point in enumerate(reddit.key_discussions[:5], 1):
                data_parts.append(f"  {i}. {point}")
                
        data_parts.append(f"Analysis Timestamp: {reddit.screenshot_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(data_parts)




    def _format_stock_data_for_llm(self, stock_data: StockData) -> str:
        """Format stock data into a readable text format for LLM processing"""

        # Basic info
        info = [
            f"Stock: {stock_data.ticker} ({stock_data.company_name})",
            f"Current Price: ${stock_data.price_info.current_price:.2f}",
            f"Change: {stock_data.price_info.change:+.2f} ({stock_data.price_info.change_percent:+.2f}%)",
        ]

        # Fundamental metrics
        fundamentals = stock_data.fundamentals
        if fundamentals.pe_ratio:
            info.append(f"P/E Ratio: {fundamentals.pe_ratio:.2f}")
        if fundamentals.roe:
            info.append(f"ROE: {fundamentals.roe:.2f}%")
        if fundamentals.dividend_yield:
            info.append(f"Dividend Yield: {fundamentals.dividend_yield:.2f}%")
        if fundamentals.market_cap:
            info.append(f"Market Cap: ${fundamentals.market_cap:,.0f}")
        if fundamentals.volume:
            info.append(f"Volume: {fundamentals.volume:,}")
        if fundamentals.fifty_two_week_range:
            info.append(
                f"52-Week Range: ${fundamentals.fifty_two_week_range.low:.2f} - ${fundamentals.fifty_two_week_range.high:.2f}"
            )

        # News count
        if stock_data.news:
            info.append(f"Recent News Articles: {len(stock_data.news)}")

        return "\n".join(info)

    async def _generate_response(self, user_prompt: str) -> str:
        """Generate response from Ollama LLM using direct client"""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )
            return response["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return "Unable to generate analysis."


class NewsAnalyzer:
    """Specialized analyzer for news sentiment and content"""

    def __init__(self):
        self.model = "deepseek-r1:8b"  # Use deepseek-r1:8b for sophisticated news sentiment analysis

        self.sentiment_system_prompt = """
You are a financial news sentiment analyst with expertise in interpreting how news events impact stock prices and investor sentiment. Your task is to analyze news headlines and content to determine their likely impact on stock performance.

SENTIMENT CLASSIFICATION:
- POSITIVE: News likely to drive stock price up (earnings beats, new partnerships, positive guidance, analyst upgrades, breakthrough products, regulatory approvals)
- NEGATIVE: News likely to drive stock price down (earnings misses, lawsuits, regulatory issues, analyst downgrades, management departures, competitive threats)
- NEUTRAL: News with unclear or minimal stock price impact (routine announcements, mixed signals, general industry news)

ANALYSIS FACTORS:
1. Direct Financial Impact: Does this news directly affect revenues, costs, or profitability?
2. Market Perception: How are investors likely to react regardless of fundamentals?
3. Timing Sensitivity: Is this news about immediate or future events?
4. Magnitude: How significant is this development for the company?
5. Market Context: How does this fit into current market themes and investor concerns?

CONFIDENCE SCORING (0.0 to 1.0):
- 0.8-1.0: Very clear positive/negative impact with strong precedent
- 0.6-0.7: Likely impact based on typical market reactions
- 0.4-0.5: Uncertain impact, mixed signals or insufficient information
- 0.1-0.3: Minimal expected impact on stock price

Always provide specific reasoning based on the headline content and financial implications.
"""

    async def analyze_sentiment(self, news_items: List[NewsItem]) -> Dict[str, Any]:
        """Analyze sentiment of news articles"""
        if not news_items:
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "reasoning": "No news available",
            }

        try:
            # Create prompt for sentiment analysis
            news_titles = "\n".join([f"- {item.title}" for item in news_items])

            user_prompt = f"""
Analyze the sentiment of these news headlines for their likely impact on stock price.

Headlines:
{news_titles}

Based on your analysis, provide:
1. Overall sentiment classification (positive, negative, or neutral)
2. Confidence score (0.0 to 1.0) - how certain you are about the sentiment
3. Brief reasoning explaining your classification and confidence level
4. Key factors that influenced your decision

Respond in JSON format:
{{"sentiment": "positive|negative|neutral", "confidence": 0.0-1.0, "reasoning": "detailed explanation", "key_factors": ["factor1", "factor2", "factor3"]}}
"""

            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.sentiment_system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )

            response_text = response["message"]["content"].strip()

            # Try to parse JSON response
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "sentiment": "neutral",
                    "confidence": 0.5,
                    "reasoning": "Unable to parse sentiment analysis",
                }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "reasoning": "Error in sentiment analysis",
            }
