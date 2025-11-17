# Multi-Agent Trading System (MVP)

**Version:** 1.0 MVP
**Status:** ✅ Working
**Cost:** ~$0.43/month (daily runs)

---

## Overview

A 3-agent system that analyzes your portfolio and market conditions to generate daily trading recommendations.

### Agents:
1. **Portfolio Analyst** - Analyzes portfolio health and concentration risks
2. **Market Analyst** - Assesses market sentiment and volatility
3. **Orchestrator** - Combines analysis and generates final recommendations

### Technology:
- **LLM Router:** OpenRouter (gpt-4o-mini for analysts, claude-3-5-sonnet for orchestrator)
- **Data Sources:** Mock data for MVP (real APIs to be added)
- **Cost Tracking:** Built-in per-run cost monitoring

---

## Quick Start

### 1. Setup (Already Done ✓)

```bash
# API keys configured via environment variables
# Dependencies installed
# Project structure created
```

### 2. Run Daily Analysis

```bash
cd /home/user/walk-in-the-park
python3 trading-agents/run_analysis.py
```

### 3. View Results

The system will output:
- Portfolio health analysis
- Market sentiment assessment
- Final trading recommendations with confidence scores
- Total cost for the run
- Analysis saved to JSON file
- Telegram notification (if configured)

---

## Sample Output

```json
{
  "final_recommendations": [
    {
      "ticker": "MSFT",
      "action": "REDUCE",
      "confidence": 90,
      "reasoning": "MSFT comprises 47.8% of portfolio during bearish market...",
      "priority": "HIGH"
    }
  ],
  "market_context_summary": "Market bearish with elevated volatility...",
  "portfolio_health_summary": "Portfolio health 82/100, high concentration risk",
  "key_insights": [...],
  "risk_alert": "URGENT: Critical concentration risk..."
}
```

---

## Cost Breakdown

| Component | Model | Cost per Run |
|-----------|-------|--------------|
| Portfolio Analyst | gpt-4o-mini | $0.0003 |
| Market Analyst | gpt-4o-mini* | $0.0003 |
| Orchestrator | claude-3-5-sonnet | $0.0136 |
| **Total** | | **$0.0142** |

*Currently using gpt-4o-mini fallback. Will use Gemini 2.5 Flash (FREE with $200 credits) once dependencies fixed.

**Monthly Cost (30 runs):** ~$0.43

---

## Architecture

```
┌─────────────────────────────────────────┐
│          ORCHESTRATOR                    │
│    (Claude 3.5 Sonnet)                  │
│   - Combines analysis                    │
│   - Generates recommendations           │
└──────────┬──────────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌────────┐   ┌────────┐
│Portfolio│   │ Market │
│Analyst  │   │Analyst │
│(GPT-4o) │   │(GPT-4o)│
└────────┘   └────────┘
    │             │
    ▼             ▼
┌────────┐   ┌────────┐
│Portfolio│   │ Market │
│  Data   │   │  Data  │
└────────┘   └────────┘
```

---

## Project Structure

```
trading-agents/
├── agents/
│   ├── portfolio_analyst.py    # Portfolio health analysis
│   ├── market_analyst.py       # Market sentiment analysis
│   └── orchestrator.py         # Final decision maker
├── config/
│   ├── settings.py             # API keys (from env vars)
│   └── llm_router_simple.py    # LLM routing (OpenRouter)
├── data/
│   ├── market_data.py          # Market data fetcher
│   └── mock_data.py            # Mock data generator (MVP)
├── tools/
│   └── telegram_notifier.py    # Telegram notifications
├── tests/
├── run_analysis.py             # Daily runner script
├── .gitignore                  # Protects API keys
└── README.md                   # This file
```

---

## Configuration

All API keys are loaded from environment variables (see `config/settings.py`):

**Required:**
- `OPENROUTER_API_KEY` ✓
- `GEMINI_API_KEY` ✓

**Optional:**
- `212_TRADING_API_KEY` - For real portfolio data (Phase 2)
- `EXA_SEARCH_API_KEY` - For enhanced news search (Phase 2)
- `TELEGRAM_BOT_TOKEN` ✓ - For daily notifications (configured)
- `TELEGRAM_CHAT_ID` ✓ - Your Telegram chat ID (configured)

**To enable Telegram notifications:**
1. Start your bot by sending `/start` to it in Telegram
2. Get your chat_id:
   - Send any message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":123456789}`
3. Set `TELEGRAM_CHAT_ID` environment variable

---

## MVP Limitations

Current version (MVP):
- ✅ Mock portfolio data (real 212 API in Phase 2)
- ✅ Mock market data (Yahoo Finance was blocked, real APIs in Phase 2)
- ✅ No database persistence yet (Neon/Pinecone in Phase 2)
- ✅ Telegram notifications ready (needs bot to be started by user)
- ✅ OpenRouter only (Gemini SDK has dependency issues, will fix)

**Phase 2 will add real data sources and 6-agent system.**

---

## Next Steps (Phase 2)

1. **Fix Gemini SDK** - Use $200 Google credits
2. **Integrate 212 Trading API** - Real portfolio data
3. **Add News + Technical agents** - 6-agent system
4. **Add Risk Manager** - Override authority
5. **Database integration** - Neon + Pinecone
6. **Notifications** - Email + Telegram

---

## Testing

### Test Individual Agents

```bash
# Test Portfolio Analyst
python3 agents/portfolio_analyst.py

# Test Market Analyst
python3 agents/market_analyst.py

# Test Full System
python3 agents/orchestrator.py
```

### Test Data Generators

```bash
# Test mock data
python3 data/mock_data.py
```

---

## Troubleshooting

**Issue:** `ModuleNotFoundError`
**Fix:** Run from `trading-agents/` directory

**Issue:** API key errors
**Fix:** Ensure environment variables are set (already done via system)

**Issue:** High costs
**Fix:** Check `llm_router.get_total_cost()` - should be ~$0.014 per run

---

## Cost Monitoring

Built-in cost tracking:

```python
from config.llm_router_simple import LLMRouter

llm_router = LLMRouter(...)
# ... use router ...
print(f"Total cost: ${llm_router.get_total_cost()}")
```

---

## Security

- ✅ `.gitignore` configured to exclude API keys
- ✅ API keys loaded from environment (never stored in code)
- ✅ No credentials in repository

---

## Performance

**Typical run time:** 10-15 seconds
**Typical cost:** $0.014 per run
**Recommendations:** 1-3 actionable items

---

## Support

For issues or questions:
1. Check logs for errors
2. Verify API keys are set
3. Test individual agents first
4. Review cost tracking

---

## License

Internal use only.

---

**Last Updated:** November 17, 2025
**MVP Status:** ✅ Functional - Ready for Phase 2
