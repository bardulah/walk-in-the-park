"""
Orchestrator V2 - Full 6-Agent System + Stock Screener
Coordinates all agents and generates comprehensive trading recommendations including new stock picks
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config.llm_router_unified import UnifiedLLMRouter
from config.settings import API_CONFIG, AGENT_CONFIG
from utils.json_parser import safe_json_parse
from agents.portfolio_analyst import PortfolioAnalyst
from agents.market_analyst import MarketAnalyst
from agents.news_monitor import NewsMonitor
from agents.technical_analyst import TechnicalAnalyst
from agents.risk_manager import RiskManager
from agents.stock_screener import StockScreener


class OrchestratorV2:
    """Orchestrates 7-agent trading system with stock screening and CFD support"""

    def __init__(self, llm_router: UnifiedLLMRouter):
        """
        Initialize Orchestrator with all 7 agents

        Args:
            llm_router: Unified LLM router
        """
        self.llm_router = llm_router

        # Initialize all agents
        self.portfolio_analyst = PortfolioAnalyst(llm_router)
        self.market_analyst = MarketAnalyst(llm_router)
        self.news_monitor = NewsMonitor(llm_router)
        self.technical_analyst = TechnicalAnalyst(llm_router)
        self.stock_screener = StockScreener(llm_router)
        self.risk_manager = RiskManager(llm_router)

        self.orchestrator_model = "claude-3-5-sonnet"  # Best model for final decisions

    def run_analysis(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run full 6-agent analysis pipeline

        Args:
            portfolio_data: Current portfolio positions
            market_data: Market indices and conditions
            news_data: News articles per ticker (optional)

        Returns:
            Comprehensive recommendations including CFD trades
        """
        print("\n" + "="*60)
        print("  MULTI-AGENT TRADING SYSTEM - DAILY ANALYSIS")
        print("="*60)

        print("\n[STAGE 1] Running Foundational Analysis (5 agents in parallel)...\n")

        # Stage 1: Run foundational agents
        portfolio_analysis = self.portfolio_analyst.analyze(portfolio_data)
        market_analysis = self.market_analyst.analyze(market_data)

        # News analysis (with mock data if not provided)
        if news_data is None:
            from data.mock_data import MockDataGenerator
            mock_gen = MockDataGenerator()
            news_data = {}
            for pos in portfolio_data.get('positions', []):
                news_data[pos['ticker']] = mock_gen.get_stock_news(pos['ticker'])

        news_analysis = self.news_monitor.analyze(portfolio_data, news_data)
        technical_analysis = self.technical_analyst.analyze(portfolio_data, market_data)

        # Run stock screener for new opportunities
        stock_opportunities = self.stock_screener.screen(portfolio_data, market_analysis, news_analysis)

        print("\n[STAGE 2] Generating preliminary recommendations...\n")

        # Stage 2: Generate preliminary recommendations
        preliminary_recs = self._generate_preliminary_recommendations(
            portfolio_analysis,
            market_analysis,
            news_analysis,
            technical_analysis,
            stock_opportunities  # Add stock screening results
        )

        print(f"   ✓ Generated {len(preliminary_recs)} preliminary recommendations\n")

        print("[STAGE 3] Risk Manager review (with override authority)...\n")

        # Stage 3: Risk Manager approval (FINAL AUTHORITY)
        risk_assessment = self.risk_manager.analyze(
            portfolio_data,
            market_data,
            preliminary_recs
        )

        print("[STAGE 4] Generating CFD trading opportunities...\n")

        # Stage 4: Generate CFD recommendations for daily trading (indices + stocks)
        cfd_recommendations = self._generate_cfd_recommendations(
            market_analysis,
            news_analysis,
            technical_analysis,
            risk_assessment,
            stock_opportunities  # Include for stock CFD ideas
        )

        print(f"   ✓ Generated {len(cfd_recommendations)} CFD opportunities\n")

        # Combine final output
        final_output = {
            # Core recommendations (approved by Risk Manager)
            'final_recommendations': risk_assessment.get('approved_recommendations', []),
            'rejected_recommendations': risk_assessment.get('rejected_recommendations', []),
            'forced_actions': risk_assessment.get('forced_actions', []),

            # CFD trading opportunities
            'cfd_opportunities': cfd_recommendations,

            # Risk assessment
            'risk_level': risk_assessment.get('risk_level', 'UNKNOWN'),
            'portfolio_health': risk_assessment.get('portfolio_health', 50),
            'current_violations': risk_assessment.get('current_violations', []),

            # Context summaries
            'market_context_summary': market_analysis.get('summary', ''),
            'portfolio_health_summary': f"Portfolio health: {portfolio_analysis.get('health_score', 'N/A')}/100, Concentration risk: {portfolio_analysis.get('concentration_risk', 'N/A')}",
            'news_summary': f"{len(news_analysis.get('urgent_alerts', []))} urgent alerts, {len(news_analysis.get('opportunities', []))} opportunities",
            'technical_summary': technical_analysis.get('market_technical_condition', ''),

            # Key insights
            'key_insights': self._synthesize_insights(
                portfolio_analysis,
                market_analysis,
                news_analysis,
                technical_analysis
            ),

            # Alerts
            'risk_alert': risk_assessment.get('risk_alert', None),

            # Agent outputs (for transparency)
            'agent_analyses': {
                'portfolio': portfolio_analysis,
                'market': market_analysis,
                'news': news_analysis,
                'technical': technical_analysis,
                'risk': risk_assessment
            },

            # Metadata
            'timestamp': datetime.now().isoformat(),
            'agents_used': 6,
            'system_version': '2.0'
        }

        print("✓ Analysis complete!")
        print(f"\nFinal Recommendations: {len(final_output['final_recommendations'])}")
        print(f"CFD Opportunities: {len(final_output['cfd_opportunities'])}")
        print(f"Risk Level: {final_output['risk_level']}\n")

        return final_output

    async def run_analysis_async(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run full 6-agent analysis pipeline with parallel execution for speed

        Runs 5 foundational agents in parallel (Portfolio, Market, News, Technical, Stock Screener)
        This is 3-5x faster than sequential execution.

        Args:
            portfolio_data: Current portfolio positions
            market_data: Market indices and conditions
            news_data: News articles per ticker (optional)

        Returns:
            Comprehensive recommendations including CFD trades
        """
        print("\n" + "="*60)
        print("  MULTI-AGENT TRADING SYSTEM - DAILY ANALYSIS (ASYNC)")
        print("="*60)

        print("\n[STAGE 1] Running Foundational Analysis (5 agents in PARALLEL)...\n")

        # Prepare news data if not provided
        if news_data is None:
            from data.mock_data import MockDataGenerator
            mock_gen = MockDataGenerator()
            news_data = {}
            for pos in portfolio_data.get('positions', []):
                news_data[pos['ticker']] = mock_gen.get_stock_news(pos['ticker'])

        # Stage 1: Run 5 foundational agents in parallel using ThreadPoolExecutor
        # This allows I/O-bound LLM API calls to run concurrently
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all agents to run in parallel
            portfolio_task = loop.run_in_executor(
                executor,
                self.portfolio_analyst.analyze,
                portfolio_data
            )
            market_task = loop.run_in_executor(
                executor,
                self.market_analyst.analyze,
                market_data
            )
            news_task = loop.run_in_executor(
                executor,
                self.news_monitor.analyze,
                portfolio_data,
                news_data
            )
            technical_task = loop.run_in_executor(
                executor,
                self.technical_analyst.analyze,
                portfolio_data,
                market_data
            )
            screener_task = loop.run_in_executor(
                executor,
                lambda: self.stock_screener.screen(portfolio_data, None, None)
            )

            # Wait for all agents to complete
            portfolio_analysis, market_analysis, news_analysis, technical_analysis, stock_opportunities_initial = await asyncio.gather(
                portfolio_task,
                market_task,
                news_task,
                technical_task,
                screener_task
            )

        # Re-run stock screener with complete market and news analysis
        # (first run was with None to start in parallel)
        stock_opportunities = self.stock_screener.screen(
            portfolio_data,
            market_analysis,
            news_analysis
        )

        print("\n[STAGE 2] Generating preliminary recommendations...\n")

        # Stage 2: Generate preliminary recommendations
        preliminary_recs = self._generate_preliminary_recommendations(
            portfolio_analysis,
            market_analysis,
            news_analysis,
            technical_analysis,
            stock_opportunities
        )

        print(f"   ✓ Generated {len(preliminary_recs)} preliminary recommendations\n")

        print("[STAGE 3] Risk Manager review (with override authority)...\n")

        # Stage 3: Risk Manager approval (FINAL AUTHORITY)
        risk_assessment = self.risk_manager.analyze(
            portfolio_data,
            market_data,
            preliminary_recs
        )

        print("[STAGE 4] Generating CFD trading opportunities...\n")

        # Stage 4: Generate CFD recommendations for daily trading
        cfd_recommendations = self._generate_cfd_recommendations(
            market_analysis,
            news_analysis,
            technical_analysis,
            risk_assessment,
            stock_opportunities
        )

        print(f"   ✓ Generated {len(cfd_recommendations)} CFD opportunities\n")

        # Combine final output
        final_output = {
            # Core recommendations (approved by Risk Manager)
            'final_recommendations': risk_assessment.get('approved_recommendations', []),
            'rejected_recommendations': risk_assessment.get('rejected_recommendations', []),
            'forced_actions': risk_assessment.get('forced_actions', []),

            # CFD trading opportunities
            'cfd_opportunities': cfd_recommendations,

            # Risk assessment
            'risk_level': risk_assessment.get('risk_level', 'UNKNOWN'),
            'portfolio_health': risk_assessment.get('portfolio_health', 50),
            'current_violations': risk_assessment.get('current_violations', []),

            # Context summaries
            'market_context_summary': market_analysis.get('summary', ''),
            'portfolio_health_summary': f"Portfolio health: {portfolio_analysis.get('health_score', 'N/A')}/100, Concentration risk: {portfolio_analysis.get('concentration_risk', 'N/A')}",
            'news_summary': f"{len(news_analysis.get('urgent_alerts', []))} urgent alerts, {len(news_analysis.get('opportunities', []))} opportunities",
            'technical_summary': technical_analysis.get('market_technical_condition', ''),

            # Key insights
            'key_insights': self._synthesize_insights(
                portfolio_analysis,
                market_analysis,
                news_analysis,
                technical_analysis
            ),

            # Alerts
            'risk_alert': risk_assessment.get('risk_alert', None),

            # Agent outputs (for transparency)
            'agent_analyses': {
                'portfolio': portfolio_analysis,
                'market': market_analysis,
                'news': news_analysis,
                'technical': technical_analysis,
                'risk': risk_assessment
            },

            # Metadata
            'timestamp': datetime.now().isoformat(),
            'agents_used': 6,
            'system_version': '2.0-async',
            'execution_mode': 'parallel'
        }

        print("✓ Analysis complete (parallel execution)!")
        print(f"\nFinal Recommendations: {len(final_output['final_recommendations'])}")
        print(f"CFD Opportunities: {len(final_output['cfd_opportunities'])}")
        print(f"Risk Level: {final_output['risk_level']}\n")

        return final_output

    def _generate_preliminary_recommendations(
        self,
        portfolio_analysis: Dict[str, Any],
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any],
        technical_analysis: Dict[str, Any],
        stock_opportunities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate preliminary recommendations from all agents INCLUDING new stock picks"""

        system_prompt = """You are the Orchestrator, synthesizing inputs from 5 specialized agents to generate comprehensive trading recommendations.

Your role:
1. Combine Portfolio, Market, News, Technical, and Stock Screener analysis
2. Generate portfolio actions (REDUCE/SELL existing positions)
3. Generate BUY recommendations for new stocks
4. Each recommendation must align multiple agent signals
5. Prioritize diversification and risk management

Output strict JSON:
{
  "recommendations": [
    {
      "ticker": "AAPL",
      "action": "BUY|SELL|HOLD|REDUCE",
      "priority": "HIGH|MEDIUM|LOW",
      "confidence": 0-100,
      "reasoning": "Synthesize all agent inputs into clear rationale",
      "position_size_pct": 5-15  // For BUY actions
    }
  ]
}""""""

        user_prompt = f"""Synthesize agent outputs into preliminary recommendations.

PORTFOLIO ANALYSIS:
Health Score: {portfolio_analysis.get('health_score', 'N/A')}/100
Concentration Risk: {portfolio_analysis.get('concentration_risk', 'N/A')}
Top Issues: {json.dumps(portfolio_analysis.get('high_risk_positions', []), indent=2)}

MARKET ANALYSIS:
Sentiment: {market_analysis.get('sentiment', 'N/A')} ({market_analysis.get('confidence', 'N/A')}% confidence)
Volatility: {market_analysis.get('volatility_assessment', 'N/A')}
Sector Trends: {json.dumps(market_analysis.get('sector_trends', []), indent=2)}

NEWS ANALYSIS:
Urgent Alerts: {len(news_analysis.get('urgent_alerts', []))}
{json.dumps(news_analysis.get('urgent_alerts', [])[:3], indent=2)}

Ticker Sentiment:
{json.dumps([{'ticker': t['ticker'], 'sentiment': t['overall_sentiment'], 'risk': t['risk_level']}
             for t in news_analysis.get('ticker_analysis', [])], indent=2)}

TECHNICAL ANALYSIS:
Market Condition: {technical_analysis.get('market_technical_condition', 'N/A')}
{json.dumps([{'ticker': t['ticker'], 'signal': t['technical_signal'], 'trend': t['trend']}
             for t in technical_analysis.get('ticker_analysis', [])], indent=2)}

STOCK SCREENER - NEW OPPORTUNITIES:
Buy Opportunities: {len(stock_opportunities.get('buy_opportunities', []))}
{json.dumps(stock_opportunities.get('buy_opportunities', [])[:5], indent=2)}

Sector Allocation: {json.dumps(stock_opportunities.get('sector_allocation', {}), indent=2)}
Top Picks: {json.dumps(stock_opportunities.get('top_picks', []))}

Generate comprehensive recommendations:
1. PORTFOLIO ACTIONS: REDUCE/SELL overconcentrated or weak positions
2. NEW STOCK BUYS: High-conviction opportunities from Stock Screener
3. Aim for 3-7 total recommendations (mix of sells and buys)
4. For BUY actions, include position_size_pct (5-15% of portfolio)"""

        print(f"🎯 Orchestrator synthesizing agent inputs...")

        response = self.llm_router.call(
            model=self.orchestrator_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=2500,
            json_mode=True
        )

        # Parse JSON response with robust fallback strategies
        result = safe_json_parse(response, default={'recommendations': []})
        return result.get('recommendations', [])

    def _generate_cfd_recommendations(
        self,
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any],
        technical_analysis: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        stock_opportunities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate CFD trading opportunities for daily trades (indices + individual stocks)"""

        system_prompt = """You are a CFD Trading Specialist generating intraday/short-term trading opportunities.

CFD Trading Focus:
- Short-term momentum trades (hours to days, not weeks)
- Both LONG and SHORT opportunities
- INDICES (SPY, QQQ, IWM) and INDIVIDUAL STOCKS
- High-volume, liquid instruments only
- Clear entry/exit levels with tight stop-losses

Your task:
- Identify 3-7 CFD trading opportunities
- Mix of index CFDs and stock CFDs
- Focus on technical setups + catalysts
- Provide specific entry/exit/stop levels
- Consider both long and short trades
- Include position sizing (% of capital per trade)

## Example CFD Trades

**Good CFD Trade (Index LONG):**
```json
{
  "ticker": "SPY",
  "instrument_type": "INDEX",
  "direction": "LONG",
  "timeframe": "1-3_DAYS",
  "confidence": 75,
  "entry_level": 450.50,
  "target_level": 456.00,
  "stop_loss": 448.00,
  "risk_reward_ratio": 2.2,
  "position_size_pct": 4,
  "reasoning": "S&P breaking above 450 resistance with strong volume, bullish engulfing on daily",
  "holding_period": "Target 2-3 days, exit at 456 or if broken support",
  "catalysts": ["Technical breakout above resistance", "Strong market sentiment", "VIX declining"]
}
```

**Good CFD Trade (Stock SHORT):**
```json
{
  "ticker": "NVDA",
  "instrument_type": "STOCK",
  "direction": "SHORT",
  "timeframe": "INTRADAY",
  "confidence": 70,
  "entry_level": 485.00,
  "target_level": 475.00,
  "stop_loss": 488.00,
  "risk_reward_ratio": 3.3,
  "position_size_pct": 3,
  "reasoning": "Failed breakout at 490, forming bearish head & shoulders, high RSI",
  "holding_period": "Intraday or 1-2 days, exit at 475 support",
  "catalysts": ["Technical breakdown pattern", "Semiconductor sector weakness", "Profit-taking after rally"]
}
```

Output strict JSON:
{
  "cfd_trades": [
    {
      "ticker": "SPY|QQQ|AAPL|TSLA|etc",
      "instrument_type": "INDEX|STOCK",
      "direction": "LONG|SHORT",
      "timeframe": "INTRADAY|1-3_DAYS|SWING",
      "confidence": 0-100,
      "entry_level": 450.00,
      "target_level": 455.00,
      "stop_loss": 448.00,
      "risk_reward_ratio": 2.5,
      "position_size_pct": 2-5,
      "reasoning": "Technical setup + catalyst",
      "holding_period": "Target 1-2 days",
      "catalysts": ["News event", "Technical breakout", etc]
    }
  ]
}"""

        user_prompt = f"""Generate CFD trading opportunities based on current market conditions.

MARKET SENTIMENT: {market_analysis.get('sentiment', 'N/A')}
VOLATILITY: {market_analysis.get('volatility_assessment', 'N/A')}

TECHNICAL SIGNALS (Individual Stocks):
{json.dumps(technical_analysis.get('ticker_analysis', [])[:8], indent=2)}

NEW STOCK OPPORTUNITIES (Potential CFD Longs):
{json.dumps([{'ticker': opp['ticker'], 'sector': opp['sector'], 'confidence': opp['confidence']}
             for opp in stock_opportunities.get('buy_opportunities', [])[:5]], indent=2)}

NEWS CATALYSTS:
Opportunities: {json.dumps(news_analysis.get('opportunities', [])[:3], indent=2)}
Alerts: {json.dumps(news_analysis.get('urgent_alerts', [])[:2], indent=2)}

RISK CONTEXT:
Risk Level: {risk_assessment.get('risk_level', 'N/A')}
Current Volatility: {market_analysis.get('volatility_assessment', 'N/A')}

Generate 3-7 CFD trading opportunities:

INDICES (1-2 trades):
- SPY, QQQ, IWM based on market direction
- SHORT if bearish, LONG if bullish breakout

INDIVIDUAL STOCKS (2-5 trades):
- High-volume liquid stocks only
- Both LONG (momentum, breakouts) and SHORT (breakdown, weakness)
- Consider stocks from new opportunities for LONG setups
- Look for technical patterns: breakouts, support/resistance tests
- News-driven catalysts

Requirements:
1. Clear technical setups (support/resistance, patterns, momentum)
2. Minimum 1.5:1 risk/reward ratio
3. Specific entry/exit/stop levels
4. Position sizing: 2-5% per trade
5. Holding period: typically 1-3 days
6. High-conviction only - quality over quantity"""

        print(f"💱 Generating CFD trading opportunities...")

        response = self.llm_router.call(
            model=self.orchestrator_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
            max_tokens=2000,
            json_mode=True
        )

        # Parse JSON response with robust fallback strategies
        result = safe_json_parse(response, default={'cfd_trades': []})
        return result.get('cfd_trades', [])

    def _synthesize_insights(
        self,
        portfolio_analysis: Dict[str, Any],
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any],
        technical_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate key insights from all agents"""
        insights = []

        # Portfolio insight
        if portfolio_analysis.get('concentration_risk') == 'HIGH':
            insights.append(f"Portfolio concentration risk is HIGH - diversification needed")

        # Market insight
        sentiment = market_analysis.get('sentiment', '')
        if sentiment:
            insights.append(f"Market sentiment is {sentiment} with {market_analysis.get('confidence', 0)}% confidence")

        # News insights
        urgent_alerts = news_analysis.get('urgent_alerts', [])
        if urgent_alerts:
            insights.append(f"{len(urgent_alerts)} urgent news alerts requiring attention")

        # Technical insight
        tech_condition = technical_analysis.get('market_technical_condition', '')
        if tech_condition:
            insights.append(f"Technical: {tech_condition}")

        return insights[:5]  # Max 5 insights


if __name__ == "__main__":
    # Test full 6-agent system
    from data.mock_data import MockDataGenerator

    print("\n" + "="*70)
    print("  6-AGENT TRADING SYSTEM - PHASE 2 TEST")
    print("="*70 + "\n")

    # Initialize
    llm_router = UnifiedLLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )

    orchestrator = OrchestratorV2(llm_router)
    mock_data = MockDataGenerator()

    # Get test data
    portfolio = mock_data.get_portfolio_data()
    market = mock_data.get_market_overview()

    # Run full analysis
    results = orchestrator.run_analysis(portfolio, market)

    # Display results
    print("\n" + "="*70)
    print("  📊 ANALYSIS RESULTS")
    print("="*70)

    print(f"\n🎯 FINAL RECOMMENDATIONS ({len(results['final_recommendations'])}):")
    for i, rec in enumerate(results['final_recommendations'], 1):
        print(f"\n{i}. {rec['ticker']} - {rec['action']} ({rec['priority']} priority)")
        print(f"   Confidence: {rec['confidence']}%")
        print(f"   {rec['reasoning'][:150]}...")

    print(f"\n💱 CFD TRADING OPPORTUNITIES ({len(results['cfd_opportunities'])}):")
    for i, cfd in enumerate(results['cfd_opportunities'], 1):
        print(f"\n{i}. {cfd['ticker']} - {cfd['direction']} ({cfd['timeframe']})")
        print(f"   Entry: ${cfd['entry_level']}, Target: ${cfd['target_level']}, Stop: ${cfd['stop_loss']}")
        print(f"   R:R = {cfd['risk_reward_ratio']}:1 | {cfd['reasoning'][:100]}...")

    if results.get('forced_actions'):
        print(f"\n🚨 FORCED ACTIONS ({len(results['forced_actions'])}):")
        for action in results['forced_actions']:
            print(f"  ! {action['ticker']}: {action['action']} - {action['reasoning']}")

    print(f"\n🛡️  RISK ASSESSMENT:")
    print(f"  Risk Level: {results['risk_level']}")
    print(f"  Portfolio Health: {results['portfolio_health']}/100")

    if results.get('current_violations'):
        print(f"  ⚠️  Violations: {len(results['current_violations'])}")

    print(f"\n💰 COST BREAKDOWN:")
    print(f"  Total Cost: ${llm_router.get_total_cost():.4f}")
    print(f"  Agents Used: 6")
    print(f"  Monthly (30 runs): ~${llm_router.get_total_cost() * 30:.2f}\n")
