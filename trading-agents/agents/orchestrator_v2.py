"""
Orchestrator V2 - Full 6-Agent System
Coordinates all agents and generates comprehensive trading recommendations including CFDs
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
from typing import Dict, Any, List
from datetime import datetime
from config.llm_router_unified import UnifiedLLMRouter
from config.settings import API_CONFIG, AGENT_CONFIG
from agents.portfolio_analyst import PortfolioAnalyst
from agents.market_analyst import MarketAnalyst
from agents.news_monitor import NewsMonitor
from agents.technical_analyst import TechnicalAnalyst
from agents.risk_manager import RiskManager


class OrchestratorV2:
    """Orchestrates 6-agent trading system with CFD support"""

    def __init__(self, llm_router: UnifiedLLMRouter):
        """
        Initialize Orchestrator with all 6 agents

        Args:
            llm_router: Unified LLM router
        """
        self.llm_router = llm_router

        # Initialize all agents
        self.portfolio_analyst = PortfolioAnalyst(llm_router)
        self.market_analyst = MarketAnalyst(llm_router)
        self.news_monitor = NewsMonitor(llm_router)
        self.technical_analyst = TechnicalAnalyst(llm_router)
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

        print("\n[STAGE 1] Running Foundational Analysis (4 agents in parallel)...\n")

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

        print("\n[STAGE 2] Generating preliminary recommendations...\n")

        # Stage 2: Generate preliminary recommendations
        preliminary_recs = self._generate_preliminary_recommendations(
            portfolio_analysis,
            market_analysis,
            news_analysis,
            technical_analysis
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
            risk_assessment
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

    def _generate_preliminary_recommendations(
        self,
        portfolio_analysis: Dict[str, Any],
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any],
        technical_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate preliminary recommendations from all agents"""

        system_prompt = """You are the Orchestrator, synthesizing inputs from 4 specialized agents to generate preliminary trading recommendations.

Your role:
1. Combine Portfolio, Market, News, and Technical analysis
2. Generate 1-5 actionable recommendations
3. Each recommendation must align multiple agent signals
4. Be specific and data-driven

Output strict JSON:
{
  "recommendations": [
    {
      "ticker": "AAPL",
      "action": "BUY|SELL|HOLD|REDUCE",
      "priority": "HIGH|MEDIUM|LOW",
      "confidence": 0-100,
      "reasoning": "Synthesize all agent inputs into clear rationale"
    }
  ]
}"""

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

Generate 1-5 high-conviction recommendations that synthesize all signals."""

        print(f"🎯 Orchestrator synthesizing agent inputs...")

        response = self.llm_router.call(
            model=self.orchestrator_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=2500,
            json_mode=True
        )

        result = json.loads(response)
        return result.get('recommendations', [])

    def _generate_cfd_recommendations(
        self,
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any],
        technical_analysis: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate CFD trading opportunities for daily trades"""

        system_prompt = """You are a CFD Trading Specialist generating intraday/short-term trading opportunities.

CFD Trading Focus:
- Short-term momentum trades (hours to days, not weeks)
- Both LONG and SHORT opportunities
- High-volume, liquid instruments
- Clear entry/exit levels
- Tight stop-losses

Your task:
- Identify 2-5 CFD trading opportunities
- Focus on technical setups + catalysts
- Provide specific entry/exit/stop levels
- Consider both long and short trades

Output strict JSON:
{
  "cfd_trades": [
    {
      "ticker": "SPY",
      "direction": "LONG|SHORT",
      "timeframe": "INTRADAY|1-3_DAYS|SWING",
      "confidence": 0-100,
      "entry_level": 450.00,
      "target_level": 455.00,
      "stop_loss": 448.00,
      "risk_reward_ratio": 2.5,
      "reasoning": "Technical setup + catalyst",
      "holding_period": "Target 1-2 days"
    }
  ]
}"""

        user_prompt = f"""Generate CFD trading opportunities based on current market conditions.

MARKET SENTIMENT: {market_analysis.get('sentiment', 'N/A')}
VOLATILITY: {market_analysis.get('volatility_assessment', 'N/A')}

TECHNICAL SIGNALS:
{json.dumps(technical_analysis.get('ticker_analysis', [])[:5], indent=2)}

NEWS CATALYSTS:
Opportunities: {json.dumps(news_analysis.get('opportunities', [])[:3], indent=2)}
Alerts: {json.dumps(news_analysis.get('urgent_alerts', [])[:2], indent=2)}

RISK CONTEXT:
Risk Level: {risk_assessment.get('risk_level', 'N/A')}
Current Volatility: {market_analysis.get('volatility_assessment', 'N/A')}

Generate 2-5 CFD trading opportunities focusing on:
1. Clear technical setups
2. News catalysts or momentum
3. Both long and short opportunities
4. Specific entry/exit/stop levels
5. Reasonable risk/reward (minimum 1.5:1)

Be selective - only high-conviction setups."""

        print(f"💱 Generating CFD trading opportunities...")

        response = self.llm_router.call(
            model=self.orchestrator_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
            max_tokens=2000,
            json_mode=True
        )

        result = json.loads(response)
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
