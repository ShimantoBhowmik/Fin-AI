"""
Data Models for Stock Analysis Agent
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MetricType(str, Enum):
    """Available metric types for analysis"""

    PRICE = "price"
    PE_RATIO = "pe_ratio"
    ROE = "roe"
    DIVIDEND_YIELD = "dividend_yield"
    MARKET_CAP = "market_cap"
    VOLUME = "volume"
    FIFTY_TWO_WEEK_RANGE = "52w_range"


class StockRequest(BaseModel):
    """User request for stock analysis"""

    tickers: List[str] = Field(..., description="List of stock tickers to analyze")
    date_range: Optional[str] = Field(
        None, description="Date range for analysis (e.g., '1y', '6m', '3m')"
    )
    metrics: List[MetricType] = Field(
        default_factory=lambda: [MetricType.PRICE, MetricType.PE_RATIO]
    )
    include_news: bool = Field(True, description="Whether to include news analysis")
    include_reddit: bool = Field(True, description="Whether to include Reddit sentiment analysis")


class StockPrice(BaseModel):
    """Stock price information"""

    current_price: float
    change: float
    change_percent: float
    currency: str = "USD"
    last_updated: datetime


class FiftyTwoWeekRange(BaseModel):
    """52-week high/low range"""

    high: float
    low: float


class FundamentalMetrics(BaseModel):
    """Fundamental analysis metrics"""

    # Basic pricing metrics
    previous_close: Optional[float] = None
    open: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    days_range: Optional[str] = None  # Keep as string since it's a range like "220.00 - 225.00"
    
    # Volume and market data
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    market_cap: Optional[float] = None
    beta: Optional[float] = None
    
    # Valuation metrics
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    target_est: Optional[float] = None
    
    # Date fields
    earnings_date: Optional[str] = None  # Keep as string since it can be a date range
    ex_dividend_date: Optional[str] = None  # Keep as string for date formatting
    
    # Range data
    fifty_two_week_range: Optional[FiftyTwoWeekRange] = None
    
    # Legacy field for backward compatibility
    roe: Optional[float] = None


class NewsItem(BaseModel):
    """News article information"""

    title: str
    url: str
    source: str
    published_date: datetime


class RedditSentiment(BaseModel):
    """Reddit sentiment analysis data"""
    
    ticker: str
    overall_sentiment: str = "neutral"  # "positive", "negative", "neutral"
    confidence_score: float = 0.5  # 0.0 to 1.0
    posts_analyzed: int = 0  # Default to 0 if not provided
    key_discussions: List[str] = Field(default_factory=list)
    sentiment_summary: str = "No sentiment analysis available"
    extracted_text: str = ""  # Raw OCR text for transparency
    screenshot_timestamp: datetime = Field(default_factory=datetime.now)





class StockData(BaseModel):
    """Complete stock data for a single ticker"""

    ticker: str
    company_name: str
    price_info: StockPrice
    fundamentals: FundamentalMetrics
    news: List[NewsItem] = Field(default_factory=list)
    reddit_sentiment: Optional[RedditSentiment] = None
    technical_indicators: Optional[Dict[str, Any]] = Field(default_factory=dict)
    valuation_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    insights: Optional[List[str]] = Field(default_factory=list)
    news_sentiment: Optional[Dict[str, Any]] = None
    chart_path: Optional[str] = None  # For screenshot storage
    llm_prompts_used: Optional[Dict[str, str]] = Field(
        default_factory=dict
    )  # Store prompts for transparency
    analysis_timestamp: datetime = Field(default_factory=datetime.now)


class AnalysisReport(BaseModel):
    """Final analysis report"""

    request: StockRequest
    stocks_data: List[StockData]
    insights: List[str]
    summary: str = ""  # Executive summary of the analysis
    generated_at: datetime = Field(default_factory=datetime.now)
    report_path: Optional[str] = None
    system_prompts_used: Optional[Dict[str, str]] = Field(
        default_factory=dict
    )  # Store system prompts
