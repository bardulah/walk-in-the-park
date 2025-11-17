# Data Flow Documentation

**System:** Multi-Agent Trading System
**Date:** 2025-11-17

---

## 📊 API Response Formats

### 1. Trading 212 API

#### GET /equity/account/cash
```json
{
  "blocked": 150.50,      // Cash reserved for pending orders
  "free": 2000.00,        // Available cash for trading
  "invested": 30557.50,   // Total deployed in positions
  "pieCash": 0.00,        // Cash in pie portfolios
  "ppl": 457.50,          // Total profit/loss on holdings
  "result": 32557.50,     // Overall account performance
  "total": 32557.50       // Combined account value
}
```

#### GET /equity/portfolio
```json
[
  {
    "averagePrice": 175.00,           // Cost basis per share
    "currentPrice": 180.25,           // Latest market price
    "frontend": "WC4",                // Trading channel
    "fxPpl": 0.00,                    // FX impact on P&L
    "initialFillDate": "2024-01-15T10:30:00Z",  // ISO 8601
    "maxBuy": 100,                    // Max shares can buy
    "maxSell": 50,                    // Max shares can sell
    "pieQuantity": 0,                 // Shares in pies
    "ppl": 262.50,                    // Unrealized gain/loss
    "quantity": 50,                   // Total shares held
    "ticker": "AAPL_US_EQ"           // Instrument identifier
  }
]
```

**Formatted Output (after processing):**
```json
{
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 50,
      "avg_cost": 175.00,
      "current_price": 180.25,
      "market_value": 9012.50,
      "unrealized_pnl": 262.50,
      "unrealized_pnl_pct": 3.00,
      "initial_fill_date": "2024-01-15T10:30:00Z"
    }
  ],
  "total_value": 30557.50,
  "cash_balance": 2000.00,
  "account_value": 32557.50,
  "total_pnl": 457.50,
  "invested": 30557.50,
  "blocked": 150.50,
  "timestamp": "2025-11-17T15:00:00.000Z",
  "source": "Trading212-live"
}
```

---

### 2. Gemini API

#### POST /v1beta/models/gemini-1.5-flash:generateContent

**Request:**
```json
{
  "contents": [
    {
      "parts": [{"text": "System: You are a portfolio analyst...\n\nUser: Analyze this portfolio..."}]
    }
  ],
  "generationConfig": {
    "temperature": 0.7,
    "maxOutputTokens": 2000,
    "responseMimeType": "application/json"
  }
}
```

**Response:**
```json
{
  "candidates": [
    {
      "content": {
        "role": "model",
        "parts": [
          {
            "text": "{\"health_score\": 78, \"concentration_risk\": \"HIGH\", ...}"
          }
        ]
      },
      "finishReason": "STOP",
      "safetyRatings": [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "NEGLIGIBLE"}
      ]
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 150,
    "candidatesTokenCount": 300,
    "totalTokenCount": 450
  },
  "modelVersion": "gemini-1.5-flash"
}
```

**Text Extraction Path:**
```
response.candidates[0].content.parts[0].text
```

---

## 🔄 Complete Data Flow

### Phase 1: Data Collection
```
┌─────────────────┐
│ Trading 212 API │
└────────┬────────┘
         │
         ├── GET /equity/account/cash → {free, total, invested, ppl, blocked}
         │
         └── GET /equity/portfolio → [{ticker, quantity, averagePrice, currentPrice, ppl}]
                 │
                 ▼
         ┌───────────────────┐
         │ Trading212API     │
         │ .get_portfolio_   │
         │  data()           │
         └────────┬──────────┘
                  │
                  │ Formats to standardized structure
                  ▼
         {positions: [...], account_value: X, total_pnl: Y}
```

### Phase 2: Agent Analysis

```
┌──────────────────────────────────────┐
│  Portfolio Data + Market Data        │
└──────────┬───────────────────────────┘
           │
    ┌──────┴──────┬──────────┬─────────┐
    │             │          │         │
    ▼             ▼          ▼         ▼
┌──────────┐ ┌─────────┐ ┌──────┐ ┌──────────┐
│Portfolio │ │ Market  │ │ News │ │Technical │
│ Analyst  │ │ Analyst │ │Monitor│ │ Analyst  │
└────┬─────┘ └────┬────┘ └───┬──┘ └────┬─────┘
     │            │           │         │
     │  Gemini    │  Gemini   │ Gemini  │ Gemini
     │  1.5-Flash │  1.5-Flash│1.5-Flash│1.5-Flash
     │            │           │         │
     ▼            ▼           ▼         ▼
{health_score,  {sentiment,  {alerts,  {signals,
 concentration,  volatility,  oppor-   patterns,
 risks}          trends}      tunities} levels}
     │            │           │         │
     └────────────┴───────────┴─────────┘
                  │
                  ▼
         ┌────────────────┐
         │  Orchestrator  │
         │ (Gemini Pro or │
         │  Claude-3.5)   │
         └────────┬───────┘
                  │
                  ▼
     {stock_recommendations: [...],
      cfd_opportunities: [...],
      risk_alert: "..."}
```

### Phase 3: Risk Management

```
         ┌──────────────────────┐
         │ Preliminary Recs     │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   Risk Manager       │
         │   (Claude-3.5)       │
         │   - Enforce limits   │
         │   - Override power   │
         └──────────┬───────────┘
                    │
        ┌───────────┴────────────┐
        │                        │
        ▼                        ▼
    Approved              Rejected/Modified
    Recommendations       Recommendations
```

### Phase 4: Output Generation

```
         ┌──────────────────────┐
         │  Final Results       │
         └──────────┬───────────┘
                    │
        ┌───────────┼────────────┐
        │           │            │
        ▼           ▼            ▼
    ┌──────┐  ┌─────────┐  ┌─────────┐
    │ JSON │  │Telegram │  │ Email   │
    │ File │  │  Bot    │  │(future) │
    └──────┘  └─────────┘  └─────────┘
```

---

## 🔧 Code Integration Points

### 1. Trading 212 Integration
**File:** `trading-agents/data/trading212_api.py`

```python
# Initialize
api = Trading212API(api_key_id, api_secret, mode='live')

# Get data
portfolio = api.get_portfolio_data()
# Returns formatted dict with positions, account_value, cash, P&L

# Access data
for position in portfolio['positions']:
    ticker = position['ticker']          # "AAPL"
    quantity = position['quantity']      # 50
    pnl_pct = position['unrealized_pnl_pct']  # 3.00
```

### 2. Gemini Integration (REST API)
**File:** `trading-agents/config/llm_router_unified.py`

```python
# Call Gemini
response = llm_router.call(
    model='gemini-2.5-flash',
    system_prompt="You are a portfolio analyst...",
    user_prompt="Analyze this portfolio...",
    json_mode=True
)

# Response is already extracted text (JSON string)
result = json.loads(response)
```

### 3. Google ADK Integration
**File:** `trading-agents/adk_system.py`

```python
# Initialize agent
portfolio_agent = PortfolioAnalystADK(api_key=gemini_api_key)

# Run analysis
result = portfolio_agent.analyze_portfolio(portfolio_data)

# Access results
health_score = result['health_score']
concentration_risk = result['concentration_risk']
```

### 4. Hybrid Data Fetcher
**File:** `trading-agents/data/data_fetcher.py`

```python
# Initialize with fallback
fetcher = HybridDataFetcher(
    trading_212_api_key=key_id,
    trading_212_api_secret=secret,
    use_mock=False  # Try real API, fallback to mock
)

# Get portfolio (tries real, falls back to mock)
portfolio = fetcher.get_portfolio_data()
```

---

## 📋 Agent Input/Output Schemas

### Portfolio Analyst
**Input:**
```json
{
  "positions": [...],
  "account_value": 32557.50,
  "cash_balance": 2000.00,
  "total_pnl": 457.50
}
```

**Output:**
```json
{
  "health_score": 78,
  "concentration_risk": "HIGH",
  "high_risk_positions": [
    {
      "ticker": "MSFT",
      "issue": "concentration",
      "severity": "HIGH",
      "recommendation": "Reduce to below 25% of portfolio"
    }
  ],
  "rebalancing_suggestions": ["Diversify into defensive sectors"],
  "summary": "Portfolio health 78/100 with critical MSFT concentration at 47.8%"
}
```

### Market Analyst
**Output:**
```json
{
  "sentiment": "BEARISH",
  "confidence": 85,
  "volatility_assessment": "HIGH",
  "sector_trends": ["Tech underperforming", "Defensive rotation"],
  "key_risks": ["VIX elevated at 28.5", "Recession fears"],
  "summary": "Market bearish with high volatility and defensive rotation"
}
```

### Orchestrator (Final Output)
```json
{
  "stock_recommendations": [
    {
      "ticker": "MSFT",
      "action": "REDUCE",
      "priority": "HIGH",
      "confidence": 90,
      "reasoning": "Critical concentration at 47.8% during bearish market..."
    }
  ],
  "cfd_opportunities": [
    {
      "ticker": "SPY",
      "direction": "SHORT",
      "timeframe": "1-3_DAYS",
      "entry": 450.00,
      "target": 440.00,
      "stop": 455.00,
      "risk_reward": 2.0,
      "reasoning": "Bearish momentum with VIX spike..."
    }
  ],
  "risk_alert": "CRITICAL: Portfolio concentration risk requires immediate action",
  "key_insights": [...]
}
```

---

## 🔐 Authentication Summary

### Trading 212
**Headers:**
```
Authorization: {API_KEY_ID}
X-API-Secret: {API_SECRET_KEY}
Content-Type: application/json
```

**Environment Variables:**
- `212_TRADING_API_KEY_ID`
- `212_TRADING_API_SECRET_KEY`

### Gemini
**URL Parameter:**
```
?key={GEMINI_API_KEY}
```

**Environment Variables:**
- `GEMINI_API_KEY`

---

## 🚀 Usage Examples

### Quick Test - Real Data (once APIs enabled)
```bash
cd /home/user/walk-in-the-park

# Test Trading 212 connection
python3 -c "from trading-agents.data.trading212_api import Trading212API; from trading-agents.config.settings import API_CONFIG; api = Trading212API(API_CONFIG.trading_212_api_key, API_CONFIG.trading_212_api_secret); print(api.get_portfolio_data())"

# Test Google ADK system
python3 trading-agents/adk_system.py

# Test MVP system
python3 trading-agents/run_analysis.py
```

### Production Run
```bash
# Daily automated run
python3 trading-agents/run_analysis.py > logs/analysis_$(date +%Y%m%d).log 2>&1
```

---

## 📊 Cost Tracking

Each API call tracks usage:

**Gemini (via REST):**
- Free with $200 credits
- usageMetadata in response: `{promptTokenCount, candidatesTokenCount, totalTokenCount}`

**OpenRouter:**
- Tracked in `llm_router.total_cost`
- Calculated from `usage.prompt_tokens` and `usage.completion_tokens`

**Trading 212:**
- Free (no usage limits documented)

---

**Last Updated:** 2025-11-17
**Status:** Ready for deployment once APIs are enabled
