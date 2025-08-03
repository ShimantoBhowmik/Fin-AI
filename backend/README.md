# Stock Analysis Agent

An AI-powered stock analysis tool that automates financial data collection, analysis, and report generation using browser automation and local LLM processing.

## Features

- **Automated Data Collection**: Uses Browserbase + Stagehand for reliable web scraping
- **Comprehensive Analysis**: Price data, fundamentals, technical indicators, and news
- **Local LLM Processing**: Powered by Ollama for privacy and control
- **Rich Reports**: Markdown and JSON reports with visualizations
- **CLI Interface**: Easy-to-use command line tools
- **Real-time Monitoring**: Track multiple stocks with custom alerts

## Quick Start

### 1. Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running
- Browserbase account (for web scraping)

### 2. Installation

```bash
# Clone and setup
git clone <repository-url>
cd agent

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys
```

### 3. Configuration

Edit `.env` file:
```bash
BROWSERBASE_API_KEY=your_api_key_here
BROWSERBASE_PROJECT_ID=your_project_id_here
OLLAMA_MODEL=llama3.1:8b
```

### 4. Setup and Test

```bash
# Test setup
python cli.py setup

# Quick stock analysis
python cli.py quick AAPL
```

## Usage Examples

### Analyze Single Stock
```bash
python cli.py analyze AAPL
```

### Analyze Multiple Stocks
```bash
python cli.py analyze AAPL MSFT GOOGL -d 6m
```

### Quick Analysis
```bash
python cli.py quick TSLA
```

### Monitor Stocks
```bash
python cli.py monitor AAPL MSFT --threshold 3.0
```

### Custom Analysis
```bash
python cli.py analyze NVDA -m price -m pe_ratio -m dividend_yield --no-charts
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Main Agent     │    │ Browser Agent   │
│                 │────│                 │────│                 │
│ cli.py          │    │ main_agent.py   │    │ browser_agent.py│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
       ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
       │  LLM Service    │ │ Data Processor  │ │ Report Generator│
       │                 │ │                 │ │                 │
       │ llm_service.py  │ │data_processor.py│ │report_generator.py│
       └─────────────────┘ └─────────────────┘ └─────────────────┘
                │
       ┌─────────────────┐
       │     Ollama      │
       │  (Local LLM)    │
       └─────────────────┘
```