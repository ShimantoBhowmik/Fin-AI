"""
FastAPI backend for stock analysis system
"""

import asyncio
import json
import re
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import ollama
from loguru import logger

from .config import settings
from .browser_agent import BrowserAgent
from .llm_service import StockAnalysisLLM
from .models import StockData


app = FastAPI(title="Stock Analysis API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    query: str


class StatusUpdate(BaseModel):
    step: str
    status: str
    message: str
    progress: float
    data: Optional[Dict[str, Any]] = None


class TickerExtractor:
    """Extract stock ticker from natural language query"""
    
    def __init__(self):
        self.model = "llama3:8b"  # Specifically use llama3:8b for ticker extraction
    
    async def extract_ticker(self, query: str) -> str:
        """Extract stock ticker from user query"""
        
        system_prompt = """
You are a financial assistant that extracts stock tickers from user queries.

Your task is to identify the stock ticker symbol from the user's question.

Rules:
1. Look for ticker symbols in the format $TICKER (e.g., $AAPL, $MSFT, $TSLA) - this is the primary format
2. Also extract standalone ticker symbols (e.g., AAPL, MSFT, TSLA)
3. If multiple tickers are mentioned, return the first one
4. Return ONLY the ticker symbol in uppercase, no other text, no $ sign
5. Common company name mappings:
   - Apple -> AAPL
   - Microsoft -> MSFT  
   - Tesla -> TSLA
   - Google/Alphabet -> GOOGL
   - Amazon -> AMZN
   - Meta/Facebook -> META
   - Netflix -> NFLX
   - Nvidia -> NVDA
6. If you cannot determine a ticker, return "UNKNOWN"

Examples:
- "Give me analysis for $AAPL" -> AAPL
- "Tell me about $AMZN stock" -> AMZN
- "Microsoft financial report" -> MSFT
- "How is $TSLA doing?" -> TSLA
- "Give me a detailed financial analysis report for AAPL" -> AAPL
- "What's the outlook for $NVDA?" -> NVDA
"""

        user_prompt = f"Extract the stock ticker from this query: '{query}'"
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            ticker = response["message"]["content"].strip().upper()
            logger.info(f"LLM response for ticker extraction: '{ticker}'")
            
            # Try to extract a valid ticker symbol from the response
            # First, look for $TICKER format in the original query
            dollar_ticker_match = re.search(r'\$([A-Z]{1,5})', query.upper())
            if dollar_ticker_match:
                extracted_ticker = dollar_ticker_match.group(1)
                logger.info(f"Found $TICKER format in query: {extracted_ticker}")
                return extracted_ticker
            
            # Then try ticker patterns in LLM response
            ticker_patterns = [
                r'\$([A-Z]{2,5})',        # $TICKER format
                r'\b([A-Z]{2,5})\b',      # 2-5 uppercase letters as word
                r'^([A-Z]{2,5})$',        # Entire response is ticker
                r'([A-Z]{2,5})',          # Any 2-5 uppercase letters
            ]
            
            for pattern in ticker_patterns:
                matches = re.findall(pattern, ticker)
                if matches:
                    # Filter out common words that aren't tickers
                    excluded_words = {'THE', 'AND', 'FOR', 'YOU', 'ARE', 'CAN', 'NOT', 'BUT', 'FROM', 'THIS', 'THAT', 'WITH', 'HAVE', 'WILL', 'YOUR', 'THEY', 'BEEN', 'THEIR', 'SAID', 'EACH', 'WHICH', 'THERE', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'USE', 'MAN', 'NEW', 'NOW', 'WAY', 'MAY', 'SAY'}
                    
                    for match in matches:
                        if match not in excluded_words and len(match) >= 2:
                            logger.info(f"Extracted ticker: {match}")
                            return match
            
            # If no pattern match, check if the entire response is UNKNOWN
            if ticker == "UNKNOWN":
                return None
                
            # Last resort: return the response if it looks like a ticker
            if len(ticker) >= 2 and len(ticker) <= 5 and ticker.isalpha():
                return ticker
            
            logger.warning(f"Could not extract valid ticker from: '{ticker}'")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting ticker: {e}")
            return None


class StockAnalysisService:
    """Main service for stock analysis with status updates"""
    
    def __init__(self):
        self.ticker_extractor = TickerExtractor()
        self.browser_agent = BrowserAgent()
        self.llm_service = StockAnalysisLLM()
    
    async def analyze_stock_stream(self, query: str) -> AsyncGenerator[str, None]:
        """Analyze stock with real-time status updates"""
        
        try:
            # Step 1: Extract ticker
            yield self._format_status(
                step="ticker_extraction",
                status="processing",
                message="Extracting stock ticker from your query...",
                progress=0.1
            )
            
            ticker = await self.ticker_extractor.extract_ticker(query)
            
            if not ticker:
                yield self._format_status(
                    step="ticker_extraction",
                    status="error",
                    message="Could not identify a stock ticker from your query",
                    progress=0.0
                )
                return
            
            yield self._format_status(
                step="ticker_extraction",
                status="completed",
                message=f"Found ticker: {ticker}",
                progress=0.2,
                data={"ticker": ticker}
            )
            
            # Step 2: Initialize browser
            yield self._format_status(
                step="browser_initialization",
                status="processing",
                message="Initializing browser for data extraction...",
                progress=0.25
            )
            
            await self.browser_agent.initialize()
            
            yield self._format_status(
                step="browser_initialization",
                status="completed",
                message="Browser initialized successfully",
                progress=0.3
            )
            
            # Step 3: Extract stock fundamentals
            yield self._format_status(
                step="fundamentals_extraction",
                status="processing",
                message=f"Extracting fundamental data for {ticker}...",
                progress=0.35
            )
            
            stock_data = await self.browser_agent.extract_stock_data(
                ticker=ticker,
                include_news=False,  # We'll get news separately for better progress tracking
                include_reddit=False  # We'll get Reddit separately too
            )
            
            yield self._format_status(
                step="fundamentals_extraction",
                status="completed",
                message=f"Extracted fundamental data for {ticker}",
                progress=0.5,
                data={
                    "price": stock_data.price_info.current_price,
                    "change_percent": stock_data.price_info.change_percent,
                    "company_name": stock_data.company_name
                }
            )
            
            # Step 4: Extract news
            yield self._format_status(
                step="news_extraction",
                status="processing",
                message="Gathering latest news articles...",
                progress=0.55
            )
            
            news_items = await self.browser_agent._extract_news(ticker)
            stock_data.news = news_items
            
            yield self._format_status(
                step="news_extraction",
                status="completed",
                message=f"Found {len(news_items)} news articles",
                progress=0.7,
                data={"news_count": len(news_items)}
            )
            
            # Step 5: Extract Reddit sentiment
            yield self._format_status(
                step="reddit_sentiment",
                status="processing",
                message="Analyzing Reddit sentiment...",
                progress=0.75
            )
            
            reddit_sentiment = await self.browser_agent._extract_reddit_sentiment(ticker)
            stock_data.reddit_sentiment = reddit_sentiment
            
            yield self._format_status(
                step="reddit_sentiment",
                status="completed",
                message="Reddit sentiment analysis completed" if reddit_sentiment else "Reddit sentiment analysis skipped",
                progress=0.8,
                data={
                    "sentiment": reddit_sentiment.overall_sentiment if reddit_sentiment else "unknown",
                    "confidence": reddit_sentiment.confidence_score if reddit_sentiment else 0.0
                }
            )
            
            # Step 6: Generate LLM analysis
            yield self._format_status(
                step="llm_analysis",
                status="processing",
                message="Generating comprehensive financial analysis...",
                progress=0.85
            )
            
            insights = await self.llm_service.generate_insights(stock_data)
            
            yield self._format_status(
                step="llm_analysis",
                status="completed",
                message="Financial analysis completed",
                progress=0.95
            )
            
            # Step 7: Final report
            yield self._format_status(
                step="report_generation",
                status="processing",
                message="Finalizing report...",
                progress=0.95
            )
            
            # Format the final report
            report = {
                "ticker": ticker,
                "company_name": stock_data.company_name,
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "price_info": {
                    "current_price": stock_data.price_info.current_price,
                    "change": stock_data.price_info.change,
                    "change_percent": stock_data.price_info.change_percent
                },
                "analysis": insights[0] if insights else "Unable to generate analysis",
                "fundamentals": self._serialize_fundamentals(stock_data),
                "reddit_sentiment": {
                    "sentiment": stock_data.reddit_sentiment.overall_sentiment if stock_data.reddit_sentiment else "unknown",
                    "confidence": stock_data.reddit_sentiment.confidence_score if stock_data.reddit_sentiment else 0.0,
                    "summary": stock_data.reddit_sentiment.sentiment_summary if stock_data.reddit_sentiment else "No Reddit analysis available"
                } if stock_data.reddit_sentiment else None,
                "news": [
                    {
                        "title": news.title,
                        "source": news.source,
                        "url": news.url,
                        "date": news.published_date.strftime("%Y-%m-%d")
                    }
                    for news in stock_data.news
                ]
            }
            
            yield self._format_status(
                step="report_generation",
                status="completed",
                message="Report generated successfully",
                progress=1.0,
                data={"report": report}
            )
            
        except Exception as e:
            logger.error(f"Error in stock analysis: {e}")
            yield self._format_status(
                step="error",
                status="error",
                message=f"Analysis failed: {str(e)}",
                progress=0.0
            )
        
        finally:
            # Clean up browser
            try:
                await self.browser_agent.close()
            except:
                pass
    
    def _format_status(self, step: str, status: str, message: str, progress: float, data: Optional[Dict] = None) -> str:
        """Format status update as JSON string"""
        status_update = StatusUpdate(
            step=step,
            status=status,
            message=message,
            progress=progress,
            data=data
        )
        return f"data: {status_update.json()}\n\n"
    
    def _serialize_fundamentals(self, stock_data: StockData) -> Dict[str, Any]:
        """Serialize fundamental metrics for JSON response"""
        fundamentals = stock_data.fundamentals
        return {
            "previous_close": fundamentals.previous_close,
            "open": fundamentals.open,
            "days_range": fundamentals.days_range,
            "volume": fundamentals.volume,
            "avg_volume": fundamentals.avg_volume,
            "market_cap": fundamentals.market_cap,
            "beta": fundamentals.beta,
            "pe_ratio": fundamentals.pe_ratio,
            "target_est": fundamentals.target_est,
            "earnings_date": fundamentals.earnings_date,
            "fifty_two_week_range": {
                "low": fundamentals.fifty_two_week_range.low,
                "high": fundamentals.fifty_two_week_range.high
            } if fundamentals.fifty_two_week_range else None
        }


# Global service instance
analysis_service = StockAnalysisService()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Stock Analysis API is running"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ollama_url": settings.ollama_base_url,
        "model": settings.ollama_model
    }


@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    """
    Analyze stock based on natural language query with streaming updates
    
    Returns Server-Sent Events (SSE) stream with real-time progress
    """
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    async def generate():
        yield "event: analysis_start\n"
        yield f"data: {json.dumps({'query': request.query, 'timestamp': datetime.now().isoformat()})}\n\n"
        
        async for status_update in analysis_service.analyze_stock_stream(request.query):
            yield f"event: status_update\n"
            yield status_update
        
        yield "event: analysis_complete\n"
        yield "data: {}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@app.post("/analyze-simple")
async def analyze_stock_simple(request: AnalysisRequest):
    """
    Simple non-streaming analysis endpoint for testing
    """
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Extract ticker
        ticker = await analysis_service.ticker_extractor.extract_ticker(request.query)
        
        if not ticker:
            raise HTTPException(status_code=400, detail="Could not identify stock ticker from query")
        
        # Initialize browser and extract data
        await analysis_service.browser_agent.initialize()
        stock_data = await analysis_service.browser_agent.extract_stock_data(ticker)
        
        # Generate analysis
        insights = await analysis_service.llm_service.generate_insights(stock_data)
        
        # Format response
        response = {
            "ticker": ticker,
            "company_name": stock_data.company_name,
            "timestamp": datetime.now().isoformat(),
            "query": request.query,
            "price_info": {
                "current_price": stock_data.price_info.current_price,
                "change": stock_data.price_info.change,
                "change_percent": stock_data.price_info.change_percent
            },
            "analysis": insights[0] if insights else "Unable to generate analysis",
            "news_count": len(stock_data.news)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in simple analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        try:
            await analysis_service.browser_agent.close()
        except:
            pass


@app.get("/test-ticker-extraction")
async def test_ticker_extraction(query: str):
    """Test endpoint for ticker extraction"""
    
    ticker = await analysis_service.ticker_extractor.extract_ticker(query)
    
    return {
        "query": query,
        "extracted_ticker": ticker,
        "success": ticker is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
