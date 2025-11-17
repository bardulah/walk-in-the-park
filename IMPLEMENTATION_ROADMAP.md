# Implementation Roadmap: Multi-Agent Trading System

**Version:** 1.0
**Date:** November 17, 2025
**Target:** Production-Ready System in 8-12 Weeks

---

## Executive Summary

This roadmap provides a phased approach to building your multi-agent trading system, starting with a minimal viable product (MVP) and progressively adding capabilities. Each phase is designed to deliver value independently while building toward the complete 6-agent architecture.

**Timeline Overview:**
- **Phase 0:** Setup & Infrastructure (Week 1)
- **Phase 1:** MVP - 3-Agent System (Weeks 2-3)
- **Phase 2:** Enhanced Analysis (Weeks 4-5)
- **Phase 3:** Full 6-Agent System (Weeks 6-7)
- **Phase 4:** Learning & Optimization (Weeks 8-10)
- **Phase 5:** Production Hardening (Weeks 11-12)

---

## Table of Contents

1. [Phase 0: Setup & Infrastructure](#phase-0-setup--infrastructure)
2. [Phase 1: MVP (3-Agent System)](#phase-1-mvp-3-agent-system)
3. [Phase 2: Enhanced Analysis](#phase-2-enhanced-analysis)
4. [Phase 3: Full 6-Agent System](#phase-3-full-6-agent-system)
5. [Phase 4: Learning & Optimization](#phase-4-learning--optimization)
6. [Phase 5: Production Hardening](#phase-5-production-hardening)
7. [Risk Mitigation Strategies](#risk-mitigation-strategies)
8. [Success Metrics](#success-metrics)
9. [Deployment Checklist](#deployment-checklist)

---

## Phase 0: Setup & Infrastructure

**Duration:** Week 1
**Goal:** Establish foundational infrastructure and API connections

### 0.1 Prerequisites

**Required Accounts:**
- [ ] 212 Trading account with API access
- [ ] Exa Search API key
- [ ] Firecrawl API account (Hobby plan)
- [ ] OpenRouter API key
- [ ] Perplexity API key (optional for Phase 1)
- [ ] Composio account
- [ ] Neon PostgreSQL account
- [ ] Pinecone account
- [ ] Gmail account for notifications
- [ ] Telegram Bot token

**Development Environment:**
- [ ] Python 3.10+
- [ ] Git repository initialized
- [ ] Virtual environment configured
- [ ] Dependencies installed (see below)

---

### 0.2 Technology Stack Setup

**Core Dependencies:**
```bash
pip install anthropic openai yfinance requests python-dotenv psycopg2-binary pinecone-client composio-core

# Additional
pip install beautifulsoup4  # For web scraping fallbacks
pip install pandas numpy  # For calculations
pip install pytest  # For testing
```

**Directory Structure:**
```
trading-system/
├── agents/
│   ├── __init__.py
│   ├── portfolio_analyst.py
│   ├── market_analyst.py
│   ├── news_monitor.py
│   ├── technical_analyst.py
│   ├── risk_manager.py
│   └── orchestrator.py
├── data/
│   ├── fetchers/
│   │   ├── trading_212.py
│   │   ├── market_data.py
│   │   ├── news_data.py
│   │   └── technical_data.py
│   └── cache.py
├── database/
│   ├── neon_client.py
│   ├── pinecone_client.py
│   └── schema.sql
├── notifications/
│   ├── email_sender.py
│   └── telegram_sender.py
├── utils/
│   ├── llm_router.py
│   ├── cost_tracker.py
│   └── config.py
├── tests/
│   ├── test_agents.py
│   ├── test_data_fetchers.py
│   └── test_integration.py
├── main.py  # Orchestrator entry point
├── requirements.txt
├── .env  # API keys (DO NOT commit)
└── README.md
```

---

### 0.3 Database Setup (Neon PostgreSQL)

**Create Tables:**
```sql
-- Portfolio snapshots
CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    positions JSONB NOT NULL,
    total_value DECIMAL(12,2),
    cash_balance DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent outputs
CREATE TABLE agent_outputs (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    ticker VARCHAR(10),
    output_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_date_agent (date, agent_name),
    INDEX idx_ticker (ticker)
);

-- Final recommendations
CREATE TABLE final_recommendations (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,
    quantity INTEGER,
    entry_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    take_profit DECIMAL(10,2),
    confidence INTEGER,
    reasoning TEXT,
    agent_consensus JSONB,
    executed BOOLEAN DEFAULT FALSE,
    execution_price DECIMAL(10,2),
    execution_date DATE,
    outcome_price DECIMAL(10,2),  -- Price 7 days later
    profit_loss DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_date (date),
    INDEX idx_ticker (ticker)
);

-- Cost tracking
CREATE TABLE cost_log (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    component VARCHAR(50) NOT NULL,
    cost DECIMAL(6,3) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_date (date)
);

-- System health monitoring
CREATE TABLE system_health (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    component VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'success', 'degraded', 'failed'
    latency_ms INTEGER,
    error_message TEXT,
    INDEX idx_timestamp (timestamp)
);
```

**Run Migration:**
```bash
psql postgresql://user:password@host/database < database/schema.sql
```

---

### 0.4 Pinecone Setup

**Create Index:**
```python
import pinecone

pinecone.init(api_key="your_api_key", environment="gcp-starter")

# Create index for market conditions
pinecone.create_index(
    name="trading-system",
    dimension=1536,  # OpenAI embedding size
    metric="cosine"
)

# Namespaces to use:
# - market_conditions
# - company_sentiment_{TICKER}
# - portfolio_health
# - recommendation_history
```

---

### 0.5 API Integration Tests

**Test Each API:**
```python
# Test 212 Trading API
from data.fetchers.trading_212 import Trading212Client
client = Trading212Client(api_key=os.getenv("TRADING_212_KEY"))
portfolio = client.get_portfolio()
print(f"✓ 212 API works. Portfolio value: ${portfolio['total_value']}")

# Test Exa
from exa_py import Exa
exa = Exa(api_key=os.getenv("EXA_API_KEY"))
results = exa.search("Tesla stock news", num_results=5, type="keyword")
print(f"✓ Exa API works. Found {len(results)} results")

# Test OpenRouter
from utils.llm_router import LLMRouter
router = LLMRouter()
response = router.call("openai/gpt-4o-mini", "Hello, test")
print(f"✓ OpenRouter works. Response: {response[:50]}")

# Test Neon
from database.neon_client import NeonClient
neon = NeonClient()
neon.execute("SELECT 1")
print("✓ Neon PostgreSQL works")

# Test Pinecone
from database.pinecone_client import PineconeClient
pc = PineconeClient()
pc.upsert("test-namespace", [{"id": "test", "values": [0.1]*1536}])
print("✓ Pinecone works")

# Test Gmail
from notifications.email_sender import send_email
send_email("test@example.com", "Test", "This is a test")
print("✓ Gmail API works")

# Test Telegram
from notifications.telegram_sender import send_telegram
send_telegram("Test message")
print("✓ Telegram Bot works")
```

---

### 0.6 Configuration Management

**.env file:**
```bash
# API Keys
TRADING_212_API_KEY=your_key
EXA_API_KEY=your_key
FIRECRAWL_API_KEY=your_key
OPENROUTER_API_KEY=your_key
PERPLEXITY_API_KEY=your_key
COMPOSIO_API_KEY=your_key

# Database
NEON_CONNECTION_STRING=postgresql://user:pass@host/db
PINECONE_API_KEY=your_key
PINECONE_ENVIRONMENT=gcp-starter

# Notifications
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Risk Tolerance
MAX_POSITION_SIZE_PCT=25.0
MAX_PORTFOLIO_VAR_PCT=10.0
MAX_LOSS_PER_TRADE_PCT=5.0

# Budget Limits
DAILY_BUDGET_USD=0.50
MONTHLY_BUDGET_USD=30.00
```

---

### 0.7 Deliverables (End of Week 1)

- [x] All APIs tested and working
- [x] Database schema deployed to Neon
- [x] Pinecone index created
- [x] Project structure established
- [x] Configuration management in place
- [x] Cost tracking system ready

**Cost:** Minimal (free tiers, setup time only)

---

## Phase 1: MVP (3-Agent System)

**Duration:** Weeks 2-3 (10-14 days)
**Goal:** Deliver basic daily recommendations with 3 core agents

### 1.1 Scope

**Included Agents:**
1. ✅ Portfolio Analyst
2. ✅ Market Analyst
3. ✅ Orchestrator (Basic)

**Excluded (Phase 2+):**
- News Monitor
- Technical Analyst
- Risk Manager (hardcoded rules only)

**Capabilities:**
- Daily portfolio health assessment
- Macro market sentiment
- Basic buy/sell/hold recommendations
- Email notifications

---

### 1.2 Implementation Tasks

**Week 2: Core Agent Development**

**Day 1-2: Portfolio Analyst**
```python
# agents/portfolio_analyst.py
class PortfolioAnalyst:
    def __init__(self):
        self.llm = LLMRouter()
        self.model = "openai/gpt-4o-mini"

    def analyze(self, portfolio_data):
        """
        Input: 212 Trading API portfolio
        Output: Health score, concentration risk, rebalancing suggestions
        """
        prompt = self.generate_prompt(portfolio_data)
        response = self.llm.call(self.model, prompt)
        result = json.loads(response)

        # Store in Neon
        self.store_output(result)

        return result
```

**Test:**
```bash
pytest tests/test_agents.py::test_portfolio_analyst
```

---

**Day 3-4: Market Analyst**
```python
# agents/market_analyst.py
class MarketAnalyst:
    def __init__(self):
        self.llm = LLMRouter()
        self.model = "anthropic/claude-3-5-sonnet-20241022"
        self.data_fetcher = MarketDataFetcher()

    def analyze(self):
        """
        Input: Market indices, sector performance
        Output: Market sentiment, confidence, sector trends
        """
        # Fetch market data (Yahoo Finance - free)
        market_data = self.data_fetcher.get_market_overview()

        # Check Pinecone for similar historical conditions
        historical = self.query_pinecone(market_data)

        # LLM analysis
        prompt = self.generate_prompt(market_data, historical)
        response = self.llm.call(self.model, prompt)
        result = json.loads(response)

        # Store in Neon + Pinecone
        self.store_output(result)

        return result
```

**Test:**
```bash
pytest tests/test_agents.py::test_market_analyst
```

---

**Day 5-6: Basic Orchestrator**
```python
# agents/orchestrator.py
class Orchestrator:
    def __init__(self):
        self.llm = LLMRouter()
        self.model = "anthropic/claude-3-5-sonnet-20241022"

    def make_decision(self, portfolio_output, market_output, portfolio_data):
        """
        Input: Portfolio Analyst + Market Analyst outputs
        Output: Final recommendations
        """
        # Basic risk check (hardcoded for MVP)
        risk_check = self.basic_risk_check(portfolio_data)

        # Aggregate recommendations
        prompt = self.generate_prompt(portfolio_output, market_output, risk_check)
        response = self.llm.call(self.model, prompt)
        result = json.loads(response)

        # Store in Neon
        self.store_recommendations(result)

        return result

    def basic_risk_check(self, portfolio_data):
        """Simple rule-based risk checks (Phase 1 only)"""
        checks = {
            "max_position_exceeded": False,
            "high_concentration": False
        }

        for position in portfolio_data['positions']:
            pct = (position['market_value'] / portfolio_data['total_value']) * 100
            if pct > 35:
                checks["high_concentration"] = True

        return checks
```

---

**Day 7-8: Data Fetchers**
```python
# data/fetchers/trading_212.py
class Trading212Client:
    def get_portfolio(self):
        """Fetch current portfolio from 212 API"""
        response = requests.get(
            "https://live.trading212.com/api/v0/equity/portfolio",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self.parse_portfolio(response.json())

# data/fetchers/market_data.py
class MarketDataFetcher:
    def get_market_overview(self):
        """Fetch market data from Yahoo Finance (free)"""
        indices = ['^GSPC', '^IXIC', '^VIX']
        data = {}
        for symbol in indices:
            ticker = yf.Ticker(symbol)
            data[symbol] = ticker.info
        return self.format_market_data(data)
```

---

**Day 9-10: Notification System**
```python
# notifications/email_sender.py
def send_daily_email(recommendations, market_summary, portfolio_summary):
    subject = f"[DAILY ANALYSIS] {len(recommendations)} Items"

    body = format_email_html(recommendations, market_summary, portfolio_summary)

    # Via Composio
    composio.execute_action(
        action="GMAIL_SEND_EMAIL",
        params={
            "to": os.getenv("NOTIFICATION_EMAIL"),
            "subject": subject,
            "body": body
        }
    )

# notifications/telegram_sender.py
def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    )
```

---

**Week 3: Integration & Testing**

**Day 11-12: Main Orchestrator Loop**
```python
# main.py
def run_daily_analysis():
    """Main entry point for daily analysis"""
    logger.info("Starting daily analysis...")

    try:
        # 1. Fetch portfolio
        portfolio = trading_212.get_portfolio()
        logger.info(f"Portfolio value: ${portfolio['total_value']}")

        # 2. Run agents in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            portfolio_future = executor.submit(portfolio_analyst.analyze, portfolio)
            market_future = executor.submit(market_analyst.analyze)

            portfolio_output = portfolio_future.result()
            market_output = market_future.result()

        # 3. Orchestrator makes final decision
        recommendations = orchestrator.make_decision(
            portfolio_output,
            market_output,
            portfolio
        )

        # 4. Send notifications
        send_daily_email(recommendations)
        send_telegram(format_telegram_summary(recommendations))

        logger.info("Daily analysis complete")

        return recommendations

    except Exception as e:
        logger.error(f"Daily analysis failed: {e}")
        send_telegram(f"⚠️ System error: {e}")
        raise

if __name__ == "__main__":
    run_daily_analysis()
```

---

**Day 13-14: Testing & Debugging**

**Integration Tests:**
```python
# tests/test_integration.py
def test_end_to_end_flow():
    """Test full MVP flow"""
    # 1. Mock portfolio data
    portfolio = load_test_portfolio()

    # 2. Run analysis
    recommendations = run_daily_analysis()

    # 3. Verify output
    assert len(recommendations) > 0
    assert all('confidence' in r for r in recommendations)
    assert all(0 <= r['confidence'] <= 100 for r in recommendations)

def test_cost_tracking():
    """Verify cost tracking works"""
    run_daily_analysis()

    # Check cost log
    cost = neon.query("SELECT SUM(cost) FROM cost_log WHERE date = CURRENT_DATE")
    assert cost < 0.50  # Daily budget limit
```

---

### 1.3 Deployment (MVP)

**Scheduling (Cron or Cloud Function):**
```bash
# Option 1: Linux cron (if running on VPS)
crontab -e
# Add: 0 9 * * 1-5 /path/to/venv/bin/python /path/to/main.py

# Option 2: Google Cloud Scheduler (recommended)
gcloud scheduler jobs create http daily-analysis \
    --schedule="0 9 * * 1-5" \
    --uri="https://your-cloud-function-url/run" \
    --time-zone="Europe/Berlin"
```

---

### 1.4 MVP Success Criteria

**Functional:**
- [x] Runs successfully every trading day at 9 AM CET
- [x] Generates portfolio health assessment
- [x] Provides market sentiment
- [x] Delivers at least 1 actionable recommendation
- [x] Sends email + Telegram notification

**Performance:**
- [x] Completes in < 90 seconds
- [x] Daily cost < $0.20
- [x] No API failures for 5 consecutive days

**Quality:**
- [x] Recommendations are logical (verified manually)
- [x] No system crashes or errors
- [x] User can act on recommendations

---

### 1.5 Deliverables (End of Week 3)

- [x] Working 3-agent MVP
- [x] Daily email + Telegram notifications
- [x] Cost tracking operational
- [x] Database logging functional
- [x] 5+ days of successful runs

**Estimated Cost:** $0.10-0.15/day = $3-4.50/month

---

## Phase 2: Enhanced Analysis

**Duration:** Weeks 4-5 (10-14 days)
**Goal:** Add News Monitor and Technical Analyst for richer insights

### 2.1 Scope

**New Agents:**
1. ✅ News & Sentiment Monitor
2. ✅ Technical Analyst

**Enhanced Capabilities:**
- Company-specific news sentiment
- Technical chart analysis (RSI, MACD, support/resistance)
- Higher confidence recommendations (more data points)

---

### 2.2 Implementation Tasks

**Week 4: News Monitor**

**Day 15-17: News Data Fetcher**
```python
# data/fetchers/news_data.py
class NewsDataFetcher:
    def __init__(self):
        self.rss_feeds = RSSAggregator(['marketwatch', 'cnbc'])
        self.exa = ExaClient()
        self.google = ComposioGoogleSearch()

    def fetch_news(self, ticker, company_name):
        """Tiered news fetching (free → premium)"""

        # TIER 1: Free RSS feeds
        rss_news = self.rss_feeds.fetch(ticker)

        # TIER 2: Google Search via Composio (free)
        if not rss_news or len(rss_news) < 3:
            google_news = self.google.search(f"{company_name} stock news today")
            rss_news.extend(google_news)

        # TIER 3: Exa (only if breaking news detected)
        if self.detect_breaking_news(rss_news):
            logger.info(f"Breaking news detected for {ticker}, using Exa")
            exa_news = self.exa.search(
                query=f"{company_name} breaking news latest",
                type="neural",
                num_results=10
            )
            return exa_news

        return rss_news[:10]  # Limit to 10 items
```

**Day 18-19: News Monitor Agent**
```python
# agents/news_monitor.py
class NewsMonitor:
    def analyze(self, ticker, company_name):
        """Analyze news sentiment for a company"""

        # Fetch news
        news = self.news_fetcher.fetch_news(ticker, company_name)

        # Check Pinecone for historical sentiment
        historical = self.query_pinecone(ticker, news)

        # LLM analysis
        prompt = self.generate_prompt(ticker, news, historical)
        response = self.llm.call(self.model, prompt)
        result = json.loads(response)

        # Store in Neon + Pinecone
        self.store_output(ticker, result)

        return result
```

---

**Week 4-5: Technical Analyst**

**Day 20-22: Technical Data Fetcher**
```python
# data/fetchers/technical_data.py
class TechnicalDataFetcher:
    def fetch_technical_data(self, ticker):
        """Fetch price data and calculate indicators"""

        # Fetch historical data (yfinance - free)
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")

        # Calculate indicators locally (free)
        indicators = {
            "rsi_14": self.calculate_rsi(hist['Close'], 14),
            "macd": self.calculate_macd(hist['Close']),
            "ma_50": hist['Close'].rolling(50).mean().iloc[-1],
            "ma_200": hist['Close'].rolling(200).mean().iloc[-1],
            "volume_avg_20": hist['Volume'].rolling(20).mean().iloc[-1]
        }

        # Support/resistance (simple approach)
        support_resistance = self.find_support_resistance(hist)

        return {
            "current_price": hist['Close'].iloc[-1],
            "indicators": indicators,
            "support_resistance": support_resistance,
            "price_history": {
                "1d_change_pct": self.calc_change(hist, 1),
                "5d_change_pct": self.calc_change(hist, 5),
                "1m_change_pct": self.calc_change(hist, 21)
            }
        }

    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs.iloc[-1]))
```

**Day 23-24: Technical Analyst Agent**
```python
# agents/technical_analyst.py
class TechnicalAnalyst:
    def analyze(self, ticker):
        """Analyze technical indicators and generate signals"""

        # Fetch technical data
        tech_data = self.tech_fetcher.fetch_technical_data(ticker)

        # LLM analysis
        prompt = self.generate_prompt(ticker, tech_data)
        response = self.llm.call(self.model, prompt)
        result = json.loads(response)

        # Store in Neon
        self.store_output(ticker, result)

        return result
```

---

**Day 25-28: Integration & Testing**

**Update Orchestrator:**
```python
# agents/orchestrator.py (Phase 2 version)
class Orchestrator:
    def make_decision(self, portfolio_output, market_output, news_outputs, technical_outputs, portfolio_data):
        """Enhanced decision with 4 agents"""

        # Aggregate all inputs
        all_agent_outputs = {
            "portfolio": portfolio_output,
            "market": market_output,
            "news": news_outputs,  # Dict keyed by ticker
            "technical": technical_outputs  # Dict keyed by ticker
        }

        # Basic risk check (still hardcoded for Phase 2)
        risk_check = self.basic_risk_check(portfolio_data, all_agent_outputs)

        # Weighted voting
        recommendations = self.weighted_voting(all_agent_outputs, risk_check)

        # Store in Neon
        self.store_recommendations(recommendations)

        return recommendations

    def weighted_voting(self, outputs, risk_check):
        """Weight agent recommendations by confidence"""

        recommendations = []

        for ticker in outputs['news'].keys():
            # Aggregate signals
            market_sentiment = outputs['market']['market_sentiment']
            market_confidence = outputs['market']['confidence']

            news_sentiment = outputs['news'][ticker]['overall_sentiment']
            news_confidence = outputs['news'][ticker]['confidence']

            tech_signal = outputs['technical'][ticker]['signal']
            tech_confidence = outputs['technical'][ticker]['confidence']

            # Weighted voting
            buy_score = 0
            sell_score = 0
            hold_score = 0

            if tech_signal in ['STRONG_BUY', 'BUY']:
                buy_score += tech_confidence
            elif tech_signal in ['STRONG_SELL', 'SELL']:
                sell_score += tech_confidence
            else:
                hold_score += tech_confidence

            # ... (aggregate market + news signals similarly)

            # Determine final action
            if buy_score > sell_score and buy_score > hold_score:
                action = "BUY"
                confidence = buy_score / (buy_score + sell_score + hold_score) * 100
            elif sell_score > buy_score and sell_score > hold_score:
                action = "SELL"
                confidence = sell_score / (buy_score + sell_score + hold_score) * 100
            else:
                action = "HOLD"
                confidence = hold_score / (buy_score + sell_score + hold_score) * 100

            # Risk check override
            if risk_check.get('high_concentration') and action == "BUY":
                action = "HOLD"
                confidence = 50
                logger.warning(f"Risk override: Blocking BUY for {ticker} due to concentration")

            recommendations.append({
                "ticker": ticker,
                "action": action,
                "confidence": int(confidence),
                "reasoning": self.generate_reasoning(outputs, ticker, action)
            })

        return recommendations
```

---

### 2.3 Deliverables (End of Week 5)

- [x] News Monitor operational (RSS + Exa fallback)
- [x] Technical Analyst operational (free data sources)
- [x] Enhanced orchestrator with 4-agent voting
- [x] Higher confidence recommendations
- [x] 5+ days of successful runs

**Estimated Cost:** $0.15-0.25/day = $4.50-7.50/month

---

## Phase 3: Full 6-Agent System

**Duration:** Weeks 6-7 (10-14 days)
**Goal:** Complete system with Risk Manager and advanced Orchestrator

### 3.1 Scope

**New Agents:**
1. ✅ Risk Manager (Full Implementation)
2. ✅ Orchestrator (Advanced Features)

**Enhanced Capabilities:**
- Position sizing calculations
- Stop-loss and take-profit levels
- Risk override authority
- Self-reflection (Orchestrator critiques own decisions)

---

### 3.2 Implementation Tasks

**Week 6: Risk Manager**

**Day 29-31: Risk Manager Agent**
```python
# agents/risk_manager.py
class RiskManager:
    def __init__(self):
        self.llm = LLMRouter()
        self.model = "anthropic/claude-3-haiku-20240307"  # Cheap + fast

    def validate(self, recommendations, portfolio_data, market_output):
        """Validate all recommendations against risk rules"""

        # Calculate portfolio VAR
        portfolio_var = self.calculate_var(portfolio_data, market_output)

        validations = []

        for rec in recommendations:
            # Position sizing
            position_size = self.calculate_position_size(rec, portfolio_data)

            # Stop loss
            stop_loss = self.calculate_stop_loss(rec, portfolio_data)

            # Risk-reward ratio
            risk_reward = self.calculate_risk_reward(rec, stop_loss)

            # Decision: APPROVE, MODIFY, REJECT
            decision = self.make_risk_decision(
                rec,
                position_size,
                portfolio_var,
                risk_reward
            )

            validations.append({
                "ticker": rec['ticker'],
                "original_action": rec['action'],
                "risk_decision": decision['status'],
                "adjusted_quantity": decision.get('adjusted_quantity'),
                "stop_loss": stop_loss,
                "take_profit": decision.get('take_profit'),
                "reasoning": decision['reasoning']
            })

        result = {
            "risk_assessment": self.overall_assessment(validations),
            "portfolio_var_pct": portfolio_var,
            "validations": validations
        }

        # Store in Neon
        self.store_output(result)

        return result

    def calculate_var(self, portfolio, market):
        """Simplified Value-at-Risk calculation"""
        # This is a simplified version
        # Production would use historical volatility
        volatility = 0.15 if market['volatility_assessment'] == 'MODERATE' else 0.25
        var_99 = portfolio['total_value'] * volatility * 2.33
        return (var_99 / portfolio['total_value']) * 100

    def make_risk_decision(self, rec, position_size_pct, portfolio_var, risk_reward):
        """Decide APPROVE, MODIFY, or REJECT"""

        # REJECT conditions
        if position_size_pct > 25:
            return {
                "status": "REJECTED",
                "reasoning": f"Position size ({position_size_pct}%) exceeds 25% limit"
            }

        if portfolio_var > 10:
            return {
                "status": "REJECTED",
                "reasoning": f"Portfolio VAR ({portfolio_var}%) exceeds 10% threshold"
            }

        if risk_reward < 2:
            return {
                "status": "MODIFIED",
                "adjusted_quantity": int(rec.get('quantity', 0) * 0.5),
                "reasoning": f"Risk-reward ratio ({risk_reward}) < 2:1, reducing position size 50%"
            }

        # APPROVE
        return {
            "status": "APPROVED",
            "reasoning": "All risk checks passed"
        }
```

---

**Week 6-7: Advanced Orchestrator**

**Day 32-35: Self-Reflection & Advanced Decision Making**
```python
# agents/orchestrator.py (Phase 3 version)
class Orchestrator:
    def make_decision(self, all_agent_outputs, portfolio_data):
        """Full 6-agent decision making with self-reflection"""

        # Stage 1: Aggregate all agent inputs
        initial_recommendations = self.weighted_voting(all_agent_outputs)

        # Stage 2: Risk Manager validation
        risk_output = all_agent_outputs['risk_manager']

        # Apply risk decisions
        final_recommendations = self.apply_risk_decisions(
            initial_recommendations,
            risk_output
        )

        # Stage 3: Self-reflection (inspired by TradingGroup research)
        critique = self.self_reflect(final_recommendations, all_agent_outputs)

        if critique['suggests_revision']:
            logger.info("Self-reflection suggests revision, adjusting recommendations")
            final_recommendations = self.revise_based_on_critique(
                final_recommendations,
                critique
            )

        # Store in Neon
        self.store_recommendations(final_recommendations)

        return final_recommendations

    def self_reflect(self, recommendations, all_outputs):
        """Critique own decisions before finalizing"""

        prompt = f"""
You are reviewing your own trading recommendations. Critique them honestly:

Recommendations:
{json.dumps(recommendations, indent=2)}

Agent Inputs:
{json.dumps(all_outputs, indent=2)}

Questions to ask yourself:
1. Did I weight agent confidence scores correctly?
2. Are there contradictions I missed?
3. Is market context adequately considered?
4. What could go wrong with each recommendation?
5. Am I being too aggressive or too conservative?

Output JSON:
{{
  "suggests_revision": boolean,
  "concerns": ["string"],
  "recommended_changes": [
    {{"ticker": "string", "change": "string", "rationale": "string"}}
  ],
  "overall_confidence_adjustment": -20 to +20 (integer)
}}
"""

        response = self.llm.call(self.model, prompt)
        return json.loads(response)
```

---

**Day 36-42: Integration, Testing, Bug Fixes**

**Full System Integration:**
```python
# main.py (Phase 3 version)
def run_daily_analysis():
    """Complete 6-agent system"""

    # 1. Fetch portfolio
    portfolio = trading_212.get_portfolio()

    # 2. Stage 1: Parallel agent execution
    with concurrent.futures.ThreadPoolExecutor() as executor:
        portfolio_future = executor.submit(portfolio_analyst.analyze, portfolio)
        market_future = executor.submit(market_analyst.analyze)

        # News and Technical for each stock in portfolio
        tickers = [p['ticker'] for p in portfolio['positions']]
        news_futures = {t: executor.submit(news_monitor.analyze, t, get_company_name(t)) for t in tickers}
        tech_futures = {t: executor.submit(technical_analyst.analyze, t) for t in tickers}

        # Collect results
        portfolio_output = portfolio_future.result()
        market_output = market_future.result()
        news_outputs = {t: f.result() for t, f in news_futures.items()}
        tech_outputs = {t: f.result() for t, f in tech_futures.items()}

    # 3. Stage 2: Risk Manager
    all_outputs = {
        "portfolio": portfolio_output,
        "market": market_output,
        "news": news_outputs,
        "technical": tech_outputs
    }

    # Generate initial recommendations
    initial_recs = orchestrator.generate_initial_recommendations(all_outputs)

    # Risk Manager validates
    risk_output = risk_manager.validate(initial_recs, portfolio, market_output)
    all_outputs["risk_manager"] = risk_output

    # 4. Stage 3: Final Orchestrator decision
    final_recommendations = orchestrator.make_decision(all_outputs, portfolio)

    # 5. Notifications
    send_daily_email(final_recommendations, market_output, portfolio_output)
    send_telegram(format_telegram(final_recommendations))

    return final_recommendations
```

---

### 3.3 Deliverables (End of Week 7)

- [x] Full 6-agent system operational
- [x] Risk Manager with override authority
- [x] Advanced Orchestrator with self-reflection
- [x] Position sizing and stop-loss calculations
- [x] 10+ days of successful production runs

**Estimated Cost:** $0.20-0.30/day = $6-9/month

---

## Phase 4: Learning & Optimization

**Duration:** Weeks 8-10 (3 weeks)
**Goal:** Implement feedback loops and performance tracking

### 4.1 Scope

**Learning Systems:**
1. ✅ Recommendation accuracy tracking
2. ✅ Agent performance analytics
3. ✅ Market regime detection
4. ✅ Adaptive confidence scoring

---

### 4.2 Implementation Tasks

**Week 8: Feedback Loop**

**Recommendation Outcome Tracking:**
```python
# utils/outcome_tracker.py
class OutcomeTracker:
    def track_recommendation(self, recommendation_id):
        """Track recommendation outcome after 7 days"""

        # Get recommendation
        rec = neon.query("""
            SELECT * FROM final_recommendations
            WHERE id = %s
        """, (recommendation_id,))

        # Get current price (7 days later)
        ticker = rec['ticker']
        current_price = self.get_current_price(ticker)

        # Calculate outcome
        if rec['action'] == 'BUY':
            # If we recommended BUY, success = price went up
            profit_loss_pct = ((current_price - rec['entry_price']) / rec['entry_price']) * 100
        elif rec['action'] == 'SELL':
            # If we recommended SELL, success = price went down
            profit_loss_pct = ((rec['entry_price'] - current_price) / rec['entry_price']) * 100
        else:
            profit_loss_pct = 0

        # Accuracy score (0-100)
        accuracy = self.calculate_accuracy(rec, profit_loss_pct)

        # Update database
        neon.execute("""
            UPDATE final_recommendations
            SET outcome_price = %s, profit_loss = %s, accuracy_score = %s
            WHERE id = %s
        """, (current_price, profit_loss_pct, accuracy, recommendation_id))

    def calculate_accuracy(self, rec, profit_loss_pct):
        """
        Accuracy scoring:
        - If confidence was high and outcome was good: high accuracy
        - If confidence was low but outcome was bad anyway: medium accuracy
        - If confidence was high but outcome was bad: low accuracy
        """
        if rec['action'] == 'HOLD':
            return 50  # Neutral

        expected_direction = 1 if rec['action'] == 'BUY' else -1
        actual_direction = 1 if profit_loss_pct > 0 else -1

        if expected_direction == actual_direction:
            # Correct direction
            return min(100, 50 + abs(profit_loss_pct) * 5)  # Up to 100
        else:
            # Wrong direction
            return max(0, 50 - abs(profit_loss_pct) * 5)  # Down to 0

# Cron job: Run daily to track 7-day-old recommendations
def track_old_recommendations():
    recs = neon.query("""
        SELECT id FROM final_recommendations
        WHERE date = CURRENT_DATE - INTERVAL '7 days'
        AND outcome_price IS NULL
    """)

    for rec in recs:
        outcome_tracker.track_recommendation(rec['id'])
```

---

**Agent Performance Analytics:**
```python
# utils/agent_analytics.py
class AgentAnalytics:
    def calculate_agent_performance(self, agent_name, month):
        """Calculate agent performance metrics"""

        # Get all recommendations where this agent contributed
        query = """
            SELECT
                fr.id,
                fr.confidence,
                fr.action,
                fr.profit_loss,
                fr.accuracy_score,
                ao.output_json->>'confidence' as agent_confidence
            FROM final_recommendations fr
            JOIN agent_outputs ao ON ao.date = fr.date
            WHERE ao.agent_name = %s
            AND fr.date >= %s
            AND fr.date < %s + INTERVAL '1 month'
            AND fr.outcome_price IS NOT NULL
        """

        results = neon.query(query, (agent_name, month, month))

        # Calculate metrics
        total_recs = len(results)
        avg_confidence = np.mean([r['agent_confidence'] for r in results])
        avg_accuracy = np.mean([r['accuracy_score'] for r in results])
        sharpe_ratio = self.calculate_sharpe(results)

        # Store in database
        neon.execute("""
            INSERT INTO agent_performance (agent_name, month, total_recommendations, avg_confidence, avg_accuracy, sharpe_ratio)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (agent_name, month, total_recs, avg_confidence, avg_accuracy, sharpe_ratio))

        return {
            "agent": agent_name,
            "month": month,
            "total_recommendations": total_recs,
            "avg_confidence": avg_confidence,
            "avg_accuracy": avg_accuracy,
            "sharpe_ratio": sharpe_ratio
        }
```

---

**Week 9-10: Adaptive Learning**

**Market Regime Detection:**
```python
# utils/market_regime.py
class MarketRegimeDetector:
    def detect_regime(self, market_data):
        """Detect current market regime based on historical patterns"""

        # Query Pinecone for similar market conditions
        current_embedding = generate_embedding(market_data)
        similar_conditions = pinecone.query(
            namespace="market_conditions",
            query_embedding=current_embedding,
            top_k=20,
            include_metadata=True
        )

        # Cluster similar conditions
        regimes = {
            "bullish_low_vol": 0,
            "bullish_high_vol": 0,
            "bearish_low_vol": 0,
            "bearish_high_vol": 0,
            "neutral": 0
        }

        for match in similar_conditions:
            sentiment = match['metadata']['sentiment']
            vix = match['metadata']['vix']

            if sentiment == 'BULLISH' and vix < 20:
                regimes["bullish_low_vol"] += match['score']
            elif sentiment == 'BULLISH' and vix >= 20:
                regimes["bullish_high_vol"] += match['score']
            elif sentiment == 'BEARISH' and vix < 30:
                regimes["bearish_low_vol"] += match['score']
            elif sentiment == 'BEARISH' and vix >= 30:
                regimes["bearish_high_vol"] += match['score']
            else:
                regimes["neutral"] += match['score']

        # Most likely regime
        current_regime = max(regimes, key=regimes.get)

        # Get best performing agents in this regime
        best_agents = self.get_best_agents_for_regime(current_regime)

        return {
            "regime": current_regime,
            "confidence": regimes[current_regime] / sum(regimes.values()),
            "best_agents": best_agents
        }

    def get_best_agents_for_regime(self, regime):
        """Which agents perform best in this market regime?"""

        # Query historical performance
        query = """
            SELECT agent_name, AVG(avg_accuracy) as accuracy
            FROM agent_performance ap
            JOIN market_conditions mc ON mc.month = ap.month
            WHERE mc.regime = %s
            GROUP BY agent_name
            ORDER BY accuracy DESC
        """

        return neon.query(query, (regime,))
```

**Adaptive Confidence Weighting:**
```python
# agents/orchestrator.py (Phase 4 enhancement)
class Orchestrator:
    def weighted_voting(self, all_outputs):
        """Weight votes by agent performance in current market regime"""

        # Detect market regime
        regime = market_regime_detector.detect_regime(all_outputs['market'])

        # Get agent performance in this regime
        agent_weights = {}
        for agent_name in ['market_analyst', 'news_monitor', 'technical_analyst']:
            performance = agent_analytics.get_agent_performance_in_regime(
                agent_name,
                regime['regime']
            )
            # Weight = base confidence × performance multiplier
            agent_weights[agent_name] = performance['avg_accuracy'] / 100

        # Apply adaptive weights to voting
        for rec in recommendations:
            # Market Analyst vote
            market_vote = all_outputs['market']['confidence'] * agent_weights['market_analyst']

            # News Monitor vote
            news_vote = all_outputs['news'][rec['ticker']]['confidence'] * agent_weights['news_monitor']

            # Technical Analyst vote
            tech_vote = all_outputs['technical'][rec['ticker']]['confidence'] * agent_weights['technical_analyst']

            # Weighted final confidence
            rec['adjusted_confidence'] = (market_vote + news_vote + tech_vote) / 3

        return recommendations
```

---

### 4.3 Deliverables (End of Week 10)

- [x] Recommendation outcome tracking operational
- [x] Agent performance analytics dashboard (SQL queries)
- [x] Market regime detection
- [x] Adaptive confidence weighting
- [x] Monthly performance reports

**Estimated Cost:** Same as Phase 3 ($6-9/month)

---

## Phase 5: Production Hardening

**Duration:** Weeks 11-12 (2 weeks)
**Goal:** Error handling, monitoring, documentation

### 5.1 Scope

**Production Readiness:**
1. ✅ Comprehensive error handling
2. ✅ Monitoring dashboards
3. ✅ Alerting system
4. ✅ Documentation
5. ✅ Backup/recovery procedures

---

### 5.2 Implementation Tasks

**Error Handling:**
```python
# utils/error_handler.py
class SystemErrorHandler:
    def __init__(self):
        self.alert_threshold = 3  # Alert after 3 failures

    def handle_agent_failure(self, agent_name, error):
        """Handle individual agent failures gracefully"""

        logger.error(f"Agent {agent_name} failed: {error}")

        # Log to database
        neon.execute("""
            INSERT INTO system_health (component, status, error_message)
            VALUES (%s, 'failed', %s)
        """, (agent_name, str(error)))

        # Check failure count
        failure_count = self.get_failure_count(agent_name, days=7)

        if failure_count >= self.alert_threshold:
            # Send urgent alert
            send_telegram(f"⚠️ CRITICAL: {agent_name} has failed {failure_count} times in past week")

        # Attempt graceful degradation
        return self.graceful_degradation(agent_name)

    def graceful_degradation(self, failed_agent):
        """Continue with reduced capabilities"""

        fallback_strategies = {
            "market_analyst": "Use cached market sentiment from yesterday",
            "news_monitor": "Skip news analysis for today",
            "technical_analyst": "Use simple price-based signals",
            "risk_manager": "Use conservative hardcoded risk limits",
            "orchestrator": "Default to HOLD for all positions"
        }

        return fallback_strategies.get(failed_agent, "Skip this component")
```

**Monitoring Dashboard:**
```sql
-- System Health Dashboard Queries

-- Daily cost summary
CREATE VIEW v_daily_cost AS
SELECT
    date,
    SUM(CASE WHEN component LIKE 'llm%' THEN cost ELSE 0 END) as llm_cost,
    SUM(CASE WHEN component LIKE 'exa%' THEN cost ELSE 0 END) as exa_cost,
    SUM(cost) as total_cost
FROM cost_log
GROUP BY date
ORDER BY date DESC;

-- Agent success rate
CREATE VIEW v_agent_success_rate AS
SELECT
    component,
    COUNT(*) as total_runs,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct
FROM system_health
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY component;

-- Recommendation accuracy over time
CREATE VIEW v_recommendation_accuracy AS
SELECT
    DATE_TRUNC('week', date) as week,
    COUNT(*) as total_recommendations,
    AVG(accuracy_score) as avg_accuracy,
    COUNT(CASE WHEN action = 'BUY' THEN 1 END) as buy_count,
    COUNT(CASE WHEN action = 'SELL' THEN 1 END) as sell_count
FROM final_recommendations
WHERE outcome_price IS NOT NULL
GROUP BY week
ORDER BY week DESC;
```

**Documentation:**
```markdown
# README.md

## Multi-Agent Trading System

### Quick Start
1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` file with API keys
4. Run database migrations: `psql < database/schema.sql`
5. Test APIs: `python tests/test_apis.py`
6. Run daily analysis: `python main.py`

### Architecture
- 6 specialized agents (Portfolio, Market, News, Technical, Risk, Orchestrator)
- Hybrid data fetching (free sources + premium APIs)
- Cost-optimized LLM routing via OpenRouter
- Shared memory via Neon PostgreSQL + Pinecone

### Daily Workflow
09:00 CET: System runs automatically
- Fetches portfolio from 212 API
- Runs 6 agents in parallel
- Generates recommendations
- Sends email + Telegram notification

### Cost Monitoring
- Daily budget: $0.50
- Monthly budget: $30
- Alerts triggered if exceeded

### Troubleshooting
- Check logs: `tail -f logs/system.log`
- Database status: `SELECT * FROM v_agent_success_rate`
- Cost tracking: `SELECT * FROM v_daily_cost WHERE date > CURRENT_DATE - 7`
```

---

### 5.3 Deliverables (End of Week 12)

- [x] Comprehensive error handling
- [x] Monitoring dashboard (SQL views)
- [x] Alert system for failures + cost overruns
- [x] Complete documentation
- [x] Backup procedures
- [x] Production deployment

**System Status:** PRODUCTION-READY ✅

---

## Risk Mitigation Strategies

### 1. API Failures
**Risk:** 212 API, Exa, or OpenRouter unavailable
**Mitigation:**
- Implement retry logic with exponential backoff
- Cache previous day's portfolio data
- Graceful degradation (use cached/free sources)
- Alert user via Telegram if critical APIs down

### 2. Cost Overruns
**Risk:** Unexpected high API usage exceeds budget
**Mitigation:**
- Hard daily budget limit ($0.50)
- Circuit breaker halts operations if exceeded
- Cost alerts at 75% of monthly budget
- Free sources as primary data layer

### 3. Bad Recommendations
**Risk:** System recommends unprofitable trades
**Mitigation:**
- Risk Manager override authority
- Position sizing limits (max 25% per stock)
- Stop-loss requirements
- User always makes final execution decision
- Track recommendation accuracy, adjust agent weights

### 4. Market Crashes (Black Swan Events)
**Risk:** Unexpected market crash invalidates normal analysis
**Mitigation:**
- VIX threshold detection (> 40 = panic mode)
- Risk Manager can halt all recommendations
- Urgent Telegram alerts
- Conservative default: HOLD in extreme volatility

### 5. Data Quality Issues
**Risk:** Free data sources provide stale/incorrect data
**Mitigation:**
- Timestamp validation (reject data > 1 hour old)
- Cross-reference multiple sources
- Upgrade to premium APIs if free sources fail 3x
- Log all data quality issues for review

---

## Success Metrics

### Functional Metrics
- **Uptime:** > 95% (system runs successfully 95%+ of trading days)
- **Latency:** < 120 seconds (full analysis completes in under 2 minutes)
- **Notification Delivery:** 100% (email + Telegram always delivered)

### Cost Metrics
- **Daily Cost:** < $0.50 (stay within budget)
- **Monthly Cost:** < $30
- **Cost Per Recommendation:** < $0.10

### Quality Metrics
- **Recommendation Accuracy:** > 60% (better than random)
- **Agent Consensus Rate:** > 70% (agents agree most of the time)
- **Risk Override Rate:** < 20% (Risk Manager blocks < 20% of recommendations)

### Business Metrics
- **Time Saved:** 5-10 hours/month (vs. manual research)
- **User Satisfaction:** Recommendations are actionable and logical
- **ROI:** Positive (system pays for itself through better decisions)

---

## Deployment Checklist

### Pre-Launch
- [ ] All API keys configured in `.env`
- [ ] Database schema deployed to Neon
- [ ] Pinecone index created
- [ ] All integration tests passing
- [ ] Cost tracking operational
- [ ] Notifications tested (email + Telegram)
- [ ] Error handling tested

### Launch Day
- [ ] Schedule daily cron job (09:00 CET)
- [ ] Run first production analysis
- [ ] Verify email + Telegram delivery
- [ ] Check cost log (should be < $0.30)
- [ ] Monitor for errors

### First Week
- [ ] Daily monitoring of system health
- [ ] Verify cost staying within budget
- [ ] Collect user feedback on recommendation quality
- [ ] Adjust agent prompts if needed

### First Month
- [ ] Review agent performance analytics
- [ ] Analyze recommendation accuracy
- [ ] Optimize LLM model choices
- [ ] Consider cost optimizations

---

## Conclusion

This phased roadmap delivers a production-ready multi-agent trading system in **8-12 weeks**, starting with a 3-agent MVP in Week 3 and progressively adding capabilities. Each phase is designed to provide incremental value while managing risk and cost.

**Next Steps:**
1. Complete Phase 0 (Infrastructure Setup) - Week 1
2. Build MVP (3-Agent System) - Weeks 2-3
3. Enhance with News + Technical agents - Weeks 4-5
4. Complete with Risk Manager - Weeks 6-7
5. Add learning systems - Weeks 8-10
6. Production hardening - Weeks 11-12

**Final System Cost:** $22-30/month
**Final System Value:** 5-10 hours/month saved + improved trading decisions

---

**END OF ROADMAP**
