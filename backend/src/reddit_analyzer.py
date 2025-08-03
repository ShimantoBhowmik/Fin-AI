"""
Reddit Sentiment Analyzer using screenshots and OCR
"""

import asyncio
import os
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import base64

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from loguru import logger
import ollama

from .models import RedditSentiment


class RedditSentimentAnalyzer:
    """Analyzes Reddit sentiment using screenshots and OCR"""
    
    def __init__(self, screenshots_dir: str = "screenshots"):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True)
        self.browser = None
        self.page = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the browser for Reddit scraping"""
        if self._initialized:
            return
            
        if not PLAYWRIGHT_AVAILABLE:
            raise Exception("Playwright is not available. Please install with: pip install playwright")
            
        if not OCR_AVAILABLE:
            logger.warning("OCR dependencies not available. Install with: pip install pytesseract pillow")
            logger.warning("Also install tesseract: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)")
            
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
            )
            
            # Create context with realistic settings
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            self.page = await context.new_page()
            
            # Set additional headers
            await self.page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            self._initialized = True
            logger.info("Reddit sentiment analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Reddit analyzer: {e}")
            raise
            
    async def analyze_sentiment(self, ticker: str) -> Optional[RedditSentiment]:
        """Analyze Reddit sentiment for a stock ticker"""
        if not self._initialized:
            await self.initialize()
            
        try:
            logger.info(f"Analyzing Reddit sentiment for {ticker}")
            
            # Take screenshot of Reddit search results
            screenshot_path = await self._capture_reddit_screenshot(ticker)
            
            if not screenshot_path:
                logger.warning(f"Failed to capture Reddit screenshot for {ticker}")
                return None
                
            # Extract text from screenshot using OCR
            extracted_text = await self._extract_text_from_screenshot(screenshot_path)
            
            if not extracted_text:
                logger.warning(f"Failed to extract text from Reddit screenshot for {ticker}")
                return None
                
            # Analyze sentiment using LLM
            sentiment_data = await self._analyze_text_sentiment(ticker, extracted_text)
            
            return RedditSentiment(
                ticker=ticker,
                overall_sentiment=sentiment_data.get("sentiment") or "neutral",
                confidence_score=sentiment_data.get("confidence") or 0.5,
                posts_analyzed=sentiment_data.get("posts_count") or 0,
                key_discussions=sentiment_data.get("key_points") or [],
                sentiment_summary=sentiment_data.get("summary") or "No clear sentiment found",
                extracted_text=extracted_text[:1000],  # Limit size
                screenshot_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing Reddit sentiment for {ticker}: {e}")
            return None
            
    async def _capture_reddit_screenshot(self, ticker: str) -> Optional[str]:
        """Capture screenshot of Reddit search results for the ticker"""
        try:
            # Search Reddit for the ticker
            search_url = f"https://www.reddit.com/search/?q={ticker}%20stock&sort=new&t=week"
            logger.info(f"Navigating to Reddit search: {search_url}")
            
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for content to load
            await self.page.wait_for_timeout(5000)
            
            # Try to handle any popups or modals
            try:
                # Look for common Reddit popup/modal selectors and close them
                popup_selectors = [
                    '[data-testid="login-popup"] button[aria-label="Close"]',
                    '.Popup button[aria-label="Close"]',
                    '[role="dialog"] button[aria-label="Close"]',
                    '.Modal button[aria-label="Close"]'
                ]
                
                for selector in popup_selectors:
                    try:
                        popup_close = await self.page.query_selector(selector)
                        if popup_close:
                            await popup_close.click()
                            await self.page.wait_for_timeout(1000)
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"No popups to close: {e}")
                
            # Scroll down to load more content
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await self.page.wait_for_timeout(2000)
            
            # Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"reddit_{ticker}_{timestamp}.png"
            screenshot_path = self.screenshots_dir / screenshot_filename
            
            await self.page.screenshot(path=str(screenshot_path), full_page=False)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Error capturing Reddit screenshot: {e}")
            return None
            
    async def _extract_text_from_screenshot(self, screenshot_path: str) -> Optional[str]:
        """Extract text from screenshot using OCR"""
        if not OCR_AVAILABLE:
            logger.warning("OCR not available, cannot extract text from screenshot")
            return None
            
        try:
            # Load image
            with Image.open(screenshot_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Extract text using OCR
                extracted_text = pytesseract.image_to_string(img, lang='eng')
                
                # Clean up the text
                cleaned_text = self._clean_ocr_text(extracted_text)
                
                logger.info(f"Extracted {len(cleaned_text)} characters from screenshot")
                return cleaned_text
                
        except Exception as e:
            logger.error(f"Error extracting text from screenshot: {e}")
            return None
            
    def _clean_ocr_text(self, text: str) -> str:
        """Clean and normalize OCR extracted text"""
        if not text:
            return ""
            
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\.\,\!\?\-\$\%\(\)]', ' ', text)
        
        # Filter out very short words that are likely OCR errors
        words = text.split()
        cleaned_words = [word for word in words if len(word) > 1 or word.lower() in ['a', 'i']]
        
        return ' '.join(cleaned_words).strip()
        
    async def _analyze_text_sentiment(self, ticker: str, text: str) -> Dict[str, Any]:
        """Analyze sentiment of extracted text using LLM"""
        try:
            system_prompt = f"""
You are a financial sentiment analyzer. Analyze the following text extracted from Reddit discussions about the stock ticker {ticker}.

Provide your analysis in JSON format with these fields:
- sentiment: "positive", "negative", or "neutral"
- confidence: float between 0.0 and 1.0
- posts_count: estimated number of posts/comments analyzed
- key_points: list of 3-5 key discussion points
- summary: brief summary of overall sentiment

Focus on:
1. Overall market sentiment (bullish/bearish)
2. Specific concerns or optimism about the company
3. Price predictions or expectations
4. Recent news impact on sentiment
5. Community confidence level

Be objective and consider both positive and negative viewpoints.
"""

            user_prompt = f"""
Analyze the sentiment of this Reddit text about {ticker}:

{text[:2000]}  # Limit text to avoid token limits

Return only valid JSON.
"""

            response = ollama.chat(
                model="deepseek-r1:8b",  # Use deepseek-r1:8b for sophisticated sentiment analysis
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            response_text = response["message"]["content"]
            logger.info(f"LLM response for sentiment analysis: {response_text[:500]}...")
            
            # Try to extract JSON from response
            try:
                import json
                # Look for JSON in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    
                    # Validate and fix all required fields
                    validated_result = {
                        "sentiment": result.get("sentiment") or "neutral",
                        "confidence": result.get("confidence") or 0.5,
                        "posts_count": 0,
                        "key_points": result.get("key_points") or [],
                        "summary": result.get("summary") or "Analysis completed"
                    }
                    
                    # Ensure posts_count is a valid integer
                    posts_count = result.get("posts_count")
                    if isinstance(posts_count, int):
                        validated_result["posts_count"] = posts_count
                    elif posts_count is not None:
                        try:
                            validated_result["posts_count"] = int(posts_count)
                        except (ValueError, TypeError):
                            validated_result["posts_count"] = 0
                    
                    # Ensure confidence is a valid float
                    confidence = result.get("confidence")
                    if isinstance(confidence, (int, float)):
                        validated_result["confidence"] = float(confidence)
                    elif confidence is not None:
                        try:
                            validated_result["confidence"] = float(confidence)
                        except (ValueError, TypeError):
                            validated_result["confidence"] = 0.5
                    
                    result = validated_result
                else:
                    # Fallback parsing
                    result = self._parse_sentiment_fallback(response_text)
            except Exception as e:
                logger.warning(f"JSON parsing failed: {e}")
                result = self._parse_sentiment_fallback(response_text)
                
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment with LLM: {e}")
            return {
                "sentiment": "neutral",
                "confidence": 0.3,
                "posts_count": 0,
                "key_points": ["Analysis failed"],
                "summary": f"Could not analyze sentiment: {str(e)}"
            }
            
    def _parse_sentiment_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback sentiment parsing when JSON fails"""
        sentiment = "neutral"
        confidence = 0.5
        
        text_lower = text.lower()
        
        # Simple keyword-based sentiment analysis
        positive_words = ["bullish", "buy", "positive", "good", "great", "strong", "up", "moon", "rocket"]
        negative_words = ["bearish", "sell", "negative", "bad", "weak", "down", "crash", "dump"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence = min(0.8, 0.5 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count:
            sentiment = "negative" 
            confidence = min(0.8, 0.5 + (negative_count - positive_count) * 0.1)
            
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "posts_count": text.count('\n') // 3,  # Rough estimate
            "key_points": [f"Detected {positive_count} positive and {negative_count} negative indicators"],
            "summary": f"Fallback analysis shows {sentiment} sentiment with {confidence:.1f} confidence"
        }
        
    async def close(self):
        """Close the browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            self._initialized = False
            logger.info("Reddit sentiment analyzer closed")
        except Exception as e:
            logger.warning(f"Error closing Reddit analyzer: {e}")
