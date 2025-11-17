#!/usr/bin/env python3
"""
Daily Trading Analysis Runner
Simple script to run the multi-agent trading system analysis
"""
import sys
import json
from datetime import datetime
from agents.orchestrator import Orchestrator
from config.llm_router_simple import LLMRouter
from config.settings import API_CONFIG
from data.mock_data import MockDataGenerator
from tools.telegram_notifier import TelegramNotifier

def main():
    """Run daily trading analysis"""
    print("\n" + "="*70)
    print(f"  DAILY TRADING ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        # Initialize LLM router
        llm_router = LLMRouter(
            gemini_api_key=API_CONFIG.gemini_api_key,
            openrouter_api_key=API_CONFIG.openrouter_api_key
        )

        # Initialize orchestrator
        orchestrator = Orchestrator(llm_router)

        # Get data (using mock data for MVP)
        mock_data = MockDataGenerator()
        portfolio = mock_data.get_portfolio_data()
        market = mock_data.get_market_overview()

        print("\n📊 Data Sources:")
        print(f"   Portfolio: Mock data ({len(portfolio.get('positions', []))} positions)")
        print(f"   Market: Mock data (SPY, QQQ, VIX)")

        # Run analysis
        recommendations = orchestrator.run_analysis(portfolio, market)

        # Display results
        print("\n" + "="*70)
        print("  📈 FINAL RECOMMENDATIONS")
        print("="*70)

        for i, rec in enumerate(recommendations.get('final_recommendations', []), 1):
            print(f"\n{i}. {rec['ticker']} - {rec['action']} ({rec['priority']} priority)")
            print(f"   Confidence: {rec['confidence']}%")
            print(f"   Reasoning: {rec['reasoning']}")

        # Market context
        print(f"\n📊 Market Context:")
        print(f"   {recommendations.get('market_context_summary', 'N/A')}")

        # Portfolio health
        print(f"\n💼 Portfolio Health:")
        print(f"   {recommendations.get('portfolio_health_summary', 'N/A')}")

        # Risk alert
        if recommendations.get('risk_alert'):
            print(f"\n⚠️  RISK ALERT:")
            print(f"   {recommendations['risk_alert']}")

        # Cost summary
        print(f"\n" + "="*70)
        print(f"💰 Cost Summary:")
        print(f"   This run: ${llm_router.get_total_cost():.4f}")
        print(f"   Daily (1 run): ~${llm_router.get_total_cost():.4f}")
        print(f"   Monthly (30 runs): ~${llm_router.get_total_cost() * 30:.2f}")
        print("="*70 + "\n")

        # Send Telegram notification
        telegram = TelegramNotifier(
            bot_token=API_CONFIG.telegram_bot_token,
            chat_id=API_CONFIG.telegram_chat_id
        )
        if telegram.is_configured():
            print("📱 Sending Telegram notification...")
            if telegram.send_daily_analysis(recommendations, llm_router.get_total_cost()):
                print("   ✓ Telegram notification sent\n")
            else:
                print("   ⚠️  Failed to send Telegram notification\n")
        else:
            print("ℹ️  Telegram not configured (skipping notification)\n")

        # Save to file (optional)
        output_file = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'portfolio': portfolio,
                'market': market,
                'recommendations': recommendations,
                'cost': llm_router.get_total_cost()
            }, f, indent=2)

        print(f"✓ Analysis saved to: {output_file}\n")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
