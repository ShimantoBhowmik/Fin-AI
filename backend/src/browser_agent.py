"""
Fallback browser automation module using Playwright directly
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re
from pathlib import Path

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available. Browser automation will be limited.")

from loguru import logger

from .config import settings
from .models import (
    StockData,
    StockPrice,
    FundamentalMetrics,
    FiftyTwoWeekRange,
    NewsItem,
    RedditSentiment,
)
from .reddit_analyzer import RedditSentimentAnalyzer


class BrowserAgent:
    """Browser agent using Playwright directly"""

    def __init__(self):
        self.browser = None
        self.page = None
        self._initialized = False
        self.reddit_analyzer = RedditSentimentAnalyzer()

    async def initialize(self):
        """Initialize the browser agent"""
        if self._initialized:
            return

        if not PLAYWRIGHT_AVAILABLE:
            raise Exception(
                "Playwright is not available. Please install with: pip install playwright"
            )

        try:
            self.playwright = await async_playwright().start()

            # Launch browser (headless by default)
            self.browser = await self.playwright.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            # Create a new page
            self.page = await self.browser.new_page()

            # Set a realistic user agent
            await self.page.set_extra_http_headers(
                {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )

            self._initialized = True
            logger.info("Browser agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize browser agent: {e}")
            raise

    async def extract_stock_data(
        self,
        ticker: str,
        include_news: bool = True,
        include_reddit: bool = True,
    ) -> StockData:
        """Extract comprehensive stock data for a given ticker"""
        if not self._initialized:
            await self.initialize()

        logger.info(f"Extracting stock data for {ticker}")

        try:
            # Navigate to Yahoo Finance for the ticker
            url = f"https://finance.yahoo.com/quote/{ticker}"
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait a bit for dynamic content to load
            await self.page.wait_for_timeout(3000)

            # Extract basic stock information
            stock_info = await self._extract_basic_info(ticker)

            # Extract fundamental metrics
            fundamentals = await self._extract_fundamentals()

            # Extract news if requested
            news = []
            if include_news:
                news = await self._extract_news(ticker)

            # Extract Reddit sentiment if requested
            reddit_sentiment = None
            if include_reddit:
                reddit_sentiment = await self._extract_reddit_sentiment(ticker)

            return StockData(
                ticker=ticker,
                company_name=stock_info.get("company_name", ticker),
                price_info=stock_info["price_info"],
                fundamentals=fundamentals,
                news=news,
                reddit_sentiment=reddit_sentiment,
                chart_path=None,
            )

        except Exception as e:
            logger.error(f"Error extracting data for {ticker}: {e}")
            raise

    async def _extract_basic_info(self, ticker: str) -> Dict[str, Any]:
        """Extract basic stock price and company information"""
        try:
            # Try to find the price element
            price_selector = (
                '[data-symbol="'
                + ticker
                + '"] [data-field="regularMarketPrice"], [data-testid="qsp-price"], fin-streamer[data-field="regularMarketPrice"]'
            )

            try:
                price_element = await self.page.wait_for_selector(
                    price_selector, timeout=10000
                )
                current_price_text = await price_element.text_content()
                current_price = self._safe_float(current_price_text.replace(",", ""))
            except:
                # Fallback: try to extract price from page text
                page_content = await self.page.content()
                current_price = self._extract_price_from_html(page_content, ticker)

            # Try to find change information
            change_selector = (
                '[data-field="regularMarketChange"], [data-testid="qsp-price-change"]'
            )
            change_percent_selector = '[data-field="regularMarketChangePercent"], [data-testid="qsp-price-change-percent"]'

            try:
                change_element = await self.page.query_selector(change_selector)
                change_percent_element = await self.page.query_selector(
                    change_percent_selector
                )

                change = 0
                change_percent = 0

                if change_element:
                    change_text = await change_element.text_content()
                    change = self._safe_float(
                        change_text.replace("+", "").replace(",", "")
                    )

                if change_percent_element:
                    change_percent_text = await change_percent_element.text_content()
                    change_percent = self._safe_float(
                        change_percent_text.replace("+", "")
                        .replace("%", "")
                        .replace("(", "")
                        .replace(")", "")
                    )

            except:
                change = 0
                change_percent = 0

            # Try to get company name
            try:
                title_element = await self.page.query_selector("h1")
                company_name = ticker
                if title_element:
                    title_text = await title_element.text_content()
                    if title_text and "(" in title_text:
                        company_name = title_text.split("(")[0].strip()
            except:
                company_name = ticker

            price_info = StockPrice(
                current_price=current_price or 0.0,
                change=change or 0.0,
                change_percent=change_percent or 0.0,
                currency="USD",
                last_updated=datetime.now(),
            )

            logger.info(
                f"Extracted price info for {ticker}: ${current_price} ({change_percent:+.2f}%)"
            )

            return {"company_name": company_name, "price_info": price_info}

        except Exception as e:
            logger.error(f"Error extracting basic info for {ticker}: {e}")
            return {
                "company_name": ticker,
                "price_info": StockPrice(
                    current_price=0.0,
                    change=0.0,
                    change_percent=0.0,
                    currency="USD",
                    last_updated=datetime.now(),
                ),
            }

    async def _extract_fundamentals(self) -> FundamentalMetrics:
        """Extract fundamental metrics from the current page"""
        try:
            fundamentals = {}

            # Wait for the page to fully load with dynamic content
            await self.page.wait_for_timeout(3000)
            
            # Scroll down to ensure all tables are visible
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await self.page.wait_for_timeout(1000)

            # First, try extracting from the current quote page (which contains most metrics)
            # Updated selectors based on Yahoo Finance's current structure - targeting quote-statistics section
            metrics_to_extract = {
                "previous_close": [
                    'div[data-testid="quote-statistics"] td:has-text("Previous Close") + td',
                    'fin-streamer[data-field="regularMarketPreviousClose"]',
                    '[data-test="PREV_CLOSE-value"]'
                ],
                "open": [
                    'div[data-testid="quote-statistics"] td:has-text("Open") + td',
                    'fin-streamer[data-field="regularMarketOpen"]',
                    '[data-test="OPEN-value"]'
                ],
                "days_range": [
                    'div[data-testid="quote-statistics"] td:has-text("Day\'s Range") + td',
                    'fin-streamer[data-field="regularMarketDayRange"]',
                    '[data-test="DAYS_RANGE-value"]'
                ],
                "volume": [
                    'div[data-testid="quote-statistics"] td:has-text("Volume") + td',
                    'fin-streamer[data-field="regularMarketVolume"]',
                    '[data-test="TD_VOLUME-value"]'
                ],
                "avg_volume": [
                    'div[data-testid="quote-statistics"] td:has-text("Avg. Volume") + td',
                    'fin-streamer[data-field="averageVolume"]',
                    '[data-test="AVERAGE_VOLUME_3MONTH-value"]'
                ],
                "market_cap": [
                    'div[data-testid="quote-statistics"] td:has-text("Market Cap") + td',
                    'fin-streamer[data-field="marketCap"]',
                    '[data-test="MARKET_CAP-value"]'
                ],
                "beta": [
                    'div[data-testid="quote-statistics"] td:has-text("Beta") + td',
                    'fin-streamer[data-field="beta"]',
                    '[data-test="BETA_5Y-value"]'
                ],
                "pe_ratio": [
                    'div[data-testid="quote-statistics"] td:has-text("PE Ratio") + td',
                    'fin-streamer[data-field="trailingPE"]',
                    '[data-test="PE_RATIO-value"]'
                ],
                "earnings_date": [
                    'div[data-testid="quote-statistics"] td:has-text("Earnings Date") + td',
                    'fin-streamer[data-field="earningsDate"]',
                    '[data-test="EARNINGS_DATE-value"]'
                ],
                "target_est": [
                    'div[data-testid="quote-statistics"] td:has-text("1y Target Est") + td',
                    'fin-streamer[data-field="targetMeanPrice"]',
                    '[data-test="ONE_YEAR_TARGET_PRICE-value"]'
                ],
            }

            # Try to extract from current page first
            for metric, selectors in metrics_to_extract.items():
                value = None
                for selector in selectors:
                    try:
                        # First try with a shorter timeout to avoid waiting too long
                        element = await self.page.query_selector(selector)
                        if element:
                            text = await element.text_content()
                            if text and text.strip() not in ["--", "N/A", "", "None"]:
                                cleaned_text = text.strip()
                                logger.info(f"Found {metric} using selector '{selector}': {cleaned_text}")
                                
                                # Handle special cases for fields that should remain as strings
                                if metric in ["days_range", "earnings_date"]:
                                    fundamentals[metric] = cleaned_text
                                    logger.info(f"Extracted {metric}: {cleaned_text} from quote page")
                                    break
                                else:
                                    # Parse as financial value for numeric fields
                                    value = self._parse_financial_value(cleaned_text)
                                    if value is not None:
                                        fundamentals[metric] = value
                                        logger.info(f"Extracted {metric}: {value} from quote page")
                                        break
                            else:
                                logger.debug(f"Empty or invalid text for {metric} using selector '{selector}': '{text}'")
                    except Exception as e:
                        # Selector didn't work, try next one
                        logger.debug(f"Selector '{selector}' failed for {metric}: {e}")
                        continue
                
                # If we couldn't extract this metric, try some alternative CSS approaches
                if metric not in fundamentals or fundamentals[metric] is None:
                    # Try more flexible selectors using valid CSS syntax
                    fallback_selectors = [
                        f'[data-testid*="{metric}"]',
                        f'[data-test*="{metric.upper()}"]',
                        f'[data-field*="{metric}"]',
                        f'td[title*="{metric.replace("_", " ").title()}"]',
                        f'span[title*="{metric.replace("_", " ").title()}"]'
                    ]
                    
                    for fallback_selector in fallback_selectors:
                        try:
                            element = await self.page.query_selector(fallback_selector)
                            if element:
                                text = await element.text_content()
                                if text and text.strip() not in ["--", "N/A", "", "None"]:
                                        cleaned_text = text.strip()
                                        logger.info(f"Found {metric} with fallback CSS: {cleaned_text}")
                                        
                                        if metric in ["days_range", "earnings_date"]:
                                            fundamentals[metric] = cleaned_text
                                            logger.info(f"Extracted {metric}: {cleaned_text} via fallback")
                                            break
                                        else:
                                            value = self._parse_financial_value(cleaned_text)
                                            if value is not None:
                                                fundamentals[metric] = value
                                                logger.info(f"Extracted {metric}: {value} via fallback")
                                                break
                        except Exception as e:
                            logger.debug(f"Fallback selector '{fallback_selector}' failed for {metric}: {e}")
                            continue

            # Log any metrics we couldn't extract
            for metric in metrics_to_extract.keys():
                if metric not in fundamentals or fundamentals[metric] is None:
                    logger.warning(f"Could not extract {metric}")
                    
            # Try one more fallback approach for missing metrics by looking at all table cells
            missing_metrics = [k for k, v in fundamentals.items() if v is None]
            if missing_metrics:
                logger.info(f"Attempting final fallback extraction for {len(missing_metrics)} missing metrics")
                
                # Look for all table rows in the quote-statistics section
                try:
                    # First try to find tables within the quote-statistics section
                    stats_section = await self.page.query_selector('div[data-testid="quote-statistics"]')
                    if stats_section:
                        all_rows = await stats_section.query_selector_all('tr')
                        logger.info(f"Found {len(all_rows)} rows in quote-statistics section")
                    else:
                        # Fallback to any table rows on the page
                        all_rows = await self.page.query_selector_all('table tr, div tr')
                        logger.info(f"Found {len(all_rows)} table rows on page")
                    
                    for row in all_rows:
                        try:
                            cells = await row.query_selector_all('td, th')
                            if len(cells) >= 2:
                                first_cell_text = await cells[0].text_content()
                                second_cell_text = await cells[1].text_content()
                                
                                if first_cell_text and second_cell_text:
                                    first_cell_text = first_cell_text.strip().lower()
                                    second_cell_text = second_cell_text.strip()
                                    
                                    # Check for matches with our missing metrics
                                    for metric in missing_metrics:
                                        metric_variations = [
                                            metric.replace("_", " "),
                                            metric.replace("_", " ").title(),
                                            metric.replace("_", "-"),
                                        ]
                                        
                                        # Add specific variations for known fields
                                        if metric == "previous_close":
                                            metric_variations.extend(["previous close", "prev close"])
                                        elif metric == "days_range":
                                            metric_variations.extend(["day's range", "days range"])
                                        elif metric == "avg_volume":
                                            metric_variations.extend(["avg. volume", "average volume"])
                                        elif metric == "market_cap":
                                            metric_variations.extend(["market cap", "market cap (intraday)"])
                                        elif metric == "pe_ratio":
                                            metric_variations.extend(["pe ratio (ttm)", "p/e ratio", "pe ratio"])
                                        elif metric == "target_est":
                                            metric_variations.extend(["1y target est", "target price"])
                                        elif metric == "beta":
                                            metric_variations.extend(["beta (5y monthly)", "beta"])
                                        elif metric == "open":
                                            metric_variations.extend(["open"])
                                        elif metric == "volume":
                                            metric_variations.extend(["volume"])
                                        elif metric == "earnings_date":
                                            metric_variations.extend(["earnings date"])
                                        
                                        for variation in metric_variations:
                                            if variation.lower() in first_cell_text:
                                                if second_cell_text not in ["--", "N/A", "", "None"]:
                                                    logger.info(f"Found {metric} in table row: '{first_cell_text}' -> '{second_cell_text}'")
                                                    
                                                    if metric in ["days_range", "earnings_date"]:
                                                        fundamentals[metric] = second_cell_text
                                                        logger.info(f"Extracted {metric}: {second_cell_text} from table fallback")
                                                    else:
                                                        value = self._parse_financial_value(second_cell_text)
                                                        if value is not None:
                                                            fundamentals[metric] = value
                                                            logger.info(f"Extracted {metric}: {value} from table fallback")
                                                    break
                        except Exception as e:
                            continue
                except Exception as e:
                    logger.debug(f"Table fallback extraction failed: {e}")
                    
            logger.info(f"Successfully extracted {len([k for k, v in fundamentals.items() if v is not None])} out of {len(metrics_to_extract)} metrics")

            # Extract 52-week range with improved selectors
            fifty_two_week_range = None
            range_selectors = [
                'div[data-testid="quote-statistics"] td:has-text("52 Week Range") + td',
                'div[data-testid="quote-statistics"] td:has-text("52-Week Range") + td',
                '[data-test="FIFTY_TWO_WK_RANGE-value"]'
            ]

            for selector in range_selectors:
                try:
                    range_element = await self.page.wait_for_selector(selector, timeout=5000)
                    if range_element:
                        range_text = await range_element.text_content()
                        if range_text and "-" in range_text:
                            parts = range_text.strip().split("-")
                            if len(parts) == 2:
                                low = self._parse_financial_value(parts[0].strip())
                                high = self._parse_financial_value(parts[1].strip())
                                if low and high:
                                    fifty_two_week_range = FiftyTwoWeekRange(high=high, low=low)
                                    logger.info(f"Extracted 52-week range: {low} - {high}")
                                    break
                except Exception as e:
                    continue

            logger.info(f"Final extracted fundamentals: {fundamentals}")

            return FundamentalMetrics(
                # Basic pricing metrics
                previous_close=fundamentals.get("previous_close"),
                open=fundamentals.get("open"),
                days_range=fundamentals.get("days_range"),  # Keep as string
                
                # Volume and market data
                volume=int(fundamentals.get("volume")) if fundamentals.get("volume") else None,
                avg_volume=int(fundamentals.get("avg_volume")) if fundamentals.get("avg_volume") else None,
                market_cap=fundamentals.get("market_cap"),
                beta=fundamentals.get("beta"),
                
                # Valuation metrics
                pe_ratio=fundamentals.get("pe_ratio"),
                target_est=fundamentals.get("target_est"),
                
                # Date fields (keep as strings for now)
                earnings_date=fundamentals.get("earnings_date"),
                
                # Range data
                fifty_two_week_range=fifty_two_week_range,
                
                # Legacy/optional fields
                bid=None,  # Removed - not available consistently
                ask=None,  # Removed - not available consistently
                eps=None,  # Removed - not available consistently
                dividend_yield=None,  # Removed - not available consistently
                ex_dividend_date=None,  # Removed - not available consistently
                roe=None,  # Not easily available on main pages
            )

        except Exception as e:
            logger.error(f"Error extracting fundamentals: {e}")
            return FundamentalMetrics()

    def _parse_financial_value(self, text: str) -> Optional[float]:
        """Parse financial values with B/M/K suffixes"""
        if not text or text.strip() in ["--", "N/A", ""]:
            return None

        try:
            # Handle dividend yield format: "1.04 (0.51%)" - extract the percentage in parentheses
            import re
            if "(" in text and "%" in text:
                # Extract percentage from parentheses: "1.04 (0.51%)" -> "0.51"
                percent_match = re.search(r"\(([0-9]+\.?[0-9]*)\%\)", text)
                if percent_match:
                    return float(percent_match.group(1))
            
            # Remove common formatting
            cleaned = text.replace(",", "").replace("$", "").replace("%", "").strip()

            # Handle suffixes
            multiplier = 1
            if cleaned.endswith("B"):
                multiplier = 1e9
                cleaned = cleaned[:-1]
            elif cleaned.endswith("M"):
                multiplier = 1e6
                cleaned = cleaned[:-1]
            elif cleaned.endswith("K"):
                multiplier = 1e3
                cleaned = cleaned[:-1]
            elif cleaned.endswith("T"):
                multiplier = 1e12
                cleaned = cleaned[:-1]

            # Extract numeric value
            number_match = re.search(r"([0-9]+\.?[0-9]*)", cleaned)
            if number_match:
                return float(number_match.group(1)) * multiplier

            return None
        except Exception:
            return None

    async def _extract_news(self, ticker: str) -> List[NewsItem]:
        try:
            news_items = []
            news_url = f"https://finance.yahoo.com/quote/{ticker}/news/"
            logger.info(f"Fetching news from: {news_url}")

            await self.page.goto(news_url, wait_until="domcontentloaded", timeout=20000)
            await self.page.wait_for_timeout(3000)

            # Try multiple selectors to find news articles
            article_selectors = [
                'div[data-testid="news-stream"] li.stream-item',
                'li.js-stream-content',
                'li[data-test-locator="StreamItem"]',
                'div[data-testid="ContentStream"] li',
                'ul[data-testid="news-stream"] li',
                'section[data-testid="news"] li'
            ]

            articles = []
            for selector in article_selectors:
                try:
                    found_articles = await self.page.query_selector_all(selector)
                    if found_articles and len(found_articles) > 0:
                        articles = found_articles
                        logger.info(f"Found {len(articles)} articles using selector: {selector}")
                        break
                except:
                    continue

            if not articles:
                logger.warning(f"No articles found for {ticker}")
                return []

            # Process articles until we have exactly 5 news items
            target_count = 5
            processed_count = 0
            
            for article in articles:
                if len(news_items) >= target_count:
                    break
                    
                processed_count += 1
                try:
                    # Try multiple link selectors
                    link_selectors = [
                        'a.subtle-link',
                        'h3 a',
                        'a[data-test-locator="StreamItemTitle"]',
                        'a[href*="/news/"]',
                        'a'
                    ]
                    
                    link_el = None
                    for link_selector in link_selectors:
                        link_el = await article.query_selector(link_selector)
                        if link_el:
                            break
                    
                    if not link_el:
                        logger.debug(f"No link found in article {processed_count}")
                        continue

                    title = await link_el.text_content()
                    href = await link_el.get_attribute("href")
                    
                    if not title or not href:
                        logger.debug(f"Missing title or href in article {processed_count}")
                        continue
                        
                    url = href if href.startswith("http") else f"https://finance.yahoo.com{href}"

                    if title and title.strip():
                        news_items.append(
                            NewsItem(
                                title=title.strip(),
                                url=url,
                                source="Yahoo Finance",
                                published_date=datetime.now(),
                            )
                        )
                        logger.debug(f"Successfully extracted news item {len(news_items)}: {title[:50]}...")
                        
                except Exception as e:
                    logger.debug(f"Failed to extract news item {processed_count}: {e}")
                    continue

            # If we still don't have 5 items, try to pad with additional sources or duplicate handling
            if len(news_items) < target_count:
                logger.warning(f"Only found {len(news_items)} news items, target was {target_count}")
                
                # Try to get more articles by scrolling down and looking for more content
                try:
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await self.page.wait_for_timeout(2000)
                    
                    # Look for additional articles after scrolling
                    for selector in article_selectors:
                        try:
                            additional_articles = await self.page.query_selector_all(selector)
                            if len(additional_articles) > len(articles):
                                logger.info(f"Found {len(additional_articles)} articles after scrolling")
                                
                                # Process the new articles
                                for article in additional_articles[len(articles):]:
                                    if len(news_items) >= target_count:
                                        break
                                        
                                    try:
                                        for link_selector in link_selectors:
                                            link_el = await article.query_selector(link_selector)
                                            if link_el:
                                                break
                                        
                                        if link_el:
                                            title = await link_el.text_content()
                                            href = await link_el.get_attribute("href")
                                            
                                            if title and href:
                                                url = href if href.startswith("http") else f"https://finance.yahoo.com{href}"
                                                
                                                # Check for duplicates
                                                duplicate = any(item.title == title.strip() for item in news_items)
                                                if not duplicate:
                                                    news_items.append(
                                                        NewsItem(
                                                            title=title.strip(),
                                                            url=url,
                                                            source="Yahoo Finance",
                                                            published_date=datetime.now(),
                                                        )
                                                    )
                                    except:
                                        continue
                                break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Error during scroll and additional extraction: {e}")

            logger.info(f"Extracted {len(news_items)} news items for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"Error extracting news for {ticker}: {e}")
            return []

    async def _extract_reddit_sentiment(self, ticker: str) -> Optional[RedditSentiment]:
        """Extract Reddit sentiment analysis for the ticker"""
        try:
            logger.info(f"Extracting Reddit sentiment for {ticker}")
            return await self.reddit_analyzer.analyze_sentiment(ticker)
        except Exception as e:
            logger.error(f"Error extracting Reddit sentiment for {ticker}: {e}")
            return None


    def _parse_relative_date(self, date_text: str) -> datetime:
        """Parse relative date strings like '2 hours ago'"""
        try:
            import re

            date_text = date_text.lower().strip()
            now = datetime.now()

            # Handle "X hours ago"
            hours_match = re.search(r"(\d+)\s*hours?\s*ago", date_text)
            if hours_match:
                hours = int(hours_match.group(1))
                return now - timedelta(hours=hours)

            # Handle "X minutes ago"
            minutes_match = re.search(r"(\d+)\s*minutes?\s*ago", date_text)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                return now - timedelta(minutes=minutes)

            # Handle "X days ago"
            days_match = re.search(r"(\d+)\s*days?\s*ago", date_text)
            if days_match:
                days = int(days_match.group(1))
                return now - timedelta(days=days)

            # Handle "yesterday"
            if "yesterday" in date_text:
                return now - timedelta(days=1)

            # Default to now
            return now

        except Exception:
            return datetime.now()

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Handle various formatting
                cleaned = re.sub(r"[^0-9.-]", "", value.replace(",", ""))
                if cleaned == "" or cleaned == "--":
                    return None
                return float(cleaned)
            return float(value)
        except (ValueError, TypeError):
            return None

    def _extract_price_from_html(self, html_content: str, ticker: str) -> float:
        """Extract price from HTML content as fallback"""
        try:
            # Look for price patterns in the HTML
            price_patterns = [
                rf'data-symbol="{ticker}"[^>]*>([0-9,]+\.?[0-9]*)',
                r"regularMarketPrice[^>]*>([0-9,]+\.?[0-9]*)",
                r"quote-header-info.*?([0-9,]+\.?[0-9]*)",
            ]

            for pattern in price_patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    price_str = matches[0].replace(",", "")
                    return float(price_str)

            return 0.0
        except:
            return 0.0

    async def close(self):
        """Close the browser agent"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, "playwright"):
                await self.playwright.stop()
            
            # Close Reddit analyzer
            if hasattr(self, 'reddit_analyzer'):
                await self.reddit_analyzer.close()
                
            self._initialized = False
            logger.info("Browser agent closed")
        except Exception as e:
            logger.warning(f"Error closing browser agent: {e}")


# Alias for easy switching
StockBrowserAgent = BrowserAgent
