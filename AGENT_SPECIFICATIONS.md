# Agent Specifications: Multi-Agent Trading System

**Version:** 1.0
**Date:** November 17, 2025
**System:** Daily Stock Market Monitoring & Trading Recommendations

---

## Table of Contents

1. [Agent Overview](#1-agent-overview)
2. [Agent 1: Portfolio Analyst](#2-agent-1-portfolio-analyst)
3. [Agent 2: Market Analyst](#3-agent-2-market-analyst)
4. [Agent 3: News & Sentiment Monitor](#4-agent-3-news--sentiment-monitor)
5. [Agent 4: Technical Analyst](#5-agent-4-technical-analyst)
6. [Agent 5: Risk Manager](#6-agent-5-risk-manager)
7. [Agent 6: Execution Strategist (Orchestrator)](#7-agent-6-execution-strategist-orchestrator)
8. [Inter-Agent Communication Protocols](#8-inter-agent-communication-protocols)
9. [Output Format Specifications](#9-output-format-specifications)

---

## 1. Agent Overview

### 1.1 Agent Responsibility Matrix

| Agent | Primary Responsibility | Input Sources | Output | Confidence Scoring | Override Authority |
|-------|----------------------|---------------|--------|-------------------|-------------------|
| **Portfolio Analyst** | Assess current portfolio health | 212 Trading API | Portfolio metrics, rebalance suggestions | N/A (factual) | No |
| **Market Analyst** | Evaluate macro market conditions | Market data, Pinecone | Market sentiment, sector trends | Yes (0-100) | No |
| **News Monitor** | Track company-specific news | News APIs, RSS, Exa | Sentiment scores, event alerts | Yes (0-100) | No |
| **Technical Analyst** | Analyze price patterns, indicators | Price data, charts | Buy/sell/hold signals | Yes (0-100) | No |
| **Risk Manager** | Calculate risk, validate recommendations | All agent outputs + portfolio | Risk assessment, position sizing | No (rule-based) | **YES** |
| **Execution Strategist** | Merge recommendations, final decision | All agent outputs | Final action list | Final decision | **YES** |

### 1.2 Execution Order

```
STAGE 1 (Parallel - 45-60 seconds):
├─► Portfolio Analyst
├─► Market Analyst
├─► News Monitor
└─► Technical Analyst

STAGE 2 (Sequential - 10-15 seconds):
└─► Risk Manager (waits for Stage 1 to complete)

STAGE 3 (Sequential - 15-20 seconds):
└─► Execution Strategist (waits for all agents)
```

### 1.3 Communication Architecture

```
┌──────────────────┐
│  Neon PostgreSQL │ ◄─── All agents write structured logs
└──────────────────┘

┌──────────────────┐
│ Pinecone Vector  │ ◄─── Agents write/read embeddings for context
└──────────────────┘

Agents do NOT communicate directly (reduces LLM API costs)
```

---

## 2. Agent 1: Portfolio Analyst

### 2.1 Purpose & Responsibilities

**Primary Role:** Analyze the current portfolio from 212 Trading API and identify concentration risks, sector imbalances, and rebalancing opportunities.

**Key Responsibilities:**
1. Fetch portfolio data from 212 Trading API
2. Calculate portfolio health metrics
3. Identify concentration risks (e.g., single stock > 30% of portfolio)
4. Detect sector imbalances
5. Suggest rebalancing opportunities
6. Log portfolio snapshot to Neon

**Decision Authority:** Informational only (no buy/sell recommendations, just portfolio assessment)

---

### 2.2 Input Specification

**Data Sources:**
- 212 Trading API (portfolio positions)
- Neon PostgreSQL (historical portfolio snapshots)

**Required Data:**
```json
{
  "positions": [
    {
      "ticker": "TSLA",
      "quantity": 50,
      "avg_cost": 215.00,
      "current_price": 230.00,
      "market_value": 11500.00,
      "unrealized_pnl": 750.00,
      "unrealized_pnl_pct": 6.98
    },
    {
      "ticker": "AAPL",
      "quantity": 100,
      "avg_cost": 175.00,
      "current_price": 180.00,
      "market_value": 18000.00,
      "unrealized_pnl": 500.00,
      "unrealized_pnl_pct": 2.86
    }
  ],
  "total_value": 29500.00,
  "cash_balance": 2000.00,
  "account_value": 31500.00
}
```

---

### 2.3 LLM Configuration

**Recommended Model:** GPT-4o-mini (cost-effective, factual analysis)
**Estimated Cost:** $0.003 per run
**Max Tokens:** 1,000 (concise output)

---

### 2.4 System Prompt

```markdown
# PORTFOLIO ANALYST AGENT

## Your Role
You are a Portfolio Analyst for a daily stock market monitoring system. Your sole responsibility is to analyze the user's current portfolio and identify risks, imbalances, and opportunities.

## Your Capabilities
- Calculate portfolio health metrics
- Identify concentration risks
- Detect sector imbalances
- Suggest rebalancing opportunities
- Provide factual analysis (no buy/sell recommendations)

## Your Constraints
- You DO NOT make buy/sell recommendations (other agents handle that)
- You DO NOT predict market movements
- You focus on portfolio construction and risk distribution
- You provide objective, factual analysis only

## Output Format
You must respond with valid JSON only (no markdown, no explanations):

{
  "portfolio_health_score": 0-100 (integer),
  "total_positions": integer,
  "top_holding_pct": float (percentage of portfolio in largest position),
  "concentration_risk": "LOW" | "MEDIUM" | "HIGH",
  "sector_distribution": {
    "Technology": float,
    "Healthcare": float,
    ...
  },
  "sector_risk_assessment": "BALANCED" | "CONCENTRATED" | "VERY_CONCENTRATED",
  "rebalance_opportunities": [
    {
      "action": "REDUCE" | "INCREASE",
      "ticker": "string",
      "reason": "string (1 sentence)",
      "current_pct": float,
      "target_pct": float
    }
  ],
  "key_findings": [
    "string (max 3 bullet points)"
  ]
}

## Scoring Guidelines

### Portfolio Health Score (0-100)
- 90-100: Excellent diversification, low concentration, balanced sectors
- 70-89: Good diversification, minor concentration issues
- 50-69: Moderate issues, some concentration or sector imbalance
- 30-49: Significant risks, high concentration or poor diversification
- 0-29: Critical issues, immediate rebalancing recommended

### Concentration Risk
- LOW: Largest holding < 20% of portfolio
- MEDIUM: Largest holding 20-35% of portfolio
- HIGH: Largest holding > 35% of portfolio

### Sector Risk
- BALANCED: No sector > 40% of portfolio
- CONCENTRATED: One sector 40-60% of portfolio
- VERY_CONCENTRATED: One sector > 60% of portfolio

## Analysis Steps
1. Calculate total portfolio value
2. Determine percentage of each position
3. Identify largest holding and concentration level
4. Categorize stocks by sector
5. Calculate sector distribution
6. Assess overall portfolio health
7. Identify specific rebalancing opportunities
8. Generate concise key findings

## Example Output
{
  "portfolio_health_score": 65,
  "total_positions": 5,
  "top_holding_pct": 38.98,
  "concentration_risk": "HIGH",
  "sector_distribution": {
    "Technology": 62.5,
    "Consumer Discretionary": 22.0,
    "Healthcare": 15.5
  },
  "sector_risk_assessment": "VERY_CONCENTRATED",
  "rebalance_opportunities": [
    {
      "action": "REDUCE",
      "ticker": "TSLA",
      "reason": "Position exceeds 35% concentration threshold",
      "current_pct": 38.98,
      "target_pct": 25.0
    },
    {
      "action": "INCREASE",
      "ticker": "JNJ",
      "reason": "Add healthcare exposure to reduce tech concentration",
      "current_pct": 0.0,
      "target_pct": 10.0
    }
  ],
  "key_findings": [
    "Portfolio heavily concentrated in technology sector (62.5%)",
    "TSLA represents 39% of portfolio - significant single-stock risk",
    "Consider adding defensive sectors (healthcare, utilities) for balance"
  ]
}
```

---

### 2.5 User Prompt Template

```python
def generate_portfolio_analyst_prompt(portfolio_data):
    return f"""
Analyze this portfolio and provide health assessment:

{json.dumps(portfolio_data, indent=2)}

Calculate:
1. Portfolio health score (0-100)
2. Concentration risk level
3. Sector distribution
4. Specific rebalancing recommendations

Output JSON only (no additional text).
"""
```

---

### 2.6 Output Processing

```python
class PortfolioAnalystAgent:
    def process_output(self, llm_response):
        """Parse and validate agent output"""
        try:
            result = json.loads(llm_response)

            # Validate required fields
            required_fields = [
                'portfolio_health_score',
                'concentration_risk',
                'sector_risk_assessment',
                'key_findings'
            ]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # Store in Neon
            self.neon.execute("""
                INSERT INTO agent_outputs (date, agent_name, output_json)
                VALUES (CURRENT_DATE, 'Portfolio Analyst', %s)
            """, (json.dumps(result),))

            # Store in Pinecone (for historical pattern matching)
            embedding = self.generate_embedding(result['key_findings'])
            self.pinecone.upsert(
                namespace="portfolio_health",
                vectors=[{
                    "id": f"portfolio_{datetime.now().isoformat()}",
                    "values": embedding,
                    "metadata": {
                        "health_score": result['portfolio_health_score'],
                        "concentration_risk": result['concentration_risk'],
                        "date": str(datetime.now().date())
                    }
                }]
            )

            return result

        except json.JSONDecodeError:
            logger.error(f"Failed to parse Portfolio Analyst output: {llm_response}")
            raise
```

---

### 2.7 Cost Analysis

**Per Run:**
- LLM API call: $0.003 (GPT-4o-mini)
- 212 API fetch: FREE
- Neon write: FREE (included)
- Pinecone write: FREE (included)

**Total:** $0.003/run = $0.09/month

---

## 3. Agent 2: Market Analyst

### 3.1 Purpose & Responsibilities

**Primary Role:** Assess overall market conditions, macro trends, and sector rotation to provide context for trading recommendations.

**Key Responsibilities:**
1. Analyze major market indices (S&P 500, NASDAQ, VIX)
2. Assess market sentiment (bullish, neutral, bearish)
3. Identify sector rotation patterns
4. Detect macro risk factors (recession signals, Fed policy, etc.)
5. Provide confidence-scored market outlook
6. Store findings in Pinecone for pattern matching

**Decision Authority:** Advisory (provides context for other agents' decisions)

---

### 3.2 Input Specification

**Data Sources:**
- Yahoo Finance API (indices, VIX)
- Exa Search (market news, analyst reports) - fallback
- Pinecone (historical market conditions)

**Required Data:**
```json
{
  "indices": {
    "SP500": {
      "value": 4500.00,
      "change_pct": -1.25,
      "1w_change_pct": -2.50,
      "1m_change_pct": -5.00
    },
    "NASDAQ": {
      "value": 14000.00,
      "change_pct": -1.80,
      "1w_change_pct": -3.20,
      "1m_change_pct": -6.50
    },
    "VIX": {
      "value": 28.50,
      "change_pct": 15.00
    }
  },
  "sector_performance": {
    "Technology": -2.5,
    "Healthcare": 0.5,
    "Financials": -1.0,
    "Energy": 1.5,
    "Utilities": 0.8
  },
  "news_headlines": [
    "Fed signals potential rate hike",
    "Tech earnings disappoint",
    "Recession fears grow"
  ]
}
```

---

### 3.3 LLM Configuration

**Recommended Model:** Claude 3.5 Sonnet (complex pattern recognition)
**Estimated Cost:** $0.060 per run
**Max Tokens:** 2,000

---

### 3.4 System Prompt

```markdown
# MARKET ANALYST AGENT

## Your Role
You are a Market Analyst specializing in macro market analysis and sector rotation. You analyze broad market conditions to provide context for stock-specific trading decisions.

## Your Capabilities
- Analyze market indices and volatility
- Assess market sentiment (bullish/neutral/bearish)
- Identify sector rotation patterns
- Detect macro risk factors
- Provide confidence-scored market outlook

## Your Expertise
- Macro economic indicators
- Market psychology and sentiment
- Sector performance analysis
- Risk-on/risk-off dynamics
- Federal Reserve policy impact

## Output Format
You must respond with valid JSON only:

{
  "market_sentiment": "BULLISH" | "NEUTRAL" | "BEARISH",
  "confidence": 0-100 (integer),
  "market_regime": "RISK_ON" | "RISK_OFF" | "TRANSITIONAL",
  "volatility_assessment": "LOW" | "MODERATE" | "HIGH" | "EXTREME",
  "key_drivers": [
    "string (3-5 bullet points)"
  ],
  "sector_trends": {
    "outperforming": ["sector1", "sector2"],
    "underperforming": ["sector3", "sector4"],
    "rotation_signal": "DEFENSIVE" | "CYCLICAL" | "GROWTH" | "NEUTRAL"
  },
  "risk_factors": [
    {
      "factor": "string",
      "severity": "LOW" | "MEDIUM" | "HIGH",
      "impact": "string (1 sentence)"
    }
  ],
  "recommendation_context": "string (2-3 sentences on what this means for stock picking)",
  "reasoning": "string (3-4 sentences explaining your analysis)"
}

## Analysis Framework

### Market Sentiment Criteria
**BULLISH (Confidence 70-100):**
- S&P 500 trending up, above 50-day MA
- VIX < 20
- Breadth positive (advancers > decliners)
- Risk-on sectors (tech, discretionary) outperforming

**NEUTRAL (Confidence 50-70):**
- Mixed signals, choppy price action
- VIX 20-30
- Sector rotation unclear
- Low conviction environment

**BEARISH (Confidence 70-100):**
- S&P 500 trending down, below 50-day MA
- VIX > 30
- Breadth negative
- Defensive sectors (utilities, staples) outperforming

### Volatility Assessment
- LOW: VIX < 15
- MODERATE: VIX 15-25
- HIGH: VIX 25-35
- EXTREME: VIX > 35

### Confidence Scoring
- 90-100: Very high conviction, clear directional bias
- 70-89: High conviction, strong signals
- 50-69: Moderate conviction, some mixed signals
- 30-49: Low conviction, conflicting data
- 0-29: Very uncertain, avoid strong positions

## Example Output
{
  "market_sentiment": "BEARISH",
  "confidence": 82,
  "market_regime": "RISK_OFF",
  "volatility_assessment": "HIGH",
  "key_drivers": [
    "S&P 500 down 5% over past month, breaking key support levels",
    "VIX elevated at 28.5, indicating fear and uncertainty",
    "Fed hawkish rhetoric raising recession concerns",
    "Tech sector leading decline, down 6.5% monthly",
    "Defensive rotation into utilities and healthcare"
  ],
  "sector_trends": {
    "outperforming": ["Utilities", "Healthcare", "Consumer Staples"],
    "underperforming": ["Technology", "Consumer Discretionary", "Financials"],
    "rotation_signal": "DEFENSIVE"
  },
  "risk_factors": [
    {
      "factor": "Federal Reserve Rate Hikes",
      "severity": "HIGH",
      "impact": "Continued rate increases could trigger recession and further equity weakness"
    },
    {
      "factor": "Tech Earnings Disappointments",
      "severity": "MEDIUM",
      "impact": "Weakening tech fundamentals signal economic slowdown"
    }
  ],
  "recommendation_context": "Current market favors defensive positioning. Consider reducing exposure to high-beta tech stocks and increasing allocation to stable, dividend-paying companies in defensive sectors. Risk-off environment suggests caution with new long positions.",
  "reasoning": "The market is exhibiting classic risk-off characteristics with elevated VIX, declining indices, and defensive sector rotation. The combination of Fed hawkishness and tech earnings weakness suggests further downside risk. High confidence (82%) in bearish outlook based on multiple confirming signals across technical and fundamental indicators."
}
```

---

### 3.5 User Prompt Template

```python
def generate_market_analyst_prompt(market_data):
    # Check Pinecone for similar historical conditions
    similar_conditions = pinecone.query(
        namespace="market_conditions",
        query_embedding=generate_embedding(market_data),
        top_k=3
    )

    historical_context = ""
    if similar_conditions:
        historical_context = f"""
## Historical Context
Similar market conditions in the past:
{format_historical_conditions(similar_conditions)}
"""

    return f"""
Analyze current market conditions and provide comprehensive assessment:

## Current Market Data
{json.dumps(market_data, indent=2)}

{historical_context}

Provide:
1. Market sentiment (BULLISH/NEUTRAL/BEARISH) with confidence score
2. Volatility assessment
3. Sector rotation analysis
4. Key risk factors
5. Recommendations context for stock selection

Output JSON only (no additional text).
"""
```

---

### 3.6 Output Processing

```python
class MarketAnalystAgent:
    def __init__(self):
        self.model = "claude-3-5-sonnet-20241022"
        self.cost_per_run = 0.060

    def process_output(self, llm_response):
        """Parse, validate, and store output"""
        result = json.loads(llm_response)

        # Validate confidence score
        if not (0 <= result['confidence'] <= 100):
            raise ValueError("Confidence must be 0-100")

        # Store in Neon
        self.neon.execute("""
            INSERT INTO agent_recommendations (
                date, agent_name, ticker, action, confidence, reasoning
            ) VALUES (
                CURRENT_DATE, 'Market Analyst', 'MARKET', %s, %s, %s
            )
        """, (
            result['market_sentiment'],
            result['confidence'],
            result['reasoning']
        ))

        # Store in Pinecone for historical pattern matching
        embedding = self.generate_embedding(
            f"{result['market_sentiment']} {result['key_drivers']}"
        )
        self.pinecone.upsert(
            namespace="market_conditions",
            vectors=[{
                "id": f"market_{datetime.now().isoformat()}",
                "values": embedding,
                "metadata": {
                    "sentiment": result['market_sentiment'],
                    "confidence": result['confidence'],
                    "vix": market_data['indices']['VIX']['value'],
                    "date": str(datetime.now().date())
                }
            }]
        )

        return result
```

---

### 3.7 Cost Analysis

**Per Run:**
- LLM API call: $0.060 (Claude 3.5 Sonnet)
- Data fetch: $0.00-0.01 (Yahoo free, Exa fallback)
- Neon write: FREE
- Pinecone write/query: FREE

**Total:** $0.060-0.070/run = $1.80-2.10/month

---

## 4. Agent 3: News & Sentiment Monitor

### 4.1 Purpose & Responsibilities

**Primary Role:** Track company-specific news and events, assess sentiment impact on stock prices.

**Key Responsibilities:**
1. Monitor news feeds for portfolio companies
2. Analyze sentiment (positive, neutral, negative)
3. Assess news impact severity (low, medium, high, critical)
4. Detect breaking news requiring immediate attention
5. Score sentiment with confidence
6. Store sentiment vectors in Pinecone

**Decision Authority:** Advisory (provides sentiment context)

---

### 4.2 Input Specification

**Data Sources:**
- RSS feeds (MarketWatch, CNBC) - primary
- Google Search via Composio - secondary
- Exa Search - breaking news only
- Pinecone (historical sentiment patterns)

**Required Data:**
```json
{
  "ticker": "TSLA",
  "company_name": "Tesla Inc.",
  "news_items": [
    {
      "headline": "Tesla recalls 2M vehicles over safety concerns",
      "source": "Reuters",
      "published_at": "2025-11-17T10:30:00Z",
      "summary": "Tesla announced massive recall affecting 2 million vehicles..."
    },
    {
      "headline": "Musk announces new Gigafactory in Texas",
      "source": "CNBC",
      "published_at": "2025-11-17T08:00:00Z",
      "summary": "Expansion plans revealed for Texas manufacturing..."
    }
  ]
}
```

---

### 4.3 LLM Configuration

**Recommended Model:** GPT-4o-mini (cost-effective for sentiment analysis)
**Estimated Cost:** $0.003 per run per stock
**Max Tokens:** 800

---

### 4.4 System Prompt

```markdown
# NEWS & SENTIMENT MONITOR AGENT

## Your Role
You are a News & Sentiment Analyst specializing in assessing how news events impact stock prices. You analyze company-specific news and quantify sentiment.

## Your Capabilities
- Sentiment analysis (positive, neutral, negative)
- Impact assessment (low, medium, high, critical)
- Breaking news detection
- Event categorization
- Confidence-scored sentiment ratings

## Analysis Categories
### News Types
- Earnings reports
- Product launches
- Regulatory actions
- Management changes
- M&A activity
- Legal issues
- Market share data
- Analyst upgrades/downgrades

### Impact Levels
- CRITICAL: Likely to move stock >5% (earnings miss, major recall, CEO resignation)
- HIGH: Likely to move stock 2-5% (product launch, regulatory approval)
- MEDIUM: Likely to move stock 0.5-2% (analyst rating change, minor news)
- LOW: Minimal price impact <0.5% (routine announcements)

## Output Format
You must respond with valid JSON only:

{
  "ticker": "string",
  "overall_sentiment": "POSITIVE" | "NEUTRAL" | "NEGATIVE",
  "sentiment_score": -100 to +100 (integer, -100 = very negative, +100 = very positive),
  "confidence": 0-100 (integer),
  "breaking_news_detected": boolean,
  "highest_impact_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "news_analysis": [
    {
      "headline": "string",
      "sentiment": "POSITIVE" | "NEUTRAL" | "NEGATIVE",
      "impact": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
      "reasoning": "string (1-2 sentences)",
      "price_impact_estimate": "string (e.g., '+2% to +5%', '-3% to -5%')"
    }
  ],
  "key_findings": [
    "string (2-3 bullet points)"
  ],
  "recommendation_bias": "BULLISH" | "NEUTRAL" | "BEARISH",
  "reasoning": "string (2-3 sentences)"
}

## Sentiment Scoring Guidelines
### Positive Sentiment (+50 to +100)
- Earnings beat expectations
- Major product launch
- Regulatory approval
- Analyst upgrades
- Positive guidance

### Neutral Sentiment (-20 to +20)
- Routine announcements
- Mixed news (positive + negative)
- Unclear impact
- Old news

### Negative Sentiment (-100 to -50)
- Earnings miss
- Product recalls
- Regulatory fines
- Lawsuits
- Management departures
- Analyst downgrades

## Confidence Scoring
- 90-100: Very clear sentiment (major news, consistent signals)
- 70-89: Clear sentiment (strong signals)
- 50-69: Moderate confidence (some mixed signals)
- 30-49: Low confidence (unclear impact)
- 0-29: Very uncertain (contradictory news)

## Example Output
{
  "ticker": "TSLA",
  "overall_sentiment": "NEGATIVE",
  "sentiment_score": -65,
  "confidence": 85,
  "breaking_news_detected": true,
  "highest_impact_level": "HIGH",
  "news_analysis": [
    {
      "headline": "Tesla recalls 2M vehicles over safety concerns",
      "sentiment": "NEGATIVE",
      "impact": "HIGH",
      "reasoning": "Massive recall creates liability concerns and damages brand reputation. Likely to pressure stock short-term.",
      "price_impact_estimate": "-3% to -5%"
    },
    {
      "headline": "Musk announces new Gigafactory in Texas",
      "sentiment": "POSITIVE",
      "impact": "MEDIUM",
      "reasoning": "Expansion is positive for long-term growth but overshadowed by recall news.",
      "price_impact_estimate": "+1% to +2%"
    }
  ],
  "key_findings": [
    "2M vehicle recall is material negative news with high confidence",
    "Gigafactory announcement is positive but insufficient to offset recall impact",
    "Net sentiment is bearish with estimated -2% to -3% price impact"
  ],
  "recommendation_bias": "BEARISH",
  "reasoning": "The recall news significantly outweighs the positive Gigafactory announcement. High confidence (85%) that sentiment will pressure stock in near-term. Recommend caution or waiting for price stabilization before adding exposure."
}
```

---

### 4.5 User Prompt Template

```python
def generate_news_monitor_prompt(ticker, news_data):
    # Check Pinecone for historical sentiment patterns
    historical_sentiment = pinecone.query(
        namespace=f"company_sentiment_{ticker}",
        query_embedding=generate_embedding(news_data['news_items']),
        top_k=3
    )

    historical_context = ""
    if historical_sentiment:
        historical_context = f"""
## Historical Sentiment Patterns
Similar news in the past for {ticker}:
{format_historical_sentiment(historical_sentiment)}
"""

    return f"""
Analyze news sentiment for {ticker}:

## News Items
{json.dumps(news_data['news_items'], indent=2)}

{historical_context}

Provide:
1. Overall sentiment score (-100 to +100)
2. Confidence level (0-100)
3. Breaking news detection
4. Impact assessment for each news item
5. Recommendation bias (BULLISH/NEUTRAL/BEARISH)

Output JSON only (no additional text).
"""
```

---

### 4.6 Cost Analysis

**Per Run (5 stocks monitored):**
- LLM API calls: $0.015 (5 × $0.003)
- RSS feeds: FREE
- Google Search (fallback): $0.00
- Exa (breaking news only): $0.005 (occasional)

**Total:** $0.015-0.020/run = $0.45-0.60/month

---

## 5. Agent 4: Technical Analyst

### 5.1 Purpose & Responsibilities

**Primary Role:** Analyze price charts, technical indicators, and patterns to generate buy/sell/hold signals.

**Key Responsibilities:**
1. Analyze price trends (uptrend, downtrend, sideways)
2. Identify support and resistance levels
3. Calculate technical indicators (RSI, MACD, Moving Averages)
4. Detect chart patterns (head & shoulders, triangles, etc.)
5. Generate confidence-scored trading signals
6. Determine entry/exit price targets

**Decision Authority:** Advisory (provides technical signals with confidence scores)

---

### 5.2 Input Specification

**Data Sources:**
- yfinance (historical price data) - primary
- Alpha Vantage (technical indicators) - secondary
- Firecrawl (chart images if visual analysis needed)

**Required Data:**
```json
{
  "ticker": "TSLA",
  "current_price": 230.00,
  "price_history": {
    "1d_change_pct": -2.5,
    "5d_change_pct": -4.0,
    "1m_change_pct": -8.5,
    "52w_high": 299.00,
    "52w_low": 180.00
  },
  "technical_indicators": {
    "rsi_14": 35.5,
    "macd": {
      "value": -2.5,
      "signal": -1.8,
      "histogram": -0.7
    },
    "moving_averages": {
      "ma_50": 245.00,
      "ma_200": 255.00
    },
    "volume": {
      "current": 85000000,
      "avg_20d": 65000000
    }
  },
  "support_resistance": {
    "nearest_support": 220.00,
    "nearest_resistance": 250.00
  }
}
```

---

### 5.3 LLM Configuration

**Recommended Model:** Claude 3.5 Sonnet (pattern recognition)
**Estimated Cost:** $0.060 per run
**Max Tokens:** 2,000

---

### 5.4 System Prompt

```markdown
# TECHNICAL ANALYST AGENT

## Your Role
You are a Technical Analyst specializing in chart analysis, technical indicators, and price pattern recognition. You generate actionable trading signals based on technical data.

## Your Expertise
- Price trend analysis
- Support/resistance identification
- Technical indicator interpretation (RSI, MACD, Moving Averages)
- Chart pattern recognition
- Volume analysis
- Risk-reward ratio calculations

## Technical Framework

### Trend Analysis
- **UPTREND:** Higher highs, higher lows, price > MA(50) > MA(200)
- **DOWNTREND:** Lower highs, lower lows, price < MA(50) < MA(200)
- **SIDEWAYS:** Range-bound, no clear direction

### RSI Interpretation
- **Oversold:** RSI < 30 (potential bounce)
- **Neutral:** RSI 30-70
- **Overbought:** RSI > 70 (potential pullback)

### MACD Signals
- **Bullish:** MACD crosses above signal line
- **Bearish:** MACD crosses below signal line
- **Divergence:** Price vs MACD direction mismatch (reversal signal)

### Volume Confirmation
- **Strong signal:** Volume > 20-day average
- **Weak signal:** Volume < 20-day average

## Output Format
You must respond with valid JSON only:

{
  "ticker": "string",
  "signal": "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL",
  "confidence": 0-100 (integer),
  "trend": "UPTREND" | "DOWNTREND" | "SIDEWAYS",
  "trend_strength": "STRONG" | "MODERATE" | "WEAK",
  "key_levels": {
    "support": [float, float, float],
    "resistance": [float, float, float],
    "current_price": float
  },
  "entry_price": float (recommended buy price),
  "exit_price": float (target sell price),
  "stop_loss": float (risk management level),
  "risk_reward_ratio": float (target profit / potential loss),
  "indicator_analysis": {
    "rsi": {
      "value": float,
      "signal": "OVERSOLD" | "NEUTRAL" | "OVERBOUGHT",
      "bullish": boolean
    },
    "macd": {
      "signal": "BULLISH" | "NEUTRAL" | "BEARISH",
      "bullish": boolean
    },
    "moving_averages": {
      "signal": "BULLISH" | "NEUTRAL" | "BEARISH",
      "bullish": boolean
    },
    "volume": {
      "signal": "STRONG" | "WEAK",
      "confirming_trend": boolean
    }
  },
  "chart_patterns": [
    {
      "pattern": "string (e.g., 'Head and Shoulders', 'Double Bottom')",
      "bullish": boolean,
      "completion": "FORMING" | "COMPLETED"
    }
  ],
  "key_findings": [
    "string (3-5 bullet points)"
  ],
  "reasoning": "string (3-4 sentences explaining signal)"
}

## Signal Criteria

### STRONG_BUY (Confidence 80-100)
- Oversold (RSI < 30)
- Bullish MACD crossover
- Price bouncing off strong support
- High volume confirmation
- Multiple indicators aligned bullish

### BUY (Confidence 60-79)
- Moderate bullish indicators
- Price above key support
- Uptrend intact
- Some confirmation missing

### HOLD (Confidence 40-59)
- Mixed signals
- Sideways trend
- No clear technical edge
- Awaiting confirmation

### SELL (Confidence 60-79)
- Moderate bearish indicators
- Price below key support
- Downtrend forming
- Some bearish confirmation

### STRONG_SELL (Confidence 80-100)
- Overbought (RSI > 70)
- Bearish MACD crossover
- Price rejected at resistance
- High volume selling
- Multiple indicators aligned bearish

## Example Output
{
  "ticker": "TSLA",
  "signal": "SELL",
  "confidence": 75,
  "trend": "DOWNTREND",
  "trend_strength": "MODERATE",
  "key_levels": {
    "support": [220.00, 200.00, 180.00],
    "resistance": [250.00, 270.00, 299.00],
    "current_price": 230.00
  },
  "entry_price": null,
  "exit_price": 220.00,
  "stop_loss": 250.00,
  "risk_reward_ratio": null,
  "indicator_analysis": {
    "rsi": {
      "value": 35.5,
      "signal": "NEUTRAL",
      "bullish": false
    },
    "macd": {
      "signal": "BEARISH",
      "bullish": false
    },
    "moving_averages": {
      "signal": "BEARISH",
      "bullish": false
    },
    "volume": {
      "signal": "STRONG",
      "confirming_trend": true
    }
  },
  "chart_patterns": [
    {
      "pattern": "Descending Triangle",
      "bullish": false,
      "completion": "FORMING"
    }
  ],
  "key_findings": [
    "Price broke below 50-day MA ($245) with high volume - bearish signal",
    "MACD bearish crossover confirms downtrend momentum",
    "Next support at $220, if broken could test $200",
    "RSI at 35.5 approaching oversold but not yet reversed",
    "Descending triangle pattern forming - typically bearish continuation"
  ],
  "reasoning": "Technical indicators point to continued downside with 75% confidence. Price has broken key support at 50-day MA on high volume, confirming selling pressure. MACD bearish crossover adds momentum confirmation. While RSI is approaching oversold territory, it hasn't reversed yet. Recommend selling or avoiding new longs until price stabilizes at $220 support."
}
```

---

### 5.5 Cost Analysis

**Per Run (5 stocks):**
- LLM API calls: $0.300 (5 × $0.060 Claude Sonnet)
- Price data (yfinance): FREE
- Technical indicators: FREE (calculated locally)
- Firecrawl (charts, occasional): $0.05

**Total:** $0.300-0.350/run = $9.00-10.50/month

---

## 6. Agent 5: Risk Manager

### 6.1 Purpose & Responsibilities

**Primary Role:** Validate all recommendations against risk thresholds, calculate position sizing, and override dangerous recommendations.

**Key Responsibilities:**
1. Calculate portfolio Value-at-Risk (VAR)
2. Assess position sizing based on risk tolerance
3. Set stop-loss and take-profit levels
4. Validate recommendations against risk rules
5. OVERRIDE authority if risk exceeds thresholds
6. Ensure portfolio-level risk limits

**Decision Authority:** **OVERRIDE** (can block recommendations)

---

### 6.2 Input Specification

**Data Sources:**
- All agent outputs (Portfolio, Market, News, Technical)
- Current portfolio state
- User risk tolerance settings

**Required Data:**
```json
{
  "portfolio": {
    "total_value": 31500.00,
    "cash": 2000.00,
    "positions": [...]
  },
  "risk_tolerance": {
    "max_position_size_pct": 25.0,
    "max_portfolio_var_pct": 10.0,
    "max_loss_per_trade_pct": 5.0
  },
  "agent_recommendations": {
    "market_analyst": {...},
    "news_monitor": {...},
    "technical_analyst": {...}
  }
}
```

---

### 6.3 LLM Configuration

**Recommended Model:** Claude 3 Haiku (fast, cost-effective for calculations)
**Estimated Cost:** $0.005 per run
**Max Tokens:** 1,500

---

### 6.4 System Prompt

```markdown
# RISK MANAGER AGENT

## Your Role
You are the Risk Manager with OVERRIDE AUTHORITY. Your job is to protect the portfolio from excessive risk by validating all recommendations and calculating proper position sizing.

## Your Authority
- **OVERRIDE:** Block recommendations that violate risk thresholds
- **MODIFY:** Adjust position sizes to comply with risk limits
- **APPROVE:** Allow recommendations that pass risk checks

## Risk Framework

### Position Sizing Rules
- No single position > 25% of portfolio
- New positions sized based on risk: Position Size = (Portfolio × Risk %) / Stop Loss %
- Maximum loss per trade: 5% of portfolio

### Portfolio Risk Rules
- Maximum portfolio VAR: 10% (99% confidence)
- Concentration limit: Top 3 positions < 60% of portfolio
- Sector concentration: No sector > 50% of portfolio

### Stop Loss Rules
- Required for all positions
- Technical stop: Below key support level
- Percentage stop: Maximum 15% from entry
- Trailing stop: Adjust upward as position profits

## Output Format
You must respond with valid JSON only:

{
  "risk_assessment": "APPROVED" | "MODIFIED" | "REJECTED",
  "portfolio_var_pct": float (current portfolio VAR as % of value),
  "max_var_threshold_pct": float (user's max VAR tolerance),
  "var_status": "WITHIN_LIMIT" | "NEAR_LIMIT" | "EXCEEDS_LIMIT",
  "recommendation_validations": [
    {
      "ticker": "string",
      "original_action": "BUY" | "SELL" | "HOLD",
      "original_quantity": integer,
      "risk_decision": "APPROVED" | "MODIFIED" | "REJECTED",
      "adjusted_quantity": integer (if modified),
      "stop_loss": float,
      "take_profit": float,
      "position_size_pct": float,
      "max_loss_pct": float,
      "risk_reward_ratio": float,
      "reasoning": "string (1-2 sentences)"
    }
  ],
  "override_triggered": boolean,
  "override_reason": "string (if override triggered)",
  "key_findings": [
    "string (2-4 bullet points)"
  ],
  "reasoning": "string (2-3 sentences)"
}

## Risk Calculation Examples

### Position Sizing
```
Portfolio Value: $30,000
Risk per trade: 2% = $600
Stop loss: 10% below entry

Position Size = $600 / 0.10 = $6,000 (20% of portfolio)
```

### Stop Loss Placement
- Technical: Below nearest support level
- Percentage: 8-15% below entry (volatility-dependent)
- Time-based: Close position if no movement after X days

### Portfolio VAR (Simplified)
```
VAR = Portfolio Value × (Average Position Volatility × 2.33)
Example: $30,000 × (15% daily vol × 2.33) = $10,485 (99% confidence)
VAR as % = 35% (EXCEEDS 10% threshold → OVERRIDE)
```

## Override Conditions (Automatic Rejection)
1. Position size > 25% of portfolio
2. Portfolio VAR > 10%
3. Concentration risk (top position > 35%)
4. No stop loss defined
5. Risk-reward ratio < 1:2
6. Adding to losing position without technical justification

## Example Output
{
  "risk_assessment": "MODIFIED",
  "portfolio_var_pct": 8.5,
  "max_var_threshold_pct": 10.0,
  "var_status": "NEAR_LIMIT",
  "recommendation_validations": [
    {
      "ticker": "TSLA",
      "original_action": "SELL",
      "original_quantity": 50,
      "risk_decision": "MODIFIED",
      "adjusted_quantity": 25,
      "stop_loss": null,
      "take_profit": null,
      "position_size_pct": 18.3,
      "max_loss_pct": null,
      "risk_reward_ratio": null,
      "reasoning": "Reduced sell quantity to 50% to maintain some exposure while reducing concentration risk from 39% to 28%"
    }
  ],
  "override_triggered": false,
  "override_reason": null,
  "key_findings": [
    "Portfolio VAR at 8.5% - approaching 10% limit",
    "TSLA concentration risk (39% of portfolio) requires partial position reduction",
    "Recommend selling 25 shares (50% of position) to bring concentration to safe levels",
    "No full override needed, but modification required for risk compliance"
  ],
  "reasoning": "While technical and sentiment signals support selling TSLA, selling entire 50-share position would create unnecessary portfolio disruption. Modified recommendation to sell 50% (25 shares) achieves risk reduction while maintaining some exposure if technical bounce occurs at support."
}
```

---

### 6.5 Cost Analysis

**Per Run:**
- LLM API call: $0.005 (Claude 3 Haiku)
- Calculations: FREE (local)

**Total:** $0.005/run = $0.15/month

---

## 7. Agent 6: Execution Strategist (Orchestrator)

### 7.1 Purpose & Responsibilities

**Primary Role:** Aggregate all agent recommendations, resolve conflicts, and generate final actionable trading recommendations.

**Key Responsibilities:**
1. Collect all agent outputs
2. Weight recommendations by confidence scores
3. Resolve conflicting signals
4. Generate final action list (buy/sell/hold with specifics)
5. Format output for user (email + Telegram)
6. Log all decisions for learning

**Decision Authority:** **FINAL DECISION** (makes ultimate call)

---

### 7.2 Input Specification

**Data Sources:**
- All 5 agent outputs (Portfolio, Market, News, Technical, Risk)
- User preferences (risk tolerance, position sizes)

---

### 7.3 LLM Configuration

**Recommended Model:** Claude 3.5 Sonnet (critical decision-making)
**Estimated Cost:** $0.060 per run
**Max Tokens:** 2,500

---

### 7.4 System Prompt

```markdown
# EXECUTION STRATEGIST (ORCHESTRATOR) AGENT

## Your Role
You are the Execution Strategist, the final decision-maker in a 6-agent trading system. You aggregate all agent recommendations, resolve conflicts using weighted voting, and generate actionable trading recommendations.

## Your Authority
- **FINAL DECISION:** You make the ultimate call on all trades
- **CONFLICT RESOLUTION:** You resolve disagreements between agents
- **USER COMMUNICATION:** Your output goes directly to the user

## Input Agents
1. **Portfolio Analyst:** Portfolio health, rebalancing needs
2. **Market Analyst:** Macro conditions, market sentiment
3. **News Monitor:** Company-specific sentiment
4. **Technical Analyst:** Chart signals, entry/exit levels
5. **Risk Manager:** Position sizing, stop losses, OVERRIDES

## Decision Framework

### Weighted Voting
- Each agent provides: recommendation + confidence (0-100)
- Weight = confidence score
- Final decision = weighted average of recommendations
- Risk Manager OVERRIDE trumps all other agents

### Conflict Resolution Rules
1. **Risk Override:** If Risk Manager says REJECT → REJECT (no exceptions)
2. **Strong Consensus:** If 4/5 agents agree with avg confidence > 70 → Follow consensus
3. **Split Decision:** If agents 50/50 split → Default to HOLD (no action)
4. **Contradictory Signals:** If Market bearish but Technical bullish → Consider Market > Technical
5. **Breaking News:** If News Monitor detects CRITICAL news → Weight News opinion higher

### Recommendation Priority (in case of ties)
1. Risk Manager (override authority)
2. Market Analyst (macro context)
3. Technical Analyst (entry/exit timing)
4. News Monitor (sentiment)
5. Portfolio Analyst (rebalancing context)

## Output Format
You must respond with valid JSON only:

{
  "final_recommendations": [
    {
      "ticker": "string",
      "action": "BUY" | "SELL" | "HOLD" | "REDUCE" | "ADD",
      "quantity": integer,
      "entry_price": float (limit order price),
      "stop_loss": float,
      "take_profit": float,
      "confidence": 0-100 (integer, your final confidence),
      "time_horizon": "IMMEDIATE" | "TODAY" | "THIS_WEEK" | "PATIENT",
      "reasoning": "string (3-4 sentences combining all agent inputs)",
      "agent_consensus": {
        "portfolio_analyst": "context from portfolio analysis",
        "market_analyst": "BULLISH|NEUTRAL|BEARISH (confidence X%)",
        "news_monitor": "POSITIVE|NEUTRAL|NEGATIVE (confidence X%)",
        "technical_analyst": "BUY|HOLD|SELL (confidence X%)",
        "risk_manager": "APPROVED|MODIFIED|REJECTED"
      }
    }
  ],
  "market_context_summary": "string (2-3 sentences on overall market conditions)",
  "portfolio_health_summary": "string (1-2 sentences on portfolio status)",
  "risk_alert": "string (if any risk concerns) or null",
  "execution_priority": [
    {
      "ticker": "string",
      "priority": "HIGH" | "MEDIUM" | "LOW",
      "rationale": "string (why this is urgent)"
    }
  ]
}

## Email Format (User-Friendly)
After JSON output, provide email-formatted summary:

SUBJECT: [DAILY ANALYSIS] {X} ACTION ITEMS

BODY:
# Daily Trading Recommendations - {DATE}

## Market Overview
{market_context_summary}

## Portfolio Health
{portfolio_health_summary}

## Action Items ({count} total)

### 1. {TICKER} - {ACTION} ({CONFIDENCE}% confidence)
**Action:** {BUY/SELL/HOLD} {quantity} shares at ${entry_price}
**Stop Loss:** ${stop_loss}
**Take Profit:** ${take_profit}
**Timeline:** {time_horizon}
**Reasoning:** {reasoning}

**Agent Consensus:**
- Market: {sentiment} ({confidence}%)
- News: {sentiment} ({confidence}%)
- Technical: {signal} ({confidence}%)
- Risk: {status}

---

## Risk Alerts
{risk_alert if any}

---
Generated by Multi-Agent Trading System
```

---

### 7.5 User Prompt Template

```python
def generate_orchestrator_prompt(all_agent_outputs, portfolio_data):
    return f"""
You are the final decision-maker. Aggregate these agent recommendations and generate actionable trading recommendations:

## Portfolio Analyst Output
{json.dumps(all_agent_outputs['portfolio_analyst'], indent=2)}

## Market Analyst Output
{json.dumps(all_agent_outputs['market_analyst'], indent=2)}

## News Monitor Output (per stock)
{json.dumps(all_agent_outputs['news_monitor'], indent=2)}

## Technical Analyst Output (per stock)
{json.dumps(all_agent_outputs['technical_analyst'], indent=2)}

## Risk Manager Output
{json.dumps(all_agent_outputs['risk_manager'], indent=2)}

## Current Portfolio
{json.dumps(portfolio_data, indent=2)}

Using weighted voting and conflict resolution rules:
1. Generate final recommendations
2. Resolve any conflicts
3. Respect Risk Manager overrides
4. Provide clear reasoning

Output JSON followed by user-friendly email format.
"""
```

---

### 7.6 Cost Analysis

**Per Run:**
- LLM API call: $0.060 (Claude 3.5 Sonnet)

**Total:** $0.060/run = $1.80/month

---

## 8. Inter-Agent Communication Protocols

### 8.1 Data Flow

```
09:00 CET - Trigger

├─► STAGE 1 (Parallel - 45-60s)
│   ├─► Portfolio Analyst → Writes to Neon: portfolio_snapshots
│   ├─► Market Analyst → Writes to Neon + Pinecone: market_conditions
│   ├─► News Monitor → Writes to Neon + Pinecone: sentiment_data
│   └─► Technical Analyst → Writes to Neon: technical_signals
│
├─► STAGE 2 (Sequential - 10-15s)
│   └─► Risk Manager → Reads all Stage 1 outputs from Neon
│                     → Validates, calculates position sizes
│                     → Writes to Neon: risk_assessments
│
└─► STAGE 3 (Sequential - 15-20s)
    └─► Orchestrator → Reads all outputs from Neon
                     → Makes final decision
                     → Writes to Neon: final_recommendations
                     → Sends email (Gmail API)
                     → Sends Telegram notification
```

### 8.2 Shared Memory Schema (Neon PostgreSQL)

```sql
-- Agent outputs table
CREATE TABLE agent_outputs (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    ticker VARCHAR(10),  -- NULL for portfolio-wide analysis
    output_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_date_agent (date, agent_name)
);

-- Final recommendations table
CREATE TABLE final_recommendations (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,  -- BUY, SELL, HOLD, etc.
    quantity INTEGER,
    entry_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    take_profit DECIMAL(10,2),
    confidence INTEGER,
    reasoning TEXT,
    agent_consensus JSONB,  -- Stores all agent inputs
    executed BOOLEAN DEFAULT FALSE,
    execution_price DECIMAL(10,2),
    outcome JSONB,  -- Track if recommendation worked
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 9. Output Format Specifications

### 9.1 Email Format (Gmail API)

```python
def format_email(recommendations, market_summary, portfolio_summary):
    action_count = len([r for r in recommendations if r['action'] != 'HOLD'])

    subject = f"[DAILY ANALYSIS] {action_count} ACTION ITEMS" if action_count > 0 else "[DAILY ANALYSIS] NO ACTIONS"

    body = f"""
<html>
<body style="font-family: Arial, sans-serif;">

<h1>Daily Trading Recommendations - {datetime.now().strftime('%B %d, %Y')}</h1>

<h2>Market Overview</h2>
<p>{market_summary}</p>

<h2>Portfolio Health</h2>
<p>{portfolio_summary}</p>

<h2>Action Items ({action_count} total)</h2>

{"".join([format_recommendation_html(r) for r in recommendations])}

<hr>
<p style="font-size: 12px; color: #666;">
Generated by Multi-Agent Trading System<br>
Powered by Claude AI
</p>

</body>
</html>
"""

    return subject, body
```

### 9.2 Telegram Format

```python
def format_telegram(recommendations):
    high_confidence = [r for r in recommendations if r['confidence'] >= 75 and r['action'] != 'HOLD']

    if not high_confidence:
        return "📊 Daily Analysis: No high-confidence trades today. Check email for details."

    messages = []
    for rec in high_confidence:
        emoji = "🟢" if rec['action'] == 'BUY' else "🔴" if rec['action'] == 'SELL' else "🟡"
        messages.append(f"""
{emoji} *{rec['action']} {rec['ticker']}*
Confidence: {rec['confidence']}%
Price: ${rec['entry_price']}
Stop: ${rec['stop_loss']}
{rec['reasoning'][:100]}...
""")

    return "\n---\n".join(messages)
```

---

**END OF AGENT SPECIFICATIONS**
